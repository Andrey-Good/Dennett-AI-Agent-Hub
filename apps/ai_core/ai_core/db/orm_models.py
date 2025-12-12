# apps/ai_core/ai_core/db/orm_models.py
"""
SQLAlchemy ORM models for AI Core database schema.

This module defines all database tables using SQLAlchemy ORM:
- agents: Stores information about AI agents
- agent_runs: Tracks execution history of agents
- agent_test_cases: Stores test cases for agents
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column, String, Text, DateTime, ForeignKey, Integer, JSON,
    create_engine, Index, UniqueConstraint, ForeignKeyConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import uuid
import json

Base = declarative_base()


class Agent(Base):
    """
    Represents an AI agent with metadata and configuration.
    
    Attributes:
        id: Unique UUID identifier for the agent
        name: Display name of the agent
        description: Detailed description of the agent's purpose
        tags: JSON-serialized list of tags for categorization
        created_at: Timestamp when the agent was created
        modified_at: Timestamp of last modification
        runs: Relationship to associated agent runs
        test_cases: Relationship to associated test cases
    """
    __tablename__ = 'agents'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    tags = Column(Text, nullable=True)  # JSON-serialized list
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    modified_at = Column(DateTime, nullable=False, default=datetime.utcnow, 
                        onupdate=datetime.utcnow, index=True)
    
    # Relationships
    runs = relationship('AgentRun', back_populates='agent', cascade='all, delete-orphan')
    test_cases = relationship('AgentTestCase', back_populates='agent', cascade='all, delete-orphan')
    
    __table_args__ = (
        Index('idx_agent_created', 'created_at'),
        Index('idx_agent_modified', 'modified_at'),
    )
    
    def set_tags(self, tags: List[str]) -> None:
        """Set tags as JSON-serialized string."""
        self.tags = json.dumps(tags) if tags else None
    
    def get_tags(self) -> List[str]:
        """Get tags from JSON-serialized string."""
        return json.loads(self.tags) if self.tags else []
    
    def __repr__(self) -> str:
        return f"<Agent(id='{self.id}', name='{self.name}')>"


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
    
    run_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
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
    
    case_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
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
