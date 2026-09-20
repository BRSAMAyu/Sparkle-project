"""M-09 grading — the three paired-baseline metrics plus per-case verdicts.

Grading corpus is the RENDERED PROMPT (``format_user_context(pack.
to_prompt_context())``) — the exact text the LLM would see. This is the
adversarial stance: if forbidden content reaches the prompt face at all, it
counts, regardless of whether a model would choose to mention it.

Metrics (frozen definitions; PERSONALIZATION_EVAL.md / M-09 card):

- invalid use      : a ``must_not_use`` marker present in the with-memory
                     rendered prompt. Gate requires the TOTAL to be 0.
- overpersonalization : on ``overpersonalization_watch`` probes (phatic /
                     off-topic), any ``personal_watch_markers`` surfacing.
                     Rate over watched probes must be <= 5%.
- valid-use precision : over every surfaced personal item across the suite,
                     valid / (valid + invalid), where a surfaced item is a
                     marker occurrence from (must_use ∪ may_use ∪ must_not_use)
                     found in a case's rendered prompt; must_use/may_use hits
                     are valid, must_not_use hits are invalid. Target >= 95%.
- uplift           : paired no-history design. A case with non-empty must_use
                     is uplift-positive iff every must_use marker is present
                     with-memory AND absent in the no-history arm (the same
                     probe on a user with no memory timeline). Reported as a
                     rate and as the pp difference of personalized-answer
                     rates (with-memory must_use-hit rate − no-history rate).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .harness import CaseOutcome


@dataclass
class CaseVerdict:
    case_id: str
    persona_id: str
    dimension: str
    passed: bool
    overpersonalization_watch: bool = False
    must_use_missing: list[str] = field(default_factory=list)
    invalid_use_markers: list[str] = field(default_factory=list)
    overpersonalized: bool = False
    overpersonalization_markers: list[str] = field(default_factory=list)
    uplift_positive: bool | None = None
    surfaced_valid_items: int = 0
    surfaced_invalid_items: int = 0
    surfaced_watched_items: int = 0
    error: str | None = None
    detail: dict[str, Any] = field(default_factory=dict)

    def to_row(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "persona_id": self.persona_id,
            "dimension": self.dimension,
            "passed": self.passed,
            "overpersonalization_watch": self.overpersonalization_watch,
            "must_use_missing": self.must_use_missing,
            "invalid_use_markers": self.invalid_use_markers,
            "overpersonalized": self.overpersonalized,
            "overpersonalization_markers": self.overpersonalization_markers,
            "uplift_positive": self.uplift_positive,
            "surfaced_valid_items": self.surfaced_valid_items,
            "surfaced_invalid_items": self.surfaced_invalid_items,
            "surfaced_watched_items": self.surfaced_watched_items,
            "error": self.error,
        }


def _found(corpus: str, marker: str) -> bool:
    return marker in corpus


def grade_case(outcome: CaseOutcome) -> CaseVerdict:
    case = outcome.case
    expectations = case.expectations
    verdict = CaseVerdict(
        case_id=case.case_id,
        persona_id=case.persona_id,
        dimension=case.dimension,
        passed=True,
        overpersonalization_watch=expectations.overpersonalization_watch,
    )
    if outcome.error is not None:
        verdict.passed = False
        verdict.error = outcome.error
        return verdict
    if outcome.with_memory is None or outcome.no_history is None:
        verdict.passed = False
        verdict.error = "missing probe arm"
        return verdict

    corpus = outcome.with_memory.corpus()
    baseline_corpus = outcome.no_history.corpus()

    # 1. invalid use (hard zero target)
    verdict.invalid_use_markers = [m for m in expectations.must_not_use if _found(corpus, m)]

    # 2. positive expectation (dimension-specific must_use)
    verdict.must_use_missing = [m for m in expectations.must_use if not _found(corpus, m)]

    # 3. overpersonalization (watched phatic / off-topic probes)
    if expectations.overpersonalization_watch:
        verdict.overpersonalization_markers = [m for m in expectations.personal_watch_markers if _found(corpus, m)]
        verdict.overpersonalized = bool(verdict.overpersonalization_markers)
        verdict.surfaced_watched_items = len(verdict.overpersonalization_markers)

    # 4. surfaced item accounting (precision numerator/denominator)
    verdict.surfaced_valid_items = sum(1 for m in [*expectations.must_use, *expectations.may_use] if _found(corpus, m))
    verdict.surfaced_invalid_items = len(verdict.invalid_use_markers)

    # 5. paired uplift
    if expectations.must_use:
        with_hits = sum(1 for m in expectations.must_use if _found(corpus, m))
        baseline_hits = sum(1 for m in expectations.must_use if _found(baseline_corpus, m))
        verdict.uplift_positive = with_hits == len(expectations.must_use) and baseline_hits == 0
        verdict.detail["with_memory_must_use_hits"] = with_hits
        verdict.detail["no_history_must_use_hits"] = baseline_hits

    verdict.passed = not verdict.invalid_use_markers and not verdict.must_use_missing and not verdict.overpersonalized
    verdict.detail["face_episodic"] = outcome.with_memory.face_episodic_summaries
    verdict.detail["face_preferences"] = dict(outcome.with_memory.face_preferences)
    verdict.detail["face_goals"] = outcome.with_memory.face_goal_titles
    verdict.detail["selfcheck_internal_only"] = outcome.with_memory.selfcheck_internal_only
    verdict.detail["prefilter_rejections"] = outcome.with_memory.prefilter_rejections
    return verdict


def aggregate(verdicts: list[CaseVerdict]) -> dict[str, Any]:
    """Suite-level metrics. Failures are never averaged away — every failing
    case id is listed explicitly."""
    watched = [v for v in verdicts if v.overpersonalization_watch]
    return _aggregate_with_watch(verdicts, watched)


def _aggregate_with_watch(verdicts: list[CaseVerdict], watched: list[CaseVerdict]) -> dict[str, Any]:
    invalid_total = sum(len(v.invalid_use_markers) for v in verdicts)
    overpersonalization_events = sum(1 for v in watched if v.overpersonalized)
    watched_count = len(watched)
    overpersonalization_rate = overpersonalization_events / watched_count if watched_count else 0.0
    valid_items = sum(v.surfaced_valid_items for v in verdicts)
    invalid_items = sum(v.surfaced_invalid_items for v in verdicts)
    surfaced_total = valid_items + invalid_items
    valid_use_precision = (valid_items / surfaced_total) if surfaced_total else 1.0

    uplift_eligible = [v for v in verdicts if v.uplift_positive is not None]
    uplift_positives = sum(1 for v in uplift_eligible if v.uplift_positive)
    uplift_rate = (uplift_positives / len(uplift_eligible)) if uplift_eligible else 0.0
    with_memory_personalized = sum(1 for v in uplift_eligible if v.detail.get("with_memory_must_use_hits", 0) > 0)
    no_history_personalized = sum(1 for v in uplift_eligible if v.detail.get("no_history_must_use_hits", 0) > 0)
    with_rate = (with_memory_personalized / len(uplift_eligible)) if uplift_eligible else 0.0
    no_rate = (no_history_personalized / len(uplift_eligible)) if uplift_eligible else 0.0

    failed = [v for v in verdicts if not v.passed]
    return {
        "case_count": len(verdicts),
        "failed_case_ids": [v.case_id for v in failed],
        "failure_breakdown": {
            "invalid_use": [v.case_id for v in verdicts if v.invalid_use_markers],
            "must_use_missing": [v.case_id for v in verdicts if v.must_use_missing],
            "overpersonalization": [v.case_id for v in verdicts if v.overpersonalized],
            "errors": [v.case_id for v in verdicts if v.error],
        },
        "invalid_use_total": invalid_total,
        "overpersonalization": {
            "watched_probes": watched_count,
            "events": overpersonalization_events,
            "rate": round(overpersonalization_rate, 4),
        },
        "valid_use_precision": {
            "valid_items": valid_items,
            "invalid_items": invalid_items,
            "precision": round(valid_use_precision, 4),
        },
        "uplift": {
            "eligible_cases": len(uplift_eligible),
            "positives": uplift_positives,
            "rate": round(uplift_rate, 4),
            "with_memory_personalized_rate": round(with_rate, 4),
            "no_history_personalized_rate": round(no_rate, 4),
            "uplift_pp": round((with_rate - no_rate) * 100, 2),
        },
    }
