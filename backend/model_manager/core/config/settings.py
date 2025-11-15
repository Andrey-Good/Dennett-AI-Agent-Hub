# model_manager/core/config/settings.py
from pathlib import Path
from typing import Optional, List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from platformdirs import user_data_dir, user_log_dir

# Константы приложения
APP_NAME = "Dennett"
APP_AUTHOR = "DennetTeam"

# Пути к данным пользователя (AppData)
APP_DATA_DIR = Path(user_data_dir(APP_NAME, APP_AUTHOR))
LOGS_DIR = Path(user_log_dir(APP_NAME, APP_AUTHOR))


class ModelManagerConfig(BaseSettings):
    """Model Manager configuration settings"""

    # API Settings
    api_token: str = Field(
        default="your-secure-api-token", alias="MODEL_MANAGER_API_TOKEN"
    )
    api_host: str = Field(
        default="127.0.0.1",  # Changed from 0.0.0.0 for security. Bind to 0.0.0.0 only if explicitly needed and secured.
        alias="API_HOST",
    )
    api_port: int = Field(default=8000, alias="API_PORT")

    # Storage Settings - теперь в AppData
    models_dir: str = Field(default=str(APP_DATA_DIR / "models"), alias="MODELS_DIR")
    downloads_dir: str = Field(
        default=str(APP_DATA_DIR / "downloads"), alias="DOWNLOADS_DIR"
    )
    metadata_file: str = Field(
        default=str(APP_DATA_DIR / "models.json"), alias="METADATA_FILE"
    )
    agents_dir: str = Field(default=str(APP_DATA_DIR / "agents"), alias="AGENTS_DIR")

    # Download Settings
    max_concurrent_downloads: int = Field(default=3, alias="MAX_CONCURRENT_DOWNLOADS")
    download_chunk_size: int = Field(default=8192, alias="DOWNLOAD_CHUNK_SIZE")
    download_timeout_seconds: int = Field(default=300, alias="DOWNLOAD_TIMEOUT")

    # Hugging Face Settings
    hf_token: Optional[str] = Field(default=None, alias="HUGGINGFACE_TOKEN")
    hf_cache_dir: Optional[str] = Field(default=None, alias="HF_CACHE_DIR")

    # Trusted GGUF Providers
    trusted_gguf_providers: List[str] = Field(
        default=[
            "TheBloke",
            "bartowski",
            "microsoft",
            "NousResearch",
            "QuantFactory",
            "MaziyarPanahi",
            "Qwen",
        ],
        alias="TRUSTED_GGUF_PROVIDERS",
    )

    # Logging Settings
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_format: str = Field(default="json", alias="LOG_FORMAT")
    log_dir: str = Field(default=str(LOGS_DIR), alias="LOG_DIR")

    # Performance Settings
    enable_file_hashing: bool = Field(default=True, alias="ENABLE_FILE_HASHING")
    cleanup_interval_hours: int = Field(default=24, alias="CLEANUP_INTERVAL_HOURS")
    max_search_results: int = Field(default=100, alias="MAX_SEARCH_RESULTS")

    # Security Settings
    enable_cors: bool = Field(default=True, alias="ENABLE_CORS")
    cors_origins: List[str] = Field(
        default=["http://localhost:1420", "tauri://localhost", "*"],
        alias="CORS_ORIGINS",
    )

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)


# Global config instance
config = ModelManagerConfig()
settings = config  # Алиас для совместимости с main.py


def validate_directories():
    """Create and validate required directories"""
    directories = [
        config.models_dir,
        config.downloads_dir,
        config.agents_dir,
        config.log_dir,
    ]

    print(f"[CONFIG] App Data Directory: {APP_DATA_DIR}")
    print(f"[CONFIG] Logs Directory: {LOGS_DIR}")

    for dir_path in directories:
        Path(dir_path).mkdir(exist_ok=True, parents=True)
        print(f"✅ Directory ready: {dir_path}")


def get_config() -> ModelManagerConfig:
    """Get configuration instance"""
    return config


def get_model_path(model_name: str) -> Path:
    """Получить путь к конкретной модели"""
    return Path(config.models_dir) / model_name


def get_agent_path(agent_name: str) -> Path:
    """Получить путь к конкретному агенту"""
    return Path(config.agents_dir) / f"{agent_name}.json"


if __name__ == "__main__":
    print("Model Manager Configuration:")
    print(f"Models directory: {config.models_dir}")
    print(f"Downloads directory: {config.downloads_dir}")
    print(f"Agents directory: {config.agents_dir}")
    print(f"Logs directory: {config.log_dir}")
    print(f"Max concurrent downloads: {config.max_concurrent_downloads}")
    print(f"Trusted GGUF providers: {', '.join(config.trusted_gguf_providers)}")
    validate_directories()
