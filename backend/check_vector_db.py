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


SECTIONS_TO_CHECK = [
    "Banking Sector",
    "Laws and Regulations",
    "Licensing Provisions",
    "Anti Money Laundering and Combating the Financing of Terrorism",
    "Cyber Risk Control",
    "Governance and Internal Control",
    "Prudential and Supervisory Requirements",
    "Preface",
    "Minimum Capital Requirements",
    "Leverage",
    "Large Exposures",
    "Risk Management",
    "Disclosure and Reporting Requirements",
    "Macroprudential Policy",
    "Foreign Banks Branches",
    "Foreign Bank Branch Instructions",
    "SAMA Approach to Foreign Banks Branches (FBB) Regulation",
    "Corporate Governance and Risk Management",
    "Funding Ratio (FR) Requirements",
    "Liquidity Requirements",
    "Business Activities and Financial Conduct",
    "Enforcement and Financial Penalties",
    "Banking Sector Circulars",
    "Finance Sector",
    "Payment Systems and Payment Services Providers",
    "Money Exchange Sector",
    "Credit Bureaus",
    "Regulatory Sandbox",
    "SAMA Circulars"
]


def check_sections_exist(section_list, language="en"):
    """
    Check if sections exist in the database.
    
    For each section:
    1. Try exact match in section_heading
    2. Try partial match (contains keywords)
    3. Try searching in chunk text (if heading doesn't match)
    """
    
    conn = psycopg2.connect(
        host=PGHOST,
        port=PGPORT,
        dbname=PGDATABASE,
        user=PGUSER,
        password=PGPASSWORD,
        sslmode="require",
    )
    cur = conn.cursor()
    
    results = {
        "found_exact": [],      # Exact section_heading match
        "found_partial": [],    # Partial match in section_heading
        "found_in_text": [],    # Found in chunk text but not heading
        "not_found": []         # Completely missing
    }
    
    for section_name in section_list:
        # 1. Exact match in section_heading
        cur.execute("""
            SELECT COUNT(*) 
            FROM chunks c
            WHERE c.language = %s 
              AND c.section_heading = %s
        """, (language, section_name))
        
        exact_count = cur.fetchone()[0]
        
        if exact_count > 0:
            results["found_exact"].append((section_name, exact_count))
            continue
        
        # 2. Partial match in section_heading (contains key words)
        # Use first 2-3 meaningful words (skip common words)
        stopwords = {"the", "a", "an", "and", "or", "of", "in", "on", "at", "to", "for", "with", "by"}
        keywords = [w for w in section_name.split() if w.lower() not in stopwords][:3]
        
        if keywords:
            keyword_conditions = " AND ".join(["c.section_heading ILIKE %s" for _ in keywords])
            params = [language] + [f"%{kw}%" for kw in keywords]
            
            cur.execute(f"""
                SELECT COUNT(*) 
                FROM chunks c
                WHERE c.language = %s 
                  AND ({keyword_conditions})
            """, params)
            
            partial_count = cur.fetchone()[0]
            
            if partial_count > 0:
                results["found_partial"].append((section_name, partial_count))
                continue
        
        # 3. Search in chunk text (not just heading)
        # Use first few words of section name
        search_terms = " ".join(section_name.split()[:4])
        cur.execute("""
            SELECT COUNT(*) 
            FROM chunks c
            WHERE c.language = %s 
              AND c.text ILIKE %s
        """, (language, f"%{search_terms}%"))
        
        text_count = cur.fetchone()[0]
        
        if text_count > 0:
            results["found_in_text"].append((section_name, text_count))
        else:
            results["not_found"].append(section_name)
    
    cur.close()
    conn.close()
    return results


def print_section_check_results(results):
    """Print results in a readable format."""
    
    print("\n" + "="*80)
    print("SECTION EXISTENCE CHECK RESULTS")
    print("="*80 + "\n")
    
    # Exact matches
    if results['found_exact']:
        print(f"✅ EXACT MATCHES ({len(results['found_exact'])}):")
        for section, count in results['found_exact']:
            print(f"   • {section}: {count} chunks")
        print()
    
    # Partial matches
    if results['found_partial']:
        print(f"⚠️  PARTIAL MATCHES ({len(results['found_partial'])}):")
        for section, count in results['found_partial']:
            print(f"   • {section}: {count} chunks (matched by keywords in section_heading)")
        print()
    
    # Found in text only
    if results['found_in_text']:
        print(f"📄 FOUND IN TEXT ONLY ({len(results['found_in_text'])}):")
        for section, count in results['found_in_text']:
            print(f"   • {section}: {count} chunks (found in chunk text, not section heading)")
        print()
    
    # Not found
    if results['not_found']:
        print(f"❌ NOT FOUND ({len(results['not_found'])}):")
        for section in results['not_found']:
            print(f"   • {section}")
        print()
    
    # Summary
    total = len(results['found_exact']) + len(results['found_partial']) + \
            len(results['found_in_text']) + len(results['not_found'])
    found_total = total - len(results['not_found'])
    
    print("="*80)
    print(f"SUMMARY: {found_total}/{total} sections found ({found_total*100//total if total > 0 else 0}%)")
    print("="*80 + "\n")


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
    
    # Check all sections from the list
    print("\n" + "="*80)
    print("Checking all sections from Banking Sector structure:")
    print("="*80)
    
    results = check_sections_exist(SECTIONS_TO_CHECK, language="en")
    print_section_check_results(results)
