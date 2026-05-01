from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

try:
    import tiktoken
except ImportError:  # pragma: no cover - optional runtime dependency
    tiktoken = None

from app.config import settings
from app.core.business_metrics import (
    CONTEXT_BRIEFING_GENERATED_TOTAL,
    CONTEXT_BUDGET_OVER_LIMIT_TOTAL,
    CONTEXT_BUDGET_UTILIZATION,
    CONTEXT_PACK_BUILD,
    CONTEXT_PACK_INTENT,
    CONTEXT_PACK_OVER_BUDGET,
    CONTEXT_SEMANTIC_GATING_APPLIED_TOTAL,
    CONTEXT_SEMANTIC_GATING_FALLBACK_TOTAL,
)
from app.core.context_budget import ContextBudgetScheduler
from app.core.context_ranker import RankedItem, rank_items
from app.core.plan_context import PlanContextBuilder
from app.orchestration.context_focus import (
    ContextFocusResolver,
    build_context_briefing_note,
    cosine_similarity,
    get_focus_profile,
)
from app.services.aurora_doc_context_kill_switch_service import AuroraDocContextKillSwitchService
from app.services.context_pack_telemetry_service import ContextPackTelemetryService
from app.services.embedding_service import embedding_service
from app.services.ltm_rollout_service import LtmRolloutService
from app.services.memory_conflict_resolver import MemoryConflictResolver
from app.services.memory_rank_policy_service import MemoryRankPolicyService
from app.services.memory_service import MemoryService
from app.services.personalization.preference_service import PreferenceService


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@lru_cache(maxsize=1)
def _get_token_encoding():
    if tiktoken is None:
        return None
    try:
        return tiktoken.get_encoding("cl100k_base")
    except Exception:
        return None


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    encoding = _get_token_encoding()
    if encoding:
        try:
            return len(encoding.encode(text))
        except Exception:
            pass
    return max(1, len(text) // 4)


def _serialize(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def _truncate_text_to_token_budget(text: str, budget: int) -> str:
    normalized = str(text or "").strip()
    if budget <= 0 or not normalized:
        return ""
    if estimate_tokens(normalized) <= budget:
        return normalized

    candidate = ""
    encoding = _get_token_encoding()
    if encoding:
        try:
            encoded = encoding.encode(normalized)
            if len(encoded) <= budget:
                return normalized
            candidate = encoding.decode(encoded[: max(1, budget - 1)]).rstrip() + "..."
        except Exception:
            pass

    if not candidate:
        approx_chars = max(16, budget * 4)
        candidate = normalized[:approx_chars].rstrip() + "..."

    while estimate_tokens(candidate) > budget and len(candidate) > 4:
        next_len = max(1, int(len(candidate) * 0.85))
        candidate = candidate[:next_len].rstrip(". ").rstrip() + "..."
    return candidate if estimate_tokens(candidate) <= budget else ""


def _trim_list(items: list[dict[str, Any]], budget: int) -> list[dict[str, Any]]:
    trimmed: list[dict[str, Any]] = []
    used = 0
    for item in items:
        item_tokens = estimate_tokens(_serialize(item))
        if used + item_tokens > budget:
            break
        trimmed.append(item)
        used += item_tokens
    return trimmed


def _trim_preferences(prefs: dict[str, Any], budget: int) -> dict[str, Any]:
    trimmed: dict[str, Any] = {}
    used = 0
    for key, value in prefs.items():
        item_tokens = estimate_tokens(_serialize({key: value}))
        if used + item_tokens > budget:
            break
        trimmed[key] = value
        used += item_tokens
    return trimmed


def _trim_ranked_preferences(
    ranked: list[RankedItem[Any]],
    budget: int,
) -> tuple[dict[str, Any], dict[str, float]]:
    items: list[dict[str, Any]] = []
    total = 0
    for entry in ranked:
        key = entry.item.pref_key
        value = entry.item.pref_value
        tokens = estimate_tokens(_serialize({key: value}))
        items.append({"key": key, "value": value, "score": entry.score, "tokens": tokens})
        total += tokens

    if total > budget:
        items.sort(key=lambda item: item["score"])
        while total > budget and items:
            dropped = items.pop(0)
            total -= dropped["tokens"]

    items.sort(key=lambda item: item["score"], reverse=True)
    trimmed = {item["key"]: item["value"] for item in items}
    scores = {item["key"]: item["score"] for item in items}
    return trimmed, scores


def _trim_ranked_list(
    payloads: list[dict[str, Any]],
    scores: dict[str, float],
    budget: int,
) -> tuple[list[dict[str, Any]], dict[str, float]]:
    entries: list[dict[str, Any]] = []
    total = 0
    for payload in payloads:
        item_id = payload.get("id")
        score = scores.get(item_id, 0.0)
        tokens = estimate_tokens(_serialize(payload))
        entries.append({"payload": payload, "score": score, "tokens": tokens, "id": item_id})
        total += tokens

    if total > budget:
        entries.sort(key=lambda item: item["score"])
        while total > budget and entries:
            dropped = entries.pop(0)
            total -= dropped["tokens"]

    entries.sort(key=lambda item: item["score"], reverse=True)
    trimmed = [entry["payload"] for entry in entries]
    trimmed_scores = {entry["id"]: entry["score"] for entry in entries if entry["id"]}
    return trimmed, trimmed_scores


def _select_with_diversity(
    ranked: list[RankedItem[Any]],
    cap: int,
    diversity_key,
) -> list[RankedItem[Any]]:
    if cap <= 0:
        return []
    selected: list[RankedItem[Any]] = []
    seen = set()
    remaining: list[RankedItem[Any]] = []

    for entry in ranked:
        key = diversity_key(entry.item)
        if key and key not in seen:
            selected.append(entry)
            seen.add(key)
        else:
            remaining.append(entry)
        if len(selected) >= cap:
            return selected

    for entry in remaining:
        if len(selected) >= cap:
            break
        selected.append(entry)
    return selected


DEFAULT_SEMANTIC_GATING_RULES: dict[str, dict[str, float | int]] = {
    "preferences": {"candidate_limit": 12, "top_k": 5, "threshold": 0.55},
    "goals": {"candidate_limit": 10, "top_k": 4, "threshold": 0.50},
    "episodic": {"candidate_limit": 12, "top_k": 4, "threshold": 0.52},
}


def _get_semantic_gating_rules() -> dict[str, dict[str, float | int]]:
    rules = {section: dict(config) for section, config in DEFAULT_SEMANTIC_GATING_RULES.items()}
    overrides = settings.CONTEXT_SEMANTIC_GATING_RULES
    if not isinstance(overrides, dict):
        return rules
    for section, config in overrides.items():
        if section not in rules or not isinstance(config, dict):
            continue
        for key in ("candidate_limit", "top_k", "threshold"):
            value = config.get(key)
            if value is None:
                continue
            try:
                rules[section][key] = int(value) if key != "threshold" else float(value)
            except Exception:
                continue
    return rules


def _normalized_ranked(items: list[Any]) -> list[RankedItem[Any]]:
    normalized: list[RankedItem[Any]] = []
    for item in items:
        normalized.append(
            RankedItem(
                item=item,
                score=float(getattr(item, "evidence_score", 0.0) or 0.0),
            )
        )
    normalized.sort(
        key=lambda entry: (
            entry.score,
            getattr(entry.item, "updated_at", None) or getattr(entry.item, "occurred_at", None),
        ),
        reverse=True,
    )
    return normalized


def _serialize_focus_value(value: Any) -> str:
    if isinstance(value, dict):
        primary = value.get("value")
        if primary is not None:
            return str(primary)
        return _serialize(value)
    if isinstance(value, list):
        return ", ".join(str(item) for item in value[:5])
    return str(value)


def _build_semantic_text(item: Any, section: str) -> str:
    if section == "preferences":
        return f"{getattr(item, 'pref_key', '')} {_serialize_focus_value(getattr(item, 'pref_value', ''))}".strip()
    if section == "goals":
        title = getattr(item, "title", "")
        status = getattr(item, "status", "")
        target_date = getattr(item, "target_date", None)
        return f"{title} {status} {target_date or ''}".strip()
    summary = getattr(item, "summary", "")
    tags = getattr(item, "tags", None) or []
    importance = getattr(item, "importance_score", "")
    return f"{summary} {' '.join(str(tag) for tag in tags)} {importance}".strip()


def _reweight_budgets(budgets: dict[str, int], focus_mode: str | None) -> dict[str, int]:
    profile = get_focus_profile(focus_mode)
    weighted = {
        key: float(budgets.get(key, 0)) * float(profile.memory_budget_weights.get(key, 1.0))
        for key in ("preferences", "goals", "episodic")
    }
    total = sum(budgets.get(key, 0) for key in weighted)
    weighted_total = sum(weighted.values())
    if total <= 0 or weighted_total <= 0:
        return dict(budgets)
    scaled = {key: weighted[key] * total / weighted_total for key in weighted}
    adjusted = {}
    remainder = total
    keys = list(weighted.keys())
    for idx, key in enumerate(keys):
        if idx == len(keys) - 1:
            adjusted[key] = max(0, remainder)
            break
        value = max(0, int(round(scaled[key])))
        adjusted[key] = value
        remainder -= value
    return adjusted


CONTEXT_SOURCE_CONVERSATION = "conversation_history"
CONTEXT_SOURCE_DOCUMENTS = "document_chunks"
CONTEXT_SOURCE_GALAXY = "galaxy_knowledge"
CONTEXT_SOURCE_TASK_ERROR = "task_error_context"
CONTEXT_SOURCE_COGNITIVE = "cognitive_profile"


@dataclass(frozen=True)
class ContextAssemblyResult:
    system_prompt: str
    conversation_history: list[dict[str, Any]]
    budgets: dict[str, int]
    token_usage: dict[str, int]
    budget_remaining: dict[str, int]
    metadata: dict[str, Any]


def _context_source_ratios() -> dict[str, float]:
    ratios = {
        CONTEXT_SOURCE_CONVERSATION: float(getattr(settings, "CONVERSATION_HISTORY_CONTEXT_RATIO", 0.40) or 0.40),
        CONTEXT_SOURCE_DOCUMENTS: float(getattr(settings, "DOCUMENT_CONTEXT_RATIO", 0.25) or 0.25),
        CONTEXT_SOURCE_GALAXY: float(getattr(settings, "GALAXY_KNOWLEDGE_CONTEXT_RATIO", 0.15) or 0.15),
        CONTEXT_SOURCE_TASK_ERROR: float(getattr(settings, "TASK_ERROR_CONTEXT_RATIO", 0.10) or 0.10),
        CONTEXT_SOURCE_COGNITIVE: float(getattr(settings, "COGNITIVE_PROFILE_CONTEXT_RATIO", 0.10) or 0.10),
    }
    positive_total = sum(max(0.0, value) for value in ratios.values())
    if positive_total <= 0:
        return {
            CONTEXT_SOURCE_CONVERSATION: 0.40,
            CONTEXT_SOURCE_DOCUMENTS: 0.25,
            CONTEXT_SOURCE_GALAXY: 0.15,
            CONTEXT_SOURCE_TASK_ERROR: 0.10,
            CONTEXT_SOURCE_COGNITIVE: 0.10,
        }
    return {key: max(0.0, value) / positive_total for key, value in ratios.items()}


def _allocate_context_source_budgets(total_budget: int) -> dict[str, int]:
    ratios = _context_source_ratios()
    keys = list(ratios.keys())
    allocated: dict[str, int] = {}
    remainder = max(0, int(total_budget))
    for idx, key in enumerate(keys):
        if idx == len(keys) - 1:
            allocated[key] = remainder
            break
        value = max(0, int(round(total_budget * ratios[key])))
        allocated[key] = value
        remainder -= value
    return allocated


def _scale_budgets_to_available(budgets: dict[str, int], available: int) -> dict[str, int]:
    total = sum(max(0, value) for value in budgets.values())
    if total <= 0 or total <= available:
        return dict(budgets)
    ratio = max(0.0, float(available) / float(total))
    keys = list(budgets.keys())
    scaled: dict[str, int] = {}
    remainder = max(0, int(available))
    for idx, key in enumerate(keys):
        if idx == len(keys) - 1:
            scaled[key] = remainder
            break
        value = max(0, int(budgets[key] * ratio))
        scaled[key] = value
        remainder -= value
    return scaled


def _as_prompt_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return _serialize(value)


def _extract_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and value.strip():
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except Exception:
            return None
    return None


def _document_item_metadata(item: Any) -> dict[str, Any]:
    metadata = getattr(item, "metadata", None)
    if isinstance(metadata, dict):
        return metadata
    raw = getattr(item, "raw", None)
    metadata = getattr(raw, "metadata", None)
    return metadata if isinstance(metadata, dict) else {}


def _document_item_chunk(item: Any) -> Any:
    return getattr(item, "chunk", None) or getattr(item, "raw", None) or item


def _document_relevance_score(item: Any) -> float:
    metadata = _document_item_metadata(item)
    for source in (item, metadata, getattr(item, "raw", None)):
        if source is None:
            continue
        for key in ("relevance_score", "score", "similarity", "cosine_similarity"):
            try:
                value = source.get(key) if isinstance(source, dict) else getattr(source, key)
            except Exception:
                continue
            if value is None:
                continue
            try:
                return max(0.0, min(1.0, float(value)))
            except Exception:
                continue
    return 0.0


def _document_recency_boost(item: Any) -> float:
    metadata = _document_item_metadata(item)
    chunk = _document_item_chunk(item)
    raw_updated_at = (
        metadata.get("updated_at")
        or metadata.get("created_at")
        or getattr(chunk, "updated_at", None)
        or getattr(chunk, "created_at", None)
    )
    updated_at = _extract_datetime(raw_updated_at)
    if updated_at is None:
        return 1.0
    if updated_at.tzinfo is not None:
        updated_at = updated_at.astimezone(UTC).replace(tzinfo=None)
    age_days = max(0.0, (_utcnow() - updated_at).total_seconds() / 86400)
    window_days = max(1.0, float(getattr(settings, "DOCUMENT_CONTEXT_RECENCY_BOOST_DAYS", 30) or 30))
    if age_days >= window_days:
        return 1.0
    return 1.0 + (0.25 * (1.0 - (age_days / window_days)))


def _document_mastery_gap_boost(item: Any) -> float:
    metadata = _document_item_metadata(item)
    for key in ("mastery_gap", "mastery_gap_score", "knowledge_gap", "gap_score"):
        value = metadata.get(key)
        if value is None:
            continue
        try:
            return 1.0 + (0.5 * max(0.0, min(1.0, float(value))))
        except Exception:
            continue

    for key in ("current_mastery", "mastery", "mastery_score"):
        value = metadata.get(key)
        if value is None:
            continue
        try:
            mastery = float(value)
        except Exception:
            continue
        if mastery > 1.0:
            mastery = mastery / 100.0
        gap = max(0.0, min(1.0, 1.0 - mastery))
        return 1.0 + (0.5 * gap)
    return 1.0


def _rank_document_chunks(chunks: list[Any]) -> list[tuple[Any, float]]:
    ranked = []
    for item in chunks:
        relevance = _document_relevance_score(item)
        recency_boost = _document_recency_boost(item)
        mastery_gap_boost = _document_mastery_gap_boost(item)
        ranked.append((item, relevance * recency_boost * mastery_gap_boost))
    ranked.sort(key=lambda entry: entry[1], reverse=True)
    return ranked


def _document_label(item: Any) -> str:
    metadata = _document_item_metadata(item)
    chunk = _document_item_chunk(item)
    label_parts = [
        str(getattr(item, "file_name", "") or getattr(item, "filename", "") or metadata.get("filename") or "").strip()
    ]
    section_title = str(getattr(chunk, "section_title", "") or metadata.get("section_title") or "").strip()
    if section_title:
        label_parts.append(section_title)
    page_number = getattr(item, "page_number", None) or metadata.get("page_number")
    page_numbers = getattr(chunk, "page_numbers", None) or metadata.get("page_numbers")
    if page_number:
        label_parts.append(f"p{page_number}")
    elif isinstance(page_numbers, list) and page_numbers:
        label_parts.append("p" + ",".join(str(page) for page in page_numbers[:3]))
    chunk_index = getattr(item, "chunk_index", None)
    if chunk_index is None:
        chunk_index = getattr(chunk, "chunk_index", None) or metadata.get("chunk_index")
    if chunk_index is not None:
        label_parts.append(f"#{chunk_index}")
    return " | ".join(part for part in label_parts if part) or "document chunk"


def format_document_chunks_for_prompt(
    chunks: list[Any],
    *,
    budget: int | None = None,
) -> tuple[str, dict[str, Any]]:
    """Rank and format retrieved document chunks inside their token budget."""
    max_chunks = max(1, int(getattr(settings, "DOCUMENT_CONTEXT_MAX_CHUNKS", 5) or 5))
    total_results = len(chunks or [])
    if not chunks:
        return "", {
            "total_results": 0,
            "shown_results": 0,
            "ranking": [],
            "token_usage": 0,
            "budget": max(0, int(budget or 0)),
        }

    effective_budget = max(0, int(budget if budget is not None else _allocate_context_source_budgets(
        int(getattr(settings, "CONTEXT_TOTAL_TOKEN_BUDGET", 8000) or 8000)
    )[CONTEXT_SOURCE_DOCUMENTS]))
    if effective_budget <= 0:
        CONTEXT_BUDGET_OVER_LIMIT_TOTAL.labels(type=CONTEXT_SOURCE_DOCUMENTS).inc()
        CONTEXT_BUDGET_UTILIZATION.labels(type=CONTEXT_SOURCE_DOCUMENTS).set(0.0)
        return "", {
            "total_results": total_results,
            "shown_results": 0,
            "ranking": [],
            "token_usage": 0,
            "budget": effective_budget,
        }

    ranked = _rank_document_chunks(list(chunks))
    selected_lines: list[str] = []
    shown = 0
    header = f"Relevant Documents (showing top 0 of {total_results} results):"
    used = estimate_tokens(header)
    ranking_metadata: list[dict[str, Any]] = []

    for item, score in ranked[:max_chunks]:
        chunk = _document_item_chunk(item)
        content = str(getattr(item, "content", "") or getattr(chunk, "content", "") or "").strip()
        if not content:
            continue
        label = _document_label(item)
        base_prefix = f"- [{label}] "
        remaining = effective_budget - used - estimate_tokens(base_prefix)
        if remaining <= 8:
            break
        snippet = _truncate_text_to_token_budget(content, min(remaining, 180))
        line = f"{base_prefix}{snippet}"
        line_tokens = estimate_tokens(line)
        if used + line_tokens > effective_budget:
            line_budget = max(8, effective_budget - used - estimate_tokens(base_prefix))
            snippet = _truncate_text_to_token_budget(content, line_budget)
            line = f"{base_prefix}{snippet}"
            line_tokens = estimate_tokens(line)
        if used + line_tokens > effective_budget:
            break
        selected_lines.append(line)
        used += line_tokens
        shown += 1
        ranking_metadata.append(
            {
                "label": label,
                "score": score,
                "relevance_score": _document_relevance_score(item),
                "recency_boost": _document_recency_boost(item),
                "mastery_gap_boost": _document_mastery_gap_boost(item),
            }
        )

    if shown == 0:
        CONTEXT_BUDGET_OVER_LIMIT_TOTAL.labels(type=CONTEXT_SOURCE_DOCUMENTS).inc()
        CONTEXT_BUDGET_UTILIZATION.labels(type=CONTEXT_SOURCE_DOCUMENTS).set(0.0)
        return "", {
            "total_results": total_results,
            "shown_results": 0,
            "ranking": ranking_metadata,
            "token_usage": 0,
            "budget": effective_budget,
        }

    prompt_text = ""
    usage = 0
    omitted = total_results - shown
    while shown > 0:
        header = f"Relevant Documents (showing top {shown} of {total_results} results):"
        omitted = total_results - shown
        lines = [header]
        if omitted > 0:
            lines.append(f"Summary: included the highest-ranked evidence; {omitted} lower-ranked result(s) omitted.")
        lines.extend(selected_lines[:shown])
        prompt_text = "\n".join(lines)
        usage = estimate_tokens(prompt_text)
        if usage <= effective_budget:
            break
        shown -= 1
        ranking_metadata = ranking_metadata[:shown]

    if shown <= 0:
        item, score = ranked[0]
        chunk = _document_item_chunk(item)
        content = str(getattr(item, "content", "") or getattr(chunk, "content", "") or "").strip()
        label = _document_label(item)
        header = f"Relevant Documents (showing top 1 of {total_results} results):"
        prefix = f"- [{label}] "
        remaining = effective_budget - estimate_tokens(header) - estimate_tokens(prefix)
        if content and remaining > 8:
            snippet = _truncate_text_to_token_budget(content, remaining)
            compact_text = "\n".join([header, f"{prefix}{snippet}"])
            compact_usage = estimate_tokens(compact_text)
            if compact_usage <= effective_budget:
                CONTEXT_BUDGET_UTILIZATION.labels(type=CONTEXT_SOURCE_DOCUMENTS).set(
                    compact_usage / effective_budget
                )
                CONTEXT_BUDGET_OVER_LIMIT_TOTAL.labels(type=CONTEXT_SOURCE_DOCUMENTS).inc()
                return compact_text, {
                    "total_results": total_results,
                    "shown_results": 1,
                    "ranking": [
                        {
                            "label": label,
                            "score": score,
                            "relevance_score": _document_relevance_score(item),
                            "recency_boost": _document_recency_boost(item),
                            "mastery_gap_boost": _document_mastery_gap_boost(item),
                        }
                    ],
                    "token_usage": compact_usage,
                    "budget": effective_budget,
                    "omitted_results": total_results - 1,
                }
        CONTEXT_BUDGET_OVER_LIMIT_TOTAL.labels(type=CONTEXT_SOURCE_DOCUMENTS).inc()
        CONTEXT_BUDGET_UTILIZATION.labels(type=CONTEXT_SOURCE_DOCUMENTS).set(0.0)
        return "", {
            "total_results": total_results,
            "shown_results": 0,
            "ranking": [],
            "token_usage": 0,
            "budget": effective_budget,
        }

    utilization = usage / effective_budget if effective_budget > 0 else 0.0
    CONTEXT_BUDGET_UTILIZATION.labels(type=CONTEXT_SOURCE_DOCUMENTS).set(utilization)
    if usage > effective_budget or shown < total_results:
        CONTEXT_BUDGET_OVER_LIMIT_TOTAL.labels(type=CONTEXT_SOURCE_DOCUMENTS).inc()
    return prompt_text, {
        "total_results": total_results,
        "shown_results": shown,
        "ranking": ranking_metadata,
        "token_usage": usage,
        "budget": effective_budget,
        "omitted_results": omitted,
    }


class ContextBudgetManager:
    """Budget and place runtime context sources for a single LLM call."""

    def __init__(self, total_token_budget: int | None = None) -> None:
        self.total_token_budget = max(
            1,
            int(total_token_budget or getattr(settings, "CONTEXT_TOTAL_TOKEN_BUDGET", 8000) or 8000),
        )

    def allocate(self) -> dict[str, int]:
        return _allocate_context_source_budgets(self.total_token_budget)

    def assemble_prompt(
        self,
        *,
        base_system_prompt: str,
        user_message: str = "",
        conversation_history: list[dict[str, Any]] | None = None,
        document_chunks: list[Any] | None = None,
        document_context: str = "",
        galaxy_knowledge: Any = "",
        task_error_context: Any = "",
        cognitive_profile: Any = "",
    ) -> ContextAssemblyResult:
        raw_budgets = self.allocate()
        shell_tokens = estimate_tokens(base_system_prompt) + estimate_tokens(user_message)
        available_for_sources = max(0, self.total_token_budget - shell_tokens)
        budgets = _scale_budgets_to_available(raw_budgets, available_for_sources)

        selected_history = self._trim_conversation_history(
            conversation_history or [],
            budgets.get(CONTEXT_SOURCE_CONVERSATION, 0),
        )
        galaxy_text = self._section(
            "Retrieved Knowledge",
            _as_prompt_text(galaxy_knowledge),
            budgets.get(CONTEXT_SOURCE_GALAXY, 0),
            CONTEXT_SOURCE_GALAXY,
        )
        task_text = self._section(
            "Task and Error Context",
            _as_prompt_text(task_error_context),
            budgets.get(CONTEXT_SOURCE_TASK_ERROR, 0),
            CONTEXT_SOURCE_TASK_ERROR,
        )
        cognitive_text = self._section(
            "Cognitive Profile",
            _as_prompt_text(cognitive_profile),
            budgets.get(CONTEXT_SOURCE_COGNITIVE, 0),
            CONTEXT_SOURCE_COGNITIVE,
        )
        doc_budget = budgets.get(CONTEXT_SOURCE_DOCUMENTS, 0)
        if document_chunks:
            document_header = "## Retrieved Documents"
            document_body, document_metadata = format_document_chunks_for_prompt(
                document_chunks,
                budget=max(0, doc_budget - estimate_tokens(document_header)),
            )
            document_text = f"## Retrieved Documents\n{document_body}".strip() if document_body else ""
            document_text = _truncate_text_to_token_budget(document_text, doc_budget)
        else:
            raw_document_text = _as_prompt_text(document_context)
            document_text = self._section(
                "Retrieved Documents",
                raw_document_text,
                doc_budget,
                CONTEXT_SOURCE_DOCUMENTS,
            )
            document_metadata = {
                "total_results": 1 if raw_document_text else 0,
                "shown_results": 1 if document_text else 0,
                "token_usage": estimate_tokens(document_text),
                "budget": doc_budget,
            }

        sections = [
            str(base_system_prompt or "").strip(),
            galaxy_text,
            task_text,
            cognitive_text,
            document_text if not document_text.startswith("## Retrieved Documents") else document_text,
        ]
        system_prompt = "\n\n".join(section for section in sections if str(section or "").strip())

        token_usage = {
            CONTEXT_SOURCE_CONVERSATION: estimate_tokens(_serialize(selected_history)),
            CONTEXT_SOURCE_DOCUMENTS: estimate_tokens(document_text),
            CONTEXT_SOURCE_GALAXY: estimate_tokens(galaxy_text),
            CONTEXT_SOURCE_TASK_ERROR: estimate_tokens(task_text),
            CONTEXT_SOURCE_COGNITIVE: estimate_tokens(cognitive_text),
        }
        budget_remaining = {
            source: budgets.get(source, 0) - token_usage.get(source, 0)
            for source in raw_budgets
        }
        for source, budget in budgets.items():
            usage = token_usage.get(source, 0)
            utilization = usage / budget if budget > 0 else 0.0
            CONTEXT_BUDGET_UTILIZATION.labels(type=source).set(utilization)
            if usage > budget:
                CONTEXT_BUDGET_OVER_LIMIT_TOTAL.labels(type=source).inc()

        total_tokens = (
            estimate_tokens(system_prompt)
            + estimate_tokens(_serialize(selected_history))
            + estimate_tokens(user_message)
        )
        if total_tokens > self.total_token_budget:
            CONTEXT_BUDGET_OVER_LIMIT_TOTAL.labels(type="total").inc()
            logger.info(
                "Context budget over total: total_tokens={total_tokens} budget={budget}",
                total_tokens=total_tokens,
                budget=self.total_token_budget,
            )

        logger.info(
            "Context budget allocation: budgets={budgets} usage={usage} total_tokens={total_tokens}/{limit}",
            budgets=budgets,
            usage=token_usage,
            total_tokens=total_tokens,
            limit=self.total_token_budget,
        )

        return ContextAssemblyResult(
            system_prompt=system_prompt,
            conversation_history=selected_history,
            budgets=budgets,
            token_usage=token_usage,
            budget_remaining=budget_remaining,
            metadata={
                "total_token_budget": self.total_token_budget,
                "raw_budgets": raw_budgets,
                "shell_tokens": shell_tokens,
                "available_for_sources": available_for_sources,
                "total_tokens": total_tokens,
                "document_context": document_metadata,
                "placement": {"document_chunks": "last_before_user_message"},
            },
        )

    def _section(self, title: str, content: str, budget: int, source_type: str) -> str:
        text = str(content or "").strip()
        if not text or budget <= 0:
            if text:
                CONTEXT_BUDGET_OVER_LIMIT_TOTAL.labels(type=source_type).inc()
            return ""
        header = f"## {title}"
        available = max(0, budget - estimate_tokens(header))
        trimmed = _truncate_text_to_token_budget(text, available)
        if estimate_tokens(text) > budget:
            CONTEXT_BUDGET_OVER_LIMIT_TOTAL.labels(type=source_type).inc()
            trimmed = f"{trimmed}\nSummary: source truncated to fit its context budget."
        section = f"{header}\n{trimmed}".strip()
        return _truncate_text_to_token_budget(section, budget)

    def _trim_conversation_history(
        self,
        messages: list[dict[str, Any]],
        budget: int,
    ) -> list[dict[str, Any]]:
        if budget <= 0 or not messages:
            if messages:
                CONTEXT_BUDGET_OVER_LIMIT_TOTAL.labels(type=CONTEXT_SOURCE_CONVERSATION).inc()
            return []

        selected_reversed: list[dict[str, Any]] = []
        used = 0
        for message in reversed(messages):
            if not isinstance(message, dict):
                continue
            candidate = dict(message)
            content = str(candidate.get("content") or "")
            token_cost = estimate_tokens(_serialize(candidate))
            if used + token_cost <= budget:
                selected_reversed.append(candidate)
                used += token_cost
                continue
            remaining = budget - used - estimate_tokens(_serialize({**candidate, "content": ""}))
            if remaining > 16:
                candidate["content"] = _truncate_text_to_token_budget(content, remaining)
                while (
                    candidate.get("content")
                    and used + estimate_tokens(_serialize(candidate)) > budget
                ):
                    candidate["content"] = _truncate_text_to_token_budget(
                        str(candidate.get("content") or ""),
                        max(1, estimate_tokens(str(candidate.get("content") or "")) - 4),
                    )
                if used + estimate_tokens(_serialize(candidate)) <= budget:
                    selected_reversed.append(candidate)
            CONTEXT_BUDGET_OVER_LIMIT_TOTAL.labels(type=CONTEXT_SOURCE_CONVERSATION).inc()
            break
        selected_reversed.reverse()
        while selected_reversed and estimate_tokens(_serialize(selected_reversed)) > budget:
            selected_reversed.pop(0)
        return selected_reversed


async def _apply_semantic_gating(
    ranked_items: list[RankedItem[Any]],
    *,
    query_text: str | None,
    section: str,
) -> tuple[list[RankedItem[Any]], dict[str, Any]]:
    metadata: dict[str, Any] = {
        "section": section,
        "applied": False,
        "candidate_count": len(ranked_items),
        "selected_count": len(ranked_items),
    }
    text = str(query_text or "").strip()
    if not text:
        metadata["fallback_reason"] = "missing_query"
        CONTEXT_SEMANTIC_GATING_FALLBACK_TOTAL.labels(reason=metadata["fallback_reason"]).inc()
        return ranked_items, metadata

    rules = _get_semantic_gating_rules()[section]
    candidates = ranked_items[: int(rules["candidate_limit"])]
    if not candidates:
        metadata["fallback_reason"] = "no_candidates"
        CONTEXT_SEMANTIC_GATING_FALLBACK_TOTAL.labels(reason=metadata["fallback_reason"]).inc()
        return ranked_items, metadata

    candidate_texts = [_build_semantic_text(entry.item, section) for entry in candidates]
    if not any(candidate_texts):
        metadata["fallback_reason"] = "empty_candidate_text"
        CONTEXT_SEMANTIC_GATING_FALLBACK_TOTAL.labels(reason=metadata["fallback_reason"]).inc()
        return ranked_items, metadata

    try:
        embeddings = await embedding_service.batch_embeddings(
            [text, *candidate_texts],
            text_type="query",
        )
        if len(embeddings) < len(candidate_texts) + 1:
            raise ValueError("embedding_count_mismatch")
        query_embedding = embeddings[0]
        if not query_embedding or not any(query_embedding):
            raise ValueError("query_embedding_empty")
    except Exception as exc:
        metadata["fallback_reason"] = f"embedding_error:{type(exc).__name__}"
        CONTEXT_SEMANTIC_GATING_FALLBACK_TOTAL.labels(reason=metadata["fallback_reason"]).inc()
        logger.warning(f"Semantic gating failed for {section}: {exc}")
        return ranked_items, metadata

    scored: list[RankedItem[Any]] = []
    threshold = float(rules["threshold"])
    top_k = int(rules["top_k"])
    for idx, entry in enumerate(candidates, start=1):
        semantic_score = cosine_similarity(query_embedding, embeddings[idx])
        final_score = (entry.score * 0.6) + (semantic_score * 0.4)
        if semantic_score >= threshold:
            scored.append(RankedItem(item=entry.item, score=final_score))

    if len(scored) < top_k:
        existing_ids = {getattr(entry.item, "id", None) or getattr(entry.item, "pref_key", None) for entry in scored}
        for entry in candidates:
            identity = getattr(entry.item, "id", None) or getattr(entry.item, "pref_key", None)
            if identity in existing_ids:
                continue
            scored.append(entry)
            if len(scored) >= top_k:
                break

    scored.sort(key=lambda entry: entry.score, reverse=True)
    selected = scored[:top_k] or ranked_items
    metadata["applied"] = True
    metadata["selected_count"] = len(selected)
    metadata["top_score"] = selected[0].score if selected else 0.0
    CONTEXT_SEMANTIC_GATING_APPLIED_TOTAL.labels(section=section).inc()
    return selected, metadata


@dataclass
class ContextPack:
    user_id: UUID
    intent: str
    preferences: dict[str, Any]
    goals: list[dict[str, Any]]
    episodic_memories: list[dict[str, Any]]
    budgets: dict[str, int]
    token_usage: dict[str, int]
    budget_remaining: dict[str, int]
    pack_id: UUID | None = None
    metadata: dict[str, Any] | None = None
    plan_context: dict[str, Any] | None = None  # PlanScope context
    context_focus: dict[str, Any] | None = None
    context_briefing_note: str | None = None

    def to_prompt_context(self) -> dict[str, Any]:
        result = {
            "preferences": self.preferences,
            "active_goals": self.goals,
            "episodic_memories": self.episodic_memories,
            "past_session_memory": self.episodic_memories,
            "context_pack": {
                "intent": self.intent,
                "budgets": self.budgets,
                "token_usage": self.token_usage,
                "budget_remaining": self.budget_remaining,
                "pack_id": str(self.pack_id) if self.pack_id else None,
                "metadata": self.metadata or {},
            },
        }
        if self.context_focus:
            result["context_focus"] = self.context_focus
        if self.context_briefing_note:
            result["context_briefing_note"] = self.context_briefing_note
        # Include plan_context if present (non-empty)
        if self.plan_context:
            result["plan_context"] = self.plan_context
        return result


@dataclass(frozen=True)
class DocumentContextControls:
    mode: str
    enabled: bool
    live: bool
    ratio: float
    max_chunks: int
    similarity_threshold: float
    recency_boost_days: int
    budget_target_tokens: int

    def to_metadata(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "enabled": self.enabled,
            "live": self.live,
            "ratio": self.ratio,
            "max_chunks": self.max_chunks,
            "similarity_threshold": self.similarity_threshold,
            "recency_boost_days": self.recency_boost_days,
            "budget_target_tokens": self.budget_target_tokens,
        }


async def _resolve_document_context_controls(budgets: dict[str, int]) -> DocumentContextControls:
    mode = await AuroraDocContextKillSwitchService().get_mode()
    ratio = min(1.0, max(0.0, float(settings.DOCUMENT_CONTEXT_RATIO or 0.0)))
    max_chunks = max(0, int(settings.DOCUMENT_CONTEXT_MAX_CHUNKS or 0))
    similarity_threshold = min(1.0, max(0.0, float(settings.DOCUMENT_CONTEXT_SIMILARITY_THRESHOLD or 0.0)))
    recency_boost_days = max(0, int(settings.DOCUMENT_CONTEXT_RECENCY_BOOST_DAYS or 0))
    total_budget = sum(max(0, int(value or 0)) for value in budgets.values())
    return DocumentContextControls(
        mode=mode,
        enabled=mode in {"shadow", "live"},
        live=mode == "live",
        ratio=ratio,
        max_chunks=max_chunks,
        similarity_threshold=similarity_threshold,
        recency_boost_days=recency_boost_days,
        budget_target_tokens=int(total_budget * ratio),
    )


class ContextPackBuilder:
    def __init__(
        self,
        db: AsyncSession,
        scheduler: ContextBudgetScheduler | None = None,
        redis=None,
    ) -> None:
        self.db = db
        self.memory_service = MemoryService(db)
        self.preference_service = PreferenceService(db, redis)
        self.scheduler = scheduler or ContextBudgetScheduler(db=db)
        self.redis = redis

    async def build(
        self,
        user_id: UUID,
        intent: str,
        request_id: str | None = None,
        trace_id: str | None = None,
        plan_id: UUID | None = None,
        query_text: str | None = None,
        focus_mode: str | None = None,
        route_intent: str | None = None,
    ) -> ContextPack:
        rollout_enabled = True
        if settings.ENABLE_LTM_ROLLOUT:
            rollout_service = LtmRolloutService(self.db)
            rollout_enabled = await rollout_service.is_enabled(user_id)

        budgets = await self.scheduler.allocate(intent, user_id=user_id)
        document_context_controls = await _resolve_document_context_controls(budgets)
        CONTEXT_PACK_BUILD.labels(intent=intent).inc()
        CONTEXT_PACK_INTENT.labels(intent=intent).inc()

        # Build enriched plan context with UserScope cognitive profile if plan_id is provided
        plan_context: dict[str, Any] | None = None
        if plan_id:
            try:
                plan_builder = PlanContextBuilder(self.db, self.redis)
                # Use build_enriched to include UserScope cognitive insights
                plan_context = await plan_builder.build_enriched(
                    user_id,
                    plan_id,
                    include_cognitive_profile=True,
                    include_behavior_patterns=True,
                )
            except Exception as e:
                logger.warning(f"Failed to build enriched plan context: {e}")
                # Fallback to basic plan context
                try:
                    plan_context = await plan_builder.build(user_id, plan_id)
                except Exception as e2:
                    logger.warning(f"Failed to build basic plan context: {e2}")
                    plan_context = None

        focus_decision = None
        if settings.ENABLE_CONTEXT_FOCUSING:
            focus_resolver = ContextFocusResolver()
            focus_decision = focus_resolver.resolve(
                user_message=str(query_text or ""),
                route_intent=route_intent or intent,
                plan_context=plan_context,
                cognitive_insights=None,
                force_focus_mode=focus_mode,
            )
            budgets = _reweight_budgets(budgets, focus_decision.focus_mode)

        conflict_enabled = settings.ENABLE_MEMORY_CONFLICT_RESOLUTION and rollout_enabled
        resolver = MemoryConflictResolver() if conflict_enabled else None

        preference_records = await self.memory_service.list_preference_records(user_id)
        goals = await self.memory_service.list_active_goals(user_id)
        episodic = await self.memory_service.list_recent_episodic(user_id, limit=20)
        pref_history: list[Any] = []
        if conflict_enabled:
            pref_history = await self.memory_service.list_preference_history(user_id)

        metadata: dict[str, Any] = {
            "document_context_controls": document_context_controls.to_metadata(),
        }
        ranking_enabled = settings.ENABLE_CONTEXT_RANKING and rollout_enabled
        conflicts: list[dict[str, Any]] = []
        weights: dict[str, float] | None = None
        if ranking_enabled and settings.ENABLE_PERSONALIZED_RANKING and rollout_enabled:
            policy_service = MemoryRankPolicyService(self.db)
            weights = await policy_service.get_policy(intent, user_id)

        if ranking_enabled:
            ranked_preferences = rank_items(preference_records, kind="preferences", weights=weights)
            ranked_goals = rank_items(goals, kind="goals", weights=weights)
            ranked_episodic = rank_items(episodic, kind="episodic", weights=weights)

            selected_goals = _select_with_diversity(
                ranked_goals,
                settings.CONTEXT_RANKING_SOFT_CAP_GOALS,
                lambda item: item.status,
            )
            selected_episodic = _select_with_diversity(
                ranked_episodic,
                settings.CONTEXT_RANKING_SOFT_CAP_EPISODIC,
                lambda item: (item.tags or [None])[0],
            )

            resolved_pref_records = preference_records
            resolved_goals = [entry.item for entry in selected_goals]
            resolved_episodic = [entry.item for entry in selected_episodic]
        else:
            preference_records.sort(
                key=lambda item: (item.evidence_score or 0.0, item.updated_at),
                reverse=True,
            )
            goals.sort(
                key=lambda item: (item.evidence_score or 0.0, item.updated_at),
                reverse=True,
            )
            episodic.sort(
                key=lambda item: (item.evidence_score or 0.0, item.occurred_at),
                reverse=True,
            )
            resolved_pref_records = preference_records
            resolved_goals = goals
            resolved_episodic = episodic

        if conflict_enabled and resolver is not None:
            preferences, resolved_pref_records, pref_conflicts = resolver.resolve_preferences(
                {item.pref_key: item.pref_value for item in preference_records},
                pref_history or resolved_pref_records,
            )
            resolved_goals, goal_conflicts = resolver.resolve_goals(resolved_goals)
            resolved_episodic, episodic_conflicts = resolver.resolve_episodic(resolved_episodic)
            resolved_goals, resolved_episodic, cross_conflicts = resolver.resolve_cross_type(
                resolved_goals,
                resolved_episodic,
            )
            conflicts.extend(pref_conflicts)
            conflicts.extend(goal_conflicts)
            conflicts.extend(episodic_conflicts)
            conflicts.extend(cross_conflicts)
        else:
            preferences = {item.pref_key: item.pref_value for item in preference_records}

        ranked_preferences = (
            rank_items(resolved_pref_records, kind="preferences", weights=weights)
            if ranking_enabled
            else _normalized_ranked(resolved_pref_records)
        )
        ranked_goals = (
            rank_items(resolved_goals, kind="goals", weights=weights)
            if ranking_enabled
            else _normalized_ranked(resolved_goals)
        )
        ranked_episodic = (
            rank_items(resolved_episodic, kind="episodic", weights=weights)
            if ranking_enabled
            else _normalized_ranked(resolved_episodic)
        )

        semantic_metadata: dict[str, Any] = {}
        if focus_decision and focus_decision.semantic_gating_enabled and settings.ENABLE_CONTEXT_SEMANTIC_GATING:
            ranked_preferences, semantic_metadata["preferences"] = await _apply_semantic_gating(
                ranked_preferences,
                query_text=query_text,
                section="preferences",
            )
            ranked_goals, semantic_metadata["goals"] = await _apply_semantic_gating(
                ranked_goals,
                query_text=query_text,
                section="goals",
            )
            ranked_episodic, semantic_metadata["episodic"] = await _apply_semantic_gating(
                ranked_episodic,
                query_text=query_text,
                section="episodic",
            )

        preferences = {entry.item.pref_key: entry.item.pref_value for entry in ranked_preferences}
        goal_payloads = [
            {
                "id": str(entry.item.id),
                "title": entry.item.title,
                "status": entry.item.status,
                "target_date": entry.item.target_date,
            }
            for entry in ranked_goals
        ]
        episodic_payloads = [
            {
                "id": str(entry.item.id),
                "summary": entry.item.summary,
                "subject_type": str(getattr(entry.item, "subject_type", "") or "").strip(),
                "source_type": str(getattr(entry.item, "source_type", "") or "").strip(),
                "source_lane": str(getattr(entry.item, "source_lane", "") or "").strip(),
                "occurred_at": entry.item.occurred_at,
                "importance_score": entry.item.importance_score,
                "tags": getattr(entry.item, "tags", None) or [],
            }
            for entry in ranked_episodic
        ]

        pref_scores = {entry.item.pref_key: entry.score for entry in ranked_preferences}
        goal_scores = {str(entry.item.id): entry.score for entry in ranked_goals}
        episodic_scores = {str(entry.item.id): entry.score for entry in ranked_episodic}

        profile_prefs = await self.preference_service.get_preferences(user_id)
        profile_keys = set((profile_prefs.inferred or {}).keys())
        explicit_profile_prefs = dict(profile_prefs.explicit or {})
        for key, value in explicit_profile_prefs.items():
            default_value = PreferenceService.DEFAULT_EXPLICIT.get(key, object())
            if key not in PreferenceService.DEFAULT_EXPLICIT or value != default_value:
                profile_keys.add(key)
        if profile_keys:
            ranked_preferences = [entry for entry in ranked_preferences if entry.item.pref_key not in profile_keys]
            preferences = {key: value for key, value in preferences.items() if key not in profile_keys}
            pref_scores = {key: score for key, score in pref_scores.items() if key not in profile_keys}

        pref_budget = budgets.get("preferences", 0)
        goals_budget = budgets.get("goals", 0)
        episodic_budget = budgets.get("episodic", 0)

        original_usage = {
            "preferences": estimate_tokens(_serialize(preferences)),
            "goals": estimate_tokens(_serialize(goal_payloads)),
            "episodic": estimate_tokens(_serialize(episodic_payloads)),
        }

        if ranking_enabled:
            trimmed_preferences, pref_scores = _trim_ranked_preferences(ranked_preferences, pref_budget)
            trimmed_goals, goal_scores = _trim_ranked_list(goal_payloads, goal_scores, goals_budget)
            trimmed_episodic, episodic_scores = _trim_ranked_list(
                episodic_payloads,
                episodic_scores,
                episodic_budget,
            )
            trimmed_pref_scores = {key: pref_scores.get(key, 0.0) for key in trimmed_preferences}
        else:
            trimmed_preferences = _trim_preferences(preferences, pref_budget)
            trimmed_goals = _trim_list(goal_payloads, goals_budget)
            trimmed_episodic = _trim_list(episodic_payloads, episodic_budget)
            trimmed_pref_scores = {}

        await self._mark_consumed_memory_records(
            ranked_preferences=ranked_preferences,
            ranked_goals=ranked_goals,
            ranked_episodic=ranked_episodic,
            trimmed_preferences=trimmed_preferences,
            trimmed_goals=trimmed_goals,
            trimmed_episodic=trimmed_episodic,
        )

        token_usage = {
            "preferences": estimate_tokens(_serialize(trimmed_preferences)),
            "goals": estimate_tokens(_serialize(trimmed_goals)),
            "episodic": estimate_tokens(_serialize(trimmed_episodic)),
        }
        budget_remaining = {
            "preferences": pref_budget - token_usage["preferences"],
            "goals": goals_budget - token_usage["goals"],
            "episodic": episodic_budget - token_usage["episodic"],
        }

        if ranking_enabled:
            metadata["ranking"] = {
                "preferences": [
                    {"key": key, "score": trimmed_pref_scores.get(key, 0.0)}
                    for key in list(trimmed_preferences.keys())[:10]
                ],
                "goals": [
                    {"id": payload.get("id"), "score": goal_scores.get(payload.get("id"), 0.0)}
                    for payload in trimmed_goals[:10]
                ],
                "episodic": [
                    {"id": payload.get("id"), "score": episodic_scores.get(payload.get("id"), 0.0)}
                    for payload in trimmed_episodic[:10]
                ],
            }
        if semantic_metadata:
            metadata["semantic_gating"] = semantic_metadata
        if conflicts:
            metadata["conflicts"] = conflicts
        if focus_decision:
            metadata["context_focus"] = focus_decision.to_dict()

        preference_source_records = resolved_pref_records if conflict_enabled else preference_records
        goal_source_records = resolved_goals if conflict_enabled else goals
        episodic_source_records = resolved_episodic if conflict_enabled else episodic

        def _iso(dt_value):
            return dt_value.isoformat() if dt_value else None

        def _top_by_score(items, limit=3):
            return sorted(items, key=lambda item: getattr(item, "evidence_score", 0.0), reverse=True)[:limit]

        evidence_summary = {
            "preferences": [
                {
                    "key": item.pref_key,
                    "score": item.evidence_score,
                    "updated_at": _iso(getattr(item, "updated_at", None)),
                }
                for item in _top_by_score(preference_source_records)
            ],
            "goals": [
                {
                    "id": str(item.id),
                    "title": item.title,
                    "score": item.evidence_score,
                    "updated_at": _iso(getattr(item, "updated_at", None)),
                    "target_date": _iso(item.target_date),
                }
                for item in _top_by_score(goal_source_records)
            ],
            "episodic": [
                {
                    "id": str(item.id),
                    "summary": item.summary[:60],
                    "score": item.evidence_score,
                    "updated_at": _iso(getattr(item, "updated_at", None)),
                    "occurred_at": _iso(item.occurred_at),
                }
                for item in _top_by_score(episodic_source_records)
            ],
        }

        if evidence_summary["preferences"] or evidence_summary["goals"] or evidence_summary["episodic"]:
            metadata["evidence_summary"] = evidence_summary

        context_briefing_note = ""
        if focus_decision and settings.ENABLE_CONTEXT_BRIEFING:
            context_briefing_note = build_context_briefing_note(
                decision=focus_decision,
                plan_context=plan_context,
                user_context={
                    "llm_profile": {},
                },
                focused_memory={
                    "preferences": trimmed_preferences,
                    "active_goals": trimmed_goals,
                    "episodic_memories": trimmed_episodic,
                },
            )
            if context_briefing_note:
                CONTEXT_BRIEFING_GENERATED_TOTAL.labels(
                    focus_mode=focus_decision.focus_mode,
                ).inc()

        pack_id = None
        if settings.ENABLE_CONTEXT_PACK_TELEMETRY:
            trimmed_goal_ids = {payload.get("id") for payload in trimmed_goals}
            trimmed_episodic_ids = {payload.get("id") for payload in trimmed_episodic}
            pref_scores = [
                item.evidence_score for item in preference_source_records if item.pref_key in trimmed_preferences
            ]
            goal_scores = [item.evidence_score for item in goal_source_records if str(item.id) in trimmed_goal_ids]
            episodic_scores = [
                item.evidence_score for item in episodic_source_records if str(item.id) in trimmed_episodic_ids
            ]
            scores = [score for score in pref_scores + goal_scores + episodic_scores if score is not None]
            evidence_avg = (sum(scores) / len(scores)) if scores else None

            telemetry = ContextPackTelemetryService(self.db)
            pack_id = await telemetry.record_run(
                user_id=user_id,
                intent=intent,
                budgets=budgets,
                token_usage=token_usage,
                memory_counts={
                    "preferences": len(trimmed_preferences),
                    "goals": len(trimmed_goals),
                    "episodic": len(trimmed_episodic),
                },
                evidence_score_avg=evidence_avg,
                request_id=request_id,
                trace_id=trace_id,
            )

        for section, usage in original_usage.items():
            budget = budgets.get(section, 0)
            if usage > budget:
                CONTEXT_PACK_OVER_BUDGET.labels(intent=intent, section=section).inc()
                logger.info(
                    "Context pack trimmed {section}: usage={usage} budget={budget}",
                    section=section,
                    usage=usage,
                    budget=budget,
                )

        return ContextPack(
            user_id=user_id,
            intent=intent,
            preferences=trimmed_preferences,
            goals=trimmed_goals,
            episodic_memories=trimmed_episodic,
            budgets=budgets,
            token_usage=token_usage,
            budget_remaining=budget_remaining,
            pack_id=pack_id,
            metadata=metadata or None,
            plan_context=plan_context,
            context_focus=focus_decision.to_dict() if focus_decision else None,
            context_briefing_note=context_briefing_note or None,
        )

    async def _mark_consumed_memory_records(
        self,
        *,
        ranked_preferences: list[RankedItem[Any]],
        ranked_goals: list[RankedItem[Any]],
        ranked_episodic: list[RankedItem[Any]],
        trimmed_preferences: dict[str, Any],
        trimmed_goals: list[dict[str, Any]],
        trimmed_episodic: list[dict[str, Any]],
    ) -> None:
        if not settings.ENABLE_MEMORY_GOVERNANCE:
            return

        touched = False
        consumed_at = _utcnow()

        preference_ids = [
            entry.item.id
            for entry in ranked_preferences
            if getattr(entry.item, "pref_key", None) in trimmed_preferences
        ]
        if preference_ids:
            from app.models.memory import MemoryPreference

            await self.db.execute(
                update(MemoryPreference)
                .where(MemoryPreference.id.in_(preference_ids))
                .values(last_consumed_at=consumed_at)
            )
            touched = True

        goal_ids = []
        for payload in trimmed_goals:
            raw_id = payload.get("id")
            if not raw_id:
                continue
            try:
                goal_ids.append(uuid.UUID(str(raw_id)))
            except Exception:
                continue
        if goal_ids:
            from app.models.memory import MemoryGoal

            await self.db.execute(
                update(MemoryGoal).where(MemoryGoal.id.in_(goal_ids)).values(last_consumed_at=consumed_at)
            )
            touched = True

        episodic_ids = []
        for payload in trimmed_episodic:
            raw_id = payload.get("id")
            if not raw_id:
                continue
            try:
                episodic_ids.append(uuid.UUID(str(raw_id)))
            except Exception:
                continue
        if episodic_ids:
            from app.models.memory import EpisodicMemory

            await self.db.execute(
                update(EpisodicMemory).where(EpisodicMemory.id.in_(episodic_ids)).values(last_consumed_at=consumed_at)
            )
            touched = True

        if touched:
            await self.db.commit()
