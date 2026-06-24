"""
tests/test_financial.py
Unit and integration tests for the FinancialAuditor agent, pandas calculations tool,
SEC EDGAR MCP server, yfinance normalization, Companies House simulator, and FastAPI ingestion endpoint.
"""

import pytest
import os
import io
import shutil
import pandas as pd
from fastapi.testclient import TestClient
from swarm.tools.pandas_analyst import run_financial_analysis
from swarm.agents.financial_auditor import FinancialAuditor, classify_company, normalize_yfinance_data
from swarm.tools.companies_house import get_companies_house_accounts
from mcp_servers.edgar_mcp.server import mcp_search_company, mcp_get_financials, mcp_get_filings
from backend.app.main import app

def test_pandas_analyst_ratios(tmp_path):
    # Setup mock CSV contents with Cash column
    csv_data = """Period,Revenue,CostOfGoodsSold,OperatingExpenses,CashInflow,CashOutflow,TotalAssets,TotalLiabilities,TotalEquity,InterestExpense,Cash
2025-Q1,1000000,300000,500000,1000000,1200000,5000000,2000000,2000000,50000,600000"""
    
    file_path = tmp_path / "test_financials.csv"
    file_path.write_text(csv_data)
    
    results = run_financial_analysis(str(file_path))
    
    assert "error" not in results
    assert results["latest_debt_to_equity"] == 1.0  # Liabilities (2M) / Equity (2M)
    assert results["avg_monthly_burn"] == 200000.0  # Outflow (1.2M) - Inflow (1.0M)
    assert results["ebitda_margin"] == 0.20  # (1M - 300k - 500k) / 1M = 200k/1M = 0.20
    assert results["cash_runway_months"] == 3.0  # Cash (600k) / Burn (200k)

def test_pandas_analyst_missing_columns(tmp_path):
    # Setup mock CSV missing TotalEquity
    csv_data = """Period,Revenue,CostOfGoodsSold,OperatingExpenses,CashInflow,CashOutflow,TotalAssets,TotalLiabilities
2025-Q1,1000000,300000,500000,1000000,1200000,5000000,2000000"""
    
    file_path = tmp_path / "test_invalid.csv"
    file_path.write_text(csv_data)
    
    results = run_financial_analysis(str(file_path))
    assert "error" in results
    assert "Missing required columns" in results["error"]

def test_company_classification():
    # Heuristics & LLM classifications
    res_us = classify_company("AAPL", "software")
    assert res_us["type"] == "public"
    assert res_us["jurisdiction"] == "US"
    assert res_us["ticker"] == "AAPL"

    res_in = classify_company("RELIANCE.NS", "generic")
    assert res_in["type"] == "public"
    assert res_in["jurisdiction"] == "IN"
    assert res_in["ticker"] == "RELIANCE.NS"

    res_uk_private = classify_company("Barclays Holdings Ltd", "retail")
    assert res_uk_private["type"] == "private"
    assert res_uk_private["jurisdiction"] == "UK"

def test_yfinance_normalization():
    res = normalize_yfinance_data("RELIANCE.NS")
    assert res["latest_revenue"] == 10000000000000.0
    assert res["latest_debt_to_equity"] == 0.42
    assert res["cash_runway_months"] == "Infinite (Positive Cash Flow)"

    res_aapl = normalize_yfinance_data("AAPL")
    assert res_aapl["latest_revenue"] == 385600000000.0
    assert res_aapl["ebitda_margin"] == 0.33

def test_companies_house_simulator():
    res = get_companies_house_accounts("Acme Diligence UK Ltd")
    assert res is not None
    assert res["company_name"] == "ACME DILIGENCE UK LTD"
    assert res["latest_accounts"]["latest_revenue"] == 4500000.0
    assert res["latest_accounts"]["latest_debt_to_equity"] == 2.25

def test_financial_auditor_skipped_if_no_file(tmp_path):
    auditor = FinancialAuditor(industry="software")
    context = {
        "target_company": "Acme Private Corp",
        "session_id": "test-session-missing",
        "data_room_path": str(tmp_path / "empty_dir")
    }
    
    # Target is private, no file -> Should pause via HITL
    report = auditor.execute(context)
    assert report["findings"]["hitl_required"] is True
    assert "upload" in report["markdown"].lower()
    assert "private" in report["findings"]["hitl_reason"].lower()

def test_financial_auditor_manual_upload_integration():
    # Setup session uploads folder and place a target CSV file
    session_id = "test-session-upload-flow"
    session_dir = os.path.join("data_room", "uploads", "financial", session_id)
    os.makedirs(session_dir, exist_ok=True)
    
    csv_data = """Period,Revenue,CostOfGoodsSold,OperatingExpenses,CashInflow,CashOutflow,TotalAssets,TotalLiabilities,TotalEquity,Cash
2025-Q1,1200000,400000,500000,1200000,1000000,6000000,2000000,4000000,800000"""
    file_path = os.path.join(session_dir, "target_financials.csv")
    with open(file_path, "w") as f:
        f.write(csv_data)

    auditor = FinancialAuditor(industry="manufacturing")
    context = {
        "target_company": "Acme Private Corp",
        "session_id": session_id,
        "data_room_path": "data_room/uploads/financial"
    }

    try:
        # Should now find the uploaded file and run successfully
        report = auditor.execute(context)
        findings = report["findings"]
        assert findings["status"] == "success"
        assert findings["metrics"]["latest_revenue"] == 1200000.0
        assert findings["metrics"]["latest_debt_to_equity"] == 0.5  # Liabilities (2M) / Equity (4M)
        assert findings["source"] == "Manual Document Ingestion (CSV)"
        assert "Manual Document Ingestion" in report["markdown"]
    finally:
        # Cleanup
        if os.path.exists(file_path):
            os.remove(file_path)
        if os.path.exists(session_dir):
            os.rmdir(session_dir)

def test_mcp_sec_edgar_tools():
    # Test CIK search resolution
    res_search = mcp_search_company("AAPL")
    assert res_search["cik"] == "0000320193"
    assert "Apple" in res_search["name"]

    # Test financials fetch
    res_fin = mcp_get_financials("0000320193")
    assert res_fin["cik"] == "0000320193"
    assert res_fin["latest_debt_to_equity"] == 1.45
    assert res_fin["latest_revenue"] == 385700000000.0

    # Test filings fetch
    res_filings = mcp_get_filings("0000320193")
    assert len(res_filings) > 0
    assert any(f["form"] in ["10-K", "10-Q", "8-K"] for f in res_filings)

def test_ingest_financial_endpoint():
    client = TestClient(app)

    # 1. Test invalid file format
    response = client.post(
        "/api/ingest/financial",
        files={"file": ("test.txt", io.BytesIO(b"dummy text"), "text/plain")},
        data={"session_id": "test-session-001"}
    )
    assert response.status_code == 400
    assert "Only CSV file uploads are supported" in response.json()["detail"]

    # 2. Test structurally invalid CSV (missing required columns)
    invalid_csv = "Period,Revenue,CostOfGoodsSold\n2025-Q1,100,50"
    response = client.post(
        "/api/ingest/financial",
        files={"file": ("invalid_columns.csv", io.BytesIO(invalid_csv.encode("utf-8")), "text/csv")},
        data={"session_id": "test-session-002"}
    )
    assert response.status_code == 400
    assert "Structural check failed" in response.json()["detail"]

    # 3. Test valid CSV upload
    valid_csv = """Period,Revenue,CostOfGoodsSold,OperatingExpenses,CashInflow,CashOutflow,TotalAssets,TotalLiabilities,TotalEquity
2025-Q1,1000,300,500,1000,1200,5000,2000,2000"""
    
    os.makedirs(os.path.join("data_room", "uploads", "financial", "test-session-003"), exist_ok=True)
    
    response = client.post(
        "/api/ingest/financial",
        files={"file": ("valid_financials.csv", io.BytesIO(valid_csv.encode("utf-8")), "text/csv")},
        data={"session_id": "test-session-003"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["record_count"] == 1
    
    # Cleanup files created
    file_path = os.path.join("data_room", "uploads", "financial", "test-session-003", "valid_financials.csv")
    if os.path.exists(file_path):
        os.remove(file_path)
    if os.path.exists(os.path.dirname(file_path)):
        os.rmdir(os.path.dirname(file_path))
