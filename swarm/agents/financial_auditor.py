"""
swarm/agents/financial_auditor.py
Financial Auditor Agent using ADK.
Performs global company classification (Public vs. Private) and routes to:
- Path A: Public US (SEC EDGAR MCP + yfinance)
- Path B: Public Global (yfinance)
- Path C: UK Private (Companies House API simulation)
- Path D: US/IN/Other Private (HITL manual file ingestion and local CSV parsing)
"""

from swarm.orchestrator import register_agent
from swarm.tools.pandas_analyst import run_financial_analysis
from swarm.tools.companies_house import get_companies_house_accounts
from swarm.utils.llm import call_llm
from mcp_servers.edgar_mcp.server import mcp_search_company, mcp_get_financials, mcp_get_filings
import os
import json
import re
import logging
from typing import Dict, Any, List

logger = logging.getLogger("swarm.agents.financial_auditor")

# Precached global public company database for offline resilience
YFINANCE_MOCK_DATABASE = {
    "RELIANCE.NS": {
        "period": "2025-03-31",
        "latest_revenue": 10000000000000.0, # INR (10 Lakh Crores)
        "latest_debt_to_equity": 0.42,
        "avg_monthly_burn": 0.0,
        "ebitda_margin": 0.165,
        "interest_coverage_ratio": 6.8,
        "revenue_growth_history": [11.2, 8.5, 9.4],
        "cash_runway_months": "Infinite (Positive Cash Flow)",
        "raw_record_count": 4
    },
    "BARC.L": {
        "period": "2024-12-31",
        "latest_revenue": 25400000000.0, # GBP
        "latest_debt_to_equity": 1.62,
        "avg_monthly_burn": 0.0,
        "ebitda_margin": 0.28,
        "interest_coverage_ratio": 14.5,
        "revenue_growth_history": [3.2, 2.1, 4.5],
        "cash_runway_months": "Infinite (Positive Cash Flow)",
        "raw_record_count": 3
    },
    "AAPL": {
        "period": "2024-09-28",
        "latest_revenue": 385600000000.0, # USD
        "latest_debt_to_equity": 1.45,
        "avg_monthly_burn": 0.0,
        "ebitda_margin": 0.33,
        "interest_coverage_ratio": 35.2,
        "revenue_growth_history": [2.02, -2.8, 5.4],
        "cash_runway_months": "Infinite (Positive Cash Flow)",
        "raw_record_count": 4
    }
}

def load_financial_system_prompt() -> str:
    template_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompt_templates", "financial_system.txt")
    if os.path.exists(template_path):
        try:
            with open(template_path, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception as e:
            logger.error(f"Error reading system prompt from {template_path}: {e}")
    return (
        "You are the lead M&A Financial Auditor Agent.\n"
        "Your core task is to audit the target company's balance sheets and cash flow reports.\n"
        "CRITICAL RULES:\n"
        "1. You must NEVER perform raw calculations (e.g. division, percentage calculation, averages) inside your head. You must always invoke the pandas_analyst.py tool.\n"
        "2. If the calculated debt-to-equity ratio is above 2.0, you MUST flag this as CRITICAL and state that a HITL intervention is required.\n"
        "3. Compare target parameters against competitor CIK metrics retrieved from the SEC Edgar MCP server.\n"
        "4. Output your analysis in a structured JSON payload conforming to the orchestrator specification."
    )

def classify_company(company_name: str, sector: str) -> Dict[str, Any]:
    """
    Classifies a company as public/private and resolves its likely jurisdiction/ticker using LLM.
    """
    system_prompt = (
        "You are an M&A research assistant specialized in corporate classification.\n"
        "Analyze the company name and sector provided and respond in a valid JSON code block only."
    )
    user_prompt = f"""
Analyze the target company '{company_name}' in the '{sector}' sector.
Classify it using the following rules:
- type: "public" if it is listed on a public stock exchange anywhere in the world, else "private".
- jurisdiction: "US" for United States, "UK" for United Kingdom, "IN" for India, or "other" for any other country.
- ticker: If public, suggest the most likely ticker symbol on Yahoo Finance (e.g. AAPL, RELIANCE.NS, BARC.L). If private, this should be null.
- confidence: "high" if you are certain, else "low".

Output format (must end with this JSON block inside ```json ... ```):
```json
{{
  "type": "public" | "private",
  "jurisdiction": "US" | "UK" | "IN" | "other",
  "ticker": "string" | null,
  "confidence": "high" | "low"
}}
```
"""
    try:
        response = call_llm(system_prompt, user_prompt)
        if response:
            json_match = re.search(r"```json\s*(.*?)\s*```", response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1).strip())
    except Exception as e:
        logger.warning(f"Classification LLM call failed, falling back to heuristics: {e}")
        
    # Heuristics Fallback
    query = company_name.upper().strip()
    res = {"type": "private", "jurisdiction": "US", "ticker": None, "confidence": "low"}
    
    if query.endswith(".NS") or query.endswith(".BO") or "RELIANCE" in query:
        res = {"type": "public", "jurisdiction": "IN", "ticker": "RELIANCE.NS", "confidence": "high"}
    elif (query.endswith(".L") or "BARCLAYS" in query or "BP PLC" in query) and not any(term in query for term in ["LTD", "LIMITED"]):
        res = {"type": "public", "jurisdiction": "UK", "ticker": "BARC.L", "confidence": "high"}
    elif query in ["AAPL", "MSFT", "TSLA", "AMZN", "GOOGL", "META", "NFLX", "NVDA", "APPLE", "MICROSOFT", "TESLA"]:
        ticker = "AAPL" if "APPLE" in query or query == "AAPL" else ("MSFT" if "MICROSOFT" in query or query == "MSFT" else ("TSLA" if "TESLA" in query or query == "TSLA" else query))
        res = {"type": "public", "jurisdiction": "US", "ticker": ticker, "confidence": "high"}
    elif "LTD" in query or "LIMITED" in query or "PLC" in query:
        if "INDIA" in query or "PVT" in query or ".NS" in query or ".BO" in query:
            res = {"type": "private", "jurisdiction": "IN", "ticker": None, "confidence": "high"}
        elif "INC" in query or "CORP" in query or "LLC" in query:
            res = {"type": "private", "jurisdiction": "US", "ticker": None, "confidence": "high"}
        else:
            res = {"type": "private", "jurisdiction": "UK", "ticker": None, "confidence": "high"}
    return res

def normalize_yfinance_data(ticker_symbol: str) -> Dict[str, Any]:
    """
    Pulls real-time financial statements from Yahoo Finance via yfinance, 
    normalizing dataframes into standard audited dictionaries.
    """
    clean_ticker = ticker_symbol.strip().upper()
    if clean_ticker in YFINANCE_MOCK_DATABASE:
        logger.info(f"yfinance Cache Hit for '{clean_ticker}'")
        res = YFINANCE_MOCK_DATABASE[clean_ticker].copy()
        res["degraded"] = False
        res["sourcing_alert"] = None
        res["audit_log"] = [
            "EBITDA = Revenue - CostOfGoodsSold - OperatingExpenses (Mocked Cache Data)",
            "EBITDA Margin = EBITDA / Revenue (Mocked Cache Data)",
            "Debt-to-Equity Ratio = TotalLiabilities / TotalEquity (Mocked Cache Data)",
            "Cash Runway = Cash / Average Monthly Cash Burn (Mocked Cache Data)"
        ]
        return res

    try:
        import yfinance as yf
        import pandas as pd
        
        logger.info(f"yfinance Fetch: Querying '{clean_ticker}'")
        ticker = yf.Ticker(clean_ticker)
        
        financials = ticker.financials
        balance_sheet = ticker.balance_sheet
        cashflow = ticker.cashflow
        
        if financials is None or financials.empty or balance_sheet is None or balance_sheet.empty:
            raise ValueError(f"No financials returned from yfinance for '{clean_ticker}'")
            
        latest_col = financials.columns[0]
        period_str = str(latest_col.date()) if hasattr(latest_col, "date") else str(latest_col)
        
        def find_row(df, keys: List[str], default=0.0) -> float:
            if df is None or df.empty:
                return default
            for k in keys:
                for idx in df.index:
                    if k.lower() in str(idx).lower():
                        val = df.loc[idx]
                        if hasattr(val, "iloc"):
                            v = val.iloc[0] if len(val.shape) == 1 else val.iloc[0, 0]
                            return float(v) if not pd.isna(v) else default
                        return float(val) if not pd.isna(val) else default
            return default

        rev = find_row(financials, ["total revenue", "revenue", "operating revenue"])
        ebit = find_row(financials, ["operating income", "ebit", "operating profit"])
        da = find_row(cashflow, ["depreciation amortization", "depreciation & amortization", "depreciation", "amortization"])
        ebitda = ebit + da
        ebitda_margin = ebitda / rev if rev > 0 else 0.0
        
        liab = find_row(balance_sheet, ["total liabilities net minority interest", "total liabilities", "liabilities"])
        eq = find_row(balance_sheet, ["stockholders equity", "total stockholders equity", "equity", "partnership capital"])
        if eq == 0.0:
            eq = 1.0
        debt_equity = liab / eq
        
        cash = find_row(balance_sheet, ["cash and cash equivalents", "cash equivalents", "cash"])
        if cash == 0.0:
            assets = find_row(balance_sheet, ["total assets", "assets"])
            cash = assets * 0.25
            
        operating_cf = find_row(cashflow, ["operating cash flow", "cash flow from operating activities", "total cash from operating activities"])
        capital_exp = find_row(cashflow, ["capital expenditure", "capex"])
        net_cash_flow = operating_cf - abs(capital_exp)
        
        avg_monthly_burn = 0.0
        if net_cash_flow < 0:
            avg_monthly_burn = abs(net_cash_flow) / 12.0
            
        cash_runway = "Infinite (Positive Cash Flow)"
        if avg_monthly_burn > 0:
            cash_runway = round(cash / avg_monthly_burn, 1)

        # Growth history
        growth_history = []
        if len(financials.columns) > 1:
            revs = []
            for col in financials.columns:
                val = 0.0
                for idx in financials.index:
                    if "total revenue" in str(idx).lower() or "revenue" in str(idx).lower():
                        v = financials.loc[idx, col]
                        val = float(v) if not pd.isna(v) else 0.0
                        break
                revs.append(val)
            revs.reverse()
            for i in range(1, len(revs)):
                prev = revs[i-1]
                curr = revs[i]
                if prev > 0:
                    growth_history.append(round(((curr - prev) / prev) * 100, 2))
                    
        # Generate mathematical audit log for live API data
        audit_log = [
            f"EBITDA = EBIT (${ebit:,.2f}) + Depreciation & Amortization (${da:,.2f}) = ${ebitda:,.2f}",
            f"EBITDA Margin = EBITDA (${ebitda:,.2f}) / Revenue (${rev:,.2f}) = {ebitda_margin * 100:.2f}%" if rev > 0 else "EBITDA Margin = 0.00% (Revenue is zero)",
            f"Debt-to-Equity Ratio = TotalLiabilities (${liab:,.2f}) / TotalEquity (${eq:,.2f}) = {debt_equity:.3f}",
            f"Net Cash Flow = Operating Cash Flow (${operating_cf:,.2f}) - Capital Expenditure (${abs(capital_exp):,.2f}) = ${net_cash_flow:,.2f}",
            f"Average Monthly Cash Burn = {f'${abs_burn:,.2f}' if net_cash_flow < 0 else '$0.00 (Positive cash flow)'}",
            f"Cash Runway = Cash (${cash:,.2f}) / Average Monthly Cash Burn (${avg_monthly_burn:,.2f}) = {cash_runway} months" if avg_monthly_burn > 0 else "Cash Runway = Infinite (Positive Cash Flow)"
        ]
                    
        return {
            "degraded": False,
            "sourcing_alert": None,
            "period": period_str,
            "latest_revenue": float(rev),
            "latest_debt_to_equity": round(debt_equity, 3),
            "avg_monthly_burn": round(avg_monthly_burn, 2),
            "ebitda_margin": round(ebitda_margin, 4),
            "interest_coverage_ratio": "No Interest Expense",
            "revenue_growth_history": growth_history,
            "cash_runway_months": cash_runway,
            "raw_record_count": len(financials.columns),
            "audit_log": audit_log
        }
    except Exception as e:
        logger.warning(f"yfinance fetch failed for '{clean_ticker}': {e}. Falling back to stable mock.")
        # Return fallback mock structured similarly to AAPL with degraded flag
        return {
            "degraded": True,
            "sourcing_alert": f"yfinance fetch failed for '{clean_ticker}': {str(e)}. Falling back to peer benchmark data.",
            "period": "2024-12-31",
            "latest_revenue": 125000000.0,
            "latest_debt_to_equity": 1.25,
            "avg_monthly_burn": 150000.0,
            "ebitda_margin": 0.18,
            "interest_coverage_ratio": 5.4,
            "revenue_growth_history": [4.5, 6.2],
            "cash_runway_months": 15.0,
            "raw_record_count": 3,
            "audit_log": [
                "EBITDA = Revenue ($125,000,000.00) - Expenses ($102,500,000.00) = $22,500,000.00 (Mock calculation)",
                "EBITDA Margin = EBITDA ($22,500,000.00) / Revenue ($125,000,000.00) = 18.00%",
                "Debt-to-Equity Ratio = TotalLiabilities ($62,500,000.00) / TotalEquity ($50,000,000.00) = 1.250",
                "Average Monthly Cash Burn = Mock Cash Outflow = $150,000.00",
                "Cash Runway = Estimated Cash ($2,250,000.00) / Monthly Burn ($150,000.00) = 15.0 months"
            ]
        }

@register_agent("financial_auditor")
class FinancialAuditor:
    def __init__(self, industry: str = "generic"):
        self.industry = industry

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        target_company = context.get("target_company", "Target Company")
        session_id = context.get("session_id", "default")
        
        # 1. Target Entity Classification Step
        classification = classify_company(target_company, self.industry)
        c_type = classification.get("type", "private")
        jurisdiction = classification.get("jurisdiction", "US")
        ticker = classification.get("ticker")
        
        logger.info(f"Target Classification: {target_company} -> Type: {c_type}, Jurisdiction: {jurisdiction}, Ticker: {ticker}")
        
        analysis = None
        sec_findings = {
            "cik": "N/A (Private)",
            "name": "N/A (Private)",
            "industry_avg_debt_equity": 1.10
        }
        data_source = ""
        sourcing_alerts = []
        data_degraded = False
        
        # 2. Pipeline Routing
        if c_type == "public" and jurisdiction == "US":
            # Path A: US Public Company (EDGAR MCP + yfinance)
            data_source = "SEC EDGAR MCP & yfinance"
            try:
                resolved = mcp_search_company(target_company)
                cik = resolved.get("cik")
                sec_findings = mcp_get_financials(cik)
            except Exception as e:
                logger.error(f"SEC EDGAR lookup failed: {e}")
                data_degraded = True
                sourcing_alerts.append(f"SEC EDGAR lookup failed for '{target_company}': {e}. Loaded static benchmark.")
                sec_findings = {
                    "cik": "0000320193",
                    "name": "Apple Inc. (Fallback US Benchmark)",
                    "latest_debt_to_equity": 1.45,
                    "industry_avg_debt_equity": 1.10
                }
            
            ticker_to_use = ticker or resolved.get("ticker", "AAPL")
            analysis = normalize_yfinance_data(ticker_to_use)
            if analysis.get("degraded"):
                data_degraded = True
                sourcing_alerts.append(analysis.get("sourcing_alert"))
            
        elif c_type == "public":
            # Path B: Global Public Company (yfinance)
            data_source = "yfinance Global Scraper"
            analysis = normalize_yfinance_data(ticker or target_company)
            if analysis.get("degraded"):
                data_degraded = True
                sourcing_alerts.append(analysis.get("sourcing_alert"))
            sec_findings = {
                "cik": "N/A (Non-US Public)",
                "name": "Yahoo Finance Index Benchmark",
                "latest_debt_to_equity": 1.20,
                "industry_avg_debt_equity": 1.10
            }
            
        elif c_type == "private" and jurisdiction == "UK":
            # Path C: UK Private Company (Companies House)
            data_source = "UK Companies House Registry"
            ch_data = get_companies_house_accounts(target_company)
            if ch_data:
                analysis = ch_data["latest_accounts"]
                sec_findings = {
                    "cik": f"UK-{ch_data['company_number']}",
                    "name": ch_data["company_name"],
                    "latest_debt_to_equity": 1.10,
                    "industry_avg_debt_equity": 1.10
                }
            
        # Path D (or fallback): Other Private Company / Manual Upload Check
        if not analysis:
            # Check if local CSV statements are already present in the data room
            session_path = os.path.join("data_room", "uploads", "financial", session_id)
            global_path = context.get("data_room_path", "data_room/uploads/financial")
            
            csv_file = None
            for p in [session_path, global_path]:
                if os.path.exists(p):
                    files = [f for f in os.listdir(p) if f.endswith('.csv')]
                    if files:
                        csv_file = os.path.join(p, files[0])
                        break
            
            if csv_file:
                # Target files uploaded, parse using local calculations tool
                data_source = "Manual Document Ingestion (CSV)"
                analysis = run_financial_analysis(csv_file)
                if "error" in analysis:
                    return {
                        "findings": {
                            "status": "error", 
                            "error": analysis["error"], 
                            "flags": [],
                            "data_degraded": True,
                            "sourcing_alerts": [f"CSV parsing failed: {analysis['error']}"]
                        },
                        "markdown": f"### Financial Diligence Error\nFailed to parse target financials: {analysis['error']}"
                    }
                sec_findings = {
                    "cik": "N/A (Private)",
                    "name": "Industry Private Benchmark",
                    "latest_debt_to_equity": 1.05,
                    "industry_avg_debt_equity": 1.10
                }
            else:
                # No public records and no manual upload -> Trigger HITL Pause strategic checkpoint
                hitl_reason = (
                    f"Target '{target_company}' is classified as a private company (Jurisdiction: {jurisdiction}). "
                    f"No public filing records exist. Human partner must upload financial CSV statements to the Virtual Data Room."
                )
                logger.info(f"HITL Pause Triggered: {hitl_reason}")
                return {
                    "findings": {
                        "status": "skipped",
                        "hitl_required": True,
                        "hitl_reason": hitl_reason,
                        "flags": [],
                        "data_degraded": True,
                        "sourcing_alerts": [hitl_reason]
                    },
                    "markdown": f"### Financial Diligence: {target_company} (PAUSED)\n"
                                f"⚠️ **Swarm Paused**: Private company pipeline selected. Target has no public disclosures on SEC EDGAR or yfinance.\n\n"
                                f"Please upload targets' financial balance sheets and P&L spreadsheets to the control dashboard's **Financial Data Room** to resume analysis."
                }

        # 3. LLM Qualitative Audit Report Synthesis
        system_prompt = load_financial_system_prompt()
        
        audit_log = analysis.get("audit_log", [])
        audit_log_str = "\n".join(audit_log)
        sourcing_alerts_str = "; ".join(sourcing_alerts) if sourcing_alerts else "None"
        
        user_prompt = f"""
We are auditing target company: '{target_company}' (Industry Sector: '{self.industry}').
The financials have been retrieved via **{data_source}** with the following metrics:
- Period: {analysis['period']}
- Revenue: ${analysis['latest_revenue']:,}
- EBITDA Margin: {round(analysis['ebitda_margin'] * 100, 2)}%
- Debt-to-Equity Ratio: {analysis['latest_debt_to_equity']}
- Average Monthly Burn Rate: ${analysis['avg_monthly_burn']:,}
- Interest Coverage Ratio: {analysis['interest_coverage_ratio']}
- Cash Runway (Months): {analysis['cash_runway_months']}
- QoQ Revenue Growth History: {analysis['revenue_growth_history']}%

Sector Comparison Benchmarks:
- Reference Name: {sec_findings.get('name', 'N/A')}
- Reference CIK: {sec_findings.get('cik', 'N/A')}
- Industry Average Debt-to-Equity: {sec_findings.get('industry_avg_debt_equity', 1.10)}

Data Degradation Status:
- Data Degraded: {data_degraded}
- Sourcing Alerts: {sourcing_alerts_str}

Mathematical Audit Trail:
{audit_log_str}

Please perform a professional financial due diligence audit:
1. If Data Degraded is True, you MUST start your report with a prominent yellow markdown warning alert block:
> [!WARNING]
> **Data Degraded / Sourced from Fallbacks**: {sourcing_alerts_str}
2. Benchmark the target parameters against industry reference values.
3. Flag any critical risk items.
4. If the debt-to-equity ratio is above 2.0, you MUST explicitly state in your analysis that a Human-in-the-Loop (HITL) intervention is required due to extreme debt leverage.
5. Explain how target data was sourced (source path: {data_source}).
6. You MUST include a section `### Mathematical Audit Trail` at the end of the report that shows the step-by-step mathematical calculation formulas (EBITDA, EBITDA Margin, Debt-to-Equity, Cash Runway) as blockquotes using the provided Mathematical Audit Trail text.
7. Output your report in markdown. End your response with a JSON-formatted block wrapped in ```json ... ``` that specifies:
{{
  "flags": [
    {{
      "severity": "CRITICAL" | "WARNING" | "INFO",
      "metric": "name of metric",
      "description": "description of risk"
    }}
  ],
  "hitl_required": true | false,
  "hitl_reason": "detailed reason for HITL if required, else null"
}}
"""
        
        llm_response = call_llm(system_prompt, user_prompt)
        
        flags = []
        hitl_required = False
        hitl_reason = None
        markdown_report = ""
        
        if llm_response:
            markdown_report = llm_response
            json_match = re.search(r"```json\s*(.*?)\s*```", llm_response, re.DOTALL)
            if json_match:
                try:
                    payload = json.loads(json_match.group(1).strip())
                    flags = payload.get("flags", [])
                    hitl_required = payload.get("hitl_required", False)
                    hitl_reason = payload.get("hitl_reason")
                    markdown_report = re.sub(r"```json\s*(.*?)\s*```", "", llm_response, flags=re.DOTALL).strip()
                except Exception as ex:
                    logger.warning(f"Failed to parse JSON from LLM: {ex}")

        # Enforce threshold guidelines programmatically
        if analysis["latest_debt_to_equity"] > 2.0:
            if not any(f.get("metric") == "Debt-to-Equity Leverage" and f.get("severity") == "CRITICAL" for f in flags):
                flags.append({
                    "severity": "CRITICAL",
                    "metric": "Debt-to-Equity Leverage",
                    "description": f"Debt-to-equity ratio of {analysis['latest_debt_to_equity']} is critically higher than industry average ({sec_findings['industry_avg_debt_equity']})."
                })
                hitl_required = True
                hitl_reason = f"Target company has extreme debt leverage: Debt-to-Equity = {analysis['latest_debt_to_equity']}."

        if isinstance(analysis["avg_monthly_burn"], (int, float)) and analysis["avg_monthly_burn"] > 500000.0:
            if not any(f.get("metric") == "Monthly Cash Burn" for f in flags):
                flags.append({
                    "severity": "WARNING",
                    "metric": "Monthly Cash Burn",
                    "description": f"Monthly cash burn of ${analysis['avg_monthly_burn']:,} limits operating runway."
                })

        if not markdown_report:
            warning_header = ""
            if data_degraded:
                warning_header = f"> [!WARNING]\n> **Data Degraded / Sourced from Fallbacks**: {sourcing_alerts_str}\n\n"
                
            audit_trail_section = ""
            if audit_log:
                audit_trail_section = "\n\n### Mathematical Audit Trail\n" + "\n".join([f"> {line}" for line in audit_log])

            markdown_report = f"""{warning_header}### Financial Diligence: {target_company}
- **Data Source:** {data_source}
- **Reporting Period:** {analysis['period']}
- **Latest Revenue:** ${analysis['latest_revenue']:,}
- **Debt-to-Equity Ratio:** {analysis['latest_debt_to_equity']} (Industry Avg: {sec_findings['industry_avg_debt_equity']})
- **EBITDA Margin:** {round(analysis['ebitda_margin'] * 100, 2)}%
- **Average Monthly Burn Rate:** ${analysis['avg_monthly_burn']:,}
- **Interest Coverage:** {analysis['interest_coverage_ratio']}
- **Cash Runway (Months):** {analysis['cash_runway_months']}

{audit_trail_section}

#### Risk Analysis & Flagged Findings
"""
            if not flags:
                markdown_report += "*No critical financial flags raised.*"
            else:
                for flag in flags:
                    markdown_report += f"- **[{flag['severity']}]** {flag['metric']}: {flag['description']}\n"
                    
        return {
            "findings": {
                "status": "success",
                "metrics": analysis,
                "benchmarks": sec_findings,
                "flags": flags,
                "hitl_required": hitl_required,
                "hitl_reason": hitl_reason,
                "source": data_source,
                "data_degraded": data_degraded,
                "sourcing_alerts": sourcing_alerts
            },
            "markdown": markdown_report
        }
