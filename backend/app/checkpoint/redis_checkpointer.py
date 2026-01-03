import json
from typing import Optional, Any, Dict
from loguru import logger
from app.orchestration.statechart_engine import WorkflowState

class RedisCheckpointer:
    """
    Persists StateGraph checkpoints to Redis.
    """
    def __init__(self, redis_client: Any, ttl: int = 3600 * 24):
        self.redis = redis_client
        self.ttl = ttl

    async def save(self, state: WorkflowState, node_id: str):
        """Save state checkpoint."""
        if not self.redis:
            return

        session_id = state.context_data.get("session_id")
        if not session_id:
            return

        key = f"checkpoint:{session_id}"
        
        # Serialize state
        # Filter out non-serializable objects from context
        safe_context = {}
        for k, v in state.context_data.items():
            if k in ["db_session", "stream_callback", "tools_schema"]:
                continue
            try:
                json.dumps(v)
                safe_context[k] = v
            except (TypeError, OverflowError):
                logger.warning(f"Skipping non-serializable context key: {k}")

        data = {
            "node_id": node_id,
            "messages": state.messages,
            "context_data": safe_context,
            "next_step": state.next_step,
            "errors": state.errors,
            "is_finished": state.is_finished,
            "trace_id": state.trace_id
        }
        
        try:
            await self.redis.set(key, json.dumps(data), ex=self.ttl)
            logger.debug(f"Saved checkpoint for session {session_id} at node {node_id}")
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")

    async def load(self, session_id: str) -> Optional[WorkflowState]:
        """Load state from checkpoint."""
        if not self.redis:
            return None

        key = f"checkpoint:{session_id}"
        try:
            data_str = await self.redis.get(key)
            if not data_str:
                return None
            
            data = json.loads(data_str)
            
            state = WorkflowState(
                messages=data.get("messages", []),
                context_data=data.get("context_data", {}),
                next_step=data.get("next_step"),
                errors=data.get("errors", []),
                is_finished=data.get("is_finished", False),
                trace_id=data.get("trace_id", "")
            )
            return state
        except Exception as e:
            logger.error(f"Failed to load checkpoint: {e}")
            return None
