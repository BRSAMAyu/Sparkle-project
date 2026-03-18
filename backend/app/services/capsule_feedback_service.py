"""
Capsule Feedback Service

处理胶囊反馈，更新用户推断偏好，重新计算胶囊质量分
"""
from __future__ import annotations
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.event_bus import event_bus
from app.core.event_types import CAPSULE_FEEDBACK_SUBMITTED, CAPSULE_REGENERATE_REQUESTED
from app.models.capsule_feedback import CapsuleFeedback, FeedbackCategory
from app.models.curiosity_capsule import CuriosityCapsule
from app.services.personalization.preference_service import PreferenceService


class CapsuleFeedbackService:
    """
    胶囊反馈服务

    核心功能：
    - 提交反馈
    - 更新用户推断偏好
    - 重新计算胶囊质量分
    """

    async def submit_feedback(
        self,
        user_id: UUID,
        capsule_id: UUID,
        db: AsyncSession,
        rating: int | None = None,
        helpful: bool | None = None,
        category: str | None = None,
        comment: str | None = None,
    ) -> CapsuleFeedback:
        """
        提交胶囊反馈

        Args:
            user_id: 用户ID
            capsule_id: 胶囊ID
            db: 数据库会话
            rating: 评分 (1-5)
            helpful: 是否有用 (点赞/点踩)
            category: 反馈分类
            comment: 用户评论

        Returns:
            反馈对象
        """
        # 检查胶囊是否存在
        capsule = await db.get(CuriosityCapsule, capsule_id)
        if not capsule:
            raise ValueError(f"Capsule {capsule_id} not found")

        if capsule.user_id != user_id:
            raise ValueError("User can only submit feedback for their own capsules")

        # 检查是否已有反馈
        existing = await db.execute(
            select(CapsuleFeedback).where(
                CapsuleFeedback.user_id == user_id,
                CapsuleFeedback.capsule_id == capsule_id,
            )
        )
        existing_feedback = existing.scalar_one_or_none()

        if existing_feedback:
            # 更新现有反馈
            if rating is not None:
                existing_feedback.rating = rating
            if helpful is not None:
                existing_feedback.helpful = helpful
            if category is not None:
                existing_feedback.category = category
            if comment is not None:
                existing_feedback.comment = comment

            feedback = existing_feedback
            logger.info(f"[Feedback] Updated feedback for capsule {capsule_id}")
        else:
            # 创建新反馈
            feedback = CapsuleFeedback(
                user_id=user_id,
                capsule_id=capsule_id,
                rating=rating,
                helpful=helpful,
                category=category,
                comment=comment,
            )
            db.add(feedback)
            logger.info(f"[Feedback] Created new feedback for capsule {capsule_id}")

        await db.flush()

        # 计算偏好变化
        depth_delta, curiosity_delta = feedback.calculate_preference_deltas()
        feedback.inferred_depth_delta = depth_delta
        feedback.inferred_curiosity_delta = curiosity_delta

        # 更新用户推断偏好
        await self._update_inferred_preferences(user_id, depth_delta, curiosity_delta, db)

        # 更新胶囊统计和质量分
        await self._recalculate_capsule_quality(capsule_id, db)

        await db.commit()
        await db.refresh(feedback)

        await event_bus.publish(
            CAPSULE_FEEDBACK_SUBMITTED,
            {
                "event_type": CAPSULE_FEEDBACK_SUBMITTED,
                "user_id": str(user_id),
                "capsule_id": str(capsule_id),
                "rating": rating,
                "helpful": helpful,
                "category": category,
                "depth_delta": depth_delta,
                "curiosity_delta": curiosity_delta,
            },
        )

        if abs(depth_delta or 0) > 0.15 or abs(curiosity_delta or 0) > 0.15:
            await event_bus.publish(
                CAPSULE_REGENERATE_REQUESTED,
                {
                    "event_type": CAPSULE_REGENERATE_REQUESTED,
                    "user_id": str(user_id),
                    "capsule_id": str(capsule_id),
                    "trigger_reason": "significant_feedback",
                    "depth_delta": depth_delta,
                    "curiosity_delta": curiosity_delta,
                },
            )

        return feedback

    async def _update_inferred_preferences(
        self,
        user_id: UUID,
        depth_delta: float | None,
        curiosity_delta: float | None,
        db: AsyncSession,
    ):
        """
        更新用户推断偏好

        基于反馈计算出的偏好变化，更新用户的推断偏好设置
        """
        if depth_delta is None and curiosity_delta is None:
            return

        pref_service = PreferenceService(db)
        prefs_center = await pref_service.get_preferences(user_id)

        # 更新推断偏好
        inferred = prefs_center.inferred or {}

        if depth_delta is not None:
            current_depth = inferred.get("depth_preference", 0.5)
            # 平滑更新，避免剧烈波动
            new_depth = max(0.0, min(1.0, current_depth + (depth_delta * 0.1)))
            inferred["depth_preference"] = new_depth
            logger.debug(f"[Feedback] Updated depth_preference: {current_depth} -> {new_depth}")

        if curiosity_delta is not None:
            current_curiosity = inferred.get("curiosity_preference", 0.5)
            new_curiosity = max(0.0, min(1.0, current_curiosity + (curiosity_delta * 0.1)))
            inferred["curiosity_preference"] = new_curiosity
            logger.debug(f"[Feedback] Updated curiosity_preference: {current_curiosity} -> {new_curiosity}")

        prefs_center.inferred = inferred
        await pref_service.save_preferences(user_id, prefs_center)

    async def _recalculate_capsule_quality(
        self,
        capsule_id: UUID,
        db: AsyncSession,
    ):
        """
        重新计算胶囊质量分

        基于所有反馈计算加权质量分
        """
        capsule = await db.get(CuriosityCapsule, capsule_id)
        if not capsule:
            return

        # 获取所有反馈
        result = await db.execute(
            select(CapsuleFeedback).where(CapsuleFeedback.capsule_id == capsule_id)
        )
        feedbacks = result.scalars().all()

        if not feedbacks:
            return

        # 计算质量分
        # 1. 评分权重 (40%)
        rating_scores = [f.rating for f in feedbacks if f.rating is not None]
        avg_rating = sum(rating_scores) / len(rating_scores) if rating_scores else 0
        rating_score = avg_rating / 5.0  # 归一化到 0-1

        # 2. 有用性权重 (30%)
        helpful_count = sum(1 for f in feedbacks if f.helpful is True)
        not_helpful_count = sum(1 for f in feedbacks if f.helpful is False)
        total_helpful = helpful_count + not_helpful_count
        helpful_score = helpful_count / total_helpful if total_helpful > 0 else 0.5

        # 3. 正面分类权重 (20%)
        positive_categories = [
            FeedbackCategory.JUST_RIGHT.value,
        ]
        positive_count = sum(1 for f in feedbacks if f.category in positive_categories)
        negative_categories = [
            FeedbackCategory.TOO_LONG.value,
            FeedbackCategory.TOO_SHORT.value,
            FeedbackCategory.TOO_COMPLEX.value,
            FeedbackCategory.TOO_SIMPLE.value,
            FeedbackCategory.IRRELEVANT.value,
        ]
        negative_count = sum(1 for f in feedbacks if f.category in negative_categories)
        total_categorized = positive_count + negative_count
        category_score = positive_count / total_categorized if total_categorized > 0 else 0.5

        # 4. 基础分 (10%) - 避免从未反馈的胶囊质量分为0
        base_score = 0.5

        # 综合质量分
        quality_score = (
            rating_score * 0.4 +
            helpful_score * 0.3 +
            category_score * 0.2 +
            base_score * 0.1
        )

        capsule.quality_score = round(quality_score, 3)
        capsule.feedback_count = len(feedbacks)

        await db.flush()
        logger.debug(f"[Feedback] Recalculated quality for capsule {capsule_id}: {quality_score:.3f}")

    async def get_capsule_feedbacks(
        self,
        capsule_id: UUID,
        db: AsyncSession,
    ) -> list[CapsuleFeedback]:
        """获取胶囊的所有反馈"""
        result = await db.execute(
            select(CapsuleFeedback).where(CapsuleFeedback.capsule_id == capsule_id)
        )
        return list(result.scalars().all())

    async def get_user_feedback_stats(
        self,
        user_id: UUID,
        db: AsyncSession,
    ) -> dict[str, Any]:
        """
        获取用户反馈统计

        Returns:
            {
                "total_feedbacks": int,
                "avg_rating": float,
                "helpful_count": int,
                "category_distribution": dict,
            }
        """
        result = await db.execute(
            select(CapsuleFeedback).where(CapsuleFeedback.user_id == user_id)
        )
        feedbacks = result.scalars().all()

        total = len(feedbacks)
        ratings = [f.rating for f in feedbacks if f.rating is not None]
        avg_rating = sum(ratings) / len(ratings) if ratings else None

        helpful_count = sum(1 for f in feedbacks if f.helpful is True)

        category_dist = {}
        for f in feedbacks:
            if f.category:
                category_dist[f.category] = category_dist.get(f.category, 0) + 1

        return {
            "total_feedbacks": total,
            "avg_rating": avg_rating,
            "helpful_count": helpful_count,
            "category_distribution": category_dist,
        }


# 全局单例
capsule_feedback_service = CapsuleFeedbackService()
