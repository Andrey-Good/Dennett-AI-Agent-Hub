"""Health check endpoint"""
from datetime import datetime
from fastapi import APIRouter


router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
    }
