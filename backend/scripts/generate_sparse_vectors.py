"""Phase 1: Build TF-IDF sparse vectors for all chunks and save vectorizer for API."""
import os
import json
from dotenv import load_dotenv
import psycopg2
from sklearn.feature_extraction.text import TfidfVectorizer
import joblib

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
MODELS_DIR = os.path.join(BASE_DIR, "models")
VECTORIZER_PATH = os.path.join(MODELS_DIR, "tfidf_vectorizer.pkl")

PGHOST = os.environ.get("PGHOST")
PGUSER = os.environ.get("PGUSER")
PGPASSWORD = os.environ.get("PGPASSWORD")
PGDATABASE = os.environ.get("PGDATABASE", "postgres")
PGPORT = os.environ.get("PGPORT", "5432")


def get_db_connection():
    return psycopg2.connect(
        host=PGHOST,
        port=PGPORT,
        dbname=PGDATABASE,
        user=PGUSER,
        password=PGPASSWORD,
        sslmode="require",
    )


def main():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, document_id, chunk_index, text FROM chunks ORDER BY id")
    rows = cur.fetchall()
    cur.close()
    conn.close()

    if not rows:
        print("No chunks in DB.")
        return

    ids = [r[0] for r in rows]
    texts = [r[3] for r in rows]

    vectorizer = TfidfVectorizer(max_features=50000, lowercase=True, strip_accents="unicode", sublinear_tf=True)
    vectorizer.fit(texts)

    os.makedirs(MODELS_DIR, exist_ok=True)
    joblib.dump(vectorizer, VECTORIZER_PATH)
    print(f"Saved vectorizer to {VECTORIZER_PATH}")

    batch_size = 200
    conn = get_db_connection()
    cur = conn.cursor()
    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        for r in batch:
            chunk_id, doc_id, chunk_idx, text = r
            vec = vectorizer.transform([text])
            pairs = []
            for j in vec.tocoo().col:
                pairs.append([int(j), float(vec[0, j])])
            cur.execute("UPDATE chunks SET sparse_vector = %s::jsonb WHERE id = %s", (json.dumps(pairs), chunk_id))
        conn.commit()
        print(f"Updated {min(i + batch_size, len(rows))}/{len(rows)} chunks")
    cur.close()
    conn.close()
    print("Done.")


if __name__ == "__main__":
    main()
