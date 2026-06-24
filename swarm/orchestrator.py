"""
swarm/orchestrator.py
Central Orchestrator loop and agent registry for the M&A Due Diligence Swarm.
Manages dynamic imports, execution state, and Human-in-the-Loop checkpoints.
"""

import os
import json
import logging
import importlib
import pkgutil
from typing import Dict, List, Any, Optional, Type, Generator
from pydantic import BaseModel, Field
from swarm.config import settings
from swarm.utils.llm import call_llm

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

    # Extract paths from package.__path__ (Namespace paths need to be handled carefully)
    paths = list(package.__path__) if hasattr(package, "__path__") else []
    for _, module_name, _ in pkgutil.iter_modules(paths):
        full_module_name = f"{package_name}.{module_name}"
        try:
            importlib.import_module(full_module_name)
            logger.debug(f"Successfully imported module: {full_module_name}")
        except Exception as e:
            logger.error(f"Error loading module {full_module_name}: {str(e)}", exc_info=True)

def load_system_prompt() -> str:
    """Loads system prompt for orchestrator agent synthesis."""
    template_path = os.path.join(os.path.dirname(__file__), "prompt_templates", "orchestrator_system.txt")
    if os.path.exists(template_path):
        try:
            with open(template_path, "r", encoding="utf-8") as f:
                return f.read().strip()
           
        except Exception as e:
            logger.error(f"Error reading system prompt from {template_path}: {e}")
    return (
        "You are the Lead Synthesizer and Orchestrator Agent for the M&A Due Diligence Swarm.\n"
        "Your primary objective is to coordinate specialized sub-agents and synthesize their reports "
        "into a comprehensive, professional, and structured Investment Memo with a clear Buy, Hold, or Pass recommendation."
    )

# Session persistence helpers
def save_session(state: 'SessionState') -> None:
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

def load_session(session_id: str) -> Optional['SessionState']:
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
