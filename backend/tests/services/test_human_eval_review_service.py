from app.services.human_eval_review_service import HumanEvalReviewService


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
