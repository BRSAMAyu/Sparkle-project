from app.core.business_metrics import HUMAN_EVAL_REPEATED_FAILURE_TAGS_TOTAL, snapshot_metric
from app.services.human_eval_review_service import HumanEvalReviewService


def _metric_value(snapshot: dict[str, float], needle: str) -> float:
    for label, value in snapshot.items():
        if needle in label:
            return value
    return 0.0


def test_human_eval_review_service_counts_repeated_failures() -> None:
    service = HumanEvalReviewService()

    summary = service.summarize_review_run(
        {
            "scenario_id": "thermo-alpha-1",
            "date_run": "2026-04-04",
            "evaluator": "founder",
            "overall_verdict": "needs_iteration",
            "segments": [
                {
                    "segment_id": "s1",
                    "visible_adaptation": "Sparkle explicitly lowered the workload.",
                    "issue_tags": ["timing_wrong", "grounding_weak"],
                },
                {
                    "segment_id": "s2",
                    "issue_tags": ["timing_wrong", "tone_drift"],
                },
            ],
        }
    )

    assert summary["segments_reviewed"] == 2
    assert summary["issue_tag_counts"]["timing_wrong"] == 2
    assert summary["repeated_failures"] == [{"tag": "timing_wrong", "count": 2}]
    assert summary["needs_product_fix"] is True
    assert summary["strongest_positive_signal"] == "Sparkle explicitly lowered the workload."


def test_human_eval_review_service_rejects_unknown_tags() -> None:
    service = HumanEvalReviewService()

    try:
        service.normalize_issue_tags(["unknown_tag"])
    except ValueError as exc:
        assert "Unsupported human-eval issue tag" in str(exc)
    else:
        raise AssertionError("Expected ValueError for unsupported issue tag")


def test_human_eval_review_service_builds_ops_loop_and_release_blockers() -> None:
    service = HumanEvalReviewService()
    before = snapshot_metric(HUMAN_EVAL_REPEATED_FAILURE_TAGS_TOTAL)

    report = service.build_operations_report(
        {
            "scenario_id": "thermo-alpha-2",
            "date_run": "2026-04-05",
            "evaluator": "founder",
            "segments": [
                {"segment_id": "s1", "issue_tags": ["grounding_weak", "diagnosis_wrong"]},
                {"segment_id": "s2", "issue_tags": ["grounding_weak"]},
                {"segment_id": "s3", "issue_tags": ["grounding_weak"]},
            ],
        }
    )

    assert report["operating_recommendation"] == "block_release_and_open_backlog_items"
    assert report["release_blockers"][0]["tag"] == "grounding_weak"
    assert report["backlog_candidates"][0]["priority"] == "high"

    after = snapshot_metric(HUMAN_EVAL_REPEATED_FAILURE_TAGS_TOTAL)
    grounding_delta = _metric_value(after, "tag=grounding_weak") - _metric_value(before, "tag=grounding_weak")
    assert grounding_delta == 1.0
