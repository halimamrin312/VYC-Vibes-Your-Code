"""
backend/app/main.py
Main entrypoint for the FastAPI M&A Swarm backend application.
Configures CORS, registers router endpoints, and initializes middleware.
"""

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from backend.app.routers import chat, hitl, memo, auth, ingest
from backend.app.database.models import init_db

# Initialize database
init_db()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("backend.app.main")

app = FastAPI(
    title="M&A Due Diligence Swarm Backend",
    description="FastAPI gateway coordinating sub-agents and orchestrator for M&A target auditing.",
    version="1.0.0"
)

# Configure CORS for frontend Vite development server and production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this to specific domains in production settings
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(chat.router)
app.include_router(hitl.router)
app.include_router(memo.router)
app.include_router(auth.router)
app.include_router(ingest.router)

@app.get("/")
def read_root():
    return {"status": "running", "service": "M&A Due Diligence Swarm API"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
