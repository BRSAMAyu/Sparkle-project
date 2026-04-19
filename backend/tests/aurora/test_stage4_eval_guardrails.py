from __future__ import annotations

import warnings
from pathlib import Path
from time import perf_counter

from app.aurora.engine import AuroraDecisionContext, AuroraEngine

from .stage4_eval_support import (
    build_corpus_v1_cases,
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
    assert placeholders["Corpus V3"].minimum_size == 15
    assert placeholders["Corpus V4"].minimum_size >= 100
    assert placeholders["Corpus V4"].distribution["boundary"] >= 10


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

    assert report.mode == "report-only"
    assert report.checked_files
    assert any(path.endswith("backend/app/aurora/engine.py") for path in report.checked_files)
    if report.has_findings:
        warnings.warn(report.render(), stacklevel=2)
