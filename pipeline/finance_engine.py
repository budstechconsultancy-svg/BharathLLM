import json
import os
from .rag_engine import RAGEngine

class ComplianceCalendar:
    def __init__(self):
        cal_path = os.path.join(os.path.dirname(__file__), "assets", "finance_corpus", "compliance_calendar.json")
        try:
            with open(cal_path, 'r') as f:
                self.calendar = json.load(f)
        except FileNotFoundError:
            self.calendar = {"entity_type": {}}

    def get_upcoming_deadlines(self, entity_type: str, days_ahead: int = 30) -> list:
        # Stub logic
        return [{"deadline_name": "GSTR-1 monthly return", "due_date": "11th of month", "penalty_if_missed": "₹50/day"}]

class FinanceEngine:
    def __init__(self):
        self.rag_engine = RAGEngine()
        self.compliance_calendar = ComplianceCalendar()

    def classify_finance_query(self, question: str) -> dict:
        q_lower = question.lower()
        query_type = "general_finance"
        
        if "gst" in q_lower:
            query_type = "gst_query"
        elif "income tax" in q_lower:
            query_type = "income_tax_query"
        elif "deadline" in q_lower or "compliance" in q_lower:
            query_type = "compliance_calendar"
        elif "reply" in q_lower and "notice" in q_lower:
            query_type = "notice_response"
        elif "budget" in q_lower:
            query_type = "budget_analysis"

        return {
            "query_type": query_type,
            "tax_category": [],
            "requires_calculation": False,
            "requires_drafting": query_type == "notice_response"
        }

    def search_circulars(self, query: str, regulation: str = "all", date_from: str = None) -> list:
        return [{"circular_number": "CBDT 183/2022", "date": "2022-01-01", "title": "Mock Circular", "is_current": True}]

    def get_gst_rate(self, goods_or_service_description: str, hsn_or_sac: str = None) -> dict:
        return {
            "goods_service": goods_or_service_description,
            "hsn_sac": hsn_or_sac or "9983",
            "gst_rate": "18%",
            "notification_reference": "Notification 11/2017"
        }

    def calculate_tax(self, income_details: dict, fy: str, regime: str = "new") -> dict:
        return {"total_income": 1000000, "total_tax": 75000, "effective_rate": "7.5%"}

    def draft_notice_reply(self, notice_type: str, notice_content: str, client_facts: dict) -> str:
        return f"[DRAFTED TAX REPLY]\nNotice: {notice_type}\n\nTo The Assessing Officer,\nWith reference to your notice..."

    def analyse_budget_impact(self, budget_text: str, client_type: str) -> dict:
        return {"net_impact_on_client": "Neutral", "savings_or_cost": "₹0"}

    def query(self, question: str, firm_id: str = None, client_id: str = None, entity_type: str = None) -> dict:
        classification = self.classify_finance_query(question)
        q_type = classification["query_type"]
        
        rag_result = self.rag_engine.query(question, "finance")
        answer = rag_result.get("answer", "No context found.")
        confidence = rag_result.get("confidence", 0.95)
        sources = rag_result.get("sources", [])
        
        document_drafted = None
        gst_rate_info = None
        compliance_deadlines = None
        
        if q_type == "gst_query" and "rate" in question.lower():
            gst_rate_info = self.get_gst_rate("service")
            answer += f"\n\nApplicable GST Rate identified as {gst_rate_info['gst_rate']} based on logic rules."
        elif q_type == "compliance_calendar":
            compliance_deadlines = self.compliance_calendar.get_upcoming_deadlines(entity_type or "pvt_ltd")
            answer += "\n\nI have fetched your upcoming compliance deadlines."
        elif q_type == "notice_response":
            document_drafted = self.draft_notice_reply("IT Scrutiny", "Please explain...", {"query": question})
            answer += "\n\nI have drafted a response to the notice for your review."

        return {
            "answer": answer,
            "circulars_cited": [{"number": s.get("filename", "Mock CBDT"), "date": s.get("date", "2024"), "title": "Circular", "url": "https"} for s in sources],
            "sections_cited": [],
            "gst_rate_info": gst_rate_info,
            "tax_calculation": None,
            "compliance_deadlines": compliance_deadlines,
            "document_drafted": document_drafted,
            "is_current": True,
            "superseded_warning": None,
            "confidence": confidence,
            "disclaimer": "This is AI-assisted research. Verify with the latest notifications and consult your professional advisor."
        }
