from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query

from app.api.deps import get_current_active_superuser
from app.config import settings
from app.core.cache import cache_service
from app.models.user import User
from app.services.expert_policy_report_service import ExpertPolicyReportService
from app.services.learning_feature_rollup_service import LearningFeatureRollupService
from app.services.meta_learning_feature_service import MetaLearningFeatureService
from app.services.meta_policy_recommendation_service import MetaPolicyRecommendationService
from app.services.policy_candidate_service import PolicyCandidateService
from app.services.policy_registry_service import PolicyRegistryService

router = APIRouter(
    prefix="/admin/learning",
    tags=["Learning Governance"],
    dependencies=[Depends(get_current_active_superuser)],
)


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@router.get("/policy-candidates")
async def list_policy_candidates(
    status: str | None = Query(default=None),
    channel: str | None = Query(default=None),
    current_user: User = Depends(get_current_active_superuser),
):
    _ = current_user
    registry = PolicyRegistryService(redis_client=cache_service.redis)
    channel_filter = str(channel or "").strip() or None
    return {
        "items": [
            row for row in await registry.list_candidates(status=status)
            if channel_filter is None or str(row.get("channel", "routing")) == channel_filter
        ],
    }


@router.post("/policy-candidates/generate")
async def generate_policy_candidates(
    window_days: int = Query(default=7, ge=1, le=30),
    channel: str | None = Query(default=None),
    current_user: User = Depends(get_current_active_superuser),
):
    _ = current_user
    service = PolicyCandidateService(redis_client=cache_service.redis)
    channel_value = str(channel or "").strip() or None
    return await service.run_candidate_job(window_days=window_days, channel=channel_value)


@router.post("/policy-candidates/{candidate_id}/approve")
async def approve_policy_candidate(
    candidate_id: str,
    payload: dict[str, Any] = Body(default={}),
    current_user: User = Depends(get_current_active_superuser),
):
    registry = PolicyRegistryService(redis_client=cache_service.redis)
    try:
        result = await registry.approve_candidate(
            candidate_id=candidate_id,
            reviewer=str(current_user.id),
            note=str(payload.get("note", "") or ""),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "ok", "candidate": result}


@router.post("/policy-candidates/{candidate_id}/reject")
async def reject_policy_candidate(
    candidate_id: str,
    payload: dict[str, Any] = Body(default={}),
    current_user: User = Depends(get_current_active_superuser),
):
    registry = PolicyRegistryService(redis_client=cache_service.redis)
    try:
        result = await registry.reject_candidate(
            candidate_id=candidate_id,
            reviewer=str(current_user.id),
            note=str(payload.get("note", "") or ""),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "ok", "candidate": result}


@router.get("/weekly-report")
async def weekly_learning_report(
    days: int = Query(default=14, ge=7, le=30),
    current_user: User = Depends(get_current_active_superuser),
):
    _ = current_user
    report_service = ExpertPolicyReportService(redis_client=cache_service.redis)
    rollup_service = LearningFeatureRollupService(redis_client=cache_service.redis)
    registry = PolicyRegistryService(redis_client=cache_service.redis)

    policy_report = await report_service.build_report(days=days)
    rollups = await rollup_service.list_rollups(days=days)
    candidates = await registry.list_candidates()

    report_payload = {
        "generated_at": _utcnow().isoformat(),
        "window_days": days,
        "policy_report": policy_report,
        "rollup_count": len(rollups),
        "candidate_count": len(candidates),
        "candidates": candidates[:30],
        "fairness": _build_fairness_summary(rollups),
    }
    tuning_service = MetaPolicyRecommendationService(redis_client=cache_service.redis)
    report_payload["tuning_package"] = await tuning_service.build_weekly_tuning_package(days=days)
    await registry.save_weekly_report(report_payload)
    return report_payload


@router.get("/reasoning-weekly-report")
async def reasoning_weekly_report(
    days: int = Query(default=14, ge=7, le=30),
    current_user: User = Depends(get_current_active_superuser),
):
    _ = current_user
    report_service = ExpertPolicyReportService(redis_client=cache_service.redis)
    rollup_service = LearningFeatureRollupService(redis_client=cache_service.redis)

    policy_report = await report_service.build_report(days=days)
    rollups = await rollup_service.list_rollups(days=days)

    verifier_samples = [row for row in rollups if str(row.get("task_type", ""))]
    avg_q = (
        sum(float(item.get("q_score", 0.0) or 0.0) for item in verifier_samples) / len(verifier_samples)
        if verifier_samples
        else 0.0
    )
    avg_repair_success = (
        sum(float(item.get("repair_success_rate", 0.0) or 0.0) for item in verifier_samples) / len(verifier_samples)
        if verifier_samples
        else 0.0
    )
    top_failures: list[dict[str, Any]] = []
    for row in verifier_samples[:200]:
        for item in row.get("failure_pattern_topn", []) if isinstance(row.get("failure_pattern_topn"), list) else []:
            if isinstance(item, dict):
                top_failures.append(item)

    return {
        "generated_at": _utcnow().isoformat(),
        "window_days": days,
        "policy_health": policy_report.get("policy_health", {}),
        "q_score_by_policy": policy_report.get("q_score_by_policy", {}),
        "q_score_by_cohort": policy_report.get("q_score_by_cohort", {}),
        "stable_cohort_q_gap": policy_report.get("stable_cohort_q_gap", 0.0),
        "delta_vs_baseline": policy_report.get("delta_vs_baseline", {}),
        "avg_q_score": round(float(avg_q), 4),
        "avg_repair_success_rate": round(float(avg_repair_success), 4),
        "failure_pattern_samples": top_failures[:20],
    }


@router.get("/fairness-dashboard")
async def fairness_dashboard(
    days: int = Query(default=14, ge=7, le=60),
    view: str = Query(default="cohort", pattern="^(cohort|task|complexity)$"),
    current_user: User = Depends(get_current_active_superuser),
):
    _ = current_user
    rollup_service = LearningFeatureRollupService(redis_client=cache_service.redis)
    rows = await rollup_service.list_rollups(days=days)
    summary = _build_fairness_summary(rows, view=view)
    return {
        "generated_at": _utcnow().isoformat(),
        "window_days": days,
        "view": view,
        **summary,
    }


@router.get("/meta-candidates")
async def list_meta_candidates(
    status: str | None = Query(default=None),
    channel: str | None = Query(default=None),
    current_user: User = Depends(get_current_active_superuser),
):
    _ = current_user
    registry = PolicyRegistryService(redis_client=cache_service.redis)
    channel_filter = str(channel or "").strip() or None
    items = await registry.list_candidates(status=status)
    if channel_filter:
        items = [item for item in items if str(item.get("channel", "routing")) == channel_filter]
    return {"items": items}


@router.post("/meta-candidates/generate")
async def generate_meta_candidates(
    window_days: int = Query(default=7, ge=1, le=30),
    channels: str | None = Query(default=None, description="comma-separated: routing,prompt,toolchain"),
    current_user: User = Depends(get_current_active_superuser),
):
    _ = current_user
    service = PolicyCandidateService(redis_client=cache_service.redis)
    if channels and str(channels).strip():
        selected = [item.strip() for item in str(channels).split(",") if item.strip()]
    else:
        selected = []
        if bool(getattr(settings, "ENABLE_META_LEARNING_CHANNEL_ROUTING", True)):
            selected.append("routing")
        if bool(getattr(settings, "ENABLE_META_LEARNING_CHANNEL_PROMPT", False)):
            selected.append("prompt")
        if bool(getattr(settings, "ENABLE_META_LEARNING_CHANNEL_TOOLCHAIN", False)):
            selected.append("toolchain")
        if not selected:
            selected = ["routing"]
    return await service.run_candidate_job(window_days=window_days, channels=selected)


@router.post("/meta-candidates/{candidate_id}/approve")
async def approve_meta_candidate(
    candidate_id: str,
    payload: dict[str, Any] = Body(default={}),
    current_user: User = Depends(get_current_active_superuser),
):
    registry = PolicyRegistryService(redis_client=cache_service.redis)
    try:
        result = await registry.approve_candidate(
            candidate_id=candidate_id,
            reviewer=str(current_user.id),
            note=str(payload.get("note", "") or ""),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "ok", "candidate": result}


@router.post("/meta-candidates/{candidate_id}/reject")
async def reject_meta_candidate(
    candidate_id: str,
    payload: dict[str, Any] = Body(default={}),
    current_user: User = Depends(get_current_active_superuser),
):
    registry = PolicyRegistryService(redis_client=cache_service.redis)
    try:
        result = await registry.reject_candidate(
            candidate_id=candidate_id,
            reviewer=str(current_user.id),
            note=str(payload.get("note", "") or ""),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "ok", "candidate": result}


@router.get("/meta-weekly-report")
async def meta_weekly_report(
    days: int = Query(default=14, ge=7, le=30),
    current_user: User = Depends(get_current_active_superuser),
):
    _ = current_user
    report_service = ExpertPolicyReportService(redis_client=cache_service.redis)
    rollup_service = LearningFeatureRollupService(redis_client=cache_service.redis)
    feature_service = MetaLearningFeatureService(redis_client=cache_service.redis)
    tuning_service = MetaPolicyRecommendationService(redis_client=cache_service.redis)
    registry = PolicyRegistryService(redis_client=cache_service.redis)

    policy_report = await report_service.build_report(days=days)
    rollups = await rollup_service.list_rollups(days=days)
    fairness = _build_fairness_summary(rollups, view="cohort")
    features = await feature_service.build_feature_vectors(days=days)
    candidates = await registry.list_candidates()

    by_channel: dict[str, int] = {}
    for candidate in candidates:
        channel = str(candidate.get("channel", "routing"))
        by_channel[channel] = by_channel.get(channel, 0) + 1

    payload = {
        "generated_at": _utcnow().isoformat(),
        "window_days": days,
        "policy_report": policy_report,
        "fairness": fairness,
        "candidate_count_by_channel": by_channel,
        "feature_vectors": features[:200],
        "tuning_package": await tuning_service.build_weekly_tuning_package(days=days),
    }
    await registry.save_weekly_report(payload)
    return payload


@router.get("/meta-tuning-package")
async def meta_tuning_package(
    days: int = Query(default=14, ge=7, le=30),
    current_user: User = Depends(get_current_active_superuser),
):
    _ = current_user
    service = MetaPolicyRecommendationService(redis_client=cache_service.redis)
    return await service.build_weekly_tuning_package(days=days)


def _build_fairness_summary(rows: list[dict[str, Any]], *, view: str = "cohort") -> dict[str, Any]:
    by_cohort: dict[str, dict[str, Any]] = {}
    by_task_type: dict[str, dict[str, Any]] = {}
    by_complexity: dict[str, dict[str, Any]] = {}
    for row in rows:
        counts = row.get("counts") if isinstance(row.get("counts"), dict) else {}
        selected = int(counts.get("expert_selected", 0))
        if selected <= 0:
            continue
        q_score = float(row.get("q_score", 0.0) or 0.0)
        cohort_id = str(row.get("cohort_id", "") or "cohort::unknown")
        task_type = str(row.get("task_type", "") or "unknown")
        complexity_tier = str(row.get("complexity_tier", "") or "unknown")

        cohort = by_cohort.setdefault(cohort_id, {"selected": 0, "q_weighted": 0.0})
        cohort["selected"] += selected
        cohort["q_weighted"] += q_score * selected

        task = by_task_type.setdefault(task_type, {"selected": 0, "q_weighted": 0.0})
        task["selected"] += selected
        task["q_weighted"] += q_score * selected

        complexity = by_complexity.setdefault(complexity_tier, {"selected": 0, "q_weighted": 0.0})
        complexity["selected"] += selected
        complexity["q_weighted"] += q_score * selected

    cohort_rows = []
    for cohort_id, agg in by_cohort.items():
        selected = int(agg["selected"])
        q_avg = (float(agg["q_weighted"]) / selected) if selected > 0 else 0.0
        cohort_rows.append(
            {
                "cohort_id": cohort_id,
                "selected": selected,
                "q_score": round(q_avg, 4),
            }
        )
    cohort_rows.sort(key=lambda item: item["selected"], reverse=True)

    min_support = int(getattr(settings, "LONG_TAIL_COHORT_MIN_SUPPORT", 20))
    stable = [row for row in cohort_rows if int(row["selected"]) >= min_support]
    q_gap = 0.0
    if stable:
        q_values = [float(row["q_score"]) for row in stable]
        q_gap = max(q_values) - min(q_values)

    long_tail = [row for row in cohort_rows if int(row["selected"]) < min_support]
    long_tail_q = (
        round(sum(float(row["q_score"]) for row in long_tail) / len(long_tail), 4)
        if long_tail
        else 0.0
    )
    overall_q = (
        round(sum(float(row["q_score"]) * int(row["selected"]) for row in cohort_rows) / max(1, sum(int(row["selected"]) for row in cohort_rows)), 4)
        if cohort_rows
        else 0.0
    )

    alerts: list[dict[str, str]] = []
    threshold = float(getattr(settings, "FAIRNESS_Q_GAP_ALERT_THRESHOLD", 0.15))
    if q_gap > threshold:
        alerts.append(
            {
                "level": "warning",
                "type": "cohort_q_gap",
                "message": f"Cohort q_score gap {q_gap:.3f} exceeds threshold {threshold:.3f}",
            }
        )
    if long_tail and long_tail_q + 0.08 < overall_q:
        alerts.append(
            {
                "level": "warning",
                "type": "long_tail_underperforming",
                "message": "Long-tail cohorts are significantly below overall quality.",
            }
        )

    task_rows = []
    for task_type, agg in by_task_type.items():
        selected = int(agg["selected"])
        q_avg = (float(agg["q_weighted"]) / selected) if selected > 0 else 0.0
        task_rows.append({"task_type": task_type, "selected": selected, "q_score": round(q_avg, 4)})
    task_rows.sort(key=lambda item: item["selected"], reverse=True)

    complexity_rows = []
    for complexity_tier, agg in by_complexity.items():
        selected = int(agg["selected"])
        q_avg = (float(agg["q_weighted"]) / selected) if selected > 0 else 0.0
        complexity_rows.append({"complexity_tier": complexity_tier, "selected": selected, "q_score": round(q_avg, 4)})
    complexity_rows.sort(key=lambda item: item["selected"], reverse=True)

    stable_q_gap = round(q_gap, 4)
    redline = float(getattr(settings, "FAIRNESS_STABLE_COHORT_Q_GAP_REDLINE", 0.08))
    fairness_guardrail_enabled = bool(
        getattr(settings, "ENABLE_FAIRNESS_GUARDRAIL_V1", False)
        or getattr(settings, "ENABLE_META_FAIRNESS_GUARDRAIL", False)
    )
    if fairness_guardrail_enabled and stable_q_gap > redline:
        alerts.append(
            {
                "level": "critical",
                "type": "stable_cohort_q_gap_redline",
                "message": f"Stable cohort q-gap {stable_q_gap:.3f} exceeds redline {redline:.3f}",
            }
        )

    focus_items: list[dict[str, Any]]
    if view == "task":
        focus_items = task_rows[:40]
    elif view == "complexity":
        focus_items = complexity_rows[:40]
    else:
        focus_items = cohort_rows[:40]

    return {
        "cohort_metrics": cohort_rows[:40],
        "task_type_metrics": task_rows[:20],
        "complexity_metrics": complexity_rows[:20],
        "view_items": focus_items,
        "fairness_overview": {
            "overall_q_score": overall_q,
            "stable_cohort_q_gap": stable_q_gap,
            "long_tail_avg_q_score": long_tail_q,
            "long_tail_count": len(long_tail),
        },
        "alerts": alerts,
    }
