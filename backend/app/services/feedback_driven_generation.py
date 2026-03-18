from __future__ import annotations
"""
Feedback-Driven Generation Service - Phase 2f

核心功能：
1. 收集用户对审查质量的反馈
2. 基于反馈请求内容重新生成
3. 跟踪反馈模式以改进审查准确性
4. 学习用户偏好

作者: Claude Code (Opus 4.5)
创建时间: 2026-01-25
"""

import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import timezone, datetime, timedelta
from enum import Enum
from typing import Any

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.agent_profiles import TaskType
from app.models.review_system import ReviewFeedback as ReviewFeedbackModel
from app.services.llm_service import get_llm_service_for_task
from app.services.review_history_service import get_review_history_service

# ============================================
# 数据模型
# ============================================


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)

class FeedbackType(str, Enum):
    """反馈类型"""
    RATING = "rating"                   # 评分反馈 (1-5星)
    QUALITY = "quality"                 # 质量反馈 (helpful/not_helpful)
    ACCURACY = "accuracy"               # 准确性反馈 (correct/incorrect)
    SPECIFICITY = "specificity"         # 具体性反馈 (too_vague/appropriate/too_detailed)
    REGENERATION_REQUEST = "regeneration_request"  # 重新生成请求


class RegenerationType(str, Enum):
    """重新生成类型"""
    IMPROVE_QUALITY = "improve_quality"           # 提升质量
    FIX_ISSUES = "fix_issues"                     # 修复问题
    CHANGE_STYLE = "change_style"                 # 改变风格
    ADD_DETAILS = "add_details"                   # 添加细节
    SIMPLIFY = "simplify"                         # 简化内容
    CUSTOM = "custom"                             # 自定义


class RegenerationStatus(str, Enum):
    """重新生成状态"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ReviewFeedback:
    """审查反馈"""
    feedback_id: str
    review_id: str
    user_id: str
    feedback_type: FeedbackType
    timestamp: str = ""

    # 评分反馈
    rating: int | None = None  # 1-5

    # 质量反馈
    was_helpful: bool | None = None

    # 准确性反馈
    was_accurate: bool | None = None
    inaccurate_points: list[str] = field(default_factory=list)

    # 具体性反馈
    specificity_level: str | None = None  # too_vague, appropriate, too_detailed

    # 自由文本反馈
    comments: str | None = None

    # 标签
    tags: list[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = _utcnow().isoformat()


@dataclass
class RegenerationRequest:
    """重新生成请求"""
    request_id: str
    original_content_id: str
    review_id: str
    user_id: str
    regeneration_type: RegenerationType

    # 请求详情
    improvement_hints: list[str] = field(default_factory=list)
    focus_areas: list[str] = field(default_factory=list)
    style_preferences: dict[str, Any] = field(default_factory=dict)
    custom_instructions: str | None = None

    # 状态
    status: RegenerationStatus = RegenerationStatus.PENDING
    created_at: str = ""
    completed_at: str | None = None

    # 结果
    new_content_id: str | None = None
    improvement_summary: str | None = None

    def __post_init__(self):
        if not self.created_at:
            self.created_at = _utcnow().isoformat()


@dataclass
class RegenerationResult:
    """重新生成结果"""
    request_id: str
    success: bool
    new_content: str | None = None
    new_content_id: str | None = None
    improvement_summary: str = ""
    changes_made: list[str] = field(default_factory=list)
    score_improvement: float = 0.0  # 分数提升量
    generation_time_ms: int = 0


@dataclass
class FeedbackPattern:
    """反馈模式（用于学习）"""
    pattern_id: str
    user_id: str
    feedback_count: int = 0

    # 统计数据
    avg_rating: float = 0.0
    helpful_rate: float = 0.0
    accuracy_rate: float = 0.0

    # 常见反馈
    common_issues: list[str] = field(default_factory=list)
    preferred_style: str | None = None
    detail_preference: str = "appropriate"  # too_vague, appropriate, too_detailed

    # 更新时间
    last_updated: str = ""


# ============================================
# Feedback-Driven Generation Service
# ============================================

class FeedbackDrivenGenerationService:
    """
    反馈驱动的内容生成服务

    职责：
    1. 收集并存储用户反馈
    2. 分析反馈模式
    3. 根据反馈触发内容重新生成
    4. 跟踪重新生成效果
    """

    def __init__(self, db_session: AsyncSession):
        self._db = db_session
        self._history_service = get_review_history_service(db_session)
        self._llm = get_llm_service_for_task(TaskType.STANDARD_RESPONSE)

        # 内存缓存（生产环境应使用Redis）
        self._feedbacks: dict[str, ReviewFeedback] = {}
        self._regeneration_requests: dict[str, RegenerationRequest] = {}
        self._feedback_patterns: dict[str, FeedbackPattern] = {}

    # ============================================
    # 反馈收集
    # ============================================

    async def submit_review_feedback(
        self,
        review_id: str,
        user_id: str,
        feedback_type: FeedbackType,
        rating: int | None = None,
        was_helpful: bool | None = None,
        was_accurate: bool | None = None,
        inaccurate_points: list[str] | None = None,
        specificity_level: str | None = None,
        comments: str | None = None,
        tags: list[str] | None = None,
    ) -> ReviewFeedback:
        """
        提交审查反馈

        Args:
            review_id: 审查ID
            user_id: 用户ID
            feedback_type: 反馈类型
            rating: 评分 (1-5)
            was_helpful: 是否有帮助
            was_accurate: 是否准确
            inaccurate_points: 不准确的点
            specificity_level: 具体性级别
            comments: 评论
            tags: 标签

        Returns:
            创建的反馈记录
        """
        logger.info(
            f"[FeedbackService] Receiving feedback for review {review_id} "
            f"from user {user_id}, type={feedback_type.value}"
        )

        # 验证审查存在
        review = await self._history_service.get_review_by_id(review_id)
        if not review:
            raise ValueError(f"Review {review_id} not found")

        # 创建反馈
        feedback = ReviewFeedback(
            feedback_id=f"fb_{uuid.uuid4().hex[:12]}",
            review_id=review_id,
            user_id=user_id,
            feedback_type=feedback_type,
            rating=rating,
            was_helpful=was_helpful,
            was_accurate=was_accurate,
            inaccurate_points=inaccurate_points or [],
            specificity_level=specificity_level,
            comments=comments,
            tags=tags or [],
        )

        # 存储反馈
        self._feedbacks[feedback.feedback_id] = feedback

        # 更新反馈模式
        await self._update_feedback_pattern(user_id, feedback)

        # 记录到历史服务
        await self._history_service.record_user_feedback(
            review_id=review_id,
            user_id=user_id,
            feedback_type=feedback_type.value,
            feedback_id=feedback.feedback_id,
            rating=rating,
            comment=comments,
            was_helpful=was_helpful,
            was_accurate=was_accurate,
            inaccurate_points=inaccurate_points,
            specificity_level=specificity_level,
            tags=tags,
        )

        logger.info(f"[FeedbackService] Feedback created: {feedback.feedback_id}")

        return feedback

    async def rate_review(
        self,
        review_id: str,
        user_id: str,
        rating: int,
        comments: str | None = None,
    ) -> ReviewFeedback:
        """
        简化的评分接口

        Args:
            review_id: 审查ID
            user_id: 用户ID
            rating: 评分 (1-5)
            comments: 可选评论

        Returns:
            反馈记录
        """
        if not 1 <= rating <= 5:
            raise ValueError("Rating must be between 1 and 5")

        return await self.submit_review_feedback(
            review_id=review_id,
            user_id=user_id,
            feedback_type=FeedbackType.RATING,
            rating=rating,
            was_helpful=rating >= 4,  # 4-5星视为有帮助
            comments=comments,
        )

    # ============================================
    # 内容重新生成
    # ============================================

    async def request_regeneration(
        self,
        original_content_id: str,
        review_id: str,
        user_id: str,
        regeneration_type: RegenerationType,
        improvement_hints: list[str] | None = None,
        focus_areas: list[str] | None = None,
        style_preferences: dict[str, Any] | None = None,
        custom_instructions: str | None = None,
    ) -> RegenerationRequest:
        """
        请求内容重新生成

        Args:
            original_content_id: 原内容ID
            review_id: 关联的审查ID
            user_id: 用户ID
            regeneration_type: 重新生成类型
            improvement_hints: 改进提示
            focus_areas: 关注领域
            style_preferences: 风格偏好
            custom_instructions: 自定义指令

        Returns:
            重新生成请求
        """
        logger.info(
            f"[FeedbackService] Regeneration requested for content {original_content_id} "
            f"by user {user_id}, type={regeneration_type.value}"
        )

        request = RegenerationRequest(
            request_id=f"regen_{uuid.uuid4().hex[:12]}",
            original_content_id=original_content_id,
            review_id=review_id,
            user_id=user_id,
            regeneration_type=regeneration_type,
            improvement_hints=improvement_hints or [],
            focus_areas=focus_areas or [],
            style_preferences=style_preferences or {},
            custom_instructions=custom_instructions,
        )

        self._regeneration_requests[request.request_id] = request

        logger.info(f"[FeedbackService] Regeneration request created: {request.request_id}")

        return request

    async def process_regeneration(
        self,
        request_id: str,
    ) -> RegenerationResult:
        """
        处理重新生成请求

        Args:
            request_id: 请求ID

        Returns:
            重新生成结果
        """
        import time
        start_time = time.time()

        request = self._regeneration_requests.get(request_id)
        if not request:
            raise ValueError(f"Regeneration request {request_id} not found")

        logger.info(f"[FeedbackService] Processing regeneration {request_id}")

        # 更新状态
        request.status = RegenerationStatus.IN_PROGRESS

        try:
            # 构建重新生成指令
            regen_prompt = self._build_regeneration_prompt(request)

            original_content = await self._resolve_original_content(request)
            regen_prompt = self._build_regeneration_prompt(request)

            system_prompt = (
                "你是一个严谨的内容优化助手。"
                "根据用户反馈和改进要求，对原始内容进行高质量重写。"
                "只输出优化后的内容，不要额外解释。"
            )
            user_prompt = (
                "原始内容:\n"
                f"{original_content}\n\n"
                "改进要求:\n"
                f"{regen_prompt}"
            )

            new_content = await self._llm.chat(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
            )
            new_content_id = f"content_{uuid.uuid4().hex[:12]}"

            # 更新请求状态
            request.status = RegenerationStatus.COMPLETED
            request.completed_at = _utcnow().isoformat()
            request.new_content_id = new_content_id
            request.improvement_summary = f"Content regenerated with {request.regeneration_type.value}"

            elapsed_ms = int((time.time() - start_time) * 1000)

            result = RegenerationResult(
                request_id=request_id,
                success=True,
                new_content=new_content,
                new_content_id=new_content_id,
                improvement_summary=request.improvement_summary,
                changes_made=self._summarize_changes(request),
                score_improvement=0.0,
                generation_time_ms=elapsed_ms,
            )

            logger.info(
                f"[FeedbackService] Regeneration completed: {request_id}, "
                f"time={elapsed_ms}ms"
            )

            return result

        except Exception as e:
            request.status = RegenerationStatus.FAILED
            logger.error(f"[FeedbackService] Regeneration failed: {e}")

            return RegenerationResult(
                request_id=request_id,
                success=False,
                improvement_summary=f"Regeneration failed: {str(e)}",
            )

    async def regenerate_with_feedback(
        self,
        content: str,
        review_id: str,
        user_id: str,
        feedback: ReviewFeedback,
    ) -> AsyncIterator[str]:
        """
        基于反馈重新生成内容（流式）

        这是供 Orchestrator 调用的主要接口

        Args:
            content: 原内容
            review_id: 审查ID
            user_id: 用户ID
            feedback: 用户反馈

        Yields:
            重新生成的内容片段
        """
        logger.info(
            f"[FeedbackService] Regenerating content based on feedback "
            f"from user {user_id}, review={review_id}"
        )

        # 根据反馈确定重新生成类型
        regen_type = self._infer_regeneration_type(feedback)

        # 构建改进提示
        improvement_hints = self._extract_improvement_hints(feedback)

        # 创建请求
        request = await self.request_regeneration(
            original_content_id=f"content_from_review_{review_id}",
            review_id=review_id,
            user_id=user_id,
            regeneration_type=regen_type,
            improvement_hints=improvement_hints,
        )

        # 流式生成（模拟）
        system_prompt = (
            "你是一个严谨的内容优化助手。"
            "根据用户反馈和改进要求，对原始内容进行高质量重写。"
            "只输出优化后的内容，不要额外解释。"
        )
        regen_prompt = self._build_regeneration_prompt(request)
        user_prompt = (
            "原始内容:\n"
            f"{content}\n\n"
            "改进要求:\n"
            f"{regen_prompt}"
        )

        improved_content = await self._llm.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
        )

        for chunk in improved_content.split():
            yield chunk + " "

        # 更新请求状态
        request.status = RegenerationStatus.COMPLETED
        request.completed_at = _utcnow().isoformat()

    # ============================================
    # 反馈模式分析
    # ============================================

    async def _update_feedback_pattern(
        self,
        user_id: str,
        feedback: ReviewFeedback,
    ) -> None:
        """更新用户反馈模式"""
        pattern = self._feedback_patterns.get(user_id)

        if not pattern:
            pattern = FeedbackPattern(
                pattern_id=f"pattern_{user_id}",
                user_id=user_id,
            )
            self._feedback_patterns[user_id] = pattern

        pattern.feedback_count += 1
        pattern.last_updated = _utcnow().isoformat()

        # 更新评分统计
        if feedback.rating is not None:
            old_avg = pattern.avg_rating
            n = pattern.feedback_count
            pattern.avg_rating = (old_avg * (n - 1) + feedback.rating) / n

        # 更新有用性统计
        if feedback.was_helpful is not None:
            old_rate = pattern.helpful_rate
            n = pattern.feedback_count
            helpful_val = 1.0 if feedback.was_helpful else 0.0
            pattern.helpful_rate = (old_rate * (n - 1) + helpful_val) / n

        # 更新准确性统计
        if feedback.was_accurate is not None:
            old_rate = pattern.accuracy_rate
            n = pattern.feedback_count
            accurate_val = 1.0 if feedback.was_accurate else 0.0
            pattern.accuracy_rate = (old_rate * (n - 1) + accurate_val) / n

        # 更新具体性偏好
        if feedback.specificity_level:
            pattern.detail_preference = feedback.specificity_level

        # 记录常见问题
        for point in feedback.inaccurate_points:
            if point not in pattern.common_issues:
                pattern.common_issues.append(point)
                # 限制最多保留10个
                if len(pattern.common_issues) > 10:
                    pattern.common_issues = pattern.common_issues[-10:]

    async def get_user_feedback_pattern(
        self,
        user_id: str,
    ) -> FeedbackPattern | None:
        """获取用户反馈模式"""
        return self._feedback_patterns.get(user_id)

    async def get_feedback_statistics(
        self,
        days: int = 30,
    ) -> dict[str, Any]:
        """
        获取反馈统计

        Args:
            days: 统计天数

        Returns:
            统计数据
        """
        cutoff = _utcnow() - timedelta(days=days)
        cutoff_str = cutoff.isoformat()

        # 筛选时间范围内的反馈
        result = await self._db.execute(
            select(ReviewFeedbackModel).where(ReviewFeedbackModel.created_at >= cutoff)
        )
        feedback_models = result.scalars().all()

        if not feedback_models:
            return {
                "total_feedbacks": 0,
                "avg_rating": 0.0,
                "helpful_rate": 0.0,
                "accuracy_rate": 0.0,
                "regeneration_requests": 0,
                "period_days": days,
            }

        # 计算统计
        ratings = [f.rating for f in feedback_models if f.rating is not None]
        helpful = [f.was_helpful for f in feedback_models if f.was_helpful is not None]
        accurate = [f.was_accurate for f in feedback_models if f.was_accurate is not None]

        avg_rating = sum(ratings) / len(ratings) if ratings else 0.0
        helpful_rate = sum(1 for h in helpful if h) / len(helpful) if helpful else 0.0
        accuracy_rate = sum(1 for a in accurate if a) / len(accurate) if accurate else 0.0

        # 重新生成请求统计
        regen_requests = [
            r for r in self._regeneration_requests.values()
            if r.created_at >= cutoff_str
        ]

        return {
            "total_feedbacks": len(feedback_models),
            "avg_rating": avg_rating,
            "helpful_rate": helpful_rate,
            "accuracy_rate": accuracy_rate,
            "regeneration_requests": len(regen_requests),
            "successful_regenerations": sum(
                1 for r in regen_requests
                if r.status == RegenerationStatus.COMPLETED
            ),
            "period_days": days,
        }

    # ============================================
    # 辅助方法
    # ============================================

    def _build_regeneration_prompt(self, request: RegenerationRequest) -> str:
        """构建重新生成提示词"""
        prompt_parts = []

        prompt_parts.append("请根据以下要求重新生成内容:")
        prompt_parts.append(f"重新生成类型: {request.regeneration_type.value}")

        if request.improvement_hints:
            prompt_parts.append(f"改进提示: {', '.join(request.improvement_hints)}")

        if request.focus_areas:
            prompt_parts.append(f"关注领域: {', '.join(request.focus_areas)}")

        if request.style_preferences:
            prompt_parts.append(f"风格偏好: {request.style_preferences}")

        if request.custom_instructions:
            prompt_parts.append(f"自定义指令: {request.custom_instructions}")

        return "\n".join(prompt_parts)

    def _summarize_changes(self, request: RegenerationRequest) -> list[str]:
        """总结变更"""
        changes = []

        type_descriptions = {
            RegenerationType.IMPROVE_QUALITY: "提升了整体内容质量",
            RegenerationType.FIX_ISSUES: "修复了识别的问题",
            RegenerationType.CHANGE_STYLE: "调整了表达风格",
            RegenerationType.ADD_DETAILS: "添加了更多细节",
            RegenerationType.SIMPLIFY: "简化了内容表达",
            RegenerationType.CUSTOM: "根据自定义指令调整",
        }

        changes.append(type_descriptions.get(
            request.regeneration_type,
            "进行了内容调整"
        ))

        if request.improvement_hints:
            changes.append(f"应用了{len(request.improvement_hints)}条改进建议")

        return changes

    def _infer_regeneration_type(self, feedback: ReviewFeedback) -> RegenerationType:
        """根据反馈推断重新生成类型"""
        if not feedback.was_accurate:
            return RegenerationType.FIX_ISSUES

        if feedback.specificity_level == "too_vague":
            return RegenerationType.ADD_DETAILS

        if feedback.specificity_level == "too_detailed":
            return RegenerationType.SIMPLIFY

        if feedback.rating is not None and feedback.rating < 3:
            return RegenerationType.IMPROVE_QUALITY

        return RegenerationType.IMPROVE_QUALITY

    def _extract_improvement_hints(self, feedback: ReviewFeedback) -> list[str]:
        """从反馈中提取改进提示"""
        hints = []

        if feedback.inaccurate_points:
            for point in feedback.inaccurate_points:
                hints.append(f"修正: {point}")

        if feedback.comments:
            hints.append(f"用户建议: {feedback.comments}")

        if feedback.specificity_level == "too_vague":
            hints.append("请添加更多具体细节和示例")
        elif feedback.specificity_level == "too_detailed":
            hints.append("请简化内容，保留核心要点")

        return hints

    async def _resolve_original_content(self, request: RegenerationRequest) -> str:
        if request.review_id:
            review = await self._history_service.get_review_by_id(request.review_id)
            if review and review.content_snapshot:
                return review.content_snapshot
        return request.original_content_id


# ============================================
# 全局实例管理
# ============================================

_feedback_services: dict[int, FeedbackDrivenGenerationService] = {}


def get_feedback_driven_generation_service(
    db_session: AsyncSession,
) -> FeedbackDrivenGenerationService:
    """获取FeedbackDrivenGenerationService实例"""
    session_id = id(db_session)
    if session_id not in _feedback_services:
        _feedback_services[session_id] = FeedbackDrivenGenerationService(db_session)
    return _feedback_services[session_id]
