from __future__ import annotations

import inspect
import json
import re
from typing import Any, Awaitable, Callable

from loguru import logger

from app.aurora.runtime_v1.dashboard import DashboardReadout, canonicalize_runtime_domain
from app.aurora.runtime_v1.decision_loop import (
    AuroraDecision,
    build_standard_layer_contract,
    describe_standard_layer_tokens,
)
from app.aurora.runtime_v1.state import merge_activity_profile_payload, merge_expression_settings
from app.core.agent_profiles import AgentRole, TaskType
from app.services.llm_service import get_configured_llm_service

LLMFactory = Callable[[], Any | Awaitable[Any]]

_TERMINAL_PUNCTUATION = ("。", "！", "？", ".", "!", "?")
_MID_SENTENCE_ENDINGS = ("，", ",", "：", ":", "；", ";", "、", "—", "-", "（", "(")
_CONTINUATION_PREFIXES = (
    "并且",
    "而且",
    "同时",
    "然后",
    "再",
    "另外",
    "这样",
    "所以",
    "因此",
    "但",
    "但是",
    "不过",
)
_DOMAIN_FALLBACK_QUESTIONS = {
    "goal": "我们先把目标钉稳：你这次最想达到的结果是什么？",
    "scope": "我们先补齐范围：这次主要考哪些章节、题型，或者老师重点抓哪几块？",
    "baseline": "我还想摸清你的基础：这些内容里你现在最熟和最虚的是哪几块？",
    "time": "再补一个时间约束就能更稳：接下来这几天你每天大概能拿出多少时间？",
    "motivation": "最后一个问题：这次考试对你来说意味着什么？是必须过、想拿高分，还是有什么更具体的压力？",
}


class ChatLayerAdapter:
    """Translate Aurora decisions into short user-visible messages."""

    def __init__(
        self,
        *,
        llm_factory: LLMFactory | None = None,
        temperature: float = 0.45,
    ) -> None:
        self.llm_factory = llm_factory or self._default_llm_factory
        self.temperature = temperature

    async def render(self, decision: AuroraDecision, readout: DashboardReadout) -> list[str]:
        if decision.action in {"wait", "drop_thread"}:
            return []

        prompt = self._build_render_prompt(decision, readout)
        wake_policy = self._wake_policy(readout)
        multimessage_setting = wake_policy.get("multimessage_allowed")
        max_messages = 3 if multimessage_setting is None or bool(multimessage_setting) else 1
        try:
            llm = await self._resolve_llm()
            raw = await llm.chat_json(
                prompt,
                temperature=self.temperature,
                max_tokens=self._max_tokens_for_wake(wake_policy),
            )
            messages = self._extract_messages(raw)
        except Exception as exc:
            logger.warning("Aurora chat adapter fell back after LLM failure: {}", exc)
            messages = []

        messages = self._sanitize_messages(messages, max_messages=max_messages)
        if messages:
            return messages
        fallback = await self._fallback_messages(
            decision=decision, readout=readout, reason="empty_or_invalid_llm_output"
        )
        return self._sanitize_messages(fallback, max_messages=max_messages)

    def _build_prompt(self, decision: AuroraDecision, readout: DashboardReadout) -> list[dict[str, str]]:
        return self._build_render_prompt(decision, readout)

    def _build_render_prompt(self, decision: AuroraDecision, readout: DashboardReadout) -> list[dict[str, str]]:
        effective_profile = self._effective_activity_profile(decision, readout)
        expression_controls = merge_expression_settings(effective_profile.get("expression"))
        standard_layer_contract = build_standard_layer_contract(decision, readout)
        wake_policy = self._wake_policy(readout)
        multimessage_setting = wake_policy.get("multimessage_allowed")
        multimessage_allowed = True if multimessage_setting is None else bool(multimessage_setting)
        message_count_instruction = (
            "Write 1-3 short, natural, non-overlapping messages for the user. "
            if multimessage_allowed
            else "Write exactly 1 short, natural message for the user. "
        )
        system = (
            "You are Sparkle's chat layer adapter. Aurora has already made the cognitive decision. "
            f"{message_count_instruction}"
            "Every message must stand on its own as a complete thought. Do not split one sentence across messages. "
            "Adjacent messages must add different value instead of paraphrasing each other. "
            "Do not expose internal decision fields. "
            "Follow expression_controls first when calibrating tone; treat the legacy conversation_style only as a coarse fallback hint. "
            "Honor teaching_strategy when wording the next move: concept_first means lead with a concise concept scaffold "
            "before practice, problem_first means move directly into practice, worked_example_first means start with a "
            "solved example, retrieval_practice means use recall or mini-test language, interleaving means mix nearby "
            "types, spaced_review means briefly resurface earlier material, and error_analysis_required means explicitly "
            "name the mistake-diagnosis step before more drills. drop_low_roi_topics means skip low-yield detours, "
            "and new_topic_allowed=false means do not introduce fresh chapters or new topic walkthroughs. "
            "The standard_layer_contract is a hard contract, not a suggestion. You MUST satisfy every item in "
            "must_include, MUST avoid every item in must_not_include, and MUST stay within max_response_length. "
            "If any other hint conflicts with standard_layer_contract, follow the contract. "
            "Stay task-level and avoid clinical, personality, or social-identity inference. "
            'Return JSON: {"messages": ["..."]}.'
        )
        user = {
            "surface": readout.surface,
            "style": effective_profile.get("conversation_style"),
            "activity_profile": effective_profile,
            "teaching_strategy": self._teaching_strategy(effective_profile),
            "expression_controls": expression_controls,
            "expression_instruction": self._build_expression_instruction(expression_controls),
            "standard_layer_contract": standard_layer_contract,
            "standard_layer_contract_instruction": self._build_standard_layer_instruction(standard_layer_contract),
            "standard_layer_contract_semantics": describe_standard_layer_tokens(
                list(standard_layer_contract.get("must_include") or [])
                + list(standard_layer_contract.get("must_not_include") or [])
            ),
            "wake_policy": wake_policy,
            "user_message": readout.user_message,
            "decision": decision.to_payload(),
            "dashboard_digest": {
                "cold_start_context": readout.cold_start_context,
                "informational_tensions": readout.informational_tensions,
                "latent_threads": readout.latent_threads,
                "covered_domains": readout.covered_domains,
                "missing_domains": readout.missing_domains,
                "recently_asked_domains": readout.recently_asked_domains,
                "sprint_policy_summary": readout.sprint_policy_summary,
                "explicit_user_constraints": readout.explicit_user_constraints,
                "latent_thread_recovery_candidates": readout.latent_thread_recovery_candidates,
                "exam_sprint_policy": readout.exam_sprint_policy,
                "checkpoint_state": readout.checkpoint_state,
            },
        }
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(user, ensure_ascii=False, default=str)},
        ]

    def _effective_activity_profile(self, decision: AuroraDecision, readout: DashboardReadout) -> dict[str, Any]:
        profile = merge_activity_profile_payload(readout.activity_profile, {})
        return merge_activity_profile_payload(profile, decision.harness_updates or {})

    def _build_expression_instruction(self, expression: dict[str, float]) -> str:
        tone_warmth = float(expression.get("tone_warmth", 0.0))
        directness = float(expression.get("directness", 0.0))
        brevity = float(expression.get("brevity", 0.0))
        friendliness = float(expression.get("friendliness", 0.0))
        challenge_intensity = float(expression.get("challenge_intensity", 0.0))

        guidance: list[str] = [
            "Primary expression control.",
            f"tone_warmth={tone_warmth:.2f}, directness={directness:.2f}, brevity={brevity:.2f}, friendliness={friendliness:.2f}, challenge_intensity={challenge_intensity:.2f}.",
        ]

        if directness >= 0.7:
            guidance.append("Lead with the answer, decision, or next step instead of easing in slowly.")
        elif directness <= 0.35:
            guidance.append("Use softer transitions and invitational phrasing instead of blunt directives.")
        else:
            guidance.append("Balance clarity with a light amount of framing.")

        if brevity >= 0.7:
            guidance.append("Keep it concise and cut filler, hedging, and repeated reassurance.")
        elif brevity <= 0.35:
            guidance.append("Add a little context or explanation when it helps the user stay oriented.")

        if tone_warmth >= 0.7:
            guidance.append("Sound noticeably warm and emotionally containing.")
        elif tone_warmth <= 0.35:
            guidance.append("Keep warmth light and do not over-cushion the message.")

        if friendliness >= 0.7:
            guidance.append("Let the tone feel friendly and companionable.")
        elif friendliness <= 0.35:
            guidance.append("Stay neutral-professional, not chatty.")

        if tone_warmth <= 0.35 and friendliness <= 0.4 and directness >= 0.7:
            guidance.append("Do not add extra encouragement or praise unless it materially helps.")

        if challenge_intensity >= 0.7:
            guidance.append(
                "Increase action pressure a bit: move the user toward a concrete next move or clear constraint."
            )
        elif challenge_intensity <= 0.35:
            guidance.append("Reduce pressure: support first, then invite the next step gently.")

        return " ".join(guidance)

    def _build_standard_layer_instruction(self, contract: dict[str, Any]) -> str:
        response_type = str(contract.get("response_type") or "general_chat")
        max_response_length = str(contract.get("max_response_length") or "normal")
        length_hint = {
            "brief": "~100 Chinese characters total",
            "normal": "~300 Chinese characters total",
            "extended": "~600 Chinese characters total",
        }.get(max_response_length, "~300 Chinese characters total")
        must_include = list(contract.get("must_include") or [])
        must_not_include = list(contract.get("must_not_include") or [])
        semantics = describe_standard_layer_tokens(must_include + must_not_include)
        include_text = "; ".join(f"{token}: {semantics.get(token, token)}" for token in must_include) or "none"
        exclude_text = "; ".join(f"{token}: {semantics.get(token, token)}" for token in must_not_include) or "none"
        return (
            f"response_type={response_type}. "
            f"max_response_length={max_response_length} ({length_hint}). "
            f"MUST include: {include_text}. "
            f"MUST NOT include: {exclude_text}."
        )

    def _extract_messages(self, raw: Any) -> list[str]:
        if isinstance(raw, dict):
            value = raw.get("messages")
            if isinstance(value, list):
                return [str(item) for item in value]
            if isinstance(raw.get("message"), str):
                return [str(raw["message"])]
        if isinstance(raw, list):
            return [str(item) for item in raw]
        return []

    def _sanitize_messages(self, messages: list[str], *, max_messages: int = 3) -> list[str]:
        merged = self._merge_split_messages(messages)
        cleaned: list[str] = []
        seen: set[str] = set()
        for message in merged:
            text = " ".join(str(message or "").split()).strip()
            if not text or text in seen:
                continue
            if any(self._semantically_overlaps(text, existing) for existing in cleaned):
                continue
            seen.add(text)
            cleaned.append(text[:260])
            if len(cleaned) >= max(1, max_messages):
                break
        return cleaned

    def _merge_split_messages(self, messages: list[str]) -> list[str]:
        merged: list[str] = []
        for raw in messages:
            text = " ".join(str(raw or "").split()).strip()
            if not text:
                continue
            if merged and self._should_merge_messages(merged[-1], text):
                merged[-1] = self._join_messages(merged[-1], text)
            else:
                merged.append(text)
        return merged

    def _should_merge_messages(self, previous: str, current: str) -> bool:
        if previous.endswith(_MID_SENTENCE_ENDINGS):
            return True
        if not previous.endswith(_TERMINAL_PUNCTUATION):
            return True
        return False

    def _join_messages(self, previous: str, current: str) -> str:
        separator = "" if self._prefer_compact_join(previous, current) else " "
        return f"{previous.rstrip()}{separator}{current.lstrip()}"

    def _prefer_compact_join(self, previous: str, current: str) -> bool:
        if not previous or not current:
            return True
        return bool(re.search(r"[\u4e00-\u9fff]$", previous) or re.match(r"^[\u4e00-\u9fff]", current))

    def _semantically_overlaps(self, current: str, existing: str) -> bool:
        current_norm = self._semantic_normalize(current)
        existing_norm = self._semantic_normalize(existing)
        if not current_norm or not existing_norm:
            return False
        if current_norm == existing_norm or current_norm in existing_norm or existing_norm in current_norm:
            return True
        current_ngrams = self._char_ngrams(current_norm)
        existing_ngrams = self._char_ngrams(existing_norm)
        if not current_ngrams or not existing_ngrams:
            return False
        intersection = len(current_ngrams.intersection(existing_ngrams))
        similarity = intersection / max(min(len(current_ngrams), len(existing_ngrams)), 1)
        return similarity >= 0.82

    def _semantic_normalize(self, text: str) -> str:
        return re.sub(r"[^\w\u4e00-\u9fff]+", "", text.lower())

    def _char_ngrams(self, text: str) -> set[str]:
        if len(text) <= 2:
            return {text}
        return {text[index : index + 2] for index in range(len(text) - 1)}

    async def _fallback_messages(
        self,
        decision: AuroraDecision,
        readout: DashboardReadout,
        *,
        reason: str | None = None,
    ) -> list[str]:
        contract = build_standard_layer_contract(decision, readout)
        response_type = str(contract.get("response_type") or "general_chat")
        if response_type == "task_help":
            return [
                "我们先走 1 个短例子，把关键步骤顺下来。",
                "然后做 3 个同型小练习，先自己答。",
                "做完把答案或卡住的那一步发我，我来检查。",
            ]
        if response_type == "emotional_support":
            return ["这几次卡住确实会很难受。我们先只做下一步：把刚才最卡的一题或一步发我，我陪你拆开。"]
        if response_type == "diagnostic":
            return ["我们先定位这次错在什么地方，再只修一个关键断点。把你刚才做错的那一步发我。"]
        if response_type == "calibration":
            return ["我先不假装自己已经判断准了。先帮我确认一个点：你现在更卡在时间不够，还是卡在方法没抓稳？"]
        if response_type == "plan_discussion":
            return ["这轮我先只收紧当前计划，不整周重排。眼下最需要调整的是哪一块：时间、顺序，还是难度？"]
        target_domain = self._target_domain(decision)
        if decision.action == "soft_return_topic":
            label = self._domain_label(target_domain)
            if label:
                return [
                    "我先接住你刚刚这句。",
                    f"等这个点处理完，我们再自然带回还没补齐的{label}。",
                ]
            return [
                "我先接住你刚刚这句。",
                "等这个点处理完，我会自然带回刚才还缺的那块信息。",
            ]
        if decision.modeling_complete:
            return ["我已经抓到够用的轮廓了。接下来可以直接进入更贴合你的规划。"]
        if readout.surface == "aurora_checkpoint":
            return ["这个检查点我先记下。我们只抓最关键的偏差，别把复盘变成新的负担。"]
        if target_domain in _DOMAIN_FALLBACK_QUESTIONS:
            return [_DOMAIN_FALLBACK_QUESTIONS[target_domain]]
        strategy = self._teaching_strategy(self._effective_activity_profile(decision, readout))
        if strategy.get("worked_example_first"):
            return ["我们先看一道完整例题，跟着走一遍，再决定下一步补哪块。"]
        if strategy.get("problem_first"):
            return ["这轮先不铺太多，我们直接做几道小题，做错的地方我再带你拆。"]
        if strategy.get("concept_first"):
            return ["这轮我先把关键概念钉稳，再马上接一个小检查题。"]
        return ["我先把这部分记住。你不用一次讲完整，我们会边走边把关键线索补齐。"]

    def _target_domain(self, decision: AuroraDecision) -> str | None:
        directive = decision.chat_directive or {}
        candidates = [
            directive.get("target_domain"),
            directive.get("question_domain"),
            directive.get("domain"),
            decision.harness_updates.get("agenda_priority"),
        ]
        tensions = decision.state_updates.get("informational_tensions")
        if isinstance(tensions, list):
            for item in tensions:
                if isinstance(item, dict):
                    candidates.append(item.get("domain"))
        for candidate in candidates:
            canonical = canonicalize_runtime_domain(candidate)
            if canonical:
                return canonical
        return None

    def _domain_label(self, domain: str | None) -> str | None:
        return {
            "goal": "目标",
            "scope": "范围",
            "baseline": "基础",
            "time": "时间约束",
            "motivation": "动机",
        }.get(str(domain or ""))

    def _teaching_strategy(self, activity_profile: dict[str, Any]) -> dict[str, bool]:
        strategy = activity_profile.get("strategy")
        return dict(strategy) if isinstance(strategy, dict) else {}

    def _wake_policy(self, readout: DashboardReadout) -> dict[str, Any]:
        return dict(readout.wake_policy or {})

    def _max_tokens_for_wake(self, wake_policy: dict[str, Any]) -> int:
        return 600 if wake_policy.get("context_budget") == "extended" else 320

    async def _resolve_llm(self) -> Any:
        service_or_awaitable = self.llm_factory()
        if inspect.isawaitable(service_or_awaitable):
            return await service_or_awaitable
        return service_or_awaitable

    async def _default_llm_factory(self) -> Any:
        return await get_configured_llm_service(AgentRole.ORCHESTRATOR, TaskType.QUICK_QUERY)
