# Sparkle Codex Alignment and Handoff

> Date: 2026-04-07  
> Status: Active handoff document for the next Codex thread  
> Audience: Founder, next Codex run, product, engineering  
> Priority: High  
> Companion docs:
> - `docs/product/SPARKLE_PRODUCT_THESIS_AND_REFOCUSED_ROADMAP_2026-04-05.md`
> - `docs/product/SPARKLE_STAGE2_PRODUCT_COHERENCE_AND_LIVE_ALPHA_PLAN_2026-04-06.md`
> - `docs/product/implementation/SPARKLE_STAGE2_PRODUCT_COHERENCE_EXECUTION_PLAN_2026-04-06.md`
> - `docs/product/implementation/SPARKLE_STAGE2_PROFILE_AND_INSIGHT_SYSTEM_EXECUTION_PLAN_2026-04-06.md`
> - `docs/product/implementation/SPARKLE_AI_SYSTEM_SEMANTIC_CONTROL_EXECUTION_PLAN_2026-04-06.md`
> - `docs/product/SPARKLE_DATA_UTILIZATION_ANALYSIS_2026-04-06.md`
> - `README.md`
> - `README_EN.md`

---

## 0. Why This Document Exists

The project has gone through several dense design and implementation phases, and the shared context is now too large to reliably re-derive from memory inside a fresh Codex thread.

This document is the transfer artifact.

Its job is to preserve:

1. the current product consensus
2. the current technical consensus
3. what is frozen and should not drift
4. what is still open and not yet proven
5. what the next Codex should treat as the real priority

This document is intentionally opinionated.

It should help the next Codex avoid:

- restarting old architecture debates
- mistaking internal completion for product truth
- over-trusting synthetic evaluation harnesses
- drifting away from the real product wedge

---

## 1. Non-Negotiable Product Consensus

### 1.1 What Sparkle Is

Sparkle is **not primarily**:

- a chatbot
- a generic AI assistant
- a showcase of many agents
- a bag of features

Sparkle is:

> **an AI-native planning and guidance operating system for ordinary users who cannot manually extract the best results from frontier AI on their own**

Operationally:

> **Sparkle helps users understand how to achieve important goals, then gives them better plans, better next moves, and better ongoing guidance than raw AI use alone.**

### 1.2 Why We Say “System,” Not “Assistant” or “Agent”

The founder’s current philosophical position is important and should be preserved:

- an `assistant` helps with a turn
- an `agent` helps with a task
- a `system` helps with the whole loop

Sparkle is a `system` because it is intended to:

1. gather and organize user information
2. identify what is still missing
3. produce the plan
4. adapt after outcomes and feedback
5. preserve continuity over time
6. let the user inspect and correct how the system understands them

This is why Sparkle should be pitched as a **goal-achievement system**, not just an assistant.

### 1.3 The Two True Moats

Everything important in Sparkle must strengthen one of these two moats:

1. `User Understanding Quality`
   Sparkle should surface things the user cannot easily see alone, in a way the user recognizes as true.

2. `Plan Quality`
   Sparkle should produce a better plan, better pacing, better next move, and better adaptation path than a non-expert user would usually get from raw AI prompting.

If a subsystem does not improve one of these two moats, it is secondary.

### 1.4 The Four External Product Modes

These are the best external-facing product modes and should be preserved for deck, README, and demo consistency:

1. `Understand`
2. `Plan`
3. `Adapt`
4. `Grow`

Internally the system has many more modes and policies, but externally these four are the cleanest product story.

### 1.5 The North-Star Scenario

The main scenario remains:

> **Thermodynamics final exam in 14 days**

The user has:

- real deadline pressure
- personal materials
- prior mistakes
- incomplete self-understanding
- overload risk

Sparkle must:

- understand the user’s real state
- detect missing planning-critical information
- build the plan
- adapt visibly after overload or failure
- preserve continuity and trust

This scenario should remain the primary reference path unless leadership explicitly changes it.

---

## 2. Where the Project Is Now

### 2.1 What Is Real

Sparkle now has a serious core operating substrate:

- compiled understanding state
- planning readiness and plan-quality control
- feedback binding and validated learning
- body-awareness and capability governance
- five-layer learning and drift-aware governance
- semantic AI control
- transparent profile and user correction surfaces
- internal benchmark and evaluation harnesses

This means Sparkle is no longer a vague architecture project.

### 2.2 What Is Also True

Sparkle is **not yet fully proven as a product** in the way that matters most.

Specifically:

- full-stack runnable coherence is still more important than more architecture
- the real mobile experience is not yet the main truth source
- several evaluators are still stronger as regression harnesses than as final product truth
- human evaluation exists as process and tooling, but not yet as the main roadmap driver
- the product is richer internally than it is externally proven

### 2.3 Bottom-Line Status

The current bottom-line status is:

> **Architecture-complete enough to stop inventing major new foundation layers**  
> **Product-incomplete enough that the next chapter must focus on runnable coherence, live truth, and human judgment**

---

## 3. What Has Been Built and Frozen

### 3.1 Five-Phase Core

The major implementation phases have been completed and treated as `v1`:

- Phase A: User Insight Engine
- Phase B: Planning Engine
- Phase C: Feedback and Growth Engine
- Phase D: Body Awareness and Capability Governance
- Phase E: Five-Layer Learning System

This does **not** mean they are final product proof.
It means their core architecture should not be casually redesigned.

### 3.2 AI Semantic-Control Layer

The AI semantic-control layer has been sealed and can now be treated as `v1 frozen`:

- ontology
- renderer
- prompt integration
- compliance checks
- trace metadata

Important boundary:

- `architecture`: frozen
- `live product proof`: not frozen

Only reopen this area if real product runs or transcript review show repeated doctrine-compliance failures.

### 3.3 User Profile and Insight System

The profile and insight system has been materially upgraded and can be treated as `v1 frozen`:

- canonical `UserInsightState`
- signal registry and compiler
- multi-span analysis
- bounded prediction
- calibration and anti-drift
- transparency and user control
- cache invalidation expanded to Stage 2 signal families

Important boundary:

- `architecture and runtime integrity`: frozen
- `market-level proof that Sparkle understands users best`: not frozen

Only reopen this area if live Stage 2 product runs or human review show repeated understanding misses.

### 3.4 README / Public Product Story

The public repo-facing story has been updated and is now aligned:

- `README.md`
- `README_EN.md`
- `README_CN.md` kept as a stable alias to avoid Chinese homepage drift

These files now reflect:

- the product thesis
- the two moats
- the four modes
- the data-utilization loop
- the current Stage 2 status

These README files are now presentation-grade and should be preserved as the default public explanation unless leadership intentionally changes the product story.

---

## 4. What Is Still Not Final Truth

The next Codex must **not** confuse these with final proof:

### 4.1 Planning Benchmark

The planning benchmark is useful and real, but still a controlled harness.

It is good for:

- regression
- comparison
- iteration

It is **not** the final proof that Sparkle beats raw AI in live product conditions.

### 4.2 Phase C Outcome Evaluator

`plan_outcome_evaluator.py` is still a regression harness, not final product truth.

It scores structured scenario payloads rather than purely live runtime artifacts.

Treat it as iteration infrastructure, not final evidence.

### 4.3 Phase E Five-Layer Evaluator

`five_layer_learning_evaluator.py` is also still a regression harness, not final live proof.

It is useful for deterministic scenario comparison, but not for claiming that five-layer learning is already proven in the real product.

### 4.4 Human Evaluation

Human evaluation is strategically central, but not yet fully operationalized as the main roadmap truth source.

This remains one of the largest gaps between internal completion and real product proof.

---

## 5. The True Stage 2 Priority

The next chapter is **not** “Phase F architecture.”

The next chapter is:

> **Product Coherence and Live Alpha Truth**

The real strategic question is no longer:

> Can Sparkle be architected?

It is now:

> Can Sparkle boot, run, feel coherent, help a real user deeply, and prove it?

### 5.1 Stage 2 Workstreams

The priority order remains:

1. `Runnable Golden Path`
2. `Full-Stack North-Star Coherence`
3. `Product Failure Inventory`
4. `Core-Loop Repair Pass`
5. `Visible Adaptation UX Reality Pass`
6. `First Human Evaluation Cycle`
7. `Product Simplification and Prioritization`
8. `Live Alpha Gate Review`

### 5.2 The Main Strategic Principle

Every meaningful change should answer:

> **Does this make Sparkle better at understanding the user, planning for the user, or improving through real feedback?**

If the answer is no, it is not a Stage 2 priority.

---

## 6. Immediate Practical Context

### 6.1 The Founder’s Current Practical Need

There is an immediate presentation and demonstration context:

- a BP / pitch presentation is near-term
- README and product story have been updated to support that presentation
- a short, high-signal story is now more important than showing every subsystem

### 6.2 Current Pitch Consensus

The best one-sentence introduction is:

> **Sparkle helps ordinary users achieve important goals by deeply understanding them and turning their own data into better plans and adaptive guidance than raw AI alone.**

The best technical summary is:

> **We built a governed intelligence stack: a user insight engine, a readiness-gated planning engine, and a feedback-driven growth engine, all coordinated by a semantic AI control layer.**

### 6.3 What to Emphasize in External Communication

For judges, investors, or first-time viewers:

- sell `coherence`, not `complexity`
- sell the `problem`, not the module count
- sell the `north-star loop`, not every subsystem

The best three-module explanation is:

1. `Understanding Engine`
2. `Planning Engine`
3. `Growth Engine`

With one support line:

> an AI semantic-control layer helps the model actually follow system intent instead of guessing what internal tags mean

---

## 7. What the Next Codex Should Not Drift On

The next Codex should preserve these rules:

### 7.1 Do Not Reopen Frozen Core Architecture Casually

Do not casually redesign:

- the user insight architecture
- the AI semantic-control architecture
- the Phase A-E system decomposition

Only reopen frozen areas if real product evidence forces it.

### 7.2 Do Not Over-Trust Internal Evaluators

Do not present synthetic or controlled harnesses as final proof.

Use them for:

- regression
- comparison
- iteration

But keep final truth tied to:

- full-stack runs
- real app behavior
- transcript review
- human evaluation

### 7.3 Do Not Optimize for Internal Cleverness

Avoid:

- architecture theater
- more agents without clear user benefit
- score inflation
- more hidden complexity that users cannot feel

### 7.4 Keep the Product Wedge Sharp

The wedge is not:

- “be the most agentic”
- “have the most tools”
- “do everything”

The wedge is:

> **understand the user deeply, then turn that understanding plus their data into the best plan**

---

## 8. Canonical Documents the Next Codex Should Trust First

If a fresh Codex thread needs orientation, these are the first files it should read:

1. `README.md`
2. `docs/product/SPARKLE_PRODUCT_THESIS_AND_REFOCUSED_ROADMAP_2026-04-05.md`
3. `docs/product/SPARKLE_STAGE2_PRODUCT_COHERENCE_AND_LIVE_ALPHA_PLAN_2026-04-06.md`
4. `docs/product/implementation/SPARKLE_STAGE2_PRODUCT_COHERENCE_EXECUTION_PLAN_2026-04-06.md`
5. `docs/product/implementation/SPARKLE_STAGE2_PROFILE_AND_INSIGHT_SYSTEM_EXECUTION_PLAN_2026-04-06.md`
6. `docs/product/implementation/SPARKLE_AI_SYSTEM_SEMANTIC_CONTROL_EXECUTION_PLAN_2026-04-06.md`
7. `docs/product/SPARKLE_DATA_UTILIZATION_ANALYSIS_2026-04-06.md`
8. this handoff document

Only then should it dive into lower-level verification or archived design history.

---

## 9. Recommended Working Posture for the Next Codex

When taking over, the next Codex should work with this hierarchy:

### 9.1 First Truth Source

- the real product path
- the real app
- the real user experience

### 9.2 Second Truth Source

- current active product docs
- current README story
- current Stage 2 plan

### 9.3 Third Truth Source

- benchmarks
- regression harnesses
- contract freeze docs

### 9.4 Last Resort

- deep historical docs
- archived alignment reports
- old architecture narratives that predate the current product wedge

---

## 10. The Most Important Current Question

If the next Codex only remembers one thing, it should remember this:

> **The main challenge is no longer building more architecture. The main challenge is turning Sparkle into a coherent, runnable, judgeable product that real users can feel is better than raw AI alone.**

That is the center of gravity now.

---

## 11. Final Handoff Summary

Sparkle now has:

- a real understanding engine
- a real planning engine
- a real feedback and growth engine
- a sealed semantic-control layer
- a frozen v1 insight/profile system
- a public README story aligned with the real product thesis

Sparkle does **not** yet have:

- final live proof
- human-evaluation-centered truth
- full confidence that the whole app runs coherently end to end

Therefore the next Codex should operate with this final summary:

> **Preserve the frozen intelligence architecture. Focus on Stage 2 product coherence. Judge progress by real product behavior, not internal cleverness.**

