import os
import re
import json
import uuid
from pathlib import Path
from collections import Counter

CLEANED_DIR = Path("data/cleaned")
CHUNKS_DIR = Path("data/chunks")
MANIFEST_PATH = Path("data/processed/manifest.json")
METADATA_PATH = Path("data/processed/metadata.json")
CHUNKS_JSONL_PATH = CHUNKS_DIR / "chunks.jsonl"

def load_json_file(path: Path) -> list:
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []

def calculate_structure_score(text: str, has_tamil: bool) -> int:
    score = 0
    
    # 1. Numbered sections check: lines starting with e.g. "1.", "2.", "10."
    numbered_lines = re.findall(r"^\s*\d+\.\s+", text, re.MULTILINE)
    if len(numbered_lines) > 3:
        score += 3
        
    # 2. Section markers: check occurrences of key Tamil Nadu gov structure words
    section_markers = [
        "ORDER:", "CIRCULAR:", "WHEREAS:", "THEREFORE:", 
        "PART", "SECTION", "ANNEXURE"
    ]
    marker_count = 0
    for marker in section_markers:
        marker_count += len(re.findall(rf"\b{marker}\b", text))
        
    if marker_count > 2:
        score += 3
        
    # 3. Paragraph breaks (double newlines) > 5
    paragraph_breaks = len(re.findall(r"\n\n", text))
    if paragraph_breaks > 5:
        score += 2
        
    # 4. Tamil bias toward paragraph chunking
    if has_tamil:
        score += 2
        
    return min(score, 10)

def split_strategy_b(words: list[str], window_size: int = 300, overlap: int = 37) -> list[str]:
    chunks = []
    i = 0
    while i < len(words):
        # Slice window
        chunk_words = words[i:i + window_size]
        if not chunk_words:
            break
        chunks.append(" ".join(chunk_words))
        
        # Advance index by window_size - overlap
        i += (window_size - overlap)
        # Prevent infinite loop if overlap >= window_size
        if window_size <= overlap:
            i += window_size
            
    return chunks

def split_strategy_a(text: str) -> list[str]:
    # Strategy A - Semantic/Section based splitting
    # Splitting markers: Numbers at start of line, ORDER:, CIRCULAR:, WHEREAS:, THEREFORE:, PART IV, etc.
    split_pattern = r"(?=(?:^\s*\d+\.\s+)|(?:\b(?:ORDER|CIRCULAR|WHEREAS|THEREFORE|PART|SECTION|ANNEXURE)\b:?))"
    raw_sections = re.split(split_pattern, text, flags=re.MULTILINE)
    
    refined_chunks = []
    current_chunk = []
    
    for section in raw_sections:
        section_stripped = section.strip()
        if not section_stripped:
            continue
            
        words = section_stripped.split()
        
        # Merge if < 150 words and we have a preceding chunk
        if len(words) < 150 and refined_chunks:
            # Add to the last chunk
            refined_chunks[-1] = refined_chunks[-1] + "\n\n" + section_stripped
        elif len(words) > 500:
            # Sub-chunk sections > 500 words using Strategy B
            sub_chunks = split_strategy_b(words, window_size=300, overlap=37)
            refined_chunks.extend(sub_chunks)
        else:
            refined_chunks.append(section_stripped)
            
    return refined_chunks

def split_strategy_c(text: str) -> list[str]:
    # Strategy C - Paragraph based splitting
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    
    refined_chunks = []
    temp_chunk = []
    temp_words_count = 0
    
    for para in paragraphs:
        para_words = para.split()
        
        # If single paragraph exceeds 500 words, split it via B
        if len(para_words) > 500:
            if temp_chunk:
                refined_chunks.append(" ".join(temp_chunk))
                temp_chunk = []
                temp_words_count = 0
            sub_chunks = split_strategy_b(para_words, window_size=300, overlap=37)
            refined_chunks.extend(sub_chunks)
            continue
            
        if temp_words_count + len(para_words) < 100:
            # Too short, accumulate paragraph
            temp_chunk.append(para)
            temp_words_count += len(para_words)
        else:
            # Commit previous chunk if it has text
            if temp_chunk:
                refined_chunks.append("\n\n".join(temp_chunk))
            # Start new chunk
            temp_chunk = [para]
            temp_words_count = len(para_words)
            
    if temp_chunk:
        refined_chunks.append("\n\n".join(temp_chunk))
        
    return refined_chunks

def main():
    manifest = load_json_file(MANIFEST_PATH)
    metadata = load_json_file(METADATA_PATH)
    
    if not manifest:
        print("Error: No manifest records. Clean data first.")
        return
        
    CHUNKS_DIR.mkdir(parents=True, exist_ok=True)
    
    metadata_map = {m["filename"]: m for m in metadata}
    strategy_counts = Counter()
    total_docs_processed = 0
    total_docs_skipped = 0
    total_chunks_created = 0
    tamil_chunk_count = 0
    
    # Open chunks.jsonl for writing
    with open(CHUNKS_JSONL_PATH, "w", encoding="utf-8") as jsonl_file:
        for entry in manifest:
            # Skip records flagged for review or failed status
            if entry["status"] == "failed" or entry.get("needs_review", False):
                total_docs_skipped += 1
                continue
                
            filename = entry["processed_filename"]
            cleaned_path = CLEANED_DIR / filename
            if not cleaned_path.exists():
                total_docs_skipped += 1
                continue
                
            with open(cleaned_path, "r", encoding="utf-8") as f:
                content = f.read()
                
            file_meta = metadata_map.get(filename, {})
            has_tamil = file_meta.get("has_tamil", False)
            
            # STEP A: Selection Score
            struct_score = calculate_structure_score(content, has_tamil)
            
            # Selection Strategy mapping
            if struct_score >= 6 and not has_tamil:
                strategy = "A"
                chunks_text = split_strategy_a(content)
            elif 3 <= struct_score <= 5:
                strategy = "B"
                words = content.split()
                chunks_text = split_strategy_b(words, window_size=300, overlap=37)
            else:
                strategy = "C"
                chunks_text = split_strategy_c(content)
                
            strategy_counts[strategy] += 1
            total_docs_processed += 1
            
            # Write Chunks metadata logs
            total_chunks = len(chunks_text)
            for idx, text in enumerate(chunks_text):
                chunk_word_count = len(text.split())
                chunk_id = str(uuid.uuid4())
                
                chunk_entry = {
                    "chunk_id": chunk_id,
                    "source_file": filename,
                    "original_file": entry["original_filename"],
                    "department": file_meta.get("department", "Unknown"),
                    "doc_type": file_meta.get("doc_type", "GENERAL"),
                    "date": file_meta.get("date", None),
                    "ref_number": file_meta.get("ref_number", None),
                    "has_tamil": has_tamil,
                    "chunk_strategy": strategy,
                    "chunk_index": idx + 1,
                    "total_chunks": total_chunks,
                    "word_count": chunk_word_count,
                    "text": text
                }
                
                # Check if this specific chunk contains Tamil characters
                if bool(re.search(r"[\u0b80-\u0bff]", text)):
                    tamil_chunk_count += 1
                    
                jsonl_file.write(json.dumps(chunk_entry, ensure_ascii=False) + "\n")
                total_chunks_created += 1
                
    # Summary report
    print(f"\n--- Chunking Execution Report ---")
    print(f"Documents processed successfully : {total_docs_processed}")
    print(f"Documents skipped (review/fail)  : {total_docs_skipped}")
    print(f"Total chunk vectors generated   : {total_chunks_created}")
    print(f"Tamil-content chunk vectors     : {tamil_chunk_count}")
    print("\nStrategy Distribution:")
    for strat, count in strategy_counts.items():
        print(f"  Strategy {strat}: {count} files")

if __name__ == "__main__":
    main()
