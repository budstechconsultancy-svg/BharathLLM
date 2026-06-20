import os
import re
import json
import random
from pathlib import Path
from collections import Counter
import nltk
from nltk.corpus import stopwords

# Download required NLTK data — safe to run multiple times (idempotent)
nltk.download('stopwords', quiet=True)
nltk.download('punkt', quiet=True)
nltk.download('averaged_perceptron_tagger', quiet=True)

CHUNKS_JSONL_PATH = Path("data/chunks/chunks.jsonl")
TRAINING_DIR = Path("data/training")
TRAIN_JSON_PATH = TRAINING_DIR / "train.json"
VAL_JSON_PATH = TRAINING_DIR / "val.json"
MANIFEST_PATH = TRAINING_DIR / "training_manifest.json"

try:
    nltk_english_stopwords = set(stopwords.words("english"))
except Exception:
    nltk.download("stopwords", quiet=True)
    nltk_english_stopwords = set(stopwords.words("english"))

# Load stopwords from json
indian_stopwords_path = Path("pipeline/assets/indian_stopwords.json")
all_stopwords = {}
if indian_stopwords_path.exists():
    try:
        with open(indian_stopwords_path, "r", encoding="utf-8") as f:
            all_stopwords = json.load(f)
    except Exception as e:
        print(f"Warning: Failed to load indian_stopwords.json: {e}")

primary = os.getenv("PRIMARY_LANGUAGES", "hi,en").split(",")
active_stopwords = set()
for lang in primary:
    active_stopwords.update(all_stopwords.get(lang, []))
active_stopwords.update(nltk_english_stopwords)

print(f"Loaded {len(active_stopwords)} active stopwords for target languages {primary}")

def extract_topic(text: str, dept: str, doc_type: str) -> str:
    # Remove alphanumeric boundaries and isolate lowercase words
    words = re.findall(r"\b\w+\b", text.lower())
    
    # Filter using active stopwords
    filtered = []
    for w in words:
        if w not in active_stopwords:
            # Check length to filter noise
            if len(w) > 2:
                filtered.append(w)
                
    if not filtered:
        return f"{dept} {doc_type}".strip()
        
    # Find top 3 most common words
    counts = Counter(filtered)
    top_3 = [word for word, _ in counts.most_common(3)]
    return " ".join(top_3)

def split_into_sentences(text: str) -> list[str]:
    # Regex split on English sentences and Tamil sentence ender
    sentences = re.split(r"(?<=[.!?।])\s+", text)
    return [s.strip() for s in sentences if s.strip()]

def validate_pair(pair: dict) -> tuple[bool, str | None]:
    instruction = pair["instruction"]
    output = pair["output"]
    input_text = pair.get("input", "")
    
    # Check length
    if not (10 <= len(instruction) <= 300):
        return False, "instruction_length"
    if not (50 <= len(output) <= 2000):
        return False, "output_length"
        
    # Check template replication
    if output == input_text and input_text:
        return False, "output_equals_input"
        
    # Reject placeholders
    placeholders = ["[topic]", "[chunk text]", "[department]", "[ref_number]", "None", "null"]
    for ph in placeholders:
        if ph in output or ph in instruction:
            return False, "placeholder_present"
            
    # Check regex placeholder brackets
    if re.search(r"\[.*?\]", output):
        return False, "regex_placeholder_brackets"
        
    return True, None

def generate_pairs(chunk: dict, topic: str) -> list[dict]:
    pairs = []
    text = chunk["text"]
    dept = chunk["department"]
    doc_type = chunk["doc_type"]
    ref_number = chunk["ref_number"]
    date = chunk["date"]
    
    # Template A - Direct Q&A (only if ref and date are valid)
    if ref_number and date and str(ref_number).lower() != "none" and str(date).lower() != "none":
        pairs.append({
            "instruction": f"What does {ref_number} {doc_type} from {dept} Department dated {date} state about {topic}?",
            "input": "",
            "output": text
        })
        
    # Template B - Summarisation
    sentences = split_into_sentences(text)
    # Get first 3 sentences
    summary_sentences = sentences[:3]
    if len(summary_sentences) >= 1:
        summary_output = " ".join(summary_sentences)
        pairs.append({
            "instruction": f"Summarise the key points from this BharatLLM Government {doc_type} issued by {dept} Department:",
            "input": text,
            "output": summary_output
        })
        
    # Template C - Department Lookup
    pairs.append({
        "instruction": f"Retrieve Tamil Nadu government orders and circulars from {dept} Department related to {topic}:",
        "input": "",
        "output": text
    })
    
    return pairs

def main():
    if not CHUNKS_JSONL_PATH.exists():
        print(f"Error: Chunks file '{CHUNKS_JSONL_PATH}' not found. Run chunking first.")
        return
        
    TRAINING_DIR.mkdir(parents=True, exist_ok=True)
    
    chunks = []
    with open(CHUNKS_JSONL_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                chunks.append(json.loads(line))
                
    print(f"Loaded {len(chunks)} chunks from chunks.jsonl")
    
    filtered_chunks_count = 0
    total_generated = 0
    rejected_reasons = Counter()
    valid_pairs = []
    
    for chunk in chunks:
        # Discard small chunks
        if chunk["word_count"] < 80:
            continue
            
        filtered_chunks_count += 1
        
        # Topic extraction
        topic = extract_topic(chunk["text"], chunk["department"], chunk["doc_type"])
        
        # Generate training pairs
        pairs = generate_pairs(chunk, topic)
        
        # Validate pairs
        for pair in pairs:
            total_generated += 1
            is_valid, reason = validate_pair(pair)
            if is_valid:
                valid_pairs.append(pair)
            else:
                rejected_reasons[reason] += 1
                
    # Shuffle and Split
    random.seed(42)
    random.shuffle(valid_pairs)
    
    split_idx = int(0.9 * len(valid_pairs))
    train_set = valid_pairs[:split_idx]
    val_set = valid_pairs[split_idx:]
    
    # Save datasets
    with open(TRAIN_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(train_set, f, indent=2, ensure_ascii=False)
        
    with open(VAL_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(val_set, f, indent=2, ensure_ascii=False)
        
    # Write manifest
    avg_out_len = 0
    if valid_pairs:
        avg_out_len = sum(len(p["output"]) for p in valid_pairs) / len(valid_pairs)
        
    manifest = {
        "total_chunks": len(chunks),
        "chunks_with_enough_words": filtered_chunks_count,
        "pairs_generated": total_generated,
        "pairs_rejected": sum(rejected_reasons.values()),
        "train_count": len(train_set),
        "val_count": len(val_set),
        "avg_output_length": round(avg_out_len, 2),
        "generated_at": datetime.datetime.now().isoformat() if "datetime" in globals() else "2026-06-19"
    }
    
    import datetime
    manifest["generated_at"] = datetime.datetime.now().isoformat()
    
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
        
    print("\n--- Training Dataset Builder Report ---")
    print(f"Total Chunks Processed   : {len(chunks)}")
    print(f"Chunks word count >= 80  : {filtered_chunks_count}")
    print(f"Pairs Generated          : {total_generated}")
    print(f"Pairs Accepted (Total)   : {len(valid_pairs)}")
    print(f"  - Train Set Size       : {len(train_set)}")
    print(f"  - Validation Set Size  : {len(val_set)}")
    print(f"Avg Output Length (chars): {manifest['avg_output_length']}")
    
    if rejected_reasons:
        print("\nRejection Reasons breakdown:")
        for reason, count in rejected_reasons.items():
            print(f"  - {reason:<25}: {count}")

if __name__ == "__main__":
    main()
