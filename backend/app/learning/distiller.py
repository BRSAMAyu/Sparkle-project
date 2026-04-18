"""Behind-flag strategy distillation helpers."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID, uuid5

from app.aurora.schemas import DistilledStrategy, DistilledStrategyLifecycle, ProjectionPolicy, Shareability
from app.learning.attributor import AttributionCandidate

_DISTILLER_NAMESPACE = UUID("a8406540-0a37-49ff-ae2f-7f9862785320")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def distiller_enabled() -> bool:
    return os.getenv("SPARKLE_WS7_DISTILLER_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class DistillationInput:
    candidate: AttributionCandidate
    conversation_context: str = ""


def _build_title(candidate: AttributionCandidate) -> str:
    primary_intervention = candidate.interventions[0] if candidate.interventions else "稳定节奏"
    return f"用{primary_intervention}达成关键进展"


def distill_strategy(input_data: DistillationInput) -> DistilledStrategy | None:
    """Create a first-pass distilled strategy from a successful attribution event."""

    if not distiller_enabled():
        return None
    candidate = input_data.candidate
    now = _utcnow()
    description_parts = [candidate.outcome_summary]
    if candidate.interventions:
        description_parts.append("关键做法：" + "；".join(candidate.interventions[:3]))
    if input_data.conversation_context.strip():
        description_parts.append("上下文：" + input_data.conversation_context.strip())
    description = " ".join(part for part in description_parts if part).strip()
    strategy_id = uuid5(_DISTILLER_NAMESPACE, f"{candidate.user_id}:{candidate.detected_at.isoformat()}:{description}")
    return DistilledStrategy(
        id=strategy_id,
        created_at=now,
        updated_at=now,
        title=_build_title(candidate),
        description=description,
        strategy_type=f"{candidate.scenario_pack_id}::distilled",
        status=DistilledStrategyLifecycle.DISTILLED,
        applicability_scope=", ".join(candidate.subject_tags) if candidate.subject_tags else candidate.scenario_pack_id,
        contraindications=["avoid_if:user_explicitly_declines", "avoid_if:active_crisis_without_support"],
        evidence_strength=max(0.5, candidate.success_score),
        diversity_score=min(1.0, 0.2 + (len(candidate.subject_tags) * 0.1)),
        safety_audit={"deidentified": False, "reviewed": False, "safe": True},
        source_trajectory_type="user_success",
        attribution_count=1,
        deidentification_verified=False,
        user_authorization=None,
        projection_policy=ProjectionPolicy.SENSITIVE_MEDIATED,
        shareability=Shareability.USER_APPROVED_ABSTRACTABLE,
    )
