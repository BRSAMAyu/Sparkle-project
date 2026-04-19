# SPARKLE Aurora Stage 8 BP5 White-list (2026-04-20)

> **Status**: Stage 8 `WS-BP5` design-freeze artifact v0
> **Purpose**: define the exact minimal parameter white-list allowed to close breakpoint `#5` (`cognitive_adjustments` text-only) without widening Aurora authority beyond Rule K.
> **Authority**:
> - `SPARKLE_USER_MODEL_LAYERED_ARCHITECTURE_2026-04-19.md`
> - `SPARKLE_AURORA_STAGE8_DISPATCH_PLAN_2026-04-20.md`

## 1. Decision Summary

Stage 8 `WS-BP5` will **not** introduce a new parameter carrier.
The initial closure path reuses the existing audited session-strategy surface:

- `UserStrategyStateService.apply_adjustment(...)`
- `CapabilityKnobGovernor`
- `experience_actuator.py`

This is the smallest governance-safe path because:

1. it already enforces field allowlists
2. it already records per-write audit entries
3. it already affects downstream control posture beyond prompt prose
4. it avoids creating a second Stage 8 control plane beside `PlanState.facts["adaptive_adjustments"]`

Hard interpretation:

- Stage 8 closes breakpoint `#5` through **session-layer reversible strategy knobs**
- Stage 8 does **not** use `PlanState.facts["adaptive_adjustments"]` as the primary carrier for this breakpoint
- Stage 8 does **not** activate runtime-only LLM parameters such as `temperature_offset` in the first white-list

## 2. White-listed Fields

The Stage 8 initial implementation white-list is:

| Field | Carrier | Layer | Allowed values | Why it is allowed | Audit source |
| --- | --- | --- | --- | --- | --- |
| `session_mode` | `UserStrategyStateService` | `session` | `guided`, `exploratory`, `review`, `recovery` | directly changes control posture and is already consumed by downstream strategy/render paths | `apply_adjustment().applied[*]` history entry |
| `push_vs_support` | `UserStrategyStateService` | `session` | `0.0` to `1.0` | converts "push less / support more" from prose into bounded numeric steering | `apply_adjustment().applied[*]` history entry |
| `intervention_intensity` | `UserStrategyStateService` | `session` | `low`, `medium`, `high` | expresses gentle vs stronger intervention intensity without touching facts | `apply_adjustment().applied[*]` history entry |
| `explanation_style` | `UserStrategyStateService` | `session` | `conceptual`, `example_based`, `step_by_step` | lets cognitive adjustments change explanation pacing/shape in a bounded way | `apply_adjustment().applied[*]` history entry |
| `difficulty_level` | `UserStrategyStateService` | `session` | `1` to `5` | converts "make this easier / harder to start" into explicit bounded execution pressure | `apply_adjustment().applied[*]` history entry |

## 3. Explicitly Not White-listed in Stage 8

The following fields are **not** in the Stage 8 initial white-list:

| Field | Status | Reason |
| --- | --- | --- |
| `retrieval_emphasis` | deferred | too close to source-selection semantics; Stage 8 keeps Rule K interpretation conservative |
| `temperature_offset` | deferred | allowed in theory only as Aurora-self runtime control, but not required for Stage 8 closure |
| `verbosity_level` | deferred | would require a new runtime carrier for limited product gain in Stage 8 |
| `presence_level_hint` | deferred | same as above; not needed for first breakpoint closure |
| `tool_invocation_priority` | deferred | requires a new runtime-control seam and stronger observability |
| `token_allocation_delta` | deferred | budget steering is still adjacent to `RB1` precision work and is not needed for this closure |
| any new field not named here | forbidden | would be a silent white-list expansion and must stop/escalate |

## 4. Audit Interpretation

Stage 8 does not introduce a new dedicated `AuroraParameterAuditLog` table.
For this workstream, the authoritative audit record is the existing
`UserStrategyStateService.apply_adjustment()` history payload, which already records:

1. `field`
2. `layer`
3. `old_value`
4. `new_value`
5. `reason`
6. `evidence`
7. `confidence`
8. `timestamp`
9. `expires_at`

That satisfies Stage 8's audit requirement without widening storage scope.

## 5. Required Invariants

Every Stage 8 `WS-BP5` write must satisfy all of the following:

1. target layer is `session`
2. write is reversible
3. field is one of the five names in this document
4. write path goes through `CapabilityKnobGovernor` and `UserStrategyStateService`
5. no profile facts, evidence records, or correction records are mutated
6. no new `PlanState.facts["adaptive_adjustments"]` write is introduced for this breakpoint

## 6. Non-goals

This white-list does **not** authorize:

1. profile-layer writes
2. episode-layer writes
3. source selection changes
4. algorithm rewrites
5. evidence-chain rewrites
6. any new runtime-only Aurora parameter without a later amendment

## 7. Exit Condition

`WS-BP5` may claim closure only if:

1. at least one previously text-only `cognitive_adjustments` outcome becomes one of the white-listed parameter writes above
2. the write is audit-visible through `UserStrategyStateService`
3. prompt-only text remains supplemental, not the sole effect
4. no Rule K or Rule O violation occurs
