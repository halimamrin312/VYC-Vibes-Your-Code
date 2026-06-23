"""
swarm/tools/data_sanitizer.py
Scrubs confidential deal indicators (bidder names, transaction metrics, deal types)
from outbound queries sent to public search engines or news indices.
"""

import re
import logging
from typing import List

logger = logging.getLogger("swarm.tools.data_sanitizer")

def sanitize_search_query(query: str, sensitive_terms: List[str]) -> str:
    """
    Takes an input search query and replaces confidential deal information
    with generic tags. Filters standard M&A operational terms.
    """
    if not query:
        return ""

    sanitized = query
    
    # Define generic list of forbidden M&A keywords (regex word boundary)
    forbidden_patterns = [
        r"\bacquisition\b",
        r"\bmerger\b",
        r"\bbuyout\b",
        r"\btakeover\b",
        r"\bvaluation\b",
        r"\bprice\b",
        r"\btransaction\b",
        r"\bdeal\b",
        r"\bhostile\b"
    ]
    
    # 1. Scrub user-defined sensitive terms (e.g., specific investor or bidder names)
    for term in sensitive_terms:
        if term:
            pattern = re.compile(re.escape(term.strip()), re.IGNORECASE)
            sanitized = pattern.sub("", sanitized)

    # 2. Scrub M&A keywords
    for pattern_str in forbidden_patterns:
        pattern = re.compile(pattern_str, re.IGNORECASE)
        sanitized = pattern.sub("", sanitized)

    # 3. Clean up formatting (remove duplicate spaces, trailing/leading punctuation)
    sanitized = re.sub(r"\s+", " ", sanitized)
    sanitized = re.sub(r"[^\w\s\-\.]", "", sanitized)  # Strip special characters
    
    cleaned_query = sanitized.strip()
    logger.debug(f"Original Query: '{query}' -> Sanitized: '{cleaned_query}'")
    
    return cleaned_query
