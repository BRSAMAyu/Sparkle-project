import hashlib
import hmac
import json
import os
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.galaxy import UserNodeStatus
from app.models.cognitive import BehaviorPattern, CognitiveFragment
from app.models.compliance import PersonaSnapshot


class PersonaService:
    """
    用户画像快照服务 (PersonaTool)
    """

    def __init__(self, db: AsyncSession, redis_client=None):
        self.db = db
        self.redis = redis_client
        self.persona_version = os.getenv("PERSONA_VERSION", "v3.1")
        self.audit_secret = os.getenv("PERSONA_AUDIT_SECRET", "persona-audit-secret")

    async def get_snapshot(self, user_id: UUID, purpose: str) -> Dict[str, Any]:
        cache_key = f"persona:snapshot:{user_id}:{purpose}"
        if self.redis:
            cached = await self.redis.get(cache_key)
            if cached:
                return json.loads(cached)

        snapshot = await self._build_snapshot(user_id, purpose)
        if self.redis:
            await self.redis.setex(cache_key, 300, json.dumps(snapshot, ensure_ascii=False))

        await self._persist_snapshot(user_id, snapshot)
        return snapshot

    async def _build_snapshot(self, user_id: UUID, purpose: str) -> Dict[str, Any]:
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

    async def _collect_tags(self, user_id: UUID) -> List[str]:
        pattern_stmt = select(BehaviorPattern.pattern_name).where(
            BehaviorPattern.user_id == user_id,
            BehaviorPattern.is_archived == False
        ).order_by(desc(BehaviorPattern.confidence_score)).limit(5)
        pattern_result = await self.db.execute(pattern_stmt)
        pattern_tags = [row[0] for row in pattern_result.all()]

        frag_stmt = select(CognitiveFragment.tags).where(
            CognitiveFragment.user_id == user_id
        ).order_by(desc(CognitiveFragment.created_at)).limit(5)
        frag_result = await self.db.execute(frag_stmt)
        recent_tags: List[str] = []
        for row in frag_result.all():
            if isinstance(row[0], list):
                recent_tags.extend(row[0])

        return list(dict.fromkeys(pattern_tags + recent_tags))

    async def _collect_capabilities(self, user_id: UUID) -> Dict[str, float]:
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

    async def _get_last_event_id(self, user_id: UUID) -> Optional[str]:
        stmt = select(CognitiveFragment.source_event_id).where(
            CognitiveFragment.user_id == user_id,
            CognitiveFragment.source_event_id.isnot(None)
        ).order_by(desc(CognitiveFragment.created_at)).limit(1)
        result = await self.db.execute(stmt)
        row = result.first()
        return row[0] if row else None

    def _sign_audit_token(self, user_id: UUID, last_event_id: Optional[str]) -> str:
        msg = f"{user_id}:{self.persona_version}:{last_event_id or 'none'}"
        digest = hmac.new(self.audit_secret.encode("utf-8"), msg.encode("utf-8"), hashlib.sha256).hexdigest()
        return digest

    async def _persist_snapshot(self, user_id: UUID, snapshot: Dict[str, Any]) -> None:
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
