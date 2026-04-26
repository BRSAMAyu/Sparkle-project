"""
Core: execution
Phase: sense→clarify
Stage: Signal-to-Action Spine Layer 3 SignalRanking

信号排序与冲突解决层 — 当多个信号同时存在时，排序并解决冲突。

核心原则（来自 Final Spec Layer 3）：
- 所有信号不能全部进 Aurora，必须排序
- 冲突必须显式处理
- 仲裁优先级：安全 > deadline > 用户目标 > 行为证据 > 错因 > 资料 > 成就 > 社群 > 游戏化
- 排序维度：goal_impact / decision_relevance / urgency / confidence / freshness / cost_of_inaction

8 层架构中的位置：
Layer 1: RawEvent → Layer 2: ActionableSignal → Layer 3: SignalRanking → Layer 4: StateRegister
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from loguru import logger

from app.signals.types import ActionableSignal, _uid


# 仲裁优先级（数字越小越优先）
_PRIORITY_TIER: dict[str, int] = {
    # Tier 1: 安全 / 隐私 / 用户硬边界
    "safety_boundary": 1,
    "user_correction": 1,
    # Tier 2: deadline 生存策略
    "deadline_pressure": 2,
    "exam_rescue": 2,
    "recall_needed": 2,
    # Tier 3: 用户显式目标与偏好
    "goal_mode": 3,
    # Tier 4: 直接行为证据
    "task_granularity_fit": 4,
    "material_utilization": 4,
    # Tier 5: 学习结果与错因
    "knowledge_transfer": 5,
    "community_cohort_pattern": 5,
    # Tier 6: 资料与知识星图
    "retrieval_context": 6,
    "community_resource_recommendation": 6,
    # Tier 7: 成就 / 动机
    "growth_momentum": 7,
    # Tier 8: 其他
    "default": 9,
}


@dataclass
class RankedSignal:
    """排序后的信号。"""
    signal: ActionableSignal
    tier: int                    # 优先级层级
    composite_score: float       # 综合评分
    conflicts_with: list[str]    # 冲突的 signal_id 列表

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal_id": self.signal.signal_id,
            "state_key": self.signal.state_key,
            "tier": self.tier,
            "composite_score": round(self.composite_score, 3),
            "conflicts_with": self.conflicts_with,
        }


@dataclass
class RankingResult:
    """信号排序结果。"""
    ranked: list[RankedSignal]       # 按优先级排序
    suppressed: list[RankedSignal]   # 被冲突抑制的信号
    conflicts_resolved: list[dict[str, Any]]  # 冲突解决记录

    def to_dict(self) -> dict[str, Any]:
        return {
            "ranked": [r.to_dict() for r in self.ranked],
            "suppressed": [r.to_dict() for r in self.suppressed],
            "conflicts_resolved": self.conflicts_resolved,
        }


# 冲突规则：当两个 state_key 同时存在时的处理
_CONFLICT_RULES: dict[tuple[str, str], str] = {
    # (higher_priority_key, lower_priority_key): resolution_strategy
    ("growth_momentum", "task_granularity_fit"): "task_granularity_fit_wins",
    ("growth_momentum", "knowledge_transfer"): "knowledge_transfer_wins",
    ("recall_needed", "growth_momentum"): "recall_wins",
}


class SignalRanker:
    """
    Layer 3: 信号排序与冲突解决。

    职责：
    1. 为每个信号计算综合评分
    2. 按仲裁优先级排序
    3. 检测并解决冲突
    4. 抑制被冲突覆盖的信号
    """

    def rank(
        self,
        signals: list[ActionableSignal],
        *,
        max_signals: int = 5,
    ) -> RankingResult:
        """
        对信号列表排序并解决冲突。

        Args:
            signals: 待排序的信号列表
            max_signals: 最大保留信号数
        """
        if not signals:
            return RankingResult(ranked=[], suppressed=[], conflicts_resolved=[])

        # Step 1: 计算综合评分
        ranked_signals: list[RankedSignal] = []
        for signal in signals:
            tier = _PRIORITY_TIER.get(signal.state_key, _PRIORITY_TIER["default"])
            score = self._compute_composite_score(signal, tier)
            ranked_signals.append(RankedSignal(
                signal=signal,
                tier=tier,
                composite_score=score,
                conflicts_with=[],
            ))

        # Step 2: 按 tier + score 排序
        ranked_signals.sort(key=lambda r: (r.tier, -r.composite_score))

        # Step 3: 检测冲突
        conflicts_resolved: list[dict[str, Any]] = []
        suppressed_ids: set[str] = set()

        for i, rs in enumerate(ranked_signals):
            for j in range(i + 1, len(ranked_signals)):
                other = ranked_signals[j]
                pair = (rs.signal.state_key, other.signal.state_key)
                reverse_pair = (other.signal.state_key, rs.signal.state_key)

                rule = _CONFLICT_RULES.get(pair) or _CONFLICT_RULES.get(reverse_pair)
                if rule:
                    # rs 排在 other 前面（tier 更低=优先级更高）
                    # rs 是赢家，other 是输家
                    suppressed_ids.add(other.signal.signal_id)
                    rs.conflicts_with.append(other.signal.signal_id)
                    other.conflicts_with.append(rs.signal.signal_id)

                    conflicts_resolved.append({
                        "winner": rs.signal.state_key,
                        "loser": other.signal.state_key,
                        "rule": rule,
                    })

        # Step 4: 分离 ranked 和 suppressed
        ranked = [r for r in ranked_signals if r.signal.signal_id not in suppressed_ids]
        suppressed = [r for r in ranked_signals if r.signal.signal_id in suppressed_ids]

        # Step 5: 限制最大数量
        if len(ranked) > max_signals:
            overflow = ranked[max_signals:]
            suppressed.extend(overflow)
            ranked = ranked[:max_signals]

        logger.info(
            "SignalRanker: input={} ranked={} suppressed={} conflicts={}",
            len(signals), len(ranked), len(suppressed), len(conflicts_resolved),
        )

        return RankingResult(
            ranked=ranked,
            suppressed=suppressed,
            conflicts_resolved=conflicts_resolved,
        )

    def _compute_composite_score(self, signal: ActionableSignal, tier: int) -> float:
        """
        计算综合评分。

        公式：score = confidence * 0.4 + urgency * 0.3 + tier_inverse * 0.3
        """
        # Confidence
        confidence = signal.confidence

        # Urgency: high=1.0, medium=0.5, low=0.2
        urgency_map = {"high": 1.0, "medium": 0.5, "low": 0.2}
        urgency = urgency_map.get(signal.priority, 0.1)

        # Tier inverse: lower tier = higher score
        tier_inverse = max(0.0, 1.0 - (tier - 1) * 0.1)

        return confidence * 0.4 + urgency * 0.3 + tier_inverse * 0.3
