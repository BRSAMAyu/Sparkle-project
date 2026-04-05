from __future__ import annotations

from typing import Any

from app.services.user_strategy_state_service import UserStrategyStateService


def _as_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return []


def _strip(value: Any) -> str:
    return str(value or "").strip()


class CapabilityKnobGovernor:
    """Bound Phase D capability-driven knob writes to safe existing strategy fields."""

    ALLOWED_FIELDS = {
        "retrieval_emphasis",
        "session_mode",
        "intervention_intensity",
        "explanation_style",
        "difficulty_level",
        "push_vs_support",
    }

    def evaluate(
        self,
        *,
        adjustments: list[dict[str, Any]] | None,
        strategy_state: dict[str, Any] | None,
    ) -> dict[str, Any]:
        strategy_state = _as_dict(strategy_state)
        allowed: list[dict[str, Any]] = []
        blocked: list[dict[str, Any]] = []

        for item in _as_list(adjustments):
            if not isinstance(item, dict):
                continue
            field = _strip(item.get("field"))
            layer = _strip(item.get("target_layer") or UserStrategyStateService.SESSION_LAYER)
            reversible = bool(item.get("reversible"))
            recommended_value = item.get("recommended_value")

            if field not in self.ALLOWED_FIELDS:
                blocked.append(
                    {
                        "field": field,
                        "reason": "field_not_allowlisted",
                    }
                )
                continue
            if layer != UserStrategyStateService.SESSION_LAYER:
                blocked.append(
                    {
                        "field": field,
                        "reason": "non_session_write_blocked",
                    }
                )
                continue
            if not reversible:
                blocked.append(
                    {
                        "field": field,
                        "reason": "non_reversible_write_blocked",
                    }
                )
                continue
            if field not in UserStrategyStateService.FIELD_SPECS:
                blocked.append({"field": field, "reason": "unknown_strategy_field"})
                continue
            if strategy_state.get(field) == recommended_value:
                continue

            allowed.append(
                {
                    **item,
                    "target_layer": UserStrategyStateService.SESSION_LAYER,
                    "source": _strip(item.get("source") or "phase_d"),
                }
            )

        return {
            "allowed_adjustments": allowed,
            "blocked_adjustments": blocked,
        }
