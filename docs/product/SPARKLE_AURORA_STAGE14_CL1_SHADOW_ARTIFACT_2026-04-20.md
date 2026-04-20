# SPARKLE Aurora Stage 14 WS-CL1-SHADOW Artifact (2026-04-20)

> **Workstream**: `WS-CL1-SHADOW`
> **Purpose**: lock the recorder contract and zero-user-impact boundary before shadow code lands.

## 1. Recorder Schema

Each shadow record must include:

1. `timestamp`
2. `user_id`
3. `source_state`
4. `fallback_choice`
5. `learner_choice`
6. `eventual_outcome`

Optional query-support fields are allowed only if they remain L2-side and non-user-visible:

1. `diverged`
2. `fallback_probability`
3. `learner_probability`

## 2. Storage Location

Shadow records must live in the existing L2 inference-cache neighborhood only.

Stage 14 authorizes:

1. Redis-backed cache records keyed under a dedicated shadow namespace
2. TTL-bounded storage for inspection

Stage 14 does **not** authorize:

1. L0 raw-event writes
2. L1 fact/projection writes
3. L3 Aurora control writes
4. any new database table or write lane

## 3. Zero User-Visible Impact Statement

Shadow outputs must **not** be consumed by:

1. prompt rendering
2. push generation
3. evidence cards
4. profile transparency payloads
5. any user-facing recommendation path

Stage 14 builds the pipe only. It does not activate observation policy or wire-on behavior.

## 4. Query Surface

Stage 14 requires a narrow query surface for inspection only:

1. fetch recent shadow records for one user
2. compute divergence rate over a recent window
3. inspect latest fallback vs learner choices

This query surface is for verification and Stage 15 design, not for product UI.

## 5. Boundary Lock

Allowed:

1. shadow recorder
2. L2-side storage
3. divergence-rate inspection helpers

Not allowed:

1. user-visible routing changes
2. prompt injection
3. push behavior
4. evidence generation
