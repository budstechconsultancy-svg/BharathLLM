import os
import re
import json
import sys
from pathlib import Path
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.exceptions import UnexpectedResponse
from sentence_transformers import SentenceTransformer

# Load configurations from environment or default
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")
CHUNKS_JSONL_PATH = Path("data/chunks/chunks.jsonl")

# Canonical departments listing
DEPARTMENTS = [
    "School Education", "Health", "Finance", "Revenue", "PWD", 
    "Agriculture", "HR&CE", "Social Welfare", "Municipal Admin", 
    "Rural Development", "Industries", "IT", "Transport", "Energy",
    "General" # fallback tag
]

def get_collection_name(dept: str) -> str:
    # canonical slug format
    slug = dept.lower().replace(" ", "_").replace("&", "and")
    return f"tn_{slug}_docs"

def main():
    # 1. Verification of the embedding model
    print("Loading BGE-M3 embedding model...")
    try:
        model = SentenceTransformer("BAAI/bge-m3")
        # Validate dimensionality
        test_vector = model.encode(["Tamil Nadu அரசு circular test"])
        assert test_vector.shape[-1] == 1024, "BGE-M3 must return 1024-dim vectors"
        print("Embedding model verified ✓")
    except Exception as e:
        print(f"CRITICAL ERROR loading BGE-M3 model: {e}")
        sys.exit(1)
        
    # 2. Check for chunks.jsonl
    if not CHUNKS_JSONL_PATH.exists():
        print(f"Chunks file missing: {CHUNKS_JSONL_PATH}. Skipping Qdrant upload initialization.")
        print("You can run this script later when documents are chunked.")
        sys.exit(0)
        
    # 3. Connection to Qdrant Vector DB
    print(f"Connecting to Qdrant at {QDRANT_URL}...")
    try:
        client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY, timeout=10.0)
        # Test connection by listing collections
        client.get_collections()
        print("Successfully connected to Qdrant Database.")
    except Exception as e:
        print(f"CRITICAL ERROR connecting to Qdrant: {e}")
        print("Ensure Qdrant is running or update QDRANT_URL in .env.")
        sys.exit(1)
        
    # 4. Group chunks by department
    print("Reading chunk items...")
    chunks_by_dept = {}
    with open(CHUNKS_JSONL_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                chunk = json.loads(line)
                dept = chunk.get("department", "General")
                # Ensure department matches canonical names
                canonical_dept = "General"
                for cd in DEPARTMENTS:
                    if cd.lower() == dept.lower():
                        canonical_dept = cd
                        break
                
                collection_name = get_collection_name(canonical_dept)
                if collection_name not in chunks_by_dept:
                    chunks_by_dept[collection_name] = []
                chunks_by_dept[collection_name].append(chunk)
                
    # 5. Initialize Collections & Indexes + Incremental Update Check
    for collection_name, dept_chunks in chunks_by_dept.items():
        print(f"\nProcessing collection: {collection_name} ({len(dept_chunks)} total chunks)")
        
        # Check if collection exists
        try:
            client.get_collection(collection_name)
            print(f"  Collection '{collection_name}' already exists.")
        except (UnexpectedResponse, ValueError):
            print(f"  Creating collection '{collection_name}'...")
            client.create_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(
                    size=1024,
                    distance=models.Distance.COSINE
                )
            )
            # Create payload indexes for faster queries
            index_fields = ["department", "doc_type", "date", "has_tamil", "ref_number"]
            for field in index_fields:
                client.create_payload_index(
                    collection_name=collection_name,
                    field_name=field,
                    field_schema=models.PayloadSchemaType.KEYWORD if field != "has_tamil" else models.PayloadSchemaType.BOOL
                )
            print(f"  Indexes generated for collection '{collection_name}'.")

        # Scroll to find existing stored chunk UUIDs
        existing_ids = set()
        try:
            scroll_results = client.scroll(
                collection_name=collection_name,
                limit=10000,
                with_payload=False,
                with_vectors=False
            )
            points = scroll_results[0]
            existing_ids = {p.id for p in points}
            print(f"  Found {len(existing_ids)} existing vectors in collection.")
        except Exception as e:
            print(f"  Warning: Scroll query failed: {e}. Defaulting to full upload.")
            
        # Filter chunks that need embedding
        chunks_to_embed = [c for c in dept_chunks if c["chunk_id"] not in existing_ids]
        print(f"  New vectors to ingest: {len(chunks_to_embed)}")
        
        if not chunks_to_embed:
            print(f"  All chunks already exists in collection {collection_name}. Skipping.")
            continue
            
        # Upload loop
        batch_size = 32
        upsert_batch = []
        for i in range(0, len(chunks_to_embed), batch_size):
            batch = chunks_to_embed[i:i+batch_size]
            batch_texts = [c["text"] for c in batch]
            
            # Embed batch
            try:
                embeddings = model.encode(batch_texts, batch_size=batch_size, show_progress_bar=False)
            except Exception as e:
                print(f"  Error generating embeddings for batch {i//batch_size}: {e}")
                continue
                
            for idx, chunk in enumerate(batch):
                payload = {
                    "chunk_id": chunk["chunk_id"],
                    "source_file": chunk["source_file"],
                    "original_file": chunk["original_file"],
                    "doc_type": chunk["doc_type"],
                    "department": chunk["department"],
                    "date": chunk["date"],
                    "ref_number": chunk["ref_number"],
                    "has_tamil": chunk["has_tamil"],
                    "chunk_index": chunk["chunk_index"],
                    "total_chunks": chunk["total_chunks"],
                    "text": chunk["text"]
                }
                
                point = models.PointStruct(
                    id=chunk["chunk_id"],
                    vector=embeddings[idx].tolist(),
                    payload=payload
                )
                upsert_batch.append(point)
                
                # Upsert to database in chunks of 1000
                if len(upsert_batch) >= 1000:
                    client.upsert(
                        collection_name=collection_name,
                        points=upsert_batch
                    )
                    upsert_batch = []
                    
        # Upsert remaining
        if upsert_batch:
            client.upsert(
                collection_name=collection_name,
                points=upsert_batch
            )
            
        print(f"  Completed upsert for {collection_name}.")
        
        # 6. TAMIL RETRIEVAL VALIDATION
        has_tamil_chunks = any(c.get("has_tamil", False) for c in dept_chunks)
        if has_tamil_chunks:
            print(f"  Running Tamil retrieval validation on '{collection_name}'...")
            try:
                test_query = "தமிழ்நாடு அரசு திட்டம்"
                test_vector = model.encode([test_query])[0].tolist()
                
                search_results = client.search(
                    collection_name=collection_name,
                    query_vector=test_vector,
                    limit=3
                )
                
                print(f"  Top 3 retrieval matches for query '{test_query}':")
                for sr in search_results:
                    txt_preview = sr.payload.get("text", "")[:120].replace("\n", " ")
                    print(f"    - [Score {sr.score:.3f}] {txt_preview}...")
            except Exception as e:
                print(f"  Warning: Tamil validation check failed: {e}")
                
    print("\nVector Ingestion Run Complete ✓")

if __name__ == "__main__":
    main()
