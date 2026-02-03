import os
import json
from typing import List, Dict
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv
import psycopg2
from openai import AzureOpenAI
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, TextIteratorStreamer, BitsAndBytesConfig
from peft import PeftModel
import asyncio
import threading
from queue import Queue
from cache import get_cached_response, set_cached_response

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
DISABLE_SEMANTIC_CACHE = os.environ.get("DISABLE_SEMANTIC_CACHE", "0") == "1"
CACHE_SIMILARITY_THRESHOLD = float(os.environ.get("CACHE_SIMILARITY_THRESHOLD", "0.95"))

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
        quantization_config = None
        if torch.cuda.is_available():
            try:
                quantization_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_quant_type="nf4",
                )
            except Exception:
                quantization_config = None
        kwargs = {"device_map": "auto"}
        if quantization_config:
            kwargs["quantization_config"] = quantization_config
        else:
            kwargs["torch_dtype"] = torch.float16
        base_model = AutoModelForCausalLM.from_pretrained(MODEL_NAME, **kwargs)
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


def generate_response(query: str, chunks: List[Dict]) -> str:
    model, tokenizer = load_model()

    lower_query = query.lower()
    is_list_query = any(
        lower_query.startswith(prefix)
        for prefix in ["what are", "list", "which are", "what are the"]
    )

    is_explain = is_explanation_query(query)

    extra_instruction = ""
    if is_list_query:
        extra_instruction += (
            "- If the question asks to 'list' items, respond with a concise bullet "
            "list of names with at most one short phrase of explanation each.\n"
        )

    if is_explain:
        extra_instruction += (
            "- If the user asks you to explain or give an overview, write in your own words "
            "instead of copying glossary-style definitions.\n"
            "- Start with 1–2 short sentences that summarize the main idea.\n"
            "- Then provide 3–5 bullets focusing on concrete obligations, actions, or takeaways.\n"
            "- Avoid dictionary-style phrasing like 'X is the process of identifying, assessing...'.\n"
        )

    used_chunks = chunks
    if is_explain:
        non_glossary_chunks = [
            c for c in chunks if not is_glossary_section(c.get("section_heading"))
        ]
        if non_glossary_chunks:
            used_chunks = non_glossary_chunks

    context = "\n\n".join(
        f"[{i+1}] {strip_chunk_metadata(chunk['text'])[:1000]}"
        for i, chunk in enumerate(used_chunks)
    )

    system_content = (
        "You are a helpful assistant for KSA regulatory compliance.\n\n"
        + extra_instruction
        + "- Always answer in clear English.\n"
        + "- Respond with 5-10 bullet points.\n"
        + "- Each bullet should be 1–2 short sentences.\n"
        + "- Focus only on the main regulatory requirements or rules relevant to the question.\n"
        + "- Do NOT copy long passages or glossary definitions verbatim from the context.\n"
        + "- Do NOT repeat the same sentence or phrase.\n"
        + "- Do NOT mention document IDs, page numbers, or chunk indices.\n"
        + "\n"
        + "Bad example (to avoid):\n"
        + "- Risk management is the process of identifying, assessing, prioritizing, and taking action to accept, "
          "transfer, mitigate, or eliminate risks. (repeated or copied from glossary)\n"
        + "Good example (preferred style):\n"
        + "- Cyber risk laws require the board and senior management to ensure that cyber risks are identified, "
          "assessed, and regularly reviewed.\n"
        + "- They must approve and oversee cyber security policies, allocate sufficient resources, and monitor key "
          "cyber risk indicators.\n"
    )

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
        gen = model.generate(
            **enc,
            max_new_tokens=384,
            temperature=0.3,
            do_sample=False,
        )
    
    # Decode only newly generated tokens (avoid echoing prompt/system text)
    prompt_len = enc["input_ids"].shape[1]
    generated_ids = gen[0][prompt_len:]
    output = tokenizer.decode(generated_ids, skip_special_tokens=True)
    raw_text = extract_assistant_response(output)
    return clean_response_text(raw_text)


def _build_prompt_enc(query: str, chunks: List[Dict], model, tokenizer):
    """Build prompt and encoding like generate_response. Returns (enc, input_tokens)."""
    lower_query = query.lower()
    is_list_query = any(lower_query.startswith(p) for p in ["what are", "list", "which are", "what are the"])
    is_explain = is_explanation_query(query)
    extra_instruction = ""
    if is_list_query:
        extra_instruction += "- If the question asks to 'list' items, respond with a concise bullet list of names with at most one short phrase of explanation each.\n"
    if is_explain:
        extra_instruction += "- If the user asks you to explain or give an overview, write in your own words instead of copying glossary-style definitions.\n- Start with 1–2 short sentences that summarize the main idea.\n- Then provide 3–5 bullets focusing on concrete obligations, actions, or takeaways.\n- Avoid dictionary-style phrasing like 'X is the process of identifying, assessing...'.\n"
    used_chunks = chunks
    if is_explain:
        non_glossary = [c for c in chunks if not is_glossary_section(c.get("section_heading"))]
        if non_glossary:
            used_chunks = non_glossary
    context = "\n\n".join(f"[{i+1}] {strip_chunk_metadata(c['text'])[:1000]}" for i, c in enumerate(used_chunks))
    system_content = (
        "You are a helpful assistant for KSA regulatory compliance.\n\n" + extra_instruction
        + "- Always answer in clear English.\n- Respond with 5-10 bullet points.\n- Each bullet should be 1–2 short sentences.\n"
        + "- Focus only on the main regulatory requirements or rules relevant to the question.\n"
        + "- Do NOT copy long passages or glossary definitions verbatim from the context.\n"
        + "- Do NOT repeat the same sentence or phrase.\n- Do NOT mention document IDs, page numbers, or chunk indices.\n"
    )
    messages = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": f"Question: {query}\n\nContext:\n{context}"},
    ]
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    enc = tokenizer(text, return_tensors="pt", truncation=True, padding=True, max_length=2048).to(model.device)
    return enc, enc["input_ids"].shape[1]


async def stream_generate_response(query: str, chunks: List[Dict], references: List[Dict]):
    """Stream tokens via thread + queue so event loop is not blocked."""
    model, tokenizer = load_model()
    enc, input_tokens = _build_prompt_enc(query, chunks, model, tokenizer)
    streamer = TextIteratorStreamer(tokenizer, skip_special_tokens=True)
    token_queue = Queue()

    def run_generate():
        with torch.no_grad():
            model.generate(**enc, max_new_tokens=384, temperature=0.3, do_sample=False, streamer=streamer)

    def run_consume():
        for t in streamer:
            token_queue.put(t)
        token_queue.put(None)

    t1 = threading.Thread(target=run_generate)
    t2 = threading.Thread(target=run_consume)
    t1.start()
    t2.start()

    output_tokens = 0
    while True:
        token = await asyncio.to_thread(token_queue.get)
        if token is None:
            break
        output_tokens += 1
        yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"

    t1.join()
    t2.join()

    yield f"data: {json.dumps({'type': 'done', 'references': references, 'input_tokens': input_tokens, 'output_tokens': output_tokens})}\n\n"


class ChatRequest(BaseModel):
    message: str


async def stream_response(query: str, chunks: List[Dict], references: List[Dict], query_embedding: List[float] = None, cached_result=None):
    if cached_result:
        response_text, cached_refs = cached_result
        CHUNK_SIZE = 80
        for i in range(0, len(response_text), CHUNK_SIZE):
            yield f"data: {json.dumps({'type': 'token', 'content': response_text[i:i+CHUNK_SIZE]})}\n\n"
        yield f"data: {json.dumps({'type': 'done', 'references': cached_refs, 'input_tokens': 0, 'output_tokens': 0})}\n\n"
        return

    full_response_text = ""
    async for chunk in stream_generate_response(query, chunks, references):
        if chunk.startswith("data: "):
            try:
                s = chunk[6:].strip()
                if s:
                    data = json.loads(s)
                    if data.get("type") == "token":
                        full_response_text += data.get("content", "")
            except Exception:
                pass
        yield chunk

    if not DISABLE_SEMANTIC_CACHE and query_embedding and full_response_text:
        cleaned = clean_response_text(extract_assistant_response(full_response_text))
        set_cached_response(query_embedding, cleaned, references)


@app.post("/api/chat")
async def chat(request: ChatRequest):
    query = request.message
    query_embedding = generate_query_embedding(query)

    if not DISABLE_SEMANTIC_CACHE:
        cache_task = asyncio.to_thread(get_cached_response, query_embedding, CACHE_SIMILARITY_THRESHOLD)
        retrieval_task = asyncio.to_thread(search_chunks, query_embedding, 5)
        cached_result, chunks = await asyncio.gather(cache_task, retrieval_task)
    else:
        cached_result = None
        chunks = await asyncio.to_thread(search_chunks, query_embedding, 5)

    references: List[Dict] = []
    for chunk in chunks:
        clean_text = strip_chunk_metadata(chunk["text"])
        snippet = clean_text[:600] + "..." if len(clean_text) > 600 else clean_text
        references.append(
            {
                "id": chunk["id"],
                "source": chunk["filename"],
                "page": chunk.get("chunk_index", 0),
                "snippet": snippet,
            }
        )

    return StreamingResponse(
        stream_response(query, chunks, references, query_embedding, cached_result),
        media_type="text/event-stream"
    )


@app.get("/health")
def health():
    return {"status": "ok"}
