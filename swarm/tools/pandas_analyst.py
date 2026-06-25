"""
swarm/tools/pandas_analyst.py
Quantitative calculations tool for parsing Target financial sheets.
Ensures zero calculations are performed inside the LLM context.
"""

import pandas as pd
import numpy as np
import logging
import json
import re
from typing import Dict, Any, List
from swarm.utils.llm import call_llm

logger = logging.getLogger("swarm.tools.pandas_analyst")

SYNONYM_MAP = {
    'Period': ['period', 'year', 'qtr', 'quarter', 'date', 'time', 'reporting period', 'period end'],
    'Revenue': ['revenue', 'sales', 'turnover', 'total revenue', 'total sales', 'operating revenue', 'gross sales', 'revenue (usd)', 'revenue (inr)', 'revenue (gbp)'],
    'CostOfGoodsSold': ['costofgoodssold', 'cogs', 'cost of sales', 'cost of goods sold', 'cost of revenue', 'cost of goods', 'direct costs'],
    'OperatingExpenses': ['operatingexpenses', 'opex', 'operating expenses', 'sg&a', 'admin expenses', 'total opex', 'indirect expenses'],
    'CashInflow': ['cashinflow', 'cash inflow', 'operating cash inflow', 'cash receipts', 'total cash inflow', 'sources of cash'],
    'CashOutflow': ['cashoutflow', 'cash outflow', 'operating cash outflow', 'cash payments', 'total cash outflow', 'uses of cash'],
    'TotalAssets': ['totalassets', 'assets', 'total assets', 'assets total'],
    'TotalLiabilities': ['totalliabilities', 'liabilities', 'total liabilities', 'liabilities total'],
    'TotalEquity': ['totalequity', 'equity', 'total equity', 'stockholders equity', 'shareholder equity', 'partnership capital', 'owner equity'],
    'Cash': ['cash', 'cash & cash equivalents', 'cash equivalents', 'cash and cash equivalents', 'ending cash', 'cash at hand']
}

def align_csv_headers(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalizes column headers in the dataframe using fuzzy/heuristic matching.
    """
    col_mapping = {}
    for standard_col, synonyms in SYNONYM_MAP.items():
        # Normalize synonyms for easier comparison (lowercase, alphanumeric only)
        norm_synonyms = [re.sub(r'[^a-z0-9]', '', s.lower()) for s in synonyms]
        for col in df.columns:
            norm_col = re.sub(r'[^a-z0-9]', '', str(col).lower())
            if norm_col in norm_synonyms:
                col_mapping[col] = standard_col
                break
    
    if col_mapping:
        df = df.rename(columns=col_mapping)
    return df

def llm_map_headers(columns: List[str], required: List[str]) -> Dict[str, str]:
    """
    Uses LLM to map existing columns to missing required columns.
    """
    system_prompt = (
        "You are a data cleaning assistant specialized in financial schema mapping.\n"
        "Respond ONLY with a valid JSON block containing column mapping pairs. Do not include any explanation."
    )
    user_prompt = f"""
We have a financial CSV with these columns: {columns}
We need to map them to these missing standard columns: {required}

Map each missing standard column to the most suitable CSV column. If a column cannot be mapped, map it to null.
Output JSON format (wrap it in ```json ... ```):
```json
{{
  "StandardColumnName": "CSVColumnName"
}}
```
"""
    try:
        response = call_llm(system_prompt, user_prompt)
        if response:
            json_match = re.search(r"```json\s*(.*?)\s*```", response, re.DOTALL)
            if json_match:
                mapping = json.loads(json_match.group(1).strip())
                # Filter out null values and ensure mapped column exists in source columns
                return {k: v for k, v in mapping.items() if v is not None and v in columns}
    except Exception as e:
        logger.error(f"LLM header mapping failed: {e}")
    return {}

def run_financial_analysis(csv_path: str) -> Dict[str, Any]:
    """
    Parses financial statements from the target data room and calculates:
      - EBITDA Margins
      - Monthly Cash Burn Rates
      - Debt-to-Equity Leverage
      - Interest Coverage Ratio (Solvency)
      - QoQ Revenue growth percentages
    
    Includes robust checks for missing columns and divide-by-zero errors.
    """
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        logger.error(f"Failed to read CSV at {csv_path}: {str(e)}")
        return {"error": f"Invalid or missing CSV: {str(e)}"}

    # Define required columns
    required_cols = [
        'Period', 'Revenue', 'CostOfGoodsSold', 'OperatingExpenses', 
        'CashInflow', 'CashOutflow', 'TotalAssets', 'TotalLiabilities', 
        'TotalEquity'
    ]
    
    # 1. Run Fuzzy Alignment
    df = align_csv_headers(df)
    
    # 2. Check for missing columns
    missing_cols = [col for col in required_cols if col not in df.columns]
    
    # 3. Trigger LLM fallback if there are missing columns
    if missing_cols:
        logger.info(f"Fuzzy matching missed columns: {missing_cols}. Invoking LLM header mapping.")
        llm_mapping = llm_map_headers(df.columns.tolist(), missing_cols)
        if llm_mapping:
            df = df.rename(columns={v: k for k, v in llm_mapping.items()})
            missing_cols = [col for col in required_cols if col not in df.columns]
            
    if missing_cols:
        error_msg = f"Missing required columns in CSV: {missing_cols}"
        logger.error(error_msg)
        return {"error": error_msg}

    # Ensure clean datatypes (fill NaNs and convert to float)
    for col in required_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
            
    if 'Cash' in df.columns:
        df['Cash'] = pd.to_numeric(df['Cash'], errors='coerce').fillna(0.0)

    # 1. Compute EBITDA (Revenue - Cost of Goods Sold - Operating Expenses)
    df['EBITDA'] = df['Revenue'] - df['CostOfGoodsSold'] - df['OperatingExpenses']
    
    # 2. Compute Net Cash Flow
    df['NetCashFlow'] = df['CashInflow'] - df['CashOutflow']

    # Retrieve last period row
    latest_row = df.iloc[-1]
    
    # 3. Compute Debt-to-Equity Ratio
    equity_val = float(latest_row['TotalEquity'])
    original_equity = equity_val
    if equity_val == 0.0:
        logger.warning("TotalEquity is zero. Using $1.0 to prevent division by zero.")
        equity_val = 1.0
    debt_to_equity = float(latest_row['TotalLiabilities']) / equity_val

    # 4. Compute Average Monthly Cash Burn Rate (Only select periods where net flow was negative)
    negative_flows = df[df['NetCashFlow'] < 0]['NetCashFlow']
    avg_monthly_burn = float(negative_flows.mean()) if not negative_flows.empty else 0.0

    # 5. Compute EBITDA Margin
    rev_val = float(latest_row['Revenue'])
    ebitda_margin = float(latest_row['EBITDA']) / rev_val if rev_val > 0.0 else 0.0

    # 6. Compute Interest Coverage Ratio
    interest_expense = 0.0
    if 'InterestExpense' in df.columns:
        interest_expense = float(latest_row['InterestExpense'])
    
    if interest_expense > 0.0:
        interest_coverage = float(latest_row['EBITDA']) / interest_expense
    else:
        interest_coverage = "No Interest Expense"

    # 7. Compute QoQ Growth
    growth_series = df['Revenue'].pct_change().fillna(0.0)
    growth_history = [round(val * 100, 2) for val in growth_series.tolist()[1:]]

    # 8. Compute Cash Runway (remaining months of cash)
    cash_val = float(latest_row['Cash']) if 'Cash' in df.columns else float(latest_row['TotalAssets']) * 0.25
    abs_burn = abs(avg_monthly_burn)
    if abs_burn > 0.0:
        cash_runway = round(cash_val / abs_burn, 1)
    else:
        cash_runway = "Infinite (Positive Cash Flow)"

    # 9. Generate Step-by-Step Mathematical Audit Trail
    audit_log = []
    
    # EBITDA trace
    rev_f = latest_row['Revenue']
    cogs_f = latest_row['CostOfGoodsSold']
    opex_f = latest_row['OperatingExpenses']
    ebitda_f = latest_row['EBITDA']
    audit_log.append(
        f"EBITDA = Revenue (${rev_f:,.2f}) - CostOfGoodsSold (${cogs_f:,.2f}) - OperatingExpenses (${opex_f:,.2f}) = ${ebitda_f:,.2f}"
    )
    
    # EBITDA Margin trace
    audit_log.append(
        f"EBITDA Margin = EBITDA (${ebitda_f:,.2f}) / Revenue (${rev_f:,.2f}) = {ebitda_margin * 100:.2f}%" if rev_f > 0.0 
        else f"EBITDA Margin = EBITDA (${ebitda_f:,.2f}) / Revenue ($0.00) = 0.00% (Revenue is zero)"
    )
    
    # Debt-to-Equity trace
    liab_f = latest_row['TotalLiabilities']
    audit_log.append(
        f"Debt-to-Equity Ratio = TotalLiabilities (${liab_f:,.2f}) / TotalEquity (${original_equity:,.2f}) = {debt_to_equity:.3f}" if original_equity != 0.0
        else f"Debt-to-Equity Ratio = TotalLiabilities (${liab_f:,.2f}) / TotalEquity ($0.00) [adjusted to $1.00 to avoid div-by-zero] = {debt_to_equity:.3f}"
    )
    
    # Average Monthly Cash Burn trace
    neg_flow_count = len(negative_flows)
    if neg_flow_count > 0:
        sum_neg_flows = negative_flows.sum()
        audit_log.append(
            f"Average Monthly Cash Burn = Sum of negative net cash flows (${sum_neg_flows:,.2f}) / negative periods ({neg_flow_count}) = ${abs_burn:,.2f}"
        )
    else:
        audit_log.append(
            f"Average Monthly Cash Burn = No periods with negative net cash flow = $0.00"
        )
        
    # Cash Runway trace
    cash_source = "Cash" if 'Cash' in df.columns else "TotalAssets * 0.25 (estimated)"
    if abs_burn > 0.0:
        audit_log.append(
            f"Cash Runway = {cash_source} (${cash_val:,.2f}) / Average Monthly Cash Burn (${abs_burn:,.2f}) = {cash_runway} months"
        )
    else:
        audit_log.append(
            f"Cash Runway = {cash_source} (${cash_val:,.2f}) / Average Monthly Cash Burn ($0.00) = Infinite (Positive Cash Flow)"
        )

    return {
        "period": str(latest_row['Period']),
        "latest_revenue": float(latest_row['Revenue']),
        "latest_debt_to_equity": round(debt_to_equity, 3),
        "avg_monthly_burn": round(abs_burn, 2),
        "ebitda_margin": round(ebitda_margin, 4),
        "interest_coverage_ratio": interest_coverage if isinstance(interest_coverage, str) else round(interest_coverage, 2),
        "revenue_growth_history": growth_history,
        "cash_runway_months": cash_runway,
        "raw_record_count": len(df),
        "audit_log": audit_log
    }

