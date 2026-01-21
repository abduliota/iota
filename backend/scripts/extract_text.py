import os
import re
import glob
import fitz  # pymupdf

# Paths
PDF_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "downloads", "pdfs")
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "downloads", "extracted_text")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def check_tesseract_available():
    """Check if Tesseract OCR is installed and has Arabic support"""
    try:
        tessdata = fitz.get_tessdata()
        if tessdata:
            arabic_pack = os.path.join(tessdata, "ara.traineddata")
            has_arabic = os.path.exists(arabic_pack)
            return True, has_arabic
        return False, False
    except:
        return False, False


def extract_text_from_pdf(pdf_path):
    """Extract text from PDF page by page, with OCR fallback for scanned PDFs"""
    doc = fitz.open(pdf_path)
    page_texts = []
    
    # Extract text first
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text")
        page_texts.append(text)
    
    # Detect scanned PDF (very little text extracted)
    total_raw = sum(len(p.strip()) for p in page_texts)
    is_scanned = total_raw < 50
    
    # If scanned, try OCR
    if is_scanned:
        tesseract_available, has_arabic = check_tesseract_available()
        if tesseract_available:
            # Re-extract with OCR
            page_texts = []
            lang = "ara+eng" if has_arabic else "eng"
            for page_num in range(len(doc)):
                page = doc[page_num]
                try:
                    textpage_ocr = page.get_textpage_ocr(language=lang, dpi=300)
                    text = textpage_ocr.get_text()
                    page_texts.append(text)
                except Exception as e:
                    # OCR failed for this page, keep empty
                    page_texts.append("")
    
    doc.close()
    return page_texts, is_scanned


def clean_text(page_texts):
    """Remove headers/footers and normalize whitespace"""
    # Detect repeated lines (headers/footers)
    line_counts = {}
    for page_text in page_texts:
        lines = page_text.split('\n')
        for line in lines:
            line = line.strip()
            if len(line) < 50:  # Short lines likely headers/footers
                line_counts[line] = line_counts.get(line, 0) + 1
    
    # Lines appearing on >50% of pages are headers/footers
    threshold = len(page_texts) * 0.5
    headers_footers = {line for line, count in line_counts.items() 
                       if count > threshold}
    
    # Remove headers/footers and page numbers
    cleaned_pages = []
    for page_text in page_texts:
        lines = page_text.split('\n')
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            # Skip headers/footers
            if line in headers_footers:
                continue
            # Skip page numbers (simple patterns)
            if re.match(r'^(Page\s*\d+|صفحة\s*\d+)$', line, re.IGNORECASE):
                continue
            if line:  # Keep non-empty lines
                cleaned_lines.append(line)
        cleaned_pages.append('\n'.join(cleaned_lines))
    
    # Join all pages and normalize whitespace
    full_text = '\n\n'.join(cleaned_pages)
    full_text = re.sub(r' +', ' ', full_text)  # Multiple spaces → single space
    full_text = re.sub(r'\n\s*\n\s*\n+', '\n\n', full_text)  # Multiple newlines → double
    
    return full_text


def main():
    """Process all PDFs"""
    pdf_files = glob.glob(os.path.join(PDF_DIR, "*.pdf"))
    print(f"Found {len(pdf_files)} PDFs to process\n")
    
    # Check Tesseract availability
    tesseract_available, has_arabic = check_tesseract_available()
    if tesseract_available:
        lang_info = "Arabic + English" if has_arabic else "English only"
        print(f"✓ Tesseract OCR available ({lang_info})\n")
    else:
        print(f"⚠ Tesseract OCR not available - scanned PDFs will have minimal extraction\n")
    
    scanned_pdfs = []
    text_based_pdfs = []
    
    for i, pdf_path in enumerate(pdf_files, 1):
        pdf_name = os.path.basename(pdf_path)
        print(f"[{i}/{len(pdf_files)}] Processing: {pdf_name}")
        
        try:
            # Extract text
            page_texts, is_scanned = extract_text_from_pdf(pdf_path)
            raw_length = sum(len(p) for p in page_texts)
            
            # Track PDF type
            if is_scanned:
                scanned_pdfs.append((pdf_name, raw_length))
                pdf_type = "SCANNED"
            else:
                text_based_pdfs.append((pdf_name, raw_length))
                pdf_type = "text-based"
            
            # Clean text
            cleaned_text = clean_text(page_texts)
            
            # Save to text file
            output_file = os.path.join(OUTPUT_DIR, pdf_name.replace('.pdf', '.txt'))
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(cleaned_text)
            
            print(f"✓ Extracted: {len(cleaned_text)} chars (raw: {raw_length}, type: {pdf_type})")
            
        except Exception as e:
            print(f"✗ Error processing {pdf_name}: {e}")
            raise  # Stop on first error
    
    # Print summary
    print(f"\n{'='*80}")
    print("SUMMARY REPORT")
    print(f"{'='*80}")
    print(f"\nText-based PDFs: {len(text_based_pdfs)}")
    print(f"Scanned PDFs: {len(scanned_pdfs)}")
    
    if scanned_pdfs:
        print(f"\nScanned PDFs processed:")
        for pdf_name, chars in scanned_pdfs[:10]:  # Show first 10
            print(f"  - {pdf_name} ({chars} chars)")
        if len(scanned_pdfs) > 10:
            print(f"  ... and {len(scanned_pdfs) - 10} more")
    
    print(f"\n✓ Completed! Text files saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
