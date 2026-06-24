"""
backend/app/routers/auth.py
Minimal authentication endpoints.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/api/auth", tags=["Auth"])

@router.get("/status")
def auth_status():
    return {"status": "authenticated"}
