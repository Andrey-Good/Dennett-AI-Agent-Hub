"""Storage and local operations endpoints"""
import logging

from fastapi import APIRouter, Depends, HTTPException

try:
    from apps.ai_core.ai_core.db.models import ImportRequest, LocalModel, ErrorResponse
    from apps.ai_core.ai_core.logic.local_storage import LocalStorage
    from apps.ai_core.ai_core.logic.download_manager import DownloadManager
    from apps.ai_core.ai_core.api.dependencies import get_local_storage, get_download_manager
    from apps.ai_core.ai_core.api.errors import handle_service_error
except ModuleNotFoundError:
    from ai_core.db.models import ImportRequest, LocalModel, ErrorResponse
    from ai_core.logic.local_storage import LocalStorage
    from ai_core.logic.download_manager import DownloadManager
    from ai_core.api.dependencies import get_local_storage, get_download_manager
    from ai_core.api.errors import handle_service_error


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/local", tags=["Storage"])


@router.post("/import", response_model=LocalModel, status_code=201)
async def import_model(
    request: ImportRequest,
    # token: str = Depends(verify_token),
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
            ).model_dump(mode='json'),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse(
                error_code="INVALID_FILE", message=str(e), details=None
            ).model_dump(mode='json'),
        )
    except Exception as e:
        handle_service_error(e, "import_model")


@router.get("/storage/stats")
async def get_storage_stats(
    # token: str = Depends(verify_token),
    local_storage: LocalStorage = Depends(get_local_storage),
):
    """Get storage usage statistics"""
    try:
        stats = await local_storage.get_storage_stats()
        return stats
    except Exception as e:
        handle_service_error(e, "get_storage_stats")


@router.post("/storage/cleanup")
async def cleanup_storage(
    # token: str = Depends(verify_token),
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
