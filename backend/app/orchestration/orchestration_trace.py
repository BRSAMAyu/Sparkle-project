from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any


def _utcnow_iso() -> str:
    return datetime.now(UTC).replace(tzinfo=None).isoformat()


@dataclass
class OrchestrationTraceStep:
    step_id: str
    label: str
    decision: str
    reason: str
    confidence: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    duration_ms: float | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "step_id": self.step_id,
            "label": self.label,
            "decision": self.decision,
            "reason": self.reason,
            "metadata": dict(self.metadata or {}),
        }
        if self.confidence is not None:
            payload["confidence"] = round(float(self.confidence), 4)
        if self.duration_ms is not None:
            payload["duration_ms"] = round(float(self.duration_ms), 2)
        return payload


@dataclass
class OrchestrationTrace:
    trace_id: str
    steps: list[OrchestrationTraceStep] = field(default_factory=list)
    created_at: str = field(default_factory=_utcnow_iso)

    def add_step(
        self,
        *,
        step_id: str,
        label: str,
        decision: str,
        reason: str,
        confidence: float | None = None,
        metadata: dict[str, Any] | None = None,
        duration_ms: float | None = None,
    ) -> OrchestrationTraceStep:
        step = OrchestrationTraceStep(
            step_id=step_id,
            label=label,
            decision=decision,
            reason=reason,
            confidence=confidence,
            metadata=dict(metadata or {}),
            duration_ms=duration_ms,
        )
        self.steps.append(step)
        return step

    def latest_step(self, step_id: str) -> OrchestrationTraceStep | None:
        for step in reversed(self.steps):
            if step.step_id == step_id:
                return step
        return None

    def to_metadata(self) -> dict[str, Any]:
        persona_step = self.latest_step("persona")
        review_step = self.latest_step("plan_review")
        mode_step = self.latest_step("mode_strategy")

        agents: list[str] = []
        if mode_step:
            metadata = mode_step.metadata or {}
            raw_agents = (
                metadata.get("agents_involved")
                or metadata.get("required_agents")
                or metadata.get("preferred_agents")
                or []
            )
            if isinstance(raw_agents, list):
                agents = [str(agent).strip() for agent in raw_agents if str(agent).strip()]

        return {
            "trace_id": self.trace_id,
            "created_at": self.created_at,
            "step_count": len(self.steps),
            "steps": [step.to_dict() for step in self.steps],
            "mode": (mode_step.metadata or {}).get("chat_mode") if mode_step else None,
            "agents": agents,
            "persona_step": persona_step.to_dict() if persona_step else None,
            "review_step": review_step.to_dict() if review_step else None,
        }
