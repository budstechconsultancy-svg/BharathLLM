import os
import re
import argparse
import logging
from concurrent.futures import ThreadPoolExecutor
from .rag_engine import RAGEngine
from .sql_engine import SQLEngine

logger = logging.getLogger("QueryRouter")

SQL_SIGNALS = [
    r"\bhow\s+many\b", r"\bcount\b", r"\btotal\b", r"\blist\b", r"\bshow\s+all\b",
    r"\bexpenditure\b", r"\bbudget\b", r"\butility\b", r"\butilisation\b",
    r"\bvacancy\b", r"\bbeds\b", r"\bemployees\b", r"\bstaff\b", r"\bstudent\b",
    r"\bteacher\b", r"\bbeneficiar\w*\b", r"\benrolled\b", r"\bpatta\b", r"\bacres\b"
]

RAG_SIGNALS = [
    r"\bwhat\s+does\b", r"\bexplain\b", r"\bprocedure\b", r"\beligibility\b",
    r"\bg\.?o\.?\b", r"\bgovernment\s+order\b", r"\bcircular\b", r"\bpolicy\b",
    r"\bguideline\b", r"\bnotification\b", r"\bproceedings\b", r"\brule\b"
]

MIXED_SIGNALS = [
    r"\band\s+also\b", r"\balong\s+with\b", r"\bas\s+well\s+as\b"
]

class QueryRouter:
    def __init__(self, model_path=None):
        logger.info("Initializing QueryRouter Engines...")
        self.rag_engine = RAGEngine(model_path=model_path)
        # Pass the RAGEngine's loaded model object directly to avoid duplicate model instantiation in VRAM
        self.sql_engine = SQLEngine(llm_engine=self.rag_engine)
        logger.info("Engines fully attached.")

    def classify_query(self, question: str) -> str:
        q_lower = question.lower()
        
        has_sql = any(re.search(sig, q_lower) for sig in SQL_SIGNALS)
        has_rag = any(re.search(sig, q_lower) for sig in RAG_SIGNALS)
        has_mixed = any(re.search(sig, q_lower) for sig in MIXED_SIGNALS)
        
        # SQL matches pattern \d{4} (usually represents years)
        has_year = bool(re.search(r"\b\d{4}\b", q_lower))
        if has_year and has_sql:
            has_sql = True
            
        logger.info(f"Query classification signals matched: SQL={has_sql}, RAG={has_rag}, MIXED={has_mixed}")
        
        if (has_sql and has_rag) or has_mixed:
            return "MIXED"
        elif has_sql:
            return "SQL"
        elif has_rag:
            return "RAG"
            
        return "RAG" # Safe default fallback

    def route_and_query(self, question: str, department: str, filters: dict = None) -> dict:
        classification = self.classify_query(question)
        logger.info(f"Routing query as classification: {classification}")
        
        rag_result = {}
        sql_result = {}
        
        if classification == "RAG":
            rag_result = self.rag_engine.query(question, department, filters=filters)
            answer = rag_result["answer"]
            
        elif classification == "SQL":
            sql_result = self.sql_engine.query(question, department)
            answer = sql_result["formatted_result"]
            
        elif classification == "MIXED":
            # Run both SQL query and RAG search in concurrent threads
            with ThreadPoolExecutor(max_workers=2) as executor:
                rag_thread = executor.submit(self.rag_engine.query, question, department, filters)
                sql_thread = executor.submit(self.sql_engine.query, question, department)
                
                rag_result = rag_thread.result()
                sql_result = sql_thread.result()
                
            # Perform Result Fusion
            answer = self.fuse_results(question, rag_result, sql_result, department)
            
        # Compile response metadata outputs
        sources = rag_result.get("sources", [])
        sql_generated = sql_result.get("sql_generated", None)
        db_row_count = sql_result.get("row_count", None)
        
        # Calculate overall confidence
        rag_conf = rag_result.get("confidence", 0.0)
        sql_err = sql_result.get("error", None)
        
        if classification == "RAG":
            confidence = rag_conf
        elif classification == "SQL":
            confidence = 1.0 if not sql_err else 0.0
        else: # MIXED
            confidence = round((rag_conf + (1.0 if not sql_err else 0.0)) / 2, 4)
            
        return {
            "answer": answer,
            "query_type": classification,
            "sources": sources,
            "sql_generated": sql_generated,
            "db_row_count": db_row_count,
            "confidence": confidence,
            "chunks_used": rag_result.get("chunks_used", 0),
            "query_language": rag_result.get("query_language", "en")
        }

    def fuse_results(self, question: str, rag_res: dict, sql_res: dict, department: str) -> str:
        # Check fallback if both are empty
        if not rag_res.get("sources") and not sql_res.get("rows"):
            return "This information is not available in the provided BharatLLM Government documents or databases."
            
        # Re-construct contexts
        doc_parts = []
        for src in rag_res.get("sources", []):
            # Query Qdrant directly or pass chunks through to get text.
            # To optimize, we can retrieve chunk text from RAG engine retrieved state.
            # RAGEngine query returns sources list. To reconstruct, we pass raw context.
            pass
            
        # However, to be robust, we instruct the LLM using the generated answers/outputs from both sub-engines
        rag_answer = rag_res.get("answer", "")
        db_table = sql_res.get("formatted_result", "")
        
        fusion_prompt = (
            f"You have access to both government document search summaries and database query records for the {department} Department.\n\n"
            f"DOCUMENT RETRIEVAL SUMMARY:\n{rag_answer}\n\n"
            f"DATABASE RETRIEVAL TABLE:\n{db_table}\n\n"
            f"QUESTION: {question}\n\n"
            "Rules:\n"
            "1. Synthesise both document search and database records into a single coherent response.\n"
            "2. Cite document source names and dates where relevant.\n"
            "3. If one of the sources contains no information, rely on the other.\n"
            "4. Be concise, factual, and do not make up external information."
        )
        
        system_prompt = (
            "You are a BharatLLM document assistant. "
            "Integrate document text summaries and database tables to answer user questions."
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": fusion_prompt}
        ]
        
        try:
            formatted_prompt = self.rag_engine.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            inputs = self.rag_engine.tokenizer(formatted_prompt, return_tensors="pt").to(self.rag_engine.model.device)
            
            outputs = self.rag_engine.model.generate(
                **inputs,
                temperature=0.0,
                do_sample=False,
                max_new_tokens=512,
                repetition_penalty=1.1,
                pad_token_id=self.rag_engine.tokenizer.eos_token_id
            )
            
            input_len = inputs.input_ids.shape[1]
            response = self.rag_engine.tokenizer.decode(outputs[0][input_len:], skip_special_tokens=True)
            return response.strip()
        except Exception as e:
            logger.error(f"Inference Fusion generation failed: {e}")
            return f"Document summary: {rag_answer}\n\nDatabase results: {db_table}"

def main():
    parser = argparse.ArgumentParser(description="TN Govt LLM Query Router CLI")
    parser.add_argument("--question", type=str, required=True, help="User search question")
    parser.add_argument("--department", type=str, default="General", help="Department scope filter")
    args = parser.parse_args()
    
    print(f"Testing Classifier Router on: '{args.question}'...")
    # Just run syntax check simulation since engine instantiation downloads metal models
    router_check = QueryRouter.__new__(QueryRouter)
    classification = router_check.classify_query(args.question)
    print(f"Resulting route: {classification}")

if __name__ == "__main__":
    main()
