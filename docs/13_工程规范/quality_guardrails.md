# Quality Guardrails (M1)

This document defines the baseline quality constraints introduced in Milestone M1.

## Coverage Gates (Current Baseline)

CI now enforces minimum coverage thresholds and fails the job when any threshold is not met.

- Go: `4%`
- Python: `25%`
- Flutter: `8%`

Implementation:
- Workflow: `.github/workflows/ci.yml`
- Checker: `scripts/check_coverage_thresholds.py`

Planned ratchet (industrial program):
- Phase A: Go `20%`, Python `40%`, Flutter `20%`
- Phase B: Go `35%`, Python `55%`, Flutter `40%`

## Technical Debt Budget Gate

Feature-freeze period requires **no debt increase** on tracked warning metrics.

Implementation:
- Budget file: `quality/tech_debt_budget.json`
- Checker: `scripts/check_tech_debt_budget.py`
- Baseline snapshot: `scripts/collect_quality_baseline.py`
- CI gate: `.github/workflows/ci.yml` (`Technical Debt Budget Gate` step)

## Async Task Policy

Fire-and-forget tasks are not allowed for critical persistence paths.

Required pattern:
- Track pending tasks in a set.
- Register done callbacks to remove completed tasks.
- Provide an explicit `drain`/`shutdown` method and call it during teardown.

Current adopters:
- `backend/app/learning/persistent_bayesian_learner.py`
- `backend/app/learning/multi_dimensional_learner.py`

## Local Cache Fallback Policy

When Redis is unavailable, local in-memory cache must:

- Apply TTL per entry.
- Periodically clean expired entries.
- Enforce a max-entry cap to avoid unbounded memory growth.

Current implementation:
- `backend/app/core/cache.py`
