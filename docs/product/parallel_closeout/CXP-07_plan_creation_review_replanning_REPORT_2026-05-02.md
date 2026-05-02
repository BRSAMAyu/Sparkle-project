# CXP-07 Report - Plan Creation, Review, And Replanning

## Mission
Make plan generation and replanning feel more like a competent coach: goals should become realistic plans with visible daily capacity, review cadence, first action, and honest tradeoffs when the requested schedule is not credible.

## What Changed
- Added schedule-feasibility signals to `PlanningStrategyCompiler`: `workload_fit`, `feasibility_flags`, and `first_review_after_days`.
- Threaded those signals into the plan quality contract so full/provisional plan validation can see capacity, review cadence, and deadline risk.
- Updated `PlanQualityGate` to downgrade or revise plans that present impossible or under-specified schedules as confident plans.
- Added a deterministic feasibility guard in `PlanReviewService` for plan/sprint/schedule/task creation tool calls. It blocks contradictions like "1 hour/day, 7 days, expert/mastery target" before LLM review or high confidence can make the plan look safe.
- Added quality fix hints so user-visible review feedback says how to recover: shrink scope, lower target level, increase time, or add daily review/fallback rules.

## User-Visible Journey
1. User says: "I need to pass X" or "I want to learn Y."
2. The compiler derives the plan mode, deadline window, daily capacity, pacing profile, review cadence, and workload fit.
3. If the goal is plausible, the plan can proceed with a first action and the first review point.
4. If the schedule is tight, the review result warns that the plan needs a short review cadence and a scope-reduction fallback.
5. If the schedule is impossible, the review result blocks auto-approval and tells the user the time, target, and capacity do not match.
6. When reality changes, the existing replanning path can consume the same capacity/review signals instead of silently mutating the plan without an explanation.

## Acceptance Evidence
- Goal → plan: `PlanningStrategyCompiler` now emits workload and review metadata for downstream planning surfaces.
- First task/review: `first_review_after_days` and `checkpoint_cadence` give the product a concrete first review point for generated plans.
- Reality change → replan: quality/review comments require scope reduction or review cadence when time pressure makes the original plan unsafe.
- Impossible schedule: deterministic review catches “一周精通 C++ / 每天 1 小时” and returns `needs_modification`, not auto-approval.

## Verification
- `cd backend && ruff check app/orchestration/planning_strategy_compiler.py app/orchestration/plan_quality_gate.py app/orchestration/plan_quality_contract.py app/orchestration/plan_review_service.py tests/unit/test_planning_strategy_compiler.py tests/services/test_plan_review_service.py`
- `python3 -m py_compile backend/app/orchestration/planning_strategy_compiler.py backend/app/orchestration/plan_quality_gate.py backend/app/orchestration/plan_quality_contract.py backend/app/orchestration/plan_review_service.py`
- `cd backend && pytest tests/unit/test_planning_strategy_compiler.py tests/services/test_plan_review_service.py -q`
- `cd backend && pytest tests/test_planning_hitl_chain.py -q`

## Notes And Handoff
- I kept this inside existing planning/review/quality-gate services instead of adding a second planner.
- This does not redesign mobile plan screens. The new fields are backend contract signals that mobile can surface in plan cards, review banners, or replan summaries.
- Existing HITL chain tests emit LangGraph typing warnings unrelated to this change.
