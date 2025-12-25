# apps/ai_core/ai_core/logic/trigger_manager.py
"""
Trigger Manager for AI Core.

This module implements the TriggerManager which:
- Maintains trigger instances matching desired state in SQLite
- Runs a supervisor/reconcile loop to sync desired and actual state
- Handles trigger lifecycle: start, stop, restart
- Processes emit() calls from triggers to create agent executions
- Implements CrashLoopBackOff before marking triggers as FAILED
"""

import asyncio
import hashlib
import json
import logging
import traceback
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    List,
    Optional,
    Protocol,
    Set,
    runtime_checkable,
)

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


# =============================================================================
# Import Helpers (support both app and test contexts)
# =============================================================================

def _get_repositories():
    """Import repositories module, handling both app and test contexts."""
    try:
        from apps.ai_core.ai_core.db import repositories
        return repositories
    except ModuleNotFoundError:
        from ai_core.db import repositories
        return repositories


# =============================================================================
# Enums
# =============================================================================

class TriggerStatus(str, Enum):
    """Trigger instance status values."""
    ENABLED = 'ENABLED'
    DISABLED = 'DISABLED'
    FAILED = 'FAILED'


# =============================================================================
# Pydantic Models (Request/Response DTOs)
# =============================================================================

class TriggerConfig(BaseModel):
    """Configuration for a single trigger."""
    trigger_id: str = Field(..., description="Type of trigger (e.g., 'cron', 'webhook')")
    status: TriggerStatus = Field(TriggerStatus.ENABLED, description="Desired status")
    config: Dict[str, Any] = Field(default_factory=dict, description="Trigger configuration")


class TriggerInstanceResponse(BaseModel):
    """Response model for trigger instance data."""
    trigger_instance_id: str = Field(..., description="Unique instance ID")
    agent_id: str = Field(..., description="Parent agent ID")
    trigger_id: str = Field(..., description="Type of trigger")
    status: TriggerStatus = Field(..., description="Current status")
    config: Dict[str, Any] = Field(..., description="Trigger configuration")
    config_hash: str = Field(..., description="Config hash for change detection")
    error_message: Optional[str] = Field(None, description="Error details if FAILED")
    error_at: Optional[datetime] = Field(None, description="Error timestamp")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True


class SetAgentTriggersRequest(BaseModel):
    """Request model for set_agent_triggers API."""
    triggers: List[TriggerConfig] = Field(..., description="List of triggers to set")


class SetAgentTriggersResponse(BaseModel):
    """Response model for set_agent_triggers API."""
    agent_id: str
    triggers: List[TriggerInstanceResponse]
    created: int = Field(0, description="Number of triggers created")
    updated: int = Field(0, description="Number of triggers updated")
    deleted: int = Field(0, description="Number of triggers deleted")


class DeleteAgentTriggersResponse(BaseModel):
    """Response model for delete_agent_triggers API."""
    agent_id: str
    deleted: int = Field(..., description="Number of triggers deleted")


class SetAgentTriggersEnabledResponse(BaseModel):
    """Response model for set_agent_triggers_enabled API."""
    agent_id: str
    enabled: bool
    affected: int = Field(..., description="Number of triggers affected")


# =============================================================================
# TriggerSpec Protocol (Plugin Interface)
# =============================================================================

@runtime_checkable
class TriggerSpec(Protocol):
    """
    Protocol for trigger type specifications.

    Each trigger type (cron, webhook, email, etc.) must provide a spec
    that defines its configuration and event schemas.
    """

    @property
    def trigger_id(self) -> str:
        """Unique identifier for this trigger type."""
        ...

    @property
    def config_schema(self) -> Optional[Dict[str, Any]]:
        """JSON Schema for validating trigger configuration."""
        ...

    @property
    def event_schema(self) -> Optional[Dict[str, Any]]:
        """JSON Schema for validating event payloads (optional but recommended)."""
        ...


@runtime_checkable
class TriggerRuntime(Protocol):
    """
    Protocol for trigger runtime instances.

    The TriggerManager creates instances of this to run triggers.
    """

    async def start(
        self,
        config: Dict[str, Any],
        emit: Callable[[Dict[str, Any]], Awaitable[None]],
        cancel_event: asyncio.Event
    ) -> None:
        """
        Start the trigger runtime.

        Args:
            config: Trigger configuration
            emit: Callback to emit events (creates executions)
            cancel_event: Event to signal cancellation
        """
        ...


class TriggerPlugin(ABC):
    """
    Abstract base class for trigger plugins.

    Plugins should inherit from this class and implement
    the required methods.
    """

    @abstractmethod
    def spec(self) -> TriggerSpec:
        """Return the trigger specification."""
        ...

    @abstractmethod
    def create_runtime(self) -> TriggerRuntime:
        """Create a new runtime instance of this trigger."""
        ...


# =============================================================================
# Runtime Handle (In-Memory State)
# =============================================================================

@dataclass
class RuntimeHandle:
    """
    Represents an active trigger instance in memory.

    Attributes:
        trigger_instance_id: Unique ID of the trigger instance
        agent_id: Parent agent ID
        trigger_id: Type of trigger
        task: The async task running the trigger
        cancel_event: Event to signal cancellation
        config_hash: Hash of the config this instance was started with
        stopping: True if intentionally stopping (draining mode)
        started_at: When the instance was started
        crash_count: Number of consecutive crashes
        last_crash_at: Timestamp of last crash
    """
    trigger_instance_id: str
    agent_id: str
    trigger_id: str
    task: asyncio.Task
    cancel_event: asyncio.Event
    config_hash: str
    stopping: bool = False
    started_at: datetime = field(default_factory=datetime.utcnow)
    crash_count: int = 0
    last_crash_at: Optional[datetime] = None


# =============================================================================
# Trigger Registry
# =============================================================================

class TriggerRegistry:
    """
    Registry for trigger plugins.

    Plugins register themselves here so the TriggerManager can
    find and instantiate them.
    """

    def __init__(self):
        self._plugins: Dict[str, TriggerPlugin] = {}

    def register(self, plugin: TriggerPlugin) -> None:
        """Register a trigger plugin."""
        spec = plugin.spec()
        trigger_id = spec.trigger_id
        if trigger_id in self._plugins:
            logger.warning(f"Overwriting existing plugin for trigger_id: {trigger_id}")
        self._plugins[trigger_id] = plugin
        logger.info(f"Registered trigger plugin: {trigger_id}")

    def get(self, trigger_id: str) -> Optional[TriggerPlugin]:
        """Get a plugin by trigger_id."""
        return self._plugins.get(trigger_id)

    def list_trigger_ids(self) -> List[str]:
        """List all registered trigger IDs."""
        return list(self._plugins.keys())

    def get_spec(self, trigger_id: str) -> Optional[TriggerSpec]:
        """Get the spec for a trigger type."""
        plugin = self.get(trigger_id)
        return plugin.spec() if plugin else None


# Global registry instance
_trigger_registry: Optional[TriggerRegistry] = None


def get_trigger_registry() -> TriggerRegistry:
    """Get the global trigger registry."""
    global _trigger_registry
    if _trigger_registry is None:
        _trigger_registry = TriggerRegistry()
    return _trigger_registry


# =============================================================================
# Config Hash Utility
# =============================================================================

def compute_config_hash(config: Dict[str, Any]) -> str:
    """
    Compute SHA-256 hash of a config dictionary.

    Uses canonical JSON (sorted keys, no whitespace) for consistent hashing.
    """
    canonical = json.dumps(config, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()


# =============================================================================
# TriggerManager (Singleton)
# =============================================================================

class TriggerManager:
    """
    Manages trigger instances and their lifecycle.

    The TriggerManager is a singleton that:
    - Maintains the desired state in SQLite
    - Runs a reconcile loop to sync actual state with desired state
    - Handles start/stop/restart of trigger instances
    - Processes emit() calls from triggers
    - Implements CrashLoopBackOff before FAILED

    Configuration:
        reconcile_interval_sec: Seconds between reconcile ticks (default: 10)
        max_crash_retries: Max retries before FAILED (default: 3)
        backoff_base_sec: Base backoff time in seconds (default: 1)
        backoff_max_sec: Maximum backoff time in seconds (default: 60)
    """

    _instance: Optional['TriggerManager'] = None
    _initialized: bool = False

    def __new__(cls, *args, **kwargs):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self,
        session_factory: Optional[Callable[[], Session]] = None,
        reconcile_interval_sec: int = 10,
        max_crash_retries: int = 3,
        backoff_base_sec: float = 1.0,
        backoff_max_sec: float = 60.0,
    ):
        """
        Initialize the TriggerManager.

        Args:
            session_factory: Callable that returns a new database session
            reconcile_interval_sec: Seconds between reconcile ticks
            max_crash_retries: Max retries before marking FAILED
            backoff_base_sec: Base backoff time for retries
            backoff_max_sec: Maximum backoff time
        """
        if TriggerManager._initialized:
            return

        TriggerManager._initialized = True

        self._session_factory = session_factory
        self._reconcile_interval_sec = reconcile_interval_sec
        self._max_crash_retries = max_crash_retries
        self._backoff_base_sec = backoff_base_sec
        self._backoff_max_sec = backoff_max_sec

        # Runtime state
        self._active_instances: Dict[str, RuntimeHandle] = {}
        self._reconcile_task: Optional[asyncio.Task] = None
        self._running = False
        self._reconcile_lock = asyncio.Lock()
        self._wake_event = asyncio.Event()

        # Registry
        self._registry = get_trigger_registry()

        logger.info(
            f"TriggerManager initialized: "
            f"reconcile_interval={reconcile_interval_sec}s, "
            f"max_retries={max_crash_retries}"
        )

    def set_session_factory(self, session_factory: Callable[[], Session]) -> None:
        """Set the session factory after initialization."""
        self._session_factory = session_factory

    def _get_session(self) -> Session:
        """Get a new database session."""
        if self._session_factory is None:
            raise RuntimeError("TriggerManager: session_factory not set")
        return self._session_factory()

    # =========================================================================
    # Start / Stop
    # =========================================================================

    async def start(self) -> None:
        """Start the supervisor/reconcile loop."""
        if self._running:
            logger.warning("TriggerManager already running")
            return

        self._running = True
        self._reconcile_task = asyncio.create_task(self._reconcile_loop())
        logger.info("TriggerManager started")

    async def stop(self, timeout_sec: float = 30.0) -> None:
        """
        Stop the TriggerManager gracefully.

        Sets stopping=True on all handles, cancels tasks, and waits
        for completion with timeout.

        Args:
            timeout_sec: Maximum time to wait for tasks to complete
        """
        if not self._running:
            logger.warning("TriggerManager not running")
            return

        logger.info("Stopping TriggerManager...")
        self._running = False

        # Cancel reconcile loop
        if self._reconcile_task:
            self._reconcile_task.cancel()
            try:
                await asyncio.wait_for(self._reconcile_task, timeout=5.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass

        # Stop all active instances gracefully
        tasks_to_wait = []
        for handle in list(self._active_instances.values()):
            handle.stopping = True
            handle.cancel_event.set()
            tasks_to_wait.append(handle.task)

        if tasks_to_wait:
            logger.info(f"Waiting for {len(tasks_to_wait)} trigger tasks to complete...")
            done, pending = await asyncio.wait(
                tasks_to_wait,
                timeout=timeout_sec,
                return_when=asyncio.ALL_COMPLETED
            )

            # Force cancel any pending tasks
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

            logger.info(f"Stopped {len(done)} trigger tasks, cancelled {len(pending)}")

        self._active_instances.clear()
        logger.info("TriggerManager stopped")

    # =========================================================================
    # Public API Methods
    # =========================================================================

    async def set_agent_triggers(
        self,
        agent_id: str,
        triggers: List[TriggerConfig]
    ) -> SetAgentTriggersResponse:
        """
        Set the triggers for an agent.

        Creates new triggers, updates existing ones, and deletes
        triggers not in the provided list.

        Args:
            agent_id: UUID of the agent
            triggers: List of trigger configurations

        Returns:
            SetAgentTriggersResponse with the final trigger list
        """
        repos = _get_repositories()
        TriggerInstanceRepository = repos.TriggerInstanceRepository

        session = self._get_session()
        try:
            repo = TriggerInstanceRepository(session)

            # Get existing triggers
            existing = repo.list_by_agent(agent_id)
            existing_by_id = {t.trigger_id: t for t in existing}

            created = 0
            updated = 0
            deleted = 0

            # Track which trigger_ids we're keeping
            new_trigger_ids: Set[str] = set()

            for trigger_cfg in triggers:
                new_trigger_ids.add(trigger_cfg.trigger_id)
                config_hash = compute_config_hash(trigger_cfg.config)

                if trigger_cfg.trigger_id in existing_by_id:
                    # Update existing trigger
                    existing_trigger = existing_by_id[trigger_cfg.trigger_id]

                    # Check if config changed
                    if existing_trigger.config_hash != config_hash:
                        existing_trigger.set_config(trigger_cfg.config)
                        updated += 1

                    # Update status and unfreeze if needed
                    if existing_trigger.status == 'FAILED' and trigger_cfg.status == TriggerStatus.ENABLED:
                        existing_trigger.error_message = None
                        existing_trigger.error_at = None

                    existing_trigger.status = trigger_cfg.status.value
                    existing_trigger.updated_at = datetime.utcnow()
                    session.commit()
                else:
                    # Create new trigger
                    repo.create(
                        agent_id=agent_id,
                        trigger_id=trigger_cfg.trigger_id,
                        config=trigger_cfg.config,
                        status=trigger_cfg.status.value
                    )
                    created += 1

            # Delete triggers not in the new list
            for existing_trigger in existing:
                if existing_trigger.trigger_id not in new_trigger_ids:
                    repo.delete(existing_trigger.trigger_instance_id)
                    deleted += 1

            # Wake up reconcile loop
            self._wake_event.set()

            # Get final list
            final_triggers = repo.list_by_agent(agent_id)

            return SetAgentTriggersResponse(
                agent_id=agent_id,
                triggers=[self._to_response(t) for t in final_triggers],
                created=created,
                updated=updated,
                deleted=deleted
            )
        finally:
            session.close()

    async def delete_agent_triggers(self, agent_id: str) -> DeleteAgentTriggersResponse:
        """
        Delete all triggers for an agent.

        Args:
            agent_id: UUID of the agent

        Returns:
            DeleteAgentTriggersResponse with deletion count
        """
        repos = _get_repositories()
        TriggerInstanceRepository = repos.TriggerInstanceRepository

        session = self._get_session()
        try:
            repo = TriggerInstanceRepository(session)
            deleted = repo.delete_by_agent(agent_id)

            # Wake up reconcile loop
            self._wake_event.set()

            return DeleteAgentTriggersResponse(
                agent_id=agent_id,
                deleted=deleted
            )
        finally:
            session.close()

    async def set_agent_triggers_enabled(
        self,
        agent_id: str,
        enabled: bool
    ) -> SetAgentTriggersEnabledResponse:
        """
        Enable or disable all triggers for an agent.

        Args:
            agent_id: UUID of the agent
            enabled: True to enable, False to disable

        Returns:
            SetAgentTriggersEnabledResponse with affected count
        """
        repos = _get_repositories()
        TriggerInstanceRepository = repos.TriggerInstanceRepository

        session = self._get_session()
        try:
            repo = TriggerInstanceRepository(session)
            affected = repo.set_agent_triggers_enabled(agent_id, enabled)

            # Wake up reconcile loop
            self._wake_event.set()

            return SetAgentTriggersEnabledResponse(
                agent_id=agent_id,
                enabled=enabled,
                affected=affected
            )
        finally:
            session.close()

    async def list_triggers(self) -> List[TriggerInstanceResponse]:
        """
        List all trigger instances.

        Returns:
            List of TriggerInstanceResponse objects
        """
        repos = _get_repositories()
        TriggerInstanceRepository = repos.TriggerInstanceRepository

        session = self._get_session()
        try:
            repo = TriggerInstanceRepository(session)
            triggers = repo.list_all()
            return [self._to_response(t) for t in triggers]
        finally:
            session.close()

    async def list_agent_triggers(self, agent_id: str) -> List[TriggerInstanceResponse]:
        """
        List all triggers for a specific agent.

        Args:
            agent_id: UUID of the agent

        Returns:
            List of TriggerInstanceResponse objects
        """
        repos = _get_repositories()
        TriggerInstanceRepository = repos.TriggerInstanceRepository

        session = self._get_session()
        try:
            repo = TriggerInstanceRepository(session)
            triggers = repo.list_by_agent(agent_id)
            return [self._to_response(t) for t in triggers]
        finally:
            session.close()

    async def get_trigger(self, trigger_instance_id: str) -> Optional[TriggerInstanceResponse]:
        """
        Get a single trigger instance.

        Args:
            trigger_instance_id: UUID of the trigger instance

        Returns:
            TriggerInstanceResponse or None if not found
        """
        repos = _get_repositories()
        TriggerInstanceRepository = repos.TriggerInstanceRepository

        session = self._get_session()
        try:
            repo = TriggerInstanceRepository(session)
            trigger = repo.get_by_id(trigger_instance_id)
            return self._to_response(trigger) if trigger else None
        finally:
            session.close()

    # =========================================================================
    # Emit (Called by Triggers)
    # =========================================================================

    async def emit(
        self,
        trigger_instance_id: str,
        payload: Dict[str, Any]
    ) -> Optional[str]:
        """
        Handle an event emitted by a trigger.

        Creates an AgentRun execution for the associated agent.

        Args:
            trigger_instance_id: ID of the trigger instance
            payload: Event payload

        Returns:
            run_id of the created execution, or None if rejected
        """
        repos = _get_repositories()
        TriggerInstanceRepository = repos.TriggerInstanceRepository
        AgentRunRepository = repos.AgentRunRepository

        # Check if handle exists and is active
        handle = self._active_instances.get(trigger_instance_id)
        if handle is None:
            logger.warning(
                f"emit() rejected: no active handle for {trigger_instance_id}"
            )
            return None

        session = self._get_session()
        try:
            # Verify trigger is still ENABLED in DB
            repo = TriggerInstanceRepository(session)
            trigger = repo.get_by_id(trigger_instance_id)

            if trigger is None:
                logger.warning(f"emit() rejected: trigger {trigger_instance_id} not found in DB")
                return None

            if trigger.status != 'ENABLED':
                logger.warning(
                    f"emit() rejected: trigger {trigger_instance_id} is {trigger.status}"
                )
                return None

            # Validate event payload against schema if available
            spec = self._registry.get_spec(trigger.trigger_id)
            if spec and spec.event_schema:
                if not self._validate_payload(payload, spec.event_schema):
                    logger.error(
                        f"emit() rejected: payload validation failed for {trigger_instance_id}"
                    )
                    return None

            # Create AgentRun execution
            run_repo = AgentRunRepository(session)
            run = run_repo.create(
                agent_id=trigger.agent_id,
                trigger_type=trigger.trigger_id,
                status='pending'
            )

            logger.info(
                f"Created execution {run.run_id} from trigger {trigger_instance_id}"
            )
            return run.run_id

        except Exception as e:
            logger.error(f"emit() failed: {e}")
            return None
        finally:
            session.close()

    def _validate_payload(
        self,
        payload: Dict[str, Any],
        schema: Dict[str, Any]
    ) -> bool:
        """Validate a payload against a JSON schema."""
        try:
            import jsonschema
            jsonschema.validate(payload, schema)
            return True
        except ImportError:
            logger.warning("jsonschema not installed, skipping validation")
            return True
        except jsonschema.ValidationError as e:
            logger.error(f"Payload validation error: {e.message}")
            return False

    # =========================================================================
    # Reconcile Loop
    # =========================================================================

    async def _reconcile_loop(self) -> None:
        """Main reconcile loop that runs periodically."""
        logger.info("Reconcile loop started")

        while self._running:
            try:
                # Wait for interval or wake event
                try:
                    await asyncio.wait_for(
                        self._wake_event.wait(),
                        timeout=self._reconcile_interval_sec
                    )
                    self._wake_event.clear()
                except asyncio.TimeoutError:
                    pass

                if not self._running:
                    break

                await self._reconcile()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Reconcile loop error: {e}")
                await asyncio.sleep(1)  # Brief pause on error

        logger.info("Reconcile loop stopped")

    async def _reconcile(self) -> None:
        """
        Perform one reconcile cycle.

        Compares desired state (DB) with actual state (active_instances)
        and starts/stops/restarts instances as needed.
        """
        async with self._reconcile_lock:
            repos = _get_repositories()
            TriggerInstanceRepository = repos.TriggerInstanceRepository

            session = self._get_session()
            try:
                repo = TriggerInstanceRepository(session)

                # Get desired state (minimal fields)
                desired_records = repo.list_for_reconcile()
                desired_map = {
                    r.trigger_instance_id: r for r in desired_records
                }

                # Get actual state
                actual_ids = set(self._active_instances.keys())

                # Instances to stop (in actual but not in desired, or DISABLED/FAILED)
                for instance_id in actual_ids:
                    handle = self._active_instances.get(instance_id)
                    if handle is None:
                        continue

                    desired = desired_map.get(instance_id)

                    should_stop = False
                    if desired is None:
                        # Deleted from DB
                        should_stop = True
                    elif desired.status in ('DISABLED', 'FAILED'):
                        should_stop = True
                    elif desired.status == 'ENABLED' and desired.config_hash != handle.config_hash:
                        # Config drift - need to restart
                        should_stop = True

                    if should_stop:
                        await self._stop_instance(instance_id)

                # Instances to start (in desired as ENABLED but not in actual)
                for instance_id, desired in desired_map.items():
                    if desired.status != 'ENABLED':
                        continue

                    if instance_id not in self._active_instances:
                        # Load full config
                        config_json = repo.get_config_json(instance_id)
                        if config_json:
                            config = json.loads(config_json)
                            await self._start_instance(
                                instance_id,
                                desired.agent_id,
                                desired.trigger_id,
                                config,
                                desired.config_hash
                            )

            finally:
                session.close()

    async def _start_instance(
        self,
        trigger_instance_id: str,
        agent_id: str,
        trigger_id: str,
        config: Dict[str, Any],
        config_hash: str
    ) -> bool:
        """
        Start a trigger instance.

        Args:
            trigger_instance_id: UUID of the instance
            agent_id: Parent agent ID
            trigger_id: Type of trigger
            config: Trigger configuration
            config_hash: Hash of the config

        Returns:
            True if started successfully
        """
        # Check if plugin exists
        plugin = self._registry.get(trigger_id)
        if plugin is None:
            logger.error(f"No plugin registered for trigger_id: {trigger_id}")
            return False

        # Create runtime
        try:
            runtime = plugin.create_runtime()
        except Exception as e:
            logger.error(f"Failed to create runtime for {trigger_id}: {e}")
            return False

        # Create cancel event
        cancel_event = asyncio.Event()

        # Create emit callback
        async def emit_callback(payload: Dict[str, Any]) -> None:
            await self.emit(trigger_instance_id, payload)

        # Create and start task
        task = asyncio.create_task(
            self._run_trigger(
                trigger_instance_id,
                runtime,
                config,
                emit_callback,
                cancel_event
            )
        )

        # Create handle
        handle = RuntimeHandle(
            trigger_instance_id=trigger_instance_id,
            agent_id=agent_id,
            trigger_id=trigger_id,
            task=task,
            cancel_event=cancel_event,
            config_hash=config_hash
        )

        self._active_instances[trigger_instance_id] = handle

        logger.info(f"Started trigger instance: {trigger_instance_id} (type={trigger_id})")
        return True

    async def _run_trigger(
        self,
        trigger_instance_id: str,
        runtime: TriggerRuntime,
        config: Dict[str, Any],
        emit: Callable[[Dict[str, Any]], Awaitable[None]],
        cancel_event: asyncio.Event
    ) -> None:
        """
        Run a trigger runtime and handle completion/errors.

        Args:
            trigger_instance_id: UUID of the instance
            runtime: The trigger runtime to run
            config: Trigger configuration
            emit: Emit callback
            cancel_event: Cancellation event
        """
        try:
            await runtime.start(config, emit, cancel_event)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(
                f"Trigger {trigger_instance_id} crashed: {e}\n"
                f"{traceback.format_exc()}"
            )
            await self._on_instance_done(trigger_instance_id, exception=e)
            return

        await self._on_instance_done(trigger_instance_id)

    async def _stop_instance(self, trigger_instance_id: str) -> None:
        """
        Stop a trigger instance gracefully.

        Args:
            trigger_instance_id: UUID of the instance
        """
        handle = self._active_instances.get(trigger_instance_id)
        if handle is None:
            return

        handle.stopping = True
        handle.cancel_event.set()

        try:
            await asyncio.wait_for(handle.task, timeout=10.0)
        except (asyncio.CancelledError, asyncio.TimeoutError):
            handle.task.cancel()
            try:
                await handle.task
            except asyncio.CancelledError:
                pass

        if trigger_instance_id in self._active_instances:
            del self._active_instances[trigger_instance_id]

        logger.info(f"Stopped trigger instance: {trigger_instance_id}")

    async def _on_instance_done(
        self,
        trigger_instance_id: str,
        exception: Optional[Exception] = None
    ) -> None:
        """
        Handle trigger instance completion.

        If stopped intentionally, just clean up.
        If crashed, implement CrashLoopBackOff.

        Args:
            trigger_instance_id: UUID of the instance
            exception: Exception if crashed
        """
        handle = self._active_instances.get(trigger_instance_id)
        if handle is None:
            return

        # Normal stop (intentional)
        if handle.stopping or handle.cancel_event.is_set():
            if trigger_instance_id in self._active_instances:
                del self._active_instances[trigger_instance_id]
            logger.info(f"Trigger {trigger_instance_id} stopped normally")
            return

        # Crashed - implement CrashLoopBackOff
        handle.crash_count += 1
        handle.last_crash_at = datetime.utcnow()

        if handle.crash_count >= self._max_crash_retries:
            # Mark as FAILED in DB
            repos = _get_repositories()
            TriggerInstanceRepository = repos.TriggerInstanceRepository

            session = self._get_session()
            try:
                repo = TriggerInstanceRepository(session)
                error_msg = str(exception)[:1000] if exception else "Unknown error"
                repo.set_failed(trigger_instance_id, error_msg)
            finally:
                session.close()

            if trigger_instance_id in self._active_instances:
                del self._active_instances[trigger_instance_id]

            logger.error(
                f"Trigger {trigger_instance_id} marked FAILED after "
                f"{self._max_crash_retries} crashes"
            )
        else:
            # Backoff and retry
            backoff = min(
                self._backoff_base_sec * (2 ** (handle.crash_count - 1)),
                self._backoff_max_sec
            )

            logger.warning(
                f"Trigger {trigger_instance_id} crashed "
                f"({handle.crash_count}/{self._max_crash_retries}), "
                f"retrying in {backoff}s"
            )

            # Remove from active and let reconcile restart
            if trigger_instance_id in self._active_instances:
                del self._active_instances[trigger_instance_id]

            await asyncio.sleep(backoff)
            self._wake_event.set()

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _to_response(self, trigger) -> TriggerInstanceResponse:
        """Convert ORM model to response model."""
        return TriggerInstanceResponse(
            trigger_instance_id=trigger.trigger_instance_id,
            agent_id=trigger.agent_id,
            trigger_id=trigger.trigger_id,
            status=TriggerStatus(trigger.status),
            config=trigger.get_config(),
            config_hash=trigger.config_hash,
            error_message=trigger.error_message,
            error_at=trigger.error_at,
            created_at=trigger.created_at,
            updated_at=trigger.updated_at
        )

    def unregister_triggers_for_agent(self, agent_id: str) -> int:
        """
        Unregister all triggers for an agent.

        Stops all running triggers and deletes them from the database.
        Called when an agent is deactivated or deleted.

        Args:
            agent_id: UUID of the agent

        Returns:
            Number of triggers deleted
        """
        repos = _get_repositories()
        TriggerInstanceRepository = repos.TriggerInstanceRepository

        # Mark in-memory handles for stopping
        to_remove = [
            handle.trigger_instance_id
            for handle in self._active_instances.values()
            if handle.agent_id == agent_id
        ]

        for instance_id in to_remove:
            handle = self._active_instances.get(instance_id)
            if handle:
                handle.stopping = True
                handle.cancel_event.set()

        # Delete from database
        deleted = 0
        session = self._get_session()
        try:
            repo = TriggerInstanceRepository(session)
            deleted = repo.delete_by_agent(agent_id)

            # Wake up reconcile loop
            self._wake_event.set()

        except Exception as e:
            logger.error(f"unregister_triggers_for_agent failed: {e}")
        finally:
            session.close()

        logger.info(f"Unregistered {deleted} triggers for agent {agent_id}")
        return deleted

    # =========================================================================
    # Legacy/Compatibility Methods (for existing code)
    # =========================================================================

    def register_trigger(
        self,
        agent_id: str,
        trigger_config: Dict[str, Any]
    ) -> bool:
        """
        Register a single trigger for an agent (synchronous wrapper).

        This method creates a trigger in the database. The reconcile loop
        will pick it up and start it asynchronously.

        Args:
            agent_id: UUID of the agent
            trigger_config: Trigger configuration dict with 'type' or 'trigger_id'

        Returns:
            True if created successfully
        """
        repos = _get_repositories()
        TriggerInstanceRepository = repos.TriggerInstanceRepository

        # Extract trigger_id from config
        trigger_id = trigger_config.get('type') or trigger_config.get('trigger_id')
        if not trigger_id:
            logger.error("register_trigger: missing 'type' or 'trigger_id' in config")
            return False

        # Extract nested config or use the whole dict minus type
        config = trigger_config.get('config', {})
        if not config:
            # Fallback: use all keys except 'type' and 'trigger_id'
            config = {k: v for k, v in trigger_config.items()
                      if k not in ('type', 'trigger_id', 'config')}

        session = self._get_session()
        try:
            repo = TriggerInstanceRepository(session)

            # Check if trigger already exists for this agent + trigger_id
            existing = repo.list_by_agent(agent_id)
            for t in existing:
                if t.trigger_id == trigger_id:
                    # Update existing trigger
                    new_hash = compute_config_hash(config)
                    if t.config_hash != new_hash:
                        t.set_config(config)
                        t.updated_at = datetime.utcnow()
                        session.commit()
                        logger.info(f"Updated trigger {t.trigger_instance_id} for agent {agent_id}")
                    return True

            # Create new trigger
            repo.create(
                agent_id=agent_id,
                trigger_id=trigger_id,
                config=config,
                status='ENABLED'
            )

            # Wake up reconcile loop
            self._wake_event.set()

            logger.info(f"Created trigger {trigger_id} for agent {agent_id}")
            return True

        except Exception as e:
            logger.error(f"register_trigger failed: {e}")
            return False
        finally:
            session.close()

    def validate_triggers_config(
        self,
        triggers: List[Dict[str, Any]]
    ) -> tuple[bool, Optional[str]]:
        """
        Validate trigger configurations.

        Args:
            triggers: List of trigger configuration dictionaries

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not isinstance(triggers, list):
            return False, "Triggers must be a list"

        for i, trigger in enumerate(triggers):
            if not isinstance(trigger, dict):
                return False, f"Trigger at index {i} must be a dictionary"

            trigger_type = trigger.get('type') or trigger.get('trigger_id')
            if not trigger_type:
                return False, f"Trigger at index {i} missing 'type' or 'trigger_id' field"

        return True, None

    def get_active_triggers(self, agent_id: str) -> List[Dict[str, Any]]:
        """
        Get list of active triggers for an agent (legacy method).
        """
        return [
            {
                'trigger_instance_id': h.trigger_instance_id,
                'trigger_id': h.trigger_id,
                'config_hash': h.config_hash,
                'started_at': h.started_at.isoformat()
            }
            for h in self._active_instances.values()
            if h.agent_id == agent_id
        ]

    def get_all_active_agents(self) -> List[str]:
        """
        Get list of all agent IDs with active triggers.
        """
        return list(set(h.agent_id for h in self._active_instances.values()))


# =============================================================================
# Global Instance
# =============================================================================

_trigger_manager: Optional[TriggerManager] = None


def get_trigger_manager() -> TriggerManager:
    """Get the global TriggerManager instance."""
    global _trigger_manager
    if _trigger_manager is None:
        _trigger_manager = TriggerManager()
    return _trigger_manager


def init_trigger_manager(
    session_factory: Callable[[], Session],
    **kwargs
) -> TriggerManager:
    """
    Initialize the global TriggerManager.

    Args:
        session_factory: Callable that returns a new database session
        **kwargs: Additional configuration options

    Returns:
        The initialized TriggerManager
    """
    global _trigger_manager
    _trigger_manager = TriggerManager(session_factory=session_factory, **kwargs)
    return _trigger_manager
