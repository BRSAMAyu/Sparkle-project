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


async def compute_retrieval_plan(
    *,
    retrieval_directive: RetrievalDirective,
    source_tray: SourceTrayState,
    target_nodes: list[str] | None = None,
    blocked_source_ids: set[str] | None = None,
    low_effectiveness_source_ids: set[str] | None = None,
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

        # SRC-014: Skip sources blocked by user correction
        if blocked_source_ids and sid in blocked_source_ids:
            do_not_load.append({"source_id": sid, "reason": "user_correction_blocked"})
            continue

        # SRC-013: Skip sources with historically low effectiveness
        if low_effectiveness_source_ids and sid in low_effectiveness_source_ids:
            do_not_load.append({"source_id": sid, "reason": "low_effectiveness_rate"})
            continue

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
        source.source_id for source in (source_tray.available_sources or []) if source.parsed_status != "failed"
    }
    return (selected_includes | directive_candidates | available_candidates) - loaded_ids - excluded_ids


def _receipt_skip_reason(source_id: str, sources_by_id: dict[str, SourceAsset]) -> str:
    source = sources_by_id.get(source_id)
    if source and source.parsed_status == "failed":
        return "parse_failed"
    return "not_loaded"


# ── SourceEffectiveness Tracking ───────────────────────────────────

_SOURCE_EFFECT_KEY = "spine:source_effect:{user_id}:{source_id}"
_SOURCE_EFFECT_INDEX = "spine:source_effects:{user_id}"
_SOURCE_EFFECT_TTL = 90 * 24 * 3600  # 90 days


class SourceEffectivenessTracker:
    """Track how effectively each source contributes to learning outcomes.

    Records a (source_id → effectiveness) mapping per user, updated
    when an outcome is recorded after a source was used in retrieval.
    """

    def __init__(self, redis_client: Any):
        self.redis = redis_client

    async def record_source_outcome(
        self,
        *,
        user_id: str,
        source_id: str,
        outcome: str,  # "effective" | "insufficient"
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        key = _SOURCE_EFFECT_KEY.format(user_id=user_id, source_id=source_id)
        import json

        raw = await self.redis.get(key)
        if raw:
            data = json.loads(raw if isinstance(raw, str) else raw.decode())
        else:
            data = {"source_id": source_id, "effective": 0, "insufficient": 0, "total": 0}

        data["total"] = data.get("total", 0) + 1
        if outcome == "effective":
            data["effective"] = data.get("effective", 0) + 1
        else:
            data["insufficient"] = data.get("insufficient", 0) + 1

        data["effectiveness_rate"] = round(data["effective"] / max(data["total"], 1), 3)
        if context:
            data["last_context"] = context

        from datetime import UTC, datetime

        data["last_updated"] = datetime.now(UTC).isoformat()

        await self.redis.set(key, json.dumps(data), ex=_SOURCE_EFFECT_TTL)
        # Index for enumeration
        idx_key = _SOURCE_EFFECT_INDEX.format(user_id=user_id)
        await self.redis.sadd(idx_key, source_id)
        await self.redis.expire(idx_key, _SOURCE_EFFECT_TTL)
        return data

    async def get_source_effectiveness(
        self,
        user_id: str,
        source_id: str,
    ) -> dict[str, Any] | None:
        import json

        key = _SOURCE_EFFECT_KEY.format(user_id=user_id, source_id=source_id)
        raw = await self.redis.get(key)
        if not raw:
            return None
        return json.loads(raw if isinstance(raw, str) else raw.decode())

    async def get_all_source_effectiveness(
        self,
        user_id: str,
    ) -> list[dict[str, Any]]:
        import json

        idx_key = _SOURCE_EFFECT_INDEX.format(user_id=user_id)
        source_ids = await self.redis.smembers(idx_key)
        results = []
        for sid in source_ids:
            sid_str = sid if isinstance(sid, str) else sid.decode()
            data = await self.get_source_effectiveness(user_id, sid_str)
            if data:
                results.append(data)
        return sorted(results, key=lambda x: x.get("effectiveness_rate", 0), reverse=True)

    # SRC-014: Source trust correction
    _BLOCKLIST_KEY = "spine:source_blocklist:{user_id}"

    async def record_user_correction(
        self,
        *,
        user_id: str,
        source_id: str,
        reason: str,
    ) -> dict[str, Any]:
        key = self._BLOCKLIST_KEY.format(user_id=user_id)
        await self.redis.sadd(key, source_id)
        await self.redis.expire(key, _SOURCE_EFFECT_TTL)
        return {
            "source_id": source_id,
            "auto_reuse_blocked": True,
            "status": "user_corrected",
        }

    async def is_source_blocked(self, user_id: str, source_id: str) -> bool:
        key = self._BLOCKLIST_KEY.format(user_id=user_id)
        return bool(await self.redis.sismember(key, source_id))

    async def get_blocked_sources(self, user_id: str) -> list[str]:
        key = self._BLOCKLIST_KEY.format(user_id=user_id)
        members = await self.redis.smembers(key)
        return [m if isinstance(m, str) else m.decode() for m in members]

    async def get_low_effectiveness_sources(
        self,
        user_id: str,
        *,
        min_trials: int = 3,
        max_rate: float = 0.3,
    ) -> list[str]:
        all_effects = await self.get_all_source_effectiveness(user_id)
        return [
            e["source_id"]
            for e in all_effects
            if e.get("total", 0) >= min_trials and e.get("effectiveness_rate", 1.0) <= max_rate
        ]

    # ── SRC-014: User correction → source_trust update ──────────────

    _TRUST_KEY = "spine:source_trust:{user_id}:{source_id}"
    _TRUST_BLOCKLIST = "spine:source_trust_blocklist:{user_id}"
    _TRUST_TTL = 30 * 24 * 3600  # 30 days

    async def record_user_correction(
        self,
        *,
        user_id: str,
        source_id: str,
        reason: str = "user_marked_irrelevant",
    ) -> dict[str, Any]:
        """User corrected a source as irrelevant/wrong. Update trust and block auto-reuse."""
        import json

        from datetime import UTC, datetime

        # Record as insufficient outcome
        await self.record_source_outcome(
            user_id=user_id,
            source_id=source_id,
            outcome="insufficient",
            context={"correction_reason": reason},
        )

        # Set trust flag
        trust_key = self._TRUST_KEY.format(user_id=user_id, source_id=source_id)
        trust_data = {
            "source_id": source_id,
            "status": "user_corrected",
            "reason": reason,
            "auto_reuse_blocked": True,
            "corrected_at": datetime.now(UTC).isoformat(),
        }
        await self.redis.set(trust_key, json.dumps(trust_data), ex=self._TRUST_TTL)

        # Add to blocklist for fast lookup
        bl_key = self._TRUST_BLOCKLIST.format(user_id=user_id)
        await self.redis.sadd(bl_key, source_id)
        await self.redis.expire(bl_key, self._TRUST_TTL)

        return trust_data

    async def is_source_blocked(self, user_id: str, source_id: str) -> bool:
        """Check if a source is blocked from auto-reuse due to user correction."""
        bl_key = self._TRUST_BLOCKLIST.format(user_id=user_id)
        return bool(await self.redis.sismember(bl_key, source_id))

    async def get_blocked_sources(self, user_id: str) -> list[str]:
        """Return all source IDs blocked from auto-reuse."""
        bl_key = self._TRUST_BLOCKLIST.format(user_id=user_id)
        members = await self.redis.smembers(bl_key)
        return [m if isinstance(m, str) else m.decode() for m in members]


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
