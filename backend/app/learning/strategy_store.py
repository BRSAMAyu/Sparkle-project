"""Sidecar repository and lifecycle helpers for DistilledStrategy."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from app.aurora.schemas import DistilledStrategy, DistilledStrategyLifecycle, Shareability


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


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


class InMemoryDistilledStrategyStore:
    """Simple in-memory repository for DistilledStrategy records."""

    def __init__(self, initial: Iterable[DistilledStrategy] | None = None) -> None:
        self._records: dict[UUID, DistilledStrategy] = {}
        if initial:
            for strategy in initial:
                self.create(strategy)

    def create(self, strategy: DistilledStrategy) -> DistilledStrategy:
        if strategy.id in self._records:
            raise ValueError(f"strategy {strategy.id} already exists")
        self._records[strategy.id] = strategy
        return strategy

    def upsert(self, strategy: DistilledStrategy) -> DistilledStrategy:
        self._records[strategy.id] = strategy
        return strategy

    def get(self, strategy_id: UUID) -> DistilledStrategy:
        return self._records[strategy_id]

    def list(self, query: StrategyQuery | None = None) -> list[DistilledStrategy]:
        query = query or StrategyQuery()
        results = list(self._records.values())
        if query.statuses:
            allowed = set(query.statuses)
            results = [item for item in results if item.status in allowed]
        if query.shareability:
            allowed_shareability = set(query.shareability)
            results = [item for item in results if item.shareability in allowed_shareability]
        if query.source_trajectory_type:
            results = [item for item in results if item.source_trajectory_type == query.source_trajectory_type]
        if query.search_text:
            needle = query.search_text.casefold()
            results = [
                item
                for item in results
                if needle in item.title.casefold()
                or needle in item.description.casefold()
                or needle in item.applicability_scope.casefold()
            ]
        return sorted(results, key=lambda item: (item.updated_at, item.created_at, str(item.id)))

    def transition(
        self,
        strategy_id: UUID,
        new_status: DistilledStrategyLifecycle,
        *,
        at: datetime | None = None,
        user_authorization: bool | None = None,
    ) -> DistilledStrategy:
        current = self.get(strategy_id)
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
        self._records[strategy_id] = updated
        return updated

    def record_application(
        self,
        strategy_id: UUID,
        *,
        satisfaction: float | None = None,
        at: datetime | None = None,
    ) -> DistilledStrategy:
        current = self.get(strategy_id)
        updated = current.model_copy(
            update={
                "application_count": current.application_count + 1,
                "satisfaction_after_application": satisfaction,
                "updated_at": at or _utcnow(),
            }
        )
        self._records[strategy_id] = updated
        return updated

    def update_fields(self, strategy_id: UUID, **updates: Any) -> DistilledStrategy:
        current = self.get(strategy_id)
        merged_updates = dict(updates)
        merged_updates.setdefault("updated_at", _utcnow())
        updated = current.model_copy(update=merged_updates)
        self._records[strategy_id] = updated
        return updated
