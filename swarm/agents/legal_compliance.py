"""
swarm/agents/legal_compliance.py
Legal Compliance agent skeleton registered with the Orchestrator.
"""

from swarm.orchestrator import register_agent
import logging
from typing import Dict, Any

logger = logging.getLogger("swarm.agents.legal_compliance")

@register_agent("legal_compliance")
class LegalCompliance:
    def __init__(self, industry: str = "generic"):
        self.industry = industry

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"LegalCompliance executing for industry: {self.industry}")
        
        # Read Wave 1 context if available
        wave_1 = context.get("wave_1_context", {})
        fin_auditor = wave_1.get("financial_auditor", {})
        
        debt_to_equity = fin_auditor.get("latest_debt_to_equity", 0.0)
        has_critical_financial_flag = False
        
        fin_flags = fin_auditor.get("flags", [])
        for f in fin_flags:
            if isinstance(f, dict) and f.get("severity") == "CRITICAL":
                has_critical_financial_flag = True
            elif isinstance(f, str) and f.upper() == "CRITICAL":
                has_critical_financial_flag = True
                
        findings = {
            "liabilities": "No significant legal liabilities identified in target contracts.",
            "flags": []
        }
        markdown = "### Legal Compliance Report\n\n- No high-risk pending litigation found.\n- Standard change-of-control clauses are in order.\n"
        
        if (debt_to_equity and debt_to_equity > 2.0) or has_critical_financial_flag:
            msg = f"WARNING: Target company has high financial risk (debt-to-equity: {debt_to_equity}). This triggers debt covenant review and bankruptcy default risk in active contracts."
            findings["flags"].append({
                "severity": "CRITICAL",
                "message": msg
            })
            findings["liabilities"] = f"Critical debt default risk identified based on financial auditor report: Debt-to-Equity is {debt_to_equity}."
            markdown += f"\n> ⚠️ **Critical Legal Risk**: {msg}\n"
            
        return {
            "findings": findings,
            "markdown": markdown
        }
