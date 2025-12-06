"""Error handling utilities"""
import logging
from fastapi import HTTPException

from apps.ai_core.ai_core.db.models import ErrorResponse


logger = logging.getLogger(__name__)


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
