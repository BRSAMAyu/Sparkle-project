# Sparkle Soul Drift Evaluation Harness

## Purpose

This harness is meant to tell the difference between:

- governed companion growth
- stylized personality drift

The core rule is simple: more vivid does not automatically mean better.

## What It Evaluates

### Companion Integrity

The evaluator scores six companion-side dimensions:

1. `consistency`
2. `independence`
3. `vividness`
4. `continuity`
5. `growth`
6. `governability`

### Product Value

The evaluator separately scores four user-facing value dimensions:

1. `residual_resolution`
2. `leap_support`
3. `freedom_preservation`
4. `felt_understanding`

This split matters because Sparkle can look more alive while becoming less useful.

## Drift Alarms

The first version explicitly monitors:

1. warmth rising while candor falls
2. relationship stage escalating too fast
3. self-authored notes becoming stylized
4. constitution-adjacent proposals appearing repeatedly
5. vividness climbing while outcomes stay flat or fall
6. self-authored note volume growing without outcome improvement

These are early warnings, not final verdicts.

## Backend Helper

Runtime evaluation lives in [soul_drift_evaluator.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/soul_drift_evaluator.py).

It produces:

- companion integrity scorecard
- product value scorecard
- `drift_score`
- `drift_indicators`
- structured alarm payloads
- a simple recommendation:
  `continue`, `monitor_closely`, or `investigate_drift`

The score shape intentionally mirrors the existing planning drift assessment style so it can later be surfaced in the same operational flows.

## Synthetic Fixtures

Synthetic scenarios live in [soul_drift_scenarios.json](/Users/brsama/code/GitHub/Sparkle-project/backend/tests/fixtures/soul_drift_scenarios.json).

They currently cover:

1. healthy governed growth
2. stylized vividness drift
3. constitution-adjacent silent drift

These fixtures are designed to be extended as the companion runtime becomes more real.

## How To Run

Use:

```bash
cd backend && pytest tests/unit/test_soul_drift_evaluator.py
```

For a broader regression slice:

```bash
cd backend && pytest tests/unit/test_soul_drift_evaluator.py tests/unit/test_soul_compiler.py tests/unit/test_companion_state_service.py
```

## Current Limits

This first harness is heuristic, not model-judged.

It does not yet:

1. call an LLM evaluator
2. compare live production cohorts
3. score raw assistant text directly
4. trigger automated rollback

It is a governed early-warning layer meant to make silent drift legible before the system starts optimizing the wrong thing.
