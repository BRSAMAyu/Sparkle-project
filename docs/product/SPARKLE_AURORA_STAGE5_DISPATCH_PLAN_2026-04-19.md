# SPARKLE Aurora Stage 5 Dispatch Plan (2026-04-19)

> **Status**: Closeout v2, execution landed on branch tip; awaiting external review and final sign-off
> **Depends on**:
> - `SPARKLE_VISION_ANCHOR_LIST_2026-04-19.md` v3
> - `SPARKLE_AURORA_STAGE4_DISPATCH_PLAN_2026-04-19.md`
> - `SPARKLE_AURORA_STAGE4_RETROACTIVE_AUDIT_2026-04-19.md`
> - `SPARKLE_AURORA_WSM_CUTOVER_RUNBOOK_2026-04-19.md`
> - `SPARKLE_DATA_UTILIZATION_ANALYSIS_2026-04-06.md`
> - `docs/01_核心模块文档/成就体系现状对齐.md`
> **Scope**: Stage 5 execution design. Defines the post-Stage-4 workstreams, user-value priorities, governance rules, hotspot ownership, and closeout gates.

### Revision History

| Version | Changes | Source |
| --- | --- | --- |
| v0 | First Stage 5 draft after Stage 4 closeout. Re-anchors the next stage on user-visible closure, inherits Rule G/H/I, and converts Claude + MIMO review into a dispatchable plan skeleton. | Codex |
| v1 | Absorb GLM-observer pre-review and Claude final-accept: split `Wave 1` into `Wave 1a / Wave 1b`, add deferred-breakpoint registry, quantify success criteria, and require the missing Stage 4 Rule I handoff artifact before `Gate S5-0`. | Codex |
| v2 | Record Stage 5 execution closeout: `WS-K1`, `WS-R1`, `WS-L1`, `WS-G1`, and `WS-S1` all landed under `Rule G`; `Gate S5-1` and `Gate S5-2` are satisfied on the current branch tip and the stage is ready for external review. | Codex |

---

## 0. Stage 5 Positioning

Stage 4 built the harness.

Stage 5 must prove that the harness can now carry **real user-value signals** instead of only architecture-ready seams.

### One-sentence definition

**Stage 5 is the stage where Aurora starts consuming and returning growth-relevant signals in a way users can actually feel, not just in a way the architecture can theoretically support.**

### What Stage 4 already solved

- `P1-P5` constitutional discipline is now code-verifiable
- the three-way routing seam exists and is tested
- TaskGuidance dual-audience output exists
- dormant task assistant context injection exists
- `WS-M Phase 1` has a runbook, shadow/active split, and rollback posture

### What Stage 4 did **not** solve

Per the anchor-list and MIMO closeout readout, Stage 4 still left the following user-value gaps largely open:

1. intervention language has not yet been elevated to a stage-level execution target
2. `adaptive_replanner -> execution / next-step` closure is still weak
3. `error / mastery / growth` signals are not yet a stable, audited control path for Aurora
4. there is still no robust end-to-end `adopt -> act -> feedback` loop

### Stage 5 strategic test

At the end of Stage 5, we should be able to say:

- Aurora does not merely route correctly
- Aurora now sees more of the user's real friction and progress
- Aurora now responds in a way that better matches the "friend + growth system" anchor
- at least one user-visible closure path has moved from "prepared" to "working"

---

## 1. Stage 5 Principles

### Principle A: User-Value First

No Stage 5 workstream may justify itself as "good infrastructure" alone.

Every workstream must explicitly name:

- which breakpoint it closes or advances
- which anchor-layer outcome it supports
- what concrete user-visible change should exist if it succeeds

### Principle B: Read Before Write

Stage 5 is primarily a **signal plumbing** and **control-surface** stage.

The default pattern is:

- read existing signals
- compress them into stable context fragments
- surface them into Aurora-visible decisions
- avoid new schema or product-surface sprawl unless explicitly approved

### Principle C: Governance Carries Forward

Stage 4's post-incident governance remains in force:

- `Rule G`
- `Rule H`
- `Rule I`

Stage 5 does not relax those rules just because Stage 4 is complete.

### Principle D: No Pretend Progress

Shadow expansion, prompt telemetry, and new samplers are valuable only if they support a visible closure path in the same stage.

Stage 5 should not become a second "beautiful substrate" stage.

---

## 2. Explicitly Out of Scope

The following are not part of Stage 5 unless a later amendment says otherwise:

1. real-user cohort activation expansion for `WS-M`
2. orchestrator FSM rewrites
3. Gate 0 schema amendments
4. new external-AI primary paths
5. new mobile product surfaces outside existing chat / task / plan containers
6. achievement-system write-path refactors
7. retroactive redesign of Stage 4 workstreams

---

## 3. Workstream Overview

| Workstream | Focus | Breakpoint Advanced | Anchor Signal | Priority |
| --- | --- | --- | --- | --- |
| `WS-K1` | learning-state fragment from error + mastery evidence | `错题 / 错误 -> mastery / profile` | `A1`, `A4` | highest |
| `WS-L1` | intervention-language contract and prompt-facing response policy | `干预交付方式和语言体系` | `A2`, `A5` | highest |
| `WS-R1` | adaptive replanner closure into next-step execution context | `adaptive_replanner -> 计划执行` | `A3`, `A4` | highest |
| `WS-G1` | achievement-to-Aurora growth signal uplink | growth signals into adaptive control | `A2`, `A4`, `A5` | medium |
| `WS-S1` | shadow expansion and Phase 2/3 hook preparation | future `WS-M` control readiness | `A3` | medium |

### Draft judgment baked into this plan

This draft makes four concrete calls rather than leaving them open:

1. `WS-S1` is **not** allowed to dominate Stage 5. It is a support workstream, not the stage's headline.
2. Stage 5 target for shadow corpus is `>=50`, not `>=100`. The `>=100` bar becomes a later activation gate.
3. achievement signals stay **read-only** in Stage 5. Aurora may consume them; it may not start writing or steering achievement state.
4. `prompt dead data repair` is treated as partially improved already. Stage 5 focuses on **stabilization, testing, budget discipline, and remaining leaks**, not on pretending the repo is still at the April 6 baseline.

---

## 4. Dispatch Rules

Stage 5 inherits the Stage 4 rules and adds one new one.

### Rule G · Single-WS-per-Agent Commit Discipline

A single agent commit must not touch more than one workstream's primary write zone unless the dispatcher explicitly approves a cross-WS batch.

### Rule H · Agent Allowlist + Escalation Contract

Every task card must include:

- exact writable file allowlist
- `out-of-allowlist -> stop and report`
- no self-selected secondary edits

### Rule I · Mandatory Handoff Artifact

Required at:

- stage close
- executor-role change
- any WS that lands after external reviewer findings

### Rule J · User-Value Closure Requirement

Every Stage 5 task card must declare:

1. the breakpoint it moves
2. the A-signal it is intended to improve
3. the user-visible proof expected at accept time

If a workstream cannot name those three things, it does not belong in Stage 5.

---

## 5. Review Lanes

High-risk lane:

`GLM-exec -> Codex initial review -> GLM-observer pre-accept -> Claude final-accept -> User sign-off`

Low-risk lane:

`GLM-exec -> Codex initial review -> User spot-check / sign-off`

### Stage 5 high-risk triggers

Any work touching one of the following is automatically high-risk:

1. `backend/app/orchestration/prompts.py`
2. `backend/app/orchestration/situation_brief.py`
3. `backend/app/orchestration/adaptive_replanner.py`
4. `backend/app/services/task_event_consumer.py`
5. `backend/app/aurora/migration.py`
6. `backend/app/aurora/observability/`
7. any growth-signal contract model consumed by Aurora
8. any feature-flag default
9. any file already classified as a Stage 4 seam anchor

---

## 6. Hotspot Ownership

| File / Zone | Owner | Reason |
| --- | --- | --- |
| `backend/app/orchestration/prompts.py` | `WS-L1` | intervention-language policy and final prompt phrasing |
| `backend/app/orchestration/situation_brief.py` | `WS-K1` | learning-state compression and evidence merge |
| `backend/app/orchestration/adaptive_replanner.py` | `WS-R1` | replanner execution closure |
| `backend/app/services/task_event_consumer.py` | `WS-R1` | task-completion bridge into replanner |
| `backend/app/orchestration/signal_samplers/` | `WS-G1` | growth signal uplink modules |
| `backend/app/aurora/migration.py` | `WS-S1` | Phase 2/3 shadow-only hook preparation |
| `docs/product/*STAGE5*` | `Codex` | integration and governance closeout |

### Shared-file rule

If one workstream needs information from a hotspot owned by another:

- it requests a seam extraction
- it does not edit the hotspot directly

---

## 7. Workstream Cards

## 7.1 `WS-K1` — Learning State Fragment

**Goal**

Turn existing `error_summary`, `recent_errors`, and `recent_mastery_changes` into a stable, compact, test-backed learning-state fragment that Aurora can rely on as a first-class input.

**Why this exists**

The repo now contains partial signal rendering in `prompts.py` and `situation_brief.py`, but Stage 5 still needs one bounded unit that:

- treats pain points and wins as one coherent learning-state object
- enforces token caps and fallback behavior
- proves the signal path with tests instead of incidental prompt drift

**Primary write zone**

- `backend/app/orchestration/situation_brief.py`
- `backend/app/orchestration/learning_state_fragment.py` (new)
- tests under `backend/tests/orchestration/` or `backend/tests/aurora/`

**Hard non-goals**

- no new DB tables
- no prompt-style rewriting here
- no intervention-language policy here

**Accept conditions**

1. one compact fragment exposes:
   - recent pain points
   - recent wins
   - bounded token size
2. cold-start and empty-signal fallback are defined
3. regression tests prove the fragment remains present for representative payloads
4. the fragment can be consumed by `WS-L1` without reopening its internals

**User-visible proof**

Aurora should be more reliably able to reference both recent struggle and recent progress instead of speaking from generic memory only.

---

## 7.2 `WS-L1` — Intervention Language Contract

**Goal**

Codify how Sparkle should speak when it uses the stronger learning-state signals: not judgmental, not shaming, and not fake-soft. This workstream turns anchor §3.3 into an execution-facing prompt contract.

**Why this exists**

MIMO is right that "data seen by Aurora" is not enough. If the language layer still fails, users will feel pressure instead of support.

**Primary write zone**

- `backend/app/orchestration/prompts.py`
- `backend/tests/orchestration/` prompt-policy tests
- docs artifact:
  - `docs/product/SPARKLE_AURORA_STAGE5_INTERVENTION_LANGUAGE_CONTRACT_2026-04-19.md`

**Depends on**

- `WS-K1` learning-state fragment

**Dispatch dependency**

`WS-L1` must be dispatched only after `WS-K1` is accepted.

It may not start from a stub or mock fragment, because the intervention-language contract has to be written against the real semantics of the learning-state signal rather than a placeholder interface.

**Hard non-goals**

- no chat-mode redesign
- no new mobile screen
- no emotional-state overreach beyond signed anchor boundaries

**Accept conditions**

1. prompt-facing contract explicitly encodes:
   - no shame
   - no moral judgment
   - side-with-user stance
   - restart / curiosity bias
2. tests cover at least:
   - recent failure evidence
   - recent mastery evidence
   - mixed pain + progress evidence
3. policy text is tied to anchor §3.3 and not phrased as generic "be supportive"
4. the result remains within prompt budget discipline

**User-visible proof**

When the system references struggle or growth, it should feel more like "a friend helping me restart" and less like "a system diagnosing me."

---

## 7.3 `WS-R1` — Adaptive Replanner Closure

**Goal**

Move `adaptive_replanner` from a mostly background capability into a visible next-step loop that can affect what Sparkle suggests after task completion or execution feedback.

**Why this exists**

This is the most direct path from Stage 4 harness to a real `adopt -> act -> feedback` loop.

**Primary write zone**

- `backend/app/orchestration/adaptive_replanner.py`
- `backend/app/services/task_event_consumer.py`
- read-only consumption in existing task / plan follow-up context builders if needed

**Hard non-goals**

- no new schema
- no plan-engine rewrite
- no Stage 6 takeover logic

**Accept conditions**

1. task completion or equivalent execution events can trigger replanner output
2. replanner output is surfaced into an existing next-step context path
3. regression tests prove the loop:
   - event received
   - replanner invoked
   - updated next-step payload produced
4. fallback behavior exists when no useful replanner delta is found

**User-visible proof**

After doing something, the user should be more likely to receive a next action or adjustment that actually reflects what just happened.

---

## 7.4 `WS-G1` — Growth Signal Uplink

**Goal**

Create a one-way contract from achievement signals into Aurora-readable growth state without letting Aurora start mutating achievement logic.

**Why this exists**

The current repo has a rich achievement system and user-facing growth evidence, but the signal path into Aurora remains weak and structurally risky if done ad hoc.

**Primary write zone**

- `backend/app/orchestration/signal_samplers/achievement_sampler.py` (new)
- `backend/app/aurora/growth_signal_contract.py` (new)
- docs artifact:
  - `docs/product/SPARKLE_AURORA_GROWTH_SIGNAL_CONTRACT_2026-04-19.md`

**Hard non-goals**

- no writes into achievement tables
- no achievement-engine API redesign
- no reverse imports from achievement UI into Aurora

**Accept conditions**

1. sampler is read-only
2. output contract is bounded and serializable
3. static review can show no forbidden reverse dependency
4. empty-state / cold-start behavior is explicit

**User-visible proof**

Aurora should begin to recognize growth momentum or stagnation with more continuity, even before any larger growth-system redesign lands.

---

## 7.5 `WS-S1` — Shadow Expansion and Phase 2/3 Hook Preparation

**Goal**

Prepare the next `WS-M` control points without letting Stage 5 collapse into a pure infrastructure stage.

**Why this exists**

We still need deeper shadow coverage, but Stage 5 should cap this work at "prepared and measured," not "become the whole stage."

**Primary write zone**

- `backend/app/aurora/migration.py`
- `backend/app/aurora/observability/`
- `backend/tests/aurora/fixtures/shadow_corpus/`
- runbook docs

**Hard non-goals**

- no active rollout widening
- no Phase 2/3 activation
- no `>=100` corpus requirement inside this stage

**Accept conditions**

1. corpus expands to `>=50`
2. Phase 2 and Phase 3 hooks exist as shadow-only, flag-gated preparation
3. observability captures divergence cleanly
4. a Stage 5 shadow report is written

**User-visible proof**

Indirect only. This workstream is accepted as a support lane because it enables safer future control-surface growth, not because it by itself closes a user-value loop.

---

## 8. Wave Plan

| Wave | Parallel Agents | Scope | Intent |
| --- | --- | --- | --- |
| `Wave 1a` | `2` | `WS-K1`, `WS-R1` | build the real signal fragment and the execution-side loop in parallel |
| `Wave 1b` | `1` | `WS-L1` | write the intervention-language contract against the accepted `WS-K1` fragment |
| `Wave 2` | `2` | `WS-G1`, `WS-S1` | add growth signals and prepare next control surfaces |
| `Wave 3` | `1` | integration, review findings, closeout docs | consolidate and freeze |

### Why this order

This order is deliberate:

- first close what the user can feel
- first use real signal semantics, not mock semantics
- then expand what Aurora can sense
- only then spend more budget on future shadow depth

---

## 9. Gates

### Gate `S5-0` — Design Sign-Off

Required before execution:

- `SPARKLE_AURORA_STAGE4_HANDOFF_2026-04-20.md` is landed as the missing Rule I closeout artifact for Stage 4
- user signs this draft or its amended successor
- `GLM-observer` pre-review completed
- Claude final design review completed

### Gate `S5-1` — User-Value Loop Baseline

Required after `Wave 1a` and `Wave 1b`:

1. learning-state fragment is present and tested
2. intervention-language contract is landed
3. adaptive replanner produces a visible next-step delta path
4. at least one first-tier breakpoint is demonstrably advanced

### Gate `S5-2` — Signal Uplink and Shadow Prep

Required after `Wave 2`:

1. growth signal contract is landed
2. shadow corpus reaches `>=50`
3. Phase 2/3 hooks remain shadow-only and default-safe

### Gate `S5-Close` — Stage 5 Closeout

Required to call Stage 5 complete:

1. all Stage 5 workstreams accepted
2. Rule G/H/I/J remained intact
3. no frozen-schema or constitutional drift occurred
4. closeout docs record:
   - what user-value loop moved
   - what remained unresolved
   - what becomes Stage 6 input

---

## 10. Success Criteria

Stage 5 should only be called a success if all of the following are true:

1. **7-phase progression** advances from the current `1 / 7` baseline to at least `3 / 7`.
   - Minimum intended movement:
   - `Execute -> Reflect`
   - `Reflect -> Adapt`
2. **Breakpoint coverage** moves at least `3` items from "unrepaired" to "visibly advanced".
   - Required public count includes:
   - `#1 adaptive_replanner -> execution`
   - `#2 error / mastery -> profile`
   - intervention language system
3. **Data-utilization ratio** shows at least one measurable improvement across the four-layer chain.
   - The closeout artifact must publish at least one concrete before/after number.
4. **Dual-core cooperation** advances from the current `0.3 / 1` baseline to at least `0.6 / 1`.
   - Minimum proof:
   - at least one end-to-end `cognitive discovery -> execution adjustment -> outcome feedback` path
5. **P1-P5 constitutional posture** remains all green with no newly introduced violation.
6. **Test baseline** remains green for all touched Stage 5 surfaces.

### What does **not** count as success

- more telemetry but no stronger user loop
- more shadow hooks but no clearer output behavior
- more documents but no tighter contract around intervention language

---

## 11. Deferred Breakpoints

Stage 5 does not try to solve every known breakpoint. The following registry makes the deferrals explicit:

| Breakpoint | Stage 5 handling | Suggested next home |
| --- | --- | --- |
| `#1 adaptive_replanner -> execution` | **in Stage 5** via `WS-R1` | first-tier |
| `#2 error / mastery -> profile` | **in Stage 5** via `WS-K1` | first-tier |
| intervention language system | **in Stage 5** via `WS-L1` | first-tier |
| `#3 plan health no event` | deferred | Stage 6 |
| `#4 push time-only` | deferred | Stage 6 or dedicated behavior-trigger stage |
| `#5 cognitive_adjustments text-only` | deferred | Stage 6 |
| `#6 intervention verification / feedback return` | deferred | Stage 6, after Stage 5 establishes the first one-way closure paths |

---

## 12. Draft Entry Conditions for Stage 6

If Stage 5 succeeds, Stage 6 should inherit:

- a tighter intervention contract
- a stronger `act -> feedback -> next-step` bridge
- read-only growth signals inside Aurora
- broader but still safe shadow coverage

Stage 6 should **not** have to reopen:

- whether Stage 5 was user-value oriented
- whether achievement signals are one-way
- whether prompt/control work can ignore intervention language

---

## 13. Immediate Recommended Next Step

If this draft direction is accepted, the next moves should be:

1. expert review on this dispatch plan draft
2. amend if needed
3. land the signed Stage 5 dispatch plan
4. dispatch `Wave 1a` first:
   - `WS-K1`
   - `WS-R1`
5. dispatch `Wave 1b` only after `WS-K1` is accepted:
   - `WS-L1`

Only after `Gate S5-1` should `WS-G1` and `WS-S1` be dispatched.

---

## 14. Closeout Addendum

Stage 5 execution is now landed on the current branch tip.

### Final landed workstreams

| Workstream | Final status | Landing commit |
| --- | --- | --- |
| `WS-K1` | **accept** | `b3afd12e` |
| `WS-R1` | **accept** | `d7fa7b9a` |
| `WS-L1` | **accept** | `6c375fcb` |
| `WS-G1` | **accept** | `e190195b` |
| `WS-S1` | **accept** | `f33e72ec` |

### Gate status on branch tip

- `Gate S5-0`: satisfied
- `Gate S5-1`: satisfied
- `Gate S5-2`: satisfied
- `Gate S5-Close`: ready for external review / final sign-off

### Closeout note

Stage 5 should now be treated as an execution-complete stage pending expert review, not as an open design draft.
