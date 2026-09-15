from __future__ import annotations

from app.services.analytics.user_state_model import UserArchetype
from app.services.analytics.user_state_model_audit import UserStateModelAuditor


def test_user_state_model_audit_reports_archetype_policy_metrics() -> None:
    report = UserStateModelAuditor().run(
        samples_per_archetype=6,
        steps=12,
        seed=101,
        archetypes=[UserArchetype.FRAGILE, UserArchetype.RESILIENT],
        policies=("execution_stress", "support_recovery"),
    )

    assert report["schema_version"] == "user_state_model_audit.v1"
    assert "fragile:execution_stress" in report["summaries"]
    assert "resilient:support_recovery" in report["summaries"]
    fragile_exec = report["summaries"]["fragile:execution_stress"]
    resilient_exec = report["summaries"]["resilient:execution_stress"]
    assert 0.0 <= fragile_exec["collapse_rate"] <= 1.0
    assert 0.0 <= resilient_exec["consistency_failure_rate"] <= 1.0
    assert "avg_final_state" in fragile_exec
