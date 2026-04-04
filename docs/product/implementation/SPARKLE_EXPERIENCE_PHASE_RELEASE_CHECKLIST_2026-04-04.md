# Sparkle Experience-Phase Release Checklist

> Date: 2026-04-04  
> Purpose: release-style acceptance gate for the experience-phase runtime

## Phase A Gate

The release is only green when all of the following are true:

- The primary backend growth path no longer fails on known orchestration integration blockers.
- The north-star acceptance covers `R_e`, `R_c` overload, `R_c` remobilization, `R_n`, and `R_i`.
- At least one acceptance path changes sessions mid-journey without losing continuity.
- Optional sidecars and shadow paths fail as warnings, not as fatal blockers.
- Visible adaptation survives the live runtime path and appears in user-facing payloads.

## Runtime Checklist

- `residual_decision_context` is present on final responses for experience-phase turns.
- `experience_phase_runtime` is written back into user context when adaptations are applied.
- `visible_adaptation` is produced when the system changes strategy, feedback binding, or grounding emphasis.
- User-material grounding failure degrades to `file_resolution_failed`, `retrieval_failed`, or `no_hits` without breaking the main answer.
- Shadow soul/runtime attachment failure is logged as non-fatal.

## Acceptance Matrix

- `R_e`: user materials repair a real misconception.
- `R_c`: overload is recognized and load is shed immediately.
- `R_c`: accepted lighter move is converted into mobilization.
- `R_n`: the system surfaces criteria instead of outsourcing judgment.
- `R_i`: identity-fragile language is answered with continuity-grounded evidence.
- Continuity: the system can continue a plan after a session boundary without acting like the user started from zero.

## UX Gate

- Chat can show one concrete “I adjusted this because...” surface.
- Chat shows reversibility when a strategy changed.
- Home can explain both what changed and why the next move is now the right one.
- Evidence-grounded phrasing is preserved when user materials were used.

## Human Evaluation Gate

- The thermodynamics north-star protocol can be run end to end by a human evaluator.
- Review findings are tagged with the shared taxonomy.
- Product priority changes can be traced back to transcript review, not engineering intuition alone.
