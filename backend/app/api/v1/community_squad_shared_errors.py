"""小队错题卡分享端点（D-COMM-5 · 错题卡互助分享）。

独立路由文件（D 线裁决：community.py 5111 行单文件是结构债，新端点挂
新文件）。分享挂靠既有冲刺小队（Group(type=SPRINT)，D-COMM-3 门面），
鉴权与 404/403/400 映射照 D-COMM-3/4 先例；分享内容服务端取真实错题
（请求体只有 error_id），过既有 SAFETY 词库面，**不产生光子/不进任何
榜**（行为断言钉死于 tests/unit/test_community_shared_errors.py）。

挂载：api/v1/router.py → ``/community`` 前缀（本文件路由自带 /squads 段）。
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.community_shared_errors import (
    SHARED_ERRORS_DEFAULT_LIMIT,
    SHARED_ERRORS_MAX_LIMIT,
    SharedErrorCreate,
    SharedErrorEntry,
    SharedErrorListResponse,
    SharedErrorRetractResponse,
)
from app.services.community_shared_error_service import (
    SquadSharedErrorService,
)
from app.services.community_squad_service import SquadNotFoundError, SquadPermissionError, SquadStateError

router = APIRouter(prefix="/squads", tags=["community-squad-shared-errors"])


def _map_share_error(exc: Exception) -> HTTPException:
    """与 D-COMM-3/4 同一映射惯例：404/403/400。"""
    if isinstance(exc, (SquadNotFoundError, LookupError)):
        # 小队不存在 / 错题不存在 / 分享不存在——统一 404 不泄露存在性
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, SquadPermissionError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


# route-tier: authed
@router.post(
    "/{group_id}/shared-errors",
    response_model=SharedErrorEntry,
    status_code=201,
    summary="分享一张自己的错题到小队",
)
async def share_error_to_squad(
    group_id: UUID,
    payload: SharedErrorCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """引用 error_id 分享（内容服务端取，客户端不可伪造）；幂等：同错题
    已在册则原样返回既有分享。命中安全过滤（SAFETY 词库面）→ 400 拒分享。
    分享不产生光子/不进任何榜（纯分发记录）。
    """
    try:
        share, _created = await SquadSharedErrorService.share_error(
            db, group_id, payload.error_id, current_user.id, note=payload.note
        )
        # 展示投影在 commit 前构建（同一会话内解析知识点名，避免提交后
        # 访问过期属性）；分享路径里分享者就是请求者本人，展示名直接取
        # 当前用户（昵称优先，缺失回落用户名——与 D-COMM-3 成员面同惯例）。
        sharer_name = (current_user.nickname or None) or (current_user.username or None)
        entry = await SquadSharedErrorService._to_entry(db, share, sharer_name)
    except (SquadNotFoundError, SquadPermissionError, SquadStateError, LookupError, ValueError) as exc:
        raise _map_share_error(exc) from exc
    await db.commit()
    return entry


# route-tier: authed
@router.get(
    "/{group_id}/shared-errors",
    response_model=SharedErrorListResponse,
    summary="小队错题卡分享列表",
)
async def list_shared_errors(
    group_id: UUID,
    limit: int = Query(SHARED_ERRORS_DEFAULT_LIMIT, ge=1, le=SHARED_ERRORS_MAX_LIMIT),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """成员可见的错题卡流（新→旧，含分享者/科目/知识点/掌握度快照/时间）。
    仅小队成员可见（非成员 403）；源错题被主人删除的分享自动不再出现。
    """
    try:
        return await SquadSharedErrorService.list_shared_errors(
            db, group_id, current_user.id, limit=limit, offset=offset
        )
    except (SquadNotFoundError, SquadPermissionError, SquadStateError, LookupError, ValueError) as exc:
        raise _map_share_error(exc) from exc


# route-tier: authed
@router.delete(
    "/{group_id}/shared-errors/{share_id}",
    response_model=SharedErrorRetractResponse,
    summary="撤回错题分享（软删）",
)
async def retract_shared_error(
    group_id: UUID,
    share_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """撤回自己的分享（软删可撤回语义）；仅分享者本人可撤，非本人/已撤 → 404。"""
    try:
        payload = await SquadSharedErrorService.retract_shared_error(db, group_id, share_id, current_user.id)
    except (SquadNotFoundError, SquadPermissionError, SquadStateError, LookupError, ValueError) as exc:
        raise _map_share_error(exc) from exc
    await db.commit()
    return payload
