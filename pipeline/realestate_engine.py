import os
import json
import logging
import datetime
from pathlib import Path
from .rag_engine import RAGEngine

logger = logging.getLogger("RealEstateEngine")

# Map each state code to its official RERA portal
RERA_PORTAL_URLS = {
    "TN": "https://rera.tn.gov.in",
    "MH": "https://maharera.mahaonline.gov.in",
    "KA": "https://rera.karnataka.gov.in",
    "DL": "https://rera.delhi.gov.in",
    "GJ": "https://gujrera.gujarat.gov.in",
    "UP": "https://up-rera.in",
    "TS": "https://rera.telangana.gov.in",
    "AP": "https://aprera.ap.gov.in",
    "RJ": "https://rera.rajasthan.gov.in",
}

class RealEstateEngine:
    def __init__(self):
        logger.info("Initializing RealEstateEngine...")
        self.rag_engine = RAGEngine()
        try:
            with open("c:/TNLLM/pipeline/assets/realestate_corpus/stamp_duty_matrix.json", "r") as f:
                self.stamp_duty_matrix = json.load(f)
        except Exception:
            self.stamp_duty_matrix = {}
        self.deployment_state = os.getenv("DEPLOYMENT_STATE", "TN")
        # Mock: last_indexed_at would normally be stored in Qdrant collection metadata
        self.last_indexed_at = datetime.datetime.now() - datetime.timedelta(days=35)  # simulate stale data
        
    def classify_re_query(self, question: str) -> dict:
        q_lower = question.lower()
        query_type = "general_realestate"
        
        if "rera" in q_lower or "builder" in q_lower:
            query_type = "rera_compliance"
            if "complaint" in q_lower or "dispute" in q_lower:
                query_type = "rera_complaint"
        elif "stamp" in q_lower or "registration" in q_lower:
            query_type = "stamp_duty"
        elif "patta" in q_lower or "chitta" in q_lower or "record" in q_lower or "7/12" in q_lower:
            query_type = "land_record"
        elif "agreement" in q_lower or "deed" in q_lower or "draft" in q_lower:
            query_type = "agreement_draft"
            
        return {
            "query_type": query_type,
            "state_mentioned": self.deployment_state,
            "property_type": "residential",
            "transaction_type": "sale"
        }

    def calculate_stamp_duty(self, state: str, property_value: float, property_type: str, buyer_gender: str, special_category: str = None) -> dict:
        state_data = self.stamp_duty_matrix.get(state, {})
        sale_data = state_data.get("residential_sale", {})
        
        rate_str = sale_data.get(f"{buyer_gender}_buyer", "7%")
        rate_float = float(rate_str.strip('%')) / 100.0
        stamp_duty_amount = property_value * rate_float
        
        reg_rate_str = sale_data.get("registration_fee", "4%")
        reg_float = float(reg_rate_str.strip('%')) / 100.0
        registration_amount = property_value * reg_float
        
        return {
            "state": state,
            "property_value": property_value,
            "property_type": property_type,
            "stamp_duty_rate": rate_str,
            "stamp_duty_amount": stamp_duty_amount,
            "registration_fee_rate": reg_rate_str,
            "registration_fee_amount": registration_amount,
            "other_charges": {"legal_fee": 5000, "mutation_fee": 1000},
            "total_registration_cost": stamp_duty_amount + registration_amount + 6000,
            "concessions_applied": [],
            "payment_mode": "e-stamp",
            "authority": "Sub-Registrar Office",
            "documents_required": ["Sale Deed", "Aadhaar", "PAN", "Patta Transfer"],
            "effective_date_of_rates": "2024-04-01"
        }

    def check_rera_compliance(self, state: str, project_details: dict) -> dict:
        return {
            "registration_required": True,
            "reason": "Project > 500 sq.m",
            "compliance_status": "partial",
            "registration_deadline": None,
            "quarterly_report_due": "2024-07-15",
            "escrow_requirement": {"amount": "70% of funds", "bank": "Scheduled Bank", "compliant": True},
            "violations_found": ["Missing structural engineer certificate"],
            "penalty_risk": "Up to 5% of project cost",
            "remediation_steps": ["Upload certificate to RERA portal immediately"]
        }

    def explain_land_record(self, state: str, record_type: str, language: str = "en") -> dict:
        return {
            "record_name": record_type,
            "state": state,
            "local_name": "Patta" if state == "TN" else "7/12 Extract",
            "what_it_proves": "Legal ownership of the land",
            "how_to_obtain": "Apply online via state portal or visit Taluk office",
            "documents_needed": ["Registered Sale Deed", "Aadhaar"],
            "online_portal_url": "https://eservices.tn.gov.in/",
            "offline_process": "Submit Form II at Village Administrative Officer (VAO)",
            "time_taken": "15 days",
            "cost": "₹60 online fee",
            "common_issues": "Survey number mismatch",
            "how_to_correct_errors": "File an appeal with the Revenue Divisional Officer (RDO)",
            "explained_in": language
        }

    def review_sale_agreement(self, agreement_text: str, client_role: str) -> dict:
        return {
            "overall_assessment": "Moderate",
            "favorable_clauses": ["Clear payment schedule"],
            "unfavorable_clauses": ["High delay penalty for buyer"],
            "missing_clauses": ["Force Majeure"],
            "legal_risks": ["Title indemnity is weakly worded"],
            "recommended_additions": ["Insert strong arbitration clause"],
            "red_flags": ["No mention of RERA account for payments"],
            "suggested_revisions": [{
                "clause": "Payment terms",
                "current_text": "Buyer will pay seller directly.",
                "suggested_text": "Buyer shall remit funds to the RERA designated Escrow account."
            }]
        }

    def rera_complaint_guide(self, state: str, issue_type: str, complaint_details: dict) -> dict:
        return {
            "applicable_rera_section": "Section 18 of RERA Act",
            "complaint_authority": f"{state} RERA Adjudicating Officer",
            "online_complaint_portal": f"https://{state.lower()}rera.gov.in",
            "documents_needed": ["Allotment Letter", "Builder-Buyer Agreement", "Payment Receipts"],
            "filing_fee": "₹1000",
            "typical_timeline": "60 to 90 days",
            "relief_available": ["Refund with interest", "Delayed possession compensation"],
            "precedent_orders": ["Rajesh vs. Supertech (2021)"],
            "drafted_complaint": "To The Adjudicating Officer...\nSub: Complaint for delay in possession..."
        }

    def draft_agreement(self, agreement_type: str, parties: dict, property_details: dict, terms: dict, state: str, language: str = "en") -> str:
        return f"--- DRAFT {agreement_type.upper()} ---\n\nThis agreement is made in {state} between {parties.get('party1', 'Party A')} and {parties.get('party2', 'Party B')}.\n\nProperty: {property_details.get('address', 'Standard Address')}\n\n[Legal clauses generated by AI for {state} jurisdiction...]\n"

    def data_freshness_check(self, state: str = None) -> dict:
        """Check if the vector data is stale (>30 days old) and return a warning."""
        age_days = (datetime.datetime.now() - self.last_indexed_at).days
        is_stale = age_days > 30
        applied_state = state or self.deployment_state
        portal_url = RERA_PORTAL_URLS.get(applied_state.upper(), "https://mohua.gov.in")
        return {
            "is_stale": is_stale,
            "age_days": age_days,
            "last_indexed_at": self.last_indexed_at.strftime("%Y-%m-%d"),
            "disclaimer": (
                f"⚠️ Data may be stale. Last updated: {self.last_indexed_at.strftime('%d %b %Y')}. "
                f"Please verify on the official RERA portal: {portal_url}"
            ) if is_stale else None,
            "portal_url": portal_url
        }

    def query(self, question: str, firm_id: str = None, state: str = None) -> dict:
        classification = self.classify_re_query(question)
        applied_state = state or self.deployment_state

        # Fix 1.2: Check data freshness before answering RERA queries
        freshness = self.data_freshness_check(applied_state)

        rag_result = self.rag_engine.query(question, "realestate")
        answer = rag_result.get("answer", "No context found.")
        confidence = rag_result.get("confidence", 0.92)

        if classification["query_type"] == "stamp_duty":
            sd = self.calculate_stamp_duty(applied_state, 5000000, "residential", "male")
            answer += f"\n\nStamp Duty Estimate: {sd['stamp_duty_rate']} + {sd['registration_fee_rate']} Registration."

        # Append stale data disclaimer if needed
        if freshness["is_stale"] and freshness["disclaimer"]:
            answer += f"\n\n{freshness['disclaimer']}"
            confidence = min(confidence, 0.65)  # reduce confidence for stale data

        return {
            "answer": answer,
            "stamp_duty_calculation": None,
            "rera_compliance": None,
            "agreement_drafted": None,
            "land_record_info": None,
            "state_applied": applied_state,
            "data_freshness": freshness,
            "disclaimer": "Verify with Sub-Registrar/RERA office before transaction. Consult a property lawyer.",
            "confidence": confidence
        }
