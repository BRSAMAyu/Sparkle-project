from __future__ import annotations

from app.services.analytics.learning_cutover_audit import LearningCutoverAuditor


def test_learning_cutover_audit_recommends_smoke_when_no_traces() -> None:
    report = LearningCutoverAuditor().build_report()

    assert report["recommendation"]["route"] == "run_real_smoke_first"
    assert "no_belief_traces" in report["recommendation"]["blockers"]


def test_learning_cutover_audit_recommends_bandit_shadow_when_density_is_sufficient() -> None:
    event_density = {
        "readiness": {
            "observed_task_outcomes": 80,
            "labeled_route_outcomes": 70,
            "daily_task_outcomes": 12.0,
            "daily_labeled_route_outcomes": 10.0,
        }
    }
    trace_summary = {
        "total_traces": 300,
        "comparable_traces": 260,
        "observed_outcomes": 90,
        "outcome_coverage_rate": 0.30,
        "training_eligible_traces": 80,
    }

    report = LearningCutoverAuditor().build_report(
        event_density=event_density,
        trace_summary=trace_summary,
    )

    assert report["recommendation"]["route"] == "contextual_bandit_shadow"
    assert report["recommendation"]["blockers"] == []
