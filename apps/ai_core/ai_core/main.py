import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.ai_core.ai_core.config.settings import config
from apps.ai_core.ai_core.api import hub, downloads, local_models, storage, health

from apps.ai_core.ai_core.db.session import DatabaseConfig, initialize_database, get_database_manager
from apps.ai_core.ai_core.db.init_db import get_database_url
from apps.ai_core.ai_core.api.agents_api import router as agents_router

from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Create FastAPI app
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting application...")

    from apps.ai_core.ai_core.api.dependencies import get_hf_service
    service = await get_hf_service()

    try:
        logger.info("Initializing database...")
        db_url = get_database_url()
        db_config = DatabaseConfig(
            database_url=db_url,
            echo=False,  # Set to True for SQL debugging
            pool_size=10,
            max_overflow=20
        )
        initialize_database(db_config)
        logger.info(f"? Database initialized successfully at: {db_url}")
    except Exception as e:
        logger.error(f"? Database initialization failed: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down application...")

    # Close HuggingFace service
    await service.__aexit__(None, None, None)

    # Close database connections
    db_manager = get_database_manager()
    if db_manager:
        db_manager.close()
        logger.info("? Database connections closed")

app = FastAPI(
    title="Model Manager API",
    description="AI model lifecycle management for Dennet platform",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(hub.router)
app.include_router(downloads.router)
app.include_router(local_models.router)
app.include_router(storage.router)
app.include_router(health.router)
app.include_router(agents_router, prefix="/api", tags=["agents"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=config.api_host, port=config.api_port)
