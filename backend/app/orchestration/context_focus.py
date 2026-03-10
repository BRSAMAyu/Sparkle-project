from __future__ import annotations

from dataclasses import dataclass, field
from math import sqrt
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings

EMOTIONAL_SIGNAL_KEYWORDS = {
    "崩溃",
    "焦虑",
    "压力好大",
    "压力很大",
    "学不进去",
    "撑不住",
    "烦死了",
    "好累",
    "很难受",
    "好痛苦",
    "不想学",
    "受不了",
    "沮丧",
    "绝望",
    "情绪",
    "低落",
}

TASK_ACTION_KEYWORDS = {
    "任务",
    "待办",
    "先做什么",
    "今天做什么",
    "下一步",
    "安排任务",
    "添加任务",
    "完成任务",
}

PLAN_ACTION_KEYWORDS = {
    "计划",
    "复习计划",
    "学习计划",
    "调整计划",
    "时间安排",
    "排期",
    "里程碑",
    "冲刺",
}

KNOWLEDGE_ACTION_KEYWORDS = {
    "讲一下",
    "解释",
    "原理",
    "概念",
    "什么意思",
    "翻译",
    "为什么",
    "矩阵",
    "知识点",
}


def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0
    dot = sum(a * b for a, b in zip(vec1, vec2, strict=False))
    norm1 = sqrt(sum(a * a for a in vec1))
    norm2 = sqrt(sum(b * b for b in vec2))
    if norm1 <= 0.0 or norm2 <= 0.0:
        return 0.0
    return max(0.0, min(1.0, dot / (norm1 * norm2)))


def normalize_route_intent(route_intent: str | None) -> str:
    value = str(route_intent or "").strip().lower()
    mapping = {
        "plan": "plan",
        "planning": "plan",
        "sprint_plan": "sprint_plan",
        "task": "task",
        "knowledge": "knowledge",
        "translation": "translation",
        "error_diagnosis": "error_diagnosis",
        "learn": "learn",
        "review": "review",
        "cognitive_prism": "cognitive_prism",
        "chat": "chat",
        "general": "chat",
    }
    return mapping.get(value, value or "chat")


def route_intent_to_budget_intent(route_intent: str | None) -> str:
    normalized = normalize_route_intent(route_intent)
    if normalized in {"plan", "sprint_plan"}:
        return "planning"
    if normalized in {"knowledge", "translation", "error_diagnosis", "learn", "review"}:
        return "learning"
    return "chat"


def infer_route_intent_from_chat_mode(chat_mode: str | None) -> str | None:
    value = str(chat_mode or "").strip().lower()
    if value == "study_plan":
        return "plan"
    if value == "error_diagnosis":
        return "error_diagnosis"
    if value == "deep_analysis":
        return "knowledge"
    return None


@dataclass(frozen=True)
class FocusProfile:
    focus_mode: str
    section_weights: dict[str, str]
    section_caps: dict[str, int]
    memory_budget_weights: dict[str, float]
    semantic_gating_enabled: bool = True


FOCUS_PROFILES: dict[str, FocusProfile] = {
    "plan_focus": FocusProfile(
        focus_mode="plan_focus",
        section_weights={
            "user_context": "medium",
            "plan_context": "full",
            "cognitive_prism": "compact",
            "preferences": "medium",
            "goals": "high",
            "episodic": "low",
            "task_summary": "medium",
        },
        section_caps={"goals": 4, "episodic": 2, "next_actions": 3, "active_plans": 2},
        memory_budget_weights={"preferences": 0.9, "goals": 1.5, "episodic": 0.6},
    ),
    "task_focus": FocusProfile(
        focus_mode="task_focus",
        section_weights={
            "user_context": "high",
            "plan_context": "medium",
            "cognitive_prism": "off",
            "preferences": "medium",
            "goals": "medium",
            "episodic": "low",
            "task_summary": "high",
        },
        section_caps={"goals": 3, "episodic": 1, "next_actions": 4, "active_plans": 2},
        memory_budget_weights={"preferences": 1.0, "goals": 1.2, "episodic": 0.6},
    ),
    "knowledge_focus": FocusProfile(
        focus_mode="knowledge_focus",
        section_weights={
            "user_context": "medium",
            "plan_context": "low",
            "cognitive_prism": "off",
            "preferences": "medium",
            "goals": "low",
            "episodic": "low",
            "task_summary": "off",
        },
        section_caps={"goals": 2, "episodic": 1, "next_actions": 1, "active_plans": 1},
        memory_budget_weights={"preferences": 1.2, "goals": 0.8, "episodic": 0.7},
    ),
    "emotional_focus": FocusProfile(
        focus_mode="emotional_focus",
        section_weights={
            "user_context": "low",
            "plan_context": "minimal",
            "cognitive_prism": "full",
            "preferences": "low",
            "goals": "low",
            "episodic": "medium",
            "task_summary": "off",
        },
        section_caps={"goals": 1, "episodic": 2, "next_actions": 0, "active_plans": 1},
        memory_budget_weights={"preferences": 0.8, "goals": 0.7, "episodic": 1.5},
    ),
    "cognitive_focus": FocusProfile(
        focus_mode="cognitive_focus",
        section_weights={
            "user_context": "low",
            "plan_context": "low",
            "cognitive_prism": "full",
            "preferences": "low",
            "goals": "low",
            "episodic": "medium",
            "task_summary": "off",
        },
        section_caps={"goals": 2, "episodic": 3, "next_actions": 1, "active_plans": 1},
        memory_budget_weights={"preferences": 0.8, "goals": 0.9, "episodic": 1.3},
    ),
    "general_focus": FocusProfile(
        focus_mode="general_focus",
        section_weights={
            "user_context": "medium",
            "plan_context": "medium",
            "cognitive_prism": "compact",
            "preferences": "medium",
            "goals": "medium",
            "episodic": "medium",
            "task_summary": "medium",
        },
        section_caps={"goals": 3, "episodic": 2, "next_actions": 3, "active_plans": 2},
        memory_budget_weights={"preferences": 1.0, "goals": 1.0, "episodic": 1.0},
    ),
}


def get_focus_profile(focus_mode: str | None) -> FocusProfile:
    return FOCUS_PROFILES.get(str(focus_mode or "").strip(), FOCUS_PROFILES["general_focus"])


@dataclass
class ContextFocusDecision:
    focus_mode: str
    focus_reason: str
    section_weights: dict[str, str]
    section_caps: dict[str, int]
    briefing_candidates: list[str] = field(default_factory=list)
    semantic_gating_enabled: bool = True
    route_intent: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "focus_mode": self.focus_mode,
            "focus_reason": self.focus_reason,
            "section_weights": dict(self.section_weights),
            "section_caps": dict(self.section_caps),
            "briefing_candidates": list(self.briefing_candidates),
            "semantic_gating_enabled": self.semantic_gating_enabled,
            "route_intent": self.route_intent,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "ContextFocusDecision | None":
        if not isinstance(payload, dict):
            return None
        focus_mode = str(payload.get("focus_mode") or "").strip()
        if not focus_mode:
            return None
        return cls(
            focus_mode=focus_mode,
            focus_reason=str(payload.get("focus_reason") or ""),
            section_weights=dict(payload.get("section_weights") or {}),
            section_caps={str(k): int(v) for k, v in dict(payload.get("section_caps") or {}).items()},
            briefing_candidates=[str(item) for item in list(payload.get("briefing_candidates") or [])],
            semantic_gating_enabled=bool(payload.get("semantic_gating_enabled", True)),
            route_intent=str(payload.get("route_intent") or "") or None,
        )


class ContextFocusResolver:
    def resolve(
        self,
        *,
        user_message: str,
        route_intent: str | None,
        plan_context: dict[str, Any] | None,
        cognitive_insights: dict[str, Any] | None,
        session_feedback_signal: dict[str, Any] | None = None,
        force_focus_mode: str | None = None,
    ) -> ContextFocusDecision:
        if force_focus_mode:
            profile = get_focus_profile(force_focus_mode)
            return ContextFocusDecision(
                focus_mode=profile.focus_mode,
                focus_reason="forced_focus_mode",
                section_weights=dict(profile.section_weights),
                section_caps=dict(profile.section_caps),
                semantic_gating_enabled=bool(
                    settings.ENABLE_CONTEXT_SEMANTIC_GATING and profile.semantic_gating_enabled
                ),
                route_intent=normalize_route_intent(route_intent),
            )

        normalized_intent = normalize_route_intent(route_intent)
        text = str(user_message or "").strip().lower()
        has_plan_context = bool(plan_context)
        has_cognitive = bool((cognitive_insights or {}).get("has_cognitive_patterns"))

        focus_mode = "general_focus"
        focus_reason = f"route:{normalized_intent or 'chat'}"

        if normalized_intent in {"plan", "sprint_plan"}:
            focus_mode = "plan_focus"
        elif normalized_intent == "task":
            focus_mode = "task_focus"
        elif normalized_intent == "cognitive_prism":
            focus_mode = "cognitive_focus"
        elif normalized_intent in {"translation", "knowledge", "error_diagnosis", "learn", "review"}:
            focus_mode = "knowledge_focus"
        elif _contains_any(text, TASK_ACTION_KEYWORDS):
            focus_mode = "task_focus"
            focus_reason = "heuristic:task"
        elif _contains_any(text, PLAN_ACTION_KEYWORDS) or (has_plan_context and "调整" in text and "计划" in text):
            focus_mode = "plan_focus"
            focus_reason = "heuristic:plan"
        elif _contains_any(text, KNOWLEDGE_ACTION_KEYWORDS):
            focus_mode = "knowledge_focus"
            focus_reason = "heuristic:knowledge"

        if (
            _contains_any(text, EMOTIONAL_SIGNAL_KEYWORDS)
            and not _contains_any(text, TASK_ACTION_KEYWORDS | PLAN_ACTION_KEYWORDS)
        ):
            focus_mode = "emotional_focus"
            focus_reason = "heuristic:emotional"

        if focus_mode == "general_focus" and has_cognitive and ("模式" in text or "习惯" in text or "状态" in text):
            focus_mode = "cognitive_focus"
            focus_reason = "heuristic:cognitive"

        if isinstance(session_feedback_signal, dict) and session_feedback_signal.get("signal_type") == "mismatch":
            focus_reason += "|session_feedback:mismatch"

        profile = get_focus_profile(focus_mode)
        briefing_candidates = _build_briefing_candidates(
            focus_mode=focus_mode,
            plan_context=plan_context,
            cognitive_insights=cognitive_insights,
        )

        return ContextFocusDecision(
            focus_mode=focus_mode,
            focus_reason=focus_reason,
            section_weights=dict(profile.section_weights),
            section_caps=dict(profile.section_caps),
            briefing_candidates=briefing_candidates,
            semantic_gating_enabled=bool(settings.ENABLE_CONTEXT_SEMANTIC_GATING and profile.semantic_gating_enabled),
            route_intent=normalized_intent,
        )


class FocusedContextAssembler:
    def __init__(self, db: AsyncSession, redis=None) -> None:
        self.db = db
        self.redis = redis
        self.resolver = ContextFocusResolver()

    async def assemble(
        self,
        *,
        user_id: UUID,
        user_message: str,
        route_intent: str | None,
        plan_id: UUID | None,
        plan_context: dict[str, Any] | None,
        user_context_payload: dict[str, Any] | None,
        session_feedback_signal: dict[str, Any] | None = None,
        force_focus_mode: str | None = None,
    ) -> tuple[ContextFocusDecision, dict[str, Any], str]:
        cognitive_insights = {}
        if isinstance(user_context_payload, dict):
            raw_cognitive = user_context_payload.get("cognitive_insights")
            if isinstance(raw_cognitive, dict):
                cognitive_insights = raw_cognitive

        decision = self.resolver.resolve(
            user_message=user_message,
            route_intent=route_intent,
            plan_context=plan_context,
            cognitive_insights=cognitive_insights,
            session_feedback_signal=session_feedback_signal,
            force_focus_mode=force_focus_mode,
        )

        focused_memory: dict[str, Any] = {}
        briefing_note = ""

        if settings.ENABLE_CONTEXT_FOCUSING:
            try:
                from app.core.context_pack import ContextPackBuilder

                builder = ContextPackBuilder(self.db, redis=self.redis)
                context_pack = await builder.build(
                    user_id=user_id,
                    intent=route_intent_to_budget_intent(route_intent),
                    plan_id=plan_id,
                    query_text=user_message,
                    focus_mode=decision.focus_mode,
                    route_intent=route_intent,
                )
                focused_memory = {
                    "preferences": dict(context_pack.preferences),
                    "active_goals": list(context_pack.goals),
                    "episodic_memories": list(context_pack.episodic_memories),
                    "context_pack": {
                        "intent": context_pack.intent,
                        "budgets": dict(context_pack.budgets),
                        "token_usage": dict(context_pack.token_usage),
                        "budget_remaining": dict(context_pack.budget_remaining),
                        "pack_id": str(context_pack.pack_id) if context_pack.pack_id else None,
                        "metadata": context_pack.metadata or {},
                    },
                }
                if context_pack.context_focus:
                    decision = ContextFocusDecision.from_dict(context_pack.context_focus) or decision
                briefing_note = context_pack.context_briefing_note or ""
            except Exception as exc:
                logger.warning(f"Failed to assemble focused memory overlay: {exc}")

        if not briefing_note and settings.ENABLE_CONTEXT_BRIEFING:
            briefing_note = build_context_briefing_note(
                decision=decision,
                plan_context=plan_context,
                user_context=user_context_payload,
                focused_memory=focused_memory,
            )

        return decision, focused_memory, briefing_note


def build_context_briefing_note(
    *,
    decision: ContextFocusDecision,
    plan_context: dict[str, Any] | None,
    user_context: dict[str, Any] | None,
    focused_memory: dict[str, Any] | None,
) -> str:
    if not settings.ENABLE_CONTEXT_BRIEFING:
        return ""

    candidates: list[str] = []

    if isinstance(plan_context, dict):
        plan_title = str(plan_context.get("plan_title") or plan_context.get("title") or plan_context.get("name") or "").strip()
        if plan_title:
            candidates.append(f"当前重点计划：{plan_title}")
        stage = str(plan_context.get("plan_stage") or "").strip()
        if stage:
            candidates.append(f"处于{stage}阶段")
        task_summary = plan_context.get("task_summary")
        if isinstance(task_summary, dict) and task_summary.get("total"):
            completed = int(task_summary.get("completed", 0) or 0)
            total = int(task_summary.get("total", 0) or 0)
            candidates.append(f"计划任务进度 {completed}/{total}")

    focused_goals = ((focused_memory or {}).get("active_goals") or [])[:2]
    for item in focused_goals:
        if isinstance(item, dict):
            title = str(item.get("title") or "").strip()
            if title:
                candidates.append(f"当前目标：{title}")

    focused_preferences = dict((focused_memory or {}).get("preferences") or {})
    if decision.focus_mode == "emotional_focus":
        tone = str(((user_context or {}).get("llm_profile") or {}).get("tone") or "").strip()
        if tone:
            candidates.append(f"回答语气偏向{tone}")
    for key in ("depth_preference", "curiosity_preference"):
        if key in focused_preferences:
            candidates.append(f"{key}={focused_preferences[key]}")

    for item in decision.briefing_candidates:
        if item:
            candidates.append(str(item).strip())

    compact = [item for item in candidates if item]
    if not compact:
        return ""
    summary = "；".join(list(dict.fromkeys(compact))[:3])
    return summary[:120]


def _build_briefing_candidates(
    *,
    focus_mode: str,
    plan_context: dict[str, Any] | None,
    cognitive_insights: dict[str, Any] | None,
) -> list[str]:
    candidates: list[str] = []
    if focus_mode == "emotional_focus":
        candidates.append("本轮优先降低认知负荷并稳定情绪")
    elif focus_mode == "plan_focus":
        candidates.append("本轮优先围绕计划调整与执行约束回答")
    elif focus_mode == "task_focus":
        candidates.append("本轮优先给出当前任务顺序与下一步")
    elif focus_mode == "cognitive_focus":
        candidates.append("本轮优先解释学习模式与行为线索")
    elif focus_mode == "knowledge_focus":
        candidates.append("本轮优先聚焦知识解释，减少无关画像噪声")

    if isinstance(plan_context, dict):
        goal = str(plan_context.get("goal") or "").strip()
        if goal:
            candidates.append(f"计划目标：{goal}")

    if isinstance(cognitive_insights, dict) and cognitive_insights.get("has_cognitive_patterns"):
        count = int(cognitive_insights.get("pattern_count", 0) or 0)
        if count > 0:
            candidates.append(f"已有{count}条行为模式可供参考")
    return candidates[:3]


def _contains_any(text: str, keywords: set[str]) -> bool:
    return any(keyword in text for keyword in keywords)
