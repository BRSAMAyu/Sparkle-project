# Incident Post-Mortem Template — T6.3.3

> Copy this template for each incident. Fill within 48 hours of resolution.

## Incident Summary

| Field | Value |
|-------|-------|
| Incident ID | INC-YYYY-NNN |
| Date | YYYY-MM-DD |
| Duration | Xm Ys |
| Severity | P1 (Critical) / P2 (Warning) / P3 (Info) |
| Affected Services | e.g., Gateway, API, gRPC |
| Impact | e.g., "500 users unable to send chat messages for 15 minutes" |
| Responder(s) | Names |
| Detected by | Alert name / User report / Monitoring |

## Timeline (UTC)

| Time | Event |
|------|-------|
| HH:MM | First alert fired / User report |
| HH:MM | Investigation started |
| HH:MM | Root cause identified |
| HH:MM | Mitigation applied |
| HH:MM | Service restored |
| HH:MM | All-clear confirmed |

## Root Cause Analysis

### What happened?
[1-2 paragraphs describing the technical failure]

### Why did it happen?
[Contributing factors — not blame, just technical causes]

### 5 Whys (if applicable)
1. Why did the service fail? → [Answer]
2. Why did [Answer 1] happen? → [Answer]
3. Why did [Answer 2] happen? → [Answer]
4. Why did [Answer 3] happen? → [Answer]
5. Why did [Answer 4] happen? → [Answer]

## Resolution

### Immediate fix
[What was done to restore service]

### Permanent fix
[What will be done to prevent recurrence]

## Action Items

| # | Action | Owner | Priority | Due Date | Status |
|---|--------|-------|----------|----------|--------|
| 1 | e.g., Add circuit breaker for Redis | | P1 | YYYY-MM-DD | Open |
| 2 | e.g., Add alert for high connection pool usage | | P2 | YYYY-MM-DD | Open |
| 3 | e.g., Update runbook with new procedure | | P2 | YYYY-MM-DD | Open |

## Lessons Learned

1. **What went well?** e.g., Alert fired within 30s, runbook was clear
2. **What could be improved?** e.g., Took 10 minutes to find relevant logs
3. **Where did we get lucky?** e.g., Happened during low-traffic hours

## Monitoring Gaps Identified

- [ ] Gap 1: e.g., No alert for Redis connection pool exhaustion
- [ ] Gap 2: e.g., No SLO tracking for this service

---

## Metrics

| Metric | Value |
|--------|-------|
| MTTR (Mean Time To Resolve) | Xm |
| MTTD (Mean Time To Detect) | Xm |
| Error budget consumed | X% |
| Users affected | X |
| Revenue impact | $X (if applicable) |

---

*Template version: 1.0 | Last updated: 2026-04-29*
