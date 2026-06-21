import json
import os
import re
from .rag_engine import RAGEngine
from .legal_entity_extractor import extract_legal_entities

class LegalEngine:
    def __init__(self, rag_engine=None):
        # In a full implementation, we initialize Qdrant here.
        # For now, we mock the connections and models.
        self.rag_engine = rag_engine or RAGEngine()
        
        # Load mapping dictionary
        maps_path = os.path.join(os.path.dirname(__file__), "assets", "legal_corpus", "section_maps.json")
        try:
            with open(maps_path, 'r') as f:
                self.section_maps = json.load(f)
        except FileNotFoundError:
            self.section_maps = {"ipc_to_bns": {}, "crpc_to_bnss": {}, "evidence_to_bsa": {}}

    def classify_legal_query(self, question: str) -> dict:
        q_lower = question.lower()
        query_type = "general_legal"
        
        if any(word in q_lower for word in ["find judgements", "show cases", "precedent"]):
            query_type = "judgement_search"
        elif any(word in q_lower for word in ["what does section", "explain section", "under which act"]):
            query_type = "act_lookup"
        elif any(word in q_lower for word in ["how to file", "procedure for", "which court"]):
            query_type = "procedure_query"
        elif any(word in q_lower for word in ["draft", "write", "prepare", "notice", "petition", "agreement"]):
            query_type = "drafting_request"
        elif any(word in q_lower for word in ["strength of case", "chances of winning", "analyse facts"]):
            query_type = "case_analysis"
        elif any(word in q_lower for word in ["limitation period", "time limit", "how many days"]):
            query_type = "limitation_check"
        elif "ipc" in q_lower and "bns" in q_lower:
            query_type = "new_law_mapping"

        return {
            "query_type": query_type,
            "legal_topics": [],
            "requires_drafting": query_type == "drafting_request",
            "language": "en" # stub
        }

    def search_judgements(self, query: str, filters: dict = None) -> list:
        entities = extract_legal_entities(query)
        # Mocking Qdrant retrieval
        return [
            {"case_name": "Mock vs State", "citation": "2024 SC 123", "court": "Supreme Court", "date": "2024-01-01", "is_overruled": False, "ratio": "Key finding of the court."}
        ]

    def lookup_act_section(self, act_name: str, section: str) -> dict:
        # Check mappings
        bns_eq = self.section_maps.get("ipc_to_bns", {}).get(section) if "ipc" in act_name.lower() else None
        
        return {
            "section_text": f"Mock text for {act_name} Section {section}",
            "bns_equivalent": bns_eq
        }

    def calculate_limitation(self, case_type: str, trigger_date: str, special_facts: str = None) -> dict:
        COMMON_LIMITATIONS = {
            "cheque_bounce_138": {"period": "1 month from receipt of notice", "article": "N.I. Act S.142"},
            "civil_appeal_sc": {"period": "90 days from decree", "article": "Limitation Act Art. 116"}
        }
        info = COMMON_LIMITATIONS.get(case_type, {"period": "Unknown", "article": "Unknown"})
        return {"limitation_period": info["period"], "article_reference": info["article"]}

    def draft_legal_document(self, doc_type: str, facts: dict, language: str = "en") -> str:
        # Mock drafting
        return f"[DRAFTED LEGAL {doc_type.upper()}]\nFacts: {facts}\nLanguage: {language}\n\nSir/Madam,\nUnder instructions from my client..."

    def analyse_case_strength(self, facts: str, client_position: str, legal_topic: str) -> dict:
        return {
            "strength": "Moderate",
            "legal_issues": ["Issue 1", "Issue 2"],
            "arguments_for": ["Arg 1"],
            "weaknesses": ["Weak 1"],
            "risk_level": "Medium",
            "disclaimer": "This is preliminary AI analysis."
        }

    def query(self, question: str, firm_id: str = None, client_matter_id: str = None) -> dict:
        classification = self.classify_legal_query(question)
        q_type = classification["query_type"]
        
        rag_result = self.rag_engine.query(question, "legal")
        answer = rag_result.get("answer", "No context found.")
        confidence = rag_result.get("confidence", 0.95)
        sources = rag_result.get("sources", [])
        
        document_drafted = None
        limitation_info = None
        
        if q_type == "drafting_request":
            document_drafted = self.draft_legal_document("notice", {"query": question})
            answer += "\n\nI have attached a drafted document for your review."
        elif q_type == "act_lookup":
            sec = self.lookup_act_section("Act", "123")
            if sec["bns_equivalent"]:
                answer += f"\nNote: Under new codes, this maps to BNS Section {sec['bns_equivalent']}."

        return {
            "answer": answer,
            "cited_cases": [{"name": s.get("filename", "Legal Source"), "citation": s.get("date", "2024"), "court": s.get("department", "SC"), "year": "2024", "ratio": ""} for s in sources],
            "cited_sections": [],
            "document_drafted": document_drafted,
            "limitation_info": limitation_info,
            "overruled_warnings": [],
            "bns_bnss_mappings": [],
            "query_type": q_type,
            "confidence": confidence,
            "disclaimer": "This is AI-assisted legal research. Consult a qualified advocate before taking legal action."
        }
