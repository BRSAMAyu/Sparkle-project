"""冲刺小队端点（D-COMM-3 · 社群×exam_sprint 首联动）。

独立路由文件（设计卡裁决：community.py 5111 行单文件是结构债，新端点挂
新文件，不再增重存量）。小队 = Group(type=SPRINT) 场景化门面；成员冲刺
完成度聚合口径唯一来自 services/sprint_task_ledger.py（XP/光子禁入）。

挂载：api/v1/router.py → ``api_router.include_router(router, prefix="/community")``
（本文件路由自带 /squads 前缀，与既有 /community/groups/** 无碰撞）。
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.community_squad import (
    SquadCreate,
    SquadInfo,
    SquadListItem,
    SquadMemberBrief,
    SquadSprintProgressResponse,
)
from app.services.community_squad_service import (
    SquadNotFoundError,
    SquadPermissionError,
    SquadService,
    SquadStateError,
)

router = APIRouter(prefix="/squads", tags=["community-squad"])


def _map_squad_error(exc: Exception) -> HTTPException:
    """小队域异常 → HTTP 状态统一映射（404/403/400，见服务层注释）。"""
    if isinstance(exc, SquadNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, SquadPermissionError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


# route-tier: authed
@router.post("", response_model=SquadInfo, status_code=201, summary="创建冲刺小队")
async def create_squad(
    payload: SquadCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建冲刺小队（3-8 人，deadline 必填；创建者为群主）。"""
    try:
        group = await SquadService.create_squad(db, current_user.id, payload)
        await db.commit()
    except (SquadNotFoundError, SquadPermissionError, SquadStateError) as exc:
        raise _map_squad_error(exc) from exc
    return await SquadService.get_squad(db, group.id, current_user.id)


# route-tier: authed
@router.get("", response_model=list[SquadListItem], summary="我的冲刺小队列表")
async def list_my_squads(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """仅冲刺周期内的小队可见（deadline 已过即不再出现）。"""
    return await SquadService.list_my_squads(db, current_user.id)


# route-tier: authed
@router.get("/{group_id}", response_model=SquadInfo, summary="冲刺小队详情")
async def get_squad(
    group_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """公开小队对登录用户可见；私密小队仅成员可见（非成员 403）。"""
    try:
        return await SquadService.get_squad(db, group_id, current_user.id)
    except (SquadNotFoundError, SquadPermissionError, SquadStateError) as exc:
        raise _map_squad_error(exc) from exc


# route-tier: authed
@router.post("/{group_id}/join", summary="加入冲刺小队")
async def join_squad(
    group_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """加入小队（仅冲刺周期内；3-8 人上限）。"""
    try:
        await SquadService.join_squad(db, group_id, current_user.id)
        await db.commit()
        return {"success": True}
    except (SquadNotFoundError, SquadPermissionError, SquadStateError) as exc:
        raise _map_squad_error(exc) from exc


# route-tier: authed
@router.post("/{group_id}/leave", summary="退出冲刺小队")
async def leave_squad(
    group_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """退出小队（软删成员记录；群主须先转让——社群既有惯例）。"""
    try:
        await SquadService.leave_squad(db, group_id, current_user.id)
        await db.commit()
        return {"success": True}
    except (SquadNotFoundError, SquadPermissionError, SquadStateError) as exc:
        raise _map_squad_error(exc) from exc


# route-tier: authed
@router.get(
    "/{group_id}/members",
    response_model=list[SquadMemberBrief],
    summary="冲刺小队成员列表",
)
async def get_squad_members(
    group_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """成员列表：仅小队成员可见（非成员 403）。"""
    try:
        members = await SquadService.get_squad_members(db, group_id, current_user.id)
    except (SquadNotFoundError, SquadPermissionError, SquadStateError) as exc:
        raise _map_squad_error(exc) from exc
    return [
        SquadMemberBrief(
            user_id=member.user_id,
            username=member.user.username if member.user else None,
            nickname=member.user.nickname if member.user else None,
            avatar_url=member.user.avatar_url if member.user else None,
            role=str(member.role.value),
            joined_at=member.joined_at,
        )
        for member in members
    ]


# route-tier: authed
@router.get(
    "/{group_id}/sprint-progress",
    response_model=SquadSprintProgressResponse,
    summary="小队成员冲刺完成度聚合",
)
async def get_squad_sprint_progress(
    group_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """每成员当前 sprint 完成率（sprint-completion 口径，唯一定义点
    sprint_task_ledger；XP/光子等行为量禁入）。仅小队成员可见（非成员 403）。
    """
    try:
        return await SquadService.get_squad_sprint_progress(db, group_id, current_user.id)
    except (SquadNotFoundError, SquadPermissionError, SquadStateError) as exc:
        raise _map_squad_error(exc) from exc
