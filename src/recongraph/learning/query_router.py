"""Query router for the GST Copilot — classifies queries into processing categories."""

import re
from enum import Enum
from typing import List, Optional, Any

# We'll rely on the LLMProvider for decomposition
# But avoiding strict type coupling if possible, so we use Any or a protocol
class LLMProviderProtocol(Any): pass


class QueryType(str, Enum):
    SIMPLE = "SIMPLE"
    GST_KNOWLEDGE = "GST_KNOWLEDGE"
    RECONCILIATION = "RECONCILIATION"
    COMPLEX = "COMPLEX"


# Patterns that indicate a reconciliation-context query
_RECON_PATTERNS = [
    r"invoice\s+(INV[\-\w]+|\w+\-\d+)",
    r"packet[\s_]?(id)?[\s:]*\w+",
    r"why\s+(was|is|did)\s+(this|that|the)\s+(invoice|packet|record)",
    r"reject(ed)?",
    r"flag(ged)?",
    r"mismatch",
    r"(auto[- ]?match|review|unmatched)",
    r"decision\s+trace",
    r"supplier\s+(history|risk|issues|problems|frequently)",
    r"GSTIN\s+\d{2}[A-Z]{5}\d{4}[A-Z]\d[A-Z\d]{2}",
]

# Patterns that indicate a GST knowledge query
_GST_PATTERNS = [
    r"section\s+\d+",
    r"rule\s+\d+",
    r"circular\s+\d+",
    r"notification\s+\d+",
    r"(input\s+tax\s+credit|ITC)",
    r"(CGST|IGST|SGST|GST)\s+(act|rule|law|provision)",
    r"(blocked\s+credit|reverse\s+charge|zero[- ]rated)",
    r"(eligible|eligibility|claim|avail|reversal)",
    r"(time\s+limit|due\s+date|deadline)",
    r"GSTR[\-]?\d[A-Z]?",
    r"(CBIC|government|gazette)",
    r"(compliance|regulation|statutory|provision)",
    r"(tax\s+liability|output\s+tax|input\s+tax)",
    r"financial\s+year",
]

# Patterns for simple/deterministic queries
_SIMPLE_PATTERNS = [
    r"^(what|which)\s+(is|are)\s+(the\s+)?(invoice\s+number|amount|date|gstin|vendor|supplier)",
    r"^(show|list|display)\s+(me\s+)?(the\s+)?(invoices?|records?|packets?|matches?)",
    r"^how\s+many\s+(invoices?|records?|packets?|matches?|mismatches?)",
    r"^(total|count|sum)\s+(of\s+)?(invoices?|records?|amount)",
]


def classify_query(
    query: str,
    has_recon_context: bool = False,
) -> QueryType:
    """
    Classify a user query into a processing category.

    Args:
        query: The user's natural language question
        has_recon_context: Whether run_id/packet_id context is attached

    Returns:
        QueryType indicating which pipeline should handle the query
    """
    q_lower = query.lower().strip()

    # 1. Check for simple deterministic queries
    for pattern in _SIMPLE_PATTERNS:
        if re.search(pattern, q_lower):
            return QueryType.SIMPLE

    # 2. Score reconciliation and GST signals
    recon_score = 0
    gst_score = 0

    for pattern in _RECON_PATTERNS:
        if re.search(pattern, q_lower, re.IGNORECASE):
            recon_score += 1

    for pattern in _GST_PATTERNS:
        if re.search(pattern, q_lower, re.IGNORECASE):
            gst_score += 1

    # Context boosts reconciliation score
    if has_recon_context:
        recon_score += 2

    # 3. Route based on scores
    if recon_score > 0 and gst_score > 0:
        return QueryType.COMPLEX  # Needs both RAG + tools
    elif recon_score > 0:
        return QueryType.RECONCILIATION
    elif gst_score > 0:
        return QueryType.GST_KNOWLEDGE
    else:
        return QueryType.SIMPLE

def decompose_complex_query(query: str, llm_provider: Any) -> List[str]:
    """
    Agentic Routing: Uses an LLM to break down a COMPLEX query into 
    distinct sub-queries (e.g., one for tool lookup, one for GST knowledge).
    """
    prompt = f"""You are a query decomposition agent for a GST reconciliation platform.
The user asked a complex question that requires both specific invoice data and general GST law knowledge.
Break this question down into exactly two or three simple sub-queries.
Return ONLY a valid JSON list of strings representing the sub-queries.

User Question: {query}
"""
    try:
        from pydantic import BaseModel
        class SubQueries(BaseModel):
            queries: List[str]
            
        result = llm_provider.generate_structured(prompt, SubQueries)
        return result.queries
    except Exception:
        # Fallback if LLM fails
        return [
            "What is the reconciliation status or data for the requested invoice?",
            "What does the GST law say about this specific scenario?"
        ]
