from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any, Mapping
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
    DECISION_CONTEXT_SIGNAL_DEGRADED_TOTAL,
)
from app.core.citation_markers import (
    CITATION_GUIDE,
    annotate_citation_markers,
    is_no_material_sentinel,
)
from app.core.context_budget import ContextBudgetScheduler
from app.core.context_ranker import RankedItem, rank_items
from app.core.decision_context import (
    DEFAULT_DECISION_SIGNAL_FIELDS,
    ContextItemDescriptor,
    DecisionContext,
    DecisionStateSignal,
    hash_query_text,
    memory_ref,
    plan_ref,
    state_signal_from_envelope,
)
from app.core.plan_context import PlanContextBuilder
from app.orchestration.context_focus import (
    ContextFocusResolver,
    build_context_briefing_note,
    cosine_similarity,
    get_focus_profile,
)
from app.orchestration.context_sources import (
    SOURCE_CATEGORIES,
    EventSourceAdapter,
    KnowledgeSourceAdapter,
    MemorySourceAdapter,
    StateSourceAdapter,
    assemble_manifest,
    detect_preference_key_overrides,
    item_source_category,
    memory_record_is_seed,
    normalize_section,
)
from app.services.aurora_doc_context_kill_switch_service import AuroraDocContextKillSwitchService
from app.services.conflict_resolution_context import (
    UNRESOLVED_FETCH_LIMIT,
    build_conflict_resolution_context,
    build_record_index,
    to_prompt_payload,
)
from app.services.conflict_resolver_service import ConflictResolverService
from app.services.context_pack_telemetry_service import ContextPackTelemetryService
from app.services.embedding_service import embedding_service
from app.services.ltm_rollout_service import LtmRolloutService
from app.services.memory_conflict_resolver import MemoryConflictResolver
from app.services.memory_rank_policy_service import MemoryRankPolicyService
from app.services.memory_retrieval_prefilter import (
    PURPOSE_LLM_CONTEXT,
    build_retrieval_context,
    prefilter_candidates,
)
from app.services.memory_service import MemoryService
from app.services.memory_use_selfcheck import (
    MemoryUseCandidate,
    SelfCheckContext,
    evaluate_memory_use_gate,
)
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


# Memory payloads carry client-only metadata (rank_factors / correction_actions /
# claim_status / ids) that never renders into the LLM prompt. The section budgets
# bound *prompt* tokens, so trimming must measure the prompt-facing projection —
# otherwise one enriched episodic payload (~580 envelope tokens vs chat default
# budget 500) is always dropped and the cross-session memory read path dies.
_PROMPT_FACING_FIELDS: dict[str, tuple[str, ...]] = {
    "episodic": (
        "summary",
        "subject_type",
        "source_type",
        "source_lane",
        "occurred_at",
        "tags",
        "confidence",
        "user_confirmed",
    ),
    "goals": ("title", "status", "target_date"),
}


def _budget_view(payload: dict[str, Any], section: str | None) -> dict[str, Any]:
    """Project a payload onto the fields the prompt actually renders."""
    fields = _PROMPT_FACING_FIELDS.get(str(section or ""))
    if not fields:
        return payload
    return {key: payload[key] for key in fields if payload.get(key) not in (None, "", [])}


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


def _trim_list(items: list[dict[str, Any]], budget: int, section: str | None = None) -> list[dict[str, Any]]:
    trimmed: list[dict[str, Any]] = []
    used = 0
    for item in items:
        item_tokens = estimate_tokens(_serialize(_budget_view(item, section)))
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
    section: str | None = None,
) -> tuple[list[dict[str, Any]], dict[str, float]]:
    entries: list[dict[str, Any]] = []
    total = 0
    for payload in payloads:
        item_id = payload.get("id")
        score = scores.get(item_id, 0.0)
        tokens = estimate_tokens(_serialize(_budget_view(payload, section)))
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


def _memory_evidence_types(item: Any) -> set[str]:
    refs = getattr(item, "evidence_refs", None) or []
    if not isinstance(refs, list):
        return set()
    return {str(ref.get("type") or "").strip().lower() for ref in refs if isinstance(ref, dict)}


def _is_inferred_memory(item: Any) -> bool:
    source_lane = str(getattr(item, "source_lane", "") or "").strip().lower()
    source_type = str(getattr(item, "source_type", "") or "").strip().lower()
    return (
        source_lane == "inferred_extraction"
        or source_type == "ai_inferred"
        or "ai_inferred" in _memory_evidence_types(item)
    )


def _memory_claim_status(item: Any) -> str:
    if _is_inferred_memory(item):
        return "inferred"
    if bool(getattr(item, "evidence_missing", False)):
        return "needs_evidence"
    if int(getattr(item, "correction_count", 0) or 0) > 0:
        return "user_corrected"
    confidence = getattr(item, "confidence", None)
    if confidence is not None:
        try:
            if float(confidence) < 0.5:
                return "uncertain"
        except (TypeError, ValueError):
            pass
    return "confirmed"


def _memory_source_label(item: Any) -> str:
    status = _memory_claim_status(item)
    if status == "inferred":
        return "AI 推断，待你确认"
    if status == "needs_evidence":
        return "证据不足，建议核对"
    if status == "user_corrected":
        return "已按你的纠错降权"
    if status == "uncertain":
        return "低置信度记忆"
    return "已确认记忆"


def _memory_correction_actions(kind: str, memory_id: str) -> list[dict[str, Any]]:
    return [
        {
            "id": f"inspect_{kind}_{memory_id}",
            "type": "inspect",
            "label": "查看依据",
            "method": "GET",
            "endpoint": f"/memory/{'episodic' if kind == 'episodic' else kind + 's'}",
            "payload": {"type": kind, "id": memory_id},
        },
        {
            "id": f"lower_confidence_{kind}_{memory_id}",
            "type": "correct",
            "label": "不太对，降低置信度",
            "method": "POST",
            "endpoint": "/memory/correct",
            "payload": {"type": kind, "id": memory_id, "action": "lower_confidence"},
        },
        {
            "id": f"reject_{kind}_{memory_id}",
            "type": "correct",
            "label": "不是事实，撤回",
            "method": "POST",
            "endpoint": "/memory/correct",
            "payload": {"type": kind, "id": memory_id, "action": "reject"},
        },
    ]


def _memory_rank_factors(item: Any, score: float) -> dict[str, Any]:
    return {
        "score": score,
        "evidence_score": getattr(item, "evidence_score", None),
        "confidence": getattr(item, "confidence", None),
        "correction_count": int(getattr(item, "correction_count", 0) or 0),
        "importance_score": getattr(item, "importance_score", None),
        "goal_linked": bool(
            getattr(item, "linked_goal_id", None)
            or getattr(item, "linked_plan_id", None)
            or getattr(item, "linked_task_id", None)
            or getattr(item, "semantic_key", None)
            or _memory_evidence_types(item).intersection({"goal", "plan", "task", "practice_outcome", "error"})
        ),
        "claim_status": _memory_claim_status(item),
    }


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

# R2-final(mr4) 回显保底：材料注入 user 消息时的置顶声明，明确来源与优先级，
# 压制 qwen3.8-flash 把注入材料当无关系统文本忽略、回复"没看到资料"的失败模式。
_DOCUMENT_NEAR_USER_NOTE = "（系统注：本轮已注入你上传的资料原文，回答必须优先引用）"


@dataclass(frozen=True)
class ContextAssemblyResult:
    system_prompt: str
    conversation_history: list[dict[str, Any]]
    budgets: dict[str, int]
    token_usage: dict[str, int]
    budget_remaining: dict[str, int]
    metadata: dict[str, Any]
    # R2-final(mr4/a2): 注入材料不再进 system prompt，改为紧邻最后一条 user
    # 消息注入。user_message 是给 LLM 的最终消息（含材料前缀，无材料时等于
    # 原始输入）；document_block 是实际注入的材料块原文（供 review/reflection
    # 继承上下文时复用）。
    user_message: str = ""
    document_block: str = ""


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

    effective_budget = max(
        0,
        int(
            budget
            if budget is not None
            else _allocate_context_source_budgets(int(getattr(settings, "CONTEXT_TOTAL_TOKEN_BUDGET", 8000) or 8000))[
                CONTEXT_SOURCE_DOCUMENTS
            ]
        ),
    )
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
    # C-06 knowledge JIT：预算内放不下的低排名切片 → references 索引块
    # （身份行可追溯，行首 "·" 不污染 C-04 [S#] 序号识别面）。计入同一
    # 预算的适配循环；开关关闭时与旧行为逐字节一致。
    jit_references_enabled = bool(getattr(settings, "ENABLE_KNOWLEDGE_JIT", False))

    def _references_block(from_index: int) -> str:
        if not jit_references_enabled:
            return ""
        from app.core.knowledge_jit import build_omitted_chunk_references

        labels = [_document_label(entry[0]) for entry in ranked[from_index:]]
        return build_omitted_chunk_references(
            labels,
            max_references=int(getattr(settings, "KNOWLEDGE_JIT_MAX_REFERENCES", 8) or 8),
        )

    while shown > 0:
        header = f"Relevant Documents (showing top {shown} of {total_results} results):"
        omitted = total_results - shown
        lines = [header]
        if omitted > 0:
            lines.append(f"Summary: included the highest-ranked evidence; {omitted} lower-ranked result(s) omitted.")
        lines.extend(selected_lines[:shown])
        references_block = _references_block(shown) if omitted > 0 else ""
        if references_block:
            lines.append(references_block)
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
                CONTEXT_BUDGET_UTILIZATION.labels(type=CONTEXT_SOURCE_DOCUMENTS).set(compact_usage / effective_budget)
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
    """Budget and place runtime context sources for a single LLM call.

    C-06：总预算解析顺序——显式 ``total_token_budget``（向后兼容，既有
    调用点/测试不变）> tier × decision-type 矩阵
    （``ENABLE_CONTEXT_BUDGET_MATRIX``，``core/context_budget_matrix.py``，
    经 ``CONTEXT_TOTAL_TOKEN_BUDGET`` 硬顶钳制）> settings 单值（旧行为）。
    """

    def __init__(
        self,
        total_token_budget: int | None = None,
        *,
        tier: str | None = None,
        decision_type: str | None = None,
    ) -> None:
        if total_token_budget:
            resolved = max(1, int(total_token_budget))
        elif getattr(settings, "ENABLE_CONTEXT_BUDGET_MATRIX", False):
            from app.core.context_budget_matrix import resolve_total_budget

            resolved = resolve_total_budget(
                tier or "free",
                decision_type or "chat",
                matrix_overrides=getattr(settings, "CONTEXT_BUDGET_MATRIX_JSON", "") or None,
            )
        else:
            resolved = max(1, int(getattr(settings, "CONTEXT_TOTAL_TOKEN_BUDGET", 8000) or 8000))
        self.total_token_budget = resolved
        self.tier = tier or "free"
        self.decision_type = decision_type or "chat"

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
        # C-06 knowledge JIT：大型知识源只注入 top chunks + references（可经
        # retrieve_user_material 按需 fetch）；小知识源原样透传（零回归）。
        _galaxy_raw = _as_prompt_text(galaxy_knowledge)
        knowledge_jit_metadata: dict[str, Any] | None = None
        if getattr(settings, "ENABLE_KNOWLEDGE_JIT", False) and _galaxy_raw:
            from app.core.knowledge_jit import build_jit_knowledge

            # references 段要与 top chunks 同生共死：给它们预留专项预算，
            # 否则 _section 的尾部截断会先把 references（可追溯性所在）裁掉。
            _galaxy_budget = budgets.get(CONTEXT_SOURCE_GALAXY, 0)
            _reference_reserve = 260 if _galaxy_budget > 400 else max(0, _galaxy_budget // 4)
            _keep_top = max(
                64,
                min(
                    int(getattr(settings, "KNOWLEDGE_JIT_KEEP_TOP_TOKENS", 600) or 600),
                    _galaxy_budget - _reference_reserve,
                ),
            )
            _jit = build_jit_knowledge(
                _galaxy_raw,
                full_load_max_tokens=min(
                    int(getattr(settings, "KNOWLEDGE_JIT_FULL_LOAD_MAX_TOKENS", 1200) or 1200),
                    max(1, _galaxy_budget),
                ),
                keep_top_tokens=_keep_top,
                max_references=int(getattr(settings, "KNOWLEDGE_JIT_MAX_REFERENCES", 8) or 8),
            )
            if _jit.applied:
                _galaxy_raw = _jit.text
                knowledge_jit_metadata = _jit.to_metadata()
        galaxy_text = self._section(
            "Retrieved Knowledge",
            _galaxy_raw,
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
            # R2-final(mr4)：正文改为紧邻 user 消息注入（见下方 document_block），
            # 标题保留自述口径让模型知道这是用户上传资料原文。
            document_text = self._section(
                "Retrieved Documents（用户上传资料原文）",
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
        ]
        system_prompt = "\n\n".join(section for section in sections if str(section or "").strip())

        # R2-final(mr4/a2): 注入材料（检索切片 / 文档原文）从 system prompt 挪到
        # 最后一条 user 消息前缀。原 placement 元数据写着 "last_before_user_message"
        # 但实际在 system prompt 尾部、距 user 消息隔大量指令，qwen3.8-flash 注意力
        # 不足时偶发"没看到资料/没有记录"（A/B 测试材料紧邻 user 消息则完美引用）。
        # 兑现 placement：材料块 + 回显保底声明紧贴用户问题，同条消息内保证近邻。
        #
        # C-04：在近邻注入之上加确定性引用标记层（[S#]）——
        # 1. 空检索哨兵块（"无相关材料"）不是材料：不得套"已注入资料必须引用"
        #    的置顶声明（与哨兵的反幻觉口径互相矛盾、诱导硬引不存在的材料），
        #    只透传哨兵原文；
        # 2. 有序号标记的材料块改写为 [S#] 并附「用到才引」引导（引用格式 +
        #    不硬引约束），给引用率与 faithfulness 一个确定性解析锚点。
        if document_text and is_no_material_sentinel(document_text):
            document_block = document_text
            citation_markers: list[dict[str, Any]] = []
            llm_user_message = f"{document_block}\n\n---\n\n{user_message}"
        else:
            document_block, citation_markers = annotate_citation_markers(document_text)
            if document_block:
                near_user_note = _DOCUMENT_NEAR_USER_NOTE
                if citation_markers:
                    near_user_note = f"{_DOCUMENT_NEAR_USER_NOTE}\n{CITATION_GUIDE}"
                llm_user_message = f"{near_user_note}\n\n{document_block}\n\n---\n\n{user_message}"
            else:
                llm_user_message = user_message

        token_usage = {
            CONTEXT_SOURCE_CONVERSATION: estimate_tokens(_serialize(selected_history)),
            CONTEXT_SOURCE_DOCUMENTS: estimate_tokens(document_text),
            CONTEXT_SOURCE_GALAXY: estimate_tokens(galaxy_text),
            CONTEXT_SOURCE_TASK_ERROR: estimate_tokens(task_text),
            CONTEXT_SOURCE_COGNITIVE: estimate_tokens(cognitive_text),
        }
        budget_remaining = {source: budgets.get(source, 0) - token_usage.get(source, 0) for source in raw_budgets}
        for source, budget in budgets.items():
            usage = token_usage.get(source, 0)
            utilization = usage / budget if budget > 0 else 0.0
            CONTEXT_BUDGET_UTILIZATION.labels(type=source).set(utilization)
            if usage > budget:
                CONTEXT_BUDGET_OVER_LIMIT_TOTAL.labels(type=source).inc()

        total_tokens = (
            estimate_tokens(system_prompt)
            + estimate_tokens(_serialize(selected_history))
            + estimate_tokens(llm_user_message)
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
            user_message=llm_user_message,
            document_block=document_block,
            metadata={
                "total_token_budget": self.total_token_budget,
                "raw_budgets": raw_budgets,
                "shell_tokens": shell_tokens,
                "available_for_sources": available_for_sources,
                "total_tokens": total_tokens,
                "document_context": document_metadata,
                "placement": {
                    "document_chunks": "last_before_user_message",
                    "document_context": "last_before_user_message",
                    "injection_surface": "user_message_prefix",
                },
                # C-04：确定性引用标记（过滤后实际注入材料的 [S#] 锚点）与
                # 引导开关，供 retrieved vs cited vs answer-supported 对照。
                "citation_markers": [entry["marker"] for entry in citation_markers],
                "citation_guided": bool(citation_markers),
                "no_material_sentinel": bool(document_text) and is_no_material_sentinel(document_text),
                # C-06：knowledge JIT 生效记录（None = 未触发/小知识源透传）。
                "knowledge_jit": knowledge_jit_metadata,
                "budget_matrix": {
                    "tier": self.tier,
                    "decision_type": self.decision_type,
                    "total_token_budget": self.total_token_budget,
                },
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
                while candidate.get("content") and used + estimate_tokens(_serialize(candidate)) > budget:
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
    # C-01 决策面契约（可选、默认 None → 现有 5 个消费者零破坏）：
    # Aurora/Router/Planner 的进程内消费面。刻意不进 to_prompt_context()——
    # manifest 是观测/决策元数据，不是 prompt 内容，避免 token 膨胀。
    decision_context: DecisionContext | None = None
    # C-05 冲突裁决注入面（可选、默认 None → 无冲突/未开启时零破坏）：
    # resolved facts（winner 归因 + 置信）+ unresolved 已知分歧（M-04 ask_once）
    # + ask-if-material + resolution refs。digest 有界注入（防冲突原文全量进
    # prompt），经 to_prompt_context 供模型/下游理解「选了哪条、为什么」。
    conflict_resolution: dict[str, Any] | None = None

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
        if self.conflict_resolution:
            # C-05：prompt 面只带有界投影（prompt_note/旗标/ids）——结构化明细
            # 留在进程内消费面，防止满额冲突整包进 prompt（token 纪律）。
            result["conflict_resolution"] = to_prompt_payload(self.conflict_resolution)
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

        # M-03 deterministic L0 prefilter: illegal candidates (wrong user /
        # non-active status incl. superseded versions / expired commitments /
        # out-of-scope goals / user_memory_settings permission blocks) are cut
        # BEFORE rank / semantic gating / budget see them (MEMORY_V3 §3 1-5).
        # Conflict-resolution history stays unfiltered —— supersede resolution
        # legitimately needs the full version chain.
        retrieval_ctx = await build_retrieval_context(
            self.db,
            user_id=user_id,
            purpose=PURPOSE_LLM_CONTEXT,
            plan_id=plan_id,
        )
        pref_prefilter = prefilter_candidates(preference_records, retrieval_ctx)
        goal_prefilter = prefilter_candidates(goals, retrieval_ctx)
        episodic_prefilter = prefilter_candidates(episodic, retrieval_ctx)
        preference_records = pref_prefilter.allowed
        goals = goal_prefilter.allowed
        episodic = episodic_prefilter.allowed
        prefilter_metadata = {
            "user_id": str(user_id),
            "purpose": PURPOSE_LLM_CONTEXT,
            "plan_id": str(plan_id) if plan_id else None,
            "sections": {
                "preferences": pref_prefilter.to_metric_payload(),
                "goals": goal_prefilter.to_metric_payload(),
                "episodic": episodic_prefilter.to_metric_payload(),
            },
        }

        metadata: dict[str, Any] = {
            "document_context_controls": document_context_controls.to_metadata(),
            # M-03: per-dimension / per-reason cut counts (D-06/O-02 observability).
            "memory_prefilter": prefilter_metadata,
        }
        ranking_enabled = settings.ENABLE_CONTEXT_RANKING and rollout_enabled
        conflicts: list[dict[str, Any]] = []
        conflict_resolution_payload: dict[str, Any] | None = None
        weights: dict[str, float] | None = None
        if ranking_enabled and settings.ENABLE_PERSONALIZED_RANKING and rollout_enabled:
            policy_service = MemoryRankPolicyService(self.db)
            weights = await policy_service.get_policy(intent, user_id)

        if ranking_enabled:
            ranked_preferences = rank_items(
                preference_records,
                kind="preferences",
                weights=weights,
                query_text=query_text,
            )
            ranked_goals = rank_items(goals, kind="goals", weights=weights, query_text=query_text)
            ranked_episodic = rank_items(episodic, kind="episodic", weights=weights, query_text=query_text)

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
                key=lambda item: (item.evidence_score or 0.0, getattr(item, "created_at", None) or item.occurred_at),
                reverse=True,
            )
            resolved_pref_records = preference_records
            resolved_goals = goals
            resolved_episodic = episodic

        if conflict_enabled and resolver is not None:
            # V3-FIX-35 契约（勿"修复"为上游过滤）：pref_history 刻意保持全量
            # 版本链（含 replaced_by_id 指向链头的被取代行）——supersede 归因
            # 与抑制面（conflicts note 的 suppressed ids）是 resolver 的职责，
            # 它的 winner 选择是链感知的（_pick_preference_winner：被取代行
            # 不参与竞争，链头胜出）。上游过滤会剥夺链归因，并造成
            # resolver on/off 两个分支语义分叉。
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
            # C-05: 冲突裁决结果注入 Context —— resolved facts（winner 归因 +
            # 置信）+ unresolved 已知分歧（M-04 ask_once）+ ask-if-material +
            # resolution refs。record_index 用**预裁决全集**（pref_history 全版
            # 本链 + goals/episodic 预裁决列表），否则被取代 loser 无 display
            # 可归因。fail-soft，绝不阻断 pack 主链路。
            conflict_resolution_payload = await self._build_conflict_resolution_payload(
                user_id=user_id,
                conflict_notes=conflicts,
                preference_records=list(preference_records) + list(pref_history or []),
                goals=goals,
                episodes=episodic,
                query_text=query_text,
            )
            # 冲突消解分支的覆盖已由 resolver 显式产出（conflicts 面）。
            preference_collapse_overrides: list[Any] = []
        else:
            preferences = {item.pref_key: item.pref_value for item in preference_records}
            # C-02：非 resolver 分支的同 key 折叠不再静默。检测在 manifest 构建
            # 点统一执行（rank/裁剪后再判）——winner 按最终值回溯，早期调用会
            # 在 rank 重排下登记错胜者。
            preference_collapse_overrides = []

        ranked_preferences = (
            rank_items(resolved_pref_records, kind="preferences", weights=weights, query_text=query_text)
            if ranking_enabled
            else _normalized_ranked(resolved_pref_records)
        )
        ranked_goals = (
            rank_items(resolved_goals, kind="goals", weights=weights, query_text=query_text)
            if ranking_enabled
            else _normalized_ranked(resolved_goals)
        )
        ranked_episodic = (
            rank_items(resolved_episodic, kind="episodic", weights=weights, query_text=query_text)
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
                "linked_task_id": str(entry.item.linked_task_id) if entry.item.linked_task_id else None,
                "linked_plan_id": str(entry.item.linked_plan_id) if entry.item.linked_plan_id else None,
                "evidence_score": getattr(entry.item, "evidence_score", None),
                "correction_count": int(getattr(entry.item, "correction_count", 0) or 0),
                "claim_status": _memory_claim_status(entry.item),
                "source_label": _memory_source_label(entry.item),
                "rank_factors": _memory_rank_factors(entry.item, entry.score),
                "correction_actions": _memory_correction_actions("goal", str(entry.item.id)),
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
                "confidence": getattr(entry.item, "confidence", None),
                "evidence_score": getattr(entry.item, "evidence_score", None),
                "correction_count": int(getattr(entry.item, "correction_count", 0) or 0),
                "user_confirmed": _memory_claim_status(entry.item) == "confirmed",
                "claim_status": _memory_claim_status(entry.item),
                "source_label": _memory_source_label(entry.item),
                "rank_factors": _memory_rank_factors(entry.item, entry.score),
                "correction_actions": _memory_correction_actions("episodic", str(entry.item.id)),
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
        # D3 止血（审计 round2 案例A）：profile 域与 memory_preferences 同 key 时，
        # 不再将证据化记忆记录从 pack 中静默剔除——双源并存，交给 rank 加权与
        # 预算竞争裁决；双源键写入 metadata 供审计（V3 再收敛为显式规则表 + 冲突登记）。
        dual_source_keys = sorted(
            key for key in profile_keys if any(entry.item.pref_key == key for entry in ranked_preferences)
        )
        if dual_source_keys:
            metadata["preference_dual_source_keys"] = dual_source_keys

        pref_budget = budgets.get("preferences", 0)
        goals_budget = budgets.get("goals", 0)
        episodic_budget = budgets.get("episodic", 0)

        original_usage = {
            "preferences": estimate_tokens(_serialize(preferences)),
            "goals": estimate_tokens(_serialize([_budget_view(p, "goals") for p in goal_payloads])),
            "episodic": estimate_tokens(_serialize([_budget_view(p, "episodic") for p in episodic_payloads])),
        }

        if ranking_enabled:
            trimmed_preferences, pref_scores = _trim_ranked_preferences(ranked_preferences, pref_budget)
            trimmed_goals, goal_scores = _trim_ranked_list(goal_payloads, goal_scores, goals_budget, section="goals")
            trimmed_episodic, episodic_scores = _trim_ranked_list(
                episodic_payloads,
                episodic_scores,
                episodic_budget,
                section="episodic",
            )
            trimmed_pref_scores = {key: pref_scores.get(key, 0.0) for key in trimmed_preferences}
        else:
            trimmed_preferences = _trim_preferences(preferences, pref_budget)
            trimmed_goals = _trim_list(goal_payloads, goals_budget, section="goals")
            trimmed_episodic = _trim_list(episodic_payloads, episodic_budget, section="episodic")
            trimmed_pref_scores = {}

        await self._mark_consumed_memory_records(
            ranked_preferences=ranked_preferences,
            ranked_goals=ranked_goals,
            ranked_episodic=ranked_episodic,
            trimmed_preferences=trimmed_preferences,
            trimmed_goals=trimmed_goals,
            trimmed_episodic=trimmed_episodic,
        )

        # M-05 over-personalization Self-ReCheck —— 输出装配面 final-gate。
        # 分工：M-03/C-03 管候选池准入（上面已过），这里管合法召回候选在本轮
        # 「该不该说出来」。两档用途：降档条目保留在内部决策档
        # （decision_tier_* 原样传给 _build_decision_context，召回不删），
        # 只有 ids + 封闭 reason 进 metadata（无正文回灌——metadata 经
        # to_prompt_context 进入 prompt，故 claims/evidence_summary 同步排除）。
        decision_tier_preferences = trimmed_preferences
        decision_tier_goals = list(trimmed_goals)
        decision_tier_episodic = list(trimmed_episodic)
        memory_selfcheck_internal_ids: frozenset[str] = frozenset()
        if settings.ENABLE_MEMORY_USE_SELFCHECK:
            selfcheck = evaluate_memory_use_gate(
                preferences=[
                    MemoryUseCandidate(
                        item_id=key,
                        section="preferences",
                        content=value if isinstance(value, str) else str(value),
                        pref_key=key,
                    )
                    for key, value in trimmed_preferences.items()
                ],
                goals=[
                    MemoryUseCandidate(
                        item_id=str(payload.get("id")),
                        section="goals",
                        content=str(payload.get("title") or ""),
                    )
                    for payload in trimmed_goals
                ],
                episodic=[
                    MemoryUseCandidate(
                        item_id=str(payload.get("id")),
                        section="episodic",
                        content=str(payload.get("summary") or ""),
                    )
                    for payload in trimmed_episodic
                ],
                ctx=SelfCheckContext(user_message=query_text),
            )
            if selfcheck.input_count:
                surfaced_prefs = selfcheck.surfaced_ids("preferences")
                surfaced_goals = selfcheck.surfaced_ids("goals")
                surfaced_episodic = selfcheck.surfaced_ids("episodic")
                trimmed_preferences = {
                    key: value for key, value in trimmed_preferences.items() if key in surfaced_prefs
                }
                trimmed_goals = [payload for payload in trimmed_goals if str(payload.get("id")) in surfaced_goals]
                trimmed_episodic = [
                    payload for payload in trimmed_episodic if str(payload.get("id")) in surfaced_episodic
                ]
                internal_entries = selfcheck.internal_only_entries()
                memory_selfcheck_internal_ids = frozenset(entry["id"] for entry in internal_entries)
                metadata["memory_selfcheck"] = {
                    **selfcheck.to_metric_payload(),
                    "internal_only": internal_entries,
                }

        token_usage = {
            "preferences": estimate_tokens(_serialize(trimmed_preferences)),
            "goals": estimate_tokens(_serialize([_budget_view(p, "goals") for p in trimmed_goals])),
            "episodic": estimate_tokens(_serialize([_budget_view(p, "episodic") for p in trimmed_episodic])),
        }
        budget_remaining = {
            "preferences": pref_budget - token_usage["preferences"],
            "goals": goals_budget - token_usage["goals"],
            "episodic": episodic_budget - token_usage["episodic"],
        }

        if ranking_enabled:
            metadata["ranking"] = {
                "preferences": [
                    {
                        "key": key,
                        "score": trimmed_pref_scores.get(key, 0.0),
                        "claim_status": _memory_claim_status(entry.item),
                        "source_label": _memory_source_label(entry.item),
                        "rank_factors": _memory_rank_factors(entry.item, trimmed_pref_scores.get(key, 0.0)),
                        "correction_actions": _memory_correction_actions("preference", str(entry.item.id)),
                    }
                    for entry in ranked_preferences
                    if (key := entry.item.pref_key) in trimmed_preferences
                ][:10],
                "goals": [
                    {"id": payload.get("id"), "score": goal_scores.get(payload.get("id"), 0.0)}
                    for payload in trimmed_goals[:10]
                ],
                "episodic": [
                    {"id": payload.get("id"), "score": episodic_scores.get(payload.get("id"), 0.0)}
                    for payload in trimmed_episodic[:10]
                ],
            }
            metadata["memory_claims"] = {
                "preferences": [
                    {
                        "type": "preference",
                        "id": str(entry.item.id),
                        "key": entry.item.pref_key,
                        "status": _memory_claim_status(entry.item),
                        "source_label": _memory_source_label(entry.item),
                        "correction_actions": _memory_correction_actions("preference", str(entry.item.id)),
                    }
                    for entry in ranked_preferences
                    if entry.item.pref_key in trimmed_preferences
                ][:10],
                "goals": [
                    {
                        "type": "goal",
                        "id": payload.get("id"),
                        "title": payload.get("title"),
                        "status": payload.get("claim_status"),
                        "source_label": payload.get("source_label"),
                        "correction_actions": payload.get("correction_actions") or [],
                    }
                    for payload in trimmed_goals[:10]
                ],
                "episodic": [
                    {
                        "type": "episodic",
                        "id": payload.get("id"),
                        "summary": payload.get("summary"),
                        "status": payload.get("claim_status"),
                        "source_label": payload.get("source_label"),
                        "correction_actions": payload.get("correction_actions") or [],
                    }
                    for payload in trimmed_episodic[:10]
                ],
            }
        if semantic_metadata:
            metadata["semantic_gating"] = semantic_metadata
        if conflicts:
            metadata["conflicts"] = conflicts
        if conflict_resolution_payload:
            # C-05：id 级 resolution refs 留 metadata（观测/遥测面）；正文注入面
            # 走 ContextPack.conflict_resolution（一等字段，digest 有界）。
            metadata["conflict_resolution_refs"] = conflict_resolution_payload["resolution_refs"]
        if focus_decision:
            metadata["context_focus"] = focus_decision.to_dict()

        preference_source_records = resolved_pref_records if conflict_enabled else preference_records
        goal_source_records = resolved_goals if conflict_enabled else goals
        episodic_source_records = resolved_episodic if conflict_enabled else episodic
        # M-05：降档（内部档）条目不得经 evidence_summary 把 title/summary
        # 带回 prompt 面——top-evidence 观测面只保留 surfaced 条目
        # （preferences 只暴露 key/score，属 identity 级，不过滤）。
        if memory_selfcheck_internal_ids:
            goal_source_records = [
                record
                for record in goal_source_records
                if str(getattr(record, "id", "")) not in memory_selfcheck_internal_ids
            ]
            episodic_source_records = [
                record
                for record in episodic_source_records
                if str(getattr(record, "id", "")) not in memory_selfcheck_internal_ids
            ]

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

        # C-02: telemetry（含四类 sources 计量）移至 decision_context 之后统一落账
        # （pack_id 供 manifest 日志关联；memory_counts 附加 "sources" 见下方 record_run）。

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

        # C-01: 决策面契约填充（Aurora/Router/Planner 消费）。失败绝不阻断 pack 主链路。
        decision_ctx: DecisionContext | None = None
        if getattr(settings, "ENABLE_DECISION_CONTEXT", True):
            try:
                decision_ctx = await self._build_decision_context(
                    user_id=user_id,
                    intent=intent,
                    route_intent=route_intent,
                    plan_id=plan_id,
                    query_text=query_text,
                    focus_mode=focus_decision.focus_mode if focus_decision else None,
                    ranked_preferences=ranked_preferences,
                    trimmed_preferences=decision_tier_preferences,
                    ranked_goals=ranked_goals,
                    trimmed_goals=decision_tier_goals,
                    goal_scores=goal_scores,
                    ranked_episodic=ranked_episodic,
                    trimmed_episodic=decision_tier_episodic,
                    episodic_scores=episodic_scores,
                    goal_candidate_count=len(goal_payloads),
                    episodic_candidate_count=len(episodic_payloads),
                    ranking_enabled=ranking_enabled,
                    semantic_metadata=semantic_metadata,
                    focus_active=focus_decision is not None,
                    plan_context=plan_context,
                )
            except Exception as exc:
                logger.warning(f"Failed to build decision context for {user_id}: {exc}")
                decision_ctx = None

        # C-02: 四分 source manifest（每 item source type / token / 项数 / seed 标记）。
        # 折叠检测在此统一执行：final_values 用 rank/语义门控/裁剪后的最终 preferences
        # （trimmed_preferences 的值域），winner 与实际胜出值一致。
        if not conflict_enabled:
            preference_collapse_overrides = detect_preference_key_overrides(
                preference_records,
                final_values=preferences,
            )
        sources_manifest = self._build_source_manifest(
            decision_ctx=decision_ctx,
            trimmed_preferences=trimmed_preferences,
            trimmed_goals=trimmed_goals,
            trimmed_episodic=trimmed_episodic,
            episodic_source_records=episodic_source_records,
            plan_context=plan_context,
            token_usage=token_usage,
            preference_collapse_overrides=preference_collapse_overrides,
            memory_prefilter_metadata=prefilter_metadata,
        )
        metadata["sources"] = sources_manifest

        pack_id = None
        if settings.ENABLE_CONTEXT_PACK_TELEMETRY:
            trimmed_goal_ids = {payload.get("id") for payload in trimmed_goals}
            trimmed_episodic_ids = {payload.get("id") for payload in trimmed_episodic}
            telemetry_pref_scores = [
                item.evidence_score for item in preference_source_records if item.pref_key in trimmed_preferences
            ]
            telemetry_goal_scores = [
                item.evidence_score for item in goal_source_records if str(item.id) in trimmed_goal_ids
            ]
            telemetry_episodic_scores = [
                item.evidence_score for item in episodic_source_records if str(item.id) in trimmed_episodic_ids
            ]
            scores = [
                score
                for score in telemetry_pref_scores + telemetry_goal_scores + telemetry_episodic_scores
                if score is not None
            ]
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
                    # C-02：四类 token/项数进既有 telemetry（JSONB 附加键，读者按
                    # 已知 key 取值不受影响；SQL 查询见 v3-output/C-02/REPORT.md）。
                    "sources": sources_manifest["sections"],
                },
                evidence_score_avg=evidence_avg,
                request_id=request_id,
                trace_id=trace_id,
            )

        _source_line = " ".join(
            f"{category}={section['item_count']}items/{section['token_estimate']}tok"
            for category, section in sources_manifest["sections"].items()
        )
        logger.info(
            "C-02 context pack sources pack_id={pack_id} user={user_id} intent={intent}: {line} "
            "item_categories={item_categories} seed_demo={seed} overrides={overrides}",
            pack_id=pack_id,
            user_id=user_id,
            intent=intent,
            line=_source_line,
            item_categories=dict(sources_manifest.get("item_category_counts") or {}),
            seed=sum(int(section.get("seed_or_demo", 0) or 0) for section in sources_manifest["sections"].values()),
            overrides=len(sources_manifest.get("overrides") or []),
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
            decision_context=decision_ctx,
            conflict_resolution=conflict_resolution_payload,
        )

    async def _build_conflict_resolution_payload(
        self,
        *,
        user_id: UUID,
        conflict_notes: list[dict[str, Any]],
        preference_records: list[Any],
        goals: list[Any],
        episodes: list[Any],
        query_text: str | None,
    ) -> dict[str, Any] | None:
        """C-05：组装冲突裁决注入面（resolved + unresolved + refs）。

        消费纪律：resolved 面只读本 build 已裁决的 records/notes（不重建裁决；
        ``preference_records`` 由调用方传入预裁决全集含 pref_history 全版本链，
        winner/loser 双侧可归因）；unresolved 面只读 M-04
        ``ConflictResolverService.list_unresolved_conflicts``（ask_once 权威，
        pending_user 过滤在真源内）。全部 fail-soft——任何失败降级为无注入，
        绝不阻断 pack 主链路。
        """
        try:
            unresolved_rows: list[Any] = []
            try:
                rows = await ConflictResolverService(self.db).list_unresolved_conflicts(user_id=user_id)
                unresolved_rows = list(rows)[:UNRESOLVED_FETCH_LIMIT]
            except Exception as exc:  # noqa: BLE001 - fail-soft per docstring
                logger.warning(f"C-05 failed to load unresolved conflicts for {user_id}: {exc}")
            payload = build_conflict_resolution_context(
                conflict_notes=conflict_notes,
                record_index=build_record_index(preference_records, goals, episodes),
                unresolved_rows=unresolved_rows,
                query_text=query_text,
            )
            if payload["resolved_facts"] or payload["unresolved_conflicts"]:
                return payload
            return None
        except Exception as exc:  # noqa: BLE001 - fail-soft per docstring
            logger.warning(f"C-05 failed to build conflict resolution context for {user_id}: {exc}")
            return None

    def _build_source_manifest(
        self,
        *,
        decision_ctx: DecisionContext | None,
        trimmed_preferences: dict[str, Any],
        trimmed_goals: list[dict[str, Any]],
        trimmed_episodic: list[dict[str, Any]],
        episodic_source_records: list[Any],
        plan_context: dict[str, Any] | None,
        token_usage: dict[str, int],
        preference_collapse_overrides: list[Any],
        memory_prefilter_metadata: Mapping[str, Any] | None,
    ) -> dict[str, Any]:
        """C-02：pack 装配结果的四类 manifest（进 metadata["sources"] + telemetry）。

        R2-F1：与 orchestrator 面**同一 key 集**——序列化唯一权威是
        context_sources.assemble_manifest / normalize_section（缺/多 key 由
        test_context_source_contract 契约测试钉死）；pack 面不适用的值为 None/{}。

        - state：decision signals（UserStateV1 投影）+ plan + goals（USER_WORLD_MODEL
          §1 Goal 属 Current State；存储在 memory 表不改变语义类别）。
        - memory：preferences + episodic（含 seed/demo 条目计数；M-03 预筛 provenance
          透传进 note——rejected 计数可在 manifest 直接观测，R2-F4 集成路径）。
        - knowledge/events：本 pack 不携带（documents/galaxy/decision_records/history
          走 orchestrator 侧 manifest 与 ContextBudgetManager 预算面）——enabled
          开关与 0 计量显式可见，不留静默空缺。
        - 每 item source type 正确性：decision_ctx.items 逐条经封闭投影
          item_source_category 归类，计数进 item_category_counts。
        """
        trimmed_episodic_ids = {str(payload.get("id")) for payload in trimmed_episodic}
        seed_episodic_keys = sorted(
            str(record.id)
            for record in episodic_source_records
            if str(record.id) in trimmed_episodic_ids and memory_record_is_seed(record)
        )

        signals = list(decision_ctx.signals) if decision_ctx else []
        signal_tokens = sum(estimate_tokens(_serialize(signal.to_dict())) for signal in signals)
        has_plan_item = bool(plan_context and plan_context.get("plan_id"))

        item_category_counts: dict[str, int] = dict.fromkeys(SOURCE_CATEGORIES, 0)
        if decision_ctx is not None:
            for item in decision_ctx.items:
                try:
                    item_category_counts[item_source_category(item.type)] += 1
                except KeyError:
                    logger.warning(f"C-02: unknown decision item type {item.type!r} skipped in source manifest")

        prefilter_note = None
        if isinstance(memory_prefilter_metadata, Mapping):
            prefilter_sections = memory_prefilter_metadata.get("sections") or {}
            rejected = sum(
                int(section.get("input_count", 0) or 0) - int(section.get("allowed_count", 0) or 0)
                for section in prefilter_sections.values()
                if isinstance(section, Mapping)
            )
            if rejected:
                prefilter_note = (
                    f"M-03 prefilter cut {rejected} candidate(s) before ranking "
                    f"(see metadata.memory_prefilter for dimensions/reasons)"
                )

        sections = {
            "state": normalize_section(
                category="state",
                enabled=StateSourceAdapter().enabled,
                adapter=StateSourceAdapter.adapter_name,
                keys=["signals", "goals", "plan"] if has_plan_item else ["signals", "goals"],
                item_count=len(signals) + len(trimmed_goals) + (1 if has_plan_item else 0),
                token_estimate=int(token_usage.get("goals", 0) or 0) + signal_tokens,
                seed_or_demo=0,
                seed_or_demo_items=[],
                decision_items=item_category_counts.get("state"),
            ),
            "memory": normalize_section(
                category="memory",
                enabled=MemorySourceAdapter().enabled,
                adapter=MemorySourceAdapter.adapter_name,
                keys=["preferences", "episodic"],
                item_count=len(trimmed_preferences) + len(trimmed_episodic),
                token_estimate=int(token_usage.get("preferences", 0) or 0) + int(token_usage.get("episodic", 0) or 0),
                seed_or_demo=len(seed_episodic_keys),
                seed_or_demo_items=[{"key": f"episodic:{record_id}"} for record_id in seed_episodic_keys],
                decision_items=item_category_counts.get("memory"),
                note=prefilter_note,
            ),
            "knowledge": normalize_section(
                category="knowledge",
                enabled=KnowledgeSourceAdapter().enabled,
                adapter=KnowledgeSourceAdapter.adapter_name,
                keys=[],
                item_count=0,
                token_estimate=0,
                seed_or_demo=0,
                seed_or_demo_items=[],
                decision_items=item_category_counts.get("knowledge"),
                note="pack does not carry document chunks; knowledge rides orchestrator-side "
                "context_sources manifest and ContextBudgetManager budgets",
            ),
            "events": normalize_section(
                category="events",
                enabled=EventSourceAdapter().enabled,
                adapter=EventSourceAdapter.adapter_name,
                keys=[],
                item_count=0,
                token_estimate=0,
                seed_or_demo=0,
                seed_or_demo_items=[],
                decision_items=item_category_counts.get("events"),
                note="decision_records and conversation history ride orchestrator-side "
                "context_sources manifest (events channel)",
            ),
        }
        for category, section in sections.items():
            sections[category] = dict(section)

        return assemble_manifest(
            sections=sections,
            overrides=preference_collapse_overrides,
            unclassified=[],
            user_is_seed_or_demo=None,  # pack 面不 fetch 用户行（R2-F1：key 恒在，值 None）
            late_stage_writers={},
            control_keys=[],
            item_category_counts=item_category_counts,
        )

    def _decision_item_reasons(
        self,
        *,
        ranking_enabled: bool,
        focus_active: bool,
        semantic_applied: bool,
        included: int,
        candidates: int,
    ) -> tuple[str, ...]:
        reasons = ["rank_policy"] if ranking_enabled else ["evidence_order"]
        if focus_active:
            reasons.append("focus_mode")
        if semantic_applied:
            reasons.append("semantic_gate")
        if included < candidates:
            reasons.append("budget_carryover")
        return tuple(reasons)

    async def _collect_decision_signals(
        self,
        user_id: UUID,
    ) -> tuple[tuple[DecisionStateSignal, ...], tuple[str, ...], dict[str, str]]:
        """逐字段投影 UserStateV1 高信号（单字段故障只降级该字段，不炸 pack）。

        V3-FIX-09 / REVIEW_RECEIPT_2 F1：治理模式与真降级可区分、可观测。
        - aggregator kill-switch=off / shadow → 原因码 governance_off / governance_shadow
          （治理性关闭，跳过取数，不冒充数据缺失）；
        - live 下 envelope 缺失或取数异常 → 原因码 unavailable（真降级）。
        观测面：聚合结构化 warning 日志 + DECISION_CONTEXT_SIGNAL_DEGRADED_TOTAL 计数；
        原因码随 DecisionContext.degraded_reasons 尾字段流出供消费方区分。
        """
        from app.services.aurora_stage18_kill_switch_service import AuroraStage18KillSwitchService
        from app.state_aggregator.service import StateAggregatorService

        aggregator_mode = await AuroraStage18KillSwitchService().get_feature_mode("aggregator_enabled")
        aggregator = StateAggregatorService(self.db)
        ttl_map = StateAggregatorService.FIELD_TTLS_SECONDS
        signals: list[DecisionStateSignal] = []
        degraded: list[str] = []
        degraded_reasons: dict[str, str] = {}
        for field_name in DEFAULT_DECISION_SIGNAL_FIELDS:
            if aggregator_mode == "off":
                # 治理性关闭：不取数、不计异常，原因显式编码（F1）
                degraded_reasons[field_name] = "governance_off"
            elif aggregator_mode == "shadow":
                # shadow 模式下 _get_field 恒返回 None（计算不外曝）：跳过无效取数（F1）
                degraded_reasons[field_name] = "governance_shadow"
            else:
                try:
                    state = await aggregator.get_user_state(user_id, required_fields=(field_name,))
                    envelope = getattr(state, field_name, None)
                    if envelope is None or getattr(envelope, "value", None) is None:
                        degraded_reasons[field_name] = "unavailable"
                    else:
                        signals.append(
                            state_signal_from_envelope(
                                field_name,
                                envelope,
                                ttl_map=ttl_map,
                                epoch=state.schema_version,
                            )
                        )
                        continue
                except Exception as exc:
                    logger.warning(f"Decision context signal {field_name} degraded for {user_id}: {exc}")
                    degraded_reasons[field_name] = "unavailable"
            degraded.append(field_name)
        if degraded:
            logger.warning(
                f"Decision context signals degraded for {user_id}: "
                f"aggregator_mode={aggregator_mode!r} "
                f"reasons={ {name: degraded_reasons[name] for name in sorted(degraded)} }"
            )
            for name in degraded:
                DECISION_CONTEXT_SIGNAL_DEGRADED_TOTAL.labels(reason=degraded_reasons[name]).inc()
        return tuple(signals), tuple(degraded), degraded_reasons

    async def _build_decision_context(
        self,
        *,
        user_id: UUID,
        intent: str,
        route_intent: str | None,
        plan_id: UUID | None,
        query_text: str | None,
        focus_mode: str | None,
        ranked_preferences: list[RankedItem[Any]],
        trimmed_preferences: dict[str, Any],
        ranked_goals: list[RankedItem[Any]],
        trimmed_goals: list[dict[str, Any]],
        goal_scores: dict[str, float],
        ranked_episodic: list[RankedItem[Any]],
        trimmed_episodic: list[dict[str, Any]],
        episodic_scores: dict[str, float],
        goal_candidate_count: int,
        episodic_candidate_count: int,
        ranking_enabled: bool,
        semantic_metadata: dict[str, Any],
        focus_active: bool,
        plan_context: dict[str, Any] | None,
    ) -> DecisionContext:
        def _iso_or_none(value: Any) -> str | None:
            return value.isoformat() if hasattr(value, "isoformat") else (str(value) if value is not None else None)

        items: list[ContextItemDescriptor] = []

        pref_candidates = len(ranked_preferences)
        pref_semantic = bool(semantic_metadata.get("preferences", {}).get("applied"))
        pref_reasons = self._decision_item_reasons(
            ranking_enabled=ranking_enabled,
            focus_active=focus_active,
            semantic_applied=pref_semantic,
            included=len(trimmed_preferences),
            candidates=pref_candidates,
        )
        for entry in ranked_preferences:
            if entry.item.pref_key not in trimmed_preferences:
                continue
            items.append(
                ContextItemDescriptor(
                    ref=memory_ref("preference", entry.item.id),
                    type="preference",
                    scope="user",
                    why_included=pref_reasons,
                    epoch=_iso_or_none(getattr(entry.item, "updated_at", None)),
                    relevance=entry.score,
                )
            )

        goal_semantic = bool(semantic_metadata.get("goals", {}).get("applied"))
        goal_reasons = self._decision_item_reasons(
            ranking_enabled=ranking_enabled,
            focus_active=focus_active,
            semantic_applied=goal_semantic,
            included=len(trimmed_goals),
            candidates=goal_candidate_count,
        )
        goal_epochs = {
            str(entry.item.id): _iso_or_none(getattr(entry.item, "updated_at", None)) for entry in ranked_goals
        }
        for payload in trimmed_goals:
            item_id = str(payload.get("id"))
            items.append(
                ContextItemDescriptor(
                    ref=memory_ref("goal", item_id),
                    type="goal",
                    scope="plan" if payload.get("linked_plan_id") else "user",
                    why_included=goal_reasons,
                    epoch=goal_epochs.get(item_id),
                    relevance=goal_scores.get(item_id),
                )
            )

        episodic_semantic = bool(semantic_metadata.get("episodic", {}).get("applied"))
        episodic_reasons = self._decision_item_reasons(
            ranking_enabled=ranking_enabled,
            focus_active=focus_active,
            semantic_applied=episodic_semantic,
            included=len(trimmed_episodic),
            candidates=episodic_candidate_count,
        )
        episodic_epochs = {
            str(entry.item.id): _iso_or_none(getattr(entry.item, "occurred_at", None)) for entry in ranked_episodic
        }
        for payload in trimmed_episodic:
            item_id = str(payload.get("id"))
            items.append(
                ContextItemDescriptor(
                    ref=memory_ref("episodic", item_id),
                    type="episodic_memory",
                    scope="user",
                    why_included=episodic_reasons,
                    epoch=episodic_epochs.get(item_id),
                    relevance=episodic_scores.get(item_id),
                )
            )

        if plan_context and plan_context.get("plan_id"):
            items.append(
                ContextItemDescriptor(
                    ref=plan_ref(plan_context.get("plan_id")),
                    type="plan",
                    scope="plan",
                    why_included=("plan_scope",),
                    epoch=str(plan_context.get("version") or "unknown"),
                )
            )

        signals, degraded, degraded_reasons = await self._collect_decision_signals(user_id)

        omitted_counts = {
            "preferences": max(0, len(ranked_preferences) - len(trimmed_preferences)),
            "goals": max(0, goal_candidate_count - len(trimmed_goals)),
            "episodic": max(0, episodic_candidate_count - len(trimmed_episodic)),
        }

        return DecisionContext(
            user_id=user_id,
            intent=intent,
            route_intent=route_intent,
            focus_mode=focus_mode,
            plan_id=plan_id,
            query_text_hash=hash_query_text(query_text),
            signals=signals,
            items=tuple(items),
            omitted_counts=omitted_counts,
            degraded_fields=degraded,
            built_at=_utcnow(),
            degraded_reasons=degraded_reasons,
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
