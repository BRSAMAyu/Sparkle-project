"""Telemetry / business-truth boundary policy (V3-FIX-11).

Single source of truth for the rules that keep client telemetry out of
business-truth surfaces. Three infiltration chains were code-confirmed by the
D-01 dual review (receipts in ``v3-output/D-01/``):

- T1: telemetry POST -> state_estimator -> user_state_snapshots -> nightly
  review / personalization. The estimator's event-volume term saturated
  cognitive_load at ~50 events/24h, so a misbehaving client could inflate a
  user's cognitive-load estimate with semantically empty noise.
- T2: cognitive_stream_worker -> CognitiveFragment/BehaviorPattern ->
  adaptive_replanner. Seeded guest-cohort patterns sit inside the replanner's
  0.7 confidence gate.
- T3: telemetry/seed sentiment -> cognitive_fragments.sentiment ->
  state_aggregator emotion_hint. The worker's sensitive-sentiment intercept
  set did not cover the aggregator's emotional-block trigger set, so
  ``frustrated``/``overwhelmed`` passed through as plaintext sentiment.

Everything in this module is policy, not mechanism: consumers import the
constants so the sets can never drift apart again. The contract guard
``backend/tests/contract/test_telemetry_boundary_contract.py`` enforces that
truth-path modules referencing telemetry-derived tables carry an explicit
waiver marker (``TELEMETRY_DERIVED_READ_WAIVER``).
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# T3: sentiment interception vs emotional-block triggers
# ---------------------------------------------------------------------------

#: Sentiments that, when dominant, trip ``emotional_block_detected`` in the
#: state aggregator's emotion_hint (UserStateV1). Owned HERE so the producer
#: side (cognitive_stream_worker intercept set) and the consumer side
#: (state_aggregator) cannot drift apart.
EMOTIONAL_BLOCK_SENTIMENTS: frozenset[str] = frozenset(
    {
        "anxious",
        "frustrated",
        "overwhelmed",
    }
)

#: Sentiments the telemetry pipeline must never persist in the plaintext
#: ``cognitive_fragments.sentiment`` column. Anything a dominant-detection
#: consumer could turn into a decision trigger (see EMOTIONAL_BLOCK_SENTIMENTS)
#: is intercepted into the encrypted sensitive-tags channel instead; the
#: historical anxious/depressed/burnout trio stays intercepted as well.
#: Invariant (guard-tested): EMOTIONAL_BLOCK_SENTIMENTS is a subset of this.
TELEMETRY_SENSITIVE_SENTIMENTS: frozenset[str] = (
    frozenset({"anxious", "depressed", "burnout"}) | EMOTIONAL_BLOCK_SENTIMENTS
)

#: Fragment source types whose ``sentiment`` column is client-influenced
#: (implicit behavior capture: telemetry stream worker or seed writes).
#: ``capsule`` (user-authored flash notes) and ``interceptor`` are not
#: telemetry-derived and may still contribute sentiment.
TELEMETRY_DERIVED_FRAGMENT_SOURCE_TYPES: frozenset[str] = frozenset({"behavior"})

# ---------------------------------------------------------------------------
# T1: state estimator bounds
# ---------------------------------------------------------------------------

#: Hard ceiling on the telemetry-derived portion of ``cognitive_load``.
#: Both terms of the estimator's load formula (wrong-event count and raw
#: event volume) are computed from client telemetry, so the combined
#: contribution is capped: semantically empty noise (heartbeat / screen_view
#: floods, ~50 events/24h used to saturate the load to 1.0) can no longer
#: push interruptibility toward 0 on its own.
TELEMETRY_DERIVED_LOAD_CAP: float = 0.3

#: Hard ceiling on ``strain_index`` (V3-FIX-14). Like cognitive_load, strain
#: is computed exclusively from client-asserted rows (wrong-event counts), so
#: a forged quiz_wrong flood can saturate it to 1.0. The estimator is the
#: only writer of the column, so this producer-side cap bounds every reader
#: (plan_context prompt injection, events API readback, chat prior_outputs,
#: evidence health). Direction preserved, only the ceiling is bounded.
TELEMETRY_DERIVED_STRAIN_CAP: float = 0.3

#: Minimum wall-clock interval between telemetry-triggered estimator
#: recomputes for the same user. Telemetry paths (events ingest endpoint,
#: cognitive stream worker) call ``update_state`` on every request/event;
#: within this window the estimator returns the latest existing snapshot
#: instead of re-arming from the request payload (V3-FIX-11 T1: a single
#: telemetry request must not synchronously refresh user state).
STATE_ESTIMATOR_MIN_INTERVAL_SECONDS: int = 300

# ---------------------------------------------------------------------------
# T2: seed cohort exclusion (registration_source, per V3-FIX-01 precedent)
# ---------------------------------------------------------------------------

#: Accounts whose data is demo/seed material and must never feed
#: decision surfaces. Same registration_source口径 as the global leaderboard
#: fix (V3-FIX-01).
EXCLUDED_COHORT_REGISTRATION_SOURCES: tuple[str, ...] = ("guest", "seed")

# ---------------------------------------------------------------------------
# Contract-guard support (see tests/contract/test_telemetry_boundary_contract.py)
# ---------------------------------------------------------------------------

#: Marker a business-truth module must carry next to (and in the header of)
#: any reference to a telemetry-derived table. The guard scans truth-path
#: modules for telemetry-derived identifiers; unmarked references fail.
TELEMETRY_DERIVED_READ_WAIVER = "TELEMETRY_DERIVED_READ_WAIVER"
