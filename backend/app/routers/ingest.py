from fastapi import APIRouter, File, UploadFile, HTTPException
from swarm.tools.local_pdf_parser import index_document
import os
import shutil

router = APIRouter(prefix="/api/ingest", tags=["Ingestion"])

@router.post("/legal")
async def ingest_legal_document(file: UploadFile = File(...)):
    """
    Ingests a legal PDF document, saves it locally, and indexes it into the local FAISS vector store.
    """
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
    
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
