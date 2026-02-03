import os
import re
import json
from typing import List, Dict, Any, Optional
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

# Config
RELEVANCE_THRESHOLD = float(os.environ.get("RELEVANCE_THRESHOLD", "0.5"))
GREETING_PATTERNS = [
    "hi", "hello", "hey", "thanks", "thank you", "ok", "okay", "bye", "goodbye",
    "مرحبا", "السلام عليكم", "شكرا", "مع السلامة",
]
ACRONYM_REWRITES = {
    "sama": "What is the Saudi Arabian Monetary Authority and what does it regulate?",
    "cma": "What is the Capital Market Authority in Saudi Arabia?",
    "ksa": "What are KSA financial regulations?",
}
FOLLOW_UP_PATTERNS = [
    "explain more", "tell me more", "go on", "continue", "what about that", "elaborate", "and?", "more detail",
]


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


def detect_language(text: str) -> str:
    """Detect language from query: Arabic script -> 'ar', else 'en'."""
    if not text or not text.strip():
        return "en"
    arabic_pattern = re.compile(r"[\u0600-\u06FF]")
    if arabic_pattern.search(text):
        return "ar"
    return "en"


def search_chunks(
    query_embedding: List[float],
    top_k: int = 5,
    filters: Optional[Dict[str, str]] = None,
) -> List[Dict]:
    conn = get_db_connection()
    cur = conn.cursor()
    embedding_str = str(query_embedding)
    filters = filters or {}

    where_parts = ["c.embedding IS NOT NULL"]
    params: List[Any] = []

    use_regulator = bool(filters.get("regulator"))
    if filters.get("language"):
        where_parts.append("c.language = %s")
    if use_regulator:
        where_parts.append("d.regulator = %s")

    where_sql = " AND ".join(where_parts)

    # Params order must match SQL: SELECT embedding, WHERE filters..., ORDER BY embedding, LIMIT
    params.append(embedding_str)
    if filters.get("language"):
        params.append(filters["language"])
    if use_regulator:
        params.append(filters["regulator"])
    params.append(embedding_str)
    params.append(top_k)

    sql = f"""
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
        WHERE {where_sql}
        ORDER BY c.embedding <=> %s::vector
        LIMIT %s
    """
    try:
        cur.execute(sql, params)
    except psycopg2.ProgrammingError as e:
        if "regulator" in str(e) and "does not exist" in str(e).lower():
            filters_no_reg = {k: v for k, v in filters.items() if k != "regulator"}
            cur.close()
            conn.close()
            return search_chunks(query_embedding, top_k, filters_no_reg)
        raise

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
def planner_plan(
    user_query: str,
    conversation_state: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Planner Agent: decide intent, language, need_retrieval, answer style, retrieval size."""
    state = conversation_state or {}
    q = user_query.strip().lower()
    raw = user_query.strip()

    # Language: from state or detect
    response_language = state.get("language") or detect_language(user_query)

    # Greeting / chitchat first -> skip RAG
    need_retrieval = True
    query_intent = "general"
    for g in GREETING_PATTERNS:
        if raw.lower() == g or (len(raw.split()) <= 2 and g in q):
            need_retrieval = False
            if any(x in q for x in ["bye", "goodbye", "مع السلامة"]):
                query_intent = "goodbye"
            elif any(x in q for x in ["thanks", "thank you", "شكرا"]):
                query_intent = "acknowledgment"
            else:
                query_intent = "greeting"
            break

    if need_retrieval:
        if any(x in q for x in ["explain", "overview", "what is", "what are", "how does", "why"]):
            query_intent = "explanation"
        elif any(x in q for x in ["list", "which are", "name the", "what are the"]):
            query_intent = "list"
        elif any(x in q for x in ["how to", "steps", "procedure", "process"]):
            query_intent = "procedural"

    answer_style = "conversational" if query_intent == "explanation" else "structured"
    top_k = 8 if query_intent == "explanation" else 5
    use_refiner = False

    # Updated state fields for response
    updated_state = {
        "language": response_language,
        "last_intent": query_intent,
        "last_query": raw if need_retrieval else state.get("last_query"),
        "active_topic": state.get("active_topic"),
        "active_regulator": state.get("active_regulator"),
    }
    if need_retrieval and raw:
        updated_state["last_query"] = raw
        if "sama" in q or "ساما" in user_query:
            updated_state["active_regulator"] = "SAMA"
        if "cma" in q or "cma" in user_query:
            updated_state["active_regulator"] = "CMA"
        if query_intent == "explanation" or query_intent == "list":
            updated_state["active_topic"] = raw[:80] if len(raw) > 10 else (state.get("active_topic") or raw[:80])

    return {
        "response_language": response_language,
        "query_intent": query_intent,
        "need_retrieval": need_retrieval,
        "answer_style": answer_style,
        "top_k": top_k,
        "use_refiner": use_refiner,
        "updated_state": updated_state,
    }


def rewrite_query(
    query: str,
    plan: Dict[str, Any],
    conversation_state: Optional[Dict[str, Any]] = None,
) -> str:
    """Rewrite user query into explicit regulatory search query."""
    state = conversation_state or {}
    q = query.strip().lower()

    # Follow-up patterns: use state context
    for pat in FOLLOW_UP_PATTERNS:
        if pat in q or (len(q.split()) <= 3 and q in ["more", "detail", "and"]):
            if state.get("active_topic"):
                return f"{state['active_topic']} - detailed explanation"
            if state.get("last_query"):
                return state["last_query"]
            break

    # Acronym / abbreviation rewrites
    for acronym, rewritten in ACRONYM_REWRITES.items():
        if acronym in q and ("what" in q or "explain" in q or "define" in q or "mean" in q):
            return rewritten

    # Vague query + state context
    if state.get("active_regulator") and len(q.split()) <= 4:
        return f"{state['active_regulator']}: {query.strip()}"
    if state.get("active_topic") and q in ["requirements", "rules", "what"]:
        return f"{state['active_topic']} {query.strip()}"

    return query.strip()


def generate_clarification_message(query: str, state: Dict[str, Any]) -> str:
    """Return a clarification prompt when retrieval is low relevance."""
    if state.get("active_topic"):
        return (
            f"I couldn't find specific information about that. "
            f"Are you asking about {state['active_topic']}, or something else? Could you rephrase your question?"
        )
    return (
        "I couldn't find relevant information for your query. "
        "Could you please rephrase or provide more details? I can help with SAMA, CMA, and other KSA regulatory questions."
    )


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

def generate_response(
    query: str,
    chunks: List[Dict],
    plan: Any = None,
    conversation_state: Optional[Dict[str, Any]] = None,
) -> str:
    """Generator Agent: produce conversational answer from retrieved chunks only."""
    model, tokenizer = load_model()
    plan = plan or planner_plan(query, conversation_state)
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


class ConversationStateModel(BaseModel):
    active_topic: Optional[str] = None
    active_regulator: Optional[str] = None
    active_domain: Optional[str] = None
    language: Optional[str] = None
    last_intent: Optional[str] = None
    last_query: Optional[str] = None


class ChatRequest(BaseModel):
    message: str
    conversation_state: Optional[ConversationStateModel] = None


def _state_to_dict(s: Optional[ConversationStateModel]) -> Dict[str, Any]:
    if s is None:
        return {}
    return {k: v for k, v in s.model_dump().items() if v is not None}


async def stream_response(
    response_text: str,
    references: List[Dict],
    conversation_state: Optional[Dict[str, Any]] = None,
):
    CHUNK_SIZE = 80
    for i in range(0, len(response_text), CHUNK_SIZE):
        chunk_text = response_text[i : i + CHUNK_SIZE]
        data = json.dumps({"type": "token", "content": chunk_text})
        yield f"data: {data}\n\n"
    final_data = json.dumps({
        "type": "done",
        "references": references,
        "conversation_state": conversation_state or {},
    })
    yield f"data: {final_data}\n\n"


# Orchestrator: planner → (optional retrieval) → reranker → generator → (optional) critic
def run_agent_pipeline(
    query: str,
    conversation_state: Optional[Dict[str, Any]] = None,
) -> tuple[str, List[Dict], Dict[str, Any]]:
    state = conversation_state or {}
    plan = planner_plan(query, state)

    if not plan.get("need_retrieval", True):
        if plan.get("query_intent") == "goodbye":
            response_text = "Goodbye! Feel free to return if you have more questions."
        elif plan.get("query_intent") == "acknowledgment":
            response_text = "You're welcome! Let me know if you need anything else."
        else:
            response_text = (
                "Hello! I'm here to help with SAMA and KSA regulatory questions. How can I assist you?"
            )
        updated_state = plan.get("updated_state") or state
        return response_text, [], updated_state

    # Build filters from state / plan
    filters: Dict[str, str] = {}
    lang = state.get("language") or plan.get("response_language") or detect_language(query)
    filters["language"] = lang
    if state.get("active_regulator"):
        filters["regulator"] = state["active_regulator"]
    elif "sama" in query.lower():
        filters["regulator"] = "SAMA"
    elif "cma" in query.lower():
        filters["regulator"] = "CMA"

    search_query = rewrite_query(query, plan, state)
    query_embedding = generate_query_embedding(search_query)
    chunks = search_chunks(query_embedding, top_k=plan["top_k"], filters=filters)
    chunks = rerank_chunks(chunks, top_n=5)

    if not chunks:
        response_text = generate_clarification_message(query, state)
        updated_state = plan.get("updated_state") or state
        return response_text, [], updated_state

    max_similarity = max(c.get("similarity", 0) for c in chunks)
    if max_similarity < RELEVANCE_THRESHOLD:
        response_text = generate_clarification_message(query, state)
        updated_state = plan.get("updated_state") or state
        return response_text, [], updated_state

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

    draft = generate_response(query, chunks, plan, state)
    if plan.get("use_refiner") and draft:
        try:
            model, tokenizer = load_model()
            draft = critic_refine(draft, model, tokenizer)
        except Exception:
            pass

    updated_state = plan.get("updated_state") or state
    return draft, references, updated_state


@app.post("/api/chat")
async def chat(request: ChatRequest):
    query = request.message
    state = _state_to_dict(request.conversation_state)
    response_text, references, updated_state = run_agent_pipeline(query, state)
    return StreamingResponse(
        stream_response(response_text, references, updated_state),
        media_type="text/event-stream",
    )


@app.get("/health")
def health():
    return {"status": "ok"}
