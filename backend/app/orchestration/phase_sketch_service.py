from __future__ import annotations

from datetime import date, timedelta
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.card_protocol import ArtifactStatus, ArtifactType, Card, CardCreatedBy, CardType, PlanningArtifact
from app.services.card_protocol.phase_service import PhaseService
from app.services.card_protocol.strategy_map_manager import StrategyMapManager
from app.services.planning_artifact_service import PlanningArtifactService


class PhaseSketchService:
    """Generate and materialize reviewable phase architecture from compass + dossier."""

    def __init__(self, db: AsyncSession, event_bus=None):
        self.db = db
        self.event_bus = event_bus
        self.artifact_service = PlanningArtifactService(db, event_bus)
        self.phase_service = PhaseService(db, event_bus)
        self.strategy_map_manager = StrategyMapManager(db, event_bus)

    async def generate_sketch(
        self,
        *,
        plan_card_id: UUID,
        compass: PlanningArtifact | dict,
        dossier: PlanningArtifact | dict,
        user_id: UUID,
    ) -> PlanningArtifact:
        plan_card = await self._get_owned_plan(plan_card_id, user_id)
        compass_payload, compass_version, compass_id = self._normalize_artifact(compass)
        dossier_payload, dossier_version, dossier_id = self._normalize_artifact(dossier)
        phases = self._build_phase_sketch(compass_payload, dossier_payload)

        artifact = await self.artifact_service.create_artifact(
            plan_card_id=plan_card_id,
            artifact_type=ArtifactType.PHASE_BLUEPRINT,
            payload={
                "phase_count": len(phases),
                "phases": phases,
                "compass_artifact_id": str(compass_id) if compass_id else None,
                "dossier_artifact_id": str(dossier_id) if dossier_id else None,
            },
            created_by_agent="phase_sketch_service",
            based_on_versions={
                "GLOBAL_COMPASS": compass_version,
                "DISCOVERY_DOSSIER": dossier_version,
            },
        )
        await self.artifact_service.propose_artifact(artifact.id)
        await self._sync_plan_metadata(
            plan_card,
            {
                "phase_blueprint_artifact_id": str(artifact.id),
                "phase_blueprint_version": artifact.version,
                "workflow_state": "PHASE_SKETCH_REVIEW",
            },
        )
        return artifact

    async def materialize_sketch(
        self,
        *,
        plan_card_id: UUID,
        sketch: PlanningArtifact | dict,
        user_id: UUID,
    ) -> list[Card]:
        plan_card = await self._get_owned_plan(plan_card_id, user_id)
        sketch_artifact, sketch_payload = await self._resolve_sketch(sketch)

        metadata = dict(plan_card.metadata_ or {})
        if metadata.get("materialized_phase_blueprint_artifact_id") == str(sketch_artifact.id):
            return await self.phase_service.get_plan_phases(plan_card.id)

        # Enforce compass approval gate: a plan must have an approved GlobalCompass
        # before its phase sketch can be materialized.
        compass = await self.artifact_service.get_approved(plan_card.id, ArtifactType.GLOBAL_COMPASS)
        if compass is None:
            raise ValueError(
                "Cannot materialize phase sketch: plan has no approved GlobalCompass. "
                "Complete the discovery conversation and approve the compass first."
            )

        if sketch_artifact.status == ArtifactStatus.DRAFT:
            await self.artifact_service.propose_artifact(sketch_artifact.id)
        if sketch_artifact.status != ArtifactStatus.APPROVED:
            maybe_approved = await self.artifact_service.approve_artifact(
                sketch_artifact.id,
                approved_by_user_id=user_id,
            )
            if maybe_approved:
                sketch_artifact = maybe_approved

        existing_phases = await self.phase_service.get_plan_phases(plan_card.id)
        real_phases = [phase for phase in existing_phases if not bool((phase.metadata_ or {}).get("synthetic_phase"))]
        if real_phases:
            raise ValueError("Plan already has real phases; refusing to rematerialize phase sketch")

        created_phases: list[Card] = []
        cursor = date.today()
        for index, phase_def in enumerate(sketch_payload.get("phases") or [], start=1):
            duration_weeks = max(1, int(phase_def.get("estimated_duration_weeks") or 2))
            estimated_start = cursor
            estimated_end = cursor + timedelta(days=duration_weeks * 7 - 1)
            cursor = estimated_end + timedelta(days=1)
            created = await self.phase_service.create_phase(
                plan_card_id=plan_card.id,
                name=phase_def.get("name") or f"Phase {index}",
                phase_index=index,
                user_id=user_id,
                estimated_start=estimated_start,
                estimated_end=estimated_end,
                entry_criteria=list(phase_def.get("entry_criteria") or []),
                exit_criteria=list(phase_def.get("exit_criteria") or []),
                feedback_gate_required=True,
                phase_weight=float(phase_def.get("weight") or 1.0),
                objective=phase_def.get("description") or phase_def.get("name"),
            )
            created_phases.append(created)

        if created_phases:
            await self.phase_service.activate_phase(
                phase_card_id=created_phases[0].id,
                user_id=user_id,
                skip_gate_check=True,
            )

        await self.strategy_map_manager.propose_update(
            plan_card.id,
            {
                "phase_architecture": {
                    "phase_count": len(created_phases),
                    "current_phase_card_id": str(created_phases[0].id) if created_phases else None,
                    "phase_titles": [
                        (phase.metadata_ or {}).get("title") or (phase.metadata_ or {}).get("objective")
                        for phase in created_phases
                    ],
                }
            },
            evidence={"compass_version": sketch_artifact.based_on_versions.get("GLOBAL_COMPASS")},
        )
        await self._sync_plan_metadata(
            plan_card,
            {
                "materialized_phase_blueprint_artifact_id": str(sketch_artifact.id),
                "workflow_state": "PHASE_DESIGN",
            },
        )
        logger.info(
            "PhaseSketchService: materialized {} phases for plan {}",
            len(created_phases),
            plan_card.id,
        )
        return created_phases

    def _build_phase_sketch(self, compass_payload: dict, dossier_payload: dict) -> list[dict[str, Any]]:
        phase_count = self._determine_phase_count(dossier_payload)
        north_star = compass_payload.get("north_star") or dossier_payload.get("goal_statement") or "growth goal"
        timeline = dossier_payload.get("timeline") or "the current horizon"
        values = list(dossier_payload.get("values") or compass_payload.get("values") or [])
        weights = self._distribute_weights(phase_count)

        phases: list[dict[str, Any]] = []
        names = [
            "Foundation",
            "Stabilize",
            "Expansion",
            "Integration",
            "Refinement",
            "Autonomy",
        ]
        for index in range(phase_count):
            phase_name = names[index] if index < len(names) else f"Phase {index + 1}"
            phases.append(
                {
                    "name": phase_name,
                    "description": self._build_phase_description(
                        phase_name=phase_name,
                        index=index,
                        total=phase_count,
                        north_star=north_star,
                        timeline=timeline,
                    ),
                    "estimated_duration_weeks": self._estimate_duration_weeks(
                        index=index,
                        phase_count=phase_count,
                        timeline_text=str(timeline),
                    ),
                    "weight": weights[index],
                    "entry_criteria": self._build_entry_criteria(index=index, values=values),
                    "exit_criteria": self._build_exit_criteria(
                        phase_name=phase_name,
                        north_star=north_star,
                        index=index,
                        phase_count=phase_count,
                    ),
                    "key_topics": self._derive_key_topics(north_star, values),
                }
            )
        return phases

    def _determine_phase_count(self, dossier_payload: dict) -> int:
        timeline = str(dossier_payload.get("timeline") or "")
        if any(token in timeline for token in ("1年", "2年", "3年", "year", "years")):
            return 5
        if any(token in timeline for token in ("6个月", "半年", "months", "month")):
            return 4
        return 3

    def _estimate_duration_weeks(self, *, index: int, phase_count: int, timeline_text: str) -> int:
        if any(token in timeline_text for token in ("30天", "60天", "days")):
            return 2 if index == 0 else 3
        if any(token in timeline_text for token in ("1年", "2年", "3年", "year")):
            return 8 if index < phase_count - 1 else 10
        return 4

    def _distribute_weights(self, phase_count: int) -> list[float]:
        base = [1.0] * phase_count
        if phase_count >= 3:
            base[0] = 0.8
            base[-1] = 1.2
        total = sum(base)
        return [round(item / total, 4) for item in base]

    def _build_phase_description(
        self,
        *,
        phase_name: str,
        index: int,
        total: int,
        north_star: str,
        timeline: str,
    ) -> str:
        if index == 0:
            return f"Build a stable execution base toward {north_star} within {timeline}."
        if index == total - 1:
            return f"Consolidate gains and prove durable capability for {north_star}."
        return f"Expand execution capacity and reduce friction while moving toward {north_star}."

    def _build_entry_criteria(self, *, index: int, values: list[str]) -> list[str]:
        criteria = ["The user still endorses the current north-star direction."]
        if index > 0:
            criteria.append("Previous phase feedback gate has been completed.")
        if values:
            criteria.append(f"Execution still respects the user's values: {', '.join(values[:3])}.")
        return criteria

    def _build_exit_criteria(self, *, phase_name: str, north_star: str, index: int, phase_count: int) -> list[str]:
        criteria = [f"{phase_name} produces visible evidence of progress toward {north_star}."]
        if index < phase_count - 1:
            criteria.append("User feedback confirms the plan still feels realistic.")
        else:
            criteria.append("System can transition into a new long-horizon cycle without losing context.")
        return criteria

    def _derive_key_topics(self, north_star: str, values: list[str]) -> list[str]:
        tokens = [token for token in north_star.replace("/", " ").split() if token][:3]
        return tokens + values[:2]

    def _normalize_artifact(self, artifact: PlanningArtifact | dict) -> tuple[dict, int, UUID | None]:
        if isinstance(artifact, PlanningArtifact):
            return dict(artifact.payload or {}), artifact.version, artifact.id
        payload = dict(artifact or {})
        version = int(payload.get("version") or payload.get("artifact_version") or 1)
        artifact_id = payload.get("artifact_id")
        return payload, version, UUID(str(artifact_id)) if artifact_id else None

    async def _resolve_sketch(self, sketch: PlanningArtifact | dict) -> tuple[PlanningArtifact, dict]:
        if isinstance(sketch, PlanningArtifact):
            return sketch, dict(sketch.payload or {})
        artifact_id = sketch.get("artifact_id")
        if artifact_id:
            artifact = await self.artifact_service.get_artifact(UUID(str(artifact_id)))
            if artifact and artifact.artifact_type == ArtifactType.PHASE_BLUEPRINT:
                return artifact, dict(artifact.payload or {})
        raise ValueError("Phase sketch artifact not found")

    async def _get_owned_plan(self, plan_card_id: UUID, user_id: UUID) -> Card:
        stmt = select(Card).where(
            Card.id == plan_card_id,
            Card.card_type == CardType.PLAN,
            Card.owner_id == user_id,
            Card.not_deleted_filter(),
        )
        result = await self.db.execute(stmt)
        plan_card = result.scalar_one_or_none()
        if not plan_card:
            raise ValueError("Plan card not found")
        return plan_card

    async def _sync_plan_metadata(self, plan_card: Card, patch: dict[str, Any]) -> None:
        metadata = dict(plan_card.metadata_ or {})
        metadata.update(patch)
        plan_card.metadata_ = metadata
        plan_card.version += 1
        plan_card.updated_by = CardCreatedBy.SYSTEM
        await self.db.flush()
