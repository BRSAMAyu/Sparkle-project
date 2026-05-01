"""
推荐系统 API Endpoints
Recommendations API

提供协同过滤推荐接口
"""
from __future__ import annotations

from datetime import UTC
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.recommendation import (
    CollaborativeFilteringRequest,
    RecommendationItemType,
    SimilarItemsRequest,
    SimilarUsersRequest,
)
from app.services.collaborative_filtering_service import CollaborativeFilteringService

router = APIRouter()


@router.get("/collaborative", response_model=dict[str, Any])
async def get_collaborative_recommendations(
    limit: int = Query(10, ge=1, le=50, description="推荐数量"),
    item_type: RecommendationItemType | None = Query(None, description="物品类型筛选"),
    subject_id: UUID | None = Query(None, description="学科筛选"),
    min_similarity: float = Query(0.3, ge=0.0, le=1.0, description="最小相似度"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取协同过滤推荐

    基于用户相似度推荐内容："学过X的人也学Y"

    Args:
        - limit: 推荐数量限制
        - item_type: 物品类型筛选
        - subject_id: 学科筛选
        - min_similarity: 最小用户相似度阈值

    Returns:
        - recommendations: 推荐列表
        - similar_users: 相似用户列表
        - stats: 统计信息
    """
    try:
        service = CollaborativeFilteringService(db)

        request = CollaborativeFilteringRequest(
            user_id=current_user.id,
            limit=limit,
            item_type=item_type,
            subject_id=subject_id,
            min_similarity=min_similarity
        )

        response = await service.get_recommendations(request)

        return {
            "success": True,
            "data": response.model_dump()
        }

    except Exception as e:
        logger.error(f"Collaborative filtering error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Recommendation failed"
        ) from e


@router.get("/similar-users", response_model=dict[str, Any])
async def get_similar_users(
    limit: int = Query(20, ge=1, le=100, description="返回数量"),
    min_common_items: int = Query(3, ge=1, description="最小共同物品数"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取相似用户列表

    返回与当前用户学习行为相似的用户列表。

    Args:
        - limit: 返回数量
        - min_common_items: 最小共同学习物品数

    Returns:
        - similar_users: 相似用户列表
    """
    try:
        service = CollaborativeFilteringService(db)

        request = SimilarUsersRequest(
            user_id=current_user.id,
            limit=limit,
            min_common_items=min_common_items
        )

        similar_users = await service.get_similar_users(request)

        return {
            "success": True,
            "data": [u.model_dump() for u in similar_users],
            "count": len(similar_users)
        }

    except Exception as e:
        logger.error(f"Similar users error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get similar users"
        ) from e


@router.get("/similar-items", response_model=dict[str, Any])
async def get_similar_items(
    item_id: UUID = Query(..., description="物品ID"),
    item_type: RecommendationItemType = Query(..., description="物品类型"),
    limit: int = Query(10, ge=1, le=50, description="返回数量"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取相似物品列表

    返回与指定物品相似的其他物品。

    Args:
        - item_id: 物品ID
        - item_type: 物品类型
        - limit: 返回数量

    Returns:
        - similar_items: 相似物品列表
    """
    try:
        service = CollaborativeFilteringService(db)

        request = SimilarItemsRequest(
            item_id=item_id,
            item_type=item_type,
            limit=limit
        )

        similar_items = await service.get_similar_items(request)

        return {
            "success": True,
            "data": [i.model_dump() for i in similar_items],
            "count": len(similar_items)
        }

    except Exception as e:
        logger.error(f"Similar items error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get similar items"
        ) from e


@router.get("/my-interactions", response_model=dict[str, Any])
async def get_my_interaction_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取我的交互摘要

    返回当前用户的学习交互统计。

    Returns:
        - user_id: 用户ID
        - total_items_learned: 学习的物品总数
        - subjects: 学习的学科列表
        - recent_items: 最近学习的物品ID
        - mastery_levels: 各学科掌握度
    """
    try:
        service = CollaborativeFilteringService(db)
        summary = await service.get_user_interaction_summary(current_user.id)

        return {
            "success": True,
            "data": summary.model_dump()
        }

    except Exception as e:
        logger.error(f"Interaction summary error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get interaction summary"
        ) from e


@router.post("/record-interaction", response_model=dict[str, Any])
async def record_interaction(
    item_id: UUID,
    item_type: str,
    interaction_type: str = "learned",
    weight: float = Query(1.0, ge=0.0, le=10.0, description="交互强度"),
    subject_id: UUID | None = Query(None, description="学科ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    记录用户-物品交互

    记录用户与学习物品的交互，用于推荐算法。

    Args:
        - item_id: 物品ID
        - item_type: 物品类型
        - interaction_type: 交互类型
        - weight: 交互强度
        - subject_id: 学科ID

    Returns:
        - success: 是否成功
        - interaction_id: 交互记录ID
    """
    try:
        service = CollaborativeFilteringService(db)

        interaction = await service.record_interaction(
            user_id=current_user.id,
            item_id=item_id,
            item_type=item_type,
            interaction_type=interaction_type,
            weight=weight,
            subject_id=subject_id
        )

        await db.commit()

        return {
            "success": True,
            "data": {
                "interaction_id": str(interaction.id),
                "recorded_at": interaction.created_at.isoformat()
            }
        }

    except Exception as e:
        logger.error(f"Record interaction error: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record interaction"
        ) from e


@router.get("/stats", response_model=dict[str, Any])
async def get_recommendation_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取推荐系统统计信息

    返回当前用户的推荐相关统计数据。

    Returns:
        - total_interactions: 总交互次数
        - similar_users_count: 相似用户数量
        - last_recommendation_time: 最后推荐时间
        - cache_hit_rate: 缓存命中率
    """
    try:
        from datetime import datetime, timedelta

        from sqlalchemy import func, or_, select

        from app.models.recommendation import RecommendationCache, UserItemInteraction, UserSimilarity

        # 统计交互次数
        interaction_count_query = select(func.count(UserItemInteraction.id)).where(
            UserItemInteraction.user_id == current_user.id,
            UserItemInteraction.not_deleted_filter()
        )
        interaction_result = await db.execute(interaction_count_query)
        total_interactions = interaction_result.scalar() or 0

        # 统计相似用户数量 (使用Python计算时间)
        yesterday = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=24)
        similar_users_query = select(func.count(UserSimilarity.id)).where(
            UserSimilarity.last_calculated_at >= yesterday,
            or_(
                UserSimilarity.user_id_1 == current_user.id,
                UserSimilarity.user_id_2 == current_user.id
            ),
            UserSimilarity.not_deleted_filter()
        )
        similar_result = await db.execute(similar_users_query)
        similar_users_count = similar_result.scalar() or 0

        # 获取最后一次推荐时间
        last_rec_query = select(RecommendationCache).where(
            RecommendationCache.user_id == current_user.id,
            RecommendationCache.not_deleted_filter()
        ).order_by(RecommendationCache.generated_at.desc()).limit(1)
        last_rec_result = await db.execute(last_rec_query)
        last_recommendation = last_rec_result.scalar_one_or_none()

        return {
            "success": True,
            "data": {
                "total_interactions": total_interactions,
                "similar_users_count": similar_users_count,
                "last_recommendation_time": last_recommendation.generated_at.isoformat() if last_recommendation else None,
                "cache_status": "active" if similar_users_count > 0 else "building"
            }
        }

    except Exception as e:
        logger.error(f"Recommendation stats error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get recommendation stats"
        ) from e
