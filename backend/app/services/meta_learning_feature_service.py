from __future__ import annotations

from collections import defaultdict
from typing import Any

from app.config import settings
from app.services.learning_feature_rollup_service import LearningFeatureRollupService


class MetaLearningFeatureService:
    """Build cross-channel, scope-aware feature vectors for meta-learning candidates."""

    def __init__(self, redis_client=None):
        self.rollup_service = LearningFeatureRollupService(redis_client=redis_client)

    async def build_feature_vectors(
        self,
        *,
        days: int = 14,
        channels: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        rows = await self.rollup_service.list_rollups(days=days)
        target_channels = channels or ["routing", "prompt", "toolchain"]

        grouped: dict[str, dict[str, Any]] = {}
        baseline_by_pack_channel: dict[str, list[tuple[float, int]]] = defaultdict(list)
        for row in rows:
            for channel in target_channels:
                support = _support_by_channel(row=row, channel=channel)
                if support <= 0:
                    continue
                strategy_pack = str(row.get("strategy_pack", "default"))
                cohort_id = str(row.get("cohort_id", ""))
                user_scope = str(row.get("user_scope", ""))
                scopes = [("global", "all"), ("cohort", cohort_id), ("personal", user_scope)]
                for scope_type, scope_key in scopes:
                    if scope_type != "global" and not scope_key:
                        continue
                    if scope_type == "personal" and scope_key == "usr::anon":
                        continue
                    key = f"{channel}|{scope_type}|{scope_key}|{strategy_pack}"
                    target = grouped.setdefault(
                        key,
                        {
                            "channel": channel,
                            "scope_type": scope_type,
                            "scope_key": scope_key or "all",
                            "strategy_pack": strategy_pack,
                            "_support": 0,
                            "_q_numerator": 0.0,
                            "_latency_numerator": 0.0,
                            "_feedback_numerator": 0.0,
                            "_fallback_numerator": 0.0,
                            "_prompt_apply_numerator": 0.0,
                            "_toolchain_degrade_numerator": 0.0,
                            "_adoption_numerator": 0.0,
                        },
                    )
                    target["_support"] += support
                    target["_q_numerator"] += float(row.get("q_score", 0.0)) * support
                    target["_latency_numerator"] += float(row.get("normalized_latency", 0.0)) * support
                    target["_feedback_numerator"] += float(row.get("feedback_up_rate", 0.0)) * support
                    target["_fallback_numerator"] += float(row.get("fallback_rate", 0.0)) * support
                    target["_prompt_apply_numerator"] += float(row.get("prompt_apply_rate", 0.0)) * support
                    target["_toolchain_degrade_numerator"] += float(row.get("toolchain_degrade_rate", 0.0)) * support
                    route_count = int((row.get("counts") or {}).get("route_decision", 0))
                    adoption = min(1.0, support / max(1, route_count)) if route_count > 0 else 0.0
                    target["_adoption_numerator"] += adoption * support
                    if scope_type == "global":
                        baseline_by_pack_channel[f"{channel}|{strategy_pack}"].append(
                            (float(row.get("q_score", 0.0)), support)
                        )

        baseline_q: dict[str, float] = {}
        for key, vals in baseline_by_pack_channel.items():
            numerator = sum(v * w for v, w in vals)
            denominator = max(1, sum(w for _, w in vals))
            baseline_q[key] = numerator / denominator

        vectors: list[dict[str, Any]] = []
        for item in grouped.values():
            support = int(item.pop("_support"))
            if support <= 0:
                continue
            q_score = float(item.pop("_q_numerator")) / support
            normalized_latency = float(item.pop("_latency_numerator")) / support
            feedback_up_rate = float(item.pop("_feedback_numerator")) / support
            fallback_rate = float(item.pop("_fallback_numerator")) / support
            prompt_apply_rate = float(item.pop("_prompt_apply_numerator")) / support
            toolchain_degrade_rate = float(item.pop("_toolchain_degrade_numerator")) / support
            adoption_rate = float(item.pop("_adoption_numerator")) / support

            baseline = float(baseline_q.get(f"{item['channel']}|{item['strategy_pack']}", q_score))
            fairness_penalty = max(0.0, baseline - q_score)
            q_global = (
                0.45 * q_score
                + 0.20 * adoption_rate
                + 0.20 * max(0.0, 1.0 - fairness_penalty)
                + 0.15 * max(0.0, 1.0 - normalized_latency)
            )
            vectors.append(
                {
                    **item,
                    "support": support,
                    "q_score": round(q_score, 4),
                    "baseline_q_score": round(baseline, 4),
                    "fairness_gap": round(fairness_penalty, 4),
                    "normalized_latency": round(normalized_latency, 4),
                    "feedback_up_rate": round(feedback_up_rate, 4),
                    "fallback_rate": round(fallback_rate, 4),
                    "prompt_apply_rate": round(prompt_apply_rate, 4),
                    "toolchain_degrade_rate": round(toolchain_degrade_rate, 4),
                    "adoption_rate": round(adoption_rate, 4),
                    "q_global": round(max(0.0, min(q_global, 1.0)), 4),
                    "quality_stable": q_score >= (baseline - float(getattr(settings, "META_Q_STABLE_DELTA", 0.015))),
                }
            )
        return vectors


def _support_by_channel(*, row: dict[str, Any], channel: str) -> int:
    counts = row.get("counts") if isinstance(row.get("counts"), dict) else {}
    if channel == "prompt":
        return int(counts.get("prompt_applied", 0) or counts.get("prompt_selected", 0))
    if channel == "toolchain":
        return int(counts.get("toolchain_selected", 0))
    return int(counts.get("expert_selected", 0))

