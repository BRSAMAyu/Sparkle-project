"""
Curiosity Capsule Service

整合新的胶囊生成服务，保持向后兼容
"""
import random
from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from loguru import logger

from app.models.curiosity_capsule import CuriosityCapsule
from app.models.user import User
from app.models.task import Task
from app.core.llm_client import llm_client
from app.services.personalization.preference_service import PreferenceService

# 导入新的增强服务
from app.services.capsule_generation_service import capsule_generation_service
from app.services.capsule_feedback_service import capsule_feedback_service
from app.services.capsule_favorite_service import capsule_favorite_service
from app.services.capsule_share_service import capsule_share_service


class CuriosityCapsuleService:
    """
    胶囊服务 - 整合增强功能

    向后兼容：
    - 保留原有方法
    - 新增方法委托给新的专用服务
    """

    # ========== 原有方法（向后兼容）==========

    async def generate_daily_capsule(
        self,
        user_id: UUID,
        db: AsyncSession,
        depth_preference: float = 0.5,
        curiosity_preference: float = 0.5,
    ) -> Optional[CuriosityCapsule]:
        """
        Generate a daily curiosity capsule for the user based on recent activity.

        增强版：使用新的生成服务，支持深度偏好控制
        """
        # 获取用户偏好
        user = await db.get(User, user_id)
        if not user:
            return None

        pref_service = PreferenceService(db)
        prefs_center = await pref_service.get_preferences(user_id)

        # 合并显式和推断偏好
        explicit_prefs = prefs_center.explicit or {}
        inferred_prefs = prefs_center.inferred or {}

        depth_pref = explicit_prefs.get("depth_preference", depth_preference)
        # 考虑推断偏好进行平滑调整
        inferred_depth = inferred_prefs.get("depth_preference")
        if inferred_depth is not None:
            depth_pref = (depth_pref * 0.7) + (inferred_depth * 0.3)

        curiosity_pref = explicit_prefs.get("curiosity_preference", curiosity_preference)
        inferred_curiosity = inferred_prefs.get("curiosity_preference")
        if inferred_curiosity is not None:
            curiosity_pref = (curiosity_pref * 0.7) + (inferred_curiosity * 0.3)

        # 如果好奇心偏好低于阈值，不自动生成
        if curiosity_pref < 0.3:
            logger.info(f"[Capsule] User {user_id} has low curiosity preference, skipping generation")
            return None

        # 使用新的生成服务
        try:
            job = await capsule_generation_service.generate_capsules_batch(
                user_id=user_id,
                db=db,
                depth_preference=depth_pref,
                curiosity_preference=curiosity_pref,
                generation_type="daily",
                requested_count=1,
            )

            if job.capsule_ids and len(job.capsule_ids) > 0:
                capsule = await db.get(CuriosityCapsule, job.capsule_ids[0])
                return capsule
        except Exception as e:
            logger.error(f"[Capsule] Enhanced generation failed, falling back: {e}")

        # 降级到原有逻辑
        return await self._generate_legacy_capsule(user_id, db, user)

    async def _generate_legacy_capsule(
        self,
        user_id: UUID,
        db: AsyncSession,
        user: User,
    ) -> Optional[CuriosityCapsule]:
        """
        原有的胶囊生成逻辑（作为降级方案）
        """
        # Get recent completed tasks to find a topic
        result = await db.execute(
            select(Task)
            .where(Task.user_id == user_id)
            .order_by(desc(Task.completed_at))
            .limit(5)
        )
        recent_tasks = result.scalars().all()

        topic = "General Knowledge"
        related_task = None

        if recent_tasks:
            # Pick a random task to elaborate on
            related_task = random.choice(recent_tasks)
            topic = related_task.title

        # Generate content using LLM
        prompt = f"""
        Generate a short, interesting 'Curiosity Capsule' (100-150 words) related to: "{topic}".
        Target audience: A college student.
        Tone: Engaging, inspiring, slightly surprising.
        Format: Markdown.
        Title: A catchy title.
        Content: The body text.
        """

        # For prototype speed, we'll use static generation
        title = f"Did you know about {topic}?"
        content = f"Here is a fascinating fact about **{topic}**...\n\nDid you know that exploring {topic} can lead to unexpected discoveries in other fields? Keep your curiosity alive!"

        # Save to DB
        capsule = CuriosityCapsule(
            user_id=user_id,
            title=title,
            content=content,
            related_subject=topic,
            related_task_id=related_task.id if related_task else None,
            is_read=False
        )

        db.add(capsule)
        await db.commit()
        await db.refresh(capsule)

        return capsule

    async def get_today_capsules(self, user_id: UUID, db: AsyncSession) -> List[CuriosityCapsule]:
        """
        Get unread capsules for today/recent.
        """
        result = await db.execute(
            select(CuriosityCapsule)
            .where(CuriosityCapsule.user_id == user_id, CuriosityCapsule.is_read == False)
            .order_by(desc(CuriosityCapsule.created_at))
        )
        return result.scalars().all()

    async def mark_as_read(self, capsule_id: UUID, db: AsyncSession):
        capsule = await db.get(CuriosityCapsule, capsule_id)
        if capsule:
            capsule.is_read = True
            await db.commit()

    # ========== 新增方法（委托给专用服务）==========

    async def generate_batch(
        self,
        user_id: UUID,
        db: AsyncSession,
        depth_preference: float = 0.5,
        curiosity_preference: float = 0.5,
        generation_type: str = "manual",
        requested_count: Optional[int] = None,
    ):
        """
        批量生成胶囊（委托给生成服务）
        """
        return await capsule_generation_service.generate_capsules_batch(
            user_id=user_id,
            db=db,
            depth_preference=depth_preference,
            curiosity_preference=curiosity_preference,
            generation_type=generation_type,
            requested_count=requested_count,
        )

    async def submit_feedback(
        self,
        user_id: UUID,
        capsule_id: UUID,
        db: AsyncSession,
        rating: Optional[int] = None,
        helpful: Optional[bool] = None,
        category: Optional[str] = None,
        comment: Optional[str] = None,
    ):
        """提交反馈（委托给反馈服务）"""
        return await capsule_feedback_service.submit_feedback(
            user_id=user_id,
            capsule_id=capsule_id,
            db=db,
            rating=rating,
            helpful=helpful,
            category=category,
            comment=comment,
        )

    async def toggle_favorite(
        self,
        user_id: UUID,
        capsule_id: UUID,
        db: AsyncSession,
        note: Optional[str] = None,
    ):
        """切换收藏状态（委托给收藏服务）"""
        return await capsule_favorite_service.toggle_favorite(
            user_id=user_id,
            capsule_id=capsule_id,
            db=db,
            note=note,
        )

    async def get_favorites(
        self,
        user_id: UUID,
        db: AsyncSession,
        limit: int = 50,
        offset: int = 0,
    ):
        """获取收藏列表（委托给收藏服务）"""
        return await capsule_favorite_service.get_user_favorites(
            user_id=user_id,
            db=db,
            limit=limit,
            offset=offset,
        )

    async def share_to_group(
        self,
        user_id: UUID,
        capsule_id: UUID,
        group_id: UUID,
        db: AsyncSession,
        message: Optional[str] = None,
    ):
        """分享到群组（委托给分享服务）"""
        return await capsule_share_service.share_to_group(
            user_id=user_id,
            capsule_id=capsule_id,
            group_id=group_id,
            db=db,
            message=message,
        )

    async def get_generation_jobs(
        self,
        user_id: UUID,
        db: AsyncSession,
        limit: int = 20,
    ):
        """获取生成任务列表（委托给生成服务）"""
        return await capsule_generation_service.get_user_generation_jobs(
            user_id=user_id,
            db=db,
            limit=limit,
        )


# 全局单例
curiosity_capsule_service = CuriosityCapsuleService()
