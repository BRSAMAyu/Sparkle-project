# Testing & Quality Coverage Audit

**Auditor**: Agent (Opus)
**Date**: 2026-05-07
**Status**: PASS WITH ISSUES

## Summary

The Sparkle project has a comprehensive and multi-layered testing infrastructure spanning Python (217K LOC across 905 test files), Go (7.5K LOC across 81 test files), and Flutter (58K LOC across 282 test files). The CI/CD pipeline is mature with 12 workflows covering linting, unit tests, integration tests, E2E, benchmarks, load testing, chaos engineering, and security scanning. Rule governance is strong with 67 rule guard scripts all verified present. However, there are notable gaps: the FSM orchestrator test uses a self-contained mock FSM rather than testing the real orchestrator, some critical event consumers lack dedicated tests, 4 Flutter tests are permanently skipped, and test coverage thresholds for critical orchestration paths are set very low (15%).

## Critical Issues (P0)

None found. No blocking issues prevent launch.

## High Issues (P1)

### P1-01: Orchestrator FSM test does not exercise real code
- **File**: `backend/tests/test_orchestrator_fsm.py:9-79`
- **Detail**: The two tests `test_orchestrator_fsm_state_transitions` and `test_orchestrator_fsm_error_recovery` create standalone `MockFSM` / `MockFSMWithError` classes and test those instead of the actual `ChatOrchestrator` or its FSM graph. These tests will always pass regardless of changes to the real orchestrator. They provide false confidence.
- **Contrast**: `backend/tests/test_orchestrator_simple.py` does properly test the real `ChatOrchestrator` with mocked dependencies.
- **Recommendation**: Replace the mock-FSM tests with tests that instantiate the real FSM graph (LangGraph StateGraph) and verify state transitions against the actual node definitions.

### P1-02: Critical event consumers lack dedicated tests
- **Files Missing**:
  - `backend/app/services/galaxy_event_consumer.py` -- no test file
  - `backend/app/services/task_event_consumer.py` -- no test file
  - `backend/app/services/push_scheduler.py` -- no test file
  - `backend/app/services/nudge_service.py` -- no test file
  - `backend/app/services/file_processing_orchestrator.py` -- no test file
- **Impact**: These consumers handle event bus signals (TaskCompleted, KnowledgeNodeUpdated, etc.) that drive achievements, galaxy refreshes, and push notifications. Failures here are silent.
- **Note**: Integration tests in `backend/tests/integration/test_event_bus_e2e.py` and journey smokes provide some indirect coverage, but dedicated unit tests for each consumer are missing.

### P1-03: Coverage thresholds for orchestration and API layers are very low
- **File**: `quality/coverage_thresholds.json:9-10,13-14`
- **Detail**: `app/orchestration` threshold is set at 15%, `app/api` at 15%, `app/routing` at 22%. These are the AI brain and routing layers of the system.
- **Context**: The global Python threshold is 50%, and critical handler paths (Go) require 50%. The orchestration layer being at 15% means 85% of the most critical code can go untested without CI failing.
- **Recommendation**: Target at least 30% for orchestration and API layers as a near-term goal.

### P1-04: WebSocket integration test is purely structural
- **File**: `mobile/test/integration/websocket_integration_test.dart:1-60`
- **Detail**: The "WebSocket Integration Tests" test string concatenation, map field existence, and timeout configuration values. They never open a WebSocket connection, send a message, or verify response streaming. The file header admits "these are integration test templates."
- **Impact**: Zero confidence that WebSocket communication actually works at the Flutter layer.

## Medium Issues (P2)

### P2-01: 205 of 361 Python services lack dedicated test files
- **Scope**: 57% of `backend/app/services/*.py` have no corresponding test file under `backend/tests/`.
- **Context**: Many are kill-switch services (aurora_stage*_kill_switch_service.py) that may be thin wrappers. But substantial services like `companion_identity_kernel.py`, `dynamic_tool_registry.py`, `lang_graph_planner.py`, `request_router.py`, and `token_tracker.py` also lack dedicated tests.
- **Mitigation**: Some of these get indirect coverage through integration/journey tests and the orchestrator mixin tests in `backend/tests/unit/orchestrator/mixins/`.

### P2-02: E2E conftest has placeholder database URL with weak password
- **File**: `tests_e2e/conftest.py:134`
- **Detail**: `postgresql+asyncpg://postgres:change-me@localhost:5432/sparkle` -- the default fallback URL uses `change-me` as password. While this is only a default fallback (env var takes precedence), it is a misleading default for a production-readiness repo.
- **Recommendation**: Change default to `sparkle_test` database name and use a clearly-test-only password like `test-only`.

### P2-03: 4 Flutter tests permanently skipped
- **Files**:
  - `mobile/test/widget_test.dart:69` -- `skip: true` on the main app smoke test
  - `mobile/test/widget/sync_center_screen_test.dart:33`
  - `mobile/test/widget/openclaw_connection_panel_test.dart:345`
  - `mobile/test/widget/focus_agent_sheet_test.dart:100`
- **Detail**: The main `widget_test.dart` (app smoke test) is skipped, likely due to the IsarCore initialization dependency. The integration_test/app_test.dart provides real coverage, but the skipped unit-level smoke test means `flutter test` in CI may not catch basic widget tree issues.

### P2-04: CI workflows hardcode test database credentials
- **Files**: Multiple `.github/workflows/*.yml` files
- **Detail**: Passwords like `password`, `test`, `sparkle` are hardcoded directly in workflow YAML as service container env vars. While these are CI-only ephemeral containers, they still represent a pattern that should use GitHub secrets or at minimum `$SECRET` references.
- **Severity**: Medium because these are ephemeral CI containers, not production credentials.

### P2-05: No codecov.yml configuration file
- **Detail**: Codecov is integrated (upload steps exist in ci.yml, e2e-tests.yml, benchmark.yml), but no `codecov.yml` configures coverage gates, status checks, or PR comment behavior. This means codecov uses default settings which may not align with the project's `quality/coverage_thresholds.json`.
- **Recommendation**: Add `codecov.yml` that mirrors the thresholds in `coverage_thresholds.json`.

### P2-06: Benchmark baseline comparison not implemented
- **File**: `.github/workflows/benchmark.yml:64-65`
- **Detail**: Go benchmark step has `echo "Baseline comparison not yet implemented"` with a TODO comment. Python benchmark results are uploaded as artifacts but not compared against baselines.
- **Impact**: Benchmark regressions will not be caught automatically.

## Low Issues (P3)

### P3-01: Some Go handler files lack dedicated test coverage
- **Files without tests**: `api_errors.go`, `chat_history.go`, `chat_orchestrator_connections.go`, `chat_orchestrator_protocol.go`, `chat_orchestrator_responder.go`, `data_consistency_handler.go`, `file_events.go`, `group_chat.go`, `ws_hardening.go`
- **Context**: The chat_orchestrator_test.go (518 lines) and e2e_chat_orchestrator_test.go (249 lines) provide substantial coverage of the orchestrator logic, so these are likely split helper files whose logic is tested indirectly.

### P3-02: test_orchestrator_init.py has a broad name but narrow scope
- **File**: `backend/tests/test_orchestrator_init.py`
- **Detail**: The filename suggests initialization testing but could be confused with a general orchestrator test. Minor naming concern.

### P3-03: No Flutter golden test failure enforcement
- **File**: `.github/workflows/benchmark.yml:199`
- **Detail**: Golden test step has `|| true` (don't fail on golden changes). This means visual regressions are not blocked by CI.

### P3-04: Stress tests use `continue-on-error: true`
- **File**: `.github/workflows/e2e-smoke.yml:103`
- **Detail**: Celery stress tests are set to continue-on-error, meaning stress test failures do not block the pipeline. Acceptable for now but should be monitored.

## Positive Findings

### 1. Exceptional CI/CD Pipeline Breadth
The project has 12 GitHub Actions workflows covering: linting (3 languages), unit tests, integration tests, E2E smoke, benchmarks, load testing (Locust + k6), chaos engineering, security scanning (Trivy + Gitleaks + Safety), proto validation, DB schema drift detection, quality baseline snapshots, and blue/green deployment. This is well above industry standard.

### 2. Strong Rule Governance
67 rule guard scripts in the manifest (`scripts/rule_guard_manifest.tsv`), all verified present on disk. The runner script (`scripts/run_all_rule_guards.sh`) supports parallel execution (`--jobs 4`) and is integrated into CI as a required job.

### 3. Comprehensive Contract Testing
9 contract test files cover: proto serialization, JSON wire format, gRPC roundtrip, WebSocket proto contract, API health contract, API router OpenAPI contract, and state manager contracts. This protects against cross-language compatibility regressions.

### 4. Journey Smoke Tests
Journey smoke scripts (`scripts/journey_smoke.sh`) exercise critical user journeys through the integration test layer, running both main and error journey paths.

### 5. Well-Structured Test Fixtures
- `backend/tests/conftest.py` provides centralized fixtures with proper async session management using SQLite in-memory for unit tests and real Redis/PostgreSQL for integration tests
- `tests_e2e/conftest.py` provides comprehensive mock infrastructure for full-stack testing
- Test credentials are properly centralized in `backend/tests/_credentials.py`

### 6. Coverage Threshold Enforcement
`quality/coverage_thresholds.json` defines both global and path-scoped thresholds for all three languages, enforced by `scripts/check_coverage_thresholds.py` in CI. Coverage reports are uploaded to Codecov.

### 7. Load Test SLO Baselines
`backend/tests/load/baseline.json` defines concrete SLO targets (p50/p95/p99 latency, error rate, target RPS) for all critical API endpoints.

### 8. Real E2E Integration Test
`mobile/integration_test/app_test.dart` exercises real app startup, guest login, and navigation through all major tabs (Galaxy, Chat, Community, Profile, Home) with proper pump-and-settle patterns.

### 9. Orchestrator Unit Test Quality
`backend/tests/test_orchestrator_simple.py` properly tests the real `ChatOrchestrator` with carefully mocked dependencies, including bridge short-circuit and OpenClaw short-circuit paths.

### 10. Performance Benchmark Suite
8 Python benchmark test files in `backend/tests/benchmark/` cover orchestrator, transparency, vector search, LLM service, tool registry, statistics, and budget optimization performance.

## Files Audited

### Python Tests
- `backend/tests/conftest.py`
- `backend/tests/_credentials.py`
- `backend/tests/__init__.py`
- `backend/tests/test_orchestrator_fsm.py`
- `backend/tests/test_orchestrator_simple.py`
- `backend/tests/test_orchestrator_init.py`
- `backend/tests/test_llm_service_streaming.py`
- `backend/tests/test_llm_parser.py`
- `backend/tests/test_context_manager.py`
- `backend/tests/test_context_pruner.py`
- `backend/tests/test_dual_core_router_kill_switch.py`
- `backend/tests/test_community_e2e.py`
- `backend/tests/test_community_security.py`
- `backend/tests/test_vector_search.py`
- `backend/tests/test_rag_retrieval.py`
- `backend/tests/test_graph_rag.py`
- `backend/tests/test_graph_reasoning.py`
- `backend/tests/test_event_bus_shutdown.py`
- `backend/tests/test_migrations.py`
- `backend/tests/test_plan_progress_update.py`
- `backend/tests/test_plan_task_tools_production.py`
- `backend/tests/test_plan_task_service_production.py`
- `backend/tests/test_plan_execution_validation.py`
- `backend/tests/test_planning_hitl_chain.py`
- `backend/tests/test_langgraph_planner_timeout.py`
- `backend/tests/test_exam_intent_detection.py`
- `backend/tests/test_cognitive_loop.py`
- `backend/tests/test_analytics_service.py`
- `backend/tests/test_agent_stats_integration.py`
- `backend/tests/test_validation_e2e.py`
- `backend/tests/test_v2_agent_integration.py`
- `backend/tests/test_phase2_comprehensive.py`
- `backend/tests/test_phase2_integration.py`
- `backend/tests/test_phase2_core.py`
- `backend/tests/test_phase_acceptance.py`
- `backend/tests/test_phase4_galaxy_services.py`
- `backend/tests/test_av_kill_switch_guard.py`
- `backend/tests/test_f16_galaxy_weak_node_injection.py`
- `backend/tests/test_fv22_resource_quality.py`
- `backend/tests/test_report_reason_enum_sync.py`
- `backend/tests/test_report_reason_enum.py`
- `backend/tests/test_leaderboard_percentile_guard.py`
- `backend/tests/test_preference_consumer_safety.py`
- `backend/tests/test_db_partitioning.py`
- `backend/tests/test_contextual_chunk_enrichment.py`
- `backend/tests/test_document_feedback_loop.py`
- `backend/tests/test_user_service_get_by_email.py`
- `backend/tests/manual_rag_test.py`

### Python Test Subdirectories (all files listed)
- `backend/tests/unit/` (82 files)
- `backend/tests/unit/spine/` (17 files)
- `backend/tests/unit/services/` (17 files)
- `backend/tests/unit/orchestrator/` (2 files)
- `backend/tests/unit/orchestrator/mixins/` (9 files)
- `backend/tests/unit/consumers/` (1 file)
- `backend/tests/integration/` (29 files)
- `backend/tests/contract/` (9 files)
- `backend/tests/workflow/` (2 files)
- `backend/tests/benchmark/` (8 files)
- `backend/tests/services/galaxy/` (3 files)
- `backend/tests/services/stt/providers/` (2 files)
- `backend/tests/profile/eval/` (3 files)
- `backend/tests/agents/graph/nodes/` (2 files)
- `backend/tests/golden/` (4 files including conftest)
- `backend/tests/load/` (5 files + k6/scenarios.js)
- `backend/tests/performance/` (3 files)

### E2E Tests (top-level)
- `tests_e2e/conftest.py`
- `tests_e2e/pytest.ini`
- `tests_e2e/test_chat_e2e.py`
- `tests_e2e/test_full_e2e.py`
- `tests_e2e/test_plan_lifecycle_e2e.py`
- `tests_e2e/test_galaxy_e2e.py`
- `tests_e2e/test_core_flow.py`
- `tests_e2e/test_integration.py`
- `tests_e2e/test_real_llm.py`
- `tests_e2e/test_offline_sync_e2e.py`
- `tests_e2e/run_e2e_tests.py`

### Go Tests (all 81 files in `backend/gateway/internal/handler/`)
- Key files examined: `auth_test.go`, `websocket_proxy_test.go`, `security_test.go`, `chat_orchestrator_test.go`, `e2e_chat_orchestrator_test.go`, `performance_load_test.go`

### Go Tests (other directories)
- `backend/gateway/cmd/server/setup_test.go`
- `backend/gateway/internal/middleware/cors_test.go`
- `backend/gateway/internal/middleware/rate_limit_paths_test.go`

### Flutter Tests
- `mobile/test/widget_test.dart`
- `mobile/test/integration/websocket_integration_test.dart`
- `mobile/test/integration/full_stack_e2e_test.dart`
- `mobile/test/integration/exam_sprint_flow_test.dart`
- `mobile/test/unit/chat_provider_test.dart`
- `mobile/test/unit/chat_notifier_actions_test.dart`
- `mobile/test/unit/websocket_chat_service_v2_test.dart`
- `mobile/test/unit/api_client_test.dart`
- `mobile/test/unit/i18n_service_test.dart`
- `mobile/test/unit/active_goal_provider_test.dart`
- `mobile/test/unit/sync_engine_test.dart`
- `mobile/test/unit/offline_sync_test.dart`
- `mobile/test/unit/smart_cache_test.dart`
- `mobile/test/unit/chat_stream_parsing_test.dart`
- `mobile/test/widget/plan_review_card_test.dart`
- `mobile/test/widget/a11y_semantic_labels_test.dart`
- `mobile/test/widget/full_route_coverage_test.dart`
- `mobile/test/app/router_smoke_test.dart`
- `mobile/test/app/main_pages_load_smoke_test.dart`
- `mobile/test/app/main_actions_smoke_test.dart`
- `mobile/test/goldens/dashboard_golden_test.dart`
- `mobile/test/goldens/chat_golden_test.dart`
- `mobile/test/performance/widget_bench_test.dart`
- `mobile/integration_test/app_test.dart`

### Configuration
- `backend/pyproject.toml` (pytest config, ruff, mypy)
- `quality/coverage_thresholds.json`
- `mobile/analysis_options.yaml`
- `.pre-commit-config.yaml`

### CI/CD Workflows
- `.github/workflows/ci.yml` (main pipeline: lint + rule guards + backend test + flutter test + security + DB schema + proto + build)
- `.github/workflows/e2e-tests.yml` (nightly: Python + Go + Flutter + full stack E2E)
- `.github/workflows/e2e-smoke.yml` (compose-based E2E with full service stack)
- `.github/workflows/benchmark.yml` (Go + Python + Flutter benchmarks + stress tests + scenario regression)
- `.github/workflows/load-test.yml` (Locust + k6 load testing)
- `.github/workflows/chaos-drill.yml` (weekly chaos engineering)
- `.github/workflows/quality-baseline.yml` (weekly quality baseline snapshot)
- `.github/workflows/deploy-prod.yml` (blue/green production deployment)
- `.github/workflows/ui-lint.yml` (UI design lint)

### Scripts
- `scripts/run_all_rule_guards.sh`
- `scripts/journey_smoke.sh`
- `scripts/run_e2e_smoke.sh`
- `scripts/rule_guard_manifest.tsv`
- `scripts/check_coverage_thresholds.py`
- All 67 rule guard scripts (verified present)
