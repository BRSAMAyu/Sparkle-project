# Stage 23 EventBus Baseline

Date: 2026-04-21

- New event types introduced by Stage 23: `0`
- Stage 23 reuses existing routing decision and outcome backfill paths.
- `routing_decision_log` remains the primary persistence surface.
- Bayesian routing wire emits Prometheus telemetry only; it does not add EventBus topics.
