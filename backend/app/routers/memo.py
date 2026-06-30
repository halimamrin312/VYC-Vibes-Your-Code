"""
backend/app/routers/memo.py
Investment memo retrieval endpoints.
"""

from fastapi import APIRouter, HTTPException
from backend.app.routers.chat import SESSIONS

router = APIRouter(prefix="/api/memo", tags=["Memo"])

@router.get("/{session_id}")
def get_investment_memo(session_id: str):
    """
    Retrieves the compiled Investment Memo markdown for the specified session_id.
    """
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
        "accumulated_red_flags": orch.state.accumulated_red_flags,
        "agent_reports": {k: v.model_dump() for k, v in orch.state.agent_reports.items()}
    }
