# apps/ai_core/ai_core/db/orm_models.py
"""
SQLAlchemy ORM models for AI Core database schema.

This module defines all database tables using SQLAlchemy ORM:
- agents: Stores information about AI agents (v5.0 with versioning, soft delete)
- agent_drafts: Draft/branch management for agents
- agent_runs: Tracks execution history of agents
- agent_test_cases: Stores test cases for agents
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column, String, Text, DateTime, ForeignKey, Integer, JSON,
    create_engine, Index, UniqueConstraint, ForeignKeyConstraint, CheckConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import json

try:
    import uuid6
    def uuid7str() -> str:
        return str(uuid6.uuid7())
except ImportError:
    # Fallback to uuid4 if uuid6 not available
    import uuid
    def uuid7str() -> str:
        return str(uuid.uuid4())

Base = declarative_base()


class Agent(Base):
    """
    Represents an AI agent with metadata and configuration (v5.0).

    Attributes:
        id: Unique UUIDv7 identifier for the agent
        name: Display name of the agent
        description: Detailed description of the agent's purpose
        tags: JSON-serialized list of tags for categorization
        version: Current active version number (1, 2, 3...)
        is_active: Whether agent triggers are loaded (0=inactive, 1=active)
        deletion_status: Soft delete status ('NONE' or 'PENDING')
        file_path: Relative path to current live JSON file
        created_at: Timestamp when the agent was created
        modified_at: Timestamp of last modification (updated_at in spec)
        runs: Relationship to associated agent runs
        test_cases: Relationship to associated test cases
        drafts: Relationship to associated drafts
    """
    __tablename__ = 'agents'

    id = Column(String(36), primary_key=True, default=uuid7str)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    tags = Column(Text, nullable=True)  # JSON-serialized list

    # v5.0 versioning fields
    version = Column(Integer, nullable=False, default=1)
    is_active = Column(Integer, nullable=False, default=0)  # 0 or 1
    deletion_status = Column(String(20), nullable=False, default='NONE')  # NONE, PENDING
    file_path = Column(Text, nullable=True)  # Relative path from DATA_ROOT

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    modified_at = Column(DateTime, nullable=False, default=datetime.utcnow,
                        onupdate=datetime.utcnow, index=True)

    # Relationships
    runs = relationship('AgentRun', back_populates='agent', cascade='all, delete-orphan')
    test_cases = relationship('AgentTestCase', back_populates='agent', cascade='all, delete-orphan')
    drafts = relationship('AgentDraft', back_populates='agent', cascade='all, delete-orphan')
    trigger_instances = relationship('TriggerInstance', back_populates='agent', cascade='all, delete-orphan')

    __table_args__ = (
        Index('idx_agent_created', 'created_at'),
        Index('idx_agent_modified', 'modified_at'),
        Index('idx_agent_deletion_status', 'deletion_status'),
        CheckConstraint("deletion_status IN ('NONE', 'PENDING')", name='ck_agent_deletion_status'),
        CheckConstraint('version >= 1', name='ck_agent_version'),
        CheckConstraint('is_active IN (0, 1)', name='ck_agent_is_active'),
    )

    def set_tags(self, tags: List[str]) -> None:
        """Set tags as JSON-serialized string."""
        self.tags = json.dumps(tags) if tags else None

    def get_tags(self) -> List[str]:
        """Get tags from JSON-serialized string."""
        return json.loads(self.tags) if self.tags else []

    def is_pending_deletion(self) -> bool:
        """Check if agent is marked for deletion."""
        return self.deletion_status == 'PENDING'

    def is_agent_active(self) -> bool:
        """Check if agent triggers are loaded."""
        return self.is_active == 1

    def __repr__(self) -> str:
        return f"<Agent(id='{self.id}', name='{self.name}', v{self.version})>"


class AgentRun(Base):
    """
    Represents a single execution of an AI agent.
    
    Attributes:
        run_id: Unique UUID identifier for this run
        agent_id: Foreign key reference to the agent
        status: Current status of the run (pending, running, completed, failed, stopped_by_user)
        start_time: When the run started
        end_time: When the run ended or was stopped
        trigger_type: How the run was triggered (manual, schedule, webhook, file_system)
        error_message: Error details if the run failed
        agent: Relationship to the Agent
    """
    __tablename__ = 'agent_runs'
    
    run_id = Column(String(36), primary_key=True, default=uuid7str)
    agent_id = Column(String(36), ForeignKey('agents.id', ondelete='CASCADE'), 
                      nullable=False, index=True)
    status = Column(String(50), nullable=False, index=True)  # pending, running, completed, failed, stopped_by_user
    priority = Column(Integer, nullable=False, default=30, index=True)
    start_time = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    end_time = Column(DateTime, nullable=True, index=True)
    trigger_type = Column(String(50), nullable=False)  # manual, schedule, webhook, file_system
    error_message = Column(Text, nullable=True)
    
    # Relationship
    agent = relationship('Agent', back_populates='runs')
    
    __table_args__ = (
        Index('idx_agent_run_status', 'agent_id', 'status'),
        Index('idx_agent_run_time', 'start_time', 'end_time'),
        Index('idx_agent_run_priority', 'status', 'priority'),
        ForeignKeyConstraint(['agent_id'], ['agents.id']),
    )
    
    def get_duration_seconds(self) -> Optional[float]:
        """Calculate run duration in seconds."""
        if self.end_time and self.start_time:
            return (self.end_time - self.start_time).total_seconds()
        return None
    
    def is_running(self) -> bool:
        """Check if the run is currently in progress."""
        return self.status == 'running'
    
    def is_completed(self) -> bool:
        """Check if the run has completed successfully."""
        return self.status == 'completed'
    
    def has_error(self) -> bool:
        """Check if the run resulted in an error."""
        return self.status == 'failed'
    
    def __repr__(self) -> str:
        return f"<AgentRun(run_id='{self.run_id}', agent_id='{self.agent_id}', status='{self.status}')>"


class AgentTestCase(Base):
    """
    Represents a test case for an AI agent.
    
    Attributes:
        case_id: Unique UUID identifier for the test case
        agent_id: Foreign key reference to the agent
        node_id: ID of the node after which this test state is inserted
        name: Descriptive name of the test case
        initial_state: JSON-serialized initial state object
        agent: Relationship to the Agent
    """
    __tablename__ = 'agent_test_cases'
    
    case_id = Column(String(36), primary_key=True, default=uuid7str)
    agent_id = Column(String(36), ForeignKey('agents.id', ondelete='CASCADE'), 
                      nullable=False, index=True)
    node_id = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    initial_state = Column(Text, nullable=False)  # JSON-serialized state object
    
    # Relationship
    agent = relationship('Agent', back_populates='test_cases')
    
    __table_args__ = (
        Index('idx_test_case_agent', 'agent_id'),
        Index('idx_test_case_node', 'node_id'),
        UniqueConstraint('agent_id', 'node_id', 'name', name='uq_test_case_identity'),
    )
    
    def set_initial_state(self, state: dict) -> None:
        """Set initial state as JSON-serialized string."""
        self.initial_state = json.dumps(state)
    
    def get_initial_state(self) -> dict:
        """Get initial state from JSON-serialized string."""
        return json.loads(self.initial_state) if self.initial_state else {}
    
    def __repr__(self) -> str:
        return f"<AgentTestCase(case_id='{self.case_id}', agent_id='{self.agent_id}', name='{self.name}')>"


class AgentDraft(Base):
    """
    Represents a draft/branch of an agent for development.

    Drafts allow editing agent configurations without affecting the live version.
    Multiple drafts can exist per agent, each based on a specific version.

    Attributes:
        draft_id: Unique UUIDv7 identifier for the draft
        agent_id: Foreign key reference to the agent
        name: Branch/draft name (e.g., "Experiment with RAG", "Autosave")
        file_path: Relative path to draft JSON file
        base_version: Version of agent this draft is based on
        updated_at: Timestamp of last autosave (ISO UTC with ms)
        his_execution_id: JSON list of execution IDs related to this draft
        agent: Relationship to the Agent
    """
    __tablename__ = 'agent_drafts'

    draft_id = Column(String(36), primary_key=True, default=uuid7str)
    agent_id = Column(String(36), ForeignKey('agents.id', ondelete='CASCADE'),
                      nullable=False, index=True)
    name = Column(String(255), nullable=False)
    file_path = Column(Text, nullable=False)  # Relative path from DATA_ROOT
    base_version = Column(Integer, nullable=False)  # Version this draft is based on
    updated_at = Column(Text, nullable=False)  # ISO UTC with milliseconds
    his_execution_id = Column(Text, nullable=True)  # JSON list of execution IDs

    # Relationship
    agent = relationship('Agent', back_populates='drafts')

    __table_args__ = (
        Index('idx_draft_agent_updated', 'agent_id', 'updated_at'),
        CheckConstraint('base_version >= 1', name='ck_draft_base_version'),
    )

    def get_execution_ids(self) -> List[str]:
        """Get execution IDs from JSON-serialized string."""
        if self.his_execution_id:
            return json.loads(self.his_execution_id)
        return []

    def set_execution_ids(self, ids: List[str]) -> None:
        """Set execution IDs as JSON-serialized string."""
        self.his_execution_id = json.dumps(ids) if ids else None

    def add_execution_id(self, execution_id: str) -> None:
        """Add an execution ID to the list."""
        ids = self.get_execution_ids()
        if execution_id not in ids:
            ids.append(execution_id)
            self.set_execution_ids(ids)

    def __repr__(self) -> str:
        return f"<AgentDraft(draft_id='{self.draft_id}', agent_id='{self.agent_id}', name='{self.name}')>"


class TriggerInstance(Base):
    """
    Represents a trigger instance bound to an agent.

    Trigger instances are the runtime configuration for triggers that
    initiate agent executions based on events (webhooks, schedules, etc.).

    Attributes:
        trigger_instance_id: Unique UUID identifier for this trigger instance
        agent_id: Foreign key reference to the agent
        trigger_id: Type of trigger (e.g., 'cron', 'webhook', 'email')
        status: Current status (ENABLED, DISABLED, FAILED)
        config_json: JSON-serialized trigger configuration
        config_hash: SHA-256 hash of canonical config for change detection
        error_message: Error details if status is FAILED
        error_at: Timestamp when error occurred
        created_at: Timestamp when the trigger was created
        updated_at: Timestamp of last modification
        agent: Relationship to the Agent
    """
    __tablename__ = 'trigger_instances'

    trigger_instance_id = Column(String(36), primary_key=True, default=uuid7str)
    agent_id = Column(String(36), ForeignKey('agents.id', ondelete='CASCADE'),
                      nullable=False, index=True)
    trigger_id = Column(String(100), nullable=False, index=True)  # e.g., 'cron', 'webhook'
    status = Column(String(20), nullable=False, default='ENABLED', index=True)  # ENABLED, DISABLED, FAILED
    config_json = Column(Text, nullable=False)  # JSON-serialized config
    config_hash = Column(String(64), nullable=False)  # SHA-256 hash of canonical config
    error_message = Column(Text, nullable=True)
    error_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow,
                        onupdate=datetime.utcnow, index=True)

    # Relationship
    agent = relationship('Agent', back_populates='trigger_instances')

    __table_args__ = (
        Index('idx_trigger_agent_status', 'agent_id', 'status'),
        Index('idx_trigger_status', 'status'),
        CheckConstraint("status IN ('ENABLED', 'DISABLED', 'FAILED')", name='ck_trigger_status'),
    )

    def get_config(self) -> dict:
        """Get config from JSON-serialized string."""
        return json.loads(self.config_json) if self.config_json else {}

    def set_config(self, config: dict) -> None:
        """Set config as JSON-serialized string and update hash."""
        import hashlib
        # Canonical JSON: sorted keys, no whitespace
        canonical = json.dumps(config, sort_keys=True, separators=(',', ':'))
        self.config_json = json.dumps(config)
        self.config_hash = hashlib.sha256(canonical.encode('utf-8')).hexdigest()

    def is_enabled(self) -> bool:
        """Check if trigger is enabled."""
        return self.status == 'ENABLED'

    def is_failed(self) -> bool:
        """Check if trigger is in failed state."""
        return self.status == 'FAILED'

    def __repr__(self) -> str:
        return f"<TriggerInstance(id='{self.trigger_instance_id}', agent='{self.agent_id}', type='{self.trigger_id}', status='{self.status}')>"


class Execution(Base):
    """Task execution queue."""
    __tablename__ = 'executions'

    execution_id = Column(String(36), primary_key=True)
    node_id = Column(String(255), nullable=False, index=True)
    status = Column(String(50), nullable=False, index=True)  # PENDING, RUNNING, COMPLETED, FAILED
    priority = Column(Integer, nullable=False, index=True)
    enqueue_ts = Column(Integer, nullable=False, index=True)  # Unix timestamp

    __table_args__ = (
        Index('idx_exec_priority_queue', 'status', 'priority', 'enqueue_ts'),
    )


class InferenceQueue(Base):
    """Model inference queue."""
    __tablename__ = 'inference_queue'

    queue_id = Column(String(36), primary_key=True)
    model_id = Column(String(255), nullable=False, index=True)
    status = Column(String(50), nullable=False, index=True)
    priority = Column(Integer, nullable=False, index=True)
    enqueue_ts = Column(Integer, nullable=False, index=True)

    __table_args__ = (
        Index('idx_inference_priority_queue', 'status', 'priority', 'enqueue_ts'),
    )

# Foreign key constraints (explicit definition for clarity)
from sqlalchemy import ForeignKeyConstraint

AgentRun.__table_args__ = (
    Index('idx_agent_run_status', 'agent_id', 'status'),
    Index('idx_agent_run_time', 'start_time', 'end_time'),
    Index('idx_agent_run_trigger', 'trigger_type'),
)

AgentTestCase.__table_args__ = (
    Index('idx_test_case_agent', 'agent_id'),
    Index('idx_test_case_node', 'node_id'),
    UniqueConstraint('agent_id', 'node_id', 'name', name='uq_test_case_identity'),
)
