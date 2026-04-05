from __future__ import annotations

from collections import Counter
from typing import Any


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
