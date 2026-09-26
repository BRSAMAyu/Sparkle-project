# rule-bj: exempt CARD-DUAL-WRITE 守卫消费模块（scripts/check_card_protocol_dual_write_consistency.py 导入）；生产面接线（API/ops 暴露）随 card_protocol 双写期收口落地——见 docs/engineering/KNOWN_CODE_DEBT_LEDGER.md
"""Card Protocol dual-write consistency validator (CARD-DUAL-WRITE).

ADR-0004 keeps the legacy plans/tasks tables and the card protocol in a
dual-write phase: PlanAdapter/TaskAdapter project every legacy row into a
Card and store the legacy id on card metadata ("legacy_plan_id" /
"legacy_task_id") for bidirectional lookup — "retire legacy only after
shadow validation". This module is the read side of that contract.

Drift-proofing: expected lifecycle states are computed with the adapters'
own mapping (``_plan_to_lifecycle`` / ``_TASK_STATUS_MAP``), imported from
``legacy_adapter`` — the definition of "consistent" cannot drift from what
the adapter actually writes.

Issue codes (severity):
- MISSING_PLAN_PROJECTION / MISSING_TASK_PROJECTION (critical):
  a live legacy row has no card projection.
- DUPLICATE_PLAN_PROJECTION / DUPLICATE_TASK_PROJECTION (critical):
  more than one card claims the same legacy id (the adapters look the
  projection up with ``scalar_one_or_none``, so duplicates break their
  write path too).
- PLAN_LIFECYCLE_DRIFT / TASK_LIFECYCLE_DRIFT (critical):
  the projected card lifecycle differs from the adapter mapping of the
  legacy row.
- ORPHAN_PLAN_CARD / ORPHAN_TASK_CARD (warning):
  a card claims a legacy id that no longer exists among live rows
  (deletion not propagated, or a fabricated id).

``limit`` restricts the per-row projection checks to the most recent
legacy rows (``created_at`` desc); orphan detection always runs against
the full legacy id sets. ``limit=None`` (guard default) checks everything.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.card_protocol import Card, CardLifecycleStatus, CardType
from app.models.plan import Plan
from app.models.task import Task
from app.services.card_protocol.legacy_adapter import (  # noqa: PLC2701 — 单一事实源：校验器必须与适配器共用同一映射
    _TASK_STATUS_MAP,
    _plan_to_lifecycle,
)

CRITICAL = "critical"
WARNING = "warning"


@dataclass(frozen=True)
class ConsistencyIssue:
    """One dual-write inconsistency found between legacy rows and cards."""

    severity: str
    code: str
    entity_type: str
    entity_id: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {
            "severity": self.severity,
            "code": self.code,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "message": self.message,
        }


def _legacy_id(metadata: dict | None, key: str) -> str | None:
    value = (metadata or {}).get(key)
    if value is None:
        return None
    return str(value)


class CardProtocolConsistencyValidator:
    """Validates legacy Plan/Task rows against Card Protocol projections."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def validate(self, limit: int | None = None) -> list[ConsistencyIssue]:
        plans = await self._load_plans(limit)
        tasks = await self._load_tasks(limit)
        plan_cards, task_cards = await self._load_projections()
        live_plan_ids = {str(p.id) for p in plans} if limit is None else await self._all_ids(Plan)
        live_task_ids = {str(t.id) for t in tasks} if limit is None else await self._all_ids(Task)

        issues: list[ConsistencyIssue] = []

        for plan in plans:
            key = str(plan.id)
            projections = plan_cards.get(key, [])
            if not projections:
                issues.append(
                    ConsistencyIssue(
                        severity=CRITICAL,
                        code="MISSING_PLAN_PROJECTION",
                        entity_type="plan",
                        entity_id=key,
                        message=f"active legacy plan {plan.name!r} has no PLAN card projection",
                    )
                )
                continue
            if len(projections) > 1:
                issues.append(
                    ConsistencyIssue(
                        severity=CRITICAL,
                        code="DUPLICATE_PLAN_PROJECTION",
                        entity_type="plan",
                        entity_id=key,
                        message=f"{len(projections)} PLAN cards claim legacy_plan_id {key}",
                    )
                )
                continue
            expected = _plan_to_lifecycle(plan)
            card = projections[0]
            if card.lifecycle_status != expected:
                issues.append(
                    ConsistencyIssue(
                        severity=CRITICAL,
                        code="PLAN_LIFECYCLE_DRIFT",
                        entity_type="plan",
                        entity_id=key,
                        message=(
                            f"plan {plan.name!r} maps to {expected.value}, "
                            f"card {card.id} is {card.lifecycle_status.value}"
                        ),
                    )
                )

        for task in tasks:
            key = str(task.id)
            projections = task_cards.get(key, [])
            if not projections:
                issues.append(
                    ConsistencyIssue(
                        severity=CRITICAL,
                        code="MISSING_TASK_PROJECTION",
                        entity_type="task",
                        entity_id=key,
                        message=f"live legacy task {task.title!r} has no TASK card projection",
                    )
                )
                continue
            if len(projections) > 1:
                issues.append(
                    ConsistencyIssue(
                        severity=CRITICAL,
                        code="DUPLICATE_TASK_PROJECTION",
                        entity_type="task",
                        entity_id=key,
                        message=f"{len(projections)} TASK cards claim legacy_task_id {key}",
                    )
                )
                continue
            expected = _TASK_STATUS_MAP.get(task.status, CardLifecycleStatus.ACTIVE)
            card = projections[0]
            if card.lifecycle_status != expected:
                issues.append(
                    ConsistencyIssue(
                        severity=CRITICAL,
                        code="TASK_LIFECYCLE_DRIFT",
                        entity_type="task",
                        entity_id=key,
                        message=(
                            f"task {task.title!r} ({task.status.value}) maps to {expected.value}, "
                            f"card {card.id} is {card.lifecycle_status.value}"
                        ),
                    )
                )

        for card_id, legacy_plan_id in sorted(
            (_legacy_plan_key(c) for cards in plan_cards.values() for c in cards),
            key=lambda item: item[0],
        ):
            if legacy_plan_id not in live_plan_ids:
                issues.append(
                    ConsistencyIssue(
                        severity=WARNING,
                        code="ORPHAN_PLAN_CARD",
                        entity_type="card",
                        entity_id=card_id,
                        message=f"PLAN card claims legacy_plan_id {legacy_plan_id} with no live plan row",
                    )
                )

        for card_id, legacy_task_id in sorted(
            (_legacy_task_key(c) for cards in task_cards.values() for c in cards),
            key=lambda item: item[0],
        ):
            if legacy_task_id not in live_task_ids:
                issues.append(
                    ConsistencyIssue(
                        severity=WARNING,
                        code="ORPHAN_TASK_CARD",
                        entity_type="card",
                        entity_id=card_id,
                        message=f"TASK card claims legacy_task_id {legacy_task_id} with no live task row",
                    )
                )

        return issues

    async def _load_plans(self, limit: int | None) -> list[Plan]:
        stmt = select(Plan).where(Plan.not_deleted_filter()).order_by(Plan.created_at.desc(), Plan.id)
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def _load_tasks(self, limit: int | None) -> list[Task]:
        stmt = select(Task).where(Task.not_deleted_filter()).order_by(Task.created_at.desc(), Task.id)
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def _load_projections(self) -> tuple[dict[str, list[Card]], dict[str, list[Card]]]:
        plan_cards: dict[str, list[Card]] = {}
        task_cards: dict[str, list[Card]] = {}

        stmt = (
            select(Card)
            .where(Card.card_type.in_([CardType.PLAN, CardType.TASK]), Card.not_deleted_filter())
            .order_by(Card.created_at, Card.id)
        )
        result = await self.db.execute(stmt)
        for card in result.scalars().all():
            legacy_plan_id = _legacy_id(card.metadata_, "legacy_plan_id")
            legacy_task_id = _legacy_id(card.metadata_, "legacy_task_id")
            if card.card_type == CardType.PLAN and legacy_plan_id:
                plan_cards.setdefault(legacy_plan_id, []).append(card)
            elif card.card_type == CardType.TASK and legacy_task_id:
                task_cards.setdefault(legacy_task_id, []).append(card)
        return plan_cards, task_cards

    async def _all_ids(self, model: type[Plan] | type[Task]) -> set[str]:
        stmt = select(model.id).where(model.not_deleted_filter())
        result = await self.db.execute(stmt)
        return {str(row[0]) for row in result.all()}


def _legacy_plan_key(card: Card) -> tuple[UUID | str, str]:
    return card.id, _legacy_id(card.metadata_, "legacy_plan_id") or ""


def _legacy_task_key(card: Card) -> tuple[UUID | str, str]:
    return card.id, _legacy_id(card.metadata_, "legacy_task_id") or ""
