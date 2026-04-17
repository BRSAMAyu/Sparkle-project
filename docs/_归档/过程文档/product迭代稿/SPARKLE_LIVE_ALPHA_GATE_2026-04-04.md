# Sparkle Live Alpha Gate

> Date: 2026-04-04  
> Status: Active milestone gate  
> Audience: Founder, chief designer, implementation Codex runs, backend, mobile, evaluation  
> Companion docs:
> - `docs/product/SPARKLE_AI_NATIVE_SYSTEM_CONSENSUS_2026-04-03.md`
> - `docs/product/SPARKLE_LIVE_PRODUCT_INTEGRATION_AND_EVALUATION_PLAN_2026-04-04.md`
> - `docs/product/SPARKLE_RESIDUAL_DECISION_POLICY_AND_EXPERIENCE_PHASE_PLAN_2026-04-04.md`
> - `docs/product/evaluation/SPARKLE_NORTH_STAR_HUMAN_EVALUATION_PROTOCOL_2026-04-04.md`
> - `docs/product/implementation/SPARKLE_EXPERIENCE_PHASE_RELEASE_CHECKLIST_2026-04-04.md`
> - `docs/product/implementation/SPARKLE_BODY_MAP_AND_CAPABILITY_REGISTRY_SPEC_2026-04-04.md`

---

## 0. Purpose

This document defines the next real milestone after bridge construction and experience-phase implementation:

> **Sparkle Live Alpha**

This is not a release marketing label.

It is an internal truth gate that answers one question:

> **Has Sparkle become alive enough as a product that we can say the system is no longer just architecturally impressive, but genuinely functioning as an AI-native growth operating system?**

The purpose of this gate is to prevent two kinds of failure:

1. shipping too early because the architecture feels exciting
2. never declaring progress because the vision is much larger than any one milestone

Live Alpha is the first milestone where Sparkle should feel like a real product organism rather than a collection of promising subsystems.

---

## 1. The Meaning of Live Alpha

Sparkle Live Alpha means:

- the core growth loop works on the real primary path
- the system can diagnose, decide, act, explain, and adapt
- users can visibly feel important adaptations
- human evaluators can run the north-star journey and produce reliable findings
- Sparkle has begun to know its own body, not just the user

Live Alpha does **not** mean:

- the full long-term vision is complete
- the five-layer system is fully mature
- the AI has full system-level autonomy
- all product surfaces are polished
- domain expansion is complete

Short version:

> **Live Alpha means the product is truly alive enough to be judged as a growth system.**

---

## 2. What Live Alpha Is Not

We should explicitly reject these false definitions:

### 2.1 Not “all major architecture documents are written”

Documentation is not fulfillment.

### 2.2 Not “the backend mostly passes”

Suite health matters, but the milestone is product-alive, not backend-auditable.

### 2.3 Not “the AI feels warm”

Warmth without diagnosis and adaptation is companion theater.

### 2.4 Not “the body map exists”

Capability metadata alone is not system self-knowledge.

### 2.5 Not “we can demo a happy path”

A real growth OS must survive difficulty, overload, ambiguity, and continuity.

---

## 3. The Live Alpha Promise

At Live Alpha, a user in the north-star journey should be able to feel:

1. Sparkle understood the real reason they were stuck.
2. Sparkle changed something real, not just its wording.
3. Sparkle used the right evidence source when it mattered.
4. Sparkle remembered the trajectory across turns and sessions.
5. Sparkle remained helpful without becoming manipulative or reducing the user’s freedom.

That is the minimum product truth for this milestone.

---

## 4. Live Alpha Gate Categories

Live Alpha has five gate categories:

1. `Core Runtime Health`
2. `Live Acceptance Proof`
3. `Visible Adaptation UX`
4. `Human Evaluation Operations`
5. `Body Awareness v1`

All five must be green enough for Live Alpha.

---

## 5. Gate 1: Core Runtime Health

### 5.1 Required State

The primary growth path must be stable enough that product failures are no longer dominated by infrastructure breakage.

### 5.2 Minimum Criteria

- The backend test suite no longer fails on known core growth-path blockers.
- `pytest --maxfail=1` can be walked without repeatedly exposing unresolved architecture-integrity regressions in:
  - orchestration
  - growth tools
  - strategy state
  - feedback binding
  - visible adaptation
  - core plan/task progress
- Optional sidecars and shadow paths fail as warnings, not as fatal blockers.
- Shadow/dual-write systems cannot poison the main transaction path.
- The primary chat/orchestration path is the truth path; fenced legacy paths do not silently bypass it.

### 5.3 Non-Negotiables

These must be true:

- `SituationBrief` is present when experience-phase logic is active.
- `residual_decision_context` is present on final responses for experience-phase turns.
- `ExperienceActuator` changes are bounded and reversible.
- feedback binding cannot corrupt same-turn runtime state.
- user-material grounding failure degrades gracefully.

### 5.4 Live Alpha Standard

Core Runtime Health is green when:

> **the system’s primary growth loop is robust enough that remaining failures are isolated product/integration issues, not foundational instability**

---

## 6. Gate 2: Live Acceptance Proof

### 6.1 Required State

We need stronger proof than component tests and partially simulated scenarios.

### 6.2 Minimum Criteria

The live acceptance matrix must cover:

- `R_e` cognitive misconception repair with user materials
- `R_c` overload recognition and immediate load-shedding
- `R_c` accepted adaptation converted into remobilization
- `R_n` normative decision support without fake certainty
- `R_i` identity-fragile moment answered with continuity-grounded evidence
- at least one multi-session continuity case

### 6.3 Quality Criteria

- Acceptance runs the real primary orchestrator path.
- Stubbing is limited to what is genuinely external or economically necessary.
- Acceptance is not allowed to manually inject optimistic high-level outcomes as proof.
- Outcome scoring should be derived as much as possible from runtime-observed behavior.
- Acceptance must explicitly verify visible adaptation payloads, not only backend state.

### 6.4 Live Alpha Standard

Live Acceptance Proof is green when:

> **the system can reliably complete the north-star journey and adjacent residual scenarios on the real primary path with trustworthy proof quality**

---

## 7. Gate 3: Visible Adaptation UX

### 7.1 Required State

Users must be able to see the system paying attention.

### 7.2 Minimum Criteria

#### Chat

- Sparkle can surface a concrete “I adjusted this because...” moment.
- Sparkle can show when a workload/pacing/strategy change occurred.
- Sparkle can express reversibility:
  - “we can change this again if it doesn’t help”
- Grounded explanations feel clearly rooted in the user’s own materials when appropriate.
- Continuity language feels specific, not generic.

#### Home

- The home experience can explain:
  - what changed
  - what matters now
  - why the next move is the right one
- Intelligence appears before dashboard mechanics.

### 7.3 Quality Criteria

- Visible adaptation should feel calm and truthful, not theatrical.
- Adaptation should not be hidden only in metadata or debugging surfaces.
- The user should not need to infer adaptation entirely from backend consequences.

### 7.4 Live Alpha Standard

Visible Adaptation UX is green when:

> **a user can clearly point to a real adaptation Sparkle made and understand why it happened**

---

## 8. Gate 4: Human Evaluation Operations

### 8.1 Required State

Automated tests alone are no longer enough.

### 8.2 Minimum Criteria

- The thermodynamics north-star evaluation protocol is runnable end to end by a human evaluator.
- There is a stable runbook and transcript review format.
- Review findings are tagged with a shared taxonomy.
- At least one full human-evaluated run has been completed.
- Findings from that run are translated into product priorities or fixes.

### 8.3 Quality Criteria

- Human findings outrank aesthetic preference.
- Product changes can be traced back to transcript evidence, not only engineering intuition.
- Evaluators can distinguish:
  - diagnosis wrong
  - timing wrong
  - adaptation invisible
  - grounding weak
  - continuity weak
  - tone drift

### 8.4 Live Alpha Standard

Human Evaluation Operations is green when:

> **Sparkle can be judged by humans using a repeatable north-star protocol, and those findings feed the roadmap**

---

## 9. Gate 5: Body Awareness v1

### 9.1 Required State

Sparkle must begin to know its own body.

This does not mean full autonomous system control.
It means the system has first-class, structured awareness of its capabilities.

### 9.2 Minimum Criteria

- A capability registry exists for major subsystems.
- It includes at least:
  - models
  - agents
  - pipelines
  - tools
  - major evidence sources
  - major user-facing adaptation surfaces
- Each capability records enough information to support reasoning:
  - what it does
  - when to use it
  - what it reads
  - what it writes
  - approximate cost
  - risk / constraints
  - current availability or health

### 9.3 Usage Criteria

For Live Alpha, body awareness does not need to be universal.
But it must be real enough that Sparkle can use it in at least one meaningful runtime flow.

Minimum meaningful uses:

- choose or justify a grounding path
- choose or justify a strategy tool or subsystem
- expose body/capability state for future system-layer decisions

### 9.4 Live Alpha Standard

Body Awareness v1 is green when:

> **Sparkle has begun to reason about its own capabilities as a coherent body, not just as scattered implementation details**

---

## 10. Five-Layer Configuration Gate for Live Alpha

The five-layer configuration system does not need to be fully mature for Live Alpha, but it must be coherent enough to support trustworthy adaptation.

### 10.1 Required Layer State

| Layer | Live Alpha requirement |
|---|---|
| Constitutional | Stable and enforced |
| Session | Live and reliable |
| Episode | Partially live with real promotion behavior |
| Profile | Partially live with evidence-based promotion only |
| System | Early design plus first body-map/capability-registry usage |

### 10.2 What Must Be True

- Sparkle can make session-level reversible changes safely.
- Some short-term and profile learning can persist with evidence.
- The constitutional layer prevents silent drift.
- The system layer is not fully built, but the path toward it is real and structured.

### 10.3 What Can Still Be Incomplete

- full autonomous system-level control
- broad system-layer writes
- universal capability reasoning
- mature conflict resolution across all learned profile settings

---

## 11. Live Alpha Exit Criteria

Sparkle Live Alpha is achieved only when all of the following are true:

1. Core runtime health is green.
2. Live acceptance proof is green.
3. Visible adaptation UX is green.
4. Human evaluation operations are green.
5. Body awareness v1 is green.
6. The five-layer configuration system is coherent enough for trustworthy adaptation.

And one more qualitative requirement:

> **At least one human-run north-star journey ends with the evaluator honestly saying: “this felt like a system that noticed, adapted, and helped in a way that was meaningfully beyond a generic assistant.”**

If that sentence cannot be honestly said yet, we are not at Live Alpha.

---

## 12. What Comes After Live Alpha

Live Alpha is not the end of the vision.

It unlocks the next chapter:

- broader pilot testing
- transcript-driven UX refinement
- deeper body-awareness and system-layer control
- stronger per-user Sparkle individuality
- better continuity and meaning-management beyond the first wedge

That next chapter should be called:

> **Sparkle Organic Beta**

But we do not need that chapter yet.
We first need to reach Live Alpha truthfully.

---

## 13. Immediate Execution Order

To reach Live Alpha, the next execution order should be:

1. Continue Pack 1 until the strict backend walk is no longer exposing core growth-path instability.
2. Strengthen live acceptance until the residual matrix is convincingly covered on the real primary path.
3. Run Pack 3 in reality, not only on paper.
4. Use the resulting transcript findings to refine Pack 2 UX.
5. Keep extending Pack 4 only where it supports real runtime self-knowledge and real user value.

This preserves the right priority:

> **truthful product aliveness before deeper AGI-system ambition**

---

## 14. Final Gate Sentence

Sparkle Live Alpha is the point where:

> **the system’s architecture, adaptation, visible experience, human evaluation, and first body-awareness loop are strong enough that Sparkle can honestly be called a living AI-native growth product rather than a promising architecture project.**
