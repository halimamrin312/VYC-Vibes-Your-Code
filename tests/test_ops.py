import pytest
import os
import shutil
import pandas as pd
from swarm.agents.ops_evaluator import OperationsEvaluator

def test_reviews_diligence_success():
    # Setup mock reviews CSV with positive sentiment and minimal complaints
    session_id = "test_reviews_success"
    log_dir = os.path.join("data_room", "uploads", "logs", session_id)
    os.makedirs(log_dir, exist_ok=True)
    
    csv_file = os.path.join(log_dir, "customer_employee_reviews.csv")
    reviews_data = pd.DataFrame([
        {"Category": "Support", "Rating": 5, "ReviewText": "Support was amazing and fast."},
        {"Category": "Support", "Rating": 5, "ReviewText": "Very helpful customer assistance."},
        {"Category": "Delivery", "Rating": 4, "ReviewText": "Delivery was quick, box intact."},
        {"Category": "Management", "Rating": 5, "ReviewText": "Transparent leadership team."},
        {"Category": "Work-Life Balance", "Rating": 5, "ReviewText": "Supportive workplace environment."}
    ])
    reviews_data.to_csv(csv_file, index=False)
    
    try:
        agent = OperationsEvaluator(industry="software")
        result = agent.execute({
            "target_company": "HealthyTech",
            "session_id": session_id
        })
        
        assert result["findings"]["status"] == "success"
        metrics = result["findings"]["metrics"]
        assert metrics["csi"] == 1.0
        assert metrics["esi"] == 1.0
        assert metrics["delivery_issues"] == 0
        assert metrics["turnover_issues"] == 0
        assert len(result["findings"]["flags"]) == 0
        
    finally:
        if os.path.exists(log_dir):
            shutil.rmtree(os.path.dirname(log_dir), ignore_errors=True)

def test_reviews_diligence_warnings():
    # Setup mock reviews CSV with negative sentiment and multiple complaints
    session_id = "test_reviews_warnings"
    log_dir = os.path.join("data_room", "uploads", "logs", session_id)
    os.makedirs(log_dir, exist_ok=True)
    
    csv_file = os.path.join(log_dir, "customer_employee_reviews.csv")
    reviews_data = pd.DataFrame([
        {"Category": "Support", "Rating": 2, "ReviewText": "Delay in response was very annoying. Poor service."},
        {"Category": "Support", "Rating": 1, "ReviewText": "Support tickets ignored. Slow and lost refund request."},
        {"Category": "Delivery", "Rating": 5, "ReviewText": "Delivery was fast."},
        {"Category": "Management", "Rating": 2, "ReviewText": "Management causes high turnover. Toxic executives."},
        {"Category": "Work-Life Balance", "Rating": 1, "ReviewText": "Extreme burnout, too much overtime required."}
    ])
    reviews_data.to_csv(csv_file, index=False)
    
    try:
        agent = OperationsEvaluator(industry="manufacturing")
        result = agent.execute({
            "target_company": "StrugglingMfg",
            "session_id": session_id
        })
        
        assert result["findings"]["status"] == "success"
        metrics = result["findings"]["metrics"]
        # CSI = 1/3 = ~33.3%, ESI = 0/2 = 0%
        assert metrics["csi"] < 0.50
        assert metrics["esi"] < 0.50
        assert metrics["delivery_issues"] == 2
        assert metrics["turnover_issues"] == 2
        
        # Verify the warning flags are raised
        flags = result["findings"]["flags"]
        assert len(flags) == 2
        flag_metrics = [f["metric"] for f in flags]
        assert "Customer Support Index" in flag_metrics
        assert "Employee Sentiment Index" in flag_metrics
        
    finally:
        if os.path.exists(log_dir):
            shutil.rmtree(os.path.dirname(log_dir), ignore_errors=True)

def test_reviews_diligence_missing_logs():
    # Executes using mock public review fallback
    agent = OperationsEvaluator(industry="generic")
    result = agent.execute({
        "target_company": "MockGenericCorp",
        "session_id": "test_session_missing_logs"
    })
    
    assert result["findings"]["status"] == "success"
    metrics = result["findings"]["metrics"]
    assert metrics["total_reviews"] > 0
    assert "findings" in result
    assert "markdown" in result

def test_ops_runway_warning_propagation():
    # Setup context indicating a short cash runway
    agent = OperationsEvaluator(industry="generic")
    result = agent.execute({
        "target_company": "ShortRunwayCorp",
        "session_id": "test_session_runway",
        "wave_1_context": {
            "financial_auditor": {
                "cash_runway_months": 6.0
            }
        }
    })
    
    assert result["findings"]["status"] == "success"
    flags = result["findings"]["flags"]
    assert len(flags) > 0
    assert any("short cash runway" in f["message"].lower() for f in flags)
    assert any(f["severity"] == "CRITICAL" for f in flags)

def test_ambiguous_reviews_classification(monkeypatch):
    agent = OperationsEvaluator(industry="generic")
    
    # Mock call_llm to simulate classifying index 0 as negative
    def mock_call_llm(system_prompt, user_prompt):
        return "```json\n[0]\n```"
        
    monkeypatch.setattr("swarm.agents.ops_evaluator.call_llm", mock_call_llm)
    
    ambiguous_reviews = [
        {"Category": "Support", "ReviewText": "Support response time was average, not great.", "Rating": 3},
        {"Category": "Work-Life Balance", "ReviewText": "Workload is fine.", "Rating": 3}
    ]
    
    negative_reviews = agent._classify_ambiguous_reviews(ambiguous_reviews)
    assert len(negative_reviews) == 1
    assert negative_reviews[0]["Category"] == "Support"

