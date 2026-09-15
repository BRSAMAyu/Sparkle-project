from __future__ import annotations

from collections import Counter
from typing import Any

from app.core.business_metrics import HUMAN_EVAL_REPEATED_FAILURE_TAGS_TOTAL

ALLOWED_HUMAN_EVAL_ISSUE_TAGS = (
    "diagnosis_wrong",
    "timing_wrong",
    "adaptation_invisible",
    "grounding_weak",
    "continuity_weak",
    "tone_drift",
)


class HumanEvalReviewService:
    """Normalize and summarize transcript-driven human evaluation runs."""

    def normalize_issue_tags(self, issue_tags: list[str] | None) -> list[str]:
        normalized: list[str] = []
        for raw_tag in issue_tags or []:
            candidate = "_".join(str(raw_tag or "").strip().lower().replace("-", "_").split())
            if not candidate:
                continue
            if candidate not in ALLOWED_HUMAN_EVAL_ISSUE_TAGS:
                raise ValueError(f"Unsupported human-eval issue tag: {candidate}")
            if candidate not in normalized:
                normalized.append(candidate)
        return normalized

    def summarize_review_run(self, payload: dict[str, Any]) -> dict[str, Any]:
        segments = [
            self._normalize_segment(segment, index=index)
            for index, segment in enumerate(payload.get("segments") or [], start=1)
            if isinstance(segment, dict)
        ]
        tag_counter: Counter[str] = Counter()
        for segment in segments:
            tag_counter.update(segment["issue_tags"])

        repeated_failures = [
            {"tag": tag, "count": count}
            for tag, count in sorted(tag_counter.items(), key=lambda item: (-item[1], item[0]))
            if count >= 2
        ]
        needs_product_fix = bool(repeated_failures)
        strongest_positive_signal = next(
            (
                segment["visible_adaptation"]
                for segment in segments
                if segment["visible_adaptation"]
            ),
            "",
        )

        return {
            "scenario_id": str(payload.get("scenario_id") or "").strip(),
            "date_run": str(payload.get("date_run") or "").strip(),
            "evaluator": str(payload.get("evaluator") or "").strip(),
            "overall_verdict": str(payload.get("overall_verdict") or "").strip() or "pending_review",
            "segments_reviewed": len(segments),
            "issue_tag_counts": dict(sorted(tag_counter.items())),
            "repeated_failures": repeated_failures,
            "needs_product_fix": needs_product_fix,
            "strongest_positive_signal": strongest_positive_signal,
            "must_fix_before_next_pilot": [
                item["tag"] for item in repeated_failures
            ],
            "segments": segments,
        }

    def render_markdown_summary(self, summary: dict[str, Any]) -> str:
        lines = [
            "# Sparkle Human Evaluation Summary",
            "",
            f"- Scenario: {summary.get('scenario_id') or 'unknown'}",
            f"- Date: {summary.get('date_run') or 'unknown'}",
            f"- Evaluator: {summary.get('evaluator') or 'unknown'}",
            f"- Overall verdict: {summary.get('overall_verdict') or 'pending_review'}",
            f"- Segments reviewed: {summary.get('segments_reviewed') or 0}",
            f"- Needs product fix: {'yes' if summary.get('needs_product_fix') else 'no'}",
        ]
        repeated = summary.get("repeated_failures") or []
        if repeated:
            lines.extend(["", "## Repeated Failures"])
            for item in repeated:
                lines.append(f"- {item['tag']}: {item['count']}")
        strongest_positive_signal = str(summary.get("strongest_positive_signal") or "").strip()
        if strongest_positive_signal:
            lines.extend(["", "## Strongest Positive Signal", f"- {strongest_positive_signal}"])
        return "\n".join(lines) + "\n"

    def build_operations_report(
        self,
        payload: dict[str, Any],
        *,
        repeated_failure_threshold: int = 2,
        release_blocker_threshold: int = 3,
    ) -> dict[str, Any]:
        summary = self.summarize_review_run(payload)
        repeated_failures = [
            dict(item)
            for item in (summary.get("repeated_failures") or [])
            if int(item.get("count") or 0) >= repeated_failure_threshold
        ]
        backlog_candidates = [
            {
                "tag": item["tag"],
                "priority": "high" if item["tag"] in {"diagnosis_wrong", "grounding_weak"} else "medium",
                "why_now": f"Repeated human-eval failure detected {item['count']} times.",
            }
            for item in repeated_failures
        ]
        release_blockers = [
            {
                "tag": item["tag"],
                "reason": "Repeated serious failure should block the next pilot until resolved.",
            }
            for item in repeated_failures
            if int(item.get("count") or 0) >= release_blocker_threshold
            or item["tag"] in {"diagnosis_wrong", "grounding_weak"}
        ]
        repeated_failure_clusters = [
            {
                "cluster_id": f"{summary.get('scenario_id') or 'scenario'}:{item['tag']}",
                "tag": item["tag"],
                "count": item["count"],
                "segment_ids": [
                    segment["segment_id"]
                    for segment in (summary.get("segments") or [])
                    if item["tag"] in (segment.get("issue_tags") or [])
                ],
            }
            for item in repeated_failures
        ]
        operating_recommendation = "continue_review"
        if release_blockers:
            operating_recommendation = "block_release_and_open_backlog_items"
        elif backlog_candidates:
            operating_recommendation = "open_backlog_items_before_next_iteration"

        for item in repeated_failures:
            HUMAN_EVAL_REPEATED_FAILURE_TAGS_TOTAL.labels(tag=item["tag"]).inc()

        return {
            **summary,
            "repeated_failure_threshold": repeated_failure_threshold,
            "release_blocker_threshold": release_blocker_threshold,
            "repeated_failure_clusters": repeated_failure_clusters,
            "backlog_candidates": backlog_candidates,
            "release_blockers": release_blockers,
            "operating_recommendation": operating_recommendation,
        }

    def render_operations_markdown(self, report: dict[str, Any]) -> str:
        lines = [
            "# Sparkle Human Eval Ops Loop",
            "",
            f"- Scenario: {report.get('scenario_id') or 'unknown'}",
            f"- Operating recommendation: {report.get('operating_recommendation') or 'continue_review'}",
            f"- Release blockers: {len(report.get('release_blockers') or [])}",
            f"- Backlog candidates: {len(report.get('backlog_candidates') or [])}",
        ]
        blockers = report.get("release_blockers") or []
        if blockers:
            lines.extend(["", "## Release Blockers"])
            for item in blockers:
                lines.append(f"- {item['tag']}: {item['reason']}")
        backlog = report.get("backlog_candidates") or []
        if backlog:
            lines.extend(["", "## Backlog Candidates"])
            for item in backlog:
                lines.append(f"- [{item['priority']}] {item['tag']}: {item['why_now']}")
        clusters = report.get("repeated_failure_clusters") or []
        if clusters:
            lines.extend(["", "## Failure Clusters"])
            for item in clusters:
                lines.append(f"- {item['tag']}: {item['count']} ({', '.join(item['segment_ids'])})")
        return "\n".join(lines) + "\n"

    def _normalize_segment(self, segment: dict[str, Any], *, index: int) -> dict[str, Any]:
        return {
            "segment_id": str(segment.get("segment_id") or f"segment-{index}").strip(),
            "turn_or_segment": str(segment.get("turn_or_segment") or "").strip(),
            "sparkle_hypothesis": str(segment.get("sparkle_hypothesis") or "").strip(),
            "real_problem": str(segment.get("real_problem") or "").strip(),
            "evidence_used": [str(item).strip() for item in (segment.get("evidence_used") or []) if str(item).strip()],
            "visible_adaptation": str(segment.get("visible_adaptation") or "").strip(),
            "timing_assessment": str(segment.get("timing_assessment") or "").strip(),
            "trust_signal": str(segment.get("trust_signal") or "").strip(),
            "should_have_done_differently": str(segment.get("should_have_done_differently") or "").strip(),
            "issue_tags": self.normalize_issue_tags(segment.get("issue_tags") or []),
        }
