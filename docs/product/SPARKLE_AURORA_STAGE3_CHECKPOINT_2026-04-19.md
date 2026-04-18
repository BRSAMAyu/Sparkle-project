# Stage 3 Repo-Side Checkpoint — 2026-04-19

Consensus sign-off: Claude + Codex + GLM

## Summary

Stage 3 repo-side delivery is complete.

Completed in-repo:

- Wave 1 core Aurora foundation
- Wave 2 first-batch user-facing layers (`WS5 / WS6 / WS9`)
- `WS7 Continuous Learning Phase A`
- `WS8 Integration & Validation`
- `WS-M Phase 1`: dual-core routing surface cutover with:
  - shadow mode
  - active mode
  - per-user cohort selection
  - config-only rollback

This does **not** mean Aurora has fully taken over the orchestrator. The current
production-safe takeover point is the dual-core routing surface only.

## Current Baseline

Backend Aurora test baseline:

```bash
cd /Users/brsama/code/GitHub/Sparkle-project/backend && ./.venv/bin/python -m pytest tests/aurora -q
```

Current result:

- `71 passed`

Dual-core routing cutover regression:

```bash
cd /Users/brsama/code/GitHub/Sparkle-project/backend && ./.venv/bin/python -m pytest tests/unit/orchestrator/mixins/test_routing_engine_dual_core.py -q
```

Current result:

- `8 passed`

## Shadow Comparison

Current gate status:

- routine agreement: `9 / 10 = 90%`
- overall agreement: `11 / 12 = 91.7%`

Primary source:

- [SPARKLE_AURORA_SHADOW_COMPARISON_REPORT_2026-04-19.md](/Users/brsama/code/GitHub/Sparkle-project/docs/product/SPARKLE_AURORA_SHADOW_COMPARISON_REPORT_2026-04-19.md)

## Three Caveats

### 1. Projection leakage

The current `90%` agreement measures **post-cutover user experience
consistency**, not pure-Aurora-output agreement in isolation.

Reason:

- the current Phase 1 projection intentionally reuses legacy routing-input
  signals to keep the first cutover surface behavior stable

So the current number is valid for:

- "Will Phase 1 cutover feel consistent to users?"

But it is not yet a pure answer to:

- "How often would raw Aurora outputs independently match legacy?"

### 2. Curated corpus vs production corpus

The current shadow corpus is `12` curated cases. That is sufficient for:

- repo-side completion
- nominal Stage 3 gate satisfaction

It is **not** sufficient, by itself, for opening a real production cohort.

### 3. The single divergence is interpreted, not unresolved

Current divergence:

- `routine_chat`
  - legacy = `cognitive_first`
  - Aurora = `balanced`

Current interpretation:

- Aurora is considered more aligned with the Stage 3 philosophy here
- legacy is considered overly conservative on low-stakes ambient chat

So this is being treated as an intentional quality difference, not an unknown.

## WS-M Scope

Current cutover is explicitly:

- **WS-M Phase 1**

Meaning:

- only the dual-core routing surface is under Aurora cutover control

Not yet included:

- `pre-tool-selection` takeover
- `pre-response-formatting` takeover

Those are deferred to later work and require their own shadow comparison and
runbook updates.

## Pre-Cohort Activation Conditions

Real first-cohort activation is still blocked on these three items:

1. The three caveats above must be reflected in runbooks/checklists.
   Owner: Codex
2. Shadow corpus must be expanded to `>=100` production-replay cases and still
   hold `>=80%` agreement.
   Owner: to be assigned (requires production replay access)
3. WS-M must remain explicitly labeled **Phase 1** in all rollout
   communication, to avoid "full Aurora takeover" misinterpretation.
   Owner: Codex

## Repo-Side Completion Call

With the current repository state, the correct completion statement is:

> Stage 3 repo-side delivery is complete.  
> Aurora’s core foundation, first-batch user-facing layers, continuous learning
> Phase A, integration/validation, and dual-core-surface cutover are now landed
> and green in-repo.  
> Real user cohort activation remains a separate operational gate.
