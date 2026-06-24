"""
backend/app/routers/chat.py
Real-time chat endpoint with Server-Sent Events (SSE) streaming of agent actions.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Dict, Optional
import json
import logging
from swarm.orchestrator import Orchestrator

# Setup logging
logger = logging.getLogger("backend.app.routers.chat")

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
            logger.info(f"Restoring session {request.session_id} from disk.")
            SESSIONS[request.session_id] = Orchestrator(
                session_id=request.session_id,
                target_company=request.target_company,
                industry_sector=request.industry_sector
            )
            SESSIONS[request.session_id].state = saved_state
        else:
            logger.info(f"Creating new Orchestrator session for ID: {request.session_id}")
            SESSIONS[request.session_id] = Orchestrator(
                session_id=request.session_id,
                target_company=request.target_company,
                industry_sector=request.industry_sector
            )
        
    orch = SESSIONS[request.session_id]
    
    # Verify that the Orchestrator is not currently paused in HITL state
    if orch.state.hitl_status == "PAUSED":
        logger.warning(f"Session {request.session_id} is PAUSED for HITL; stream requested.")
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
