# dennett/core/models.py
"""
Status models and constants.
"""

class ExecutionStatus:
    """Execution statuses."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCEL_REQUESTED = "CANCEL_REQUESTED"
    CANCELED = "CANCELED"

class InferenceStatus:
    """Inference task statuses."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCEL_REQUESTED = "CANCEL_REQUESTED"
    CANCELED = "CANCELED"

class NodeEventStatus:
    """Node event statuses."""
    STARTED = "STARTED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class EventType:
    """Event types for EventHub."""
    NODE_STARTED = "STARTED"
    NODE_COMPLETED = "COMPLETED"
    NODE_FAILED = "FAILED"
    TOKEN = "TOKEN"
    DONE = "DONE"
    ERROR = "ERROR"
    CANCELED = "CANCELED"
