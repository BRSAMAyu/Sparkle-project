"""
Plan Matching Service
计划匹配服务 - P0: 任务→计划自动切换

功能:
- 基于向量相似度匹配任务与计划
- 考虑计划优先级和主计划状态
- 支持关键词提取和主题匹配
"""
from __future__ import annotations
from typing import Any
from uuid import UUID

import numpy as np
from loguru import logger
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plan import Plan, PlanPriority
from app.services.embedding_service import EmbeddingService


class PlanMatchingService:
    """
    计划匹配服务

    将任务内容与用户的活跃计划进行语义匹配，
    帮助系统自动切换到最相关的计划上下文。
    """

    # 相似度阈值：低于此值不匹配
    SIMILARITY_THRESHOLD = 0.3

    # 优先级权重加成
    PRIORITY_WEIGHTS = {
        PlanPriority.CRITICAL: 1.25,
        PlanPriority.HIGH: 1.15,
        PlanPriority.NORMAL: 1.0,
        PlanPriority.LOW: 0.9,
    }

    # 主计划权重加成
    PRIMARY_PLAN_WEIGHT = 1.1

    def __init__(
        self,
        db: AsyncSession,
        embedding_service: EmbeddingService | None = None,
        llm_service=None
    ):
        self.db = db
        self.embedding_service = embedding_service or EmbeddingService()
        self.llm_service = llm_service

    async def match_task_to_plan(
        self,
        user_id: UUID,
        task_content: str,
        task_type: str = "chat",
        current_plan_id: UUID | None = None
    ) -> Plan | None:
        """
        将任务匹配到最相关的计划

        Args:
            user_id: 用户 ID
            task_content: 任务内容（用户消息/任务描述）
            task_type: 任务类型
            current_plan_id: 当前计划 ID（用于避免不必要的切换）

        Returns:
            最匹配的计划，如果没有合适的匹配则返回 None
        """
        if not task_content or not task_content.strip():
            logger.debug("Empty task content, skipping plan matching")
            return None

        # 1. 获取用户活跃计划
        active_plans = await self._get_active_plans(user_id)

        if not active_plans:
            logger.debug(f"No active plans for user {user_id}")
            return None

        # 如果只有一个计划，直接返回
        if len(active_plans) == 1:
            return active_plans[0]

        # 2. 计算任务与每个计划的相似度
        try:
            plan_scores = await self._calculate_plan_scores(
                task_content=task_content,
                plans=active_plans,
                current_plan_id=current_plan_id
            )
        except Exception as e:
            logger.error(f"Error calculating plan scores: {e}")
            # 回退到主计划或第一个计划
            return self._get_fallback_plan(active_plans)

        if not plan_scores:
            return self._get_fallback_plan(active_plans)

        # 3. 选择得分最高的计划
        best_plan, best_score = max(plan_scores, key=lambda x: x[1])

        # 4. 检查是否达到切换阈值
        if best_score < self.SIMILARITY_THRESHOLD:
            logger.debug(
                f"Best match score {best_score:.3f} below threshold {self.SIMILARITY_THRESHOLD}, "
                f"keeping current plan"
            )
            # 返回当前计划或主计划
            if current_plan_id:
                for plan in active_plans:
                    if plan.id == current_plan_id:
                        return plan
            return self._get_fallback_plan(active_plans)

        logger.info(
            f"Matched task to plan {best_plan.id} ({best_plan.name}) "
            f"with score {best_score:.3f}"
        )
        return best_plan

    async def extract_task_keywords(self, task_context: dict[str, Any]) -> list[str]:
        """
        从任务上下文中提取关键词

        Args:
            task_context: 任务上下文

        Returns:
            关键词列表
        """
        content = task_context.get("content", "")
        task_type = task_context.get("type", "")

        if not content:
            return []

        # 简单实现：使用 jieba 或基于规则的分词
        # 完整实现可以使用 LLM 提取关键词
        if self.llm_service:
            try:
                keywords = await self._extract_keywords_with_llm(content, task_type)
                return keywords
            except Exception as e:
                logger.warning(f"LLM keyword extraction failed: {e}")

        # 回退到简单分词
        return self._simple_keyword_extraction(content)

    async def get_plan_context_summary(self, plan: Plan) -> str:
        """
        生成计划的上下文摘要（用于向量化）

        Args:
            plan: 计划对象

        Returns:
            计划摘要文本
        """
        parts = [plan.name]

        if plan.description:
            parts.append(plan.description)

        if plan.subject:
            parts.append(f"学科: {plan.subject}")

        # TRACKED(TD-008): 可以添加 milestones、recent tasks 等信息

        return " ".join(parts)

    # ========== 私有方法 ==========

    async def _get_active_plans(self, user_id: UUID) -> list[Plan]:
        """获取用户活跃计划"""
        query = (
            select(Plan)
            .where(
                and_(
                    Plan.user_id == user_id,
                    Plan.is_active
                )
            )
            .order_by(Plan.is_primary.desc(), Plan.created_at.desc())
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def _calculate_plan_scores(
        self,
        task_content: str,
        plans: list[Plan],
        current_plan_id: UUID | None = None
    ) -> list[tuple]:
        """
        计算任务与每个计划的匹配分数

        Returns:
            [(plan, score), ...] 列表
        """
        # 1. 获取任务向量
        task_embedding = await self.embedding_service.get_embedding(
            task_content,
            text_type="query"
        )
        task_vector = np.array(task_embedding)

        # 2. 获取每个计划的向量
        plan_contexts = []
        for plan in plans:
            context = await self.get_plan_context_summary(plan)
            plan_contexts.append(context)

        plan_embeddings = await self.embedding_service.batch_embeddings(
            plan_contexts,
            text_type="document"
        )

        # 3. 计算余弦相似度并应用权重
        scores = []
        for i, plan in enumerate(plans):
            plan_vector = np.array(plan_embeddings[i])

            # 余弦相似度
            similarity = self._cosine_similarity(task_vector, plan_vector)

            # 应用优先级权重
            priority = plan.priority or PlanPriority.NORMAL
            weight = self.PRIORITY_WEIGHTS.get(priority, 1.0)
            weighted_score = similarity * weight

            # 主计划加成
            if plan.is_primary:
                weighted_score *= self.PRIMARY_PLAN_WEIGHT

            # 当前计划轻微加成（避免频繁切换）
            if current_plan_id and plan.id == current_plan_id:
                weighted_score *= 1.05

            scores.append((plan, weighted_score))

        return scores

    @staticmethod
    def _cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
        """计算余弦相似度"""
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(np.dot(vec1, vec2) / (norm1 * norm2))

    def _get_fallback_plan(self, plans: list[Plan]) -> Plan | None:
        """获取回退计划（主计划或第一个计划）"""
        if not plans:
            return None

        # 优先返回主计划
        for plan in plans:
            if plan.is_primary:
                return plan

        # 返回第一个计划
        return plans[0]

    async def _extract_keywords_with_llm(
        self,
        content: str,
        task_type: str
    ) -> list[str]:
        """使用 LLM 提取关键词"""
        if not self.llm_service:
            return []

        prompt = f"""从以下任务描述中提取3-5个关键词，用于匹配学习计划：

任务类型: {task_type}
任务内容: {content}

只返回关键词列表，用逗号分隔。"""

        # 调用 LLM
        response = await self.llm_service.complete(prompt)
        return [k.strip() for k in response.split(",") if k.strip()]

    def _simple_keyword_extraction(self, content: str) -> list[str]:
        """简单关键词提取（基于规则）"""
        # 移除标点符号
        import re
        content = re.sub(r'[^\w\s]', ' ', content)

        # 分词（简单按空格分割）
        words = content.split()

        # 过滤停用词（简化版）
        stopwords = {
            '的', '是', '在', '我', '有', '和', '就', '不', '人', '都',
            '一', '这', '中', '大', '为', '上', '个', '国', '我们', '你',
            'the', 'is', 'at', 'which', 'on', 'a', 'an', 'and', 'or', 'but',
            'i', 'you', 'he', 'she', 'it', 'we', 'they', 'what', 'how',
        }

        keywords = []
        for word in words:
            word_lower = word.lower()
            if len(word) > 1 and word_lower not in stopwords:
                keywords.append(word)

        return keywords[:5]  # 返回前5个关键词
