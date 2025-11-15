import shutil
import hashlib
import json
import uuid
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
import asyncio
import aiofiles
from ai_core.models import LocalModel, ImportAction

logger = logging.getLogger(__name__)


class LocalStorage:
    """Service for managing local model storage"""

    def __init__(
        self, storage_dir: Optional[str] = None, metadata_file: Optional[str] = None
    ):
        """Initialize local storage service

        Args:
            storage_dir: Directory to store model files
            metadata_file: File to store model metadata
        """
        from ai_core.config.settings import config

        # Use config values if not provided
        if storage_dir is None:
            storage_dir = config.models_dir
        if metadata_file is None:
            metadata_file = config.metadata_file

        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True, parents=True)

        self.metadata_file = self.storage_dir / metadata_file
        self._models_cache: Dict[str, LocalModel] = {}
        self._lock = asyncio.Lock()

        # Load existing metadata
        asyncio.create_task(self._load_metadata())

    async def list_models(self) -> List[LocalModel]:
        """Get list of all locally stored models

        Returns:
            List of LocalModel objects
        """
        async with self._lock:
            return list(self._models_cache.values())

    async def get_model(self, model_id: str) -> Optional[LocalModel]:
        """Get specific model by ID

        Args:
            model_id: Local model identifier

        Returns:
            LocalModel or None if not found
        """
        async with self._lock:
            return self._models_cache.get(model_id)

    async def import_model(
        self,
        file_path: str,
        action: ImportAction = ImportAction.COPY,
        display_name: Optional[str] = None,
        repo_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> LocalModel:
        """Import a GGUF file into local storage

        Args:
            file_path: Path to source GGUF file
            action: Whether to copy or move the file
            display_name: Custom display name
            repo_id: Original HuggingFace repo ID
            metadata: Additional metadata

        Returns:
            LocalModel object

        Raises:
            FileNotFoundError: If source file doesn't exist
            ValueError: If file is not a valid GGUF file
            OSError: If file operations fail
        """
        source_path = Path(file_path)

        # Validate source file
        if not source_path.exists():
            raise FileNotFoundError(f"Source file not found: {file_path}")

        if not source_path.suffix.lower() == ".gguf":
            raise ValueError(f"File must have .gguf extension: {file_path}")

        # Generate unique model ID
        model_id = str(uuid.uuid4())

        # Create target filename
        safe_filename = self._sanitize_filename(source_path.name)
        target_path = self.storage_dir / f"{model_id}_{safe_filename}"

        async with self._lock:
            try:
                # Calculate file hash before moving/copying
                file_hash = await self._calculate_file_hash(source_path)
                file_size = source_path.stat().st_size

                # Check for duplicates based on hash
                existing_model = self._find_model_by_hash(file_hash)
                if existing_model:
                    logger.warning(
                        f"Model with same hash already exists: {existing_model.model_id}"
                    )
                    return existing_model

                # Copy or move file
                if action == ImportAction.COPY:
                    shutil.copy2(source_path, target_path)
                    logger.info(f"Copied {source_path} to {target_path}")
                else:  # MOVE
                    shutil.move(str(source_path), str(target_path))
                    logger.info(f"Moved {source_path} to {target_path}")

                # Create model record
                model = LocalModel(
                    model_id=model_id,
                    original_repo_id=repo_id,
                    display_name=display_name or source_path.stem,
                    file_path=str(target_path),
                    file_size_bytes=file_size,
                    file_hash=file_hash,
                    imported_at=datetime.utcnow(),
                    last_accessed=None,
                    metadata=metadata or {},
                    is_downloaded=False,  # This was imported, not downloaded
                )

                # Add to cache and save
                self._models_cache[model_id] = model
                await self._save_metadata()

                logger.info(f"Successfully imported model {model_id}")
                return model

            except Exception as e:
                # Clean up target file if it was created
                if target_path.exists():
                    try:
                        target_path.unlink()
                    except OSError as cleanup_e:
                        logger.error(
                            f"Failed to clean up target file {target_path}: {cleanup_e}"
                        )
                raise e

    async def add_downloaded_model(
        self,
        download_id: str,
        repo_id: str,
        filename: str,
        file_path: str,
        file_hash: Optional[str] = None,
    ) -> LocalModel:
        """Add a downloaded model to local storage

        Args:
            download_id: Original download ID
            repo_id: HuggingFace repository ID
            filename: Original filename
            file_path: Local file path
            file_hash: File hash if available

        Returns:
            LocalModel object
        """
        path = Path(file_path)
        model_id = str(uuid.uuid4())

        async with self._lock:
            # Calculate hash if not provided
            if not file_hash:
                file_hash = await self._calculate_file_hash(path)

            # Check for duplicates
            existing_model = self._find_model_by_hash(file_hash)
            if existing_model:
                logger.warning(
                    f"Downloaded model is duplicate of {existing_model.model_id}"
                )
                return existing_model

            model = LocalModel(
                model_id=model_id,
                original_repo_id=repo_id,
                display_name=self._extract_display_name(repo_id, filename),
                file_path=file_path,
                file_size_bytes=path.stat().st_size,
                file_hash=file_hash,
                imported_at=datetime.utcnow(),
                last_accessed=None,
                metadata={"download_id": download_id, "original_filename": filename},
                is_downloaded=True,
            )

            self._models_cache[model_id] = model
            await self._save_metadata()

            logger.info(f"Added downloaded model {model_id} from {repo_id}")
            return model

    async def delete_model(self, model_id: str, force: bool = False) -> bool:
        """Delete a model from local storage

        Args:
            model_id: Model to delete
            force: Force deletion even if file is in use

        Returns:
            True if deleted successfully

        Raises:
            ValueError: If model not found
            OSError: If file is in use and force=False
        """
        async with self._lock:
            if model_id not in self._models_cache:
                raise ValueError(f"Model not found: {model_id}")

            model = self._models_cache[model_id]
            file_path = Path(model.file_path)

            try:
                # Check if file is in use (basic check)
                if not force and self._is_file_in_use(file_path):
                    raise OSError(f"File appears to be in use: {file_path}")

                # Delete file
                if file_path.exists():
                    file_path.unlink()
                    logger.info(f"Deleted file: {file_path}")

                # Remove from cache
                del self._models_cache[model_id]
                await self._save_metadata()

                logger.info(f"Successfully deleted model {model_id}")
                return True

            except Exception as e:
                logger.error(f"Failed to delete model {model_id}: {e}")
                raise

    async def update_model_access(self, model_id: str):
        """Update last access time for a model

        Args:
            model_id: Model ID to update
        """
        async with self._lock:
            if model_id in self._models_cache:
                self._models_cache[model_id].last_accessed = datetime.utcnow()
                await self._save_metadata()

    async def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics

        Returns:
            Dictionary with storage information
        """
        async with self._lock:
            total_models = len(self._models_cache)
            total_size = sum(
                model.file_size_bytes for model in self._models_cache.values()
            )

            # Get disk usage
            disk_usage = shutil.disk_usage(self.storage_dir)

            return {
                "total_models": total_models,
                "total_size_bytes": total_size,
                "total_size_gb": round(total_size / (1024**3), 2),
                "disk_free_bytes": disk_usage.free,
                "disk_free_gb": round(disk_usage.free / (1024**3), 2),
                "disk_total_gb": round(disk_usage.total / (1024**3), 2),
                "storage_directory": str(self.storage_dir),
            }

    async def cleanup_orphaned_files(self) -> List[str]:
        """Clean up files in storage directory not tracked in metadata

        Returns:
            List of removed file paths
        """
        async with self._lock:
            tracked_files = {
                Path(model.file_path) for model in self._models_cache.values()
            }
            removed_files = []

            # Find orphaned GGUF files
            for file_path in self.storage_dir.glob("*.gguf"):
                if file_path not in tracked_files:
                    try:
                        file_path.unlink()
                        removed_files.append(str(file_path))
                        logger.info(f"Removed orphaned file: {file_path}")
                    except Exception as e:
                        logger.error(f"Failed to remove orphaned file {file_path}: {e}")

            return removed_files

    async def _load_metadata(self):
        """Load model metadata from disk"""
        if not self.metadata_file.exists():
            logger.info("No existing metadata file found")
            return

        try:
            async with aiofiles.open(self.metadata_file, "r") as f:
                content = await f.read()
                data = json.loads(content)

            for model_data in data.get("models", []):
                try:
                    model = LocalModel(**model_data)
                    # Verify file still exists
                    if Path(model.file_path).exists():
                        self._models_cache[model.model_id] = model
                    else:
                        logger.warning(
                            f"Model file not found, skipping: {model.file_path}"
                        )
                except Exception as e:
                    logger.error(f"Failed to load model metadata: {e}")

            logger.info(f"Loaded {len(self._models_cache)} models from metadata")

        except Exception as e:
            logger.error(f"Failed to load metadata: {e}")

    async def _save_metadata(self):
        """Save model metadata to disk"""
        try:
            data = {
                "models": [model.dict() for model in self._models_cache.values()],
                "updated_at": datetime.utcnow().isoformat(),
            }

            async with aiofiles.open(self.metadata_file, "w") as f:
                await f.write(json.dumps(data, indent=2, default=str))

        except Exception as e:
            logger.error(f"Failed to save metadata: {e}")

    async def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of a file"""
        hash_sha256 = hashlib.sha256()

        async with aiofiles.open(file_path, "rb") as f:
            while chunk := await f.read(8192):
                hash_sha256.update(chunk)

        return hash_sha256.hexdigest()

    def _find_model_by_hash(self, file_hash: str) -> Optional[LocalModel]:
        """Find model with matching hash"""
        for model in self._models_cache.values():
            if model.file_hash == file_hash:
                return model
        return None

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for safe storage"""
        # Remove or replace unsafe characters
        unsafe_chars = '<>:"/\|?*'
        for char in unsafe_chars:
            filename = filename.replace(char, "_")
        return filename

    def _extract_display_name(self, repo_id: str, filename: str) -> str:
        """Extract a reasonable display name from repo_id and filename"""
        # Use filename without extension, or repo name if filename is generic
        name_from_file = Path(filename).stem
        name_from_repo = repo_id.split("/")[-1]

        if name_from_file and name_from_file.lower() not in ["model", "pytorch_model"]:
            return name_from_file
        return name_from_repo

    def _is_file_in_use(self, file_path: Path) -> bool:
        """Basic check if file is in use (Windows/Unix compatible)"""
        try:
            # Try to open file exclusively
            with open(file_path, "r+b"):
                pass
            return False
        except (OSError, IOError):
            return True
