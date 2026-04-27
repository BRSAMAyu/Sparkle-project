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

from app.signals.types import RetrievalDirective, SourceAsset, SourceTrayState


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


def _estimate_tokens(source: SourceAsset) -> int:
    """Rough token estimate: ~4 tokens per char of summary, min 500."""
    slices = source.slices or []
    if slices:
        return sum(200 for _ in slices)  # ~200 tokens per slice
    return 500
