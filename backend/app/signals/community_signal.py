"""
Core: execution
Phase: sense→clarify
Stage: Signal-to-Action Spine P1-6 CommunitySignal v1

社群信号 v1 — 匿名共性错因 + 共享资料推荐。

核心原则：
- 社群信号不直接写个人状态（铁律）
- 只做匿名聚合，不暴露个体数据
- 共性错因 → 提示"其他同学也在这个地方出错了"
- 共享资料 → 推荐"跟你同考的同学都在看这个"
- 社群信号优先级永远 <= medium
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from loguru import logger

from app.signals.types import ActionableSignal, _uid


@dataclass
class CohortMistakePattern:
    """匿名共性错因模式。"""
    knowledge_node_id: str       # 知识节点
    subject: str                 # 学科
    mistake_type: str            # 错因类型
    cohort_size: int             # 匿名群体大小（至少 5 人）
    frequency_ratio: float       # 出错比例 0.0~1.0
    common_misconception: str    # 常见误解描述

    def to_dict(self) -> dict[str, Any]:
        return {
            "knowledge_node_id": self.knowledge_node_id,
            "subject": self.subject,
            "mistake_type": self.mistake_type,
            "cohort_size": self.cohort_size,
            "frequency_ratio": self.frequency_ratio,
            "common_misconception": self.common_misconception,
        }


@dataclass
class SharedResourceRecommendation:
    """共享资料推荐。"""
    resource_id: str
    resource_title: str
    subject: str
    recommendation_reason: str    # "highly_rated_by_cohort" | "frequently_used"
    peer_count: int               # 使用该资料的同学数（匿名）
    relevance_score: float        # 0.0~1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "resource_id": self.resource_id,
            "resource_title": self.resource_title,
            "subject": self.subject,
            "recommendation_reason": self.recommendation_reason,
            "peer_count": self.peer_count,
            "relevance_score": self.relevance_score,
        }


# 阈值
_MIN_COHORT_SIZE = 5
_MIN_FREQUENCY_RATIO = 0.4
_MIN_PEER_COUNT = 3
_MIN_RELEVANCE_SCORE = 0.5


class CommunitySignalDetector:
    """
    P1-6: 社群信号检测 v1。

    只做两件事：
    1. 匿名共性错因检测（不暴露个体）
    2. 共享资料推荐（基于使用频率）

    禁止：
    - 社群信号直接写个人状态
    - 暴露个体数据
    - 社群信号优先级 > medium
    """

    def detect_cohort_mistake(
        self,
        *,
        knowledge_node_id: str,
        subject: str,
        mistake_type: str,
        cohort_size: int,
        error_count: int,
        common_misconception: str,
    ) -> CohortMistakePattern | None:
        """
        检测共性错因。

        条件：
        - 匿名群体 >= 5 人
        - 出错比例 >= 40%
        """
        if cohort_size < _MIN_COHORT_SIZE:
            return None

        frequency_ratio = min(1.0, error_count / cohort_size)
        if frequency_ratio < _MIN_FREQUENCY_RATIO:
            return None

        return CohortMistakePattern(
            knowledge_node_id=knowledge_node_id,
            subject=subject,
            mistake_type=mistake_type,
            cohort_size=cohort_size,
            frequency_ratio=round(frequency_ratio, 2),
            common_misconception=common_misconception,
        )

    def detect_shared_resource(
        self,
        *,
        resource_id: str,
        resource_title: str,
        subject: str,
        recommendation_reason: str,
        peer_count: int,
        relevance_score: float,
    ) -> SharedResourceRecommendation | None:
        """
        检测共享资料推荐。

        条件：
        - 使用人数 >= 3
        - 相关度 >= 0.5
        """
        if peer_count < _MIN_PEER_COUNT:
            return None
        if relevance_score < _MIN_RELEVANCE_SCORE:
            return None

        return SharedResourceRecommendation(
            resource_id=resource_id,
            resource_title=resource_title,
            subject=subject,
            recommendation_reason=recommendation_reason,
            peer_count=peer_count,
            relevance_score=relevance_score,
        )

    def to_actionable_signal(
        self,
        source: CohortMistakePattern | SharedResourceRecommendation,
    ) -> ActionableSignal:
        """
        转化为 ActionableSignal。

        社群信号优先级永远 <= medium（铁律）。
        """
        if isinstance(source, CohortMistakePattern):
            # 纵深防御：重新验证隐私阈值
            if source.cohort_size < _MIN_COHORT_SIZE:
                raise ValueError(f"cohort_size={source.cohort_size} below minimum {_MIN_COHORT_SIZE}")
            clamped_ratio = min(1.0, source.frequency_ratio)
            return ActionableSignal(
                signal_id=_uid("sig"),
                source_event_ids=["community_cohort_mistake"],
                source_system="community_signal",
                state_key="community_cohort_pattern",
                claim="cohort_mistake_detected",
                confidence=min(0.85, clamped_ratio),
                scope="current_sprint",
                ttl_hours=24,
                evidence_summary=(
                    f"在{source.subject}的{source.knowledge_node_id}节点，"
                    f"有{source.cohort_size}位同学中{int(clamped_ratio * 100)}%在此出错。"
                    f"常见误解：{source.common_misconception}"
                ),
                possible_effects=[
                    "show_cohort_mistake_hint",
                    "offer_shared_explanation",
                ],
                priority="medium",
            )

        if isinstance(source, SharedResourceRecommendation):
            return ActionableSignal(
                signal_id=_uid("sig"),
                source_event_ids=["community_shared_resource"],
                source_system="community_signal",
                state_key="community_resource_recommendation",
                claim="shared_resource_relevant",
                confidence=source.relevance_score,
                scope="current_sprint",
                ttl_hours=48,
                evidence_summary=(
                    f"跟你同考{source.subject}的{source.peer_count}位同学"
                    f"都在看「{source.resource_title}」"
                ),
                possible_effects=[
                    "show_resource_recommendation",
                ],
                priority="low",
            )

        raise TypeError(f"Unknown source type: {type(source).__name__}")
