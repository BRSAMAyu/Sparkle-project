# Sparkle Phase B Planning Baseline Audit

> Date: 2026-04-05  
> Scope: Phase B `B0` baseline audit, rubric, and harness entrypoint

## Current Planning Entry Points

- `backend/app/api/v1/plans.py`
  - direct plan creation endpoints
- `backend/app/orchestration/validation_engine.py`
  - Phase A readiness gate and ask/provisional/full-plan branching
- `backend/app/orchestration/lang_graph_planner.py`
  - executable planning path that emits `ExecutablePlan`
- `backend/app/orchestration/plan_review_service.py`
  - current safety/alignment review path
- `backend/app/orchestration/adaptive_replanner.py`
  - revision/adaptation path after execution drift

## Baseline Reading of Current Gaps

- Sparkle already has a real Phase A readiness guardrail, but it did not yet expose one canonical Phase B plan-quality contract.
- Planning strategy was partly implicit in prompt/context shape and persona constraints, not compiled into one deterministic read model.
- Review logic focused on safety, alignment, and feasibility of executable steps, but not yet on explicit plan-quality coverage.
- Replanning preserved adaptation history, but not an explicit “what changed / what stays / new next action” revision summary.
- Benchmark proof against mixed-provider raw-model baselines was not yet codified as a reusable harness.

## Phase B Benchmark Dossiers

- `phase_b_thermo_14_day_sprint`
- `phase_b_overloaded_urgent_user`
- `phase_b_materials_and_weak_spots`
- `phase_b_contradictory_self_report`
- `phase_b_vague_goal_needs_clarification`
- `phase_b_missed_execution_replan`
- `phase_b_high_readiness_full_plan`
- `phase_b_medium_readiness_provisional`

Fixture file:

- `/Users/brsama/code/GitHub/Sparkle-project/backend/tests/fixtures/planning_benchmark_scenarios.json`

## Rubric V1

Each scenario should be scored on:

- `understanding_fit`
- `constraint_realism`
- `plan_sequence_quality`
- `grounding_quality`
- `next_action_usefulness`
- `adaptation_fallback_quality`
- `non_expert_usability`
- `trustworthiness`

## Mixed-Provider Baseline Rule

- Baseline A: `dashscope_chat`
- Baseline B: `deepseek_chat`
- Both baselines receive the same dossier payload and the same raw direct-planning prompt structure.
- Sparkle Phase B is measured as a system-level planning stack, which means its benchmark prompt may include compiled planning strategy derived from dossier-side readiness inputs.
- Live runs must fail fast if either provider is not configured.

## Harness Entry

Service:

- `/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/planning_benchmark_service.py`

Current supported run types:

- `sparkle_current`
- `sparkle_phase_b`
- `raw_baseline`

## Suggested Execution Flow

1. Load dossiers from the fixture file.
2. Capture `sparkle_current` output.
3. Capture `sparkle_phase_b` output.
4. Capture both raw-model baselines.
5. Generate scorecards for automated review.
6. Treat the resulting report as `benchmark proof v1`, not final superiority truth.
7. Escalate to human evaluation if benchmark outcomes and product judgment diverge repeatedly.

## Command Notes

Unit-level verification:

```bash
cd backend
pytest tests/unit/test_planning_benchmark_service.py -v
```

The live benchmark harness intentionally depends on configured provider credentials and is not expected to run in CI by default.
