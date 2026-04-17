# Sparkle Stage 2 Product Coherence Execution Plan

> Date: 2026-04-06  
> Status: Active implementation plan  
> Audience: Founder, chief designer, implementation Codex runs, backend, mobile, evaluation  
> Companion docs:
> - `docs/product/SPARKLE_STAGE2_PRODUCT_COHERENCE_AND_LIVE_ALPHA_PLAN_2026-04-06.md`
> - `docs/product/SPARKLE_LIVE_ALPHA_GATE_2026-04-04.md`
> - `docs/product/SPARKLE_PRODUCT_THESIS_AND_REFOCUSED_ROADMAP_2026-04-05.md`
> - `docs/product/SPARKLE_THREE_SYSTEM_IMPROVEMENT_PLAN_2026-04-05.md`
> - `docs/product/evaluation/SPARKLE_NORTH_STAR_HUMAN_EVALUATION_PROTOCOL_2026-04-04.md`
> - `docs/product/evaluation/SPARKLE_PHASE_C_HUMAN_EVAL_OPS_LOOP_2026-04-05.md`
> - `docs/product/implementation/SPARKLE_S2_0_RUNNABLE_GOLDEN_PATH_BRING_UP_2026-04-06.md`

---

## 0. Why This Plan Exists

Stage 2 is the chapter after architecture freeze.

Phases A through E gave Sparkle:

- a user insight engine
- a planning engine
- a feedback and growth engine
- first body-awareness
- first five-layer learning governance

That work is important and should remain largely frozen unless real evidence forces a return.

The current problem is different:

> **Sparkle still needs to become a runnable, coherent, judgeable product.**

This plan defines exactly how to do that without drifting back into endless internal architecture work.

---

## 1. Stage 2 Goal

The goal of Stage 2 is:

> **Reach a truthful Live Alpha by proving one real full-stack Sparkle loop works, feels coherent, and is judged helpful by humans.**

This requires four things to become true together:

1. the system boots and runs on a real device/emulator path
2. the north-star loop works through the real product stack
3. adaptation is visible and calm in the UI
4. human evaluation becomes a real operating loop

---

## 2. The Main Rule

From this point forward, Stage 2 work must obey one rule:

> **Do not add new major architecture unless a real product failure proves it is necessary.**

That means:

- prefer full-stack debugging over new abstraction
- prefer product simplification over adding more systems
- prefer transcript review over argument by theory
- prefer one working north-star journey over many partially wired experiences

---

## 3. What Counts as Success

Stage 2 is successful when all of these are true:

1. you can reliably launch the real product locally
2. you can run the 14-day exam journey on the actual app
3. Sparkle asks good clarifying questions when needed
4. Sparkle produces grounded plans on the real path
5. Sparkle shows visible adaptation after feedback
6. continuity works across at least one later session
7. a human evaluator can review the transcript and produce actionable findings
8. those findings change implementation priorities

If any of those is missing, Stage 2 is not complete.

---

## 4. Execution Order

The Stage 2 execution order is:

1. `S2-0 Runnable Golden Path Bring-Up`
2. `S2-1 Full-Stack North-Star Smoke`
3. `S2-2 Product Failure Inventory`
4. `S2-3 Core-Loop Repair Pass`
5. `S2-4 Visible Adaptation UX Reality Pass`
6. `S2-5 First Human Evaluation Cycle`
7. `S2-6 Product Simplification and Prioritization`
8. `S2-7 Live Alpha Gate Review`

This order is mandatory.

Do not skip ahead to human evaluation before the product is runnable.
Do not broaden features before the core loop is stable.
Do not declare Live Alpha from evaluator scores alone.

---

## 5. Stage Breakdown

## 5.1 Stage S2-0: Runnable Golden Path Bring-Up

### Purpose

Build one repeatable local path that starts the real system and opens the real product.

### Why This Comes First

Right now, too much product judgment is still inferred from code and harnesses.

That must stop.

### Deliverables

- one bring-up checklist covering:
  - infra
  - backend
  - gateway
  - mobile
  - emulator/simulator
- one chosen golden-path target
  - either one iOS simulator path or one Android emulator path
- one “known blockers” sheet for startup and auth/session/chat issues
- one smoke walkthrough from app open to first Sparkle response

### Required Scope

- real environment variables
- real startup commands
- real app boot
- real chat entry path
- real logging/inspection steps

### Acceptance Criteria

- a new Codex can follow the checklist without hidden tribal knowledge
- the app launches
- user can enter the main chat/product loop
- Sparkle produces at least one real response in the UI
- startup failures are explicit and reproducible

### Non-Goals

- perfect deployment documentation
- multi-platform parity
- full production hardening

### Codex Packs

- `S2-0A`: environment and startup audit
- `S2-0B`: golden-path bring-up checklist
- `S2-0C`: emulator/simulator smoke validation
- `S2-0D`: startup blocker fixes

### Exit Rule

Do not move to S2-1 until the product can be launched and the main chat loop can be entered on one real device target.

---

## 5.2 Stage S2-1: Full-Stack North-Star Smoke

### Purpose

Run one real north-star flow through the actual product stack.

### Target Scenario

The thermodynamics-in-14-days journey:

- cold start
- user uploads or references study materials
- Sparkle clarifies missing information when needed
- Sparkle produces a real study plan
- user expresses overload or confusion
- Sparkle adapts

### Deliverables

- one scripted founder walkthrough
- one transcript capture
- one screenshot or UI-state capture set
- one artifact showing:
  - initial user input
  - Sparkle clarification or plan
  - grounded evidence use
  - adaptation after feedback

### Acceptance Criteria

- the journey runs through the real primary app path
- Sparkle asks when readiness is insufficient
- Sparkle plans when readiness is sufficient
- Sparkle uses grounding when user materials matter
- Sparkle visibly adapts when the user reports trouble
- at least one later-turn continuity element appears in the product

### Non-Goals

- full domain coverage
- proving every residual class before the main loop is alive

### Codex Packs

- `S2-1A`: north-star walkthrough setup
- `S2-1B`: capture and inspect the first full-stack journey
- `S2-1C`: document observed breakpoints

### Exit Rule

Do not move to S2-2 until one north-star flow has run end to end on the app, even if it is imperfect.

---

## 5.3 Stage S2-2: Product Failure Inventory

### Purpose

Translate the first real run into a product failure map.

### Why This Matters

The next fixes must come from reality, not imagination.

### Deliverables

- one prioritized failure inventory grouped by:
  - startup and routing
  - user understanding failures
  - planning failures
  - grounding failures
  - adaptation invisibility
  - continuity failures
  - UI/comprehension failures
- one “core loop criticality” label for each item:
  - critical
  - important
  - later

### Acceptance Criteria

- each failure is tied to a real observed run
- critical items are only the ones that damage the main user loop
- secondary modules are not allowed to dominate the list

### Codex Packs

- `S2-2A`: transcript and screenshot review
- `S2-2B`: backend/runtime trace correlation
- `S2-2C`: prioritized failure inventory

### Exit Rule

Do not start broad repair work until the failure inventory is written and prioritized by core-loop impact.

---

## 5.4 Stage S2-3: Core-Loop Repair Pass

### Purpose

Fix the smallest set of issues necessary to make the real product loop feel coherent.

### Scope Rules

Only repair issues that directly improve:

- user understanding quality
- plan quality
- visible adaptation
- continuity
- grounded evidence use
- startup and runtime viability

Do not use this stage to reopen large architecture questions unless a real blocker demands it.

### Deliverables

- fixes for the top critical items from S2-2
- updated smoke path
- updated screenshots/transcript
- updated known-issues list with resolved vs unresolved items

### Acceptance Criteria

- the main loop no longer fails for obvious reasons
- Sparkle feels more coherent on the same north-star run
- no new major architectural sprawl is introduced

### Codex Packs

- `S2-3A`: understanding and readiness fixes
- `S2-3B`: plan and grounding fixes
- `S2-3C`: feedback/adaptation/continuity fixes
- `S2-3D`: re-run and compare

### Exit Rule

Do not move to UX polish until the repaired loop is visibly better on the same real walkthrough.

---

## 5.5 Stage S2-4: Visible Adaptation UX Reality Pass

### Purpose

Make the product’s intelligence legible and trustworthy in the real interface.

### Design Standard

Visible adaptation should feel:

- calm
- specific
- grounded
- reversible
- non-theatrical

### Focus Areas

#### Chat

- “I adjusted this because...”
- “Here’s what I noticed...”
- “We can change this again if it doesn’t help”
- grounded references to the user’s own materials or prior outcomes

#### Home

- what changed
- what matters now
- why this next move

### Deliverables

- one final wording system for adaptation cards/messages
- one reality pass on chat surfaces
- one reality pass on home/dashboard surfaces
- one before/after transcript example set

### Acceptance Criteria

- a user can point to one real adaptation Sparkle made
- adaptation is not hidden only in metadata
- wording feels helpful, not manipulative

### Codex Packs

- `S2-4A`: chat adaptation UX pass
- `S2-4B`: home/dashboard adaptation UX pass
- `S2-4C`: transcript-based wording cleanup

### Exit Rule

Do not move to human evaluation until a real observer can say, “I can see what Sparkle changed and why.”

---

## 5.6 Stage S2-5: First Human Evaluation Cycle

### Purpose

Turn human evaluation from a prepared protocol into a live product truth loop.

### Required Inputs

- runnable product
- north-star walkthrough path
- transcript capture
- adaptation surfaces visible enough to judge

### Deliverables

- at least one real human-evaluated north-star run
- one transcript review summary
- issue tags for:
  - wrong diagnosis
  - wrong clarification
  - weak plan
  - weak grounding
  - invisible adaptation
  - continuity failure
  - tone/trust failure
- one action memo mapping findings to implementation priorities

### Acceptance Criteria

- evaluation is real, not simulated
- findings are transcript-backed
- findings change what gets built next

### Codex Packs

- `S2-5A`: evaluator run support and transcript collection
- `S2-5B`: transcript normalization and issue tagging
- `S2-5C`: roadmap update from findings

### Exit Rule

Do not claim Stage 2 maturity until at least one real human evaluation cycle has happened and affected implementation priorities.

---

## 5.7 Stage S2-6: Product Simplification and Prioritization

### Purpose

Reduce system sprawl so Sparkle feels like one product.

### Why This Matters

You now have many sophisticated systems:

- OpenClaw
- Mirofish
- cards
- body-awareness
- five-layer learning
- Knowledge Galaxy
- achievements
- community
- ambient/visual systems

The risk is not lack of power.
The risk is diluted product identity.

### Deliverables

- one “core now” list
- one “supporting now” list
- one “defer now” list
- one simplified product-surface map for the first live slice

### Acceptance Criteria

- there is a clear answer to “what Sparkle is right now”
- core loop surfaces are obvious
- secondary systems no longer dominate the first user experience

### Codex Packs

- `S2-6A`: subsystem value audit against the two moats
- `S2-6B`: core/supporting/deferred decision memo
- `S2-6C`: product-surface simplification pass

### Exit Rule

Do not run final Live Alpha review until the team can clearly explain the current product without listing every subsystem.

---

## 5.8 Stage S2-7: Live Alpha Gate Review

### Purpose

Use the existing Live Alpha gate as the final truth test for Stage 2.

### Inputs

- runnable golden path
- repaired north-star flow
- visible adaptation pass
- at least one human evaluation cycle
- simplified product scope

### Deliverables

- one Live Alpha gate review memo
- gate status for:
  - core runtime health
  - live acceptance proof
  - visible adaptation UX
  - human evaluation operations
  - body awareness v1
- one “green / yellow / red” table
- one explicit answer:
  - `Live Alpha reached`
  - or `not yet`

### Acceptance Criteria

- the gate is judged honestly
- no synthetic harness is mistaken for final truth
- red or yellow categories produce the next focused roadmap

### Codex Packs

- `S2-7A`: Live Alpha evidence collection
- `S2-7B`: gate scoring and judgment memo

---

## 6. Cross-Stage Rules

These rules apply to all Stage 2 work.

### 6.1 Preserve the Frozen Architecture Unless Reality Forces Change

Do not reopen Phase A-E design casually.
Only revisit them if:

- the real product run exposes a repeatable failure
- human evaluation repeatedly shows the same weakness
- the frozen design clearly blocks the north-star loop

### 6.2 Always Prefer Real Product Evidence Over Synthetic Confidence

Hierarchy of truth:

1. real app behavior
2. real transcript review
3. human evaluation
4. orchestrator-backed acceptance
5. internal evaluators and scorecards

### 6.3 Keep the Product Thesis Visible

Every major decision should still answer:

- does this improve user understanding quality?
- does this improve plan quality?
- does this improve feedback-driven evolution?

### 6.4 Protect the User Experience From System Theater

Do not make Sparkle feel impressive by exposing too much internal machinery.
Expose only what helps the user:

- what changed
- why it changed
- what to do next

### 6.5 One Golden Path First

Do not try to validate many product loops at once.
The first job is one excellent, repeatable path.

---

## 7. What To Postpone During Stage 2

Postpone unless directly required by the core loop:

- new major subsystem creation
- broad domain expansion
- deeper autonomous execution layers
- richer ambient/visual complexity
- community expansion
- achievement expansion
- non-essential dashboard proliferation

This is sequencing discipline, not abandonment.

---

## 8. What the Next Codex Should Do First

The next Codex should start with:

### `Pack S2-0A: Environment and Startup Audit`

Its job:

- inspect current startup commands and dependencies
- identify the real full-stack path:
  - backend
  - gateway
  - mobile
  - device target
- produce the initial golden-path bring-up checklist
- attempt the first real startup
- document every blocker precisely

The first deliverable is not a redesign.

It is:

> **a working or nearly-working path to open the real Sparkle product and inspect it**

---

## 9. Final Stage 2 Principle

Stage 2 should be judged by one sentence:

> **Sparkle is becoming a real product only if a real user journey can run through the actual app, feel helpful, and generate human evidence that guides what we do next.**

That is the standard for every Codex run in this chapter.

