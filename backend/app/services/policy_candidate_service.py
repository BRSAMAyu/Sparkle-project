from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any

from app.config import settings
from app.orchestration.expert_strategy_v2 import ExpertStrategyV2
from app.services.learning_feature_rollup_service import LearningFeatureRollupService
from app.services.policy_registry_service import PolicyRegistryService


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class PolicyCandidateService:
    """Generate channel-aware candidate policies from aggregated learning features."""

    SUPPORTED_CHANNELS = ("routing", "prompt", "toolchain")

    def __init__(self, redis_client=None):
        self.rollups = LearningFeatureRollupService(redis_client=redis_client)
        self.registry = PolicyRegistryService(redis_client=redis_client)

    async def run_candidate_job(
        self,
        *,
        window_days: int = 7,
        channel: str | None = None,
        channels: list[str] | None = None,
    ) -> dict[str, Any]:
        if not getattr(settings, "ENABLE_POLICY_CANDIDATE_PIPELINE", False):
            return {"status": "disabled", "reason": "flag_off"}

        chosen_channels = self._resolve_channels(channel=channel, channels=channels)
        rollups = await self.rollups.list_rollups(days=window_days)
        existing = await self.registry.list_candidates()

        total_created = 0
        total_skipped = 0
        total_groups = 0
        channel_summaries: list[dict[str, Any]] = []

        for current_channel in chosen_channels:
            grouped = _group_rollups_by_scope(rollups=rollups, channel=current_channel)
            baseline_q = _weighted_q_baseline(
                groups=(row for row in grouped.values() if str(row.get("scope_type", "")) == "global"),
                channel=current_channel,
            )
            created = 0
            skipped = 0
            groups_count = 0
            for item in grouped.values():
                groups_count += 1
                metrics = item["metrics"]
                scope_type = str(item.get("scope_type", "global"))
                support = _support_by_channel(metrics=metrics, channel=current_channel)
                min_support = self._scope_min_support(scope_type=scope_type, channel=current_channel)
                if support < min_support:
                    skipped += 1
                    self._metric_candidate(channel=current_channel, scope_type=scope_type, result="skipped_low_support")
                    continue
                if not self._needs_candidate(
                    channel=current_channel,
                    metrics=metrics,
                    q_score=float(item.get("q_score", 0.0)),
                    baseline_q=baseline_q,
                    normalized_latency=float(item.get("normalized_latency", 0.0)),
                ):
                    skipped += 1
                    self._metric_candidate(channel=current_channel, scope_type=scope_type, result="skipped_no_need")
                    continue
                candidate = self._build_candidate_payload(
                    channel=current_channel,
                    item=item,
                    window_days=window_days,
                    baseline_q=baseline_q,
                )
                if _has_equivalent_candidate(existing, candidate):
                    skipped += 1
                    self._metric_candidate(channel=current_channel, scope_type=scope_type, result="skipped_duplicate")
                    continue
                saved = await self.registry.create_candidate(candidate)
                if not getattr(settings, "ENABLE_POLICY_MANUAL_APPROVAL", True):
                    await self.registry.approve_candidate(
                        candidate_id=str(saved.get("id", "")),
                        reviewer="system:auto",
                        note="auto-approval enabled by configuration",
                    )
                created += 1
                self._metric_candidate(channel=current_channel, scope_type=scope_type, result="created")

            total_created += created
            total_skipped += skipped
            total_groups += groups_count
            channel_summaries.append(
                {
                    "channel": current_channel,
                    "baseline_q_score": round(baseline_q, 4),
                    "total_groups": groups_count,
                    "created": created,
                    "skipped": skipped,
                }
            )

        return {
            "status": "ok",
            "window_days": window_days,
            "channels": chosen_channels,
            "total_groups": total_groups,
            "created": total_created,
            "skipped": total_skipped,
            "channel_summaries": channel_summaries,
            "baseline_q_score": round(
                sum(float(item["baseline_q_score"]) for item in channel_summaries) / max(1, len(channel_summaries)),
                4,
            ),
        }

    @staticmethod
    def _metric_candidate(*, channel: str, scope_type: str, result: str) -> None:
        try:
            from app.core.metrics import META_POLICY_CANDIDATE_TOTAL
            META_POLICY_CANDIDATE_TOTAL.labels(
                channel=str(channel),
                scope_type=str(scope_type),
                result=str(result),
            ).inc()
        except Exception:
            return

    def _resolve_channels(self, *, channel: str | None, channels: list[str] | None) -> list[str]:
        if channel:
            selected = [str(channel)]
        elif channels:
            selected = [str(item) for item in channels]
        else:
            selected = ["routing"]

        allowed = set(self.SUPPORTED_CHANNELS)
        normalized: list[str] = []
        for item in selected:
            if item in allowed and item not in normalized:
                normalized.append(item)
        if not normalized:
            normalized = ["routing"]
        return normalized

    @staticmethod
    def _scope_min_support(*, scope_type: str, channel: str) -> int:
        if channel == "prompt":
            base = int(getattr(settings, "META_PROMPT_CANDIDATE_MIN_SUPPORT", 30))
        elif channel == "toolchain":
            base = int(getattr(settings, "META_TOOLCHAIN_CANDIDATE_MIN_SUPPORT", 25))
        else:
            base = 40

        if scope_type == "cohort":
            return max(base, int(getattr(settings, "COHORT_POLICY_MIN_SUPPORT", 80)))
        if scope_type == "personal":
            return max(max(10, base // 2), int(getattr(settings, "PERSONAL_POLICY_MIN_SUPPORT", 30)))
        return base

    @staticmethod
    def _needs_candidate(
        *,
        channel: str,
        metrics: dict[str, int],
        q_score: float,
        baseline_q: float,
        normalized_latency: float,
    ) -> bool:
        feedback_up = int(metrics.get("feedback_up", 0))
        feedback_down = int(metrics.get("feedback_down", 0))
        feedback_total = feedback_up + feedback_down
        feedback_up_rate = _rate(feedback_up, feedback_total)

        if channel == "prompt":
            selected = int(metrics.get("prompt_selected", 0))
            applied = int(metrics.get("prompt_applied", 0))
            apply_rate = _rate(applied, selected)
            if selected >= 20 and apply_rate < 0.8:
                return True
            if feedback_total >= 8 and feedback_up_rate < 0.56:
                return True
            if selected >= 30 and q_score + 0.02 < baseline_q:
                return True
            return False

        if channel == "toolchain":
            selected = int(metrics.get("toolchain_selected", 0))
            degraded = int(metrics.get("toolchain_degraded", 0))
            degrade_rate = _rate(degraded, selected)
            if selected >= 15 and degrade_rate > 0.06:
                return True
            if selected >= 20 and normalized_latency > 0.55:
                return True
            if feedback_total >= 8 and feedback_up_rate < 0.55:
                return True
            return False

        selected = int(metrics.get("expert_selected", 0))
        fallback = int(metrics.get("expert_fallback", 0))
        plan_total = int(metrics.get("plan_execution_total", 0))
        plan_success = int(metrics.get("plan_execution_success", 0))
        gate_blocked = int(metrics.get("quality_gate_blocked", 0))
        route_count = int(metrics.get("route_decision", 0))
        repair_triggered = int(metrics.get("plan_repair_triggered", 0))
        repair_success = int(metrics.get("plan_repair_succeeded", 0))
        repair_success_rate = _rate(repair_success, repair_triggered)

        fallback_rate = _rate(fallback, selected)
        quality_gate_pass_rate = _rate(plan_success, plan_total + gate_blocked)

        if fallback_rate > 0.08:
            return True
        if feedback_down >= 8 and feedback_up_rate < 0.55:
            return True
        if quality_gate_pass_rate < 0.85 and (plan_total + gate_blocked) >= 10:
            return True
        if repair_triggered >= 8 and repair_success_rate < 0.55:
            return True
        if route_count >= 30 and q_score + 0.02 < baseline_q:
            return True
        return False

    def _build_candidate_payload(
        self,
        *,
        channel: str,
        item: dict[str, Any],
        window_days: int,
        baseline_q: float,
    ) -> dict[str, Any]:
        metrics = item["metrics"]
        strategy_pack = str(item["strategy_pack"])
        scope_type = str(item.get("scope_type", "global"))
        scope_key = str(item.get("scope_key", "all"))
        base_policy = str(item.get("base_policy", f"expert_strategy_v2:{strategy_pack}"))
        normalized_latency = float(item.get("normalized_latency", 0.0) or 0.0)
        q_score_source = float(item.get("q_score", 0.0) or 0.0)
        failure_pattern_topn = item.get("failure_pattern_topn") if isinstance(item.get("failure_pattern_topn"), list) else []
        repair_success_rate = float(item.get("repair_success_rate", 0.0) or 0.0)

        selected_count = _support_by_channel(metrics=metrics, channel=channel)
        feedback_up = int(metrics.get("feedback_up", 0))
        feedback_down = int(metrics.get("feedback_down", 0))
        feedback_up_rate = _rate(feedback_up, feedback_up + feedback_down)

        weights: dict[str, float] = {}
        thresholds: dict[str, float] = {}
        params: dict[str, float] = {}
        arm_weights: dict[str, float] = {}

        if channel == "prompt":
            selected = int(metrics.get("prompt_selected", 0))
            applied = int(metrics.get("prompt_applied", 0))
            apply_rate = _rate(applied, selected)
            thresholds = {
                "min_feedback_up_rate": round(max(0.5, min(0.75, feedback_up_rate + 0.03)), 4),
                "min_prompt_apply_rate": round(max(0.7, min(0.95, apply_rate + 0.03)), 4),
            }
            params = {
                "exploration_ratio": round(0.12 if q_score_source < baseline_q else 0.18, 4),
            }
            if q_score_source + 0.02 < baseline_q:
                arm_weights = {"v1": 0.65, "v2": 0.35}
            else:
                arm_weights = {"v1": 0.4, "v2": 0.6}

        elif channel == "toolchain":
            selected = int(metrics.get("toolchain_selected", 0))
            degraded = int(metrics.get("toolchain_degraded", 0))
            degrade_rate = _rate(degraded, selected)
            thresholds = {
                "max_degrade_rate": round(max(0.03, min(0.18, degrade_rate - 0.01)), 4),
            }
            max_parallel = 2
            if degrade_rate > 0.1 or normalized_latency > 0.65:
                max_parallel = 1
            params = {
                "max_parallel_experts": float(max_parallel),
                "timeout_multiplier": round(1.15 if normalized_latency > 0.6 else 1.0, 3),
                "retry_limit": float(1 if degrade_rate > 0.08 else 2),
            }

        else:
            defaults = self._default_pack(strategy_pack)
            fallback_rate = _rate(int(metrics.get("expert_fallback", 0)), int(metrics.get("expert_selected", 0)))
            quality_gate_pass_rate = _rate(
                int(metrics.get("plan_execution_success", 0)),
                int(metrics.get("plan_execution_total", 0)) + int(metrics.get("quality_gate_blocked", 0)),
            )

            thresholds = dict(defaults["thresholds"])
            weights = dict(defaults["weights"])

            if fallback_rate > 0.06:
                thresholds["min_selected_score"] = min(0.7, thresholds["min_selected_score"] + 0.02)
                thresholds["medium_complexity_threshold"] = min(0.9, thresholds["medium_complexity_threshold"] + 0.03)
                thresholds["high_complexity_threshold"] = min(0.95, thresholds["high_complexity_threshold"] + 0.03)
            if normalized_latency > 0.55:
                thresholds["medium_complexity_threshold"] = min(0.9, thresholds["medium_complexity_threshold"] + 0.02)
                thresholds["high_complexity_threshold"] = min(0.95, thresholds["high_complexity_threshold"] + 0.02)
            if feedback_up_rate < 0.55:
                weights["semantic_weight"] = min(0.7, weights["semantic_weight"] + 0.04)
                weights["affinity_weight"] = max(0.05, weights["affinity_weight"] - 0.02)
            if quality_gate_pass_rate < 0.85:
                weights["decomposition_weight"] = min(0.35, weights["decomposition_weight"] + 0.03)
                weights["latency_weight"] = max(0.03, weights["latency_weight"] - 0.01)
            if repair_success_rate < 0.55:
                thresholds["min_selected_score"] = min(0.72, thresholds["min_selected_score"] + 0.015)
            weights = _normalize_weights(weights)

        expected_delta = round(
            max(0.0, baseline_q - q_score_source) * 0.45
            + max(0.0, 0.58 - feedback_up_rate) * 0.2
            + max(0.0, normalized_latency - 0.45) * 0.2
            + max(0.0, 0.55 - repair_success_rate) * 0.1
            + (0.05 if scope_type != "global" else 0.0),
            4,
        )
        risk_level = "low"
        if scope_type == "personal":
            risk_level = "high"
        elif expected_delta >= 0.12 or selected_count < 60:
            risk_level = "high"
        elif expected_delta >= 0.06:
            risk_level = "medium"

        window_token = (
            f"{window_days}d:{_utcnow().date().isoformat()}:"
            f"{channel}:{strategy_pack}:{scope_type}:{scope_key}:{base_policy}"
        )
        candidate_hash = hashlib.sha1(window_token.encode("utf-8")).hexdigest()[:8]
        candidate_id = f"pc_{channel}_{scope_type}_{strategy_pack}_{candidate_hash}"
        scope_prefix = {"global": "g", "cohort": "c", "personal": "p"}.get(scope_type, "g")
        channel_prefix = {"routing": "r", "prompt": "pm", "toolchain": "tc"}.get(channel, "r")
        policy_id = f"expert_strategy_v2:{strategy_pack}:candidate_{channel_prefix}_{scope_prefix}_{candidate_hash}"

        payload = {
            "id": candidate_id,
            "channel": channel,
            "policy_id": policy_id,
            "base_policy": base_policy,
            "strategy_pack": strategy_pack,
            "scope_type": scope_type,
            "scope_key": scope_key,
            "support_size": selected_count,
            "weights": weights,
            "thresholds": thresholds,
            "params": params,
            "arm_weights": arm_weights,
            "created_from_window": f"last_{window_days}d",
            "expected_delta": expected_delta,
            "risk_level": risk_level,
            "status": "pending",
            "rollout_percent": 10,
            "q_score_baseline": round(baseline_q, 4),
            "q_score_source": round(q_score_source, 4),
            "metrics_snapshot": {
                "expert_selected": int(metrics.get("expert_selected", 0)),
                "expert_fallback": int(metrics.get("expert_fallback", 0)),
                "prompt_selected": int(metrics.get("prompt_selected", 0)),
                "prompt_applied": int(metrics.get("prompt_applied", 0)),
                "toolchain_selected": int(metrics.get("toolchain_selected", 0)),
                "toolchain_degraded": int(metrics.get("toolchain_degraded", 0)),
                "feedback_up": feedback_up,
                "feedback_down": feedback_down,
                "repair_success_rate": round(repair_success_rate, 4),
                "failure_pattern_topn": failure_pattern_topn[:5],
                "failure_pattern_actions": _map_failure_patterns_to_actions(failure_pattern_topn[:5]),
                "quality_gate_blocked": int(metrics.get("quality_gate_blocked", 0)),
                "plan_execution_total": int(metrics.get("plan_execution_total", 0)),
                "plan_execution_success": int(metrics.get("plan_execution_success", 0)),
            },
            "created_at": _utcnow().isoformat(),
        }
        return payload

    @staticmethod
    def _default_pack(strategy_pack: str) -> dict[str, dict[str, float]]:
        pack_map = {
            ExpertStrategyV2.GENERAL_PACK.pack_id: ExpertStrategyV2.GENERAL_PACK,
            ExpertStrategyV2.STUDY_PLAN_PACK.pack_id: ExpertStrategyV2.STUDY_PLAN_PACK,
            ExpertStrategyV2.ERROR_DIAGNOSIS_PACK.pack_id: ExpertStrategyV2.ERROR_DIAGNOSIS_PACK,
            ExpertStrategyV2.DEEP_ANALYSIS_PACK.pack_id: ExpertStrategyV2.DEEP_ANALYSIS_PACK,
        }
        pack = pack_map.get(strategy_pack, ExpertStrategyV2.GENERAL_PACK)
        return {
            "thresholds": {
                "high_complexity_threshold": float(pack.high_complexity_threshold),
                "medium_complexity_threshold": float(pack.medium_complexity_threshold),
                "min_selected_score": float(pack.min_selected_score),
            },
            "weights": {
                "semantic_weight": float(pack.semantic_weight),
                "affinity_weight": float(pack.affinity_weight),
                "success_weight": float(pack.success_weight),
                "complexity_weight": float(pack.complexity_weight),
                "decomposition_weight": float(pack.decomposition_weight),
                "latency_weight": float(pack.latency_weight),
            },
        }


def _group_rollups_by_scope(*, rollups: list[dict[str, Any]], channel: str) -> dict[str, dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for row in rollups:
        strategy_pack = str(row.get("strategy_pack", "default"))
        cohort_id = str(row.get("cohort_id", ""))
        user_scope = str(row.get("user_scope", ""))
        metrics = row.get("counts") if isinstance(row.get("counts"), dict) else {}

        scopes = [
            ("global", "all"),
            ("cohort", cohort_id),
            ("personal", user_scope),
        ]
        for scope_type, scope_key in scopes:
            if scope_type != "global" and not scope_key:
                continue
            if scope_type == "personal" and scope_key == "usr::anon":
                continue
            key = f"{channel}|{scope_type}|{scope_key}|{strategy_pack}"
            if key not in grouped:
                grouped[key] = {
                    "channel": channel,
                    "scope_type": scope_type,
                    "scope_key": scope_key or "all",
                    "strategy_pack": strategy_pack,
                    "base_policy": f"expert_strategy_v2:{strategy_pack}",
                    "metrics": {},
                    "q_score": 0.0,
                    "normalized_latency": 0.0,
                    "_weighted_q_numerator": 0.0,
                    "_weighted_q_denominator": 0,
                    "_weighted_latency_numerator": 0.0,
                    "_weighted_repair_success_numerator": 0.0,
                    "_failure_patterns": {},
                }
            target = grouped[key]
            target_metrics = target["metrics"]
            for name, val in metrics.items():
                target_metrics[name] = int(target_metrics.get(name, 0)) + int(val or 0)
            support = max(1, _support_by_channel(metrics=metrics, channel=channel))
            target["_weighted_q_numerator"] += float(row.get("q_score", 0.0)) * support
            target["_weighted_latency_numerator"] += float(row.get("normalized_latency", 0.0)) * support
            target["_weighted_repair_success_numerator"] += float(row.get("repair_success_rate", 0.0)) * support
            target["_weighted_q_denominator"] += support
            failure_patterns = row.get("failure_pattern_topn")
            if isinstance(failure_patterns, list):
                merged_patterns = target["_failure_patterns"]
                for item in failure_patterns:
                    if not isinstance(item, dict):
                        continue
                    pattern = str(item.get("pattern", "")).strip()
                    if not pattern:
                        continue
                    try:
                        count = int(item.get("count", 0))
                    except (TypeError, ValueError):
                        count = 0
                    merged_patterns[pattern] = int(merged_patterns.get(pattern, 0)) + max(0, count)

    for row in grouped.values():
        denom = max(1, int(row.pop("_weighted_q_denominator")))
        q_numerator = float(row.pop("_weighted_q_numerator", 0.0))
        latency_numerator = float(row.pop("_weighted_latency_numerator", 0.0))
        repair_numerator = float(row.pop("_weighted_repair_success_numerator", 0.0))
        merged_patterns = row.pop("_failure_patterns", {})
        row["q_score"] = q_numerator / denom
        row["normalized_latency"] = latency_numerator / denom
        row["repair_success_rate"] = repair_numerator / denom
        pattern_rows = sorted(
            ((str(k), int(v)) for k, v in merged_patterns.items()),
            key=lambda item: item[1],
            reverse=True,
        )
        row["failure_pattern_topn"] = [
            {"pattern": name, "count": count}
            for name, count in pattern_rows[:5]
        ]
    return grouped


def _weighted_q_baseline(*, groups: Any, channel: str) -> float:
    numerator = 0.0
    denominator = 0
    for row in groups:
        metrics = row.get("metrics") if isinstance(row.get("metrics"), dict) else {}
        support = max(1, _support_by_channel(metrics=metrics, channel=channel))
        numerator += float(row.get("q_score", 0.0)) * support
        denominator += support
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def _normalize_weights(weights: dict[str, float]) -> dict[str, float]:
    ordered_keys = (
        "semantic_weight",
        "affinity_weight",
        "success_weight",
        "complexity_weight",
        "decomposition_weight",
        "latency_weight",
    )
    bounded = {key: max(0.01, float(weights.get(key, 0.01))) for key in ordered_keys}
    total = sum(bounded.values())
    if total <= 0:
        return {key: round(1.0 / len(ordered_keys), 4) for key in ordered_keys}
    return {key: round(val / total, 4) for key, val in bounded.items()}


def _support_by_channel(*, metrics: dict[str, int], channel: str) -> int:
    if channel == "prompt":
        return int(metrics.get("prompt_applied", 0) or metrics.get("prompt_selected", 0))
    if channel == "toolchain":
        return int(metrics.get("toolchain_selected", 0))
    return int(metrics.get("expert_selected", 0))


def _map_failure_patterns_to_actions(failure_pattern_topn: list[dict[str, Any]]) -> list[str]:
    actions: list[str] = []
    for item in failure_pattern_topn:
        if not isinstance(item, dict):
            continue
        pattern = str(item.get("pattern", ""))
        if "fallback" in pattern and "tighten_routing_thresholds" not in actions:
            actions.append("tighten_routing_thresholds")
        if "quality_gate" in pattern and "raise_contract_gate_weight" not in actions:
            actions.append("raise_contract_gate_weight")
        if "step::timeout" in pattern and "degrade_parallelism" not in actions:
            actions.append("degrade_parallelism")
        if "step::missing_output" in pattern and "harden_output_contract" not in actions:
            actions.append("harden_output_contract")
        if len(actions) >= 4:
            break
    return actions


def _rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return max(0.0, min(float(numerator) / float(denominator), 1.0))


def _has_equivalent_candidate(existing: list[dict[str, Any]], candidate: dict[str, Any]) -> bool:
    candidate_window = str(candidate.get("created_from_window", ""))
    candidate_pack = str(candidate.get("strategy_pack", ""))
    candidate_scope = str(candidate.get("scope_type", "global"))
    candidate_scope_key = str(candidate.get("scope_key", "all"))
    candidate_channel = str(candidate.get("channel", "routing"))
    for row in existing:
        if str(row.get("status")) == "rejected":
            continue
        if str(row.get("created_from_window", "")) != candidate_window:
            continue
        if str(row.get("strategy_pack", "")) != candidate_pack:
            continue
        if str(row.get("scope_type", "global")) != candidate_scope:
            continue
        if str(row.get("scope_key", "all")) != candidate_scope_key:
            continue
        if str(row.get("channel", "routing")) != candidate_channel:
            continue
        return True
    return False
