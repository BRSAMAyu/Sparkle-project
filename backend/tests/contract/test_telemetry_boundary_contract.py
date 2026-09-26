"""Telemetry / business-truth boundary contract guard (V3-FIX-11).

Upgrades the D-01 seven-module direct-reference scan to cover SECOND HOPS
(D-01 R2 finding F12: "the scan only looks at tracking_events/TrackingEvent
direct references; derived-table second hops are all invisible — T1
(user_state_snapshots) and T2/T3 (cognitive_fragments/behavior_patterns) all
walk second hops and the guard stays green for them").

Two tiers:

- Tier 1 (direct, zero tolerance): business-truth modules must never
  reference TrackingEvent / tracking_events. Same rule as the D-01 guard,
  but directory-level for state_aggregator/ and services/evidence/ so new
  files in those packages are covered automatically (F12 recommendation).
- Tier 2 (second hop, waiver-gated): truth modules and decision-surface
  consumers referencing telemetry-derived tables (cognitive_fragments,
  user_state_snapshots, behavior_patterns) must carry an explicit
  TELEMETRY_DERIVED_READ_WAIVER marker in the file, and must be listed in
  WAIVED_MODULES below. A new unwaivered reference fails with an actionable
  message; a waiver without a live reference fails too (dead waivers drop).

This is deliberately a source scan (static, cheap, CI-able): dynamic/runtime
assertions can prove one bounded read is bounded, but cannot see the next
infiltration someone adds. The behavioral bounds themselves are pinned by the
per-chain tests in tests/unit/ and tests/services/ (see test files referencing
V3-FIX-11).
"""

from __future__ import annotations

import io
import re
import tokenize
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]

from app.core.telemetry_boundary import (  # noqa: E402
    TELEMETRY_DERIVED_READ_WAIVER as WAIVER_MARKER,
)

# ---------------------------------------------------------------------------
# Scan targets
# ---------------------------------------------------------------------------

# Business-truth modules (D-01 seven, upgraded to directory level per F12) —
# authors of authoritative user state / evidence / decision context.
TRUTH_PATH_DIRS = (
    "app/state_aggregator",
    "app/services/evidence",
)
TRUTH_PATH_FILES = (
    "app/core/context_pack.py",
    "app/services/galaxy/stats_service.py",
    # Decision-surface consumers of telemetry-derived tables (V3-FIX-11
    # chains): nightly review reads user_state_snapshots (T1), the adaptive
    # replanner reads behavior_patterns (T2), runtime context reads
    # user_state_snapshots (T1).
    "app/services/nightly_review_service.py",
    "app/orchestration/adaptive_replanner.py",
    "app/services/personalization/runtime_context_service.py",
    # V3-FIX-14: plan_context.build_enriched reads the latest per-user
    # user_state_snapshots row (strain_index consumer) and per-user
    # behavior_patterns for the user's own plan prompt — decision-adjacent
    # surface named in V3-FIX-11 REVIEW_RECEIPT §5; incorporated into the
    # scan set so its read stays waiver-gated like the consumers above.
    "app/core/plan_context.py",
)

DIRECT_TELEMETRY_IDENTIFIERS = ("TrackingEvent", "tracking_events")

TELEMETRY_DERIVED_IDENTIFIERS = (
    "CognitiveFragment",
    "cognitive_fragments",
    "UserStateSnapshot",
    "user_state_snapshots",
    "BehaviorPattern",
    "behavior_patterns",
)

# Files allowed to reference telemetry-derived tables, with the bounded-read
# reason. Every entry must also carry the WAIVER_MARKER comment in its
# source. Anything not listed here fails tier 2.
WAIVED_MODULES: dict[str, str] = {
    "app/state_aggregator/service.py": (
        "V3-FIX-11 T3: emotion_hint reads cognitive_fragments.sentiment with "
        "source_type NOT IN telemetry-derived fragment sources; producer-side "
        "intercept set covers the emotional_block trigger set"
    ),
    "app/services/nightly_review_service.py": (
        "V3-FIX-11 T1: reads latest user_state_snapshots; snapshots are "
        "debounce-rate-limited and their telemetry-derived cognitive_load is "
        "capped by TELEMETRY_DERIVED_LOAD_CAP"
    ),
    "app/services/personalization/runtime_context_service.py": (
        "V3-FIX-11 T1: reads focus_mode/snapshot_at only from "
        "user_state_snapshots, whose writes are debounce-gated and whose "
        "telemetry-derived cognitive_load is capped (same bound as nightly review)"
    ),
    "app/orchestration/adaptive_replanner.py": (
        "V3-FIX-11 T2: reads behavior_patterns with registration_source NOT "
        "IN guest/seed cohort filter at the 0.7 confidence gate"
    ),
    "app/core/plan_context.py": (
        "V3-FIX-14: build_enriched second-hop reads for the user's own plan "
        "prompt, both strictly per-user (user_id filter): latest "
        "user_state_snapshots row under a 24h recency filter, whose writes "
        "are debounce-gated and whose telemetry-derived cognitive_load/"
        "strain_index are capped by TELEMETRY_DERIVED_*_CAP; behavior_patterns "
        "read is per-user with an is_archived gate and confidence ordering — "
        "no cross-user truth path (V3-FIX-11 REVIEW_RECEIPT §5 per-user audit)"
    ),
}


def _iter_py_files() -> list[Path]:
    files: list[Path] = []
    for rel_dir in TRUTH_PATH_DIRS:
        directory = BACKEND_DIR / rel_dir
        assert directory.is_dir(), f"truth-path directory moved: {rel_dir}"
        files.extend(sorted(directory.glob("*.py")))
    for rel_file in TRUTH_PATH_FILES:
        path = BACKEND_DIR / rel_file
        assert path.exists(), f"truth-path module moved: {rel_file}"
        files.append(path)
    return files


def _rel(path: Path) -> str:
    return str(path.relative_to(BACKEND_DIR))


def _strip_comments(source: str) -> str:
    """Drop COMMENT tokens but keep STRING literals.

    Comments are documentation — boundary waivers must be allowed to *name*
    the tables they bound. String literals stay in scope because they can
    carry dynamic SQL (D-01 R2 F12 bypass class), so ``text("select ... from
    tracking_events")`` must remain detectable.
    """
    kept: list[str] = []
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.type == tokenize.COMMENT:
            continue
        kept.append(token.string if token.type != tokenize.NEWLINE else "\n")
    return " ".join(kept)


def _matching_identifiers(source: str, identifiers: tuple[str, ...]) -> set[str]:
    found: set[str] = set()
    for identifier in identifiers:
        # Word-boundary match: '_cognitive_fragments' or
        # 'include_behavior_patterns' must NOT count as a reference.
        if re.search(rf"\b{re.escape(identifier)}\b", source):
            found.add(identifier)
    return found


def test_truth_path_modules_never_read_client_telemetry_directly():
    """Tier 1: zero tolerance for direct tracking_events references
    (code and string literals; comments are exempt as documentation)."""
    offenders: list[str] = []
    for path in _iter_py_files():
        source = path.read_text(encoding="utf-8")
        found = _matching_identifiers(_strip_comments(source), DIRECT_TELEMETRY_IDENTIFIERS)
        if found:
            offenders.append(f"{_rel(path)}: {sorted(found)}")
    assert not offenders, (
        "business-truth modules must not read client telemetry directly " f"(D-01 boundary): {offenders}"
    )


def test_truth_path_modules_reference_telemetry_derived_tables_only_with_waiver():
    """Tier 2: second-hop references need an explicit, listed waiver."""
    unwaived: list[str] = []
    for path in _iter_py_files():
        source = path.read_text(encoding="utf-8")
        found = _matching_identifiers(_strip_comments(source), TELEMETRY_DERIVED_IDENTIFIERS)
        if not found:
            continue
        rel = _rel(path)
        if rel not in WAIVED_MODULES:
            unwaived.append(
                f"{rel}: references {sorted(found)} without a waiver — add the "
                f"read bound + '{WAIVER_MARKER}' marker and register it in "
                "WAIVED_MODULES with review"
            )
            continue
        if WAIVER_MARKER not in source:
            unwaived.append(
                f"{rel}: listed in WAIVED_MODULES but the source no longer "
                f"carries the '{WAIVER_MARKER}' marker (waiver drifted)"
            )
    assert not unwaived, (
        "telemetry-derived tables (second hop) leaked into truth-path "
        f"modules without a bounded-read waiver: {unwaived}"
    )


def test_waived_modules_all_exist_and_still_reference_their_tables():
    """Dead waivers fail: a waived module that no longer references any
    telemetry-derived table must be removed from WAIVED_MODULES."""
    stale: list[str] = []
    for rel, reason in WAIVED_MODULES.items():
        path = BACKEND_DIR / rel
        if not path.exists():
            stale.append(f"{rel}: file gone (waiver: {reason})")
            continue
        source = path.read_text(encoding="utf-8")
        if not _matching_identifiers(_strip_comments(source), TELEMETRY_DERIVED_IDENTIFIERS):
            stale.append(
                f"{rel}: waiver present but no telemetry-derived reference " "remains — remove the waiver entry"
            )
    assert not stale, f"stale waivers: {stale}"


def test_waiver_reasons_document_a_bound():
    """Every waiver must name a concrete bound (filter/cap/debounce/gate),
    not a bare justification. Keeps waivers honest as they evolve."""
    bound_keywords = (
        "filter",
        "cap",
        "debounce",
        "gate",
        "NOT IN",
    )
    weak: list[str] = []
    for rel, reason in WAIVED_MODULES.items():
        if not any(keyword in reason for keyword in bound_keywords):
            weak.append(f"{rel}: waiver reason lacks a named bound — {reason}")
    assert not weak, weak
