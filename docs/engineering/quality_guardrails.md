# Quality Guardrails (M1)

This document defines the baseline quality constraints introduced in Milestone M1.

## Coverage Gates

CI now enforces minimum coverage thresholds and fails the job when any threshold is not met.

- Go: `65%`
- Python: `25%`
- Flutter: `8%`

Implementation:
- Workflow: `.github/workflows/ci.yml`
- Checker: `scripts/check_coverage_thresholds.py`

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
