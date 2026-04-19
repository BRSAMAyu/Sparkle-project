"""Stage 4 async substrate task entrypoints.

Wave 1a scope: define Celery-backed nearline/long-horizon seams without
changing current user-visible routing behavior when flags are off.
"""

from __future__ import annotations

from time import perf_counter
from typing import Any

from app.aurora.context import AuroraDecisionContext, AuroraTier, AuroraTierExecution, AuroraTierStatus
from app.aurora.observability.tiering import record_tier_failure, record_tier_outcome, tier_latency
from app.core.celery_app import celery_app

NEARLINE_TASK_NAME = "app.aurora.tasks.run_aurora_nearline"
LONG_HORIZON_TASK_NAME = "app.aurora.tasks.run_aurora_long_horizon"


def _miss_execution(context: AuroraDecisionContext, reason: str) -> AuroraTierExecution[dict[str, Any]]:
    record_tier_outcome(
        tier=context.tier.value,
        trigger_point=context.trigger_point,
        status=AuroraTierStatus.MISS.value,
        enabled=context.async_flags.any_enabled,
        reason=reason,
    )
    return AuroraTierExecution(
        tier=context.tier,
        status=AuroraTierStatus.MISS,
        trigger_point=context.trigger_point,
        reason=reason,
    )


def _failure_execution(context: AuroraDecisionContext, reason: str, exc: Exception | None = None) -> AuroraTierExecution[dict[str, Any]]:
    error = None if exc is None else str(exc)
    record_tier_failure(
        tier=context.tier.value,
        trigger_point=context.trigger_point,
        reason=reason,
        enabled=context.async_flags.any_enabled,
        error=error,
    )
    return AuroraTierExecution(
        tier=context.tier,
        status=AuroraTierStatus.FAILURE,
        trigger_point=context.trigger_point,
        reason=reason,
        error=error,
    )


def enqueue_nearline_context(context: AuroraDecisionContext) -> AuroraTierExecution[dict[str, Any]]:
    """Schedule nearline Aurora work via existing Celery infrastructure."""

    nearline_context = context.with_tier(AuroraTier.NEARLINE)
    if nearline_context.snapshot is None:
        return _miss_execution(nearline_context, "missing_snapshot")
    if not nearline_context.async_flags.enabled_for(AuroraTier.NEARLINE):
        return _miss_execution(nearline_context, "nearline_flag_disabled")

    try:
        task = celery_app.send_task(
            NEARLINE_TASK_NAME,
            kwargs={"payload": nearline_context.to_payload()},
            queue=nearline_context.async_flags.nearline_queue,
        )
    except Exception as exc:  # pragma: no cover - broker errors depend on runtime infra
        return _failure_execution(nearline_context, "celery_dispatch_failed", exc)

    record_tier_outcome(
        tier=nearline_context.tier.value,
        trigger_point=nearline_context.trigger_point,
        status=AuroraTierStatus.SUCCESS.value,
        enabled=nearline_context.async_flags.any_enabled,
        reason="scheduled",
    )
    return AuroraTierExecution(
        tier=nearline_context.tier,
        status=AuroraTierStatus.SUCCESS,
        trigger_point=nearline_context.trigger_point,
        reason="scheduled",
        task_name=NEARLINE_TASK_NAME,
        task_id=getattr(task, "id", None),
        payload={"queued": True},
    )


def enqueue_long_horizon_context(context: AuroraDecisionContext) -> AuroraTierExecution[dict[str, Any]]:
    """Optional placeholder seam for long-horizon work."""

    long_context = context.with_tier(AuroraTier.LONG_HORIZON)
    if long_context.snapshot is None:
        return _miss_execution(long_context, "missing_snapshot")
    if not long_context.async_flags.enabled_for(AuroraTier.LONG_HORIZON):
        return _miss_execution(long_context, "long_horizon_flag_disabled")

    try:
        task = celery_app.send_task(
            LONG_HORIZON_TASK_NAME,
            kwargs={"payload": long_context.to_payload()},
            queue=long_context.async_flags.long_horizon_queue,
        )
    except Exception as exc:  # pragma: no cover - broker errors depend on runtime infra
        return _failure_execution(long_context, "celery_dispatch_failed", exc)

    record_tier_outcome(
        tier=long_context.tier.value,
        trigger_point=long_context.trigger_point,
        status=AuroraTierStatus.SUCCESS.value,
        enabled=long_context.async_flags.any_enabled,
        reason="scheduled",
    )
    return AuroraTierExecution(
        tier=long_context.tier,
        status=AuroraTierStatus.SUCCESS,
        trigger_point=long_context.trigger_point,
        reason="scheduled",
        task_name=LONG_HORIZON_TASK_NAME,
        task_id=getattr(task, "id", None),
        payload={"queued": True},
    )


def _run_context_with_engine(context: AuroraDecisionContext) -> AuroraTierExecution[dict[str, Any]]:
    from app.aurora.engine import AuroraEngine

    if context.snapshot is None:
        return _miss_execution(context, "missing_snapshot")

    engine = AuroraEngine()
    started = perf_counter()
    with tier_latency(context.tier.value, context.trigger_point, enabled=context.async_flags.any_enabled):
        try:
            decision = engine.safe_route(context)
        except Exception as exc:  # pragma: no cover - defensive path
            return _failure_execution(context, "decision_failure", exc)
    duration_ms = (perf_counter() - started) * 1000
    record_tier_outcome(
        tier=context.tier.value,
        trigger_point=context.trigger_point,
        status=AuroraTierStatus.SUCCESS.value,
        enabled=context.async_flags.any_enabled,
        reason="completed",
    )
    return AuroraTierExecution(
        tier=context.tier,
        status=AuroraTierStatus.SUCCESS,
        trigger_point=context.trigger_point,
        duration_ms=duration_ms,
        payload={
            "decision_id": str(decision.id),
            "decision_type": decision.decision_type,
            "policy_version": decision.policy_version,
            "snapshot_ref": decision.input_snapshot_ref,
        },
    )


@celery_app.task(bind=True, name=NEARLINE_TASK_NAME, max_retries=1)
def run_aurora_nearline(self, payload: dict[str, Any]) -> dict[str, Any]:
    """Celery entrypoint for nearline Aurora work."""

    context = AuroraDecisionContext.from_payload(payload).with_tier(AuroraTier.NEARLINE)
    return _run_context_with_engine(context).to_payload()


@celery_app.task(bind=True, name=LONG_HORIZON_TASK_NAME, max_retries=1)
def run_aurora_long_horizon(self, payload: dict[str, Any]) -> dict[str, Any]:
    """Celery entrypoint for long-horizon Aurora work."""

    context = AuroraDecisionContext.from_payload(payload).with_tier(AuroraTier.LONG_HORIZON)
    return _run_context_with_engine(context).to_payload()


__all__ = [
    "NEARLINE_TASK_NAME",
    "LONG_HORIZON_TASK_NAME",
    "enqueue_nearline_context",
    "enqueue_long_horizon_context",
    "run_aurora_nearline",
    "run_aurora_long_horizon",
]

