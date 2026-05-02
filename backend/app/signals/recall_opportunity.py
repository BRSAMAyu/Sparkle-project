"""
Core: execution
Phase: sense→clarify
Stage: Signal-to-Action Spine P1-4 RecallOpportunity

召回机会检测 — 检测用户需要被"召回"的场景。

支持 4 种召回：
1. 上传资料未诊断 — 用户上传了文件但没有触发诊断流程
2. 首张任务卡未启动 — 计划生成后第一张任务没开始
3. 任务错过 — 已分配的任务超过 deadline 未完成
4. 考前 48h 沉默 — 考试倒计时 48h 内无任何活动

核心原则：
- 召回是温和提醒，不是催促
- 每种召回有对应的状态补丁（不是纯文本）
- 召回频率有冷却期
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.signals.types import ActionableSignal, _uid


@dataclass
class RecallTrigger:
    """单个召回触发条件。"""
    trigger_type: str        # "undigested_material" | "task_not_started" | "task_missed" | "pre_exam_silence"
    user_id: str
    context: dict[str, Any]  # 触发上下文
    urgency: str             # "low" | "medium" | "high"
    message_template: str    # 召回消息模板
    value_reason: str = ""   # why this recall is worth the interruption
    recall_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "trigger_type": self.trigger_type,
            "user_id": self.user_id,
            "context": self.context,
            "urgency": self.urgency,
            "message_template": self.message_template,
            "value_reason": self.value_reason,
            "recall_score": self.recall_score,
        }


# 召回冷却期（秒）
_COOLDOWN_SECONDS: dict[str, int] = {
    "undigested_material": 3600,     # 1 小时
    "task_not_started": 7200,        # 2 小时
    "task_missed": 3600,             # 1 小时
    "pre_exam_silence": 1800,        # 30 分钟
}


class RecallOpportunityDetector:
    """
    P1-4: 检测需要召回的场景。

    职责：
    1. 检测 4 种召回触发条件
    2. 检查冷却期
    3. 生成 ActionableSignal
    """

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
            recall_score=min(1.0, 0.55 + undigested * 0.1),
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
            recall_score=min(1.0, 0.35 + hours_since_assignment / 12),
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

        return RecallTrigger(
            trigger_type="task_missed",
            user_id=user_id,
            context={
                "task_id": task_id,
                "deadline_overdue_hours": abs(deadline_hours),
            },
            urgency="high",
            message_template=(
                "这张任务错过了截止时间。"
                "要调整一下计划，还是直接跳过？"
            ),
            value_reason="任务已经错过截止时间，及时选择调整或跳过可以保护计划健康。",
            recall_score=min(1.0, 0.7 + abs(deadline_hours) / 24),
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
            recall_score=0.95 if exam_deadline_days <= 1.0 else 0.82,
        )

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
