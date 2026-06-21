import os
import json
import logging
import asyncio
from typing import Callable, Dict, List, Any
from dataclasses import dataclass

log = logging.getLogger("ToolRegistry")

@dataclass
class Tool:
    name: str
    description: str
    parameters: dict
    requires_approval: bool
    category: str
    execute: Callable

# --- MOCK / STUB EXECUTE FUNCTIONS ---
# These functions will integrate with the rest of BharatLLM in a real environment.
# For now they wrap the logic described in the prompt to allow agent iteration.

async def execute_rag_search(query: str, org_unit: str, top_k: int = 5):
    # calls rag_engine.retrieve(query, org_unit, state_code)
    log.info(f"RAG Search executed for '{query}' in {org_unit}")
    return f"Mocked RAG results for: {query}"

async def execute_web_search(query: str, govt_only: bool = True):
    # calls web_search_engine.query(query, org_unit)
    log.info(f"Web Search executed for '{query}' (govt_only={govt_only})")
    return f"Mocked Web Search results for: {query}"

async def execute_sql_query(question: str, tables_hint: str = ""):
    # calls sql_engine.query(question, org_unit, state_code)
    log.info(f"SQL Query executed: '{question}'")
    return f"Mocked SQL Data for: {question}"

async def execute_translate(text: str, from_lang: str, to_lang: str):
    # uses LLaMA with translation prompt
    log.info(f"Translating {len(text)} chars from {from_lang} to {to_lang}")
    return f"[Translated text from {from_lang} to {to_lang}] {text}"

async def execute_draft_document(doc_type: str, org_unit: str, subject: str, content_points: list, language: str, ref_number: str = ""):
    log.info(f"Drafting {doc_type} document for {org_unit}: {subject}")
    content = "\n".join([f"- {p}" for p in content_points])
    return f"GOVERNMENT OF TAMIL NADU\nABSTRACT\n\nSubject: {subject}\nRef: {ref_number}\n\n{content}\n\nBy Order of Governor"

async def execute_fill_form(form_type: str, field_data: dict, output_format: str):
    log.info(f"Filling {form_type} form into {output_format}")
    return f"Form {form_type} successfully generated as {output_format}"

async def execute_generate_report(title: str, sections: list, charts: list, language: str, output_format: str):
    log.info(f"Generating report: {title} in {output_format}")
    return f"/tmp/report_{title.replace(' ', '_')}.{output_format}"

async def execute_analyse_excel(file_path: str, analysis_task: str, output: str):
    log.info(f"Analyzing excel {file_path}: {analysis_task}")
    return f"Analysis result for {analysis_task} (output: {output})"

async def execute_generate_chart(chart_type: str, data: dict, title: str, x_label: str, y_label: str, language: str):
    log.info(f"Generating {chart_type} chart: {title}")
    return f"/tmp/chart_{title.replace(' ', '_')}.png"

async def execute_execute_python(code: str, description: str):
    # Sandbox execution (E2B)
    log.info(f"Executing Sandbox Python code: {description}")
    # In reality this uses e2b
    return f"Mock Sandbox Execution Result for:\n{code}"

async def execute_draft_email(to: str, subject: str, body_points: list, tone: str, language: str, cc: str = ""):
    log.info(f"Drafting {tone} email to {to}")
    body = "\n".join([f"- {p}" for p in body_points])
    return {"to": to, "cc": cc, "subject": subject, "body": f"Draft Email Body:\n{body}"}

async def execute_send_email(to: str, subject: str, body: str, attachments: list = [], cc: str = ""):
    log.info(f"Sending email to {to} via SendGrid")
    return f"Email sent successfully to {to}"

async def execute_send_sms(to: str, message: str, channel: str):
    log.info(f"Sending {channel} to {to}")
    return f"SMS sent successfully to {to}"

async def execute_call_govt_api(api_name: str, endpoint: str, method: str, params: dict):
    log.info(f"Calling Govt API {api_name} at {endpoint}")
    return f"Mock API Response from {api_name}"

async def execute_scrape_portal(url: str, task: str, selectors: dict):
    log.info(f"Scraping portal {url} for task: {task}")
    return f"Mock scraped data from {url}"

# --- TOOL DEFINITIONS ---

TOOL_REGISTRY: Dict[str, Tool] = {}

def register(tool: Tool):
    TOOL_REGISTRY[tool.name] = tool

register(Tool(
    name="rag_search",
    description="Search BharatLLM's private document collection for information from uploaded government documents. Use this when the user's question can be answered from department circulars, G.O.s, or scheme guidelines.",
    parameters={"type": "object", "properties": {"query": {"type": "string"}, "org_unit": {"type": "string"}, "top_k": {"type": "integer"}}, "required": ["query", "org_unit"]},
    requires_approval=False, category="research", execute=execute_rag_search
))

register(Tool(
    name="web_search",
    description="Search government websites and the open web for information not found in private documents. Searches *.gov.in and *.nic.in domains first.",
    parameters={"type": "object", "properties": {"query": {"type": "string"}, "govt_only": {"type": "boolean"}}, "required": ["query"]},
    requires_approval=False, category="research", execute=execute_web_search
))

register(Tool(
    name="sql_query",
    description="Query the live government database for structured data: beneficiary counts, budget figures, employee records, hospital capacity, school enrollment statistics.",
    parameters={"type": "object", "properties": {"question": {"type": "string"}, "tables_hint": {"type": "string"}}, "required": ["question"]},
    requires_approval=False, category="data", execute=execute_sql_query
))

register(Tool(
    name="translate",
    description="Translate text between any of the 22 Indian scheduled languages and English. Use when the user writes in one language but the source document is in another.",
    parameters={"type": "object", "properties": {"text": {"type": "string"}, "from_lang": {"type": "string"}, "to_lang": {"type": "string"}}, "required": ["text", "to_lang"]},
    requires_approval=False, category="research", execute=execute_translate
))

register(Tool(
    name="draft_document",
    description="Draft an official Indian government document: G.O., circular, proceedings, notification, scheme guidelines, tender notice, or official letter. Outputs properly formatted text with standard headers.",
    parameters={"type": "object", "properties": {"doc_type": {"type": "string"}, "org_unit": {"type": "string"}, "subject": {"type": "string"}, "content_points": {"type": "array", "items": {"type": "string"}}, "language": {"type": "string"}, "ref_number": {"type": "string"}}, "required": ["doc_type", "org_unit", "subject", "content_points", "language"]},
    requires_approval=False, category="document", execute=execute_draft_document
))

register(Tool(
    name="fill_form",
    description="Fill a standard Indian government form with provided data. Supports: application forms, RTI forms, scheme enrollment, tender documents, employee joining reports.",
    parameters={"type": "object", "properties": {"form_type": {"type": "string"}, "field_data": {"type": "object"}, "output_format": {"type": "string"}}, "required": ["form_type", "field_data", "output_format"]},
    requires_approval=True, category="document", execute=execute_fill_form
))

register(Tool(
    name="generate_report",
    description="Generate a formatted PDF or Word report with data tables, charts, and narrative. Use for monthly reports, scheme performance summaries, audit reports.",
    parameters={"type": "object", "properties": {"title": {"type": "string"}, "sections": {"type": "array"}, "charts": {"type": "array"}, "language": {"type": "string"}, "output_format": {"type": "string"}}, "required": ["title", "sections", "output_format"]},
    requires_approval=False, category="document", execute=execute_generate_report
))

register(Tool(
    name="analyse_excel",
    description="Read and analyse Excel or CSV files. Extract data, compute statistics, identify trends, flag anomalies.",
    parameters={"type": "object", "properties": {"file_path": {"type": "string"}, "analysis_task": {"type": "string"}, "output": {"type": "string"}}, "required": ["file_path", "analysis_task", "output"]},
    requires_approval=False, category="data", execute=execute_analyse_excel
))

register(Tool(
    name="generate_chart",
    description="Create a chart or visualisation from data. Returns a PNG image file path.",
    parameters={"type": "object", "properties": {"chart_type": {"type": "string"}, "data": {"type": "object"}, "title": {"type": "string"}, "x_label": {"type": "string"}, "y_label": {"type": "string"}, "language": {"type": "string"}}, "required": ["chart_type", "data", "title"]},
    requires_approval=False, category="data", execute=execute_generate_chart
))

register(Tool(
    name="execute_python",
    description="Execute Python code in a secure isolated sandbox. Use for custom calculations, data transformations, statistical analysis, or generating visualisations.",
    parameters={"type": "object", "properties": {"code": {"type": "string"}, "description": {"type": "string"}}, "required": ["code", "description"]},
    requires_approval=True, category="code", execute=execute_execute_python
))

register(Tool(
    name="draft_email",
    description="Draft an official government email. Does NOT send — only drafts. Use send_email tool to actually send after human approval.",
    parameters={"type": "object", "properties": {"to": {"type": "string"}, "cc": {"type": "string"}, "subject": {"type": "string"}, "body_points": {"type": "array", "items": {"type": "string"}}, "tone": {"type": "string"}, "language": {"type": "string"}}, "required": ["to", "subject", "body_points", "tone", "language"]},
    requires_approval=False, category="comms", execute=execute_draft_email
))

register(Tool(
    name="send_email",
    description="Send an email using SendGrid. Always requires human approval before sending. Logs all sent emails.",
    parameters={"type": "object", "properties": {"to": {"type": "string"}, "cc": {"type": "string"}, "subject": {"type": "string"}, "body": {"type": "string"}, "attachments": {"type": "array", "items": {"type": "string"}}}, "required": ["to", "subject", "body"]},
    requires_approval=True, category="comms", execute=execute_send_email
))

register(Tool(
    name="send_sms",
    description="Send an SMS or WhatsApp notification via Twilio. Use for beneficiary alerts, officer notifications, deadline reminders.",
    parameters={"type": "object", "properties": {"to": {"type": "string"}, "message": {"type": "string"}, "channel": {"type": "string"}}, "required": ["to", "message", "channel"]},
    requires_approval=True, category="comms", execute=execute_send_sms
))

register(Tool(
    name="call_govt_api",
    description="Call official Indian Government APIs: DigiLocker, ePFMS, eOffice, UDISE+, NHA, PFMS scheme data API.",
    parameters={"type": "object", "properties": {"api_name": {"type": "string"}, "endpoint": {"type": "string"}, "method": {"type": "string"}, "params": {"type": "object"}}, "required": ["api_name", "endpoint", "method"]},
    requires_approval=True, category="code", execute=execute_call_govt_api
))

register(Tool(
    name="scrape_portal",
    description="Scrape data from Indian government web portals that do not have APIs. Uses Playwright browser automation.",
    parameters={"type": "object", "properties": {"url": {"type": "string"}, "task": {"type": "string"}, "selectors": {"type": "object"}}, "required": ["url", "task"]},
    requires_approval=True, category="code", execute=execute_scrape_portal
))

# --- LEGAL TOOLS ---
register(Tool(
    name="search_judgements",
    description="Search Indian Supreme Court and High Court judgements by legal point, section number, or fact pattern.",
    parameters={"type": "object", "properties": {"query": {"type": "string"}, "court": {"type": "string"}, "state": {"type": "string"}, "years_back": {"type": "integer"}}, "required": ["query", "court"]},
    requires_approval=False, category="legal", execute=lambda *a, **k: "Mock judgement search"
))

register(Tool(
    name="lookup_section",
    description="Get the exact text of any section of any Indian Act.",
    parameters={"type": "object", "properties": {"act_name": {"type": "string"}, "section_number": {"type": "string"}}, "required": ["act_name", "section_number"]},
    requires_approval=False, category="legal", execute=lambda *a, **k: "Mock section lookup"
))

register(Tool(
    name="check_limitation",
    description="Calculate limitation period for any legal action under Limitation Act 1963.",
    parameters={"type": "object", "properties": {"case_type": {"type": "string"}, "trigger_date": {"type": "string"}}, "required": ["case_type", "trigger_date"]},
    requires_approval=False, category="legal", execute=lambda *a, **k: "Mock limitation check"
))

register(Tool(
    name="draft_legal_doc",
    description="Draft a legal document — notice, plaint, petition, bail application, agreement, or affidavit.",
    parameters={"type": "object", "properties": {"doc_type": {"type": "string"}, "facts": {"type": "object"}, "language": {"type": "string"}}, "required": ["doc_type", "facts", "language"]},
    requires_approval=False, category="legal", execute=lambda *a, **k: "Mock draft legal doc"
))

register(Tool(
    name="map_old_to_new_law",
    description="Map old IPC/CrPC/Evidence Act sections to new BNS/BNSS/BSA equivalents.",
    parameters={"type": "object", "properties": {"old_code": {"type": "string"}, "section_number": {"type": "string"}}, "required": ["old_code", "section_number"]},
    requires_approval=False, category="legal", execute=lambda *a, **k: "Mock law mapping"
))

# --- FINANCE TOOLS ---
register(Tool(
    name="search_tax_circulars",
    description="Search CBDT, GSTN, RBI, SEBI, MCA circulars and notifications.",
    parameters={"type": "object", "properties": {"query": {"type": "string"}, "regulation": {"type": "string"}}, "required": ["query", "regulation"]},
    requires_approval=False, category="finance", execute=lambda *a, **k: "Mock tax circular search"
))

register(Tool(
    name="get_gst_rate",
    description="Get the exact GST rate for any goods or service with HSN/SAC code and circular citation.",
    parameters={"type": "object", "properties": {"description": {"type": "string"}, "hsn_sac": {"type": "string"}}, "required": ["description"]},
    requires_approval=False, category="finance", execute=lambda *a, **k: "Mock gst rate"
))

register(Tool(
    name="calculate_income_tax",
    description="Calculate income tax liability for individual or company under old or new tax regime.",
    parameters={"type": "object", "properties": {"income_details": {"type": "object"}, "financial_year": {"type": "string"}, "entity_type": {"type": "string"}, "regime": {"type": "string"}}, "required": ["income_details", "financial_year"]},
    requires_approval=False, category="finance", execute=lambda *a, **k: "Mock tax calc"
))

register(Tool(
    name="get_compliance_deadlines",
    description="Get upcoming compliance deadlines for GST, TDS, advance tax, ROC filings.",
    parameters={"type": "object", "properties": {"entity_type": {"type": "string"}, "days_ahead": {"type": "integer"}}, "required": ["entity_type", "days_ahead"]},
    requires_approval=False, category="finance", execute=lambda *a, **k: "Mock compliance deadlines"
))

register(Tool(
    name="draft_tax_notice_reply",
    description="Draft a formal reply to an Income Tax or GST notice with all required citations and legal grounds.",
    parameters={"type": "object", "properties": {"notice_type": {"type": "string"}, "notice_content": {"type": "string"}, "client_facts": {"type": "object"}}, "required": ["notice_type", "notice_content", "client_facts"]},
    requires_approval=True, category="finance", execute=lambda *a, **k: "Mock draft tax notice reply"
))

register(Tool(
    name="analyse_budget_impact",
    description="Analyse the impact of Union Budget announcements on a specific client type.",
    parameters={"type": "object", "properties": {"budget_points": {"type": "string"}, "client_type": {"type": "string"}, "financial_year": {"type": "string"}}, "required": ["budget_points", "client_type", "financial_year"]},
    requires_approval=False, category="finance", execute=lambda *a, **k: "Mock budget impact"
))

# --- HEALTHCARE TOOLS ---
register(Tool(
    name="get_drug_info",
    description="Get complete information about any drug available in India — indications, contraindications, dosage, schedule, CDSCO status, CGHS reimbursability, and any active alerts or bans.",
    parameters={"type": "object", "properties": {"drug_name": {"type": "string"}, "context": {"type": "string"}}, "required": ["drug_name"]},
    requires_approval=False, category="healthcare", execute=lambda *a, **k: "Mock drug info"
))

register(Tool(
    name="check_drug_interactions",
    description="Check interactions between multiple drugs. Returns severity (MAJOR/MODERATE/MINOR) and clinical recommendation.",
    parameters={"type": "object", "properties": {"drugs": {"type": "array", "items": {"type": "string"}}}, "required": ["drugs"]},
    requires_approval=False, category="healthcare", execute=lambda *a, **k: "Mock drug interactions"
))

register(Tool(
    name="nabh_compliance_check",
    description="Check a hospital department's compliance against NABH accreditation standards. Returns gap analysis and corrective action plan.",
    parameters={"type": "object", "properties": {"department": {"type": "string"}, "current_practices": {"type": "object"}}, "required": ["department", "current_practices"]},
    requires_approval=False, category="healthcare", execute=lambda *a, **k: "Mock nabh compliance"
))

register(Tool(
    name="get_icd_code",
    description="Get ICD-10 and ICD-11 codes for any clinical description. Also returns CGHS procedure code and Ayushman Bharat package.",
    parameters={"type": "object", "properties": {"clinical_description": {"type": "string"}, "language": {"type": "string"}}, "required": ["clinical_description", "language"]},
    requires_approval=False, category="healthcare", execute=lambda *a, **k: "Mock icd code"
))

register(Tool(
    name="check_health_scheme",
    description="Check patient eligibility for Ayushman Bharat, CMHIS, or any state health insurance scheme.",
    parameters={"type": "object", "properties": {"scheme_name": {"type": "string"}, "patient_details": {"type": "object"}}, "required": ["scheme_name", "patient_details"]},
    requires_approval=False, category="healthcare", execute=lambda *a, **k: "Mock health scheme"
))

register(Tool(
    name="check_cdsco_alerts",
    description="Check for active CDSCO drug bans, recalls, or quality alerts for any drug or manufacturer.",
    parameters={"type": "object", "properties": {"drug_name": {"type": "string"}, "manufacturer": {"type": "string"}}, "required": []},
    requires_approval=False, category="healthcare", execute=lambda *a, **k: "Mock cdsco alerts"
))

# --- REAL ESTATE TOOLS ---
register(Tool(
    name="calculate_stamp_duty",
    description="Calculate stamp duty and registration charges for any property transaction in any Indian state.",
    parameters={"type": "object", "properties": {"state": {"type": "string"}, "property_value": {"type": "number"}, "property_type": {"type": "string"}, "buyer_gender": {"type": "string"}, "special_category": {"type": "string"}}, "required": ["state", "property_value", "property_type", "buyer_gender"]},
    requires_approval=False, category="realestate", execute=lambda *a, **k: "Mock stamp duty"
))

register(Tool(
    name="check_rera_status",
    description="Verify if a real estate project is RERA registered and compliant. Check registration details and violations.",
    parameters={"type": "object", "properties": {"project_name": {"type": "string"}, "state": {"type": "string"}, "rera_id": {"type": "string"}}, "required": ["project_name", "state"]},
    requires_approval=False, category="realestate", execute=lambda *a, **k: "Mock rera status"
))

register(Tool(
    name="explain_land_record",
    description="Explain any Indian state land record document — what it proves, how to get it, how to read it.",
    parameters={"type": "object", "properties": {"state": {"type": "string"}, "record_type": {"type": "string"}, "language": {"type": "string"}}, "required": ["state", "record_type", "language"]},
    requires_approval=False, category="realestate", execute=lambda *a, **k: "Mock land record"
))

register(Tool(
    name="review_property_agreement",
    description="Review a sale agreement or rental agreement for missing clauses, unfair terms, and legal risks.",
    parameters={"type": "object", "properties": {"agreement_text": {"type": "string"}, "client_role": {"type": "string"}}, "required": ["agreement_text", "client_role"]},
    requires_approval=False, category="realestate", execute=lambda *a, **k: "Mock review agreement"
))

register(Tool(
    name="draft_property_agreement",
    description="Draft a sale agreement, rental agreement, gift deed, or joint development agreement.",
    parameters={"type": "object", "properties": {"agreement_type": {"type": "string"}, "parties": {"type": "object"}, "property_details": {"type": "object"}, "terms": {"type": "object"}, "state": {"type": "string"}, "language": {"type": "string"}}, "required": ["agreement_type", "parties", "property_details", "terms", "state", "language"]},
    requires_approval=False, category="realestate", execute=lambda *a, **k: "Mock draft property agreement"
))

register(Tool(
    name="rera_complaint_guide",
    description="Guide on filing an RERA complaint — procedure, documents, applicable sections, and draft complaint text.",
    parameters={"type": "object", "properties": {"state": {"type": "string"}, "issue_type": {"type": "string"}, "complaint_details": {"type": "object"}}, "required": ["state", "issue_type", "complaint_details"]},
    requires_approval=False, category="realestate", execute=lambda *a, **k: "Mock rera complaint guide"
))

# --- HR / LABOUR LAW TOOLS ---
register(Tool(
    name="get_minimum_wages",
    description="Get current minimum wages for any state, category, and sector in India.",
    parameters={"type": "object", "properties": {"state": {"type": "string"}, "category": {"type": "string"}, "sector": {"type": "string"}}, "required": ["state", "category"]},
    requires_approval=False, category="hr", execute=lambda *a, **k: "Mock minimum wages"
))

register(Tool(
    name="calculate_epf_esic",
    description="Calculate EPF and ESIC contributions for any salary. Shows employee and employer portions separately.",
    parameters={"type": "object", "properties": {"gross_salary": {"type": "number"}, "employee_type": {"type": "string"}, "state": {"type": "string"}}, "required": ["gross_salary", "employee_type", "state"]},
    requires_approval=False, category="hr", execute=lambda *a, **k: "Mock epf esic calc"
))

register(Tool(
    name="calculate_gratuity",
    description="Calculate gratuity amount under Payment of Gratuity Act.",
    parameters={"type": "object", "properties": {"years_of_service": {"type": "number"}, "last_drawn_basic_da": {"type": "number"}, "organisation_type": {"type": "string"}}, "required": ["years_of_service", "last_drawn_basic_da", "organisation_type"]},
    requires_approval=False, category="hr", execute=lambda *a, **k: "Mock gratuity calc"
))

register(Tool(
    name="check_posh_compliance",
    description="Assess company's POSH Act compliance status — ICC constitution, policy display, training, annual report.",
    parameters={"type": "object", "properties": {"company_details": {"type": "object"}}, "required": ["company_details"]},
    requires_approval=False, category="hr", execute=lambda *a, **k: "Mock posh compliance"
))

register(Tool(
    name="map_labour_code",
    description="Map any old Indian labour law section to the new Labour Code equivalent and explain what changed.",
    parameters={"type": "object", "properties": {"old_act": {"type": "string"}, "old_section": {"type": "string"}}, "required": ["old_act", "old_section"]},
    requires_approval=False, category="hr", execute=lambda *a, **k: "Mock labour code map"
))

register(Tool(
    name="get_termination_procedure",
    description="Get the correct termination procedure under Indian labour law based on company size, reason, and state.",
    parameters={"type": "object", "properties": {"company_size": {"type": "integer"}, "employee_type": {"type": "string"}, "reason": {"type": "string"}, "state": {"type": "string"}}, "required": ["company_size", "employee_type", "reason", "state"]},
    requires_approval=False, category="hr", execute=lambda *a, **k: "Mock termination procedure"
))

register(Tool(
    name="draft_hr_document",
    description="Draft any HR document — offer letter, appointment letter, warning letter, termination letter, POSH notice.",
    parameters={"type": "object", "properties": {"doc_type": {"type": "string"}, "company_details": {"type": "object"}, "employee_details": {"type": "object"}, "language": {"type": "string"}}, "required": ["doc_type", "company_details", "employee_details", "language"]},
    requires_approval=False, category="hr", execute=lambda *a, **k: "Mock draft hr document"
))

def get_tool(name: str) -> Tool:
    return TOOL_REGISTRY.get(name)

def get_tools_for_agent(category: str) -> List[Tool]:
    if category == "all":
        return list(TOOL_REGISTRY.values())
    return [t for t in TOOL_REGISTRY.values() if t.category == category]

def get_tool_schemas() -> List[dict]:
    return [
        {
            "name": t.name,
            "description": t.description,
            "parameters": t.parameters
        } for t in TOOL_REGISTRY.values()
    ]
