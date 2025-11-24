"""Main FastAPI application"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.ai_core.ai_core.config.settings import config
from apps.ai_core.ai_core.api import hub, downloads, local_models, storage, health


# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


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

# Include routers
app.include_router(hub.router)
app.include_router(downloads.router)
app.include_router(local_models.router)
app.include_router(storage.router)
app.include_router(health.router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=config.api_host, port=config.api_port)
