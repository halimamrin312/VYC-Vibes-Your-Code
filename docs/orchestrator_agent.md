# Orchestrator Agent (Lead Synthesizer) - Detailed Technical Specification

This document provides the complete, production-grade specification for implementing the **Orchestrator Agent (Lead Synthesizer)**. It contains fully realized code skeletons with type annotations, docstrings, comprehensive logging, explicit error handling, and web integration layers.

---

## 📂 Component Layout & File Locations
- **Main Agent Code:** `swarm/orchestrator.py`
- **Configuration & Settings:** `swarm/config.py`
- **System Prompt Template:** `swarm/prompt_templates/orchestrator_system.txt`
- **FastAPI Backend Routers:** 
  - `backend/app/routers/chat.py` (Chat stream & execution loop)
  - `backend/app/routers/memo.py` (Memo generation and final output endpoints)
  - `backend/app/routers/hitl.py` (HITL pause/resume and response submission)
- **Frontend UI Components (React):**
  - `frontend/src/components/ChatWindow.jsx`
  - `frontend/src/components/MemoViewer.jsx`

---

## ⚙️ Core Python Implementation (`swarm/orchestrator.py`)

This file manages the loading registry, initializes sub-agents, routes tool execution, coordinates the agent loop, and controls the Human-in-the-Loop flow.

```python
"""
swarm/orchestrator.py
Central Orchestrator loop and agent registry for the M&A Due Diligence Swarm.
Manages dynamic imports, execution state, and Human-in-the-Loop checkpoints.
"""

import os
import logging
import importlib
import pkgutil
from typing import Dict, List, Any, Optional, Type, Generator
from pydantic import BaseModel, Field

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("swarm.orchestrator")

# Global agent registry
AGENT_REGISTRY: Dict[str, Type[Any]] = {}

def register_agent(name: str):
    """
    Decorator to register a sub-agent class with the orchestrator.
    Usage:
        @register_agent("financial_auditor")
        class FinancialAuditor:
            ...
    """
    def decorator(cls):
        normalized_name = name.strip().lower()
        if normalized_name in AGENT_REGISTRY:
            logger.warning(f"Overwriting already registered agent: {normalized_name}")
        AGENT_REGISTRY[normalized_name] = cls
        logger.info(f"Registered agent: {normalized_name} (Class: {cls.__name__})")
        return cls
    return decorator

def discover_and_load_agents(package_name: str = "swarm.agents") -> None:
    """
    Dynamically scans and imports all modules inside the specified agents package
    to trigger registration decorators at startup.
    """
    try:
        package = importlib.import_module(package_name)
    except ModuleNotFoundError as e:
        logger.critical(f"Failed to find agent package '{package_name}': {str(e)}")
        return

    for _, module_name, _ in pkgutil.iter_modules(package.__path__):
        full_module_name = f"{package_name}.{module_name}"
        try:
            importlib.import_module(full_module_name)
            logger.debug(f"Successfully imported module: {full_module_name}")
        except Exception as e:
            logger.error(f"Error loading module {full_module_name}: {str(e)}", exc_info=True)

# Pydantic Schemas for Session State
class ChatMessage(BaseModel):
    role: str = Field(..., description="Role of the sender: user, assistant, system, or agent")
    content: str = Field(..., description="Content of the message")
    timestamp: str = Field(..., description="ISO 8601 formatted UTC timestamp")

class AgentReport(BaseModel):
    agent_name: str
    status: str = Field(..., pattern="^(success|error|skipped)$")
    findings: Dict[str, Any] = Field(default_factory=dict)
    raw_markdown: str = Field(..., description="Formatted markdown report produced by agent")

class SessionState(BaseModel):
    session_id: str
    target_company: str
    industry_sector: str = Field(..., pattern="^(software|manufacturing|retail|pharma|generic)$")
    history: List[ChatMessage] = Field(default_factory=list)
    agent_reports: Dict[str, AgentReport] = Field(default_factory=dict)
    hitl_status: str = Field("IDLE", pattern="^(IDLE|PAUSED|RESOLVED)$")
    pending_hitl_question: Optional[str] = None
    accumulated_red_flags: List[Dict[str, Any]] = Field(default_factory=list)

# Session persistence helpers
def save_session(state: SessionState) -> None:
    """Serializes and saves the SessionState Pydantic model to a local JSON file."""
    try:
        sessions_dir = os.path.join(settings.data_room_dir, "sessions")
        os.makedirs(sessions_dir, exist_ok=True)
        file_path = os.path.join(sessions_dir, f"{state.session_id}.json")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(state.model_dump_json(indent=2))
        logger.info(f"Successfully saved session state to disk at: {file_path}")
    except Exception as e:
        logger.error(f"Failed to save session state for {state.session_id}: {e}", exc_info=True)

def load_session(session_id: str) -> Optional[SessionState]:
    """Loads and deserializes the SessionState from a local JSON file."""
    try:
        file_path = os.path.join(settings.data_room_dir, "sessions", f"{session_id}.json")
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.loads(f.read())
            state = SessionState(**data)
            logger.info(f"Successfully loaded session state from disk at: {file_path}")
            return state
    except Exception as e:
        logger.error(f"Failed to load session state for {session_id}: {e}", exc_info=True)
    return None

# Explicit mapping of sub-agents to upload subdirectories
AGENT_DATA_PATHS = {
    "financial_auditor": "data_room/uploads/financial",
    "legal_compliance": "data_room/uploads/legal",
    "ops_evaluator": "data_room/uploads/logs",
    "brand_sentiment": "data_room/uploads/brand",
}

class Orchestrator:
    def __init__(self, session_id: str, target_company: str, industry_sector: str):
        self.state = SessionState(
            session_id=session_id,
            target_company=target_company,
            industry_sector=industry_sector
        )
        discover_and_load_agents()
        
    def get_registered_agents(self) -> List[str]:
        """Returns list of currently registered agents."""
        return list(AGENT_REGISTRY.keys())
        
    def dispatch_agent(self, agent_name: str, context: Dict[str, Any]) -> AgentReport:
        """
        Instantiates and executes a registered sub-agent.
        Includes robust error isolation to prevent individual agent crashes from halting the swarm.
        """
        agent_name_clean = agent_name.strip().lower()
        if agent_name_clean not in AGENT_REGISTRY:
            error_msg = f"Agent '{agent_name_clean}' not found in registry."
            logger.error(error_msg)
            return AgentReport(
                agent_name=agent_name_clean,
                status="error",
                findings={"error": error_msg},
                raw_markdown=f"### Error\n{error_msg}"
            )
            
        try:
            agent_class = AGENT_REGISTRY[agent_name_clean]
            if hasattr(agent_class, "industry"):
                agent_instance = agent_class(industry=self.state.industry_sector)
            else:
                agent_instance = agent_class()
                
            logger.info(f"Executing agent: {agent_name_clean}")
            result = agent_instance.execute(context)
            
            return AgentReport(
                agent_name=agent_name_clean,
                status="success",
                findings=result.get("findings", {}),
                raw_markdown=result.get("markdown", "No report content generated.")
            )
        except Exception as e:
            logger.error(f"Execution failed for agent '{agent_name_clean}': {str(e)}", exc_info=True)
            return AgentReport(
                agent_name=agent_name_clean,
                status="error",
                findings={"error": str(e)},
                raw_markdown=f"### Error in {agent_name_clean}\n{str(e)}"
            )
            
    def run_loop(self, user_message: str) -> Generator[Dict[str, Any], None, None]:
        """
        Main execution loop. Routes tasks to sub-agents concurrently, handles red-flag triggers,
        saves state to disk, and yields execution frames for SSE stream compatibility.
        """
        # Append User Message
        from datetime import datetime, timezone
        self.state.history.append(ChatMessage(
            role="user",
            content=user_message,
            timestamp=datetime.now(timezone.utc).isoformat()
        ))
        save_session(self.state)
        
        yield {"event": "status", "message": f"Analyzing due diligence parameters for {self.state.target_company}..."}
        
        # Determine active agents based on configuration
        active_agents = ["financial_auditor", "legal_compliance", "ops_evaluator", "brand_sentiment"]
        
        agents_to_run = []
        for agent_name in active_agents:
            # If agent has already run successfully, skip executing it on resume
            if agent_name in self.state.agent_reports and self.state.agent_reports[agent_name].status in ("success", "skipped"):
                logger.info(f"Agent {agent_name} already executed successfully. Loading cached result.")
                yield {
                    "event": "agent_status",
                    "agent": agent_name,
                    "status": self.state.agent_reports[agent_name].status,
                    "message": f"Loaded completed {agent_name.replace('_', ' ').title()} audit from session state."
                }
            else:
                agents_to_run.append(agent_name)

        if agents_to_run:
            yield {"event": "status", "message": f"Initializing {len(agents_to_run)} sub-agents for concurrent execution..."}
            
            # Construct contexts with explicit AGENT_DATA_PATHS mapping (Flaw 4)
            agent_contexts = {}
            for agent_name in agents_to_run:
                agent_contexts[agent_name] = {
                    "target_company": self.state.target_company,
                    "session_id": self.state.session_id,
                    "data_room_path": AGENT_DATA_PATHS.get(agent_name, f"data_room/uploads/{agent_name.split('_')[0]}"),
                    "sensitive_terms": [self.state.target_company, "merger", "buyout", "acquisition"]
                }
            
            # Execute sub-agents concurrently in a thread pool (Flaw 1)
            from concurrent.futures import ThreadPoolExecutor, as_completed
            
            yield {"event": "status", "message": "Executing active sub-agents in parallel threads..."}
            reports = {}
            with ThreadPoolExecutor(max_workers=len(agents_to_run)) as executor:
                future_to_agent = {
                    executor.submit(self.dispatch_agent, name, agent_contexts[name]): name
                    for name in agents_to_run
                }
                for future in as_completed(future_to_agent):
                    agent_name = future_to_agent[future]
                    try:
                        report = future.result()
                        reports[agent_name] = report
                    except Exception as e:
                        logger.error(f"Agent {agent_name} generated an exception: {e}", exc_info=True)
                        reports[agent_name] = AgentReport(
                            agent_name=agent_name,
                            status="error",
                            findings={"error": str(e)},
                            raw_markdown=f"### Error in {agent_name}\n{str(e)}"
                        )

            # Record reports and yield status updates
            for agent_name in agents_to_run:
                report = reports[agent_name]
                self.state.agent_reports[agent_name] = report
                yield {
                    "event": "agent_status",
                    "agent": agent_name,
                    "status": report.status,
                    "message": f"Finished {agent_name.replace('_', ' ').title()} audit."
                }
            
            # Save session state to disk after execution results are populated
            save_session(self.state)
            
            # Check for critical red-flag triggers (Human-In-The-Loop Checkpoint - Flaw 1 & 3)
            hitl_agents = []
            hitl_reasons = []
            
            for agent_name in agents_to_run:
                report = self.state.agent_reports[agent_name]
                
                # Robust check for CRITICAL flags
                flags = report.findings.get("flags", [])
                has_critical = False
                for f in flags:
                    if isinstance(f, dict) and f.get("severity") == "CRITICAL":
                        has_critical = True
                    elif isinstance(f, str) and f.upper() == "CRITICAL":
                        has_critical = True
                
                if report.findings.get("hitl_required") or has_critical:
                    hitl_agents.append(agent_name)
                    reason = report.findings.get("hitl_reason") or "Unspecified critical risk flagged."
                    hitl_reasons.append(f"{agent_name.replace('_', ' ').title()}: {reason}")
            
            if hitl_agents:
                self.state.hitl_status = "PAUSED"
                self.state.pending_hitl_question = " | ".join(hitl_reasons)
                save_session(self.state)
                
                yield {
                    "event": "hitl_pause",
                    "payload": {
                        "question": self.state.pending_hitl_question,
                        "options": [
                            {"key": "A", "text": "Halt due diligence process"},
                            {"key": "B", "text": "Adjust valuation model and continue"},
                            {"key": "C", "text": "Ignore and proceed"}
                        ]
                    }
                }
                return  # Terminate generator execution until resumed

        # Step 3: Synthesis of Final Investment Memo
        yield {"event": "status", "message": "Compiling final investment memo..."}
        
        # Compile reports to text context
        reports_content = ""
        for name, rep in self.state.agent_reports.items():
            reports_content += f"### {name.replace('_', ' ').title()} Report (Status: {rep.status})\n"
            reports_content += rep.raw_markdown + "\n\n"

        system_prompt = load_system_prompt()
        
        # Build context for synthesis
        prompt = (
            f"Perform due diligence synthesis for target company '{self.state.target_company}' "
            f"in the '{self.state.industry_sector}' industry sector.\n\n"
            f"User request context: {user_message}\n\n"
            f"Sub-agent Auditing Reports:\n{reports_content}\n"
            f"Accumulated Red Flags and Adjustments: {json.dumps(self.state.accumulated_red_flags, indent=2)}\n\n"
            f"Please synthesize the above findings into a cohesive, professional investment memo. "
            f"Include a clear Buy, Hold, or Pass recommendation, key deal parameters, consolidated red flags, "
            f"and valuation adjustments based on the human partner's decisions."
        )
        
        yield {"event": "status", "message": f"Synthesizing investment memo using model provider '{settings.model_provider}'..."}
        memo_content = call_llm(system_prompt, prompt)
        
        # Flaw 6: Add honest warning indicator to fallback memo if LLM call is unavailable
        if not memo_content:
            logger.info("LLM synthesis unavailable or failed; falling back to direct report compilation.")
            memo_content = "# Investment Memo: " + self.state.target_company + "\n\n"
            memo_content += "> ⚠️ **LLM Synthesis Unavailable**: The final synthesized investment recommendation could not be generated because the LLM API key is unconfigured or the request failed. Raw sub-agent outputs follow below.\n\n"
            memo_content += "## Executive Summary\n"
            memo_content += "⚠️ LLM synthesis unavailable — raw agent outputs follow. No recommendation generated.\n\n"
            if self.state.accumulated_red_flags:
                memo_content += "### Strategic Adjustments Applied\n"
                for flag in self.state.accumulated_red_flags:
                    memo_content += f"- **{flag.get('action')}**: {flag.get('description')} (Adjusted Amount: ${flag.get('amount'):,.2f})\n"
                memo_content += "\n"
            for name, rep in self.state.agent_reports.items():
                memo_content += f"## {name.replace('_', ' ').title()} Summary\n"
                memo_content += rep.raw_markdown + "\n\n"
            
        yield {"event": "assistant_message", "content": memo_content}
        
        # Save session final state
        save_session(self.state)
        
        yield {"event": "complete", "session_id": self.state.session_id}

```

---

## 📡 Web API Router Implementations (FastAPI)

### 1. Chat & Stream API (`backend/app/routers/chat.py`)
```python
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import json
import asyncio
from swarm.orchestrator import Orchestrator

router = APIRouter(prefix="/api/chat", tags=["Chat"])

# Simple in-memory session cache (Replace with Redis in Production)
SESSIONS: Dict[str, Orchestrator] = {}

class ChatRequest(BaseModel):
    session_id: str
    user_message: str
    target_company: str
    industry_sector: str

@router.post("/stream")
async def stream_chat(request: ChatRequest):
    # Retrieve or create session Orchestrator
    if request.session_id not in SESSIONS:
        from swarm.orchestrator import load_session
        saved_state = load_session(request.session_id)
        if saved_state:
            SESSIONS[request.session_id] = Orchestrator(
                session_id=request.session_id,
                target_company=request.target_company,
                industry_sector=request.industry_sector
            )
            SESSIONS[request.session_id].state = saved_state
        else:
            SESSIONS[request.session_id] = Orchestrator(
                session_id=request.session_id,
                target_company=request.target_company,
                industry_sector=request.industry_sector
            )
        
    orch = SESSIONS[request.session_id]
    
    # Verify that the Orchestrator is not currently paused in HITL state
    if orch.state.hitl_status == "PAUSED":
        raise HTTPException(
            status_code=400, 
            detail="Session is currently paused waiting for Human-In-The-Loop feedback. Submit to /api/hitl/respond."
        )

    def event_generator():
        try:
            for frame in orch.run_loop(request.user_message):
                yield f"data: {json.dumps(frame)}\n\n"
        except Exception as e:
            logger.error(f"Error in chat stream: {str(e)}", exc_info=True)
            yield f"data: {json.dumps({'event': 'error', 'message': f'Internal Server Error: {str(e)}'})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

### 2. HITL API Endpoint Router (`backend/app/routers/hitl.py`)
```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from backend.app.routers.chat import SESSIONS
from swarm.orchestrator import ChatMessage

router = APIRouter(prefix="/api/hitl", tags=["HITL"])

class HITLResponsePayload(BaseModel):
    session_id: str
    selected_option: str  # "A", "B", or "C"
    custom_feedback: Optional[str] = None

@router.post("/respond")
async def submit_hitl_response(payload: HITLResponsePayload):
    if payload.session_id not in SESSIONS:
        from swarm.orchestrator import load_session, Orchestrator
        saved_state = load_session(payload.session_id)
        if saved_state:
            SESSIONS[payload.session_id] = Orchestrator(
                session_id=payload.session_id,
                target_company=saved_state.target_company,
                industry_sector=saved_state.industry_sector
            )
            SESSIONS[payload.session_id].state = saved_state
        else:
            raise HTTPException(status_code=404, detail="Session ID not found.")
        
    orch = SESSIONS[payload.session_id]
    
    if orch.state.hitl_status != "PAUSED":
        raise HTTPException(status_code=400, detail="Orchestrator is not in a paused state.")
        
    # Process user decision
    from datetime import datetime, timezone
    user_note = f"Human Partner decision: Option {payload.selected_option}."
    if payload.custom_feedback:
        user_note += f" Feedback: {payload.custom_feedback}"
        
    orch.state.history.append(ChatMessage(
        role="system",
        content=user_note,
        timestamp=datetime.now(timezone.utc).isoformat()
    ))
    
    # Update state variables to release loop
    orch.state.hitl_status = "RESOLVED"
    orch.state.pending_hitl_question = None
    
    # Clean up local flag lists or adjust metrics as instructed
    if payload.selected_option == "B":
        # Example: Deduct liability fee from target calculations
        orch.state.accumulated_red_flags.append({
            "action": "DEDUCTION",
            "amount": 5000000.0,
            "description": "Adjusting target valuation model by $5,000,000 as instructed by human partner."
        })
        
    return {
        "status": "success", 
        "message": f"Strategic response registered (Option {payload.selected_option}). Swarm will resume on next user prompt."
    }
```

### 3. Memo API Endpoint Router (`backend/app/routers/memo.py`)
```python
from fastapi import APIRouter, HTTPException
from backend.app.routers.chat import SESSIONS

router = APIRouter(prefix="/api/memo", tags=["Memo"])

@router.get("/{session_id}")
def get_investment_memo(session_id: str):
    if session_id not in SESSIONS:
        from swarm.orchestrator import load_session, Orchestrator
        saved_state = load_session(session_id)
        if saved_state:
            SESSIONS[session_id] = Orchestrator(
                session_id=session_id,
                target_company=saved_state.target_company,
                industry_sector=saved_state.industry_sector
            )
            SESSIONS[session_id].state = saved_state
        else:
            raise HTTPException(status_code=404, detail="Session ID not found.")
        
    orch = SESSIONS[session_id]
    
    # Compile all sub-agent reports into Markdown
    memo_content = f"# Investment Memo: {orch.state.target_company}\n\n"
    if not orch.state.agent_reports:
        memo_content += "*No agent reports have been generated yet.*"
    else:
        for name, rep in orch.state.agent_reports.items():
            memo_content += f"## {name.replace('_', ' ').title()} Summary\n"
            memo_content += rep.raw_markdown + "\n\n"
            
    return {
        "session_id": session_id,
        "target_company": orch.state.target_company,
        "industry_sector": orch.state.industry_sector,
        "memo_markdown": memo_content,
        "accumulated_red_flags": orch.state.accumulated_red_flags
    }

```

---

## 🧪 E2E Unit Test Specifications
Ensure the following tests are configured using `pytest` inside `tests/test_orchestrator.py`:

```python
# tests/test_orchestrator.py
import pytest
from swarm.orchestrator import Orchestrator, register_agent, AGENT_REGISTRY

@pytest.fixture
def clean_registry():
    original_registry = AGENT_REGISTRY.copy()
    AGENT_REGISTRY.clear()
    yield
    AGENT_REGISTRY.update(original_registry)

def test_dynamic_agent_registration(clean_registry):
    @register_agent("mock_test_agent")
    class MockAgent:
        def execute(self, context):
            return {"findings": {"status": "ok"}}
            
    assert "mock_test_agent" in AGENT_REGISTRY
    assert AGENT_REGISTRY["mock_test_agent"] == MockAgent

def test_orchestrator_initialization_and_discovery():
    # Verify that initialization correctly auto-discovers and registers sub-agents
    orch = Orchestrator("session-001", "Acme Corp", "software")
    registered_agents = orch.get_registered_agents()
    
    assert len(registered_agents) > 0
    assert "financial_auditor" in registered_agents

def test_orchestrator_loop_execution():
    """Verifies a full successful orchestrator execution loop."""
    orch = Orchestrator("session-002", "Acme Corp", "software")
    frames = list(orch.run_loop("Begin due diligence audit"))
    
    events = [frame["event"] for frame in frames]
    assert "status" in events
    assert "assistant_message" in events
    assert "complete" in events
    
    assert len(orch.state.agent_reports) == 4
    assert orch.state.agent_reports["financial_auditor"].status == "success"

def test_orchestrator_error_isolation(clean_registry):
    """Verifies that an error in one sub-agent does not crash the orchestrator loop."""
    @register_agent("financial_auditor")
    class GoodFinancialAgent:
        def execute(self, context):
            return {"findings": {}, "markdown": "good"}
            
    @register_agent("legal_compliance")
    class CrashLegalAgent:
        def execute(self, context):
            raise RuntimeError("Database connection failed")

    @register_agent("ops_evaluator")
    class GoodOpsAgent:
        def execute(self, context):
            return {"findings": {}, "markdown": "good"}

    @register_agent("brand_sentiment")
    class GoodSentimentAgent:
        def execute(self, context):
            return {"findings": {}, "markdown": "good"}

    orch = Orchestrator("session-003", "Acme Corp", "software")
    frames = list(orch.run_loop("Audit target"))
    
    events = [frame["event"] for frame in frames]
    assert "complete" in events
    
    assert orch.state.agent_reports["legal_compliance"].status == "error"
    assert "Database connection failed" in orch.state.agent_reports["legal_compliance"].findings["error"]
    
    assert orch.state.financial_auditor.status == "success"

def test_orchestrator_hitl_pausing(clean_registry):
    """Verifies that a critical flag or hitl request triggers a loop pause."""
    @register_agent("financial_auditor")
    class DangerFinancialAgent:
        def execute(self, context):
            return {
                "findings": {
                    "hitl_required": True,
                    "hitl_reason": "EBITDA indicates insolvency risks"
                },
                "markdown": "Danger"
            }

    @register_agent("legal_compliance")
    class GoodLegalAgent:
        def execute(self, context):
            return {"findings": {}, "markdown": "good"}

    @register_agent("ops_evaluator")
    class GoodOpsAgent:
        def execute(self, context):
            return {"findings": {}, "markdown": "good"}

    @register_agent("brand_sentiment")
    class GoodSentimentAgent:
        def execute(self, context):
            return {"findings": {}, "markdown": "good"}

    orch = Orchestrator("session-004", "Acme Corp", "software")
    frames = list(orch.run_loop("Audit target"))
    
    events = [frame["event"] for frame in frames]
    assert "hitl_pause" in events
    assert "complete" not in events
    
    assert orch.state.hitl_status == "PAUSED"
    assert orch.state.pending_hitl_question == "Financial Auditor: EBITDA indicates insolvency risks"

def test_orchestrator_hitl_resume(clean_registry):
    """Verifies that resuming a paused loop successfully skips completed agents and finishes."""
    @register_agent("financial_auditor")
    class DangerFinancialAgent:
        def execute(self, context):
            return {
                "findings": {
                    "hitl_required": True,
                    "hitl_reason": "EBITDA indicates insolvency risks"
                },
                "markdown": "Danger"
            }

    @register_agent("legal_compliance")
    class GoodLegalAgent:
        def execute(self, context):
            return {"findings": {}, "markdown": "good"}

    @register_agent("ops_evaluator")
    class GoodOpsAgent:
        def execute(self, context):
            return {"findings": {}, "markdown": "good"}

    @register_agent("brand_sentiment")
    class GoodSentimentAgent:
        def execute(self, context):
            return {"findings": {}, "markdown": "good"}

    orch = Orchestrator("session-005", "Acme Corp", "software")
    
    # 1. First run: should pause at financial auditor
    frames = list(orch.run_loop("Audit target"))
    events = [frame["event"] for frame in frames]
    assert "hitl_pause" in events
    assert "complete" not in events
    assert orch.state.hitl_status == "PAUSED"
    
    # 2. Simulate user response
    orch.state.hitl_status = "RESOLVED"
    orch.state.pending_hitl_question = None
    
    # 3. Resume run: should skip financial auditor and complete
    resume_frames = list(orch.run_loop("Resume audit"))
    resume_events = [frame["event"] for frame in resume_frames]
    
    assert "complete" in resume_events
    assert orch.state.agent_reports["financial_auditor"].status == "success"
    assert orch.state.agent_reports["legal_compliance"].status == "success"
```
