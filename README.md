# M&A Due Diligence Swarm Platform

An automated, multi-agent due diligence platform for Mergers & Acquisitions (M&A). The system coordinates specialized agents to analyze target financials, legal contracts, market sentiment, and operational efficiency using the **Google Agent Development Kit (ADK)** and the **Model Context Protocol (MCP)**.

---

## 🚀 Key Features

* **Multi-Agent Orchestration (2-Wave Execution):** Coordinates parallel agent executions (Wave 1: Financial & Sentiment; Wave 2: Legal & Operations) with dynamic context propagation.
* **Human-in-the-Loop (HITL) Checkpoints:** Automatically pauses the swarm and prompts the user for strategic decisions when critical risks (Severity 1) or missing data are detected.
* **Secure Script Execution Sandbox:** Executes agent-written code safely in an isolated subprocess sandbox with AST-based import/function gating and path-traversal validation.
* **Semantic Legal Contract RAG:** Ingests legal agreements, chunks them, and builds a local FAISS vector index to run 10 targeted legal risk queries (LQ-01 to LQ-10).
* **Model Context Protocol (MCP):** Connects agents directly to public regulatory databases (such as SEC EDGAR Search) using stdio-based JSON-RPC tools.
* **Interactive Control Dashboard:** Features a modern, glassmorphic UI built with React/Vite and lucide-icons, displaying log streams, ESI/CSI graphs, and generated memos.

---

## 📂 Project Architecture

```mermaid
graph TD
    User([User / Investment Partner]) <--> Frontend[React/Vite Dashboard]
    Frontend <--> |HTTP / SSE Streaming| Backend[FastAPI Gateway]
    Backend <--> DB[(SQLite Session DB)]
    Backend <--> Orchestrator[Orchestrator / Lead Agent]
    
    Orchestrator --> |Wave 1 - Parallel| FinAuditor[Financial Auditor Agent]
    Orchestrator --> |Wave 1 - Parallel| BrandSentiment[Brand Sentiment Agent]
    
    FinAuditor -.-> |Context Distillation| ContextBuffer[Wave 1 Context: Revenue, Debt, Runway]
    ContextBuffer -.-> |Passed to Wave 2| LegalCompliance
    ContextBuffer -.-> |Passed to Wave 2| OpsEvaluator
    
    Orchestrator --> |Wave 2 - Parallel| LegalCompliance[Legal & Compliance Agent]
    Orchestrator --> |Wave 2 - Parallel| OpsEvaluator[Operations Evaluator Agent]
```

---

## 🛠️ Technology Stack

* **Backend:** FastAPI (Python 3.14+), Uvicorn, Peewee ORM (SQLite).
* **Frontend:** React 18, Vite, Lucide React, CSS Glassmorphism.
* **Agent Engine:** Google Agent Development Kit (ADK), Custom Registry Patterns.
* **Security:** Python AST (Abstract Syntax Trees), Subprocess Sandboxing.
* **Vector Store:** FAISS (Facebook AI Similarity Search) and SentenceTransformers.

---

## ⚡ Quick Start

### Prerequisites
* Python 3.14+
* Node.js & npm

### 1. Configuration Setup
Create a `.env` file in the project root:
```properties
GEMINI_API_KEY="your_gemini_api_key"
COURTLISTENER_API_TOKEN="optional_courtlistener_token"
GOVINFO_API_KEY="optional_govinfo_key"
```

### 2. Start the Backend API Server
```bash
# Activate virtual environment
source venv/bin/activate

# Start Uvicorn reload server
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Start the Frontend Dev Server
In a new terminal window:
```bash
cd frontend
npm install
npm run dev
```
Open **[http://localhost:3000/](http://localhost:3000/)** in your web browser.

---

## 🧪 Testing the Swarm

Verify code compliance, security policies, and agent mechanics:

* **Run all tests:**
  ```bash
  venv/bin/pytest -v
  ```
* **Interactive Scenarios on the Dashboard:**
  * **Public Flow (Auto):** Set target company to `TSLA` or `AAPL` and dispatch. It pulls financial metrics automatically via yfinance/SEC.
  * **Private Flow (HITL):** Set target company to `Acme Corp` and dispatch. The system will pause and ask you to upload a financial CSV file in the Data Room tab.
  * **Legal Warning (HITL):** Set target company to `Cyberdyne Systems` and dispatch. It will pause on Wave 2 to alert you about an active lawsuit from CourtListener.
