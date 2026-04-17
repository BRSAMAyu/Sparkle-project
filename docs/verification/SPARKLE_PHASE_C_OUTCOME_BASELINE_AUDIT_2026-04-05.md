# Sparkle Phase C Outcome Baseline Audit

> Date: 2026-04-05  
> Scope: Phase C `C0` baseline audit, signal inventory, and taxonomy v1  
> Inventory fixture: `/Users/brsama/code/GitHub/Sparkle-project/backend/tests/fixtures/phase_c_outcome_signal_inventory_v1.json`

## Current Outcome Entry Points

- `backend/app/services/response_feedback_service.py`
  - explicit user thumbs/reason feedback and linked context-pack feedback
- `backend/app/services/intervention_feedback_binding_service.py`
  - binds conversational feedback to active interventions and records short-horizon action payloads
- `backend/app/services/intervention_record_service.py`
  - canonical intervention acceptance lifecycle and outcome status persistence
- `backend/app/services/behavioral_outcome_tracker.py`
  - durable post-intervention behavioral outcome rows
- `backend/app/services/card_protocol/outcome_verifier.py`
  - verifies pending intervention outcomes from later evidence
- `backend/app/services/plan_feedback_service.py`
  - plan review comments, user feedback, rejection tracking, and rollback triggers
- `backend/app/models/task_feedback.py`
  - task-level difficulty, clarity, and quality feedback
- `backend/app/services/human_eval_review_service.py`
  - normalized transcript review, repeated-failure detection, and summary rendering
- `backend/app/services/companion_state_service.py`
  - repeated-evidence promotion guardrails across session, episode, and profile layers

## Current Signal Families

| Signal family | Main sources | Current evidence level | Current promotability | Main consumers |
| --- | --- | --- | --- | --- |
| Turn reaction | `ResponseFeedback`, `ContextPackFeedback` | `Turn Reaction` | session-only in practice | prompt bandit, agent scoring, context-pack tuning |
| Intervention acceptance and feedback binding | intervention record lifecycle + feedback binding | `Behavioral Signal` | limited session-to-episode behavior | experience actuator, strategy learner, semantic outcome state |
| Behavioral outcomes | `BehavioralOutcome` rows | `Behavioral Signal` | not promoted directly | intervention analytics, future aggregation candidate |
| Verified intervention outcomes | `InterventionOutcomeStatus` + evidence payload | `Plan Outcome` proxy | strategy-learning only | outcome verifier, card artifacts |
| Plan feedback and rejection tracking | `PlanState.feedback_log`, rejection counter | mostly `Turn Reaction` | episode-only | plan review loop, rollback logic |
| Plan health and execution miss proxies | plan facts, task/focus state, card metadata | `Plan Outcome` proxy | not promoted directly | verifier heuristics, dashboard, replanning |
| Task difficulty and clarity | `TaskFeedback` | `Behavioral Signal` | preference tuning only | task reflection, replanner triggers |
| Human transcript review | human-eval review summaries | `Human Truth` | manual only | evaluation summaries and product judgment |
| Companion and relationship promotion guardrails | companion/relationship revision histories | repeated `Behavioral Signal` | session -> episode -> profile with gates | effective companion state, relationship profile |

## Baseline Reading of Current Gaps

- Sparkle already has real feedback and outcome surfaces, but they are spread across response, intervention, plan, task, and review systems rather than one canonical Phase C outcome record.
- Durable storage already exists for several weak signals. The main problem is not data absence; it is that the system does not share one contract for evidence strength, freshness, conflict, and reversibility.
- Intervention outcomes are the closest thing to outcome learning today, but they remain intervention-centric. They do not yet unify plan attempts, replans, execution misses, and human-review findings.
- Companion-state promotion proves the repo already knows how to require repeated evidence before profile writes, but that governor is field-specific and not yet the general outcome-learning governor Phase C needs.
- Human review already normalizes issue tags and repeated failures, but it still ends as a summary artifact rather than a backlog feed or release-blocking loop.

## Evidence-Level Mapping V1

### `Turn Reaction`

- `response_feedback`
- `context_pack_feedback`
- much of `plan_states.feedback_log`

This is durable and useful, but it is still mostly about how a response or plan felt in the moment.

### `Behavioral Signal`

- intervention acceptance transitions such as `ACCEPTED` and `ACTED`
- feedback-binding records with measurable effect
- `behavioral_outcomes`
- `task_feedbacks`
- repeated companion/relationship revisions with measurable effect

This is stronger than sentiment because it reflects what the user actually did or could handle after Sparkle changed something.

### `Plan Outcome`

- `InterventionOutcomeStatus` plus verifier evidence payloads
- plan-health recovery and replan events used by outcome verification
- execution-miss and rollback proxies in plan state

This is currently fragmented. Sparkle can sometimes infer whether a move worked, but it does not yet write one canonical record for that conclusion.

### `Human Truth`

- normalized transcript review segments
- repeated failure clusters
- `must_fix_before_next_pilot` tags

This is the strongest product-learning signal, but it is still manual and report-level.

## Session / Episode / Profile Promotability

| Signal family | Session | Episode | Profile | Notes |
| --- | --- | --- | --- | --- |
| Response/context-pack feedback | yes | no | no | durable rows exist, but semantics remain mostly turn-local |
| Intervention acceptance/binding | yes | partial | no | useful for short-horizon adaptation, not durable learning truth yet |
| Behavioral outcomes | yes | partial | no | real evidence, but not governed as promotable learning today |
| Verified intervention outcomes | yes | partial | no | strategy-learning useful, but not yet a general promotion surface |
| Plan feedback/rejections | yes | yes | no | plan-local history and rollback protection, not profile truth |
| Task feedback | yes | partial | indirect only | tunes preference surfaces more than outcome learning |
| Human review | no automatic runtime promotion | manual product loop only | manual product loop only | strongest human signal, but not yet operationalized |
| Companion/relationship guardrails | yes | yes | yes | existing repeated-evidence and conflict-aware promotion model |

## Current Blind Spots

- No canonical `PlanOutcomeRecord` spans plan attempts, replans, interventions, task friction, and human review.
- No shared evidence-strength, freshness, conflict, or expiry contract exists across feedback surfaces.
- Plan progress, execution misses, and recovery signals are fragmented across `PlanState`, task/focus aggregates, card metadata, and intervention evidence payloads.
- Human-eval output stops at normalized summary and repeated-failure lists; it does not yet create backlog labels, release blockers, or outcome-learning inputs.
- Existing promotion safeguards are strong proof of concept, but they govern companion/relationship state rather than validated outcome learning.

## Phase C Outcome Taxonomy V1

Use this taxonomy as the C0 contract for later packs.

| Level | Definition | Examples | Durable-learning rule |
| --- | --- | --- | --- |
| `Turn Reaction` | The user said a response or plan felt good or bad. | thumbs down, too verbose, too hard, dissatisfied pack feedback | never promote by itself |
| `Behavioral Signal` | The user acted, avoided, delayed, completed, overloaded, or re-engaged after a Sparkle change. | intervention acted, task too difficult, measurable effect in feedback binding | can support session/episode learning, not profile truth alone |
| `Plan Outcome` | Evidence shows a plan or intervention actually improved or harmed progress. | verified effective intervention, rollback after repeated rejection, plan-health recovery | candidate promotable learning when repeated and conflict-checked |
| `Human Truth` | Transcript review reveals a repeated diagnosis, timing, grounding, continuity, or adaptation issue. | repeated `grounding_weak`, `diagnosis_wrong`, `timing_wrong` clusters | can override weak runtime signals, but still needs audit trail and operating loop |

## Recommended Stage 1 Constraints For `PlanOutcomeRecord`

Phase C Stage 1 should not create a second memory system. The record should be append-only, audit-first, and compatible with current surfaces.

Minimum constraints:

- One record must describe exactly one observed outcome claim.
- A record must include:
  - target object identity such as `plan_id`, `intervention_id`, `session_id`, or task/reference id
  - target layer such as `session`, `episode`, or `profile_candidate`
  - observed outcome type and time horizon
  - evidence sources with explicit provenance
  - confidence
  - freshness timestamp or window
  - promotion recommendation
  - reversal or conflict candidate metadata
- A record must preserve the original source surface instead of flattening away whether it came from response feedback, intervention verification, plan feedback, task feedback, or human review.
- A record must separate:
  - raw signal
  - normalized interpretation
  - promotion recommendation
- A record must be safe to reject later. Nothing in Stage 1 should silently write profile truth.

## Characterization Proof

The Phase C baseline should be treated as credible only if the current repo already demonstrates the following semantics in tests:

- response feedback is real but mostly turn-level
- intervention signals already distinguish acceptance and measured outcomes
- human eval already normalizes issue tags and repeated failures
- repeated-evidence promotion guardrails already exist for companion and relationship state

Requested suites:

1. `cd backend && pytest tests/unit/test_response_feedback_service.py tests/unit/test_context_pack_feedback.py -v`
2. `cd backend && pytest tests/unit/test_intervention_feedback_binding_service.py tests/unit/test_phase2_intervention_pipeline.py -v`
3. `cd backend && pytest tests/services/test_human_eval_review_service.py tests/unit/test_companion_state_service.py -v`

See the completion note at the end of this report for actual run status and characterization outcome.

## Completion Note

- Runtime behavior changed: `no`
- Schema changed: `no`
- New production API or proto: `no`
- New characterization tests added: `no`
- Characterization test result: `pass`

Executed suites:

1. `cd backend && pytest tests/unit/test_response_feedback_service.py tests/unit/test_context_pack_feedback.py -v`
   - Result: `6 passed`
   - Audit read: response and context-pack feedback are durable and real, but the covered semantics remain response-local and optimization-oriented rather than validated outcome learning.
2. `cd backend && pytest tests/unit/test_intervention_feedback_binding_service.py tests/unit/test_phase2_intervention_pipeline.py -v`
   - Result: `22 passed`
   - Audit read: intervention signals already distinguish acceptance lifecycle, deduped feedback binding, and later outcome verification with measured evidence.
3. `cd backend && pytest tests/services/test_human_eval_review_service.py tests/unit/test_companion_state_service.py -v`
   - Result: `13 passed`
   - Audit read: human review already normalizes issue tags and repeated failures, and companion-state writes already require repeated evidence plus conflict-aware promotion before profile-level durability.

Warnings observed during characterization:

- recurring SQLAlchemy drop-order warnings in SQLite-backed tests
- recurring Pydantic v2 deprecation warnings in existing schemas

These warnings do not change the C0 audit conclusions, but they remain background cleanup work outside Phase C baseline scope.
