import os
import csv
import json
import psycopg2
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
METADATA_CSV = os.path.join(BASE_DIR, "downloads", "documents_metadata.csv")
CHUNKS_FILE = os.path.join(BASE_DIR, "downloads", "chunks.jsonl")

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


def load_metadata():
    """Load document metadata from CSV."""
    metadata = []
    if not os.path.exists(METADATA_CSV):
        print(f"Warning: {METADATA_CSV} not found.")
        return metadata
    
    with open(METADATA_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            metadata.append(row)
    
    return metadata


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


def insert_documents(metadata):
    """Insert documents into database, return filename -> document_id mapping."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    filename_to_id = {}
    
    for row in metadata:
        filename = row.get("filename", "")
        if not filename:
            continue
        
        cur.execute("""
            INSERT INTO documents (source_url, pdf_url, filename, page_title)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT DO NOTHING
            RETURNING id
        """, (
            row.get("source_url"),
            row.get("pdf_url"),
            filename,
            row.get("page_title"),
        ))
        
        result = cur.fetchone()
        if result:
            doc_id = result[0]
        else:
            cur.execute("SELECT id FROM documents WHERE filename = %s", (filename,))
            doc_id = cur.fetchone()[0]
        
        filename_to_id[filename] = doc_id
    
    conn.commit()
    cur.close()
    conn.close()
    
    return filename_to_id


def insert_chunks(chunks, filename_to_id):
    """Bulk insert chunks into database."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    inserted = 0
    skipped = 0
    
    for chunk in chunks:
        chunk_filename = chunk["filename"]
        chunk_base = os.path.splitext(chunk_filename)[0]
        
        doc_id = None
        for pdf_filename, pdf_id in filename_to_id.items():
            pdf_base = os.path.splitext(pdf_filename)[0]
            if chunk_base == pdf_base:
                doc_id = pdf_id
                break
        
        if not doc_id:
            print(f"  ⚠ Skipping chunk: document not found for {chunk_filename}")
            skipped += 1
            continue
        
        cur.execute("""
            INSERT INTO chunks (
                document_id, chunk_index, text, token_count,
                section_heading, language, status
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (document_id, chunk_index) DO UPDATE
            SET text = EXCLUDED.text,
                token_count = EXCLUDED.token_count,
                section_heading = EXCLUDED.section_heading,
                language = EXCLUDED.language
        """, (
            doc_id,
            chunk["chunk_index"],
            chunk["text"],
            chunk["token_count"],
            chunk.get("section_heading"),
            chunk.get("language"),
            "pending",
        ))
        inserted += 1
    
    conn.commit()
    
    cur.execute("""
        UPDATE documents d
        SET total_chunks = (
            SELECT COUNT(*) FROM chunks c WHERE c.document_id = d.id
        )
    """)
    conn.commit()
    
    cur.close()
    conn.close()
    
    return inserted, skipped


def main():
    """Main upload process."""
    print("Loading metadata...")
    metadata = load_metadata()
    print(f"Loaded {len(metadata)} documents\n")
    
    print("Loading chunks...")
    chunks = load_chunks()
    print(f"Loaded {len(chunks)} chunks\n")
    
    if not metadata:
        print("No metadata to upload.")
        return
    
    print("Inserting documents...")
    filename_to_id = insert_documents(metadata)
    print(f"✓ Inserted/updated {len(filename_to_id)} documents\n")
    
    if not chunks:
        print("No chunks to upload.")
        return
    
    print("Inserting chunks...")
    inserted, skipped = insert_chunks(chunks, filename_to_id)
    print(f"✓ Inserted {inserted} chunks, skipped {skipped}\n")
    
    print("✓ Upload complete!")


if __name__ == "__main__":
    main()
