import re

def extract_legal_entities(text: str) -> dict:
    """Extract acts, citations, limitation periods, and topics from text."""
    entities = {
        "acts": [],
        "citations": [],
        "limitation_refs": [],
        "topics": [],
        "parties": [],
        "court_names": []
    }
    
    # 1. ACT REFERENCES
    # Pattern: "Section 138 of the Negotiable Instruments Act, 1881"
    act_pattern = r"(Section|S\.|Sec\.)\s*(\d+[A-Z]?)\s*(?:of\s+the\s+)?([A-Z][A-Za-z\s]+Act,?\s*\d{4})"
    for match in re.finditer(act_pattern, text):
        entities["acts"].append(f"Section {match.group(2)}, {match.group(3)}")
        
    article_pattern = r"Article\s+(\d+[A-Z]?)\s+of\s+the\s+Constitution"
    for match in re.finditer(article_pattern, text):
        entities["acts"].append(f"Article {match.group(1)} of the Constitution")

    # 2. CASE CITATIONS
    # Pattern: "2019 12 SCC 2014" or "AIR 2019 SC 2014"
    cit_pattern = r"(\d{4})\s+(\d+)\s+(SCC|AIR|SCR|Cr\.?LJ|ILR)\s+(\d+)"
    for match in re.finditer(cit_pattern, text):
        entities["citations"].append(match.group(0))
        
    # Parties: "Indus Airways v. Magnum Aviation (2014)"
    party_pattern = r"([A-Z][a-z]+\s+v\.?\s+[A-Z][a-z]+)\s*[\(\[]?(\d{4})[\)\]]?"
    for match in re.finditer(party_pattern, text):
        entities["parties"].append(match.group(1))

    # 3. LIMITATION PERIODS
    limit_pattern = r"within\s+(\d+)\s+(days|months|years)"
    for match in re.finditer(limit_pattern, text.lower()):
        entities["limitation_refs"].append(f"{match.group(1)} {match.group(2)}")

    # 4. LEGAL TOPICS
    topic_keywords = {
        "Criminal": ["murder", "rape", "theft", "cheating", "bail", "fir", "cognisable", "ipc", "crpc", "bns"],
        "Civil": ["contract", "decree", "injunction", "specific performance", "damages"],
        "Family": ["divorce", "maintenance", "custody", "succession", "will"],
        "Tax": ["gst", "income tax", "tds", "assessment", "appeal", "penalty"],
        "Corporate": ["company", "director", "winding up", "insolvency", "nclt"],
        "Property": ["sale", "lease", "mortgage", "partition", "patta", "encumbrance"],
        "Constitutional": ["fundamental rights", "writ", "habeas corpus", "mandamus"],
        "Consumer": ["deficiency", "unfair trade", "redressal", "compensation"]
    }
    
    text_lower = text.lower()
    for category, keywords in topic_keywords.items():
        if any(keyword in text_lower for keyword in keywords):
            entities["topics"].append(category)

    return entities
