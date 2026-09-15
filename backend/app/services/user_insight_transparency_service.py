from __future__ import annotations

from typing import Any

from app.core.user_insight_state import UserInsightState
from app.services.personalization.inferred_meta import INFERRED_META


def _strip(value: Any) -> str:
    return str(value or "").strip()


def _display_value(value: Any) -> Any:
    if isinstance(value, dict) and set(value.keys()) == {"value"}:
        return value.get("value")
    return value


class UserInsightTransparencyService:
    """Render the canonical insight state into a user-facing transparency surface."""

    def build_payload(
        self,
        *,
        state: UserInsightState,
        merged_preferences: dict[str, Any],
        inferred_backups: dict[str, dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        inferred_backups = inferred_backups or {}
        scope_overrides = dict(merged_preferences.get("insight_scope_overrides") or {})

        claims = [
            self._build_claim(evidence=evidence, scope_overrides=scope_overrides, inferred_backups=inferred_backups)
            for evidence in state.signal_evidence
        ]
        claims.sort(
            key=lambda item: (
                -float(item.get("confidence") or 0.0),
                str(item.get("family") or ""),
                str(item.get("id") or ""),
            )
        )

        predictions = [
            self._build_prediction_item(prediction_id, payload)
            for prediction_id, payload in state.prediction_summaries.items()
            if isinstance(payload, dict)
        ]
        predictions.sort(key=lambda item: (str(item.get("kind") or ""), str(item.get("id") or "")))

        recent_changes = self._recent_changes(state)
        unknowns = self._unknowns(state)

        return {
            "claims": claims,
            "predictions": predictions,
            "recent_changes": recent_changes,
            "unknowns": unknowns,
            "calibration": dict(state.calibration_summary or {}),
            "current_profile": {
                "stable_preferences": dict(state.stable_preferences or {}),
                "current_state": dict(state.current_state or {}),
                "inferred_work_style": dict(state.inferred_work_style or {}),
            },
        }

    def _build_claim(
        self,
        *,
        evidence,
        scope_overrides: dict[str, Any],
        inferred_backups: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        meta = INFERRED_META.get(evidence.signal_id)
        scope_override = scope_overrides.get(evidence.signal_id) if isinstance(scope_overrides, dict) else None
        scope_value = ""
        if isinstance(scope_override, dict):
            scope_value = _strip(scope_override.get("scope"))
        elif scope_override not in (None, "", [], {}):
            scope_value = _strip(scope_override)

        controls = ["wrong", "used_to_be_true"]
        if meta and meta.adjustable:
            controls.append("exam_mode_only")
        if evidence.signal_id in inferred_backups:
            controls.append("reset_override")

        return {
            "id": evidence.signal_id,
            "family": evidence.family,
            "label": evidence.label,
            "value": _display_value(evidence.value),
            "confidence": round(float(evidence.confidence or 0.0), 3),
            "freshness": _strip(evidence.freshness),
            "status": _strip(scope_value or evidence.status),
            "source": _strip(evidence.source),
            "surfaces": list(evidence.surfaces or []),
            "explanation": _strip(evidence.explanation),
            "controls": controls,
        }

    @staticmethod
    def _build_prediction_item(prediction_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": prediction_id,
            "kind": _strip(payload.get("kind")),
            "level": _strip(payload.get("level")),
            "score": payload.get("score"),
            "confidence": payload.get("calibrated_confidence", payload.get("confidence")),
            "recommended_action": _strip(payload.get("recommended_action")),
            "explanation": _strip(payload.get("explanation")),
            "evidence_signals": list(payload.get("evidence_signals") or []),
            "calibration_status": _strip(payload.get("calibration_status")),
        }

    @staticmethod
    def _recent_changes(state: UserInsightState) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for win in state.recent_wins[:3]:
            items.append({"type": "recent_win", "label": _strip(win.get("label")), "details": dict(win)})
        for pain in state.recent_pain_points[:2]:
            items.append({"type": "recent_pain", "label": _strip(pain.get("label")), "details": dict(pain)})
        for correction in list((state.calibration_summary or {}).get("recent_corrections") or [])[:3]:
            items.append({"type": "correction", "label": _strip(correction.get("target")), "details": dict(correction)})
        return items

    @staticmethod
    def _unknowns(state: UserInsightState) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for marker in state.uncertainty_markers[:5]:
            if isinstance(marker, dict):
                items.append({"id": _strip(marker.get("id")), "description": _strip(marker.get("description"))})
        for item in state.missing_information[:5]:
            text = _strip(item)
            if text:
                items.append({"id": text, "description": text})
        return items
