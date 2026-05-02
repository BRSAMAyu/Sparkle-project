# Sparkle E2E Acceptance & Launch Checklist

> Created: 2026-05-01 | C30 Final Acceptance
> Status: Scenarios defined, commands documented, gaps tracked

## Launch Readiness Summary

| Gate | Status | Owner |
|------|--------|-------|
| Core growth loop (C01-C04) | ✅ Wired & tested | C00 verified |
| Security & proto (C05-C09) | ✅ Hardened | C05-C09 closed |
| Aurora correction UX (C12) | ✅ Closed | C12 verified |
| Go gateway hardening (C14-C15) | ✅ Tests passing | C14/C15 closed |
| Flutter failures & UX (C16-C18) | ✅ Typed, tokenized, accessible | C16-C18 closed |
| OpenClaw & reviews (C19-C20) | ✅ Routed & tested | C19/C20 closed |
| i18n (C22) | ⚠️ Deferred to Wave 3 | Tracked |
| Legal & compliance (C25) | ✅ Docs created | C25 closed |
| Event system (C26) | ✅ Reconciled | C26 closed |
| Python exceptions (C27) | ✅ HIGH risk fixed | C27 closed |
| Flutter tech debt (C28) | ✅ SSE & API fixed | C28 closed |
| CI/CD hygiene (C29) | ✅ Actions updated | C29 closed |
| E2E scenarios (C30) | ⬜ This document | In progress |

---

## Scenario 1: New User → Onboarding → Goal → Plan → Task → Execution → Reflection

**Priority**: P0 — Core growth loop

### Steps
```
1. Launch Flutter app (fresh install)
2. Register new account (email + password)
3. Complete onboarding flow:
   a. Set nickname, avatar
   b. State learning goal (e.g., "Pass Calculus final exam in 3 weeks")
   c. Set study preferences (morning, visual learner)
4. Receive AI-generated staged plan
5. Review plan: approve first stage, request adjustment for second
6. Receive first executable task card
7. Mark task as completed
8. Receive reflection prompt
9. Write reflection note
10. Verify progress dashboard shows completion
```

### Verification Commands
```bash
# Backend: verify user created
docker compose exec sparkle_db psql -U postgres -d sparkle -c \
  "SELECT id, email, nickname, registration_source FROM users ORDER BY created_at DESC LIMIT 1;"

# Backend: verify plan created
docker compose exec sparkle_db psql -U postgres -d sparkle -c \
  "SELECT id, title, status FROM plans ORDER BY created_at DESC LIMIT 1;"

# Backend: verify task created and completed
docker compose exec sparkle_db psql -U postgres -d sparkle -c \
  "SELECT id, title, status, completion_rate FROM tasks ORDER BY updated_at DESC LIMIT 1;"

# Backend: verify reflection recorded
docker compose exec sparkle_db psql -U postgres -d sparkle -c \
  "SELECT COUNT(*) FROM task_reflections WHERE created_at > NOW() - INTERVAL '5 minutes';"
```

### Automated Coverage
- `backend/tests/orchestration/test_orchestrator_process_stream_integration.py` — live process stream tests
- `backend/tests/orchestration/test_orchestrator_process_stream_integration.py::test_process_stream_phase_a_hard_stops_cold_start_plan_before_planning`
- `backend/tests/unit/test_goal_quality_evaluator.py` — goal quality gating tests

### Status
| Step | Auto | Manual | Evidence |
|------|------|--------|---------|
| Registration flow | ⬜ | ⬜ | Manual only |
| Onboarding | ⬜ | ⬜ | Manual only |
| Plan generation | ✅ | ⬜ | integration test |
| Plan review (approve/reject) | ✅ | ⬜ | plan_review tests |
| Task execution | ⬜ | ⬜ | Manual only |
| Reflection | ⬜ | ⬜ | Manual only |
| Progress dashboard | ⬜ | ⬜ | Manual only |

---

## Scenario 2: Aurora Notices Risk → User Corrects → Aurora Learns → Future Response Changes

**Priority**: P0 — Core product trust path

### Steps
```
1. User has a task consistently delayed (3+ days past due date)
2. Aurora status band shows "stuck" energy level
3. Aurora sends proactive nudge about the stuck task
4. User taps nudge → chat opens with Aurora explanation
5. User provides correction: "I can't start because I need prerequisite knowledge"
6. Aurora records correction in correction feedback processor
7. Aurora adjusts future plan to add prerequisite tasks
8. Aurora's future responses reference the correction
9. Bayesian learner updates posterior confidence
```

### Verification Commands
```bash
# Backend: verify correction recorded
docker compose exec sparkle_db psql -U postgres -d sparkle -c \
  "SELECT * FROM correction_feedback WHERE created_at > NOW() - INTERVAL '1 hour' ORDER BY created_at DESC LIMIT 5;"

# Backend: verify Aurora intervention recorded
docker compose exec sparkle_db psql -U postgres -d sparkle -c \
  "SELECT * FROM intervention_records WHERE created_at > NOW() - INTERVAL '1 hour' LIMIT 5;"

# Backend: verify Bayesian posterior updated
docker compose exec sparkle_redis redis-cli KEYS "aurora:*bayesian*"
```

### Automated Coverage
- `backend/tests/unit/test_t33_predicted_reply_correction.py` — 38 correction tests
- `backend/tests/unit/test_aurora_bayesian_learner.py` — 4 Bayesian tests
- `backend/tests/unit/test_push_policy_compiler.py` — proactive nudge policy tests
- `mobile/test/features/aurora/data/services/aurora_telemetry_service_test.dart` — telemetry
- `mobile/test/widget/aurora_freeform_correction_dialog_test.dart` — correction UI

### Status
| Step | Auto | Manual | Evidence |
|------|------|--------|---------|
| Aurora detects stuck | ✅ | ⬜ | Bayesian learner test |
| Proactive nudge sent | ✅ | ⬜ | push_policy_compiler tests |
| User correction (freeform) | ✅ | ⬜ | correction UI tests |
| Correction recorded | ✅ | ⬜ | t33 tests |
| Aurora adjusts future plan | ✅ | ⬜ | adaptive_replanner tests |
| Bayesian posterior updates | ✅ | ⬜ | bayesian learner tests |

---

## Scenario 3: Document Upload → Knowledge/Galaxy Retrieval → Task Material Selection

**Priority**: P1 — Knowledge integration

### Steps
```
1. User uploads a PDF study document
2. Document is processed and indexed in Galaxy knowledge graph
3. Knowledge nodes are created from document content
4. User creates a task related to the document topic
5. Task material selector suggests relevant Galaxy nodes
6. User selects nodes as task reference materials
7. During task execution, Galaxy knowledge is retrieved for context
```

### Verification Commands
```bash
# Backend: verify document uploaded
docker compose exec sparkle_db psql -U postgres -d sparkle -c \
  "SELECT id, filename, status FROM documents ORDER BY created_at DESC LIMIT 5;"

# Backend: verify Galaxy nodes created
docker compose exec sparkle_db psql -U postgres -d sparkle -c \
  "SELECT id, name, node_type FROM galaxy_nodes WHERE created_at > NOW() - INTERVAL '1 hour' LIMIT 10;"

# Backend: verify RAG index updated
docker compose exec sparkle_redis redis-cli FT.SEARCH idx:rag "*" LIMIT 0 5
```

### Automated Coverage
- `backend/tests/acceptance/galaxy_plan_acceptance.py` — Galaxy+plan integration
- `backend/tests/acceptance/document_stt_acceptance.py` — document processing

### Status
| Step | Auto | Manual | Evidence |
|------|------|--------|---------|
| Document upload | ⬜ | ⬜ | Manual only |
| Galaxy indexing | ✅ | ⬜ | galaxy tests |
| Knowledge node creation | ✅ | ⬜ | galaxy tests |
| Task material selection | ⬜ | ⬜ | Manual only |
| RAG context retrieval | ✅ | ⬜ | graph_rag tests |

---

## Scenario 4: Community Share → Feed/Goal Mates/Following → Board/Task Handoff

**Priority**: P1 — Social features

### Steps
```
1. User shares a completed plan reflection to community feed
2. Post appears in followers' feeds
3. Goal mate sees post and sends encouragement
4. Goal mate creates a shared accountability check-in
5. User and goal mate create a shared board task
```

### Verification Commands
```bash
# Backend: verify community post created
docker compose exec sparkle_db psql -U postgres -d sparkle -c \
  "SELECT id, content, visibility FROM community_posts ORDER BY created_at DESC LIMIT 5;"

# Backend: verify accountability check-in
docker compose exec sparkle_db psql -U postgres -d sparkle -c \
  "SELECT * FROM accountability_checkins WHERE created_at > NOW() - INTERVAL '1 hour' LIMIT 5;"
```

### Automated Coverage
- `backend/tests/acceptance/community_acceptance.py`
- `backend/tests/acceptance/accountability_acceptance.py`

### Status
| Step | Auto | Manual | Evidence |
|------|------|--------|---------|
| Share to community | ⬜ | ⬜ | Manual only |
| Feed visibility | ⬜ | ⬜ | Manual only |
| Goal mate interaction | ⬜ | ⬜ | Manual only |
| Accountability check-in | ✅ | ⬜ | accountability tests |
| Board task handoff | ⬜ | ⬜ | Manual only |

---

## Scenario 5: Offline/Poor Network → Queued Action → Recovery

**Priority**: P1 — Resilience

### Steps
```
1. User opens chat with active WiFi
2. Turn off WiFi / enable airplane mode
3. User sends chat message (should enqueue locally)
4. User sees queued message indicator
5. User sends 3 more messages (all queued)
6. Turn WiFi back on
7. WebSocket reconnects
8. Queued messages are drained and sent
9. Messages appear in chat with sent status
```

### Verification Commands
```bash
# Flutter: verify offline queue (debug/dev mode)
# Check Isar DB for pending messages
cd mobile && flutter run --debug
# In app: turn off network, send messages, check offline indicator
```

### Automated Coverage
- `mobile/lib/core/offline/offline_message_queue_service.dart` — queue CRUD
- `mobile/lib/core/offline/models/offline_chat_message.dart` — state model

### Status
| Step | Auto | Manual | Evidence |
|------|------|--------|---------|
| Message enqueue on offline | ⬜ | ⬜ | Manual + Isar |
| Queue indicator visible | ⬜ | ⬜ | C28-001 tracked (no UI badge) |
| Reconnect on network restore | ⬜ | ⬜ | Manual only |
| Queue drain on reconnect | ⬜ | ⬜ | Manual + Isar |
| Messages marked as sent | ⬜ | ⬜ | Manual + Isar |

---

## Scenario 6: Production Deploy Smoke → Monitoring → Rollback/Drain

**Priority**: P0 — Operations

### Steps
```
1. Deploy to staging environment
2. Run health checks: gateway (:8080), API (:8000), gRPC (:50051)
3. Verify Prometheus metrics are scraping
4. Verify Grafana dashboards load
5. Verify Loki logs are flowing
6. Verify Tempo traces are available
7. Simulate gateway failure → verify Alertmanager fires
8. Perform drain: stop traffic, allow in-flight requests to complete
9. Perform rollback: revert to previous deployment
10. Verify service recovery
```

### Verification Commands
```bash
# Health checks
curl http://localhost:8080/api/v1/health
curl http://localhost:8000/api/v1/health
grpcurl -plaintext localhost:50051 list

# Prometheus metrics
curl http://localhost:9090/api/v1/targets | jq '.data.activeTargets[].labels'

# Grafana health
curl http://localhost:3000/api/health

# Loki ready
curl http://localhost:3100/ready

# Tempo ready
curl http://localhost:4317/ready  # gRPC
curl http://localhost:3200/ready  # HTTP

# Alertmanager
curl http://localhost:9093/api/v2/status

# Drain simulation (via make)
make gateway-drain

# Full signoff
make local-final-signoff
```

### Automated Coverage
- Monitoring SLO alerts: 11 alert rules in `monitoring/prometheus/alerts.yml`
- Runbook: `monitoring/runbooks/incident_response.md`
- DR runbook: `docs/ops/disaster_recovery_runbook.md`

### Status
| Step | Auto | Manual | Evidence |
|------|------|--------|---------|
| Staging deploy | ⬜ | ⬜ | Manual ops |
| Health checks | ✅ | ⬜ | make smoke |
| Prometheus scraping | ✅ | ⬜ | targets API |
| Grafana dashboards | ⬜ | ⬜ | Manual login |
| Loki logs | ⬜ | ⬜ | Manual query |
| Tempo traces | ⬜ | ⬜ | Manual query |
| Alertmanager fires | ⬜ | ⬜ | Simulate failure |
| Drain procedure | ✅ | ⬜ | make gateway-drain |
| Rollback procedure | ⬜ | ⬜ | Manual ops |
| Recovery verification | ⬜ | ⬜ | Manual smoke |

---

## Known Blockers

| ID | Issue | Impact | Resolution |
|----|-------|--------|-----------|
| FLUTTER-CHAT-SYNTAX | `chat_screen.dart` has syntax errors (unmatched parentheses L1374-1531) | Blocks all Flutter tests | C12 dirty worktree — coordinate with C00 |
| GW-SERVICE-TEST | `internal/service` chat history test expects "Calculus review" but gets `chat_history.new_conversation` | Blocks `go test ./...` | Known C14 finding, separate fix needed |
| C28-001 | No offline queue UI indicator | User doesn't see queued message count | Tracked for follow-up |
| C28-002 | BGM service not split | 3,494-line monolith | Tracked for refactor |

---

## Remaining Manual Ops Items

| Item | Category | Priority |
|------|----------|----------|
| First staging deploy with real secrets | Deployment | P0 |
| First backup taken and verified | DR | P0 |
| First restore drill completed | DR | P1 |
| TLS certificate provisioning for prod domain | Infra | P0 |
| SMTP setup for notification emails | Infra | P1 |
| Real API keys rotated from placeholder values | Security | P0 |
| Production monitoring alert channels configured | Monitoring | P0 |
| App store submission (iOS + Android) | Release | P1 |

---

## Automated Coverage Summary

| Layer | Test Files | Tests | Key Acceptance |
|-------|-----------|-------|---------------|
| Python | 3214+ | 21 acceptance scripts | AI chat, Galaxy, Community, Aurora, Exam Sprint |
| Go | 34 | Handler, middleware, agent | WS/STT hardening, middleware auth/rate-limit |
| Flutter | 131+ | Widget, golden, integration | Aurora correction, accessibility, design system, failures |

---

## Final Integrator Decision Items

These items were identified during C25-C30 closeout and require C00 decision:

1. **Dual event systems**: Python EventBus + Go CQRS + Redis Pub/Sub co-exist. Should they be unified? C00 to decide architectural direction.
2. **17 consumerless event types**: 61% of `event_types.py` constants are published but never consumed. Intentional instrumentation or dead code? 
3. **`mastery_updated_from_error`**: Published by `galaxy_service.py` but no consumer. Missing integration or orphaned event?
4. **Flutter chat_screen.dart merge**: C12 dirty worktree blocks all Flutter tests. C00 must resolve merge before final acceptance.
5. **Offline queue UI indicator**: Queue infrastructure exists, but `pendingCount()` is never called from UI. Implement or defer?
