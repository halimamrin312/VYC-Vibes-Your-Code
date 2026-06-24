"""
backend/app/routers/hitl.py
Human-in-the-Loop (HITL) response submission router.
"""

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

    # Clear cached financial auditor report if it was paused for missing files, so it reruns
    if "financial_auditor" in orch.state.agent_reports:
        rep = orch.state.agent_reports["financial_auditor"]
        findings = rep.findings
        # Check if it was paused/skipped due to missing files
        if findings.get("status") == "skipped" or findings.get("hitl_required") and "private" in findings.get("hitl_reason", "").lower():
            del orch.state.agent_reports["financial_auditor"]
    
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
