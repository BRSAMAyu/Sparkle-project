from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_user, get_db
from app.core.cache import cache_service
from app.models.user import User
from app.services.directive_audit_service import RecentDirectiveAuditService

router = APIRouter()


# route-tier: authed
@router.get("/recent-directives", response_model=dict[str, Any])
async def get_recent_directives(
    limit: int = Query(default=20, ge=1, le=50),
    directive_type: str | None = Query(default=None, description="Filter by canonical or display directive type"),
    hours: int | None = Query(default=None, ge=1, le=24 * 90, description="Only include directives in this window"),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Return recent Causal Control directive decisions for the current user."""
    redis = cache_service.redis
    if redis is None:
        return {"data": [], "meta": {"total": 0, "limit": limit}}

    entries = await RecentDirectiveAuditService(redis).list_recent_directives(
        user_id=str(current_user.id),
        limit=limit,
        directive_type=directive_type,
        hours=hours,
    )
    return {
        "data": entries,
        "meta": {
            "total": len(entries),
            "limit": limit,
            "directive_type": directive_type,
            "hours": hours,
        },
    }


# route-tier: authed
@router.get("/understanding-depth", response_model=dict[str, Any])
async def get_understanding_depth(
    days: int = Query(default=7, ge=7, le=30, description="Trend window: 7 or 30 days"),
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
) -> dict[str, Any]:
    """Return the daily understanding-depth baseline trend for the current user.

    数据飞轮 MVP：每日离线聚合的"越用越懂用户"0-1 合成分（understanding_depth_daily），
    含近 7/30 天趋势与各维度分量（memory_injection/personalization/non_correction/
    non_repeat）。无活动日不落行，前端按日期补零即可。
    """
    from app.services.understanding_depth_metric_service import UnderstandingDepthMetricService

    window = 30 if days >= 30 else 7
    service = UnderstandingDepthMetricService(db)
    rows = await service.get_trend(user_id=current_user.id, days=window)
    data = [
        {
            "date": row.metric_date.isoformat(),
            "score": row.score,
            "components": row.components or {},
            "context_pack_runs": row.context_pack_runs,
            "chat_turns": row.chat_turns,
        }
        for row in rows
    ]
    latest = data[-1] if data else None
    return {
        "data": data,
        "meta": {
            "window_days": window,
            "days": days,
            "total": len(data),
            "latest": latest,
            "definition_version": "v0.1",
        },
    }


# route-tier: authed
@router.get("/understanding-dimensions", response_model=dict[str, Any])
async def get_understanding_dimensions(
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
) -> dict[str, Any]:
    """Return the diagnosable five-dimension understanding summary (D-03).

    五维内部度量（DATA_FLYWHEEL §2：coverage/correctness/scope_precision/
    freshness/utility）的可解释 summary —— **没有单一理解百分比**。

    消费纪律（卡面 work 3）：
    - 每维只给 {status, band, value, samples}；value 仅在维度有值时给出，
      unknown 维如实标 unknown（缺数据不假装）。
    - coverage 展示值经过离线校准 map 重标定（校准前后误差见 calibration 块）；
      漂移红的维度 value 置 null（未校准百分数不出 UI 面）。
    """
    from app.core.understanding_dimensions import DimensionName, DimensionStatus, band_of
    from app.services.understanding_calibration_service import (
        UnderstandingCalibrationService,
        apply_coverage_calibration,
    )
    from app.services.understanding_dimensions_service import UnderstandingDimensionsService

    dims_service = UnderstandingDimensionsService(db)
    row = await dims_service.get_latest_row(user_id=current_user.id)
    if row is None:
        return {
            "data": None,
            "meta": {
                "schema_version": "understanding.dimensions.v1",
                "note": "no understanding rows yet (no activity in any source window)",
            },
        }

    calib_service = UnderstandingCalibrationService(db)
    calibration_run = await calib_service.latest_run(user_id=current_user.id)
    drift_report = (calibration_run.drift_report if calibration_run else {}) or {}
    coverage_map = (calibration_run.coverage_map if calibration_run else None) or None

    dimensions_out: dict[str, Any] = {}
    ok_count = 0
    for dim in (
        DimensionName.COVERAGE,
        DimensionName.CORRECTNESS,
        DimensionName.SCOPE_PRECISION,
        DimensionName.FRESHNESS,
        DimensionName.UTILITY,
    ):
        entry = (row.dimensions or {}).get(dim.value) or {}
        item: dict[str, Any] = {
            "status": entry.get("status") or DimensionStatus.UNKNOWN.value,
            "samples": int(entry.get("samples") or 0),
        }
        drift = drift_report.get(dim.value) or {}
        drifted = drift.get("status") == "drift"
        value = entry.get("value") if entry.get("status") == DimensionStatus.OK.value else None
        if value is not None and not drifted:
            ok_count += 1
            display = float(value)
            if dim is DimensionName.COVERAGE and coverage_map:
                display = apply_coverage_calibration(display, coverage_map)
            item["value"] = round(display, 4)
            item["band"] = band_of(display)
        else:
            item["value"] = None
            item["band"] = None
            if drifted:
                item["note"] = "calibration_drift: value withheld pending recalibration"
            elif entry.get("status") != DimensionStatus.OK.value:
                item["note"] = (entry.get("detail") or {}).get("unknown_reason", "insufficient evidence")
        if dim is DimensionName.COVERAGE and (entry.get("detail") or {}).get("top_missing"):
            item["top_missing"] = entry["detail"]["top_missing"]
        dimensions_out[dim.value] = item

    return {
        "data": {
            "date": row.metric_date.isoformat(),
            "window_days": row.window_days,
            "dimensions": dimensions_out,
            "overall": {
                "ok_dimensions": ok_count,
                "unknown_dimensions": 5 - ok_count,
                "evidence": "diagnosable" if ok_count * 2 > 5 else "insufficient_evidence",
            },
            "calibration": {
                "ran_at": calibration_run.ran_at.isoformat() if calibration_run else None,
                "overall_status": (calibration_run.overall_status if calibration_run else "insufficient"),
                "coverage_map": coverage_map or {},
                "drift_report": drift_report,
            },
        },
        "meta": {"schema_version": "understanding.dimensions.v1"},
    }
