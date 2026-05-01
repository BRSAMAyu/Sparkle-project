"""Durable repository and lifecycle helpers for DistilledStrategy."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.aurora.schemas import DistilledStrategy, DistilledStrategyLifecycle, Shareability
from app.db.session import AsyncSessionLocal
from app.models.distilled_strategy_cache import DistilledStrategyCacheEntry


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


_ALLOWED_TRANSITIONS: dict[DistilledStrategyLifecycle, set[DistilledStrategyLifecycle]] = {
    DistilledStrategyLifecycle.DISTILLED: {
        DistilledStrategyLifecycle.USER_REVIEWED,
        DistilledStrategyLifecycle.RETIRED,
    },
    DistilledStrategyLifecycle.USER_REVIEWED: {
        DistilledStrategyLifecycle.USER_PRIVATE,
        DistilledStrategyLifecycle.COMMUNITY_SHARED,
        DistilledStrategyLifecycle.RETIRED,
    },
    DistilledStrategyLifecycle.USER_PRIVATE: {
        DistilledStrategyLifecycle.COMMUNITY_SHARED,
        DistilledStrategyLifecycle.RETIRED,
    },
    DistilledStrategyLifecycle.COMMUNITY_SHARED: {
        DistilledStrategyLifecycle.RETIRED,
    },
    DistilledStrategyLifecycle.RETIRED: set(),
}


class StrategyLifecycleError(ValueError):
    """Raised when a lifecycle transition is not allowed."""


@dataclass(frozen=True)
class StrategyQuery:
    """Filter options for querying strategy records."""

    statuses: tuple[DistilledStrategyLifecycle, ...] = ()
    shareability: tuple[Shareability, ...] = ()
    source_trajectory_type: str | None = None
    search_text: str | None = None


def _payload_from_strategy(strategy: DistilledStrategy) -> dict[str, Any]:
    return strategy.model_dump(mode="json")


def _strategy_from_entry(entry: DistilledStrategyCacheEntry) -> DistilledStrategy:
    return DistilledStrategy.model_validate(entry.payload)


class DistilledStrategyStore:
    """DB-backed L2 inference cache for continuous-learning strategy records."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession]
        | Callable[[], Awaitable[AsyncSession]]
        | Callable[[], AsyncSession]
        | None = None,
    ) -> None:
        self._session_factory = session_factory or AsyncSessionLocal

    def _open_session(self):
        session = self._session_factory()
        return session

    async def create(self, strategy: DistilledStrategy) -> DistilledStrategy:
        async with self._open_session() as session:
            existing = await session.get(DistilledStrategyCacheEntry, strategy.id)
            if existing is not None:
                raise ValueError(f"strategy {strategy.id} already exists")
            entry = DistilledStrategyCacheEntry(
                id=strategy.id,
                title=strategy.title,
                description=strategy.description,
                applicability_scope=strategy.applicability_scope,
                status=strategy.status.value,
                shareability=strategy.shareability.value,
                source_trajectory_type=strategy.source_trajectory_type,
                payload=_payload_from_strategy(strategy),
                created_at=strategy.created_at,
                updated_at=strategy.updated_at,
            )
            session.add(entry)
            await session.commit()
            return strategy

    async def upsert(self, strategy: DistilledStrategy) -> DistilledStrategy:
        async with self._open_session() as session:
            entry = await session.get(DistilledStrategyCacheEntry, strategy.id)
            if entry is None:
                entry = DistilledStrategyCacheEntry(id=strategy.id)
                session.add(entry)
            entry.title = strategy.title
            entry.description = strategy.description
            entry.applicability_scope = strategy.applicability_scope
            entry.status = strategy.status.value
            entry.shareability = strategy.shareability.value
            entry.source_trajectory_type = strategy.source_trajectory_type
            entry.payload = _payload_from_strategy(strategy)
            entry.created_at = strategy.created_at
            entry.updated_at = strategy.updated_at
            await session.commit()
            return strategy

    async def get(self, strategy_id: UUID) -> DistilledStrategy:
        async with self._open_session() as session:
            entry = await session.get(DistilledStrategyCacheEntry, strategy_id)
            if entry is None:
                raise KeyError(strategy_id)
            return _strategy_from_entry(entry)

    async def list(self, query: StrategyQuery | None = None) -> list[DistilledStrategy]:
        query = query or StrategyQuery()
        async with self._open_session() as session:
            statement = select(DistilledStrategyCacheEntry)
            if query.statuses:
                statement = statement.where(
                    DistilledStrategyCacheEntry.status.in_([status.value for status in query.statuses])
                )
            if query.shareability:
                statement = statement.where(
                    DistilledStrategyCacheEntry.shareability.in_(
                        [shareability.value for shareability in query.shareability]
                    )
                )
            if query.source_trajectory_type:
                statement = statement.where(
                    DistilledStrategyCacheEntry.source_trajectory_type == query.source_trajectory_type
                )
            if query.search_text:
                needle = f"%{query.search_text.casefold()}%"
                statement = statement.where(
                    or_(
                        DistilledStrategyCacheEntry.title.ilike(needle),
                        DistilledStrategyCacheEntry.description.ilike(needle),
                        DistilledStrategyCacheEntry.applicability_scope.ilike(needle),
                    )
                )
            statement = statement.order_by(
                DistilledStrategyCacheEntry.updated_at,
                DistilledStrategyCacheEntry.created_at,
                DistilledStrategyCacheEntry.id,
            )
            result = await session.execute(statement)
            return [_strategy_from_entry(entry) for entry in result.scalars().all()]

    async def transition(
        self,
        strategy_id: UUID,
        new_status: DistilledStrategyLifecycle,
        *,
        at: datetime | None = None,
        user_authorization: bool | None = None,
    ) -> DistilledStrategy:
        current = await self.get(strategy_id)
        if current.status == new_status:
            return current
        allowed = _ALLOWED_TRANSITIONS[current.status]
        if new_status not in allowed:
            raise StrategyLifecycleError(f"{current.status.value} -> {new_status.value} is not allowed")
        updated = current.model_copy(
            update={
                "status": new_status,
                "updated_at": at or _utcnow(),
                "user_authorization": current.user_authorization if user_authorization is None else user_authorization,
            }
        )
        await self.upsert(updated)
        return updated

    async def record_application(
        self,
        strategy_id: UUID,
        *,
        satisfaction: float | None = None,
        at: datetime | None = None,
    ) -> DistilledStrategy:
        current = await self.get(strategy_id)
        updated = current.model_copy(
            update={
                "application_count": current.application_count + 1,
                "satisfaction_after_application": satisfaction,
                "updated_at": at or _utcnow(),
            }
        )
        await self.upsert(updated)
        return updated

    async def update_fields(self, strategy_id: UUID, **updates: Any) -> DistilledStrategy:
        current = await self.get(strategy_id)
        merged_updates = dict(updates)
        merged_updates.setdefault("updated_at", _utcnow())
        updated = current.model_copy(update=merged_updates)
        await self.upsert(updated)
        return updated
