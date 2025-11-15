import asyncio
import uuid
from typing import List, Optional
from datetime import datetime
import logging
import json

from fastapi import FastAPI, HTTPException, Query, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Internal imports
import sys
from pathlib import Path

# Add project root to sys.path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Service imports
from ai_core.core.config.settings import config
from ai_core.core.models import (
    ModelInfoShort,
    ModelInfoDetailed,
    GGUFProvider,
    DownloadRequest,
    DownloadResponse,
    ImportRequest,
    LocalModel,
    SearchFilters,
    ErrorResponse,
    SortType,
)

from ai_core.core.services.huggingface_service import HuggingFaceService
from ai_core.core.services.download_manager import DownloadManager
from ai_core.core.services.local_storage import LocalStorage

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Service Dependencies
def get_hf_service():
    return HuggingFaceService()


def get_download_manager():
    return DownloadManager()


def get_local_storage():
    return LocalStorage()


# Create FastAPI app
app = FastAPI(
    title="Model Manager API",
    description="AI model lifecycle management for Dennet platform",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()


# Authentication dependency
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


# Utility functions
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


# === HUB ENDPOINTS ===


@app.get("/hub/search", response_model=List[ModelInfoShort])
async def search_models(
    query: str = Query(..., description="Search query"),
    limit: int = Query(20, ge=1, le=100, description="Number of results"),
    offset: int = Query(0, ge=0, description="Results offset"),
    sort: SortType = Query(SortType.LIKES, description="Sort order"),
    filters_json: Optional[str] = Query(None, description="URL-encoded JSON filters"),
    # token: str = Depends(verify_token),#
    hf_service: HuggingFaceService = Depends(get_hf_service),
):
    """Search for models on Hugging Face Hub

    Supports filtering by task type, license, and other criteria.
    Returns paginated results sorted by specified criteria.
    """
    try:
        # Parse filters if provided
        filters = None
        if filters_json:
            try:
                filter_data = json.loads(filters_json)
                filters = SearchFilters(**filter_data)
            except (json.JSONDecodeError, ValueError) as e:
                raise HTTPException(
                    status_code=400,
                    detail=ErrorResponse(
                        error_code="INVALID_FILTERS",
                        message=f"Invalid filters JSON: {str(e)}",
                        details=None,
                    ).dict(),
                )

        results = await hf_service.search_models(
            query=query, limit=limit, offset=offset, sort=sort, filters=filters
        )

        logger.info(f"Search completed: query='{query}', results={len(results)}")
        return results

    except HTTPException:
        raise
    except Exception as e:
        handle_service_error(e, "search_models")


@app.get("/hub/model/{author}/{model_name}", response_model=ModelInfoDetailed)
async def get_model_details(
    author: str,
    model_name: str,
    # token: str = Depends(verify_token),#
    hf_service: HuggingFaceService = Depends(get_hf_service),
):
    """Get detailed information about a specific model

    Returns comprehensive model metadata including README content,
    license information, and repository statistics.
    """
    try:
        model_details = await hf_service.get_model_details(author, model_name)

        logger.info(f"Retrieved model details: {author}/{model_name}")
        return model_details

    except Exception as e:
        handle_service_error(e, "get_model_details")


@app.get(
    "/hub/model/{author}/{model_name}/gguf-providers", response_model=List[GGUFProvider]
)
async def find_gguf_providers(
    author: str,
    model_name: str,
    # token: str = Depends(verify_token),#
    hf_service: HuggingFaceService = Depends(get_hf_service),
):
    """Find and rank GGUF format providers for a model

    Returns ranked list of providers with the recommended option marked.
    Prioritizes trusted providers like TheBloke and official conversions.
    """
    try:
        providers = await hf_service.find_gguf_providers(author, model_name)

        logger.info(f"Found {len(providers)} GGUF providers for {author}/{model_name}")
        return providers

    except Exception as e:
        handle_service_error(e, "find_gguf_providers")


# === LOCAL DOWNLOAD ENDPOINTS ===


@app.post("/local/download", response_model=DownloadResponse, status_code=202)
async def start_download(
    request: DownloadRequest,
    background_tasks: BackgroundTasks,
    # token: str = Depends(verify_token),#
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


@app.get("/local/download/status")
async def get_download_status_stream(
    # token: str = Depends(verify_token),#
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


@app.delete("/local/download/{download_id}")
async def cancel_download(
    download_id: str,
    # token: str = Depends(verify_token),#
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


# === LOCAL MODEL MANAGEMENT ENDPOINTS ===


@app.post("/local/import", response_model=LocalModel, status_code=201)
async def import_model(
    request: ImportRequest,
    # token: str = Depends(verify_token),#
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


@app.get("/local/models", response_model=List[LocalModel])
async def list_local_models(
    # token: str = Depends(verify_token),#
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


@app.get("/local/models/{model_id}", response_model=LocalModel)
async def get_local_model(
    model_id: str,
    # token: str = Depends(verify_token),#
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

        # Update last accessed time
        await local_storage.update_model_access(model_id)

        return model

    except HTTPException:
        raise
    except Exception as e:
        handle_service_error(e, "get_local_model")


@app.delete("/local/models/{model_id}", status_code=204)
async def delete_local_model(
    model_id: str,
    force: bool = Query(
        False, description="Force deletion even if file appears in use"
    ),
    # token: str = Depends(verify_token),#
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


# === UTILITY ENDPOINTS ===


@app.get("/local/storage/stats")
async def get_storage_stats(
    # token: str = Depends(verify_token),#
    local_storage: LocalStorage = Depends(get_local_storage),
):
    """Get storage usage statistics"""
    try:
        stats = await local_storage.get_storage_stats()
        return stats
    except Exception as e:
        handle_service_error(e, "get_storage_stats")


@app.post("/local/storage/cleanup")
async def cleanup_storage(
    # token: str = Depends(verify_token),#
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


# === HEALTH CHECK ===


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=config.api_host, port=config.api_port)
