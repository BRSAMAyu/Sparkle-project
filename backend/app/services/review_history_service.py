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
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from enum import Enum
from loguru import logger

from sqlalchemy import select, and_, or_, func, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base
from app.db.models import User, Conversation
from app.core.exceptions import NotFoundError


# ============================================
# 数据模型
# ============================================

class FeedbackType(str, Enum):
    """用户反馈类型"""
    SATISFIED = "satisfied"           # 用户满意（接受内容）
    UNSATISFIED = "unsatisfied"       # 用户不满意（拒绝内容）
    MODIFIED = "modified"             # 用户修改后接受
    REPORTED_ERROR = "reported_error" # 用户报告错误
    SKIPPED = "skipped"               # 用户跳过审查


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
    metrics: List[Dict[str, Any]]     # 审查指标列表
    issues_count: int
    critical_count: int
    warning_count: int

    # 反思信息（如果有）
    reflection_round: int = 0
    reflection_outcome: Optional[str] = None
    score_delta: float = 0.0

    # 用户反馈
    user_feedback: Optional[str] = None
    user_satisfied: Optional[bool] = None
    feedback_timestamp: Optional[str] = None

    # 审查元数据
    reviewer_model: str = ""
    review_duration_ms: int = 0
    requires_reflection: bool = False


@dataclass
class FeedbackEntry:
    """用户反馈条目"""
    feedback_id: str
    review_id: str
    user_id: str
    feedback_type: FeedbackType
    timestamp: str

    # 反馈详情
    rating: Optional[int] = None      # 1-5评分
    comment: Optional[str] = None     # 用户评论
    issues_reported: List[str] = field(default_factory=list)

    # 上下文
    original_score: float = 0.0
    original_decision: str = ""
    was_reflected: bool = False


class OverrideDecision(str, Enum):
    """用户覆盖决策类型"""
    ACCEPT_DESPITE_FAILURE = "accept_despite_failure"  # 接受尽管审查失败
    REJECT_DESPITE_PASS = "reject_despite_pass"        # 拒绝尽管审查通过
    MODIFY_DECISION = "modify_decision"                # 修改决策


class AppealStatus(str, Enum):
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
    was_correct: Optional[bool] = None # 后续验证：用户覆盖是否正确
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
    issues_with_review: List[str] = field(default_factory=list)  # 审查中的问题

    # 状态追踪
    status: AppealStatus = AppealStatus.PENDING
    assigned_to: Optional[str] = None  # 分配给谁处理

    # 二次审查结果
    secondary_review_id: Optional[str] = None
    secondary_decision: Optional[str] = None
    secondary_score: Optional[float] = None

    # 解决信息
    resolution: Optional[str] = None   # 解决方案
    resolved_by: Optional[str] = None  # 解决者
    resolved_at: Optional[str] = None  # 解决时间


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
    common_issues: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ReviewTrend:
    """审查趋势分析"""
    metric_name: str
    trend: str                        # 'improving', 'stable', 'declining'
    current_avg: float
    previous_avg: float
    change_percent: float
    data_points: List[float]          # 最近的数据点


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
        self._memory_cache: Dict[str, ReviewHistoryEntry] = {}
        self._feedback_cache: List[FeedbackEntry] = []
        self._override_cache: List[OverrideEntry] = []
        self._appeal_cache: List[AppealEntry] = []

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
        metrics: List[Dict[str, Any]],
        issues_count: int,
        critical_count: int,
        warning_count: int,
        reviewer_model: str = "",
        review_duration_ms: int = 0,
        requires_reflection: bool = False,
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
        entry = ReviewHistoryEntry(
            review_id=review_id,
            target_id=target_id,
            target_type=target_type,
            user_id=user_id,
            session_id=session_id,
            timestamp=datetime.utcnow().isoformat(),
            decision=decision,
            overall_score=overall_score,
            metrics=metrics,
            issues_count=issues_count,
            critical_count=critical_count,
            warning_count=warning_count,
            reviewer_model=reviewer_model,
            review_duration_ms=review_duration_ms,
            requires_reflection=requires_reflection,
        )

        # 保存到内存缓存
        self._memory_cache[review_id] = entry

        # TODO: 持久化到数据库
        # await self._persist_to_db(entry)

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
        if review_id in self._memory_cache:
            entry = self._memory_cache[review_id]
            entry.reflection_round = reflection_round
            entry.reflection_outcome = outcome
            entry.score_delta = score_delta

            logger.info(
                f"[ReviewHistory] Updated reflection for {review_id}: "
                f"{outcome}, delta={score_delta:+.2f}"
            )

    async def record_user_feedback(
        self,
        review_id: str,
        user_id: str,
        feedback_type: FeedbackType,
        rating: Optional[int] = None,
        comment: Optional[str] = None,
        issues_reported: Optional[List[str]] = None,
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
        import uuid

        # 获取原审查记录
        original_review = self._memory_cache.get(review_id)
        if original_review:
            original_review.user_feedback = feedback_type.value
            original_review.user_satisfied = (feedback_type == FeedbackType.SATISFIED)
            original_review.feedback_timestamp = datetime.utcnow().isoformat()

        feedback = FeedbackEntry(
            feedback_id=f"fb_{uuid.uuid4().hex[:12]}",
            review_id=review_id,
            user_id=user_id,
            feedback_type=feedback_type,
            timestamp=datetime.utcnow().isoformat(),
            rating=rating,
            comment=comment,
            issues_reported=issues_reported or [],
            original_score=original_review.overall_score if original_review else 0.0,
            original_decision=original_review.decision if original_review else "",
            was_reflected=(original_review.reflection_round > 0) if original_review else False,
        )

        self._feedback_cache.append(feedback)

        logger.info(
            f"[ReviewHistory] Recorded feedback {feedback.feedback_id}: "
            f"{feedback_type.value} for review {review_id}"
        )

        return feedback

    # ============================================
    # 历史查询
    # ============================================

    async def get_review_history(
        self,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        target_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[ReviewHistoryEntry]:
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
        results = list(self._memory_cache.values())

        # 应用筛选
        if user_id:
            results = [r for r in results if r.user_id == user_id]
        if session_id:
            results = [r for r in results if r.session_id == session_id]
        if target_type:
            results = [r for r in results if r.target_type == target_type]

        # 排序（最新在前）
        results.sort(key=lambda x: x.timestamp, reverse=True)

        return results[offset:offset + limit]

    async def get_review_by_id(self, review_id: str) -> Optional[ReviewHistoryEntry]:
        """根据ID获取审查记录"""
        return self._memory_cache.get(review_id)

    async def get_feedback_history(
        self,
        user_id: Optional[str] = None,
        review_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[FeedbackEntry]:
        """获取反馈历史"""
        results = self._feedback_cache

        if user_id:
            results = [f for f in results if f.user_id == user_id]
        if review_id:
            results = [f for f in results if f.review_id == review_id]

        results.sort(key=lambda x: x.timestamp, reverse=True)
        return results[:limit]

    # ============================================
    # 聚合统计
    # ============================================

    async def get_aggregation(
        self,
        period: str = "daily",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        user_id: Optional[str] = None,
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
            end_date = datetime.utcnow().isoformat()
        if not start_date:
            if period == "daily":
                start_date = (datetime.utcnow() - timedelta(days=1)).isoformat()
            elif period == "weekly":
                start_date = (datetime.utcnow() - timedelta(days=7)).isoformat()
            else:  # monthly
                start_date = (datetime.utcnow() - timedelta(days=30)).isoformat()

        # 筛选时间范围内的记录
        reviews = list(self._memory_cache.values())
        reviews = [
            r for r in reviews
            if start_date <= r.timestamp <= end_date
        ]
        if user_id:
            reviews = [r for r in reviews if r.user_id == user_id]

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
        feedbacks = [
            f for f in self._feedback_cache
            if start_date <= f.timestamp <= end_date
        ]
        if user_id:
            feedbacks = [f for f in feedbacks if f.user_id == user_id]

        satisfaction_rate = 0.0
        if feedbacks:
            satisfied = sum(1 for f in feedbacks if f.feedback_type == FeedbackType.SATISFIED)
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
        user_id: Optional[str] = None,
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
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        # 获取时间范围内的记录
        reviews = list(self._memory_cache.values())
        reviews = [
            r for r in reviews
            if start_date <= datetime.fromisoformat(r.timestamp) <= end_date
        ]
        if user_id:
            reviews = [r for r in reviews if r.user_id == user_id]

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
        learning_data = {
            "reviews": [asdict(r) for r in self._memory_cache.values()],
            "feedbacks": [asdict(f) for f in self._feedback_cache],
            "export_timestamp": datetime.utcnow().isoformat(),
            "total_count": len(self._memory_cache),
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
    ) -> List[Dict[str, Any]]:
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

        for entry in self._memory_cache.values():
            # 检查是否有用户反馈
            if entry.user_feedback == FeedbackType.SATISFIED.value and not entry.user_satisfied:
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
        import uuid

        # 确定覆盖类型
        if original_decision == "failed" and new_decision == "passed":
            override_type = OverrideDecision.ACCEPT_DESPITE_FAILURE
        elif original_decision == "passed" and new_decision == "failed":
            override_type = OverrideDecision.REJECT_DESPITE_PASS
        else:
            override_type = OverrideDecision.MODIFY_DECISION

        override = OverrideEntry(
            override_id=f"ovr_{uuid.uuid4().hex[:12]}",
            review_id=review_id,
            user_id=user_id,
            timestamp=datetime.utcnow().isoformat(),
            original_decision=original_decision,
            new_decision=new_decision,
            override_type=override_type,
            reason=reason,
        )

        self._override_cache.append(override)

        # 更新原审查记录
        if review_id in self._memory_cache:
            entry = self._memory_cache[review_id]
            entry.user_feedback = f"override:{new_decision}"
            entry.user_satisfied = (new_decision == "passed")
            entry.feedback_timestamp = datetime.utcnow().isoformat()

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
        issues_with_review: Optional[List[str]] = None,
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
        import uuid

        appeal = AppealEntry(
            appeal_id=f"apl_{uuid.uuid4().hex[:12]}",
            review_id=review_id,
            user_id=user_id,
            timestamp=datetime.utcnow().isoformat(),
            appeal_reason=appeal_reason,
            issues_with_review=issues_with_review or [],
            status=AppealStatus.PENDING,
        )

        self._appeal_cache.append(appeal)

        logger.info(
            f"[ReviewHistory] Recorded appeal {appeal.appeal_id}: "
            f"for review {review_id}, reason: {appeal_reason[:50]}..."
        )

        return appeal

    async def get_appeal_queue(
        self,
        status: Optional[AppealStatus] = None,
        limit: int = 50,
    ) -> List[AppealEntry]:
        """
        获取待处理申诉队列

        Args:
            status: 按状态筛选（None表示待处理）
            limit: 返回数量限制

        Returns:
            申诉条目列表
        """
        if status is None:
            # 默认返回待处理的申诉
            results = [
                a for a in self._appeal_cache
                if a.status in [AppealStatus.PENDING, AppealStatus.IN_REVIEW]
            ]
        else:
            results = [
                a for a in self._appeal_cache
                if a.status == status
            ]

        # 按时间排序（最早的在前，FIFO）
        results.sort(key=lambda x: x.timestamp)
        return results[:limit]

    async def update_appeal_status(
        self,
        appeal_id: str,
        status: AppealStatus,
        resolution: Optional[str] = None,
        resolved_by: Optional[str] = None,
        secondary_review_id: Optional[str] = None,
        secondary_decision: Optional[str] = None,
        secondary_score: Optional[float] = None,
    ) -> Optional[AppealEntry]:
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
        for appeal in self._appeal_cache:
            if appeal.appeal_id == appeal_id:
                appeal.status = status
                if resolution:
                    appeal.resolution = resolution
                if resolved_by:
                    appeal.resolved_by = resolved_by
                    appeal.resolved_at = datetime.utcnow().isoformat()
                if secondary_review_id:
                    appeal.secondary_review_id = secondary_review_id
                if secondary_decision:
                    appeal.secondary_decision = secondary_decision
                if secondary_score is not None:
                    appeal.secondary_score = secondary_score

                logger.info(
                    f"[ReviewHistory] Updated appeal {appeal_id}: status={status.value}"
                )
                return appeal

        return None

    async def get_appeal_by_id(self, appeal_id: str) -> Optional[AppealEntry]:
        """根据ID获取申诉"""
        for appeal in self._appeal_cache:
            if appeal.appeal_id == appeal_id:
                return appeal
        return None

    async def get_override_history(
        self,
        user_id: Optional[str] = None,
        review_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[OverrideEntry]:
        """获取覆盖历史"""
        results = self._override_cache

        if user_id:
            results = [o for o in results if o.user_id == user_id]
        if review_id:
            results = [o for o in results if o.review_id == review_id]

        results = sorted(results, key=lambda x: x.timestamp, reverse=True)
        return results[:limit]

    async def get_override_patterns(
        self,
        user_id: Optional[str] = None,
        days: int = 30,
    ) -> Dict[str, Any]:
        """
        分析用户覆盖模式

        用于检测可能的滥用行为

        Args:
            user_id: 用户ID
            days: 分析天数

        Returns:
            覆盖模式分析
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        cutoff_str = cutoff.isoformat()

        overrides = [
            o for o in self._override_cache
            if o.timestamp >= cutoff_str
        ]

        if user_id:
            overrides = [o for o in overrides if o.user_id == user_id]

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

_review_history_services: Dict[str, ReviewHistoryService] = {}


def get_review_history_service(db_session: AsyncSession) -> ReviewHistoryService:
    """获取ReviewHistoryService实例"""
    session_id = id(db_session)
    if session_id not in _review_history_services:
        _review_history_services[session_id] = ReviewHistoryService(db_session)
    return _review_history_services[session_id]
