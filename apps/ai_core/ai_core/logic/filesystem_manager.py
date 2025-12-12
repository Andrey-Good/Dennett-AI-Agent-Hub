"""
FileSystemManager - Centralized Path Management Module

This module provides a singleton service for managing all file system paths
in the AI Core application. It implements a two-phase initialization pattern
to resolve dependencies between database and asset storage paths.

Phase 1: Core Startup (UserData/"Brains")
- Immediately available after instantiation
- Provides paths to lightweight data: DB, logs, agents, plugins

Phase 2: Post-Database Initialization (AssetData/"Muscles")
- Activated after calling set_asset_root_path()
- Provides paths to heavy assets: models, vector stores
"""

from pathlib import Path
from platformdirs import user_data_dir
import logging

logger = logging.getLogger(__name__)


class FileSystemManager:
    """
    Singleton manager for all file system paths.

    Ensures consistent path management across the application and prevents
    hardcoded paths in individual services.
    """

    # --- Singleton Implementation ---
    _instance = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        """
        Singleton pattern implementation.
        Ensures only one instance exists throughout the application lifecycle.
        """
        if not cls._instance:
            cls._instance = super(FileSystemManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """
        Phase 1 Initialization: UserData ("Brains")

        Sets up lightweight data directories and makes database path available.
        This method can be called multiple times safely due to _initialized flag.
        """
        # Prevent re-initialization
        if FileSystemManager._initialized:
            return

        FileSystemManager._initialized = True

        # --- Phase 1: UserData Root ("Brains") ---
        # Use platformdirs to find OS-specific application data directory
        self.user_data_root: Path = Path(user_data_dir(appname="Dennett", appauthor="DennettAI"))

        # Define all UserData paths
        self.db_path: Path = self.user_data_root / "storage.db"
        self.log_path: Path = self.user_data_root / "ai_core.log"
        self.agents_dir: Path = self.user_data_root / "agents"
        self.custom_nodes_dir: Path = self.user_data_root / "custom_nodes"
        self.custom_triggers_dir: Path = self.user_data_root / "custom_triggers"

        # Create UserData directory structure
        try:
            self.user_data_root.mkdir(parents=True, exist_ok=True)
            self.agents_dir.mkdir(exist_ok=True)
            self.custom_nodes_dir.mkdir(exist_ok=True)
            self.custom_triggers_dir.mkdir(exist_ok=True)
            logger.info(f"UserData directories initialized at: {self.user_data_root}")
        except PermissionError as e:
            logger.error(f"Permission denied creating UserData directories: {e}")
            raise RuntimeError(f"Cannot create UserData directories at {self.user_data_root}: {e}")
        except Exception as e:
            logger.error(f"Failed to create UserData directories: {e}")
            raise

        # --- Phase 2: AssetData Placeholders ("Muscles") ---
        # These will be initialized when set_asset_root_path() is called
        self.asset_data_root: Path | None = None
        self.models_dir: Path | None = None
        self.vector_stores_dir: Path | None = None
        self.cache_dir: Path | None = None

        logger.info("FileSystemManager Phase 1 initialization complete")

    # ========================================================================
    # PHASE 1 METHODS (Always Available)
    # ========================================================================

    def get_db_path(self) -> Path:
        """Returns the absolute path to the SQLite database file."""
        return self.db_path

    def get_log_path(self) -> Path:
        """Returns the absolute path to the application log file."""
        return self.log_path

    def get_agents_dir(self) -> Path:
        """Returns the directory path where agent JSON graphs are stored."""
        return self.agents_dir

    def get_agent_json_path(self, agent_id: str) -> Path:
        """Returns the full path to a specific agent's JSON file."""
        return self.agents_dir / f"{agent_id}.json"

    def get_custom_nodes_dir(self) -> Path:
        """Returns the directory path for custom node plugins."""
        return self.custom_nodes_dir

    def get_custom_triggers_dir(self) -> Path:
        """Returns the directory path for custom trigger plugins."""
        return self.custom_triggers_dir

    def get_user_data_root(self) -> Path:
        """Returns the root UserData directory path."""
        return self.user_data_root

    # ========================================================================
    # PHASE 2 INITIALIZATION (Called Once After Database Startup)
    # ========================================================================

    def set_asset_root_path(self, asset_path: str | Path) -> None:
        """
        Phase 2 Initialization: Configure AssetData ("Muscles") location.

        This method should be called exactly once during application startup,
        after the database is initialized and settings are loaded.
        """
        self.asset_data_root = Path(asset_path)

        # Define AssetData subdirectories
        self.models_dir = self.asset_data_root / "models"
        self.vector_stores_dir = self.asset_data_root / "vector_stores"
        self.cache_dir = self.asset_data_root / "cache"

        # Create AssetData directory structure
        try:
            self.asset_data_root.mkdir(parents=True, exist_ok=True)
            self.models_dir.mkdir(exist_ok=True)
            self.vector_stores_dir.mkdir(exist_ok=True)
            self.cache_dir.mkdir(exist_ok=True)
            logger.info(f"AssetData directories initialized at: {self.asset_data_root}")
        except PermissionError as e:
            logger.error(f"Permission denied creating AssetData directories: {e}")
            raise RuntimeError(f"Cannot create AssetData directories at {self.asset_data_root}: {e}")
        except Exception as e:
            logger.error(f"Failed to create AssetData directories: {e}")
            raise

        logger.info("FileSystemManager Phase 2 initialization complete")

    # ========================================================================
    # PHASE 2 METHODS (Require set_asset_root_path() to be called first)
    # ========================================================================

    def _check_asset_root_initialized(self) -> None:
        """Internal guard method to ensure Phase 2 initialization has occurred."""
        if self.asset_data_root is None:
            raise RuntimeError(
                "FileSystemManager: Attempting to access AssetData ('Muscles') "
                "before Phase 2 initialization. Call set_asset_root_path() first!"
            )

    def get_models_dir(self) -> Path:
        """Returns the directory path where GGUF models are stored."""
        self._check_asset_root_initialized()
        return self.models_dir

    def get_model_path(self, model_filename: str) -> Path:
        """Returns the full path to a specific model file."""
        self._check_asset_root_initialized()
        return self.models_dir / model_filename

    def get_vector_stores_dir(self) -> Path:
        """Returns the directory path where vector stores are stored."""
        self._check_asset_root_initialized()
        return self.vector_stores_dir

    def get_vector_store_path(self, store_name: str) -> Path:
        """Returns the full path to a specific vector store directory."""
        self._check_asset_root_initialized()
        return self.vector_stores_dir / store_name

    def get_cache_dir(self) -> Path:
        """Returns the directory path for temporary cache files."""
        self._check_asset_root_initialized()
        return self.cache_dir

    def get_asset_data_root(self) -> Path:
        """Returns the root AssetData directory path."""
        self._check_asset_root_initialized()
        return self.asset_data_root

    def is_asset_root_initialized(self) -> bool:
        """Check if Phase 2 initialization has been completed."""
        return self.asset_data_root is not None


# All other modules should import this instance!!!!!!!!!, not the class
file_system_manager = FileSystemManager()
