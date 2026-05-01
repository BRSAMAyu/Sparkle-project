# rule-at: orphan-by-design CardProtocol v2 validation utility, consumed by future migration scripts
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.card_protocol import Card, CardEdge, CardType, EdgeType
from app.models.plan import Plan
from app.models.task import Task


@dataclass(frozen=True)
class CardProtocolConsistencyIssue:
    severity: str
    code: str
    entity_type: str
    entity_id: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


class CardProtocolConsistencyValidator:
    """Validates dual-write consistency between legacy Plan/Task rows and cards."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def validate(self, *, limit: int | None = None) -> list[CardProtocolConsistencyIssue]:
        plans = await self._load_plans(limit=limit)
        tasks = await self._load_tasks(limit=limit)
        cards = await self._load_cards()
        edges = await self._load_active_contains_edges()

        plan_cards_by_legacy = self._cards_by_metadata(cards, CardType.PLAN, "legacy_plan_id")
        task_cards_by_legacy = self._cards_by_metadata(cards, CardType.TASK, "legacy_task_id")
        issues: list[CardProtocolConsistencyIssue] = []

        issues.extend(self._validate_duplicate_projection(plan_cards_by_legacy, entity_type="plan"))
        issues.extend(self._validate_duplicate_projection(task_cards_by_legacy, entity_type="task"))

        plan_cards = {legacy_id: card_list[0] for legacy_id, card_list in plan_cards_by_legacy.items() if card_list}
        task_cards = {legacy_id: card_list[0] for legacy_id, card_list in task_cards_by_legacy.items() if card_list}

        legacy_plan_ids = {str(plan.id) for plan in plans}
        legacy_task_ids = {str(task.id) for task in tasks}
        for legacy_id, card in plan_cards.items():
            if legacy_id not in legacy_plan_ids:
                issues.append(
                    self._issue(
                        "warning",
                        "orphan_plan_card",
                        "card",
                        card.id,
                        f"PLAN card points to missing legacy plan {legacy_id}",
                    )
                )
        for legacy_id, card in task_cards.items():
            if legacy_id not in legacy_task_ids:
                issues.append(
                    self._issue(
                        "warning",
                        "orphan_task_card",
                        "card",
                        card.id,
                        f"TASK card points to missing legacy task {legacy_id}",
                    )
                )

        for plan in plans:
            if str(plan.id) not in plan_cards:
                issues.append(
                    self._issue(
                        "critical",
                        "missing_plan_card",
                        "plan",
                        plan.id,
                        "Legacy plan has no PLAN card projection",
                    )
                )

        for task in tasks:
            task_card = task_cards.get(str(task.id))
            if not task_card:
                issues.append(
                    self._issue(
                        "critical",
                        "missing_task_card",
                        "task",
                        task.id,
                        "Legacy task has no TASK card projection",
                    )
                )
                continue

            card_legacy_plan_id = str((task_card.metadata_ or {}).get("legacy_plan_id") or "")
            task_legacy_plan_id = str(task.plan_id) if task.plan_id else ""
            if card_legacy_plan_id != task_legacy_plan_id:
                issues.append(
                    self._issue(
                        "critical",
                        "task_plan_mismatch",
                        "task",
                        task.id,
                        "TASK card legacy_plan_id does not match legacy task.plan_id",
                    )
                )

            if not task.plan_id:
                continue
            plan_card = plan_cards.get(str(task.plan_id))
            if not plan_card:
                continue
            phase_id = self._resolve_current_phase_id(plan_card, cards, edges)
            if not phase_id:
                issues.append(
                    self._issue(
                        "critical",
                        "missing_plan_phase",
                        "plan",
                        task.plan_id,
                        "PLAN card has no current or contained PHASE card",
                    )
                )
                continue
            if (phase_id, task_card.id) not in edges:
                issues.append(
                    self._issue(
                        "critical",
                        "missing_task_contains_edge",
                        "task",
                        task.id,
                        "Task card is not contained by the plan current phase",
                    )
                )

        return issues

    async def _load_plans(self, *, limit: int | None) -> list[Plan]:
        stmt = select(Plan).where(Plan.not_deleted_filter()).order_by(Plan.created_at.desc())
        if limit:
            stmt = stmt.limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def _load_tasks(self, *, limit: int | None) -> list[Task]:
        stmt = select(Task).where(Task.not_deleted_filter()).order_by(Task.created_at.desc())
        if limit:
            stmt = stmt.limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def _load_cards(self) -> list[Card]:
        result = await self.db.execute(select(Card).where(Card.not_deleted_filter()))
        return list(result.scalars().all())

    async def _load_active_contains_edges(self) -> set[tuple[UUID, UUID]]:
        result = await self.db.execute(
            select(CardEdge).where(
                CardEdge.edge_type == EdgeType.CONTAINS,
                CardEdge.active.is_(True),
            )
        )
        return {(edge.from_card_id, edge.to_card_id) for edge in result.scalars().all()}

    @staticmethod
    def _cards_by_metadata(cards: list[Card], card_type: CardType, key: str) -> dict[str, list[Card]]:
        grouped: dict[str, list[Card]] = {}
        for card in cards:
            if card.card_type != card_type:
                continue
            value = str((card.metadata_ or {}).get(key) or "").strip()
            if not value:
                continue
            grouped.setdefault(value, []).append(card)
        return grouped

    def _validate_duplicate_projection(
        self,
        grouped: dict[str, list[Card]],
        *,
        entity_type: str,
    ) -> list[CardProtocolConsistencyIssue]:
        issues: list[CardProtocolConsistencyIssue] = []
        for legacy_id, cards in grouped.items():
            if len(cards) <= 1:
                continue
            issues.append(
                CardProtocolConsistencyIssue(
                    severity="critical",
                    code=f"duplicate_{entity_type}_card",
                    entity_type=entity_type,
                    entity_id=legacy_id,
                    message=f"{len(cards)} cards project the same legacy {entity_type}",
                )
            )
        return issues

    @staticmethod
    def _resolve_current_phase_id(
        plan_card: Card,
        cards: list[Card],
        edges: set[tuple[UUID, UUID]],
    ) -> UUID | None:
        raw_phase_id = (plan_card.metadata_ or {}).get("current_phase_card_id")
        if raw_phase_id:
            try:
                return UUID(str(raw_phase_id))
            except ValueError:
                pass
        cards_by_id = {card.id: card for card in cards}
        for from_card_id, to_card_id in edges:
            if from_card_id != plan_card.id:
                continue
            child = cards_by_id.get(to_card_id)
            if child and child.card_type == CardType.PHASE:
                return child.id
        return None

    @staticmethod
    def _issue(
        severity: str,
        code: str,
        entity_type: str,
        entity_id: Any,
        message: str,
    ) -> CardProtocolConsistencyIssue:
        return CardProtocolConsistencyIssue(
            severity=severity,
            code=code,
            entity_type=entity_type,
            entity_id=str(entity_id),
            message=message,
        )
