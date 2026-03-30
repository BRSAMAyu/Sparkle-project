# Final Release Snapshot 1.0.0

- Date: 2026-03-22
- Version: `1.0.0+1`
- Branch: `本地全量收尾`

## Verification Summary

- Flutter analyze: `0 errors`, `0 warnings`, info-only lint backlog remains.
- Flutter test: `516 passed`, `6 skipped`, `0 failed`.
- Flutter live integration smoke: `test/integration/full_stack_e2e_test.dart` passed.
- Go gateway tests: `cd backend/gateway && go test ./...` passed.
- Python runtime compile check: `auth_session_service.py` and `deps.py` passed `py_compile`.

## Release Readiness Notes

- Duplicate source asset removed:
  - kept `mobile/assets/icons/Gemini_Generated_Image_yt8rz9yt8rz9yt8r.png`
  - removed duplicate `(... 1).png`
- Audio asset bundle baseline: `mobile/assets/audio` = `17M`
- Backend dependency declaration now includes `structlog>=24.1.0`
- Local backend venv and running `sparkle_api` container were updated with `structlog` for verification parity

## Quality Gates Confirmed

- Full Flutter suite is green after fixing:
  - `ActionCard` specialized card default expansion
  - secure storage mock signature drift in auth repository tests
  - websocket event timing flake in full-suite runs
  - backend auth session duplicate insert path
  - backend missing `structlog` runtime dependency
- Gateway container healthy on `:8080`
- API container healthy on `:8000`

## Monitoring and Runbooks Present

- Grafana dashboard:
  - `monitoring/grafana-dashboards/sparkle-production-admin-ops.json`
- Alerts:
  - `monitoring/sparkle_slo_alerts.yml`
  - `monitoring/sparkle_production_baseline_alerts.yml`
  - `monitoring/celery_alerts.yml`
- Runbook:
  - `monitoring/runbooks/incident_response.md`
- Backup / restore:
  - `scripts/backup_prod_data.sh`
  - `scripts/restore_prod_data.sh`

## Known Non-Blocking Items

- Flutter analyze still contains info-level lint only; no error/warning gate violations.
- Performance benchmark outputs are recorded by test suite, but no new benchmark thresholds were changed in this snapshot.
- External provider key rotation must still be completed in provider dashboards if any historical exposure policy requires it; repository state alone cannot prove that step.

## Commands Used

```bash
cd mobile && flutter test
cd mobile && flutter test test/integration/full_stack_e2e_test.dart -r compact
cd backend/gateway && go test ./...
cd backend && .venv/bin/python -m py_compile app/services/auth_session_service.py app/api/deps.py
```
