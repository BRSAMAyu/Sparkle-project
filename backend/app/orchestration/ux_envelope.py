from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from app.orchestration.chat_modes import CHAT_MODE_STANDARD
from app.orchestration.mode_workflow_config import get_workflow_config


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
}


class UXEnvelopeBuilder:
    def build(
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
        chat_mode = str((getattr(final_state, "context_data", {}) or {}).get("chat_mode") or CHAT_MODE_STANDARD)
        profile = self._get_profile(chat_mode)
        selected_experts = self._selected_experts(final_state)

        ux_turn = {
            "intent_summary": self._intent_summary(user_message, chat_mode),
            "mode_label": profile.mode_label,
            "companion_frame": profile.companion_frame,
            "dual_core_mode": self._dual_core_mode(final_state),
            "mode_reason": self._dual_core_reason(final_state),
        }

        completion_state = self._completion_state(final_state, executable_plan, execution_validation)
        confidence_band = self._confidence_band(executable_plan, route_decision, execution_validation)
        ux_result = {
            "answer_kind": self._answer_kind(profile, executable_plan, chat_mode),
            "confidence_band": confidence_band,
            "completion_state": completion_state,
            "headline": self._result_headline(chat_mode, completion_state, selected_experts),
            "first_screen_focus": profile.first_screen_focus,
            "why_this_answer": self._why_this_answer(
                chat_mode=chat_mode,
                include_references=include_references,
                selected_experts=selected_experts,
                execution_validation=execution_validation,
                route_decision=route_decision,
            ),
        }
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
        ux_result.update(recovery_state)

        memory_updates = self._memory_updates(final_state, user_context_payload)
        ux_followthrough = {
            "next_actions_title": profile.next_actions_title,
            "next_actions": self._next_actions(
                chat_mode=chat_mode,
                executable_plan=executable_plan,
                plan_context=plan_context,
                profile=profile,
                full_response=full_response,
            ),
            "retry_options": self._retry_options(
                completion_state=completion_state,
                include_references=include_references,
                has_files=bool(file_ids),
                profile=profile,
                recovery_kind=recovery_state["failure_kind"],
            ),
            "recovery_message": recovery_state["failure_message"],
            "memory_updates": memory_updates,
        }

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

        return envelope

    def to_metadata_map(self, envelope: dict[str, dict[str, Any]]) -> dict[str, str]:
        return {
            key: json.dumps(value, ensure_ascii=False)
            for key, value in envelope.items()
            if value
        }

    def _get_profile(self, chat_mode: str) -> PresentationProfile:
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

    def _completion_state(self, final_state: Any, executable_plan: Any | None, execution_validation: dict[str, Any] | None) -> str:
        if execution_validation:
            failed = execution_validation.get("failed_steps") or execution_validation.get("failed_tool_calls") or 0
            total = execution_validation.get("total_steps") or execution_validation.get("total_tool_calls") or 0
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
        if execution_validation and (execution_validation.get("failed_steps") or execution_validation.get("failed_tool_calls")):
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
        if execution_validation and execution_validation.get("failed_steps"):
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
            if execution_validation and (
                execution_validation.get("failed_steps") or execution_validation.get("failed_tool_calls")
            ):
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
        if execution_validation and (
            execution_validation.get("failed_steps") or execution_validation.get("failed_tool_calls")
        ):
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

    def _retry_options(
        self,
        *,
        completion_state: str,
        include_references: bool,
        has_files: bool,
        profile: PresentationProfile,
        recovery_kind: str,
    ) -> list[str]:
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
        return deduped[:3]

    def _memory_updates(self, final_state: Any, user_context_payload: dict[str, Any] | None) -> dict[str, Any]:
        highlights: list[str] = []
        adaptation_records = self._adaptation_records(final_state)
        preference_learnings = self._preference_learnings(final_state)
        context_data = getattr(final_state, "context_data", {}) or {}
        evolution_highlights = list(context_data.get("evolution_highlights") or [])
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
        deduped: list[str] = []
        for item in highlights:
            if item and item not in deduped:
                deduped.append(item)
        return {
            "highlights": deduped[:3],
            "adaptation_records": adaptation_records,
            "preference_learnings": preference_learnings,
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
        if not adaptation_records and not preference_learnings:
            return None
        headline = "系统正在根据你的反馈继续调整"
        summary = (
            str(highlights[0])
            if highlights
            else "我会把这轮新学到的偏好和调整继续用于后续对话。"
        )
        return {
            "headline": headline,
            "summary": summary,
            "adaptation_records": adaptation_records,
            "preference_learnings": preference_learnings,
            "highlights": highlights,
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
            plan_name = plan_context.get("plan_name") or "当前计划"
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


ux_envelope_builder = UXEnvelopeBuilder()
