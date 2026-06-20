import os
import re
import json
from pathlib import Path
from collections import Counter
from pipeline.language_registry import normalise_numerals, MONTH_NAMES_INDIAN, convert_saka_date

PROCESSED_DIR = Path("data/processed")
MANIFEST_PATH = PROCESSED_DIR / "manifest.json"
METADATA_PATH = PROCESSED_DIR / "metadata.json"

# Canonical department naming mappings
DEPT_MAPPING = {
    "School Education": ["school education", "school edu", "dee"],
    "Health": ["health and family welfare", "tnhsp", "health dept", "health"],
    "Finance": ["finance", "tnifmc", "finance dept"],
    "Revenue": ["revenue", "revenue dept", "revenue administration"],
    "PWD": ["public works", "pwd"],
    "Agriculture": ["agriculture", "agri. dept", "tnau"],
    "HR&CE": ["hr&ce", "hindu religious"],
    "Social Welfare": ["social welfare", "wcd"],
    "Municipal Admin": ["municipal administration", "maws", "dtcp"],
    "Rural Development": ["rural development", "rd&pr", "tnrd"],
    "Industries": ["industries", "sipcot", "tidco"],
    "IT": ["information technology", "elcot", "tnega"],
    "Transport": ["transport", "mtc", "tnstc"],
    "Energy": ["energy", "tangedco", "tneb"]
}

MONTH_MAP = {
    "january": "01", "february": "02", "march": "03", "april": "04", "may": "05", "june": "06",
    "july": "07", "august": "08", "september": "09", "october": "10", "november": "11", "december": "12",
    "jan": "01", "feb": "02", "mar": "03", "apr": "04", "jun": "06",
    "jul": "07", "aug": "08", "sep": "09", "oct": "10", "nov": "11", "dec": "12"
}

def extract_doc_type(first_chars: str, full_text: str) -> str:
    combined = (first_chars + " " + full_text[:2000]).upper()
    
    if "G.O." in combined or "G. O." in combined or "GOVERNMENT ORDER" in combined:
        return "GO"
    if "CIRCULAR" in combined or "CIRCULAR NO." in combined:
        return "CIRCULAR"
    if "POLICY" in combined:
        return "POLICY"
    if "SCHEME" in combined or "SCHEME GUIDELINES" in combined:
        return "SCHEME"
    if "NOTIFICATION" in combined:
        return "NOTIFICATION"
    if "PROCEEDINGS" in combined or "PROC. NO." in combined:
        return "PROCEEDINGS"
    if "TENDER" in combined:
        return "TENDER"
    
    return "GENERAL"

def extract_department(first_chars: str, manifest_dept: str) -> str:
    # If the manifest department is valid and not 'unknown', use it
    if manifest_dept and manifest_dept.lower() != "unknown":
        # Check if we can map it to a canonical name
        for canonical, variants in DEPT_MAPPING.items():
            if manifest_dept.lower() in [v.lower() for v in variants] or manifest_dept.lower() == canonical.lower():
                return canonical
        return manifest_dept.capitalize()
    
    # Otherwise, scan first_chars (first 300 chars) for matches
    search_text = first_chars.lower()
    for canonical, variants in DEPT_MAPPING.items():
        for variant in variants:
            if variant.lower() in search_text:
                return canonical
                
    return "Unknown"

def preprocess_for_date(text: str) -> str:
    # 1. Convert all Indian script numerals to ASCII digits
    text = normalise_numerals(text)
    # 2. Replace Indian month names with numeric equivalents
    for month_name, month_num in MONTH_NAMES_INDIAN.items():
        text = text.replace(month_name, f" {month_num} ")
    return text

def parse_date(text: str) -> str:
    # Look in the first 2000 characters
    sample = preprocess_for_date(text[:2000])
    
    # 0. Check Saka Era date pattern (Gazette standard)
    # e.g., "15 Ashadha, 1945 (Saka 1945)" or "15 Ashadha 1945 Saka 1945" or similar
    # Gazette standard: "(\d{1,2})\s+(\w+),?\s+(\d{4})\s+\(?Saka\s+(\d{4})\)?"
    match_saka1 = re.search(r"(\d{1,2})\s+([A-Za-z\u0900-\u097F]+),?\s+(\d{4})\s+\(?Saka\s+(\d{4})\)?", sample, re.IGNORECASE)
    if match_saka1:
        day, month_name, greg_year, saka_year = match_saka1.groups()
        saka_months = {
            "chaitra": 1, "vaishakha": 2, "jyeshtha": 3, "ashadha": 4, "shravana": 5, "bhadrapada": 6,
            "ashwin": 7, "kartik": 8, "margashirsha": 9, "pausha": 10, "magha": 11, "phalguna": 12,
            "चैत्र": 1, "वैशाख": 2, "ज्येष्ठ": 3, "आषाढ़": 4, "श्रावण": 5, "भाद्रपद": 6,
            "अश्विन": 7, "कार्तिक": 8, "मार्गशीर्ष": 9, "पौष": 10, "माघ": 11, "फाल्गुन": 12
        }
        m_val = saka_months.get(month_name.lower(), 1)
        res = convert_saka_date(int(saka_year), m_val, int(day))
        print(f"Saka Era date found and converted to Gregorian: {res}")
        return res
        
    # Pattern 2: "(\d{1,4})\s+(?:Saka|शक|साका)\s+(\d{1,2})\s+(\d{4})"
    match_saka2 = re.search(r"(\d{1,4})\s+(?:Saka|शक|साका)\s+(\d{1,2})\s+(\d{4})", sample, re.IGNORECASE)
    if match_saka2:
        saka_year, month_num, day = match_saka2.groups()
        res = convert_saka_date(int(saka_year), int(month_num), int(day))
        print(f"Saka Era date found and converted to Gregorian: {res}")
        return res
    
    # 1. Regex DD.MM.YYYY | DD/MM/YYYY | DD-MM-YYYY
    match_dmy = re.search(r"\b(\d{1,2})[\.\/\-](\d{1,2})[\.\/\-](\d{4})\b", sample)
    if match_dmy:
        day, month, year = match_dmy.groups()
        return f"{year}-{int(month):02d}-{int(day):02d}"
        
    # 2. Regex "DD Month YYYY" or "Month DD, YYYY"
    # Match strings like "15 June 2023", "15th June 2023", "June 15, 2023"
    months_pattern = "|".join(list(MONTH_MAP.keys()) + list(MONTH_NAMES_INDIAN.keys()))
    
    # Case: DD Month YYYY (e.g. 15 June 2023 or 15th June 2023)
    match_dd_month_yyyy = re.search(
        rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+({months_pattern})\s+(\d{{4}})\b", sample, re.IGNORECASE
    )
    if match_dd_month_yyyy:
        day, month_str, year = match_dd_month_yyyy.groups()
        month = MONTH_MAP.get(month_str.lower(), MONTH_NAMES_INDIAN.get(month_str))
        if month:
            return f"{year}-{month}-{int(day):02d}"
        
    # Case: Month DD, YYYY (e.g. June 15, 2023)
    match_month_dd_yyyy = re.search(
        rf"\b({months_pattern})\s+(\d{{1,2}}),?\s+(\d{{4}})\b", sample, re.IGNORECASE
    )
    if match_month_dd_yyyy:
        month_str, day, year = match_month_dd_yyyy.groups()
        month = MONTH_MAP.get(month_str.lower(), MONTH_NAMES_INDIAN.get(month_str))
        if month:
            return f"{year}-{month}-{int(day):02d}"
        
    return None

def extract_ref_number(text: str) -> str:
    sample = text[:2000]
    # Match variants of No., Proc. No., Circular No., Lr. No.
    patterns = [
        r"\b(?:Proc\.\s+)?No\.?\s*([A-Za-z0-9\.\-\/]+)\b",
        r"\bCircular\s+No\.?\s*([A-Za-z0-9\.\-\/]+)\b",
        r"\bLr\.\s+No\.?\s*([A-Za-z0-9\.\-\/]+)\b",
        r"\bG\.O\.\s*\(?[A-Za-z0-9\s]*\)?\s*No\.?\s*([A-Za-z0-9\.\-\/]+)\b"
    ]
    for pattern in patterns:
        match = re.search(pattern, sample, re.IGNORECASE)
        if match:
            # Clean trailing punctuation
            val = match.group(1).strip()
            if val and val[-1] in (".", ",", "-"):
                val = val[:-1]
            return val
    return None

def main():
    if not MANIFEST_PATH.exists():
        print(f"Error: Manifest file '{MANIFEST_PATH}' does not exist. Run ingestion first.")
        return
        
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)
        
    metadata_list = []
    
    print(f"Extracting metadata from {len(manifest)} files...")
    
    for entry in manifest:
        if entry["status"] == "failed":
            continue
            
        filename = entry["processed_filename"]
        file_path = PROCESSED_DIR / filename
        if not file_path.exists():
            continue
            
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        first_chars = content[:500]
        
        doc_type = extract_doc_type(first_chars, content)
        dept = extract_department(content[:300], entry["department"])
        date = parse_date(content)
        ref_number = extract_ref_number(content)
        
        # Check script flags
        has_tamil = bool(re.search(r"[\u0b80-\u0bff]", content))
        has_english = bool(re.search(r"[a-zA-Z]", content))
        
        metadata_list.append({
            "filename": filename,
            "department": dept,
            "doc_type": doc_type,
            "date": date,
            "ref_number": ref_number,
            "word_count": entry["word_count"],
            "has_tamil": has_tamil,
            "has_english": has_english,
            "detected_language": entry["detected_language"]
        })
        
    with open(METADATA_PATH, "w", encoding="utf-8") as f:
        json.dump(metadata_list, f, indent=2, ensure_ascii=False)
        
    # Print statistics
    doc_types = [m["doc_type"] for m in metadata_list]
    depts = [m["department"] for m in metadata_list]
    null_dates = [m["filename"] for m in metadata_list if m["date"] is None]
    tamil_count = sum(1 for m in metadata_list if m["has_tamil"])
    
    print("\n--- Document Type Distribution ---")
    for dt, count in Counter(doc_types).items():
        print(f"  {dt:<15}: {count}")
        
    print("\n--- Department Distribution ---")
    for d, count in Counter(depts).items():
        print(f"  {d:<25}: {count}")
        
    print(f"\nTamil Documents: {tamil_count} / {len(metadata_list)}")
    print(f"Documents missing dates (requires review): {len(null_dates)}")
    for nd in null_dates[:10]:
         print(f"  - {nd}")
    if len(null_dates) > 10:
         print(f"  ... and {len(null_dates) - 10} more.")

if __name__ == "__main__":
    main()
