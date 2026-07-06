"""
backend/app/routers/ingest.py
FastAPI Router for handling secure document ingestion.
"""

import os
import shutil
import pandas as pd
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
import logging
from backend.app.utils.sanitizer import sanitize_filename
from backend.app.utils.file_processor import process_csv
from swarm.tools.local_pdf_parser import index_document

logger = logging.getLogger("backend.app.routers.ingest")

router = APIRouter(prefix="/api/ingest", tags=["Ingest"])

@router.get("/status")
def ingest_status():
    return {"status": "ready"}

@router.post("/financial")
async def ingest_financial(
    file: UploadFile = File(...),
    session_id: str = Form(...)
):
    """
    Ingests and validates target financial CSV statements.
    Stores files in a session-specific secure directory.
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV file uploads are supported.")

    # Sanitize the filename to prevent directory traversal
    safe_filename = sanitize_filename(file.filename)

    # Create target directory for session
    target_dir = os.path.join("data_room", "uploads", "financial", session_id)
    os.makedirs(target_dir, exist_ok=True)
    
    file_path = os.path.join(target_dir, safe_filename)
    
    # Save file contents locally
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        logger.error(f"Failed to write file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to write file to disk: {str(e)}")

    # Structural Validation check (Ensure it contains required columns)
    try:
        required_cols = [
            'Period', 'Revenue', 'CostOfGoodsSold', 'OperatingExpenses', 
            'CashInflow', 'CashOutflow', 'TotalAssets', 'TotalLiabilities', 
            'TotalEquity'
        ]
        df = process_csv(file_path, required_columns=required_cols)
    except ValueError as e:
        # Clean up the invalid file
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(
            status_code=400, 
            detail=f"Structural check failed: {str(e)}"
        )
    except Exception as e:
        # Clean up in case of malformed CSV parse failure
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=400, detail=f"Malformed or unreadable CSV file: {str(e)}")

    logger.info(f"Successfully ingested and validated financials for session {session_id}: {safe_filename}")
    
    return {
        "status": "success",
        "filename": safe_filename,
        "session_id": session_id,
        "columns": list(df.columns),
        "record_count": len(df)
    }

@router.post("/logs")
async def ingest_logs(
    file: UploadFile = File(...),
    session_id: str = Form(...),
    industry: str = Form("generic")
):
    """
    Ingests and validates target operations log CSV.
    Stores files in a session-specific secure directory.
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV file uploads are supported.")

    # Sanitize the filename to prevent directory traversal
    safe_filename = sanitize_filename(file.filename)

    # Create target directory for session
    target_dir = os.path.join("data_room", "uploads", "logs", session_id)
    os.makedirs(target_dir, exist_ok=True)
    
    file_path = os.path.join(target_dir, safe_filename)
    
    # Save file contents locally
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        logger.error(f"Failed to write log file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to write file to disk: {str(e)}")

    # Structural Validation check (Ensure it contains required columns: ReviewText, Rating, Category)
    try:
        required_cols = ['ReviewText', 'Rating', 'Category']
        df = process_csv(file_path, required_columns=required_cols)
    except ValueError as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(
            status_code=400, 
            detail=f"Log structural check failed: {str(e)}"
        )
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=400, detail=f"Malformed or unreadable CSV file: {str(e)}")

    logger.info(f"Successfully ingested and validated logs for session {session_id}: {safe_filename}")
    
    return {
        "status": "success",
        "filename": safe_filename,
        "session_id": session_id,
        "columns": list(df.columns),
        "record_count": len(df)
    }

@router.post("/legal")
async def ingest_legal_document(file: UploadFile = File(...)):
    """
    Ingests a legal PDF or DOCX document, saves it locally, and indexes it into the local FAISS vector store.
    """
    if not (file.filename.lower().endswith(".pdf") or file.filename.lower().endswith(".docx")):
        raise HTTPException(status_code=400, detail="Only PDF and DOCX files are supported.")
    
    upload_dir = "data_room/uploads/legal"
    os.makedirs(upload_dir, exist_ok=True)
    
    file_path = os.path.join(upload_dir, file.filename)
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
        
    # Index the document
    success = index_document(file_path)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to index PDF document into local vector store.")
        
    return {
        "status": "success",
        "message": f"Successfully ingested and indexed {file.filename}",
        "file_path": file_path
    }
