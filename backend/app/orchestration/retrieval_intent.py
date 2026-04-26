from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Any, Literal

RetrievalMode = Literal["aggressive", "selective", "skip"]


@dataclass(frozen=True)
class RetrievalDecision:
    should_retrieve: bool
    retrieval_mode: RetrievalMode
    budget_tokens: int
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "should_retrieve": self.should_retrieve,
            "retrieval_mode": self.retrieval_mode,
            "budget_tokens": self.budget_tokens,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class RetrievalIntentBudgets:
    aggressive: int = 2200
    selective: int = 900
    ambiguous: int = 500


_TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9_+-]*|[0-9]+|[\u4e00-\u9fff]")

_EMOTIONAL_PATTERNS = (
    r"\b(stress|stressed|anxious|anxiety|overwhelmed|panic|panicking|burned out|burnout|sad|upset|lonely|scared|afraid|tired|exhausted|frustrated|depressed|crying)\b",
    r"(压力|焦虑|紧张|崩溃|难过|害怕|慌|烦|累|撑不住|想哭|沮丧|心态炸)|\bemo\b",
)
_SOCIAL_PATTERNS = (
    r"^\s*(hi|hello|hey|thanks|thank you|good morning|good night|lol|haha|what'?s up)[!.。！\s]*$",
    r"^\s*(你好|嗨|谢谢|早上好|晚安|哈哈|在吗|早|嗨嗨)[!.。！\s]*$",
)
_SIMPLE_TASK_PATTERNS = (
    r"\b(add|create|mark|complete|finish|delete|remove|rename|reschedule)\s+(a\s+)?(task|todo|to-do|reminder)\b",
    r"\b(mark|set)\s+.+\s+(done|complete|completed)\b",
    r"(添加|新增|创建|删除|完成|标记|打卡).{0,12}(任务|待办|todo|提醒)",
    r"(把|将).{1,40}(加入|加到|放进).{0,10}(任务|待办|todo)",
)
_KNOWLEDGE_PATTERNS = (
    r"\b(explain|define|teach|derive|compare|summarize|walk me through)\b",
    r"\b(what is|what are|why does|why do|how does|how do|how is|help me understand|i don'?t understand|i do not understand)\b",
    r"(解释|讲讲|什么是|为什么|怎么|如何|原理|机制|区别|推导|帮我理解|看不懂|不理解)",
)
_PLANNING_PATTERNS = (
    r"\b(plan|schedule|roadmap|study plan|revision plan|review plan|break down|milestone|sprint|timeline)\b",
    r"(计划|安排|规划|路线|学习路径|复习节奏|备考|拆解|里程碑|冲刺)",
)
_AMBIGUOUS_PATTERNS = (
    r"\b(help me|can you help|stuck|confused|this topic|chapter|lecture|notes|material)\b",
    r"(帮我|卡住|这个知识点|这章|课件|笔记|材料|教材)",
)

_LINKED_DOC_KEYS = (
    "file_ids",
    "linked_document_ids",
    "selected_document_ids",
    "attached_file_ids",
    "document_ids",
    "document_filter",
)

_PROTOTYPES = {
    "emotional": (
        "i am stressed anxious overwhelmed sad tired panicking scared frustrated burned out",
        "压力 焦虑 紧张 崩溃 难过 害怕 累 烦",
    ),
    "simple_task": (
        "add task create todo mark done complete reminder delete task",
        "添加 任务 待办 完成 标记 打卡 提醒",
    ),
    "knowledge": (
        "explain concept how does work help me understand define compare why derive summarize",
        "解释 什么是 原理 机制 为什么 区别 推导 帮我理解",
    ),
    "planning": (
        "make a study plan schedule roadmap break down milestones revision plan sprint timeline",
        "计划 安排 规划 路线 学习路径 复习节奏 备考 拆解",
    ),
    "ambiguous": (
        "help me with this topic stuck confused chapter lecture notes material",
        "帮我 卡住 这个知识点 这章 课件 笔记 材料",
    ),
}


def _normalize_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def _matches_any(text: str, patterns: tuple[str, ...]) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)


def _tokens(text: str) -> list[str]:
    normalized = _normalize_text(text)
    raw_tokens = [match.group(0).lower() for match in _TOKEN_RE.finditer(normalized)]
    if not raw_tokens and normalized:
        return [normalized]
    bigrams = [f"{left}_{right}" for left, right in zip(raw_tokens, raw_tokens[1:], strict=False)]
    return raw_tokens + bigrams


def _vector(text: str) -> Counter[str]:
    return Counter(_tokens(text))


def _cosine(left: Counter[str], right: Counter[str]) -> float:
    if not left or not right:
        return 0.0
    dot = sum(value * right.get(key, 0) for key, value in left.items())
    if dot <= 0:
        return 0.0
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    if left_norm <= 0 or right_norm <= 0:
        return 0.0
    return dot / (left_norm * right_norm)


_PROTOTYPE_VECTORS = {
    label: [_vector(text) for text in samples]
    for label, samples in _PROTOTYPES.items()
}


def _prototype_scores(text: str) -> dict[str, float]:
    text_vector = _vector(text)
    return {
        label: max((_cosine(text_vector, prototype) for prototype in prototypes), default=0.0)
        for label, prototypes in _PROTOTYPE_VECTORS.items()
    }


def _has_linked_documents(context: dict[str, Any] | None) -> bool:
    if not isinstance(context, dict):
        return False
    candidates = [context]
    for key in ("session", "session_flags", "extra_context", "document_context"):
        nested = context.get(key)
        if isinstance(nested, dict):
            candidates.append(nested)
    for candidate in candidates:
        for key in _LINKED_DOC_KEYS:
            value = candidate.get(key)
            if isinstance(value, (list, tuple, set)) and len(value) > 0:
                return True
            if isinstance(value, str) and value.strip():
                return True
    return False


def extract_use_document_context(context: dict[str, Any] | None) -> bool | None:
    if not isinstance(context, dict):
        return None
    candidates = [context]
    for key in ("session", "session_flags", "extra_context", "document_context", "conversation"):
        nested = context.get(key)
        if isinstance(nested, dict):
            candidates.append(nested)

    for candidate in candidates:
        for key in ("use_document_context", "document_context_enabled", "enable_document_context"):
            if key not in candidate:
                continue
            value = candidate.get(key)
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                normalized = value.strip().lower()
                if normalized in {"1", "true", "yes", "on", "enabled"}:
                    return True
                if normalized in {"0", "false", "no", "off", "disabled"}:
                    return False
    return None


class RetrievalIntentClassifier:
    KNOWLEDGE_ROUTE_HINTS = {"knowledge", "error_diagnosis", "translation", "math", "reasoning"}
    PLANNING_ROUTE_HINTS = {"plan", "sprint_plan", "goal", "schedule", "review"}
    SIMPLE_ROUTE_HINTS = {"task", "todo", "preference_update"}

    def classify(
        self,
        message: str,
        *,
        route_intent: str | None = None,
        context: dict[str, Any] | None = None,
        use_document_context: bool | None = None,
        aurora_doc_context_mode: str = "auto",
        budgets: RetrievalIntentBudgets | None = None,
    ) -> RetrievalDecision:
        budgets = budgets or RetrievalIntentBudgets()
        text = _normalize_text(message)
        mode_override = _normalize_text(aurora_doc_context_mode) or "auto"

        if mode_override in {"off", "skip", "disabled", "false", "0"}:
            return RetrievalDecision(False, "skip", 0, "aurora_doc_context_mode_skip")
        if use_document_context is False:
            return RetrievalDecision(False, "skip", 0, "session_use_document_context_false")
        if not text:
            return RetrievalDecision(False, "skip", 0, "empty_message")

        base_decision = self._classify_without_overrides(text, route_intent=route_intent, context=context, budgets=budgets)
        if not base_decision.should_retrieve:
            return base_decision

        if mode_override in {"selective", "conservative"} and base_decision.retrieval_mode == "aggressive":
            return RetrievalDecision(
                True,
                "selective",
                budgets.selective,
                f"{base_decision.reason}; aurora_doc_context_mode_selective_cap",
            )
        if mode_override == "aggressive" and base_decision.retrieval_mode == "selective":
            return RetrievalDecision(
                True,
                "aggressive",
                budgets.aggressive,
                f"{base_decision.reason}; aurora_doc_context_mode_aggressive_cap",
            )
        return base_decision

    def _classify_without_overrides(
        self,
        text: str,
        *,
        route_intent: str | None,
        context: dict[str, Any] | None,
        budgets: RetrievalIntentBudgets,
    ) -> RetrievalDecision:
        route = _normalize_text(route_intent)
        scores = _prototype_scores(text)
        linked_docs = _has_linked_documents(context)

        if _matches_any(text, _EMOTIONAL_PATTERNS) or _matches_any(text, _SOCIAL_PATTERNS) or scores["emotional"] >= 0.30:
            return RetrievalDecision(False, "skip", 0, "emotional_or_social_turn")

        if _matches_any(text, _SIMPLE_TASK_PATTERNS) or route in self.SIMPLE_ROUTE_HINTS or scores["simple_task"] >= 0.32:
            return RetrievalDecision(False, "skip", 0, "simple_task_turn")

        knowledge_signal = _matches_any(text, _KNOWLEDGE_PATTERNS) or scores["knowledge"] >= 0.24
        planning_signal = _matches_any(text, _PLANNING_PATTERNS) or scores["planning"] >= 0.24
        ambiguous_signal = _matches_any(text, _AMBIGUOUS_PATTERNS) or scores["ambiguous"] >= 0.22

        if route in self.KNOWLEDGE_ROUTE_HINTS:
            knowledge_signal = True
        if route in self.PLANNING_ROUTE_HINTS:
            planning_signal = True

        if planning_signal and not knowledge_signal:
            reason = "planning_query_selective"
            if linked_docs:
                reason += "_linked_docs"
            return RetrievalDecision(True, "selective", budgets.selective, reason)

        if knowledge_signal:
            return RetrievalDecision(True, "aggressive", budgets.aggressive, "knowledge_query_aggressive")

        if ambiguous_signal or linked_docs:
            budget = budgets.ambiguous if not linked_docs else budgets.selective
            reason = "ambiguous_query_selective"
            if linked_docs:
                reason += "_linked_docs"
            return RetrievalDecision(True, "selective", budget, reason)

        return RetrievalDecision(False, "skip", 0, "no_document_retrieval_signal")


default_retrieval_intent_classifier = RetrievalIntentClassifier()


def build_retrieval_decision(
    *,
    message: str,
    route_intent: str | None = None,
    context: dict[str, Any] | None = None,
    aurora_doc_context_mode: str = "auto",
    budgets: RetrievalIntentBudgets | None = None,
) -> RetrievalDecision:
    return default_retrieval_intent_classifier.classify(
        message,
        route_intent=route_intent,
        context=context,
        use_document_context=extract_use_document_context(context),
        aurora_doc_context_mode=aurora_doc_context_mode,
        budgets=budgets,
    )
