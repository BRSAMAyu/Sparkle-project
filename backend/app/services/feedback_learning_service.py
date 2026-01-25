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

import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from collections import defaultdict
from loguru import logger

from app.services.review_history_service import (
    ReviewHistoryService,
    ReviewHistoryEntry,
    FeedbackEntry,
    FeedbackType,
)


# ============================================
# 学习数据模型
# ============================================

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
    threshold_adjustments: List[ThresholdAdjustment]
    weight_adjustments: List[WeightAdjustment]

    # 趋势
    improving_metrics: List[str]
    declining_metrics: List[str]
    stable_metrics: List[str]


@dataclass
class PatternInsight:
    """模式洞察"""
    pattern_type: str                  # 'false_positive', 'false_negative', 'inconsistency'
    description: str
    confidence: float
    examples: List[Dict[str, Any]]
    suggested_action: str


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

    def __init__(self, history_service: ReviewHistoryService):
        self._history = history_service
        self._learning_reports: List[LearningReport] = []
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
        end_date = datetime.utcnow()
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
            timestamp=datetime.utcnow().isoformat(),
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
        reviews: List[ReviewHistoryEntry],
        feedbacks: List[FeedbackEntry],
    ) -> List[Dict[str, Any]]:
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
        reviews: List[ReviewHistoryEntry],
        feedbacks: List[FeedbackEntry],
    ) -> List[ThresholdAdjustment]:
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
        reviews: List[ReviewHistoryEntry],
        feedbacks: List[FeedbackEntry],
    ) -> List[WeightAdjustment]:
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
        reviews: List[ReviewHistoryEntry],
        days: int,
    ) -> Tuple[List[str], List[str], List[str]]:
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

    def _calculate_satisfaction_rate(self, feedbacks: List[FeedbackEntry]) -> float:
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
            timestamp=datetime.utcnow().isoformat(),
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
    ) -> List[PatternInsight]:
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
        reviews: List[ReviewHistoryEntry],
        feedbacks: List[FeedbackEntry],
    ) -> Optional[PatternInsight]:
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
        reviews: List[ReviewHistoryEntry],
        feedbacks: List[FeedbackEntry],
    ) -> Optional[PatternInsight]:
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
        reviews: List[ReviewHistoryEntry],
    ) -> Optional[PatternInsight]:
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

    def _find_common_metrics(self, metrics_list: List[List[Dict]]) -> List[str]:
        """找出共同的未通过指标"""
        metric_failures = defaultdict(int)
        for metrics in metrics_list:
            for metric in metrics:
                if not metric.get("passed", True):
                    metric_failures[metric.get("metric")] += 1

        threshold = len(metrics_list) * 0.5
        return [m for m, count in metric_failures.items() if count >= threshold]

    # ============================================
    # 配置获取
    # ============================================

    def get_current_thresholds(self) -> Dict[str, float]:
        """获取当前阈值配置"""
        return dict(self._current_thresholds)

    def get_current_weights(self) -> Dict[str, float]:
        """获取当前权重配置"""
        return dict(self._current_weights)

    def get_learning_reports(
        self,
        limit: int = 10,
    ) -> List[LearningReport]:
        """获取学习报告"""
        return self._learning_reports[-limit:]

    def get_latest_report(self) -> Optional[LearningReport]:
        """获取最新的学习报告"""
        return self._learning_reports[-1] if self._learning_reports else None


# ============================================
# 全局实例管理
# ============================================

_learning_services: Dict[str, FeedbackLearningService] = {}


def get_feedback_learning_service(history_service: ReviewHistoryService) -> FeedbackLearningService:
    """获取FeedbackLearningService实例"""
    service_id = id(history_service)
    if service_id not in _learning_services:
        _learning_services[service_id] = FeedbackLearningService(history_service)
    return _learning_services[service_id]
