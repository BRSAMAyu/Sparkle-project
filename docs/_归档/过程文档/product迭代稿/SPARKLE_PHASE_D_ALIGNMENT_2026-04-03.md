# Sparkle Card Protocol — Phase D Alignment Report

Date: 2026-04-03
Status: COMPLETE (backend scope)

## Objective

Phase D upgrades the system from "default-initialized planning artifacts" to a real discovery-driven planning pipeline:

1. Multi-turn discovery collects user reality before plan design
2. Discovery is materialized as `DISCOVERY_DOSSIER`
3. `GLOBAL_COMPASS` is built from the dossier, not from defaults
4. Compass requires explicit user approval
5. Phase architecture is generated as a reviewable `PHASE_BLUEPRINT`
6. Approved blueprint materializes real `PHASE` cards and enters `PHASE_DESIGN`

## Deliverables

### 1. Discovery conversation pipeline

File:
- `backend/app/orchestration/discovery_manager.py`

What it does:
- Starts Redis/cache-backed discovery sessions
- Tracks structured `DiscoveryState`
- Computes sufficiency and missing dimensions
- Generates next-question guidance
- Finalizes into:
  - a new legacy `Plan`
  - canonical `PLAN` card projection
  - approved `DISCOVERY_DOSSIER`
  - proposed dossier-driven `GLOBAL_COMPASS`

Workflow states emitted in responses / plan metadata:
- `DISCOVERY_ACTIVE`
- `COMPASS_REVIEW`
- `PHASE_SKETCH_REVIEW`
- `PHASE_DESIGN`

### 2. Real compass review flow

File:
- `backend/app/services/card_protocol/global_compass_manager.py`

What changed:
- Added `build_compass_from_dossier(...)`
- Added `present_compass_for_review(...)`
- Added `user_approve_compass(...)`

Behavior:
- Keeps Phase 3 default-initialization behavior intact
- Creates a new dossier-driven compass version instead of mutating the default one
- Requires explicit approval before downstream phase design
- Syncs workflow metadata back to the `PLAN` card

### 3. Phase sketch generation and materialization

File:
- `backend/app/orchestration/phase_sketch_service.py`

What it does:
- Generates reviewable `PHASE_BLUEPRINT` artifacts from:
  - approved `GLOBAL_COMPASS`
  - approved `DISCOVERY_DOSSIER`
- Materializes real `PHASE` cards from blueprint payload
- Activates the first phase automatically
- Updates `STRATEGY_MAP` with phase architecture metadata
- Moves the plan into `PHASE_DESIGN`

### 4. Phase D API surface

File:
- `backend/app/api/v1/plans.py`

New endpoints:
- `POST /api/v1/plans/discovery/start`
- `POST /api/v1/plans/discovery/{session_id}/turn`
- `POST /api/v1/plans/discovery/{session_id}/finalize`
- `GET /api/v1/plans/{plan_id}/compass/review`
- `POST /api/v1/plans/compass/{artifact_id}/approve`
- `POST /api/v1/plans/{plan_id}/phase-sketch/generate`
- `POST /api/v1/plans/{plan_id}/phase-sketch/{artifact_id}/materialize`

Guardrails added:
- Phase sketch generation is blocked while a compass review is still pending
- Phase sketch generation requires an `APPROVED` compass

## Closed-loop result

Phase D now supports this backend flow:

`vague goal -> discovery session -> dossier -> reviewable compass -> approved compass -> reviewable phase sketch -> real phases -> phase design state`

This closes the biggest Phase 3 gap:
- `DISCOVERY_DOSSIER` is no longer only an enum value

## Verification

Compile:
- `python3 -m compileall backend/app/orchestration/discovery_manager.py backend/app/orchestration/phase_sketch_service.py backend/app/services/card_protocol/global_compass_manager.py backend/app/api/v1/plans.py backend/tests/unit/test_phase_d_discovery_pipeline.py`

Targeted Phase D tests:
- `cd backend && pytest tests/unit/test_phase_d_discovery_pipeline.py -q`

Regression:
- `cd backend && pytest tests/unit/test_card_operations_service.py tests/unit/test_card_protocol_phaseb.py tests/unit/test_card_protocol_phasec.py tests/unit/test_phase_d_discovery_pipeline.py -q`

Result:
- `16 passed`

## Notes

This report marks Phase D as backend-complete.

Not included in this pass:
- mobile discovery UI
- chat-orchestrator full FSM rewrite

Instead, workflow-state transitions are now represented explicitly in:
- discovery responses
- plan-card metadata
- planning artifact progression

That keeps the system implementation-safe while preserving a clean upgrade path for Phase E.
