from __future__ import annotations
"""
Feedback Learning Service - Phase 2c

核心功能：
1. 从用户反馈中学习
2. 调整审查阈值和权重
3. 识别误判模式
4. 持续改进审查质量

作者: Claude Code (Opus 4.5)
创建时间: 2026-01-25
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import timezone, datetime, timedelta
from typing import Any

from loguru import logger

from app.services.review_history_service import (
    FeedbackEntry,
    FeedbackType,
    ReviewHistoryEntry,
    ReviewHistoryService,
)

# ============================================
# 学习数据模型
# ============================================


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)

@dataclass
class ThresholdAdjustment:
    """阈值调整建议"""
    metric_name: str
    current_threshold: float
    suggested_threshold: float
    confidence: float                  # 0-1，调整的置信度
    reason: str
    data_points: int                   # 支持此调整的数据点数


@dataclass
class WeightAdjustment:
    """权重调整建议"""
    metric_name: str
    current_weight: float
    suggested_weight: float
    reason: str
    expected_improvement: float


@dataclass
class LearningReport:
    """学习报告"""
    report_id: str
    timestamp: str
    period_days: int

    # 统计
    total_reviews_analyzed: int
    total_feedback_analyzed: int

    # 发现
    misclassification_rate: float      # 误判率
    satisfaction_rate: float           # 满意率

    # 调整建议
    threshold_adjustments: list[ThresholdAdjustment]
    weight_adjustments: list[WeightAdjustment]

    # 趋势
    improving_metrics: list[str]
    declining_metrics: list[str]
    stable_metrics: list[str]


@dataclass
class PatternInsight:
    """模式洞察"""
    pattern_type: str                  # 'false_positive', 'false_negative', 'inconsistency'
    description: str
    confidence: float
    examples: list[dict[str, Any]]
    suggested_action: str


@dataclass
class ExecutionQualityReport:
    """方案执行质量报告"""
    report_id: str
    timestamp: str
    period_days: int

    # 执行统计
    total_executions: int
    avg_quality_score: float
    pass_rate: float

    # 趋势
    score_trend: str                   # 'improving', 'declining', 'stable'
    common_issues: list[str]

    # 工具表现
    tool_success_rates: dict[str, float]


# ============================================
# Feedback Learning Service
# ============================================

class FeedbackLearningService:
    """
    反馈学习服务

    职责：
    1. 分析用户反馈与审查结果的一致性
    2. 识别系统性的误判模式
    3. 生成审查参数调整建议
    4. 持续监控审查质量
    """

    # 默认审查配置
    DEFAULT_THRESHOLDS = {
        "accuracy": 0.7,
        "completeness": 0.7,
        "relevance": 0.7,
        "clarity": 0.7,
        "safety": 0.9,
        "feasibility": 0.7,
        "helpfulness": 0.7,
    }

    DEFAULT_WEIGHTS = {
        "accuracy": 1.0,
        "completeness": 1.0,
        "relevance": 1.2,
        "clarity": 0.8,
        "safety": 1.5,
        "feasibility": 0.7,
        "helpfulness": 1.0,
    }

    def __init__(
        self,
        history_service: ReviewHistoryService,
        execution_record_service=None,
    ):
        self._history = history_service
        self._execution_record_service = execution_record_service
        self._learning_reports: list[LearningReport] = []
        self._execution_quality_reports: list[ExecutionQualityReport] = []
        self._current_thresholds = dict(self.DEFAULT_THRESHOLDS)
        self._current_weights = dict(self.DEFAULT_WEIGHTS)

    # ============================================
    # 学习分析
    # ============================================

    async def analyze_and_learn(
        self,
        days: int = 7,
        min_data_points: int = 10,
    ) -> LearningReport:
        """
        分析反馈并生成学习报告

        Args:
            days: 分析天数
            min_data_points: 最小数据点数

        Returns:
            LearningReport: 学习报告
        """
        import uuid

        logger.info(f"[FeedbackLearning] Starting analysis for past {days} days")

        # 获取时间范围内的数据
        end_date = _utcnow()
        start_date = end_date - timedelta(days=days)

        # 获取审查历史
        all_reviews = await self._history.get_review_history(limit=1000)
        period_reviews = [
            r for r in all_reviews
            if start_date <= datetime.fromisoformat(r.timestamp) <= end_date
        ]

        # 获取用户反馈
        all_feedbacks = await self._history.get_feedback_history(limit=1000)
        period_feedbacks = [
            f for f in all_feedbacks
            if start_date <= datetime.fromisoformat(f.timestamp) <= end_date
        ]

        if len(period_reviews) < min_data_points:
            logger.warning(
                f"[FeedbackLearning] Insufficient data: {len(period_reviews)} reviews"
            )
            return self._create_empty_report(days, len(period_reviews), len(period_feedbacks))

        # 分析误判
        misclassifications = await self._analyze_misclassifications(period_reviews, period_feedbacks)

        # 分析阈值调整
        threshold_adjustments = await self._analyze_thresholds(period_reviews, period_feedbacks)

        # 分析权重调整
        weight_adjustments = await self._analyze_weights(period_reviews, period_feedbacks)

        # 分析趋势
        improving, declining, stable = await self._analyze_trends(period_reviews, days)

        # 计算指标
        misclassification_rate = len(misclassifications) / len(period_reviews) if period_reviews else 0.0
        satisfaction_rate = self._calculate_satisfaction_rate(period_feedbacks)

        # 生成报告
        report = LearningReport(
            report_id=f"lr_{uuid.uuid4().hex[:12]}",
            timestamp=_utcnow().isoformat(),
            period_days=days,
            total_reviews_analyzed=len(period_reviews),
            total_feedback_analyzed=len(period_feedbacks),
            misclassification_rate=misclassification_rate,
            satisfaction_rate=satisfaction_rate,
            threshold_adjustments=threshold_adjustments,
            weight_adjustments=weight_adjustments,
            improving_metrics=improving,
            declining_metrics=declining,
            stable_metrics=stable,
        )

        self._learning_reports.append(report)

        # 自动应用高置信度的调整
        await self._apply_high_confidence_adjustments(report)

        logger.info(
            f"[FeedbackLearning] Analysis complete: "
            f"misclassification_rate={misclassification_rate:.2%}, "
            f"satisfaction_rate={satisfaction_rate:.2%}"
        )

        return report

    async def _analyze_misclassifications(
        self,
        reviews: list[ReviewHistoryEntry],
        feedbacks: list[FeedbackEntry],
    ) -> list[dict[str, Any]]:
        """分析误判"""
        misclassified = []

        # 创建feedback字典
        feedback_by_review = {f.review_id: f for f in feedbacks}

        for review in reviews:
            feedback = feedback_by_review.get(review.review_id)
            if not feedback:
                continue

            # 假阴性：审查未通过但用户满意
            if review.decision != "passed" and feedback.feedback_type == FeedbackType.SATISFIED:
                misclassified.append({
                    "review_id": review.review_id,
                    "type": "false_negative",
                    "review_score": review.overall_score,
                    "review_decision": review.decision,
                    "user_feedback": feedback.feedback_type.value,
                    "timestamp": review.timestamp,
                })

            # 假阳性：审查通过但用户不满意
            elif review.decision == "passed" and feedback.feedback_type == FeedbackType.UNSATISFIED:
                misclassified.append({
                    "review_id": review.review_id,
                    "type": "false_positive",
                    "review_score": review.overall_score,
                    "review_decision": review.decision,
                    "user_feedback": feedback.feedback_type.value,
                    "timestamp": review.timestamp,
                })

        logger.info(f"[FeedbackLearning] Found {len(misclassified)} misclassifications")
        return misclassified

    async def _analyze_thresholds(
        self,
        reviews: list[ReviewHistoryEntry],
        feedbacks: list[FeedbackEntry],
    ) -> list[ThresholdAdjustment]:
        """分析阈值调整建议"""
        adjustments = []

        # 按指标分组分析
        metric_data = defaultdict(list)
        for review in reviews:
            for metric in review.metrics:
                metric_name = metric.get("metric")
                metric_score = metric.get("score", 0.0)
                metric_passed = metric.get("passed", True)
                metric_data[metric_name].append({
                    "score": metric_score,
                    "passed": metric_passed,
                    "review_decision": review.decision,
                    "review_id": review.review_id,
                })

        # 创建feedback字典
        feedback_by_review = {f.review_id: f for f in feedbacks}

        # 分析每个指标的阈值
        for metric_name, data_points in metric_data.items():
            if len(data_points) < 5:
                continue

            current_threshold = self._current_thresholds.get(metric_name, 0.7)

            # 找出假阴性（未通过但用户满意）的分数分布
            false_negative_scores = []
            for dp in data_points:
                feedback = feedback_by_review.get(dp["review_id"])
                if feedback and feedback.feedback_type == FeedbackType.SATISFIED:
                    if not dp["passed"]:  # 指标未通过但用户满意
                        false_negative_scores.append(dp["score"])

            if false_negative_scores:
                # 如果有假阴性，考虑降低阈值
                avg_fn_score = sum(false_negative_scores) / len(false_negative_scores)
                if avg_fn_score > current_threshold - 0.1:  # 假阴性的分数接近阈值
                    suggested_threshold = max(0.5, current_threshold - 0.05)
                    confidence = min(1.0, len(false_negative_scores) / 20)
                    adjustments.append(ThresholdAdjustment(
                        metric_name=metric_name,
                        current_threshold=current_threshold,
                        suggested_threshold=suggested_threshold,
                        confidence=confidence,
                        reason=f"有{len(false_negative_scores)}个假阴性案例，平均分数{avg_fn_score:.2f}",
                        data_points=len(false_negative_scores),
                    ))

        return adjustments

    async def _analyze_weights(
        self,
        reviews: list[ReviewHistoryEntry],
        feedbacks: list[FeedbackEntry],
    ) -> list[WeightAdjustment]:
        """分析权重调整建议"""
        adjustments = []

        # 分析哪些指标与用户满意度最相关
        # 简化实现：统计未通过且用户不满意的指标

        feedback_by_review = {f.review_id: f for f in feedbacks}
        metric_failures = defaultdict(int)

        for review in reviews:
            feedback = feedback_by_review.get(review.review_id)
            if feedback and feedback.feedback_type == FeedbackType.UNSATISFIED:
                # 用户不满意，统计哪些指标未通过
                for metric in review.metrics:
                    if not metric.get("passed", True):
                        metric_failures[metric.get("metric")] += 1

        # 对失败次数多的指标，建议增加权重
        total_unsatisfied = sum(metric_failures.values()) or 1
        for metric_name, failures in metric_failures.items():
            if failures > total_unsatisfied * 0.3:  # 失败率超过30%
                current_weight = self._current_weights.get(metric_name, 1.0)
                suggested_weight = min(2.0, current_weight * 1.2)
                adjustments.append(WeightAdjustment(
                    metric_name=metric_name,
                    current_weight=current_weight,
                    suggested_weight=suggested_weight,
                    reason=f"在不满意的案例中，此指标未通过{failures}次",
                    expected_improvement=0.1,
                ))

        return adjustments

    async def _analyze_trends(
        self,
        reviews: list[ReviewHistoryEntry],
        days: int,
    ) -> tuple[list[str], list[str], list[str]]:
        """分析指标趋势"""
        # 获取趋势数据
        improving, declining, stable = [], [], []

        # 按指标分组
        metric_scores = defaultdict(list)
        for review in reviews:
            for metric in review.metrics:
                metric_name = metric.get("metric")
                metric_score = metric.get("score", 0.0)
                metric_scores[metric_name].append((review.timestamp, metric_score))

        # 分析每个指标的趋势
        for metric_name, scores in metric_scores.items():
            if len(scores) < 3:
                continue

            # 按时间排序
            scores.sort(key=lambda x: x[0])

            # 简单线性趋势
            mid = len(scores) // 2
            early_avg = sum(s[1] for s in scores[:mid]) / mid
            late_avg = sum(s[1] for s in scores[mid:]) / (len(scores) - mid)

            change_percent = ((late_avg - early_avg) / early_avg * 100) if early_avg > 0 else 0

            if change_percent > 5:
                improving.append(metric_name)
            elif change_percent < -5:
                declining.append(metric_name)
            else:
                stable.append(metric_name)

        return improving, declining, stable

    def _calculate_satisfaction_rate(self, feedbacks: list[FeedbackEntry]) -> float:
        """计算满意度"""
        if not feedbacks:
            return 0.0

        satisfied = sum(1 for f in feedbacks if f.feedback_type == FeedbackType.SATISFIED)
        return satisfied / len(feedbacks)

    def _create_empty_report(
        self,
        days: int,
        reviews_count: int,
        feedbacks_count: int,
    ) -> LearningReport:
        """创建空报告（数据不足时）"""
        import uuid
        return LearningReport(
            report_id=f"lr_empty_{uuid.uuid4().hex[:8]}",
            timestamp=_utcnow().isoformat(),
            period_days=days,
            total_reviews_analyzed=reviews_count,
            total_feedback_analyzed=feedbacks_count,
            misclassification_rate=0.0,
            satisfaction_rate=0.0,
            threshold_adjustments=[],
            weight_adjustments=[],
            improving_metrics=[],
            declining_metrics=[],
            stable_metrics=[],
        )

    async def _apply_high_confidence_adjustments(self, report: LearningReport) -> None:
        """应用高置信度的调整"""
        applied_count = 0

        for adj in report.threshold_adjustments:
            if adj.confidence >= 0.7:  # 高置信度阈值
                self._current_thresholds[adj.metric_name] = adj.suggested_threshold
                applied_count += 1
                logger.info(f"[FeedbackLearning] Applied threshold adjustment: {adj.metric_name} -> {adj.suggested_threshold}")

        for adj in report.weight_adjustments:
            self._current_weights[adj.metric_name] = adj.suggested_weight
            applied_count += 1
            logger.info(f"[FeedbackLearning] Applied weight adjustment: {adj.metric_name} -> {adj.suggested_weight}")

        if applied_count > 0:
            logger.info(f"[FeedbackLearning] Applied {applied_count} adjustments")

    # ============================================
    # 模式识别
    # ============================================

    async def identify_patterns(
        self,
        days: int = 30,
    ) -> list[PatternInsight]:
        """
        识别审查模式

        Args:
            days: 分析天数

        Returns:
            List[PatternInsight]: 识别到的模式
        """
        insights = []

        # 获取数据
        reviews = await self._history.get_review_history(limit=1000)
        feedbacks = await self._history.get_feedback_history(limit=1000)

        # 分析假阳性模式
        false_positives = await self._find_false_positive_pattern(reviews, feedbacks)
        if false_positives:
            insights.append(false_positives)

        # 分析假阴性模式
        false_negatives = await self._find_false_negative_pattern(reviews, feedbacks)
        if false_negatives:
            insights.append(false_negatives)

        # 分析不一致模式
        inconsistencies = await self._find_inconsistency_pattern(reviews)
        if inconsistencies:
            insights.append(inconsistencies)

        return insights

    async def _find_false_positive_pattern(
        self,
        reviews: list[ReviewHistoryEntry],
        feedbacks: list[FeedbackEntry],
    ) -> PatternInsight | None:
        """查找假阳性模式"""
        feedback_by_review = {f.review_id: f for f in feedbacks}

        false_positives = []
        for review in reviews:
            feedback = feedback_by_review.get(review.review_id)
            if feedback and review.decision == "passed" and feedback.feedback_type == FeedbackType.UNSATISFIED:
                false_positives.append({
                    "review_id": review.review_id,
                    "score": review.overall_score,
                    "metrics": review.metrics,
                })

        if len(false_positives) >= 3:
            # 分析共同特征
            common_metrics = self._find_common_metrics([fp["metrics"] for fp in false_positives])

            return PatternInsight(
                pattern_type="false_positive",
                description=f"发现{len(false_positives)}个假阳性案例，审查通过但用户不满意",
                confidence=min(1.0, len(false_positives) / 10),
                examples=false_positives[:3],
                suggested_action=f"考虑提高以下指标的阈值: {', '.join(common_metrics)}" if common_metrics else "调整审查标准",
            )

        return None

    async def _find_false_negative_pattern(
        self,
        reviews: list[ReviewHistoryEntry],
        feedbacks: list[FeedbackEntry],
    ) -> PatternInsight | None:
        """查找假阴性模式"""
        feedback_by_review = {f.review_id: f for f in feedbacks}

        false_negatives = []
        for review in reviews:
            feedback = feedback_by_review.get(review.review_id)
            if feedback and review.decision != "passed" and feedback.feedback_type == FeedbackType.SATISFIED:
                false_negatives.append({
                    "review_id": review.review_id,
                    "score": review.overall_score,
                    "metrics": review.metrics,
                })

        if len(false_negatives) >= 3:
            # 分析共同特征
            common_metrics = self._find_common_metrics([fn["metrics"] for fn in false_negatives])

            return PatternInsight(
                pattern_type="false_negative",
                description=f"发现{len(false_negatives)}个假阴性案例，审查未通过但用户满意",
                confidence=min(1.0, len(false_negatives) / 10),
                examples=false_negatives[:3],
                suggested_action=f"考虑降低以下指标的阈值: {', '.join(common_metrics)}" if common_metrics else "调整审查标准",
            )

        return None

    async def _find_inconsistency_pattern(
        self,
        reviews: list[ReviewHistoryEntry],
    ) -> PatternInsight | None:
        """查找不一致模式"""
        # 简化实现：检查相似分数的不同决策
        decision_by_score = defaultdict(set)
        for review in reviews:
            score_range = int(review.overall_score * 10) / 10  # 0.1精度
            decision_by_score[score_range].add(review.decision)

        inconsistent_ranges = {
            score: decisions
            for score, decisions in decision_by_score.items()
            if len(decisions) > 1
        }

        if inconsistent_ranges:
            return PatternInsight(
                pattern_type="inconsistency",
                description=f"发现{len(inconsistent_ranges)}个分数区间存在决策不一致",
                confidence=0.7,
                examples=[{"score_range": k, "decisions": list(v)} for k, v in list(inconsistent_ranges.items())[:3]],
                suggested_action="审查决策逻辑，确保一致性",
            )

        return None

    def _find_common_metrics(self, metrics_list: list[list[dict]]) -> list[str]:
        """找出共同的未通过指标"""
        metric_failures = defaultdict(int)
        for metrics in metrics_list:
            for metric in metrics:
                if not metric.get("passed", True):
                    metric_failures[metric.get("metric")] += 1

        threshold = len(metrics_list) * 0.5
        return [m for m, count in metric_failures.items() if count >= threshold]

    # ============================================
    # 方案执行质量分析 (Phase 5 Extension)
    # ============================================

    async def record_execution_result(
        self,
        validation_result: "dict[str, Any]",
    ) -> None:
        """
        记录方案执行结果到学习系统

        Args:
            validation_result: ExecutionValidationResult 的 to_dict() 输出
        """
        if not validation_result:
            return

        logger.info(
            f"[FeedbackLearning] Recorded execution result for learning: "
            f"plan_id={validation_result.get('plan_id')}, "
            f"status={validation_result.get('validation_status')}, "
            f"score={validation_result.get('quality_score', 0):.2f}"
        )

        # 内部记录可用于后续分析
        # 实际持久化由 PlanExecutionRecordService 完成

    async def analyze_execution_quality(
        self,
        days: int = 30,
    ) -> ExecutionQualityReport:
        """
        分析方案执行质量趋势

        Args:
            days: 分析天数

        Returns:
            ExecutionQualityReport: 执行质量报告
        """
        import uuid

        logger.info(f"[FeedbackLearning] Analyzing execution quality for past {days} days")

        # 如果没有执行记录服务，返回空报告
        if not self._execution_record_service:
            logger.warning("[FeedbackLearning] No execution record service available")
            return self._create_empty_execution_report(days)

        try:
            # 获取用户执行统计（简化版，使用平均用户数据）
            # 注意：这里需要指定 user_id，实际使用时可以通过参数传入
            stats = await self._execution_record_service.get_user_execution_stats(
                user_id=uuid.UUID("00000000-0000-0000-0000-000000000000"),  # 占位符
                days=days,
            )

            # 获取质量趋势
            trend_data = await self._execution_record_service.get_quality_trend(
                user_id=uuid.UUID("00000000-0000-0000-0000-000000000000"),  # 占位符
                days=days,
            )

            # 计算趋势方向
            score_trend = "stable"
            if len(trend_data) >= 2:
                first_avg = trend_data[0].get("avg_score", 0.5)
                last_avg = trend_data[-1].get("avg_score", 0.5)
                if last_avg > first_avg + 0.05:
                    score_trend = "improving"
                elif last_avg < first_avg - 0.05:
                    score_trend = "declining"

            # 收集常见问题
            common_issues = self._extract_common_issues(trend_data)

            report = ExecutionQualityReport(
                report_id=f"eq_{uuid.uuid4().hex[:12]}",
                timestamp=_utcnow().isoformat(),
                period_days=days,
                total_executions=stats.get("total", 0),
                avg_quality_score=stats.get("avg_score", 0.0),
                pass_rate=stats.get("pass_rate", 0.0),
                score_trend=score_trend,
                common_issues=common_issues,
                tool_success_rates={},  # 可从趋势数据中提取
            )

            self._execution_quality_reports.append(report)

            logger.info(
                f"[FeedbackLearning] Execution quality analysis complete: "
                f"total={report.total_executions}, "
                f"avg_score={report.avg_quality_score:.2f}, "
                f"trend={score_trend}"
            )

            return report

        except Exception as e:
            logger.warning(f"[FeedbackLearning] Failed to analyze execution quality: {e}")
            return self._create_empty_execution_report(days)

    def _extract_common_issues(
        self,
        trend_data: list[dict[str, Any]],
    ) -> list[str]:
        """从趋势数据中提取常见问题"""
        issue_counts = defaultdict(int)

        for day_data in trend_data:
            # 如果通过率较低，标记问题
            pass_rate = day_data.get("pass_rate", 1.0)
            if pass_rate < 0.7:
                issue_counts["low_pass_rate"] += 1

            # 如果平均分数较低，标记问题
            avg_score = day_data.get("avg_score", 1.0)
            if avg_score < 0.6:
                issue_counts["low_quality_score"] += 1

        # 返回出现频率最高的问题
        sorted_issues = sorted(
            issue_counts.items(),
            key=lambda x: x[1],
            reverse=True,
        )

        return [
            {
                "low_pass_rate": "方案通过率偏低",
                "low_quality_score": "执行质量分数偏低",
            }.get(issue, issue)
            for issue, count in sorted_issues[:3]
        ]

    def _create_empty_execution_report(
        self,
        days: int,
    ) -> ExecutionQualityReport:
        """创建空的执行质量报告（数据不足时）"""
        import uuid
        return ExecutionQualityReport(
            report_id=f"eq_empty_{uuid.uuid4().hex[:8]}",
            timestamp=_utcnow().isoformat(),
            period_days=days,
            total_executions=0,
            avg_quality_score=0.0,
            pass_rate=0.0,
            score_trend="stable",
            common_issues=[],
            tool_success_rates={},
        )

    # ============================================
    # 配置获取
    # ============================================

    def get_current_thresholds(self) -> dict[str, float]:
        """获取当前阈值配置"""
        return dict(self._current_thresholds)

    def get_current_weights(self) -> dict[str, float]:
        """获取当前权重配置"""
        return dict(self._current_weights)

    def get_learning_reports(
        self,
        limit: int = 10,
    ) -> list[LearningReport]:
        """获取学习报告"""
        return self._learning_reports[-limit:]

    def get_latest_report(self) -> LearningReport | None:
        """获取最新的学习报告"""
        return self._learning_reports[-1] if self._learning_reports else None

    def get_execution_quality_reports(
        self,
        limit: int = 10,
    ) -> list[ExecutionQualityReport]:
        """获取执行质量报告"""
        return self._execution_quality_reports[-limit:]

    def get_latest_execution_report(self) -> ExecutionQualityReport | None:
        """获取最新的执行质量报告"""
        return self._execution_quality_reports[-1] if self._execution_quality_reports else None


# ============================================
# 全局实例管理
# ============================================

_learning_services: dict[str, FeedbackLearningService] = {}


def get_feedback_learning_service(
    history_service: ReviewHistoryService,
    execution_record_service=None,
) -> FeedbackLearningService:
    """
    获取FeedbackLearningService实例

    Args:
        history_service: ReviewHistoryService 实例
        execution_record_service: 可选的 PlanExecutionRecordService 实例
    """
    service_id = id(history_service)
    if service_id not in _learning_services:
        _learning_services[service_id] = FeedbackLearningService(
            history_service=history_service,
            execution_record_service=execution_record_service,
        )
    return _learning_services[service_id]
