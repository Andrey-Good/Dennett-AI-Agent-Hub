from typing import List, Optional
import json
import logging

from fastapi import APIRouter, HTTPException, Query, Depends, BackgroundTasks
from apps.ai_core.ai_core.models import (
    ModelInfoShort,
    ModelInfoDetailed,
    GGUFProvider,
    SearchFilters,
    ErrorResponse,
    SortType,
)
from apps.ai_core.ai_core.logic.huggingface_service import HuggingFaceService
from apps.ai_core.ai_core.dependencies import get_hf_service, handle_service_error

logger = logging.getLogger(__name__)

hub_router = APIRouter()

@hub_router.get("/hub/search", response_model=List[ModelInfoShort])
async def search_models(
    query: str = Query(..., description="Search query"),
    limit: int = Query(20, ge=1, le=100, description="Number of results"),
    offset: int = Query(0, ge=0, description="Results offset"),
    sort: SortType = Query(SortType.LIKES, description="Sort order"),
    filters_json: Optional[str] = Query(None, description="URL-encoded JSON filters"),
    hf_service: HuggingFaceService = Depends(get_hf_service),
):
    """Search for models on Hugging Face Hub

    Supports filtering by task type, license, and other criteria.
    Returns paginated results sorted by specified criteria.
    """
    try:
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


@hub_router.get("/hub/model/{author}/{model_name}", response_model=ModelInfoDetailed)
async def get_model_details(
    author: str,
    model_name: str,
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


@hub_router.get(
    "/hub/model/{author}/{model_name}/gguf-providers", response_model=List[GGUFProvider]
)
async def find_gguf_providers(
    author: str,
    model_name: str,
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
