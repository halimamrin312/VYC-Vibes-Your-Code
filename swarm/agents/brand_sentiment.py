"""
swarm/agents/brand_sentiment.py
Brand & Market Sentiment Agent using ADK. Ingests public news/reviews,
calculates Brand Health Index (BHI), and aggregates sentiment profiles.
"""

from swarm.orchestrator import register_agent
from swarm.tools.data_sanitizer import sanitize_search_query
from swarm.utils.llm import call_llm
import os
import re
import json
import pandas as pd
import logging
from typing import Dict, Any, List

logger = logging.getLogger("swarm.agents.brand_sentiment")

def load_sentiment_system_prompt() -> str:
    """Loads system prompt for brand sentiment analysis."""
    template_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompt_templates", "sentiment_system.txt")
    if os.path.exists(template_path):
        try:
            with open(template_path, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception as e:
            logger.error(f"Error reading system prompt from {template_path}: {e}")
    return (
        "You are the lead M&A Brand & Market Sentiment Agent.\n"
        "Your core task is to evaluate target public perception, news mentions, and customer reviews.\n\n"
        "CRITICAL RULES:\n"
        "1. You must NEVER query external search engines with transaction keywords (acquisition, merger, buyout). Always route search requests through the data_sanitizer.py utility first.\n"
        "2. Compile star ratings and reviews to calculate the Brand Health Index (BHI) score.\n"
        "3. If BHI is negative, raise a WARNING severity flag detailing the primary customer complaints.\n"
        "4. Output your analysis in a structured JSON payload conforming to the orchestrator specification."
    )

@register_agent("brand_sentiment")
class BrandSentiment:
    def __init__(self, industry: str = "generic"):
        self.industry = industry.strip().lower()

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes public brand perception diligence.
        - Inputs: context containing 'target_company' and 'sensitive_terms'
        - Outputs: aggregated sentiment metrics, BHI, and markdown report
        """
        target_company = context.get("target_company", "Target Company")
        sensitive_terms = context.get("sensitive_terms", [])
        session_id = context.get("session_id", "default")
        
        # 1. Generate & sanitize query
        raw_query = f"{target_company} customer reviews and quality complaints"
        sanitized_query = sanitize_search_query(raw_query, sensitive_terms)
        
        # 2. Check for local CSV statements in data room
        session_path = os.path.join("data_room", "uploads", "brand", session_id)
        global_path = context.get("data_room_path", "data_room/uploads/brand")
        selected_path = session_path if os.path.exists(session_path) else global_path
        
        csv_file = None
        if os.path.exists(selected_path):
            files = [f for f in os.listdir(selected_path) if f.endswith('.csv')]
            if files:
                csv_file = os.path.join(selected_path, files[0])
                
        df = None
        data_source = "Simulated Consumer Sentiment Feed"
        if csv_file:
            try:
                df = pd.read_csv(csv_file)
                data_source = f"Target Document Ingestion ({os.path.basename(csv_file)})"
                
                # Check for standard columns and normalize
                text_col = None
                rating_col = None
                for col in df.columns:
                    col_lower = col.lower().strip()
                    if any(kw in col_lower for kw in ['text', 'review', 'feedback', 'comment', 'message', 'body']):
                        text_col = col
                    if any(kw in col_lower for kw in ['rating', 'score', 'star']):
                        rating_col = col
                
                if rating_col and text_col:
                    # Rename to standard schema
                    df = df.rename(columns={text_col: 'ReviewText', rating_col: 'Rating'})
                else:
                    logger.warning(f"CSV {csv_file} missing text/rating headers, falling back to mock.")
                    df = None
            except Exception as e:
                logger.error(f"Failed to read brand reviews CSV: {e}")
                df = None
                
        if df is None:
            mock_reviews = [
                {"Rating": 5, "ReviewText": "Absolutely love their products, highly recommended!"},
                {"Rating": 4, "ReviewText": "Good performance overall, but customer support took a day to reply."},
                {"Rating": 2, "ReviewText": "Terrible customer experience. Support tickets are ignored."},
                {"Rating": 5, "ReviewText": "Solid features, best in the market."},
                {"Rating": 1, "ReviewText": "System crashed twice this week. Unstable release."}
            ]
            df = pd.DataFrame(mock_reviews)

        # 3. Calculate Brand Health Index (BHI)
        # BHI Formula: (Positive Reviews - Negative Reviews) / Total Reviews
        # Positive = Rating >= 4, Neutral = Rating 3, Negative = Rating <= 2
        pos_count = len(df[df['Rating'] >= 4])
        neu_count = len(df[df['Rating'] == 3])
        neg_count = len(df[df['Rating'] <= 2])
        total_revs = len(df)
        
        if total_revs > 0:
            brand_health_index = (pos_count - neg_count) / total_revs
            pos_ratio = pos_count / total_revs
            neu_ratio = neu_count / total_revs
            neg_ratio = neg_count / total_revs
        else:
            brand_health_index = 0.0
            pos_ratio, neu_ratio, neg_ratio = 0.0, 0.0, 0.0

        flags = []
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

        # Format subset of reviews for LLM input
        formatted_reviews = ""
        reviews_list = df.to_dict('records')
        for idx, rev in enumerate(reviews_list[:10]):
            formatted_reviews += f"- Rating: {rev['Rating']} | Text: {rev['ReviewText']}\n"
            
        system_prompt = load_sentiment_system_prompt()
        user_prompt = f"""
We are auditing target company: '{target_company}' (Industry Sector: '{self.industry}').
The public brand review logs have been audited (Source: {data_source}):
- Sanitized Search Query: '{sanitized_query}'
- Brand Health Index (BHI): {round(brand_health_index, 2)} (Scale: -1.0 to +1.0)
- Positive Sentiment Ratio: {round(pos_ratio * 100, 2)}%
- Negative Sentiment Ratio: {round(neg_ratio * 100, 2)}%
- Total Customer Review Samples: {total_revs}

Here is a subset of the customer review logs:
{formatted_reviews}

Please perform a professional brand sentiment audit:
1. Explain the market meaning of the Brand Health Index (BHI) and positive/negative sentiment ratios.
2. Highlight primary customer satisfaction drivers or complaints.
3. Formulate the response in markdown. End the response with a JSON block:
```json
{{
  "status": "success",
  "metrics": {{
    "brand_health_index": {brand_health_index},
    "pos_ratio": {pos_ratio},
    "neg_ratio": {neg_ratio},
    "total_reviews": {total_revs}
  }},
  "flags": {json.dumps(flags)},
  "hitl_required": false
}}
```
"""
        try:
            llm_response = call_llm(system_prompt, user_prompt)
            if llm_response:
                json_match = re.search(r"```json\s*(.*?)\s*```", llm_response, re.DOTALL)
                if json_match:
                    payload = json.loads(json_match.group(1).strip())
                    markdown_report = re.sub(r"```json\s*(.*?)\s*```", "", llm_response, flags=re.DOTALL).strip()
                    return {
                        "findings": payload,
                        "markdown": markdown_report
                    }
        except Exception as e:
            logger.warning(f"LLM sentiment synthesis failed, falling back to static report: {e}")

        # Fallback structured markdown report
        markdown_report = f"""### Brand & Sentiment Diligence: {target_company}
- **Sanitized Search Query:** '{sanitized_query}'
- **Brand Health Index (BHI):** {round(brand_health_index, 2)} (Scale: -1.0 to +1.0)
- **Positive Sentiment Ratio:** {round(pos_ratio * 100, 2)}%
- **Negative Sentiment Ratio:** {round(neg_ratio * 100, 2)}%
- **Total Customer Review Samples:** {total_revs}
- **Data Source:** {data_source}

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
