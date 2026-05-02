"""Task-stuck pattern detection and product payload helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import desc, func, select

from app.models.task import Task, TaskStatus


def _strip(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _status_value(value: Any) -> str:
    return str(getattr(value, "value", value) or "").strip().upper()


@dataclass(frozen=True)
class TaskExecutionSignal:
    task_id: str
    title: str
    status: str
    estimated_minutes: int | None = None
    actual_minutes: int | None = None
    occurred_at: str | None = None
    source: str = "task"

    @property
    def issue_type(self) -> str | None:
        status = _status_value(self.status)
        if status == TaskStatus.ABANDONED.value:
            return "abandoned"
        if status == TaskStatus.STUCK.value:
            return "stuck"
        if (
            status == TaskStatus.COMPLETED.value
            and self.estimated_minutes
            and self.actual_minutes
            and self.actual_minutes >= self.estimated_minutes * TaskStuckPatternAnalyzer.OVERRUN_RATIO
        ):
            return "timeout"
        return None

    @property
    def is_issue(self) -> bool:
        return self.issue_type is not None

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "title": self.title,
            "status": self.status,
            "estimated_minutes": self.estimated_minutes,
            "actual_minutes": self.actual_minutes,
            "occurred_at": self.occurred_at,
            "issue_type": self.issue_type,
            "source": self.source,
        }


class TaskStuckPatternAnalyzer:
    """Pure helper for task-interruption detection shared by backend surfaces."""

    STREAK_LENGTH = 3
    OVERRUN_RATIO = 1.5

    _ISSUE_LABELS = {
        "abandoned": "放弃",
        "stuck": "卡住",
        "timeout": "超时",
    }

    @classmethod
    def from_task(cls, task: Task) -> TaskExecutionSignal:
        occurred_at = (
            getattr(task, "completed_at", None)
            or getattr(task, "updated_at", None)
            or getattr(task, "created_at", None)
        )
        return TaskExecutionSignal(
            task_id=str(getattr(task, "id", "")),
            title=_strip(getattr(task, "title", None)) or "未命名任务",
            status=_status_value(getattr(task, "status", "")),
            estimated_minutes=cls._positive_int(getattr(task, "estimated_minutes", None)),
            actual_minutes=cls._positive_int(getattr(task, "actual_minutes", None)),
            occurred_at=occurred_at.isoformat() if isinstance(occurred_at, datetime) else None,
        )

    @classmethod
    def summarize_health(cls, events: list[TaskExecutionSignal]) -> dict[str, Any]:
        recent = list(events[: cls.STREAK_LENGTH])
        if not recent:
            return {"visible": False}

        issue_events = [event for event in recent if event.is_issue]
        total = len(recent)
        issue_count = len(issue_events)
        issue_counts = cls._issue_counts(issue_events)
        dominant_issue = cls._dominant_issue(issue_counts)
        status = "healthy"
        trend_label = "节奏稳定"
        severity = "neutral"

        if total >= cls.STREAK_LENGTH and issue_count >= cls.STREAK_LENGTH:
            status = "needs_attention"
            trend_label = "需要关注"
            severity = "warning"
        elif cls.detect_recovery(events):
            status = "recovering"
            trend_label = "正在恢复"
            severity = "success"
        elif issue_count > 0:
            status = "watch"
            trend_label = "轻度关注"
            severity = "info"

        label = f"最近 {total} 张任务中有 {issue_count} 张出现卡点"
        if issue_count == 0:
            label = f"最近 {total} 张任务节奏稳定"
        elif dominant_issue:
            label = f"最近 {total} 张任务中有 {issue_counts[dominant_issue]} 张{cls._ISSUE_LABELS[dominant_issue]}"

        return {
            "visible": True,
            "status": status,
            "severity": severity,
            "label": label,
            "subtitle": trend_label,
            "trend_label": trend_label,
            "total_count": total,
            "issue_count": issue_count,
            "issue_counts": issue_counts,
            "dominant_issue": dominant_issue,
            "receipt": {
                "receipt_type": "task_health",
                "events": [event.to_dict() for event in recent],
                "decision_reason": "Aurora 只参考任务状态节奏，用来判断是否需要轻量帮你调整下一步。",
            },
        }

    @classmethod
    def detect_intervention(cls, events: list[TaskExecutionSignal]) -> dict[str, Any] | None:
        recent = list(events[: cls.STREAK_LENGTH])
        if len(recent) < cls.STREAK_LENGTH or any(not event.is_issue for event in recent):
            return None

        issue_counts = cls._issue_counts(recent)
        dominant_issue = cls._dominant_issue(issue_counts)
        titles = [event.title for event in recent]
        if dominant_issue and issue_counts[dominant_issue] == cls.STREAK_LENGTH:
            description = f"连续 {cls.STREAK_LENGTH} 张任务都{cls._ISSUE_LABELS[dominant_issue]}了"
        else:
            issue_labels = "、".join(cls._ISSUE_LABELS[event.issue_type or "stuck"] for event in recent)
            description = f"连续 {cls.STREAK_LENGTH} 张任务出现了{issue_labels}这样的卡点"

        return {
            "pattern_name": "Task Stuck Intervention",
            "pattern_type": "execution",
            "confidence": 0.86,
            "frequency": cls.STREAK_LENGTH,
            "streak_count": cls.STREAK_LENGTH,
            "description": description,
            "task_titles": titles,
            "task_ids": [event.task_id for event in recent if event.task_id],
            "issue_counts": issue_counts,
            "dominant_issue": dominant_issue,
            "micro_adjustment": "先把下一张任务卡缩小到 15-25 分钟，并只保留一个可验证输出。",
            "task_health": cls.summarize_health(events),
            "receipt": {
                "receipt_type": "task_stuck_intervention",
                "observed_events": [event.to_dict() for event in recent],
                "decision_reason": "连续任务卡点达到 3 次，触发一次可拒绝、可稍后的轻量 Aurora 介入。",
            },
        }

    @classmethod
    def detect_recovery(cls, events: list[TaskExecutionSignal]) -> dict[str, Any] | None:
        if len(events) < 4:
            return None
        latest_two = list(events[:2])
        prior = list(events[2 : min(len(events), 6)])
        if any(event.is_issue or _status_value(event.status) != TaskStatus.COMPLETED.value for event in latest_two):
            return None
        prior_issues = [event for event in prior if event.is_issue]
        if not prior_issues:
            return None
        return {
            "description": "最近的任务节奏已经恢复",
            "task_titles": [event.title for event in latest_two],
            "recovered_count": len(latest_two),
            "prior_issue_count": len(prior_issues),
            "message": "你最近的任务节奏恢复了。之前把任务变小、先拿下最小输出的方式看起来正在起作用。",
            "receipt": {
                "receipt_type": "task_stuck_recovery",
                "recovered_events": [event.to_dict() for event in latest_two],
                "prior_issue_events": [event.to_dict() for event in prior_issues[:3]],
            },
        }

    @classmethod
    def build_micro_session_payload(
        cls,
        pattern: dict[str, Any],
        *,
        next_task_title: str | None = None,
    ) -> dict[str, Any]:
        title = _strip(next_task_title) or "下一张任务卡"
        description = _strip(pattern.get("description")) or "最近任务节奏有点卡"
        return {
            "session_type": "task_stuck_light",
            "max_user_turns": 3,
            "estimated_minutes": 2,
            "scope": description,
            "entry_reason": {
                "trigger_source": "task_stuck_card",
                "observed_signals": [description, *list(pattern.get("task_titles") or [])[:2]],
                "suggested_agenda_preview": [
                    "确认卡点更像时间、难度还是启动问题",
                    f"把「{title}」调成一个更容易开始的版本",
                ],
                "why_now": "连续任务卡点会影响下一张任务的颗粒度，先轻量校准可以少绕路。",
                "estimated_minutes": 2,
            },
            "calibration_result_preview": {
                "state_patches": [
                    {
                        "target": "next_task_card",
                        "field": "estimated_minutes",
                        "operation": "cap",
                        "value": 25,
                    }
                ],
                "next_changes": [
                    "下一张任务卡会优先缩小范围",
                    "完成标准会改成一个可验证输出",
                ],
            },
        }

    @staticmethod
    def _positive_int(value: Any) -> int | None:
        numeric = _safe_float(value)
        if numeric is None or numeric <= 0:
            return None
        return int(numeric)

    @classmethod
    def _issue_counts(cls, events: list[TaskExecutionSignal]) -> dict[str, int]:
        counts = {"timeout": 0, "abandoned": 0, "stuck": 0}
        for event in events:
            issue = event.issue_type
            if issue in counts:
                counts[issue] += 1
        return counts

    @staticmethod
    def _dominant_issue(issue_counts: dict[str, int]) -> str | None:
        if not issue_counts:
            return None
        issue, count = max(issue_counts.items(), key=lambda item: item[1])
        return issue if count > 0 else None


async def load_recent_task_execution_signals(
    db,
    *,
    user_id: UUID,
    limit: int = 14,
) -> list[TaskExecutionSignal]:
    result = await db.execute(
        select(Task)
        .where(
            Task.user_id == user_id,
            Task.status.in_(
                [
                    TaskStatus.COMPLETED,
                    TaskStatus.ABANDONED,
                    TaskStatus.STUCK,
                ]
            ),
            Task.not_deleted_filter(),
        )
        .order_by(desc(func.coalesce(Task.completed_at, Task.updated_at, Task.created_at)))
        .limit(limit)
    )
    return [TaskStuckPatternAnalyzer.from_task(task) for task in result.scalars().all()]
