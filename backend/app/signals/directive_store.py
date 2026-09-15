"""
Core: execution
Phase: sense→clarify→plan→execute→reflect

DirectiveStore — extracted from SpineOrchestrator (P2-1 God Class reduction).

Generic Redis-backed CRUD for Spine directives: store, retrieve, publish.
All per-type convenience methods delegate to the generic _store_directive / _get_directive.
"""
from __future__ import annotations

import json
from typing import Any

from loguru import logger

from app.signals.types import (
    ModelWriteDirective,
    NotificationDirective,
    PlanDirective,
    ResponseDirective,
    RetrievalDirective,
    UXDirective,
)


class DirectiveStore:
    """Redis-backed directive store with per-type convenience methods.

    Expects callers to provide a redis client and a CausalTraceStore-compatible
    object via the constructor.
    """

    _TTL_DEFAULT = 72 * 3600

    def __init__(self, redis: Any, trace_store: Any) -> None:
        self.redis = redis
        self.trace_store = trace_store

    # ── Generic helpers ──────────────────────────────────────────────────

    async def store(self, user_id: str, directive_type: str, directive: Any) -> None:
        key = f"spine:{directive_type}_directive:{user_id}:latest"
        await self.redis.set(key, json.dumps(directive.to_dict()), ex=self._TTL_DEFAULT)
        await self.trace_store.store_directive_by_id(directive.directive_id, directive.to_dict())

    async def retrieve(self, user_id: str, directive_type: str, cls: type) -> Any | None:
        try:
            raw = await self.redis.get(f"spine:{directive_type}_directive:{user_id}:latest")
            if not raw:
                return None
            return cls.from_dict(json.loads(raw))
        except Exception:
            logger.debug("get_{}_directive degraded: Redis unavailable for user={}", directive_type, user_id)
            return None

    async def publish_event(self, channel: str, payload: dict) -> None:
        try:
            await self.redis.publish(channel, json.dumps(payload))
        except Exception:
            logger.debug("directive pub/sub failed on channel={}", channel, exc_info=True)

    # ── Per-type convenience methods ─────────────────────────────────────

    # ResponseDirective

    async def store_response(self, user_id: str, rd: ResponseDirective) -> None:
        await self.store(user_id, "response", rd)

    async def get_response(self, user_id: str) -> ResponseDirective | None:
        return await self.retrieve(user_id, "response", ResponseDirective)

    # NotificationDirective

    async def store_notification(self, user_id: str, nd: NotificationDirective) -> None:
        await self.store(user_id, "notification", nd)
        try:
            from app.core.event_bus import EventBus
            bus = EventBus()
            await bus.publish("spine.notification_directive", {
                "user_id": user_id,
                "directive_id": nd.directive_id,
                "notification_type": nd.notification_type,
                "allowed": nd.allowed,
                "user_visible_reason": nd.user_visible_reason,
            })
        except Exception:
            logger.debug("notification_directive event publish failed", exc_info=True)

    async def get_notification(self, user_id: str) -> NotificationDirective | None:
        return await self.retrieve(user_id, "notification", NotificationDirective)

    # RetrievalDirective

    async def store_retrieval(self, user_id: str, rd: RetrievalDirective) -> None:
        await self.store(user_id, "retrieval", rd)
        await self.publish_event("spine:retrieval_directive_channel", {
            "user_id": user_id, "directive_id": rd.directive_id,
            "retrieval_mode": rd.retrieval_mode if hasattr(rd, "retrieval_mode") else None,
        })

    async def get_retrieval(self, user_id: str) -> RetrievalDirective | None:
        return await self.retrieve(user_id, "retrieval", RetrievalDirective)

    # PlanDirective

    async def store_plan(self, user_id: str, pd: PlanDirective) -> None:
        await self.store(user_id, "plan", pd)
        try:
            from datetime import UTC as _UTC
            from datetime import datetime
            await self.redis.publish(
                "spine:plan_directive_channel",
                json.dumps({
                    "user_id": user_id,
                    "directive_id": pd.directive_id,
                    "action": pd.action if hasattr(pd, "action") else None,
                    "plan_id": pd.plan_id if hasattr(pd, "plan_id") else None,
                    "timestamp": datetime.now(_UTC).isoformat(),
                }),
            )
        except Exception:
            logger.debug("plan_directive pub/sub publish failed for user={}", user_id, exc_info=True)

    async def get_plan(self, user_id: str) -> PlanDirective | None:
        return await self.retrieve(user_id, "plan", PlanDirective)

    # ModelWriteDirective

    async def store_model_write(self, user_id: str, mwd: ModelWriteDirective) -> None:
        await self.store(user_id, "model_write", mwd)

    async def get_model_write(self, user_id: str) -> ModelWriteDirective | None:
        return await self.retrieve(user_id, "model_write", ModelWriteDirective)

    async def get_model_claims(
        self, user_id: str, target_model: str | None = None, scope: str | None = None,
    ) -> list[dict[str, Any]]:
        try:
            if target_model and scope:
                key = f"spine:model_claim:{user_id}:{target_model}:{scope}"
                raw = await self.redis.get(key)
                return [json.loads(raw)] if raw else []
            return []
        except Exception:
            logger.warning("get_model_claims: failed", exc_info=True)
            return []

    # UXDirective

    async def store_ux(self, user_id: str, uxd: UXDirective) -> None:
        await self.store(user_id, "ux", uxd)
        await self.publish_event("spine:ux_directive_channel", {
            "user_id": user_id, "directive_id": uxd.directive_id,
            "presentation_mode": uxd.presentation_mode if hasattr(uxd, "presentation_mode") else None,
        })

    async def get_ux(self, user_id: str) -> UXDirective | None:
        return await self.retrieve(user_id, "ux", UXDirective)
