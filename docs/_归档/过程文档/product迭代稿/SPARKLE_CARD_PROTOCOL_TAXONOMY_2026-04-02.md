# Sparkle Card Protocol — Frozen Taxonomy

> Status: **FROZEN** (Phase 0 deliverable)
> Date: 2026-04-02
> Supersedes: All prior card/plan/task vocabulary discussions
> Acceptance gate: A0

---

## 0. Purpose

This document freezes the vocabulary, boundaries, and semantics of the Sparkle Card Protocol.
Every subsequent implementation phase must conform to these definitions without ambiguity.

---

## 1. Card Type Taxonomy

### 1.1 Card Types (canonical)

| Type | Code | Description | Key Rule |
|------|------|-------------|----------|
| **PLAN** | `PLAN` | A long-lived coordination shell that owns direction and near-term execution | A plan owns phases via CONTAINS edges; it does not directly own tasks |
| **PHASE** | `PHASE` | A time-bounded bridge from strategy to executable work | A phase is always contained by exactly one plan; it contains tasks |
| **TASK** | `TASK` | The canonical definition of a unit of work | Tasks are reusable definitions; execution happens through TaskOccurrences |
| **KNOWLEDGE** | `KNOWLEDGE` | An evidence-oriented understanding object linked to mastery | Valuable only insofar as it supports diagnosis, path correction, and outcome verification |
| **ACHIEVEMENT** | `ACHIEVEMENT` | A motivational and recognition object | Supports persistence but must not distract from the main growth loop |
| **CUSTOM** | `CUSTOM` | Extensible type for future card kinds (e.g., REFLECTION, JOURNAL) | Not used in the first 90 days; reserved for Phase 5+ |

### 1.2 Canonical Card vs. Execution Instance vs. Presentation Card

These are three different things and must never be conflated:

| Concept | What it is | Where it lives |
|---------|-----------|---------------|
| **Canonical Card** | The semantic entity: the reusable definition | `cards` table |
| **Execution Instance** | A concrete occurrence of a task on a specific date | `task_occurrences` table |
| **Presentation Card** | The UI-rendered view (Flutter widget) | Flutter presentation layer |

Rule: Never store UI state in the canonical card. Never store scheduling data in the canonical card.
Rule: `TaskOccurrence` is **not** a card and does **not** participate in `card_edges` in Phase 1.

---

## 2. Edge Type Taxonomy

### 2.1 Edge Types

| Edge Type | Code | Semantics | Example |
|-----------|------|-----------|---------|
| **Contains** | `CONTAINS` | Structural parent-child; the child is part of the parent's working set | Plan CONTAINS Phase; Phase CONTAINS Task |
| **References** | `REFERENCES` | Non-owning pointer; the parent cites the child without owning it | A task REFERENCES a knowledge card |
| **Depends On** | `DEPENDS_ON` | Real execution ordering constraint | Task A DEPENDS_ON Task B |
| **Blocks** | `BLOCKS` | Blocking dependency (stronger than DEPENDS_ON) | A knowledge gap BLOCKS a task |
| **Generated From** | `GENERATED_FROM` | Provenance: one canonical card was derived from another canonical card | A remediation task GENERATED_FROM a reusable task template |
| **Evidence For** | `EVIDENCE_FOR` | Connects evidence to a claim or node | An error record EVIDENCE_FOR a knowledge gap |
| **Enables** | `ENABLES` | Completing the source makes the target easier | A prerequisite knowledge card ENABLES a task |
| **Rewards** | `REWARDS` | Completing the source unlocks the target achievement | A task REWARDS an achievement card |
| **Adopted From** | `ADOPTED_FROM` | A new owned card was created from a snapshot | User B's plan ADOPTED_FROM User A's snapshot |
| **Forked From** | `FORKED_FROM` | Lineage retained but future sync is detached | A forked plan keeps origin reference |

### 2.2 Binding Modes

| Mode | Code | Semantics |
|------|------|-----------|
| **Owned** | `OWNED` | The child is a structural part of the parent; deleting parent removes edge |
| **Reference** | `REFERENCE` | The parent points to the same canonical card without ownership |
| **Mirror** | `MIRROR` | Read-only live view of the canonical card |
| **Snapshot** | `SNAPSHOT` | Frozen immutable reference to a specific version |

Rule: `card_edges` connect canonical cards only. Execution-instance provenance for `TaskOccurrence` is stored directly on the occurrence record via fields such as `series_card_id`, `plan_card_id`, `phase_card_id`, and `generated_by_rule_hash`. If occurrence-to-occurrence or occurrence-to-card graphing is needed later, it must be introduced as a dedicated execution relationship model rather than overloading `card_edges`.

---

## 3. Planning Artifact Taxonomy

### 3.1 Artifact Types

| Artifact | Code | Purpose | Created By |
|----------|------|---------|------------|
| **Discovery Dossier** | `DISCOVERY_DOSSIER` | User goals, motives, constraints, resistance patterns, prior failures | Discovery Agent |
| **Global Compass** | `GLOBAL_COMPASS` | North star, success criteria, non-negotiables, pacing philosophy | Architecture Agent |
| **Strategy Map** | `STRATEGY_MAP` | Phase architecture, milestone logic, fallback logic, intentionally not materialized yet | Architecture Agent |
| **Phase Blueprint** | `PHASE_BLUEPRINT` | Per-phase objective, entry/exit criteria, adaptation policy | Tactical Agent |
| **Active Phase Pack** | `ACTIVE_PHASE_PACK` | Current phase tasks, scheduling assumptions, intervention triggers | Tactical Agent |
| **Reflection Report** | `REFLECTION_REPORT` | What happened, what changed, what worked, what failed, recommended adjustment | Reflection Agent |
| **Decision Log** | `DECISION_LOG` | Important system decisions with rationale, expected observation, later confirmation | Governance Agent |
| **Risk Register** | `RISK_REGISTER` | Major risks, likelihood, mitigation, trigger threshold | Governance Agent |

### 3.2 Artifact Status Lifecycle

```
DRAFT → PROPOSED → APPROVED → SUPERSEDED
                  → REJECTED
```

Rule: Only APPROVED artifacts can drive execution writes. DRAFT and PROPOSED artifacts can inform AI reasoning but cannot directly modify the user's path.

Temporary implementation exception:

- In Phase 1 and Phase 2, before full artifact governance is live, execution writebacks may be authorized by `legacy PlanState + deterministic system policy + explicit service guardrails`.
- This exception exists only to support the 90-day main loop and must be retired once `GLOBAL_COMPASS` and `STRATEGY_MAP` become authoritative in Phase 3.

---

## 4. Intervention Taxonomy

### 4.1 Trigger Types

| Trigger | Code | Description |
|---------|------|-------------|
| **Concept Gap** | `CONCEPT_GAP` | User lacks foundational understanding needed for current task |
| **Plan Risk** | `PLAN_RISK` | Plan health degraded; path is at risk of failure |
| **Stall Pattern** | `STALL_PATTERN` | Behavioral evidence shows user is stuck (procrastination, avoidance, repeated deferrals) |
| **Overload** | `OVERLOAD` | User has too many active tasks or too little time for current commitments |
| **Misalignment** | `MISALIGNMENT` | User's actual behavior diverges from stated goals or plan assumptions |

### 4.2 Delivery Strategies (Tone)

| Strategy | Code | Tone Principle | When to use |
|----------|------|---------------|-------------|
| **Curious** | `CURIOUS` | "I noticed something — want to explore it?" | Low confidence, first-time detection, user is sensitive |
| **Supportive** | `SUPPORTIVE` | "Here's something that might help — no pressure" | Medium confidence, user has accepted help before |
| **Direct** | `DIRECT` | "Based on what I'm seeing, I recommend X" | High confidence, repeated pattern, user prefers directness |
| **Micro Restart** | `MICRO_RESTART` | "Let's try one small thing right now" | Stall/overload, user needs momentum, cognitive load is high |

### 4.3 Delivery Channels

| Channel | Code | Description |
|---------|------|-------------|
| **Chat** | `CHAT` | Inline in conversation (most natural, lowest friction) |
| **Push** | `PUSH` | Notification delivered outside the app |
| **In-App** | `IN_APP` | Banner/card overlay within the app |
| **Focus Mode** | `FOCUS_MODE` | Intervention during focus session (highest care required) |

### 4.4 Acceptance Status Lifecycle

```
CREATED → DELIVERED → SEEN → DISMISSED
                           → SNOOZED → (re-enters CREATED after snooze window)
                           → ACCEPTED → ACTED
```

| Status | Code | Meaning |
|--------|------|---------|
| **Created** | `CREATED` | Intervention generated, not yet delivered |
| **Delivered** | `DELIVERED` | Intervention has been surfaced through its intended channel |
| **Seen** | `SEEN` | User viewed the intervention |
| **Dismissed** | `DISMISSED` | User explicitly dismissed |
| **Snoozed** | `SNOOZED` | User postponed (returns to CREATED after window) |
| **Accepted** | `ACCEPTED` | User acknowledged and agreed to try |
| **Acted** | `ACTED` | User took concrete action based on the intervention |

### 4.5 Outcome Status

| Status | Code | Meaning |
|--------|------|---------|
| **Pending** | `PENDING` | Outcome window has not closed yet |
| **Effective** | `EFFECTIVE` | Evidence shows the intervention improved the situation |
| **Ineffective** | `INEFFECTIVE` | Evidence shows no improvement or worsening |
| **Unknown** | `UNKNOWN` | Outcome window closed but insufficient evidence |

---

## 5. Lifecycle Status Taxonomy

### 5.1 Card Lifecycle

```
DRAFT → ACTIVE → PAUSED → ACTIVE (resume)
                → COMPLETED
                → ARCHIVED
                → CANCELLED
```

| Status | Code | Meaning |
|--------|------|---------|
| **Draft** | `DRAFT` | Card is being composed, not yet committed |
| **Active** | `ACTIVE` | Card is live and part of the user's working set |
| **Paused** | `PAUSED` | Card is temporarily suspended |
| **Completed** | `COMPLETED` | Card has been finished successfully |
| **Archived** | `ARCHIVED` | Card is retained for reference but inactive |
| **Cancelled** | `CANCELLED` | Card was abandoned without completion |

### 5.2 TaskOccurrence Lifecycle

```
PLANNED → READY → IN_PROGRESS → COMPLETED
                       → DEFERRED → PLANNED (re-scheduled)
                       → CANCELLED
         → MISSED
```

| Status | Code | Meaning |
|--------|------|---------|
| **Planned** | `PLANNED` | Scheduled for future execution |
| **Ready** | `READY` | Within the execution window, ready to start |
| **In Progress** | `IN_PROGRESS` | Currently being executed |
| **Completed** | `COMPLETED` | Successfully finished |
| **Missed** | `MISSED` | Execution window passed without action |
| **Deferred** | `DEFERRED` | User chose to postpone |
| **Cancelled** | `CANCELLED` | Abandoned for this occurrence |

---

## 6. Source Type Taxonomy

| Source | Code | Meaning |
|--------|------|---------|
| **Original** | `ORIGINAL` | Created by user or AI from scratch |
| **Adopted** | `ADOPTED` | Created from another user's snapshot (with origin tracking) |
| **Forked** | `FORKED` | Copied with lineage but detached from future updates |
| **Imported** | `IMPORTED` | Brought in from external source |
| **Generated** | `GENERATED` | Created by system/AI as a derived artifact |

---

## 7. Visibility Taxonomy

| Level | Code | Meaning |
|-------|------|---------|
| **Private** | `PRIVATE` | Only the owner can see |
| **Friends** | `FRIENDS` | Owner's friends can see |
| **Community** | `COMMUNITY` | All community members can see |
| **Public** | `PUBLIC` | Anyone can see |

---

## 8. Key Unambiguous Definitions

These definitions eliminate all ambiguity for implementation.

### 8.1 Plan

A **plan** is a governed path with strategic direction, rolling near-term materialization, execution evidence, intervention history, and adaptation memory. It is NOT a pile of tasks. It is the top-level coordination shell.

### 8.2 Phase

A **phase** is a time-bounded chapter of a plan that bridges strategy to executable work. It has entry criteria, exit criteria, and an adaptation policy. It is always contained by exactly one plan.

### 8.3 Task

A **task** is the canonical reusable definition of a unit of work. It is NOT a scheduled event. Scheduling creates TaskOccurrences. A task can be referenced by multiple phases.

### 8.4 TaskOccurrence

A **task occurrence** is a concrete execution instance of a task on a specific date within a specific time window. All scheduling, reminders, and execution analytics operate on occurrences, not on tasks.

Occurrence provenance is stored on the occurrence record itself, not in `card_edges`.

### 8.5 Intervention

An **intervention** is an explicit, tracked, measured attempt by the system to help the user overcome a detected blockage. It has a trigger, a diagnosis, a delivery strategy, an acceptance lifecycle, and an outcome. It is NOT a chat message. It is a structured record with lifecycle.

### 8.6 Adopt

To **adopt** means to create a new owned card from another user's shared snapshot, preserving origin tracking. The adopting user gets full ownership and control. The original user's data is not affected.

### 8.7 Fork

To **fork** means to copy a card with lineage reference but detach from future synchronization. The forking user can modify freely. The original continues independently.

### 8.8 Evidence

**Evidence** is structured data connecting an observation (error, completion, feedback, behavioral signal) to a claim (knowledge gap, plan risk, intervention outcome). Evidence flows through `EVIDENCE_FOR` edges. It is the foundation of the system's long-term moat.

### 8.9 Compass

The **global compass** is the highest-level approved artifact that captures the user's north star, success criteria, non-negotiables, and pacing philosophy. The AI cannot silently mutate it. Changes require user approval.

### 8.10 Strategy Map

The **strategy map** is the approved artifact that defines the phase architecture, milestone logic, and fallback logic for a plan. It specifies what is intentionally not yet materialized.

---

## 9. Boundary Rules

These rules define what is IN scope and OUT of scope for each implementation phase.

### Phase 1 Scope (0-20 days)
- IN: PLAN, PHASE, TASK, KNOWLEDGE card types
- IN: CardEdge (CONTAINS, REFERENCES, DEPENDS_ON, EVIDENCE_FOR)
- IN: TaskOccurrence
- IN: adaptive_replanner → execution writeback
- IN: error analysis → knowledge mastery writeback
- IN: intervention language system v1
- IN: temporary execution authorization via `legacy PlanState + deterministic system policy + service guardrails`
- OUT: ACHIEVEMENT card type (use existing system)
- OUT: CUSTOM card type
- OUT: CardSnapshot (sharing)
- OUT: ADOPTED_FROM, FORKED_FROM edges
- OUT: Discovery Dossier, Global Compass (full implementation)
- OUT: Flutter UI changes beyond what is needed for the main loop

### Phase 2 Scope (21-50 days)
- IN: InterventionRecord table and lifecycle
- IN: Risk events from plan health
- IN: Behavior-triggered intervention delivery
- IN: Intervention tone/framing experiments
- IN: Reflection Report artifact
- OUT: CardSnapshot sharing
- OUT: ADOPT/FORK flows

### Phase 3 Scope (51-70 days)
- IN: Parameter compiler
- IN: Effect verification pipeline
- IN: Decision Log and Risk Register artifacts
- IN: Global Compass and Strategy Map (full)
- IN: Discovery Dossier (full)
- OUT: CardSnapshot sharing
- OUT: Community/federation features

### Phase 4 Scope (71-90 days)
- IN: End-to-end main scenario hardening
- IN: Key UI polish for the main chain
- IN: Demo narrative calibration
- OUT: Everything not on the main chain

### Phase 5 Scope (post-90 days)
- IN: CardSnapshot sharing and adoption
- IN: ACHIEVEMENT and CUSTOM card types
- IN: Community and social growth links
- IN: ADOPT/FORK flows
- IN: Federation and portability

---

**Document Status**: FROZEN
**Acceptance Gate**: A0
**Next Review**: R1 (after Phase 0 signoff)
