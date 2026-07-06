# tests/test_sentiment.py
import pytest
import os
import shutil
import pandas as pd
from swarm.tools.data_sanitizer import sanitize_search_query
from swarm.agents.brand_sentiment import BrandSentiment

def test_query_sanitizer_rules():
    raw_query = "Acme Corp acquisition terms by VentureCorp"
    sensitive_terms = ["VentureCorp"]
    
    sanitized = sanitize_search_query(raw_query, sensitive_terms)
    
    # Assert sensitive terms and M&A keywords are removed
    assert "VentureCorp" not in sanitized
    assert "acquisition" not in sanitized
    assert "Acme Corp" in sanitized

def test_brand_sentiment_mock_calculation(monkeypatch):
    # Mock call_llm to avoid external API calls during verification
    monkeypatch.setattr("swarm.agents.brand_sentiment.call_llm", lambda *args, **kwargs: None)
    
    agent = BrandSentiment(industry="software")
    context = {
        "target_company": "HealthyCorp",
        "sensitive_terms": [],
        "session_id": "test_mock_sentiment"
    }
    
    result = agent.execute(context)
    assert result["findings"]["status"] == "success"
    metrics = result["findings"]["metrics"]
    
    # Standard mocks has 3 positive (5, 4, 5), 0 neutral, 2 negative (2, 1) out of 5 reviews
    # BHI = (3 - 2)/5 = 0.2
    assert metrics["brand_health_index"] == 0.2
    assert metrics["pos_ratio"] == 0.6
    assert metrics["neg_ratio"] == 0.4
    assert len(result["findings"]["flags"]) == 1  # Negative feedback ratio > 20% warning
    assert any(f["metric"] == "Negative Feedback Ratio" for f in result["findings"]["flags"])

def test_brand_sentiment_negative_bhi_warning(monkeypatch):
    monkeypatch.setattr("swarm.agents.brand_sentiment.call_llm", lambda *args, **kwargs: None)
    
    # Create local CSV with bad reviews to force negative BHI
    session_id = "test_negative_bhi"
    brand_dir = os.path.join("data_room", "uploads", "brand", session_id)
    os.makedirs(brand_dir, exist_ok=True)
    
    csv_file = os.path.join(brand_dir, "reviews.csv")
    reviews_df = pd.DataFrame([
        {"Rating": 1, "ReviewText": "Horrible app. Crashed my server."},
        {"Rating": 2, "ReviewText": "Very bad customer support."},
        {"Rating": 3, "ReviewText": "Average performance."},
        {"Rating": 5, "ReviewText": "Excellent features!"}
    ])
    reviews_df.to_csv(csv_file, index=False)
    
    try:
        agent = BrandSentiment(industry="retail")
        context = {
            "target_company": "FailingStore",
            "sensitive_terms": [],
            "session_id": session_id
        }
        
        result = agent.execute(context)
        assert result["findings"]["status"] == "success"
        metrics = result["findings"]["metrics"]
        
        # BHI = (1 - 2) / 4 = -0.25
        assert metrics["brand_health_index"] == -0.25
        assert len(result["findings"]["flags"]) == 1
        assert result["findings"]["flags"][0]["metric"] == "Brand Health Index"
        assert "Negative BHI score" in result["findings"]["flags"][0]["description"]
        
    finally:
        # Cleanup
        if os.path.exists(brand_dir):
            shutil.rmtree(os.path.dirname(brand_dir), ignore_errors=True)

def test_brand_sentiment_local_csv_ingestion(monkeypatch):
    monkeypatch.setattr("swarm.agents.brand_sentiment.call_llm", lambda *args, **kwargs: None)
    
    session_id = "test_local_ingest"
    brand_dir = os.path.join("data_room", "uploads", "brand", session_id)
    os.makedirs(brand_dir, exist_ok=True)
    
    csv_file = os.path.join(brand_dir, "customer_satisfaction.csv")
    reviews_df = pd.DataFrame([
        {"CustomerScore": 5, "CustomerFeedback": "Amazing products!"},
        {"CustomerScore": 4, "CustomerFeedback": "Liked it."}
    ])
    reviews_df.to_csv(csv_file, index=False)
    
    try:
        agent = BrandSentiment(industry="manufacturing")
        context = {
            "target_company": "GoodMfg",
            "sensitive_terms": [],
            "session_id": session_id
        }
        
        result = agent.execute(context)
        assert result["findings"]["status"] == "success"
        metrics = result["findings"]["metrics"]
        
        # BHI = (2 - 0) / 2 = 1.0
        assert metrics["brand_health_index"] == 1.0
        assert metrics["total_reviews"] == 2
        assert len(result["findings"]["flags"]) == 0
        
    finally:
        if os.path.exists(brand_dir):
            shutil.rmtree(os.path.dirname(brand_dir), ignore_errors=True)
