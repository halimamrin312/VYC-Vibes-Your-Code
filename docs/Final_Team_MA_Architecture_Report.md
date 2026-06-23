# Capstone Project Deep Dive: Automated M&A Due Diligence Swarm

## 1. Executive Summary
Mergers and Acquisitions (M&A) require hundreds of hours of grueling manual due diligence by analysts, accountants, and lawyers. This capstone project proposes a **Multi-Agent Swarm** that drastically accelerates this process. By utilizing Google's Agent Development Kit (ADK) and Model Context Protocol (MCP), this system parallel-processes a target company's financial, legal, and operational data, generating a cohesive investment recommendation. 

To ensure safety and strategic alignment, the system features critical **Human-in-the-Loop (HITL)** checkpoints, allowing an investment partner to guide the AI when high-stakes anomalies are detected.

---

## 2. Generalized Swarm Architecture
Unlike an IT-only evaluator, this swarm is designed to evaluate *any* type of business (Retail, Manufacturing, Pharma, or Tech) by swapping out specific asset checks. 

### A. The Lead Synthesizer Agent (The Orchestrator)
* **Role:** Acts as the "Deal Lead." It takes the initial prompt (e.g., "Evaluate Acme Corp for a $50M acquisition") and delegates specific tasks to the sub-agents. 
* **Output:** Compiles the sub-agent reports into a final, interactive "Investment Memo" with a Buy/Pass recommendation.

### B. Financial Auditor Agent
* **Role:** Analyzes the target company's financial health.
* **Tools:** Uses a Python Code Execution tool to ingest raw CSVs/Excel sheets (balance sheets, P&L statements). It runs pandas scripts to detect revenue churn, unusual burn rates, and outstanding debt.

### C. Legal & Compliance Agent
* **Role:** Acts as the corporate lawyer.
* **Tools:** Uses RAG (Retrieval-Augmented Generation) and MCP to connect to a Google Drive or secure vault containing the target's contracts. It scans for "poison pills," pending lawsuits, and tricky liability clauses.

### D. Operations & Core Asset Evaluator Agent (Generalized)
* **Role:** Evaluates the actual "engine" of the business.
* **Tools:** Depending on the industry, it uses specialized tools:
  * *For IT/Software:* Uses a GitHub MCP to audit code quality and tech debt.
  * *For Retail/Manufacturing:* Evaluates inventory databases and supply chain logs for bottlenecks.
  * *For Pharma/Biotech:* Audits patent databases and FDA compliance documents.

### E. Brand & Market Sentiment Agent
* **Role:** Assesses public perception.
* **Tools:** Uses web-search and social media APIs to analyze customer reviews, news sentiment, and competitor positioning.

---

## 3. Human-in-the-Loop (HITL) Workflow
In high-stakes M&A, AI cannot make the final call autonomously. The system incorporates ADK's Human-in-the-Loop capabilities at critical junctures:

**Scenario: The "Red Flag" Pause**
1. The *Legal Agent* discovers a pending intellectual property lawsuit buried in the contracts.
2. The *Lead Synthesizer* halts the reporting process.
3. It sends a message to the human user (the Investment Partner): 
   > *"URGENT: A pending IP lawsuit was found regarding Acme Corp's flagship product. Potential liability is $5M. How should I proceed? (A) Halt the due diligence, (B) Deduct $5M from the valuation model and continue, (C) Ignore for now."*
4. The human provides strategic direction, and the swarm dynamically adjusts its analysis based on that feedback.

---

## 4. M&A Due Diligence Agent System — Data Architecture & Ingestion Map

Here's a complete breakdown per agent: what data it needs, where to actually get it (free government sources first), and which MCP servers exist to wire it in.

### Agent A — Financial Auditor
**What it needs:** Balance sheets, income statements, cash flow, burn rate, debt, revenue trends.
* **Free government source (primary):** SEC EDGAR (U.S. Securities and Exchange Commission).
* **MCP servers:** 
  * `stefanoamorelli/sec-edgar-mcp` (pip-installable) - exposes balance sheets, income statements, and cash flow via XBRL-parsed data.
  * `cyanheads/secedgar-mcp-server` - supports fetching SEC XBRL frames for one concept across all reporting companies.
* **Supplementary free APIs (non-government):** Alpha Vantage (JSON/CSV stock/fundamental data), Finnhub (quotes, news, sentiment), Financial Modeling Prep (FMP).
* **Ingestion pattern:** SEC EDGAR MCP → pandas agent reads XBRL-parsed JSON → detects churn via YoY revenue diffs, computes burn rate from cash flow, flags unusual debt-to-equity ratios.

### Agent B — Legal & Compliance
**What it needs:** Pending lawsuits, court records, federal regulations, contract red flags, compliance violations.
* **Free government sources:** 
  * **CourtListener** (Free Law Project) for US court records.
  * **GovInfo API** for US federal law/regulations.
  * **EUR-Lex** for EU regulations.
* **MCP servers:** 
  * `JamesANZ/us-legal-mcp` (connects to Congress bills, Federal Register, CourtListener).
  * `TCoder920x/open-legal-compliance-mcp` (covers US federal law via GovInfo, US case law, and EU regulations).
  * `blakeox/courtlistener-mcp` (production-grade for deep court record access).
* **Ingestion pattern:** Feed target company name → search CourtListener for active dockets → scan Federal Register for regulatory actions → RAG layer runs over retrieved documents to extract poison pills, indemnification clauses, liability caps.

### Agent C — Operations & Core Asset Evaluator
This agent splits by industry vertical.
* **For IT/Software:** GitHub MCP covers code quality, commit history, and open issues. Pair with `edgartools` for any capitalized software assets.
* **For Pharma/Biotech — Patent Data:** 
  * `riemannzeta/patent_mcp_server` accessing USPTO data through PPUBS search and ODP tools.
  * Google Patents API via Apify (covers USPTO, EPO, WIPO, JPO, CN, KR).
  * EPO's Open Patent Services (OPS) API.
* **For FDA compliance (Pharma):** FDA's public APIs at `api.fda.gov` (drug approvals, adverse events).
* **For Retail/Manufacturing:** World Bank Open Data API and UN Comtrade cover supply chain/trade flow data. BLS (Bureau of Labor Statistics) public API covers wage and labor data.

### Agent D — Brand & Market Sentiment
**What it needs:** News coverage, customer reviews, competitor positioning, social sentiment.
* **Free/freemium sources:** 
  * Alpha Vantage (market news API with sentiment scores).
  * GDELT Project (monitors global news media).
  * Finnhub (news-sentiment endpoint).
  * Google Places API and Yelp Fusion API (consumer reviews).
* **Ingestion pattern:** Web search MCP → retrieve last 90 days of news mentions → GDELT API for sentiment time-series → alpha vantage NEWS_SENTIMENT endpoint by ticker → aggregate into bearish/bullish signal with flagged keywords (layoffs, lawsuit, recall, fraud).

---

## 5. Cross-Agent: Global Company Identity Layer
Before any agent starts, you need to resolve the target company to a verified legal entity.
* **OpenCorporates:** Has over 200 million companies from primary public sources. The API supports company search by name, retrieval of officers, filings, and registrations.
* **Officer Search:** You can search by officer name and see all companies that person is related to across all jurisdictions—critical for due diligence.

---

## 6. Architecture Summary (Plain Text)

```
INPUT: Company name / ticker
    ↓
[Entity Resolution Layer]
    OpenCorporates API → canonical legal entity, jurisdiction, registration status

    ↓ feeds all 4 agents in parallel

[Financial Auditor]
    SEC EDGAR MCP (10-K, 10-Q, 8-K, XBRL) → pandas analysis
    Alpha Vantage / FMP / Finnhub → supplementary ratios

[Legal & Compliance]
    CourtListener MCP → active dockets, opinions
    GovInfo API → CFR/US Code compliance checks
    EUR-Lex (no key) → EU regulatory exposure

[Operations Evaluator]
    IT:     GitHub MCP → code/tech debt
    Pharma: USPTO Patent MCP + EPO OPS API + FDA API
    Retail: UN Comtrade + BLS API

[Brand & Sentiment]
    Alpha Vantage NEWS_SENTIMENT + GDELT → time-series sentiment
    Web search MCP → recent coverage
    Google Places / Yelp → consumer reviews

    ↓
[Orchestrator / Synthesis Agent]
    Aggregates agent outputs → risk score + flag summary → final report
```

---

## 7. Key Architectural Concerns to Address
* **Data freshness mismatch:** SEC EDGAR filings are quarterly; GDELT news is real-time. Your synthesis layer needs to timestamp-weight signals—a bad Q4 filing matters less if Q1 news is bullish recovery.
* **Rate limits on free tiers:** OpenCorporates is 500 calls/month, Alpha Vantage free is 25 calls/day. For Kaggle evaluation, pre-cache target company data in CSVs rather than hitting live APIs per query.
* **First-Priority Local Data Ingestion UI:** The system UI must support direct user ingestion of CSVs (financial sheets) and other files (PDF agreements, internal reports). This uploaded data constitutes highly classified target information and must be treated as **first-priority data**. The agents will prioritize analyzing these local files first.
* **Hybrid Search and Priority Routing:** External agent lookups (e.g., via SEC EDGAR, CourtListener, web search) will serve as secondary/corroborating sources. The Orchestrator will query public endpoints only to fill in missing gaps or cross-verify claims from the uploaded priority documents, preserving API call budgets and ensuring focus on the company's proprietary data.
* **Private companies:** SEC EDGAR only covers US public companies. For private M&A targets, you'll need OpenCorporates + manual CSV ingestion. 
* **RAG for Legal Agent:** The legal agent's contract scanning needs a local RAG layer. The target's own contracts live in Google Drive or a file vault (via Drive MCP connector), while public court data comes from CourtListener.

---

## 8. Extended Section: Security, Privacy & Compliance Protocols
In the context of M&A, the target company's data is highly confidential. We must design the architecture to prevent sensitive data leakage.
* **Zero-Retention LLM Policies:** API requests to foundational models (e.g., Gemini Enterprise, Claude API) must be configured with explicit zero-data-retention agreements so that target financials are not used for model training.
* **Local RAG & Embeddings:** For parsing the private data room (VDR), all vector embeddings will be generated locally. External APIs will only be queried using sanitized data or public queries (e.g., querying USPTO with a patent number, not the proprietary source code).
* **Sanitized External Queries:** When the agent needs to supplement local uploaded documents with external web searches or public API queries (e.g. SEC, CourtListener), it must dynamically sanitize the query. Proprietary code names, internal deal parameters, and classified transaction details must never be sent to third-party public search engines or general indexes.
* **Role-Based Access Control (RBAC):** The swarm's `Lead Synthesizer` will enforce permissions. For example, the `Brand Sentiment` agent is entirely sandboxed from the `Financial Auditor` agent to prevent cross-contamination of public and highly classified private data.

---

## 9. Extended Section: Evaluation Metrics & KPIs
To prove the viability of this system to the Kaggle judges and business stakeholders, we will measure the swarm against the following KPIs:
1. **Time-to-Insight (TTI):** Compare the swarm's execution time (e.g., 5 minutes) against the industry average for initial manual due diligence (often 40-80 hours).
2. **Red Flag Detection Accuracy:** Measured by precision and recall over the mock dataset. Does the Legal Agent successfully identify the planted "poison pill" contract clause without flagging standard NDA boilerplate as a risk?
3. **HITL Resolution Speed:** How effectively the Orchestrator pauses, formats the contextual question for the human partner, and correctly applies the human's decision to the final valuation model.

---

## 10. Capstone Implementation Strategy (Vibe Coding)
To build this for the Kaggle competition:
1. **Mock Data:** Generate realistic mock datasets for a fake company ("Acme Corp")—a financial CSV, a few legal PDF contracts with a hidden "red flag," and some operational logs.
2. **MCP Servers:** Set up simple local FileSystem MCP servers to allow the agents to read the mock data securely, alongside the public data MCPs.
3. **ADK Multi-Agent Routing:** Define the Router/Lead agent and the Sub-agents using ADK's standard patterns.
4. **HITL Implementation:** Use ADK's pause/resume state management to demonstrate the interactive "Red Flag" scenario.

---

## 11. Proposed Project Directory Structure
To facilitate parallel development by multiple team members (frontend, backend, agent engineering, and data integration), the codebase is organized with clear separation of concerns.

### Swarm Architecture Diagram
![M&A Due Diligence Swarm Architecture](file:///D:/kaggle%20capstone%20project/docs/architecture_diagram.png)

```text
ma-due-diligence-swarm/
├── README.md                  # Project overview, architecture, and setup instructions
├── requirements.txt           # Python backend & agent dependencies
├── package.json               # Node.js/Frontend package definition
├── docker-compose.yml         # Local stack orchestration (Frontend, Backend, DB, MCP servers)
│
├── frontend/                  # Web Dashboard and File Ingestion UI (React/Vite)
│   ├── public/                # Static assets (logos, icons)
│   └── src/
│       ├── components/        # Reusable UI (ChatWindow, DocumentUploader, MemoViewer)
│       ├── hooks/             # React hooks (useAgent, useUpload)
│       ├── services/          # API client integration
│       ├── App.jsx            # Main app entrypoint
│       └── index.css          # Styling (custom CSS properties, dark mode)
│
├── backend/                   # FastAPI Web Server & API Layer
│   └── app/
│       ├── main.py            # API entrypoint (FastAPI app)
│       ├── config.py          # Environment settings and credentials
│       ├── routers/           # Endpoints (auth, ingest, chat, memo)
│       ├── database/          # Database models, schemas, and migrations
│       └── utils/             # Helper scripts (file processing, sanitization)
│
├── swarm/                     # Multi-Agent System Core (using Google ADK)
│   ├── __init__.py
│   ├── config.py              # Agent configurations, models, and global parameters
│   ├── orchestrator.py        # Deal Lead Synthesizer Agent (ADK Router/Coordinator)
│   │
│   ├── agents/                # Individual Specialized Sub-Agents
│   │   ├── financial_auditor.py  # Ingests and audits CSV financial statements
│   │   ├── legal_compliance.py   # RAG-based legal agreement checking agent
│   │   ├── ops_evaluator.py      # Operations and core asset auditor agent
│   │   └── brand_sentiment.py    # Public market sentiment and review aggregator
│   │
│   ├── tools/                 # Custom Agent Tools
│   │   ├── data_sanitizer.py  # Strips PII/Classified identifiers from external queries
│   │   ├── local_pdf_parser.py # Processes local target contracts & PDFs
│   │   └── pandas_analyst.py  # Executes pandas code to generate cash-flow metrics
│   │
│   └── prompt_templates/      # System prompts externalized for prompt engineering
│       ├── orchestrator_system.txt
│       ├── financial_system.txt
│       ├── legal_system.txt
│       └── sentiment_system.txt
│
├── mcp_servers/               # Custom and standard MCP Servers
│   ├── file_system_mcp/       # Custom local filesystem MCP to read uploaded docs
│   ├── courtlistener_mcp/     # Custom/standard CourtListener API MCP
│   └── edgar_mcp/             # Custom/standard SEC EDGAR API MCP
│
├── data_room/                 # Virtual Data Room (Local Sandbox storage for uploaded files)
│   ├── uploads/               # Raw user-uploaded CSVs, PDFs, etc.
│   ├── mock_data/             # Mock datasets for "Acme Corp" (CSVs, contracts with red flags)
│   └── vector_store/          # Local FAISS or SQLite Vector storage (Zero-leakage RAG)
│
└── docs/                      # Documentation and reports
    ├── capstone_writeup_draft.md # Draft of the 2,500 word Kaggle submission writeup
    ├── presentation_plan.md      # Plan for the 5-minute video presentation
    └── architecture_diagram.png  # Graphic of the Swarm layout
```

---

## 12. Git Merge Conflict Mitigation Strategies
To ensure that a large, distributed team can work on the codebase concurrently without constantly running into merge conflicts, the following rules are enforced in the architecture:

1. **Decoupled System Prompts (`prompt_templates/`):**
   * **The Problem:** In many agent projects, prompts are hardcoded inside agent class files, causing multiple developers to edit the same `.py` files.
   * **The Solution:** All system prompts and agent instructions are stored in separate `.txt` or `.md` files under the `swarm/prompt_templates/` folder. Developers working on prompt engineering do not need to touch the python implementation files.

2. **Dynamic Agent Registration Pattern:**
   * **The Problem:** The central `orchestrator.py` usually needs to import and reference each individual sub-agent. Adding or modifying sub-agents requires editing the orchestrator, leading to git conflicts on main coordinator loops.
   * **The Solution:** Each agent dynamically registers itself using a registry pattern (e.g. `@register_agent("financial")`). The orchestrator loads sub-agents dynamically via configuration or runtime discovery, ensuring `orchestrator.py` remains untouched when adding new sub-agents.

3. **Isolated Backend Routing:**
   * **The Problem:** Having a single file handle all HTTP/WebSocket endpoints causes severe conflicts between backend and frontend developers.
   * **The Solution:** Endpoints are decoupled into specific routers in `backend/app/routers/` (e.g., `ingest.py`, `chat.py`, `memo.py`). 

4. **Environment-Based Configs (.env):**
   * **The Problem:** Different developers hardcode their personal API keys, DB urls, or model parameters in a shared `config.py` file, leading to constant merge conflicts.
   * **The Solution:** All configurations are read from environment variables via a local `.env` file (ignored by git). A `.env.example` file is committed to repository to document the necessary keys without sharing confidential credentials.
