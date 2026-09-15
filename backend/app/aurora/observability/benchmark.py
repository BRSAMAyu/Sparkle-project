"""Inline benchmark harness infrastructure for Corpus V1."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from statistics import mean
from time import perf_counter
from typing import Any

from app.aurora.context import AuroraDecisionContext, AuroraTier, AuroraTierStatus
from app.aurora.observability.tiering import emit_tier_event


@dataclass(frozen=True)
class AuroraBenchmarkCase:
    """Corpus-owned benchmark case contract.

    Agent C owns fixtures/content. Agent A owns this harness infrastructure.
    """

    case_id: str
    context_factory: Callable[[], AuroraDecisionContext]
    budget_ms: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AuroraBenchmarkCapture:
    """Tier-tagged benchmark output for a single case."""

    case_id: str
    tier: AuroraTier
    status: AuroraTierStatus
    duration_ms: float
    within_budget: bool
    trigger_point: str
    decision_type: str | None
    metadata: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


@dataclass(frozen=True)
class AuroraBenchmarkSuiteResult:
    """Collection result suitable for CI reporting."""

    captures: tuple[AuroraBenchmarkCapture, ...]

    @property
    def case_count(self) -> int:
        return len(self.captures)

    @property
    def failures(self) -> int:
        return sum(1 for capture in self.captures if not capture.within_budget or capture.status == AuroraTierStatus.FAILURE)

    @property
    def mean_duration_ms(self) -> float:
        if not self.captures:
            return 0.0
        return mean(capture.duration_ms for capture in self.captures)

    def to_ci_payload(self) -> dict[str, Any]:
        return {
            "case_count": self.case_count,
            "failures": self.failures,
            "mean_duration_ms": round(self.mean_duration_ms, 3),
            "captures": [
                {
                    "case_id": capture.case_id,
                    "tier": capture.tier.value,
                    "status": capture.status.value,
                    "duration_ms": round(capture.duration_ms, 3),
                    "within_budget": capture.within_budget,
                    "trigger_point": capture.trigger_point,
                    "decision_type": capture.decision_type,
                    "error": capture.error,
                    "metadata": capture.metadata,
                }
                for capture in self.captures
            ],
        }


class AuroraInlineBenchmarkHarness:
    """Runner/collector seam for Corpus V1 timing checks."""

    def __init__(self, engine: Any, *, emit_events: bool = True) -> None:
        self._engine = engine
        self._emit_events = emit_events

    def run_case(self, case: AuroraBenchmarkCase) -> AuroraBenchmarkCapture:
        start = perf_counter()
        context = case.context_factory().with_tier(AuroraTier.INLINE).with_benchmark_case(case.case_id)
        try:
            decision = self._engine.safe_route(context)
            duration_ms = (perf_counter() - start) * 1000
            capture = AuroraBenchmarkCapture(
                case_id=case.case_id,
                tier=AuroraTier.INLINE,
                status=AuroraTierStatus.SUCCESS,
                duration_ms=duration_ms,
                within_budget=duration_ms <= case.budget_ms,
                trigger_point=context.trigger_point,
                decision_type=decision.decision_type,
                metadata=case.metadata,
            )
        except Exception as exc:  # pragma: no cover - defensive seam for CI
            duration_ms = (perf_counter() - start) * 1000
            capture = AuroraBenchmarkCapture(
                case_id=case.case_id,
                tier=AuroraTier.INLINE,
                status=AuroraTierStatus.FAILURE,
                duration_ms=duration_ms,
                within_budget=False,
                trigger_point=context.trigger_point,
                decision_type=None,
                metadata=case.metadata,
                error=str(exc),
            )
        if self._emit_events:
            emit_tier_event(
                "inline_benchmark_case",
                enabled=True,
                case_id=capture.case_id,
                tier=capture.tier.value,
                status=capture.status.value,
                duration_ms=round(capture.duration_ms, 3),
                within_budget=capture.within_budget,
                trigger_point=capture.trigger_point,
            )
        return capture

    def run_suite(self, cases: Iterable[AuroraBenchmarkCase]) -> AuroraBenchmarkSuiteResult:
        captures = tuple(self.run_case(case) for case in cases)
        return AuroraBenchmarkSuiteResult(captures=captures)

