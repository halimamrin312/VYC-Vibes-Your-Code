# Project Development Schedule: M&A Due Diligence Swarm

This document outlines the collaborative, 9-day implementation plan (June 23 – July 1) for a team of **4 developers** to build and integrate the Automated M&A Due Diligence Swarm.

---

## 👥 Agent Team Assignments

To align with a vertical vibe-coding approach and minimize integration friction, development is divided by **Agent Verticals**. Each team/developer owns their agent's full-stack implementation (prompts, specialized tools, backend API endpoints, and React frontend UI components):

*   **Team Orchestrator (Orchestrator Agent & Deal Lead Platform)**
    *   *Domain:* Core ADK setup, dynamic agent loader registry, orchestrator loop, global React/Vite theme & basic routing, memory/state management, streaming chat endpoints, HITL pause/resume backend logic, and the final Investment Memo view.
*   **Team Financial Auditor (Financial Agent & Auditing Tools)**
    *   *Domain:* Financial Auditor agent prompts, `pandas_analyst.py` tool, local CSV/Excel parser, `/api/ingest/financial` ingestion endpoint, SEC EDGAR MCP integration, and the financial dashboard UI with status indicators.
*   **Team Legal Compliance (Legal Agent & Contract RAG)**
    *   *Domain:* Legal compliance agent prompts, local PDF parser tool, SQLite/FAISS vector database for local embeddings, `/api/ingest/legal` ingestion endpoint, CourtListener/open-legal MCP integration, and the legal red-flag panel UI.
*   **Team Operations & Brand Sentiment (Ops & Sentiment Agent & Web-Search)**
    *   *Domain:* Operations evaluator and brand sentiment agent prompts, web-search tool with `data_sanitizer.py`, GitHub MCP for IT metrics, supply chain APIs, `/api/ingest/logs` endpoint, and the operations/sentiment charts UI.

---

## 📅 Daily Milestones (June 23 – July 1)

### Phase 1: Foundation (June 23 – June 24)
> [!NOTE]
> Focus is on setting up the project skeleton, establishing API communication contracts, and compiling test data.

#### **Day 1 (June 23): Environment Setup & Architecture Skeleton**
*   **Team Orchestrator:** Initialize the Git repository. Set up the Python project skeleton (using ADK) and the dynamic agent loader framework in `swarm/orchestrator.py`. Bootstrap the FastAPI server skeleton in `backend/` and define global API schemas. Scaffold the frontend using Vite (React), establishing the global theme, vanilla CSS variables (dark-slate tech theme), and basic page routing.
*   **Team Financial Auditor:** Gather mock financial CSV data for "Acme Corp" and save under `data_room/mock_data/`. Set up backend schemas for financial endpoints.
*   **Team Legal Compliance:** Gather mock legal contracts (with a planted liability clause) for "Acme Corp" and save under `data_room/mock_data/`. Set up backend schemas for contract ingestion.
*   **Team Operations & Brand Sentiment:** Gather mock operational logs for "Acme Corp" and save under `data_room/mock_data/`. Set up backend schemas for operations and sentiment metrics.

#### **Day 2 (June 24): Ingestion Pipeline & Basic Chat Connection**
*   **Team Orchestrator:** Implement the first version of the Orchestrator routing loop, reading configuration from `.env` and loading empty sub-agents. Build the mobile-responsive chat container in React. Write the Orchestrator's initial system prompt template in `swarm/prompt_templates/orchestrator_system.txt`.
*   **Team Financial Auditor:** Create the financial file ingestion API endpoint (e.g. `/api/ingest/financial`). Write the local CSV parser script to read uploaded CSVs and save them. Build the financial document uploader React components. Write the initial financial system prompt template.
*   **Team Legal Compliance:** Create the legal file ingestion API endpoint (e.g. `/api/ingest/legal`). Build the legal document uploader React components. Write the initial legal compliance system prompt template.
*   **Team Operations & Brand Sentiment:** Create the operations log ingestion API endpoint. Write the initial operations and sentiment system prompt templates.

---

### Phase 2: Core Agent & Feature Development (June 25 – June 27)
> [!TIP]
> The primary logic of the Financial and Legal agents is built and wired to the UI.

#### **Day 3 (June 25): Financial Auditor Agent & Local Data Parsing**
*   **Team Orchestrator:** Integrate basic tool call routing into the ADK Orchestrator so sub-agents can invoke Python scripts or vector search. Implement global dynamic upload feedback and status indicators in the UI.
*   **Team Financial Auditor:** Complete the `financial_auditor.py` agent. Implement the `pandas_analyst.py` tool to parse the mock CSV and calculate burn rates, churn, and debt ratios. Wire backend endpoints to return audit findings.
*   **Team Legal Compliance:** Set up the local vector database (e.g., SQLite or FAISS) for storing parsed PDFs, configuring the embedding generation logic. Build local PDF text extraction tools.
*   **Team Operations & Brand Sentiment:** Prepare backend infrastructure for sentiment analysis and log processing.

#### **Day 4 (June 26): Legal Compliance Agent & Local RAG**
*   **Team Orchestrator:** Implement memory storage so agents can reference historical context from the uploaded documents across chat turns. Design the Markdown Viewer component to display the formatted investment memo generated by the Orchestrator.
*   **Team Financial Auditor:** Connect the financial agent to memory and optimize pandas analysis based on context.
*   **Team Legal Compliance:** Build a local RAG extraction tool that segments PDFs and does similarity search without leaking data. Complete the `legal_compliance.py` agent. Wire it to the local RAG tool to search target contracts for liability clauses and "poison pills".
*   **Team Operations & Brand Sentiment:** Set up operational log parsing tools and wire them to sentiment context.

#### **Day 5 (June 27): Operations & Brand Sentiment Agents**
*   **Team Orchestrator:** Standardize error-handling and API responses across all sub-agents to prevent a crash in one agent from halting the swarm. Write the API endpoint for streaming chat messages from the Orchestrator to the UI. Wire the frontend chat window to the backend streaming endpoint, ensuring messages render smoothly.
*   **Team Financial Auditor:** Wire financial audit alerts and stream metrics directly to the Orchestrator.
*   **Team Legal Compliance:** Wire legal liability alerts and stream compliance indicators directly to the Orchestrator.
*   **Team Operations & Brand Sentiment:** Build the `ops_evaluator.py` and `brand_sentiment.py` agents. Code a web-search tool to fetch sentiment indicators without sharing confidential company metadata (using `data_sanitizer.py`).

---

### Phase 3: Advanced Integrations & HITL Checkpoints (June 28 – June 29)
> [!IMPORTANT]
> Establish the Human-in-the-Loop workflow and configure custom MCP servers.

#### **Day 6 (June 28): Human-in-the-Loop (HITL) Implementation**
*   **Team Orchestrator:** Implement ADK's pause/resume state management in the Orchestrator. Expose backend endpoints `/api/hitl/pause` and `/api/hitl/respond` to manage the interactive verification loop. Add interactive HITL prompts to the chat UI (e.g., action buttons: "Proceed with Deducted Valuation", "Halt Due Diligence", "Ignore Risk").
*   **Team Financial Auditor:** Add triggers to pause when financial risks exceed thresholds (e.g. extreme debt/burn), prompting user confirmation on valuation adjustments.
*   **Team Legal Compliance:** Create the logic to trigger a "Red Flag" pause when the Legal agent flags a high-priority risk. Write test cases validating the halt and the user response routing.
*   **Team Operations & Brand Sentiment:** Add triggers to pause when critical operational flaws or brand crises are detected.

#### **Day 7 (June 29): MCP Server Integrations**
*   **Team Orchestrator:** Enhance UI responsiveness. Integrate subtle micro-animations (loading spinners, agent typing indicators, panel transitions). Optimize the orchestrator prompt template to incorporate external search results retrieved from the MCP servers.
*   **Team Financial Auditor:** Build, configure, and wire the SEC EDGAR MCP server. Integrate the MCP tool into the financial agent and optimize financial prompts.
*   **Team Legal Compliance:** Build, configure, and wire the CourtListener / open-legal MCP servers. Integrate the MCP tool into the legal agent and optimize legal prompts.
*   **Team Operations & Brand Sentiment:** Integrate file-system MCP or public API integrations into the operations/sentiment prompts.

---

### Phase 4: Verification, Security & Polish (June 30 – July 1)
> [!CAUTION]
> Focus is on verifying security protocols (zero-leakage), performance testing, and setting up remote tunnels for phone access.

#### **Day 8 (June 30): Remote Tunneling & Security Verification**
*   **Team Orchestrator:** Run security audits on orchestrator routing. Expose the local FastAPI server using a secure tunnel (Tailscale or Ngrok). Test the React UI on mobile viewports. Connect your phone to the server via the secure tunnel and test file uploads. Run E2E evaluation seeding different M&A scenarios.
*   **Team Financial Auditor:** Verify zero-leakage of private financials. Audit calculations and test financial scenarios.
*   **Team Legal Compliance:** Verify zero-leakage of private contracts. Audit RAG prompts and sanitize queries sent to external court APIs using `data_sanitizer.py`.
*   **Team Operations & Brand Sentiment:** Run audits on external web search queries using `data_sanitizer.py` to ensure zero-leakage of target company metadata.

#### **Day 9 (July 1): Final Polish & Code Freeze**
*   **All Teams:** Conduct a complete end-to-end dry run. Verify all agent paths function correctly, CSV data is calculated accurately, and the investment memo compiles properly. Freeze the code and package the application (`docker-compose.yml` or standard start scripts). Prepare the repository's `README.md` and initial outline for the Kaggle Writeup.
