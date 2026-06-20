import os
import sys
import re
import json
import argparse
import datetime
import nltk
nltk.download('stopwords', quiet=True)
import subprocess
from pathlib import Path
from tqdm import tqdm

import fitz  # PyMuPDF
import pytesseract
from PIL import Image
from langdetect import detect, DetectorFactory

# Set seed for reproducible language detection
DetectorFactory.seed = 42

RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")
MANIFEST_PATH = PROCESSED_DIR / "manifest.json"

def run_preflight_checks():
    print("Running pre-flight checks...")
    # Check Tesseract version
    try:
        version = pytesseract.get_tesseract_version()
        print(f"Tesseract OCR found. Version: {version}")
    except Exception as e:
        print(f"CRITICAL ERROR: Tesseract is not installed or not in PATH. Details: {e}")
        sys.exit(1)

    # Check for Tamil and English language support
    try:
        # Tesseract output is typically a list of langs separated by newlines
        langs_output = subprocess.check_output(["tesseract", "--list-langs"], text=True)
        langs = [line.strip() for line in langs_output.split("\n") if line.strip()]
        
        # Verify 'tam' (or 'tam_eng') and 'eng'
        has_tam = "tam" in langs or "ta" in langs
        has_eng = "eng" in langs or "en" in langs
        
        if not has_tam:
            print("CRITICAL ERROR: Tamil language pack ('tam') is missing in Tesseract.")
            print("Please run: sudo apt-get install tesseract-ocr-tam (on Linux) or install the Tamil pack on Windows.")
            sys.exit(1)
        if not has_eng:
            print("CRITICAL ERROR: English language pack ('eng') is missing in Tesseract.")
            sys.exit(1)
            
        print("Tesseract language packs verified: 'tam' and 'eng' are present.")
    except Exception as e:
        print(f"CRITICAL ERROR: Failed to run 'tesseract --list-langs'. Details: {e}")
        sys.exit(1)

    # Verify directories exist
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    print("Storage directories validated.")

def detect_tamil_presence(text: str) -> bool:
    # Tamil Unicode block range: U+0B80 to U+0BFF
    tamil_regex = re.compile(r"[\u0b80-\u0bff]")
    return bool(tamil_regex.search(text))

def detect_language(text: str) -> str:
    cleaned = text.strip()[:1000]
    if not cleaned:
        return "unknown"
    
    has_tam = detect_tamil_presence(cleaned)
    
    try:
        lang = detect(cleaned)
    except Exception:
        lang = "unknown"
        
    if has_tam and (lang == "ta" or "ta" in lang):
        return "ta"
    elif has_tam:
        return "mixed"
    elif lang == "en":
        return "en"
    return lang

def clean_text_light(text: str) -> str:
    # Remove null bytes and non-printable control chars, preserving common ones like \n, \t
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", text)
    # Collapse 3+ consecutive spaces to a single space
    text = re.sub(r" {3,}", " ", text)
    # Normalize line endings to \n
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text

def process_pdf(pdf_path: Path, department: str) -> dict:
    manifest_entry = {
        "original_filename": pdf_path.name,
        "processed_filename": "",
        "department": department,
        "ingested_at": datetime.datetime.now().isoformat(),
        "source_type": "text",
        "detected_language": "en",
        "page_count": 0,
        "word_count": 0,
        "ocr_confidence": None,
        "low_confidence_pages": [],
        "status": "ok",
        "error": None
    }
    
    doc = None
    try:
        doc = fitz.open(pdf_path)
        manifest_entry["page_count"] = len(doc)
        
        if len(doc) == 0:
            raise ValueError("PDF is empty (0 pages).")
            
        # STEP A: Type detection
        # Extract first page text
        first_page = doc[0]
        first_page_text = first_page.get_text()
        
        # text_based if average characters per page on 1st page is > 50
        is_text_based = len(first_page_text.strip()) > 50
        manifest_entry["source_type"] = "text" if is_text_based else "scanned"
        
        extracted_text_pages = []
        confidences = []
        low_conf_pages = []
        
        # STEP B: Extraction
        for idx, page in enumerate(doc):
            page_num = idx + 1
            if is_text_based:
                # Text-based extraction
                text = page.get_text()
                extracted_text_pages.append(f"\n\n[PAGE_{page_num}]\n\n" + text)
            else:
                # Scanned extraction (OCR)
                # Convert to image (DPI=300)
                pix = page.get_pixmap(dpi=300)
                # Convert fitz pixmap to PIL Image
                img_data = pix.tobytes("png")
                
                from io import BytesIO
                img = Image.open(BytesIO(img_data))
                
                # Run OCR
                # Config --oem 3 (Default, LSTMBased), --psm 6 (Assume a single uniform block of text)
                ocr_text = pytesseract.image_to_string(img, lang="tam+eng", config="--oem 3 --psm 6")
                extracted_text_pages.append(f"\n\n[PAGE_{page_num}]\n\n" + ocr_text)
                
                # Fetch confidence
                try:
                    data = pytesseract.image_to_data(img, lang="tam+eng", config="--oem 3 --psm 6", output_type=pytesseract.Output.DICT)
                    conf_values = [int(c) for c in data["conf"] if c != "-1" and str(c).strip()]
                    if conf_values:
                        avg_conf = sum(conf_values) / len(conf_values)
                        confidences.append(avg_conf)
                        if avg_conf < 40:
                            low_conf_pages.append(page_num)
                    else:
                        confidences.append(0.0)
                        low_conf_pages.append(page_num)
                except Exception as e:
                    print(f"Warning: Failed to extract confidence metrics for page {page_num}: {e}")
                    confidences.append(0.0)
                    low_conf_pages.append(page_num)
        
        full_text = "".join(extracted_text_pages)
        
        # Detect language
        manifest_entry["detected_language"] = detect_language(full_text)
        
        # OCR Confidence calculation
        if not is_text_based:
            if confidences:
                manifest_entry["ocr_confidence"] = round(sum(confidences) / len(confidences), 2)
            else:
                manifest_entry["ocr_confidence"] = 0.0
            manifest_entry["low_confidence_pages"] = low_conf_pages
            if manifest_entry["ocr_confidence"] < 40 or len(low_conf_pages) > 0.5 * len(doc):
                manifest_entry["status"] = "low_confidence"
                
        # STEP C: Cleanup
        cleaned_text = clean_text_light(full_text)
        
        # Word count estimate
        manifest_entry["word_count"] = len(cleaned_text.split())
        
        # STEP D: Save
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_stem = "".join([c if c.isalnum() else "_" for c in pdf_path.stem])
        out_filename = f"{department}_{safe_stem}_{timestamp}.txt"
        out_path = PROCESSED_DIR / out_filename
        
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(cleaned_text)
            
        manifest_entry["processed_filename"] = out_filename
        
    except Exception as e:
        manifest_entry["status"] = "failed"
        manifest_entry["error"] = str(e)
        print(f"Error processing {pdf_path.name}: {e}")
    finally:
        if doc is not None:
            doc.close()
            
    return manifest_entry

def update_manifest(entry: dict):
    manifest_data = []
    if MANIFEST_PATH.exists():
        try:
            with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
                manifest_data = json.load(f)
        except Exception:
            manifest_data = []
            
    # Filter out existing entries for the same original_filename to prevent duplication
    manifest_data = [e for e in manifest_data if e["original_filename"] != entry["original_filename"]]
    manifest_data.append(entry)
    
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2, ensure_ascii=False)

def main():
    parser = argparse.ArgumentParser(description="TN Govt LLM Ingestion Pipeline")
    parser.add_argument("--folder", type=str, default="data/raw", help="Folder containing raw PDFs")
    parser.add_argument("--dept", type=str, default="unknown", help="Department tag (e.g. health, finance)")
    args = parser.parse_args()
    
    run_preflight_checks()
    
    input_folder = Path(args.folder)
    if not input_folder.exists():
        print(f"Error: Raw PDF folder '{input_folder}' does not exist.")
        sys.exit(1)
        
    pdf_files = list(input_folder.glob("*.pdf")) + list(input_folder.glob("*.PDF"))
    if not pdf_files:
        print(f"No PDF files found in '{input_folder}'.")
        return
        
    print(f"Found {len(pdf_files)} PDF files to process.")
    
    succeeded = 0
    failed = 0
    tamil_count = 0
    
    for pdf_path in tqdm(pdf_files, desc="Ingesting PDFs"):
        entry = process_pdf(pdf_path, args.dept)
        update_manifest(entry)
        
        if entry["status"] in ("ok", "low_confidence"):
            succeeded += 1
            if entry["detected_language"] in ("ta", "mixed"):
                tamil_count += 1
        else:
            failed += 1
            
    print("\nIngestion Summary:")
    print(f"Total processed: {len(pdf_files)}")
    print(f"Succeeded:       {succeeded}")
    print(f"Failed:          {failed}")
    print(f"Tamil/Mixed:     {tamil_count}")

if __name__ == "__main__":
    main()
