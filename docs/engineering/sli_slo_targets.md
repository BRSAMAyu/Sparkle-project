# SLI/SLO Targets (M5)

Last updated: 2026-02-07

## SLI catalog

1. Availability
- Gateway availability (`up{job="sparkle_gateway"}`)
- Backend availability (`up{job="sparkle_backend"}`)

2. Reliability
- Backend 5xx ratio over 5m (`http_requests_total` based)

3. Latency
- Backend P95 HTTP latency (`http_request_duration_seconds_bucket`)

4. Event pipeline health
- Event stream lag (`sparkle_event_stream_lag_seconds`)

5. Budget stability
- Context-pack over-budget spikes (`sparkle_context_pack_over_budget_total`)

## SLO targets (initial)

- Gateway availability: >= 99.9%
- Backend availability: >= 99.9%
- Backend 5xx ratio: <= 2% (5m rolling)
- Backend P95 latency: <= 1.5s (5m rolling)
- Event stream lag: <= 120s

## Alerting mapping

- P1: service down (`SparkleGatewayDown`, `SparkleBackendDown`)
- P2: SLO breach (`SparkleBackendHigh5xxRate`, `SparkleBackendP95LatencyHigh`, `SparkleEventStreamLagHigh`)
- P3: optimization signal (`SparkleContextPackOverBudgetSpike`)

## Files

- Rules: `monitoring/sparkle_slo_alerts.yml`
- Prometheus load: `monitoring/prometheus.yml`
- Incident playbook: `monitoring/runbooks/incident_response.md`
