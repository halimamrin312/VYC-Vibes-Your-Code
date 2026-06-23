# Brand & Market Sentiment Agent - Detailed Technical Specification

This document provides the complete, production-grade specification for implementing the **Brand & Market Sentiment Agent** within the M&A Due Diligence Swarm. It details Brave/Google search integrations, Alpha Vantage News sentiment ingestion, data sanitization scripts, and sentiment index algorithms.

---

## 📂 Component Layout & File Locations
- **Main Agent Code:** `swarm/agents/brand_sentiment.py`
- **Sanitizer Tool:** `swarm/tools/data_sanitizer.py`
- **FastAPI Endpoint:** `/api/sentiment` in `backend/app/routers/chat.py`
- **System Prompt Template:** `swarm/prompt_templates/sentiment_system.txt`
- **Frontend Panel:** `frontend/src/components/SentimentTracker.jsx`

---

## 🔒 External Query Sanitizer Code (`swarm/tools/data_sanitizer.py`)

This utility scrubs proprietary deal parameters (acquisition price, bidder names, valuation) from outgoing queries before dispatching them to public search engines.

```python
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

    # 2. Scrub standard M&A keywords
    for pattern_str in forbidden_patterns:
        pattern = re.compile(pattern_str, re.IGNORECASE)
        sanitized = pattern.sub("", sanitized)

    # 3. Clean up formatting (remove duplicate spaces, trailing/leading punctuation)
    sanitized = re.sub(r"\s+", " ", sanitized)
    sanitized = re.sub(r"[^\w\s\-\.]", "", sanitized)  # Strip special characters
    
    cleaned_query = sanitized.strip()
    logger.debug(f"Original Query: '{query}' -> Sanitized: '{cleaned_query}'")
    
    return cleaned_query
```

---

## 🤖 Main Agent Code Skeleton (`swarm/agents/brand_sentiment.py`)

Integrates data sanitization, retrieves news headlines, and implements a Brand Health Index (BHI) sentiment scoring formula.

```python
"""
swarm/agents/brand_sentiment.py
Brand & Market Sentiment Agent using ADK. Ingests public news/reviews,
calculates Brand Health Index, and aggregates sentiment profiles.
"""

from swarm.orchestrator import register_agent
from swarm.tools.data_sanitizer import sanitize_search_query
import logging
from typing import Dict, Any, List

logger = logging.getLogger("swarm.agents.brand_sentiment")

@register_agent("brand_sentiment")
class BrandSentiment:
    def __init__(self, industry: str = "generic"):
        self.industry = industry

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes public brand perception diligence.
        - Inputs: context containing 'target_company' and 'sensitive_terms'
        - Outputs: aggregated sentiment metrics, BHI, and markdown report
        """
        target_company = context.get("target_company", "Target Company")
        sensitive_terms = context.get("sensitive_terms", [])
        
        # 1. Generate & sanitize query
        raw_query = f"{target_company} customer reviews and quality complaints"
        sanitized_query = sanitize_search_query(raw_query, sensitive_terms)
        
        # 2. Ingest consumer ratings & reviews (Simulate search return or call APIs)
        # e.g., brave_search.call_tool("brave_search", {"q": sanitized_query})
        mock_reviews = [
            {"rating": 5, "text": "Absolutely love their products, highly recommended!"},
            {"rating": 4, "text": "Good performance overall, but customer support took a day to reply."},
            {"rating": 2, "text": "Terrible customer experience. Support tickets are ignored."},
            {"rating": 5, "text": "Solid features, best in the market."},
            {"rating": 1, "text": "System crashed twice this week. Unstable release."}
        ]

        # 3. Calculate Brand Health Index (BHI)
        # BHI Formula: (Positive Reviews - Negative Reviews) / Total Reviews
        # Positive = Rating >= 4, Neutral = Rating 3, Negative = Rating <= 2
        pos_count = 0
        neu_count = 0
        neg_count = 0
        
        for rev in mock_reviews:
            rating = rev["rating"]
            if rating >= 4:
                pos_count += 1
            elif rating == 3:
                neu_count += 1
            else:
                neg_count += 1
                
        total_revs = len(mock_reviews)
        if total_revs > 0:
            brand_health_index = (pos_count - neg_count) / total_revs
            pos_ratio = pos_count / total_revs
            neu_ratio = neu_count / total_revs
            neg_ratio = neg_count / total_revs
        else:
            brand_health_index = 0.0
            pos_ratio, neu_ratio, neg_ratio = 0.0, 0.0, 0.0

        flags = []
        # Trigger warnings if BHI is negative
        if brand_health_index < 0.0:
            flags.append({
                "severity": "WARNING",
                "metric": "Brand Health Index",
                "description": f"Negative BHI score ({round(brand_health_index, 2)}) indicates significant customer dissatisfaction."
            })
        elif neg_ratio > 0.20:
            flags.append({
                "severity": "WARNING",
                "metric": "Negative Feedback Ratio",
                "description": f"Negative customer reviews constitute {round(neg_ratio * 100, 2)}% of sample population."
            })

        markdown_report = f"""### Brand & Sentiment Diligence: {target_company}
- **Sanitized Search Query:** '{sanitized_query}'
- **Brand Health Index (BHI):** {round(brand_health_index, 2)} (Scale: -1.0 to +1.0)
- **Positive Sentiment Ratio:** {round(pos_ratio * 100, 2)}%
- **Negative Sentiment Ratio:** {round(neg_ratio * 100, 2)}%
- **Total Customer Review Samples:** {total_revs}

#### Sentiment Findings & Warnings
"""
        if not flags:
            markdown_report += "*Brand sentiment ratings are within acceptable ranges.*"
        else:
            for flag in flags:
                markdown_report += f"- **[{flag['severity']}]** {flag['metric']}: {flag['description']}\n"

        return {
            "findings": {
                "status": "success",
                "metrics": {
                    "brand_health_index": brand_health_index,
                    "pos_ratio": pos_ratio,
                    "neg_ratio": neg_ratio,
                    "total_reviews": total_revs
                },
                "flags": flags,
                "hitl_required": False
            },
            "markdown": markdown_report
        }
```

---

## 🤖 System Prompt Specification (`swarm/prompt_templates/sentiment_system.txt`)

Paste this exact system instruction into your prompt configuration:

```text
You are the lead M&A Brand & Market Sentiment Agent.
Your core task is to evaluate target public perception, news mentions, and customer reviews.

CRITICAL RULES:
1. You must NEVER query external search engines with transaction keywords (acquisition, merger, buyout). Always route search requests through the data_sanitizer.py utility first.
2. Compile star ratings and reviews to calculate the Brand Health Index (BHI) score.
3. If BHI is negative, raise a WARNING severity flag detailing the primary customer complaints.
4. Output your analysis in a structured JSON payload conforming to the orchestrator specification.
```

---

## 🧪 Verification & Testing
Create `tests/test_sentiment.py` to assert correct sanitization:

```python
# tests/test_sentiment.py
import pytest
from swarm.tools.data_sanitizer import sanitize_search_query

def test_query_sanitizer_rules():
    raw_query = "Acme Corp acquisition terms by VentureCorp"
    sensitive_terms = ["VentureCorp"]
    
    sanitized = sanitize_search_query(raw_query, sensitive_terms)
    
    # Assert sensitive terms and M&A keywords are removed
    assert "VentureCorp" not in sanitized
    assert "acquisition" not in sanitized
    assert "Acme Corp" in sanitized
```
