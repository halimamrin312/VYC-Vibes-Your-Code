"""
tests/test_orchestrator.py
E2E Unit tests for the Swarm Orchestrator agent registry, execution loop,
error isolation, and Human-in-the-Loop (HITL) pause behaviors.
"""

import pytest
from swarm.orchestrator import Orchestrator, register_agent, AGENT_REGISTRY, AgentReport

@pytest.fixture
def clean_registry():
    """Temporarily clears the agent registry to isolate registration tests."""
    original_registry = AGENT_REGISTRY.copy()
    AGENT_REGISTRY.clear()
    yield
    AGENT_REGISTRY.update(original_registry)

def test_dynamic_agent_registration(clean_registry):
    """Verifies that the @register_agent decorator correctly adds agents."""
    @register_agent("mock_test_agent")
    class MockAgent:
        def execute(self, context):
            return {"findings": {"status": "ok"}, "markdown": "ok"}
            
    assert "mock_test_agent" in AGENT_REGISTRY
    assert AGENT_REGISTRY["mock_test_agent"] == MockAgent

def test_orchestrator_initialization_and_discovery():
    """Verifies that orchestrator correctly loads and registers all sub-agents."""
    orch = Orchestrator("session-001", "Acme Corp", "software")
    registered_agents = orch.get_registered_agents()
    
    assert len(registered_agents) > 0
    assert "financial_auditor" in registered_agents
    assert "legal_compliance" in registered_agents
    assert "ops_evaluator" in registered_agents
    assert "brand_sentiment" in registered_agents

def test_orchestrator_loop_execution():
    """Verifies a full successful orchestrator execution loop."""
    orch = Orchestrator("session-002", "AAPL", "software")
    frames = list(orch.run_loop("Begin due diligence audit"))
    
    # Assert we got status updates and completion event
    events = [frame["event"] for frame in frames]
    assert "status" in events
    assert "assistant_message" in events
    assert "complete" in events
    
    # Confirm reports are stored
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
    
    # Ensure loop completes despite the crash
    events = [frame["event"] for frame in frames]
    assert "complete" in events
    
    # Verify the crashed agent is marked as error
    assert orch.state.agent_reports["legal_compliance"].status == "error"
    assert "Database connection failed" in orch.state.agent_reports["legal_compliance"].findings["error"]
    
    # Verify the healthy agents executed successfully
    assert orch.state.agent_reports["financial_auditor"].status == "success"
    assert orch.state.agent_reports["ops_evaluator"].status == "success"

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
    
    # Check that loop yielded a hitl_pause and stopped
    events = [frame["event"] for frame in frames]
    assert "hitl_pause" in events
    assert "complete" not in events  # Loop should be paused
    
    assert orch.state.hitl_status == "PAUSED"
    assert orch.state.pending_hitl_question == "Financial Auditor Wave 1: EBITDA indicates insolvency risks"

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

def test_orchestrator_chronological_context_passing(clean_registry):
    """Verifies that Wave 2 agents receive distilled context from Wave 1."""
    @register_agent("financial_auditor")
    class MockFinancialAgent:
        def execute(self, context):
            return {
                "findings": {
                    "summary": "Financial analysis complete.",
                    "latest_revenue": 100000.0,
                    "latest_debt_to_equity": 2.5,
                    "cash_runway_months": 8.0,
                    "flags": [{"severity": "CRITICAL", "message": "High debt ratio"}]
                },
                "markdown": "# Financial Report"
            }

    @register_agent("brand_sentiment")
    class MockSentimentAgent:
        def execute(self, context):
            return {"findings": {"summary": "Sentiment is stable."}, "markdown": "Sentiment Report"}

    @register_agent("legal_compliance")
    class MockLegalAgent:
        def execute(self, context):
            wave_1 = context.get("wave_1_context", {})
            assert "financial_auditor" in wave_1
            assert "brand_sentiment" in wave_1
            assert wave_1["financial_auditor"]["latest_debt_to_equity"] == 2.5
            
            from swarm.agents.legal_compliance import LegalCompliance
            instance = LegalCompliance()
            return instance.execute(context)

    @register_agent("ops_evaluator")
    class MockOpsAgent:
        def execute(self, context):
            wave_1 = context.get("wave_1_context", {})
            assert "financial_auditor" in wave_1
            
            from swarm.agents.ops_evaluator import OperationsEvaluator
            instance = OperationsEvaluator()
            return instance.execute(context)

    orch = Orchestrator("session-006", "Acme Corp", "software")
    frames = list(orch.run_loop("Audit target"))
    
    assert orch.state.hitl_status == "PAUSED"
    
    orch.state.hitl_status = "RESOLVED"
    orch.state.pending_hitl_question = None
    
    resume_frames = list(orch.run_loop("Resume audit"))
    # Wave 2 runs and pauses again due to legal/ops flagging critical issues
    assert orch.state.hitl_status == "PAUSED"
    
    # Resume the loop second time to allow final synthesis to run
    orch.state.hitl_status = "RESOLVED"
    orch.state.pending_hitl_question = None
    
    final_frames = list(orch.run_loop("Resume audit 2"))
    events = [frame["event"] for frame in final_frames]
    assert "complete" in events
    
    assert "legal_compliance" in orch.state.agent_reports
    legal_report = orch.state.agent_reports["legal_compliance"]
    assert legal_report.status == "success"
    assert any("high financial risk" in f["message"].lower() for f in legal_report.findings.get("flags", []))
    
    assert "ops_evaluator" in orch.state.agent_reports
    ops_report = orch.state.agent_reports["ops_evaluator"]
    assert ops_report.status == "success"
    assert any("short cash runway" in f["message"].lower() for f in ops_report.findings.get("flags", []))

def test_agent_dispatch_retry_and_fallback(clean_registry):
    """Verifies that dispatch_agent retries on error."""
    fail_count = 0
    
    @register_agent("ops_evaluator")
    class FlakyOpsAgent:
        def execute(self, context):
            nonlocal fail_count
            fail_count += 1
            if fail_count < 2:
                raise RuntimeError("API timeout")
            return {"findings": {"status": "recovered"}, "markdown": "Recovered"}
            
    orch = Orchestrator("session-007", "Acme Corp", "software")
    report = orch.dispatch_agent("ops_evaluator", {})
    assert report.status == "success"
    assert fail_count == 2

