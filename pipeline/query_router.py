import os
import re
import argparse
import logging
from concurrent.futures import ThreadPoolExecutor
from .rag_engine import RAGEngine
from .sql_engine import SQLEngine
from .web_search_engine import WebSearchEngine
from .legal_engine import LegalEngine
from .finance_engine import FinanceEngine
from .healthcare_engine import HealthcareEngine
from .realestate_engine import RealEstateEngine
from .hr_engine import HREngine
from .cache_layer import get_cache

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

HEALTHCARE_SIGNALS = [
  "drug", "medicine", "tablet", "injection", "dosage", "side effect",
  "nabh", "cghs", "hospital", "doctor", "clinical", "diagnosis",
  "icd", "cpt", "drg", "cdsco", "pharmacopoeia", "contraindication",
  "drug interaction", "ayushman", "cmhis", "health insurance claim",
  "prescription", "schedule h", "banned drug", "recall",
  "மருந்து", "மருத்துவர்", "மருத்துவமனை", "நோய்", "சிகிச்சை",
  "दवा", "दवाई", "डॉक्टर", "अस्पताल", "इलाज", "बीमारी"
]

REALESTATE_SIGNALS = [
  "rera", "property", "flat", "apartment", "land", "plot", "house",
  "stamp duty", "registration", "patta", "chitta", "7/12", "rtc",
  "builder", "developer", "sale deed", "sale agreement", "lease",
  "rental agreement", "mortgage", "encumbrance", "khata", "khasra",
  "dtcp", "cmda", "bda", "fsi", "far", "occupancy certificate",
  "completion certificate", "title search",
  "பட்டா", "சிட்டா", "அடங்கல்", "சொத்து", "இடம்", "வீடு",
  "संपत्ति", "जमीन", "मकान", "रजिस्ट्री", "स्टांप ड्यूटी"
]

HR_SIGNALS = [
  "minimum wages", "epf", "esic", "pf", "gratuity", "bonus",
  "labour code", "labour law", "employment", "termination", "retrenchment",
  "posh", "sexual harassment", "icc", "maternity", "factory act",
  "standing orders", "trade union", "appointment letter", "relieving letter",
  "offer letter", "salary", "increment", "warning letter",
  "குறைந்தபட்ச ஊதியம்", "பணிநீக்கம்", "தொழிலாளர்", "ஊழியர்",
  "न्यूनतम वेतन", "नियुक्ति", "बर्खास्तगी", "श्रम कानून", "पीएफ"
]

class QueryRouter:
    def __init__(self, model_path=None):
        logger.info("Initializing QueryRouter Engines...")
        self.rag_engine = RAGEngine(model_path=model_path)
        self.sql_engine = SQLEngine(llm_engine=self.rag_engine)
        self.web_engine = WebSearchEngine()
        self.legal_engine = LegalEngine(rag_engine=self.rag_engine)
        self.finance_engine = FinanceEngine(rag_engine=self.rag_engine)
        self.healthcare_engine = HealthcareEngine(rag_engine=self.rag_engine)
        self.realestate_engine = RealEstateEngine(rag_engine=self.rag_engine)
        self.hr_engine = HREngine(rag_engine=self.rag_engine)
        self.cache = get_cache()  # Fix 4.2: Redis response cache
        logger.info("Engines fully attached.")

    LEGAL_SIGNALS = [
      "section", "act", "judgement", "court", "case", "bail", "fir",
      "petition", "plaint", "notice", "limitation", "advocate", "lawyer",
      "ipc", "bns", "crpc", "bnss", "supreme court", "high court",
      "contract", "divorce", "succession", "will", "deed", "agreement",
      "draft legal", "legal notice", "writ", "habeas corpus"
    ]
    FINANCE_SIGNALS = [
      "gst", "income tax", "tds", "cbdt", "gstn", "circular", "rbi",
      "sebi", "return", "filing", "compliance", "advance tax", "deduction",
      "80c", "gstr", "itr", "demand", "assessment", "appeal",
      "itat", "ca", "audit", "balance sheet", "p&l", "fema", "transfer pricing",
      "customs", "ibc", "insolvency", "nbfc", "irda"
    ]

    def classify_query(self, question: str) -> str:
        q_lower = question.lower()
        has_sql = any(re.search(sig, q_lower) for sig in SQL_SIGNALS)
        has_rag = any(re.search(sig, q_lower) for sig in RAG_SIGNALS)
        has_mixed = any(re.search(sig, q_lower) for sig in MIXED_SIGNALS)
        
        has_legal = any(s in q_lower for s in self.LEGAL_SIGNALS)
        has_finance = any(s in q_lower for s in self.FINANCE_SIGNALS)
        has_health = any(s in q_lower for s in HEALTHCARE_SIGNALS)
        has_re = any(s in q_lower for s in REALESTATE_SIGNALS)
        has_hr = any(s in q_lower for s in HR_SIGNALS)
        
        has_year = bool(re.search(r"\b\d{4}\b", q_lower))
        if has_year and has_sql:
            has_sql = True

        # Detect cross-domain queries (multiple verticals triggered)
        active_verticals = [
            v for v, flag in [
                ("LEGAL", has_legal), ("FINANCE", has_finance),
                ("HEALTHCARE", has_health), ("REALESTATE", has_re), ("HR", has_hr)
            ] if flag
        ]
            
        logger.info(f"Query classification signals matched: SQL={has_sql}, RAG={has_rag}, LEGAL={has_legal}, FINANCE={has_finance}, HEALTHCARE={has_health}, REALESTATE={has_re}, HR={has_hr}")
        
        if len(active_verticals) >= 2:
            return f"CROSS_DOMAIN:{':'.join(active_verticals)}"
        elif has_health:
            return "HEALTHCARE"
        elif has_re:
            return "REALESTATE"
        elif has_hr:
            return "HR"
        elif has_legal and not has_finance:
            return "LEGAL"
        elif has_finance and not has_legal:
            return "FINANCE"
        elif has_legal and has_finance:
            return "LEGAL_FINANCE"
        elif (has_sql and has_rag) or has_mixed:
            return "MIXED"
        elif has_sql:
            return "SQL"
        elif has_rag:
            return "RAG"
        return "RAG"

    def _run_vertical(self, vertical: str, question: str, department: str) -> dict:
        """Run a single vertical engine and return its result with confidence."""
        try:
            if vertical == "LEGAL":
                res = self.legal_engine.query(question)
            elif vertical == "FINANCE":
                res = self.finance_engine.query(question)
            elif vertical == "HEALTHCARE":
                res = self.healthcare_engine.query(question, department)
            elif vertical == "REALESTATE":
                res = self.realestate_engine.query(question, department)
            elif vertical == "HR":
                res = self.hr_engine.query(question, department)
            else:
                return {"vertical": vertical, "answer": "", "confidence": 0.0}
            return {"vertical": vertical, "answer": res.get("answer", ""), "confidence": res.get("confidence", 0.7)}
        except Exception as e:
            logger.error(f"Cross-domain vertical {vertical} failed: {e}")
            return {"vertical": vertical, "answer": f"Could not retrieve answer for {vertical}.", "confidence": 0.0}

    def _merge_cross_domain(self, results: list) -> dict:
        """Merge results from multiple verticals into a structured answer."""
        sections = []
        all_confidence = []
        emoji_map = {
            "LEGAL": "⚖️", "FINANCE": "₹", "HEALTHCARE": "🏥",
            "REALESTATE": "🏠", "HR": "👤"
        }
        for r in results:
            if r["answer"]:
                icon = emoji_map.get(r["vertical"], "•")
                sections.append(f"{icon} **{r['vertical'].title()} Answer** (confidence: {r['confidence']:.0%})\n{r['answer']}")
                all_confidence.append(r["confidence"])
        
        merged_answer = "\n\n---\n\n".join(sections)
        avg_confidence = sum(all_confidence) / len(all_confidence) if all_confidence else 0.0
        return {
            "answer": f"🔀 *This query spans multiple domains. Here is a consolidated response:*\n\n{merged_answer}",
            "query_type": "CROSS_DOMAIN",
            "sources": [],
            "confidence": round(avg_confidence, 3),
            "chunks_used": 0,
            "query_language": "en"
        }

    def route_and_query(self, question: str, department: str, filters: dict = None) -> dict:
        q_type = self.classify_query(question)

        # Fix 4.2: Check Redis cache before any engine call (skip cache for safety-blocked queries)
        cached = self.cache.get(question, department)
        if cached:
            logger.info("Returning cached response.")
            return cached

        # Cross-domain: run all matching verticals in parallel and merge
        if q_type.startswith("CROSS_DOMAIN:"):
            verticals = q_type.split(":", 1)[1].split(":")
            logger.info(f"Cross-domain query detected. Running verticals in parallel: {verticals}")
            with ThreadPoolExecutor(max_workers=len(verticals)) as ex:
                futures = {ex.submit(self._run_vertical, v, question, department): v for v in verticals}
                results = [f.result() for f in futures]
            result = self._merge_cross_domain(results)
            self.cache.set(question, department, result)
            return result

        if q_type == "HEALTHCARE":
            result = self.healthcare_engine.query(question, department)
            result["vertical"] = "HEALTHCARE"
            return result
        elif q_type == "REALESTATE":
            result = self.realestate_engine.query(question, department)
            result["vertical"] = "REALESTATE"
            return result
        elif q_type == "HR":
            result = self.hr_engine.query(question, department)
            result["vertical"] = "HR"
            return result
        elif q_type == "LEGAL":
            result = self.legal_engine.query(question)
            result["vertical"] = "LEGAL"
            return result
        elif q_type == "FINANCE":
            result = self.finance_engine.query(question)
            result["vertical"] = "FINANCE"
            return result
        elif q_type == "LEGAL_FINANCE":
            legal_res = self.legal_engine.query(question)
            fin_res = self.finance_engine.query(question)
            fin_res["answer"] = f"⚖️ **Legal:**\n{legal_res['answer']}\n\n---\n\n₹ **Finance:**\n{fin_res['answer']}"
            fin_res["vertical"] = "LEGAL_FINANCE"
            return fin_res

        # Step 1: RAG retrieval (always try first)
        rag_result = self.rag_engine.query(question, department, filters=filters)
        rag_confidence = rag_result.get("confidence", 0.0)
        rag_chunks = rag_result.get("sources", [])

        # Step 2: SQL classification and query
        query_type_rag = self.classify_query(question)

        # Step 3: Web search fallback
        web_result = self.web_engine.query(question, department, rag_confidence)
        web_source_type = web_result.get("source_type", "NOT_NEEDED")
        web_chunks = web_result.get("chunks", [])

        # Step 4: SQL if needed
        sql_result = None
        if query_type_rag in ("SQL", "MIXED"):
            sql_result = self.sql_engine.query(question, department)

        # Step 5: Determine final query type
        if rag_confidence >= 0.70 and not sql_result:
            final_type = "RAG"
        elif rag_confidence >= 0.70 and sql_result:
            final_type = "MIXED_RAG_SQL"
        elif web_source_type == "GOV":
            final_type = "RAG_GOV" if rag_chunks else "GOV"
        elif web_source_type == "WEB":
            final_type = "WEB"
        elif web_source_type == "NOT_FOUND":
            final_type = "NOT_FOUND"
        else:
            final_type = "RAG"

        # Step 6: Build fused context
        context_parts = []
        if rag_chunks:
            context_parts.append(
                "PRIVATE DOCUMENT CONTEXT (from uploaded department documents):\n"
                + "\n---\n".join([
                    f"[Source: {s.get('filename')} | {s.get('doc_type')} | {s.get('department')} | {s.get('date')}]\n{s.get('text','')}"
                    for s in rag_chunks[:5]
                ])
            )

        if sql_result and sql_result.get("formatted_result"):
            context_parts.append(
                "DATABASE CONTEXT (from live department database):\n"
                + sql_result["formatted_result"]
            )

        if web_chunks:
            source_label = "GOVERNMENT WEBSITE CONTEXT" if web_source_type == "GOV" else "WEB SEARCH CONTEXT"
            context_parts.append(
                f"{source_label}:\n"
                + "\n---\n".join([
                    f"[Source: {c.get('title')} | {c.get('url')} | {c.get('source_type')}]\n{c.get('text', '')}"
                    for c in web_chunks[:5]
                ])
            )

        fused_context = "\n\n".join(context_parts)

        # Step 7: Updated system prompt for hybrid answers
        system_prompt_addition = ""
        if web_source_type in ("GOV", "WEB"):
            system_prompt_addition = """
            ADDITIONAL RULES FOR WEB SEARCH RESULTS:
            - Clearly distinguish between answers from uploaded documents vs web sources.
            - For web sources, always cite the URL and website name.
            - If the web source is a government website (*.gov.in, *.nic.in), treat it as authoritative. If it is an open web result, treat it as supplementary.
            - If information from private documents and web sources conflicts, trust the private documents and note the discrepancy.
            - Always tell the user which source type answered their question: '(Source: Department document)' or '(Source: govt website)' or '(Source: web search)'
            """

        # Step 8: Generate answer
        if not context_parts:
            answer = ("I could not find a reliable answer in your department's "
                      "documents, government websites, or web search. Please "
                      "contact your department directly or visit "
                      "https://india.gov.in for official information.")
            confidence = 0.0
        else:
            answer = self.generate_answer(question, fused_context, system_prompt_addition)
            confidence = max(
                rag_confidence,
                0.60 if web_source_type == "GOV" else
                0.40 if web_source_type == "WEB" else 0.0
            )

        # Step 9: Build source list (combined RAG + web)
        all_sources = []
        for s in (rag_chunks or []):
            all_sources.append({
                "type": "RAG",
                "filename": s.get("filename"),
                "department": s.get("department"),
                "date": s.get("date"),
                "relevance_score": s.get("relevance_score", 0)
            })
        for c in (web_chunks or []):
            all_sources.append({
                "type": c.get("source_type", "WEB"),
                "url": c.get("url"),
                "title": c.get("title"),
                "domain": c.get("domain")
            })

        final_result = {
            "answer": answer,
            "query_type": final_type,
            "sources": all_sources,
            "sql_generated": sql_result.get("sql_generated") if sql_result else None,
            "db_row_count": sql_result.get("row_count") if sql_result else None,
            "confidence": round(confidence, 3),
            "chunks_used": len(rag_chunks) + len(web_chunks),
            "web_source_type": web_source_type,
            "web_query_used": web_result.get("query_used", ""),
            "query_language": rag_result.get("query_language", "en")
        }
        # Fix 4.2: Cache the result for future identical queries
        self.cache.set(question, department, final_result)
        return final_result

    def generate_answer(self, question: str, fused_context: str, extra_system: str = "") -> str:
        fusion_prompt = (
            f"You have access to context from documents, databases, and/or web searches.\n\n"
            f"CONTEXT:\n{fused_context}\n\n"
            f"QUESTION: {question}\n\n"
            "Rules:\n"
            "1. Synthesise the provided context into a single coherent response.\n"
            "2. Cite document source names and dates where relevant.\n"
            "3. Be concise, factual, and do not make up external information."
        )
        
        system_prompt = (
            "You are a BharatLLM document assistant. "
            "Integrate document text summaries, database tables, and web search context to answer user questions.\n"
        ) + extra_system
        
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
            # Fallback to RAG engine generate if the tokenizer generation failed (it's what prompt 4.4 implied could be used)
            if hasattr(self.rag_engine, 'generate'):
                return self.rag_engine.generate(question, fused_context, extra_system=extra_system)
            return "An error occurred while generating the response from context."

def main():
    parser = argparse.ArgumentParser(description="TN Govt LLM Query Router CLI")
    parser.add_argument("--question", type=str, required=True, help="User search question")
    parser.add_argument("--department", type=str, default="General", help="Department scope filter")
    args = parser.parse_args()
    
    print(f"Testing Classifier Router on: '{args.question}'...")
    router_check = QueryRouter.__new__(QueryRouter)
    classification = router_check.classify_query(args.question)
    print(f"Resulting route: {classification}")

if __name__ == "__main__":
    main()
