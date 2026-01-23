"""
协同过滤推荐服务
Collaborative Filtering Recommendation Service

实现"学过X的人也学Y"的个性化推荐
使用 Jaccard 相似度计算用户相似度
"""
import time
from typing import List, Dict, Any, Optional, Set, Tuple
from uuid import UUID
from datetime import datetime, timedelta
from loguru import logger
from collections import defaultdict

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc

from app.schemas.recommendation import (
    RecommendationItemType,
    UserSimilarityScore,
    CollaborativeRecommendation,
    ItemSimilarity,
    CollaborativeFilteringRequest,
    SimilarUsersRequest,
    SimilarItemsRequest,
    CollaborativeFilteringResponse,
    RecommendationStats,
    UserInteractionSummary
)
from app.models.recommendation import (
    UserSimilarity,
    ItemSimilarity as ItemSimilarityModel,
    UserItemInteraction,
    UserLearningProfile,
    RecommendationCache
)
from app.models.galaxy import UserNodeStatus, KnowledgeNode
from app.models.user import User
from app.models.task import Task


class CollaborativeFilteringService:
    """
    协同过滤推荐服务

    核心算法：
    - Jaccard 相似度：similarity = |A ∩ B| / |A ∪ B|
    - 用户协同过滤：找到相似用户学过但当前用户未学的物品
    - 物品协同过滤：找到相似物品推荐

    更新策略：
    - 每日定时任务计算用户相似度
    - 实时计算物品相似度
    - 缓存推荐结果（TTL 24小时）
    """

    # 相似度缓存时间（秒）
    SIMILARITY_CACHE_TTL = 24 * 60 * 60
    # 推荐缓存时间（秒）
    RECOMMENDATION_CACHE_TTL = 12 * 60 * 60

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_recommendations(
        self,
        request: CollaborativeFilteringRequest
    ) -> CollaborativeFilteringResponse:
        """
        获取协同过滤推荐

        Args:
            request: 推荐请求

        Returns:
            CollaborativeFilteringResponse: 推荐结果
        """
        start_time = time.time()
        cache_hit = False

        # 检查缓存
        cached = await self._get_cached_recommendations(
            request.user_id,
            request.item_type
        )
        if cached:
            cache_hit = True
            return CollaborativeFilteringResponse(
                recommendations=[
                    CollaborativeRecommendation(**item)
                    for item in cached.cached_recommendations
                ],
                stats=RecommendationStats(
                    total_users_compared=0,
                    similar_users_found=0,
                    recommendations_generated=len(cached.cached_recommendations),
                    cache_hit=True,
                    computation_time_ms=(time.time() - start_time) * 1000
                )
            )

        # 计算相似用户
        similar_users = await self._get_similar_users(
            request.user_id,
            request.limit * 3  # 获取更多相似用户以增加推荐多样性
        )

        # 获取用户已学物品
        learned_items = await self._get_user_learned_items(request.user_id)

        # 基于相似用户生成推荐
        recommendations = await self._generate_recommendations_from_users(
            request.user_id,
            similar_users,
            learned_items,
            request.item_type,
            request.subject_id,
            request.limit
        )

        # 缓存结果
        await self._cache_recommendations(
            request.user_id,
            recommendations,
            request.item_type
        )

        computation_time = (time.time() - start_time) * 1000

        return CollaborativeFilteringResponse(
            recommendations=recommendations,
            similar_users=similar_users[:request.limit],
            stats=RecommendationStats(
                total_users_compared=len(similar_users) + 1,
                similar_users_found=len(similar_users),
                recommendations_generated=len(recommendations),
                cache_hit=False,
                computation_time_ms=computation_time
            )
        )

    async def get_similar_users(
        self,
        request: SimilarUsersRequest
    ) -> List[UserSimilarityScore]:
        """
        获取相似用户列表

        Args:
            request: 相似用户查询请求

        Returns:
            List[UserSimilarityScore]: 相似用户列表
        """
        # 规范化用户ID顺序
        user_id_str = str(request.user_id)

        # 查询缓存相似度
        query = select(UserSimilarity, User).join(
            User,
            or_(
                UserSimilarity.user_id_1 == request.user_id,
                UserSimilarity.user_id_2 == request.user_id
            )
        ).where(
            UserSimilarity.similarity_score >= 0.3,
            UserSimilarity.common_items_count >= request.min_common_items,
            UserSimilarity.not_deleted_filter()
        ).order_by(desc(UserSimilarity.similarity_score)).limit(request.limit)

        result = await self.db.execute(query)

        similar_users = []
        for sim, user in result.all():
            similar_users.append(UserSimilarityScore(
                user_id=user.id,
                username=user.username,
                avatar_url=user.avatar_url,
                similarity=sim.similarity_score,
                common_items=sim.common_items_count,
                common_subjects=sim.common_subjects or [],
                last_interaction=sim.last_calculated_at
            ))

        return similar_users

    async def get_similar_items(
        self,
        request: SimilarItemsRequest
    ) -> List[ItemSimilarity]:
        """
        获取相似物品列表

        Args:
            request: 相似物品查询请求

        Returns:
            List[ItemSimilarity]: 相似物品列表
        """
        # 查询物品相似度
        query = select(ItemSimilarityModel).where(
            or_(
                and_(
                    ItemSimilarityModel.item_id_1 == request.item_id,
                    ItemSimilarityModel.item_type_1 == request.item_type.value
                ),
                and_(
                    ItemSimilarityModel.item_id_2 == request.item_id,
                    ItemSimilarityModel.item_type_2 == request.item_type.value
                )
            ),
            ItemSimilarityModel.not_deleted_filter()
        ).order_by(desc(ItemSimilarityModel.similarity_score)).limit(request.limit)

        result = await self.db.execute(query)
        similarities = result.scalars().all()

        # 转换结果
        items = []
        for sim in similarities:
            # 确定哪个是目标物品
            if str(sim.item_id_1) == str(request.item_id):
                other_id, other_type = sim.item_id_2, sim.item_type_2
            else:
                other_id, other_type = sim.item_id_1, sim.item_type_1

            # 获取物品详情
            title = await self._get_item_title(other_id, other_type)

            items.append(ItemSimilarity(
                item_id=other_id,
                item_type=RecommendationItemType(other_type),
                title=title or f"{other_type}",
                similarity=sim.similarity_score,
                common_learners=sim.common_learners
            ))

        return items

    async def record_interaction(
        self,
        user_id: UUID,
        item_id: UUID,
        item_type: str,
        interaction_type: str,
        weight: float = 1.0,
        subject_id: Optional[UUID] = None
    ) -> UserItemInteraction:
        """
        记录用户-物品交互

        Args:
            user_id: 用户ID
            item_id: 物品ID
            item_type: 物品类型
            interaction_type: 交互类型
            weight: 交互强度
            subject_id: 学科ID

        Returns:
            UserItemInteraction: 交互记录
        """
        interaction = UserItemInteraction(
            user_id=user_id,
            item_id=item_id,
            item_type=item_type,
            interaction_type=interaction_type,
            interaction_weight=weight,
            subject_id=subject_id
        )

        self.db.add(interaction)
        await self.db.flush()

        logger.debug(
            f"Recorded interaction: user={user_id}, item={item_id}, "
            f"type={interaction_type}"
        )

        return interaction

    async def get_user_interaction_summary(
        self,
        user_id: UUID
    ) -> UserInteractionSummary:
        """
        获取用户交互摘要

        Args:
            user_id: 用户ID

        Returns:
            UserInteractionSummary: 交互摘要
        """
        # 获取学习的物品
        learned_query = select(UserItemInteraction.item_id).where(
            UserItemInteraction.user_id == user_id,
            UserItemInteraction.interaction_type.in_(["learned", "LEARNED"]),
            UserItemInteraction.not_deleted_filter()
        ).distinct()

        result = await self.db.execute(learned_query)
        item_ids = [row[0] for row in result.all()]

        # 获取学科分布
        subject_query = select(
            UserItemInteraction.subject_id,
            func.count(UserItemInteraction.id).label('count')
        ).where(
            UserItemInteraction.user_id == user_id,
            UserItemInteraction.subject_id.isnot(None),
            UserItemInteraction.not_deleted_filter()
        ).group_by(UserItemInteraction.subject_id)

        subject_result = await self.db.execute(subject_query)
        subjects = [row[0] for row in subject_result.all() if row[0]]

        return UserInteractionSummary(
            user_id=user_id,
            total_items_learned=len(item_ids),
            subjects=[str(s) for s in subjects],
            recent_items=item_ids[-10:] if len(item_ids) > 10 else item_ids
        )

    # ==================== 私有方法 ====================

    async def _get_similar_users(
        self,
        user_id: UUID,
        limit: int = 50
    ) -> List[UserSimilarityScore]:
        """获取相似用户（内部方法）"""
        # 先尝试从缓存获取
        query = select(UserSimilarity, User).join(
            User,
            or_(
                and_(
                    UserSimilarity.user_id_1 == user_id,
                    User.id == UserSimilarity.user_id_2
                ),
                and_(
                    UserSimilarity.user_id_2 == user_id,
                    User.id == UserSimilarity.user_id_1
                )
            )
        ).where(
            UserSimilarity.similarity_score >= 0.2,
            UserSimilarity.not_deleted_filter()
        ).order_by(desc(UserSimilarity.similarity_score)).limit(limit)

        result = await self.db.execute(query)

        similar_users = []
        for sim, user in result.all():
            # 检查缓存是否过期
            cache_age = (datetime.utcnow() - sim.last_calculated_at).total_seconds()
            if cache_age > self.SIMILARITY_CACHE_TTL:
                continue  # 跳过过期的缓存

            similar_users.append(UserSimilarityScore(
                user_id=user.id,
                username=user.username,
                avatar_url=user.avatar_url,
                similarity=sim.similarity_score,
                common_items=sim.common_items_count,
                common_subjects=sim.common_subjects or [],
                last_interaction=sim.last_calculated_at
            ))

        return similar_users

    async def _get_user_learned_items(
        self,
        user_id: UUID
    ) -> Set[UUID]:
        """获取用户已学习的物品ID集合"""
        query = select(UserItemInteraction.item_id).where(
            UserItemInteraction.user_id == user_id,
            UserItemInteraction.interaction_type.in_(["learned", "LEARNED", "completed", "COMPLETED"]),
            UserItemInteraction.not_deleted_filter()
        ).distinct()

        result = await self.db.execute(query)
        return {row[0] for row in result.all()}

    async def _generate_recommendations_from_users(
        self,
        user_id: UUID,
        similar_users: List[UserSimilarityScore],
        learned_items: Set[UUID],
        item_type: Optional[RecommendationItemType],
        subject_id: Optional[UUID],
        limit: int
    ) -> List[CollaborativeRecommendation]:
        """基于相似用户生成推荐"""
        recommendations = []
        item_scores = defaultdict(float)
        item_users = defaultdict(set)
        item_details = {}

        for similar_user in similar_users:
            # 获取该相似用户学过的物品
            user_items = await self._get_user_learned_items(similar_user.user_id)

            # 过滤掉当前用户已学过的物品
            new_items = user_items - learned_items

            for item_id in new_items:
                # 计算推荐分数：相似度 × 用户权重
                score = similar_user.similarity

                # 应用物品类型过滤
                if item_type:
                    actual_type = await self._get_item_type(item_id)
                    if actual_type != item_type.value:
                        continue

                # 应用学科过滤
                if subject_id:
                    item_subject = await self._get_item_subject(item_id)
                    if item_subject != subject_id:
                        continue

                item_scores[item_id] += score
                item_users[item_id].add(similar_user.user_id)

                # 缓存物品详情
                if item_id not in item_details:
                    item_details[item_id] = {
                        "title": await self._get_item_title(item_id),
                        "description": await self._get_item_description(item_id)
                    }

        # 按分数排序并生成推荐
        sorted_items = sorted(
            item_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:limit]

        for item_id, score in sorted_items:
            details = item_details.get(item_id, {})

            # 获取相似用户名
            similar_user_ids = list(item_users[item_id])[:3]
            similar_usernames = await self._get_usernames(similar_user_ids)

            recommendations.append(CollaborativeRecommendation(
                item_id=item_id,
                item_type=RecommendationItemType(await self._get_item_type(item_id)),
                title=details.get("title", "推荐内容"),
                description=details.get("description"),
                reason=f"和你进度相似的同学也在学",
                similar_users=list(item_users[item_id]),
                similar_usernames=similar_usernames,
                predicted_score=min(score / len(similar_users), 1.0),
                confidence=min(score, 1.0)
            ))

        return recommendations

    async def _get_cached_recommendations(
        self,
        user_id: UUID,
        item_type: Optional[RecommendationItemType]
    ) -> Optional[RecommendationCache]:
        """获取缓存的推荐"""
        query = select(RecommendationCache).where(
            RecommendationCache.user_id == user_id,
            RecommendationCache.recommendation_type == item_type.value if item_type else "collaborative",
            RecommendationCache.expires_at > datetime.utcnow(),
            RecommendationCache.not_deleted_filter()
        ).order_by(desc(RecommendationCache.generated_at)).first()

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def _cache_recommendations(
        self,
        user_id: UUID,
        recommendations: List[CollaborativeRecommendation],
        item_type: Optional[RecommendationItemType]
    ) -> None:
        """缓存推荐结果"""
        cache = RecommendationCache(
            user_id=user_id,
            recommendation_type=item_type.value if item_type else "collaborative",
            cached_recommendations=[r.model_dump() for r in recommendations],
            generated_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(seconds=self.RECOMMENDATION_CACHE_TTL)
        )

        self.db.add(cache)
        await self.db.flush()

    async def _get_item_title(self, item_id: UUID) -> Optional[str]:
        """获取物品标题"""
        # 尝试从 KnowledgeNode 获取
        node = await self.db.get(KnowledgeNode, item_id)
        if node:
            return node.name

        # 尝试从 Task 获取
        task = await self.db.get(Task, item_id)
        if task:
            return task.title

        return None

    async def _get_item_description(self, item_id: UUID) -> Optional[str]:
        """获取物品描述"""
        node = await self.db.get(KnowledgeNode, item_id)
        if node:
            return node.description

        task = await self.db.get(Task, item_id)
        if task:
            return task.description

        return None

    async def _get_item_type(self, item_id: UUID) -> Optional[str]:
        """获取物品类型"""
        node = await self.db.get(KnowledgeNode, item_id)
        if node:
            return "knowledge_node"

        task = await self.db.get(Task, item_id)
        if task:
            return "task"

        return "unknown"

    async def _get_item_subject(self, item_id: UUID) -> Optional[UUID]:
        """获取物品所属学科"""
        node = await self.db.get(KnowledgeNode, item_id)
        if node:
            return node.subject_id

        task = await self.db.get(Task, item_id)
        if task:
            return task.subject_id

        return None

    async def _get_usernames(self, user_ids: List[UUID]) -> List[str]:
        """获取用户名列表"""
        if not user_ids:
            return []

        query = select(User.username).where(User.id.in_(user_ids))
        result = await self.db.execute(query)
        return [row[0] for row in result.all()]


# 便捷函数
async def get_collaborative_recommendations(
    db: AsyncSession,
    user_id: UUID,
    limit: int = 10,
    item_type: Optional[RecommendationItemType] = None
) -> List[CollaborativeRecommendation]:
    """获取协同过滤推荐的便捷函数"""
    service = CollaborativeFilteringService(db)
    request = CollaborativeFilteringRequest(
        user_id=user_id,
        limit=limit,
        item_type=item_type
    )
    response = await service.get_recommendations(request)
    return response.recommendations
