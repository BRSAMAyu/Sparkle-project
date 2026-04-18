"""Continuous learning pipeline for attribution -> distillation -> review."""

from __future__ import annotations

from dataclasses import dataclass

from app.aurora.schemas import DistilledStrategy, DistilledStrategyLifecycle
from app.learning.attributor import AttributionSignalBundle, detect_successful_attribution
from app.learning.deidentifier import deidentify_text
from app.learning.distiller import DistillationInput, distill_strategy
from app.learning.quality_gate import QualityGateDecision, evaluate_strategy_quality
from app.learning.strategy_store import InMemoryDistilledStrategyStore


@dataclass(frozen=True)
class PipelineResult:
    status: str
    strategy: DistilledStrategy | None = None
    reasons: tuple[str, ...] = ()


def run_continuous_learning_pipeline(
    bundle: AttributionSignalBundle,
    store: InMemoryDistilledStrategyStore,
) -> PipelineResult:
    """Run the Phase A continuous learning pipeline."""

    candidate = detect_successful_attribution(bundle)
    if candidate is None:
        return PipelineResult(status="no_attribution", reasons=("attribution_not_detected",))

    strategy = distill_strategy(DistillationInput(candidate=candidate, conversation_context=bundle.context_excerpt))
    if strategy is None:
        return PipelineResult(status="distiller_disabled", reasons=("distiller_flag_disabled",))

    title_result = deidentify_text(strategy.title)
    description_result = deidentify_text(strategy.description)
    scope_result = deidentify_text(strategy.applicability_scope)
    failures = [result.blocked_reasons for result in (title_result, description_result, scope_result) if not result.passed]
    if failures:
        flattened = tuple(reason for group in failures for reason in group)
        return PipelineResult(status="blocked_by_deidentifier", reasons=flattened or ("deidentification_failed",))

    safety_audit = dict(strategy.safety_audit or {})
    safety_audit["deidentified"] = True
    safety_audit["reviewed"] = True
    safety_audit.setdefault("safe", True)
    strategy = strategy.model_copy(
        update={
            "title": title_result.sanitized_text,
            "description": description_result.sanitized_text,
            "applicability_scope": scope_result.sanitized_text,
            "deidentification_verified": True,
            "safety_audit": safety_audit,
        }
    )
    decision: QualityGateDecision = evaluate_strategy_quality(strategy)
    if not decision.passed:
        return PipelineResult(status="blocked_by_quality_gate", strategy=strategy, reasons=decision.reasons)

    store.create(strategy)
    return PipelineResult(status="created", strategy=strategy, reasons=())


def review_distilled_strategy(
    strategy_id,
    store: InMemoryDistilledStrategyStore,
    *,
    approved: bool,
) -> DistilledStrategy:
    """Apply the initial user review decision to a strategy."""

    target_status = (
        DistilledStrategyLifecycle.USER_REVIEWED if approved else DistilledStrategyLifecycle.RETIRED
    )
    return store.transition(strategy_id, target_status, user_authorization=approved)
