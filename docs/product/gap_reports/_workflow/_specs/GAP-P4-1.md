# GAP-P4-1: Release Gate (部署阻断门禁) -- Implementation Spec

> **Mode**: spec→you | **Level**: L3 (Cross-Boundary) | **Effort**: L (6.5-9.5 days)
> **Source**: OBS-015 from 06_observability.md -- Release Gates Blocking Deployment
> **Status**: Spec ready for user implementation

---

## 1. Objectives

Build a unified release gate system for Sparkle that blocks deployment when critical checks fail. Sparkle currently has 15+ quality checks across multiple Makefile targets, shell scripts, and Python checkers, but there is no single gate runner that aggregates them into a deploy/no-deploy decision. Every release decision is manual.

### 1.1 Why This Exists

The OBS-015 audit found:

- No release-level metrics gates exist.
- No CI check fails on "latency regressed 20%".
- No deployment is blocked by "error rate spike detected".
- All release decisions are manual, post-hoc monitoring.
- Quality gates exist only for the planning subsystem (`PlanQualityGate`).

This creates a concrete risk: Dangerous changes can deploy without any automated metric verification.

### 1.2 Core Goals

1. Create a unified `ReleaseGateRunner` system that aggregates all quality checks into gate categories
2. Support **blocking** vs **warning** severity per gate, with a configurable threshold for overall pass/fail
3. Consolidate 15+ existing quality checks from disparate Makefile targets into the gate runner
4. Add metric-based deployment gates: Prometheus queries for latency SLO, error rate, event stream lag
5. Integrate with both local sign-off (`make local-final-signoff`) and CI pipeline (future GitHub Actions)
6. Produce a machine-readable gate report for audit trail

### 1.3 Non-Goals

- Not building a CI/CD pipeline from scratch -- GitHub Actions is out of scope for this spec
- Not adding a UI dashboard for gate results -- machine-readable JSON output is the interface
- Not modifying the deployment process itself (`deploy-prod.sh`, `blue_green_switch.sh`) -- only adding a pre-deploy gate check step
- Not implementing cost prediction gates -- GAP-P4-2 handles that separately; wire it in later

---

## 2. Current State Assessment

### 2.1 Existing Quality Checks

The following checks exist across the codebase but are NOT unified into a single gate runner:

| # | Check | Where It Lives | How It Runs |
|---|-------|---------------|-------------|
| 1 | Local preflight (DB, Redis, health, Alembic) | `backend/scripts/local_signoff_preflight.py` | `make local-signoff-preflight` |
| 2 | Backend unit tests (pytest) | `backend/tests/unit/` | Manual / `make local-backend-smoke` |
| 3 | Gateway unit tests (go test) | `backend/gateway/internal/handler/`, etc. | `make local-final-signoff` inline |
| 4 | Flutter tests | `mobile/test/` | `make local-mobile-smoke` |
| 5 | Flutter analyze gate | `scripts/check_flutter_analyze_gate.py` | `make flutter-analyze-gate` |
| 6 | Backend acceptance scripts (~10 scripts) | `backend/scripts/*_acceptance.py` | `make local-final-signoff` inline |
| 7 | Config self-check | `backend/scripts/check_config_effective.py` | `make env-check` / `make smoke` |
| 8 | AI provider probe | `backend/scripts/check_ai_providers.py` | `make local-ai-check` |
| 9 | Required local config check | `backend/scripts/check_required_local_config.py` | `make local-config-check` |
| 10 | Auth smoke test | `backend/scripts/auth_smoke.py` | `make auth-test` |
| 11 | Community smoke test | `backend/scripts/community_smoke.py` | `make community-test` |
| 12 | Worker smoke test | `backend/scripts/worker_smoke.py` | `make worker-test` |
| 13 | OpenAPI contract check | `scripts/check_openapi_contract.py` | `make openapi-contract-check` |
| 14 | Coverage thresholds | `scripts/check_coverage_thresholds.py` | Manual (CI only) |
| 15 | Tech debt budget | `scripts/check_tech_debt_budget.py` | `make quality-budget-check` |
| 16 | Rule guards (~47 rules) | `scripts/run_all_rule_guards.sh` + manifest | Manual |
| 17 | Journey smoke tests | `scripts/journey_smoke.sh` | Manual |
| 18 | Production readiness check | `scripts/production_readiness_check.sh` | Manual pre-production |
| 19 | Proto lint + breaking changes | `make proto-lint`, `make proto-breaking` | Manual |
| 20 | Proto deprecation check | `scripts/check_proto_deprecated_windows.py` | Manual |

### 2.2 Existing Gate-Like Patterns

**Pattern A: `make local-final-signoff`** — A Makefile target that chains multiple checks sequentially. Each check is a command that must exit 0. This is a de facto gate but is hardcoded in the Makefile and not configurable.

**Pattern B: `scripts/check_tech_debt_budget.py`** — A Python script that loads a JSON budget file, runs metric commands, compares results against thresholds, and exits non-zero on any threshold breach. This is the closest existing model to a proper gate system.

**Pattern C: `scripts/run_all_rule_guards.sh`** — A shell script that reads a TSV manifest of rules and commands, runs them (optionally in parallel with `--jobs`), collects failures, and reports pass/fail.

### 2.3 Gap Details from OBS-015

1. **No machine-enforced SLO gates** — SLO targets are documented but not checked as part of deployment
2. **No Prometheus query in deployment path** — Latency, error rate, event stream lag are not queried pre-deploy
3. **No unified gate runner** — Each check is a standalone script or Makefile target
4. **No blocking/warning severity distinction** — All failures in a Makefile chain are equally fatal
5. **No gate report** — No machine-readable output aggregating results for audit trail
6. **No incremental gate** — Cannot skip slow checks during development; all-or-nothing

---

## 3. Gate Categories

### 3.1 Category Taxonomy

| Category | Purpose | Blocking? | Example Gates |
|----------|---------|-----------|--------------|
| **correctness** | Code and behavior correctness | Always blocking | Unit tests, acceptance tests, journey smoke |
| **security** | Secrets, isolation, safety | Always blocking | Rule guards, secret check |
| **contract** | API/proto/interface stability | Always blocking | OpenAPI contract drift, proto breaking changes |
| **performance** | Latency/throughput SLO | Configurable (blocking in prod, warning in dev) | P95 latency check, 5xx rate check |
| **operability** | Infrastructure health | Configurable (blocking in prod, warning in dev) | Health endpoints, Alembic head, RediSearch index |
| **compliance** | Tech debt, deprecation policy | Warning (escalates to blocking in freeze period) | Tech debt budget, proto deprecation windows |

### 3.2 Gate Severity Model

| Severity | Symbol | Meaning |
|----------|--------|---------|
| **P0** | BLOCK | Must pass. Failure = deployment blocked unconditionally. |
| **P1** | BLOCK | Must pass. Failure = deployment blocked unless explicitly overridden. |
| **P2** | WARN | Should pass. Failure = warning emitted but deployment continues. |
| **P3** | INFO | Nice to pass. Failure = informational only. |

The overall gate decision algorithm:
1. If any P0 gate fails → BLOCKED.
2. If any P1 gate fails → BLOCKED (can be overridden with `--allow-p1-failure` flag).
3. If any P2 gate fails → WARNING emitted, deployment ALLOWED.
4. P3 failures are informational only.

---

## 4. Gate Configuration Format

### 4.1 Configuration File

Create `quality/release_gates.json` as the single source of truth:

```json
{
  "version": 1,
  "updated_at": "2026-05-06T00:00:00Z",
  "gates": [
    {
      "id": "backend_unit_tests",
      "category": "correctness",
      "severity": "P0",
      "description": "Backend Python unit tests must pass",
      "command": "cd backend && .venv/bin/pytest tests/unit/ -x -q --timeout=30",
      "timeout_seconds": 600,
      "environments": ["local", "ci"],
      "required_output_pattern": null,
      "failure_hint": "Run 'cd backend && pytest tests/unit/' to debug failures"
    },
    {
      "id": "gateway_unit_tests",
      "category": "correctness",
      "severity": "P0",
      "description": "Go Gateway unit tests must pass",
      "command": "cd backend/gateway && go test ./internal/handler ./internal/middleware ./internal/service -count=1",
      "timeout_seconds": 300,
      "environments": ["local", "ci"],
      "required_output_pattern": null,
      "failure_hint": "Run 'cd backend/gateway && go test ./...' to debug failures"
    },
    {
      "id": "flutter_analyze",
      "category": "correctness",
      "severity": "P0",
      "description": "Flutter analyze must have 0 errors and 0 warnings",
      "command": "python3 scripts/check_flutter_analyze_gate.py --project-dir mobile --budget-file quality/flutter_analyze_allowlist.json --write-report quality/flutter_analyze_report.json",
      "timeout_seconds": 120,
      "environments": ["local", "ci"],
      "failure_hint": "Review flutter_analyze_report.json for issue details"
    },
    {
      "id": "flutter_tests",
      "category": "correctness",
      "severity": "P0",
      "description": "Flutter unit and widget tests must pass",
      "command": "cd mobile && flutter test -r compact",
      "timeout_seconds": 300,
      "environments": ["ci"],
      "failure_hint": "Run 'cd mobile && flutter test' to see which tests failed"
    },
    {
      "id": "backend_acceptance",
      "category": "correctness",
      "severity": "P0",
      "description": "Backend acceptance scripts must pass",
      "command": "cd backend && .venv/bin/python scripts/ai_chat_multiturn_acceptance.py && .venv/bin/python scripts/accountability_acceptance.py && .venv/bin/python scripts/galaxy_plan_acceptance.py",
      "timeout_seconds": 900,
      "environments": ["ci"],
      "failure_hint": "Run individual acceptance scripts to isolate failures"
    },
    {
      "id": "rule_guards",
      "category": "security",
      "severity": "P0",
      "description": "All registered rule guards must pass",
      "command": "bash scripts/run_all_rule_guards.sh --jobs 4",
      "timeout_seconds": 300,
      "environments": ["local", "ci"],
      "failure_hint": "Review the rule guard output; each failed rule shows the file and reason"
    },
    {
      "id": "hardcoded_secrets",
      "category": "security",
      "severity": "P0",
      "description": "No hardcoded secrets or tokens in codebase",
      "command": "python3 scripts/guards/check_rule_bi_hardcoded_secrets.py",
      "timeout_seconds": 60,
      "environments": ["local", "ci"],
      "failure_hint": "Remove any detected secrets; use environment variables or settings.py"
    },
    {
      "id": "openapi_contract",
      "category": "contract",
      "severity": "P0",
      "description": "OpenAPI contract must not have unintended drift",
      "command": "python3 scripts/check_openapi_contract.py",
      "timeout_seconds": 60,
      "environments": ["local", "ci"],
      "failure_hint": "Run 'python3 scripts/check_openapi_contract.py --update' to regenerate snapshot if drift is intentional"
    },
    {
      "id": "proto_breaking",
      "category": "contract",
      "severity": "P0",
      "description": "No protobuf breaking changes",
      "command": "make proto-breaking",
      "timeout_seconds": 120,
      "environments": ["ci"],
      "failure_hint": "Review buf breaking change report; intentional breaks require ADR"
    },
    {
      "id": "proto_deprecation",
      "category": "compliance",
      "severity": "P1",
      "description": "Proto deprecation windows must not be violated",
      "command": "python3 scripts/check_proto_deprecated_windows.py",
      "timeout_seconds": 30,
      "environments": ["ci"],
      "failure_hint": "Remove deprecated fields whose removal window has expired"
    },
    {
      "id": "coverage_thresholds",
      "category": "correctness",
      "severity": "P1",
      "description": "Coverage must meet minimum thresholds per path",
      "command": "python3 scripts/check_coverage_thresholds.py --kind python --report <coverage_xml> --rules-file quality/coverage_thresholds.json && python3 scripts/check_coverage_thresholds.py --kind go --report <go_cover_file> --rules-file quality/coverage_thresholds.json && python3 scripts/check_coverage_thresholds.py --kind flutter --report <lcov_file> --rules-file quality/coverage_thresholds.json",
      "timeout_seconds": 30,
      "environments": ["ci"],
      "failure_hint": "Add tests for uncovered paths; see coverage report"
    },
    {
      "id": "infra_preflight",
      "category": "operability",
      "severity": "P1",
      "description": "Infrastructure connectivity (DB, Redis, health endpoints, Alembic head)",
      "command": "cd backend && .venv/bin/python scripts/local_signoff_preflight.py",
      "timeout_seconds": 30,
      "environments": ["local"],
      "failure_hint": "Ensure 'make dev-up' is running and services are healthy"
    },
    {
      "id": "ai_providers_reachable",
      "category": "operability",
      "severity": "P1",
      "description": "All configured AI providers must be reachable",
      "command": "cd backend && .venv/bin/python scripts/check_ai_providers.py",
      "timeout_seconds": 60,
      "environments": ["local"],
      "failure_hint": "Check API keys and network connectivity for LLM providers"
    },
    {
      "id": "tech_debt_budget",
      "category": "compliance",
      "severity": "P2",
      "description": "Technical debt metrics must not exceed budget",
      "command": "python3 scripts/check_tech_debt_budget.py",
      "timeout_seconds": 60,
      "environments": ["local", "ci"],
      "failure_hint": "Run 'python3 scripts/collect_quality_baseline.py' to assess current debt levels"
    },
    {
      "id": "journey_smoke",
      "category": "correctness",
      "severity": "P1",
      "description": "End-to-end journey smoke tests must pass",
      "command": "bash scripts/journey_smoke.sh all",
      "timeout_seconds": 300,
      "environments": ["ci"],
      "failure_hint": "Review smoke test failures; check for environmental issues"
    },
    {
      "id": "latency_p95_slo",
      "category": "performance",
      "severity": "P1",
      "description": "P95 latency must be below SLO threshold (1.5s over 5m)",
      "command": "python3 scripts/check_metrics_gate.py --metric sparkle_p95_latency_5m --operator lt --threshold 1.5 --prometheus-url http://localhost:9090",
      "timeout_seconds": 15,
      "environments": ["production"],
      "failure_hint": "P95 latency is elevated; investigate recent changes affecting request handling"
    },
    {
      "id": "error_rate_slo",
      "category": "performance",
      "severity": "P0",
      "description": "5xx error rate must be below SLO threshold (2% over 5m)",
      "command": "python3 scripts/check_metrics_gate.py --metric sparkle_backend_5xx_ratio_5m --operator lt --threshold 0.02 --prometheus-url http://localhost:9090",
      "timeout_seconds": 15,
      "environments": ["production"],
      "failure_hint": "High error rate detected; check logs for recent errors before deploying"
    },
    {
      "id": "event_stream_lag",
      "category": "performance",
      "severity": "P2",
      "description": "Event stream lag must be below 120s",
      "command": "python3 scripts/check_metrics_gate.py --metric sparkle_event_stream_lag_seconds --operator lt --threshold 120 --prometheus-url http://localhost:9090",
      "timeout_seconds": 15,
      "environments": ["production"],
      "failure_hint": "Event stream lag is elevated; check Celery workers and Redis connectivity"
    }
  ],
  "policies": {
    "allow_override_p1": false,
    "warn_threshold_p2_failures": 3,
    "max_gate_duration_seconds": 3600
  }
}
```

### 4.2 Gate Schema (per-entry)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | yes | Unique gate identifier |
| `category` | enum | yes | `correctness`, `security`, `contract`, `performance`, `operability`, `compliance` |
| `severity` | enum | yes | `P0`, `P1`, `P2`, `P3` |
| `description` | string | yes | Human-readable explanation |
| `command` | string | yes | Shell command; exit 0 = pass, non-zero = fail |
| `timeout_seconds` | int | yes | Max allowed runtime; exceeded = failure |
| `environments` | string[] | yes | Which environments this gate runs in: `local`, `ci`, `production` |
| `required_output_pattern` | string or null | no | If set, must find regex in stdout; null = exit code determines pass/fail |
| `failure_hint` | string | yes | Actionable hint shown when gate fails |

### 4.3 Policy Configuration

| Field | Default | Description |
|-------|---------|-------------|
| `allow_override_p1` | false | If true, P1 failures can be overridden with `--allow-p1-failure` |
| `warn_threshold_p2_failures` | 3 | If P2 failures exceed this count, escalate to blocking |
| `max_gate_duration_seconds` | 3600 | Max total gate runner duration; times out if exceeded |

---

## 5. File Inventory

### Files to Create

| File | Purpose |
|------|---------|
| `scripts/release_gate_runner.py` | Main gate runner: loads config, executes gates, produces report |
| `scripts/check_metrics_gate.py` | Prometheus metric query gate checker |
| `scripts/__init__.py` | Package init for scripts (so runner can be imported by tests) |
| `quality/release_gates.json` | Gate configuration file |
| `scripts/tests/test_release_gate_runner.py` | Unit tests for the gate runner |
| `scripts/tests/test_check_metrics_gate.py` | Unit tests for the metrics gate checker |
| `scripts/tests/__init__.py` | Package init for tests |

### Files to Modify

| File | Change Description |
|------|-------------------|
| `Makefile` | Add `make release-gate`, `make release-gate-local`, `make release-gate-ci`, `make release-gate-prod` targets. Update `make local-final-signoff` to call `make release-gate-local`. |
| `scripts/verify_deployment.sh` | Add gate runner call before health check step. |
| `scripts/production_readiness_check.sh` | Replace inline checks with `make release-gate-prod` call. Keep deploy-artifact existence checks. |

### Files Not Modified

| File | Reason |
|------|--------|
| `scripts/deploy-prod.sh` | Already has smoke + health + observe; gate runner is called *before* this script |
| `scripts/blue_green_switch.sh` | Deprecated; not in production deploy path |
| `scripts/chaos_drill.sh` | Chaos testing is orthogonal to release gates |
| All individual checker scripts | These remain as standalone tools usable outside the gate runner |

---

## 6. Implementation Steps

### Phase 1: Gate Runner Framework (2-3 days)

**Step 1.1 -- Create the gate runner core**

Create `scripts/release_gate_runner.py` with the following architecture:

- `ReleaseGateRunner` class that loads `quality/release_gates.json`
- Filters gates by environment (`local`, `ci`, `production`)
- Executes each gate via `subprocess.run` with configurable timeout
- Collects exit codes, stdout, stderr, and duration
- Applies severity model to produce `PASS`, `BLOCKED`, or `WARNING` decisions
- Outputs a JSON report for audit trail
- CLI flags: `--environment`, `--output`, `--gate <id>`, `--list-gates`, `--allow-p1-failure`

**Key Design Details:**
- The runner reads `quality/release_gates.json` for configuration
- Sequential execution in Phase 1 (parallel via `--jobs N` in future)
- Shell command execution via `subprocess.run` — all existing checks are scripts
- Exit-code-based pass/fail: a gate passes if exit code = 0
- Substitutes `--prometheus-url` placeholder in commands when provided

**Step 1.2 -- Create the release gate configuration file**

Create `quality/release_gates.json` (see Section 4 for the full content).

**Step 1.3 -- Create the metrics gate checker**

Create `scripts/check_metrics_gate.py`:
- Queries a Prometheus instant query endpoint
- Compares the returned scalar value against a threshold
- Exits 0 if comparison passes, 1 if fails or Prometheus is unreachable
- CLI: `--metric`, `--operator` (lt/gt/lte/gte/eq), `--threshold`, `--prometheus-url`

**Step 1.4 -- Wire into the Makefile**

```makefile
release-gate:
	python3 scripts/release_gate_runner.py --environment local --output quality/release_gate_report.json

release-gate-ci:
	python3 scripts/release_gate_runner.py --environment ci --output quality/release_gate_report.json

release-gate-prod:
	python3 scripts/release_gate_runner.py --environment production --prometheus-url $(PROMETHEUS_URL) --output quality/release_gate_report.json

local-final-signoff: release-gate
	@$(MAKE) smoke
```

**Step 1.5 -- Create package init files**

Create empty `scripts/__init__.py` and `scripts/tests/__init__.py`.

### Phase 2: Consolidate Existing Checks into Gate Config (1-2 days)

- Audit and standardize all 20 existing check commands
- Populate `quality/release_gates.json` with entries for all existing checks
- Add CI-only gates for slow checks (acceptance suite, Flutter widget tests)
- Test the full gate runner end-to-end

### Phase 3: Add Metric-Based Gates (1-2 days)

- Define PromQL queries for P95 latency, 5xx error rate, event stream lag, gateway availability
- Add metric gates to `quality/release_gates.json` with `"environments": ["production"]`
- Test metric gates against a dev Prometheus instance

### Phase 4: Integration and Polish (1-2 days)

- Update `scripts/verify_deployment.sh` to call gate runner as first step
- Update `scripts/production_readiness_check.sh` to use gate runner
- Add README documentation in `docs/engineering/quality_guardrails.md`
- Add `.gitignore` entry for `quality/release_gate_report.json`

---

## 7. Test Plan

### Unit Tests -- ReleaseGateRunner (`scripts/tests/test_release_gate_runner.py`)

| Test | Description |
|------|-------------|
| `test_load_config_valid` | Valid JSON config loads without error |
| `test_load_config_missing_file` | Missing config file raises error |
| `test_filter_gates_by_environment` | Only gates for the requested environment are returned |
| `test_run_gate_pass` | Gate with exit code 0 returns PASS |
| `test_run_gate_fail` | Gate with exit code 1 returns FAIL |
| `test_run_gate_timeout` | Gate exceeding timeout returns TIMEOUT |
| `test_run_gate_error` | Gate with subprocess error returns ERROR |
| `test_overall_pass` | All P0/P1 gates pass → decision is PASS |
| `test_overall_blocked_p0` | One P0 gate fails → decision is BLOCKED |
| `test_overall_blocked_p1_no_override` | P1 failure without override → BLOCKED |
| `test_overall_pass_p1_with_override` | P1 failure with allow_p1_failure → PASS |
| `test_overall_warning_p2` | Only P2 gates fail → WARNING |
| `test_p2_escalation_threshold` | P2 failures exceed threshold → BLOCKED |
| `test_skipped_environment` | Gates not for this environment are skipped |
| `test_report_json_structure` | Generated report has all required fields |
| `test_command_substitution` | Prometheus URL placeholder is substituted correctly |

### Unit Tests -- Metrics Gate Checker (`scripts/tests/test_check_metrics_gate.py`)

| Test | Description |
|------|-------------|
| `test_compare_lt_pass` | 0.5 < 1.0 → pass |
| `test_compare_lt_fail` | 2.0 < 1.0 → fail |
| `test_compare_gt_pass` | 2.0 > 1.0 → pass |
| `test_compare_gte_pass` | 1.0 >= 1.0 → pass |
| `test_prometheus_unreachable` | Prometheus URL not reachable → exit 1 |
| `test_prometheus_no_data` | Metric returns no data → exit 1 |
| `test_prometheus_bad_response` | Prometheus returns error → exit 1 |

### Integration Tests

| Test | Description |
|------|-------------|
| `test_full_gate_run_local` | Run all local gates, verify report is valid JSON and exits with correct code |
| `test_make_release_gate_target` | `make release-gate` runs and produces report |
| `test_gate_report_contains_all_fields` | Report has overall_decision, results, blocking_failures, etc. |
| `test_single_gate_flag` | `--gate backend_unit_tests` runs only one gate |

---

## 8. Acceptance Criteria

### Functional

- [ ] `scripts/release_gate_runner.py` exists and runs all configured gates for a given environment
- [ ] `quality/release_gates.json` contains entries for all 20 existing checks plus 3 metric gates
- [ ] Gate runner exits 0 when all blocking gates pass, non-zero when any blocking gate fails
- [ ] Gate report is written to a JSON file containing overall_decision, per-gate results, blocking_failures, and total duration
- [ ] Severity model is correctly applied: P0 always blocks, P1 blocks unless overridden, P2 warns, P3 info
- [ ] `make release-gate` target exists and works
- [ ] `make release-gate-local` runs only gates tagged with `local` environment
- [ ] `make release-gate-ci` runs gates tagged with `ci` environment
- [ ] `make release-gate-prod` runs gates tagged with `production` environment
- [ ] `scripts/check_metrics_gate.py` correctly queries Prometheus and compares against thresholds
- [ ] `scripts/verify_deployment.sh` calls the gate runner before deployment
- [ ] `scripts/production_readiness_check.sh` uses the gate runner instead of inline checks

### Non-Functional

- [ ] Gate runner completes in under 60s for `--environment local` (subset of gates)
- [ ] Gate runner completes in under 300s for `--environment ci` (subset of gates)
- [ ] Single gate timeout honored; hung gate does not block the overall runner
- [ ] Gate report JSON is valid and always written, even when gates fail
- [ ] No secrets or credentials are exposed in the gate report output

### Quality Gates

- [ ] All unit tests pass (`pytest scripts/tests/ -v`)
- [ ] Gate runner works from the repo root
- [ ] `python3 -m py_compile scripts/release_gate_runner.py` passes
- [ ] `python3 -m py_compile scripts/check_metrics_gate.py` passes
- [ ] No hardcoded secrets or tokens in any new file
- [ ] Config JSON is valid

---

## 9. Design Decisions

| # | Decision | Choice | Rationale |
|---|----------|--------|-----------|
| DD1 | Gate configuration format | Single JSON file (`quality/release_gates.json`) | Follows existing config patterns; easier to audit and version-control than scattered Makefile targets |
| DD2 | Environment filtering | Gates declare `environments` list; runner filters by `--environment` flag | Different environments have different needs: local needs fast checks, CI needs comprehensive, prod needs metrics |
| DD3 | Sequential execution in Phase 1 | Gates run one at a time | Simpler implementation, easier debugging, avoids resource contention |
| DD4 | Shell command execution | Gates are shell commands; runner uses `subprocess.run` | All existing checks are scripts; least-invasive approach |
| DD5 | Exit-code-based pass/fail | Gate passes if exit code = 0 | Every existing checker follows this convention |
| DD6 | Prometheus query as separate script | `check_metrics_gate.py` is standalone | Follows Unix philosophy; independently testable; gate runner stays simple |
| DD7 | Report output as JSON file | Machine-readable report | Enables CI/CD integration, audit trail, future dashboard building |
| DD8 | P2 escalation threshold | Configurable threshold escalates P2 to blocking | Prevents warning fatigue; if N warnings accumulate, something is systematically wrong |
| DD9 | No database or Redis dependency | Gate runner is stateless; config is a JSON file | Runner must not depend on infrastructure it's checking |

---

## 10. Dependencies

### Internal Dependencies

| Dependency | Why | Risk |
|------------|-----|------|
| `quality/release_gates.json` | Runner reads this to know which gates to run | Low — new file |
| Existing checker scripts (20 scripts) | Each is called by the runner's command strings | Low — already work standalone |
| `quality/tech_debt_budget.json` | Read by `check_tech_debt_budget.py` gate | Low — existing, stable |
| `quality/coverage_thresholds.json` | Read by coverage gate | Low — existing, stable |
| `scripts/rule_guard_manifest.tsv` | Read by rule guard gate | Low — existing, stable |
| Prometheus (for metric gates) | Queried by `check_metrics_gate.py` | Medium — optional; metric gates only in `production` environment |

### External Dependencies

| Dependency | Why | Risk |
|------------|-----|------|
| Python 3.11+ | Gate runner runtime | Low — already in stack |
| No new pip packages | All imports are stdlib (`subprocess`, `json`, `argparse`, `urllib`) | Zero risk |

### Phase Dependencies

- Phase 2 (consolidation) depends on Phase 1 (framework)
- Phase 3 (metric gates) depends on Phase 1 (framework + `check_metrics_gate.py`)
- Phase 4 (integration) depends on Phases 1-3

---

## 11. Open Questions

### Q1: JSON vs YAML for gate configuration?
- **Context**: JSON does not support comments, making it harder to document thresholds inline.
- **Proposed**: Start with JSON (consistent with all other config files). If the team finds comments essential, migrate to YAML later.

### Q2: Python runner or Makefile target?
- **Context**: The current `local-final-signoff` is a Makefile target. A Python runner is more portable, testable, and configurable.
- **Proposed**: Python runner. The Makefile target delegates to the Python runner.

### Q3: What happens when Prometheus is unavailable during prod gate run?
- **Context**: If Prometheus is down, metric gates fail (blocking). This could be too conservative.
- **Proposed**: Metric gates return exit code 1 when Prometheus unreachable. Deployer can use `--allow-p1-failure` to override. Do not silently pass metric gates.

### Q4: Parallel execution support from Day 1?
- **Context**: `run_all_rule_guards.sh` already supports `--jobs 4`.
- **Proposed**: No. Phase 1 is sequential for simplicity. Add `--jobs N` in follow-up.

### Q5: Gate report archival?
- **Context**: Each run overwrites `quality/release_gate_report.json`. Historical reports may be needed for audits.
- **Proposed**: Overwrite by default. CI environments can archive as build artifact. Add `--archive-dir` later if needed.

### Q6: How should new gates be added?
- **Context**: Multiple team members may add gates.
- **Proposed**: Manual editing of JSON file. Blocking gates (P0/P1) require PR approval.

### Q7: Go gate runner alternative?
- **Context**: Gateway is written in Go; some teams prefer Go tooling.
- **Proposed**: Python runner is simpler and more portable. The JSON config format allows a Go runner later without changing gate definitions.

---

## Appendix A: Gate Runner CLI Reference

```bash
# Run all gates for the local environment
python3 scripts/release_gate_runner.py --environment local

# Run all gates for CI, allowing P1 overrides
python3 scripts/release_gate_runner.py --environment ci --allow-p1-failure

# Run production gates with Prometheus metrics
python3 scripts/release_gate_runner.py --environment production \
  --prometheus-url http://prometheus.internal:9090

# Run a single gate by ID
python3 scripts/release_gate_runner.py --environment local --gate backend_unit_tests

# List all configured gates
python3 scripts/release_gate_runner.py --list-gates

# Save report to a file
python3 scripts/release_gate_runner.py --environment ci --output quality/release_gate_report.json

# Makefile shortcuts
make release-gate           # local environment
make release-gate-ci        # CI environment
make release-gate-prod      # production environment (needs PROMETHEUS_URL)
```

## Appendix B: Example Gate Report Output

```json
{
  "generated_at": "2026-05-06T14:30:00Z",
  "environment": "local",
  "overall_decision": "PASS",
  "total_gates": 12,
  "passed": 11,
  "failed": 0,
  "warnings": 1,
  "skipped": 0,
  "total_duration_seconds": 45.32,
  "results": [
    {
      "gate_id": "backend_unit_tests",
      "category": "correctness",
      "severity": "P0",
      "description": "Backend Python unit tests must pass",
      "status": "PASS",
      "exit_code": 0,
      "duration_seconds": 12.5,
      "stderr_tail": ""
    },
    {
      "gate_id": "infra_preflight",
      "category": "operability",
      "severity": "P1",
      "description": "Infrastructure connectivity check",
      "status": "PASS",
      "exit_code": 0,
      "duration_seconds": 2.3,
      "stderr_tail": ""
    },
    {
      "gate_id": "tech_debt_budget",
      "category": "compliance",
      "severity": "P2",
      "status": "FAIL",
      "exit_code": 1,
      "duration_seconds": 1.2,
      "stderr_tail": "gateway_go_coverage_shortfall_bp exceeded budget: 2900 > 2852"
    }
  ],
  "blocking_failures": [],
  "warning_items": [
    "tech_debt_budget: gateway_go_coverage_shortfall_bp exceeded budget: 2900 > 2852"
  ]
}
```

---

*Spec generated 2026-05-06 by Claude Opus Plan Agent*
*GAP-P4-1: Release Gate -- OBS-015*
