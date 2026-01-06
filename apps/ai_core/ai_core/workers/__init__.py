# apps/ai_core/ai_core/workers/__init__.py
"""
Background workers for AI Core.
"""

from apps.ai_core.ai_core.workers.garbage_collector import (
    AgentGarbageCollector,
    get_garbage_collector,
    init_garbage_collector
)

__all__ = [
    'AgentGarbageCollector',
    'get_garbage_collector',
    'init_garbage_collector'
]
