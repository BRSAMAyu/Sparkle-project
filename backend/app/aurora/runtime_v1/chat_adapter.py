from __future__ import annotations

import inspect
import json
import re
from typing import Any, Awaitable, Callable

from loguru import logger

from app.aurora.runtime_v1.dashboard import DashboardReadout, canonicalize_runtime_domain
from app.aurora.runtime_v1.decision_loop import AuroraDecision
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

        prompt = self._build_prompt(decision, readout)
        try:
            llm = await self._resolve_llm()
            raw = await llm.chat_json(prompt, temperature=self.temperature)
            messages = self._extract_messages(raw)
        except Exception as exc:
            logger.warning("Aurora chat adapter fell back after LLM failure: {}", exc)
            messages = []

        messages = self._sanitize_messages(messages)
        if messages:
            return messages
        return self._fallback_messages(decision, readout)

    def _build_prompt(self, decision: AuroraDecision, readout: DashboardReadout) -> list[dict[str, str]]:
        system = (
            "You are Sparkle's chat layer adapter. Aurora has already made the cognitive decision. "
            "Write 1-3 short, natural, non-overlapping messages for the user. "
            "Every message must stand on its own as a complete thought. Do not split one sentence across messages. "
            "Adjacent messages must add different value instead of paraphrasing each other. "
            "Do not expose internal decision fields. "
            "Stay task-level and avoid clinical, personality, or social-identity inference. "
            'Return JSON: {"messages": ["..."]}.'
        )
        user = {
            "surface": readout.surface,
            "style": readout.activity_profile.get("conversation_style"),
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

    def _sanitize_messages(self, messages: list[str]) -> list[str]:
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
            if len(cleaned) >= 3:
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

    def _fallback_messages(self, decision: AuroraDecision, readout: DashboardReadout) -> list[str]:
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

    async def _resolve_llm(self) -> Any:
        service_or_awaitable = self.llm_factory()
        if inspect.isawaitable(service_or_awaitable):
            return await service_or_awaitable
        return service_or_awaitable

    async def _default_llm_factory(self) -> Any:
        return await get_configured_llm_service(AgentRole.ORCHESTRATOR, TaskType.QUICK_QUERY)
