import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

# Database connection (same as your api_server.py)
PGHOST = os.environ.get("PGHOST")
PGUSER = os.environ.get("PGUSER")
PGPASSWORD = os.environ.get("PGPASSWORD")
PGDATABASE = os.environ.get("PGDATABASE", "postgres")
PGPORT = os.environ.get("PGPORT", "5432")

def check_vector_db(language="en", limit=20):
    """Check what data exists in vector DB for a specific language."""
    
    conn = psycopg2.connect(
        host=PGHOST,
        port=PGPORT,
        dbname=PGDATABASE,
        user=PGUSER,
        password=PGPASSWORD,
        sslmode="require",
    )
    cur = conn.cursor()
    
    print(f"\n{'='*80}")
    print(f"Checking Vector DB - Language: {language.upper()}")
    print(f"{'='*80}\n")
    
    # 1. Count total chunks by language
    cur.execute("""
        SELECT language, COUNT(*) as count
        FROM chunks
        WHERE language IS NOT NULL
        GROUP BY language
        ORDER BY count DESC
    """)
    
    print("📊 Total chunks by language:")
    for row in cur.fetchall():
        lang, count = row
        print(f"   {lang or 'NULL'}: {count:,} chunks")
    print()
    
    # 2. Show sample chunks for specified language
    cur.execute("""
        SELECT 
            c.id,
            LEFT(c.text, 200) as text_preview,
            c.section_heading,
            d.filename,
            c.chunk_index,
            c.language
        FROM chunks c
        JOIN documents d ON c.document_id = d.id
        WHERE c.language = %s
        ORDER BY d.filename, c.chunk_index
        LIMIT %s
    """, (language, limit))
    
    print(f"📄 Sample chunks (Language: {language}, Showing: {limit}):")
    print(f"{'='*80}\n")
    
    for i, row in enumerate(cur.fetchall(), 1):
        chunk_id, text_preview, section_heading, filename, chunk_index, lang = row
        
        print(f"[{i}] Chunk ID: {chunk_id}")
        print(f"    File: {filename}")
        print(f"    Section: {section_heading or '(no section)'}")
        print(f"    Chunk Index: {chunk_index}")
        print(f"    Language: {lang}")
        print(f"    Text Preview: {text_preview}...")
        print()
    
    # 3. Show unique section headings
    cur.execute("""
        SELECT DISTINCT c.section_heading, COUNT(*) as count
        FROM chunks c
        WHERE c.language = %s AND c.section_heading IS NOT NULL
        GROUP BY c.section_heading
        ORDER BY count DESC
        LIMIT 30
    """, (language,))
    
    print(f"\n📑 Section headings in {language.upper()} (top 30):")
    print(f"{'='*80}\n")
    
    for row in cur.fetchall():
        section, count = row
        print(f"   • {section}: {count} chunks")
    
    # 4. Show unique filenames
    cur.execute("""
        SELECT DISTINCT d.filename, COUNT(c.id) as chunk_count
        FROM documents d
        JOIN chunks c ON c.document_id = d.id
        WHERE c.language = %s
        GROUP BY d.filename
        ORDER BY chunk_count DESC
    """, (language,))
    
    print(f"\n📁 Documents in {language.upper()}:")
    print(f"{'='*80}\n")
    
    for row in cur.fetchall():
        filename, chunk_count = row
        print(f"   • {filename}: {chunk_count:,} chunks")
    
    cur.close()
    conn.close()
    
    print(f"\n{'='*80}")
    print("✅ Done!")
    print(f"{'='*80}\n")


def search_section_headings(keyword, language="en"):
    """Search for chunks by section heading keyword."""
    
    conn = psycopg2.connect(
        host=PGHOST,
        port=PGPORT,
        dbname=PGDATABASE,
        user=PGUSER,
        password=PGPASSWORD,
        sslmode="require",
    )
    cur = conn.cursor()
    
    print(f"\n🔍 Searching section headings for: '{keyword}'")
    print(f"{'='*80}\n")
    
    cur.execute("""
        SELECT 
            c.section_heading,
            d.filename,
            COUNT(*) as chunk_count
        FROM chunks c
        JOIN documents d ON c.document_id = d.id
        WHERE c.language = %s 
          AND c.section_heading ILIKE %s
        GROUP BY c.section_heading, d.filename
        ORDER BY chunk_count DESC
    """, (language, f"%{keyword}%"))
    
    results = cur.fetchall()
    
    if results:
        for section, filename, count in results:
            print(f"   ✓ '{section}' in {filename}: {count} chunks")
    else:
        print(f"   ✗ No sections found matching '{keyword}'")
    
    cur.close()
    conn.close()
    print()


if __name__ == "__main__":
    # Check English chunks
    check_vector_db(language="en", limit=10)
    
    # Search for specific keywords
    print("\n" + "="*80)
    print("Testing keyword searches:")
    print("="*80)
    
    search_section_headings("licensing", language="en")
    search_section_headings("guidelines", language="en")
    search_section_headings("provisions", language="en")
    search_section_headings("AML", language="en")
    search_section_headings("credit risk", language="en")
