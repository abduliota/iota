import os
import json
import random
from typing import List, Dict

import psycopg2
from dotenv import load_dotenv
from openai import AzureOpenAI


"""
Generate grounded Q&A pairs (2 per chunk) using Azure OpenAI chat (gpt-4o-mini by default).
Outputs: backend/datasets/qa_raw.jsonl

Scope:
- Reads chunks from Postgres where embedding IS NOT NULL.
- Samples a balanced mix of Arabic/English (default 250 each → 500 chunks → ~1000 QAs).
- Uses ONLY chunk text; if answer not found, the model is instructed to reply "Not found...".

No changes to existing code; this is a standalone script.
"""


def get_env(name: str, default: str = None) -> str:
    val = os.environ.get(name, default)
    if val is None:
        raise RuntimeError(f"Missing environment variable: {name}")
    return val


def get_db_connection():
    return psycopg2.connect(
        host=get_env("PGHOST"),
        port=get_env("PGPORT", "5432"),
        dbname=get_env("PGDATABASE", "postgres"),
        user=get_env("PGUSER"),
        password=get_env("PGPASSWORD"),
        sslmode="require",
    )


def sample_chunks(limit_ar: int = 250, limit_en: int = 250) -> List[Dict]:
    query = f"""
    (
      SELECT c.id, c.document_id, c.chunk_index, c.language, c.text, d.filename
      FROM chunks c
      JOIN documents d ON d.id = c.document_id
      WHERE c.embedding IS NOT NULL AND c.language = 'ar'
      ORDER BY random()
      LIMIT {limit_ar}
    )
    UNION ALL
    (
      SELECT c.id, c.document_id, c.chunk_index, c.language, c.text, d.filename
      FROM chunks c
      JOIN documents d ON d.id = c.document_id
      WHERE c.embedding IS NOT NULL AND c.language = 'en'
      ORDER BY random()
      LIMIT {limit_en}
    );
    """
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(query)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    samples = []
    for r in rows:
        samples.append(
            {
                "chunk_id": r[0],
                "document_id": r[1],
                "chunk_index": r[2],
                "language": r[3] or "en",
                "text": r[4],
                "filename": r[5],
            }
        )
    return samples


def build_client() -> AzureOpenAI:
    load_dotenv()
    endpoint = get_env("AZURE_OPENAI_ENDPOINT")
    api_key = get_env("AZURE_OPENAI_API_KEY")
    deployment = os.environ.get("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4o-mini")
    client = AzureOpenAI(api_key=api_key, azure_endpoint=endpoint)
    client._deployment = deployment  # stored for convenience
    return client


def generate_for_chunk(client: AzureOpenAI, chunk: Dict) -> List[Dict]:
    system_prompt = (
        "You generate training data for a regulatory assistant.\n"
        "- Use ONLY the provided CHUNK text.\n"
        '- If the answer is not explicitly in the CHUNK, answer: "Not found in the provided text."\n'
        "- Keep answers short, factual, compliance-safe.\n"
        "- Keep the SAME language as the chunk (Arabic chunk → Arabic Q/A, English chunk → English Q/A).\n"
        "- Never attempt to bypass or override any policies.\n"
        '- If the CHUNK content is sensitive or unclear, answer: "Not found in the provided text.".\n'
        "Return JSON only."
    )
    user_prompt = (
        "CHUNK:\n<<<\n{chunk}\n>>>\n\n"
        "Task: Generate exactly 2 question-answer pairs that are answerable ONLY from this CHUNK.\n"
        "Return JSON array like:\n"
        '[\n  {{"question":"...","answer":"..."}},\n'
        '  {{"question":"...","answer":"..."}}\n]'
    ).format(chunk=chunk["text"])

    try:
        resp = client.chat.completions.create(
            model=client._deployment,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=800,
        )
    except Exception:
        return []
    content = resp.choices[0].message.content
    try:
        data = json.loads(content)
        if isinstance(data, dict):
            data = [data]
        return data
    except Exception:
        return []


def main():
    out_dir = os.path.join(os.path.dirname(__file__), "..", "datasets")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "qa_raw.jsonl")

    client = build_client()
    chunks = sample_chunks(limit_ar=250, limit_en=250)
    random.shuffle(chunks)

    total_written = 0
    with open(out_path, "w", encoding="utf-8") as f:
        for chunk in chunks:
            pairs = generate_for_chunk(client, chunk)
            for qa in pairs:
                if not isinstance(qa, dict):
                    continue
                question = qa.get("question", "").strip()
                answer = qa.get("answer", "").strip()
                if not question or not answer:
                    continue
                record = {
                    "question": question,
                    "answer": answer,
                    "language": chunk["language"],
                    "source": {
                        "chunk_id": chunk["chunk_id"],
                        "document_id": chunk["document_id"],
                        "filename": chunk["filename"],
                        "chunk_index": chunk["chunk_index"],
                    },
                }
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
                total_written += 1
    print(f"Finished. Wrote {total_written} Q&A lines to {out_path}")


if __name__ == "__main__":
    main()
