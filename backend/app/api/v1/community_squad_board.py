"""小队榜端点（D-COMM-4 · 冲刺完成度口径榜）。

独立路由文件（D-COMM-4 第二面；与自习室 community_study_room.py 同卡
交付）。榜分零新口径：唯一消费 D-COMM-3 的 get_squad_sprint_progress
聚合面（sprint_task_ledger，BP-4 单一事实源），本文件只暴露排序 + 分页
+ <3 人自我视图标记。挂载：api/v1/router.py → ``/community`` 前缀。
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.community_squad_board import SquadLeaderboardResponse
from app.services.community_squad_board_service import BOARD_DEFAULT_LIMIT, SquadBoardService
from app.services.community_squad_service import (
    SquadNotFoundError,
    SquadPermissionError,
    SquadStateError,
)

router = APIRouter(prefix="/squads", tags=["community-squad-board"])


# route-tier: authed
@router.get(
    "/{group_id}/leaderboard",
    response_model=SquadLeaderboardResponse,
    summary="小队榜（冲刺完成度口径）",
)
async def get_squad_leaderboard(
    group_id: UUID,
    limit: int = Query(default=BOARD_DEFAULT_LIMIT, ge=1, le=100, description="分页大小"),
    offset: int = Query(default=0, ge=0, description="分页偏移"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """成员按当前 sprint 完成率排序（并列同名次 + percentile 区间）。

    - 口径唯一来自 sprint_task_ledger（XP/光子/在场时长等行为量禁入）；
    - 成员不足 3 人：board_valid=False / self_view_only=True（设计裁决：
      榜不成立，客户端切自我锚视图）；
    - 仅小队成员可见（非成员 403）；小队不存在/非 SPRINT 统一 404。
    """
    try:
        return await SquadBoardService.get_squad_leaderboard(db, group_id, current_user.id, limit=limit, offset=offset)
    except (SquadNotFoundError, SquadPermissionError, SquadStateError) as exc:
        if isinstance(exc, SquadNotFoundError):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        if isinstance(exc, SquadPermissionError):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
