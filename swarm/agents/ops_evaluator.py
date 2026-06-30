"""
swarm/agents/ops_evaluator.py
Operations Evaluator Agent using ADK. Audits customer support feedback, 
fulfillment efficiency, and employee sentiment using a Hybrid AI Filter.
"""

from swarm.orchestrator import register_agent
from swarm.utils.llm import call_llm
import os
import re
import json
import pandas as pd
import logging
from typing import Dict, Any, List

logger = logging.getLogger("swarm.agents.ops_evaluator")

def load_ops_system_prompt() -> str:
    """Loads system prompt for operations agent analysis."""
    template_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompt_templates", "ops_system.txt")
    if os.path.exists(template_path):
        try:
            with open(template_path, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception as e:
            logger.error(f"Error reading system prompt from {template_path}: {e}")
    return (
        "You are the lead M&A Operations Inspector Agent.\n"
        "Your core task is to evaluate real-world customer support, fulfillment efficiency, and employee organizational health.\n\n"
        "CRITICAL RULES:\n"
        "1. Evaluate customer support quality and fulfillment delays by analyzing customer reviews (Rating, Category == Support or Delivery).\n"
        "2. Evaluate employee retention, workload, and turnover risks by analyzing employee feedback (Rating, Category == Management or Work-Life Balance).\n"
        "3. If Customer Support Index (CSI) or Employee Sentiment Index (ESI) is negative or below 50%, raise a WARNING flag detailing the issues.\n"
        "4. Output your analysis in a structured JSON payload conforming to the orchestrator specification."
    )

@register_agent("ops_evaluator")
class OperationsEvaluator:
    def __init__(self, industry: str = "generic"):
        self.industry = industry.strip().lower()

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes the business-centric operational audit using a Hybrid AI Filter.
        """
        target_company = context.get("target_company", "Target Company")
        session_id = context.get("session_id", "default")
        
        # Read Wave 1 context for cash runway checks (orchestrator compatibility)
        wave_1 = context.get("wave_1_context", {})
        fin_auditor = wave_1.get("financial_auditor", {})
        cash_runway = fin_auditor.get("cash_runway_months", "Infinite (Positive Cash Flow)")
        is_runway_short = False
        if isinstance(cash_runway, (int, float)) and cash_runway < 12.0:
            is_runway_short = True
        
        # Locate operations log file (customer/employee reviews CSV)
        session_log_dir = os.path.join("data_room", "uploads", "logs", session_id)
        global_log_dir = context.get("data_room_path", "data_room/uploads/logs")
        selected_path = session_log_dir if os.path.exists(session_log_dir) else global_log_dir
        
        csv_file = None
        if os.path.exists(selected_path):
            files = [f for f in os.listdir(selected_path) if f.endswith('.csv')]
            if files:
                csv_file = os.path.join(selected_path, files[0])
        
        df = None
        data_source = "Simulated Public Review Indices"
        if csv_file:
            try:
                df = pd.read_csv(csv_file)
                data_source = f"Target Document Ingestion ({os.path.basename(csv_file)})"
                required = ['ReviewText', 'Rating', 'Category']
                if not all(col in df.columns for col in required):
                    logger.warning(f"CSV missing required columns {required}, falling back to mock.")
                    df = None
            except Exception as e:
                logger.error(f"Failed to read ops log CSV: {e}")
                df = None
        
        # Create default mock data if no valid CSV was found
        if df is None:
            mock_data = [
                {"Category": "Support", "Rating": 5, "ReviewText": "Support resolved my issue in 5 minutes! Excellent service."},
                {"Category": "Support", "Rating": 4, "ReviewText": "Very polite agent, though took a day to get back to me."},
                {"Category": "Support", "Rating": 3, "ReviewText": "Support was average. They eventually fixed it but response was slow."},
                {"Category": "Support", "Rating": 2, "ReviewText": "Terrible response time. Waited three days for a standard reply."},
                {"Category": "Delivery", "Rating": 5, "ReviewText": "Super fast shipping, package arrived in perfect shape."},
                {"Category": "Delivery", "Rating": 1, "ReviewText": "Package was delayed for over a week and box was damaged."},
                {"Category": "Management", "Rating": 4, "ReviewText": "Great team members, but management can be slow to make decisions."},
                {"Category": "Work-Life Balance", "Rating": 3, "ReviewText": "Workload is alright, but overtime is starting to increase due to turnover."},
                {"Category": "Work-Life Balance", "Rating": 5, "ReviewText": "Flexible hours, very supportive culture."},
                {"Category": "Work-Life Balance", "Rating": 2, "ReviewText": "High workload, lots of overtime required. People are burning out."}
            ]
            df = pd.DataFrame(mock_data)

        # Normalize categories to lower case
        df['Category_Normalized'] = df['Category'].str.strip().str.lower()
        
        # Group categories
        cust_categories = ['support', 'delivery', 'customer support', 'customer service']
        emp_categories = ['management', 'work-life balance', 'culture', 'employees']
        
        cust_df = df[df['Category_Normalized'].isin(cust_categories)]
        emp_df = df[df['Category_Normalized'].isin(emp_categories)]
        
        # Partition data: numerical checks (Rating 1 & 2 -> Negative, 4 & 5 -> Positive)
        strongly_negative = df[df['Rating'] <= 2].to_dict('records')
        strongly_positive = df[df['Rating'] >= 4].to_dict('records')
        ambiguous = df[df['Rating'] == 3].to_dict('records')
        
        # Batch LLM classify ambiguous (Rating 3) reviews
        classified_negative_ambiguous = self._classify_ambiguous_reviews(ambiguous)
        
        # Combine all negative/risk reviews
        operational_risks = strongly_negative + classified_negative_ambiguous
        
        # 1. Calculate Customer Support Index (CSI)
        csi = 1.0
        delivery_complaints_count = 0
        if not cust_df.empty:
            # Positive reviews are those with Rating >= 4 (which are not flagged as negative)
            # Or simpler: count reviews where Rating >= 4 out of all customer reviews
            pos_cust_count = len(cust_df[cust_df['Rating'] >= 4])
            csi = pos_cust_count / len(cust_df)
            
            # Count delivery/fulfillment delay issues from confirmed operational risks
            cust_risks = [r for r in operational_risks if r['Category_Normalized'] in cust_categories]
            delivery_complaints_count = len(cust_risks)
            
        # 2. Calculate Employee Sentiment Index (ESI)
        esi = 1.0
        turnover_complaints_count = 0
        if not emp_df.empty:
            pos_emp_count = len(emp_df[emp_df['Rating'] >= 4])
            esi = pos_emp_count / len(emp_df)
            
            # Count turnover/burnout issues from confirmed operational risks
            emp_risks = [r for r in operational_risks if r['Category_Normalized'] in emp_categories]
            turnover_complaints_count = len(emp_risks)

        # Build flags list
        flags = []
        
        # Propagate cash runway warning
        if is_runway_short:
            msg = f"WARNING: Target company has short cash runway ({cash_runway} months). Operational expenditures (OpEx) must be audited for cost reduction opportunities."
            flags.append({
                "severity": "CRITICAL",
                "metric": "Cash Runway",
                "message": msg,
                "description": msg
            })
            
        if csi < 0.50:
            msg = f"Low Customer Support Index ({round(csi * 100, 1)}%). Customers report high support friction or delivery delays."
            flags.append({
                "severity": "WARNING",
                "metric": "Customer Support Index",
                "message": msg,
                "description": msg
            })
            
        if esi < 0.50:
            msg = f"Low Employee Sentiment Index ({round(esi * 100, 1)}%). High risk of employee burnout or management turnover."
            flags.append({
                "severity": "WARNING",
                "metric": "Employee Sentiment Index",
                "message": msg,
                "description": msg
            })

        metrics = {
            "csi": csi,
            "delivery_issues": delivery_complaints_count,
            "esi": esi,
            "turnover_issues": turnover_complaints_count,
            "total_reviews": len(df)
        }

        # Format the pre-filtered negative reviews for final synthesis (low token cost)
        formatted_risks = ""
        for idx, rev in enumerate(operational_risks[:15]): # Limit to top 15 to safeguard token size
            formatted_risks += f"- Rating: {rev['Rating']} | Category: {rev['Category']} | Text: {rev['ReviewText']}\n"
        if not formatted_risks:
            formatted_risks = "No significant operational risk reviews identified."

        # Synthesize final narrative report via LLM
        system_prompt = load_ops_system_prompt()
        user_prompt = f"""
We are auditing target company: '{target_company}' (Industry Sector: '{self.industry}').
The operational review logs have been audited (Source: {data_source}):
- Customer Support Index (CSI): {round(csi * 100, 2)}%
- Logistical/Delivery Issues Flagged: {delivery_complaints_count}
- Employee Sentiment Index (ESI): {round(esi * 100, 2)}%
- Employee Burnout/Turnover Warnings Flagged: {turnover_complaints_count}
- Total Review Records Audited: {len(df)}

Here is the pre-filtered subset of reviews flagged with operational risks:
{formatted_risks}

Please synthesize a professional operations due diligence audit:
1. Explain the operational meaning of the Customer Support Index (CSI) and Employee Sentiment Index (ESI).
2. Detail the potential risks associated with the reported delivery complaints or turnover warnings.
3. Incorporate any strategic runway warnings if the company has high financial strain.
4. Formulate the response in markdown. End the response with a JSON block:
```json
{{
  "status": "success",
  "metrics": {{
    "csi": {csi},
    "delivery_issues": {delivery_complaints_count},
    "esi": {esi},
    "turnover_issues": {turnover_complaints_count},
    "total_reviews": {len(df)}
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
                    return {
                        "findings": payload,
                        "markdown": llm_response
                    }
        except Exception as e:
            logger.warning(f"LLM synthesis failed, falling back to static report: {e}")

        # Fallback static report
        markdown_report = f"""### Operations Diligence: Customer & Organizational Health
- **Customer Support Index (CSI):** {round(csi * 100, 1)}%
- **Logistical / Delivery Issues:** {delivery_complaints_count} flagged
- **Employee Sentiment Index (ESI):** {round(esi * 100, 1)}%
- **Employee Turnover / Burnout Warnings:** {turnover_complaints_count} flagged
- **Audit Source:** {data_source}

#### Operational Findings & Warnings
"""
        if not flags:
            markdown_report += "*Operational indicators meet general business stability baselines.*"
        else:
            for flag in flags:
                markdown_report += f"- **[{flag['severity']}]** {flag['metric']}: {flag['description']}\n"

        return {
            "findings": {
                "status": "success",
                "metrics": metrics,
                "flags": flags,
                "hitl_required": False
            },
            "markdown": markdown_report
        }

    def _classify_ambiguous_reviews(self, reviews: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Uses LLM to perform high-accuracy sentiment classification on a batch of ambiguous (rating 3) reviews."""
        if not reviews:
            return []
        
        formatted_list = ""
        for idx, rev in enumerate(reviews):
            formatted_list += f"ID: {idx} | Category: {rev['Category']} | Text: {rev['ReviewText']}\n"
            
        system_prompt = (
            "You are a sentiment classification system. Your job is to analyze rating 3 reviews "
            "and determine if they contain operational risks (burnout, high turnover, poor management, "
            "delivery delays, slow support response, package damage, or refund issues)."
        )
        
        user_prompt = f"""
Analyze the following rating-3 reviews and classify each.
Respond with a JSON list containing the IDs of reviews that contain operational risks or negative sentiment.
Reviews list:
{formatted_list}

Response format:
```json
[id_number, id_number, ...]
```
"""
        try:
            response = call_llm(system_prompt, user_prompt)
            if response:
                json_match = re.search(r"```json\s*(.*?)\s*```", response, re.DOTALL)
                if json_match:
                    negative_ids = json.loads(json_match.group(1).strip())
                    return [reviews[i] for i in negative_ids if 0 <= i < len(reviews)]
        except Exception as e:
            logger.warning(f"Batch LLM sentiment classification failed, treating all as negative: {e}")
            return reviews
        return []
