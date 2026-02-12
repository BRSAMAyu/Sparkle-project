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

## P3: ContextPackOverBudgetSpike

1. Review recent prompt/context budget policy changes.
2. Sample traces to identify oversized context sources.
3. Create optimization backlog and monitor trend over 24h.

## Post-incident checklist

1. Document timeline, root cause, blast radius, and mitigation.
2. Add regression test or gate preventing recurrence.
3. Update this runbook if playbook changed.
