from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user
from app.services.audit_service import AuditService
from app.schemas.user import UserProfile, AvatarStatus
from app.models.user import User

router = APIRouter(prefix="/audit", tags=["Audit"])

def admin_required(current_user: User = Depends(get_current_user)):
    """权限校验：仅超级管理员可操作"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅管理员可执行此操作"
        )
    return current_user

@router.get("/avatars", response_model=List[UserProfile])
async def get_pending_avatars(
    db: AsyncSession = Depends(get_db),
    _admin = Depends(admin_required)
):
    """获取待审核头像列表"""
    return await AuditService.get_pending_avatars(db)

@router.post("/avatars/{user_id}/approve", response_model=UserProfile)
async def approve_avatar(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    _admin = Depends(admin_required)
):
    """通过头像审核"""
    user = await AuditService.approve_avatar(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="待审核用户不存在")
    return user

@router.post("/avatars/{user_id}/reject", response_model=UserProfile)
async def reject_avatar(
    user_id: UUID,
    reason: str = "头像不符合社区规范",
    db: AsyncSession = Depends(get_db),
    _admin = Depends(admin_required)
):
    """驳回头像审核"""
    user = await AuditService.reject_avatar(db, user_id, reason)
    if not user:
        raise HTTPException(status_code=404, detail="待审核用户不存在")
    return user
