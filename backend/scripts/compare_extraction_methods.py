import os
import glob
import time
import fitz  # pymupdf
import pytesseract
from PIL import Image
import io

# Paths
PDF_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "downloads", "pdfs")
OUTPUT_BASE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "downloads", "comparison")
OUTPUT_DIRS = {
    "method1": os.path.join(OUTPUT_BASE, "method1_pymupdf_text"),
    "method2": os.path.join(OUTPUT_BASE, "method2_pymupdf_ocr"),
    "method3": os.path.join(OUTPUT_BASE, "method3_tesseract_ocr"),
}
for dir_path in OUTPUT_DIRS.values():
    os.makedirs(dir_path, exist_ok=True)

REPORT_FILE = os.path.join(OUTPUT_BASE, "comparison_report.txt")


def extract_method1_pymupdf_text(pdf_path):
    """Method 1: PyMuPDF text extraction"""
    try:
        doc = fitz.open(pdf_path)
        page_texts = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text")
            page_texts.append(text)
        doc.close()
        return '\n\n'.join(page_texts)
    except Exception as e:
        return None


def extract_method2_pymupdf_ocr(pdf_path):
    """Method 2: PyMuPDF OCR (requires Tesseract)"""
    try:
        doc = fitz.open(pdf_path)
        page_texts = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            # Try text first
            text = page.get_text("text")
            # If empty, try OCR
            if not text or len(text.strip()) < 10:
                try:
                    text = page.get_text("ocr")
                except:
                    text = ""  # OCR not available or failed
            page_texts.append(text)
        doc.close()
        return '\n\n'.join(page_texts)
    except Exception as e:
        return None


def extract_method3_tesseract_ocr(pdf_path):
    """Method 3: Pure Tesseract OCR extraction using pytesseract directly"""
    try:
        doc = fitz.open(pdf_path)
        page_texts = []
        
        # Check if Tesseract is available
        try:
            pytesseract.get_tesseract_version()
        except:
            doc.close()
            return None  # Tesseract not available
        
        # Check for Arabic support
        try:
            langs = pytesseract.get_languages()
            has_arabic = 'ara' in langs
        except:
            has_arabic = False
        
        lang = "ara+eng" if has_arabic else "eng"
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            try:
                # Convert PDF page to image (PIL Image)
                mat = fitz.Matrix(300/72, 300/72)  # 300 DPI
                pix = page.get_pixmap(matrix=mat)
                img_data = pix.tobytes("png")
                img = Image.open(io.BytesIO(img_data))
                
                # OCR the image using pytesseract
                text = pytesseract.image_to_string(img, lang=lang)
                page_texts.append(text)
            except Exception as e:
                # Log error for debugging
                print(f"  ⚠ OCR failed page {page_num + 1}: {str(e)[:80]}")
                page_texts.append("")
        
        doc.close()
        return '\n\n'.join(page_texts)
    except Exception as e:
        return None


def count_words(text):
    """Count words in text"""
    if not text:
        return 0
    words = text.split()
    return len(words)


def compare_methods(pdf_path):
    """Compare all 3 methods on a single PDF"""
    pdf_name = os.path.basename(pdf_path)
    results = {
        "pdf": pdf_name,
        "method1": {"text": None, "chars": 0, "words": 0, "time": 0, "error": None, "success": False},
        "method2": {"text": None, "chars": 0, "words": 0, "time": 0, "error": None, "success": False},
        "method3": {"text": None, "chars": 0, "words": 0, "time": 0, "error": None, "success": False},
    }
    
    # Method 1: PyMuPDF text
    try:
        start = time.time()
        text = extract_method1_pymupdf_text(pdf_path)
        elapsed = time.time() - start
        if text:
            results["method1"]["text"] = text
            results["method1"]["chars"] = len(text)
            results["method1"]["words"] = count_words(text)
            results["method1"]["success"] = len(text) > 0
        results["method1"]["time"] = elapsed
    except Exception as e:
        results["method1"]["error"] = str(e)
    
    # Method 2: PyMuPDF OCR
    try:
        start = time.time()
        text = extract_method2_pymupdf_ocr(pdf_path)
        elapsed = time.time() - start
        if text:
            results["method2"]["text"] = text
            results["method2"]["chars"] = len(text)
            results["method2"]["words"] = count_words(text)
            results["method2"]["success"] = len(text) > 0
        results["method2"]["time"] = elapsed
    except Exception as e:
        results["method2"]["error"] = str(e)
    
    # Method 3: Tesseract OCR (only if Method 1 has low word count)
    method1_words = results["method1"]["words"]
    if method1_words < 50:  # Only run OCR if text extraction was poor
        try:
            start = time.time()
            text = extract_method3_tesseract_ocr(pdf_path)
            elapsed = time.time() - start
            if text:
                results["method3"]["text"] = text
                results["method3"]["chars"] = len(text)
                results["method3"]["words"] = count_words(text)
                results["method3"]["success"] = len(text) > 0
            results["method3"]["time"] = elapsed
        except Exception as e:
            results["method3"]["error"] = str(e)
    else:
        # Skip OCR if Method 1 already extracted enough text
        results["method3"]["text"] = None
        results["method3"]["success"] = False
    
    # Save outputs
    for method_key, output_dir in OUTPUT_DIRS.items():
        if results[method_key]["text"]:
            output_file = os.path.join(output_dir, pdf_name.replace('.pdf', '.txt'))
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(results[method_key]["text"])
    
    return results


def generate_summary_report(all_results):
    """Generate summary statistics report"""
    total_pdfs = len(all_results)
    
    # Aggregate stats
    stats = {
        "method1": {"success": 0, "total_chars": 0, "total_words": 0, "total_time": 0, "errors": 0},
        "method2": {"success": 0, "total_chars": 0, "total_words": 0, "total_time": 0, "errors": 0},
        "method3": {"success": 0, "total_chars": 0, "total_words": 0, "total_time": 0, "errors": 0},
    }
    
    for result in all_results:
        for method in ["method1", "method2", "method3"]:
            if result[method]["success"]:
                stats[method]["success"] += 1
                stats[method]["total_chars"] += result[method]["chars"]
                stats[method]["total_words"] += result[method]["words"]
            if result[method]["error"]:
                stats[method]["errors"] += 1
            stats[method]["total_time"] += result[method]["time"]
    
    # Generate report
    report_lines = [
        "=" * 80,
        "PDF TEXT EXTRACTION METHODS COMPARISON REPORT",
        "=" * 80,
        f"\nTotal PDFs tested: {total_pdfs}\n",
        "-" * 80,
        "SUMMARY STATISTICS",
        "-" * 80,
        "",
        "Method 1: PyMuPDF Text Extraction",
        f"  Success Rate: {stats['method1']['success']}/{total_pdfs} ({stats['method1']['success']/total_pdfs*100:.1f}%)",
        f"  Total Characters: {stats['method1']['total_chars']:,}",
        f"  Total Words: {stats['method1']['total_words']:,}",
        f"  Avg Characters per PDF: {stats['method1']['total_chars']/max(stats['method1']['success'], 1):,.0f}",
        f"  Avg Words per PDF: {stats['method1']['total_words']/max(stats['method1']['success'], 1):,.0f}",
        f"  Total Time: {stats['method1']['total_time']:.2f}s",
        f"  Avg Time per PDF: {stats['method1']['total_time']/total_pdfs:.2f}s",
        f"  Errors: {stats['method1']['errors']}",
        "",
        "Method 2: PyMuPDF OCR",
        f"  Success Rate: {stats['method2']['success']}/{total_pdfs} ({stats['method2']['success']/total_pdfs*100:.1f}%)",
        f"  Total Characters: {stats['method2']['total_chars']:,}",
        f"  Total Words: {stats['method2']['total_words']:,}",
        f"  Avg Characters per PDF: {stats['method2']['total_chars']/max(stats['method2']['success'], 1):,.0f}",
        f"  Avg Words per PDF: {stats['method2']['total_words']/max(stats['method2']['success'], 1):,.0f}",
        f"  Total Time: {stats['method2']['total_time']:.2f}s",
        f"  Avg Time per PDF: {stats['method2']['total_time']/total_pdfs:.2f}s",
        f"  Errors: {stats['method2']['errors']}",
        "",
        "Method 3: Tesseract OCR",
        f"  Success Rate: {stats['method3']['success']}/{total_pdfs} ({stats['method3']['success']/total_pdfs*100:.1f}%)",
        f"  Total Characters: {stats['method3']['total_chars']:,}",
        f"  Total Words: {stats['method3']['total_words']:,}",
        f"  Avg Characters per PDF: {stats['method3']['total_chars']/max(stats['method3']['success'], 1):,.0f}",
        f"  Avg Words per PDF: {stats['method3']['total_words']/max(stats['method3']['success'], 1):,.0f}",
        f"  Total Time: {stats['method3']['total_time']:.2f}s",
        f"  Avg Time per PDF: {stats['method3']['total_time']/total_pdfs:.2f}s",
        f"  Errors: {stats['method3']['errors']}",
        "",
        "-" * 80,
        "WINNER BY METRIC",
        "-" * 80,
    ]
    
    # Determine winners
    winners = {
        "Success Rate": max(stats.items(), key=lambda x: x[1]["success"])[0],
        "Total Characters": max(stats.items(), key=lambda x: x[1]["total_chars"])[0],
        "Total Words": max(stats.items(), key=lambda x: x[1]["total_words"])[0],
        "Speed (Fastest)": min(stats.items(), key=lambda x: x[1]["total_time"])[0],
        "Fewest Errors": min(stats.items(), key=lambda x: x[1]["errors"])[0],
    }
    
    for metric, winner in winners.items():
        method_name = {
            "method1": "PyMuPDF Text",
            "method2": "PyMuPDF OCR",
            "method3": "Tesseract OCR"
        }[winner]
        report_lines.append(f"  {metric}: {method_name} ({winner})")
    
    report_lines.extend([
        "",
        "=" * 80,
        f"Report generated at: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        "=" * 80,
    ])
    
    # Write report
    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_lines))
    
    # Print to console
    print('\n'.join(report_lines))


def main():
    """Main comparison function"""
    # Check Tesseract availability
    tessdata = fitz.get_tessdata()
    if not tessdata:
        print("⚠ WARNING: Tesseract OCR not found!")
        print("  Method 3 (Tesseract OCR) will be skipped.")
        print("  Set TESSDATA_PREFIX environment variable or install Tesseract\n")
    else:
        arabic_pack = os.path.join(tessdata, "ara.traineddata")
        has_arabic = os.path.exists(arabic_pack)
        lang_info = "Arabic + English" if has_arabic else "English only"
        print(f"✓ Tesseract OCR available ({lang_info})\n")
    
    pdf_files = glob.glob(os.path.join(PDF_DIR, "*.pdf"))
    print(f"Found {len(pdf_files)} PDFs to compare\n")
    
    all_results = []
    
    for i, pdf_path in enumerate(pdf_files, 1):
        pdf_name = os.path.basename(pdf_path)
        print(f"[{i}/{len(pdf_files)}] Comparing: {pdf_name}")
        
        try:
            results = compare_methods(pdf_path)
            all_results.append(results)
            
            # Print quick stats
            m1 = results["method1"]
            m2 = results["method2"]
            m3 = results["method3"]
            print(f"  Method1: {m1['chars']} chars, {m1['words']} words, {m1['time']:.2f}s")
            print(f"  Method2: {m2['chars']} chars, {m2['words']} words, {m2['time']:.2f}s")
            print(f"  Method3: {m3['chars']} chars, {m3['words']} words, {m3['time']:.2f}s")
            
        except Exception as e:
            print(f"  ✗ Error: {e}")
            continue
    
    # Generate summary report
    print(f"\n{'='*80}")
    print("Generating summary report...")
    print(f"{'='*80}\n")
    generate_summary_report(all_results)
    
    print(f"\n✓ Comparison complete!")
    print(f"  Results saved to: {OUTPUT_BASE}")
    print(f"  Report saved to: {REPORT_FILE}")


if __name__ == "__main__":
    main()
