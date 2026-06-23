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
            # Initialize with sector/industry configuration if applicable
            if hasattr(agent_class, "industry"):
                agent_instance = agent_class(industry=self.state.industry_sector)
            else:
                agent_instance = agent_class()
                
            logger.info(f"Executing agent: {agent_name_clean}")
            # Call standard execute method
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
        Main execution loop. Routes tasks to sub-agents, handles red-flag triggers,
        and yields execution frames for SSE stream compatibility.
        """
        # Append User Message
        from datetime import datetime, timezone
        self.state.history.append(ChatMessage(
            role="user",
            content=user_message,
            timestamp=datetime.now(timezone.utc).isoformat()
        ))
        
        yield {"event": "status", "message": f"Analyzing due diligence parameters for {self.state.target_company}..."}
        
        # Determine active agents based on configuration
        active_agents = ["financial_auditor", "legal_compliance", "ops_evaluator", "brand_sentiment"]
        
        for agent_name in active_agents:
            yield {"event": "status", "message": f"Initializing {agent_name.replace('_', ' ').title()}..."}
            
            context = {
                "target_company": self.state.target_company,
                "session_id": self.state.session_id,
                "data_room_path": f"data_room/uploads/{agent_name.split('_')[0]}"
            }
            
            # Execute sub-agent
            report = self.dispatch_agent(agent_name, context)
            self.state.agent_reports[agent_name] = report
            
            # Check for critical red-flag triggers (Human-In-The-Loop Checkpoint)
            if report.findings.get("hitl_required") or "CRITICAL" in str(report.findings.get("flags", [])):
                self.state.hitl_status = "PAUSED"
                self.state.pending_hitl_question = report.findings.get("hitl_reason", "Unspecified critical risk flagged.")
                
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
                
            yield {
                "event": "agent_status",
                "agent": agent_name,
                "status": report.status,
                "message": f"Finished {agent_name.replace('_', ' ').title()} audit."
            }

        # Step 3: Synthesis of Final Investment Memo
        yield {"event": "status", "message": "Compiling final investment memo..."}
        # Compile all sub-agent reports into Markdown
        memo_content = "# Investment Memo: " + self.state.target_company + "\n\n"
        for name, rep in self.state.agent_reports.items():
            memo_content += f"## {name.replace('_', ' ').title()} Summary\n"
            memo_content += rep.raw_markdown + "\n\n"
            
        yield {"event": "assistant_message", "content": memo_content}
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

router = APIRouter(prefix="/api/hitl", tags=["HITL"])

class HITLResponsePayload(BaseModel):
    session_id: str
    selected_option: str  # "A", "B", or "C"
    custom_feedback: Optional[str] = None

@router.post("/respond")
async def submit_hitl_response(payload: HITLResponsePayload):
    if payload.session_id not in SESSIONS:
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
```
