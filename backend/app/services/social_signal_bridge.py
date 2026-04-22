from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.personalization.preference_service import PreferenceService
from app.services.social_signal_types import SocialSignalsV1


class SocialSignalBridge:
    def __init__(self, db: AsyncSession, redis=None) -> None:
        self.db = db
        self.redis = redis
        self.preference_service = PreferenceService(db, redis)
        from app.routing.aggregator_backed_social_context_provider import (
            AggregatorBackedSocialContextProvider,
        )

        self.provider = AggregatorBackedSocialContextProvider(db)

    async def _fetch_for_user(self, user_id: UUID) -> dict[str, Any]:
        snapshot = await self.provider.fetch_social_snapshot(user_id)
        prefs_center = await self.preference_service.get_preferences(user_id)
        inferred = dict(getattr(prefs_center, "inferred", {}) or {})
        return {
            "snapshot": snapshot,
            "inferred": inferred,
        }

    async def build_social_signals_v1(self, user_id: UUID) -> SocialSignalsV1 | None:
        payload = await self._fetch_for_user(user_id)
        snapshot = payload.get("snapshot")
        if snapshot is None:
            return None

        inferred = payload.get("inferred")
        inferred = inferred if isinstance(inferred, dict) else {}
        mention_count = len(getattr(snapshot, "recent_person_mentions", []) or [])
        relationship_count = int(getattr(snapshot, "relationship_count", 0) or 0)
        pending_commitments_count = int(getattr(snapshot, "pending_commitments_count", 0) or 0)
        engagement_level = str(inferred.get("community_engagement_level") or "").strip() or None
        social_learning_preference = inferred.get("social_learning_preference")
        if social_learning_preference is not None:
            social_learning_preference = float(social_learning_preference)
        content_contribution_rate = inferred.get("content_contribution_rate")
        if content_contribution_rate is not None:
            content_contribution_rate = float(content_contribution_rate)

        summary_lines: list[str] = []
        if mention_count > 0:
            summary_lines.append(f"最近 7 天提到过 {mention_count} 位学习相关人物。")
        if relationship_count > 0:
            summary_lines.append(f"当前有 {relationship_count} 条关系型背景需要在建议里保持边界感。")
        if pending_commitments_count > 0:
            summary_lines.append(f"目前有 {pending_commitments_count} 条到期承诺待跟进。")
        if engagement_level:
            summary_lines.append(f"社区参与度推断为 {engagement_level}。")
        if social_learning_preference is not None:
            summary_lines.append(f"社交学习倾向约为 {social_learning_preference:.2f}。")
        if content_contribution_rate is not None:
            summary_lines.append(f"内容贡献倾向约为 {content_contribution_rate:.2f}。")

        signals = SocialSignalsV1(
            mention_count=mention_count,
            relationship_count=relationship_count,
            pending_commitments_count=pending_commitments_count,
            community_engagement_level=engagement_level,
            social_learning_preference=social_learning_preference,
            content_contribution_rate=content_contribution_rate,
            summary_lines=tuple(summary_lines[:4]),
        )
        if not signals.summary_lines and mention_count <= 0 and relationship_count <= 0:
            return None
        return signals
