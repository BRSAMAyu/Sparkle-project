from __future__ import annotations

from datetime import datetime, timedelta, UTC
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.memory_rank_policy import MemoryRankPolicy

WEIGHT_KEYS = ("evidence", "freshness", "correction")


def _default_weights() -> dict[str, float]:
    return {
        "evidence": settings.MEMORY_RANK_DEFAULT_EVIDENCE,
        "freshness": settings.MEMORY_RANK_DEFAULT_FRESHNESS,
        "correction": settings.MEMORY_RANK_DEFAULT_CORRECTION,
    }


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class MemoryRankPolicyService:
    _cache: dict[str, tuple[datetime, dict[str, float]]] = {}
    _cache_ttl = timedelta(seconds=60)

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def _cache_key(self, intent: str, user_id: UUID) -> str:
        return f"{intent}:{user_id}"

    def _normalize_weights(self, weights: dict[str, float]) -> dict[str, float]:
        defaults = _default_weights()
        cleaned = {}
        for key in WEIGHT_KEYS:
            value = weights.get(key, defaults[key])
            value = max(0.0, min(1.0, float(value)))
            cleaned[key] = value
        total = sum(cleaned.values())
        if total <= 0:
            return defaults
        return {key: cleaned[key] / total for key in WEIGHT_KEYS}

    async def _fetch_policy(
        self,
        scope_type: str,
        scope_key: str | None,
        include_deleted: bool = False,
    ) -> MemoryRankPolicy | None:
        stmt = select(MemoryRankPolicy).where(
            MemoryRankPolicy.scope_type == scope_type,
            MemoryRankPolicy.scope_key == scope_key,
        )
        if not include_deleted:
            stmt = stmt.where(MemoryRankPolicy.deleted_at.is_(None))
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_policy(self, intent: str, user_id: UUID) -> dict[str, float]:
        cache_key = self._cache_key(intent, user_id)
        cached = self._cache.get(cache_key)
        if cached and cached[0] > _utcnow():
            return cached[1].copy()

        resolved = _default_weights()
        global_policy = await self._fetch_policy("global", None)
        if global_policy and isinstance(global_policy.weights, dict):
            resolved.update({k: v for k, v in global_policy.weights.items() if k in WEIGHT_KEYS})

        intent_policy = await self._fetch_policy("intent", intent)
        if intent_policy and isinstance(intent_policy.weights, dict):
            resolved.update({k: v for k, v in intent_policy.weights.items() if k in WEIGHT_KEYS})

        user_policy = await self._fetch_policy("user", str(user_id))
        if user_policy and isinstance(user_policy.weights, dict):
            resolved.update({k: v for k, v in user_policy.weights.items() if k in WEIGHT_KEYS})

        normalized = self._normalize_weights(resolved)
        self._cache[cache_key] = (_utcnow() + self._cache_ttl, normalized.copy())
        return normalized

    async def list_policies(self) -> list[MemoryRankPolicy]:
        result = await self.db.execute(
            select(MemoryRankPolicy).where(MemoryRankPolicy.deleted_at.is_(None)).order_by(
                MemoryRankPolicy.created_at.desc()
            )
        )
        return list(result.scalars().all())

    async def upsert_policy(
        self,
        scope_type: str,
        scope_key: str | None,
        weights: dict[str, float],
    ) -> MemoryRankPolicy:
        if scope_type not in {"global", "intent", "user"}:
            raise ValueError("invalid scope_type")
        if scope_type == "global":
            scope_key = None
        if scope_type in {"intent", "user"} and not scope_key:
            raise ValueError("scope_key required")

        normalized = self._normalize_weights(weights)
        existing = await self._fetch_policy(scope_type, scope_key, include_deleted=True)
        if existing:
            existing.weights = normalized
            existing.deleted_at = None
            await self.db.commit()
            await self.db.refresh(existing)
            self._cache.clear()
            return existing

        record = MemoryRankPolicy(scope_type=scope_type, scope_key=scope_key, weights=normalized)
        self.db.add(record)
        await self.db.commit()
        await self.db.refresh(record)
        self._cache.clear()
        return record

    async def delete_policy(self, policy_id: UUID) -> bool:
        result = await self.db.execute(
            select(MemoryRankPolicy).where(
                MemoryRankPolicy.id == policy_id,
                MemoryRankPolicy.deleted_at.is_(None),
            )
        )
        record = result.scalar_one_or_none()
        if record is None:
            return False
        record.deleted_at = _utcnow()
        await self.db.commit()
        self._cache.clear()
        return True
