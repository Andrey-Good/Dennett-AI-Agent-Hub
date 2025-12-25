import sys
import os
import logging
import asyncio
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

try:
    from apps.ai_core.ai_core.config.settings import config
    from apps.ai_core.ai_core.api import hub, downloads, local_models, storage, health
    from apps.ai_core.ai_core.db.session import DatabaseConfig, initialize_database, get_database_manager
    from apps.ai_core.ai_core.db.init_db import get_database_url
    from apps.ai_core.ai_core.api.agents_api import router as agents_router
    from apps.ai_core.ai_core.api.triggers_api import router as triggers_router, agent_triggers_router
    from apps.ai_core.ai_core.logic.priority_policy import init_priority_policy, get_priority_policy
    from apps.ai_core.ai_core.logic.trigger_manager import init_trigger_manager, get_trigger_manager
    from apps.ai_core.ai_core.logic.filesystem_manager import file_system_manager
    from apps.ai_core.ai_core.workers.garbage_collector import init_garbage_collector
    from apps.ai_core.ai_core.db.migrator import run_incremental_migrations
except ModuleNotFoundError:
    from ai_core.config.settings import config
    from ai_core.api import hub, downloads, local_models, storage, health
    from ai_core.db.session import DatabaseConfig, initialize_database, get_database_manager
    from ai_core.db.init_db import get_database_url
    from ai_core.api.agents_api import router as agents_router
    from ai_core.api.triggers_api import router as triggers_router, agent_triggers_router
    from ai_core.logic.priority_policy import init_priority_policy, get_priority_policy
    from ai_core.logic.trigger_manager import init_trigger_manager, get_trigger_manager
    from ai_core.logic.filesystem_manager import file_system_manager
    from ai_core.workers.garbage_collector import init_garbage_collector
    from ai_core.db.migrator import run_incremental_migrations

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

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

    try:
        from apps.ai_core.ai_core.api.dependencies import get_hf_service
    except ModuleNotFoundError:
        from ai_core.api.dependencies import get_hf_service
    service = await get_hf_service()

    try:
        logger.info("Initializing database...")
        db_url = get_database_url()
        db_config = DatabaseConfig(
            database_url=db_url,
            echo=False,
            pool_size=10,
            max_overflow=20
        )
        initialize_database(db_config)
        logger.info(f"Database initialized successfully at: {db_url}")

        # Run incremental migrations for v5.0 schema updates
        logger.info("Running incremental migrations...")
        run_incremental_migrations(get_database_manager().get_engine())
        logger.info("Incremental migrations completed")

        logger.info("Reading asset storage path from database settings...")
        try:
            from apps.ai_core.ai_core.logic.settings_service import SettingsService
            from apps.ai_core.ai_core.db.session import get_database_manager
        except ModuleNotFoundError:
            from ai_core.logic.settings_service import SettingsService
            from ai_core.db.session import get_database_manager

        db_manager = get_database_manager()
        session = db_manager.create_session()

        try:
            settings_service = SettingsService(session)

            # Get asset path from settings, or use default
            asset_path = settings_service.get_setting("HEAVY_ASSET_PATH")

            if asset_path is None:
                # Use default path in user's home directory
                default_asset_path = Path.home() / "DennettLibrary"
                asset_path = str(default_asset_path)
                logger.info(f"No asset path in settings, using default: {asset_path}")

                # Save default to database for future use
                settings_service.update_setting("HEAVY_ASSET_PATH", asset_path)
            else:
                logger.info(f"Asset path from settings: {asset_path}")

            # Initialize Phase 2 of FileSystemManager
            file_system_manager.set_asset_root_path(asset_path)
            logger.info(f"FileSystemManager Phase 2 initialized. AssetData root: {asset_path}")

        finally:
            session.close()

    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise

    aging_task = None
    try:
        logger.info("Initializing PriorityPolicy...")

        settings_dict = {
            "PRIORITY_CORRIDORS": {},
            "AGING_INTERVAL_SEC": 60,
            "AGING_THRESHOLD_SEC": 300,
            "AGING_BOOST": 10,
            "AGING_CAP_COMMUNITY": 65
        }

        priority_policy = init_priority_policy(settings_dict)
        logger.info("PriorityPolicy initialized successfully")

        # Start AgingWorker
        logger.info("Starting AgingWorker...")
        db_manager = get_database_manager()
        session = db_manager.create_session()

        aging_task = asyncio.create_task(
            priority_policy.run_aging_worker(session)
        )
        logger.info("AgingWorker started")

    except Exception as e:
        logger.error(f"PriorityPolicy initialization failed: {e}")
        raise

    # Start AgentGarbageCollector
    gc_task = None
    try:
        logger.info("Starting AgentGarbageCollector...")
        garbage_collector = init_garbage_collector(interval_seconds=300)
        db_manager = get_database_manager()
        agents_dir = str(file_system_manager.get_agents_dir())

        gc_task = asyncio.create_task(
            garbage_collector.run(db_manager.create_session, agents_dir)
        )
        logger.info("AgentGarbageCollector started")

    except Exception as e:
        logger.error(f"AgentGarbageCollector initialization failed: {e}")
        # Non-fatal - continue without GC

    # Start TriggerManager
    trigger_manager = None
    try:
        logger.info("Starting TriggerManager...")
        db_manager = get_database_manager()
        trigger_manager = init_trigger_manager(
            session_factory=db_manager.create_session,
            reconcile_interval_sec=10,
            max_crash_retries=3
        )
        await trigger_manager.start()
        logger.info("TriggerManager started")

    except Exception as e:
        logger.error(f"TriggerManager initialization failed: {e}")
        # Non-fatal - continue without TriggerManager

    yield

    # Shutdown
    logger.info("Shutting down application...")

    # Stop TriggerManager first (graceful shutdown)
    if trigger_manager is not None:
        try:
            await trigger_manager.stop()
            logger.info("TriggerManager stopped")
        except Exception as e:
            logger.error(f"Error stopping TriggerManager: {e}")

    if aging_task is not None:
        aging_task.cancel()
        try:
            await aging_task
        except asyncio.CancelledError:
            logger.info("AgingWorker stopped")
        except Exception as e:
            logger.error(f"Error stopping AgingWorker: {e}")

    if gc_task is not None:
        gc_task.cancel()
        try:
            await gc_task
        except asyncio.CancelledError:
            logger.info("AgentGarbageCollector stopped")
        except Exception as e:
            logger.error(f"Error stopping AgentGarbageCollector: {e}")

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
app.include_router(triggers_router, prefix="/api", tags=["triggers"])
app.include_router(agent_triggers_router, prefix="/api", tags=["triggers"])

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=config.api_host, port=config.api_port)
