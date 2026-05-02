"""
Core: execution
Phase: sense→clarify→plan→execute
Stage: Signal-to-Action Spine P1-6 RecallNotification

Goal-respectful recall notification builder.
Turns NotificationDirective choices into short, user-facing recall messages.
"""

from __future__ import annotations

import inspect
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from loguru import logger

from app.signals.types import _uid

_COOLDOWN_SECONDS: dict[str, int] = {
    "undigested_material": 24 * 3600,
    "task_not_started": 12 * 3600,
    "task_missed": 8 * 3600,
    "pre_exam_silence": 6 * 3600,
    "long_silence": 48 * 3600,
    "context_window_optimal": 24 * 3600,
    "material_decay": 12 * 3600,
    "cohort_pattern_alert": 18 * 3600,
}

_FREQUENCY_TAGS: dict[str, str] = {
    "undigested_material": "1_per_day",
    "task_not_started": "1_per_day",
    "task_missed": "2_per_day",
    "pre_exam_silence": "2_per_day",
    "long_silence": "1_per_day",
    "context_window_optimal": "1_per_day",
    "material_decay": "1_per_day",
    "cohort_pattern_alert": "1_per_day",
}


def _utcnow() -> str:
    return datetime.now(UTC).isoformat()


def _cooldown_key(user_id: str, trigger_type: str) -> str:
    return f"spine:recall_notification_cooldown:{user_id}:{trigger_type}"


def _format_number(value: Any) -> Any:
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def _format_score(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


@dataclass
class RecallMessage:
    message_id: str
    trigger_type: str
    strategy: str
    title: str
    body: str
    deep_link: str
    cooldown_until: str | None
    frequency_tag: str
    reasoning: str = ""  # NUDGE-009: Why this notification was sent
    value_reason: str = ""
    effort_estimate: str = ""
    deadline_pressure_label: str = ""
    recall_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "message_id": self.message_id,
            "trigger_type": self.trigger_type,
            "strategy": self.strategy,
            "title": self.title,
            "body": self.body,
            "deep_link": self.deep_link,
            "cooldown_until": self.cooldown_until,
            "frequency_tag": self.frequency_tag,
            "reasoning": self.reasoning,
            "recall_reason": self.reasoning,
            "value_reason": self.value_reason,
            "effort_estimate": self.effort_estimate,
            "deadline_pressure_label": self.deadline_pressure_label,
            "recall_score": self.recall_score,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> RecallMessage:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


class RecallNotificationBuilder:
    """Build user-facing recall messages from NotificationDirective."""

    MESSAGE_TEMPLATES: dict[str, dict[str, dict[str, str]]] = {
        "undigested_material": {
            "low_effort_next_step": {
                "title": "你的课件还没看完",
                "body": "上次上传的{material_count}份资料，还有{undigested}份没诊断。花5分钟看看？",
                "deep_link": "/materials?filter=undigested",
            },
        },
        "task_not_started": {
            "low_effort_next_step": {
                "title": "任务等你开始",
                "body": "今天的第一个任务还没开始，要不要先看一眼？",
                "deep_link": "/tasks?status=pending",
            },
        },
        "task_missed": {
            "recovery_offer": {
                "title": "有个任务错过了",
                "body": "没关系，帮你重新安排了一个更合适的任务。",
                "deep_link": "/tasks?status=recovery",
            },
        },
        "pre_exam_silence": {
            "quick_review_offer": {
                "title": "考前快速复习",
                "body": "还有{days_to_exam}天就考了，要不要快速过一遍高频考点？",
                "deep_link": "/review?mode=quick",
            },
        },
        "long_silence": {
            "gentle_checkin": {
                "title": "好久不见",
                "body": "有{silence_days}天没见了。你的目标还在等你，要不要花几分钟看看进度？",
                "deep_link": "/home?tab=progress",
            },
        },
        "context_window_optimal": {
            "optimal_review": {
                "title": "复习好时机",
                "body": "现在是复习某个知识点的最佳时机，花几分钟效果最好。",
                "deep_link": "/review?mode=spaced",
            },
        },
        "material_decay": {
            "decay_alert": {
                "title": "知识在遗忘",
                "body": "你之前看过的资料，掌握度在下降。快速回顾能省很多时间。",
                "deep_link": "/materials?filter=decaying",
            },
        },
        "cohort_pattern_alert": {
            "peer_nudge": {
                "title": "同学们在复习",
                "body": "和你相似的同学最近都在学习。要不要也看看你的进度？",
                "deep_link": "/community?tab=activity",
            },
        },
    }

    # NUDGE-009: Explainable reasoning templates
    REASONING_TEMPLATES: dict[str, str] = {
        "undigested_material": "你上传了资料但还没完成诊断。资料如果不诊断就不会影响你的学习计划。",
        "task_not_started": "今天的计划中有待办任务。开始第一个任务能帮你保持节奏。",
        "task_missed": "有一个任务过了截止时间。跳过没关系，但重新安排能避免知识点脱节。",
        "pre_exam_silence": "考试临近但你最近没有复习活动。考前高频回顾对成绩帮助最大。",
        "long_silence": "你有一段时间没活动了。长时间中断会导致学习动量归零。",
        "context_window_optimal": "间隔重复算法判断当前是最佳复习窗口，错过这个窗口效率会降低。",
        "material_decay": "已诊断资料的知识正在衰减，及时回顾能用最少时间恢复记忆。",
        "cohort_pattern_alert": "和你相似的同学最近都在学习，同伴效应能提升学习动力。",
    }

    VALUE_REASON_TEMPLATES: dict[str, str] = {
        "undigested_material": "这些资料已经进入你的目标上下文，完成诊断后计划才不会基于缺失信息推进。",
        "task_not_started": "第一张任务卡启动后，系统才能校准今天的任务粒度和节奏。",
        "task_missed": "及时调整错过的任务，可以保护计划健康，避免后续知识点脱节。",
        "pre_exam_silence": "考试窗口很近，快速回到高频考点能优先保护最低可行通过路径。",
        "long_silence": "长时间沉默会导致学习动量归零，轻量级召回能帮助恢复最低可行节奏。",
        "context_window_optimal": "间隔重复研究表明，在知识即将遗忘时复习，记忆保持率提升 2-3 倍。",
        "material_decay": "知识正在衰减，及时回顾能用最少时间恢复记忆到有效水平。",
        "cohort_pattern_alert": "同伴效应研究表明，看到同类用户活跃能显著提升学习动力和参与度。",
    }

    EFFORT_ESTIMATE_TEMPLATES: dict[str, str] = {
        "undigested_material": "预计先花 5 分钟确认资料诊断入口。",
        "task_not_started": "预计先投入 5 分钟打开任务并完成第一小步。",
        "task_missed": "预计 3 分钟选择调整、跳过或重排。",
        "pre_exam_silence": "预计 10 分钟完成一轮高频考点快扫。",
        "long_silence": "预计 3 分钟查看进度和下一步。",
        "context_window_optimal": "预计 5-10 分钟完成一次快扫复习。",
        "material_decay": "预计 5 分钟回顾核心要点。",
        "cohort_pattern_alert": "预计 5 分钟查看进度对比。",
    }

    DEADLINE_PRESSURE_LABELS: dict[str, str] = {
        "undigested_material": "目标上下文不完整",
        "task_not_started": "今日节奏待启动",
        "task_missed": "已过截止时间",
        "pre_exam_silence": "考前窗口",
        "long_silence": "节奏中断",
        "context_window_optimal": "记忆窗口",
        "material_decay": "知识衰减中",
        "cohort_pattern_alert": "同伴活跃期",
    }

    def build_message(
        self,
        trigger_type: str,
        message_strategy: str,
        context: dict[str, Any],
    ) -> RecallMessage | None:
        templates_for_trigger = self.MESSAGE_TEMPLATES.get(trigger_type)
        if not templates_for_trigger:
            return None

        template = templates_for_trigger.get(message_strategy)
        if not template:
            return None

        safe_context = self._normalize_context(trigger_type, context)
        try:
            body = template["body"].format(**safe_context)
        except KeyError as exc:
            logger.warning(
                "Recall notification missing template context: trigger={} strategy={} key={}",
                trigger_type,
                message_strategy,
                exc,
            )
            return None

        return RecallMessage(
            message_id=_uid("rmsg"),
            trigger_type=trigger_type,
            strategy=message_strategy,
            title=template["title"],
            body=body,
            deep_link=template["deep_link"],
            cooldown_until=context.get("cooldown_until"),
            frequency_tag=context.get("frequency_tag", _FREQUENCY_TAGS.get(trigger_type, "1_per_day")),
            reasoning=self.REASONING_TEMPLATES.get(trigger_type, ""),
            value_reason=context.get("value_reason") or self.VALUE_REASON_TEMPLATES.get(trigger_type, ""),
            effort_estimate=context.get("effort_estimate") or self.EFFORT_ESTIMATE_TEMPLATES.get(trigger_type, ""),
            deadline_pressure_label=(
                context.get("deadline_pressure_label") or self.DEADLINE_PRESSURE_LABELS.get(trigger_type, "")
            ),
            recall_score=_format_score(context.get("recall_score")),
        )

    def check_cooldown(
        self,
        user_id: str,
        trigger_type: str,
        redis_client: Any,
    ) -> bool:
        """Check if user is in cooldown for this trigger type."""
        key = _cooldown_key(user_id, trigger_type)
        raw = self._sync_get(redis_client, key)
        return bool(raw)

    async def check_cooldown_async(
        self,
        user_id: str,
        trigger_type: str,
        redis_client: Any,
    ) -> bool:
        """Async Redis variant for orchestrator integrations."""
        key = _cooldown_key(user_id, trigger_type)
        raw = await redis_client.get(key)
        return bool(raw)

    def record_sent(
        self,
        user_id: str,
        trigger_type: str,
        redis_client: Any,
    ) -> None:
        """Record that a recall message was sent, starting cooldown."""
        cooldown_seconds = _COOLDOWN_SECONDS.get(trigger_type, 24 * 3600)
        cooldown_until = (datetime.now(UTC) + timedelta(seconds=cooldown_seconds)).isoformat()
        payload = json.dumps({"sent_at": _utcnow(), "cooldown_until": cooldown_until})
        key = _cooldown_key(user_id, trigger_type)
        self._sync_set(redis_client, key, payload, ex=cooldown_seconds)

    async def record_sent_async(
        self,
        user_id: str,
        trigger_type: str,
        redis_client: Any,
    ) -> str:
        """Async Redis variant for orchestrator integrations. Returns cooldown end."""
        cooldown_seconds = _COOLDOWN_SECONDS.get(trigger_type, 24 * 3600)
        cooldown_until = (datetime.now(UTC) + timedelta(seconds=cooldown_seconds)).isoformat()
        payload = json.dumps({"sent_at": _utcnow(), "cooldown_until": cooldown_until})
        await redis_client.set(_cooldown_key(user_id, trigger_type), payload, ex=cooldown_seconds)
        return cooldown_until

    def build_user_preference_schema(self) -> dict[str, Any]:
        """Return the schema for user recall preferences."""
        return {
            trigger_type: {
                "enabled": True,
                "quiet_hours": "22:00-08:00",
                "max_per_day": 2 if frequency == "2_per_day" else 1,
            }
            for trigger_type, frequency in _FREQUENCY_TAGS.items()
        }

    def get_cooldown_until(self, trigger_type: str) -> str:
        cooldown_seconds = _COOLDOWN_SECONDS.get(trigger_type, 24 * 3600)
        return (datetime.now(UTC) + timedelta(seconds=cooldown_seconds)).isoformat()

    @staticmethod
    def _build_reasoning(trigger_type: str, strategy: str, context: dict[str, Any]) -> str:
        reasons = {
            "undigested_material": "检测到{material_count}份资料中还有{undigested}份未完成诊断，建议用户花少量时间完成。",
            "task_not_started": "今日首个任务尚未开始，通过低阻力提醒推动执行。",
            "task_missed": "检测到任务过期未完成，提供恢复方案降低重新启动的心理门槛。",
            "spaced_recall": "基于间隔重复算法，当前是最佳复习时间窗口。",
            "momentum_recovery": "检测到学习动量下降趋势，主动介入恢复节奏。",
            "streak_celebration": "检测到连续学习streak达成，确认并强化积极行为。",
            "long_silence": "检测到{silence_days}天无活动，通过温和召回恢复学习节奏。",
            "context_window_optimal": "间隔重复算法判断当前是最佳复习窗口，推荐轻量复习。",
            "material_decay": "已诊断资料知识正在衰减，推荐快速回顾恢复记忆。",
            "cohort_pattern_alert": "同类用户群体活跃度较高，通过同伴效应助推学习参与。",
        }
        template = reasons.get(trigger_type, f"基于{trigger_type}触发规则，策略为{strategy}，主动提醒用户。")
        try:
            return template.format(**context)
        except (KeyError, IndexError):
            return template

    def _normalize_context(self, trigger_type: str, context: dict[str, Any]) -> dict[str, Any]:
        normalized = {k: _format_number(v) for k, v in context.items()}
        if trigger_type == "undigested_material":
            material_count = (
                context.get("material_count") or context.get("uploaded") or context.get("uploaded_files_count") or 0
            )
            normalized["material_count"] = _format_number(material_count)
            normalized["undigested"] = _format_number(context.get("undigested", 0))
        elif trigger_type == "pre_exam_silence":
            days_to_exam = context.get("days_to_exam", context.get("exam_deadline_days", 0))
            normalized["days_to_exam"] = _format_number(days_to_exam)
        elif trigger_type == "long_silence":
            silence_days = context.get("silence_days", context.get("hours_since_last_activity", 0) / 24.0)
            normalized["silence_days"] = _format_number(silence_days)
        return normalized

    def _sync_get(self, redis_client: Any, key: str) -> Any:
        if hasattr(redis_client, "_store"):
            return redis_client._store.get(key)
        get = getattr(redis_client, "get", None)
        if get is None or inspect.iscoroutinefunction(get):
            return None
        return get(key)

    def _sync_set(self, redis_client: Any, key: str, value: str, ex: int | None = None) -> None:
        if hasattr(redis_client, "_store"):
            redis_client._store[key] = value
            return
        set_method = getattr(redis_client, "set", None)
        if set_method is None or inspect.iscoroutinefunction(set_method):
            logger.warning("RecallNotificationBuilder.record_sent skipped async Redis client in sync path")
            return
        set_method(key, value, ex=ex)
