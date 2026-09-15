from __future__ import annotations

import os
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tool_history import UserToolHistory
from app.routing.tool_preference_router import ToolPreferenceRouter
from app.routing.tool_preference_shadow import ToolPreferenceShadowRecorder


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class WithinCategoryPreferenceService:
    """Builds the bounded Stage 15 CL1 dashboard hint payload."""

    FEATURE_FLAG = "SPARKLE_CL1_WITHIN_CATEGORY_WIRE_ON"
    SURFACE = "dashboard.predicted_intent_card"
    SHADOW_LIMIT = 20
    MIN_SHADOW_RECORDS = 5
    MAX_DIVERGENCE_RATE = 0.35
    MIN_CATEGORY_OBSERVATIONS = 3
    MIN_DISTINCT_TOOLS = 2
    MIN_PREFERRED_PROBABILITY = 0.65
    MIN_MARGIN = 0.10
    HISTORY_DAYS = 30

    def __init__(self, db: AsyncSession, redis_client) -> None:
        self.db = db
        self.redis = redis_client
        self.shadow_recorder = ToolPreferenceShadowRecorder(redis_client) if redis_client else None

    @classmethod
    def is_enabled(cls) -> bool:
        raw = os.getenv(cls.FEATURE_FLAG, "").strip().lower()
        return raw in {"1", "true", "yes", "on"}

    async def build_hint(
        self,
        *,
        user_id: UUID,
        request_category: str | None,
    ) -> dict[str, Any] | None:
        if not self.is_enabled() or not self.redis or not request_category:
            return None

        summary = await self._get_shadow_summary(user_id)
        if summary is None:
            return None

        category_snapshot = await self._load_category_snapshot(
            user_id=user_id,
            request_category=request_category,
        )
        if category_snapshot is None:
            return None

        router = ToolPreferenceRouter(
            db_session=self.db,
            user_id=user_id,
            redis_client=self.redis,
        )
        await router.update_learner_from_history()

        ranked = await self._rank_tools_for_category(
            router=router,
            request_category=request_category,
            tool_names=category_snapshot["tool_names"],
        )
        if ranked is None:
            return None

        return {
            "claim_scope": "within_category_only",
            "surface": self.SURFACE,
            "request_category": request_category,
            "preferred_tool": ranked["preferred_tool"],
            "confidence": ranked["confidence"],
            "support_count": category_snapshot["observation_count"],
            "shadow_records": summary["total_records"],
            "divergence_rate": summary["divergence_rate"],
        }

    async def _get_shadow_summary(self, user_id: UUID) -> dict[str, Any] | None:
        if not self.shadow_recorder:
            return None

        summary = await self.shadow_recorder.get_divergence_summary(
            user_id=str(user_id),
            limit=self.SHADOW_LIMIT,
        )
        total_records = int(summary.get("total_records") or 0)
        divergence_rate = float(summary.get("divergence_rate") or 0.0)
        if total_records < self.MIN_SHADOW_RECORDS:
            return None
        if divergence_rate > self.MAX_DIVERGENCE_RATE:
            return None
        return summary

    async def _load_category_snapshot(
        self,
        *,
        user_id: UUID,
        request_category: str,
    ) -> dict[str, Any] | None:
        since = _utcnow() - timedelta(days=self.HISTORY_DAYS)
        stmt = (
            select(
                UserToolHistory.tool_name,
                func.count(UserToolHistory.id).label("usage_count"),
            )
            .where(
                and_(
                    UserToolHistory.user_id == user_id,
                    UserToolHistory.tool_category == request_category,
                    UserToolHistory.tool_name.is_not(None),
                    UserToolHistory.created_at >= since,
                )
            )
            .group_by(UserToolHistory.tool_name)
            .order_by(func.count(UserToolHistory.id).desc(), UserToolHistory.tool_name.asc())
        )

        rows = (await self.db.execute(stmt)).all()
        tool_names = [
            str(row.tool_name)
            for row in rows
            if row.tool_name and int(row.usage_count or 0) > 0
        ]
        observation_count = sum(int(row.usage_count or 0) for row in rows)
        if observation_count < self.MIN_CATEGORY_OBSERVATIONS:
            return None
        if len(tool_names) < self.MIN_DISTINCT_TOOLS:
            return None
        return {
            "tool_names": tool_names,
            "observation_count": observation_count,
        }

    async def _rank_tools_for_category(
        self,
        *,
        router: ToolPreferenceRouter,
        request_category: str,
        tool_names: Iterable[str],
    ) -> dict[str, Any] | None:
        source = f"state_{request_category}"
        ranked: list[tuple[str, float]] = []
        for tool_name in tool_names:
            probability = await router.learner.get_probability(source, tool_name)
            ranked.append((tool_name, probability))

        if len(ranked) < self.MIN_DISTINCT_TOOLS:
            return None

        ranked.sort(key=lambda item: item[1], reverse=True)
        top_tool, top_probability = ranked[0]
        runner_up_probability = ranked[1][1]
        if top_probability < self.MIN_PREFERRED_PROBABILITY:
            return None
        if (top_probability - runner_up_probability) < self.MIN_MARGIN:
            return None

        return {
            "preferred_tool": top_tool,
            "confidence": round(top_probability, 3),
        }
