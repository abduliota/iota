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


def generate_response(query: str, chunks: List[Dict]) -> str:
    model, tokenizer = load_model()

    lower_query = query.lower()
    is_list_query = any(
        lower_query.startswith(prefix)
        for prefix in ["what are", "list", "which are", "what are the"]
    )

    extra_instruction = ""
    if is_list_query:
        extra_instruction = (
            "- If the question asks to 'list' items, respond with a concise bullet "
            "list of names with at most one short phrase of explanation each.\n"
        )

    context = "\n\n".join(
        f"[{i+1}] {strip_chunk_metadata(chunk['text'])[:1000]}"
        for i, chunk in enumerate(chunks)
    )

    system_content = (
        "You are a helpful assistant for KSA regulatory compliance.\n\n"
        + extra_instruction
        + "- Always answer in clear English.\n"
        + "- Respond in at most 5 short bullet points.\n"
        + "- Each bullet should be 1–2 short sentences.\n"
        + "- Focus only on the main regulatory requirements or rules relevant to the question.\n"
        + "- Do NOT copy long passages or glossary definitions verbatim from the context.\n"
        + "- Do NOT repeat the same sentence or phrase.\n"
        + "- Do NOT mention document IDs, page numbers, or chunk indices.\n"
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
            max_new_tokens=256,
            temperature=0.3,
            do_sample=False,
        )
    
    # Decode only newly generated tokens (avoid echoing prompt/system text)
    prompt_len = enc["input_ids"].shape[1]
    generated_ids = gen[0][prompt_len:]
    output = tokenizer.decode(generated_ids, skip_special_tokens=True)
    return extract_assistant_response(output)


class ChatRequest(BaseModel):
    message: str


async def stream_response(query: str, chunks: List[Dict], references: List[Dict]):
    response_text = generate_response(query, chunks)
    
    words = response_text.split()
    buffer: List[str] = []
    CHUNK_SIZE = 8  # number of words per streamed chunk

    for word in words:
        buffer.append(word)
        if len(buffer) >= CHUNK_SIZE:
            chunk_text = " ".join(buffer)
            data = json.dumps({"type": "token", "content": chunk_text})
            yield f"data: {data}\n\n"
            buffer = []

    if buffer:
        chunk_text = " ".join(buffer)
        data = json.dumps({"type": "token", "content": chunk_text})
        yield f"data: {data}\n\n"
    
    final_data = json.dumps({
        "type": "done",
        "references": references
    })
    yield f"data: {final_data}\n\n"


@app.post("/api/chat")
async def chat(request: ChatRequest):
    query = request.message
    
    query_embedding = generate_query_embedding(query)
    chunks = search_chunks(query_embedding, top_k=5)
    
    references: List[Dict] = []
    for chunk in chunks:
        clean_text = strip_chunk_metadata(chunk["text"])
        snippet = clean_text[:200] + "..." if len(clean_text) > 200 else clean_text
        references.append(
            {
                "id": chunk["id"],
                "source": chunk["filename"],
                "page": chunk.get("chunk_index", 0),
                "snippet": snippet,
            }
        )
    
    return StreamingResponse(
        stream_response(query, chunks, references),
        media_type="text/event-stream"
    )


@app.get("/health")
def health():
    return {"status": "ok"}
