# Financial Auditor Agent Reliability & Auditability Design

This document details the approved design to enhance the [FinancialAuditor](file:///d:/kaggle%20capstone%20project/code/swarm/agents/financial_auditor.py) agent and the [pandas_analyst.py](file:///d:/kaggle%20capstone%20project/code/swarm/tools/pandas_analyst.py) calculations tool.

## 1. Robust CSV Schema Normalization & Pre-flight Check

### Problem Statement
The quantitative calculation tool expects strict headers (`Period`, `Revenue`, `CostOfGoodsSold`, etc.). If a target uploads spreadsheets with naming variants (e.g., `Sales` instead of `Revenue`), calculations fail.

### Solution
Implement a two-stage column normalizer before performing calculations:
1. **Fuzzy & Heuristic Matching**: Compare input headers against known synonyms:
   - `Revenue` -> `Revenue`, `Sales`, `Turnover`, `Total Revenue`, `Total Sales`, `Operating Revenue`
   - `CostOfGoodsSold` -> `CostOfGoodsSold`, `COGS`, `Cost of Sales`, `Cost of Goods Sold`, `Cost of Revenue`
   - `OperatingExpenses` -> `OperatingExpenses`, `OpEx`, `Operating Expenses`, `SG&A`, `Admin Expenses`
   - `TotalLiabilities` -> `TotalLiabilities`, `Liabilities`, `Total Liabilities`
   - `TotalEquity` -> `TotalEquity`, `Equity`, `Total Equity`, `Stockholders Equity`, `Shareholder Equity`
   - `CashInflow` -> `CashInflow`, `Cash Inflow`, `Operating Cash Inflow`, `Cash Receipts`
   - `CashOutflow` -> `CashOutflow`, `Cash Outflow`, `Operating Cash Outflow`, `Cash Payments`
   - `TotalAssets` -> `TotalAssets`, `Assets`, `Total Assets`
   - `Cash` -> `Cash`, `Cash & Cash Equivalents`, `Cash Equivalents`

2. **LLM Schema Alignment Fallback**: If heuristic matching fails to resolve required columns, query the LLM with the list of CSV headers and a JSON schema specification. The LLM must return a JSON mapping of source columns to standard columns.
3. **Programmatic HITL Fallback**: If neither heuristics nor LLM can confidently resolve the columns, raise a Human-in-the-Loop exception asking the user to map the CSV headers manually.

---

## 2. API Resilience & Non-Silent Failover Alerts

### Problem Statement
When real-time API integrations (`yfinance` or SEC EDGAR) fail, the agent silently loads mock data. This creates a high risk of misleading a human M&A auditor.

### Solution
1. Introduce a `data_degraded` boolean flag and a `sourcing_alerts` list in the agent's findings output.
2. If `yfinance` or `edgar` fail and fallback static metrics are loaded, populate:
   - `data_degraded: true`
   - `sourcing_alerts: ["yfinance fetch failed for Apple: rate limit exceeded. Static benchmark peer data loaded instead."]`
3. Pass this warning directly to the markdown report so that it is prominently displayed to the user on the UI dashboard.

---

## 3. Mathematical Proof Audit Trails

### Problem Statement
Calculations performed inside [pandas_analyst.py](file:///d:/kaggle%20capstone%20project/code/swarm/tools/pandas_analyst.py) are opaque to the human auditor. We need to generate a clear, step-by-step mathematical trace of how ratios and margins were computed.

### Solution
1. Update `run_financial_analysis` to build a list of string proofs:
   - Example: `EBITDA = Revenue ($10,000,000) - CostOfGoodsSold ($6,000,000) - OperatingExpenses ($2,000,000) = $2,000,000`
   - Example: `EBITDA Margin = EBITDA ($2,000,000) / Revenue ($10,000,000) = 20.00%`
   - Example: `Debt-to-Equity = TotalLiabilities ($5,000,000) / TotalEquity ($4,000,000) = 1.25`
2. Include this audit log under a new `audit_log` field in the financial findings JSON payload.
3. Render the audit trail clearly in a structured table or blockquote in the generated Markdown report.
