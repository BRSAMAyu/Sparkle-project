"""Promotion gate for safe adaptive experiments.

The gate is intentionally conservative: it never promotes an experiment directly
into production. It emits approval candidates for the release workflow that FV-09
owns, while preserving the stage-by-stage shadow -> canary -> safe_live path.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


def _utcnow() -> str:
    return datetime.now(UTC).isoformat()


NEXT_STAGE = {
    "shadow": "canary",
    "canary": "safe_live",
    "concluded": "promotion_review",
}


@dataclass(frozen=True)
class PromotionGateResult:
    experiment_key: str
    eligible: bool
    current_status: str
    target_status: str | None = None
    reasons: list[str] = field(default_factory=list)
    candidate_payload: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_key": self.experiment_key,
            "eligible": self.eligible,
            "current_status": self.current_status,
            "target_status": self.target_status,
            "reasons": self.reasons,
            "candidate_payload": self.candidate_payload,
        }


def _guardrail_clean(outcomes: list[dict[str, Any]]) -> bool:
    for outcome in outcomes:
        if not isinstance(outcome, dict):
            continue
        trust = outcome.get("trust") or {}
        load = outcome.get("load") or {}
        agency = outcome.get("agency") or {}
        if trust.get("explicit_negative_feedback") or trust.get("receipt_dismissed"):
            return False
        if agency.get("user_corrected_system"):
            return False
        if load.get("cognitive_load_after") == "high" or load.get("affective_pressure_after") == "anxious":
            return False
    return True


def evaluate_safe_experiment_promotion(experiment: Any) -> PromotionGateResult:
    """Evaluate whether an experiment can advance or needs approval review."""
    status = str(getattr(experiment, "status", "") or "")
    experiment_key = str(getattr(experiment, "experiment_key", "") or "")
    target_status = NEXT_STAGE.get(status)
    reasons: list[str] = []

    if target_status is None:
        return PromotionGateResult(
            experiment_key=experiment_key,
            eligible=False,
            current_status=status,
            reasons=[f"status {status} has no automatic promotion target"],
        )

    current_episodes = int(getattr(experiment, "current_episodes", 0) or 0)
    min_episodes = int(getattr(experiment, "min_episodes", 50) or 50)
    distinct_users = getattr(experiment, "distinct_users", []) or []
    min_distinct_users = int(getattr(experiment, "min_distinct_users", 15) or 15)
    outcome_history = getattr(experiment, "outcome_history", []) or []

    if status == "shadow" and current_episodes < 10:
        reasons.append(f"shadow episodes {current_episodes}/10")
    if status in {"canary", "concluded"} and current_episodes < min_episodes:
        reasons.append(f"episodes {current_episodes}/{min_episodes}")
    if status in {"canary", "concluded"} and len(distinct_users) < min_distinct_users:
        reasons.append(f"distinct users {len(distinct_users)}/{min_distinct_users}")
    if not _guardrail_clean(outcome_history[-20:]):
        reasons.append("recent guardrail violation")

    eligible = not reasons
    candidate_payload = None
    if eligible:
        candidate_payload = {
            "type": "safe_experiment_promotion",
            "experiment_key": experiment_key,
            "from_status": status,
            "target_status": target_status,
            "requires_release_approval": True,
            "created_at": _utcnow(),
            "evidence": {
                "episodes": current_episodes,
                "distinct_users": len(distinct_users),
                "guardrail_window_clean": True,
            },
        }

    return PromotionGateResult(
        experiment_key=experiment_key,
        eligible=eligible,
        current_status=status,
        target_status=target_status,
        reasons=reasons,
        candidate_payload=candidate_payload,
    )


async def enqueue_promotion_candidate(redis_client: Any, candidate_payload: dict[str, Any]) -> None:
    """Best-effort bridge to FV-09's release approval queue."""
    if redis_client is None:
        return
    import json

    payload = json.dumps(candidate_payload)
    await redis_client.lpush("safe_experiment:promotion_candidates", payload)
    await redis_client.set(
        f"safe_experiment:promotion_candidate:{candidate_payload['experiment_key']}",
        payload,
        ex=7 * 24 * 3600,
    )
