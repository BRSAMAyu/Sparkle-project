# Sparkle Card Protocol — Phase E Alignment Report

Date: 2026-04-03
Status: COMPLETE (backend scope)

## Objective

Phase E upgrades the system from "reviewable long-horizon planning" to "phase-by-phase adaptive execution with persistent memory".

It closes four backend gaps:

1. Persistent planning memory across phases
2. Concrete task design for the active phase
3. Context-aware feedback gates at phase boundaries
4. Drift detection that can trigger `MISALIGNMENT` interventions

## Deliverables

### 1. Planning memory service

File:
- `backend/app/services/card_protocol/planning_memory_service.py`

What it provides:
- `load_planning_context(...)`
  - Level 1: approved `GLOBAL_COMPASS`
  - Level 2: phase archive from completed phase feedback gates
  - Level 3: rolling context from recent tasks / occurrences / feedback
  - Level 4: relevant decisions from `DECISION_LOG`
- `archive_phase(...)`
  - stores durable lessons on the phase card after feedback-gate completion
- `compute_drift_score(...)`
  - returns:
    - `drift_score`
    - `drift_indicators`
    - `recommendation`
    - `supporting_metrics`

### 2. Phase design service

File:
- `backend/app/services/card_protocol/phase_design_service.py`

What it does:
- designs concrete short-horizon tasks for exactly one phase
- uses planning memory + compass constraints + recent execution signals
- creates legacy `Task` rows
- relies on dual-write projection to canonical task cards
- moves new tasks into the target phase
- sets recurrence rules
- generates initial occurrences

### 3. Feedback gate engine

File:
- `backend/app/services/card_protocol/feedback_gate_engine.py`

What it does:
- starts a context-aware phase feedback gate
- computes retrospective from real phase execution data
- generates questions based on what actually happened
- processes multi-turn answers
- submits structured phase feedback
- archives phase lessons
- computes drift after the gate
- prepares the next phase for execution

### 4. Drift detection integration

File:
- `backend/app/services/card_protocol/outcome_verifier.py`

What changed:
- after outcome evaluation, the verifier now also computes planning drift
- if drift is high enough, it creates a `MISALIGNMENT` intervention
- duplicate unresolved misalignment interventions are suppressed

### 5. Phase E APIs

File:
- `backend/app/api/v1/plans.py`

New endpoints:
- `GET /api/v1/plans/{plan_id}/planning-context`
- `POST /api/v1/plans/phases/{phase_card_id}/design-tasks`
- `POST /api/v1/plans/phases/{phase_card_id}/feedback-gate/start`
- `POST /api/v1/plans/phases/feedback-gate/{session_id}/respond`
- `POST /api/v1/plans/{plan_id}/advance-phase`

## Closed-loop result

Phase E now supports this backend flow:

`approved compass -> active phase -> concrete task design -> execution -> feedback gate -> archive lessons -> drift assessment -> next phase or compass review`

This means the backend now has a real long-term adaptive execution loop rather than only a planning/governance loop.

## Verification

Compile:
- `python3 -m compileall backend/app/services/card_protocol/planning_memory_service.py backend/app/services/card_protocol/phase_design_service.py backend/app/services/card_protocol/feedback_gate_engine.py backend/app/services/card_protocol/outcome_verifier.py backend/app/api/v1/plans.py backend/tests/unit/test_phase_e_planning_loop.py`

Phase E tests:
- `cd backend && pytest tests/unit/test_phase_e_planning_loop.py -q`

A-E regression:
- `cd backend && pytest tests/unit/test_card_operations_service.py tests/unit/test_card_protocol_phaseb.py tests/unit/test_card_protocol_phasec.py tests/unit/test_phase_d_discovery_pipeline.py tests/unit/test_phase_e_planning_loop.py -q`

Result:
- `19 passed`

## Notes

This marks Phase E as backend-complete.

Not included in this pass:
- mobile UI for discovery / compass review / feedback gate
- a full chat-orchestrator FSM rewrite across every conversational path

The backend state machine is still explicit and durable because workflow state is written into:
- plan-card metadata
- planning artifacts
- feedback-gate sessions
- drift-triggered intervention records
