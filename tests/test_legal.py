# tests/test_legal.py
import os
import pytest
from unittest.mock import MagicMock, patch
from swarm.tools.local_pdf_parser import chunk_document_text
from swarm.agents.legal_compliance import LegalCompliance
from swarm.tools.legal_api_clients import query_courtlistener, query_govinfo
from swarm.tools.gemini_clause_analyzer import analyze_clauses_with_gemini

def test_document_chunk_boundaries():
    text = "one two three four five six"
    # Chunk size: 3 words, overlap: 1 word
    chunks = chunk_document_text(text, chunk_size_words=3, overlap_words=1)
    
    assert len(chunks) == 3
    assert chunks[0] == "one two three"
    assert chunks[1] == "three four five"
    assert chunks[2] == "five six"

@pytest.fixture(autouse=True)
def cleanup_test_files():
    yield
    # Clean up test vector files if any were written
    for path in ["data_room/vector_store/test_faiss_index.index", "data_room/vector_store/test_metadata.pkl"]:
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass

@patch('swarm.agents.legal_compliance.query_courtlistener')
@patch('swarm.agents.legal_compliance.query_govinfo')
@patch('swarm.agents.legal_compliance.query_local_vector_store')
@patch('swarm.agents.legal_compliance.os.path.exists')
def test_legal_agent_compliance_audit(mock_exists, mock_query, mock_govinfo, mock_courtlistener):
    # Mock database file checks to return True only for vector index
    def exists_side_effect(path):
        if "faiss_index.index" in str(path):
            return True
        return False
    mock_exists.side_effect = exists_side_effect
    
    # Mock query_local_vector_store outputs for 10 category scans
    mock_query.side_effect = [
        # LQ-01
        [{"source": "agreement.pdf", "page": 14, "text": "This change of control successor entity agreement contains a flip-in poison pill to deter hostile bids."}],
        # LQ-02
        [],
        # LQ-03
        [],
        # LQ-04
        [],
        # LQ-05
        [{"source": "agreement.pdf", "page": 2, "text": "The golden parachute clause allows executive severance payout of $5M."}],
        # LQ-06
        [],
        # LQ-07
        [],
        # LQ-08
        [],
        # LQ-09
        [],
        # LQ-10
        [],
    ]
    
    # Mock CourtListener and GovInfo to return empty lists for this test
    mock_courtlistener.return_value = []
    mock_govinfo.return_value = []
    
    agent = LegalCompliance()
    context = {"target_company": "Acme Corp Buyout"}
    
    result = agent.execute(context)
    
    assert "findings" in result
    findings = result["findings"]
    assert findings["status"] == "success"
    
    # Assert flags raised
    flags = findings["flags"]
    assert len(flags) == 2  # One Poison Pill (Critical) and one Severance (Critical)
    
    # Verify critical severity (both are escalated or have base severity 1)
    critical_flags = [f for f in flags if f["severity"] == 1]
    assert len(critical_flags) == 2
    
    # Verify categories
    categories = [f["category"] for f in flags]
    assert "Poison Pill / Deal Blocker" in categories
    assert "HR Liability / Golden Parachute" in categories
    
    # Verify HITL triggers
    assert findings["hitl_required"] is True
    assert "Poison Pill / Deal Blocker" in findings["hitl_reasons"][0]
    
    # Verify search query sanitization (should remove transaction word 'Buyout' from 'Acme Corp Buyout')
    assert findings["courtlistener_audit"]["search_query"] == "Acme Corp"


def test_courtlistener_simulator():
    records = query_courtlistener("Acme Corp", api_token=None)
    assert len(records) > 0
    assert records[0]["id"] == "DK-9028"
    assert "Patent Holding Corp" in records[0]["caseName"]
    assert records[0]["court"] == "Delaware Court of Chancery"
    
    empty_records = query_courtlistener("Unknown LLC", api_token=None)
    assert len(empty_records) == 0


def test_govinfo_simulator():
    records = query_govinfo("Acme Corp", api_key=None)
    assert len(records) > 0
    assert "EPA Notice of Violation" in records[0]["title"]
    assert records[0]["collection"] == "FR (Federal Register)"
    
    empty_records = query_govinfo("Unknown LLC", api_key=None)
    assert len(empty_records) == 0


@patch('google.genai.Client')
def test_gemini_clause_analyzer_api(mock_genai_client):
    # Setup mock Gemini response
    mock_instance = MagicMock()
    mock_genai_client.return_value = mock_instance
    
    mock_response = MagicMock()
    mock_response.text = '{"flags": [{"lq_id": "LQ-01", "severity": 1, "severity_label": "🔴 CRITICAL", "category": "Poison Pill / Deal Blocker", "document": "agreement.pdf", "page": 10, "quote": "poison pill", "description": "critical poison pill", "estimated_exposure": "$1.5M", "recommended_action": "Seek counsel"}]}'
    mock_instance.models.generate_content.return_value = mock_response
    
    chunks = [{"source": "agreement.pdf", "page": 10, "text": "dilutive poison pill here"}]
    findings = analyze_clauses_with_gemini("Acme Corp", chunks, "fake_api_key")
    
    assert findings is not None
    assert len(findings["flags"]) == 1
    assert findings["flags"][0]["lq_id"] == "LQ-01"
    assert findings["flags"][0]["category"] == "Poison Pill / Deal Blocker"

import zipfile
import io
from fastapi.testclient import TestClient
from backend.app.main import app

def _create_dummy_docx(text: str) -> bytes:
    # A DOCX file is a zip containing word/document.xml
    xml_content = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
        <w:body>
            <w:p>
                <w:r>
                    <w:t>{text}</w:t>
                </w:r>
            </w:p>
        </w:body>
    </w:document>
    """
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as zip_file:
        zip_file.writestr('word/document.xml', xml_content)
    return buffer.getvalue()

def test_extract_text_from_docx(tmp_path):
    from swarm.tools.local_pdf_parser import extract_text_from_docx
    
    dummy_text = "This is a contract containing poison pill clause."
    docx_bytes = _create_dummy_docx(dummy_text)
    
    file_path = tmp_path / "test_contract.docx"
    with open(file_path, "wb") as f:
        f.write(docx_bytes)
        
    extracted_text = extract_text_from_docx(str(file_path))
    assert dummy_text in extracted_text

def test_ingest_legal_endpoint():
    client = TestClient(app)
    
    # 1. Test invalid file format
    response = client.post(
        "/api/ingest/legal",
        files={"file": ("test.txt", io.BytesIO(b"dummy text"), "text/plain")}
    )
    assert response.status_code == 400
    assert "Only PDF and DOCX files are supported." in response.json()["detail"]

    # 2. Test valid DOCX upload and indexing
    dummy_text = "This is a legal document with buyout penalty."
    docx_bytes = _create_dummy_docx(dummy_text)
    
    uploaded_file_path = "data_room/uploads/legal/test_legal.docx"
    
    with patch("backend.app.routers.ingest.index_document") as mock_index:
        mock_index.return_value = True
        try:
            response = client.post(
                "/api/ingest/legal",
                files={"file": ("test_legal.docx", io.BytesIO(docx_bytes), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
            )
            
            assert response.status_code == 200
            assert "Successfully ingested and indexed test_legal.docx" in response.json()["message"]
            mock_index.assert_called_once()
        finally:
            if os.path.exists(uploaded_file_path):
                os.remove(uploaded_file_path)
