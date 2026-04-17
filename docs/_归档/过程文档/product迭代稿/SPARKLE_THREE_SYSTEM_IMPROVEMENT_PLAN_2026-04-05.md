# Sparkle Three-System Improvement Plan

> Date: 2026-04-05  
> Status: Active top-layer product and architecture plan  
> Audience: Founder, chief designer, implementation Codex runs, product, backend, mobile, evaluation  
> Companion docs:
> - `docs/product/SPARKLE_PRODUCT_THESIS_AND_REFOCUSED_ROADMAP_2026-04-05.md`
> - `docs/product/SPARKLE_NEXT_PHASE_MASTER_PLAN_2026-04-04.md`
> - `docs/product/SPARKLE_LIVE_ALPHA_GATE_2026-04-04.md`
> - `docs/product/SPARKLE_LIVE_PRODUCT_INTEGRATION_AND_EVALUATION_PLAN_2026-04-04.md`

---

## 0. Why This Document Exists

We now have enough architecture to stop asking vague questions.

The real product is organized around three essential systems:

1. `User Profile and User Insight System`
2. `AI Planning and Guidance System`
3. `Feedback Loop and Growth System`

These three systems are the real center of Sparkle.

Everything else:

- OpenClaw
- Knowledge Galaxy
- community
- achievements
- visual systems
- BGM
- prediction
- extra tools

only matters if it strengthens one of these three.

This document defines:

1. what each system is for
2. what we already have
3. what is still weak
4. what must become true to fulfill the vision
5. how we should improve each system
6. how we should prove the improvement is real

---

## 1. Product Truth

Sparkle is currently not a general execution platform first.

Sparkle is:

> **an AI-native planning and guidance operating system for ordinary users who cannot manually extract the best results from frontier AI on their own**

Its current product wedge is:

> **understand the user deeply, then turn that understanding plus their data into the best plan**

This means the three-system architecture exists to win two real moats:

1. `User understanding quality`
2. `Plan quality`

The third system, feedback and growth, exists to make those two moats better over time.

---

## 2. Honest Current State

Sparkle is no longer missing its foundation.

It already has:

- `SituationBrief`
- semantic primitives
- profile context
- strategy state
- residual diagnosis
- decision policy
- experience actuation
- visible adaptation
- companion state
- feedback binding
- evaluation tooling
- first body-awareness / capability-registry work

This is significant.

But Sparkle is still not yet clearly the best product in its category, because:

- the user-insight layer is stronger at aggregating signals than at discovering decisive missing information
- the planning layer is structured, but not yet proven superior to raw frontier-model use
- the feedback layer can bind and score, but does not yet fully prove compounding plan-quality improvement

So the current state is:

> **the organism exists**
>
> **the core product moat is not yet fully won**

---

## 3. System One: User Profile and User Insight System

### 3.1 Purpose

This system exists to answer:

- who is this user really
- what do they want
- what matters to them
- what is blocking them
- what guidance style works for them
- what do we still need to know before we can build the best plan

Its purpose is not mere storage.

Its purpose is:

> **to surface truths the user cannot easily see alone, in a way the user recognizes as true**

### 3.2 What We Already Have

- explicit and inferred preference storage
- `ProfileContext` as a unified read model
- knowledge summaries, weak spots, and recent mastery changes
- cognitive fragments and behavior patterns
- semantic primitive mapping
- companion state and relationship profile
- strategy state across session / episode / profile

### 3.3 What Is Strong

- Sparkle can already see more than a plain chat transcript.
- It has real cross-session memory and structured profile reads.
- It can assemble many signals into one runtime summary.

### 3.4 What Is Still Weak

- It is still mostly an `assembly layer`, not yet a fully mature `insight engine`.
- It knows many things about the user, but is not yet consistently excellent at deciding which missing information matters most.
- Cold start is still weaker than the vision requires.
- Profile truth is still somewhat fragmented across preference, cognition, plan, and companion subsystems.

### 3.5 What Must Become True

The system should become excellent at:

1. identifying the minimum high-value information required to make a strong plan
2. asking for that information naturally and efficiently
3. distinguishing stable traits from temporary state
4. identifying real bottlenecks instead of only reporting surface symptoms
5. turning scattered user data into one coherent user model

### 3.6 Improvement Priorities

#### Keep

- `ProfileContext`
- semantic primitives
- cognitive fragments and pattern summaries
- strategy and companion state layering

#### Strengthen

- cold-start information acquisition
- profile truth fusion across subsystems
- bottleneck detection
- missing-information detection
- confidence and freshness scoring on insight claims

#### Build New

- `Insight Gap Detector`
  A runtime layer that explicitly answers: what must we still learn to plan well?
- `Profile Truth Compiler`
  A layer that reconciles preference, cognition, progress, plan, and companion evidence into one coherent current user model.
- `Planning Readiness Score`
  A measure of whether Sparkle truly has enough information to generate a strong plan.

#### Demote or Delay

- profile detail that does not improve planning
- decorative persona richness that does not improve trust or insight
- extra memory breadth without better signal quality

### 3.7 How We Prove It

We should evaluate this system by asking:

- Did Sparkle ask for the right missing information?
- Did Sparkle infer a bottleneck the user later recognized as true?
- Did Sparkle distinguish stable tendency from temporary frustration?
- Did better user understanding produce a better plan?

---

## 4. System Two: AI Planning and Guidance System

### 4.1 Purpose

This system exists to answer:

- what is the best plan for this user now
- what is the best next move
- what evidence should ground that recommendation
- how should the plan adapt when reality changes

Its purpose is not “be smart.”

Its purpose is:

> **turn user understanding plus user data into better plans than competitors can provide to non-expert users**

### 4.2 What We Already Have

- `SituationBrief`
- residual diagnosis
- decision policy compiler
- user strategy state
- experience actuator
- user-material grounding path
- prompt-level decision-policy exposure
- visible adaptation generation

### 4.3 What Is Strong

- Sparkle already has a true diagnose -> decide -> act loop.
- It can now adapt pacing, explanation style, retrieval emphasis, and visible stance.
- The system is more like an operating runtime than a plain chat wrapper.

### 4.4 What Is Still Weak

- Planning superiority is not yet proven.
- Some reasoning is still heuristic and prompt-shaped rather than deeply benchmarked.
- Body awareness is present, but mostly advisory.
- The system still needs a more explicit quality bar for plan generation and plan revision.

### 4.5 What Must Become True

The AI system should become excellent at:

1. generating better plans than raw model prompting for ordinary users
2. choosing the right planning depth for the user’s real capacity
3. grounding plans in user materials and real constraints
4. producing good next moves, not just good overviews
5. adapting quickly and legibly when the plan is too hard, too vague, or no longer fits reality

### 4.6 Improvement Priorities

#### Keep

- `SituationBrief`
- residual diagnosis
- decision policy
- bounded strategy writes
- grounding-first path

#### Strengthen

- plan quality benchmarking
- adaptive task decomposition quality
- pacing and sequencing quality
- explanation-to-action conversion quality
- real runtime use of capability registry

#### Build New

- `Planning Benchmark Harness`
  Compare Sparkle against raw frontier-model plans on the same user data.
- `Plan Quality Rubric`
  Explicitly score plans on personalization, feasibility, pacing, grounding, clarity, and adaptability.
- `Planning Readiness Gate`
  Sparkle should sometimes decide it does not yet know enough to plan well.

#### Demote or Delay

- broad execution autonomy
- more agents that do not improve planning quality
- more internal orchestration complexity without better plan output

### 4.7 How We Prove It

We should compare Sparkle versus raw model use on:

- same user goal
- same deadline
- same uploaded materials
- same constraints

And measure:

- plan quality
- user trust
- follow-through likelihood
- adaptation quality
- clarity of next move

If Sparkle does not clearly win there, this system is not yet complete.

---

## 5. System Three: Feedback Loop and Growth System

### 5.1 Purpose

This system exists to answer:

- what happened after Sparkle helped
- what worked
- what failed
- how should Sparkle change next time
- how does each user’s Sparkle become more individual and more effective over time

Its purpose is:

> **to make user understanding and plan quality improve across time, not just within one turn**

### 5.2 What We Already Have

- intervention feedback binding
- strategy write audit history
- session / episode / profile promotion paths
- drift evaluator
- experience evaluator
- human-eval tooling
- visible dashboard summaries

### 5.3 What Is Strong

- Sparkle can now bind natural user feedback to active interventions.
- It can evaluate runtime quality with scorecards.
- It has the start of a real learning loop.

### 5.4 What Is Still Weak

- episode/profile learning is still immature
- compounding improvement is not yet strongly proven
- human evaluation is toolable but not yet a mature repeated operating loop
- the system layer is still too early for true “each user has their own Sparkle”

### 5.5 What Must Become True

The growth system should become excellent at:

1. distinguishing one-turn noise from real repeated evidence
2. promoting only well-supported learning across sessions
3. improving future plan quality, not just future tone or pacing
4. preserving reversibility and avoiding silent drift
5. turning transcript-level human review into actual product prioritization

### 5.6 Improvement Priorities

#### Keep

- feedback binding
- strategy history
- drift checks
- experience evaluation
- human-eval review tooling

#### Strengthen

- episode/profile promotion rules
- conflict resolution across layers
- plan-quality outcome learning
- human-eval operational cadence
- transcript-driven product issue taxonomy

#### Build New

- `Plan Outcome Learning Layer`
  Learn not only from “did this help” but from whether the resulting plan actually improved progress.
- `Human Eval Operations Loop`
  A repeated founder/evaluator ritual that creates backlog priorities from transcripts.
- `Cross-Session Personalization Maturity Model`
  A clear definition of what the user-specific Sparkle should be allowed to learn at each layer.

#### Demote or Delay

- overly aggressive permanent learning
- system-layer self-modification before bounded maturity
- decorative “growth” metrics that do not improve the plan or insight engines

### 5.7 How We Prove It

We should ask:

- Did Sparkle get better for this user across multiple sessions?
- Did it avoid silent drift?
- Did the next plan become better because of previous feedback?
- Did human evaluation findings actually change product decisions?

---

## 6. How The Rest of the System Should Be Judged

Every major subsystem must now justify itself by helping one of the three systems.

### 6.1 Directly Relevant

- OpenClaw
- Galaxy
- prediction
- capability registry
- companion state
- dashboard adaptation
- intervention layer

### 6.2 Conditionally Relevant

- community
- achievements
- visual systems
- BGM

These may remain, but only if they materially improve:

- understanding
- planning
- feedback-driven growth

### 6.3 Product Discipline Rule

If a subsystem cannot clearly improve one of the three systems, it is not on the critical path.

---

## 7. Evaluation Hierarchy

We should stop evaluating Sparkle mostly by feature completion.

The new proof hierarchy should be:

### 7.1 Level 1: Technical Truth

- runtime works
- tests pass
- primary path is stable
- optional sidecars fail safely

### 7.2 Level 2: System Truth

- user insight claims are grounded
- planning quality beats naive baselines
- adaptation is real and visible
- feedback binds correctly

### 7.3 Level 3: Human Truth

- users feel understood
- users say the plan is better than what they would have made alone
- users feel Sparkle changed something real
- users trust the system more over time

### 7.4 Level 4: Competitive Truth

- Sparkle beats raw frontier-model use for ordinary users on planning and guidance

This is the real market proof.

---

## 8. Recommended Execution Order

### Phase A: User Insight Engine Strengthening

Goal:

- make Sparkle better at identifying missing information and real bottlenecks

Deliverables:

- insight gap detector
- planning readiness gate
- improved cold-start acquisition flow
- profile truth compiler design

### Phase B: Planning Quality Benchmarking

Goal:

- prove Sparkle generates better plans than raw AI use

Deliverables:

- plan quality rubric
- Sparkle vs raw-model benchmark scenarios
- plan comparison harness
- north-star journey evaluation with stronger human review

### Phase C: Feedback-to-Planning Improvement

Goal:

- make feedback improve future plan quality, not just local adaptation

Deliverables:

- plan outcome learning layer
- stronger episode/profile promotion rules
- transcript issue taxonomy tied to backlog decisions

### Phase D: Body Awareness That Actually Governs

Goal:

- move system self-knowledge from advisory to operational

Deliverables:

- capability-registry-guided subsystem choice in at least one real runtime path
- bounded system-layer write design
- runtime evidence on whether body-awareness improves plan quality or grounding

### Phase E: Live Alpha Product Truth

Goal:

- reach the first milestone where Sparkle can honestly be judged as a living AI-native growth product

Deliverables:

- technically stable core path
- visible adaptation users can feel
- real evaluator runs
- benchmark evidence that Sparkle planning is materially strong

---

## 9. The Real Standard

Sparkle should only be considered successful when a real user can say:

> **Sparkle understood my situation better than I could explain it myself, turned my messy information into a plan I would not have made alone, and kept improving that plan as reality changed.**

Until that is true, the project is still in construction.

---

## 10. Final Rule

From this point on, every major implementation question should be filtered through:

1. Does this improve user understanding quality?
2. Does this improve plan quality?
3. Does this make feedback improve future understanding or planning?
4. Can we prove the improvement is real?

If the answer is no, it is not on the main path.

