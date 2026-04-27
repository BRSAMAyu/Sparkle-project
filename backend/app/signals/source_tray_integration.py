"""
Core: execution
Phase: sense→clarify
Stage: Signal-to-Action Spine v2.0

SourceTrayIntegration — Bridges SourceAsset/SourceTrayState with RetrievalDirective.

When a RetrievalDirective is generated, this module uses the user's SourceTrayState
to compute concrete must_load/may_load/do_not_load lists and relevance scores.

Per Final Spec Iron Law 6: RAG is not a switch, it's a ContextPlan.
"""

from __future__ import annotations

from typing import Any

from loguru import logger

from app.signals.types import RetrievalDirective, SourceAsset, SourceTraySelection, SourceTrayState


def compute_retrieval_plan(
    *,
    retrieval_directive: RetrievalDirective,
    source_tray: SourceTrayState,
    target_nodes: list[str] | None = None,
) -> dict[str, Any]:
    """
    Given a RetrievalDirective and the user's SourceTrayState, compute
    a concrete retrieval plan with must_load/may_load/do_not_load
    populated from actual source metadata.

    Returns:
        {
            "must_load": [{"source_id": str, "slices": [...], "reason": str}],
            "may_load": [...],
            "do_not_load": [...],
            "relevance_scores": {"source_id": float},
            "token_budget_used": int,
        }
    """
    must_load: list[dict[str, Any]] = []
    may_load: list[dict[str, Any]] = []
    do_not_load: list[dict[str, Any]] = []
    relevance_scores: dict[str, float] = {}
    token_budget_used = 0

    available = source_tray.available_sources or []
    selections = source_tray.selections or []

    # Build explicit selection map
    selected_actions: dict[str, str] = {}
    for sel in selections:
        selected_actions[sel.source_id] = sel.action

    # Guard: pollution_guard = strict means only user-pinned or high-relevance
    strict_mode = retrieval_directive.pollution_guard == "strict"
    token_budget = retrieval_directive.token_budget

    for source in available:
        sid = source.source_id

        # Skip failed parses
        if source.parsed_status == "failed":
            do_not_load.append({"source_id": sid, "reason": "parse_failed"})
            continue

        # Compute relevance if target_nodes provided
        relevance = 0.0
        if target_nodes:
            relevance = source.relevance_for_nodes(target_nodes)
        relevance_scores[sid] = relevance

        # Check explicit user action
        explicit_action = selected_actions.get(sid)
        if explicit_action == "include":
            must_load.append({
                "source_id": sid,
                "relevance": relevance,
                "reason": "user_explicitly_included",
            })
            token_budget_used += _estimate_tokens(source)
            continue
        elif explicit_action == "exclude":
            do_not_load.append({"source_id": sid, "reason": "user_explicitly_excluded"})
            continue

        # Auto mode: decide based on relevance + directive constraints
        if retrieval_directive.must_load and sid in retrieval_directive.must_load:
            must_load.append({
                "source_id": sid,
                "relevance": relevance,
                "reason": "directive_required",
            })
            token_budget_used += _estimate_tokens(source)
        elif retrieval_directive.do_not_load and sid in retrieval_directive.do_not_load:
            do_not_load.append({"source_id": sid, "reason": "directive_excluded"})
        elif strict_mode and relevance < 0.3:
            do_not_load.append({
                "source_id": sid,
                "reason": f"low_relevance({relevance:.2f})_strict_guard",
            })
        elif token_budget_used < token_budget:
            may_load.append({
                "source_id": sid,
                "relevance": relevance,
                "reason": "available_within_budget",
            })
            token_budget_used += _estimate_tokens(source)

    logger.info(
        "SourceTrayIntegration: must={} may={} skip={} budget={}/{}",
        len(must_load), len(may_load), len(do_not_load),
        token_budget_used, token_budget,
    )

    return {
        "must_load": must_load,
        "may_load": may_load,
        "do_not_load": do_not_load,
        "relevance_scores": relevance_scores,
        "token_budget_used": token_budget_used,
    }


def build_source_receipt(
    retrieval_directive: RetrievalDirective,
    source_tray: SourceTrayState,
    loaded_source_ids: list[str],
) -> dict[str, Any]:
    """
    Build a user-visible receipt for how SourceTray materials were used.

    The receipt is intentionally compact: it names loaded sources, sources that
    could not be loaded, explicit exclusions, and one corrective sentence.
    """
    sources_by_id = {source.source_id: source for source in (source_tray.available_sources or [])}
    selections_by_id = {selection.source_id: selection for selection in (source_tray.selections or [])}
    loaded_ids = set(loaded_source_ids)
    directive_includes = set(retrieval_directive.must_load or []) | set(retrieval_directive.may_load or [])
    directive_excludes = set(retrieval_directive.do_not_load or [])

    loaded = [
        {
            "source_id": source_id,
            "title": _source_title(source_id, sources_by_id),
            "reason": _receipt_load_reason(source_id, selections_by_id, directive_includes),
        }
        for source_id in loaded_source_ids
    ]

    excluded_ids = {
        selection.source_id for selection in (source_tray.selections or []) if selection.action == "exclude"
    } | directive_excludes
    excluded = [
        {
            "source_id": source_id,
            "title": _source_title(source_id, sources_by_id),
            "reason": _receipt_exclude_reason(source_id, selections_by_id, directive_excludes),
        }
        for source_id in sorted(excluded_ids)
        if source_id not in loaded_ids
    ]

    candidate_ids = _receipt_candidate_ids(retrieval_directive, source_tray, loaded_ids, excluded_ids)
    skipped = [
        {
            "source_id": source_id,
            "title": _source_title(source_id, sources_by_id),
            "reason": _receipt_skip_reason(source_id, sources_by_id),
        }
        for source_id in sorted(candidate_ids)
    ]

    return {
        "loaded": loaded,
        "skipped": skipped,
        "excluded": excluded,
        "reason_for_user": _build_receipt_reason(len(loaded), skipped),
    }


def validate_source_tray_selections(
    source_tray: SourceTrayState,
    available_sources: list[SourceAsset],
) -> SourceTrayState:
    """Remove stale include selections that no longer point to available sources."""
    available_ids = {source.source_id for source in available_sources}
    cleaned_selections: list[SourceTraySelection] = []

    for selection in source_tray.selections or []:
        if selection.action == "include" and selection.source_id not in available_ids:
            logger.info(
                "SourceTrayIntegration: removing stale include selection source_id={}",
                selection.source_id,
            )
            continue
        cleaned_selections.append(selection)

    return SourceTrayState(
        mode=source_tray.mode,
        selections=cleaned_selections,
        available_sources=available_sources,
    )


def _estimate_tokens(source: SourceAsset) -> int:
    """Rough token estimate: ~4 tokens per char of summary, min 500."""
    slices = source.slices or []
    if slices:
        return sum(200 for _ in slices)  # ~200 tokens per slice
    return 500


def _source_title(source_id: str, sources_by_id: dict[str, SourceAsset]) -> str:
    source = sources_by_id.get(source_id)
    return source.title if source else source_id


def _receipt_load_reason(
    source_id: str,
    selections_by_id: dict[str, SourceTraySelection],
    directive_includes: set[str],
) -> str:
    selection = selections_by_id.get(source_id)
    if selection and selection.action == "include":
        return "user_selected"
    if source_id in directive_includes:
        return "directive_selected"
    return "auto_selected"


def _receipt_exclude_reason(
    source_id: str,
    selections_by_id: dict[str, SourceTraySelection],
    directive_excludes: set[str],
) -> str:
    selection = selections_by_id.get(source_id)
    if selection and selection.action == "exclude":
        return "user_excluded"
    if source_id in directive_excludes:
        return "directive_excluded"
    return "excluded"


def _receipt_candidate_ids(
    retrieval_directive: RetrievalDirective,
    source_tray: SourceTrayState,
    loaded_ids: set[str],
    excluded_ids: set[str],
) -> set[str]:
    selected_includes = {
        selection.source_id for selection in (source_tray.selections or []) if selection.action == "include"
    }
    directive_candidates = set(retrieval_directive.must_load or []) | set(retrieval_directive.may_load or [])
    available_candidates = {
        source.source_id for source in (source_tray.available_sources or []) if source.parsed_status == "failed"
    }
    return (selected_includes | directive_candidates | available_candidates) - loaded_ids - excluded_ids


def _receipt_skip_reason(source_id: str, sources_by_id: dict[str, SourceAsset]) -> str:
    source = sources_by_id.get(source_id)
    if source and source.parsed_status == "failed":
        return "parse_failed"
    return "not_loaded"


def _build_receipt_reason(loaded_count: int, skipped: list[dict[str, Any]]) -> str:
    skipped_count = len(skipped)
    if loaded_count == 0 and skipped_count == 0:
        return "这轮没有加载资料。"
    if loaded_count == 0:
        return f"这轮没有加载资料，跳过了 {skipped_count} 份。"
    if skipped_count == 0:
        return f"使用了你选的 {loaded_count} 份资料。"

    parse_failed_count = sum(1 for item in skipped if item["reason"] == "parse_failed")
    if parse_failed_count:
        return f"使用了你选的 {loaded_count} 份资料，跳过了 {skipped_count} 份（解析失败）。"
    return f"使用了你选的 {loaded_count} 份资料，跳过了 {skipped_count} 份。"
