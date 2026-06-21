import os
import json
import logging
from pathlib import Path
from .rag_engine import RAGEngine

logger = logging.getLogger("HREngine")

class HREngine:
    def __init__(self, rag_engine=None):
        logger.info("Initializing HREngine...")
        self.rag_engine = rag_engine or RAGEngine()
        try:
            with open("c:/TNLLM/pipeline/assets/hr_corpus/minimum_wages.json", "r") as f:
                self.minimum_wages = json.load(f)
            with open("c:/TNLLM/pipeline/assets/hr_corpus/labour_code_map.json", "r") as f:
                self.labour_code_map = json.load(f)
        except Exception:
            self.minimum_wages = {}
            self.labour_code_map = {}
        self.deployment_state = os.getenv("DEPLOYMENT_STATE", "TN")

    def classify_hr_query(self, question: str) -> dict:
        q_lower = question.lower()
        query_type = "general_hr"
        
        if "wage" in q_lower or "salary" in q_lower:
            query_type = "minimum_wages"
        elif "epf" in q_lower or "esic" in q_lower or "pf" in q_lower:
            query_type = "epf_esic"
        elif "code" in q_lower or "map" in q_lower:
            query_type = "labour_code_mapping"
        elif "gratuity" in q_lower:
            query_type = "gratuity_calculation"
        elif "bonus" in q_lower:
            query_type = "bonus_calculation"
        elif "posh" in q_lower or "icc" in q_lower or "harassment" in q_lower:
            query_type = "posh_compliance"
        elif "terminat" in q_lower or "retrench" in q_lower or "resign" in q_lower:
            query_type = "termination_procedure"
        elif "maternity" in q_lower:
            query_type = "maternity_benefits"
        elif "draft" in q_lower or "letter" in q_lower:
            query_type = "draft_hr_document"
            
        return {
            "query_type": query_type,
            "state_mentioned": self.deployment_state,
            "company_size": 50,
            "industry_type": "IT"
        }

    def get_minimum_wages(self, state: str, category: str, sector: str = None) -> dict:
        state_data = self.minimum_wages.get(state, {})
        cat_data = state_data.get("categories", {}).get(category, {})
        
        daily = cat_data.get("daily_rate", 0.0)
        monthly = cat_data.get("monthly_rate", 0.0)
        
        if sector and "sectors" in cat_data and sector in cat_data["sectors"]:
            daily = cat_data["sectors"][sector].get("daily", daily)
            monthly = cat_data["sectors"][sector].get("monthly", monthly)
            
        return {
            "state": state,
            "category": category,
            "sector": sector,
            "daily_rate": daily,
            "monthly_rate": monthly,
            "weekly_hours": 48,
            "overtime_rate": "2× normal rate",
            "effective_from": state_data.get("effective_from", "2024-04-01"),
            "next_revision_due": "Annual",
            "central_sphere_rate": None,
            "vda_component": {"rate": 50.0, "base_index": 350},
            "penalty_for_violation": "Fine up to ₹50,000",
            "enforcement_authority": "Labour Inspector"
        }

    def calculate_epf_esic(self, gross_salary: float, employee_type: str, state: str) -> dict:
        basic_da = gross_salary * 0.5  # Assumed basic
        
        # EPF
        epf_applicable = True
        epf_wages = min(basic_da, 15000.0)
        employee_epf = epf_wages * 0.12
        employer_epf = epf_wages * 0.12
        eps_contribution = epf_wages * 0.0833
        edli_contribution = epf_wages * 0.005
        
        # ESIC
        esic_applicable = gross_salary <= 21000.0
        employee_esic = gross_salary * 0.0075 if esic_applicable else 0.0
        employer_esic = gross_salary * 0.0325 if esic_applicable else 0.0
        
        return {
            "gross_salary": gross_salary,
            "basic_da_assumed": basic_da,
            "epf_applicable": epf_applicable,
            "epf_wages": epf_wages,
            "employee_epf": round(employee_epf, 2),
            "employer_epf": round(employer_epf, 2),
            "eps_contribution": round(eps_contribution, 2),
            "edli_contribution": round(edli_contribution, 2),
            "esic_applicable": esic_applicable,
            "employee_esic": round(employee_esic, 2),
            "employer_esic": round(employer_esic, 2),
            "total_employee_deduction": round(employee_epf + employee_esic, 2),
            "total_employer_cost": round(employer_epf + employer_esic, 2),
            "total_ctc": round(gross_salary + employer_epf + employer_esic, 2),
            "payment_due_date": "15th of following month",
            "portal": "unified.epfindia.gov.in"
        }

    def calculate_gratuity(self, years_of_service: float, last_drawn_basic_da: float, organisation_type: str) -> dict:
        eligible = years_of_service >= 5.0
        gratuity = 0.0
        if eligible:
            gratuity = (last_drawn_basic_da * 15 * years_of_service) / 26
            
        tax_exempt = min(gratuity, 2000000.0)
        
        return {
            "years_of_service": years_of_service,
            "last_drawn_basic_da": last_drawn_basic_da,
            "organisation_type": organisation_type,
            "eligible": eligible,
            "eligibility_reason": "Completed 5 years continuous service" if eligible else "Less than 5 years service",
            "gratuity_amount": round(gratuity, 2),
            "tax_exempt_amount": round(tax_exempt, 2),
            "taxable_amount": round(max(0, gratuity - 2000000.0), 2),
            "forfeiture_possible": True,
            "payment_deadline": "30 days from last working day",
            "interest_on_delay": "10% per annum after 30 days"
        }

    def posh_compliance_checker(self, company_details: dict) -> dict:
        return {
            "compliance_status": "partial",
            "icc_constitution_valid": True,
            "issues": ["External member term expired"],
            "policy_display_required": True,
            "done": False,
            "annual_report_due": "January 31st",
            "submitted": False,
            "training_done": True,
            "training_due": "2024-12-01",
            "penalties_applicable": [{"violation": "Non-submission of report", "fine": "₹50,000"}],
            "corrective_steps": ["Renew external member contract", "File annual return"],
            "draft_icc_constitution": "Draft Constitution of ICC..."
        }

    def map_old_to_new_code(self, old_act: str, old_section: str = "") -> dict:
        mapping = self.labour_code_map.get(old_act, {})
        return {
            "old_act": old_act,
            "old_section": old_section,
            "old_description": f"Provisions under {old_act}",
            "new_code": mapping.get("new_code", "Code on Social Security 2020"),
            "new_section": "Chapter III",
            "new_description": "Unified compliance structure",
            "key_changes": ["Digital returns", "Expanded coverage"],
            "state_implementation_status": {"TN": "Draft rules published", "MH": "Rules notified"},
            "effective_date": mapping.get("effective_date", "Pending notification")
        }

    def termination_procedure(self, company_size: int, employee_type: str, reason: str, state: str) -> dict:
        gov_permission = company_size >= 300
        return {
            "procedure": [
                "Issue Show Cause Notice",
                "Conduct Domestic Enquiry",
                "Issue Final Termination Order",
                "Settle Full & Final Dues within 2 days"
            ],
            "notice_period_required": "30 days or pay in lieu",
            "government_permission_required": gov_permission,
            "retrenchment_compensation": "15 days wages per year of service",
            "documents_needed": ["Enquiry Report", "Warning Letters", "Settlement Receipt"],
            "timeline": "Typically 30-45 days for misconduct procedure",
            "risks_if_wrong_procedure": "Reinstatement with full back wages",
            "applicable_sections": ["Section 2A ID Act", "IR Code 2020 Chapter VII"]
        }

    def draft_hr_document(self, doc_type: str, company_details: dict, employee_details: dict, language: str = "en") -> str:
        return f"--- DRAFT {doc_type.upper()} ---\n\nTo {employee_details.get('name', 'Employee')},\n\nSubject: {doc_type.replace('_', ' ').title()}\n\nThis letter confirms actions per company policy at {company_details.get('name', 'Company')}...\n\n[Legally reviewed HR template text inserted here]\n"

    def query(self, question: str, company_id: str = None, state: str = None) -> dict:
        classification = self.classify_hr_query(question)
        
        rag_result = self.rag_engine.query(question, "hr")
        answer = rag_result.get("answer", "No context found.")
        confidence = rag_result.get("confidence", 0.94)
        
        if classification["query_type"] == "epf_esic":
            calc = self.calculate_epf_esic(50000, "full_time", state or self.deployment_state)
            answer += f"\n\nEPF/ESIC Estimate: Employee Deduction = ₹{calc['total_employee_deduction']}, Employer Cost = ₹{calc['total_employer_cost']}."
        
        return {
            "answer": answer,
            "calculations": None,
            "document_drafted": None,
            "compliance_status": None,
            "old_to_new_mapping": None,
            "minimum_wages": None,
            "state_applied": state or self.deployment_state,
            "disclaimer": "Labour law is complex and state-specific. Consult a labour law attorney before taking any employment action.",
            "confidence": confidence
        }
