# dennett/runners/model_runner.py
"""
ModelRunner: Abstract contract for LLM model execution.
"""

from typing import Callable, Optional
import asyncio

class ModelRunner:
    """
    Contract for LLM model runners.
    Does NOT know about: DB, queues, leasing, WS, EventHub.
    Only responsible for: model loading, unloading, and inference.
    """
    
    def __init__(self, *, settings: dict):
        """Initialize model runner with settings."""
        self.settings = settings

    async def ensure_loaded(self, model_id: str) -> None:
        """
        Load model into memory.
        
        Args:
            model_id: Identifier of the model to load.
        
        Raises:
            RuntimeError: If model cannot be loaded.
        """
        raise NotImplementedError

    async def unload(self) -> None:
        """
        Unload model from memory.
        """
        raise NotImplementedError

    async def run_chat(
        self,
        *,
        messages: list[dict],
        parameters: dict,
        on_token: Optional[Callable[[str], None]] = None,
        cancel_event: Optional[asyncio.Event] = None
    ) -> tuple[dict, Optional[float]]:
        """
        Run inference chat.
        
        Args:
            messages: List of chat messages [{"role": "user", "content": "..."}, ...]
            parameters: Generation parameters (temperature, max_tokens, etc.)
            on_token: Callback for each token (optional, for streaming)
            cancel_event: Signal to cancel execution (optional)
        
        Returns:
            (result_json, tokens_per_second)
            
        Where result_json matches:
            {
                "text": "full_generated_text",
                "finish_reason": "stop|length|cancelled|error",
                "usage": {
                    "prompt_tokens": 123,
                    "completion_tokens": 456,
                    "total_tokens": 579
                }
            }
        
        Raises:
            asyncio.CancelledError: If cancel_event is set.
        """
        raise NotImplementedError
