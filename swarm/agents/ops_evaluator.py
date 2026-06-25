"""
swarm/agents/ops_evaluator.py
Operations Evaluator agent skeleton registered with the Orchestrator.
"""

from swarm.orchestrator import register_agent
import logging
from typing import Dict, Any

logger = logging.getLogger("swarm.agents.ops_evaluator")

@register_agent("ops_evaluator")
class OperationsEvaluator:
    def __init__(self, industry: str = "generic"):
        self.industry = industry

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"OperationsEvaluator executing for industry: {self.industry}")
        
        # Read Wave 1 context if available
        wave_1 = context.get("wave_1_context", {})
        fin_auditor = wave_1.get("financial_auditor", {})
        
        cash_runway = fin_auditor.get("cash_runway_months", "Infinite (Positive Cash Flow)")
        is_runway_short = False
        if isinstance(cash_runway, (int, float)) and cash_runway < 12.0:
            is_runway_short = True
            
        findings = {
            "efficiency_index": 0.82,
            "flags": []
        }
        markdown = "### Operations Evaluation Report\n\n- Operational Efficiency Index: 82%\n- Infrastructure scalability matches sector standards.\n"
        
        if is_runway_short:
            msg = f"WARNING: Target company has short cash runway ({cash_runway} months). Operational expenditures (OpEx) must be audited for cost reduction opportunities."
            findings["flags"].append({
                "severity": "CRITICAL",
                "message": msg
            })
            markdown += f"\n> ⚠️ **Critical Operational Risk**: {msg}\n"
            
        return {
            "findings": findings,
            "markdown": markdown
        }
