# CXP-26 Report — Observability, Metrics, Dashboards, And Runbooks

Date: 2026-05-02
Branch: `codex/CXP-26-observability-ops`

## User-Visible Outcome

Operators can now watch the product loops users actually feel: Aurora corrections, timeline/card actions, push usefulness, task completion, and community feed freshness. The team can move from "something seems off" to a concrete metric, dashboard panel, and runbook action without weakening product behavior or privacy boundaries.

## Changes Made

- Added low-cardinality product-loop Prometheus metrics in `backend/app/core/metrics.py`:
  - `sparkle_product_loop_event_total{loop,surface,outcome,reason}`
  - `sparkle_product_loop_latency_seconds{loop,surface,outcome}`
  - `sparkle_product_loop_items{loop,surface}`
  - `sparkle_aurora_correction_failure_total{surface,reason}`
- Instrumented user-impact flows:
  - Task completion success, idempotent completion, not-found completion attempts.
  - Aurora correction processor failures and timeline card actions.
  - Push open/dismiss/ignore interactions and invalid actions.
  - Community feed load, empty-feed, invalid-scope, item count, and latency.
- Added Grafana dashboard: `monitoring/grafana-dashboards/sparkle-product-loops.json`.
- Added Prometheus alerts in `monitoring/sparkle_slo_alerts.yml`.
- Expanded `monitoring/runbooks/incident_response.md` with alert-specific playbooks.
- Added metric initialization and label-sanitization tests in `backend/tests/unit/test_core_metrics.py`.

## Dashboard Panels And Queries

- Product Loop Event Rate:
  `sum(rate(sparkle_product_loop_event_total[10m])) by (loop, outcome)`
- Aurora Correction Effectiveness:
  `sum(rate(sparkle_aurora_correction_to_state_change_total{changed="true"}[30m])) / clamp_min(sum(rate(sparkle_aurora_correction_to_state_change_total[30m])), 0.001)`
- Push Fatigue Signal:
  `sum(rate(sparkle_product_loop_event_total{loop="push_judgment",outcome=~"dismissed|ignored"}[30m])) / clamp_min(sum(rate(sparkle_product_loop_event_total{loop="push_judgment"}[30m])), 0.001)`
- Card Actions And Failures:
  `sum(rate(sparkle_product_loop_event_total{loop="card_action"}[10m])) by (outcome, reason)`
- Task Completion Loop Health:
  `sum(rate(sparkle_product_loop_event_total{loop="task_execution",outcome="completed"}[30m])) / clamp_min(sum(rate(sparkle_product_loop_event_total{loop="task_execution"}[30m])), 0.001)`
- Community Empty Feed Ratio:
  `sum(rate(sparkle_product_loop_event_total{loop="community_feed",reason="empty"}[30m])) by (surface) / clamp_min(sum(rate(sparkle_product_loop_event_total{loop="community_feed"}[30m])) by (surface), 0.001)`
- Product Loop P95 Latency:
  `histogram_quantile(0.95, sum(rate(sparkle_product_loop_latency_seconds_bucket[10m])) by (le, loop, surface))`
- Community Feed Depth:
  `histogram_quantile(0.50, sum(rate(sparkle_product_loop_items_bucket{loop="community_feed"}[30m])) by (le, surface))`

## Alerts Added

- `SparkleAuroraCorrectionsNotTakingEffect`
- `SparkleCardActionFailuresHigh`
- `SparklePushFatigueHigh`
- `SparkleCommunityFeedEmptyHigh`
- `SparkleProductLoopLatencyHigh`

## Operational Scenarios

1. Symptom: users say Aurora ignores corrections.
   Metric: `sparkle_aurora_correction_to_state_change_total{changed="false"}` plus `sparkle_aurora_correction_failure_total`.
   Action: inspect correction receipts/run ledger, fix unmapped correction payloads or processor failures.

2. Symptom: AI cards look fine but actions do not work.
   Metric: `sparkle_product_loop_event_total{loop="card_action",outcome=~"failed|invalid"}`.
   Action: check Redis first for `redis_unavailable`, then compare mobile action payloads against allowed backend actions.

3. Symptom: proactive pushes feel annoying.
   Metric: negative push ratio from `sparkle_product_loop_event_total{loop="push_judgment",outcome=~"dismissed|ignored"}`.
   Action: lower proactive push volume for the dominant reason/surface, then verify the negative rate drops.

4. Symptom: community feels empty or stale.
   Metric: empty-feed ratio and item histogram for `sparkle_product_loop_event_total{loop="community_feed"}` and `sparkle_product_loop_items`.
   Action: verify eligible content after privacy/block/soft-delete filters; do not relax privacy filters to fill the feed.

5. Symptom: finishing tasks feels slow.
   Metric: `histogram_quantile(0.95, sum(rate(sparkle_product_loop_latency_seconds_bucket{loop="task_execution"}[10m])) by (le, surface))`.
   Action: inspect downstream plan, Galaxy, achievement, and next-action calls; make non-critical follow-ups async if they dominate latency.

6. Symptom: a feed or task loop regresses after release.
   Metric: product-loop event rate by `loop/outcome` and latency by `loop/surface`.
   Action: compare release window, isolate the surface, and roll back only the affected product path.

## Verification

- `cd backend && .venv/bin/python -m ruff check app/core/metrics.py app/api/v1/tasks.py app/api/v1/aurora.py app/api/v1/push_interaction.py app/api/v1/community.py tests/unit/test_core_metrics.py`
- `cd backend && .venv/bin/python -m pytest tests/unit/test_core_metrics.py`
- `backend/.venv/bin/python` YAML parse for `monitoring/sparkle_slo_alerts.yml` and `monitoring/prometheus.yml`
- `python3 -m json.tool monitoring/grafana-dashboards/sparkle-product-loops.json`

Note: `promtool` is not installed in this workspace, so Prometheus rule validation was limited to YAML parsing.
