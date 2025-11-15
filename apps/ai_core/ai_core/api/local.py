import asyncio
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
import json

from fastapi import APIRouter, HTTPException, Query, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse
from apps.ai_core.ai_core.models import (
    DownloadRequest,
    DownloadResponse,
    ImportRequest,
    LocalModel,
    ErrorResponse,
)
from apps.ai_core.ai_core.logic.download_manager import DownloadManager
from apps.ai_core.ai_core.logic.local_storage import LocalStorage
from apps.ai_core.ai_core.dependencies import get_download_manager, get_local_storage, handle_service_error

logger = logging.getLogger(__name__)

local_router = APIRouter()

@local_router.post("/local/download", response_model=DownloadResponse, status_code=202)
async def start_download(
    request: DownloadRequest,
    background_tasks: BackgroundTasks,
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


@local_router.get("/local/download/status")
async def get_download_status_stream(
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


@local_router.delete("/local/download/{download_id}")
async def cancel_download(
    download_id: str,
    download_manager: DownloadManager = Depends(get_download_manager),
):
    """Cancel an active download

    Stops download in progress and updates status accordingly.
    """
    try:
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


@local_router.post("/local/import", response_model=LocalModel, status_code=201)
async def import_model(
    request: ImportRequest,
    local_storage: LocalStorage = Depends(get_local_storage),
):
    """Import a local GGUF file into Dennet library

    Validates file format, calculates hash for duplicate detection,
    and adds to local model registry.
    """
    try:
        model = await local_storage.import_model(
            file_path=request.file_path, action=request.action
        )

        logger.info(f"Model imported: {model.model_id} from {request.file_path}")
        return model

    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error_code="FILE_NOT_FOUND",
                message=f"Source file not found: {request.file_path}",
                details=None,
            ).dict(),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse(
                error_code="INVALID_FILE", message=str(e), details=None
            ).dict(),
        )
    except Exception as e:
        handle_service_error(e, "import_model")


@local_router.get("/local/models", response_model=List[LocalModel])
async def list_local_models(
    local_storage: LocalStorage = Depends(get_local_storage),
):
    """Get list of all locally stored models

    Returns comprehensive information about each model including
    file size, import date, and metadata.
    """
    try:
        models = await local_storage.list_models()
        logger.info(f"Listed {len(models)} local models")
        return models

    except Exception as e:
        handle_service_error(e, "list_local_models")


@local_router.get("/local/models/{model_id}", response_model=LocalModel)
async def get_local_model(
    model_id: str,
    local_storage: LocalStorage = Depends(get_local_storage),
):
    """Get details of a specific local model"""
    try:
        model = await local_storage.get_model(model_id)
        if not model:
            raise HTTPException(
                status_code=404,
                detail=ErrorResponse(
                    error_code="MODEL_NOT_FOUND",
                    message=f"Local model not found: {model_id}",
                    details=None,
                ).dict(),
            )

        await local_storage.update_model_access(model_id)

        return model

    except HTTPException:
        raise
    except Exception as e:
        handle_service_error(e, "get_local_model")


@local_router.delete("/local/models/{model_id}", status_code=204)
async def delete_local_model(
    model_id: str,
    force: bool = Query(
        False, description="Force deletion even if file appears in use"
    ),
    local_storage: LocalStorage = Depends(get_local_storage),
):
    """Delete a local model

    Removes model file and metadata. Use force=true to override
    usage checks (use with caution).
    """
    try:
        await local_storage.delete_model(model_id, force=force)
        logger.info(f"Model deleted: {model_id}")

    except ValueError:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error_code="MODEL_NOT_FOUND",
                message=f"Local model not found: {model_id}",
                details=None,
            ).dict(),
        )
    except OSError as e:
        raise HTTPException(
            status_code=409,
            detail=ErrorResponse(
                error_code="FILE_IN_USE",
                message=f"Cannot delete file (in use): {str(e)}",
                details=None,
            ).dict(),
        )
    except Exception as e:
        handle_service_error(e, "delete_local_model")


@local_router.get("/local/storage/stats")
async def get_storage_stats(
    local_storage: LocalStorage = Depends(get_local_storage),
):
    """Get storage usage statistics"""
    try:
        stats = await local_storage.get_storage_stats()
        return stats
    except Exception as e:
        handle_service_error(e, "get_storage_stats")


@local_router.post("/local/storage/cleanup")
async def cleanup_storage(
    local_storage: LocalStorage = Depends(get_local_storage),
    download_manager: DownloadManager = Depends(get_download_manager),
):
    """Clean up orphaned files and old download records"""
    try:
        removed_files = await local_storage.cleanup_orphaned_files()
        await download_manager.cleanup_completed(older_than_hours=24)

        return {
            "message": "Storage cleanup completed",
            "removed_files": removed_files,
            "removed_count": len(removed_files),
        }
    except Exception as e:
        handle_service_error(e, "cleanup_storage")
