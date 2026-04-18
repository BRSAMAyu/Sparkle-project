# Sparkle Aurora Shadow Comparison Report (2026-04-19)

## Scope

This report captures the Wave 2 shadow comparison gate between:

- legacy `dual_core_router`
- Aurora `safe_route()` projected back into legacy dual-core mode semantics

The comparison is intentionally limited to the current Stage 3 surface:

- trigger point: `pre-node-routing`
- Aurora policy: `aurora_policy@v1.0`
- case count: `12`
- routine gate cases: `10`

## Projection Rule

Aurora is not compared to legacy by raw field equality. Instead, Aurora is first
projected back into the legacy mode space:

- `cognitive_first`
  - Aurora surfaces `holding / reconciliation / identity / meta-surface`
  - or basis is `energy_drop / partner_signal`
  - or the snapshot clearly indicates concept-confusion / support-first framing
- `execution_first`
  - Aurora transitions because of `commitment_conflict / schedule_constraint`
  - or Aurora stays ambient/routine on clearly structured planning/task requests
- `balanced`
  - low-intensity conversational situations without a strong support-first cue

The executable source of truth for this projection is:

- [test_shadow_comparison.py](/Users/brsama/code/GitHub/Sparkle-project/backend/tests/aurora/test_shadow_comparison.py)

## Results

- Overall agreement: `11 / 12 = 91.7%`
- Routine gate agreement: `9 / 10 = 90.0%`

This passes the Wave 2 gate requirement of `>= 80%` routine agreement.

## Divergences

There is one current divergence:

| Case | Legacy | Aurora projection | Why it diverges |
| --- | --- | --- | --- |
| `routine_chat` | `cognitive_first` | `balanced` | Legacy remains conservative on low-confidence chat-like requests. Aurora keeps the interaction ambient/routine when there is no stronger blockage signal. |

## Interpretation

The current divergence profile is acceptable for Stage 3 progression:

- The disagreement is narrow and interpretable.
- It does not occur on the high-value execution / crisis / procrastination /
  concept-confusion paths that define Sparkle's primary product behavior.
- Aurora is already aligned with legacy on the more important support-first and
  execution-first cases, while preserving richer signals such as partner input
  and explicit crisis routing.

## Gate Decision

- Wave 2 shadow comparison gate: **PASS**
- WS-M migration unblock condition (`>= 80%` routine agreement): **SATISFIED**

## Follow-up

Two follow-ups remain intentionally outside this gate:

1. Move hard-coded strong-signal basis logic further toward policy truth.
2. Expand the shadow corpus from the current curated 12 cases toward the larger
   migration-time comparison set planned for later waves.
