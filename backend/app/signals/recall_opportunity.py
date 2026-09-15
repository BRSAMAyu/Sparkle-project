"""
Core: execution
Phase: sense→clarify
Stage: Signal-to-Action Spine P1-4 RecallOpportunity + P2-3.1 ML Scoring

召回机会检测 — 检测用户需要被"召回"的场景。

支持 8 种召回（FV-21: 从 4 扩展到 8）：
1. 上传资料未诊断 — 用户上传了文件但没有触发诊断流程
2. 首张任务卡未启动 — 计划生成后第一张任务没开始
3. 任务错过 — 已分配的任务超过 deadline 未完成
4. 考前 48h 沉默 — 考试倒计时 48h 内无任何活动
5. 长时间沉默 — 用户超过 72h 无任何活动（非考试场景）
6. 最佳复习窗口 — 间隔重复算法判断当前是最佳复习时机
7. 资料衰减 — 已诊断资料的知识正在衰减（Ebbinghaus curve）
8. 同伴模式提醒 — 同类用户群体正在活跃复习，形成社交助推

核心原则：
- 召回是温和提醒，不是催促
- 每种召回有对应的状态补丁（不是纯文本）
- 召回频率有冷却期
- ML 评分决定召回优先级和是否值得打扰
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from app.signals.types import ActionableSignal, _uid


@dataclass
class RecallTrigger:
    """单个召回触发条件。"""
    trigger_type: str        # one of 8 trigger types
    user_id: str
    context: dict[str, Any]  # 触发上下文
    urgency: str             # "low" | "medium" | "high"
    message_template: str    # 召回消息模板
    value_reason: str = ""   # why this recall is worth the interruption
    effort_estimate: str = ""  # how long the user would need to spend
    deadline_pressure: str = ""  # deadline pressure label
    recall_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "trigger_type": self.trigger_type,
            "user_id": self.user_id,
            "context": self.context,
            "urgency": self.urgency,
            "message_template": self.message_template,
            "value_reason": self.value_reason,
            "effort_estimate": self.effort_estimate,
            "deadline_pressure": self.deadline_pressure,
            "recall_score": self.recall_score,
        }


# 召回冷却期（秒）— FV-21: 扩展到 8 种
_COOLDOWN_SECONDS: dict[str, int] = {
    "undigested_material": 3600,          # 1 小时
    "task_not_started": 7200,            # 2 小时
    "task_missed": 3600,                 # 1 小时
    "pre_exam_silence": 1800,            # 30 分钟
    "long_silence": 86400,               # 24 小时
    "context_window_optimal": 43200,     # 12 小时
    "material_decay": 14400,             # 4 小时
    "cohort_pattern_alert": 21600,       # 6 小时
}


class RecallOpportunityDetector:
    """
    P1-4 + P2-3.1: 检测需要召回的场景。

    职责：
    1. 检测 8 种召回触发条件（FV-21: 从 4 扩展到 8）
    2. 检查冷却期
    3. 使用 RecallRanker ML 评分
    4. 生成 ActionableSignal
    """

    def __init__(self, ranker: Any | None = None):
        """Initialize with optional ML ranker.

        Args:
            ranker: RecallRanker instance. If None, uses rule-based scoring only.
        """
        self._ranker = ranker

    # ── Original 4 triggers ──────────────────────────────────────────

    def check_undigested_material(
        self,
        *,
        user_id: str,
        uploaded_files_count: int,
        diagnosed_files_count: int,
        hours_since_upload: float,
    ) -> RecallTrigger | None:
        """上传了资料但没有诊断。"""
        if diagnosed_files_count >= uploaded_files_count:
            return None
        if hours_since_upload < 0.5:
            return None

        undigested = uploaded_files_count - diagnosed_files_count
        rule_score = min(1.0, 0.55 + undigested * 0.1)
        ml_score = self._score_trigger(
            "undigested_material", user_id=user_id,
            goal_value=0.6, decay_factor=min(1.0, hours_since_upload / 48.0),
            material_relevance=0.7,
        )

        return RecallTrigger(
            trigger_type="undigested_material",
            user_id=user_id,
            context={
                "uploaded": uploaded_files_count,
                "diagnosed": diagnosed_files_count,
                "undigested": undigested,
                "hours_since_upload": hours_since_upload,
            },
            urgency="medium",
            message_template=(
                f"你上传了{uploaded_files_count}份资料，"
                f"还有{undigested}份没看过。要我帮你诊断一下吗？"
            ),
            value_reason="资料已进入目标上下文，但尚未被诊断，及时处理能避免计划基于不完整信息。",
            effort_estimate="预计 5 分钟完成资料诊断入口确认。",
            deadline_pressure="目标上下文不完整",
            recall_score=self._blend(rule_score, ml_score),
        )

    def check_task_not_started(
        self,
        *,
        user_id: str,
        task_id: str,
        hours_since_assignment: float,
        has_started: bool,
    ) -> RecallTrigger | None:
        """首张任务卡未启动。"""
        if has_started:
            return None
        if hours_since_assignment < 1.0:
            return None

        rule_score = min(1.0, 0.35 + hours_since_assignment / 12)
        ml_score = self._score_trigger(
            "task_not_started", user_id=user_id,
            goal_value=0.5, decay_factor=min(1.0, hours_since_assignment / 24.0),
            deadline_proximity=min(1.0, hours_since_assignment / 12.0),
        )

        return RecallTrigger(
            trigger_type="task_not_started",
            user_id=user_id,
            context={
                "task_id": task_id,
                "hours_since_assignment": hours_since_assignment,
            },
            urgency="low" if hours_since_assignment < 3 else "medium",
            message_template=(
                f"你的任务已经等了{hours_since_assignment:.0f}小时了。"
                "要不要先看一眼？哪怕只做 5 分钟也行。"
            ),
            value_reason="首张任务卡迟迟未启动会让计划无法产生反馈，轻量启动能帮助系统校准任务粒度。",
            effort_estimate="预计先投入 5 分钟打开任务并完成第一小步。",
            deadline_pressure="今日节奏待启动",
            recall_score=self._blend(rule_score, ml_score),
        )

    def check_task_missed(
        self,
        *,
        user_id: str,
        task_id: str,
        deadline_hours: float,
        is_completed: bool,
    ) -> RecallTrigger | None:
        """任务错过 deadline。"""
        if is_completed:
            return None
        if deadline_hours > 0:
            return None  # 还没到 deadline

        overdue_h = abs(deadline_hours)
        rule_score = min(1.0, 0.7 + overdue_h / 24)
        ml_score = self._score_trigger(
            "task_missed", user_id=user_id,
            goal_value=0.7, deadline_proximity=min(1.0, overdue_h / 12.0),
        )

        return RecallTrigger(
            trigger_type="task_missed",
            user_id=user_id,
            context={
                "task_id": task_id,
                "deadline_overdue_hours": overdue_h,
            },
            urgency="high",
            message_template=(
                "这张任务错过了截止时间。"
                "要调整一下计划，还是直接跳过？"
            ),
            value_reason="任务已经错过截止时间，及时选择调整或跳过可以保护计划健康。",
            effort_estimate="预计 3 分钟选择调整、跳过或重排。",
            deadline_pressure="已过截止时间",
            recall_score=self._blend(rule_score, ml_score),
        )

    def check_pre_exam_silence(
        self,
        *,
        user_id: str,
        exam_deadline_days: float,
        hours_since_last_activity: float,
    ) -> RecallTrigger | None:
        """考前 48h 沉默。"""
        if exam_deadline_days > 2.0:
            return None  # 考试还远
        if hours_since_last_activity < 2.0:
            return None  # 最近有活动

        rule_score = 0.95 if exam_deadline_days <= 1.0 else 0.82
        ml_score = self._score_trigger(
            "pre_exam_silence", user_id=user_id,
            goal_value=0.9,
            deadline_proximity=min(1.0, (2.0 - exam_deadline_days) / 2.0),
            silence_hours=min(1.0, hours_since_last_activity / 48.0),
        )

        return RecallTrigger(
            trigger_type="pre_exam_silence",
            user_id=user_id,
            context={
                "exam_deadline_days": exam_deadline_days,
                "hours_since_last_activity": hours_since_last_activity,
            },
            urgency="high" if exam_deadline_days <= 1.0 else "medium",
            message_template=(
                f"还有{exam_deadline_days:.0f}天就考试了，"
                "最近没看到你的活动。要我帮你快速过一遍重点吗？"
            ),
            value_reason="考试窗口很近且最近沉默，召回能帮助用户回到最低可行通过路径。",
            effort_estimate="预计 10 分钟完成一轮高频考点快扫。",
            deadline_pressure="考前窗口",
            recall_score=self._blend(rule_score, ml_score),
        )

    # ── FV-21: 4 new ML-based triggers ───────────────────────────────

    def check_long_silence(
        self,
        *,
        user_id: str,
        hours_since_last_activity: float,
        has_active_goal: bool,
        is_exam_period: bool = False,
    ) -> RecallTrigger | None:
        """长时间沉默 — 用户超过 72h 无任何活动（非考试场景）。

        New trigger for FV-21: detects prolonged user disengagement.
        """
        if is_exam_period:
            return None  # 考试期间用 pre_exam_silence
        if hours_since_last_activity < 72.0:
            return None
        if not has_active_goal:
            return None  # 无活跃目标则不打扰

        silence_days = hours_since_last_activity / 24.0
        ml_score = self._score_trigger(
            "long_silence", user_id=user_id,
            goal_value=0.6,
            silence_hours=min(1.0, hours_since_last_activity / 168.0),  # Normalize to 1 week
        )
        rule_score = min(1.0, 0.4 + silence_days / 14.0)

        return RecallTrigger(
            trigger_type="long_silence",
            user_id=user_id,
            context={
                "hours_since_last_activity": hours_since_last_activity,
                "silence_days": silence_days,
                "has_active_goal": has_active_goal,
            },
            urgency="medium" if silence_days < 7 else "high",
            message_template=(
                f"有{silence_days:.0f}天没见了。"
                "你的目标还在等你。要不要花几分钟看看进度？"
            ),
            value_reason="长时间沉默会导致学习动量归零，轻量级召回能帮助恢复最低可行节奏。",
            effort_estimate="预计 3 分钟查看进度和下一步。",
            deadline_pressure="节奏中断",
            recall_score=self._blend(rule_score, ml_score),
        )

    def check_context_window_optimal(
        self,
        *,
        user_id: str,
        last_review_hours: float,
        mastery_level: float,
        optimal_interval_hours: float,
        current_fatigue: float = 0.0,
    ) -> RecallTrigger | None:
        """最佳复习窗口 — 间隔重复算法判断当前是最佳复习时机。

        New trigger for FV-21: uses Ebbinghaus forgetting curve to detect
        when a knowledge node is at the optimal recall boundary.
        """
        # Only trigger when we're within the optimal window (±20%)
        ratio = last_review_hours / max(0.1, optimal_interval_hours)
        if ratio < 0.8 or ratio > 1.3:
            return None
        if mastery_level > 0.9:
            return None  # Already mastered, no need to review
        if current_fatigue > 0.7:
            return None  # Too fatigued for review

        # Optimal decay: we want to review when knowledge has decayed just enough
        decay_factor = 1.0 - mastery_level * math.exp(-last_review_hours / max(1.0, optimal_interval_hours))
        ml_score = self._score_trigger(
            "context_window_optimal", user_id=user_id,
            goal_value=0.6,
            decay_factor=decay_factor,
            fatigue_state=current_fatigue,
            material_relevance=0.8,
        )
        rule_score = 0.70 if mastery_level < 0.5 else 0.60

        return RecallTrigger(
            trigger_type="context_window_optimal",
            user_id=user_id,
            context={
                "last_review_hours": last_review_hours,
                "mastery_level": mastery_level,
                "optimal_interval_hours": optimal_interval_hours,
                "decay_factor": decay_factor,
            },
            urgency="low",
            message_template=(
                "现在是复习「某个知识点」的最佳时机。"
                "花几分钟回顾一下，效果比以后再补好很多。"
            ),
            value_reason="间隔重复研究表明，在知识即将遗忘时复习，记忆保持率提升 2-3 倍。",
            effort_estimate="预计 5-10 分钟完成一次快扫复习。",
            deadline_pressure="记忆窗口",
            recall_score=self._blend(rule_score, ml_score),
        )

    def check_material_decay(
        self,
        *,
        user_id: str,
        material_id: str,
        days_since_diagnosis: float,
        mastery_delta: float,
        relevance_to_goal: float,
        has_been_recalled: bool = False,
    ) -> RecallTrigger | None:
        """资料衰减 — 已诊断资料的知识正在衰减。

        New trigger for FV-21: detects when previously digested material
        knowledge is decaying below a useful threshold.
        """
        if has_been_recalled:
            return None  # Already recalled recently
        if days_since_diagnosis < 3.0:
            return None  # Too recent
        if mastery_delta >= 0:
            return None  # Knowledge is stable or growing

        # Ebbinghaus-inspired decay: exponential decay model
        decay_rate = abs(mastery_delta) / max(0.1, days_since_diagnosis)
        if decay_rate < 0.02:
            return None  # Decay too slow to worry about

        decay_factor = min(1.0, decay_rate * 10.0)  # Normalize
        ml_score = self._score_trigger(
            "material_decay", user_id=user_id,
            goal_value=relevance_to_goal,
            decay_factor=decay_factor,
            material_relevance=relevance_to_goal,
        )
        rule_score = min(1.0, 0.5 + decay_factor * 0.3)

        return RecallTrigger(
            trigger_type="material_decay",
            user_id=user_id,
            context={
                "material_id": material_id,
                "days_since_diagnosis": days_since_diagnosis,
                "mastery_delta": mastery_delta,
                "relevance_to_goal": relevance_to_goal,
                "decay_rate": decay_rate,
            },
            urgency="medium" if decay_factor >= 0.5 else "low",
            message_template=(
                f"你之前看过的资料，掌握度在下降（已过{days_since_diagnosis:.0f}天）。"
                "要不要快速回顾一下重点？"
            ),
            value_reason="知识正在衰减，及时回顾能用最少时间恢复记忆到有效水平。",
            effort_estimate="预计 5 分钟回顾核心要点。",
            deadline_pressure="知识衰减中",
            recall_score=self._blend(rule_score, ml_score),
        )

    def check_cohort_pattern_alert(
        self,
        *,
        user_id: str,
        cohort_activity_rate: float,
        user_relative_position: str,  # "below" | "average" | "above"
        days_until_deadline: float | None = None,
    ) -> RecallTrigger | None:
        """同伴模式提醒 — 同类用户群体正在活跃复习。

        New trigger for FV-21: leverages anonymized cohort data to nudge
        users when their peer group is actively engaged.
        """
        if cohort_activity_rate < 0.4:
            return None  # Cohort isn't active enough to use as signal
        if user_relative_position != "below":
            return None  # Only nudge users who are behind their cohort

        deadline_proximity = 0.0
        if days_until_deadline is not None:
            deadline_proximity = min(1.0, max(0.0, 1.0 - days_until_deadline / 14.0))

        ml_score = self._score_trigger(
            "cohort_pattern_alert", user_id=user_id,
            goal_value=0.5,
            cohort_response_rate=cohort_activity_rate,
            deadline_proximity=deadline_proximity,
        )
        rule_score = min(1.0, 0.45 + cohort_activity_rate * 0.3)

        return RecallTrigger(
            trigger_type="cohort_pattern_alert",
            user_id=user_id,
            context={
                "cohort_activity_rate": cohort_activity_rate,
                "user_relative_position": user_relative_position,
                "days_until_deadline": days_until_deadline,
            },
            urgency="low",
            message_template=(
                "和你相似的同学最近都在复习。"
                "要不要也花点时间看看你的进度？"
            ),
            value_reason="同伴效应研究表明，看到同类用户活跃能显著提升学习动力和参与度。",
            effort_estimate="预计 5 分钟查看进度对比。",
            deadline_pressure="同伴活跃期",
            recall_score=self._blend(rule_score, ml_score),
        )

    # ── Shared helpers ────────────────────────────────────────────────

    def to_actionable_signal(self, trigger: RecallTrigger) -> ActionableSignal:
        """将召回触发转化为 ActionableSignal。"""
        priority_map = {"low": "low", "medium": "medium", "high": "high"}

        return ActionableSignal(
            signal_id=_uid("sig"),
            source_event_ids=[f"recall_{trigger.trigger_type}"],
            source_system="recall_opportunity",
            state_key="recall_needed",
            claim=trigger.trigger_type,
            confidence=trigger.recall_score or 0.80,
            scope="current_sprint",
            ttl_hours=6,
            evidence_summary=trigger.value_reason or trigger.message_template,
            possible_effects=[
                "send_recall_message",
                "adjust_plan_if_needed",
            ],
            priority=priority_map.get(trigger.urgency, "low"),
        )

    def get_cooldown_seconds(self, trigger_type: str) -> int:
        """获取冷却时间。"""
        return _COOLDOWN_SECONDS.get(trigger_type, 3600)

    def _score_trigger(
        self,
        trigger_type: str,
        *,
        user_id: str = "",
        goal_value: float = 0.5,
        decay_factor: float = 0.5,
        user_response_rate: float = 0.5,
        fatigue_state: float = 0.0,
        deadline_proximity: float = 0.0,
        material_relevance: float = 0.5,
        silence_hours: float = 0.0,
        cohort_response_rate: float = 0.5,
    ) -> float:
        """Score a trigger using the ML ranker if available."""
        if self._ranker is None:
            return 0.5  # Neutral score when no ML available

        from app.services.ml.recall_ranker import RecallFeatures

        features = RecallFeatures(
            goal_value=goal_value,
            decay_factor=decay_factor,
            user_response_rate=user_response_rate,
            fatigue_state=fatigue_state,
            deadline_proximity=deadline_proximity,
            material_relevance=material_relevance,
            silence_hours=silence_hours,
            cohort_response_rate=cohort_response_rate,
        )
        return self._ranker.score(features)

    @staticmethod
    def _blend(rule_score: float, ml_score: float) -> float:
        """Blend rule-based and ML scores. Rule score gets 70% weight."""
        return max(0.0, min(1.0, 0.7 * rule_score + 0.3 * ml_score))
