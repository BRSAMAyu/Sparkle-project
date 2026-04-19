# Sparkle Aurora Stage 6 Profile Eval Baseline (2026-04-19)

## Purpose

This document records the Stage 6 `WS-E1` evaluation skeleton baseline.
The goal is to create a read-only evaluation contract for profile-aware
assessment before any real LLM-backed evaluation runner is attached.

## Scope

`WS-E1` in Stage 6 only delivers:

- fixture shapes for profile-aware evaluation
- a minimal pytest harness that validates schema and intent
- a documented read-only boundary for future runners

`WS-E1` does **not** deliver:

- a real LLM evaluation runner
- writes into the profile fact layer
- writes into Aurora control parameters
- cohort analytics

## Fixture Families

Three baseline fixture families are defined:

1. `prediction_accuracy`
   Focus: whether prediction summaries line up with later observed evidence.

2. `calibration_effectiveness`
   Focus: whether corrected or promoted signals remain in the expected posture.

3. `freshness_validation`
   Focus: whether freshness labels remain aligned with evidence age.

## Read-Only Boundary

The evaluation skeleton is intentionally constrained:

- read input from cached / compiled profile outputs
- write only evaluation records in the future runner
- do not mutate raw evidence
- do not mutate profile facts
- do not mutate Aurora control state

This keeps `WS-E1` aligned with `Rule K` and the layered user-model architecture.

## Next Step

A later Stage 6 / Stage 7 runner may attach to these fixtures, but it must stay
within the documented `skeleton_only -> read-only runner` path.
