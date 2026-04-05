from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.services.five_layer_learning_contract import (
    DEFAULT_FIVE_LAYER_CONTRACT,
    LayerConflictReport,
    LayeredGrowthStateSnapshot,
    LayeredLearningContract,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _strip(value: Any) -> str:
    return str(value or "").strip()


def _as_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return []


def _parse_dt(value: Any) -> datetime | None:
    raw = _strip(value)
    if not raw:
        return None
    normalized = raw.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def _normalize_value(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.3f}"
    return " ".join(str(value or "").strip().lower().split())


class LayerConflictResolver:
    """Detect and adjudicate contradictions across session, episode, and profile layers."""

    def __init__(self, contract: LayeredLearningContract | None = None) -> None:
        self.contract = contract or DEFAULT_FIVE_LAYER_CONTRACT

    def resolve_field_conflict(
        self,
        *,
        learning_key: str,
        layer_values: list[dict[str, Any]],
        context_preferred_layer: str | None = None,
        constitutional_override: bool = False,
    ) -> LayerConflictReport | None:
        comparable = [
            dict(item)
            for item in layer_values
            if isinstance(item, dict) and _strip(item.get("layer")) and _strip(item.get("value")) != ""
        ]
        if len(comparable) < 2:
            return None

        unique_values = {_normalize_value(item.get("value")) for item in comparable}
        if len(unique_values) < 2:
            return None

        involved_layers = tuple(_strip(item.get("layer")) for item in comparable)
        winner = "constitutional" if constitutional_override else self._pick_winner(
            comparable,
            context_preferred_layer=context_preferred_layer,
        )
        blocked_layers = tuple(layer for layer in involved_layers if layer != winner)
        evidence_summary = tuple(
            _strip(item.get("evidence_summary") or f"{item.get('layer')}={item.get('value')}")
            for item in comparable
            if _strip(item.get("evidence_summary") or item.get("value"))
        )
        return LayerConflictReport(
            conflict_id=f"conflict:{learning_key}",
            learning_key=learning_key,
            involved_layers=involved_layers,
            conflict_type="cross_layer_value_conflict",
            evidence_summary=evidence_summary,
            winner=winner,
            blocked_layers=blocked_layers,
            required_action="demote_or_review_conflicting_layers",
            explanation=f"{learning_key} disagrees across {', '.join(involved_layers)}; {winner} currently wins.",
        )

    def resolve_outcome_learning_conflicts(
        self,
        *,
        profile_state: dict[str, Any] | None,
        episode_state: dict[str, Any] | None,
        session_state: dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        by_key: dict[str, list[dict[str, Any]]] = {}
        for layer_name, state in (
            ("profile", _as_dict(profile_state)),
            ("episode", _as_dict(episode_state)),
            ("session", _as_dict(session_state)),
        ):
            for item in _as_list(state.get("validated_learnings")):
                if not isinstance(item, dict):
                    continue
                learning_key = _strip(item.get("learning_key"))
                direction = _strip(item.get("direction"))
                if not learning_key or not direction:
                    continue
                by_key.setdefault(learning_key, []).append(
                    {
                        "layer": layer_name,
                        "value": direction,
                        "confidence": item.get("confidence"),
                        "updated_at": item.get("promoted_at") or item.get("updated_at"),
                        "repeated_evidence": item.get("sample_count"),
                        "evidence_summary": _strip(item.get("summary")),
                    }
                )

        reports: list[dict[str, Any]] = []
        for learning_key, entries in by_key.items():
            report = self.resolve_field_conflict(
                learning_key=learning_key,
                layer_values=entries,
                context_preferred_layer="episode" if any(item.get("layer") == "episode" for item in entries) else None,
            )
            if report is not None:
                reports.append(report.to_dict())
        return reports

    def stale_items_from_governance(
        self,
        governance_by_key: dict[str, Any] | None,
        *,
        now: datetime | None = None,
    ) -> list[dict[str, Any]]:
        now = now or _utcnow()
        stale: list[dict[str, Any]] = []
        for key, metadata in _as_dict(governance_by_key).items():
            item = _as_dict(metadata)
            expires_at = _parse_dt(item.get("expires_at"))
            review_after = _parse_dt(item.get("review_after"))
            status = _strip(item.get("status"))
            if status in {"demoted", "blocked", "stale"}:
                stale.append({"learning_key": key, "status": status, "metadata": item})
                continue
            if expires_at is not None and expires_at <= now:
                stale.append({"learning_key": key, "status": "stale", "metadata": item})
                continue
            if review_after is not None and review_after <= now:
                stale.append({"learning_key": key, "status": "review_due", "metadata": item})
        return stale

    def build_growth_snapshot(
        self,
        *,
        constitutional_state: dict[str, Any],
        session_state: dict[str, Any],
        episode_state: dict[str, Any],
        profile_state: dict[str, Any],
        system_state: dict[str, Any],
        active_conflicts: list[dict[str, Any]] | None = None,
        stale_items: list[dict[str, Any]] | None = None,
        pending_promotions: list[dict[str, Any]] | None = None,
        pending_reviews: list[dict[str, Any]] | None = None,
    ) -> LayeredGrowthStateSnapshot:
        return LayeredGrowthStateSnapshot(
            constitutional_state=dict(constitutional_state),
            session_state=dict(session_state),
            episode_state=dict(episode_state),
            profile_state=dict(profile_state),
            system_state=dict(system_state),
            active_conflicts=tuple(dict(item) for item in (active_conflicts or []) if isinstance(item, dict)),
            stale_items=tuple(dict(item) for item in (stale_items or []) if isinstance(item, dict)),
            pending_promotions=tuple(dict(item) for item in (pending_promotions or []) if isinstance(item, dict)),
            pending_reviews=tuple(dict(item) for item in (pending_reviews or []) if isinstance(item, dict)),
        )

    def _pick_winner(
        self,
        values: list[dict[str, Any]],
        *,
        context_preferred_layer: str | None = None,
    ) -> str:
        scored: list[tuple[float, str]] = []
        for item in values:
            layer = _strip(item.get("layer"))
            repeated_evidence = min(1.0, max(0.0, float(item.get("repeated_evidence") or 0.0) / 4.0))
            confidence = max(0.0, min(1.0, float(item.get("confidence") or 0.0)))
            freshness = self._freshness_score(item.get("updated_at"))
            score = repeated_evidence * 0.45 + confidence * 0.35 + freshness * 0.2
            if context_preferred_layer and layer == context_preferred_layer:
                score += 0.6
            if layer == "profile":
                score += 0.05
            scored.append((score, layer))
        scored.sort(reverse=True)
        return scored[0][1] if scored else "profile"

    @staticmethod
    def _freshness_score(value: Any) -> float:
        timestamp = _parse_dt(value)
        if timestamp is None:
            return 0.4
        hours_old = max(0.0, (_utcnow() - timestamp).total_seconds() / 3600.0)
        return max(0.05, min(1.0, 1.0 - (hours_old / 720.0)))
