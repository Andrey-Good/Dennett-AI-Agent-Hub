"""Local model management endpoints"""
import logging
from typing import List

from fastapi import APIRouter, Query, Depends, HTTPException

try:
    from apps.ai_core.ai_core.db.models import LocalModel, ErrorResponse
    from apps.ai_core.ai_core.logic.local_storage import LocalStorage
    from apps.ai_core.ai_core.api.dependencies import get_local_storage
    from apps.ai_core.ai_core.api.errors import handle_service_error
except ModuleNotFoundError:
    from ai_core.db.models import LocalModel, ErrorResponse
    from ai_core.logic.local_storage import LocalStorage
    from ai_core.api.dependencies import get_local_storage
    from ai_core.api.errors import handle_service_error


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/local/models", tags=["Local Models"])


@router.get("", response_model=List[LocalModel])
async def list_local_models(
    # token: str = Depends(verify_token),
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


@router.get("/{model_id}", response_model=LocalModel)
async def get_local_model(
    model_id: str,
    # token: str = Depends(verify_token),
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


@router.delete("/{model_id}", status_code=204)
async def delete_local_model(
    model_id: str,
    force: bool = Query(
        False, description="Force deletion even if file appears in use"
    ),
    # token: str = Depends(verify_token),
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
