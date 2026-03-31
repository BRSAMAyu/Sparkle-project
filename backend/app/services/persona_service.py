from __future__ import annotations
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
        force_refresh: bool = False,
    ) -> dict[str, Any]:
        cache_key = f"persona:snapshot:{user_id}:{purpose}"
        if self.redis and not force_refresh:
            cached = await self.redis.get(cache_key)
            if cached:
                return json.loads(cached)

        snapshot = await self._build_snapshot(user_id, purpose, profile_context=profile_context)
        snapshot["audit_token"] = self._sign_snapshot_payload(user_id, snapshot)
        if self.redis:
            await self.redis.setex(cache_key, 300, json.dumps(snapshot, ensure_ascii=False))

        await self._persist_snapshot(user_id, snapshot)
        return snapshot

    async def get_snapshot(self, user_id: UUID, purpose: str) -> dict[str, Any]:
        """Return the latest verified snapshot for a purpose, rebuilding if needed."""
        record = await self._load_latest_snapshot_record(user_id, purpose)
        if record is None:
            return await self.build_profile_snapshot(user_id, purpose, force_refresh=True)

        snapshot = dict(record.snapshot_data or {})
        integrity = self.verify_integrity(user_id, snapshot)
        if integrity == "valid":
            return snapshot
        if integrity == "legacy":
            return await self.build_profile_snapshot(user_id, purpose, force_refresh=True)

        return await self.build_profile_snapshot(user_id, purpose, force_refresh=True)

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

        return {
            "persona_version": self.persona_version,
            "purpose": purpose,
            "tags": tags,
            "capabilities": capabilities,
            "last_update_event_id": last_update_event_id
        }

    async def _collect_tags(self, user_id: UUID) -> list[str]:
        pattern_stmt = select(BehaviorPattern.pattern_name).where(
            BehaviorPattern.user_id == user_id,
            BehaviorPattern.is_archived.is_(False),
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

    def _sign_snapshot_payload(self, user_id: UUID, snapshot: dict[str, Any]) -> str:
        payload = self._canonicalize_snapshot(user_id, snapshot)
        digest = hmac.new(self.audit_secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
        return digest

    def _sign_legacy_audit_token(self, user_id: UUID, last_event_id: str | None) -> str:
        msg = f"{user_id}:{self.persona_version}:{last_event_id or 'none'}"
        digest = hmac.new(self.audit_secret.encode("utf-8"), msg.encode("utf-8"), hashlib.sha256).hexdigest()
        return digest

    def _canonicalize_snapshot(self, user_id: UUID, snapshot: dict[str, Any]) -> str:
        payload = {
            key: value
            for key, value in snapshot.items()
            if key != "audit_token"
        }
        envelope = {
            "user_id": str(user_id),
            "snapshot": payload,
        }
        return json.dumps(envelope, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    def verify_integrity(self, user_id: UUID, snapshot: dict[str, Any]) -> str:
        token = str(snapshot.get("audit_token") or "")
        if not token:
            return "invalid"

        expected = self._sign_snapshot_payload(user_id, snapshot)
        if hmac.compare_digest(token, expected):
            return "valid"

        legacy_expected = self._sign_legacy_audit_token(user_id, snapshot.get("last_update_event_id"))
        if hmac.compare_digest(token, legacy_expected):
            return "legacy"

        return "invalid"

    async def _load_latest_snapshot_record(self, user_id: UUID, purpose: str) -> PersonaSnapshot | None:
        stmt = select(PersonaSnapshot).where(
            PersonaSnapshot.user_id == user_id
        ).order_by(desc(PersonaSnapshot.created_at)).limit(20)
        result = await self.db.execute(stmt)
        for record in result.scalars().all():
            snapshot = record.snapshot_data or {}
            if isinstance(snapshot, dict) and snapshot.get("purpose") == purpose:
                return record
        return None

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
