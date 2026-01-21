import fitz
import os

print("Checking Tesseract installation...\n")

# Use PyMuPDF's built-in detection
tessdata = fitz.get_tessdata()

if tessdata:
    print(f"✓ Tesseract found!")
    print(f"  Tessdata folder: {tessdata}")
    print(f"  Installation: {os.path.dirname(tessdata)}")
    
    # List available language packs
    lang_files = [f for f in os.listdir(tessdata) if f.endswith('.traineddata')]
    print(f"\n  Available language packs: {len(lang_files)}")
    for lang in sorted(lang_files):
        print(f"    - {lang}")
    
    # Check for Arabic
    arabic_pack = os.path.join(tessdata, "ara.traineddata")
    if os.path.exists(arabic_pack):
        print(f"\n✓ Arabic language pack found!")
    else:
        print(f"\n✗ Arabic language pack NOT found")
        print(f"  Download from: https://github.com/tesseract-ocr/tessdata/raw/main/ara.traineddata")
        print(f"  Place in: {tessdata}")
else:
    print("✗ Tesseract not detected")
    print("\nPossible locations to check:")
    print("  - C:\\ProgramData\\chocolatey\\lib\\tesseract\\")
    print("  - C:\\tools\\tesseract\\")
    print("  - Check Chocolatey package location")