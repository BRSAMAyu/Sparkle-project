"""
Model Fallback Service - Phase 2d

核心功能：
1. 追踪模型在审查中的表现
2. 检测持续审查失败
3. 触发模型切换
4. 管理模型降级策略

作者: Claude Code (Opus 4.5)
创建时间: 2026-01-25
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from loguru import logger

from app.core.agent_profiles import TaskType

# ============================================
# 数据模型
# ============================================

class FallbackReason(str, Enum):
    """降级原因"""
    CONSISTENT_REJECTION = "consistent_rejection"     # 持续被用户拒绝
    LOW_QUALITY_SCORE = "low_quality_score"          # 质量分数持续过低
    REFLECTION_FAILURE = "reflection_failure"         # 反思修正失败
    HIGH_ERROR_RATE = "high_error_rate"               # 错误率过高
    USER_COMPLAINT = "user_complaint"                 # 用户投诉
    TIMEOUT = "timeout"                               # 响应超时


class ModelTierPreference(str, Enum):
    """模型层级偏好"""
    """模型使用策略"""
    QUALITY_FIRST = "quality_first"     # 质量优先，使用最强模型
    BALANCED = "balanced"               # 平衡模式
    SPEED_FIRST = "speed_first"         # 速度优先


@dataclass
class ModelPerformanceRecord:
    """模型性能记录"""
    model_name: str
    task_type: str                     # 'generation', 'review', etc.
    timestamp: str

    # 审查结果
    review_passed: bool
    review_score: float
    issues_count: int

    # 用户反馈
    user_satisfied: bool | None = None

    # 执行信息
    response_time_ms: int = 0
    token_count: int = 0


@dataclass
class FallbackDecision:
    """降级决策"""
    should_fallback: bool
    reason: FallbackReason | None
    current_model: str
    suggested_model: str
    confidence: float                  # 0-1，决策置信度
    description: str


@dataclass
class FallbackConfig:
    """降级配置"""
    # 触发阈值
    max_consecutive_failures: int = 3  # 连续失败次数阈值
    min_avg_score_threshold: float = 0.5  # 平均分数阈值
    max_reflection_failures: int = 2    # 反思失败次数阈值

    # 模型层级
    preferred_tier: ModelTierPreference = ModelTierPreference.BALANCED

    # 时间窗口（秒）
    failure_time_window: int = 300     # 5分钟内统计失败次数
    performance_window: int = 3600     # 1小时内的性能统计


@dataclass
class ModelUsageStats:
    """模型使用统计"""
    model_name: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_review_score: float = 0.0
    avg_response_time_ms: float = 0.0
    last_used: str | None = None


# ============================================
# Model Fallback Service
# ============================================

class ModelFallbackService:
    """
    模型降级服务

    职责：
    1. 追踪模型性能
    2. 检测需要降级的场景
    3. 推荐替代模型
    4. 管理模型选择策略
    """

    # 模型能力映射（用于降级时的替代选择）
    MODEL_ALTERNATIVES = {
        # 从高级模型降级
        "claude-3-5-sonnet": ["claude-3-5-haiku", "gpt-4o-mini"],
        "claude-3-opus": ["claude-3-5-sonnet", "claude-3-sonnet", "gpt-4o"],
        "claude-3-sonnet": ["claude-3-haiku", "gpt-4o-mini"],

        # 从中级模型降级
        "gpt-4o": ["gpt-4o-mini", "claude-3-haiku"],
        "claude-3-5-haiku": ["gpt-4o-mini"],

        # 从轻量模型升级（质量优先时）
        "gpt-4o-mini": ["gpt-4o", "claude-3-5-haiku"],
        "claude-3-haiku": ["claude-3-sonnet", "gpt-4o"],
    }

    # 模型层级（用于质量优先策略）
    MODEL_TIERS = {
        "highest": ["claude-3-opus", "claude-3-5-sonnet"],
        "high": ["claude-3-sonnet", "gpt-4o", "claude-3-5-haiku"],
        "medium": ["gpt-4o-mini", "claude-3-haiku"],
    }

    def __init__(self, config: FallbackConfig | None = None):
        self._config = config or FallbackConfig()
        self._performance_history: list[ModelPerformanceRecord] = []
        self._model_stats: dict[str, ModelUsageStats] = {}
        self._consecutive_failures: dict[str, int] = defaultdict(int)
        self._last_fallback_time: datetime | None = None

    # ============================================
    # 性能记录
    # ============================================

    def record_performance(
        self,
        model_name: str,
        task_type: str,
        review_passed: bool,
        review_score: float,
        issues_count: int,
        response_time_ms: int = 0,
        token_count: int = 0,
        user_satisfied: bool | None = None,
    ) -> None:
        """
        记录模型性能

        Args:
            model_name: 使用的模型
            task_type: 任务类型
            review_passed: 是否通过审查
            review_score: 审查分数
            issues_count: 问题数量
            response_time_ms: 响应时间
            token_count: Token数量
            user_satisfied: 用户是否满意
        """
        record = ModelPerformanceRecord(
            model_name=model_name,
            task_type=task_type,
            timestamp=datetime.utcnow().isoformat(),
            review_passed=review_passed,
            review_score=review_score,
            issues_count=issues_count,
            user_satisfied=user_satisfied,
            response_time_ms=response_time_ms,
            token_count=token_count,
        )

        self._performance_history.append(record)

        # 更新模型统计
        if model_name not in self._model_stats:
            self._model_stats[model_name] = ModelUsageStats(model_name=model_name)

        stats = self._model_stats[model_name]
        stats.total_requests += 1
        if review_passed:
            stats.successful_requests += 1
        else:
            stats.failed_requests += 1
            self._consecutive_failures[model_name] += 1

        # 更新平均分数
        n = stats.total_requests
        stats.avg_review_score = (
            (stats.avg_review_score * (n - 1) + review_score) / n
        )

        # 更新平均响应时间
        if response_time_ms > 0:
            stats.avg_response_time_ms = (
                (stats.avg_response_time_ms * (n - 1) + response_time_ms) / n
            )

        stats.last_used = record.timestamp

        # 重置连续失败计数
        if review_passed or user_satisfied:
            self._consecutive_failures[model_name] = 0

        logger.debug(
            f"[ModelFallback] Recorded performance: {model_name} "
            f"passed={review_passed}, score={review_score:.2f}"
        )

    def record_reflection_failure(
        self,
        model_name: str,
        original_score: float,
        rounds_attempted: int,
    ) -> None:
        """
        记录反思失败

        Args:
            model_name: 使用的模型
            original_score: 原始分数
            rounds_attempted: 尝试的轮数
        """
        self._consecutive_failures[f"{model_name}_reflection"] += 1

        logger.warning(
            f"[ModelFallback] Reflection failure: {model_name}, "
            f"score={original_score:.2f}, rounds={rounds_attempted}"
        )

    # ============================================
    # 降级决策
    # ============================================

    def should_fallback(
        self,
        model_name: str,
        task_type: str = "generation",
    ) -> FallbackDecision:
        """
        判断是否应该降级

        Args:
            model_name: 当前使用的模型
            task_type: 任务类型

        Returns:
            FallbackDecision: 降级决策
        """
        consecutive_failures = self._consecutive_failures.get(model_name, 0)

        # 检查连续失败次数
        if consecutive_failures >= self._config.max_consecutive_failures:
            suggested = self._get_alternative_model(model_name, preference="quality")
            return FallbackDecision(
                should_fallback=True,
                reason=FallbackReason.CONSISTENT_REJECTION,
                current_model=model_name,
                suggested_model=suggested,
                confidence=0.8,
                description=f"连续{consecutive_failures}次审查失败",
            )

        # 检查最近时间窗口内的失败率
        recent_records = self._get_recent_records(
            model_name=model_name,
            window_seconds=self._config.failure_time_window,
        )

        if recent_records:
            failure_rate = sum(1 for r in recent_records if not r.review_passed) / len(recent_records)
            avg_score = sum(r.review_score for r in recent_records) / len(recent_records)

            if failure_rate > 0.7 and avg_score < self._config.min_avg_score_threshold:
                suggested = self._get_alternative_model(model_name, preference="quality")
                return FallbackDecision(
                    should_fallback=True,
                    reason=FallbackReason.LOW_QUALITY_SCORE,
                    current_model=model_name,
                    suggested_model=suggested,
                    confidence=0.7,
                    description=f"最近失败率{failure_rate:.0%}, 平均分数{avg_score:.2f}",
                )

        # 检查反思失败
        reflection_failures = self._consecutive_failures.get(f"{model_name}_reflection", 0)
        if reflection_failures >= self._config.max_reflection_failures:
            suggested = self._get_alternative_model(model_name, preference="quality")
            return FallbackDecision(
                should_fallback=True,
                reason=FallbackReason.REFLECTION_FAILURE,
                current_model=model_name,
                suggested_model=suggested,
                confidence=0.75,
                description=f"连续{reflection_failures}次反思失败",
            )

        # 不需要降级
        return FallbackDecision(
            should_fallback=False,
            reason=None,
            current_model=model_name,
            suggested_model=model_name,
            confidence=1.0,
            description="模型表现正常",
        )

    # ============================================
    # 模型选择
    # ============================================

    def _get_alternative_model(
        self,
        current_model: str,
        preference: str = "quality",
    ) -> str:
        """
        获取替代模型

        Args:
            current_model: 当前模型
            preference: 选择偏好 ('quality', 'balanced', 'speed')

        Returns:
            替代模型名称
        """
        # 首选：从预定义的替代列表中选择
        if current_model in self.MODEL_ALTERNATIVES:
            alternatives = self.MODEL_ALTERNATIVES[current_model]
            if alternatives:
                # 根据偏好选择
                if preference == "quality":
                    # 选择能力最强的替代
                    return alternatives[0]
                else:
                    # 选择第一个可用替代
                    return alternatives[0]

        # 次选：根据层级偏好选择
        if preference == "quality":
            # 选择高层级模型
            for tier in ["highest", "high", "medium"]:
                for model in self.MODEL_TIERS.get(tier, []):
                    if model != current_model:
                        return model
        else:
            # 选择低层级模型（更快）
            for tier in ["medium", "high", "highest"]:
                for model in self.MODEL_TIERS.get(tier, []):
                    if model != current_model:
                        return model

        # 默认：返回常用备选
        return "claude-3-5-sonnet"

    def get_model_for_task(
        self,
        task_type: TaskType,
        current_model: str | None = None,
        retry_count: int = 0,
    ) -> str:
        """
        根据任务类型和当前状态选择最佳模型

        Args:
            task_type: 任务类型
            current_model: 当前使用的模型
            retry_count: 重试次数

        Returns:
            模型名称
        """
        # 如果是重试且之前的模型失败过，选择替代模型
        if retry_count > 0 and current_model:
            decision = self.should_fallback(current_model, task_type.value)
            if decision.should_fallback:
                logger.info(
                    f"[ModelFallback] Switching from {current_model} "
                    f"to {decision.suggested_model} (reason: {decision.reason.value})"
                )
                return decision.suggested_model

        # 根据配置偏好选择
        if self._config.preferred_tier == ModelTierPreference.QUALITY_FIRST:
            return self._get_highest_quality_model(task_type)
        elif self._config.preferred_tier == ModelTierPreference.SPEED_FIRST:
            return self._get_fastest_model(task_type)
        else:  # BALANCED
            return self._get_balanced_model(task_type)

    def _get_highest_quality_model(self, task_type: TaskType) -> str:
        """获取最高质量模型"""
        # 审查任务使用最强模型
        if task_type == TaskType.REVIEW:
            return "claude-3-5-sonnet"
        # 生成任务使用高质量模型
        return "claude-3-5-sonnet"

    def _get_balanced_model(self, task_type: TaskType) -> str:
        """获取平衡模型"""
        if task_type == TaskType.REVIEW:
            return "claude-3-5-haiku"
        return "claude-3-5-haiku"

    def _get_fastest_model(self, task_type: TaskType) -> str:
        """获取最快模型"""
        return "gpt-4o-mini"

    # ============================================
    # 性能分析
    # ============================================

    def get_model_stats(self, model_name: str | None = None) -> dict[str, ModelUsageStats]:
        """获取模型使用统计"""
        if model_name:
            return {model_name: self._model_stats.get(model_name)}
        return dict(self._model_stats)

    def get_performance_summary(self) -> dict[str, Any]:
        """获取性能摘要"""
        if not self._performance_history:
            return {
                "total_records": 0,
                "models_used": [],
                "overall_success_rate": 0.0,
            }

        total = len(self._performance_history)
        successful = sum(1 for r in self._performance_history if r.review_passed)
        models_used = list({r.model_name for r in self._performance_history})

        return {
            "total_records": total,
            "successful_reviews": successful,
            "overall_success_rate": successful / total if total > 0 else 0.0,
            "models_used": models_used,
            "avg_score": sum(r.review_score for r in self._performance_history) / total,
            "consecutive_failures": dict(self._consecutive_failures),
        }

    def _get_recent_records(
        self,
        model_name: str,
        window_seconds: int,
    ) -> list[ModelPerformanceRecord]:
        """获取最近的记录"""
        cutoff_time = datetime.utcnow() - timedelta(seconds=window_seconds)
        return [
            r for r in self._performance_history
            if r.model_name == model_name
            and datetime.fromisoformat(r.timestamp) > cutoff_time
        ]

    # ============================================
    # 配置管理
    # ============================================

    def update_config(self, **kwargs) -> None:
        """更新配置"""
        for key, value in kwargs.items():
            if hasattr(self._config, key):
                setattr(self._config, key, value)
                logger.info(f"[ModelFallback] Updated config: {key}={value}")

    def get_config(self) -> FallbackConfig:
        """获取当前配置"""
        return self._config

    def reset_consecutive_failures(self, model_name: str | None = None) -> None:
        """重置连续失败计数"""
        if model_name:
            self._consecutive_failures[model_name] = 0
        else:
            self._consecutive_failures.clear()
        logger.info(f"[ModelFallback] Reset consecutive failures for {model_name or 'all'}")


# ============================================
# 全局实例
# ============================================

_fallback_service_instance: ModelFallbackService | None = None


def get_model_fallback_service(config: FallbackConfig | None = None) -> ModelFallbackService:
    """获取ModelFallbackService单例"""
    global _fallback_service_instance
    if _fallback_service_instance is None:
        _fallback_service_instance = ModelFallbackService(config)
    return _fallback_service_instance
