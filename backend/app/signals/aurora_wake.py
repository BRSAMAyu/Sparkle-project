"""
Core: execution
Phase: sense→clarify
Stage: Signal-to-Action Spine P1-2 AuroraWakeEligibility

Aurora 唤醒资格判断 — 判断是否可以唤醒完整 Aurora Session。

核心原则：
- Aurora Core Session 是稀缺资源，不能无限调用
- 有明确的唤醒条件、冷却期、配额管理
- 判断基于当前状态而非猜测
- 唤醒原因必须可追溯
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from loguru import logger



@dataclass
class AuroraWakeEligibility:
    """Aurora 唤醒资格检查结果。"""
    can_wake: bool
    user_id: str
    quota_remaining: int               # 剩余可用次数
    cooldown_status: str               # "available" | "cooling" | "exhausted"
    recommended_session_type: str      # "strategy_recalibration" | "deep_review" | "motivation_check"
    wake_reasons: list[str]            # 唤醒理由
    suggested_scope: str               # 建议的范围
    cooldown_minutes_left: int = 0     # 冷却剩余分钟

    def to_dict(self) -> dict[str, Any]:
        return {
            "can_wake": self.can_wake,
            "user_id": self.user_id,
            "quota_remaining": self.quota_remaining,
            "cooldown_status": self.cooldown_status,
            "recommended_session_type": self.recommended_session_type,
            "wake_reasons": self.wake_reasons,
            "suggested_scope": self.suggested_scope,
            "cooldown_minutes_left": self.cooldown_minutes_left,
        }


# 配额限制
_DEFAULT_QUOTA_PER_DAY = 3
_DEFAULT_COOLDOWN_MINUTES = 60


class AuroraWakeJudge:
    """
    P1-2: Spine 管线专用的 Aurora 唤醒资格判断（简化版）。

    注意：完整的唤醒策略由 aurora/runtime_v1/wake_policy.py 的
    AuroraWakePolicyService 管理（含 Redis 冷却、配额追踪）。
    本模块是 Spine 管线的入口判断，不替代 Aurora 内部实现。

    唤醒条件（满足任一即可，但需通过冷却和配额检查）：
    1. strategy_recalibration — 策略连续失效（≥2 次负向 outcome）
    2. deep_review — 用户主动请求深度复盘
    3. motivation_check — 成就动量停滞

    禁止：
    - 无理由唤醒
    - 冷却期内唤醒
    - 配额耗尽后唤醒
    """

    def judge(
        self,
        *,
        user_id: str,
        quota_remaining: int,
        cooldown_status: str,
        cooldown_minutes_left: int = 0,
        consecutive_negative_outcomes: int = 0,
        user_requested_deep_review: bool = False,
        momentum_stalled: bool = False,
        model_conflict: bool = False,
        consecutive_user_rejections: int = 0,
        goal_changed: bool = False,
        deadline_high_risk: bool = False,
        self_model_confidence_dropped: bool = False,
    ) -> AuroraWakeEligibility:
        """
        判断唤醒资格。

        Args:
            user_id: 用户 ID
            quota_remaining: 今日剩余配额
            cooldown_status: 冷却状态
            cooldown_minutes_left: 冷却剩余分钟
            consecutive_negative_outcomes: 连续负向结果次数
            user_requested_deep_review: 用户是否主动请求深度复盘
            momentum_stalled: 成就动量是否停滞
            model_conflict: 系统发现关键模型冲突
            consecutive_user_rejections: 连续用户否定判断次数
            goal_changed: 目标发生变化
            deadline_high_risk: deadline 高风险
            self_model_confidence_dropped: SparkleSelfModel 置信度下降
        """
        wake_reasons: list[str] = []
        session_type = "strategy_recalibration"
        scope = ""

        # 检查唤醒理由（按优先级排列，前者优先决定 session_type）
        if deadline_high_risk:
            wake_reasons.append("deadline_high_risk")
            session_type = "exam_emergency"
            scope = "deadline 高风险，紧急校准"

        if model_conflict:
            wake_reasons.append("model_conflict")
            if not scope:
                session_type = "conflict_resolution"
                scope = "系统发现关键模型冲突"

        if consecutive_user_rejections >= 2:
            wake_reasons.append("consecutive_user_rejections")
            if not scope:
                session_type = "belief_revision"
                scope = "用户连续否定系统判断"

        if consecutive_negative_outcomes >= 2:
            wake_reasons.append("consecutive_strategy_failure")
            if not scope:
                session_type = "strategy_recalibration"
                scope = "策略连续失效，需要 Aurora 重新校准"

        if goal_changed:
            wake_reasons.append("goal_changed")
            if not scope:
                session_type = "goal_realignment"
                scope = "目标发生变化，重新对齐"

        if self_model_confidence_dropped:
            wake_reasons.append("self_model_confidence_dropped")
            if not scope:
                session_type = "self_model_recalibration"
                scope = "SparkleSelfModel 置信度下降"

        if user_requested_deep_review:
            wake_reasons.append("user_requested_deep_review")
            if not scope:
                session_type = "deep_review"
                scope = "用户主动请求深度复盘"

        if momentum_stalled:
            wake_reasons.append("momentum_stalled")
            if not scope:
                session_type = "motivation_check"
                scope = "成就动量停滞，可能需要重新对齐目标"

        # 没有唤醒理由 → 不可唤醒
        if not wake_reasons:
            return AuroraWakeEligibility(
                can_wake=False,
                user_id=user_id,
                quota_remaining=quota_remaining,
                cooldown_status=cooldown_status,
                recommended_session_type="",
                wake_reasons=[],
                suggested_scope="",
                cooldown_minutes_left=cooldown_minutes_left,
            )

        # 配额耗尽
        if quota_remaining <= 0:
            return AuroraWakeEligibility(
                can_wake=False,
                user_id=user_id,
                quota_remaining=0,
                cooldown_status="exhausted",
                recommended_session_type=session_type,
                wake_reasons=wake_reasons,
                suggested_scope=scope,
                cooldown_minutes_left=0,
            )

        # 冷却中
        if cooldown_status == "cooling":
            return AuroraWakeEligibility(
                can_wake=False,
                user_id=user_id,
                quota_remaining=quota_remaining,
                cooldown_status="cooling",
                recommended_session_type=session_type,
                wake_reasons=wake_reasons,
                suggested_scope=scope,
                cooldown_minutes_left=cooldown_minutes_left,
            )

        # 通过所有检查
        result = AuroraWakeEligibility(
            can_wake=True,
            user_id=user_id,
            quota_remaining=quota_remaining,
            cooldown_status="available",
            recommended_session_type=session_type,
            wake_reasons=wake_reasons,
            suggested_scope=scope,
            cooldown_minutes_left=0,
        )

        logger.info(
            "AuroraWake: user={} can_wake={} type={} reasons={}",
            user_id, True, session_type, wake_reasons,
        )

        return result
