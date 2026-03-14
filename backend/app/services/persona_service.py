import hashlib
import hmac
import json
import os
from typing import Any
from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.profile_context import ProfileContext
from app.models.cognitive import BehaviorPattern, CognitiveFragment
from app.models.compliance import PersonaSnapshot
from app.models.galaxy import UserNodeStatus


class ProfileSnapshotService:
    """
    用户画像快照服务 (Profile Snapshot)
    """

    def __init__(self, db: AsyncSession, redis_client=None):
        self.db = db
        self.redis = redis_client
        self.persona_version = os.getenv("PERSONA_VERSION", "v3.1")
        self.audit_secret = os.getenv("PERSONA_AUDIT_SECRET", "persona-audit-secret")

    async def build_profile_snapshot(
        self,
        user_id: UUID,
        purpose: str,
        profile_context: ProfileContext | None = None,
    ) -> dict[str, Any]:
        cache_key = f"persona:snapshot:{user_id}:{purpose}"
        if self.redis:
            cached = await self.redis.get(cache_key)
            if cached:
                return json.loads(cached)

        snapshot = await self._build_snapshot(user_id, purpose, profile_context=profile_context)
        if self.redis:
            await self.redis.setex(cache_key, 300, json.dumps(snapshot, ensure_ascii=False))

        await self._persist_snapshot(user_id, snapshot)
        return snapshot

    async def get_snapshot(self, user_id: UUID, purpose: str) -> dict[str, Any]:
        """Backward-compatible alias for legacy callers."""
        return await self.build_profile_snapshot(user_id, purpose)

    async def _build_snapshot(
        self,
        user_id: UUID,
        purpose: str,
        profile_context: ProfileContext | None = None,
    ) -> dict[str, Any]:
        if profile_context is not None:
            tags = [pattern.pattern_name for pattern in profile_context.cognitive_summary.active_patterns]
            capabilities = {
                "mastery_avg": float(profile_context.knowledge_summary.overall_mastery or 0.0),
                "active_subjects": profile_context.knowledge_summary.active_learning_subjects,
            }
        else:
            tags = await self._collect_tags(user_id)
            capabilities = await self._collect_capabilities(user_id)
        last_update_event_id = await self._get_last_event_id(user_id)

        audit_token = self._sign_audit_token(user_id, last_update_event_id)
        return {
            "persona_version": self.persona_version,
            "audit_token": audit_token,
            "purpose": purpose,
            "tags": tags,
            "capabilities": capabilities,
            "last_update_event_id": last_update_event_id
        }

    async def _collect_tags(self, user_id: UUID) -> list[str]:
        pattern_stmt = select(BehaviorPattern.pattern_name).where(
            BehaviorPattern.user_id == user_id,
            not BehaviorPattern.is_archived
        ).order_by(desc(BehaviorPattern.confidence_score)).limit(5)
        pattern_result = await self.db.execute(pattern_stmt)
        pattern_tags = [row[0] for row in pattern_result.all()]

        frag_stmt = select(CognitiveFragment.tags).where(
            CognitiveFragment.user_id == user_id
        ).order_by(desc(CognitiveFragment.created_at)).limit(5)
        frag_result = await self.db.execute(frag_stmt)
        recent_tags: list[str] = []
        for row in frag_result.all():
            if isinstance(row[0], list):
                recent_tags.extend(row[0])

        return list(dict.fromkeys(pattern_tags + recent_tags))

    async def _collect_capabilities(self, user_id: UUID) -> dict[str, float]:
        stmt = select(
            func.avg(UserNodeStatus.mastery_score),
            func.avg(UserNodeStatus.bkt_mastery_prob)
        ).where(UserNodeStatus.user_id == user_id)
        result = await self.db.execute(stmt)
        avg_mastery, avg_bkt = result.one_or_none() or (0.0, 0.0)
        return {
            "mastery_avg": float(avg_mastery or 0.0),
            "bkt_mastery_avg": float(avg_bkt or 0.0)
        }

    async def _get_last_event_id(self, user_id: UUID) -> str | None:
        stmt = select(CognitiveFragment.source_event_id).where(
            CognitiveFragment.user_id == user_id,
            CognitiveFragment.source_event_id.isnot(None)
        ).order_by(desc(CognitiveFragment.created_at)).limit(1)
        result = await self.db.execute(stmt)
        row = result.first()
        return row[0] if row else None

    def _sign_audit_token(self, user_id: UUID, last_event_id: str | None) -> str:
        msg = f"{user_id}:{self.persona_version}:{last_event_id or 'none'}"
        digest = hmac.new(self.audit_secret.encode("utf-8"), msg.encode("utf-8"), hashlib.sha256).hexdigest()
        return digest

    async def _persist_snapshot(self, user_id: UUID, snapshot: dict[str, Any]) -> None:
        stmt = select(PersonaSnapshot).where(
            PersonaSnapshot.user_id == user_id
        ).order_by(desc(PersonaSnapshot.created_at)).limit(1)
        result = await self.db.execute(stmt)
        latest = result.scalar_one_or_none()

        if latest and latest.snapshot_data == snapshot:
            return

        record = PersonaSnapshot(
            user_id=user_id,
            persona_version=snapshot["persona_version"],
            audit_token=snapshot["audit_token"],
            source_event_id=snapshot.get("last_update_event_id"),
            snapshot_data=snapshot
        )
        self.db.add(record)
        await self.db.commit()


# Backward-compatible alias
PersonaService = ProfileSnapshotService
