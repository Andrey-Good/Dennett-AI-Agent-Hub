"""Download management endpoints"""
import asyncio
import json
import logging
import uuid

from fastapi import APIRouter, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse

from apps.ai_core.ai_core.db.models import DownloadRequest, DownloadResponse
from apps.ai_core.ai_core.logic.download_manager import DownloadManager
from apps.ai_core.ai_core.api.dependencies import get_download_manager  # verify_token
from apps.ai_core.ai_core.api.errors import handle_service_error


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/local/download", tags=["Downloads"])


@router.post("", response_model=DownloadResponse, status_code=202)
async def start_download(
    request: DownloadRequest,
    background_tasks: BackgroundTasks,
    # token: str = Depends(verify_token),
    download_manager: DownloadManager = Depends(get_download_manager),
):
    """Initiate download of a model file

    Starts asynchronous download with progress tracking.
    Returns download ID for status monitoring.
    """
    try:
        download_id = await download_manager.start_download(
            repo_id=request.repo_id,
            filename=request.filename,
            background_tasks=background_tasks,
        )

        logger.info(
            f"Download initiated: {download_id} for {request.repo_id}/{request.filename}"
        )

        return DownloadResponse(
            download_id=download_id,
            message=f"Download started for {request.repo_id}/{request.filename}",
        )

    except Exception as e:
        handle_service_error(e, "start_download")


@router.get("/status")
async def get_download_status_stream(
    # token: str = Depends(verify_token),
    download_manager: DownloadManager = Depends(get_download_manager),
):
    """Get real-time download status updates via Server-Sent Events

    Returns SSE stream with JSON-encoded DownloadStatus updates.
    Automatically includes status of all active downloads.
    """
    try:
        subscriber_id = str(uuid.uuid4())

        async def event_stream():
            try:
                async for update in download_manager.subscribe_to_updates(
                    subscriber_id
                ):
                    yield update
                    await asyncio.sleep(0.1)  # Small delay to prevent overwhelming
            except Exception as e:
                logger.error(f"SSE stream error: {e}")
                yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )

    except Exception as e:
        handle_service_error(e, "get_download_status_stream")


@router.delete("/{download_id}")
async def cancel_download(
    download_id: str,
    # token: str = Depends(verify_token),
    download_manager: DownloadManager = Depends(get_download_manager),
):
    """Cancel an active download

    Stops download in progress and updates status accordingly.
    """
    try:
        from fastapi import HTTPException
        from apps.ai_core.ai_core.db.models import ErrorResponse

        success = await download_manager.cancel_download(download_id)
        if not success:
            raise HTTPException(
                status_code=404,
                detail=ErrorResponse(
                    error_code="DOWNLOAD_NOT_FOUND",
                    message=f"Download not found: {download_id}",
                    details=None,
                ).dict(),
            )

        logger.info(f"Download cancelled: {download_id}")
        return {"message": "Download cancelled successfully"}

    except HTTPException:
        raise
    except Exception as e:
        handle_service_error(e, "cancel_download")
