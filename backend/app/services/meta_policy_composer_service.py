from __future__ import annotations

import hashlib
from typing import Any

from app.config import settings


class MetaPolicyComposerService:
    """Compose global/cohort/personal policy layers with support-aware shrinkage."""

    @classmethod
    def compose(
        cls,
        *,
        strategy_pack: str,
        channel: str,
        layers: list[dict[str, Any]],
        cohort_id: str,
        user_scope: str,
    ) -> dict[str, Any]:
        if not layers:
            raise ValueError("layers_required")

        base_alpha = {
            "global": float(getattr(settings, "META_POLICY_GLOBAL_WEIGHT", 0.55)),
            "cohort": float(getattr(settings, "META_POLICY_COHORT_WEIGHT", 0.30)),
            "personal": float(getattr(settings, "META_POLICY_PERSONAL_WEIGHT", 0.15)),
        }
        min_support = {
            "global": 1,
            "cohort": int(getattr(settings, "COHORT_POLICY_MIN_SUPPORT", 80)),
            "personal": int(getattr(settings, "PERSONAL_POLICY_MIN_SUPPORT", 30)),
        }

        reliability: list[float] = []
        for layer in layers:
            scope_type = str(layer.get("scope_type", "global"))
            support_size = max(0, int(layer.get("support_size", 0) or 0))
            threshold = max(1, min_support.get(scope_type, 1))
            ratio = min(1.0, float(support_size) / float(threshold))
            reliability.append(max(0.0, ratio))

        raw_alpha = [
            max(0.0, base_alpha.get(str(layer.get("scope_type", "global")), 0.0)) * reliability[idx]
            for idx, layer in enumerate(layers)
        ]
        alpha_sum = sum(raw_alpha)
        if alpha_sum <= 0:
            normalized = [1.0 / len(layers) for _ in layers]
        else:
            normalized = [val / alpha_sum for val in raw_alpha]

        blend_maps = {
            "weights": cls._blend_numeric_dicts(
                dicts=[layer.get("weights") if isinstance(layer.get("weights"), dict) else {} for layer in layers],
                weights=normalized,
            ),
            "thresholds": cls._blend_numeric_dicts(
                dicts=[layer.get("thresholds") if isinstance(layer.get("thresholds"), dict) else {} for layer in layers],
                weights=normalized,
            ),
            "params": cls._blend_numeric_dicts(
                dicts=[layer.get("params") if isinstance(layer.get("params"), dict) else {} for layer in layers],
                weights=normalized,
            ),
            "arm_weights": cls._blend_numeric_dicts(
                dicts=[layer.get("arm_weights") if isinstance(layer.get("arm_weights"), dict) else {} for layer in layers],
                weights=normalized,
            ),
        }
        selected_layers = []
        layer_ids: list[str] = []
        for idx, layer in enumerate(layers):
            policy_id = str(layer.get("policy_id", ""))
            if policy_id:
                layer_ids.append(policy_id)
            selected_layers.append(
                {
                    "policy_id": policy_id,
                    "scope_type": str(layer.get("scope_type", "global")),
                    "scope_key": str(layer.get("scope_key", "")),
                    "status": str(layer.get("status", "")),
                    "support_size": int(layer.get("support_size", 0) or 0),
                    "alpha": round(normalized[idx], 4),
                }
            )

        hash_seed = "|".join(layer_ids) if layer_ids else "none"
        composed_policy_id = (
            f"meta_policy_v1:{channel}:{strategy_pack}:{hashlib.sha1(hash_seed.encode('utf-8')).hexdigest()[:8]}"
        )
        result = {
            "policy_id": composed_policy_id,
            "strategy_pack": strategy_pack,
            "channel": channel,
            "selected_layers": selected_layers,
            "scope_resolution": {
                "cohort_id": cohort_id,
                "user_scope": user_scope,
            },
            "meta_learning_scope": cls._resolve_scope_label(selected_layers),
        }
        for key, value in blend_maps.items():
            if value:
                result[key] = value
        return result

    @staticmethod
    def _resolve_scope_label(layers: list[dict[str, Any]]) -> str:
        scopes = {str(layer.get("scope_type", "")) for layer in layers}
        if scopes == {"global"}:
            return "global"
        if scopes == {"cohort"}:
            return "cohort"
        if scopes == {"personal"}:
            return "personal"
        return "composed"

    @staticmethod
    def _blend_numeric_dicts(*, dicts: list[dict[str, Any]], weights: list[float]) -> dict[str, float]:
        aggregate: dict[str, float] = {}
        for idx, item in enumerate(dicts):
            if not isinstance(item, dict):
                continue
            weight = weights[idx] if idx < len(weights) else 0.0
            for key, value in item.items():
                try:
                    numeric = float(value)
                except (TypeError, ValueError):
                    continue
                aggregate[str(key)] = aggregate.get(str(key), 0.0) + weight * numeric
        return {key: round(val, 6) for key, val in aggregate.items()}

