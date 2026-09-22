"""共学自习室端点（D-COMM-4 · beacon 式在场证明）。

独立路由文件（设计卡 §6-6 裁决：community.py 5111 行是结构债，D 线新
端点一律挂新文件）。自习室挂靠既有冲刺小队（Group(type=SPRINT)，D-COMM-3
门面），鉴权与 404/403/400 映射照 D-COMM-3 先例。挂载：
api/v1/router.py → ``/community`` 前缀（本文件路由自带 /squads 段）。
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.community_study_room import (
    StudyRoomEnterResponse,
    StudyRoomExitResponse,
    StudyRoomHeartbeatResponse,
    StudyRoomPresenceResponse,
)
from app.services.community_squad_service import (
    SquadNotFoundError,
    SquadPermissionError,
    SquadStateError,
)
from app.services.community_study_room_service import StudyRoomService

router = APIRouter(prefix="/squads", tags=["community-squad-study-room"])


def _map_room_error(exc: Exception) -> HTTPException:
    """与 D-COMM-3 community_squad.py 同一映射惯例：404/403/400。"""
    if isinstance(exc, SquadNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, SquadPermissionError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


# route-tier: authed
@router.post(
    "/{group_id}/study-room/enter",
    response_model=StudyRoomEnterResponse,
    summary="进入共学自习室",
)
async def enter_study_room(
    group_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """在场证明：记录进入时刻（幂等——已在场则刷新心跳并返回既有会话）。"""
    try:
        payload = await StudyRoomService.enter_room(db, group_id, current_user.id)
    except (SquadNotFoundError, SquadPermissionError, SquadStateError) as exc:
        raise _map_room_error(exc) from exc
    await db.commit()
    return payload


# route-tier: authed
@router.post(
    "/{group_id}/study-room/exit",
    response_model=StudyRoomExitResponse,
    summary="退出共学自习室",
)
async def exit_study_room(
    group_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """记录离开时刻并结算本次会话分钟数（幂等：不在场诚实上报 already_out）。"""
    try:
        payload = await StudyRoomService.exit_room(db, group_id, current_user.id)
    except (SquadNotFoundError, SquadPermissionError, SquadStateError) as exc:
        raise _map_room_error(exc) from exc
    await db.commit()
    return payload


# route-tier: authed
@router.post(
    "/{group_id}/study-room/heartbeat",
    response_model=StudyRoomHeartbeatResponse,
    summary="自习室心跳",
)
async def study_room_heartbeat(
    group_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """崩溃恢复兜底（显式进出为主）：在场刷新 last_heartbeat_at，不在场如实上报。"""
    try:
        payload = await StudyRoomService.heartbeat(db, group_id, current_user.id)
    except (SquadNotFoundError, SquadPermissionError, SquadStateError) as exc:
        raise _map_room_error(exc) from exc
    await db.commit()
    return payload


# route-tier: authed
@router.get(
    "/{group_id}/study-room/presence",
    response_model=StudyRoomPresenceResponse,
    summary="小队自习室在室视图",
)
async def get_study_room_presence(
    group_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """谁在自习 + 各成员今日累计自习时长（本地日界）。仅小队成员可见（非成员 403）。"""
    try:
        return await StudyRoomService.get_presence(db, group_id, current_user.id)
    except (SquadNotFoundError, SquadPermissionError, SquadStateError) as exc:
        raise _map_room_error(exc) from exc
