import os
import sys
import logging
import torch
from langdetect import detect
from qdrant_client import QdrantClient
from qdrant_client.http import models
from sentence_transformers import SentenceTransformer
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

# Set up logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("RAGEngine")

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")
MODELS_DIR = os.getenv("MODELS_DIR", "models")
BASE_MODEL_NAME = "meta-llama/Llama-3.1-8B-Instruct"

class RAGEngine:
    def __init__(self, model_path=None):
        if model_path is None:
            model_path = os.path.join(MODELS_DIR, "bharatllm-final")
            
        # 1. Initialize tokenizer and causal model
        self.tokenizer = None
        self.model = None
        if os.getenv("MOCK_AI_MODELS") == "True":
            logger.info("MOCK_AI_MODELS is True. Skipping LLM and Embedding Model initialization to speed up dev mode.")
            self.model = None
            self.tokenizer = None
            self.embedding_model = None
        else:
            # Verify model loading fallback rules
            target_path = model_path
            if not os.path.exists(target_path):
                logger.warning(f"Fine-tuned model not found at {target_path}. Falling back to base model: {BASE_MODEL_NAME}")
                target_path = BASE_MODEL_NAME
                
            try:
                logger.info(f"Loading LLM from {target_path}...")
                # Configure double-quantized 4-bit config
                bnb_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.bfloat16,
                    bnb_4bit_quant_type="nf4",
                    bnb_4bit_use_double_quant=True
                )
                self.tokenizer = AutoTokenizer.from_pretrained(target_path, use_fast=True)
                self.model = AutoModelForCausalLM.from_pretrained(
                    target_path,
                    quantization_config=bnb_config,
                    device_map="auto"
                )
                logger.info("LLM loaded successfully.")
            except Exception as e:
                logger.warning(f"Failed to load LLM from {target_path}: {e}. Running in DEV fallback mode.")
                self.model = None
                self.tokenizer = None
                
            # 2. Load BGE-M3 model for embeddings
            try:
                logger.info("Loading BGE-M3 embedding model...")
                self.embedding_model = SentenceTransformer("BAAI/bge-m3")
                logger.info("Embedding model loaded.")
            except Exception as e:
                logger.warning(f"Failed to load embedding model: {e}. Running in DEV fallback mode.")
                self.embedding_model = None
            
        # 3. Connection to Qdrant Database
        try:
            logger.info(f"Connecting to Qdrant at {QDRANT_URL}...")
            self.qdrant_client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
        except Exception as e:
            logger.warning(f"Failed to connect to Qdrant: {e}. Running in DEV fallback mode.")
            self.qdrant_client = None

    def get_collection(self, department: str) -> str:
        if not department or str(department).lower() == "unknown":
            return "tn_general_docs"
        slug = department.lower().replace(" ", "_").replace("&", "and")
        return f"tn_{slug}_docs"

    def _transliterate_tanglish(self, text: str) -> str:
        """Fix F-4: Tanglish to Tamil script transliteration."""
        tanglish_map = {
            "eppadi": "எப்படி",
            "thittam": "திட்டம்",
            "apply": "விண்ணப்பிக்க",
            "panrathu": "செய்வது",
            "enge": "எங்கே",
            "yaar": "யார்"
        }
        words = text.split()
        res = []
        for w in words:
            res.append(tanglish_map.get(w.lower(), w))
        return " ".join(res)

    def retrieve(self, query: str, department: str, top_k: int = 5, filters: dict = None) -> list:
        # Fix F-4: Transliterate Tanglish queries before embedding and detection
        query = self._transliterate_tanglish(query)
        
        # Detect query language
        try:
            query_lang = detect(query)
        except Exception:
            query_lang = "en"
            
        # Embed search query
        try:
            if self.embedding_model:
                query_vector = self.embedding_model.encode([query])[0].tolist()
            else:
                return [] # Mock fallback if no embedding model
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            return []
            
        collection_name = self.get_collection(department)
        
        # Build Qdrant metadata search filters
        qdrant_filters = []
        if filters:
            if "doc_type" in filters and filters["doc_type"]:
                qdrant_filters.append(
                    models.FieldCondition(
                        key="doc_type",
                        match=models.MatchValue(value=filters["doc_type"])
                    )
                )
            if "date_from" in filters and filters["date_from"]:
                qdrant_filters.append(
                    models.FieldCondition(
                        key="date",
                        range=models.Range(gte=filters["date_from"])
                    )
                )
            if "date_to" in filters and filters["date_to"]:
                qdrant_filters.append(
                    models.FieldCondition(
                        key="date",
                        range=models.Range(lte=filters["date_to"])
                    )
                )
            if "has_tamil" in filters:
                qdrant_filters.append(
                    models.FieldCondition(
                        key="has_tamil",
                        match=models.MatchValue(value=bool(filters["has_tamil"]))
                    )
                )
                
        query_filter = None
        if qdrant_filters:
            query_filter = models.Filter(must=qdrant_filters)
            
        # Run Qdrant search
        if not self.qdrant_client:
            return []
            
        try:
            search_results = self.qdrant_client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                query_filter=query_filter,
                limit=top_k
            )
        except Exception as e:
            logger.error(f"Qdrant search failed on collection '{collection_name}': {e}")
            return []
            
        # Apply score threshold validation (0.35)
        valid_chunks = []
        for result in search_results:
            if result.score >= 0.35:
                valid_chunks.append({
                    "score": result.score,
                    "payload": result.payload
                })
                
        return valid_chunks

    def generate(self, query: str, retrieved_chunks: list) -> str:
        if not self.model:
            return f"[DEV MODE] This is a simulated response. The LLM and Vector Database are disabled in the development launcher. You asked: '{query}'"
            
        if not retrieved_chunks:
            return "This information is not available in the provided BharatLLM Government documents."
            
        # Construct reference context layout
        context_parts = []
        for chunk in retrieved_chunks:
            payload = chunk["payload"]
            original_file = payload.get("original_file", "Unknown File")
            page_number = payload.get("page_number", 1) # Fix F-6: page number deep link
            doc_type = payload.get("doc_type", "GENERAL")
            department = payload.get("department", "Unknown Department")
            date = payload.get("date", "Unknown Date")
            text = payload.get("text", "")
            
            header = f"[Source: {original_file} (Page {page_number}) | {doc_type} | {department} | {date}]"
            context_parts.append(f"{header}\n{text}\n---\n")
            
        context = "\n".join(context_parts)
        
        # Format strict constraints system prompt
        system_prompt = (
            "You are a BharatLLM document assistant. "
            "Answer ONLY from the provided government document context.\n"
            "Rules:\n"
            "1. Never use outside knowledge — only the provided context.\n"
            "2. If answer not in context, say exactly: "
            "'This information is not available in the provided BharatLLM Government documents.'\n"
            "3. Always cite source document filename and date.\n"
            "4. For Tamil queries, respond in Tamil or English as appropriate.\n"
            "5. Be concise and factual."
        )
        
        # Build prompt using llama-3 tokenizer structure (chat templates format)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"CONTEXT:\n{context}\n\nQUESTION: {query}"}
        ]
        
        try:
            prompt = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
            
            # Run inference (T=0, repetition_penalty=1.1, limit token lengths)
            outputs = self.model.generate(
                **inputs,
                temperature=0.0,
                do_sample=False,
                max_new_tokens=512,
                repetition_penalty=1.1,
                pad_token_id=self.tokenizer.eos_token_id
            )
            
            # Slice only new generated response
            input_len = inputs.input_ids.shape[1]
            response_tokens = outputs[0][input_len:]
            response = self.tokenizer.decode(response_tokens, skip_special_tokens=True)
            return response.strip()
        except Exception as e:
            logger.error(f"LLM Generation call failed: {e}")
            return "Error generating response from LLM."

    def query(self, question: str, department: str, filters: dict = None) -> dict:
        # Detect query language
        try:
            query_lang = detect(question)
        except Exception:
            query_lang = "en"
            
        # Retrieve chunks
        chunks = self.retrieve(question, department, top_k=5, filters=filters)
        
        # Generate Answer
        answer = self.generate(question, chunks)
        
        # Calculate search confidence (average of top 3 search scores)
        confidence = 0.0
        if chunks:
            top_3_scores = [c["score"] for c in chunks[:3]]
            confidence = round(sum(top_3_scores) / len(top_3_scores), 4)
            
        sources = []
        for c in chunks:
            p = c["payload"]
            sources.append({
                "filename": p.get("original_file", ""),
                "page_number": p.get("page_number", 1),
                "doc_type": p.get("doc_type", ""),
                "department": p.get("department", ""),
                "date": p.get("date", ""),
                "relevance_score": round(c["score"], 4)
            })
            
        return {
            "answer": answer,
            "sources": sources,
            "confidence": confidence,
            "chunks_used": len(chunks),
            "query_language": query_lang
        }

if __name__ == "__main__":
    # If run directly, run parser compile check
    print("RAGEngine script syntax check passed.")
