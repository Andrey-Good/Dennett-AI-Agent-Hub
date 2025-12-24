# dennett/core/eventhub.py
"""
EventHub: In-process pub/sub for realtime events.
"""

import asyncio
from typing import Callable, Dict, List, Any

class EventHub:
    """In-process publish/subscribe for events."""
    
    def __init__(self):
        self.subscribers: Dict[str, List[Callable]] = {}
        self.lock = asyncio.Lock()

    def subscribe(self, channel: str, callback: Callable):
        """Subscribe to channel: execution:{id}, inference:{id}"""
        if channel not in self.subscribers:
            self.subscribers[channel] = []
        self.subscribers[channel].append(callback)

    async def publish(self, channel: str, event: Dict[str, Any]):
        """Publish event to channel."""
        async with self.lock:
            if channel in self.subscribers:
                for callback in self.subscribers[channel]:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(event)
                        else:
                            callback(event)
                    except Exception as e:
                        print(f"❌ EventHub callback error: {e}")

    def unsubscribe(self, channel: str, callback: Callable):
        """Unsubscribe from channel."""
        if channel in self.subscribers and callback in self.subscribers[channel]:
            self.subscribers[channel].remove(callback)
