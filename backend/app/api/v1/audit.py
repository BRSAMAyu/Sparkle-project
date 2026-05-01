from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_superuser, get_db
from app.aurora.runtime_v1.telemetry import AuroraDecisionTelemetryService, AuroraEffectivenessReport
from app.core.cache import cache_service
from app.models.user import User
from app.schemas.exam_sprint import PackQualityReport
from app.schemas.user import UserProfile
from app.services.audit_service import AuditService
from app.services.exam_sprint_review_service import ExamSprintReviewService
from app.services.kill_switch_readiness_service import KillSwitchReadinessService

router = APIRouter(prefix="/audit", tags=["Audit"])

@router.get("/avatars", response_model=list[UserProfile])
async def get_pending_avatars(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_active_superuser),
):
    """获取待审核头像列表"""
    return await AuditService.get_pending_avatars(db)

@router.post("/avatars/{user_id}/approve", response_model=UserProfile)
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

@router.post("/avatars/{user_id}/reject", response_model=UserProfile)
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
async def get_kill_switch_readiness(
    _admin: User = Depends(get_current_active_superuser),
):
    """返回所有 Aurora kill switch 的升级就绪报告（管理员专用）"""
    svc = KillSwitchReadinessService()
    report = svc.get_readiness_report()
    return report


# route-tier: admin
@router.get("/aurora-effectiveness", response_model=AuroraEffectivenessReport)
async def get_aurora_effectiveness(
    days: int = Query(default=30, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_active_superuser),
) -> AuroraEffectivenessReport:
    """返回 Aurora 策略调整的有效性报告（管理员专用）"""
    return await AuroraDecisionTelemetryService(db).get_effectiveness_report(days=days)


# route-tier: admin
@router.get("/pack-quality", response_model=PackQualityReport)
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
