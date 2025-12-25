"""Service dependencies and authentication"""
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import AsyncGenerator, Optional

try:
    from apps.ai_core.ai_core.config.settings import config
    from apps.ai_core.ai_core.db.models import ErrorResponse
    from apps.ai_core.ai_core.logic.huggingface_service import HuggingFaceService
    from apps.ai_core.ai_core.logic.download_manager import DownloadManager
    from apps.ai_core.ai_core.logic.local_storage import LocalStorage
except ModuleNotFoundError:
    from ai_core.config.settings import config
    from ai_core.db.models import ErrorResponse
    from ai_core.logic.huggingface_service import HuggingFaceService
    from ai_core.logic.download_manager import DownloadManager
    from ai_core.logic.local_storage import LocalStorage
from contextlib import asynccontextmanager

security = HTTPBearer()
_hf_service: Optional[HuggingFaceService] = None


async def get_hf_service() -> HuggingFaceService:
    """Get HuggingFace service instance"""
    global _hf_service
    if _hf_service is None:
        _hf_service = HuggingFaceService()
        await _hf_service.__aenter__()
    return _hf_service


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
