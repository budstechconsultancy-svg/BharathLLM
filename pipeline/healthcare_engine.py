import os
import json
import logging
from pathlib import Path
from .rag_engine import RAGEngine

logger = logging.getLogger("HealthcareEngine")

# Fix 1.3: Healthcare safety guardrail — keywords that imply personal medical advice
DANGEROUS_MEDICAL_KEYWORDS = [
    "home remedy", "treat at home", "self medicate", "self-medicate",
    "home treatment", "natural cure", "natural remedy", "heal myself",
    "symptoms of", "do i have", "am i sick", "can i take", "is it safe to take",
    "dosage for me", "my dosage", "how much should i take", "overdose",
    "suicide", "self harm", "kill myself", "end my life",
    "cure cancer", "cure diabetes", "cure aids", "cure covid",
    "abort", "abortion pill", "emergency contraception",
    "chest pain", "heart attack", "stroke symptoms", "seizure treatment",
    "எவ்வளவு மருந்து", "வீட்டு வைத்தியம்", "மருத்துவர் இல்லாமல்",
    "घर पर इलाज", "खुद का इलाज", "दवाई कितनी लें"
]

SAFE_RESPONSE = (
    "⚕️ **BharatLLM cannot provide personal medical advice.**\n\n"
    "• For medical **emergencies**, call **112** immediately.\n"
    "• For mental health support, call **iCall: 9152987821**.\n\n"
    "BharatLLM is designed to assist with:\n"
    "  ✅ Health scheme eligibility (PMJAY, CMHIS, CGHS)\n"
    "  ✅ Hospital empanelment and NABH compliance\n"
    "  ✅ ICD-10 medical coding for billing\n"
    "  ✅ Drug regulatory (CDSCO) alerts\n\n"
    "Please rephrase your question around one of these topics."
)

class HealthcareEngine:
    def __init__(self, rag_engine=None):
        logger.info("Initializing HealthcareEngine...")
        self.rag_engine = rag_engine or RAGEngine()
        self.drug_interaction_matrix = {}
        self.icd10_to_cghs_map = {}
        
    def classify_health_query(self, question: str) -> dict:
        """Classify the health query type."""
        q_lower = question.lower()
        query_type = "general_health"
        
        if "drug" in q_lower or "medicine" in q_lower or "dosage" in q_lower:
            query_type = "drug_info"
            if "interact" in q_lower:
                query_type = "drug_interaction"
        elif "nabh" in q_lower or "compliance" in q_lower:
            query_type = "nabh_compliance"
        elif "icd" in q_lower or "code" in q_lower:
            query_type = "icd_coding"
        elif "cghs" in q_lower or "rate" in q_lower:
            query_type = "cghs_query"
        elif "scheme" in q_lower or "ayushman" in q_lower:
            query_type = "scheme_eligibility"
        elif "ban" in q_lower or "cdsco" in q_lower or "recall" in q_lower:
            query_type = "cdsco_alert"
            
        return {
            "query_type": query_type,
            "clinical_domain": "medicine",
            "involves_prescription": "dosage" in q_lower or "prescription" in q_lower,
            "patient_facing": "doctor" in q_lower or "my " in q_lower
        }

    def get_drug_info(self, drug_name: str, query_context: str = "") -> dict:
        # Mocking drug information retrieval
        return {
            "generic_name": f"{drug_name} Generic",
            "brand_names": [f"{drug_name} Brand1", f"{drug_name} Brand2"],
            "drug_class": "Antibiotic" if "mycin" in drug_name.lower() else "Analgesic",
            "indications": ["Fever", "Pain"],
            "contraindications": ["Allergy"],
            "key_interactions": ["Alcohol"],
            "dosage_summary": "1 tablet twice daily after meals",
            "side_effects_summary": "Nausea, dizziness",
            "schedule": "H1",
            "prescription_required": True,
            "is_banned": False,
            "ban_reason": None,
            "active_alerts": [],
            "cghs_reimbursable": True,
            "cghs_rate": 15.50,
            "ayushman_covered": True,
            "disclaimer": "For clinical use by registered practitioners only. Consult a doctor."
        }

    def check_drug_interactions(self, drugs: list) -> dict:
        # Mock checking interactions
        return {
            "interactions_found": [{
                "drug1": drugs[0] if len(drugs) > 0 else "Drug1",
                "drug2": drugs[1] if len(drugs) > 1 else "Drug2",
                "severity": "MODERATE",
                "effect": "Increased risk of side effects",
                "mechanism": "CYP450 inhibition",
                "clinical_recommendation": "Monitor patient closely.",
                "alternative_drug": "Consider alternative therapy."
            }],
            "most_severe": "MODERATE",
            "overall_recommendation": "Use with caution.",
            "disclaimer": "Always consult prescribing physician before changing medications."
        }

    def nabh_compliance_check(self, department: str, current_practices: dict) -> dict:
        return {
            "department": department,
            "total_applicable_standards": 25,
            "compliant": 20,
            "partial": 3,
            "non_compliant": 2,
            "compliance_percentage": 80.0,
            "critical_gaps": [{
                "standard_code": "COP.1",
                "requirement": "Uniform care",
                "current_gap": "Inconsistent protocols",
                "corrective_action": "Standardise SOPs"
            }],
            "documentation_gaps": ["Missing consent forms"],
            "training_gaps": ["BLS training pending for 5 nurses"],
            "estimated_compliance_timeline": "2 weeks"
        }

    def get_icd_code(self, clinical_description: str, language: str = "en") -> dict:
        return {
            "clinical_description_original": clinical_description,
            "translated_description": clinical_description,
            "icd_10_code": "J01.90",
            "icd_10_description": "Acute sinusitis, unspecified",
            "icd_11_code": "CA01.Z",
            "icd_11_description": "Acute sinusitis, unspecified",
            "cghs_procedure_codes": ["ENT001"],
            "drg_code": "DRG123",
            "drg_description": "ENT Infections",
            "ayushman_package_code": "AB-ENT-01",
            "billing_notes": "Requires pre-auth."
        }

    def get_cghs_rates(self, procedure: str, city_category: str = "A") -> dict:
        return {
            "procedure_name": procedure,
            "cghs_code": "CGHS-456",
            "ward_rates": {
                "general": 5000.0,
                "semi_private": 6500.0,
                "private": 8000.0
            },
            "city_category": city_category,
            "effective_date": "2024-01-01",
            "pre_auth_required": False,
            "excluded_items": ["Consumables", "Implants"],
            "empanelment_required": True
        }

    def check_scheme_eligibility(self, scheme_name: str, patient_details: dict) -> dict:
        return {
            "eligible": True,
            "reason": "Family income below threshold",
            "documents_needed": ["Ration Card", "Aadhaar"],
            "benefit_amount": "5,00,000",
            "enrolled_hospitals_nearby": ["Govt General Hospital", "City Care Hospital"],
            "claim_procedure": "Present e-card at hospital PMJAY desk."
        }

    def query(self, question: str, hospital_id: str = None, language: str = "en") -> dict:
        q_lower = question.lower()

        # Fix 1.3: Safety guardrail — intercept dangerous personal-advice queries
        if any(kw in q_lower for kw in DANGEROUS_MEDICAL_KEYWORDS):
            logger.warning(f"SAFETY_GUARDRAIL triggered for query: '{question[:80]}...'")
            # Log to audit file
            try:
                import datetime
                log_path = "logs/healthcare_safety_audit.log"
                os.makedirs("logs", exist_ok=True)
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(f"{datetime.datetime.utcnow().isoformat()} | BLOCKED | {question[:200]}\n")
            except Exception as log_err:
                logger.error(f"Audit log write failed: {log_err}")
            return {
                "answer": SAFE_RESPONSE,
                "query_type": "SAFETY_BLOCKED",
                "safety_blocked": True,
                "emergency_detected": any(e in q_lower for e in ["chest pain", "heart attack", "stroke", "seizure", "suicide"]),
                "confidence": 1.0,
                "disclaimer": "This response was generated by the BharatLLM Safety Guardrail."
            }

        classification = self.classify_health_query(question)
        
        rag_result = self.rag_engine.query(question, "healthcare")
        answer = rag_result.get("answer", "No context found.")
        confidence = rag_result.get("confidence", 0.95)
        
        if classification["query_type"] == "drug_interaction":
            interaction = self.check_drug_interactions(["DrugA", "DrugB"])
            answer += f"\n\nInteraction Alert: {interaction['overall_recommendation']}"
        elif classification["query_type"] == "icd_coding":
            icd = self.get_icd_code(question)
            answer += f"\n\nICD-10 Code Reference: {icd['icd_10_code']} - {icd['icd_10_description']}"
        
        return {
            "answer": answer,
            "drugs_mentioned": [],
            "cdsco_alerts": [],
            "nabh_standards": [],
            "icd_codes": [],
            "cghs_rates": [],
            "scheme_info": None,
            "language_used": language,
            "patient_facing": classification["patient_facing"],
            "emergency_detected": False,
            "disclaimer": "This is for information only. Consult your doctor before starting any medication.",
            "confidence": confidence
        }
