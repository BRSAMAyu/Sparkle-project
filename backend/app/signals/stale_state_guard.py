"""
Core: execution
Phase: sense→clarify
Stage: Signal-to-Action Spine P0-2 TimeContext + StaleStateGuard

时间感知机制 — 用户离开后回来，系统不能假装时间没过去。

检测逻辑：
- 用户返回时检查 last_interaction_at
- 如有活跃任务，检查任务是否应该已经结束
- 生成 TimeDeltaPacket → 返回恢复选项

用户体验：
"你离开了大约 2 小时。
上一张 TCP 任务卡原本预计 45 分钟结束，但我还没有收到完成反馈。
先不用重新开始。你现在是哪种情况？
[做完了，补记录] [做了一半，卡住了] [没开始] [换个小任务]"
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from loguru import logger

# ── 阈值 ──────────────────────────────────────────────────────────
_STALE_THRESHOLD_MIN = 60  # 离开超过 60 分钟即视为 stale
_TASK_OVERRUN_FACTOR = 1.5  # 任务预计时间 × 1.5 后仍未完成 → 视为 stale


@dataclass
class TimeContext:
    """P0-2: 当前时间上下文。"""
    now: str                           # ISO timestamp
    timezone: str = "Asia/Shanghai"
    goal_deadline: str | None = None
    time_to_deadline_hours: float | None = None
    last_user_interaction_at: str | None = None
    elapsed_since_last_interaction_min: float | None = None
    active_task_id: str | None = None
    active_task_expected_end_at: str | None = None
    active_task_status: str | None = None  # "started" | "no_completion" | None
    quiet_hours_active: bool = False
    deadline_phase: str = "normal_sprint"  # normal_sprint / high_pressure / final_day

    def to_dict(self) -> dict[str, Any]:
        return {
            "now": self.now,
            "timezone": self.timezone,
            "goal_deadline": self.goal_deadline,
            "time_to_deadline_hours": self.time_to_deadline_hours,
            "last_user_interaction_at": self.last_user_interaction_at,
            "elapsed_since_last_interaction_min": self.elapsed_since_last_interaction_min,
            "active_task_id": self.active_task_id,
            "active_task_expected_end_at": self.active_task_expected_end_at,
            "active_task_status": self.active_task_status,
            "quiet_hours_active": self.quiet_hours_active,
            "deadline_phase": self.deadline_phase,
        }


@dataclass
class TimeDeltaPacket:
    """用户返回时的状态快照和恢复建议。"""
    elapsed_since_last_seen_min: float
    pending_task_status: str      # "expected_finished_but_no_feedback" | "still_in_progress" | "no_active_task"
    new_background_updates: list[str] = field(default_factory=list)
    deadline_phase_changed: bool = False
    recommended_resume_strategy: str = "ask_task_status_then_recover"
    resume_options: list[dict[str, str]] = field(default_factory=list)
    message_template: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "elapsed_since_last_seen_min": self.elapsed_since_last_seen_min,
            "pending_task_status": self.pending_task_status,
            "new_background_updates": self.new_background_updates,
            "deadline_phase_changed": self.deadline_phase_changed,
            "recommended_resume_strategy": self.recommended_resume_strategy,
            "resume_options": self.resume_options,
            "message_template": self.message_template,
        }


class StaleStateGuard:
    """
    P0-2: 用户返回时的 Stale State 检测。

    核心原则：
    - 不假装时间没过去
    - 不强制用户重新开始
    - 提供低摩擦恢复选项
    """

    def check(
        self,
        time_context: TimeContext,
        *,
        user_id: str = "",
    ) -> TimeDeltaPacket | None:
        """
        检查用户返回时的状态。

        Returns:
            TimeDeltaPacket if stale state detected, None if fresh.
        """
        elapsed = time_context.elapsed_since_last_interaction_min
        if elapsed is None or elapsed < _STALE_THRESHOLD_MIN:
            return None

        # 确定任务状态
        pending_status = self._determine_task_status(time_context)

        # 构建恢复选项
        options = self._build_resume_options(pending_status)

        # 生成消息模板
        message = self._build_message(elapsed, pending_status, time_context)

        packet = TimeDeltaPacket(
            elapsed_since_last_seen_min=elapsed,
            pending_task_status=pending_status,
            recommended_resume_strategy=self._recommend_strategy(pending_status),
            resume_options=options,
            message_template=message,
        )

        logger.info(
            "StaleStateGuard: user={} elapsed={:.0f}min task_status={}",
            user_id, elapsed, pending_status,
        )

        return packet

    def _determine_task_status(self, ctx: TimeContext) -> str:
        """判断活跃任务的状态。"""
        if not ctx.active_task_id:
            return "no_active_task"

        if ctx.active_task_status == "started" or ctx.active_task_status == "no_completion":
            # 有任务但可能已完成或过期
            return "expected_finished_but_no_feedback"

        return "no_active_task"

    def _build_resume_options(self, pending_status: str) -> list[dict[str, str]]:
        """构建恢复选项。"""
        if pending_status == "expected_finished_but_no_feedback":
            return [
                {"label": "做完了，补记录", "value": "completed_late", "semantic": "task_done"},
                {"label": "做了一半，卡住了", "value": "half_done", "semantic": "task_blocked"},
                {"label": "没开始", "value": "not_started", "semantic": "task_skipped"},
                {"label": "换个小任务", "value": "switch_smaller", "semantic": "task_downgrade"},
            ]
        return [
            {"label": "继续上次的话题", "value": "continue", "semantic": "resume"},
            {"label": "直接做今天的任务", "value": "start_fresh", "semantic": "new_task"},
        ]

    def _recommend_strategy(self, pending_status: str) -> str:
        """推荐恢复策略。"""
        if pending_status == "expected_finished_but_no_feedback":
            return "ask_task_status_then_recover"
        return "suggest_resume_or_start_fresh"

    def _build_message(
        self,
        elapsed: float,
        pending_status: str,
        ctx: TimeContext,
    ) -> str:
        """生成返回消息模板。"""
        hours = int(elapsed // 60)
        mins = int(elapsed % 60)

        if hours > 0:
            time_desc = f"大约 {hours} 小时"
            if mins > 0:
                time_desc += f" {mins} 分钟"
        else:
            time_desc = f"大约 {mins} 分钟"

        if pending_status == "expected_finished_but_no_feedback":
            return (
                f"你离开了{time_desc}。"
                "上一张任务卡原本应该已经结束，但我还没有收到完成反馈。"
                "先不用重新开始。告诉我你现在在哪个状态，我会接上。"
            )

        return f"你离开了{time_desc}。欢迎回来，我们继续。"

    # ── 神性时刻: 记得时间 ──────────────────────────────────────────

    def build_recovery_card(
        self,
        packet: TimeDeltaPacket,
        *,
        deadline_phase: str = "normal_sprint",
        days_to_deadline: int | None = None,
    ) -> dict[str, Any]:
        """
        Build a structured recovery card for the "Remember Time" divine moment.

        The card includes:
        - Time context (how long away, what changed)
        - Deadline urgency (if applicable)
        - Personalized resume action based on where the user left off
        """
        hours = int(packet.elapsed_since_last_seen_min // 60)
        mins = int(packet.elapsed_since_last_seen_min % 60)

        if hours > 0:
            time_summary = f"{hours} 小时 {mins} 分钟"
        else:
            time_summary = f"{mins} 分钟"

        # Deadline context
        deadline_context = None
        if days_to_deadline is not None and days_to_deadline <= 7:
            deadline_context = {
                "days_to_deadline": days_to_deadline,
                "urgency": "high" if days_to_deadline <= 3 else "medium",
                "message": f"距考试还有 {days_to_deadline} 天" if days_to_deadline > 0 else "考试日",
            }

        # Recommended action
        action = self._derive_recovery_action(packet, deadline_phase)

        return {
            "type": "divine_moment_recovery",
            "time_summary": time_summary,
            "message": packet.message_template,
            "resume_options": packet.resume_options,
            "recommended_action": action,
            "deadline_context": deadline_context,
        }

    @staticmethod
    def _derive_recovery_action(packet: TimeDeltaPacket, deadline_phase: str) -> dict[str, str]:
        """Derive the single best recovery action from context."""
        if deadline_phase == "final_day":
            return {"action": "light_recall", "reason": "考试日，只推荐轻量回忆任务"}
        if packet.pending_task_status == "expected_finished_but_no_feedback":
            return {"action": "ask_status", "reason": "需要确认上次任务状态才能继续"}
        if deadline_phase == "high_pressure":
            return {"action": "high_yield_drill", "reason": "冲刺阶段，优先高频收益节点"}
        return {"action": "resume_or_fresh", "reason": "正常节奏恢复"}
