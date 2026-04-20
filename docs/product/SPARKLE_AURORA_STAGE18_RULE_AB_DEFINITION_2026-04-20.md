# SPARKLE Aurora Stage 18 Rule AB Definition (2026-04-20)

> Rule AB: State Aggregator is an L1 derived layer and must remain read-only; push decisions may only use user-explicit goals and commitments. Every Aggregator output must be traceable, every push must carry evidence, each user has a hard cap of 2 pushes per day, and local quiet hours 22:00-08:00 are hard-locked.

## 1. Mandatory Constraints

1. Every Aggregator output field carries `computed_at` and `source_snapshot_ids`.
2. Aggregator may not write to any L0/L1 source system.
3. Every push decision carries an `evidence_token` pointing to explicit user evidence.
4. Push has a per-user daily hard cap of `2`.
5. Quiet hours `22:00-08:00` local time are hard-locked.

## 2. Forbidden Scenarios

1. Caching activity freshness longer than 5 minutes without an explicit freshness marker.
2. Triggering push from emotion, style profile, or inferred learning-style features.
3. Triggering push from friends', classmates', or community activity.
4. Re-triggering the same commitment within 7 days after a user dismiss.
5. Rendering inferred profile facts verbatim inside push copy.
6. Writing Aggregator fields back into inferred memory or profile tables.
7. Replacing the daily cap with an hourly-only cap.
8. Omitting `evidence_token` from any Aurora push decision record.

## 3. CI Guard

`scripts/check_rule_ab_aggregator_integrity.py` scans `backend/app/state_aggregator/` and fails on:

1. `.save(`
2. `.update(`
3. raw `INSERT`
4. raw `UPDATE`

## 4. Stage 18 Interpretation

Rule AB exists to keep Stage 18 honest:

1. Aggregator is a pull-only state view, not a shadow write path.
2. Push is a deterministic compiler over bounded state, not a new LLM autonomy surface.
3. Any exception to these boundaries requires a new dispatch addendum, not an implementation shortcut.

