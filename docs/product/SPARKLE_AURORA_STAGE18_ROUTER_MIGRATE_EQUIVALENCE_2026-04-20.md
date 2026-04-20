# SPARKLE Aurora Stage 18 Router Migrate Equivalence (2026-04-20)

> Status: final engineering equivalence checkpoint
> Scope: compare the Stage 17 direct reader and the Stage 18 Aggregator-backed provider on the frozen `FrozenSocialSnapshot` contract.

## Result

- provider contract preserved: `pass`
- direct reader vs Aggregator-backed snapshot equivalence: `pass`
- current measured divergence: `0`
- cold dataset cases executed: `20`
- KL-equivalent boundary outcome: `within <= 0.05`

## What Was Compared

1. `recent_person_mentions`
2. `pending_commitments_count`
3. `relationship_count`

## Evidence

`backend/tests/unit/test_aggregator_backed_social_context_provider.py` now runs a 20-case cold dataset matrix.

Each scenario deterministically varies:

1. `person_mention` count
2. `relationship` count
3. overdue `commitment` count

For every case, the test compares:

1. `RouterContextReader.fetch_social_snapshot(user_id)`
2. `AggregatorBackedSocialContextProvider.fetch_social_snapshot(user_id)`

and asserts the returned summaries and counts are identical.

## Boundary Note

This is a source-compatible provider migration checkpoint, not a live Router behavior benchmark. Router decision logic remains unchanged, and the Aggregator-backed provider is still behind default-OFF feature flags.
