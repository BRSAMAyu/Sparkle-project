# Sparkle Incident Response Runbook

## Alert tiers

- `P1` Immediate response (service unavailable / critical path down)
- `P2` Same-day response (SLO breach)
- `P3` Observe + scheduled remediation

## P1: GatewayDown

1. `docker compose ps` and confirm `sparkle_gateway` status.
2. Check logs: `docker compose logs --since=10m gateway`.
3. Validate downstreams: `curl -f http://localhost:8080/api/v1/health`.
4. If unhealthy after restart, switch traffic to previous blue/green color and rollback image tag.

## P1: BackendDown

1. Check backend and agent containers: `docker compose ps backend sparkle_agent`.
2. Inspect logs: `docker compose logs --since=10m backend sparkle_agent`.
3. Verify DB/Redis health and credentials.
4. If startup regression confirmed, rollback image and re-run smoke checks.

## P2: BackendHigh5xxRate

1. Query failing endpoints from logs/trace IDs.
2. Correlate with release window and recent migrations.
3. If concentrated in one endpoint, apply route-level circuit breaker / temporary mitigation.
4. Open hotfix issue with impact scope and rollback plan.

## P2: BackendP95LatencyHigh

1. Verify DB pool saturation and slow query logs.
2. Inspect Redis latency and queue backlog.
3. Check LLM upstream latency and fallback rate.
4. If needed, reduce expensive background jobs or scale workers.

## P2: EventStreamLagHigh

1. Inspect consumer health and stream group state.
2. Check Redis CPU/memory and pending list growth.
3. Restart lagging consumers; validate lag drops under threshold.

## P2: Spine Degradation

1. Check backend logs for `Spine signal check degraded` and group by exception reason.
2. Verify Redis health first, then inspect recent changes to `spine_orchestrator.py` and directive stores.
3. Confirm chat responses include `spine_degraded=true` metadata so UX can degrade visibly.
4. If degradation persists, keep chat fallback live and roll back the latest Spine change.

## P2: AI First Token Latency High

1. Check AI ops dashboard by `chat_mode` and `reasoning_mode`.
2. Inspect provider health, fallback rate, and recent routing changes.
3. If only one mode regressed, temporarily lower its routing tier.
4. If all modes regressed, inspect gateway first-event latency and upstream LLM status.

## P2: AI Total Duration High

1. Confirm whether the regression is isolated to `study_plan / deep_analysis / error_diagnosis`.
2. Inspect retrieval latency, tool-call count, and review-node blocking.
3. Reduce expensive background jobs or lower high-cost AI mode usage temporarily.
4. Roll back the recent prompt/routing change if regression is confirmed.

## P2: Prediction Rules Fallback Spike

1. Check `free` and `free_fast` provider availability and timeout trends.
2. Verify whether 429 or upstream latency caused the spike.
3. Keep rules fallback enabled and reduce front-end dependency on AI prediction until recovered.

## P2: Outbox Backlog High

1. Check DB write pressure and Redis health.
2. Inspect consumer lag and DLQ growth.
3. Pause non-critical async fan-out until backlog drops.

## P2: Backend Memory High

1. Determine whether growth is traffic-driven or leak-like.
2. Check cache growth, batch jobs, and worker side effects.
3. Drain and recycle the unhealthy instance if memory keeps climbing.

## P3: Gateway Goroutines High

1. Inspect reconnect storms, blocked upstream calls, and duplicate client sessions.
2. Check logs for retry loops or websocket fan-out anomalies.
3. Drain traffic and restart the unhealthy color if needed.

## P3: ContextPackOverBudgetSpike

1. Review recent prompt/context budget policy changes.
2. Sample traces to identify oversized context sources.
3. Create optimization backlog and monitor trend over 24h.

## Product Loop Observability

Primary dashboard: `Sparkle Product Loop Operations` (`monitoring/grafana-dashboards/sparkle-product-loops.json`).

## P2: Aurora Corrections Not Taking Effect

1. Open the product loop dashboard and compare `sparkle_aurora_correction_to_state_change_total{changed="false"}` by `surface` and `action`.
2. Sample recent correction receipts from `/api/v1/admin/observability/responses/{response_id}` or Redis `aurora:last_correction_effect:*`.
3. If a surface is sending vague or unmapped corrections, disable that correction chip/surface copy until the semantic payload maps to profile/state updates.
4. If writes are failing, check `sparkle_aurora_correction_failure_total` and backend logs for `Correction feedback processing failed`.

## P2: Card Action Failures High

1. Inspect `sparkle_product_loop_event_total{loop="card_action"}` by `outcome` and `reason`.
2. If `redis_unavailable`, verify Redis health before debugging card rendering.
3. If `bad_action`, compare mobile card action payloads with the backend action contract: `confirm`, `correct`, `partial`, `dismiss`.
4. Sample affected traces from the run ledger and keep card rendering live if failures are isolated to one action.

## P2: Push Fatigue High

1. Inspect `sparkle_product_loop_event_total{loop="push_judgment"}` split by `opened`, `dismissed`, and `ignored`.
2. Check wake/push policy changes, quiet-hour config, cooldowns, and recent campaign or scheduler changes.
3. Temporarily lower proactive push volume for the dominant reason/surface while preserving critical reminders.
4. Confirm the negative interaction rate drops before restoring normal push policy.

## P3: Community Feed Empty High

1. Inspect empty ratio by `surface` (`global`, `squad`, `goal_mates`, `following`).
2. Verify whether the scope has real eligible content after soft-delete, block, privacy, and friendship filters.
3. If content exists but does not render, inspect community API logs and recent query/filter changes.
4. If content genuinely does not exist, schedule seed/recommendation work instead of relaxing privacy filters.

## P3: Product Loop Latency High

1. Check the product loop latency panel by `loop` and `surface`.
2. For `community_feed`, inspect database query plans and pagination/filter fan-out.
3. For `task_execution`, inspect downstream plan, Galaxy, achievement, and next-action calls.
4. For `card_action` or `push_judgment`, verify Redis latency and avoid blocking the user on non-critical telemetry.

## Post-incident checklist

1. Document timeline, root cause, blast radius, and mitigation.
2. Add regression test or gate preventing recurrence.
3. Update this runbook if playbook changed.
