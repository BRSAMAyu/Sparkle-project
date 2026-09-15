# Quality Guardrails (M1)

This document defines the baseline quality constraints introduced in Milestone M1.

## Coverage Gates (Current Baseline)

CI now enforces minimum coverage thresholds and fails the job when any threshold is not met.

- Go: `4%`
- Python: `25%`
- Flutter: `8%`

CI now also enforces directory-scoped risk thresholds from `quality/coverage_thresholds.json`.
This prevents low-risk files from hiding gaps in the highest-risk paths.

Current scoped gates:
- Python: `app/core`, `app/orchestration` (coverage-report relative paths)
- Go: `internal/handler`, `internal/service` (coverage-report relative paths)
- Flutter: `mobile/lib/features/chat`, `mobile/lib/core/network`

Implementation:
- Workflow: `.github/workflows/ci.yml`
- Checker: `scripts/check_coverage_thresholds.py`
- Rules file: `quality/coverage_thresholds.json`

Planned ratchet (industrial program):
- Phase A: Go `20%`, Python `40%`, Flutter `20%`
- Phase B: Go `35%`, Python `55%`, Flutter `40%`

## Risk Suites

CI now runs focused risk suites in addition to the broad test sweep.

- Python: `backend/tests/contract`, `backend/tests/workflow`
- Go: `internal/handler`, `internal/service`, `internal/db`
- Flutter: app smoke, integration smoke, selected regression widgets

These suites are intended to catch behavioral drift during upgrades and refactors,
even when aggregate coverage changes only slightly.

## Anti-Drift Contracts

The following contracts are enforced or wired into CI:

- OpenAPI snapshot drift check via `scripts/check_openapi_contract.py`
- Coverage path thresholds via `scripts/check_coverage_thresholds.py`
- Redis/state-manager key and payload contract tests under `backend/tests/contract`
- Orchestrator resilience workflow tests under `backend/tests/workflow`

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
