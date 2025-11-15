from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime


# Enums for type safety
class TaskType(str, Enum):
    TEXT_GENERATION = "text-generation"
    TEXT_CLASSIFICATION = "text-classification"
    QUESTION_ANSWERING = "question-answering"
    SUMMARIZATION = "summarization"
    TRANSLATION = "translation"


class LicenseType(str, Enum):
    APACHE_2_0 = "apache-2.0"
    MIT = "mit"
    GPL_3_0 = "gpl-3.0"
    BSD = "bsd"
    OTHER = "other"


class SortType(str, Enum):
    LIKES = "likes"
    DOWNLOADS = "downloads"
    TIME = "time"
    UPDATE = "update"


class DownloadState(str, Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ImportAction(str, Enum):
    COPY = "copy"
    MOVE = "move"


# Base model information (short version for search results)
class ModelInfoShort(BaseModel):
    """Short model information for search results"""

    repo_id: str = Field(..., description="Repository ID in format author/model-name")
    model_name: str = Field(..., description="Display name of the model")
    author: str = Field(..., description="Model author/organization")
    task: Optional[TaskType] = Field(None, description="Primary task type")
    license: Optional[LicenseType] = Field(None, description="Model license")
    downloads: int = Field(0, description="Total download count")
    likes: int = Field(0, description="Number of likes/stars")
    last_modified: Optional[datetime] = Field(
        None, description="Last modification timestamp"
    )
    tags: List[str] = Field(default_factory=list, description="Model tags")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat() if v else None}


# Detailed model information
class ModelInfoDetailed(BaseModel):
    """Detailed model information with full metadata"""

    repo_id: str = Field(..., description="Repository ID")
    model_name: str = Field(..., description="Display name")
    author: str = Field(..., description="Author/organization")
    task: Optional[TaskType] = Field(None, description="Primary task type")
    license: Optional[LicenseType] = Field(None, description="License type")
    downloads: int = Field(0, description="Download count")
    likes: int = Field(0, description="Likes count")
    last_modified: Optional[datetime] = Field(None, description="Last modified")
    tags: List[str] = Field(default_factory=list, description="Tags")

    # Detailed fields
    description: Optional[str] = Field(None, description="Model description")
    readme_content: Optional[str] = Field(None, description="README content")
    model_card: Optional[Dict[str, Any]] = Field(
        None, description="Model card metadata"
    )
    file_count: int = Field(0, description="Number of files in repository")
    total_size_bytes: Optional[int] = Field(None, description="Total repository size")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat() if v else None}


# GGUF Provider information
class GGUFProvider(BaseModel):
    """Information about GGUF format provider for a model"""

    repo_id: str = Field(..., description="GGUF provider repository ID")
    provider_name: str = Field(..., description="Provider name (e.g., TheBloke)")
    model_variants: List[str] = Field(..., description="Available GGUF variants")
    is_recommended: bool = Field(
        False, description="Whether this provider is recommended"
    )
    total_downloads: int = Field(0, description="Total downloads from this provider")
    last_updated: Optional[datetime] = Field(None, description="Last update timestamp")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat() if v else None}


# Download request models
class DownloadRequest(BaseModel):
    """Request to start model download"""

    repo_id: str = Field(..., description="Repository ID to download from")
    filename: str = Field(..., description="Specific file to download")


class DownloadResponse(BaseModel):
    """Response with download ID"""

    download_id: str = Field(..., description="Unique download identifier")
    message: str = Field("Download initiated", description="Status message")


# Download status for SSE
class DownloadStatus(BaseModel):
    """Real-time download status information"""

    download_id: str = Field(..., description="Download identifier")
    repo_id: str = Field(..., description="Repository being downloaded")
    filename: str = Field(..., description="File being downloaded")
    status: DownloadState = Field(..., description="Current download state")
    progress_percent: float = Field(0.0, description="Download progress percentage")
    bytes_downloaded: int = Field(0, description="Bytes downloaded so far")
    total_bytes: Optional[int] = Field(None, description="Total file size in bytes")
    download_speed_mbps: Optional[float] = Field(
        None, description="Current download speed"
    )
    eta_seconds: Optional[int] = Field(None, description="Estimated time remaining")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    started_at: Optional[datetime] = Field(None, description="Download start time")
    completed_at: Optional[datetime] = Field(
        None, description="Download completion time"
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat() if v else None}


# Local model management
class ImportRequest(BaseModel):
    """Request to import local GGUF file"""

    file_path: str = Field(..., description="Path to local GGUF file")
    action: ImportAction = Field(
        ImportAction.COPY, description="Whether to copy or move file"
    )


class LocalModel(BaseModel):
    """Information about locally stored model"""

    model_id: str = Field(..., description="Unique local model identifier")
    original_repo_id: Optional[str] = Field(
        None, description="Original HF repository ID"
    )
    display_name: str = Field(..., description="Display name for the model")
    file_path: str = Field(..., description="Local file path")
    file_size_bytes: int = Field(..., description="File size in bytes")
    file_hash: Optional[str] = Field(None, description="SHA256 hash of the file")
    imported_at: datetime = Field(..., description="Import timestamp")
    last_accessed: Optional[datetime] = Field(None, description="Last access time")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )
    is_downloaded: bool = Field(
        True, description="Whether file was downloaded by Dennet"
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat() if v else None}


# Search filters
class SearchFilters(BaseModel):
    """Search filters for model discovery"""

    task: Optional[TaskType] = Field(None, description="Filter by task type")
    license: Optional[LicenseType] = Field(None, description="Filter by license")
    min_downloads: Optional[int] = Field(None, description="Minimum download count")
    min_likes: Optional[int] = Field(None, description="Minimum likes count")
    tags: Optional[List[str]] = Field(None, description="Required tags")


# Error response model
class ErrorResponse(BaseModel):
    """Standardized error response"""

    error_code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(
        None, description="Additional error details"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Error timestamp"
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


# Success response wrapper
class SuccessResponse(BaseModel):
    """Generic success response wrapper"""

    message: str = Field(
        "Operation completed successfully", description="Success message"
    )
    data: Optional[Dict[str, Any]] = Field(None, description="Response data")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Response timestamp"
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
