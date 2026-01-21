import os
import glob

# Paths (same style as compare_extraction_methods.py)
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
PDF_DIR = os.path.join(BASE_DIR, "downloads", "pdfs")
COMPARISON_BASE = os.path.join(BASE_DIR, "downloads", "comparison")

METHOD_DIRS = {
    "method1": os.path.join(COMPARISON_BASE, "method1_pymupdf_text"),
    "method2": os.path.join(COMPARISON_BASE, "method2_pymupdf_ocr"),
    "method3": os.path.join(COMPARISON_BASE, "method3_tesseract_ocr"),
}

FINAL_DIR = os.path.join(BASE_DIR, "downloads", "extracted_text")
os.makedirs(FINAL_DIR, exist_ok=True)


def read_text_if_exists(path: str) -> str:
    """Read text file if it exists, return empty string otherwise."""
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def count_words(text: str) -> int:
    """Count words in text."""
    return len(text.split()) if text else 0


def build_final_texts():
    """Build final text files by selecting best extraction method for each PDF."""
    pdf_files = glob.glob(os.path.join(PDF_DIR, "*.pdf"))
    print(f"Found {len(pdf_files)} PDFs to finalize\n")

    for i, pdf_path in enumerate(pdf_files, 1):
        pdf_name = os.path.basename(pdf_path)
        txt_name = pdf_name.replace(".pdf", ".txt")

        print(f"[{i}/{len(pdf_files)}] Selecting best text for: {pdf_name}")

        # Check all method outputs
        candidates = {}
        for method, dir_path in METHOD_DIRS.items():
            cand_path = os.path.join(dir_path, txt_name)
            text = read_text_if_exists(cand_path)
            candidates[method] = {
                "path": cand_path,
                "text": text,
                "words": count_words(text),
            }

        # Pick method with highest word count
        best_method = max(candidates.items(), key=lambda x: x[1]["words"])[0]
        best = candidates[best_method]

        if best["words"] == 0:
            print("  ⚠ No non-empty text found for this PDF, skipping")
            continue

        # Write final text file
        final_path = os.path.join(FINAL_DIR, txt_name)
        with open(final_path, "w", encoding="utf-8") as f:
            f.write(best["text"])

        print(f"  ✓ Chosen: {best_method} ({best['words']} words) -> {final_path}")

    print(f"\n✓ Complete! Final texts saved to: {FINAL_DIR}")


if __name__ == "__main__":
    build_final_texts()
