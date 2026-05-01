"""Execution strategy experimentation and quality metrics for Phase 4."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, UTC
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.execution_intent import ExecutionIntent, ExecutionMode, TrustLevel
from app.models.execution_record import ExecutionRecord
from app.models.experiment import ABExperiment, ABExperimentAssignment, ABExperimentMetric, ABExperimentVariant


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@dataclass(frozen=True)
class ExecutionStrategyAssignment:
    experiment_id: str
    variant_id: str
    variant_name: str
    configuration: dict[str, Any]

    def to_policy_payload(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "variant_id": self.variant_id,
            "variant_name": self.variant_name,
            "configuration": self.configuration,
        }


class ExecutionQualityService:
    """Assign execution strategies and log terminal execution metrics."""

    EXPERIMENT_NAME = "openclaw_execution_strategy_v1"

    def __init__(self, db: AsyncSession):
        self._db = db

    async def assign_strategy(
        self,
        *,
        user_id: UUID,
        target_env: str,
        execution_mode: ExecutionMode,
        template_id: str | None = None,
    ) -> ExecutionStrategyAssignment:
        experiment = await self._ensure_experiment()
        variant = await self._ensure_assignment(experiment=experiment, user_id=user_id)
        config = dict(variant.configuration or {})
        config.setdefault("target_env", target_env)
        config.setdefault("execution_mode", execution_mode.value)
        if template_id:
            config.setdefault("template_id", template_id)
        return ExecutionStrategyAssignment(
            experiment_id=str(experiment.id),
            variant_id=str(variant.id),
            variant_name=str(variant.variant_name),
            configuration=config,
        )

    async def record_outcome(
        self,
        *,
        intent: ExecutionIntent,
        record: ExecutionRecord,
        outcome: str,
    ) -> None:
        strategy = (intent.policy or {}).get("quality_strategy") or {}
        experiment_id = strategy.get("experiment_id")
        variant_id = strategy.get("variant_id")
        if not experiment_id or not variant_id:
            return

        metrics = [
            ("success", 1.0 if intent.status.value == "succeeded" else 0.0, "success"),
            ("quality", float(record.quality_score or 0.0), "custom"),
            ("latency", float(record.duration_ms or 0), "latency"),
            ("trusted", 1.0 if intent.trust_level == TrustLevel.TRUSTED else 0.0, "conversion"),
            ("approval_requested", float(record.approval_requested or 0), "engagement"),
            ("outcome_code", self._outcome_code(outcome), "custom"),
        ]

        for metric_name, metric_value, metric_type in metrics:
            self._db.add(
                ABExperimentMetric(
                    experiment_id=experiment_id,
                    variant_id=variant_id,
                    user_id=intent.user_id,
                    metric_name=metric_name,
                    metric_value=metric_value,
                    metric_type=metric_type,
                    context_data={
                        "execution_intent_id": str(intent.id),
                        "execution_record_id": str(record.id),
                        "target_env": intent.target_env.value if intent.target_env else None,
                        "execution_mode": intent.execution_mode.value if intent.execution_mode else None,
                    },
                    timestamp=_utcnow(),
                )
            )
        await self._db.commit()

    async def get_summary(self) -> dict[str, Any]:
        experiment = await self._get_experiment()
        if experiment is None:
            return {
                "experiment_name": self.EXPERIMENT_NAME,
                "status": "missing",
                "variants": [],
                "sample_size_collected": 0,
            }

        variants_result = await self._db.execute(
            select(ABExperimentVariant).where(ABExperimentVariant.experiment_id == experiment.id)
        )
        variants = list(variants_result.scalars().all())

        payload_variants: list[dict[str, Any]] = []
        sample_size = 0
        for variant in variants:
            assignment_count = await self._metric_count(
                experiment_id=experiment.id,
                variant_id=variant.id,
                metric_name="success",
            )
            success_rate = await self._metric_average(
                experiment_id=experiment.id,
                variant_id=variant.id,
                metric_name="success",
            )
            avg_quality = await self._metric_average(
                experiment_id=experiment.id,
                variant_id=variant.id,
                metric_name="quality",
            )
            avg_latency = await self._metric_average(
                experiment_id=experiment.id,
                variant_id=variant.id,
                metric_name="latency",
            )
            sample_size += assignment_count
            payload_variants.append(
                {
                    "variant_id": str(variant.id),
                    "variant_name": variant.variant_name,
                    "is_control": bool(variant.is_control),
                    "configuration": variant.configuration or {},
                    "sample_size": assignment_count,
                    "success_rate": success_rate,
                    "avg_quality": avg_quality,
                    "avg_latency": avg_latency,
                }
            )

        return {
            "experiment_id": str(experiment.id),
            "experiment_name": experiment.name,
            "status": experiment.status,
            "sample_size_collected": sample_size,
            "variants": payload_variants,
        }

    async def _ensure_experiment(self) -> ABExperiment:
        experiment = await self._get_experiment()
        if experiment is not None:
            return experiment

        experiment = ABExperiment(
            name=self.EXPERIMENT_NAME,
            description="Evaluate delegated execution strategies across templates and environments.",
            hypothesis="Structured evidence and approval strategies improve trusted execution quality.",
            status="running",
            sample_size_target=300,
            significance_level=0.05,
            power=0.8,
            minimum_detectable_effect=0.08,
            extra_metadata={"scope": "execution_quality"},
        )
        self._db.add(experiment)
        await self._db.flush()

        variants = [
            {
                "variant_name": "balanced_control",
                "is_control": True,
                "configuration": {
                    "instruction_suffixes": ["Keep output balanced between completeness and speed."],
                    "artifact_types": ["text"],
                },
            },
            {
                "variant_name": "evidence_strict",
                "is_control": False,
                "configuration": {
                    "instruction_suffixes": [
                        "Include explicit evidence references and a concise risk note.",
                    ],
                    "artifact_types": ["text", "screenshot"],
                },
            },
            {
                "variant_name": "speed_optimized",
                "is_control": False,
                "configuration": {
                    "instruction_suffixes": ["Prefer the shortest reliable path and summarize aggressively."],
                    "artifact_types": ["text"],
                    "timeout_multiplier": 0.85,
                },
            },
        ]
        for entry in variants:
            self._db.add(
                ABExperimentVariant(
                    experiment_id=experiment.id,
                    variant_name=entry["variant_name"],
                    is_control=entry["is_control"],
                    configuration=entry["configuration"],
                    allocation_weight=1 / len(variants),
                    traffic_allocation_percentage=100 / len(variants),
                )
            )
        await self._db.commit()
        await self._db.refresh(experiment)
        return experiment

    async def _ensure_assignment(self, *, experiment: ABExperiment, user_id: UUID) -> ABExperimentVariant:
        result = await self._db.execute(
            select(ABExperimentAssignment)
            .where(
                ABExperimentAssignment.experiment_id == experiment.id,
                ABExperimentAssignment.user_id == user_id,
                ABExperimentAssignment.is_excluded.is_(False),
            )
        )
        assignment = result.scalar_one_or_none()
        if assignment is not None:
            variant = await self._db.get(ABExperimentVariant, assignment.variant_id)
            if variant is not None:
                return variant

        variants_result = await self._db.execute(
            select(ABExperimentVariant)
            .where(ABExperimentVariant.experiment_id == experiment.id)
            .order_by(ABExperimentVariant.created_at.asc())
        )
        variants = list(variants_result.scalars().all())
        if not variants:
            raise ValueError("Execution quality experiment has no variants")

        digest = hashlib.sha256(f"{user_id}:{experiment.id}".encode()).hexdigest()
        assigned_index = int(digest, 16) % len(variants)
        variant = variants[assigned_index]

        self._db.add(
            ABExperimentAssignment(
                experiment_id=experiment.id,
                user_id=user_id,
                variant_id=variant.id,
                assignment_date=_utcnow(),
            )
        )
        await self._db.commit()
        return variant

    async def _get_experiment(self) -> ABExperiment | None:
        result = await self._db.execute(
            select(ABExperiment).where(ABExperiment.name == self.EXPERIMENT_NAME)
        )
        return result.scalar_one_or_none()

    async def _metric_average(
        self,
        *,
        experiment_id: UUID,
        variant_id: UUID,
        metric_name: str,
    ) -> float:
        result = await self._db.execute(
            select(func.avg(ABExperimentMetric.metric_value)).where(
                ABExperimentMetric.experiment_id == experiment_id,
                ABExperimentMetric.variant_id == variant_id,
                ABExperimentMetric.metric_name == metric_name,
            )
        )
        return round(float(result.scalar() or 0.0), 4)

    async def _metric_count(
        self,
        *,
        experiment_id: UUID,
        variant_id: UUID,
        metric_name: str,
    ) -> int:
        result = await self._db.execute(
            select(func.count(ABExperimentMetric.id)).where(
                ABExperimentMetric.experiment_id == experiment_id,
                ABExperimentMetric.variant_id == variant_id,
                ABExperimentMetric.metric_name == metric_name,
            )
        )
        return int(result.scalar() or 0)

    @staticmethod
    def _outcome_code(outcome: str) -> float:
        mapping = {
            "succeeded": 1.0,
            "partial": 0.5,
            "failed": 0.0,
            "handed_back": -1.0,
            "canceled": -0.5,
        }
        return mapping.get(outcome, 0.0)
