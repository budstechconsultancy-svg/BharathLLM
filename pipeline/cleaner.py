import os
import re
import json
from pathlib import Path

PROCESSED_DIR = Path("data/processed")
CLEANED_DIR = Path("data/cleaned")
MANIFEST_PATH = PROCESSED_DIR / "manifest.json"
METADATA_PATH = PROCESSED_DIR / "metadata.json"

# Canonical department name mappings used for validation/normalisation reference
DEPT_CANONICALS = [
    "School Education", "Health", "Finance", "Revenue", "PWD", "Agriculture", 
    "HR&CE", "Social Welfare", "Municipal Admin", "Rural Development", 
    "Industries", "IT", "Transport", "Energy"
]

def load_json_file(path: Path) -> list:
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []

def save_json_file(path: Path, data: list):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def clean_text_content(text: str, source_type: str, file_metadata: dict) -> tuple[str, int]:
    tamil_ocr_errors = 0
    lines = text.split("\n")
    cleaned_lines = []
    
    # 1. BOILERPLATE REMOVAL (Line-by-line checks)
    # Define English and Tamil boilerplate filters
    boilerplate_patterns = [
        r"^GOVERNMENT OF TAMIL NADU$",
        r"^ABSTRACT$",
        r"^Page \d+ of \d+$",
        r"^-\s*\d+\s*-$",
        r"^\[\s*\d+\s*\]$",
        r"^DRAFT$",
        r"^CONFIDENTIAL$",
        r"^COPY$",
        r"^Forwarded\s*/\s*Forward$"
    ]
    compiled_patterns = [re.compile(p, re.IGNORECASE) for p in boilerplate_patterns]
    
    # Repeated standalone headers (Tamil)
    tamil_header_pattern = re.compile(r"^தமிழ்நாடு\s+அரசு$", re.IGNORECASE)
    
    for line in lines:
        line_stripped = line.strip()
        
        # Filter divider lines (e.g. ---, ===, ____)
        if re.match(r"^[\-\=\_]{3,}$", line_stripped):
            continue
            
        # Match English boilerplate
        matched_boilerplate = False
        for pattern in compiled_patterns:
            if pattern.match(line_stripped):
                matched_boilerplate = True
                break
        if matched_boilerplate:
            continue
            
        # Match Tamil boilerplate
        if tamil_header_pattern.match(line_stripped):
            continue
            
        cleaned_lines.append(line)
        
    cleaned_text = "\n".join(cleaned_lines)
    
    # 2. OCR ERROR CORRECTION
    if source_type == "scanned":
        # Hyphenated line breaks: "word-\n" -> "word"
        cleaned_text = re.sub(r"(\w+)-\n(\w+)", r"\1\2", cleaned_text)
        
        # Missing space after period (excluding abbreviation or decimals)
        # e.g., "G.O.Ms.No" -> space rules handled below, or standard text sentences
        cleaned_text = re.sub(r"(?<=[a-zA-Z]{3,})\.(?=[a-zA-Z]{2,})", ". ", cleaned_text)
        
        # Reference IDs adjustment: check if letter is preceded by "0" vs "O"
        # Often IDs have "sk-0..." or similar pattern. Let's fix common "No.0..." -> "No. O..." or similar
        # E.g., "No.0" -> "No. 0" (handled in spaces), "G.O" formatting is handled below.
        
        # Tamil OCR Glyphs error replacement: replacing unrecognised glyphs
        unrecognised_glyphs = ["?", "□", "■", ""]
        for glyph in unrecognised_glyphs:
            if glyph in cleaned_text:
                # Count only occurrences in Tamil unicode context area to avoid replacing normal English punctuation question marks
                # Find all occurrences of glyph preceded or succeeded by Tamil characters within 5 chars
                tamil_context_matches = re.findall(rf"(?:[\u0b80-\u0bff].{{0,5}}{re.escape(glyph)})|({re.escape(glyph)}.{{0,5}}[\u0b80-\u0bff])", cleaned_text)
                glyph_count = len(tamil_context_matches)
                if glyph_count > 0:
                    tamil_ocr_errors += glyph_count
                    # Replace glyph with placeholder in Tamil context
                    # For simple robust correction, if we find these markers near Tamil, we replace them
                    cleaned_text = re.sub(rf"([\u0b80-\u0bff].{{0,5}}){re.escape(glyph)}", r"\1[TAMIL_OCR_ERROR]", cleaned_text)
                    cleaned_text = re.sub(rf"{re.escape(glyph)}(.{{0,5}}[\u0b80-\u0bff])", r"[TAMIL_OCR_ERROR]\1", cleaned_text)

    # 3. TERMINOLOGY NORMALISATION
    # Standardise G.O. variations
    cleaned_text = re.sub(r"\b(?:G\.?\s*O\.?|Govt\.?\s*Order)\b", "Government Order", cleaned_text)
    # Standardise Dates variations
    cleaned_text = re.sub(r"\b(?:Dt\.?|dt\.?|Dtd\.?|dtd\.?)\b", "Dated", cleaned_text)
    # Standardise Department abbreviation variants
    cleaned_text = re.sub(r"\b(?:Dept\.?|dept\.?)\b", "Department", cleaned_text)
    # Rupees normalization
    cleaned_text = re.sub(r"\b(?:Rs\.?|rs\.?|INR)\b", "Rs.", cleaned_text)
    
    # 4. WHITESPACE & PARAGRAPH STRUCTURE
    # Remove trailing spaces on each line
    lines = [line.rstrip() for line in cleaned_text.split("\n")]
    # Join with newlines
    cleaned_text = "\n".join(lines)
    # Collapse multiple spaces (excluding newlines) to a single space
    cleaned_text = re.sub(r"[ \t]{2,}", " ", cleaned_text)
    # Collapse 3+ blank lines into a single blank line (double newline paragraph structure)
    cleaned_text = re.sub(r"\n{3,}", "\n\n", cleaned_text)
    
    return cleaned_text.strip(), tamil_ocr_errors

def calculate_quality_score(text: str, ocr_confidence: float | None, source_type: str) -> float:
    words = text.split()
    if not words:
        return 0.0
        
    # score_a: words with length 3-15 chars / total words * 100
    good_length_words = [w for w in words if 3 <= len(w) <= 15]
    score_a = (len(good_length_words) / len(words)) * 100
    
    # score_b: ocr_confidence (100 if text-based)
    score_b = 100.0 if source_type == "text" else (ocr_confidence if ocr_confidence is not None else 0.0)
    
    # score_c: sentence ratio score
    # Count sentences ending in . ? ! or Tamil character ।
    sentence_endings = re.findall(r"[\.\?\!।]+", text)
    sentence_count = len(sentence_endings)
    if sentence_count == 0:
        score_c = 0.0
    else:
        word_count = len(words)
        expected_ratio = word_count / 20.0  # assume average 20 words per sentence
        if expected_ratio == 0:
            score_c = 0.0
        else:
            score_c = min((sentence_count / expected_ratio) * 100, 100.0)
            
    # Composite Quality Score formula
    quality_score = (score_a * 0.4) + (score_b * 0.4) + (score_c * 0.2)
    return round(quality_score, 2)

def main():
    manifest = load_json_file(MANIFEST_PATH)
    metadata = load_json_file(METADATA_PATH)
    
    if not manifest:
        print("Error: No manifest records found. Ingest files first.")
        return
        
    CLEANED_DIR.mkdir(parents=True, exist_ok=True)
    
    metadata_map = {m["filename"]: m for m in metadata}
    updated_manifest = []
    
    review_list = []
    cleaned_count = 0
    
    print(f"Cleaning {len(manifest)} manifest entries...")
    
    for entry in manifest:
        if entry["status"] == "failed":
            updated_manifest.append(entry)
            continue
            
        proc_filename = entry["processed_filename"]
        proc_path = PROCESSED_DIR / proc_filename
        if not proc_path.exists():
            entry["status"] = "failed"
            entry["error"] = f"Processed text file missing: {proc_filename}"
            updated_manifest.append(entry)
            continue
            
        with open(proc_path, "r", encoding="utf-8") as f:
            raw_text = f.read()
            
        file_metadata = metadata_map.get(proc_filename, {})
        
        cleaned_text, tamil_errors = clean_text_content(raw_text, entry["source_type"], file_metadata)
        
        # Save to /data/cleaned/
        cleaned_path = CLEANED_DIR / proc_filename
        with open(cleaned_path, "w", encoding="utf-8") as f:
            f.write(cleaned_text)
            
        # Calculate quality score
        quality_score = calculate_quality_score(cleaned_text, entry["ocr_confidence"], entry["source_type"])
        needs_review = quality_score < 40.0
        
        # Log review
        if needs_review:
            review_list.append((proc_filename, quality_score))
            
        # Update manifest entry
        entry["quality_score"] = quality_score
        entry["cleaned_filename"] = str(cleaned_path.relative_to(Path(".")))
        entry["needs_review"] = needs_review
        
        updated_manifest.append(entry)
        cleaned_count += 1
        
    save_json_file(MANIFEST_PATH, updated_manifest)
    
    print(f"\n--- Cleaning Complete ---")
    print(f"Total files cleaned: {cleaned_count}")
    print(f"Needs review (score < 40): {len(review_list)}")
    
    if review_list:
        print("\nFiles requiring review:")
        for r_file, score in review_list:
            print(f"  - {r_file:<50} (Score: {score})")

if __name__ == "__main__":
    main()
