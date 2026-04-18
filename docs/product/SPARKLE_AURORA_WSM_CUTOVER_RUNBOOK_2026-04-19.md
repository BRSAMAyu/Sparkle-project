# Sparkle Aurora WS-M Cutover Runbook (2026-04-19)

## Scope

This runbook covers the current Stage 3 cutover surface that is now implemented:

- Aurora cohort gating for the existing dual-core decision surface
- shadow vs active user selection
- rollback expectations

This is intentionally **not** a full orchestrator-wide Aurora takeover. The
current production-safe cutover point is:

- `backend/app/orchestration/routing_engine.py`
  - `_apply_dual_core_routing()`

At this layer, Aurora can replace or shadow the legacy `dual_core_router`
without destabilizing the rest of the orchestration stack.

## Implemented Flags

Defined in:

- [aurora.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/config/aurora.py)

### Global toggles

- `AURORA_SHADOW_MODE`
- `AURORA_ACTIVE`
- `INTERACTION_VARIANTS`

### Per-user / cohort selectors

- `AURORA_SHADOW_USER_IDS`
- `AURORA_ACTIVE_USER_IDS`
- `AURORA_SHADOW_COHORT_PERCENT`
- `AURORA_ACTIVE_COHORT_PERCENT`

## Resolution Rules

Implemented in:

- [migration.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/aurora/migration.py)

Resolution order:

1. `active` cohort wins over `shadow`
2. explicit user allowlists beat percentage buckets
3. if no selector is configured:
   - `AURORA_ACTIVE=true` means global active
   - `AURORA_SHADOW_MODE=true` means global shadow
4. if neither applies, user stays on legacy

## Current Cutover Behavior

### Legacy

- legacy `dual_core_router` drives the decision
- no Aurora projection is used

### Shadow

- legacy `dual_core_router` still drives the user path
- Aurora runs through the migration adapter
- comparison result is stored in `state.context_data["aurora_shadow_comparison"]`
- divergence is emitted through Aurora observability metrics

### Active

- Aurora projection replaces the legacy dual-core decision
- downstream code still receives a `DualCoreDecision`-shaped object
- this keeps the rest of the orchestrator stable while enabling real cohort cutover

## What Aurora Replaces Today

Aurora currently replaces only the **dual-core routing decision surface**:

- `execution_first`
- `cognitive_first`
- `balanced`

It does this by:

1. translating `DualCoreRoutingInput` into a minimal `SignalSnapshot`
2. running `AuroraEngine.safe_route()`
3. projecting the resulting TDR back into legacy dual-core semantics

This projection is implemented in:

- [migration.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/aurora/migration.py)

The executable regression guard is:

- [test_migration_cutover.py](/Users/brsama/code/GitHub/Sparkle-project/backend/tests/aurora/test_migration_cutover.py)
- [test_shadow_comparison.py](/Users/brsama/code/GitHub/Sparkle-project/backend/tests/aurora/test_shadow_comparison.py)

## Gate Status

### Shadow comparison

- routine agreement: `9 / 10 = 90%`
- overall agreement: `11 / 12 = 91.7%`

Important interpretation:

- current `90%` measures **post-cutover user experience consistency** on the
  current dual-core surface
- it does **not** yet measure pure-Aurora-output agreement in isolation,
  because the current projection intentionally reuses legacy routing input
  signals to keep Phase 1 cutover user-visible behavior stable

Source:

- [SPARKLE_AURORA_SHADOW_COMPARISON_REPORT_2026-04-19.md](/Users/brsama/code/GitHub/Sparkle-project/docs/product/SPARKLE_AURORA_SHADOW_COMPARISON_REPORT_2026-04-19.md)

### Current regression baseline

```bash
cd /Users/brsama/code/GitHub/Sparkle-project/backend && ./.venv/bin/python -m pytest tests/aurora -q
```

Current result:

- `71 passed`

Additional routing cutover verification:

```bash
cd /Users/brsama/code/GitHub/Sparkle-project/backend && ./.venv/bin/python -m pytest tests/unit/orchestrator/mixins/test_routing_engine_dual_core.py -q
```

Current result:

- `8 passed`

## Recommended Rollout Sequence

### Step 1 — Shadow all or targeted users

Set:

- `AURORA_SHADOW_MODE=true`
- `AURORA_ACTIVE=false`

Optional targeting:

- `AURORA_SHADOW_USER_IDS=<comma-separated-user-ids>`
- or `AURORA_SHADOW_COHORT_PERCENT=<0-100>`

Exit criteria:

- divergence profile remains interpretable
- fallback metrics stay stable
- no regression in dual-core downstream behavior

### Step 2 — Active first cohort

Pre-conditions:

- the 3 shadow-projection caveats from the Stage 3 checkpoint are documented
- shadow corpus is expanded to `>=100` production-replay cases and still holds
  `>=80%` agreement
- WS-M is treated as **Phase 1 only**, not as full Aurora takeover

Set:

- `AURORA_ACTIVE=true`
- `AURORA_ACTIVE_USER_IDS=<first cohort ids>`

Recommended initial cohort:

- explicit allowlist only
- do not start with percentage rollout first

Exit criteria:

- no unexpected routing regressions on the cohort
- observability confirms decisions are flowing through Aurora active path

### Step 3 — Gradual expansion

Move from explicit allowlist to:

- `AURORA_ACTIVE_COHORT_PERCENT=<small percentage>`

Recommended growth:

- 1% → 5% → 10% → broader

Only expand if:

- shadow comparison stays healthy
- fallback/no-op rates do not spike
- downstream prompt / UX behavior remains stable

## Rollback

Fastest rollback path:

1. set `AURORA_ACTIVE=false`
2. optionally keep `AURORA_SHADOW_MODE=true`
3. if needed, set `AURORA_SHADOW_MODE=false` too

Because the active cutover only swaps the dual-core decision source and keeps
legacy-shaped downstream objects, rollback is configuration-only for this stage.

## Known Limits

1. This cutover is **WS-M Phase 1**, not full Aurora orchestration takeover.
2. Phase 2 (`pre-tool-selection`) and Phase 3 (`pre-response-formatting`) are
   deferred to Stage 4 and require separate shadow comparison + runbook.
3. Strong-signal basis logic still deserves a later move closer to policy truth.
4. User cohort routing is implemented for the dual-core surface first, not every
   Aurora trigger point from the integration contract.
5. Current shadow agreement is based on a curated 12-case corpus and is
   sufficient for repo-side completion, but not yet sufficient by itself for
   real-user cohort activation.
6. Real production cohort activation still needs operator choice of user ids or
   rollout percentage, plus the production-replay shadow expansion noted above.

## Pre-Cohort Activation Checklist

Before opening the first real user cohort, the following items must be complete:

1. Document the 3 caveats around current shadow comparison interpretation.
   Owner: Codex
2. Expand the shadow corpus to `>=100` production-replay cases and confirm
   `>=80%` agreement still holds.
   Owner: to be assigned (requires production traffic replay access)
3. Keep WS-M explicitly labeled as **Phase 1** in all user-facing/internal
   checkpoint communication.
   Owner: Codex

## Completion Call

For the current repo state, WS-M is **cutover-ready at the dual-core surface**:

- cohort selection implemented
- active/shadow switching implemented
- rollback is config-only
- tests and shadow report are green
