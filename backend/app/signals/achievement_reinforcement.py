"""
Core: execution
Phase: reinforce→adapt
Stage: Signal-to-Action Spine P1-1 AchievementReinforcementConsumer

成就回流消费者 — 将成就事件转化为 spine 可消费的信号。

核心原则：
- 成就解锁/进度 → growth momentum 信号
- 不直接写长期人格，只影响当前 sprint 的 tone/nudge/challenge
- momentum 高 → 降低压力，强化鼓励
- momentum 停滞 → 考虑调整策略

禁止：成就事件不能直接修改 personality 或 long-term profile。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from loguru import logger

from app.signals.types import ActionableSignal, _uid


@dataclass
class AchievementMomentum:
    """成就动量快照。"""
    user_id: str
    recent_unlocks: int          # 最近 7 天解锁数
    active_streaks: int          # 当前活跃连击数
    in_progress_count: int       # 进行中成就数
    momentum_score: float        # 0.0 ~ 1.0，综合动量分
    period_days: int = 7

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "recent_unlocks": self.recent_unlocks,
            "active_streaks": self.active_streaks,
            "in_progress_count": self.in_progress_count,
            "momentum_score": self.momentum_score,
            "period_days": self.period_days,
        }


# 动量阈值
_MOMENTUM_HIGH = 0.7
_MOMENTUM_STALLED = 0.3


class AchievementReinforcementConsumer:
    """
    P1-1: 消费成就事件，生成 growth momentum 信号。

    职责：
    1. 接收 achievement.progress / achievement.unlocked 事件
    2. 计算 momentum score
    3. 生成 ActionableSignal 用于 spine 消费
    4. 不直接写 personality
    """

    def compute_momentum(
        self,
        *,
        user_id: str,
        recent_unlocks: int,
        active_streaks: int,
        in_progress_count: int,
        period_days: int = 7,
    ) -> AchievementMomentum:
        """
        计算成就动量分数。

        公式：
        momentum = (
            unlock_factor * 0.5 +
            streak_factor * 0.3 +
            progress_factor * 0.2
        )
        """
        # 解锁因子：2+ 解锁/周 = 满分
        unlock_factor = min(1.0, recent_unlocks / 2.0)

        # 连击因子：3+ 连击 = 满分
        streak_factor = min(1.0, active_streaks / 3.0)

        # 进度因子：有进行中成就表示活跃
        progress_factor = min(1.0, in_progress_count / 5.0) if in_progress_count > 0 else 0.0

        momentum_score = (
            unlock_factor * 0.5
            + streak_factor * 0.3
            + progress_factor * 0.2
        )

        return AchievementMomentum(
            user_id=user_id,
            recent_unlocks=recent_unlocks,
            active_streaks=active_streaks,
            in_progress_count=in_progress_count,
            momentum_score=round(momentum_score, 2),
            period_days=period_days,
        )

    def to_actionable_signal(
        self,
        momentum: AchievementMomentum,
    ) -> ActionableSignal | None:
        """
        将动量转化为 ActionableSignal。

        - momentum >= 0.7 → growth_momentum_high（强化鼓励）
        - momentum <= 0.3 且 in_progress > 0 → growth_momentum_stalled（调整策略）
        - 其他 → 不生成信号（无行动意义）
        """
        if momentum.momentum_score >= _MOMENTUM_HIGH:
            return ActionableSignal(
                signal_id=_uid("sig"),
                source_event_ids=["achievement_momentum"],
                source_system="achievement_reinforcement",
                state_key="growth_momentum",
                claim="momentum_high",
                confidence=min(1.0, momentum.momentum_score),
                scope="current_sprint",
                ttl_hours=48,
                evidence_summary=(
                    f"7天解锁{momentum.recent_unlocks}个成就，"
                    f"{momentum.active_streaks}个连击"
                ),
                possible_effects=[
                    "reinforce_current_strategy",
                    "increase_challenge_difficulty",
                ],
                priority="low",
            )

        if (momentum.momentum_score <= _MOMENTUM_STALLED
                and momentum.in_progress_count > 0):
            return ActionableSignal(
                signal_id=_uid("sig"),
                source_event_ids=["achievement_momentum"],
                source_system="achievement_reinforcement",
                state_key="growth_momentum",
                claim="momentum_stalled",
                confidence=0.70,
                scope="current_sprint",
                ttl_hours=24,
                evidence_summary=(
                    f"7天仅解锁{momentum.recent_unlocks}个成就，"
                    f"但有{momentum.in_progress_count}个进行中"
                ),
                possible_effects=[
                    "reduce_task_pressure",
                    "offer_encouragement",
                    "suggest_strategy_change",
                ],
                priority="medium",
            )

        return None

    def process_achievement_event(
        self,
        *,
        user_id: str,
        event_type: str,
        recent_unlocks: int,
        active_streaks: int,
        in_progress_count: int,
    ) -> ActionableSignal | None:
        """
        处理单个成就事件，返回信号（如果有）。

        这是外部调用的入口方法。
        """
        momentum = self.compute_momentum(
            user_id=user_id,
            recent_unlocks=recent_unlocks,
            active_streaks=active_streaks,
            in_progress_count=in_progress_count,
        )

        signal = self.to_actionable_signal(momentum)

        if signal:
            logger.info(
                "AchievementReinforcement: user={} momentum={:.2f} signal={}",
                user_id, momentum.momentum_score, signal.claim,
            )
        else:
            logger.debug(
                "AchievementReinforcement: user={} momentum={:.2f} no signal",
                user_id, momentum.momentum_score,
            )

        return signal
