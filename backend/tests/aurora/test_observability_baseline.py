from __future__ import annotations

from app.aurora.observability import (
    AURORA_DECISION_TOTAL,
    AURORA_FALLBACK_TOTAL,
    AURORA_MATERIALITY_TOTAL,
    AURORA_SHADOW_DIVERGENCE_TOTAL,
    AURORA_SHADOW_HOOK_TOTAL,
    AURORA_TRIGGER_DISPATCH_TOTAL,
    record_decision,
    record_fallback,
    record_materiality,
    record_shadow_divergence,
    record_shadow_hook,
    record_trigger_dispatch,
)


def test_observability_metrics_are_registered() -> None:
    metric_names = {
        AURORA_DECISION_TOTAL._name,
        AURORA_MATERIALITY_TOTAL._name,
        AURORA_TRIGGER_DISPATCH_TOTAL._name,
        AURORA_FALLBACK_TOTAL._name,
        AURORA_SHADOW_DIVERGENCE_TOTAL._name,
        AURORA_SHADOW_HOOK_TOTAL._name,
    }

    assert "sparkle_aurora_decision" in metric_names
    assert "sparkle_aurora_fallback" in metric_names


def test_observability_recorders_accept_shadow_mode_payloads() -> None:
    record_materiality("pre-node-routing", "skip", enabled=True)
    record_trigger_dispatch("reactive", "pre-node-routing", "immediate", enabled=True)
    record_decision("pre-node-routing", "deterministic", "mixed", "shadow", "stay", enabled=True)
    record_shadow_hook("pre-tool-selection", "pre-tool-selection", "aligned", enabled=True)

    before_fallback = sum(
        sample.value
        for sample in AURORA_FALLBACK_TOTAL.collect()[0].samples
        if sample.name == "sparkle_aurora_fallback_total"
        and sample.labels.get("reason") == "snapshot_corrupted"
        and sample.labels.get("trigger_point") == "pre-node-routing"
    )
    record_fallback(reason="snapshot_corrupted", trigger_point="pre-node-routing", enabled=True)
    record_shadow_divergence("route_mismatch", "pre-node-routing", enabled=True)

    samples = AURORA_FALLBACK_TOTAL.collect()[0].samples
    assert any(
        sample.labels.get("reason") == "snapshot_corrupted"
        and sample.labels.get("trigger_point") == "pre-node-routing"
        and sample.value == before_fallback + 1.0
        for sample in samples
    )

    hook_samples = AURORA_SHADOW_HOOK_TOTAL.collect()[0].samples
    assert any(
        sample.labels.get("hook_point") == "pre-tool-selection"
        and sample.labels.get("trigger_point") == "pre-tool-selection"
        and sample.labels.get("outcome") == "aligned"
        for sample in hook_samples
    )
    assert any(
        sample.labels.get("signal") == "route_mismatch"
        and sample.labels.get("trigger_point") == "pre-node-routing"
        for sample in AURORA_SHADOW_DIVERGENCE_TOTAL.collect()[0].samples
    )
