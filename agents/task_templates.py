# Government-Specific Agentic Workflows

TASK_TEMPLATES = [
    {
        "id": "monthly_scheme_report",
        "name": "Monthly Scheme Report",
        "description": "Fetch scheme beneficiary data for a specific month and district, generate charts, write a report, and draft an email.",
        "prompt": "Fetch scheme beneficiary data for {month} {year} in {district}, calculate coverage vs target, generate a district-wise bar chart, write a 1-page summary report in Tamil and English, and draft an email for the {superior_officer} with the report attached.",
        "recommended_agents": ["data_agent", "document_agent", "code_agent", "comms_agent"]
    },
    {
        "id": "new_go_briefing",
        "name": "New G.O. Briefing",
        "description": "Fetch latest G.O.s, summarise, translate, and generate a briefing document.",
        "prompt": "Fetch the latest G.O.s issued by {department} in the last {N} days, summarise each in 3 bullet points, translate summaries to Tamil, and generate a briefing document for department staff.",
        "recommended_agents": ["research_agent", "document_agent"]
    },
    {
        "id": "budget_utilisation_alert",
        "name": "Budget Utilisation Alert",
        "description": "Check budget utilisation and draft advisory circulars if below threshold.",
        "prompt": "Check current budget utilisation for {department} Q{N} {year}. If utilisation is below 70%, identify the top 3 under-spending schemes and draft an advisory circular to the District Collectors.",
        "recommended_agents": ["data_agent", "document_agent"]
    },
    {
        "id": "rti_response_draft",
        "name": "RTI Response Draft",
        "description": "Draft an RTI response based on a citizen's question.",
        "prompt": "An RTI application asks: '{rti_question}'. Search our department documents and database for the relevant information, draft a formal RTI response letter, and flag if any information must be withheld under Section 8 of the RTI Act.",
        "recommended_agents": ["research_agent", "data_agent", "document_agent"]
    },
    {
        "id": "beneficiary_sms_campaign",
        "name": "Beneficiary SMS Campaign",
        "description": "Identify unenrolled beneficiaries and generate SMS reminders.",
        "prompt": "Identify beneficiaries in {scheme} who have not renewed in the last {N} months, generate a personalised SMS reminder in their preferred language, and send to all {count} identified beneficiaries.",
        "recommended_agents": ["data_agent", "comms_agent"]
    },
    {
        "id": "scheme_eligibility_check",
        "name": "Scheme Eligibility Check",
        "description": "Check eligibility for a scheme and draft confirmation/rejection.",
        "prompt": "A citizen claims to be eligible for {scheme}. Their details are: {citizen_data}. Check eligibility against the scheme guidelines, query the database to see if they are already enrolled, and draft a formal eligibility confirmation or rejection letter.",
        "recommended_agents": ["research_agent", "data_agent", "document_agent"]
    }
]

def get_templates():
    return TASK_TEMPLATES
