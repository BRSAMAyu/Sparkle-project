from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any

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
        request_id = str(state.context_data.get("request_id") or "").strip()
        now = datetime.now(UTC).replace(tzinfo=None)

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
            "session_id": str(session_id),
            "request_id": request_id,
            "checkpoint_kind": "stategraph_node_pre_execute",
            "incomplete": True,
            "completed_at": None,
            "saved_at": now.isoformat(),
            "expires_at": (now + timedelta(seconds=self.ttl)).isoformat(),
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

    async def mark_completed(self, session_id: str, request_id: str | None = None) -> None:
        """Mark a checkpoint complete without deleting it immediately."""
        if not self.redis or not session_id:
            return
        key = f"checkpoint:{session_id}"
        try:
            data_str = await self.redis.get(key)
            if not data_str:
                return
            data = json.loads(data_str)
            if request_id and data.get("request_id") and data.get("request_id") != request_id:
                return
            data["incomplete"] = False
            data["completed_at"] = datetime.now(UTC).replace(tzinfo=None).isoformat()
            await self.redis.set(key, json.dumps(data, ensure_ascii=False), ex=min(self.ttl, 6 * 3600))
        except Exception as e:
            logger.debug(f"Failed to mark checkpoint completed: {e}")

    async def load(self, session_id: str) -> WorkflowState | None:
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

    async def load_interrupted(
        self,
        *,
        session_id: str,
        request_id: str,
        max_age_seconds: int | None = None,
    ) -> tuple[WorkflowState, str, dict[str, Any]] | None:
        """Load an incomplete checkpoint for same-request interrupted recovery."""
        if not self.redis or not session_id or not request_id:
            return None

        key = f"checkpoint:{session_id}"
        try:
            data_str = await self.redis.get(key)
            if not data_str:
                return None
            data = json.loads(data_str)
            if data.get("request_id") != request_id:
                return None
            if data.get("checkpoint_kind") != "stategraph_node_pre_execute":
                return None
            if not bool(data.get("incomplete")):
                return None
            saved_at_raw = str(data.get("saved_at") or "").strip()
            if max_age_seconds is not None and saved_at_raw:
                saved_at = datetime.fromisoformat(saved_at_raw)
                if saved_at.tzinfo is not None:
                    saved_at = saved_at.astimezone(UTC).replace(tzinfo=None)
                if datetime.now(UTC).replace(tzinfo=None) - saved_at > timedelta(seconds=max_age_seconds):
                    return None

            state = WorkflowState(
                messages=data.get("messages", []),
                context_data=data.get("context_data", {}),
                next_step=data.get("next_step"),
                errors=data.get("errors", []),
                is_finished=data.get("is_finished", False),
                trace_id=data.get("trace_id", ""),
            )
            node_id = str(data.get("node_id") or "").strip()
            if not node_id:
                return None
            return state, node_id, data
        except Exception as e:
            logger.error(f"Failed to load interrupted checkpoint: {e}")
            return None
