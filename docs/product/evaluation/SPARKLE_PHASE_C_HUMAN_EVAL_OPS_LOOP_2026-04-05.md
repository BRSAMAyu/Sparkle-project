# Sparkle Phase C Human Eval Ops Loop

> Date: 2026-04-05  
> Scope: Phase C `C5` operational loop for transcript review

## Goal

Turn transcript review from a passive summary into an operational product loop that can:

- normalize issue tags
- detect repeated failures
- emit backlog candidates
- flag release blockers for repeated serious issues

## Runtime Entry Points

- Service: `/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/human_eval_review_service.py`
- Script: `/Users/brsama/code/GitHub/Sparkle-project/scripts/review_human_eval_run.py`

## Operating Cadence

1. Run review on a human-eval payload.
2. Generate the normalized summary.
3. Generate the ops report.
4. Open backlog items for repeated failures.
5. Block the next pilot when release blockers are present.

## Default Thresholds

- repeated failure threshold: `2`
- release blocker threshold: `3`

High-severity tags such as `diagnosis_wrong` and `grounding_weak` should be treated as blocker candidates even before broad tag sprawl appears.
