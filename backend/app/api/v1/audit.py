from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_superuser, get_db
from app.aurora.runtime_v1.telemetry import AuroraDecisionTelemetryService, AuroraEffectivenessReport
from app.core.cache import cache_service
from app.middleware.admin_audit import archive_due_admin_audit_logs, audit_admin_action
from app.models.audit_log import AdminAuditLog
from app.models.user import User
from app.schemas.exam_sprint import PackQualityReport
from app.schemas.user import UserProfile
from app.services.audit_service import AuditService
from app.services.exam_sprint_review_service import ExamSprintReviewService
from app.services.kill_switch_readiness_service import KillSwitchReadinessService

router = APIRouter(prefix="/audit", tags=["Audit"])


class AdminAuditActionResponse(BaseModel):
    id: str
    admin_user_id: str | None
    action: str
    category: str
    risk: str
    method: str
    path: str
    status_code: int
    outcome: str
    duration_ms: float
    ip_address: str | None
    request_id: str | None
    trace_id: str | None
    error_message: str | None
    occurred_at: str
    retention_until: str
    details: dict | None = Field(default=None)


class AdminAuditActionListResponse(BaseModel):
    items: list[AdminAuditActionResponse]
    limit: int
    offset: int


def _serialize_admin_audit_log(row: AdminAuditLog) -> AdminAuditActionResponse:
    return AdminAuditActionResponse(
        id=str(row.id),
        admin_user_id=str(row.admin_user_id) if row.admin_user_id else None,
        action=row.action,
        category=row.category,
        risk=row.risk,
        method=row.method,
        path=row.path,
        status_code=row.status_code,
        outcome=row.outcome,
        duration_ms=row.duration_ms,
        ip_address=row.ip_address,
        request_id=row.request_id,
        trace_id=row.trace_id,
        error_message=row.error_message,
        occurred_at=row.occurred_at.isoformat(),
        retention_until=row.retention_until.isoformat(),
        details=row.details,
    )

# route-tier: authed
@router.get("/avatars", response_model=list[UserProfile])
@audit_admin_action(category="avatar_moderation", risk="medium", action="list_pending_avatars")
async def get_pending_avatars(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_active_superuser),
):
    """获取待审核头像列表"""
    return await AuditService.get_pending_avatars(db)

# route-tier: authed
@router.post("/avatars/{user_id}/approve", response_model=UserProfile)
@audit_admin_action(category="avatar_moderation", risk="medium", action="approve_avatar")
async def approve_avatar(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_active_superuser),
):
    """通过头像审核"""
    user = await AuditService.approve_avatar(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="没有找到待审核的用户")
    return user

# route-tier: authed
@router.post("/avatars/{user_id}/reject", response_model=UserProfile)
@audit_admin_action(category="avatar_moderation", risk="medium", action="reject_avatar")
async def reject_avatar(
    user_id: UUID,
    reason: str = "头像不符合社区规范",
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_active_superuser),
):
    """驳回头像审核"""
    user = await AuditService.reject_avatar(db, user_id, reason)
    if not user:
        raise HTTPException(status_code=404, detail="没有找到待审核的用户")
    return user

# route-tier: authed
@router.get("/kill-switch-readiness")
@audit_admin_action(category="kill_switch", risk="medium", action="view_kill_switch_readiness")
async def get_kill_switch_readiness(
    _admin: User = Depends(get_current_active_superuser),
):
    """返回所有 Aurora kill switch 的升级就绪报告（管理员专用）"""
    svc = KillSwitchReadinessService()
    report = svc.get_readiness_report()
    return report


# route-tier: admin
# route-tier: authed
@router.get("/aurora-effectiveness", response_model=AuroraEffectivenessReport)
@audit_admin_action(category="aurora_effectiveness", risk="medium", action="view_aurora_effectiveness")
async def get_aurora_effectiveness(
    days: int = Query(default=30, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_active_superuser),
) -> AuroraEffectivenessReport:
    """返回 Aurora 策略调整的有效性报告（管理员专用）"""
    return await AuroraDecisionTelemetryService(db).get_effectiveness_report(days=days)


# route-tier: admin
# route-tier: authed
@router.get("/pack-quality", response_model=PackQualityReport)
@audit_admin_action(category="pack_quality", risk="medium", action="view_pack_quality")
async def get_pack_quality_report(
    pack_id: str = Query(..., min_length=1, description="Sprint Pack ID，例如 computer_networks@v1"),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_active_superuser),
) -> PackQualityReport:
    """返回 Sprint Pack 节点质量报告（管理员专用）。"""
    service = ExamSprintReviewService(db, cache_service.redis)
    cache_key = service.build_pack_quality_alerts_cache_key(pack_id)
    cached_report = await cache_service.get(cache_key)
    if isinstance(cached_report, dict):
        try:
            return PackQualityReport.model_validate(cached_report)
        except Exception:
            pass
    return await service.build_pack_quality_report(pack_id)


# route-tier: internal
@router.get("/admin_actions", response_model=AdminAuditActionListResponse)
@audit_admin_action(category="audit_log_access", risk="high", action="query_admin_audit_log")
async def list_admin_audit_actions(
    admin_user_id: UUID | None = Query(default=None),
    category: str | None = Query(default=None, min_length=1, max_length=80),
    risk: str | None = Query(default=None, min_length=1, max_length=20),
    outcome: str | None = Query(default=None, min_length=1, max_length=20),
    path_prefix: str | None = Query(default=None, min_length=1, max_length=500),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_active_superuser),
) -> AdminAuditActionListResponse:
    """Query privileged admin operation audit rows. Super-admin only."""

    query = select(AdminAuditLog).order_by(AdminAuditLog.occurred_at.desc()).offset(offset).limit(limit)
    if admin_user_id:
        query = query.where(AdminAuditLog.admin_user_id == admin_user_id)
    if category:
        query = query.where(AdminAuditLog.category == category)
    if risk:
        query = query.where(AdminAuditLog.risk == risk)
    if outcome:
        query = query.where(AdminAuditLog.outcome == outcome)
    if path_prefix:
        query = query.where(AdminAuditLog.path.startswith(path_prefix))

    result = await db.execute(query)
    rows = list(result.scalars().all())
    return AdminAuditActionListResponse(
        items=[_serialize_admin_audit_log(row) for row in rows],
        limit=limit,
        offset=offset,
    )


# route-tier: internal
@router.post("/admin_actions/archive_due")
@audit_admin_action(category="audit_log_archive", risk="high", action="archive_due_admin_audit_logs")
async def archive_due_admin_audit_actions(
    limit: int = Query(default=1000, ge=1, le=10000),
    _admin: User = Depends(get_current_active_superuser),
) -> dict:
    """Copy admin audit rows past their 90-day retention window to object storage."""

    return await archive_due_admin_audit_logs(limit=limit)
