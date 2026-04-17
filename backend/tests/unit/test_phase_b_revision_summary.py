from uuid import uuid4

from app.orchestration.adaptive_replanner import AdaptiveReplanner
from app.services.plan_progress_service import PlanHealthReport


def test_adaptive_replanner_builds_revision_summary() -> None:
    replanner = AdaptiveReplanner(db=None, redis=None)
    report = PlanHealthReport(
        plan_id=uuid4(),
        user_id=uuid4(),
        status="at_risk",
        severity="high",
        reasons=["time_overrun", "difficulty_too_hard"],
        metrics={},
        requires_adjustment=True,
        recommended_action="replan",
    )

    summary = replanner._build_revision_summary(
        report=report,
        feedback_category="too_difficult",
        what_changes="Reduce workload and resequence the current phase.",
        new_next_action="Start with one 20-minute prerequisite review block.",
        outcome_learning={
            "known_failure_avoidance_rules": ["Avoid dense first steps when similar conditions recur."],
            "known_success_patterns": ["Grounded planning improved outcomes in similar scenarios."],
        },
    )

    payload = summary.to_dict()
    assert "time_overrun" in payload["why_plan_changed"]
    assert "validated learning" in payload["why_plan_changed"]
    assert "too_difficult" in payload["what_assumption_failed"]
    assert "Grounded planning improved outcomes" in payload["what_stays"]
    assert payload["what_changes"] == "Reduce workload and resequence the current phase."
    assert payload["new_next_action"] == "Start with one 20-minute prerequisite review block."
