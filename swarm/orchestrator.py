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

    # Check package.__path__ is valid
    if not hasattr(package, "__path__"):
        logger.error(f"Package '{package_name}' has no __path__ attribute.")
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
