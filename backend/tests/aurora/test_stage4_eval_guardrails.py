from __future__ import annotations
from pathlib import Path
from time import perf_counter

from app.aurora.engine import AuroraDecisionContext, AuroraEngine

from .stage4_eval_support import (
    build_corpus_v1_cases,
    build_corpus_v2_cases,
    build_p1_guardrail_report,
    build_stage4_corpus_placeholders,
    run_corpus_v1_with_runner,
    summarize_tier_tagged_events,
)


def test_stage4_corpus_v1_content_covers_required_dispatch_categories() -> None:
    cases = build_corpus_v1_cases()

    assert len(cases) >= 20
    categories = {case.category for case in cases}
    assert categories == {
        "casual_direct",
        "workflow_plan",
        "task_assistant",
        "escalation",
        "fallback_or_miss",
    }
    routing_targets = {case.routing_target for case in cases}
    assert routing_targets == {"direct", "workflow", "task_assistant"}


def test_stage4_corpus_v2_v3_v4_placeholders_are_ready_before_wave_1b() -> None:
    placeholders = {placeholder.corpus_id: placeholder for placeholder in build_stage4_corpus_placeholders()}

    assert set(placeholders) == {"Corpus V2", "Corpus V3", "Corpus V4"}
    assert placeholders["Corpus V2"].distribution == {"direct": 10, "workflow": 10, "task_assistant": 10}
    assert placeholders["Corpus V2"].status == "materialized"
    assert placeholders["Corpus V3"].minimum_size == 15
    assert placeholders["Corpus V4"].minimum_size >= 100
    assert placeholders["Corpus V4"].distribution["boundary"] >= 10


def test_stage4_corpus_v2_materialized_content_covers_required_distribution() -> None:
    cases = build_corpus_v2_cases()
    placeholders = {p.corpus_id: p for p in build_stage4_corpus_placeholders()}
    v2_placeholder = placeholders["Corpus V2"]

    assert len(cases) >= v2_placeholder.minimum_size

    categories = {case.category for case in cases}
    assert "corpus_v2_direct" in categories
    assert "corpus_v2_workflow" in categories
    assert "corpus_v2_workflow_escalation" in categories
    assert "corpus_v2_task_assistant" in categories

    by_target: dict[str, int] = {}
    for case in cases:
        by_target[case.routing_target] = by_target.get(case.routing_target, 0) + 1
    for target, expected_count in v2_placeholder.distribution.items():
        assert by_target.get(target, 0) >= expected_count, (
            f"Corpus V2 routing_target={target}: expected >= {expected_count}, got {by_target.get(target, 0)}"
        )

    escalation_cases = [c for c in cases if c.category == "corpus_v2_workflow_escalation"]
    assert len(escalation_cases) >= 5, f"Expected >=5 escalation cases, got {len(escalation_cases)}"


def test_stage4_corpus_v2_escalation_cases_use_approved_triggers_only() -> None:
    cases = build_corpus_v2_cases()
    escalation_cases = [c for c in cases if c.category == "corpus_v2_workflow_escalation"]

    approved_triggers = {
        "explicit_planning_request",
        "structural_topic_turns",
        "frustration_blockage",
    }

    for case in escalation_cases:
        snapshot = case.snapshot
        assert snapshot is not None, f"Escalation case {case.case_id} must have a snapshot"
        from app.aurora.decision_fns.escalation import detect_escalation

        verdict = detect_escalation(snapshot)
        assert verdict.should_escalate is True, (
            f"Escalation case {case.case_id} should trigger escalation but got: {verdict.reason}"
        )
        assert verdict.trigger in approved_triggers, (
            f"Escalation case {case.case_id} trigger={verdict.trigger} not in approved set"
        )


def test_stage4_tier_tagged_events_support_dashboard_and_test_consumers() -> None:
    engine = AuroraEngine()
    policy = engine.load_policy("v1.0")

    def _runner(case):
        start = perf_counter()
        decision = engine.safe_route(
            AuroraDecisionContext(
                snapshot=case.snapshot,
                trigger_point=case.trigger_point,
                current_node=case.current_node,
                candidate_node=case.candidate_node,
                policy_version=policy,
                mode="shadow",
            )
        )
        return {
            "tier": "inline",
            "latency_ms": (perf_counter() - start) * 1000.0,
            "decision_type": decision.decision_type,
            "metadata": {
                "impact_class": decision.impact_class.value,
                "basis": decision.decision_basis.value,
            },
        }

    events = run_corpus_v1_with_runner(_runner)
    summary = summarize_tier_tagged_events(events)

    assert summary["total"] == 20
    assert summary["by_tier"]["inline"] == 20
    assert summary["p95_latency_ms"] >= 0.0
    assert {"case_id", "tier", "routing_target", "status", "latency_ms", "decision_type"} <= set(events[0].__dict__)


def test_stage4_p1_guardrail_report_runs_in_report_only_mode() -> None:
    report = build_p1_guardrail_report(repo_root=Path(__file__).resolve().parents[3])

    assert report.mode == "hard-fail"
    assert report.checked_files
    assert any(path.endswith("backend/app/aurora/engine.py") for path in report.checked_files)
    assert report.has_findings is False, report.render()


def test_stage4_p1_guardrail_no_longer_flags_aurora_tasks() -> None:
    report = build_p1_guardrail_report(repo_root=Path(__file__).resolve().parents[3])

    assert all(violation.file_path != "backend/app/aurora/tasks.py" for violation in report.violations)
