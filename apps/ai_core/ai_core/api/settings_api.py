# apps/ai_core/ai_core/api/settings_api.py
"""
Settings API endpoints for admin configuration management.

Provides REST API endpoints for:
- Getting all settings
- Getting a specific setting
- Updating settings
- Deleting settings
"""

import logging
from typing import Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

try:
    from apps.ai_core.ai_core.db.session import get_session
    from apps.ai_core.ai_core.logic.settings_service import SettingsService, create_settings_service
except ModuleNotFoundError:
    from ai_core.db.session import get_session
    from ai_core.logic.settings_service import SettingsService, create_settings_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/settings", tags=["settings"])


# Pydantic models for request/response

class SettingResponse(BaseModel):
    """Response model for a single setting."""
    key: str
    value: str


class SettingsResponse(BaseModel):
    """Response model for all settings."""
    settings: Dict[str, str]
    count: int


class UpdateSettingRequest(BaseModel):
    """Request model for updating a single setting."""
    value: str = Field(..., description="New value for the setting")


class UpdateSettingsRequest(BaseModel):
    """Request model for updating multiple settings."""
    settings: Dict[str, str] = Field(..., description="Dictionary of key-value pairs to update")


class SettingUpdateResponse(BaseModel):
    """Response model for setting update operations."""
    success: bool
    message: str
    key: Optional[str] = None


# Dependency to get SettingsService
def get_settings_service(session: Session = Depends(get_session)) -> SettingsService:
    """Dependency to create SettingsService instance."""
    return create_settings_service(session)


# API Endpoints

@router.get("/", response_model=SettingsResponse)
def get_all_settings(service: SettingsService = Depends(get_settings_service)):
    """
    Get all application settings.
    
    Returns all settings as a dictionary with the total count.
    
    Returns:
        SettingsResponse: All settings and count
    """
    try:
        settings = service.get_all_settings_as_dict()
        return SettingsResponse(
            settings=settings,
            count=len(settings)
        )
    except Exception as e:
        logger.error(f"Failed to get all settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve settings: {str(e)}"
        )


@router.get("/{key}", response_model=SettingResponse)
def get_setting(key: str, service: SettingsService = Depends(get_settings_service)):
    """
    Get a specific setting by key.
    
    Args:
        key: Setting key to retrieve
    
    Returns:
        SettingResponse: The setting key and value
    
    Raises:
        HTTPException: If setting not found
    """
    try:
        value = service.get_setting(key)
        if value is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Setting '{key}' not found"
            )
        return SettingResponse(key=key, value=value)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get setting '{key}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve setting: {str(e)}"
        )


@router.post("/{key}", response_model=SettingUpdateResponse)
def update_setting(
    key: str,
    request: UpdateSettingRequest,
    service: SettingsService = Depends(get_settings_service)
):
    """
    Update a single setting.
    
    This endpoint is called when the user clicks 'Save' in the UI.
    
    Args:
        key: Setting key to update
        request: Request body containing the new value
    
    Returns:
        SettingUpdateResponse: Success status and message
    """
    try:
        service.update_setting(key, request.value)
        return SettingUpdateResponse(
            success=True,
            message=f"Setting '{key}' updated successfully",
            key=key
        )
    except Exception as e:
        logger.error(f"Failed to update setting '{key}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update setting: {str(e)}"
        )


@router.put("/", response_model=SettingUpdateResponse)
def update_multiple_settings(
    request: UpdateSettingsRequest,
    service: SettingsService = Depends(get_settings_service)
):
    """
    Update multiple settings at once.
    
    Args:
        request: Request body containing dictionary of settings to update
    
    Returns:
        SettingUpdateResponse: Success status and message
    """
    try:
        service.update_settings(request.settings)
        return SettingUpdateResponse(
            success=True,
            message=f"{len(request.settings)} settings updated successfully"
        )
    except Exception as e:
        logger.error(f"Failed to update settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update settings: {str(e)}"
        )


@router.delete("/{key}", response_model=SettingUpdateResponse)
def delete_setting(
    key: str,
    service: SettingsService = Depends(get_settings_service)
):
    """
    Delete a setting by key.
    
    Args:
        key: Setting key to delete
    
    Returns:
        SettingUpdateResponse: Success status and message
    
    Raises:
        HTTPException: If setting not found
    """
    try:
        deleted = service.delete_setting(key)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Setting '{key}' not found"
            )
        return SettingUpdateResponse(
            success=True,
            message=f"Setting '{key}' deleted successfully",
            key=key
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete setting '{key}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete setting: {str(e)}"
        )


@router.get("/health/check")
def health_check(service: SettingsService = Depends(get_settings_service)):
    """
    Health check endpoint for settings service.
    
    Returns:
        dict: Health status and settings count
    """
    try:
        count = service.get_all_settings_count()
        return {
            "status": "healthy",
            "settings_count": count,
            "message": "Settings service is operational"
        }
    except Exception as e:
        logger.error(f"Settings service health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Settings service unhealthy: {str(e)}"
        )
