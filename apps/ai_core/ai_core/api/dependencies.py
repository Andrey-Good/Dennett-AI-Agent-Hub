"""Service dependencies and authentication"""
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from apps.ai_core.ai_core.config.settings import config
from apps.ai_core.ai_core.db.models import ErrorResponse
from apps.ai_core.ai_core.logic.huggingface_service import HuggingFaceService
from apps.ai_core.ai_core.logic.download_manager import DownloadManager
from apps.ai_core.ai_core.logic.local_storage import LocalStorage


security = HTTPBearer()


def get_hf_service():
    """Get HuggingFace service instance"""
    return HuggingFaceService()


def get_download_manager():
    """Get download manager instance"""
    return DownloadManager()


def get_local_storage():
    """Get local storage instance"""
    return LocalStorage()


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
