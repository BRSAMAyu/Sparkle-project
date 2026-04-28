# Sparkle Test Methodology

## Test Categories

### Unit Tests (1024+ tests)
- **Spine subsystem**: `tests/unit/spine/` — 18 modular test files
- **Signals**: types, detectors, ranker, state register, directives, outcome attribution
- **Services**: notification, memory, achievement, community, galaxy
- **Run**: `cd backend && pytest tests/unit/ -q --timeout=120`

### E2E Integration Tests (12 tests)
- **Full pipeline**: `tests/unit/spine/test_e2e_pipeline.py`
- **Coverage**: all 6 divine moments, CRDT merge, consent tracking, data deletion, metrics rollover, error bridge
- **Run**: `cd backend && pytest tests/unit/spine/test_e2e_pipeline.py -v`

### Acceptance Tests (21 scripts)
- **Location**: `backend/scripts/*_acceptance.py`
- **Coverage**: chat, galaxy, community, achievement, focus, calendar, security, API contracts
- **Run**: `cd backend && python scripts/ai_chat_multiturn_acceptance.py`

### Governance Rule Guards (17 scripts)
- **Location**: `scripts/guards/check_rule_*.py`
- **Manifest**: `scripts/rule_guard_manifest.tsv` (61 rules)
- **Run**: `bash scripts/run_all_rule_guards.sh` or `bash scripts/run_all_rule_guards.sh --rule AO`

### Go Tests
- **Location**: `backend/gateway/**/*_test.go` (43 files)
- **Run**: `cd backend/gateway && go test ./...`

### Flutter Tests
- **Location**: `mobile/test/**/*_test.dart` (207 files)
- **Run**: `cd mobile && flutter test`

## Verification Commands

```bash
# Spine unit tests — must be 1024+
cd backend && pytest tests/unit/spine/ -q --timeout=120

# Full backend suite
cd backend && pytest tests/ -q --timeout=300

# Test count verification
cd backend && pytest tests/unit/spine/ --co -q | tail -1

# No duplicate test names
cd backend && pytest tests/unit/spine/ --co -q | grep "::" | sort | uniq -d

# Governance guards — all must pass
bash scripts/run_all_rule_guards.sh

# Lint check
ruff check backend/app/signals/ backend/app/services/ backend/app/api/
```

## Coverage Expectations

| Subsystem | Min Tests | Files |
|-----------|-----------|-------|
| Signal Spine (8 layers) | 1024 | `tests/unit/spine/` (18 files) |
| E2E Pipeline | 12 | `tests/unit/spine/test_e2e_pipeline.py` |
| Governance Rules | 17 guards | `scripts/guards/` |
| Go Gateway | 43 test files | `backend/gateway/` |
| Flutter | 207 test files | `mobile/test/` |

## CI Integration

All tests run in CI via `.github/workflows/ci.yml`:
1. **lint**: ruff + mypy (Python), golangci-lint (Go), flutter analyze
2. **backend-test**: Python unit + contract + workflow tests
3. **flutter-test**: Flutter unit + widget + integration tests
4. **security-scan**: Trivy + Gitleaks
