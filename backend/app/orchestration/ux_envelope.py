from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import timezone, datetime
from typing import Any

from app.config import settings
from app.core.business_metrics import (
    UX_BLOCKED_HISTORY_HIT_TOTAL,
    UX_BLOCKED_TEMPERATURE_TOTAL,
    UX_NEXT_ACTION_FALLBACK_TOTAL,
    UX_NEXT_ACTION_GENERATED_TOTAL,
    UX_PRESENTATION_STYLE_TOTAL,
    UX_STAGE_DETECTED_TOTAL,
)
from app.core.cache import cache_service
from app.orchestration.chat_modes import CHAT_MODE_STANDARD
from app.orchestration.mode_workflow_config import get_workflow_config


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


WARM_TONE_KEYWORDS = {"warm", "gentle", "encouraging", "supportive", "温和", "鼓励", "陪伴", "柔和"}
ANALYTICAL_TONE_KEYWORDS = {"analytical", "professional", "structured", "rational", "理性", "结构化", "专业", "冷静"}
HIGH_EXPLORATION_KEYWORDS = {"high", "deep", "wide", "exploratory", "高", "深入", "发散"}
COMPACT_VERBOSITY_KEYWORDS = {"low", "brief", "concise", "short", "简洁", "精简", "短"}
EXPLORATORY_VERBOSITY_KEYWORDS = {"high", "verbose", "detailed", "rich", "详细", "展开", "丰富"}
NEGATIVE_USER_SIGNAL_KEYWORDS = {
    "崩溃",
    "焦虑",
    "压力",
    "学不进去",
    "撑不住",
    "烦",
    "累",
    "难受",
    "痛苦",
    "沮丧",
    "低落",
    "不想",
}
HIGH_FRICTION_ACTION_TYPES = {"start_focus", "create_task_draft", "switch_plan"}


@dataclass(frozen=True)
class PresentationProfile:
    mode_label: str
    companion_frame: str
    answer_kind: str
    default_retry_options: list[str]
    first_screen_focus: str
    next_actions_title: str
    blocked_title: str
    blocked_message: str
    partial_message: str
    next_action_limit: int = 3


@dataclass(frozen=True)
class PresentationStyleDecision:
    style_variant: str
    tone_variant: str
    next_action_limit: int
    companion_frame_variant: str
    next_actions_title_variant: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "style_variant": self.style_variant,
            "tone_variant": self.tone_variant,
            "next_action_limit": self.next_action_limit,
            "companion_frame_variant": self.companion_frame_variant,
            "next_actions_title_variant": self.next_actions_title_variant,
        }


@dataclass(frozen=True)
class StructuredAction:
    label: str
    type: str
    payload: dict[str, Any]
    style: str
    stage: str
    reason_key: str

    def to_dict(self) -> dict[str, Any]:
        data = {
            "label": self.label,
            "type": self.type,
            "payload": self.payload,
            "style": self.style,
            "stage": self.stage,
            "reason_key": self.reason_key,
        }
        for key in ("prompt", "route", "plan_id", "task_id", "title"):
            if key in self.payload and self.payload[key]:
                data[key] = self.payload[key]
        return data


class BlockedPresentationHistoryStore:
    TTL_SECONDS = 60 * 60 * 24 * 30

    def __init__(self) -> None:
        self._local_state: dict[str, dict[str, Any]] = {}

    @staticmethod
    def _key(user_id: str, failure_kind: str) -> str:
        return f"ux:blocking:{user_id}:{failure_kind}"

    async def record(self, user_id: str | None, failure_kind: str | None) -> int:
        if not user_id or not failure_kind or failure_kind == "none":
            return 0
        key = self._key(user_id, failure_kind)
        now = _utcnow().isoformat()
        redis_client = cache_service.redis
        if redis_client:
            try:
                raw = await redis_client.get(key)
                payload = json.loads(raw) if raw else {}
                count = int(payload.get("count") or 0) + 1
                await redis_client.setex(
                    key,
                    self.TTL_SECONDS,
                    json.dumps({"count": count, "last_seen_at": now}, ensure_ascii=False),
                )
                return count
            except Exception:
                pass

        payload = self._local_state.get(key) or {"count": 0}
        count = int(payload.get("count") or 0) + 1
        self._local_state[key] = {"count": count, "last_seen_at": now}
        return count


_MODE_PROFILES: dict[str, PresentationProfile] = {
    "standard": PresentationProfile(
        mode_label="标准对话",
        companion_frame="我先给你一个直接可用的回答，再补充依据和下一步。",
        answer_kind="direct_answer",
        default_retry_options=["换个问法", "补充材料", "切换模式"],
        first_screen_focus="先给结论，再给你一个可继续追问的切口。",
        next_actions_title="你现在可以继续这样推进",
        blocked_title="继续前我还需要一点补充",
        blocked_message="我已经抓到问题主轴，但还缺一个关键上下文，补上后我能直接收敛答案。",
        partial_message="主结论已经给出，但有一部分细节还需要你补充或让我继续收紧。",
    ),
    "deep_analysis": PresentationProfile(
        mode_label="深度解析",
        companion_frame="我先帮你拆清问题边界，再给出更扎实的结论与依据。",
        answer_kind="synthesis",
        default_retry_options=["补充约束", "只看结论", "切回标准模式"],
        first_screen_focus="先给综合判断，再展开观点、证据和风险。",
        next_actions_title="如果要继续深挖，建议按这个顺序来",
        blocked_title="继续深入前还差一个分析约束",
        blocked_message="我可以继续往下推，但需要你明确范围、目标或判断标准，否则会浪费你的注意力。",
        partial_message="主判断已形成，但部分证据链或反例还可以继续压实。",
    ),
    "study_plan": PresentationProfile(
        mode_label="学习计划",
        companion_frame="我先把目标拆成可执行步骤，再帮你落到今天能开始的动作。",
        answer_kind="plan",
        default_retry_options=["降低难度", "调整节奏", "重新规划"],
        first_screen_focus="先给阶段目标，再落到今天和本周的动作。",
        next_actions_title="先把计划落地到这几步",
        blocked_title="排计划前还差你的现实约束",
        blocked_message="我已经有了方向，但还需要你的时间、目标期限或当前水平，计划才会真正可执行。",
        partial_message="计划骨架已经成形，但我建议再补一个现实约束，让它更贴你的节奏。",
    ),
    "error_diagnosis": PresentationProfile(
        mode_label="错题分析",
        companion_frame="我先定位错误类型和根因，再给你修复动作。",
        answer_kind="diagnosis",
        default_retry_options=["补充题目", "上传材料", "切到深度解析"],
        first_screen_focus="先说错因，再给证据和修复动作。",
        next_actions_title="先把这个错误修干净",
        blocked_title="要定位错因，我还需要题目证据",
        blocked_message="我已经能判断大方向，但没有题目、解题步骤或截图，没法把根因钉准。",
        partial_message="我已经定位了主要错因，但还可以再补证据，把修复动作更精准。",
    ),
    "expert_auto": PresentationProfile(
        mode_label="专家自动",
        companion_frame="我会先调度合适的专家协作，再给你综合结论。",
        answer_kind="synthesis",
        default_retry_options=["指定专家", "只保留主结论", "切回标准模式"],
        first_screen_focus="先给综合结论，再说明主要专家贡献和分歧。",
        next_actions_title="如果要继续协作，建议这样走",
        blocked_title="专家协作已开始，但我还需要你确认方向",
        blocked_message="我已经调到合适的处理路径，但还需要你确认优先级，否则专家会在错误方向上继续发力。",
        partial_message="综合结论已可用，但有部分专家结果处于降级或待补状态。",
    ),
    "execution_delegate": PresentationProfile(
        mode_label="执行委派",
        companion_frame="我帮你把这个交给AI执行，你可以在完成前随时取回控制权。",
        answer_kind="delegation_brief",
        default_retry_options=["换一个方案执行", "我自己来", "修改执行参数"],
        first_screen_focus="delegation_status",
        next_actions_title="执行完成后",
        blocked_title="执行受限",
        blocked_message="当前任务不适合自动执行，建议手动完成。",
        partial_message="AI已部分完成执行，你可以在此基础上继续。",
        next_action_limit=2,
    ),
}


class UXEnvelopeBuilder:
    def __init__(self, blocked_history_store: BlockedPresentationHistoryStore | None = None) -> None:
        self._blocked_history_store = blocked_history_store or BlockedPresentationHistoryStore()

    async def build(
        self,
        *,
        user_message: str,
        full_response: str,
        final_state: Any,
        executable_plan: Any | None,
        route_decision: Any,
        include_references: bool,
        file_ids: list[str],
        execution_validation: dict[str, Any] | None,
        conversation_context: dict[str, Any] | None,
        plan_context: dict[str, Any] | None,
        user_context_payload: dict[str, Any] | None,
    ) -> dict[str, dict[str, Any]]:
        context_data = getattr(final_state, "context_data", {}) or {}
        chat_mode = str(context_data.get("chat_mode") or CHAT_MODE_STANDARD)
        if execution_validation and execution_validation.get("execution_suggestion"):
            chat_mode = "execution_delegate"
        profile = self._get_profile(chat_mode)
        selected_experts = self._selected_experts(final_state)
        style_decision = self._presentation_style_decision(
            chat_mode=chat_mode,
            profile=profile,
            user_message=user_message,
            user_context_payload=user_context_payload,
            final_state=final_state,
        )
        if settings.ENABLE_ADAPTIVE_PRESENTATION:
            UX_PRESENTATION_STYLE_TOTAL.labels(
                style_variant=style_decision.style_variant,
                tone_variant=style_decision.tone_variant,
                chat_mode=chat_mode,
            ).inc()

        completion_state = self._completion_state(final_state, executable_plan, execution_validation)
        recovery_state = self._recovery_state(
            chat_mode=chat_mode,
            completion_state=completion_state,
            include_references=include_references,
            file_ids=file_ids,
            selected_experts=selected_experts,
            execution_validation=execution_validation,
            route_decision=route_decision,
            profile=profile,
        )
        blocked_repeat_count = 0
        blocked_temperature = None
        if recovery_state["failure_kind"] != "none":
            blocked_repeat_count, blocked_temperature = await self._blocked_state(
                failure_kind=recovery_state["failure_kind"],
                user_message=user_message,
                user_context_payload=user_context_payload,
                final_state=final_state,
                style_decision=style_decision,
            )
            recovery_state["failure_message"] = self._temperature_adjusted_failure_message(
                profile=profile,
                failure_kind=recovery_state["failure_kind"],
                base_message=recovery_state["failure_message"],
                blocked_temperature=blocked_temperature,
            )

        confidence_band = self._confidence_band(executable_plan, route_decision, execution_validation)
        stage = self._conversation_stage(
            chat_mode=chat_mode,
            completion_state=completion_state,
            recovery_kind=recovery_state["failure_kind"],
            final_state=final_state,
            executable_plan=executable_plan,
            execution_validation=execution_validation,
            plan_context=plan_context,
            full_response=full_response,
        )
        if settings.ENABLE_ADAPTIVE_PRESENTATION:
            UX_STAGE_DETECTED_TOTAL.labels(stage=stage, chat_mode=chat_mode).inc()

        headline = self._result_headline(chat_mode, completion_state, selected_experts)
        if blocked_temperature and completion_state in {"blocked", "needs_input"}:
            headline = self._blocked_headline(
                profile=profile,
                blocked_temperature=blocked_temperature,
                completion_state=completion_state,
            )

        ux_turn = {
            "intent_summary": self._intent_summary(user_message, chat_mode),
            "mode_label": profile.mode_label,
            "companion_frame": (
                style_decision.companion_frame_variant
                if settings.ENABLE_ADAPTIVE_PRESENTATION
                else profile.companion_frame
            ),
            "dual_core_mode": self._dual_core_mode(final_state),
            "mode_reason": self._dual_core_reason(final_state),
        }
        if settings.ENABLE_ADAPTIVE_PRESENTATION or settings.ENABLE_UX_PRESENTATION_METADATA:
            ux_turn["presentation_style"] = style_decision.style_variant
            ux_turn["tone_variant"] = style_decision.tone_variant

        ux_result = {
            "answer_kind": self._answer_kind(profile, executable_plan, chat_mode),
            "confidence_band": confidence_band,
            "completion_state": completion_state,
            "headline": headline,
            "first_screen_focus": profile.first_screen_focus,
            "why_this_answer": self._why_this_answer(
                chat_mode=chat_mode,
                include_references=include_references,
                selected_experts=selected_experts,
                execution_validation=execution_validation,
                route_decision=route_decision,
            ),
        }
        ux_result.update(recovery_state)
        if settings.ENABLE_BLOCKED_TEMPERATURE or settings.ENABLE_UX_PRESENTATION_METADATA:
            ux_result["blocked_reason"] = recovery_state["failure_kind"]
            ux_result["blocked_temperature"] = blocked_temperature
            ux_result["blocked_repeat_count"] = blocked_repeat_count

        memory_updates = self._memory_updates(final_state, user_context_payload)
        next_actions = self._next_actions(
            chat_mode=chat_mode,
            executable_plan=executable_plan,
            plan_context=plan_context,
            profile=profile,
            full_response=full_response,
            final_state=final_state,
            stage=stage,
            style_decision=style_decision,
            completion_state=completion_state,
        )
        retry_options = self._retry_options(
            completion_state=completion_state,
            include_references=include_references,
            has_files=bool(file_ids),
            profile=profile,
            recovery_kind=recovery_state["failure_kind"],
        )

        ux_followthrough = {
            "next_actions_title": self._next_actions_title(
                profile=profile,
                stage=stage,
                style_decision=style_decision,
            ),
            "next_actions": next_actions,
            "retry_options": retry_options,
            "recovery_message": recovery_state["failure_message"],
            "memory_updates": memory_updates,
        }
        if settings.ENABLE_ADAPTIVE_PRESENTATION or settings.ENABLE_UX_PRESENTATION_METADATA:
            ux_followthrough["stage"] = stage
            ux_followthrough["next_actions_strategy"] = f"{stage}:{style_decision.style_variant}"

        ux_sources = {
            "citations_available": bool(include_references or file_ids),
            "reference_scope": self._reference_scope(include_references, file_ids),
            "evidence_summary": self._evidence_summary(include_references, file_ids, selected_experts),
            "confidence_band": confidence_band,
            "completion_state": completion_state,
            "why_this_answer": ux_result["why_this_answer"],
        }

        envelope: dict[str, dict[str, Any]] = {
            "ux_turn": ux_turn,
            "ux_result": ux_result,
            "ux_followthrough": ux_followthrough,
            "ux_sources": ux_sources,
        }

        orchestration_summary = self._orchestration_summary(
            final_state=final_state,
            chat_mode=chat_mode,
            executable_plan=executable_plan,
        )
        if orchestration_summary:
            envelope["orchestration_summary"] = orchestration_summary

        ux_evolution = self._ux_evolution(final_state=final_state, memory_updates=memory_updates)
        if ux_evolution:
            envelope["ux_evolution"] = ux_evolution

        continuity_banner = self._continuity_banner(
            conversation_context=conversation_context,
            plan_context=plan_context,
            final_state=final_state,
        )
        if continuity_banner:
            envelope["continuity_banner"] = continuity_banner

        mode_explanation = self._mode_explanation(chat_mode=chat_mode, profile=profile, selected_experts=selected_experts)
        if mode_explanation:
            envelope["mode_explanation"] = mode_explanation

        collaboration_summary = self._collaboration_summary(final_state, selected_experts)
        if collaboration_summary:
            envelope["collaboration_summary"] = collaboration_summary

        session_adaptation = self._session_adaptation(final_state)
        if session_adaptation:
            envelope["session_adaptation"] = session_adaptation

        return envelope

    def to_metadata_map(self, envelope: dict[str, dict[str, Any]]) -> dict[str, str]:
        return {
            key: json.dumps(value, ensure_ascii=False)
            for key, value in envelope.items()
            if value
        }

    def _get_profile(self, chat_mode: str) -> PresentationProfile:
        if chat_mode == "execution_delegate":
            return _MODE_PROFILES["execution_delegate"]
        if chat_mode.startswith("expert::"):
            return PresentationProfile(
                mode_label="专家直达",
                companion_frame="我会直接用该专家视角处理你的问题，再补充可执行建议。",
                answer_kind="synthesis",
                default_retry_options=["换专家", "切回专家自动", "切回标准模式"],
                first_screen_focus="先给专家结论，再说明关键依据和执行建议。",
                next_actions_title="如果要继续用专家视角推进，建议这样问",
                blocked_title="继续前还需要一个专家判断条件",
                blocked_message="我已经切到指定专家视角，但还需要你补一个关键条件，才能避免答得太泛。",
                partial_message="专家视角的主结论已经给出，但仍可以补充一层证据或约束，让建议更稳。",
            )
        return _MODE_PROFILES.get(chat_mode, _MODE_PROFILES[CHAT_MODE_STANDARD])

    def _presentation_style_decision(
        self,
        *,
        chat_mode: str,
        profile: PresentationProfile,
        user_message: str,
        user_context_payload: dict[str, Any] | None,
        final_state: Any,
    ) -> PresentationStyleDecision:
        context_data = getattr(final_state, "context_data", {}) or {}
        llm_profile = (user_context_payload or {}).get("llm_profile")
        llm_profile = llm_profile if isinstance(llm_profile, dict) else {}
        verbosity = str(llm_profile.get("verbosity_target") or "").strip().lower()
        exploration = str(llm_profile.get("exploration_level") or "").strip().lower()
        tone = str(llm_profile.get("tone") or "").strip().lower()
        session_signal = context_data.get("session_feedback_signal")
        signal_type = str((session_signal or {}).get("signal_type") or "").strip().lower()
        focus_mode = str(((context_data.get("context_focus") or {}).get("focus_mode")) or "").strip().lower()

        if signal_type == "simplify" or any(token in verbosity for token in COMPACT_VERBOSITY_KEYWORDS):
            style_variant = "compact"
        elif (
            signal_type == "expand"
            or any(token in verbosity for token in EXPLORATORY_VERBOSITY_KEYWORDS)
            or any(token in exploration for token in HIGH_EXPLORATION_KEYWORDS)
        ):
            style_variant = "exploratory"
        else:
            style_variant = "balanced"

        if focus_mode == "emotional_focus" or any(token in tone for token in WARM_TONE_KEYWORDS):
            tone_variant = "warm"
        elif any(token in tone for token in ANALYTICAL_TONE_KEYWORDS):
            tone_variant = "analytical"
        else:
            tone_variant = "direct"

        next_action_limit = {
            "compact": 2,
            "balanced": profile.next_action_limit,
            "exploratory": 4,
        }.get(style_variant, profile.next_action_limit)

        companion_frame_variant = self._companion_frame_variant(
            profile=profile,
            chat_mode=chat_mode,
            style_variant=style_variant,
            tone_variant=tone_variant,
            user_message=user_message,
        )
        next_actions_title_variant = self._base_next_actions_title(
            profile=profile,
            style_variant=style_variant,
            tone_variant=tone_variant,
        )
        return PresentationStyleDecision(
            style_variant=style_variant,
            tone_variant=tone_variant,
            next_action_limit=next_action_limit,
            companion_frame_variant=companion_frame_variant,
            next_actions_title_variant=next_actions_title_variant,
        )

    async def _blocked_state(
        self,
        *,
        failure_kind: str,
        user_message: str,
        user_context_payload: dict[str, Any] | None,
        final_state: Any,
        style_decision: PresentationStyleDecision,
    ) -> tuple[int, str]:
        if not settings.ENABLE_BLOCKED_TEMPERATURE:
            return 0, self._blocked_temperature(
                repeat_count=0,
                user_message=user_message,
                user_context_payload=user_context_payload,
                final_state=final_state,
                style_decision=style_decision,
            )

        user_id = self._extract_user_id(user_context_payload=user_context_payload, final_state=final_state)
        repeat_count = await self._blocked_history_store.record(user_id, failure_kind)
        if repeat_count > 1:
            UX_BLOCKED_HISTORY_HIT_TOTAL.labels(failure_kind=failure_kind).inc()
        blocked_temperature = self._blocked_temperature(
            repeat_count=repeat_count,
            user_message=user_message,
            user_context_payload=user_context_payload,
            final_state=final_state,
            style_decision=style_decision,
        )
        UX_BLOCKED_TEMPERATURE_TOTAL.labels(
            failure_kind=failure_kind,
            temperature=blocked_temperature,
        ).inc()
        return repeat_count, blocked_temperature

    def _blocked_temperature(
        self,
        *,
        repeat_count: int,
        user_message: str,
        user_context_payload: dict[str, Any] | None,
        final_state: Any,
        style_decision: PresentationStyleDecision,
    ) -> str:
        context_data = getattr(final_state, "context_data", {}) or {}
        focus_mode = str(((context_data.get("context_focus") or {}).get("focus_mode")) or "")
        if focus_mode == "emotional_focus":
            return "gentle"
        if style_decision.tone_variant == "warm" and self._message_has_negative_signal(user_message):
            return "gentle"
        if repeat_count >= 2:
            return "direct"
        return "guided"

    def _blocked_headline(
        self,
        *,
        profile: PresentationProfile,
        blocked_temperature: str,
        completion_state: str,
    ) -> str:
        if blocked_temperature == "gentle":
            return "别急，我还差一点点信息，就能继续帮你收敛。"
        if blocked_temperature == "direct":
            if completion_state == "needs_input":
                return "先补这一个关键信息，我就继续。"
            return "这轮先停在这里，补上关键条件后继续。"
        return profile.blocked_title

    def _temperature_adjusted_failure_message(
        self,
        *,
        profile: PresentationProfile,
        failure_kind: str,
        base_message: str,
        blocked_temperature: str | None,
    ) -> str:
        if not blocked_temperature or failure_kind == "none":
            return base_message
        if blocked_temperature == "guided":
            return base_message
        if blocked_temperature == "direct":
            direct_messages = {
                "missing_input": "还缺一个关键信息。补上后我就直接继续。",
                "tool_failure": "有步骤执行失败了。先补条件，或让我换一种做法。",
                "timeout": "这轮超时了。你可以先看当前结果，或让我基于现有信息继续。",
                "blocked": "还差一个关键条件。补上后我继续。",
                "partial_tool_failure": "主结论可用，但还有执行失败项。先决定是否继续复核。",
                "expert_degraded": "这轮走了降级路径。主结论可用，但深度会略弱。",
                "limited_evidence": "当前证据不够。先补材料，或接受保守结论。",
                "provider_unavailable": "外部模型这轮降级了。现在能先给主结论，稍后可再试深挖。",
            }
            return direct_messages.get(failure_kind, base_message)
        gentle_messages = {
            "missing_input": "我已经靠近答案了，只差一点点现实信息，补上后我就能继续帮你收紧。",
            "tool_failure": "我已经尽量保住这轮可用的部分了，只是有个执行步骤没顺利完成。我们可以换一种更稳的方式继续。",
            "timeout": "我已经拿到一部分结果了，只是这轮时间不太够。你可以先看当前结论，我也可以接着帮你慢慢收紧。",
            "blocked": "方向已经有了，只是还差一个关键条件。补上以后，我会尽量更顺着你的节奏继续。",
        }
        return gentle_messages.get(failure_kind, base_message or profile.blocked_message)

    def _conversation_stage(
        self,
        *,
        chat_mode: str,
        completion_state: str,
        recovery_kind: str,
        final_state: Any,
        executable_plan: Any | None,
        execution_validation: dict[str, Any] | None,
        plan_context: dict[str, Any] | None,
        full_response: str,
    ) -> str:
        context_data = getattr(final_state, "context_data", {}) or {}
        if completion_state in {"blocked", "needs_input"} or recovery_kind != "none":
            return "blocked"

        plan_result = context_data.get("plan_execution_result")
        if execution_validation:
            total = self._execution_total_count(execution_validation)
            failed = self._execution_failed_count(execution_validation)
            if total > 0 and failed == 0:
                has_reflection = bool(
                    context_data.get("adaptation_records")
                    or context_data.get("preference_learnings")
                    or context_data.get("progress_snapshot")
                )
                return "reflect" if has_reflection else "completed"
            if total > 0 and plan_result is not None:
                return "executing"

        plan_review = context_data.get("plan_review")
        if isinstance(plan_review, dict) and plan_review.get("decision") in {
            "approved",
            "requires_confirmation",
            "needs_modification",
        }:
            return "plan_ready"

        if plan_context and plan_context.get("plan_id") and (
            chat_mode == "study_plan"
            or executable_plan is not None
            or any(token in full_response for token in ("第一步", "开始", "执行", "今天先"))
        ):
            return "plan_ready"

        if plan_result is not None and hasattr(plan_result, "step_results"):
            return "executing"

        return "explore"

    def _companion_frame_variant(
        self,
        *,
        profile: PresentationProfile,
        chat_mode: str,
        style_variant: str,
        tone_variant: str,
        user_message: str,
    ) -> str:
        if style_variant == "compact":
            if tone_variant == "warm":
                return "我先用更短、更轻一点的方式，把当前最有用的部分说清。"
            if tone_variant == "analytical":
                return "我先压缩成结论、关键依据和下一步，避免信息过载。"
            return "我先给你最直接可用的部分，再看要不要展开。"
        if style_variant == "exploratory":
            if tone_variant == "warm":
                return f"{profile.companion_frame} 如果你愿意，我也会补几个更适合继续聊下去的方向。"
            if tone_variant == "analytical":
                return f"{profile.companion_frame} 我会顺手标出关键依据、风险和可选分支。"
            return f"{profile.companion_frame} 我也会补几个可继续探索的方向。"
        if tone_variant == "warm" or self._message_has_negative_signal(user_message):
            return "我会先顺着你的节奏把关键部分说清，再带你决定下一步。"
        if tone_variant == "analytical":
            return f"{profile.companion_frame} 我会尽量按结论、依据、动作来组织。"
        return profile.companion_frame

    def _base_next_actions_title(
        self,
        *,
        profile: PresentationProfile,
        style_variant: str,
        tone_variant: str,
    ) -> str:
        if style_variant == "compact":
            return "先做这 1 到 2 步就够了"
        if style_variant == "exploratory" and tone_variant == "warm":
            return "如果你愿意，可以从这里继续往前走"
        if tone_variant == "analytical":
            return "建议按这个顺序继续"
        return profile.next_actions_title

    def _next_actions_title(
        self,
        *,
        profile: PresentationProfile,
        stage: str,
        style_decision: PresentationStyleDecision,
    ) -> str:
        if not settings.ENABLE_ADAPTIVE_PRESENTATION:
            return profile.next_actions_title
        stage_titles = {
            "explore": {
                "compact": "你可以先这样继续",
                "balanced": style_decision.next_actions_title_variant,
                "exploratory": "如果要继续深入，可以从这里展开",
            },
            "plan_ready": {
                "compact": "先把计划落到这一步",
                "balanced": "下一步先把计划落地",
                "exploratory": "先开始第一步，再决定要不要继续扩展",
            },
            "executing": {
                "compact": "继续把这一小步推进完",
                "balanced": "现在最值得继续的是这几步",
                "exploratory": "执行中可以优先推进这些动作",
            },
            "blocked": {
                "compact": "先补这一点，我就继续",
                "balanced": "先解除当前阻塞",
                "exploratory": "先把阻塞拆开，再继续推进",
            },
            "completed": {
                "compact": "这轮结束后，建议这样承接",
                "balanced": "你现在可以这样收尾或承接",
                "exploratory": "这轮完成后，还可以这样往前走",
            },
            "reflect": {
                "compact": "现在适合做个短回顾",
                "balanced": "这时候适合回顾一下过程",
                "exploratory": "如果你愿意，现在可以顺手做一轮反思更新",
            },
        }
        title = stage_titles.get(stage, {}).get(style_decision.style_variant) or style_decision.next_actions_title_variant
        if style_decision.tone_variant == "warm" and stage == "blocked":
            return "别急，我们先把这一点补齐"
        return title

    def _selected_experts(self, final_state: Any) -> list[str]:
        context_data = getattr(final_state, "context_data", {}) or {}
        raw = context_data.get("selected_experts")
        if not isinstance(raw, list):
            return []
        return [str(item).strip() for item in raw if str(item).strip()]

    def _intent_summary(self, user_message: str, chat_mode: str) -> str:
        compact = " ".join(user_message.strip().split())
        compact = compact[:80] + ("..." if len(compact) > 80 else "")
        if chat_mode == "study_plan":
            return f"你想把目标拆成可执行的学习安排：{compact}"
        if chat_mode == "error_diagnosis":
            return f"你希望定位问题根因并得到修复方案：{compact}"
        if chat_mode == "deep_analysis":
            return f"你希望获得更深入、更可验证的分析：{compact}"
        if chat_mode.startswith("expert::"):
            return f"你希望由指定专家直接处理这个问题：{compact}"
        if chat_mode == "expert_auto":
            return f"你希望我自动调度合适专家协作处理：{compact}"
        return f"你希望我直接帮你推进这个问题：{compact}"

    def _answer_kind(self, profile: PresentationProfile, executable_plan: Any | None, chat_mode: str) -> str:
        if executable_plan is not None and getattr(executable_plan, "tool_calls", None):
            return "action_bundle"
        if chat_mode == "study_plan":
            return "plan"
        if chat_mode == "error_diagnosis":
            return "diagnosis"
        return profile.answer_kind

    def _result_headline(self, chat_mode: str, completion_state: str, selected_experts: list[str]) -> str:
        if completion_state == "blocked":
            return "这轮先给你可用结论，但要继续推进还需要补一个关键条件。"
        if completion_state == "needs_input":
            return "我已经整理出方向，等你确认后就能继续收敛。"
        if completion_state == "partial":
            return "主结论已经成立，剩下的是把边角证据和执行细节补齐。"
        if chat_mode == "study_plan":
            return "我会先把目标拆成阶段，再落到今天就能开始的动作。"
        if chat_mode == "error_diagnosis":
            return "我会先判断错因，再给你一条最省力的修复路径。"
        if chat_mode == "deep_analysis":
            return "我会先给综合判断，再把依据、反例和风险摊开。"
        if chat_mode.startswith("expert::"):
            return "这轮我直接用指定专家视角先给你结论，再补执行建议。"
        if chat_mode == "expert_auto":
            expert_hint = f" 已调度 {len(selected_experts)} 位专家参与。" if selected_experts else ""
            return f"我会先给综合结论，再说明主要专家贡献。{expert_hint}".strip()
        return "我会先直接回答你的当前问题，再补依据和下一步。"

    @staticmethod
    def _execution_metric(
        execution_validation: dict[str, Any] | None,
        primary_key: str,
        fallback_key: str,
    ) -> int:
        if not execution_validation:
            return 0
        value = execution_validation.get(primary_key)
        if value is None:
            value = execution_validation.get(fallback_key)
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            return 0

    def _execution_failed_count(self, execution_validation: dict[str, Any] | None) -> int:
        return self._execution_metric(execution_validation, "failed_steps", "failed_tool_calls")

    def _execution_total_count(self, execution_validation: dict[str, Any] | None) -> int:
        return self._execution_metric(execution_validation, "total_steps", "total_tool_calls")

    def _completion_state(self, final_state: Any, executable_plan: Any | None, execution_validation: dict[str, Any] | None) -> str:
        if execution_validation:
            if execution_validation.get("execution_suggestion"):
                return "partial"
            failed = self._execution_failed_count(execution_validation)
            total = self._execution_total_count(execution_validation)
            if total and failed and failed < total:
                return "partial"
            if total and failed >= total:
                return "blocked"
        context_data = getattr(final_state, "context_data", {}) or {}
        if context_data.get("plan_review"):
            return "needs_input"
        if executable_plan is not None and not getattr(executable_plan, "tool_calls", []):
            return "done"
        return "done"

    def _confidence_band(self, executable_plan: Any | None, route_decision: Any, execution_validation: dict[str, Any] | None) -> str:
        validation_score = None
        if execution_validation:
            validation_score = execution_validation.get("quality_score") or execution_validation.get("confidence")
        plan_confidence = getattr(executable_plan, "confidence", None)
        route_confidence = getattr(route_decision, "confidence", None)
        for score in (validation_score, plan_confidence, route_confidence):
            if isinstance(score, (float, int)):
                if score >= 0.8:
                    return "high"
                if score >= 0.55:
                    return "medium"
        if self._execution_failed_count(execution_validation) > 0:
            return "cautious"
        return "medium"

    def _why_this_answer(
        self,
        *,
        chat_mode: str,
        include_references: bool,
        selected_experts: list[str],
        execution_validation: dict[str, Any] | None,
        route_decision: Any,
    ) -> str:
        parts: list[str] = []
        if selected_experts:
            experts = "、".join(selected_experts[:3])
            parts.append(f"本轮已结合 {experts} 的处理结果")
        elif chat_mode == "deep_analysis":
            parts.append("这轮优先按观点、依据和风险组织了回答")
        elif chat_mode == "study_plan":
            parts.append("这轮优先把目标拆成节奏和执行动作")
        elif chat_mode == "error_diagnosis":
            parts.append("这轮优先按错因、证据和修复动作组织了回答")
        elif chat_mode != CHAT_MODE_STANDARD:
            parts.append("本轮按当前协作模式组织了回答结构")
        else:
            parts.append("本轮优先给出直接可执行的回答")
        if include_references:
            parts.append("并优先参考了你提供的材料或检索依据")
        if self._execution_failed_count(execution_validation) > 0:
            parts.append("部分执行步骤失败，所以我对结论保持审慎")
        fallback_reason = getattr(route_decision, "reason", "") or ""
        if fallback_reason and "fallback" in fallback_reason.lower():
            parts.append("当前结果包含降级综合")
        return "，".join(parts) + "。"

    def _recovery_state(
        self,
        *,
        chat_mode: str,
        completion_state: str,
        include_references: bool,
        file_ids: list[str],
        selected_experts: list[str],
        execution_validation: dict[str, Any] | None,
        route_decision: Any,
        profile: PresentationProfile,
    ) -> dict[str, str]:
        fallback_reason = (getattr(route_decision, "reason", "") or "").lower()
        if completion_state == "needs_input":
            return {
                "failure_kind": "missing_input",
                "failure_message": profile.blocked_message,
            }
        if completion_state == "blocked":
            if self._execution_failed_count(execution_validation) > 0:
                return {
                    "failure_kind": "tool_failure",
                    "failure_message": "我已经给出目前能确认的部分，但有执行步骤失败了。你可以补充条件、换一种做法，或让我先给降级方案。",
                }
            if "timeout" in fallback_reason:
                return {
                    "failure_kind": "timeout",
                    "failure_message": "我已经拿到一部分结果，但本轮处理超时了。你可以先看当前结论，或让我基于现有材料继续收敛。",
                }
            return {
                "failure_kind": "blocked",
                "failure_message": profile.blocked_message,
            }
        if self._execution_failed_count(execution_validation) > 0:
            message = profile.partial_message
            if selected_experts and "fallback" in fallback_reason:
                message = "综合结论已可用，但有部分专家结果降级或执行步骤失败，所以这轮更适合先拿主结论，再决定是否继续复核。"
            return {
                "failure_kind": "partial_tool_failure",
                "failure_message": message,
            }
        if selected_experts and "fallback" in fallback_reason:
            return {
                "failure_kind": "expert_degraded",
                "failure_message": "这轮已经做了降级综合，主结论仍可用，但专家深度会比完整协作略弱。",
            }
        if include_references and not file_ids:
            return {
                "failure_kind": "limited_evidence",
                "failure_message": "你希望我带依据回答，但当前可用材料有限。我会先给可用判断，并明确哪些部分还需要证据。",
            }
        if any(token in fallback_reason for token in ("provider", "unavailable", "model")):
            return {
                "failure_kind": "provider_unavailable",
                "failure_message": "外部模型服务这轮发生了降级切换。我已经保住主结论，但如果你需要更深结果，可以稍后重试或切模式。",
            }
        return {
            "failure_kind": "none",
            "failure_message": "",
        }

    def _next_actions(
        self,
        *,
        chat_mode: str,
        executable_plan: Any | None,
        plan_context: dict[str, Any] | None,
        profile: PresentationProfile,
        full_response: str,
        final_state: Any,
        stage: str,
        style_decision: PresentationStyleDecision,
        completion_state: str,
    ) -> list[Any]:
        if not settings.ENABLE_ADAPTIVE_PRESENTATION and not settings.ENABLE_STRUCTURED_NEXT_ACTIONS:
            return self._default_next_action_labels(
                chat_mode=chat_mode,
                executable_plan=executable_plan,
                plan_context=plan_context,
                profile=profile,
                full_response=full_response,
            )

        task_candidates = self._task_candidates(plan_context=plan_context, final_state=final_state)
        actions = self._build_stage_actions(
            stage=stage,
            chat_mode=chat_mode,
            full_response=full_response,
            plan_context=plan_context,
            task_candidates=task_candidates,
            style_decision=style_decision,
            completion_state=completion_state,
        )
        if not actions:
            UX_NEXT_ACTION_FALLBACK_TOTAL.labels(reason="empty_stage_actions").inc()
            fallback = self._default_next_action_labels(
                chat_mode=chat_mode,
                executable_plan=executable_plan,
                plan_context=plan_context,
                profile=profile,
                full_response=full_response,
            )
            if not settings.ENABLE_STRUCTURED_NEXT_ACTIONS:
                return fallback
            actions = [
                StructuredAction(
                    label=label,
                    type="prompt",
                    payload={"prompt": label},
                    style="primary" if idx == 0 else "secondary",
                    stage=stage,
                    reason_key="fallback_prompt",
                )
                for idx, label in enumerate(fallback)
            ]

        finalized = self._finalize_actions(
            actions=actions,
            limit=style_decision.next_action_limit if settings.ENABLE_ADAPTIVE_PRESENTATION else profile.next_action_limit,
        )
        if not settings.ENABLE_STRUCTURED_NEXT_ACTIONS:
            return [action.label for action in finalized]
        for action in finalized:
            UX_NEXT_ACTION_GENERATED_TOTAL.labels(stage=stage, action_type=action.type).inc()
        return [action.to_dict() for action in finalized]

    def _build_stage_actions(
        self,
        *,
        stage: str,
        chat_mode: str,
        full_response: str,
        plan_context: dict[str, Any] | None,
        task_candidates: list[dict[str, Any]],
        style_decision: PresentationStyleDecision,
        completion_state: str,
    ) -> list[StructuredAction]:
        actions: list[StructuredAction] = []
        primary_task = task_candidates[0] if task_candidates else None
        plan_id = str((plan_context or {}).get("plan_id") or "").strip()
        plan_title = str(
            (plan_context or {}).get("plan_title")
            or (plan_context or {}).get("plan_name")
            or "当前计划"
        ).strip()

        if stage == "plan_ready":
            if primary_task:
                actions.append(self._start_focus_action(primary_task, stage=stage, style="primary"))
                actions.append(self._open_task_action(primary_task, stage=stage, style="secondary"))
            elif plan_title:
                actions.append(
                    StructuredAction(
                        label="把第一步建成任务",
                        type="create_task_draft",
                        payload={"title": f"开始执行：{plan_title}"},
                        style="primary",
                        stage=stage,
                        reason_key="draft_first_task",
                    )
                )
                UX_NEXT_ACTION_FALLBACK_TOTAL.labels(reason="missing_task_context").inc()
            if plan_id:
                actions.append(
                    StructuredAction(
                        label="切回这个计划继续",
                        type="switch_plan",
                        payload={"plan_id": plan_id},
                        style="ghost",
                        stage=stage,
                        reason_key="switch_plan_context",
                    )
                )
            actions.append(
                StructuredAction(
                    label="帮我再调一下时间安排",
                    type="prompt",
                    payload={"prompt": "帮我再调整一下这份计划的时间安排"},
                    style="secondary",
                    stage=stage,
                    reason_key="adjust_plan",
                )
            )
            return actions

        if stage == "executing":
            if primary_task:
                actions.append(self._open_task_action(primary_task, stage=stage, style="primary"))
                actions.append(self._start_focus_action(primary_task, stage=stage, style="secondary"))
            else:
                UX_NEXT_ACTION_FALLBACK_TOTAL.labels(reason="executing_without_task").inc()
                actions.append(
                    StructuredAction(
                        label="我来继续拆下一步",
                        type="prompt",
                        payload={"prompt": "根据当前执行结果，继续帮我拆下一步"},
                        style="primary",
                        stage=stage,
                        reason_key="continue_execution_prompt",
                    )
                )
            actions.append(
                StructuredAction(
                    label="帮我汇总当前进展",
                    type="prompt",
                    payload={"prompt": "帮我汇总一下当前进展和下一步"},
                    style="secondary",
                    stage=stage,
                    reason_key="summarize_progress",
                )
            )
            return actions

        if stage == "blocked":
            blocked_prompt = {
                "compact": "我补一下关键信息",
                "balanced": "我来补充缺失信息后继续",
                "exploratory": "换一种方式继续推进这个问题",
            }.get(style_decision.style_variant, "我补一下关键信息")
            actions.append(
                StructuredAction(
                    label=blocked_prompt,
                    type="prompt",
                    payload={"prompt": blocked_prompt},
                    style="primary",
                    stage=stage,
                    reason_key="recover_prompt",
                )
            )
            if plan_id:
                actions.append(
                    StructuredAction(
                        label="先回到当前计划看上下文",
                        type="switch_plan",
                        payload={"plan_id": plan_id},
                        style="secondary",
                        stage=stage,
                        reason_key="recover_plan_context",
                    )
                )
            actions.append(
                StructuredAction(
                    label="去任务页看当前状态",
                    type="route",
                    payload={"route": "/tasks"},
                    style="ghost",
                    stage=stage,
                    reason_key="open_tasks_overview",
                )
            )
            return actions

        if stage == "completed":
            actions.append(
                StructuredAction(
                    label="帮我总结这次结果",
                    type="prompt",
                    payload={"prompt": "帮我总结一下这次结果，并告诉我接下来怎么承接"},
                    style="primary",
                    stage=stage,
                    reason_key="summarize_outcome",
                )
            )
            actions.append(
                StructuredAction(
                    label="打开任务页继续承接",
                    type="route",
                    payload={"route": "/tasks"},
                    style="secondary",
                    stage=stage,
                    reason_key="route_tasks",
                )
            )
            if plan_id:
                actions.append(
                    StructuredAction(
                        label="切回这个计划继续",
                        type="switch_plan",
                        payload={"plan_id": plan_id},
                        style="ghost",
                        stage=stage,
                        reason_key="switch_plan_after_completion",
                    )
                )
            return actions

        if stage == "reflect":
            actions.append(
                StructuredAction(
                    label="回顾一下这个过程",
                    type="prompt",
                    payload={"prompt": "回顾一下这个过程，告诉我哪里做得好、哪里还可以优化"},
                    style="primary",
                    stage=stage,
                    reason_key="reflect_process",
                )
            )
            actions.append(
                StructuredAction(
                    label="根据这次表现更新计划",
                    type="prompt",
                    payload={"prompt": "根据这次表现，帮我更新接下来的计划节奏"},
                    style="secondary",
                    stage=stage,
                    reason_key="update_plan_from_reflection",
                )
            )
            actions.append(
                StructuredAction(
                    label="去今日复盘页看看",
                    type="route",
                    payload={"route": "/review?mode=today"},
                    style="ghost",
                    stage=stage,
                    reason_key="open_review",
                )
            )
            return actions

        actions.append(
            StructuredAction(
                label="继续问下去",
                type="prompt",
                payload={"prompt": "继续围绕这个问题展开，但优先告诉我最关键的下一步"},
                style="primary",
                stage=stage,
                reason_key="continue_conversation",
            )
        )
        if "清单" in full_response or "总结" in full_response:
            actions.append(
                StructuredAction(
                    label="把它改成执行清单",
                    type="prompt",
                    payload={"prompt": "把刚才的内容改写成一个可以直接执行的清单"},
                    style="secondary",
                    stage=stage,
                    reason_key="convert_to_checklist",
                )
            )
        elif chat_mode == "deep_analysis":
            actions.append(
                StructuredAction(
                    label="只保留结论和风险",
                    type="prompt",
                    payload={"prompt": "只保留结论、关键依据和风险，帮我压缩成短版"},
                    style="secondary",
                    stage=stage,
                    reason_key="compress_analysis",
                )
            )
        else:
            actions.append(
                StructuredAction(
                    label="帮我改成可执行步骤",
                    type="prompt",
                    payload={"prompt": "把刚才的回答改成可执行步骤"},
                    style="secondary",
                    stage=stage,
                    reason_key="convert_to_actions",
                )
            )
        actions.append(
            StructuredAction(
                label="去任务页看看当前安排",
                type="route",
                payload={"route": "/tasks"},
                style="ghost",
                stage=stage,
                reason_key="route_tasks_from_explore",
            )
        )
        return actions

    def _default_next_action_labels(
        self,
        *,
        chat_mode: str,
        executable_plan: Any | None,
        plan_context: dict[str, Any] | None,
        profile: PresentationProfile,
        full_response: str,
    ) -> list[str]:
        actions: list[str] = []
        if chat_mode == "study_plan":
            actions.extend(["确认今天先做哪一步", "把计划拆成今天/本周两个层级", "根据你的时间再压缩一次"])
        elif chat_mode == "error_diagnosis":
            actions.extend(["补充题目或截图让我定位证据", "先做一个针对性修复练习", "把错因整理进错题本"])
        elif chat_mode == "deep_analysis":
            actions.extend(["补充一个具体约束让我继续深入", "只提炼执行结论", "让我给出反方观点和风险"])
        elif chat_mode.startswith("expert::") or chat_mode == "expert_auto":
            actions.extend(["查看专家协作依据", "指定另一个专家复核", "把结论改写成执行清单"])
        else:
            actions.extend(["继续追问细节", "让我改成执行清单", "让我结合当前计划继续推进"])

        if executable_plan is not None and getattr(executable_plan, "tool_calls", None):
            actions.insert(0, "确认是否执行我建议的动作")
        if plan_context and plan_context.get("plan_id"):
            actions.append("把结果绑定到当前计划")
        if "总结" in full_response or "清单" in full_response:
            actions.append("把这轮结果保存到历史会话")

        deduped: list[str] = []
        seen: set[str] = set()
        for action in actions:
            if action not in seen:
                deduped.append(action)
                seen.add(action)
            if len(deduped) >= profile.next_action_limit:
                break
        return deduped

    def _task_candidates(self, *, plan_context: dict[str, Any] | None, final_state: Any) -> list[dict[str, Any]]:
        context_data = getattr(final_state, "context_data", {}) or {}
        raw_tasks = (
            (plan_context or {}).get("task_summaries")
            or (plan_context or {}).get("recent_tasks")
            or (context_data.get("plan_context") or {}).get("task_summaries")
            or []
        )
        candidates: list[dict[str, Any]] = []
        if not isinstance(raw_tasks, list):
            return candidates
        for item in raw_tasks:
            if not isinstance(item, dict):
                continue
            task_id = str(item.get("task_id") or item.get("id") or "").strip()
            if not task_id:
                continue
            candidates.append(
                {
                    "task_id": task_id,
                    "title": str(item.get("title") or "当前任务").strip() or "当前任务",
                    "status": str(item.get("status") or "").strip().lower(),
                    "route": f"/tasks/{task_id}",
                    "execute_route": f"/tasks/{task_id}/execute",
                    "focus_route": f"/focus/mindfulness/{task_id}",
                }
            )
        status_priority = {"in_progress": 0, "pending": 1, "todo": 2, "not_started": 3, "completed": 9}
        candidates.sort(key=lambda item: status_priority.get(item["status"], 5))
        return candidates

    def _open_task_action(self, task: dict[str, Any], *, stage: str, style: str) -> StructuredAction:
        return StructuredAction(
            label=f"打开「{task['title']}」",
            type="open_task",
            payload={"task_id": task["task_id"], "route": task["execute_route"]},
            style=style,
            stage=stage,
            reason_key="open_primary_task",
        )

    def _start_focus_action(self, task: dict[str, Any], *, stage: str, style: str) -> StructuredAction:
        return StructuredAction(
            label=f"开始专注「{task['title']}」",
            type="start_focus",
            payload={"task_id": task["task_id"], "route": task["focus_route"]},
            style=style,
            stage=stage,
            reason_key="start_focus",
        )

    def _finalize_actions(self, *, actions: list[StructuredAction], limit: int) -> list[StructuredAction]:
        deduped: list[StructuredAction] = []
        seen: set[str] = set()
        high_friction_used = False
        for action in actions:
            key = json.dumps(
                {
                    "label": action.label,
                    "type": action.type,
                    "payload": action.payload,
                },
                ensure_ascii=False,
                sort_keys=True,
            )
            if key in seen:
                continue
            if action.type in HIGH_FRICTION_ACTION_TYPES:
                if high_friction_used:
                    continue
                high_friction_used = True
            seen.add(key)
            deduped.append(action)
            if len(deduped) >= limit:
                break
        if deduped and not any(action.style == "primary" for action in deduped):
            first = deduped[0]
            deduped[0] = StructuredAction(
                label=first.label,
                type=first.type,
                payload=first.payload,
                style="primary",
                stage=first.stage,
                reason_key=first.reason_key,
            )
        return deduped

    def _retry_options(
        self,
        *,
        completion_state: str,
        include_references: bool,
        has_files: bool,
        profile: PresentationProfile,
        recovery_kind: str,
    ) -> list[Any]:
        options = list(profile.default_retry_options)
        if completion_state in {"partial", "blocked", "needs_input"}:
            options.insert(0, "补充信息后重试")
        if recovery_kind in {"tool_failure", "partial_tool_failure"}:
            options.insert(0, "换一种执行方式")
        if recovery_kind == "provider_unavailable":
            options.insert(0, "稍后重试")
        if recovery_kind == "timeout":
            options.insert(0, "先看当前结果")
        if recovery_kind == "expert_degraded":
            options.insert(0, "指定专家复核")
        if include_references or has_files:
            options.append("去掉引用限制再试")
        deduped: list[str] = []
        for option in options:
            if option not in deduped:
                deduped.append(option)
        trimmed = deduped[:3]
        if not settings.ENABLE_STRUCTURED_NEXT_ACTIONS:
            return trimmed
        return [
            StructuredAction(
                label=option,
                type="prompt",
                payload={"prompt": option},
                style="secondary",
                stage="blocked",
                reason_key="retry_option",
            ).to_dict()
            for option in trimmed
        ]

    def _memory_updates(self, final_state: Any, user_context_payload: dict[str, Any] | None) -> dict[str, Any]:
        highlights: list[str] = []
        adaptation_records = self._adaptation_records(final_state)
        preference_learnings = self._preference_learnings(final_state)
        context_data = getattr(final_state, "context_data", {}) or {}
        evolution_highlights = list(context_data.get("evolution_highlights") or [])
        plan_review = context_data.get("plan_review") if isinstance(context_data.get("plan_review"), dict) else {}
        plan_reasoning_summary = str((plan_review or {}).get("reasoning_summary") or "").strip()
        plan_reasoning_details = (plan_review or {}).get("reasoning_details")
        if not isinstance(plan_reasoning_details, list):
            plan_reasoning_details = []
        if context_data.get("plan_review"):
            highlights.append("已记录本轮计划审查状态")
        if context_data.get("pending_review_action_id"):
            highlights.append("已等待你的确认后再继续执行")
        if (user_context_payload or {}).get("preference_version"):
            highlights.append("本轮回答已按你的偏好配置生成")
        for record in adaptation_records:
            message = str(record.get("user_facing_message") or "").strip()
            if message:
                highlights.append(message)
        for record in preference_learnings:
            message = str(record.get("user_facing_message") or "").strip()
            if message:
                highlights.append(message)
        for message in evolution_highlights:
            message = str(message or "").strip()
            if message:
                highlights.append(message)
        progress_snapshot = context_data.get("progress_snapshot")
        if isinstance(progress_snapshot, dict):
            for item in (progress_snapshot.get("highlights") or [])[:2]:
                label = str(item or "").strip()
                if label:
                    highlights.append(label)
        deduped: list[str] = []
        for item in highlights:
            if item and item not in deduped:
                deduped.append(item)
        return {
            "highlights": deduped[:3],
            "adaptation_records": adaptation_records,
            "preference_learnings": preference_learnings,
            "progress_snapshot": progress_snapshot if isinstance(progress_snapshot, dict) else None,
            "plan_reasoning_summary": plan_reasoning_summary,
            "plan_reasoning_details": plan_reasoning_details[:3],
        }

    def _adaptation_records(self, final_state: Any) -> list[dict[str, Any]]:
        context_data = getattr(final_state, "context_data", {}) or {}
        raw = context_data.get("adaptation_records") or context_data.get("evolution_records") or []
        records: list[dict[str, Any]] = []
        if not isinstance(raw, list):
            return records
        for item in raw:
            if isinstance(item, dict):
                records.append(item)
        return records[:3]

    def _preference_learnings(self, final_state: Any) -> list[dict[str, Any]]:
        context_data = getattr(final_state, "context_data", {}) or {}
        raw = context_data.get("preference_learnings") or []
        records: list[dict[str, Any]] = []
        if not isinstance(raw, list):
            return records
        for item in raw:
            if isinstance(item, dict):
                records.append(item)
        return records[:3]

    def _ux_evolution(self, *, final_state: Any, memory_updates: dict[str, Any]) -> dict[str, Any] | None:
        adaptation_records = memory_updates.get("adaptation_records") or []
        preference_learnings = memory_updates.get("preference_learnings") or []
        highlights = memory_updates.get("highlights") or []
        progress_snapshot = memory_updates.get("progress_snapshot")
        plan_reasoning_summary = str(memory_updates.get("plan_reasoning_summary") or "").strip()
        plan_reasoning_details = memory_updates.get("plan_reasoning_details") or []
        if not adaptation_records and not preference_learnings and not progress_snapshot and not plan_reasoning_summary:
            return None
        headline = "系统正在根据你的反馈继续调整"
        summary = (
            str(highlights[0])
            if highlights
            else "我会把这轮新学到的偏好和调整继续用于后续对话。"
        )
        evolution_kind = "adaptation"
        if isinstance(progress_snapshot, dict) and (progress_snapshot.get("highlights") or []):
            headline = "这是你最近一段时间最值得看到的进步"
            summary = str((progress_snapshot.get("highlights") or [summary])[0])
            evolution_kind = "progress_snapshot"
        elif plan_reasoning_summary:
            headline = "这次计划这样安排，是有依据的"
            summary = plan_reasoning_summary
            evolution_kind = "plan_reasoning"
        return {
            "evolution_kind": evolution_kind,
            "headline": headline,
            "summary": summary,
            "adaptation_records": adaptation_records,
            "preference_learnings": preference_learnings,
            "highlights": highlights,
            "progress_snapshot": progress_snapshot,
            "reasoning_summary": plan_reasoning_summary,
            "reasoning_details": plan_reasoning_details,
        }

    def _dual_core_mode(self, final_state: Any) -> str:
        context_data = getattr(final_state, "context_data", {}) or {}
        decision = context_data.get("dual_core_decision") or {}
        mode = str((decision or {}).get("mode") or "").strip()
        if mode == "execution_first":
            return "execution"
        if mode == "cognitive_first":
            return "cognitive"
        return "balanced"

    def _dual_core_reason(self, final_state: Any) -> str:
        context_data = getattr(final_state, "context_data", {}) or {}
        decision = context_data.get("dual_core_decision") or {}
        return str((decision or {}).get("reason") or "").strip()

    def _orchestration_summary(
        self,
        *,
        final_state: Any,
        chat_mode: str,
        executable_plan: Any | None,
    ) -> dict[str, Any] | None:
        context_data = getattr(final_state, "context_data", {}) or {}
        trace = context_data.get("orchestration_trace")
        if isinstance(trace, str):
            try:
                trace = json.loads(trace)
            except Exception:
                trace = None
        if not isinstance(trace, dict):
            return None

        mode = str(trace.get("mode") or chat_mode).strip()
        agents_used = trace.get("agents") or []
        if not agents_used and executable_plan is not None:
            agents_used = getattr(executable_plan, "agents_involved", []) or []
        agents_used = [str(agent).strip() for agent in agents_used if str(agent).strip()]

        persona_step = trace.get("persona_step") or {}
        persona_meta = persona_step.get("metadata") if isinstance(persona_step, dict) else {}
        persona_meta = persona_meta if isinstance(persona_meta, dict) else {}
        persona_highlights: list[str] = []
        preferred_task_size = persona_meta.get("preferred_task_size")
        if preferred_task_size:
            persona_highlights.append(f"偏好 {preferred_task_size} 任务")
        max_session_minutes = persona_meta.get("max_session_minutes")
        if max_session_minutes:
            persona_highlights.append(f"最大专注 {max_session_minutes} 分钟")
        time_multiplier = persona_meta.get("time_multiplier")
        if isinstance(time_multiplier, (int, float)):
            persona_highlights.append(f"时间倍率 {float(time_multiplier):.2f}")
        if persona_meta.get("require_warmup_task"):
            persona_highlights.append("需要热身任务")

        review_step = trace.get("review_step") or {}
        review_meta = review_step.get("metadata") if isinstance(review_step, dict) else {}
        review_meta = review_meta if isinstance(review_meta, dict) else {}
        review_result = review_meta.get("decision")
        if review_result is None and isinstance(review_step, dict):
            review_result = review_step.get("decision")

        return {
            "mode": mode,
            "agents_used": agents_used,
            "persona_highlights": persona_highlights,
            "review_result": review_result,
        }

    def _reference_scope(self, include_references: bool, file_ids: list[str]) -> str:
        if include_references and file_ids:
            return "file_only"
        if include_references:
            return "mixed"
        return "none"

    def _evidence_summary(self, include_references: bool, file_ids: list[str], selected_experts: list[str]) -> str:
        if include_references and file_ids:
            return "这轮回答优先基于你上传的材料与相关引用。"
        if selected_experts:
            return "这轮回答综合了专家协作结果，来源摘要可展开查看。"
        return "这轮回答主要基于当前上下文、历史对话和系统策略生成。"

    def _continuity_banner(
        self,
        *,
        conversation_context: dict[str, Any] | None,
        plan_context: dict[str, Any] | None,
        final_state: Any,
    ) -> dict[str, Any] | None:
        if plan_context and plan_context.get("plan_id"):
            plan_name = plan_context.get("plan_name") or plan_context.get("plan_title") or "当前计划"
            return {
                "title": "继续当前节奏",
                "message": f"我会继续围绕 {plan_name} 帮你推进，不用从头再讲。",
                "kind": "plan_context",
            }
        messages = (conversation_context or {}).get("messages") or []
        if len(messages) >= 2:
            return {
                "title": "延续上轮对话",
                "message": "我会接着上一轮的目标和下一步继续回答。",
                "kind": "conversation_context",
            }
        context_data = getattr(final_state, "context_data", {}) or {}
        if context_data.get("plan_review"):
            return {
                "title": "等待你的选择",
                "message": "上轮已经生成了计划审查结果，这轮会沿着你的反馈继续。",
                "kind": "pending_review",
            }
        return None

    def _session_adaptation(self, final_state: Any) -> dict[str, Any] | None:
        context_data = getattr(final_state, "context_data", {}) or {}
        signal = context_data.get("session_feedback_signal")
        if not isinstance(signal, dict):
            return None
        adaptation = context_data.get("session_adaptation")
        return {
            "signal_type": str(signal.get("signal_type") or ""),
            "confidence": signal.get("confidence"),
            "trigger_text": str(signal.get("trigger_text") or ""),
            "applies_adaptation": bool(signal.get("applies_adaptation")),
            "visible_hint": str(signal.get("visible_hint") or ""),
            "applied_strategy": (
                str((adaptation or {}).get("applied_strategy") or "")
                if isinstance(adaptation, dict)
                else ""
            ),
        }

    def _mode_explanation(self, *, chat_mode: str, profile: PresentationProfile, selected_experts: list[str]) -> dict[str, Any]:
        description = profile.companion_frame
        if selected_experts:
            description += f" 当前已激活：{'、'.join(selected_experts[:3])}。"
        workflow = get_workflow_config(chat_mode)
        if workflow and workflow.collaboration_agents:
            description += f" 本模式会按 {workflow.collaboration_mode} 协作推进。"
        return {
            "mode": chat_mode,
            "label": profile.mode_label,
            "description": description,
        }

    def _collaboration_summary(self, final_state: Any, selected_experts: list[str]) -> dict[str, Any] | None:
        context_data = getattr(final_state, "context_data", {}) or {}
        metadata = context_data.get("expert_routing_metadata")
        if not isinstance(metadata, dict) and not selected_experts:
            return None
        return {
            "selected_experts": selected_experts,
            "routing_strategy": (metadata or {}).get("routing_strategy") or context_data.get("routing_strategy"),
            "fallback_reason": (metadata or {}).get("fallback_reason") or context_data.get("fallback_reason"),
            "route_confidence": (metadata or {}).get("route_confidence") or context_data.get("route_confidence"),
        }

    def _extract_user_id(self, *, user_context_payload: dict[str, Any] | None, final_state: Any) -> str | None:
        if isinstance(user_context_payload, dict):
            user_context = user_context_payload.get("user_context")
            if isinstance(user_context, dict):
                user_id = str(user_context.get("user_id") or "").strip()
                if user_id:
                    return user_id
        context_data = getattr(final_state, "context_data", {}) or {}
        user_id = str(context_data.get("user_id") or "").strip()
        return user_id or None

    def _message_has_negative_signal(self, user_message: str) -> bool:
        compact = str(user_message or "").strip().lower()
        return any(token in compact for token in NEGATIVE_USER_SIGNAL_KEYWORDS)


ux_envelope_builder = UXEnvelopeBuilder()
