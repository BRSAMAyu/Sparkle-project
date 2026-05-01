from __future__ import annotations
import contextlib
from datetime import datetime, timedelta, UTC
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_superuser, get_db
from app.config import settings
from app.core.business_metrics import (
    ADAPTIVE_ROLLBACK_TOTAL,
    CONTEXT_SEMANTIC_GATING_FALLBACK_TOTAL,
    CONTEXT_PACK_INTENT,
    EVIDENCE_BACKED_VISIBLE_UPDATE_TOTAL,
    PHASE4_OPERATION_DURATION_SECONDS,
    PERCEPTIBLE_INSIGHT_SENT_TOTAL,
    PERCEPTIBLE_INSIGHT_SKIPPED_TOTAL,
    PLAN_REASONING_GENERATED_TOTAL,
    PLAN_REASONING_SOURCE_TOTAL,
    PROGRESS_COMPARISON_GENERATED_TOTAL,
    PROGRESS_COMPARISON_SKIPPED_TOTAL,
    WEEKLY_LEARNING_REPORT_GENERATED_TOTAL,
    WEEKLY_LEARNING_REPORT_SKIPPED_TOTAL,
    snapshot_metric,
)
from app.core.cache import cache_service
from app.core.celery_app import get_celery_status
from app.core.context_budget import DEFAULT_BUDGETS, _apply_min_budget, _normalize_budget
from app.models.memory import EpisodicMemory, MemoryGoal, MemoryPreference
from app.models.user import User
from app.services.budget_tuning_service import BudgetTuningService
from app.services.aurora_stage18_kill_switch_service import AuroraStage18KillSwitchService
from app.services.aurora_stage19_kill_switch_service import AuroraStage19KillSwitchService
from app.services.aurora_stage21_kill_switch_service import AuroraStage21KillSwitchService
from app.services.aurora_stage23_kill_switch_service import AuroraStage23KillSwitchService
from app.services.aurora_stage24_policy_kill_switch_service import AuroraStage24PolicyKillSwitchService
from app.services.aurora_stage25_reflection_kill_switch_service import AuroraStage25ReflectionKillSwitchService
from app.services.aurora_stage26_scene_kill_switch_service import AuroraStage26SceneKillSwitchService
from app.services.aurora_stage27_foresight_kill_switch_service import AuroraStage27ForesightKillSwitchService
from app.services.aurora_stage28_traits_kill_switch_service import AuroraStage28TraitsKillSwitchService
from app.services.aurora_stage29_srl_kill_switch_service import AuroraStage29SRLKillSwitchService
from app.services.aurora_stage30_metacognition_kill_switch_service import AuroraStage30MetacognitionKillSwitchService
from app.services.aurora_stage31_idiographic_kill_switch_service import AuroraStage31IdiographicKillSwitchService
from app.services.aurora_stage33_kill_switch_service import AuroraStage33KillSwitchService
from app.services.evidence_health_service import EvidenceHealthService
from app.services.ltm_health_snapshot import LtmHealthSnapshotService
from app.services.ltm_release_gate import LtmReleaseGate
from app.services.ltm_rollout_service import LtmRolloutService
from app.services.memory_eval_service import MemoryEvalService
from app.services.memory_jobs import MemoryJobsService
from app.services.memory_rank_policy_service import MemoryRankPolicyService
from app.services.memory_inferred_write_lane import revoke_inferred_lane
from app.services.self_evolution_service import CohortPromotionService, MetricBaselineService, StrategyCalibrationService

router = APIRouter(
    prefix="/admin/memory",
    tags=["memory-admin"],
    dependencies=[Depends(get_current_active_superuser)],
)


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _ensure_governance_enabled() -> None:
    if not settings.ENABLE_MEMORY_GOVERNANCE:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory governance disabled")

def _ensure_ltm_eval_enabled() -> None:
    if not settings.ENABLE_LTM_EVAL:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="LTM eval disabled")


@router.get("/stats")
async def memory_stats(db: AsyncSession = Depends(get_db)):
    _ensure_governance_enabled()
    counts = {}
    for name, model in (
        ("preferences", MemoryPreference),
        ("goals", MemoryGoal),
        ("episodic", EpisodicMemory),
    ):
        total_result = await db.execute(
            select(func.count(model.id)).where(
                model.deleted_at.is_(None),
                getattr(model, "archived_at", None).is_(None) if hasattr(model, "archived_at") else True,
            )
        )
        missing_result = await db.execute(
            select(func.count(model.id)).where(
                model.deleted_at.is_(None),
                getattr(model, "archived_at", None).is_(None) if hasattr(model, "archived_at") else True,
                model.evidence_missing.is_(True),
            )
        )
        cutoff = _utcnow() - timedelta(days=7)
        retracted_result = await db.execute(
            select(func.count(model.id)).where(
                model.retracted_at.isnot(None),
                model.retracted_at >= cutoff,
            )
        )
        total = total_result.scalar() or 0
        missing = missing_result.scalar() or 0
        retracted = retracted_result.scalar() or 0
        counts[name] = {
            "total": total,
            "evidence_missing": missing,
            "missing_rate": (missing / total) if total else 0.0,
            "recent_retractions": retracted,
        }
    inferred_total = await db.execute(
        select(func.count(EpisodicMemory.id)).where(
            EpisodicMemory.deleted_at.is_(None),
            EpisodicMemory.source_lane == "inferred_extraction",
            EpisodicMemory.revoked_at.is_(None),
        )
    )
    inferred_revoked = await db.execute(
        select(func.count(EpisodicMemory.id)).where(
            EpisodicMemory.deleted_at.is_(None),
            EpisodicMemory.source_lane == "inferred_extraction",
            EpisodicMemory.revoked_at.is_not(None),
        )
    )
    counts["episodic_inferred"] = {
        "total": inferred_total.scalar() or 0,
        "revoked": inferred_revoked.scalar() or 0,
    }
    return {"counts": counts}


def _experiment_cohort_for_user(user_id: str | None) -> str | None:
    import hashlib

    raw = str(user_id or "").strip()
    if not raw:
        return None
    bucket = int(hashlib.sha256(raw.encode("utf-8")).hexdigest(), 16) % 3
    return ("A", "B", "C")[bucket]


@router.get("/health")
async def memory_health(
    limit: int = Query(default=20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    _ensure_governance_enabled()
    samples = []
    for model, kind in (
        (MemoryPreference, "preference"),
        (MemoryGoal, "goal"),
        (EpisodicMemory, "episodic"),
    ):
        result = await db.execute(
            select(model)
            .where(model.evidence_missing.is_(True))
            .where(getattr(model, "archived_at", None).is_(None) if hasattr(model, "archived_at") else True)
            .order_by(model.updated_at.desc())
            .limit(limit)
        )
        for item in result.scalars().all():
            samples.append(
                {
                    "type": kind,
                    "id": str(item.id),
                    "updated_at": item.updated_at,
                    "evidence_refs": item.evidence_refs or [],
                }
            )
    return {"items": samples[:limit]}


@router.get("/health-snapshot")
async def memory_health_snapshot(db: AsyncSession = Depends(get_db)):
    _ensure_governance_enabled()
    if not settings.ENABLE_MEMORY_HEALTH_SNAPSHOT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Memory health snapshot disabled")
    service = LtmHealthSnapshotService(db)
    return await service.compute_snapshot()


@router.post("/health/run")
async def run_memory_health(
    user_id: UUID,
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    _ensure_governance_enabled()
    if not settings.ENABLE_EVIDENCE_HEALTH_JOB:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Evidence health job disabled")
    service = EvidenceHealthService(db)
    summary = await service.run_health_check(user_id, limit=limit)
    return {"status": "ok", "summary": summary}


@router.post("/adjustments/run")
async def run_adjustments(db: AsyncSession = Depends(get_db)):
    _ensure_governance_enabled()
    summary = {}

    tuning_status = "skipped"
    if settings.ENABLE_BUDGET_TUNING:
        tuning = BudgetTuningService(db)
        for intent in DEFAULT_BUDGETS:
            await tuning.get_multipliers(intent)
        tuning_status = "ok"
    summary["budget_tuning_decay"] = tuning_status

    jobs = MemoryJobsService(db)
    summary["evidence_health"] = await jobs.run_evidence_health_job(limit_per_type=200)
    summary["decay"] = await jobs.run_decay_job(window_days=14)

    return {"status": "ok", "summary": summary}


@router.get("/jobs/status")
async def memory_jobs_status(db: AsyncSession = Depends(get_db)):
    _ensure_governance_enabled()
    job_status = MemoryJobsService.get_status()
    missing = {}
    for model, kind in (
        (MemoryPreference, "preference"),
        (MemoryGoal, "goal"),
        (EpisodicMemory, "episodic"),
    ):
        conditions = [model.evidence_missing.is_(True), model.deleted_at.is_(None)]
        if hasattr(model, "archived_at"):
            conditions.append(model.archived_at.is_(None))
        if hasattr(model, "retracted_at"):
            conditions.append(model.retracted_at.is_(None))
        result = await db.execute(
            select(func.count(model.id)).where(*conditions)
        )
        missing[kind] = result.scalar() or 0
    return {"jobs": job_status, "evidence_missing": missing}


@router.post("/jobs/run")
async def run_memory_job(
    payload: dict = Body(...),
    db: AsyncSession = Depends(get_db),
):
    _ensure_governance_enabled()
    if not settings.ENABLE_MEMORY_JOBS:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Memory jobs disabled")
    job_type = (payload or {}).get("job")
    service = MemoryJobsService(db)
    if job_type == "evidence_health":
        limit_per_type = payload.get("limit_per_type", 200)
        return await service.run_evidence_health_job(limit_per_type=limit_per_type)
    if job_type == "decay":
        user_id = payload.get("user_id")
        window_days = payload.get("window_days", 14)
        try:
            parsed_user_id = UUID(user_id) if user_id else None
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid user_id") from exc
        return await service.run_decay_job(user_id=parsed_user_id, window_days=window_days)
    if job_type == "repair":
        limit = payload.get("limit", 200)
        return await service.run_repair_job(limit=limit)
    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="unsupported job")


# route-tier: internal
@router.post("/inferred/revoke")
async def revoke_inferred_memory_lane(
    payload: dict = Body(default={}),
    db: AsyncSession = Depends(get_db),
):
    _ensure_governance_enabled()
    user_id_raw = (payload or {}).get("user_id")
    reason = (payload or {}).get("reason") or "admin_kill_switch"
    subject_types = (payload or {}).get("subject_types")
    try:
        user_id = UUID(user_id_raw) if user_id_raw else None
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid user_id") from exc
    revoked = await revoke_inferred_lane(db, user_id=user_id, reason=reason, subject_types=subject_types)
    return {"status": "ok", "revoked": revoked}


# route-tier: internal
@router.get("/stage18/killswitch")
async def get_stage18_kill_switches():
    service = AuroraStage18KillSwitchService()
    return {"flags": await service.get_all()}


# route-tier: internal
@router.put("/stage18/killswitch")
async def update_stage18_kill_switches(payload: dict = Body(default={})):
    service = AuroraStage18KillSwitchService()
    flags = await service.set_flags(
        {
            "aggregator_enabled": payload.get("aggregator_enabled"),
            "push_policy_enabled": payload.get("push_policy_enabled"),
            "push_delivery_enabled": payload.get("push_delivery_enabled"),
        }
    )
    return {"status": "ok", "flags": flags}


# route-tier: internal
@router.get("/stage19/killswitch")
async def get_stage19_kill_switches():
    service = AuroraStage19KillSwitchService()
    return {"flags": await service.get_all()}


# route-tier: internal
@router.put("/stage19/killswitch")
async def update_stage19_kill_switches(payload: dict = Body(default={})):
    service = AuroraStage19KillSwitchService()
    flags = await service.set_flags(
        {
            "working_memory_enabled": payload.get("working_memory_enabled"),
            "llm_extractor_enabled": payload.get("llm_extractor_enabled"),
            "consolidation_enabled": payload.get("consolidation_enabled"),
        }
    )
    return {"status": "ok", "flags": flags}


# route-tier: internal
@router.get("/stage21/killswitch")
async def get_stage21_kill_switches():
    service = AuroraStage21KillSwitchService()
    return {"flags": await service.get_all()}


# route-tier: internal
@router.put("/stage21/killswitch")
async def update_stage21_kill_switches(payload: dict = Body(default={})):
    service = AuroraStage21KillSwitchService()
    flags = await service.set_flags(
        {
            "skill_store_enabled": payload.get("skill_store_enabled"),
            "skill_selection_enabled": payload.get("skill_selection_enabled"),
            "skill_share_enabled": payload.get("skill_share_enabled"),
        }
    )
    return {"status": "ok", "flags": flags}


# route-tier: internal
@router.get("/stage23/killswitch")
async def get_stage23_kill_switches():
    return {"flags": await AuroraStage23KillSwitchService().get_all()}


# route-tier: internal
@router.put("/stage23/killswitch")
async def update_stage23_kill_switches(payload: dict = Body(default={})):
    service = AuroraStage23KillSwitchService()
    mode = payload.get("bayesian_mode", payload.get("mode"))
    if mode is not None:
        await service.set_mode(mode)
    return {"status": "ok", "flags": await service.get_all()}


# route-tier: internal
@router.get("/stage24/killswitch")
async def get_stage24_kill_switches():
    return {"flags": await AuroraStage24PolicyKillSwitchService().get_all()}


# route-tier: internal
@router.put("/stage24/killswitch")
async def update_stage24_kill_switches(payload: dict = Body(default={})):
    service = AuroraStage24PolicyKillSwitchService()
    mode = payload.get("policy_compiler_mode", payload.get("mode"))
    if mode is not None:
        await service.set_mode(mode)
    return {"status": "ok", "flags": await service.get_all()}


# route-tier: internal
@router.get("/stage25/killswitch")
async def get_stage25_kill_switches():
    return {"flags": await AuroraStage25ReflectionKillSwitchService().get_all()}


# route-tier: internal
@router.put("/stage25/killswitch")
async def update_stage25_kill_switches(payload: dict = Body(default={})):
    service = AuroraStage25ReflectionKillSwitchService()
    mode = payload.get("reflection_wire_mode", payload.get("mode"))
    if mode is not None:
        await service.set_mode(mode)
    for category, enabled in dict(payload.get("trigger_toggles") or {}).items():
        await service.set_trigger_enabled(category, bool(enabled))
    return {"status": "ok", "flags": await service.get_all()}


# route-tier: internal
@router.get("/stage26/killswitch")
async def get_stage26_kill_switches():
    service = AuroraStage26SceneKillSwitchService()
    return {"flags": {"mode": await service.get_mode()}}


# route-tier: internal
@router.put("/stage26/killswitch")
async def update_stage26_kill_switches(payload: dict = Body(default={})):
    service = AuroraStage26SceneKillSwitchService()
    if payload.get("mode") is not None:
        await service.set_mode(payload.get("mode"))
    return {"status": "ok", "flags": {"mode": await service.get_mode()}}


# route-tier: internal
@router.get("/stage27/killswitch")
async def get_stage27_kill_switches():
    return {"flags": await AuroraStage27ForesightKillSwitchService().get_all()}


# route-tier: internal
@router.put("/stage27/killswitch")
async def update_stage27_kill_switches(payload: dict = Body(default={})):
    service = AuroraStage27ForesightKillSwitchService()
    if payload.get("mode") is not None:
        await service.set_mode(payload.get("mode"))
    for feature in service.FEATURE_BINDINGS:
        if payload.get(feature) is not None:
            await service.set_feature_mode(feature, payload.get(feature))
    return {"status": "ok", "flags": await service.get_all()}


# route-tier: internal
@router.get("/stage28/killswitch")
async def get_stage28_kill_switches():
    service = AuroraStage28TraitsKillSwitchService()
    return {
        "flags": {
            "mode": await service.get_mode(),
            "nlp_mode": await service.get_nlp_mode(),
            "coldstart_mode": await service.get_coldstart_mode(),
        }
    }


# route-tier: internal
@router.put("/stage28/killswitch")
async def update_stage28_kill_switches(payload: dict = Body(default={})):
    service = AuroraStage28TraitsKillSwitchService()
    if payload.get("mode") is not None:
        await service.set_mode(payload.get("mode"))
    if payload.get("nlp_mode") is not None:
        await service.set_nlp_mode(payload.get("nlp_mode"))
    if payload.get("coldstart_mode") is not None:
        await service.set_coldstart_mode(payload.get("coldstart_mode"))
    return await get_stage28_kill_switches()


# route-tier: internal
@router.get("/stage29/killswitch")
async def get_stage29_kill_switches():
    return {"flags": await AuroraStage29SRLKillSwitchService().summary()}


# route-tier: internal
@router.put("/stage29/killswitch")
async def update_stage29_kill_switches(payload: dict = Body(default={})):
    service = AuroraStage29SRLKillSwitchService()
    if payload.get("mode") is not None:
        await service.set_mode(payload.get("mode"))
    if payload.get("tracker_mode") is not None:
        await service.set_tracker_mode(payload.get("tracker_mode"))
    if payload.get("bridge_mode") is not None:
        await service.set_bridge_mode(payload.get("bridge_mode"))
    if payload.get("scaffolding_consume_mode") is not None:
        await service.set_scaffolding_consume_mode(payload.get("scaffolding_consume_mode"))
    return {"status": "ok", "flags": await service.summary()}


# route-tier: internal
@router.get("/stage30/killswitch")
async def get_stage30_kill_switches():
    service = AuroraStage30MetacognitionKillSwitchService()
    return {
        "flags": {
            "mode": await service.get_mode(),
            **{
                feature: await service.get_feature_mode(feature)
                for feature in service.FEATURE_BINDINGS
            },
        }
    }


# route-tier: internal
@router.put("/stage30/killswitch")
async def update_stage30_kill_switches(payload: dict = Body(default={})):
    service = AuroraStage30MetacognitionKillSwitchService()
    if payload.get("mode") is not None:
        await service.set_mode(payload.get("mode"))
    for feature in service.FEATURE_BINDINGS:
        if payload.get(feature) is not None:
            await service.set_feature_mode(feature, payload.get(feature))
    return await get_stage30_kill_switches()


# route-tier: internal
@router.get("/stage31/killswitch")
async def get_stage31_kill_switches():
    service = AuroraStage31IdiographicKillSwitchService()
    return {"flags": {"mode": await service.get_mode()}}


# route-tier: internal
@router.put("/stage31/killswitch")
async def update_stage31_kill_switches(payload: dict = Body(default={})):
    service = AuroraStage31IdiographicKillSwitchService()
    if payload.get("mode") is not None:
        await service.set_mode(payload.get("mode"))
    return {"status": "ok", "flags": {"mode": await service.get_mode()}}


# route-tier: internal
@router.get("/stage33/killswitch")
async def get_stage33_kill_switches():
    return {"flags": await AuroraStage33KillSwitchService().summary()}


# route-tier: internal
@router.put("/stage33/killswitch")
async def update_stage33_kill_switches(payload: dict = Body(default={})):
    service = AuroraStage33KillSwitchService()
    if payload.get("mode") is not None:
        await service.set_mode(payload.get("mode"))
    for feature in service.FEATURE_BINDINGS:
        if payload.get(feature) is not None:
            await service.set_feature_mode(feature, payload.get(feature))
    return {"status": "ok", "flags": await service.summary()}


@router.get("/context-pack/stats")
async def context_pack_stats():
    _ensure_governance_enabled()
    intents = {}
    for labels, metric in CONTEXT_PACK_INTENT._metrics.items():  # type: ignore[attr-defined]
        intent = labels.get("intent", "unknown")
        intents[intent] = metric._value.get()  # type: ignore[attr-defined]
    return {"intent_distribution": intents}


@router.get("/budgets")
async def get_budget_profiles(db: AsyncSession = Depends(get_db)):
    _ensure_governance_enabled()
    tuning = BudgetTuningService(db)
    payload = {}
    for intent, base in DEFAULT_BUDGETS.items():
        multipliers = await tuning.get_multipliers(intent)
        tuned = {bucket: base[bucket] * multipliers.get(bucket, 1.0) for bucket in base}
        tuned = _apply_min_budget(_normalize_budget(tuned, sum(base.values())), min_value=50)
        payload[intent] = {
            "multipliers": multipliers,
            "effective_budgets": {bucket: int(round(value)) for bucket, value in tuned.items()},
        }
    return payload


@router.get("/release-gate")
async def get_release_gate(db: AsyncSession = Depends(get_db)):
    _ensure_governance_enabled()
    gate = LtmReleaseGate(db)
    result = await gate.check()
    return {"ok": result.ok, "reasons": result.reasons, "metrics": result.metrics}


@router.post("/release-gate/run")
async def run_release_gate(db: AsyncSession = Depends(get_db)):
    _ensure_governance_enabled()
    gate = LtmReleaseGate(db)
    result = await gate.check()
    return {"ok": result.ok, "reasons": result.reasons, "metrics": result.metrics}


@router.get("/rollout/status")
async def rollout_status(
    sample_size: int = Query(default=50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    _ensure_governance_enabled()
    rollout_service = LtmRolloutService(db)
    result = await db.execute(select(User).where(User.is_active.is_(True)).limit(sample_size))
    users = result.scalars().all()
    enabled = 0
    for user in users:
        if await rollout_service.is_enabled(user.id):
            enabled += 1
    return {
        "config": {
            "enabled": settings.ENABLE_LTM_ROLLOUT,
            "percent": settings.LTM_ROLLOUT_PERCENT,
            "allowlist": settings.LTM_ROLLOUT_USER_ALLOWLIST,
            "cohort_tags": settings.LTM_ROLLOUT_COHORT_TAGS,
        },
        "sample": {"size": len(users), "enabled": enabled},
    }


@router.get("/ai-phases/status")
async def ai_phases_status(user_id: str | None = Query(default=None)):
    _ensure_governance_enabled()
    redis_status = {"status": "unknown"}
    if cache_service.redis is None:
        redis_status = {"status": "unavailable"}
    else:
        try:
            await cache_service.redis.ping()
            redis_status = {"status": "healthy"}
        except Exception as exc:
            redis_status = {"status": "unhealthy", "error": str(exc)}
    celery_status = get_celery_status()
    redis_state = str(redis_status.get("status") or "")
    baseline_strategy = None
    promotion_history: list[dict[str, object]] = []
    metric_baseline: dict[str, object] = {}
    metric_anomalies: dict[str, object] = {}
    rule_calibration: dict[str, object] = {"by_rule": {}, "weak_rules": []}
    if cache_service.redis is not None:
        baseline_service = MetricBaselineService(cache_service.redis)
        metric_baseline, metric_anomalies = await baseline_service.get_status_payload()
        promotion_service = CohortPromotionService(cache_service.redis)
        baseline_strategy, promotion_history = await promotion_service.get_admin_payload()
        if user_id:
            with contextlib.suppress(Exception):
                calibration = StrategyCalibrationService(redis=cache_service.redis)
                rule_calibration = await calibration.get_rule_calibration(user_id=user_id)

    return {
        "stages": {
            "stage_1_context_focusing": {
                "enabled": settings.ENABLE_CONTEXT_FOCUSING,
                "semantic_gating": settings.ENABLE_CONTEXT_SEMANTIC_GATING,
                "briefing": settings.ENABLE_CONTEXT_BRIEFING,
                "metadata": settings.ENABLE_CONTEXT_FOCUS_METADATA,
            },
            "stage_2_feedback_adaptation": {
                "enabled": settings.ENABLE_SESSION_FEEDBACK_ADAPTATION,
            },
            "stage_3_adaptive_presentation": {
                "enabled": settings.ENABLE_ADAPTIVE_PRESENTATION,
                "structured_next_actions": settings.ENABLE_STRUCTURED_NEXT_ACTIONS,
                "blocked_temperature": settings.ENABLE_BLOCKED_TEMPERATURE,
                "metadata": settings.ENABLE_UX_PRESENTATION_METADATA,
            },
            "stage_4_perceptible_intelligence": {
                "enabled": settings.ENABLE_PERCEPTIBLE_INTELLIGENCE,
                "proactive_insights": settings.ENABLE_PROACTIVE_INSIGHTS,
                "plan_reasoning_summary": settings.ENABLE_PLAN_REASONING_SUMMARY,
                "weekly_learning_report": settings.ENABLE_WEEKLY_LEARNING_REPORT,
                "progress_comparisons": settings.ENABLE_PROGRESS_COMPARISONS,
            },
        },
        "dependencies": {
            "redis": redis_status,
            "celery": celery_status,
        },
        "degradation": {
            "redis_unavailable": redis_state != "healthy",
            "semantic_gating_fallback_active": any(
                value > 0.0 for value in snapshot_metric(CONTEXT_SEMANTIC_GATING_FALLBACK_TOTAL).values()
            ),
            "llm_review_fallback_recent": any(
                value > 0.0
                for key, value in snapshot_metric(PLAN_REASONING_SOURCE_TOTAL).items()
                if "source=llm_fallback" in key or "source=rules_only" in key
            ),
            "weekly_report_delivery_blocked": redis_state != "healthy" or celery_status.get("status") != "healthy",
        },
        "experiment_cohort": _experiment_cohort_for_user(user_id),
        "rule_calibration": rule_calibration,
        "metric_baseline": metric_baseline,
        "metric_anomalies": metric_anomalies,
        "baseline_strategy": baseline_strategy,
        "promotion_history": promotion_history[-5:],
        "metrics": {
            "perceptible_insight_sent_total": snapshot_metric(PERCEPTIBLE_INSIGHT_SENT_TOTAL),
            "perceptible_insight_skipped_total": snapshot_metric(PERCEPTIBLE_INSIGHT_SKIPPED_TOTAL),
            "plan_reasoning_generated_total": snapshot_metric(PLAN_REASONING_GENERATED_TOTAL),
            "plan_reasoning_source_total": snapshot_metric(PLAN_REASONING_SOURCE_TOTAL),
            "weekly_learning_report_generated_total": snapshot_metric(WEEKLY_LEARNING_REPORT_GENERATED_TOTAL),
            "weekly_learning_report_skipped_total": snapshot_metric(WEEKLY_LEARNING_REPORT_SKIPPED_TOTAL),
            "progress_comparison_generated_total": snapshot_metric(PROGRESS_COMPARISON_GENERATED_TOTAL),
            "progress_comparison_skipped_total": snapshot_metric(PROGRESS_COMPARISON_SKIPPED_TOTAL),
            "evidence_backed_visible_update_total": snapshot_metric(EVIDENCE_BACKED_VISIBLE_UPDATE_TOTAL),
            "context_semantic_gating_fallback_total": snapshot_metric(CONTEXT_SEMANTIC_GATING_FALLBACK_TOTAL),
            "phase4_operation_duration_seconds": snapshot_metric(PHASE4_OPERATION_DURATION_SECONDS),
            "adaptive_rollback_total": snapshot_metric(ADAPTIVE_ROLLBACK_TOTAL),
        },
    }


@router.post("/budgets/reset")
async def reset_budget_profiles(db: AsyncSession = Depends(get_db)):
    _ensure_governance_enabled()
    tuning = BudgetTuningService(db)
    payload = {}
    for intent in DEFAULT_BUDGETS:
        multipliers = await tuning.reset_profiles(intent)
        payload[intent] = {"multipliers": multipliers}
    return payload


@router.post("/eval/run")
async def run_ltm_eval(
    payload: dict = Body(default=None),
    db: AsyncSession = Depends(get_db),
):
    _ensure_governance_enabled()
    _ensure_ltm_eval_enabled()
    payload = payload or {}
    dataset_path = payload.get("dataset_path") or settings.LTM_EVAL_DATASET_PATH
    intent = payload.get("intent")
    user_id = payload.get("user_id")
    try:
        parsed_user_id = UUID(user_id) if user_id else None
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid user_id") from exc
    service = MemoryEvalService(db)
    summary = await service.run_dataset(
        dataset_path,
        intent=intent,
        user_id=parsed_user_id,
        threshold=settings.LTM_EVAL_FAIL_THRESHOLD,
    )
    return summary


@router.get("/rank-policies")
async def list_rank_policies(db: AsyncSession = Depends(get_db)):
    _ensure_governance_enabled()
    service = MemoryRankPolicyService(db)
    policies = await service.list_policies()
    return {
        "items": [
            {
                "id": str(policy.id),
                "scope_type": policy.scope_type,
                "scope_key": policy.scope_key,
                "weights": policy.weights,
                "updated_at": policy.updated_at,
            }
            for policy in policies
        ]
    }


@router.post("/rank-policies")
async def upsert_rank_policy(
    payload: dict = Body(...),
    db: AsyncSession = Depends(get_db),
):
    _ensure_governance_enabled()
    service = MemoryRankPolicyService(db)
    try:
        record = await service.upsert_policy(
            scope_type=payload.get("scope_type"),
            scope_key=payload.get("scope_key"),
            weights=payload.get("weights") or {},
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return {
        "id": str(record.id),
        "scope_type": record.scope_type,
        "scope_key": record.scope_key,
        "weights": record.weights,
        "updated_at": record.updated_at,
    }


@router.delete("/rank-policies/{policy_id}")
async def delete_rank_policy(
    policy_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    _ensure_governance_enabled()
    service = MemoryRankPolicyService(db)
    ok = await service.delete_policy(policy_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")
    return {"status": "ok"}
