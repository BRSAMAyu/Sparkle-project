# Definition of Done (Industrial Release Program)

Last updated: 2026-02-07

A change is considered done only when all conditions below are satisfied.

## 1. Correctness

- Relevant unit/integration/e2e tests pass locally.
- No regression in core chains (gateway <-> gRPC <-> backend <-> mobile).

## 2. Quality gates

- No new `P0`/`P1` warnings introduced.
- Technical debt metrics do not exceed budget (`check_tech_debt_budget.py`).
- Contract-sensitive changes include compatibility checks.

## 3. Operability

- Health endpoints remain green (`/health`, `/api/v1/health`, `/api/v1/health/cqrs`).
- Rollback path is explicit in PR/change notes.

## 4. Security/compliance

- No secrets in code.
- Dependency/security checks pass CI gates.

## 5. Evidence

- Include command evidence in PR description:
  - `pytest` / `go test` / `flutter test` results
  - Gate outputs (coverage + debt budget)
  - Impacted interfaces list (if any)

## 6. Freeze policy

- Feature-freeze period allows only non-breaking quality/stability/security/operability changes.
- Any functional expansion must be approved via ADR + migration plan.
