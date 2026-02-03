import os
import json
from typing import List, Dict, Any
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv
import psycopg2
from openai import AzureOpenAI
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel
import asyncio

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Config
AZURE_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT")
AZURE_API_KEY = os.environ.get("AZURE_OPENAI_API_KEY")
AZURE_DEPLOYMENT = os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME", "text-embedding-3-large")
MODEL_NAME = os.environ.get("BASE_MODEL_NAME", "Qwen/Qwen2-7B-Instruct")
ADAPTER_DIR = os.path.join(os.path.dirname(__file__), "models", "lora_adapter")

PGHOST = os.environ.get("PGHOST")
PGUSER = os.environ.get("PGUSER")
PGPASSWORD = os.environ.get("PGPASSWORD")
PGDATABASE = os.environ.get("PGDATABASE", "postgres")
PGPORT = os.environ.get("PGPORT", "5432")

# Global model and tokenizer
model = None
tokenizer = None
embedding_client = None


def get_db_connection():
    return psycopg2.connect(
        host=PGHOST,
        port=PGPORT,
        dbname=PGDATABASE,
        user=PGUSER,
        password=PGPASSWORD,
        sslmode="require",
    )


def load_model():
    global model, tokenizer
    if model is None:
        tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
        tokenizer.pad_token = tokenizer.eos_token
        base_model = AutoModelForCausalLM.from_pretrained(
            MODEL_NAME,
            torch_dtype=torch.float16,
            device_map="auto",
        )
        model = PeftModel.from_pretrained(base_model, ADAPTER_DIR)
        model.config.pad_token_id = tokenizer.pad_token_id
    return model, tokenizer


def get_embedding_client():
    global embedding_client
    if embedding_client is None:
        embedding_client = AzureOpenAI(
            api_key=AZURE_API_KEY,
            api_version="2024-02-15-preview",
            azure_endpoint=AZURE_ENDPOINT,
        )
    return embedding_client


def generate_query_embedding(query: str) -> List[float]:
    client = get_embedding_client()
    response = client.embeddings.create(
        model=AZURE_DEPLOYMENT,
        input=query
    )
    return response.data[0].embedding


def search_chunks(query_embedding: List[float], top_k: int = 5) -> List[Dict]:
    conn = get_db_connection()
    cur = conn.cursor()
    
    embedding_str = str(query_embedding)
    
    cur.execute("""
        SELECT 
            c.id,
            c.text,
            c.chunk_index,
            c.section_heading,
            d.filename,
            d.page_title,
            1 - (c.embedding <=> %s::vector) as similarity
        FROM chunks c
        JOIN documents d ON c.document_id = d.id
        WHERE c.embedding IS NOT NULL
        ORDER BY c.embedding <=> %s::vector
        LIMIT %s
    """, (embedding_str, embedding_str, top_k))
    
    results = []
    for row in cur.fetchall():
        results.append({
            "id": str(row[0]),
            "text": row[1],
            "chunk_index": row[2],
            "section_heading": row[3],
            "filename": row[4],
            "page_title": row[5],
            "similarity": float(row[6]),
        })
    
    cur.close()
    conn.close()
    return results


def extract_assistant_response(full_output: str) -> str:
    if "assistant" in full_output.lower():
        parts = full_output.split("assistant")
        if len(parts) > 1:
            answer = parts[-1].strip()
            if "\nuser\n" in answer:
                answer = answer.split("\nuser\n")[0]
            if "\nsystem\n" in answer:
                answer = answer.split("\nsystem\n")[0]
            return answer.strip()
    return full_output.strip()


def strip_chunk_metadata(text: str) -> str:
    parts = text.split("\n\n", 1)
    return parts[1] if len(parts) == 2 else text


def is_explanation_query(query: str) -> bool:
    """Simple check for 'explain / overview' style questions."""
    q = query.lower()
    keywords = [
        "explain ",
        "overview",
        "in simple terms",
        "high level",
        "summary of",
    ]
    return any(k in q for k in keywords)


def is_glossary_section(heading) -> bool:
    """Detect basic glossary / definition headings."""
    if not heading:
        return False
    h = str(heading).lower()
    return ("glossary" in h) or ("definition" in h)


# --- Planner (rule-based, predictable) ---
def planner_plan(user_query: str) -> Dict[str, Any]:
    """Planner Agent: decide intent, language, answer style, retrieval size, refinement."""
    q = user_query.strip().lower()
    # Language: default English; detect Arabic by script or common words
    response_language = "en"
    if any("\u0600" <= c <= "\u06FF" for c in user_query):
        response_language = "ar"
    # Intent
    if any(x in q for x in ["explain", "overview", "what is", "what are", "how does", "why"]):
        query_intent = "explanation"
    elif any(x in q for x in ["list", "which are", "name the", "what are the"]):
        query_intent = "list"
    elif any(x in q for x in ["how to", "steps", "procedure", "process"]):
        query_intent = "procedural"
    else:
        query_intent = "general"
    # Answer style: conversational for explanation, structured for list
    answer_style = "conversational" if query_intent == "explanation" else "structured"
    # Retrieval: more chunks for complex/explanation
    top_k = 8 if query_intent == "explanation" else 5
    # Refinement: off by default for latency; set True for explanation if needed
    use_refiner = False
    return {
        "response_language": response_language,
        "query_intent": query_intent,
        "answer_style": answer_style,
        "top_k": top_k,
        "use_refiner": use_refiner,
    }


# --- Reranker: relevance + diversity, limit N ---
def rerank_chunks(chunks: List[Dict], top_n: int = 5) -> List[Dict]:
    """Reranker Agent: dedupe by source/section, keep top by similarity."""
    if len(chunks) <= top_n:
        return chunks[:top_n]
    seen = set()
    out = []
    for c in chunks:
        key = (c.get("filename", ""), c.get("section_heading") or "")
        if key in seen:
            continue
        seen.add(key)
        out.append(c)
        if len(out) >= top_n:
            break
    return out if out else chunks[:top_n]


# --- Critic Refiner (optional) ---
def critic_refine(draft: str, model, tokenizer) -> str:
    """Critic Refiner Agent: improve clarity and flow, preserve meaning."""
    if not draft or len(draft.strip()) < 20:
        return draft
    system_refine = (
        "You are an editor. Improve clarity and conversational flow of the following text. "
        "Preserve all meaning and facts. Do not add new information. Output only the refined text, nothing else."
    )
    messages = [
        {"role": "system", "content": system_refine},
        {"role": "user", "content": draft[:1500]},
    ]
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    enc = tokenizer(text, return_tensors="pt", truncation=True, max_length=2048).to(model.device)
    with torch.no_grad():
        gen = model.generate(**enc, max_new_tokens=400, temperature=0.2, do_sample=True)
    prompt_len = enc["input_ids"].shape[1]
    out = tokenizer.decode(gen[0][prompt_len:], skip_special_tokens=True)
    return extract_assistant_response(out).strip() or draft


def clean_response_text(text: str, max_bullets: int = 10) -> str:
    """Remove duplicate lines and cap number of bullet points."""
    lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    seen = set()
    cleaned = []
    bullet_count = 0

    for line in lines:
        key = line.strip().lower()
        if key in seen:
            continue
        seen.add(key)

        if line.lstrip().startswith(("-", "*")):
            if bullet_count >= max_bullets:
                continue
            bullet_count += 1

        cleaned.append(line)

    return "\n".join(cleaned)


# Generator Agent master prompt (conversational, grounded)
GENERATOR_SYSTEM = (
    "You are a regulatory AI assistant. Explain KSA/SAMA regulations clearly and naturally, "
    "like an expert explaining to a colleague. Use ONLY the provided context for facts; never invent or assume.\n\n"
    "Rules:\n"
    "- Explain in your own words; do not dump regulation text or sound like a law book.\n"
    "- Start with a direct, human answer (1–3 sentences) before any list.\n"
    "- Use short paragraphs or 3–5 bullets only when listing obligations or steps.\n"
    "- Be calm, professional, and conversational. Never mention document names, page numbers, or chunk IDs.\n"
    "- Do not copy glossary definitions verbatim. Do not repeat the same phrase.\n"
    "Bad: 'Risk management is the process of identifying, assessing, prioritizing...' (dictionary style).\n"
    "Good: 'Under KSA rules, the board must ensure cyber risks are identified and reviewed regularly, "
    "and that policies and resources are in place to manage them.'\n"
)

def generate_response(query: str, chunks: List[Dict], plan: Any = None) -> str:
    """Generator Agent: produce conversational answer from retrieved chunks only."""
    model, tokenizer = load_model()
    plan = plan or planner_plan(query)
    intent = plan.get("query_intent", "general")
    answer_style = plan.get("answer_style", "conversational")
    lang = plan.get("response_language", "en")

    used_chunks = chunks
    if intent == "explanation":
        non_glossary = [c for c in chunks if not is_glossary_section(c.get("section_heading"))]
        if non_glossary:
            used_chunks = non_glossary

    context = "\n\n".join(
        f"[{i+1}] {strip_chunk_metadata(chunk['text'])[:1000]}"
        for i, chunk in enumerate(used_chunks)
    )

    lang_rule = "Respond in English only." if lang == "en" else "Respond in Arabic only."
    style_rule = (
        "Start with a direct explanation in 1–3 sentences, then add 3–5 bullets only if listing obligations or steps."
        if answer_style == "conversational"
        else "Give a concise answer; use bullets only when listing specific items."
    )

    system_content = GENERATOR_SYSTEM + "\n" + lang_rule + "\n" + style_rule + "\n"

    messages = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": f"Question: {query}\n\nContext:\n{context}"},
    ]
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    enc = tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        padding=True,
        max_length=2048,
    ).to(model.device)
    with torch.no_grad():
        gen = model.generate(**enc, max_new_tokens=384, temperature=0.3, do_sample=False)
    prompt_len = enc["input_ids"].shape[1]
    output = tokenizer.decode(gen[0][prompt_len:], skip_special_tokens=True)
    raw_text = extract_assistant_response(output)
    return clean_response_text(raw_text)


class ChatRequest(BaseModel):
    message: str


async def stream_response(response_text: str, references: List[Dict]):
    CHUNK_SIZE = 80
    for i in range(0, len(response_text), CHUNK_SIZE):
        chunk_text = response_text[i : i + CHUNK_SIZE]
        data = json.dumps({"type": "token", "content": chunk_text})
        yield f"data: {data}\n\n"
    final_data = json.dumps({"type": "done", "references": references})
    yield f"data: {final_data}\n\n"


# Orchestrator: planner → retrieval → reranker → generator → (optional) critic
def run_agent_pipeline(query: str) -> tuple[str, List[Dict]]:
    plan = planner_plan(query)
    query_embedding = generate_query_embedding(query)
    chunks = search_chunks(query_embedding, top_k=plan["top_k"])
    chunks = rerank_chunks(chunks, top_n=5)
    references = []
    for chunk in chunks:
        clean_text = strip_chunk_metadata(chunk["text"])
        snippet = clean_text[:600] + "..." if len(clean_text) > 600 else clean_text
        references.append({
            "id": chunk["id"],
            "source": chunk["filename"],
            "page": chunk.get("chunk_index", 0),
            "snippet": snippet,
        })
    draft = generate_response(query, chunks, plan)
    if plan.get("use_refiner") and draft:
        try:
            model, tokenizer = load_model()
            draft = critic_refine(draft, model, tokenizer)
        except Exception:
            pass
    return draft, references


@app.post("/api/chat")
async def chat(request: ChatRequest):
    query = request.message
    response_text, references = run_agent_pipeline(query)
    return StreamingResponse(
        stream_response(response_text, references),
        media_type="text/event-stream",
    )


@app.get("/health")
def health():
    return {"status": "ok"}
