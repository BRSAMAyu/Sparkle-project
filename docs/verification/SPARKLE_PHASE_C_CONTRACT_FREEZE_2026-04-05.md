# Sparkle Phase C Contract Freeze

> Date: 2026-04-05  
> Scope: Stable Phase C runtime contracts after the durability pass

## Stable Interfaces

Treat these as stable Phase C interfaces until a later explicit phase changes them with a compatibility note:

- `PlanOutcomeRecord`
  Source: `/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/plan_outcome_service.py`
- `OutcomeLearningReport`
  Source: `/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/outcome_learning_service.py`
- `validated_outcome_learning`
  Durable planning-facing truth stored in episode/profile state
- `planning_bridge`
  The planner-facing projection derived from validated learning
- `ALLOWED_HUMAN_EVAL_ISSUE_TAGS`
  Source: `/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/human_eval_review_service.py`

## Change Policy

- Field additions require a short migration note plus test updates in the Phase C regression pack.
- Field renames or removals are disallowed unless a later phase defines a compatibility plan.
- Raw `plan_outcome_records` and profile-ledger entries remain evidence inputs. Planning should read `validated_outcome_learning`, not raw ledgers.

## Evaluator Role Freeze

`PlanOutcomeEvaluator` is frozen in role as:

- regression harness
- scenario comparison tool

It is not frozen as product truth. Final truth for Phase C still comes from real human-eval runs and repeated live-cycle evidence.
