from __future__ import annotations

from datetime import date, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.card_protocol import Card, CardType
from app.models.task import TaskType
from app.schemas.task import TaskCreate
from app.services.card_protocol.card_operations_service import CardOperationsService
from app.services.card_protocol.phase_service import PhaseService
from app.services.card_protocol.planning_memory_service import PlanningMemoryService
from app.services.card_protocol.temporal_engine import RecurrenceRule, TemporalEngine
from app.services.task_service import TaskService


class PhaseDesignService:
    """Design concrete short-horizon tasks for one phase using planning memory."""

    def __init__(self, db: AsyncSession, event_bus=None):
        self.db = db
        self.event_bus = event_bus
        self.phase_service = PhaseService(db, event_bus)
        self.memory_service = PlanningMemoryService(db, event_bus)
        self.card_operations = CardOperationsService(db, event_bus)
        self.temporal_engine = TemporalEngine(db, event_bus)

    async def design_phase_tasks(
        self,
        *,
        phase_card_id: UUID,
        plan_card_id: UUID,
        user_id: UUID,
    ) -> list[dict[str, Any]]:
        phase_card = await self.phase_service._get_owned_phase(phase_card_id, user_id)
        plan_card = await self.phase_service._get_owned_plan(plan_card_id, user_id)
        context = await self.memory_service.load_planning_context(
            plan_card_id=plan_card.id,
            user_id=user_id,
        )
        phase_metadata = dict(phase_card.metadata_ or {})
        objective = phase_metadata.get("objective") or phase_metadata.get("title") or "Current phase"
        compass = context.global_compass or {}
        rolling = context.rolling_context or {}

        task_specs = self._build_task_specs(
            objective=objective,
            compass=compass,
            rolling_context=rolling,
            phase_metadata=phase_metadata,
        )

        created: list[dict[str, Any]] = []
        legacy_plan_id = (plan_card.metadata_ or {}).get("legacy_plan_id")
        if not legacy_plan_id:
            raise ValueError("Legacy plan projection is required for phase task design")
        start_date = self._coerce_date(phase_metadata.get("estimated_start")) or date.today()
        end_date = self._coerce_date(phase_metadata.get("estimated_end")) or (start_date + timedelta(days=20))
        for spec in task_specs:
            task = await TaskService.create(
                db=self.db,
                obj_in=TaskCreate(
                    title=spec["title"],
                    type=spec["task_type"],
                    plan_id=UUID(str(legacy_plan_id)),
                    tags=spec["tags"],
                    estimated_minutes=spec["estimated_minutes"],
                    difficulty=spec["difficulty"],
                    energy_cost=spec["energy_cost"],
                    guide_content=spec["guide_content"],
                    due_date=end_date,
                ),
                user_id=user_id,
            )
            matches = await self.card_operations.search_cards(
                user_id=user_id,
                card_type=CardType.TASK,
                legacy_task_id=task.id,
                limit=1,
            )
            task_card = matches[0] if matches else None
            if task_card is None:
                raise ValueError("Task card projection unavailable during phase design")
            await self.card_operations.move_card(
                card_id=task_card.id,
                new_parent_card_id=phase_card.id,
                user_id=user_id,
            )
            await self.temporal_engine.set_task_recurrence(
                task_card_id=task_card.id,
                rule=spec["recurrence_rule"],
                user_id=user_id,
            )
            await self.temporal_engine.generate_occurrences(
                task_card_id=task_card.id,
                phase_card_id=phase_card.id,
                from_date=start_date,
                to_date=end_date,
            )
            created.append(
                {
                    "task_id": str(task.id),
                    "task_card_id": str(task_card.id),
                    "title": task.title,
                    "estimated_minutes": task.estimated_minutes,
                    "difficulty": task.difficulty,
                    "recurrence_rule": self.temporal_engine._rule_to_payload(spec["recurrence_rule"]),
                }
            )

        await self._sync_phase_design_metadata(phase_card, task_specs, created)
        return created

    def _build_task_specs(
        self,
        *,
        objective: str,
        compass: dict[str, Any],
        rolling_context: dict[str, Any],
        phase_metadata: dict[str, Any],
    ) -> list[dict[str, Any]]:
        values = list(compass.get("values") or [])
        base_minutes = int(compass.get("hard_constraints", {}).get("max_session_minutes") or 60)
        completion_rate = float(rolling_context.get("completion_rate") or 0.0)
        deferral_rate = float(rolling_context.get("deferral_rate") or 0.0)
        if deferral_rate >= 0.35:
            base_minutes = min(base_minutes, 35)
        elif completion_rate >= 0.7:
            base_minutes = min(90, max(base_minutes, 50))

        normalized_objective = objective.strip() or "current objective"
        recurring_days = [1, 3, 5] if deferral_rate < 0.35 else [2, 4]
        return [
            {
                "title": f"{normalized_objective}: Core session",
                "task_type": TaskType.LEARNING,
                "tags": ["phase-e", "core-session", *values[:2]],
                "estimated_minutes": base_minutes,
                "difficulty": 2 if deferral_rate >= 0.35 else 3,
                "energy_cost": 2,
                "guide_content": f"Focus on the main objective of this phase: {normalized_objective}.",
                "recurrence_rule": RecurrenceRule(
                    pattern="weekly",
                    days_of_week=recurring_days,
                    flexible=True,
                    max_deferrals=3,
                ),
            },
            {
                "title": f"{normalized_objective}: Deliberate practice",
                "task_type": TaskType.TRAINING,
                "tags": ["phase-e", "practice", *values[:2]],
                "estimated_minutes": max(20, base_minutes - 10),
                "difficulty": 3 if completion_rate >= 0.5 else 2,
                "energy_cost": 2,
                "guide_content": "Convert the current phase objective into one small measurable practice loop.",
                "recurrence_rule": RecurrenceRule(
                    pattern="weekly",
                    days_of_week=[6],
                    flexible=True,
                    max_deferrals=2,
                ),
            },
            {
                "title": f"{normalized_objective}: Reflection and calibration",
                "task_type": TaskType.REFLECTION,
                "tags": ["phase-e", "reflection"],
                "estimated_minutes": 15,
                "difficulty": 1,
                "energy_cost": 1,
                "guide_content": "Record what felt easier, harder, and what should be adjusted before the next cycle.",
                "recurrence_rule": RecurrenceRule(
                    pattern="weekly",
                    days_of_week=[7],
                    flexible=True,
                    max_deferrals=1,
                ),
            },
        ]

    async def _sync_phase_design_metadata(
        self,
        phase_card: Card,
        specs: list[dict[str, Any]],
        created: list[dict[str, Any]],
    ) -> None:
        metadata = dict(phase_card.metadata_ or {})
        metadata["phase_design"] = {
            "generated_at": date.today().isoformat(),
            "task_blueprint_count": len(specs),
            "created_task_ids": [item["task_id"] for item in created],
            "created_task_card_ids": [item["task_card_id"] for item in created],
        }
        phase_card.metadata_ = metadata
        phase_card.version += 1
        await self.db.flush()

    def _coerce_date(self, value: Any) -> date | None:
        if value is None:
            return None
        if isinstance(value, date):
            return value
        try:
            return date.fromisoformat(str(value))
        except ValueError:
            return None
