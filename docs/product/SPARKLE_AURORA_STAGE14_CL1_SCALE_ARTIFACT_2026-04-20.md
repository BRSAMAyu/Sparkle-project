# SPARKLE Aurora Stage 14 WS-CL1-SCALE Artifact (2026-04-20)

> **Workstream**: `WS-CL1-SCALE`
> **Purpose**: lock the production-scale proxy fixture and anti-cheating rules before the SQAM rerun.

## 1. Frozen Method Reference

The rerun must use exactly:

- `SPARKLE_AURORA_STAGE13_SIGNAL_QUALITY_AUDIT_METHOD_2026-04-20.md`

No metric definition, threshold, or fallback rule may change after reading the data.

## 2. Fixture Floor

The Stage 14 proxy fixture must contain:

1. `>=10` distinct source states
2. `>=200` total observations
3. at least `2` candidate targets for every source state counted in `DP1`

## 3. Source-State Naming Discipline

The fixture may use only production-shaped source states that map to real routing/tool-history semantics already present in the repo.

Stage 14 freezes the proxy source-state vocabulary to:

1. `state_plan`
2. `state_task`
3. `state_focus`
4. `state_growth`
5. `state_query`
6. `state_knowledge`
7. `state_review`
8. `state_research`
9. `state_memory`
10. `state_cognitive`
11. `state_general`

Why this list is allowed:

1. `plan / task / focus / growth / query / knowledge` are first-class tool categories in `ToolCategory`
2. `review` and `research` already appear in tool-history-facing test/data surfaces
3. `memory` and `cognitive` already appear as real product-side categories in memory/cognitive services
4. `general` is the existing learner fallback state

## 4. Target Coverage Expectation

For each source state:

1. use real tool names that already exist in the repo
2. keep at least one candidate with stronger user-perceived outcome and one weaker candidate
3. preserve the Stage 13 label precedence:
   - `was_helpful`
   - else `user_satisfaction >= 4`
   - else raw `success`

## 5. Anti-Cheating Statement

The proxy fixture is frozen **before** the rerun.

It may **not** be tuned after reading rerun scores by:

1. removing bad states
2. relabeling observations to rescue a dimension
3. lowering the source-state floor
4. padding observations with synthetic placeholder states

## 6. Downgrade Rule

If any one of `ID1`, `ST1`, `DP1`, or `SM1` falls below the Stage 13 threshold, Stage 14 exits Path A and locks `Path B`.

## 7. Boundary Lock

Allowed:

1. proxy fixture definition
2. rerun using the frozen SQAM method
3. dimension-by-dimension reporting

Not allowed:

1. threshold tuning
2. learner redesign
3. user-visible wire-on
4. shadow-runtime implementation
