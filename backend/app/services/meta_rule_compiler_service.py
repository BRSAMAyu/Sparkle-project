from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class MetaRuleCompileResult:
    patches: dict[str, dict[str, Any]]
    meta_rule_ids: list[str]
    motif_graph_id: str
    transfer_source: str
    rule_confidence: float
    rule_block_reason: str = ""
    rule_block_detail: dict[str, Any] | None = None


class MetaRuleCompilerService:
    """Compile active cognitive rules into channel-level runtime patches."""

    CHANNELS = ("routing", "prompt", "toolchain")

    @classmethod
    def compile(
        cls,
        *,
        rules: list[dict[str, Any]],
        task_type: str,
        complexity_tier: str,
        cohort_id: str = "",
        user_scope: str = "",
        allow_personal: bool = True,
        guardrail_inputs: dict[str, Any] | None = None,
    ) -> MetaRuleCompileResult:
        matched = cls._select_rules(
            rules=rules,
            task_type=task_type,
            complexity_tier=complexity_tier,
            cohort_id=cohort_id,
            user_scope=user_scope,
            allow_personal=allow_personal,
        )
        if not matched:
            return MetaRuleCompileResult(
                patches={},
                meta_rule_ids=[],
                motif_graph_id="",
                transfer_source="global",
                rule_confidence=0.0,
            )

        block_reason = cls._guardrail_block_reason(guardrail_inputs or {})
        if block_reason:
            return MetaRuleCompileResult(
                patches={},
                meta_rule_ids=[str(item.get("rule_id", "")) for item in matched],
                motif_graph_id=str(matched[0].get("motif_graph_id", "")),
                transfer_source=cls._resolve_transfer_source(matched),
                rule_confidence=round(cls._avg_confidence(matched), 4),
                rule_block_reason=block_reason,
                rule_block_detail=cls._build_block_detail(block_reason=block_reason, guardrail_inputs=guardrail_inputs or {}),
            )

        channel_groups: dict[str, list[dict[str, Any]]] = {channel: [] for channel in cls.CHANNELS}
        for row in matched:
            channel = str(row.get("channel", "routing"))
            if channel not in channel_groups:
                continue
            channel_groups[channel].append(row)

        patches: dict[str, dict[str, Any]] = {}
        for channel, rows in channel_groups.items():
            if not rows:
                continue
            patches[channel] = cls._compose_channel_patch(channel=channel, rows=rows)

        return MetaRuleCompileResult(
            patches=patches,
            meta_rule_ids=[str(item.get("rule_id", "")) for item in matched],
            motif_graph_id=str(matched[0].get("motif_graph_id", "")),
            transfer_source=cls._resolve_transfer_source(matched),
            rule_confidence=round(cls._avg_confidence(matched), 4),
        )

    @classmethod
    def _compose_channel_patch(cls, *, channel: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
        confidence = cls._avg_confidence(rows)
        expected_delta = max(0.0, sum(float(row.get("expected_delta_q", 0.0) or 0.0) for row in rows))
        guardrail_limits = {
            "max_fallback_rate": min(0.12, 0.08 + (0.05 * (1.0 - confidence))),
            "max_negative_feedback_rate": min(0.65, 0.55 + (0.1 * (1.0 - confidence))),
            "max_p95_latency_delta": 0.12,
            "max_stable_cohort_q_gap": 0.08,
        }

        action_overrides: list[str] = []
        for row in rows:
            for action in row.get("recommended_actions", []) if isinstance(row.get("recommended_actions"), list) else []:
                if action not in action_overrides:
                    action_overrides.append(str(action))

        weight_overrides: dict[str, float] = {}
        threshold_overrides: dict[str, float] = {}
        if channel == "routing":
            weight_overrides = {
                "decomposition_weight": round(0.12 + min(0.2, expected_delta), 4),
                "latency_weight": round(max(0.04, 0.08 - min(0.04, expected_delta / 2)), 4),
            }
            threshold_overrides = {
                "min_selected_score": round(0.34 + min(0.06, expected_delta / 2), 4),
            }
        elif channel == "prompt":
            threshold_overrides = {
                "min_prompt_apply_rate": round(0.78 + min(0.12, expected_delta), 4),
            }
            weight_overrides = {"clarification_guidance_weight": round(0.3 + min(0.3, expected_delta), 4)}
        elif channel == "toolchain":
            threshold_overrides = {
                "max_parallel_experts": round(max(1.0, 2.0 - min(1.0, expected_delta * 10)), 3),
                "timeout_multiplier": round(1.0 + min(0.25, expected_delta), 3),
            }
            weight_overrides = {"repair_weight": round(0.2 + min(0.3, expected_delta), 4)}

        return {
            "channel": channel,
            "weight_overrides": weight_overrides,
            "threshold_overrides": threshold_overrides,
            "action_overrides": action_overrides[:6],
            "guardrail_limits": guardrail_limits,
            "source_rule_ids": [str(row.get("rule_id", "")) for row in rows],
            "confidence": round(confidence, 4),
        }

    @staticmethod
    def _select_rules(
        *,
        rules: list[dict[str, Any]],
        task_type: str,
        complexity_tier: str,
        cohort_id: str,
        user_scope: str,
        allow_personal: bool,
    ) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for row in rules:
            if str(row.get("status", "")) != "active":
                continue
            rule_task = str(row.get("task_type", ""))
            if rule_task and rule_task != task_type:
                continue
            tier = str(row.get("complexity_tier", "unknown"))
            if tier not in {"unknown", complexity_tier}:
                continue
            scope_type = str(row.get("scope_type", "global") or "global")
            scope_key_raw = row.get("scope_key")
            scope_key = str(scope_key_raw) if scope_key_raw is not None else ""
            if scope_type == "global":
                pass
            elif scope_type == "cohort":
                # Backward compatibility: legacy cohort rules may miss scope_key and should behave as wildcard.
                if scope_key and scope_key not in {"all", "*"} and scope_key != cohort_id:
                    continue
            elif scope_type == "personal":
                if not allow_personal:
                    continue
                # Personal scope must be explicit and exact; never wildcard to avoid leakage.
                if not user_scope or not scope_key or scope_key != user_scope:
                    continue
            else:
                continue
            out.append(row)
        out.sort(
            key=lambda item: (
                float(item.get("confidence", 0.0) or 0.0),
                float(item.get("support_size", 0) or 0.0),
            ),
            reverse=True,
        )
        return out[:8]

    @staticmethod
    def _avg_confidence(rows: list[dict[str, Any]]) -> float:
        if not rows:
            return 0.0
        return sum(float(row.get("confidence", 0.0) or 0.0) for row in rows) / max(1, len(rows))

    @staticmethod
    def _resolve_transfer_source(rows: list[dict[str, Any]]) -> str:
        scopes = {str(item.get("scope_type", "global")) for item in rows if str(item.get("scope_type", ""))}
        if not scopes:
            return "global"
        if scopes == {"global"}:
            return "global"
        if scopes == {"cohort"}:
            return "cohort"
        if scopes == {"personal"}:
            return "personal"
        return "composed"

    @staticmethod
    def _guardrail_block_reason(guardrail_inputs: dict[str, Any]) -> str:
        negative_feedback_rate = float(guardrail_inputs.get("negative_feedback_rate", 0.0) or 0.0)
        fallback_rate = float(guardrail_inputs.get("fallback_rate", 0.0) or 0.0)
        stable_cohort_q_gap = float(guardrail_inputs.get("stable_cohort_q_gap", 0.0) or 0.0)
        p95_delta = float(guardrail_inputs.get("p95_latency_delta", 0.0) or 0.0)
        if negative_feedback_rate > 0.55:
            return "guardrail_negative_feedback"
        if fallback_rate > 0.12:
            return "guardrail_fallback_rate"
        if stable_cohort_q_gap > 0.08:
            return "guardrail_fairness_gap"
        if p95_delta > 0.12:
            return "guardrail_latency_budget"
        return ""

    @staticmethod
    def _build_block_detail(*, block_reason: str, guardrail_inputs: dict[str, Any]) -> dict[str, Any]:
        metric_by_reason = {
            "guardrail_negative_feedback": ("negative_feedback_rate", 0.55),
            "guardrail_fallback_rate": ("fallback_rate", 0.12),
            "guardrail_fairness_gap": ("stable_cohort_q_gap", 0.08),
            "guardrail_latency_budget": ("p95_latency_delta", 0.12),
        }
        metric_name, threshold = metric_by_reason.get(block_reason, ("unknown", 0.0))
        observed = float(guardrail_inputs.get(metric_name, 0.0) or 0.0) if metric_name != "unknown" else 0.0
        return {
            "reason": block_reason,
            "metric": metric_name,
            "threshold": round(float(threshold), 4),
            "observed": round(float(observed), 4),
            "inputs": {
                "negative_feedback_rate": round(float(guardrail_inputs.get("negative_feedback_rate", 0.0) or 0.0), 4),
                "fallback_rate": round(float(guardrail_inputs.get("fallback_rate", 0.0) or 0.0), 4),
                "stable_cohort_q_gap": round(float(guardrail_inputs.get("stable_cohort_q_gap", 0.0) or 0.0), 4),
                "p95_latency_delta": round(float(guardrail_inputs.get("p95_latency_delta", 0.0) or 0.0), 4),
            },
            "source": str(guardrail_inputs.get("_source", "heuristic")),
            "support": int(float(guardrail_inputs.get("_support", 0) or 0)),
        }
