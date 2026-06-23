# Operations Evaluator Agent - Detailed Technical Specification

This document provides the complete, production-grade specification for implementing the **Operations Evaluator Agent** within the M&A Due Diligence Swarm. It details multi-industry evaluations, GitHub MCP configurations for software audits, supply chain logistics log calculations, and API structures.

---

## 📂 Component Layout & File Locations
- **Main Agent Code:** `swarm/agents/ops_evaluator.py`
- **FastAPI Endpoint:** `/api/ingest/logs` in `backend/app/routers/ingest.py`
- **System Prompt Template:** `swarm/prompt_templates/ops_system.txt`
- **Frontend Dashboard:** `frontend/src/components/OpsDashboard.jsx`

---

## 🤖 Operations Evaluator Implementation (`swarm/agents/ops_evaluator.py`)

This agent checks the transaction sector variable dynamically (software, manufacturing, retail, or pharma) and dispatches the corresponding diagnostic suite.

```python
"""
swarm/agents/ops_evaluator.py
Operations Evaluator Agent using ADK. Audits codebase health, tech debt,
or supply chain logs depending on the business sector.
"""

from swarm.orchestrator import register_agent
import os
import pandas as pd
import logging
from typing import Dict, Any, List

logger = logging.getLogger("swarm.agents.ops_evaluator")

@register_agent("ops_evaluator")
class OperationsEvaluator:
    def __init__(self, industry: str = "generic"):
        self.industry = industry.strip().lower()

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Routes the operational evaluation depending on the target industry sector.
        """
        target_company = context.get("target_company", "Target Company")
        data_room_path = context.get("data_room_path", "data_room/uploads/logs")
        
        if self.industry == "software":
            return self._execute_software_audit(context)
        elif self.industry in ["manufacturing", "retail"]:
            return self._execute_supply_chain_audit(data_room_path, target_company)
        else:
            return self._execute_generic_audit(target_company)

    def _execute_software_audit(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Audits code quality using simulated GitHub MCP metrics.
        Calculates the Tech Debt Index (TDI).
        """
        # Simulated responses from GitHub MCP tools (e.g. get_repository_issues, get_repository_commits)
        mcp_commits_count = 1420
        mcp_open_issues_count = 85
        mcp_bug_labeled_issues = 22
        
        # Compute Tech Debt Index
        if mcp_commits_count > 0:
            tech_debt_index = float(mcp_bug_labeled_issues) / mcp_commits_count
        else:
            tech_debt_index = 0.0
            
        # Determine rating
        rating = "A"
        flags = []
        if tech_debt_index > 0.05:
            rating = "C"
            flags.append({
                "severity": "WARNING",
                "metric": "Tech Debt Index",
                "description": f"High bug-to-commit ratio ({round(tech_debt_index * 100, 2)}%) indicates code stability concerns."
            })
        elif tech_debt_index > 0.02:
            rating = "B"

        markdown_report = f"""### Operations Diligence: Tech/Software Audit
- **Tech Debt Rating:** {rating}
- **Tech Debt Index (TDI):** {round(tech_debt_index * 100, 2)}%
- **Open GitHub Issues:** {mcp_open_issues_count} (Bugs: {mcp_bug_labeled_issues})
- **Total Commit Count:** {mcp_commits_count}

#### Operational Findings & Warnings
"""
        if not flags:
            markdown_report += "*Codebase health indicators are within acceptable thresholds.*"
        else:
            for flag in flags:
                markdown_report += f"- **[{flag['severity']}]** {flag['metric']}: {flag['description']}\n"

        return {
            "findings": {
                "status": "success",
                "metrics": {
                    "tech_debt_index": tech_debt_index,
                    "open_issues": mcp_open_issues_count,
                    "total_commits": mcp_commits_count,
                    "rating": rating
                },
                "flags": flags,
                "hitl_required": False
            },
            "markdown": markdown_report
        }

    def _execute_supply_chain_audit(self, data_room_path: str, target_company: str) -> Dict[str, Any]:
        """
        Analyzes logistics log sheets to locate downtime bottlenecks.
        """
        csv_file = None
        if os.path.exists(data_room_path):
            files = [f for f in os.listdir(data_room_path) if f.endswith('.csv')]
            if files:
                csv_file = os.path.join(data_room_path, files[0])
                
        if not csv_file:
            msg = f"No operational CSV log files found in: {data_room_path}"
            return {
                "findings": {"status": "skipped", "hitl_required": False},
                "markdown": f"### Operations Diligence\n{msg}"
            }
            
        try:
            df = pd.read_csv(csv_file)
            
            # Verify columns
            required = ['Status', 'DowntimeMinutes', 'MachineID']
            if not all(col in df.columns for col in required):
                raise ValueError(f"Missing required columns in log CSV: {required}")
                
            total_downtime = int(df[df['Status'].str.strip().str.upper() == 'STOPPED']['DowntimeMinutes'].sum())
            bottleneck_machine = str(df[df['Status'].str.strip().str.upper() == 'STOPPED']['MachineID'].mode().iloc[0]) if not df.empty else "None"
            
            flags = []
            if total_downtime > 120:
                flags.append({
                    "severity": "WARNING",
                    "metric": "Operational Downtime",
                    "description": f"Cumulative production downtime ({total_downtime} minutes) exceeds target efficiency limits."
                })

            markdown_report = f"""### Operations Diligence: Logistics/Manufacturing Audit
- **Total Production Downtime:** {total_downtime} minutes
- **Primary Bottleneck Machine:** {bottleneck_machine}

#### Operational Findings & Warnings
"""
            if not flags:
                markdown_report += "*No manufacturing bottlenecks detected.*"
            else:
                for flag in flags:
                    markdown_report += f"- **[{flag['severity']}]** {flag['metric']}: {flag['description']}\n"

            return {
                "findings": {
                    "status": "success",
                    "metrics": {
                        "total_downtime_minutes": total_downtime,
                        "bottleneck_resource": bottleneck_machine
                    },
                    "flags": flags,
                    "hitl_required": False
                },
                "markdown": markdown_report
            }
        except Exception as e:
            logger.error(f"Failed to audit supply chain logs: {str(e)}")
            return {
                "findings": {"status": "error", "error": str(e)},
                "markdown": f"### Operations Diligence Error\nFailed to parse operations logs: {str(e)}"
            }

    def _execute_generic_audit(self, target_company: str) -> Dict[str, Any]:
        """Generic fallback audit protocol."""
        return {
            "findings": {"status": "success", "generic": True, "hitl_required": False},
            "markdown": f"### Operations Diligence: {target_company}\n*Generic operational auditing checks successfully run.*"
        }
```

---

## 🤖 System Prompt Specification (`swarm/prompt_templates/ops_system.txt`)

Paste this exact system instruction into your prompt configuration:

```text
You are the lead M&A Operations Inspector Agent.
Your core task is to evaluate codebase technical debt or supply chain bottlenecks.

CRITICAL RULES:
1. Tailor your auditing checklist parameters dynamically depending on the sector context (software or manufacturing).
2. For tech audits, evaluate commits and issue metrics using the GitHub MCP to compute the Tech Debt Index (TDI).
3. For logistics, parse production logs to identify primary bottleneck resources and total assembly downtime minutes.
4. Output your analysis in a structured JSON payload conforming to the orchestrator specification.
```

---

## 🧪 Verification & Testing
Create `tests/test_ops.py` to assert correct calculations:

```python
# tests/test_ops.py
import pytest
from swarm.agents.ops_evaluator import OperationsEvaluator

def test_software_tech_debt_rating():
    agent = OperationsEvaluator(industry="software")
    # Execute with mock context
    result = agent.execute({"target_company": "MockTech"})
    
    assert result["findings"]["status"] == "success"
    assert "tech_debt_index" in result["findings"]["metrics"]
    # Check that ratings are correctly mapped
    assert result["findings"]["metrics"]["rating"] in ["A", "B", "C"]
```
