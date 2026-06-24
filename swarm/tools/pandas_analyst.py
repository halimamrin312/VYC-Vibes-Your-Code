"""
swarm/tools/pandas_analyst.py
Quantitative calculations tool for parsing Target financial sheets.
Ensures zero calculations are performed inside the LLM context.
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, Any, List

logger = logging.getLogger("swarm.tools.pandas_analyst")

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

    # Define required columns and check presence
    required_cols = [
        'Period', 'Revenue', 'CostOfGoodsSold', 'OperatingExpenses', 
        'CashInflow', 'CashOutflow', 'TotalAssets', 'TotalLiabilities', 
        'TotalEquity'
    ]
    
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        error_msg = f"Missing required columns in CSV: {missing_cols}"
        logger.error(error_msg)
        return {"error": error_msg}

    # Ensure clean datatypes (fill NaNs and convert to float)
    for col in required_cols[1:]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)

    # 1. Compute EBITDA (Revenue - Cost of Goods Sold - Operating Expenses)
    df['EBITDA'] = df['Revenue'] - df['CostOfGoodsSold'] - df['OperatingExpenses']
    
    # 2. Compute Net Cash Flow
    df['NetCashFlow'] = df['CashInflow'] - df['CashOutflow']

    # Retrieve last period row
    latest_row = df.iloc[-1]
    
    # 3. Compute Debt-to-Equity Ratio
    equity_val = float(latest_row['TotalEquity'])
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

    return {
        "period": str(latest_row['Period']),
        "latest_revenue": float(latest_row['Revenue']),
        "latest_debt_to_equity": round(debt_to_equity, 3),
        "avg_monthly_burn": round(abs_burn, 2),
        "ebitda_margin": round(ebitda_margin, 4),
        "interest_coverage_ratio": interest_coverage if isinstance(interest_coverage, str) else round(interest_coverage, 2),
        "revenue_growth_history": growth_history,
        "cash_runway_months": cash_runway,
        "raw_record_count": len(df)
    }
