"""
State Event Manager - Unified Event Bus for State Changes
"""
from __future__ import annotations
import asyncio
from collections.abc import Callable
from typing import Any

from loguru import logger


class StateEventManager:
    def __init__(self):
        self._handlers: dict[str, list[Callable]] = {}

    def subscribe(self, event_type: str, handler: Callable):
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    async def publish(self, event_type: str, payload: dict[str, Any]):
        handlers = self._handlers.get(event_type, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(payload)
                else:
                    handler(payload)
            except Exception as e:
                logger.error(f"Error handling event {event_type}: {e}")

    async def publish_plan_scope_update(
        self,
        user_id: str,
        plan_id: str,
        changes: dict[str, Any],
        old_version: int | None = None,
        new_version: int | None = None,
    ):
        await self.publish("plan_scope_updated", {
            "user_id": str(user_id),
            "plan_id": str(plan_id),
            "changes": changes,
            "old_version": old_version,
            "new_version": new_version
        })

state_event_manager = StateEventManager()
