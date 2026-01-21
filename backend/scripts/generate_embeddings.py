import os
import json
import asyncio
import time
from openai import AzureOpenAI
from dotenv import load_dotenv
import psycopg2

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
CHUNKS_FILE = os.path.join(BASE_DIR, "downloads", "chunks.jsonl")

AZURE_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT")
AZURE_API_KEY = os.environ.get("AZURE_OPENAI_API_KEY")
AZURE_DEPLOYMENT = os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME", "text-embedding-3-large")

RPM_LIMIT = 6
TPM_LIMIT = 1000
DELAY_SECONDS = 11
BATCH_SIZE = 1

PGHOST = os.environ.get("PGHOST")
PGUSER = os.environ.get("PGUSER")
PGPASSWORD = os.environ.get("PGPASSWORD")
PGDATABASE = os.environ.get("PGDATABASE", "postgres")
PGPORT = os.environ.get("PGPORT", "5432")


def get_db_connection():
    """Get PostgreSQL connection."""
    return psycopg2.connect(
        host=PGHOST,
        port=PGPORT,
        dbname=PGDATABASE,
        user=PGUSER,
        password=PGPASSWORD,
        sslmode="require",
    )


def load_chunks():
    """Load chunks from JSONL file."""
    chunks = []
    if not os.path.exists(CHUNKS_FILE):
        print(f"Error: {CHUNKS_FILE} not found. Run chunk_text.py first.")
        return chunks
    
    with open(CHUNKS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                chunks.append(json.loads(line))
    
    return chunks


def get_pending_chunks():
    """Get chunks that need embedding (not in DB or status=pending)."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT d.filename, c.chunk_index
        FROM chunks c
        JOIN documents d ON c.document_id = d.id
        WHERE c.status = 'pending' OR c.status IS NULL OR c.embedding IS NULL
    """)
    
    pending = set()
    for row in cur.fetchall():
        filename_base = os.path.splitext(row[0])[0]
        pending.add((filename_base, row[1]))
    
    cur.close()
    conn.close()
    
    return pending


def generate_embedding(client, text):
    """Generate embedding for single text."""
    try:
        response = client.embeddings.create(
            model=AZURE_DEPLOYMENT,
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"  ✗ Embedding error: {e}")
        return None


async def process_chunks_batch(chunks_batch, client):
    """Process a batch of chunks (1-2 chunks to respect rate limits)."""
    embeddings = []
    for chunk in chunks_batch:
        embedding = await asyncio.to_thread(generate_embedding, client, chunk["text"])
        if embedding:
            embeddings.append({
                "filename": chunk["filename"],
                "chunk_index": chunk["chunk_index"],
                "embedding": embedding,
            })
        await asyncio.sleep(DELAY_SECONDS)
    return embeddings


def update_db_embeddings(embeddings):
    """Update database with embeddings."""
    if not embeddings:
        return
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    for emb in embeddings:
        embedding_list = emb["embedding"]
        chunk_filename_base = os.path.splitext(emb["filename"])[0]

        cur.execute(
            """
            UPDATE chunks c
            SET embedding = %s::vector(3072),
                status = 'embedded'
            FROM documents d
            WHERE c.document_id = d.id
              AND regexp_replace(d.filename, '\.[^.]+$', '') = %s
              AND c.chunk_index = %s
              AND (c.embedding IS NULL OR c.status IS NULL OR c.status = 'pending')
            """,
            (str(embedding_list), chunk_filename_base, emb["chunk_index"]),
        )
    
    conn.commit()
    cur.close()
    conn.close()


async def main():
    """Main embedding generation loop."""
    print("Loading chunks...")
    all_chunks = load_chunks()
    print(f"Loaded {len(all_chunks)} chunks from {CHUNKS_FILE}\n")
    
    if not all_chunks:
        print("No chunks to process.")
        return
    
    pending = get_pending_chunks()
    
    if not pending:
        print("No pending chunks found in database. Run upload_to_db.py first.")
        return
    
    chunks_to_process = []
    for chunk in all_chunks:
        chunk_base = os.path.splitext(chunk["filename"])[0]
        for pdf_filename, chunk_idx in pending:
            pdf_base = os.path.splitext(pdf_filename)[0]
            if chunk_base == pdf_base and chunk["chunk_index"] == chunk_idx:
                chunks_to_process.append(chunk)
                break
    
    if not chunks_to_process:
        print("No matching chunks found. Make sure chunks.jsonl matches uploaded chunks.")
        return
    
    print(f"Processing {len(chunks_to_process)} chunks...\n")
    
    client = AzureOpenAI(
        api_key=AZURE_API_KEY,
        api_version="2024-02-15-preview",
        azure_endpoint=AZURE_ENDPOINT,
    )
    
    processed = 0
    for i in range(0, len(chunks_to_process), BATCH_SIZE):
        batch = chunks_to_process[i:i + BATCH_SIZE]
        print(f"[{i+1}/{len(chunks_to_process)}] Processing batch...")
        
        embeddings = await process_chunks_batch(batch, client)
        if embeddings:
            update_db_embeddings(embeddings)
            processed += len(embeddings)
            print(f"  ✓ Embedded {len(embeddings)} chunks (total: {processed})")
        
        if i + BATCH_SIZE < len(chunks_to_process):
            await asyncio.sleep(DELAY_SECONDS)
    
    print(f"\n✓ Complete! Processed {processed} chunks.")


if __name__ == "__main__":
    asyncio.run(main())
