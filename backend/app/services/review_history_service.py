from __future__ import annotations

"""
Review History Service - Phase 2c

核心功能：
1. 记录所有审查历史
2. 追踪用户反馈
3. 聚合审查数据用于学习
4. 提供审查趋势分析

作者: Claude Code (Opus 4.5)
创建时间: 2026-01-25
"""

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.review_system import (
    ReviewAppeal as ReviewAppealModel,
)
from app.models.review_system import (
    ReviewFeedback as ReviewFeedbackModel,
)
from app.models.review_system import (
    ReviewHistory as ReviewHistoryModel,
)
from app.models.review_system import (
    ReviewOverride as ReviewOverrideModel,
)

# ============================================
# 数据模型
# ============================================


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)

class ContentReviewFeedbackType(StrEnum):
    """用户反馈类型 — 对应 proto agent_service.proto ContentReviewFeedbackType"""
    SATISFIED = "satisfied"           # 用户满意（接受内容）
    UNSATISFIED = "unsatisfied"       # 用户不满意（拒绝内容）
    MODIFIED = "modified"             # 用户修改后接受
    REPORTED_ERROR = "reported_error" # 用户报告错误
    SKIPPED = "skipped"               # 用户跳过审查


# 向后兼容别名，逐步迁移
FeedbackType = ContentReviewFeedbackType


@dataclass
class ReviewHistoryEntry:
    """审查历史条目"""
    review_id: str
    target_id: str                    # 被审查内容的ID（如response_id）
    target_type: str                  # 'llm_response', 'plan', 'tool_result'
    user_id: str
    session_id: str
    timestamp: str

    # 审查结果
    decision: str                     # 'passed', 'failed', 'needs_refinement'
    overall_score: float
    metrics: list[dict[str, Any]]     # 审查指标列表
    issues_count: int
    critical_count: int
    warning_count: int

    # 反思信息（如果有）
    reflection_round: int = 0
    reflection_outcome: str | None = None
    score_delta: float = 0.0

    # 用户反馈
    user_feedback: str | None = None
    user_satisfied: bool | None = None
    feedback_timestamp: str | None = None

    # 审查元数据
    reviewer_model: str = ""
    review_duration_ms: int = 0
    requires_reflection: bool = False

    # 原始内容快照
    user_query: str | None = None
    content_snapshot: str | None = None


@dataclass
class FeedbackEntry:
    """用户反馈条目"""
    feedback_id: str
    review_id: str
    user_id: str
    feedback_type: FeedbackType
    timestamp: str

    # 反馈详情
    rating: int | None = None      # 1-5评分
    comment: str | None = None     # 用户评论
    issues_reported: list[str] = field(default_factory=list)

    # 上下文
    original_score: float = 0.0
    original_decision: str = ""
    was_reflected: bool = False


class OverrideDecision(StrEnum):
    """用户覆盖决策类型"""
    ACCEPT_DESPITE_FAILURE = "accept_despite_failure"  # 接受尽管审查失败
    REJECT_DESPITE_PASS = "reject_despite_pass"        # 拒绝尽管审查通过
    MODIFY_DECISION = "modify_decision"                # 修改决策


class AppealStatus(StrEnum):
    """申诉状态"""
    PENDING = "pending"                # 待处理
    IN_REVIEW = "in_review"            # 二次审查中
    RESOLVED = "resolved"              # 已解决
    REJECTED = "rejected"              # 已拒绝
    ESCALATED = "escalated"            # 已升级（人工处理）


@dataclass
class OverrideEntry:
    """用户覆盖条目"""
    override_id: str
    review_id: str
    user_id: str
    timestamp: str

    # 覆盖详情
    original_decision: str             # 原审查决策
    new_decision: str                  # 用户新决策
    override_type: OverrideDecision    # 覆盖类型
    reason: str                        # 用户理由

    # 审计信息
    was_correct: bool | None = None # 后续验证：用户覆盖是否正确
    admin_reviewed: bool = False       # 是否被管理员审查


@dataclass
class AppealEntry:
    """审查申诉条目"""
    appeal_id: str
    review_id: str
    user_id: str
    timestamp: str

    # 申诉内容
    appeal_reason: str                 # 申诉理由
    issues_with_review: list[str] = field(default_factory=list)  # 审查中的问题

    # 状态追踪
    status: AppealStatus = AppealStatus.PENDING
    assigned_to: str | None = None  # 分配给谁处理

    # 二次审查结果
    secondary_review_id: str | None = None
    secondary_decision: str | None = None
    secondary_score: float | None = None

    # 解决信息
    resolution: str | None = None   # 解决方案
    resolved_by: str | None = None  # 解决者
    resolved_at: str | None = None  # 解决时间


@dataclass
class ReviewAggregation:
    """审查聚合统计"""
    period: str                       # 'daily', 'weekly', 'monthly'
    start_date: str
    end_date: str

    total_reviews: int = 0
    passed_reviews: int = 0
    failed_reviews: int = 0
    avg_score: float = 0.0

    # 反思统计
    reflection_triggered: int = 0
    reflection_success: int = 0
    avg_score_improvement: float = 0.0

    # 用户反馈统计
    feedback_count: int = 0
    satisfaction_rate: float = 0.0

    # 问题统计
    common_issues: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ReviewTrend:
    """审查趋势分析"""
    metric_name: str
    trend: str                        # 'improving', 'stable', 'declining'
    current_avg: float
    previous_avg: float
    change_percent: float
    data_points: list[float]          # 最近的数据点


# ============================================
# Review History Service
# ============================================

class ReviewHistoryService:
    """
    审查历史服务

    职责：
    1. 持久化审查历史记录
    2. 记录用户反馈
    3. 提供历史查询和聚合
    4. 支持学习循环
    """

    def __init__(self, db_session: AsyncSession):
        self._db = db_session

    @staticmethod
    def _parse_uuid(value: str | None) -> uuid.UUID | None:
        if not value:
            return None
        try:
            return uuid.UUID(str(value))
        except ValueError:
            return None

    @staticmethod
    def _format_dt(value: datetime | None) -> str | None:
        return value.isoformat() if value else None

    def _to_review_entry(self, model: ReviewHistoryModel) -> ReviewHistoryEntry:
        return ReviewHistoryEntry(
            review_id=model.review_id,
            target_id=model.target_id,
            target_type=model.target_type,
            user_id=str(model.user_id) if model.user_id else "",
            session_id=model.session_id or "",
            timestamp=self._format_dt(model.created_at) or "",
            decision=model.decision,
            overall_score=model.overall_score or 0.0,
            metrics=model.metrics or [],
            issues_count=model.issues_count or 0,
            critical_count=model.critical_count or 0,
            warning_count=model.warning_count or 0,
            reflection_round=model.reflection_round or 0,
            reflection_outcome=model.reflection_outcome,
            score_delta=model.score_delta or 0.0,
            user_feedback=model.user_feedback,
            user_satisfied=model.user_satisfied,
            feedback_timestamp=self._format_dt(model.feedback_timestamp),
            reviewer_model=model.reviewer_model or "",
            review_duration_ms=model.review_duration_ms or 0,
            requires_reflection=bool(model.requires_reflection),
            user_query=model.user_query,
            content_snapshot=model.content_snapshot,
        )

    def _to_feedback_entry(self, model: ReviewFeedbackModel) -> FeedbackEntry:
        try:
            feedback_type = FeedbackType(model.feedback_type)
        except ValueError:
            feedback_type = ContentReviewFeedbackType.SKIPPED
        return FeedbackEntry(
            feedback_id=model.feedback_id,
            review_id=model.review_id,
            user_id=str(model.user_id) if model.user_id else "",
            feedback_type=feedback_type,
            timestamp=self._format_dt(model.created_at) or "",
            rating=model.rating,
            comment=model.comment,
            issues_reported=model.issues_reported or [],
            original_score=model.original_score or 0.0,
            original_decision=model.original_decision or "",
            was_reflected=bool(model.was_reflected),
        )

    def _to_override_entry(self, model: ReviewOverrideModel) -> OverrideEntry:
        return OverrideEntry(
            override_id=model.override_id,
            review_id=model.review_id,
            user_id=str(model.user_id) if model.user_id else "",
            timestamp=self._format_dt(model.created_at) or "",
            original_decision=model.original_decision,
            new_decision=model.new_decision,
            override_type=OverrideDecision(model.override_type),
            reason=model.reason or "",
            was_correct=model.was_correct,
            admin_reviewed=bool(model.admin_reviewed),
        )

    def _to_appeal_entry(self, model: ReviewAppealModel) -> AppealEntry:
        status = AppealStatus(model.status) if model.status else AppealStatus.PENDING
        return AppealEntry(
            appeal_id=model.appeal_id,
            review_id=model.review_id,
            user_id=str(model.user_id) if model.user_id else "",
            timestamp=self._format_dt(model.created_at) or "",
            appeal_reason=model.appeal_reason,
            issues_with_review=model.issues_with_review or [],
            status=status,
            assigned_to=model.assigned_to,
            secondary_review_id=model.secondary_review_id,
            secondary_decision=model.secondary_decision,
            secondary_score=model.secondary_score,
            resolution=model.resolution,
            resolved_by=model.resolved_by,
            resolved_at=self._format_dt(model.resolved_at),
        )

    # ============================================
    # 记录保存
    # ============================================

    async def record_review(
        self,
        review_id: str,
        target_id: str,
        target_type: str,
        user_id: str,
        session_id: str,
        decision: str,
        overall_score: float,
        metrics: list[dict[str, Any]],
        issues_count: int,
        critical_count: int,
        warning_count: int,
        reviewer_model: str = "",
        review_duration_ms: int = 0,
        requires_reflection: bool = False,
        content_snapshot: str | None = None,
        user_query: str | None = None,
        **kwargs
    ) -> ReviewHistoryEntry:
        """
        记录审查历史

        Args:
            review_id: 审查ID
            target_id: 被审查内容ID
            target_type: 内容类型
            user_id: 用户ID
            session_id: 会话ID
            decision: 审查决策
            overall_score: 总分
            metrics: 指标列表
            issues_count: 问题数量
            critical_count: 严重问题数
            warning_count: 警告问题数
            reviewer_model: 审查模型
            review_duration_ms: 审查耗时
            requires_reflection: 是否需要反思

        Returns:
            ReviewHistoryEntry: 保存的历史条目
        """
        model = ReviewHistoryModel(
            review_id=review_id,
            target_id=target_id,
            target_type=target_type,
            user_id=self._parse_uuid(user_id),
            session_id=session_id or None,
            decision=decision,
            overall_score=overall_score,
            metrics=metrics,
            issues_count=issues_count,
            critical_count=critical_count,
            warning_count=warning_count,
            reviewer_model=reviewer_model,
            review_duration_ms=review_duration_ms,
            requires_reflection=requires_reflection,
            content_snapshot=content_snapshot,
            user_query=user_query,
        )

        self._db.add(model)
        await self._db.flush()
        entry = self._to_review_entry(model)

        logger.info(
            f"[ReviewHistory] Recorded review {review_id}: "
            f"{decision}, score={overall_score:.2f}"
        )

        return entry

    async def record_reflection(
        self,
        review_id: str,
        reflection_round: int,
        outcome: str,
        score_delta: float,
    ) -> None:
        """
        更新审查记录，添加反思信息

        Args:
            review_id: 原审查ID
            reflection_round: 反思轮次
            outcome: 反思结果
            score_delta: 分数变化
        """
        result = await self._db.execute(
            select(ReviewHistoryModel).where(ReviewHistoryModel.review_id == review_id)
        )
        model = result.scalar_one_or_none()
        if not model:
            return

        model.reflection_round = reflection_round
        model.reflection_outcome = outcome
        model.score_delta = score_delta
        await self._db.flush()

        logger.info(
            f"[ReviewHistory] Updated reflection for {review_id}: "
            f"{outcome}, delta={score_delta:+.2f}"
        )

    async def record_user_feedback(
        self,
        review_id: str,
        user_id: str,
        feedback_type: FeedbackType,
        feedback_id: str | None = None,
        rating: int | None = None,
        comment: str | None = None,
        issues_reported: list[str] | None = None,
        was_helpful: bool | None = None,
        was_accurate: bool | None = None,
        inaccurate_points: list[str] | None = None,
        specificity_level: str | None = None,
        tags: list[str] | None = None,
    ) -> FeedbackEntry:
        """
        记录用户反馈

        Args:
            review_id: 审查ID
            user_id: 用户ID
            feedback_type: 反馈类型
            rating: 评分（1-5）
            comment: 用户评论
            issues_reported: 用户报告的问题

        Returns:
            FeedbackEntry: 保存的反馈条目
        """
        # 获取原审查记录
        review_result = await self._db.execute(
            select(ReviewHistoryModel).where(ReviewHistoryModel.review_id == review_id)
        )
        original_review = review_result.scalar_one_or_none()
        if original_review:
            feedback_val = feedback_type.value if isinstance(feedback_type, FeedbackType) else str(feedback_type)
            original_review.user_feedback = feedback_val
            original_review.user_satisfied = (feedback_val == "satisfied")
            original_review.feedback_timestamp = _utcnow()

        feedback_model = ReviewFeedbackModel(
            feedback_id=feedback_id or f"fb_{uuid.uuid4().hex[:12]}",
            review_id=review_id,
            user_id=self._parse_uuid(user_id),
            feedback_type=feedback_type.value if isinstance(feedback_type, FeedbackType) else str(feedback_type),
            rating=rating,
            comment=comment,
            issues_reported=issues_reported or [],
            original_score=original_review.overall_score if original_review else 0.0,
            original_decision=original_review.decision if original_review else "",
            was_reflected=bool(original_review.reflection_round) if original_review else False,
            was_helpful=was_helpful,
            was_accurate=was_accurate,
            inaccurate_points=inaccurate_points or [],
            specificity_level=specificity_level,
            tags=tags or [],
        )

        self._db.add(feedback_model)
        await self._db.flush()
        feedback = self._to_feedback_entry(feedback_model)

        logger.info(
            f"[ReviewHistory] Recorded feedback {feedback.feedback_id}: "
            f"{feedback_val} for review {review_id}"
        )

        return feedback

    # ============================================
    # 历史查询
    # ============================================

    async def get_review_history(
        self,
        user_id: str | None = None,
        session_id: str | None = None,
        target_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ReviewHistoryEntry]:
        """
        获取审查历史

        Args:
            user_id: 按用户筛选
            session_id: 按会话筛选
            target_type: 按内容类型筛选
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            审查历史列表
        """
        query = select(ReviewHistoryModel)
        if user_id:
            user_uuid = self._parse_uuid(user_id)
            if user_uuid:
                query = query.where(ReviewHistoryModel.user_id == user_uuid)
        if session_id:
            query = query.where(ReviewHistoryModel.session_id == session_id)
        if target_type:
            query = query.where(ReviewHistoryModel.target_type == target_type)

        query = query.order_by(ReviewHistoryModel.created_at.desc()).offset(offset).limit(limit)
        result = await self._db.execute(query)
        models = result.scalars().all()
        return [self._to_review_entry(model) for model in models]

    async def get_review_by_id(self, review_id: str) -> ReviewHistoryEntry | None:
        """根据ID获取审查记录"""
        result = await self._db.execute(
            select(ReviewHistoryModel).where(ReviewHistoryModel.review_id == review_id)
        )
        model = result.scalar_one_or_none()
        if not model:
            return None
        return self._to_review_entry(model)

    async def get_feedback_history(
        self,
        user_id: str | None = None,
        review_id: str | None = None,
        limit: int = 100,
    ) -> list[FeedbackEntry]:
        """获取反馈历史"""
        valid_types = [ft.value for ft in FeedbackType]
        query = select(ReviewFeedbackModel).where(ReviewFeedbackModel.feedback_type.in_(valid_types))
        if user_id:
            user_uuid = self._parse_uuid(user_id)
            if user_uuid:
                query = query.where(ReviewFeedbackModel.user_id == user_uuid)
        if review_id:
            query = query.where(ReviewFeedbackModel.review_id == review_id)

        query = query.order_by(ReviewFeedbackModel.created_at.desc()).limit(limit)
        result = await self._db.execute(query)
        models = result.scalars().all()
        return [self._to_feedback_entry(model) for model in models]

    # ============================================
    # 聚合统计
    # ============================================

    async def get_aggregation(
        self,
        period: str = "daily",
        start_date: str | None = None,
        end_date: str | None = None,
        user_id: str | None = None,
    ) -> ReviewAggregation:
        """
        获取聚合统计

        Args:
            period: 时间周期
            start_date: 开始日期
            end_date: 结束日期
            user_id: 用户筛选

        Returns:
            审查聚合统计
        """
        # 解析日期范围
        if not end_date:
            end_date = _utcnow().isoformat()
        if not start_date:
            if period == "daily":
                start_date = (_utcnow() - timedelta(days=1)).isoformat()
            elif period == "weekly":
                start_date = (_utcnow() - timedelta(days=7)).isoformat()
            else:  # monthly
                start_date = (_utcnow() - timedelta(days=30)).isoformat()

        start_dt = datetime.fromisoformat(start_date)
        end_dt = datetime.fromisoformat(end_date)

        query = select(ReviewHistoryModel).where(
            ReviewHistoryModel.created_at >= start_dt,
            ReviewHistoryModel.created_at <= end_dt,
        )
        if user_id:
            user_uuid = self._parse_uuid(user_id)
            if user_uuid:
                query = query.where(ReviewHistoryModel.user_id == user_uuid)

        result = await self._db.execute(query)
        models = result.scalars().all()
        reviews = [self._to_review_entry(model) for model in models]

        # 计算统计
        total = len(reviews)
        passed = sum(1 for r in reviews if r.decision == "passed")
        failed = sum(1 for r in reviews if r.decision == "failed")

        avg_score = sum(r.overall_score for r in reviews) / total if total > 0 else 0.0

        reflection_triggered = sum(1 for r in reviews if r.requires_reflection)
        reflection_success = sum(
            1 for r in reviews
            if r.reflection_outcome in ["fixed", "improved"]
        )

        avg_score_improvement = 0.0
        reflected = [r for r in reviews if r.score_delta != 0]
        if reflected:
            avg_score_improvement = sum(r.score_delta for r in reflected) / len(reflected)

        # 用户反馈统计
        feedback_query = select(ReviewFeedbackModel).where(
            ReviewFeedbackModel.created_at >= start_dt,
            ReviewFeedbackModel.created_at <= end_dt,
        )
        if user_id:
            user_uuid = self._parse_uuid(user_id)
            if user_uuid:
                feedback_query = feedback_query.where(ReviewFeedbackModel.user_id == user_uuid)

        feedback_result = await self._db.execute(feedback_query)
        feedback_models = feedback_result.scalars().all()
        feedbacks = [self._to_feedback_entry(model) for model in feedback_models]

        satisfaction_rate = 0.0
        if feedbacks:
            satisfied = sum(1 for f in feedbacks if f.feedback_type == ContentReviewFeedbackType.SATISFIED)
            satisfaction_rate = satisfied / len(feedbacks)

        # 常见问题统计
        all_issues = []
        for r in reviews:
            for metric in r.metrics:
                if not metric.get("passed", True):
                    all_issues.append(metric.get("metric", "unknown"))

        from collections import Counter
        common_issues = [
            {"issue": issue, "count": count}
            for issue, count in Counter(all_issues).most_common(5)
        ]

        return ReviewAggregation(
            period=period,
            start_date=start_date,
            end_date=end_date,
            total_reviews=total,
            passed_reviews=passed,
            failed_reviews=failed,
            avg_score=avg_score,
            reflection_triggered=reflection_triggered,
            reflection_success=reflection_success,
            avg_score_improvement=avg_score_improvement,
            feedback_count=len(feedbacks),
            satisfaction_rate=satisfaction_rate,
            common_issues=common_issues,
        )

    async def get_review_trends(
        self,
        metric_name: str,
        days: int = 7,
        user_id: str | None = None,
    ) -> ReviewTrend:
        """
        获取审查趋势

        Args:
            metric_name: 指标名称
            days: 分析天数
            user_id: 用户筛选

        Returns:
            审查趋势分析
        """
        end_date = _utcnow()
        start_date = end_date - timedelta(days=days)

        query = select(ReviewHistoryModel).where(
            ReviewHistoryModel.created_at >= start_date,
            ReviewHistoryModel.created_at <= end_date,
        )
        if user_id:
            user_uuid = self._parse_uuid(user_id)
            if user_uuid:
                query = query.where(ReviewHistoryModel.user_id == user_uuid)

        result = await self._db.execute(query)
        models = result.scalars().all()
        reviews = [self._to_review_entry(model) for model in models]

        # 提取指定指标的数据
        data_points = []
        for r in reviews:
            for metric in r.metrics:
                if metric.get("metric") == metric_name:
                    data_points.append(metric.get("score", 0.0))
                    break

        if len(data_points) < 2:
            return ReviewTrend(
                metric_name=metric_name,
                trend="stable",
                current_avg=sum(data_points) / len(data_points) if data_points else 0.0,
                previous_avg=0.0,
                change_percent=0.0,
                data_points=data_points,
            )

        # 计算趋势
        mid = len(data_points) // 2
        current_avg = sum(data_points[mid:]) / len(data_points[mid:])
        previous_avg = sum(data_points[:mid]) / len(data_points[:mid])

        change_percent = 0.0
        if previous_avg > 0:
            change_percent = ((current_avg - previous_avg) / previous_avg) * 100

        if change_percent > 5:
            trend = "improving"
        elif change_percent < -5:
            trend = "declining"
        else:
            trend = "stable"

        return ReviewTrend(
            metric_name=metric_name,
            trend=trend,
            current_avg=current_avg,
            previous_avg=previous_avg,
            change_percent=change_percent,
            data_points=data_points,
        )

    # ============================================
    # 学习数据导出
    # ============================================

    async def export_learning_data(
        self,
        format: str = "json",
    ) -> str:
        """
        导出学习数据

        用于训练或微调审查模型

        Args:
            format: 导出格式 ('json', 'csv')

        Returns:
            序列化的数据
        """
        review_result = await self._db.execute(select(ReviewHistoryModel))
        feedback_result = await self._db.execute(select(ReviewFeedbackModel))
        reviews = [self._to_review_entry(model) for model in review_result.scalars().all()]
        feedbacks = [self._to_feedback_entry(model) for model in feedback_result.scalars().all()]

        learning_data = {
            "reviews": [asdict(r) for r in reviews],
            "feedbacks": [asdict(f) for f in feedbacks],
            "export_timestamp": _utcnow().isoformat(),
            "total_count": len(reviews),
        }

        if format == "json":
            return json.dumps(learning_data, ensure_ascii=False, indent=2)
        else:
            # CSV format could be added here
            return json.dumps(learning_data)

    async def get_misclassified_reviews(
        self,
        threshold: float = 0.3,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """
        获取可能误判的审查记录

        误判定义：审查未通过但用户表示满意

        Args:
            threshold: 分数差异阈值
            limit: 返回数量限制

        Returns:
            可能误判的记录列表
        """
        misclassified = []

        review_result = await self._db.execute(select(ReviewHistoryModel))
        for model in review_result.scalars().all():
            entry = self._to_review_entry(model)
            # 检查是否有用户反馈
            if entry.user_feedback == ContentReviewFeedbackType.SATISFIED.value and not entry.user_satisfied:
                # 审查未通过但用户满意 -> 可能误判
                misclassified.append({
                    "review_id": entry.review_id,
                    "review_decision": entry.decision,
                    "review_score": entry.overall_score,
                    "user_feedback": entry.user_feedback,
                    "timestamp": entry.timestamp,
                    "severity": "high" if entry.overall_score < threshold else "medium",
                })

        misclassified.sort(key=lambda x: x["timestamp"], reverse=True)
        return misclassified[:limit]

    # ============================================
    # Phase 2e: 用户覆盖与申诉
    # ============================================

    async def record_user_override(
        self,
        review_id: str,
        user_id: str,
        original_decision: str,
        new_decision: str,
        reason: str,
    ) -> OverrideEntry:
        """
        记录用户覆盖审查决策

        当用户不同意审查结果并选择覆盖时调用

        Args:
            review_id: 审查ID
            user_id: 用户ID
            original_decision: 原审查决策
            new_decision: 用户新决策
            reason: 用户覆盖理由

        Returns:
            OverrideEntry: 保存的覆盖条目
        """
        # 确定覆盖类型
        if original_decision == "failed" and new_decision == "passed":
            override_type = OverrideDecision.ACCEPT_DESPITE_FAILURE
        elif original_decision == "passed" and new_decision == "failed":
            override_type = OverrideDecision.REJECT_DESPITE_PASS
        else:
            override_type = OverrideDecision.MODIFY_DECISION

        override_model = ReviewOverrideModel(
            override_id=f"ovr_{uuid.uuid4().hex[:12]}",
            review_id=review_id,
            user_id=self._parse_uuid(user_id),
            original_decision=original_decision,
            new_decision=new_decision,
            override_type=override_type.value,
            reason=reason,
        )

        self._db.add(override_model)

        # 更新原审查记录
        review_result = await self._db.execute(
            select(ReviewHistoryModel).where(ReviewHistoryModel.review_id == review_id)
        )
        entry_model = review_result.scalar_one_or_none()
        if entry_model:
            entry_model.user_feedback = f"override:{new_decision}"
            entry_model.user_satisfied = (new_decision == "passed")
            entry_model.feedback_timestamp = _utcnow()

        await self._db.flush()
        override = self._to_override_entry(override_model)

        logger.info(
            f"[ReviewHistory] Recorded override {override.override_id}: "
            f"{original_decision} -> {new_decision} for review {review_id}"
        )

        return override

    async def record_review_appeal(
        self,
        review_id: str,
        user_id: str,
        appeal_reason: str,
        issues_with_review: list[str] | None = None,
    ) -> AppealEntry:
        """
        记录审查申诉

        当用户认为审查本身有问题时调用

        Args:
            review_id: 审查ID
            user_id: 用户ID
            appeal_reason: 申诉理由
            issues_with_review: 审查中的问题列表

        Returns:
            AppealEntry: 保存的申诉条目
        """
        appeal_model = ReviewAppealModel(
            appeal_id=f"apl_{uuid.uuid4().hex[:12]}",
            review_id=review_id,
            user_id=self._parse_uuid(user_id),
            appeal_reason=appeal_reason,
            issues_with_review=issues_with_review or [],
            status=AppealStatus.PENDING.value,
        )

        self._db.add(appeal_model)
        await self._db.flush()
        appeal = self._to_appeal_entry(appeal_model)

        logger.info(
            f"[ReviewHistory] Recorded appeal {appeal.appeal_id}: "
            f"for review {review_id}, reason: {appeal_reason[:50]}..."
        )

        return appeal

    async def get_appeal_queue(
        self,
        status: AppealStatus | None = None,
        limit: int = 50,
    ) -> list[AppealEntry]:
        """
        获取待处理申诉队列

        Args:
            status: 按状态筛选（None表示待处理）
            limit: 返回数量限制

        Returns:
            申诉条目列表
        """
        query = select(ReviewAppealModel)
        if status is None:
            query = query.where(
                ReviewAppealModel.status.in_(
                    [AppealStatus.PENDING.value, AppealStatus.IN_REVIEW.value]
                )
            )
        else:
            query = query.where(ReviewAppealModel.status == status.value)

        query = query.order_by(ReviewAppealModel.created_at.asc()).limit(limit)
        result = await self._db.execute(query)
        models = result.scalars().all()
        return [self._to_appeal_entry(model) for model in models]

    async def update_appeal_status(
        self,
        appeal_id: str,
        status: AppealStatus,
        resolution: str | None = None,
        resolved_by: str | None = None,
        secondary_review_id: str | None = None,
        secondary_decision: str | None = None,
        secondary_score: float | None = None,
    ) -> AppealEntry | None:
        """
        更新申诉状态

        Args:
            appeal_id: 申诉ID
            status: 新状态
            resolution: 解决方案
            resolved_by: 解决者
            secondary_review_id: 二次审查ID
            secondary_decision: 二次审查决策
            secondary_score: 二次审查分数

        Returns:
            更新后的申诉条目
        """
        result = await self._db.execute(
            select(ReviewAppealModel).where(ReviewAppealModel.appeal_id == appeal_id)
        )
        model = result.scalar_one_or_none()
        if not model:
            return None

        model.status = status.value
        if resolution:
            model.resolution = resolution
        if resolved_by:
            model.resolved_by = resolved_by
            model.resolved_at = _utcnow()
        if secondary_review_id:
            model.secondary_review_id = secondary_review_id
        if secondary_decision:
            model.secondary_decision = secondary_decision
        if secondary_score is not None:
            model.secondary_score = secondary_score

        await self._db.flush()

        logger.info(
            f"[ReviewHistory] Updated appeal {appeal_id}: status={status.value}"
        )
        return self._to_appeal_entry(model)

    async def get_appeal_by_id(self, appeal_id: str) -> AppealEntry | None:
        """根据ID获取申诉"""
        result = await self._db.execute(
            select(ReviewAppealModel).where(ReviewAppealModel.appeal_id == appeal_id)
        )
        model = result.scalar_one_or_none()
        if not model:
            return None
        return self._to_appeal_entry(model)

    async def get_override_history(
        self,
        user_id: str | None = None,
        review_id: str | None = None,
        limit: int = 100,
    ) -> list[OverrideEntry]:
        """获取覆盖历史"""
        query = select(ReviewOverrideModel)
        if user_id:
            user_uuid = self._parse_uuid(user_id)
            if user_uuid:
                query = query.where(ReviewOverrideModel.user_id == user_uuid)
        if review_id:
            query = query.where(ReviewOverrideModel.review_id == review_id)

        query = query.order_by(ReviewOverrideModel.created_at.desc()).limit(limit)
        result = await self._db.execute(query)
        models = result.scalars().all()
        return [self._to_override_entry(model) for model in models]

    async def get_override_patterns(
        self,
        user_id: str | None = None,
        days: int = 30,
    ) -> dict[str, Any]:
        """
        分析用户覆盖模式

        用于检测可能的滥用行为

        Args:
            user_id: 用户ID
            days: 分析天数

        Returns:
            覆盖模式分析
        """
        cutoff = _utcnow() - timedelta(days=days)
        cutoff.isoformat()

        query = select(ReviewOverrideModel).where(
            ReviewOverrideModel.created_at >= cutoff
        )
        if user_id:
            user_uuid = self._parse_uuid(user_id)
            if user_uuid:
                query = query.where(ReviewOverrideModel.user_id == user_uuid)

        result = await self._db.execute(query)
        overrides = [self._to_override_entry(model) for model in result.scalars().all()]

        if not overrides:
            return {
                "total_overrides": 0,
                "by_type": {},
                "suspicious": False,
            }

        # 按类型统计
        by_type = {}
        for o in overrides:
            t = o.override_type.value
            by_type[t] = by_type.get(t, 0) + 1

        # 检测可疑行为（例如：大量覆盖失败审查）
        accept_despite_failure = by_type.get(OverrideDecision.ACCEPT_DESPITE_FAILURE.value, 0)
        suspicious = accept_despite_failure > 10  # 阈值可配置

        return {
            "total_overrides": len(overrides),
            "by_type": by_type,
            "suspicious": suspicious,
            "accept_despite_failure_count": accept_despite_failure,
            "period_days": days,
        }


# ============================================
# 全局实例管理
# ============================================

_review_history_services: dict[str, ReviewHistoryService] = {}


def get_review_history_service(db_session: AsyncSession) -> ReviewHistoryService:
    """获取ReviewHistoryService实例"""
    session_id = id(db_session)
    if session_id not in _review_history_services:
        _review_history_services[session_id] = ReviewHistoryService(db_session)
    return _review_history_services[session_id]
