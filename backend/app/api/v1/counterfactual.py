from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_superuser, get_current_user, get_db
from app.models.user import User
from app.signals.counterfactual_evaluation import CounterfactualReportService

router = APIRouter(prefix="/counterfactual", tags=["counterfactual"])


def _serialize_report(report: Any) -> dict[str, Any]:
    return {
        "id": str(report.id),
        "user_id": str(report.user_id),
        "context_signature": report.context_signature or {},
        "policy_a": report.policy_a,
        "policy_b": report.policy_b,
        "estimate": report.estimate or {},
        "confidence": report.confidence,
        "evidence_grade": report.evidence_grade,
        "generated_at": report.generated_at.isoformat() if report.generated_at else None,
        "replaced_by_id": str(report.replaced_by_id) if report.replaced_by_id else None,
        "promotion_candidate": report.promotion_candidate or {},
        "promotion_status": report.promotion_status,
        "iron_law_compliance": report.iron_law_compliance or {},
        "metadata": report.runtime_metadata or {},
    }


# route-tier: internal
@router.get("/reports")
async def list_counterfactual_reports(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    include_replaced: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    service = CounterfactualReportService(db)
    reports = await service.list_reports(
        user_id=str(current_user.id),
        include_replaced=include_replaced,
        limit=limit,
        offset=offset,
    )
    return {"items": [_serialize_report(report) for report in reports], "limit": limit, "offset": offset}


# route-tier: internal
@router.get("/reports/{report_id}")
async def get_counterfactual_report(
    report_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    service = CounterfactualReportService(db)
    report = await service.get_report(
        report_id,
        user_id=None if current_user.is_superuser else str(current_user.id),
    )
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="counterfactual_report_not_found")
    return _serialize_report(report)


# route-tier: internal
@router.post("/promote/{report_id}")
async def promote_counterfactual_report(
    report_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser),
) -> dict[str, Any]:
    service = CounterfactualReportService(db)
    try:
        report = await service.promote_report(report_id, admin_user_id=str(current_user.id))
    except ValueError as exc:
        message = str(exc)
        if message == "counterfactual_report_not_found":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message) from exc
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=message) from exc
    return _serialize_report(report)
