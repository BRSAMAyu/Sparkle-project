# Test Drift Guardrails

This document captures the minimum anti-drift protection expected for the
highest-risk parts of Sparkle.

## Risk Domains

### Python backend
- `backend/app/orchestration`
  - Required protection: unit logic tests, workflow resilience tests, fallback/breaker coverage
- `backend/app/core`
  - Required protection: routing policy tests, state/queue tests, contract tests for emitted metadata
- `backend/app/routing`
  - Required protection: strategy matrix tests for preference routing and downgrade behavior

### Go gateway
- `backend/gateway/internal/handler`
  - Required protection: HTTP/WebSocket contract tests, auth/rate-limit/error-shape checks
- `backend/gateway/internal/service`
  - Required protection: downstream failure tests, quota/cache semantics, command/query correctness
- `backend/gateway/internal/db`
  - Required protection: query/integration tests and schema-shape stability

### Flutter mobile
- `mobile/lib/features/chat`
  - Required protection: provider/repository tests, navigation smoke, chat regression widgets
- `mobile/lib/features/plan`
  - Required protection: provider/repository tests and plan-flow smoke
- `mobile/lib/core/network`
  - Required protection: DTO parsing and transport error handling

## Minimum Checklist For Critical Changes

When a PR changes a high-risk domain, it should include:

- At least one deterministic logic test for the changed decision path
- At least one contract assertion if external payload shape changed
- At least one workflow/smoke assertion if the user-visible path changed
- Updated snapshot/fixture when API or schema changes are intentional

## Current Automated Gates

- Global coverage thresholds in CI
- Path-scoped coverage thresholds from `quality/coverage_thresholds.json`
  - Note: Python/Go prefixes follow the paths emitted by their coverage reports
- OpenAPI drift check
- Focused risk suites:
  - Python `backend/tests/contract` and `backend/tests/workflow`
  - Go `internal/handler`, `internal/service`, `internal/db`
  - Flutter app/integration/regression smoke tests
