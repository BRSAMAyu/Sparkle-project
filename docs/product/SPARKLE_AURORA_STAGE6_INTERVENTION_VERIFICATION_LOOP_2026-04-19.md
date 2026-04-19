# Sparkle Aurora Stage 6 Intervention Verification Loop (2026-04-19)

## Purpose

This document records the minimal `WS-VR1` closure landed in Stage 6:

`intervention -> outcome verification -> explicit verification payload`

## What `WS-VR1` Adds

The intervention pipeline already had:

- `InterventionRecordService`
- `InterventionOutcomeVerifier`
- pending/effective/ineffective outcome transitions

`WS-VR1` makes the verification result explicit by ensuring resolved
interventions carry a `verification` block inside `evidence_payload`.

That block records:

- `verdict`
- `resolved_at`
- `resolved_via`

## Why This Matters

The loop is no longer only implicit in status transitions.

Stage 6 now has a stable, testable place to inspect the outcome-verification
result without changing raw evidence or introducing a new write lane.

## Boundary

`WS-VR1` does **not**:

- redesign the intervention schema
- add cohort analytics
- write back into profile facts
- change Aurora control parameters

It only makes the existing verification outcome explicit and testable.
