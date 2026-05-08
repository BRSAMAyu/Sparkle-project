# Sparkle Automation Audit

> Generated: 2026-05-08 | Status: Phase 0 Deliverable

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│  FLUTTER MOBILE (mobile/)                                │
│  39 features | Riverpod | GoRouter | 5-tab shell         │
│  iOS 16+ / Android API 24+ | WebSocket chat              │
└──────────────────────────┬──────────────────────────────┘
                           │ WebSocket (JWT) + REST
┌──────────────────────────▼──────────────────────────────┐
│  GO GATEWAY (backend/gateway/)                           │
│  Gin HTTP + WebSocket proxy | Auth | Rate Limit          │
│  CQRS outbox | gRPC client | 66+ handlers                │
└──────────────────────────┬──────────────────────────────┘
                           │ gRPC (protobuf)
┌──────────────────────────▼──────────────────────────────┐
│  PYTHON AI ENGINE (backend/app/)                         │
│  FastAPI + LangGraph FSM | Aurora Adaptive Kernel        │
│  100+ REST endpoints | 15+ gRPC services | RAG           │
│  390+ service files | Multi-LLM providers                │
└──────────────────────────┬──────────────────────────────┘
                           │
    ┌──────────┬───────────┼───────────┬──────────┐
    ▼          ▼           ▼           ▼          ▼
 PostgreSQL   Redis     MinIO      Kafka     LLM APIs
 pgvector    Streams   S3 compat  Consumers  OpenAI/Qwen
    AGE       PubSub                           DeepSeek/GLM
```

## 2. Existing Automation Inventory

### Scripts (70+ files)

| Category | Count | Key Files |
|----------|-------|-----------|
| Dev/Deploy | 8 | `dev_local_stack.sh`, `deploy_k8s.sh`, `deploy-prod.sh` |
| Quality/Governance | 25+ | `check_rule_*.py`, `run_all_rule_guards.sh` |
| Testing | 6 | `run-integration-tests.sh`, `run_e2e_smoke.sh`, `journey_smoke.sh` |
| Proto/Codegen | 3 | `proto_toolchain.sh`, `generate_python_protos.sh` |
| Load/Chaos | 3 | `run-load-tests.sh`, `chaos_drill.sh` |
| Production | 4 | `backup_prod_data.sh`, `restore_prod_data.sh`, `production_readiness_check.sh` |
| i18n/Design | 3 | `check_hardcoded_strings.sh`, `migrate_design_system.sh` |
| AI/ML | 5+ | `aurora_v1_acceptance.py`, `xiaolin_lifecycle_acceptance.py` |

### Makefile Targets (80+)

| Category | Targets | Status |
|----------|---------|--------|
| Infrastructure | `dev-up`, `dev-up-all`, `dev-preflight` | EXIST |
| DB Management | `sync-db`, `db-migrate`, `db-dump`, `db-sqlc`, `db-reset` | EXIST |
| Proto | `proto-gen`, `proto-lint`, `proto-breaking` | EXIST |
| Services | `grpc-server`, `api-server`, `gateway-dev` | EXIST |
| Testing | `smoke`, `integration-test`, `e2e-multiturn` | EXIST |
| Quality | `quality-baseline`, `quality-budget-check`, `flutter-analyze-gate` | EXIST |
| Signoff | `local-signoff-preflight`, `local-final-signoff` | EXIST |
| Mobile | `mobile-run`, `mobile-gen`, `mobile-build-china/intl` | EXIST |
| Celery | `celery-up/down/status/logs/flush/restart` | EXIST |

### Test Coverage (~1,500 files)

| Component | Files | Framework | Coverage |
|-----------|-------|-----------|----------|
| Python Backend | 905+ | pytest (async) | Comprehensive |
| Go Gateway | 81 | go test + testify | Well-covered |
| Flutter Mobile | 287 | flutter test | Good |
| Cross-layer E2E | 10 | pytest + mock infra | Focused |
| Flutter Integration | 1 | integration_test | MINIMAL |

### CI/CD (GitHub Actions)

| Workflow | Purpose |
|----------|---------|
| `ci.yml` | Lint + test + quality gates |
| `e2e-tests.yml` | Nightly E2E |
| `e2e-smoke.yml` | Quick smoke |
| `benchmark.yml` | Performance |
| `load-test.yml` | Load testing |
| `chaos-drill.yml` | Chaos engineering |

### Health Endpoints

| Service | Paths |
|---------|-------|
| Python Backend | `/health`, `/health/live`, `/health/ready`, `/health/database` |
| Go Gateway | `/healthz`, `/live`, `/readyz`, `/ready`, `/health` |

## 3. Gap Analysis

### Critical Missing (P0)

| Gap | Impact | Current State |
|-----|--------|---------------|
| **iOS Simulator automation** | Cannot verify iOS builds locally | NO scripts exist |
| **Android Emulator automation** | Cannot verify Android builds locally | NO scripts exist |
| **Flutter integration tests** | Only 1 test (guest tab navigation) | 9 critical paths untested |
| **Unified prelaunch runner** | No single command to verify everything | `make local-final-signoff` close but no mobile |
| **E2E artifact management** | Test results scattered across repos | No unified artifacts/e2e/ |
| **Log/screenshot analysis** | Manual log reading required | No automated analysis tools |

### Important Missing (P1)

| Gap | Impact | Current State |
|-----|--------|---------------|
| **Device test scripts** | Cannot test on real hardware | NO scripts exist |
| **E2E_TEST_MODE** | Integration tests depend on real LLM | No mock LLM mode |
| **Stable ValueKeys** | E2E selectors fragile (text-based) | Sparse, inconsistent |
| **Test fixture accounts** | No standard test user for E2E | `seed_demo_user_enhanced.py` exists but no E2E account |
| **Report generation** | No structured prelaunch report | Manual Makefile output only |

### Enhancement Opportunities (P2)

| Gap | Impact | Current State |
|-----|--------|---------------|
| **Auto-fix loop** | Manual fix-test cycle | Scripts fail and stop |
| **Patrol framework** | Cannot test system dialogs | integration_test only |
| **Visual regression** | No screenshot comparison | Golden tests exist but limited |
| **Performance baselines** | No mobile perf tracking | Backend has benchmarks |

## 4. Existing Infrastructure to Leverage

Avoid duplication. These existing pieces should be wrapped, not rewritten:

| Existing | Wrap Into |
|----------|-----------|
| `make dev-up` | `scripts/dev/up.sh` |
| `docker compose down` | `scripts/dev/down.sh` |
| `make smoke` | `scripts/dev/smoke.sh` |
| `make env-check` | `scripts/dev/healthcheck.sh` (part) |
| `make local-signoff-preflight` | `scripts/test/run_prelaunch.sh` (part) |
| `scripts/dev_local_stack.sh` | `scripts/dev/up.sh` (reference) |
| `make local-backend-smoke` | `scripts/test/run_backend_tests.sh` (part) |
| Backend `tests/conftest.py` | Test fixtures reuse |
| `mobile/integration_test/app_test.dart` | Build upon existing pattern |

## 5. Implementation Priority

### Phase 1: Foundation (This Session)
1. `scripts/dev/` — 6 scripts wrapping Makefile + new capabilities
2. `scripts/test/` — 5 unified test runners
3. `artifacts/e2e/` — output directory structure
4. `tool/e2e/` — log analysis + report generation

### Phase 2: Mobile Automation (This Session)
5. `scripts/mobile/` — iOS simulator + Android emulator scripts
6. Device test scripts for both platforms

### Phase 3: Integration Tests (This Session)
7. 9 Flutter integration tests covering core user flows
8. E2E_TEST_MODE with mock LLM fixtures
9. Stable ValueKeys for core components

### Phase 4: Orchestration (This Session)
10. `scripts/test/run_prelaunch.sh` — master runner
11. Auto-fix protocol documentation
12. Report templates

## 6. Risk Assessment

| Risk | Mitigation |
|------|------------|
| iOS signing blocks automation | Script detects + reports; no blind config changes |
| Real LLM instability in E2E | E2E_TEST_MODE with mock fixtures |
| Flutter version compatibility | Scripts check `flutter --version` |
| Docker resource limits | healthcheck validates service state |
| Emulator boot time | Scripts poll with timeout, don't block |
