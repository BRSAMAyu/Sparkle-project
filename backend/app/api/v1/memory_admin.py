from datetime import datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_superuser, get_db
from app.config import settings
from app.core.business_metrics import CONTEXT_PACK_INTENT
from app.core.context_budget import DEFAULT_BUDGETS, _apply_min_budget, _normalize_budget
from app.models.memory import EpisodicMemory, MemoryGoal, MemoryPreference
from app.models.user import User
from app.services.budget_tuning_service import BudgetTuningService
from app.services.evidence_health_service import EvidenceHealthService
from app.services.ltm_health_snapshot import LtmHealthSnapshotService
from app.services.ltm_release_gate import LtmReleaseGate
from app.services.ltm_rollout_service import LtmRolloutService
from app.services.memory_eval_service import MemoryEvalService
from app.services.memory_jobs import MemoryJobsService
from app.services.memory_rank_policy_service import MemoryRankPolicyService

router = APIRouter(
    prefix="/admin/memory",
    tags=["memory-admin"],
    dependencies=[Depends(get_current_active_superuser)],
)


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
            select(func.count(model.id)).where(model.deleted_at.is_(None))
        )
        missing_result = await db.execute(
            select(func.count(model.id)).where(
                model.deleted_at.is_(None),
                model.evidence_missing.is_(True),
            )
        )
        cutoff = datetime.utcnow() - timedelta(days=7)
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
    return {"counts": counts}


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
    summary["decay"] = await jobs.run_decay_job(window_days=30)

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
        window_days = payload.get("window_days", 30)
        try:
            parsed_user_id = UUID(user_id) if user_id else None
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid user_id") from exc
        return await service.run_decay_job(user_id=parsed_user_id, window_days=window_days)
    if job_type == "repair":
        limit = payload.get("limit", 200)
        return await service.run_repair_job(limit=limit)
    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="unsupported job")


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
