import os
import sys
import logging
import datetime
from pathlib import Path
from .celery_app import celery_app
from .job_store import store_job

# Import pipeline helpers
from pipeline.ingest import process_pdf
from pipeline.cleaner import clean_text_content, calculate_quality_score
from pipeline.metadata_extractor import extract_doc_type, extract_department, parse_date, extract_ref_number
from pipeline.chunker import calculate_structure_score, split_strategy_a, split_strategy_b, split_strategy_c
from pipeline.embed_and_store import get_collection_name

# Dynamic library imports inside tasks to avoid early loading
import fitz
import re
import uuid

logger = logging.getLogger("Workers")

PROCESSED_DIR = Path("data/processed")
CLEANED_DIR = Path("data/cleaned")

@celery_app.task(bind=True, max_retries=3, queue="embedding")
def ingest_pdf_task(self, pdf_path_str: str, filename: str, department: str):
    logger.info(f"Ingesting task started for {filename} (dept: {department})")
    pdf_path = Path(pdf_path_str)
    
    # Store initial state tracking
    job_data = {
        "job_id": self.request.id,
        "filename": filename,
        "department": department,
        "status": "PROGRESS",
        "progress_pct": 10,
        "step": "OCR",
        "error": None,
        "created_at": datetime.datetime.now().isoformat()
    }
    store_job(self.request.id, job_data)
    
    try:
        # STEP 1: Ingestion OCR (10%)
        self.update_state(state="PROGRESS", meta={"step": "OCR", "pct": 10})
        ingest_entry = process_pdf(pdf_path, department)
        if ingest_entry["status"] == "failed":
            raise ValueError(f"Ingestion extraction failed: {ingest_entry['error']}")
            
        processed_filename = ingest_entry["processed_filename"]
        processed_path = PROCESSED_DIR / processed_filename
        
        # STEP 2: Text Cleaning (30%)
        self.update_state(state="PROGRESS", meta={"step": "Cleaning", "pct": 30})
        job_data["progress_pct"] = 30
        job_data["step"] = "Cleaning"
        store_job(self.request.id, job_data)
        
        with open(processed_path, "r", encoding="utf-8") as f:
            raw_text = f.read()
            
        # Get metadata placeholder context for cleaner
        temp_meta = {}
        cleaned_text, tamil_errors = clean_text_content(raw_text, ingest_entry["source_type"], temp_meta)
        
        cleaned_path = CLEANED_DIR / processed_filename
        cleaned_path.parent.mkdir(parents=True, exist_ok=True)
        with open(cleaned_path, "w", encoding="utf-8") as f:
            f.write(cleaned_text)
            
        # STEP 3: Metadata Extraction (50%)
        self.update_state(state="PROGRESS", meta={"step": "Metadata", "pct": 50})
        job_data["progress_pct"] = 50
        job_data["step"] = "Metadata"
        store_job(self.request.id, job_data)
        
        first_chars = cleaned_text[:500]
        doc_type = extract_doc_type(first_chars, cleaned_text)
        detected_dept = extract_department(cleaned_text[:300], department)
        date = parse_date(cleaned_text)
        ref_number = extract_ref_number(cleaned_text)
        has_tamil = bool(re.search(r"[\u0b80-\u0bff]", cleaned_text))
        
        # Calculate quality score
        quality_score = calculate_quality_score(cleaned_text, ingest_entry["ocr_confidence"], ingest_entry["source_type"])
        needs_review = quality_score < 40.0
        
        # STEP 4: Smart Chunking (65%)
        self.update_state(state="PROGRESS", meta={"step": "Chunking", "pct": 65})
        job_data["progress_pct"] = 65
        job_data["step"] = "Chunking"
        store_job(self.request.id, job_data)
        
        struct_score = calculate_structure_score(cleaned_text, has_tamil)
        if struct_score >= 6 and not has_tamil:
            strategy = "A"
            chunks_text = split_strategy_a(cleaned_text)
        elif 3 <= struct_score <= 5:
            strategy = "B"
            chunks_text = split_strategy_b(cleaned_text.split(), window_size=300, overlap=37)
        else:
            strategy = "C"
            chunks_text = split_strategy_c(cleaned_text)
            
        # STEP 5: Embeddings Vector Store Upload (80%)
        self.update_state(state="PROGRESS", meta={"step": "Embedding", "pct": 80})
        job_data["progress_pct"] = 80
        job_data["step"] = "Embedding"
        store_job(self.request.id, job_data)
        
        # Load embedding model dynamic context
        from sentence_transformers import SentenceTransformer
        from qdrant_client import QdrantClient
        from qdrant_client.http import models
        
        device = "cpu" if os.environ.get("CUDA_VISIBLE_DEVICES", "") == "" else "cuda"
        model = SentenceTransformer("BAAI/bge-m3", device=device)
        qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
        qdrant_key = os.getenv("QDRANT_API_KEY", "")
        client = QdrantClient(url=qdrant_url, api_key=qdrant_key)
        
        collection_name = get_collection_name(detected_dept)
        
        # Ensure collection exists
        try:
            client.get_collection(collection_name)
        except Exception:
            client.create_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(size=1024, distance=models.Distance.COSINE)
            )
            
        points = []
        for idx, text in enumerate(chunks_text):
            chunk_vector = model.encode([text])[0].tolist()
            chunk_id = str(uuid.uuid4())
            
            payload = {
                "chunk_id": chunk_id,
                "source_file": processed_filename,
                "original_file": filename,
                "doc_type": doc_type,
                "department": detected_dept,
                "date": date,
                "ref_number": ref_number,
                "has_tamil": has_tamil,
                "chunk_index": idx + 1,
                "total_chunks": len(chunks_text),
                "text": text
            }
            
            points.append(
                models.PointStruct(id=chunk_id, vector=chunk_vector, payload=payload)
            )
            
        if points:
            client.upsert(collection_name=collection_name, points=points)
            
        # STEP 6: Ingestion task completed (100%)
        self.update_state(state="SUCCESS")
        job_data["progress_pct"] = 100
        job_data["status"] = "SUCCESS"
        job_data["step"] = "Done"
        job_data["result"] = {
            "filename": filename,
            "department": detected_dept,
            "chunks_created": len(chunks_text),
            "quality_score": quality_score,
            "doc_type": doc_type,
            "date": date
        }
        store_job(self.request.id, job_data)
        
        return job_data["result"]
        
    except Exception as exc:
        logger.error(f"Ingestion Task failed on file {filename}: {exc}")
        job_data["status"] = "FAILURE"
        job_data["error"] = str(exc)
        store_job(self.request.id, job_data)
        
        # Exponential backoff countdown retry
        try:
            self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
        except Exception as retry_exc:
            # Re-raised if retries exceeded
            raise retry_exc
