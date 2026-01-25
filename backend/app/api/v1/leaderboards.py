"""
排行榜 API Endpoints
Leaderboards API

提供多种类型的排行榜查询接口
"""
from typing import Dict, Any, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.leaderboard import (
    LeaderboardType,
    LeaderboardPeriod,
    LeaderboardRequest,
    LeaderboardResponse,
    MyRankResponse,
    LeaderboardSummary
)
from app.services.leaderboard_service import LeaderboardService

router = APIRouter()


@router.get("", response_model=Dict[str, Any])
async def get_leaderboard(
    type: LeaderboardType = Query(LeaderboardType.GLOBAL, description="排行榜类型"),
    limit: int = Query(50, ge=1, le=100, description="返回数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
    period: LeaderboardPeriod = Query(LeaderboardPeriod.ALL_TIME, description="统计周期"),
    subject_id: Optional[UUID] = Query(None, description="学科ID（仅学科榜）"),
    group_id: Optional[UUID] = Query(None, description="群组ID（仅群组榜）"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取排行榜

    支持多种排行榜类型：
    - global: 全局综合排行榜
    - friends: 好友排行榜
    - group: 群组排行榜
    - subject: 学科排行榜
    - weekly: 本周学习排行榜
    - streak: 连胜排行榜

    Args:
        - type: 排行榜类型
        - limit: 返回数量
        - offset: 偏移量
        - period: 统计周期
        - subject_id: 学科ID（仅学科榜需要）
        - group_id: 群组ID（仅群组榜需要）

    Returns:
        - type: 排行榜类型
        - title: 排行榜标题
        - entries: 排行榜条目
        - my_rank: 我的排名
        - my_score: 我的分数
        - total_participants: 总参与人数
        - last_updated: 最后更新时间
    """
    try:
        service = LeaderboardService(db)

        request = LeaderboardRequest(
            type=type,
            limit=limit,
            offset=offset,
            period=period,
            subject_id=subject_id,
            group_id=group_id
        )

        response = await service.get_leaderboard(request, current_user.id)

        return {
            "success": True,
            "data": response.model_dump()
        }

    except Exception as e:
        logger.error(f"Leaderboard error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get leaderboard: {str(e)}"
        )


@router.get("/summary", response_model=Dict[str, Any])
async def get_leaderboard_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取排行榜摘要

    一次性获取多种排行榜的摘要信息，用于首页展示。

    Returns:
        - global: 全局榜摘要
        - friends: 好友榜摘要
        - weekly: 周榜摘要
        - streak: 连胜榜摘要
        - my_stats: 我的统计信息
    """
    try:
        service = LeaderboardService(db)
        summary = await service.get_summary(current_user.id)

        return {
            "success": True,
            "data": summary.model_dump()
        }

    except Exception as e:
        logger.error(f"Leaderboard summary error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get summary: {str(e)}"
        )


@router.get("/my-rank", response_model=Dict[str, Any])
async def get_my_rank(
    type: LeaderboardType = Query(LeaderboardType.GLOBAL, description="排行榜类型"),
    period: LeaderboardPeriod = Query(LeaderboardPeriod.ALL_TIME, description="统计周期"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取我的排名

    返回当前用户在指定排行榜中的排名和附近用户。

    Args:
        - type: 排行榜类型
        - period: 统计周期

    Returns:
        - rank: 我的排名
        - score: 我的分数
        - score_label: 分数标签
        - total_participants: 总参与人数
        - percentile: 百分位数
        - change_from_last_period: 与上周期排名变化
        - nearby_users: 附近用户列表
    """
    try:
        service = LeaderboardService(db)
        my_rank = await service.get_my_rank(current_user.id, type, period)

        return {
            "success": True,
            "data": my_rank.model_dump()
        }

    except Exception as e:
        logger.error(f"My rank error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get my rank: {str(e)}"
        )


@router.get("/types", response_model=Dict[str, Any])
async def list_leaderboard_types():
    """
    获取支持的排行榜类型列表

    Returns:
        - types: 排行榜类型列表及其说明
    """
    type_descriptions = {
        LeaderboardType.GLOBAL: "全局综合排行榜 - 基于知识点、成就、连胜等综合计算",
        LeaderboardType.FRIENDS: "好友排行榜 - 与好友的对比排名",
        LeaderboardType.GROUP: "群组排行榜 - 群组成员内的排名",
        LeaderboardType.SUBJECT: "学科排行榜 - 指定学科的掌握度排名",
        LeaderboardType.WEEKLY: "本周学习排行榜 - 本周学习活跃度排名",
        LeaderboardType.STREAK: "连胜排行榜 - 连续学习天数排名",
        LeaderboardType.GROUP_FLAME: "群组火苗榜 - 群组火焰贡献排名"
    }

    period_descriptions = {
        LeaderboardPeriod.ALL_TIME: "全部时间",
        LeaderboardPeriod.WEEKLY: "本周",
        LeaderboardPeriod.MONTHLY: "本月",
        LeaderboardPeriod.DAILY: "今日"
    }

    return {
        "success": True,
        "data": {
            "types": [
                {
                    "value": t.value,
                    "description": type_descriptions.get(t, "")
                }
                for t in LeaderboardType
            ],
            "periods": [
                {
                    "value": p.value,
                    "description": period_descriptions.get(p, "")
                }
                for p in LeaderboardPeriod
            ]
        }
    }


@router.get("/top-three/{type}", response_model=Dict[str, Any])
async def get_top_three(
    type: LeaderboardType = Path(..., description="排行榜类型"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取排行榜前三名

    用于领奖台展示。

    Args:
        - type: 排行榜类型

    Returns:
        - first: 第一名
        - second: 第二名
        - third: 第三名
    """
    try:
        service = LeaderboardService(db)

        request = LeaderboardRequest(
            type=type,
            limit=3
        )

        response = await service.get_leaderboard(request, current_user.id)

        first = None
        second = None
        third = None

        if len(response.entries) > 0:
            first = response.entries[0]
        if len(response.entries) > 1:
            second = response.entries[1]
        if len(response.entries) > 2:
            third = response.entries[2]

        return {
            "success": True,
            "data": {
                "first": first.model_dump() if first else None,
                "second": second.model_dump() if second else None,
                "third": third.model_dump() if third else None
            }
        }

    except Exception as e:
        logger.error(f"Top three error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get top three: {str(e)}"
        )


@router.post("/refresh-cache", response_model=Dict[str, Any])
async def refresh_leaderboard_cache(
    type: Optional[LeaderboardType] = Query(None, description="刷新指定类型，不传则刷新全部"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    刷新排行榜缓存

    手动触发排行榜缓存刷新（管理员功能）。

    Args:
        - type: 排行榜类型（可选）

    Returns:
        - success: 是否成功
        - refreshed_types: 被刷新的类型列表
    """
    try:
        # 这里可以实现缓存刷新逻辑
        # 例如：清除相关缓存、触发重新计算等

        refreshed_types = [type.value] if type else ["all"]

        return {
            "success": True,
            "data": {
                "refreshed_types": refreshed_types,
                "refreshed_at": None  # 实际实现时返回刷新时间
            }
        }

    except Exception as e:
        logger.error(f"Refresh cache error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refresh cache: {str(e)}"
        )
