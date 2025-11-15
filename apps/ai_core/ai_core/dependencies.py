import logging
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from ai_core.config.settings import config
from ai_core.models import ErrorResponse
from ai_core.logic.huggingface_service import HuggingFaceService
from ai_core.logic.download_manager import DownloadManager
from ai_core.logic.local_storage import LocalStorage

logger = logging.getLogger(__name__)

security = HTTPBearer()

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify API token"""
    if credentials.credentials != config.api_token:
        raise HTTPException(
            status_code=401,
            detail=ErrorResponse(
                error_code="INVALID_TOKEN", message="Invalid API token", details=None
            ).dict(),
        )
    return credentials.credentials

def handle_service_error(e: Exception, operation: str):
    """Convert service exceptions to HTTP responses"""
    logger.error(f"Service error in {operation}: {e}")

    if "not found" in str(e).lower():
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error_code="NOT_FOUND",
                message=f"Resource not found: {str(e)}",
                details=None,
            ).dict(),
        )
    elif "unavailable" in str(e).lower() or "timeout" in str(e).lower():
        raise HTTPException(
            status_code=502,
            detail=ErrorResponse(
                error_code="SERVICE_UNAVAILABLE",
                message="External service temporarily unavailable",
                details=None,
            ).dict(),
        )
    else:
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error_code="INTERNAL_ERROR",
                message=f"Internal service error: {str(e)}",
                details=None,
            ).dict(),
        )

def get_hf_service():
    return HuggingFaceService()

def get_download_manager():
    return DownloadManager()

def get_local_storage():
    return LocalStorage()
