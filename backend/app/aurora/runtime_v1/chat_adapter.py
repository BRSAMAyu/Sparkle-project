from __future__ import annotations

import inspect
import json
import re
from collections.abc import Awaitable, Callable, Mapping
from typing import Any

from loguru import logger

from app.aurora.runtime_v1.dashboard import DashboardReadout, canonicalize_runtime_domain
from app.aurora.runtime_v1.decision_loop import (
    AuroraDecision,
    build_standard_layer_contract,
    describe_standard_layer_tokens,
)
from app.aurora.runtime_v1.state import merge_activity_profile_payload, merge_expression_settings
from app.core.agent_profiles import AgentRole, TaskType
from app.orchestration.prompts import build_conversation_memory_fragment
from app.services.llm_service import get_configured_llm_service
from app.sprint_packs.sprint_pack_loader import get_mistake_by_nodes, load_pack

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
    "scope": "这门课里，最让你头疼的是哪部分？如果老师画过重点或你知道章节范围，也可以直接说。",
    "baseline": "这些内容里，你更像完全没接触过，还是学过一点但现在串不起来？",
    "time": "再补一个时间约束就能更稳：接下来这几天你每天大概能拿出多少时间？",
    "motivation": "最后一个问题：这次考试对你来说意味着什么？是一定要过还是想尽量考高分？",
}
_DOMAIN_QUESTION_ORDER = ("goal", "scope", "baseline", "time", "motivation")
_DOMAIN_ANSWER_KEYS = {
    "goal": ("goal", "goal_raw", "goal_summary", "primary_goal_description", "objective", "target"),
    "scope": ("scope", "exam_scope", "subject", "subjects", "chapter", "chapters", "topics", "focus_areas"),
    "baseline": ("baseline", "knowledge_baseline", "starting_point", "current_level", "foundation", "mastery"),
    "time": ("time", "time_available", "daily_available_hours", "time_constraint_days", "schedule", "availability"),
    "motivation": ("motivation", "motivation_context", "goal_motivation", "exam_motivation", "pressure"),
}
_BASELINE_ZERO_PATTERNS = ("没学过", "零基础", "完全不会", "完全没接触", "从没学", "从来没学")
_BASELINE_LIGHT_PATTERNS = ("不太会", "不太懂", "有点虚", "薄弱", "学了一点", "学过一点", "会一点")
_BASELINE_CLASS_ONLY_PATTERNS = ("上过课", "没复习", "忘了", "听过课")
_SCOPE_TOPIC_LABELS = (
    ("传输层", "传输层"),
    ("网络层", "网络层"),
    ("应用层", "应用层"),
    ("数据链路层", "数据链路层"),
    ("物理层", "物理层"),
    ("tcp", "TCP"),
    ("udp", "UDP"),
    ("ip", "IP"),
    ("拥塞控制", "拥塞控制"),
    ("路由", "路由"),
    ("子网", "子网"),
)
_SUBJECT_LABELS = (
    ("计算机网络", "计算机网络"),
    ("计网", "计网"),
    ("操作系统", "操作系统"),
    ("数据库", "数据库"),
    ("高数", "高数"),
    ("线代", "线代"),
    ("概率论", "概率论"),
    ("英语", "英语"),
)


def _context_text(value: Any) -> str:
    if value in (None, "", [], {}):
        return ""
    if isinstance(value, dict):
        return " ".join(_context_text(item) for item in value.values()).strip()
    if isinstance(value, (list, tuple, set)):
        return " ".join(_context_text(item) for item in value).strip()
    return " ".join(str(value).split()).strip()


def _contains_any(text: str, patterns: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(pattern.lower() in lowered for pattern in patterns)


def _unique_join(items: list[str], *, limit: int = 3) -> str:
    seen: set[str] = set()
    unique: list[str] = []
    for item in items:
        normalized = item.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        unique.append(normalized)
        if len(unique) >= limit:
            break
    return "和".join(unique) if len(unique) <= 2 else "、".join(unique)


def _infer_context_answers(already_said: str) -> dict[str, str]:
    text = " ".join(str(already_said or "").split()).strip()
    lowered = text.lower()
    answers: dict[str, str] = {}
    if not text:
        return answers
    if _contains_any(text, _BASELINE_ZERO_PATTERNS):
        answers["baseline"] = "零基础"
    elif _contains_any(text, _BASELINE_CLASS_ONLY_PATTERNS):
        answers["baseline"] = "上过课但没复习"
    elif _contains_any(text, _BASELINE_LIGHT_PATTERNS):
        answers["baseline"] = "不太稳"
    scope_topics = [label for token, label in _SCOPE_TOPIC_LABELS if token.lower() in lowered]
    if scope_topics:
        answers["scope"] = _unique_join(scope_topics)
    subject = next((label for token, label in _SUBJECT_LABELS if token.lower() in lowered), "")
    if subject:
        answers["subject"] = subject
    if "想考" in text or "备考" in text or "考试" in text or "期末" in text or "帮我规划" in text:
        answers["goal"] = text[:60]
    if re.search(r"\d+(?:\.\d+)?\s*(小时|h|hour|分钟)", lowered) or "每天" in text:
        answers["time"] = text[:60]
    if _contains_any(text, ("必须过", "一定要过", "不能挂", "不挂科", "不想挂", "想拿高分", "冲高分")):
        answers["motivation"] = text[:60]
    return answers


def _baseline_is_zero(value: Any) -> bool:
    return _contains_any(_context_text(value), _BASELINE_ZERO_PATTERNS + ("zero", "零基础"))


def _baseline_is_uncertain(value: Any) -> bool:
    return _contains_any(_context_text(value), _BASELINE_LIGHT_PATTERNS)


def _scope_label(value: Any, subject: str = "") -> str:
    text = _context_text(value)
    inferred = _infer_context_answers(text)
    scope = inferred.get("scope") or text
    if not scope:
        return subject
    if subject and scope == subject:
        return subject
    return scope[:36]


def context_aware_question(domain: str | None, already_said: str, previous_answers: dict[str, Any]) -> str:
    """Choose a coach-like follow-up using what the user has already supplied."""
    canonical = canonicalize_runtime_domain(domain) or ""
    inferred = _infer_context_answers(already_said)
    answers = {**previous_answers}
    for key, value in inferred.items():
        answers.setdefault(key, value)

    subject = _context_text(answers.get("subject")) or "这门课"
    scope = _scope_label(answers.get("scope"), subject=subject)
    baseline = _context_text(answers.get("baseline"))

    if canonical == "goal":
        return f"{subject}这次你最想保住的结果是什么：稳过、冲高分，还是先把核心章节补起来？"
    if canonical == "scope":
        if _baseline_is_zero(baseline):
            return f"好，零基础先别把面铺太大。{subject}这次主要考哪几块：章节、题型，还是老师画过的重点？"
        return f"{subject}这门课，最让你头疼的是哪部分？如果已经知道考试范围，就直接说章节或题型。"
    if canonical == "baseline":
        if _baseline_is_uncertain(already_said):
            return "大概是完全没接触过，还是学了一点点但串不起来？"
        if scope:
            return f"{scope}这几块里，你更像完全没接触过，还是上过课但现在不稳？"
        return "你现在更像完全没接触过，还是学过一点但还串不起来？"
    if canonical == "time":
        if _baseline_is_zero(baseline):
            scope_part = f"先围绕{scope}" if scope else "先按最核心范围"
            return f"好，零基础的话，咱们{scope_part}排一个保底节奏。接下来这几天你每天大概能拿出多少时间？"
        if scope:
            return f"好，范围先按{scope}来抓。接下来这几天你每天大概能拿出多少时间？有没有哪天会特别忙？"
        return _DOMAIN_FALLBACK_QUESTIONS["time"]
    if canonical == "motivation":
        return _DOMAIN_FALLBACK_QUESTIONS["motivation"]
    return "我先把你刚刚说的记住。现在只补一个最关键的缺口：接下来你最希望我按什么约束来安排？"


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
            "When intent=diagnose_stuck_point, use micro_teaching: first narrow the stuck point with one "
            "two-choice diagnosis question; after the user answers, give a one-minute targeted fix and one simple "
            "confirmation question. Do not give the full solution or turn it into a drill set. "
            "Stay task-level and avoid clinical, personality, or social-identity inference. "
            'Return JSON: {"messages": ["..."]}.'
        )
        conversation_summary = readout.conversation_summary if isinstance(readout.conversation_summary, dict) else {}
        recent_messages = conversation_summary.get("recent_messages")
        try:
            summary_message_count = int(conversation_summary.get("message_count") or 0)
        except (TypeError, ValueError):
            summary_message_count = 0
        has_conversation_history = bool(
            summary_message_count
            or (isinstance(recent_messages, list) and recent_messages)
            or conversation_summary.get("summary")
            or conversation_summary.get("text")
        )
        conversation_memory_fragment = build_conversation_memory_fragment(conversation_summary)
        if has_conversation_history:
            system += (
                "\n\n在适当时机自然地引用用户之前提到的具体内容"
                "（困难点/已完成的任务），而不是每次都从头开始。"
            )
        if conversation_memory_fragment:
            system += f"\n\n{conversation_memory_fragment}"
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
            "task_help_context": self._build_task_help_context(decision, readout),
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

    def _build_task_help_context(self, decision: AuroraDecision, readout: DashboardReadout) -> dict[str, Any]:
        directive = decision.chat_directive if isinstance(decision.chat_directive, Mapping) else {}
        intent = str(directive.get("intent") or "").strip()
        task_state = dict(readout.task_state) if isinstance(readout.task_state, Mapping) else {}
        if not task_state and intent != "diagnose_stuck_point":
            return {}

        context: dict[str, Any] = {"task_state": task_state}
        if intent != "diagnose_stuck_point":
            return context

        context["micro_teaching"] = {
            "mode": "diagnose_then_targeted_fix",
            "step_1": "Ask one two-choice diagnosis question about the user's exact stuck point.",
            "step_2": "After the user chooses, give a one-minute targeted fix plus one simple same-type check question.",
            "diagnosis_choice_limit": 2,
            "avoid": ["full_solution", "full_week_replan", "three_practice_questions"],
        }
        candidate_mistakes = self._candidate_stuck_mistakes(readout)
        if candidate_mistakes:
            context["candidate_mistake_types"] = candidate_mistakes
        return context

    def _candidate_stuck_mistakes(self, readout: DashboardReadout) -> list[dict[str, Any]]:
        checkpoint_state = readout.checkpoint_state if isinstance(readout.checkpoint_state, Mapping) else {}
        mistakes = self._as_list_of_dicts(checkpoint_state.get("sprint_pack_mistakes"))
        pack = self._load_sprint_pack_for_readout(readout)
        if not mistakes and pack:
            node_ids = self._diagnosis_node_ids(readout)
            if node_ids:
                mistakes = get_mistake_by_nodes(pack, node_ids)
            if not mistakes:
                mistakes = self._filter_mistakes_by_topic(pack, self._stuck_topic_text(readout))
        return [self._slim_mistake(mistake) for mistake in mistakes[:8]]

    def _load_sprint_pack_for_readout(self, readout: DashboardReadout) -> dict[str, Any] | None:
        checkpoint_state = readout.checkpoint_state if isinstance(readout.checkpoint_state, Mapping) else {}
        exam_policy = readout.exam_sprint_policy if isinstance(readout.exam_sprint_policy, Mapping) else {}
        cold_start = readout.cold_start_context if isinstance(readout.cold_start_context, Mapping) else {}
        pack_id = (
            checkpoint_state.get("sprint_pack_id")
            or exam_policy.get("sprint_pack_id")
            or cold_start.get("sprint_pack_id")
        )
        if pack_id and str(pack_id).strip():
            subject, version = self._split_sprint_pack_id(str(pack_id).strip())
            return load_pack(subject, version)
        subject = cold_start.get("subject") or exam_policy.get("subject")
        if subject and str(subject).strip():
            return load_pack(str(subject).strip())
        return None

    def _split_sprint_pack_id(self, pack_id: str) -> tuple[str, str]:
        subject, separator, version = pack_id.partition("@")
        return subject.strip(), (version.strip() if separator and version.strip() else "v1")

    def _diagnosis_node_ids(self, readout: DashboardReadout) -> list[str]:
        node_ids: list[str] = []
        for source in (
            readout.checkpoint_state if isinstance(readout.checkpoint_state, Mapping) else {},
            readout.task_state if isinstance(readout.task_state, Mapping) else {},
        ):
            for key in (
                "today_nodes",
                "knowledge_nodes",
                "knowledge_node_ids",
                "node_ids",
                "related_nodes",
            ):
                node_ids.extend(self._string_list(source.get(key)))
            for key in ("knowledge_node_id", "node_id", "current_node_id"):
                value = str(source.get(key) or "").strip()
                if value:
                    node_ids.append(value)
        if not node_ids and self._looks_like_tcp_state_machine(self._stuck_topic_text(readout)):
            node_ids.extend(["cn.tcp_three_way", "cn.tcp_four_way"])
        return self._dedupe(node_ids)

    def _stuck_topic_text(self, readout: DashboardReadout) -> str:
        task_state = readout.task_state if isinstance(readout.task_state, Mapping) else {}
        parts = [
            task_state.get("stuck_topic"),
            task_state.get("topic"),
            task_state.get("title"),
            task_state.get("current_task"),
            readout.user_message,
        ]
        return " ".join(str(part or "").strip() for part in parts if str(part or "").strip()).lower()

    def _filter_mistakes_by_topic(self, pack: dict[str, Any], topic_text: str) -> list[dict[str, Any]]:
        mistake_types = self._as_list_of_dicts(pack.get("mistake_types"))
        if not topic_text:
            return mistake_types[:8]
        if self._looks_like_tcp_state_machine(topic_text):
            markers = (
                "tcp_state_diagram",
                "状态机",
                "状态图",
                "状态/过程",
                "三次握手状态",
                "四次挥手状态",
                "time_wait",
            )
            matches = [
                mistake
                for mistake in mistake_types
                if any(marker in json.dumps(mistake, ensure_ascii=False).lower() for marker in markers)
            ]
            if matches:
                return matches
        return mistake_types[:8]

    def _looks_like_tcp_state_machine(self, text: str) -> bool:
        lowered = str(text or "").lower()
        return "tcp" in lowered and any(
            marker in lowered
            for marker in ("状态机", "状态图", "状态转换", "state machine", "state diagram", "握手", "挥手")
        )

    def _slim_mistake(self, mistake: dict[str, Any]) -> dict[str, Any]:
        return {
            key: mistake[key] for key in ("mistake_id", "label", "related_nodes", "repair_strategy") if key in mistake
        }

    def _as_list_of_dicts(self, value: Any) -> list[dict[str, Any]]:
        if not isinstance(value, list):
            return []
        return [dict(item) for item in value if isinstance(item, Mapping)]

    def _string_list(self, value: Any) -> list[str]:
        if isinstance(value, (list, tuple, set)):
            return [str(item).strip() for item in value if str(item).strip()]
        if value in (None, ""):
            return []
        return [str(value).strip()]

    def _dedupe(self, values: list[str]) -> list[str]:
        deduped: list[str] = []
        seen: set[str] = set()
        for value in values:
            if value in seen:
                continue
            seen.add(value)
            deduped.append(value)
        return deduped

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
        directive = decision.chat_directive if isinstance(decision.chat_directive, Mapping) else {}
        if directive.get("intent") == "diagnose_stuck_point":
            task_state = readout.task_state if isinstance(readout.task_state, Mapping) else {}
            topic = f"（{task_state['stuck_topic']}）" if task_state.get("stuck_topic") else ""
            return [f"先定位卡点{topic}：你更卡在“哪些状态之间有连线”，还是“每条线的触发条件”？回我一个就行。"]
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
        question = self._context_aware_fallback_question(decision, readout)
        if question:
            return [question]
        strategy = self._teaching_strategy(self._effective_activity_profile(decision, readout))
        if strategy.get("worked_example_first"):
            return ["我们先看一道完整例题，跟着走一遍，再决定下一步补哪块。"]
        if strategy.get("problem_first"):
            return ["这轮先不铺太多，我们直接做几道小题，做错的地方我再带你拆。"]
        if strategy.get("concept_first"):
            return ["这轮我先把关键概念钉稳，再马上接一个小检查题。"]
        return ["我先把这部分记住。你不用一次讲完整，我们会边走边把关键线索补齐。"]

    def _context_aware_fallback_question(self, decision: AuroraDecision, readout: DashboardReadout) -> str | None:
        return self._choose_question_for_domain(self._target_domain(decision), readout)

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

    def _choose_question_for_domain(self, domain: str | None, readout: DashboardReadout) -> str | None:
        already_said = self._already_said(readout)
        previous_answers = self._previous_answers(readout)
        target_domain = self._contextual_target_domain(domain, readout, already_said, previous_answers)
        if not target_domain:
            return None
        return context_aware_question(target_domain, already_said, previous_answers)

    def _contextual_target_domain(
        self,
        domain: str | None,
        readout: DashboardReadout,
        already_said: str,
        previous_answers: dict[str, Any],
    ) -> str | None:
        inferred_answers = _infer_context_answers(already_said)
        covered = {
            canonical
            for item in list(readout.covered_domains or []) + list(previous_answers.get("covered_domains") or [])
            if (canonical := canonicalize_runtime_domain(item))
        }
        inferred_domains = {
            canonical
            for item in inferred_answers
            if (canonical := canonicalize_runtime_domain(item)) in _DOMAIN_QUESTION_ORDER
        }
        unavailable = covered | inferred_domains
        recent = {
            canonical
            for item in list(readout.recently_asked_domains or [])
            + list(previous_answers.get("recently_asked_domains") or [])
            if (canonical := canonicalize_runtime_domain(item))
        }
        canonical_domain = canonicalize_runtime_domain(domain)
        if canonical_domain and canonical_domain not in unavailable:
            return canonical_domain

        for candidate in list(readout.missing_domains or []):
            canonical_candidate = canonicalize_runtime_domain(candidate)
            if canonical_candidate and canonical_candidate not in unavailable and canonical_candidate not in recent:
                return canonical_candidate
        for candidate in _DOMAIN_QUESTION_ORDER:
            if candidate not in unavailable and candidate not in recent:
                return candidate
        if canonical_domain and canonical_domain not in unavailable and canonical_domain not in recent:
            return canonical_domain
        return None

    def _already_said(self, readout: DashboardReadout) -> str:
        parts = [str(readout.user_message or "")]
        summary = readout.conversation_summary if isinstance(readout.conversation_summary, dict) else {}
        recent_messages = summary.get("recent_messages")
        if isinstance(recent_messages, list):
            for item in recent_messages[-6:]:
                if isinstance(item, dict) and str(item.get("role") or "").lower() == "user":
                    parts.append(str(item.get("content") or ""))
                elif isinstance(item, str):
                    parts.append(item)
        request_recent = readout.request_extra_context.get("recent_user_messages")
        if isinstance(request_recent, list):
            parts.extend(str(item) for item in request_recent[-4:])
        return " ".join(part for part in parts if part).strip()

    def _previous_answers(self, readout: DashboardReadout) -> dict[str, Any]:
        answers: dict[str, Any] = {
            "covered_domains": list(readout.covered_domains or []),
            "missing_domains": list(readout.missing_domains or []),
            "recently_asked_domains": list(readout.recently_asked_domains or []),
        }
        for source in (
            readout.cold_start_context,
            readout.request_extra_context,
            readout.explicit_user_constraints,
            readout.sprint_policy_summary,
        ):
            self._merge_domain_answers(answers, source)
        for tension in readout.informational_tensions or []:
            if not isinstance(tension, dict):
                continue
            domain = canonicalize_runtime_domain(tension.get("domain"))
            evidence = tension.get("evidence")
            if domain and evidence not in (None, "", [], {}) and domain not in answers:
                answers[domain] = evidence
        inferred = _infer_context_answers(self._already_said(readout))
        for key, value in inferred.items():
            answers.setdefault(key, value)
        return answers

    def _merge_domain_answers(self, answers: dict[str, Any], source: Any) -> None:
        if not isinstance(source, dict):
            return
        for key, value in source.items():
            if value in (None, "", [], {}):
                continue
            canonical = canonicalize_runtime_domain(key)
            if canonical in _DOMAIN_ANSWER_KEYS and canonical not in answers:
                answers[canonical] = value
            for domain, keys in _DOMAIN_ANSWER_KEYS.items():
                if key in keys and domain not in answers:
                    answers[domain] = value
            if isinstance(value, dict):
                self._merge_domain_answers(answers, value)

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
