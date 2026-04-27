"""
Core: execution
Phase: sense→clarify
Stage: Signal-to-Action Spine Layer 3 SignalRanking

信号排序与冲突解决层 — 当多个信号同时存在时，排序并解决冲突。

Final Spec Section 3 — 10 ranking dimensions:
- goal_impact: 是否影响当前目标达成
- decision_relevance: 是否会改变本轮行动
- urgency: 是否受 deadline 压力影响
- confidence: 信号可信度
- freshness: 是否新鲜
- contradiction_level: 是否和已有状态冲突
- cost_of_inaction: 不处理的代价
- reversibility: 判断错了是否容易纠正
- user_visibility_need: 是否应该让用户知道
- privacy_sensitivity: 是否涉及隐私或外部反馈

8 层架构中的位置：
Layer 1: RawEvent → Layer 2: ActionableSignal → Layer 3: SignalRanking → Layer 4: StateRegister
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
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
    "community_resource_recommendation": 6,
    # Tier 7: 成就 / 动机
    "growth_momentum": 7,
    # Tier 8: 其他
    "default": 9,
}

# ── 10-Dimension Weight Configuration ──────────────────────────────────
_DIMENSION_WEIGHTS = {
    "goal_impact": 0.15,
    "decision_relevance": 0.12,
    "urgency": 0.12,
    "confidence": 0.15,
    "freshness": 0.08,
    "cost_of_inaction": 0.10,
    "reversibility": 0.08,
    "user_visibility_need": 0.07,
    "privacy_sensitivity": 0.05,
    "contradiction_level": 0.08,
}

# state_keys where user should be notified
_HIGH_VISIBILITY_KEYS = {
    "exam_rescue", "deadline_pressure", "task_granularity_fit",
    "knowledge_transfer", "safety_boundary", "user_correction",
}

# state_keys with community/external data — higher privacy sensitivity
_HIGH_PRIVACY_KEYS = {
    "community_cohort_pattern", "community_resource_recommendation",
}

# scope → reversibility (shorter scope = easier to reverse)
_SCOPE_REVERSIBILITY = {
    "turn": 1.0,
    "task": 0.95,
    "session": 0.85,
    "day": 0.7,
    "sprint": 0.5,
    "goal": 0.3,
    "relationship": 0.2,
    "long_term": 0.1,
}


@dataclass
class RankedSignal:
    """排序后的信号。"""
    signal: ActionableSignal
    tier: int                    # 优先级层级
    composite_score: float       # 综合评分
    conflicts_with: list[str]    # 冲突的 signal_id 列表
    dimension_scores: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal_id": self.signal.signal_id,
            "state_key": self.signal.state_key,
            "tier": self.tier,
            "composite_score": round(self.composite_score, 3),
            "conflicts_with": self.conflicts_with,
            "dimension_scores": {k: round(v, 3) for k, v in self.dimension_scores.items()},
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


# 冲突规则：当两个 state_key 同时存在时，低优先级（loser）被抑制。
# Key: (loser_state_key, winner_state_key) — loser 被 suppress
# Iron Law: 成就信号永远不能压过焦虑、超时和错因信号
_CONFLICT_RULES: dict[tuple[str, str], str] = {
    ("growth_momentum", "task_granularity_fit"): "task_granularity_fit_wins",
    ("growth_momentum", "knowledge_transfer"): "knowledge_transfer_wins",
    ("growth_momentum", "recall_needed"): "recall_wins",
    ("growth_momentum", "deadline_pressure"): "deadline_wins",
    ("growth_momentum", "exam_rescue"): "exam_rescue_wins",
    ("growth_momentum", "affective_pressure"): "affective_pressure_wins",
    ("community_cohort_pattern", "knowledge_transfer"): "knowledge_transfer_wins",
    ("community_resource_recommendation", "material_utilization"): "material_utilization_wins",
    ("community_resource_recommendation", "source_relevance"): "source_relevance_wins",
    ("recall_needed", "exam_rescue"): "exam_rescue_wins",
}


class SignalRanker:
    """
    Layer 3: 信号排序与冲突解决 — 10 维评分。

    职责：
    1. 为每个信号在 10 个维度上计算评分
    2. 加权合成综合评分
    3. 按仲裁优先级排序
    4. 检测并解决冲突
    5. 抑制被冲突覆盖的信号
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

        # Step 1: 计算 10 维评分
        ranked_signals: list[RankedSignal] = []
        for signal in signals:
            tier = _PRIORITY_TIER.get(signal.state_key, _PRIORITY_TIER["default"])
            dims = self._compute_dimensions(signal, tier)
            score = sum(dims[k] * _DIMENSION_WEIGHTS[k] for k in _DIMENSION_WEIGHTS)
            ranked_signals.append(RankedSignal(
                signal=signal,
                tier=tier,
                composite_score=score,
                conflicts_with=[],
                dimension_scores=dims,
            ))

        # Step 2: 按 tier + score 排序
        ranked_signals.sort(key=lambda r: (r.tier, -r.composite_score))

        # Step 3: 检测冲突 — 规则显式指定 winner/loser
        conflicts_resolved: list[dict[str, Any]] = []
        suppressed_ids: set[str] = set()

        # Build state_key → RankedSignal index for O(1) lookup
        by_key: dict[str, list[RankedSignal]] = {}
        for rs in ranked_signals:
            by_key.setdefault(rs.signal.state_key, []).append(rs)

        for (loser_key, winner_key), rule in _CONFLICT_RULES.items():
            losers = by_key.get(loser_key, [])
            winners = by_key.get(winner_key, [])
            if not losers or not winners:
                continue
            for loser_rs in losers:
                for winner_rs in winners:
                    if loser_rs.signal.signal_id in suppressed_ids:
                        continue
                    suppressed_ids.add(loser_rs.signal.signal_id)
                    winner_rs.conflicts_with.append(loser_rs.signal.signal_id)
                    loser_rs.conflicts_with.append(winner_rs.signal.signal_id)
                    conflicts_resolved.append({
                        "winner": winner_key,
                        "loser": loser_key,
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

    def _compute_dimensions(self, signal: ActionableSignal, tier: int) -> dict[str, float]:
        """计算 Final Spec Section 3 的 10 维评分。每维归一化到 [0, 1]。"""
        return {
            "goal_impact": self._goal_impact(tier),
            "decision_relevance": self._decision_relevance(signal),
            "urgency": self._urgency(signal),
            "confidence": signal.confidence,
            "freshness": self._freshness(signal),
            "cost_of_inaction": self._cost_of_inaction(signal),
            "reversibility": self._reversibility(signal),
            "user_visibility_need": self._user_visibility_need(signal),
            "privacy_sensitivity": self._privacy_sensitivity(signal),
            "contradiction_level": 0.5,  # default; requires state register for accurate value
        }

    @staticmethod
    def _goal_impact(tier: int) -> float:
        """Tier 1-3 = high impact (1.0), tier 7-9 = low (0.2)."""
        return max(0.2, 1.0 - (tier - 1) * 0.1)

    @staticmethod
    def _decision_relevance(signal: ActionableSignal) -> float:
        """Signals with concrete possible_effects are more decision-relevant."""
        if signal.possible_effects:
            return min(1.0, 0.5 + len(signal.possible_effects) * 0.15)
        return 0.3

    @staticmethod
    def _urgency(signal: ActionableSignal) -> float:
        """Priority: high=1.0, medium=0.5, low=0.2."""
        return {"high": 1.0, "medium": 0.5, "low": 0.2}.get(signal.priority, 0.1)

    @staticmethod
    def _freshness(signal: ActionableSignal) -> float:
        """Signals <5 min old = 1.0, >24h = 0.1."""
        try:
            normalized = signal.created_at.replace("Z", "+00:00")
            created = datetime.fromisoformat(normalized)
            if created.tzinfo is None:
                created = created.replace(tzinfo=UTC)
            age_seconds = (datetime.now(UTC) - created).total_seconds()
            if age_seconds < 300:
                return 1.0
            if age_seconds > 86400:
                return 0.1
            return max(0.1, 1.0 - (age_seconds / 86400) * 0.9)
        except (ValueError, TypeError):
            return 0.5

    @staticmethod
    def _cost_of_inaction(signal: ActionableSignal) -> float:
        """High priority + tier 1-3 = high cost of not acting."""
        urgency = {"high": 1.0, "medium": 0.5, "low": 0.2}.get(signal.priority, 0.1)
        tier_factor = 1.0 if _PRIORITY_TIER.get(signal.state_key, 9) <= 3 else 0.5
        return min(1.0, urgency * 0.6 + tier_factor * 0.4)

    @staticmethod
    def _reversibility(signal: ActionableSignal) -> float:
        """Short scope = easy to reverse = high score."""
        return _SCOPE_REVERSIBILITY.get(signal.scope, 0.5)

    @staticmethod
    def _user_visibility_need(signal: ActionableSignal) -> float:
        """Safety, deadline, error signals should be visible."""
        return 1.0 if signal.state_key in _HIGH_VISIBILITY_KEYS else 0.3

    @staticmethod
    def _privacy_sensitivity(signal: ActionableSignal) -> float:
        """Community signals have higher privacy sensitivity."""
        return 0.8 if signal.state_key in _HIGH_PRIVACY_KEYS else 0.2
