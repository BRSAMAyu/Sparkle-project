from uuid import uuid4

from app.orchestration.adaptive_replanner import AdaptiveReplanner
from app.orchestration.step_feedback_collector import PlanExecutionFeedback
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


def test_adaptive_replanner_builds_execution_feedback_revision_summary() -> None:
    replanner = AdaptiveReplanner(db=None, redis=None)
    feedback = PlanExecutionFeedback(
        plan_id=str(uuid4()),
        user_id=str(uuid4()),
        session_id="session-1",
        validation_status="failed",
        quality_score=0.41,
        total_steps=4,
        steps_passed=1,
        steps_failed=3,
        aborted=True,
        step_feedbacks=[],
        slow_tools=["search"],
        failed_tools=["planner"],
        unreliable_dependencies=["step-2"],
    )

    summary = replanner._build_execution_revision_summary(
        feedback=feedback,
        outcome_learning={
            "known_failure_avoidance_rules": ["Avoid retrying the same failed tool chain."],
            "known_success_patterns": ["Keep the validated boundary small."],
        },
    )

    payload = summary.to_dict()
    assert "validation_status=failed" in payload["why_plan_changed"]
    assert "Avoid retrying the same failed tool chain." in payload["why_plan_changed"]
    assert "planner" in payload["what_assumption_failed"]
    assert "Keep the validated boundary small." in payload["what_stays"]
    assert "失败" in payload["what_changes"] or "修复" in payload["what_changes"]
    assert "重新开始" in payload["new_next_action"] or "retry" in payload["new_next_action"].lower()
