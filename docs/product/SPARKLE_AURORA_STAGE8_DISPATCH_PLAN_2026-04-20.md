# SPARKLE Aurora Stage 8 Dispatch Plan (2026-04-20)

> **Status**: Stage 8 dispatch baseline v0 after Stage 7 closeout
> **Authority**: `SPARKLE_AURORA_STAGE7_HANDOFF_2026-04-19.md` is the only Stage 7 truth source; this plan starts from that frozen baseline and must not reopen completed Stage 5 / Stage 6 / Stage 7 work.
> **Depends on**:
> - `SPARKLE_VISION_ANCHOR_LIST_2026-04-19.md`
> - `SPARKLE_USER_MODEL_LAYERED_ARCHITECTURE_2026-04-19.md`
> - `SPARKLE_AURORA_STAGE5_HANDOFF_2026-04-19.md`
> - `SPARKLE_AURORA_STAGE7_DISPATCH_PLAN_2026-04-19.md`
> - `SPARKLE_AURORA_STAGE7_HANDOFF_2026-04-19.md`
> **Scope**: Stage 8 execution design. Converts the last explicitly deferred Stage 5 breakpoints plus the Rule K CI hardening gap into dispatchable workstreams, ownership boundaries, acceptance rules, and closeout gates.

## 0. Stage 8 Positioning

Stage 7 proved that mobile transparency is live, the evaluation runner is real,
the `M1` coverage contract is explicit, and the compiler seam is adapter-shaped.

Stage 8 must not relitigate that.

### One-sentence definition

**Stage 8 is the stage where Sparkle's day-to-day loop stops being "mostly wired"
and becomes governance-backed closure: the remaining drifting breakpoints become
auditable user-facing paths, and Rule K gets an actual CI stop sign.**

### What Stage 8 must treat as already settled

The following are frozen baseline facts unless new evidence proves a regression:

1. mobile transparency/correction can consume canonical Stage 6/7 payloads
2. a real read-only profile evaluation runner exists
3. canonical profile truth still belongs to `UserInsightCompiler -> UserInsightState`
4. `M1` source coverage and quality markers can live in the projection contract
5. Rule K remains the governing write-path discipline for the five-lane user-model system

### Stage 8 starting gaps

Per Stage 5 carry-forward debt, Stage 7 handoff, and accepted Stage 8 review notes,
Stage 8 starts from exactly five work items:

1. Rule K CI static detection
2. breakpoint `#3` `plan health no event` end-to-end closure
3. breakpoint `#4` `push time-only` closure by wiring behavior-triggered push delivery
4. breakpoint `#5` `cognitive_adjustments text-only` closure through minimal white-listed parameter steering
5. `WS-V2` fallback telemetry hardening

## 1. Stage 8 Principles

### Principle A: No Earlier Stage Reopen

Stage 8 may close, verify, instrument, or harden the already-landed system.
It may not treat Stage 5 / 6 / 7 as unfinished just to justify another broad rewrite.

### Principle B: Governance First, Then Control Writes

If Stage 8 wants to make Aurora write any new parameterized control signal, CI
must be able to reject out-of-bounds writes first.

`WS-K-CI` is therefore not optional hygiene. It is the safety precondition for `WS-BP5`.

### Principle C: Existing Bridges Beat Greenfield Reinvention

Stage 8 must prefer connecting and verifying already-landed bridges over inventing parallel systems.

Hard interpretation:

1. `WS-BP3` closes the `plan.health.alerted -> intervention -> delivery` path; it does not reinvent plan-health detection.
2. `WS-BP4` connects the existing behavior bridge to push scheduling; it does not pretend behavior-trigger reasoning is absent.
3. `WS-BP5` must reuse the existing strategy-knob and adaptive-parameter surfaces wherever possible.

### Principle D: Parameters Are Not Profile Facts

Aurora may steer bounded parameters.
Aurora may not write user facts, evidence, or profile truth.

This includes the Stage 8 clarification that `temperature_offset` is only legal
when it affects Aurora's own LLM invocation parameters. It may not become a backdoor
for writing user-model data.

### Principle E: End-to-End Proof Beats File Existence

For Stage 8, the existence of a bridge, consumer, or task is not closure.
Acceptance must prove that the path actually runs end to end.

### Principle F: Minimal White-list Beats Flexible White-list

`WS-BP5` must land the smallest parameter set that closes the breakpoint.
If a new parameter is not necessary to prove closure, it should not be added.

## 2. Explicitly Out of Scope

The following are not Stage 8 scope unless a later amendment says otherwise:

1. in-chat profile query or in-chat profile correction UX
2. graph-as-diagnostic product work
3. continuous-learning / distillation pipeline integration
4. home growth dashboard or weekly/monthly review UX
5. dual interaction mode rollout
6. Aurora shadow-model production drift adjudication
7. broad push-product redesign beyond behavior-triggered scheduling closure
8. expanding the Stage 8 parameter white-list beyond the minimal accepted set
9. turning `AI inference >= 70%` into a Stage 8 hard gate before its metric is formally defined

## 3. Workstream Overview

| Workstream | Focus | Primary lane | Breakpoint advanced | Anchor signal | Priority | Risk |
| --- | --- | --- | --- | --- | --- | --- |
| `WS-K-CI` | Rule K static detection in pre-commit + CI | governance | GLM `P2-3` -> enforced stop | `A1`, `A5` | highest | low |
| `WS-BP3` | `plan health` event -> intervention -> visible action | `L2` diagnostics -> delivery | `#3` | `A3`, `A4` | highest | medium |
| `WS-BP4` | behavior-triggered push scheduling | behavior bridge -> push delivery | `#4` | `A3`, `A4` | highest | medium |
| `WS-BP5` | `cognitive_adjustments` -> white-listed parameter steering | `L3` control / session strategy | `#5` | `A1`, `A2`, `A5` | highest | high |
| `WS-V2T` | transparency fallback telemetry | mobile consumer observability | GLM `P2-1` | `A1`, `A5` | medium | low |

### Wave Order

Stage 8 keeps the five-workstream scope, but the close order is intentionally staged:

1. `WS-K-CI` must close before `WS-BP5` reaches final accept.
2. `WS-BP3`, `WS-BP4`, and `WS-BP5` may prepare in parallel after `WS-K-CI` scope is frozen, but `WS-BP5` final accept depends on CI hard-stop coverage being real.
3. `WS-V2T` closes after the live paths are stable enough that fallback telemetry reflects real residuals rather than in-flight implementation noise.

### Concrete judgments baked into Stage 8

1. `WS-BP3` means proving `plan.health.alerted` becomes a tracked user-facing action path, not merely pointing at bridge files.
2. `WS-BP4` means wiring the existing `behavior_intervention_bridge` into push scheduling; it is not a greenfield behavior-trigger subsystem.
3. `WS-BP5` means moving beyond text-only `cognitive_adjustments`; prompt prose alone no longer counts as closure.
4. `WS-V2T` means recording fallback use and failure mode, not redesigning the profile surface.

## 4. Dispatch Rules

Stage 8 inherits `Rule G`, `Rule H`, `Rule I`, `Rule J`, `Rule K`, `Rule L`, and `Rule M`.

### Rule N · CI Hard Stop

Any pull request or local signoff path that fails the Rule K static detector must be treated as merge-blocking.

Hard interpretation:

1. failing pre-commit or CI is not advisory
2. a red Rule K gate cannot be waived by "tests still pass"
3. Stage 8 is not closed until this stop sign is wired into the normal engineering path

### Rule O · No Silent White-list Expansion

`WS-BP5` may only write parameters explicitly named in its white-list artifact.
Any new candidate field discovered during implementation must stop and escalate to a later amendment or later stage.

### Stage 8 BP5 white-list interpretation

Stage 8 recognizes two bounded parameter families, but the final implementation must choose the smallest subset actually needed:

1. existing audited strategy/session knobs already supported by `UserStrategyStateService` and `CapabilityKnobGovernor`
   - `difficulty_level`
   - `push_vs_support`
   - `session_mode`
   - `intervention_intensity`
   - `explanation_style`
   - `retrieval_emphasis`
2. Aurora runtime-only self parameters, allowed only if implemented as control parameters rather than user-model data
   - `token_allocation_delta`
   - `verbosity_level`
   - `presence_level_hint`
   - `temperature_offset`
   - `tool_invocation_priority`

`temperature_offset` is only legal when it changes Aurora's own LLM invocation behavior.
It may not mutate profile facts, evidence chains, or user-state records.

## 5. Review Lanes

High-risk lane:

`Codex design freeze -> implementation -> internal pre-accept -> Claude final-accept -> User sign-off`

Medium-risk lane:

`Codex design freeze -> implementation -> internal pre-accept -> Claude spot-check or user sign-off`

Low-risk lane:

`Codex design freeze -> implementation -> internal pre-accept -> user sign-off`

### Stage 8 workstream lane assignment

| Workstream | Review lane | Reason |
| --- | --- | --- |
| `WS-K-CI` | low-risk | governance hardening with narrow repo-scoped hot spots |
| `WS-BP3` | medium-risk | event/delivery closure without new write-lane design |
| `WS-BP4` | medium-risk | push scheduling semantics change, but on top of existing behavior bridge |
| `WS-BP5` | high-risk | touches Rule K white-list interpretation and Aurora control writes |
| `WS-V2T` | low-risk | observability hardening only |

### Stage 8 high-risk triggers

Any task touching one of the following is automatically high-risk:

1. `backend/app/services/user_strategy_state_service.py`
2. `backend/app/services/capability_knob_governor.py`
3. `backend/app/orchestration/experience_actuator.py`
4. `backend/app/orchestration/dual_core_router.py`
5. `backend/app/orchestration/routing_engine.py`
6. any new Stage 8 Aurora runtime-parameter carrier

## 6. Hotspot Ownership

| File / Zone | Owner | Reason |
| --- | --- | --- |
| `.pre-commit-config.yaml` | `WS-K-CI` | local Rule K stop sign |
| `.github/workflows/ci.yml` | `WS-K-CI` | PR-time Rule K enforcement |
| `scripts/check_rule_k_write_paths.py` | `WS-K-CI` | static detector entrypoint |
| `backend/app/services/plan_health_signal_service.py` | `WS-BP3` | event emission semantics and dedup boundary |
| `backend/app/services/plan_health_event_consumer.py` | `WS-BP3` | plan-health consumer -> delivery closure |
| `backend/app/services/card_protocol/health_intervention_bridge.py` | `WS-BP3` | intervention record generation from plan-health signals |
| `backend/app/services/behavior_signal_collector.py` | `WS-BP4` | behavior pattern event source and bridge invocation seam |
| `backend/app/services/card_protocol/behavior_intervention_bridge.py` | `WS-BP4` | behavior -> intervention mapping and delivery-channel choice |
| `backend/app/core/celery_tasks.py` | `WS-BP4` | push scheduling entrypoint currently too stub-like |
| `backend/app/services/user_strategy_state_service.py` | `WS-BP5` | existing audited parameter-write surface |
| `backend/app/services/capability_knob_governor.py` | `WS-BP5` | allowlist enforcement over bounded knob writes |
| `backend/app/orchestration/experience_actuator.py` | `WS-BP5` | current automatic bounded-adjustment application path |
| `backend/app/orchestration/dual_core_router.py` | `WS-BP5` | current text-only `cognitive_adjustments` producer |
| `backend/app/orchestration/routing_engine.py` | `WS-BP5` | current empty adjustment path in direct-mode cutovers |
| `mobile/lib/features/user/presentation/providers/ws6_profile_mirror_provider.dart` | `WS-V2T` | canonical / fallback / inert binding point |
| `mobile/lib/core/services/client_observability_service.dart` | `WS-V2T` | telemetry emission path |
| `backend/app/api/v1/client_telemetry.py` | `WS-V2T` | telemetry aggregation surface |
| `docs/product/*STAGE8*` | `Codex` | sequencing, governance, and closeout integration |

### Shared-file rule

If one workstream needs information from another hotspot:

1. request a seam extraction or explicit handoff
2. do not silently co-edit the other workstream's hotspot

## 7. Workstream Cards

## 7.1 `WS-K-CI` — Rule K Static Detection

**Goal**

Make Rule K enforceable in normal engineering flow through local pre-commit and CI.

**Why this exists**

Stage 7 accepted GLM `P2-3` as real debt:

- Rule K is defined in docs and handoffs
- current engineering flow has no static detector for Rule K violations
- Stage 8 wants to harden Aurora-side parameter writes, which is unsafe without an automated stop sign

**Stage 8 in-scope**

- add a repo-local Rule K static detector
- wire it into `.pre-commit-config.yaml`
- wire it into `.github/workflows/ci.yml`
- define at least the initial forbidden-pattern inventory needed to catch obvious lane violations

**Stage 8 out-of-scope**

- perfect semantic program analysis
- replacing unit/integration tests
- turning Rule K into a broad architecture-lint framework for unrelated modules

**Acceptance target**

At accept time, we should be able to show:

1. a local pre-commit command that fails on known Rule K violations
2. a CI step that fails on the same violations
3. at least one regression test or fixture proving the detector catches a real forbidden pattern

## 7.2 `WS-BP3` — Plan Health Event Closure

**Goal**

Turn `plan.health.alerted` from a partly wired event source into a verified intervention/delivery path.

**Why this exists**

The repo already contains most of the path:

- `PlanHealthSignalService`
- `plan_health_event_consumer.py`
- `health_intervention_bridge.py`
- tests proving pieces of the chain

What remains open is governance-grade proof that a real plan-health alert becomes a tracked user-facing action path rather than just a latent capability.

**Stage 8 in-scope**

- verify and harden the end-to-end chain from plan-health signal to intervention record and delivery path
- preserve the no-double-notify rule relative to breakpoint `#1`
- add acceptance coverage for visible action outcomes rather than silent internal state only

**Stage 8 out-of-scope**

- reworking plan-health evaluation heuristics
- expanding plan-health into a new product surface
- bundling breakpoint `#4` behavior-trigger push work into the same WS

**Acceptance target**

At accept time, we should be able to demonstrate:

1. `plan.health.alerted` produces a tracked downstream action path
2. the dedup / cooldown rules still hold
3. user-visible delivery is not duplicated when breakpoint `#1` already acted

## 7.3 `WS-BP4` — Behavior-Triggered Push Scheduling

**Goal**

Close breakpoint `#4` by turning the existing behavior-intervention bridge into a real behavior-triggered push scheduling path.

**Why this exists**

Current reality is not "nothing exists." The repo already has:

- `BehaviorSignalCollector`
- `behavior_intervention_bridge.py`
- trigger-type mapping and delivery-channel selection
- a push scheduling task entrypoint

The remaining gap is that push behavior is still effectively time-driven in practice, while the behavior-trigger path remains under-verified and too stub-like.

**Stage 8 in-scope**

- connect the existing behavior bridge to push scheduling in a way that is test-backed
- prove that a high-confidence behavior pattern can schedule push delivery because of the pattern, not only clock time
- keep the existing low-pressure delivery semantics rather than escalating into spammy behavior

**Stage 8 out-of-scope**

- inventing a new behavior trigger taxonomy
- replacing the existing push stack
- redesigning notification-center UX

**Acceptance target**

At accept time, we should be able to show:

1. a behavior pattern can create a push-scheduled intervention path
2. the path is distinguishable from time-only reminder scheduling
3. tests prove the scheduling trigger is behavioral rather than clock-based

## 7.4 `WS-BP5` — Cognitive Adjustments to White-listed Parameter Steering

**Goal**

Move `cognitive_adjustments` beyond text-only prompt hints into bounded, audited parameter steering.

**Why this exists**

Current reality is split:

- `DualCoreDecision.cognitive_adjustments` is still `list[str]`
- `routing_engine.py` still has direct-mode paths with empty adjustments
- existing bounded knob infrastructure already exists in `UserStrategyStateService`, `CapabilityKnobGovernor`, and `experience_actuator.py`
- card-protocol `ParameterCompiler` already writes real adaptive adjustments in another lane

Stage 8 should close the breakpoint by binding these existing control surfaces more explicitly, not by creating another control plane.

**Stage 8 in-scope**

- produce a minimal white-list artifact before implementation
- choose the smallest parameter subset needed for real closure
- route qualifying cognitive-adjustment outcomes into a bounded parameter surface with audit trails
- preserve reversibility and bounded write semantics
- prove that the result changes control posture beyond plain prompt prose

**Stage 8 out-of-scope**

- broad expansion of Aurora authority
- unrestricted runtime prompt steering
- user-fact or profile-data writes
- adding new white-list fields beyond the accepted artifact

**Required pre-implementation artifact**

Before implementation accept, Stage 8 must land:

- `docs/product/SPARKLE_AURORA_STAGE8_BP5_WHITELIST_2026-04-20.md`

That artifact must say:

1. which exact fields are allowed in Stage 8
2. which ones reuse existing strategy-state storage
3. which ones, if any, are Aurora runtime-only parameters
4. how audit logging is recorded for each field

**Acceptance target**

At accept time, we should be able to say:

1. `cognitive_adjustments` no longer remain text-only
2. every actual write is within the approved Stage 8 white-list
3. audit evidence exists for each parameterized write
4. no Rule K violation occurs and no third control plane emerges

## 7.5 `WS-V2T` — Transparency Fallback Telemetry

**Goal**

Instrument the remaining Stage 7 fallback paths so the team can see whether the mobile transparency surface is using canonical binding, deprecated fallback, or inert failure.

**Why this exists**

Stage 7 closed the visible surface, but GLM `P2-1` correctly noted that fallback use is still opaque.

Current repo reality already provides:

- a canonical/fallback/inert branching point in `ws6_profile_mirror_provider.dart`
- a client telemetry ingestion API
- a mobile client observability service

**Stage 8 in-scope**

- emit telemetry when the provider chooses canonical binding, deprecated fallback, or inert failure
- keep payloads lightweight and privacy-safe
- add tests or verification showing these states can be distinguished

**Stage 8 out-of-scope**

- redesigning the transparency UI
- backend contract changes unrelated to telemetry
- building a broad analytics dashboard

**Acceptance target**

At accept time, we should be able to inspect telemetry and answer:

1. how often canonical binding succeeds
2. whether deprecated fallback is still being used
3. whether inert/failure binding still occurs in the field

## 8. Acceptance Gates

### Gate S8-0 · Baseline Freeze

Before landing Stage 8 work, the Stage 7 post-close sweep must still reproduce:

```bash
cd backend && ./.venv/bin/python -m pytest \
  tests/aurora \
  tests/api/test_profile_transparency_api.py \
  tests/profile/eval/test_profile_eval_skeleton.py \
  tests/profile/eval/test_profile_eval_runner.py \
  tests/profile/test_intervention_verification_loop.py \
  tests/unit/test_situation_brief.py \
  tests/unit/test_phase2_intervention_pipeline.py -q
```

Baseline result on branch tip when this plan was written:

- `143 passed`
- `0 failed`

### Gate S8-1 · Per-WS Proof

Each Stage 8 workstream must land with:

1. focused automated verification for its owned hotspot
2. a short accept artifact or note if the WS changes a governance boundary
3. explicit confirmation that no Stage 7 truth claim was reopened

### Gate S8-Close · Full Post-Close Sweep

Before Stage 8 can be declared closed:

1. rerun the Stage 7 baseline command above
2. run any new Stage 8 CI / push / parameter-steering / telemetry tests
3. update the anchor list so breakpoint `#3 / #4 / #5` move from deferred to closed
4. record the full post-close result in the Stage 8 handoff artifact

Subset-only green is not sufficient.

## 9. Next Entry Condition

Stage 8 execution may start immediately from this plan if:

1. `SPARKLE_AURORA_STAGE7_HANDOFF_2026-04-19.md` remains the governing Stage 7 baseline
2. Stage 7's `143 passed` baseline remains reproducible
3. scope stays pinned to the five Stage 8 workstreams defined here

If those conditions hold, Stage 8 should spend its effort on closure and governance hardening rather than rediscovering architecture already settled in earlier stages.

## 10. Explicit Forward Tracking

Stage 8 intentionally focuses on daily-loop closure and Rule K hardening.
The following strategic items remain tracked but are not Stage 8 scope:

| Item | Status after Stage 7 | Next home |
| --- | --- | --- |
| in-chat profile query / correction | not started | Stage 9 |
| graph as diagnostic surface | not started | Stage 10 |
| continuous learning / distillation mainline | not started | Stage 11 |
| growth dashboard + weekly/monthly review UX | not started | Stage 12 |
| dual interaction mode | not started | Stage 13 |
| shadow-model production drift adjudication | not started | Stage 13 |
| `RB1` tokenizer-aware inline budget precision | tracked precision tail | Stage 8 candidate or later amendment |

Hard interpretation:

1. Stage 8 does not get to silently absorb Stage 9+ product themes.
2. `RB1` remains tracked, but it is not a blocker for Stage 8 breakpoint closure unless a regression proves bounded snapshot discipline insufficient.
