from __future__ import annotations
import asyncio
import json
from datetime import date, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.cache import cache_service
from app.core.agent_profiles import AgentRole, ModelTier, TaskType
from app.models.accountability import AccountabilityPartnership, AccountabilitySlotType, AccountabilityStatus
from app.models.card_protocol import InterventionAcceptanceStatus, InterventionRecord
from app.models.chat import ChatMessage, ChatSession as ChatSessionModel, MessageRole
from app.models.user import User
from app.api.v1.accountability import _build_relationship_summary
from app.orchestration.session_state_mixin import SessionStateMixin
from app.services.cognitive_service import CognitiveService
from app.services.intervention_record_service import InterventionRecordService
from app.services.llm_service import get_configured_llm_service_for_tier
from app.services.memory_service import MemoryService
from app.services.personalization import get_personalization_engine
from app.services.personalization.inferred_meta import INFERRED_META, build_inferred_explanation
from app.services.personalization.preference_service import PreferenceService
from app.services.profile_context_service import ProfileContextService
from app.services.profile_insight_control_service import ProfileInsightControlService
from app.services.profile_write_service import ProfileWriteService
from app.services.insight_copy import present_pattern_name
from app.services.system_update_service import SystemUpdateService, build_system_update
from app.services.user_insight_transparency_service import UserInsightTransparencyService

router = APIRouter(prefix="/profile", tags=["profile"])


def _snippet(value: str, limit: int = 80) -> str:
    if not value:
        return ""
    return value if len(value) <= limit else f"{value[:limit - 1]}…"


def _strip(value: Any) -> str:
    return str(value or "").strip()


def _response_style_from_depth(depth: float) -> str:
    if depth >= 0.7:
        return "detailed"
    if depth <= 0.3:
        return "concise"
    return "balanced"


class ChatOpeningRequest(BaseModel):
    conversation_id: UUID


class ChatOpeningResponse(BaseModel):
    created: bool
    conversation_id: UUID
    message_id: UUID | None = None
    content: str | None = None


def _source_score(source: str) -> float:
    mapping = {
        "user": 1.0,
        "mixed": 0.6,
        "system": 0.2,
    }
    return mapping.get(source, 0.5)


def _is_chat_opening_update(update: dict[str, Any]) -> bool:
    if not isinstance(update, dict):
        return False
    update_type = str(update.get("type") or "").strip()
    metadata = update.get("metadata") if isinstance(update.get("metadata"), dict) else {}
    evolution_kind = str(metadata.get("evolution_kind") or "").strip()
    return update_type == "plan_adjusted_from_error" or evolution_kind in {
        "adjustment",
        "plan_reasoning",
        "progress_comparison",
        "proactive_insight",
        "weekly_learning_report",
    }


def _compose_chat_opening_content(prompt_context: dict[str, str]) -> str:
    lines: list[str] = []
    for key in ("proactive_opening_message", "pending_observation", "post_adaptation_question"):
        text = str(prompt_context.get(key) or "").strip()
        if text and text not in lines:
            lines.append(text)
    return "\n\n".join(lines).strip()


def _extract_intervention_id(updates: list[dict[str, Any]]) -> UUID | None:
    for update in updates:
        if not isinstance(update, dict):
            continue
        metadata = update.get("metadata") if isinstance(update.get("metadata"), dict) else {}
        raw = metadata.get("intervention_id")
        if not raw:
            continue
        try:
            return UUID(str(raw))
        except (TypeError, ValueError):
            continue
    return None


def _build_chat_opening_widgets(
    *,
    proactive_opening_message: str,
    post_adaptation_question: str,
    intervention_id: UUID | None,
) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []

    if proactive_opening_message:
        actions.append(
            {
                "label": "看看我改了什么",
                "type": "route",
                "route": "/tasks",
            }
        )

    if intervention_id and post_adaptation_question:
        actions.extend(
            [
                {
                    "label": "这样更合适",
                    "type": "intervention_feedback",
                    "intervention_id": str(intervention_id),
                    "feedback_action": "acted",
                    "message": "已记住，这次调整对你是有帮助的。",
                },
                {
                    "label": "不太对",
                    "type": "intervention_feedback",
                    "intervention_id": str(intervention_id),
                    "feedback_action": "dismissed",
                    "message": "收到，我不会继续沿着这个方向强推。",
                },
            ]
        )

    if not actions:
        return []

    return [
        {
            "type": "next_actions",
            "data": {
                "title": "你想怎么继续？",
                "actions": actions,
            },
        }
    ]


async def _mark_chat_opening_intervention_seen(
    *,
    db: AsyncSession,
    user_id: UUID,
    intervention_id: UUID | None,
) -> None:
    if intervention_id is None:
        return

    record = await db.get(InterventionRecord, intervention_id)
    if record is None or record.user_id != user_id:
        return

    service = InterventionRecordService(db)
    if record.acceptance_status == InterventionAcceptanceStatus.CREATED:
        await service.mark_delivered(record.id)
    if record.acceptance_status == InterventionAcceptanceStatus.DELIVERED:
        await service.mark_seen(record.id)


def _risk_score(risk: str) -> float:
    mapping = {
        "low": 0.1,
        "medium": 0.4,
        "high": 0.8,
    }
    return mapping.get(risk, 0.4)


def _field_score(field_type: str) -> float:
    mapping = {
        "preference": 1.0,
        "behavior": 0.4,
        "analysis": 0.2,
    }
    return mapping.get(field_type, 0.5)


def _goal_type_label(value: str | None) -> str:
    mapping = {
        "exam": "备考目标",
        "skill": "技能目标",
        "interest": "兴趣探索",
    }
    return mapping.get(str(value or "").strip().lower(), "学习目标")


def _build_first_session_message(
    *,
    learning_goal: str | None,
    learning_goal_type: str | None,
    knowledge_level: str | None,
    study_time_minutes: int | None,
) -> str:
    """Deterministic fallback for the first-session opener message."""
    if not (learning_goal or "").strip():
        return "你好！我是 Sparkle。告诉我你现在最想突破的学习难关，我们一起来想办法。"
    goal = learning_goal.strip()
    goal_label = _goal_type_label(learning_goal_type)
    level_map = {
        "beginner": "刚开始接触",
        "intermediate": "有一些基础",
        "advanced": "已经有较深积累",
    }
    level_label = level_map.get(str(knowledge_level or "").strip(), "")
    time_label = f"每天 {study_time_minutes} 分钟" if study_time_minutes else "你的时间"
    lines = [f"你好！我已经了解你想推进「{goal}」这个{goal_label}目标。"]
    if level_label:
        lines.append(f"你目前{level_label}，我会根据这个来调整节奏和难度。")
    lines.append(f"我们用{time_label}来开始——先告诉我：你现在这个目标里，觉得最卡住的是哪一块？")
    return "\n".join(lines)


async def _generate_first_session_message(
    *,
    learning_goal: str | None,
    learning_goal_type: str | None,
    knowledge_level: str | None,
    study_time_minutes: int | None,
) -> str:
    """Generate a personalized AI opening message for the user's very first chat session."""
    fallback = _build_first_session_message(
        learning_goal=learning_goal,
        learning_goal_type=learning_goal_type,
        knowledge_level=knowledge_level,
        study_time_minutes=study_time_minutes,
    )
    goal = (learning_goal or "").strip()
    if not goal:
        return fallback

    summary_bits = [f"目标类型：{_goal_type_label(learning_goal_type)}", f"目标：{goal}"]
    if knowledge_level:
        summary_bits.append(f"当前基础：{knowledge_level}")
    if study_time_minutes is not None:
        summary_bits.append(f"每日学习时间：{study_time_minutes} 分钟")

    llm = await get_configured_llm_service_for_tier(
        AgentRole.GENERATION,
        ModelTier.FAST,
        task_type=TaskType.QUICK_QUERY,
        reasoning_mode="fast",
    )
    messages = [
        {
            "role": "system",
            "content": (
                "你是 Sparkle，一个AI学习成长伙伴。"
                "用户刚完成画像设置，现在第一次进入对话界面。"
                "请生成一段自然的开场白，3句话以内：第1句表达你已了解他们的目标；"
                "第2句（可选）针对他们的基础/时间给出一句个性化观察；"
                "第3句以开放式问题结尾，邀请他们告诉你现在最卡住的地方。"
                "语气温暖、直接，像朋友不像客服。总字数80字内。不要markdown，不要列表。"
            ),
        },
        {"role": "user", "content": "\n".join(summary_bits)},
    ]
    try:
        message = await asyncio.wait_for(llm.chat(messages, temperature=0.3), timeout=8.0)
        message = " ".join((message or "").split())
        return message if message else fallback
    except Exception:
        return fallback


def _build_onboarding_preview_fallback(payload: OnboardingRequest) -> str:
    goal = (payload.learning_goal or "").strip()
    goal_label = _goal_type_label(payload.learning_goal_type)
    minutes = payload.study_time_minutes
    time_hint = f"、每天大约 {minutes} 分钟" if minutes else ""
    if not goal:
        return "先告诉我你现在最想推进的学习目标，我会立刻帮你判断难度并给出第一版起步建议。"
    return (
        f"我理解你现在想围绕「{goal}」推进一个{goal_label}{time_hint}。"
        "我接下来会先帮你补齐画像，再给你一版可直接开始的学习路径和任务建议。"
    )


async def _generate_onboarding_preview(payload: OnboardingRequest) -> tuple[str, str, bool]:
    fallback = _build_onboarding_preview_fallback(payload)
    goal = (payload.learning_goal or "").strip()
    if not goal:
        return fallback, "fallback", True

    summary_bits = [
        f"目标类型：{_goal_type_label(payload.learning_goal_type)}",
        f"目标：{goal}",
    ]
    if payload.learning_style:
        summary_bits.append(f"偏好风格：{payload.learning_style}")
    if payload.study_time_minutes is not None:
        summary_bits.append(f"每日时间：{payload.study_time_minutes} 分钟")
    if payload.knowledge_level:
        summary_bits.append(f"当前基础：{payload.knowledge_level}")

    llm = await get_configured_llm_service_for_tier(
        AgentRole.GENERATION,
        ModelTier.FAST,
        task_type=TaskType.QUICK_QUERY,
        reasoning_mode="fast",
    )
    messages = [
        {
            "role": "system",
            "content": (
                "你是 Sparkle onboarding 助手。"
                "用户刚输入第一个学习目标，请只用中文输出 2 句。"
                "第 1 句复述你理解到的目标与节奏，第 2 句说明你接下来会如何帮助。"
                "总字数控制在 70 字内，不要列表，不要寒暄，不要 markdown。"
            ),
        },
        {
            "role": "user",
            "content": "\n".join(summary_bits),
        },
    ]

    try:
        preview = await asyncio.wait_for(llm.chat(messages, temperature=0.2), timeout=8.0)
        preview = " ".join((preview or "").split())
        if not preview:
            return fallback, "fallback", True
        return preview, "llm_fast", False
    except Exception:
        return fallback, "fallback", True


def _editability_meta(
    *,
    source: str,
    confidence: float,
    risk_level: str,
    field_type: str,
    source_type: str = None,
) -> dict[str, Any]:
    """
    构建偏好项的可编辑性元数据

    Args:
        source: 数据来源 ("user", "system", "mixed")
        confidence: 置信度 (0-1)
        risk_level: 风险等级 ("low", "medium", "high")
        field_type: 字段类型 ("preference", "behavior", "analysis")
        source_type: 来源类型，用于前端显示
            - "explicit": 用户直接设置的偏好
            - "inferred": 系统推断的偏好
            - "collaborative": 协作校准的内容

    Returns:
        包含可编辑性元数据的字典
    """
    score = (
        0.4 * _source_score(source) + 0.3 * confidence - 0.2 * _risk_score(risk_level) + 0.1 * _field_score(field_type)
    )
    if score > 0.6:
        level = "editable"
    elif score >= 0.3:
        level = "warn"
    else:
        level = "readonly"

    reason_map = {
        "editable": "来源可信且风险较低，可直接修改",
        "warn": "建议提交修正，系统评估后采纳",
        "readonly": "基于系统分析，暂不支持修改",
    }

    # 自动推断 source_type（如果未显式指定）
    if source_type is None:
        if source == "user":
            source_type = "explicit"
        elif source == "system":
            source_type = "inferred"
        else:  # mixed
            source_type = "collaborative"

    # source_type 的用户友好标签
    source_type_labels = {
        "explicit": "用户设置",
        "inferred": "系统推断",
        "collaborative": "协作校准",
    }

    return {
        "level": level,
        "score": round(score, 2),
        "reason": reason_map[level],
        "source": source,
        "source_type": source_type,
        "source_type_label": source_type_labels.get(source_type, source_type),
        "risk_level": risk_level,
        "confidence": confidence,
        "field_type": field_type,
    }


class OnboardingRequest(BaseModel):
    learning_goal_type: str | None = None
    learning_goal: str | None = None
    learning_style: str | None = None
    study_time_minutes: int | None = Field(default=None, ge=5, le=360)
    knowledge_level: str | None = None
    response_depth: float | None = Field(default=None, ge=0.0, le=1.0)
    curiosity_preference: float | None = Field(default=None, ge=0.0, le=1.0)


class OnboardingPreviewResponse(BaseModel):
    message: str
    source: str = "fallback"
    fallback_used: bool = True


class CorrectionRequest(BaseModel):
    target_type: str
    target_id: str | None = None
    field_name: str | None = None
    suggested_value: str | None = None
    reason: str | None = None


class PreferenceUpdateRequest(BaseModel):
    pref_key: str
    value: Any


class PreferenceRollbackRequest(BaseModel):
    pref_key: str


class GoalUpdateRequest(BaseModel):
    goal_id: UUID
    title: str | None = None
    status: str | None = None
    target_date: date | None = None


class InferredOverrideRequest(BaseModel):
    key: str
    value: Any
    reason: str | None = None


class ResetOverrideRequest(BaseModel):
    key: str


class InsightControlRequest(BaseModel):
    target_id: str
    action: str
    value: Any | None = None
    reason: str | None = None


def _coerce_preference_value(pref_key: str, value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, (int, float)):
        return {"value": value}
    if isinstance(value, str):
        stripped = value.strip()
        if pref_key == "study_time_preference" and stripped.isdigit():
            return {"minutes": int(stripped)}
        if stripped.replace(".", "", 1).isdigit():
            if "." in stripped:
                return {"value": float(stripped)}
            return {"value": int(stripped)}
        return {"value": stripped}
    return {"value": str(value)}


def _display_preference_value(pref_key: str, value: Any) -> Any:
    if pref_key == "study_time_preference" and isinstance(value, dict) and "minutes" in value:
        return value.get("minutes")
    if isinstance(value, dict) and set(value.keys()) == {"value"}:
        return value.get("value")
    return value


def _merge_preferences(explicit: dict[str, Any], inferred: dict[str, Any]) -> dict[str, Any]:
    merged = dict(inferred or {})
    merged.update(explicit or {})
    return merged


def _merge_scope_overrides(merged_preferences: dict[str, Any], target_id: str, scope: str | None) -> dict[str, Any]:
    current = dict(merged_preferences.get("insight_scope_overrides") or {})
    if scope:
        current[target_id] = {"scope": scope}
    else:
        current.pop(target_id, None)
    return current


def _normalize_inferred_display_value(value: Any) -> Any:
    if isinstance(value, dict) and set(value.keys()) == {"value"}:
        return value.get("value")
    return value


_INFERRED_KEY_LABELS = {
    "achievement_motivation_response": "成就激励响应",
    "achievement_pace_style": "成就节奏风格",
    "achievement_peak_hours": "成就高峰时段",
    "achievement_reward_sensitivity": "成就奖励敏感度",
    "avg_question_complexity": "问题复杂度",
    "chat_active_hours": "聊天活跃时段",
    "community_engagement_level": "社区参与度",
    "content_contribution_rate": "社区贡献倾向",
    "curiosity_preference": "探索偏好",
    "curiosity_push_receptivity": "探索推送接受度",
    "depth_preference": "讲解深度偏好",
    "depth_preference_signal": "深度讲解倾向",
    "error_correction_rate": "错题纠正率",
    "error_density_score": "错题密度",
    "peak_focus_hours": "高专注时段",
    "preferred_focus_duration": "偏好专注时长",
    "push_receptivity": "推送接受度",
    "recurring_error_tags": "高频错误标签",
    "response_satisfaction_rate": "回答满意度",
    "social_learning_preference": "社交学习倾向",
}

_INFERRED_SOURCE_LABELS = {
    "achievement_signals": "成就行为",
    "behavior": "行为推断",
    "chat_behavior": "聊天行为",
    "community": "社区行为",
    "error_book": "错题记录",
    "focus_sessions": "专注记录",
    "push_feedback": "推送反馈",
    "streak_stats": "连续记录",
    "task_feedback": "任务反馈",
    "learning_assets": "学习资产",
    "galaxy_feedback": "知识星图反馈",
}

_VALUE_LABELS = {
    "moderate": "中等",
    "high": "高",
    "low": "低",
    "balanced": "均衡",
    "mastery_affirmation": "掌握提升型鼓励",
    "milestone_celebration": "里程碑庆祝型鼓励",
    "mixed": "混合",
    "progress_praise": "进度肯定型鼓励",
    "detailed": "详细",
    "concise": "简洁",
    "sprint": "冲刺型",
    "steady": "稳步型",
    "structured": "结构化",
    "intermediate": "中等基础",
}

_POLICY_PROFILE_LABELS = {
    "llm": "AI 回复",
    "push": "提醒推送",
    "task": "任务规划",
}

_POLICY_SIGNAL_LABELS = {
    "llm.feedback.emphasize_progress": "强调进度反馈",
    "llm.explanation.add_foundation": "补齐前置概念",
    "push.timing.earlier_reminder": "提醒时间前移",
    "push.timing.avoid_inactive_hours": "避开低响应时段",
    "task.time_estimate.add_buffer_30pct": "任务时长增加缓冲",
    "task.difficulty.start_easy": "先从低门槛开始",
    "task.content.scaffold_prerequisites": "优先补前置知识",
    "task.review.raise_priority_for_recurring_errors": "高频错题优先复盘",
    "plan.milestone.add_checkpoint": "里程碑增加检查点",
}

_POLICY_EFFECT_LABELS = {
    "llm.feedback.emphasize_progress": "AI 在反馈时会先强调你已经取得的进展，减少挫败感和过度纠错。",
    "llm.explanation.add_foundation": "AI 在解释复杂问题前会先补上必要的基础概念，避免直接跳步。",
    "push.timing.earlier_reminder": "提醒会更早出现，把关键任务尽量推到你更容易启动的时段。",
    "push.timing.avoid_inactive_hours": "系统会尽量避开你常常忽略提醒或不适合被打断的时间段。",
    "task.time_estimate.add_buffer_30pct": "任务时长会自动预留额外缓冲，减少计划过满带来的失真。",
    "task.difficulty.start_easy": "任务会先给一个更容易启动的版本，帮助你快速进入状态。",
    "task.content.scaffold_prerequisites": "任务与讲解会优先补齐前置知识，再推进到更高难度内容。",
    "task.review.raise_priority_for_recurring_errors": "系统会把高频错题与复盘任务排得更靠前，优先解决反复出现的问题。",
    "plan.milestone.add_checkpoint": "计划里会加入更多检查点，帮助你更早发现偏航并及时回正。",
}

_SOURCE_PATTERN_LABELS = {
    "push_feedback": "推送反馈",
    "error_book": "错题记录",
    "behavior_pattern": "行为模式",
}


def _present_value_text(value: Any) -> str:
    if isinstance(value, str):
        return _VALUE_LABELS.get(value, value)
    if isinstance(value, float):
        return f"{value:.2f}"
    if isinstance(value, list):
        return "、".join(str(item) for item in value[:5]) if value else "暂无"
    if isinstance(value, dict):
        return "；".join(f"{key}: {raw}" for key, raw in list(value.items())[:5]) if value else "暂无"
    return str(value)


def _localize_inferred_explanation(key: str, value: Any, fallback: str) -> str:
    label = _INFERRED_KEY_LABELS.get(key, key)
    if key == "achievement_peak_hours" and isinstance(value, list):
        return (
            f"系统观察到你最近更常在 { _present_value_text(value) } 解锁成就，这些时段会被视为更容易形成正反馈的窗口。"
        )
    if key == "achievement_motivation_response":
        return f"最近成就行为显示，你更容易被「{ _present_value_text(value) }」这类反馈方式带动。"
    if key == "achievement_pace_style":
        return f"结合最近的成就节奏，系统判断你当前更接近 { _present_value_text(value) } 的推进方式。"
    if key == "achievement_reward_sensitivity":
        return f"根据最近成就的稀有度与分享行为，系统认为你对奖励反馈的敏感度大约是 { _present_value_text(value) }。"
    if key == "peak_focus_hours" and isinstance(value, list):
        return f"系统根据最近专注记录判断，你更容易进入状态的时间集中在 { _present_value_text(value) }。"
    if key == "chat_active_hours" and isinstance(value, list):
        return f"系统观察到你最近更常在 { _present_value_text(value) } 发起对话，这些时段会被视为更自然的互动窗口。"
    if key == "error_density_score":
        return f"最近错题密度约为 { _present_value_text(value) }，偏高时系统会放慢节奏并提高复盘优先级。"
    if key == "error_correction_rate":
        return f"最近错题纠正率约为 { _present_value_text(value) }，这会影响系统对你复盘力度的判断。"
    if key == "recurring_error_tags" and isinstance(value, list):
        return f"系统最近识别到这些高频错误模式：{ _present_value_text(value) }。"
    if key == "social_learning_preference":
        return f"从最近互动看，你对社交式学习的偏好约为 { _present_value_text(value) }。"
    if key == "depth_preference_signal":
        return "系统发现你常常围绕同一主题连续追问，因此会更倾向于提供更深入、分层的解释。"
    if key == "response_satisfaction_rate":
        return f"结合最近聊天反馈，系统估计你当前的回答满意度约为 { _present_value_text(value) }。"
    if fallback and any("\u4e00" <= ch <= "\u9fff" for ch in fallback):
        return fallback
    return f"系统根据最近行为推断出「{label}」目前约为 { _present_value_text(value) }。"


def _present_source_pattern_label(value: str) -> str:
    return present_pattern_name(_SOURCE_PATTERN_LABELS.get(value, value))


def _build_inferred_entries(
    *,
    explicit: dict[str, Any],
    inferred: dict[str, Any],
    inferred_updated_at: Any,
    backups: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    baseline_inferred: dict[str, Any] = {}
    behavioral_keys = {
        "avg_question_complexity",
        "community_engagement_level",
        "social_learning_preference",
    }
    if not ((set(inferred.keys()) | set(backups.keys())) & behavioral_keys):
        baseline_inferred = {
            "avg_question_complexity": 0.5,
            "community_engagement_level": "moderate",
            "social_learning_preference": 0.5,
        }

    items: list[dict[str, Any]] = []
    seen: set[str] = set()
    all_keys = set(inferred.keys()) | set(backups.keys()) | set(baseline_inferred.keys())
    for key in sorted(all_keys):
        meta = INFERRED_META.get(key)
        source = meta.source if meta is not None else "behavior"
        adjustable = meta.adjustable if meta is not None else False
        overridden = key in explicit and key in backups
        stored_value = inferred.get(key, baseline_inferred.get(key))
        backup_value = backups.get(key, {}).get("value")
        effective_value = explicit.get(key) if overridden else stored_value
        display_value = _normalize_inferred_display_value(effective_value)
        explanation_value = backup_value if overridden and backup_value is not None else stored_value
        explanation = build_inferred_explanation(
            key,
            explanation_value,
            related_values={key: explanation_value},
        )
        updated_at = backups.get(key, {}).get("updated_at") or (
            inferred_updated_at.isoformat() if inferred_updated_at is not None else None
        )
        items.append(
            {
                "key": key,
                "label": _INFERRED_KEY_LABELS.get(key, key),
                "value": display_value,
                "source": source,
                "source_label": _INFERRED_SOURCE_LABELS.get(source, source),
                "explanation": _localize_inferred_explanation(key, display_value, explanation),
                "updated_at": updated_at,
                "adjustable": adjustable,
                "overridden": overridden,
                "related_fields": list(meta.related_fields) if meta is not None else [],
            }
        )
        seen.add(key)
    return items


def _serialize_policy_explanations(profile_name: str, items: list[Any]) -> list[dict[str, Any]]:
    serialized: list[dict[str, Any]] = []
    for item in items:
        serialized.append(
            {
                "profile": profile_name,
                "profile_label": _POLICY_PROFILE_LABELS.get(profile_name, profile_name),
                "signal": item.signal,
                "signal_label": _POLICY_SIGNAL_LABELS.get(item.signal, item.signal),
                "effect": _POLICY_EFFECT_LABELS.get(item.signal, item.effect),
                "source_pattern": item.source_pattern,
                "source_pattern_label": _present_source_pattern_label(item.source_pattern),
            }
        )
    return serialized


def _build_preference_entries(
    explicit_prefs: dict[str, Any],
    history: list[Any],
) -> list[dict[str, Any]]:
    latest_by_key: dict[str, Any] = {}
    history_count: dict[str, int] = {}
    for item in history:
        history_count[item.pref_key] = history_count.get(item.pref_key, 0) + 1
        if item.pref_key not in latest_by_key:
            latest_by_key[item.pref_key] = item

    entries: list[dict[str, Any]] = []
    for pref_key in sorted(explicit_prefs.keys()):
        history_item = latest_by_key.get(pref_key)
        entries.append(
            {
                "id": str(history_item.id) if history_item is not None else pref_key,
                "key": pref_key,
                "value": _display_preference_value(pref_key, explicit_prefs.get(pref_key)),
                "confidence": history_item.confidence if history_item is not None else None,
                "version": history_item.version if history_item is not None else 1,
                "can_rollback": history_count.get(pref_key, 0) > 1,
                "updated_at": history_item.updated_at if history_item is not None else None,
                "metadata": _editability_meta(
                    source="user",
                    confidence=float((history_item.confidence if history_item is not None else 0.9) or 0.9),
                    risk_level="low",
                    field_type="preference",
                ),
            }
        )
    return entries


@router.get("/transparent")
async def get_profile_transparent(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    memory_service = MemoryService(db)
    profile_write_service = ProfileWriteService(db, cache_service.redis)
    cognitive_service = CognitiveService(db)
    profile_context_service = ProfileContextService(db, cache_service.redis)

    prefs_center = await profile_write_service.pref_service.get_preferences(current_user.id)
    preferences = await memory_service.list_preference_history(current_user.id)
    goals = await memory_service.list_active_goals(current_user.id)
    profile_context = await profile_context_service.get_profile_context(current_user.id)
    patterns = profile_context.cognitive_summary.active_patterns
    fragments = await cognitive_service.get_fragments(current_user.id, limit=5)

    layer_1 = {
        "preferences": _build_preference_entries(prefs_center.explicit or {}, preferences),
        "goals": [
            {
                "id": str(item.id),
                "title": item.title,
                "status": item.status,
                "target_date": item.target_date,
                "updated_at": item.updated_at,
                "metadata": _editability_meta(
                    source="user",
                    confidence=0.9,
                    risk_level="low",
                    field_type="preference",
                ),
            }
            for item in goals
        ],
    }

    layer_2 = {
        "persona": {
            "tags": [
                {
                    "value": pattern.pattern_name,
                    "metadata": _editability_meta(
                        source="mixed",
                        confidence=float(pattern.confidence or 0.6),
                        risk_level="medium",
                        field_type="behavior",
                    ),
                }
                for pattern in patterns
            ],
            "capabilities": [
                {
                    "key": k,
                    "value": v,
                    "metadata": _editability_meta(
                        source="mixed",
                        confidence=0.6,
                        risk_level="medium",
                        field_type="analysis",
                    ),
                }
                for k, v in {
                    "overall_mastery": profile_context.knowledge_summary.overall_mastery,
                    "active_learning_subjects": profile_context.knowledge_summary.active_learning_subjects,
                    "weak_spot_count": len(profile_context.knowledge_summary.weak_spots),
                }.items()
            ],
            "meta": {
                "preference_version": profile_context.preference_version,
            },
        },
        "editable": False,
    }

    layer_3 = {
        "patterns": [
            {
                "id": item.pattern_name,
                "name": item.pattern_name,
                "type": item.pattern_type,
                "confidence": item.confidence,
                "description": None,
                "metadata": {
                    **_editability_meta(
                        source="system",
                        confidence=float(item.confidence or 0.0),
                        risk_level="high",
                        field_type="analysis",
                    ),
                    "policy_signals": item.policy_signals,
                },
            }
            for item in patterns
        ],
        "fragments": [
            {
                "id": str(item.id),
                "content": _snippet(item.content),
                "source_type": item.source_type,
                "created_at": item.created_at,
                "metadata": _editability_meta(
                    source="system",
                    confidence=0.7,
                    risk_level="high",
                    field_type="analysis",
                ),
            }
            for item in fragments
        ],
    }

    return {
        "layer_1": layer_1,
        "layer_2": layer_2,
        "layer_3": layer_3,
    }


@router.get("/context")
async def get_profile_context(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    profile_context_service = ProfileContextService(db, cache_service.redis)
    pref_service = PreferenceService(db, cache_service.redis)
    profile_write_service = ProfileWriteService(db, cache_service.redis)

    context = await profile_context_service.get_profile_context(current_user.id)
    prefs = await pref_service.get_preferences(current_user.id)
    merged_preferences = _merge_preferences(prefs.explicit or {}, prefs.inferred or {})
    inferred_backups = await profile_write_service.list_inferred_backups(current_user.id)

    payload = context.to_prompt_context()
    payload["preferences"] = merged_preferences
    payload["preference_version"] = prefs.version or payload.get("preference_version", 0)
    user_insight_state = getattr(context, "user_insight_state", None)
    if user_insight_state is not None:
        payload["user_insight_transparency"] = UserInsightTransparencyService().build_payload(
            state=user_insight_state,
            merged_preferences=merged_preferences,
            inferred_backups=inferred_backups,
        )
    partnership_result = await db.execute(
        select(AccountabilityPartnership)
        .where(
            and_(
                AccountabilityPartnership.slot_type == AccountabilitySlotType.CORE,
                AccountabilityPartnership.status == AccountabilityStatus.ACTIVE,
                or_(
                    AccountabilityPartnership.initiator_id == current_user.id,
                    AccountabilityPartnership.partner_id == current_user.id,
                ),
            )
        )
        .order_by(AccountabilityPartnership.updated_at.desc())
    )
    active_partnership = partnership_result.scalars().first()
    payload["accountability_summary"] = (
        await _build_relationship_summary(db, active_partnership, current_user)
        if active_partnership is not None
        else {
            "slot_type": AccountabilitySlotType.CORE.value,
            "status": "inactive",
            "has_core_partner": False,
        }
    )
    if active_partnership is not None:
        payload["accountability_summary"]["has_core_partner"] = True
    return payload


@router.get("/insights")
async def get_profile_insights(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    profile_context_service = ProfileContextService(db, cache_service.redis)
    pref_service = PreferenceService(db, cache_service.redis)
    profile_write_service = ProfileWriteService(db, cache_service.redis)

    context = await profile_context_service.get_profile_context(current_user.id)
    prefs = await pref_service.get_preferences(current_user.id)
    merged_preferences = _merge_preferences(prefs.explicit or {}, prefs.inferred or {})
    inferred_backups = await profile_write_service.list_inferred_backups(current_user.id)

    state = context.user_insight_state
    if state is None:
        return {
            "claims": [],
            "predictions": [],
            "recent_changes": [],
            "unknowns": [],
            "calibration": {},
            "current_profile": {},
        }

    return UserInsightTransparencyService().build_payload(
        state=state,
        merged_preferences=merged_preferences,
        inferred_backups=inferred_backups,
    )


@router.get("/inferred-preferences")
async def get_inferred_preferences(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    profile_write_service = ProfileWriteService(db, cache_service.redis)
    prefs = await profile_write_service.pref_service.get_preferences(current_user.id)
    backups = await profile_write_service.list_inferred_backups(current_user.id)
    return _build_inferred_entries(
        explicit=prefs.explicit or {},
        inferred=prefs.inferred or {},
        inferred_updated_at=prefs.last_inferred_update,
        backups=backups,
    )


@router.get("/active-policies")
async def get_active_policies(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    engine = get_personalization_engine(db, cache_service.redis)
    llm_profile = await engine.get_llm_profile(current_user.id)
    push_profile = await engine.get_push_policy_profile(current_user.id)
    task_profile = await engine.get_task_plan_profile(current_user.id)
    return (
        _serialize_policy_explanations("llm", llm_profile.applied_policies)
        + _serialize_policy_explanations("push", push_profile.applied_policies)
        + _serialize_policy_explanations("task", task_profile.applied_policies)
    )


@router.get("/system-updates")
async def list_system_updates(
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    service = SystemUpdateService(cache_service.redis)
    items = await service.list_updates(current_user.id, limit=limit, offset=offset)
    return {"items": items}


@router.post("/chat-opening", response_model=ChatOpeningResponse)
async def create_chat_opening(
    payload: ChatOpeningRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatOpeningResponse:
    service = SystemUpdateService(cache_service.redis)
    updates = await service.drain(current_user.id, limit=20)
    relevant_updates = [update for update in updates if _is_chat_opening_update(update)]
    deferred_updates = [update for update in updates if update not in relevant_updates]

    if not relevant_updates:
        for update in reversed(deferred_updates):
            await service.enqueue(current_user.id, update)
        return ChatOpeningResponse(created=False, conversation_id=payload.conversation_id)

    prompt_context = SessionStateMixin._build_system_update_prompt_context(relevant_updates)
    content = _compose_chat_opening_content(prompt_context)
    if not content:
        for update in reversed(updates):
            await service.enqueue(current_user.id, update)
        return ChatOpeningResponse(created=False, conversation_id=payload.conversation_id)

    intervention_id = _extract_intervention_id(relevant_updates)
    widgets = _build_chat_opening_widgets(
        proactive_opening_message=prompt_context.get("proactive_opening_message", ""),
        post_adaptation_question=prompt_context.get("post_adaptation_question", ""),
        intervention_id=intervention_id,
    )

    session_meta = await db.get(ChatSessionModel, payload.conversation_id)
    now = datetime.utcnow()
    if session_meta is None:
        session_meta = ChatSessionModel(
            id=payload.conversation_id,
            user_id=current_user.id,
            is_active=True,
            last_message_at=now,
        )
        db.add(session_meta)
    elif session_meta.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found")
    else:
        session_meta.is_active = True
        session_meta.last_message_at = now

    message = ChatMessage(
        user_id=current_user.id,
        session_id=payload.conversation_id,
        role=MessageRole.ASSISTANT,
        content=content,
        actions=widgets or None,
    )
    db.add(message)

    await _mark_chat_opening_intervention_seen(
        db=db,
        user_id=current_user.id,
        intervention_id=intervention_id,
    )
    await db.commit()
    await db.refresh(message)

    for update in reversed(deferred_updates):
        await service.enqueue(current_user.id, update)

    return ChatOpeningResponse(
        created=True,
        conversation_id=payload.conversation_id,
        message_id=message.id,
        content=content,
    )


@router.post("/onboarding")
async def submit_onboarding(
    payload: OnboardingRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    memory_service = MemoryService(db)
    profile_write_service = ProfileWriteService(db, cache_service.redis)

    evidence_refs = [{"type": "user_state", "id": "onboarding", "schema_version": "onboarding.v1"}]

    updated: dict[str, Any] = {}
    preference_updates: dict[str, Any] = {}

    if payload.learning_style:
        result = await profile_write_service.set_explicit_preference(
            user_id=current_user.id,
            pref_key="learning_style",
            pref_value={"value": payload.learning_style},
            evidence_refs=evidence_refs,
            source_type="user_state",
            source="onboarding",
        )
        if result.preference_version:
            updated["learning_style"] = payload.learning_style

    if payload.knowledge_level:
        result = await profile_write_service.set_explicit_preference(
            user_id=current_user.id,
            pref_key="knowledge_level",
            pref_value={"value": payload.knowledge_level},
            evidence_refs=evidence_refs,
            source_type="user_state",
            source="onboarding",
        )
        if result.preference_version:
            updated["knowledge_level"] = payload.knowledge_level

    if payload.study_time_minutes is not None:
        result = await profile_write_service.set_explicit_preference(
            user_id=current_user.id,
            pref_key="study_time_preference",
            pref_value={"minutes": payload.study_time_minutes},
            evidence_refs=evidence_refs,
            source_type="user_state",
            source="onboarding",
        )
        if result.preference_version:
            updated["study_time_preference"] = payload.study_time_minutes

    if payload.response_depth is not None:
        style = _response_style_from_depth(payload.response_depth)
        preference_updates["depth_preference"] = {"value": payload.response_depth}
        preference_updates["response_style"] = {"value": style}
        updated["depth_preference"] = payload.response_depth
        updated["response_style"] = style

    if payload.curiosity_preference is not None:
        preference_updates["curiosity_preference"] = {"value": payload.curiosity_preference}
        updated["curiosity_preference"] = payload.curiosity_preference

    if preference_updates:
        await profile_write_service.set_explicit_preferences(
            user_id=current_user.id,
            updates=preference_updates,
            evidence_refs_by_key={key: evidence_refs for key in preference_updates},
            source_type="user_state",
            source="onboarding",
        )

    if payload.learning_goal:
        metadata: dict[str, Any] | None = None
        if payload.learning_goal_type:
            metadata = {"goal_type": payload.learning_goal_type}
        record = await memory_service.create_goal(
            current_user.id,
            payload.learning_goal,
            metadata=metadata,
            evidence_refs=evidence_refs,
            source_type="user_state",
        )
        if record:
            updated["learning_goal"] = payload.learning_goal

    # Bootstrap galaxy scaffold nodes from goal
    try:
        from app.services.galaxy_bootstrap_service import GalaxyBootstrapService

        bootstrap_service = GalaxyBootstrapService(db)
        await bootstrap_service.seed_from_goal(
            user_id=current_user.id,
            learning_goal=payload.learning_goal,
            goal_type=payload.learning_goal_type,
        )
        await db.commit()
    except Exception as _exc:
        import logging

        logging.getLogger(__name__).warning("Galaxy bootstrap failed during onboarding: %s", _exc)

    # Generate personalized first-session opener for the chat
    first_message = await _generate_first_session_message(
        learning_goal=payload.learning_goal,
        learning_goal_type=payload.learning_goal_type,
        knowledge_level=payload.knowledge_level,
        study_time_minutes=payload.study_time_minutes,
    )

    return {"status": "ok", "updated": updated, "first_message": first_message}


@router.post("/onboarding/preview", response_model=OnboardingPreviewResponse)
async def preview_onboarding(
    payload: OnboardingRequest,
    current_user: User = Depends(get_current_user),
) -> OnboardingPreviewResponse:
    _ = current_user
    message, source, fallback_used = await _generate_onboarding_preview(payload)
    return OnboardingPreviewResponse(
        message=message,
        source=source,
        fallback_used=fallback_used,
    )


@router.put("/preferences")
async def update_preference(
    payload: PreferenceUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    if not payload.pref_key:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="pref_key required")

    profile_write_service = ProfileWriteService(db, cache_service.redis)
    evidence_refs = [{"type": "user_state", "id": "manual_edit", "schema_version": "manual_edit.v1"}]
    value_payload = _coerce_preference_value(payload.pref_key, payload.value)
    result = await profile_write_service.set_explicit_preference(
        user_id=current_user.id,
        pref_key=payload.pref_key,
        pref_value=value_payload,
        evidence_refs=evidence_refs,
        source_type="user_state",
        source="manual_edit",
    )
    return {
        "status": "ok",
        "version": result.preference_version,
        "history_version": result.history_version,
    }


@router.post("/override-inferred")
async def override_inferred_preference(
    payload: InferredOverrideRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    if not payload.key:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="key required")
    meta = INFERRED_META.get(payload.key)
    if meta is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="unknown inferred key")
    if not meta.adjustable:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="key is not adjustable")

    profile_write_service = ProfileWriteService(db, cache_service.redis)
    evidence_refs = [{"type": "user_state", "id": "user_override", "schema_version": "user_override.v1"}]
    value_payload = _coerce_preference_value(payload.key, payload.value)
    result = await profile_write_service.override_inferred_preference(
        user_id=current_user.id,
        pref_key=payload.key,
        pref_value=value_payload,
        evidence_refs=evidence_refs,
        source="user_override",
    )
    return {
        "status": "ok",
        "version": result.preference_version,
        "message": payload.reason or "override applied",
    }


@router.post("/reset-override")
async def reset_override_preference(
    payload: ResetOverrideRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    if not payload.key:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="key required")
    profile_write_service = ProfileWriteService(db, cache_service.redis)
    result = await profile_write_service.reset_override_preference(
        user_id=current_user.id,
        pref_key=payload.key,
    )
    return {
        "status": "ok",
        "version": result.preference_version,
    }


@router.post("/insights/control")
async def control_profile_insight(
    payload: InsightControlRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    target_id = _strip(payload.target_id)
    action = _strip(payload.action).lower()
    if not target_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="target_id required")
    service = ProfileInsightControlService(db, cache_service.redis)
    try:
        result = await service.apply_control(
            user_id=current_user.id,
            target_id=target_id,
            action=action,
            value=payload.value,
            reason=payload.reason,
            source="insight_control",
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return {
        "status": result.status,
        "target_id": result.target_id,
        "action": result.action,
        "preference_version": result.preference_version,
    }


@router.post("/preferences/rollback")
async def rollback_preference(
    payload: PreferenceRollbackRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    if not payload.pref_key:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="pref_key required")

    memory_service = MemoryService(db)
    history = await memory_service.list_preference_history(current_user.id)
    candidates = [item for item in history if item.pref_key == payload.pref_key]
    if len(candidates) < 2:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="no previous version")

    current = candidates[0]
    previous = candidates[1]
    evidence_refs = [{"type": "user_state", "id": "rollback", "schema_version": "rollback.v1"}]
    profile_write_service = ProfileWriteService(db, cache_service.redis)
    result = await profile_write_service.set_explicit_preference(
        user_id=current_user.id,
        pref_key=payload.pref_key,
        pref_value=previous.pref_value,
        evidence_refs=evidence_refs,
        source_type="user_state",
        source="rollback",
    )
    restored = await profile_write_service.restore_inferred_backup(
        user_id=current_user.id,
        pref_key=payload.pref_key,
        source="rollback_restore",
        delete_backup=True,
    )
    return {
        "status": "ok",
        "from_version": current.version,
        "to_version": previous.version,
        "new_version": result.history_version,
        "preference_version": (restored.preference_version if restored is not None else result.preference_version),
    }


@router.put("/goals")
async def update_goal(
    payload: GoalUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    memory_service = MemoryService(db)
    updates: dict[str, Any] = {}
    if payload.title is not None:
        updates["title"] = payload.title
    if payload.status is not None:
        updates["status"] = payload.status
    if payload.target_date is not None:
        updates["target_date"] = payload.target_date

    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="no updates")

    record = await memory_service.update_goal(current_user.id, payload.goal_id, **updates)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="goal not found")

    await SystemUpdateService(cache_service.redis).enqueue(
        current_user.id,
        build_system_update(
            update_type="memory_goal_updated",
            category="goal",
            title=f"更新了目标：{_snippet(record.title)}",
            description="学习目标已更新",
            priority="medium",
            metadata={
                "goal_id": str(record.id),
                "status": record.status,
            },
        ),
    )
    return {"status": "ok"}


@router.post("/corrections")
async def submit_correction(
    payload: CorrectionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    from app.models.memory import MemoryCorrection

    if not payload.target_type:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="target_type required")

    correction = MemoryCorrection(
        user_id=current_user.id,
        memory_type=payload.target_type,
        memory_id=current_user.id,
        action="suggest_update",
        reason=json.dumps(
            {
                "target_id": payload.target_id,
                "field_name": payload.field_name,
                "suggested_value": payload.suggested_value,
                "reason": payload.reason,
            },
            ensure_ascii=True,
        ),
    )
    db.add(correction)
    await db.commit()
    await SystemUpdateService(cache_service.redis).enqueue(
        current_user.id,
        build_system_update(
            update_type="correction_received",
            category="cognitive",
            title="收到你的修正建议",
            description="系统将评估并逐步调整画像",
            priority="medium",
            metadata={
                "target_type": payload.target_type,
                "field_name": payload.field_name,
            },
        ),
    )
    return {"status": "ok"}
