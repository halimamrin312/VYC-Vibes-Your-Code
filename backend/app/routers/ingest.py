"""
backend/app/routers/ingest.py
FastAPI Router for handling secure document ingestion.
"""

import os
import shutil
import pandas as pd
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
import logging

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

    # Create target directory for session
    target_dir = os.path.join("data_room", "uploads", "financial", session_id)
    os.makedirs(target_dir, exist_ok=True)
    
    file_path = os.path.join(target_dir, file.filename)
    
    # Save file contents locally
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        logger.error(f"Failed to write file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to write file to disk: {str(e)}")

    # Structural Validation check (Ensure it contains required columns)
    try:
        df = pd.read_csv(file_path)
        required_cols = [
            'Period', 'Revenue', 'CostOfGoodsSold', 'OperatingExpenses', 
            'CashInflow', 'CashOutflow', 'TotalAssets', 'TotalLiabilities', 
            'TotalEquity'
        ]
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            # Clean up the invalid file
            os.remove(file_path)
            raise HTTPException(
                status_code=400, 
                detail=f"Structural check failed: Missing required columns: {missing_cols}"
            )
    except HTTPException:
        raise
    except Exception as e:
        # Clean up in case of malformed CSV parse failure
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=400, detail=f"Malformed or unreadable CSV file: {str(e)}")

    logger.info(f"Successfully ingested and validated financials for session {session_id}: {file.filename}")
    
    return {
        "status": "success",
        "filename": file.filename,
        "session_id": session_id,
        "columns": list(df.columns),
        "record_count": len(df)
    }
