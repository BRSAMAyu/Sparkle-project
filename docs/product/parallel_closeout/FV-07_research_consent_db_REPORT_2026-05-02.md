# FV-07 Research Consent DB Closeout

Date: 2026-05-02
Branch: `codex/FV-07-consent-db-production`

## Result

Research consent is no longer memory-only. The existing synchronous `ConsentTracker` API remains compatible with existing tests, while production can now use durable async methods backed by PostgreSQL and user-facing REST endpoints.

## Changes

- Added durable models:
  - `ResearchConsent`
  - `ResearchExportUsage`
- Added Alembic migration `c17_20260502_research_consent.py`.
- Extended `ConsentTracker` with DB-backed methods:
  - `grant_consent_db`
  - `revoke_consent_db`
  - `has_consent_db`
  - `check_all_consents_db`
  - `can_include_in_research_db`
  - `get_user_consents_db`
- Revocation now marks active `ResearchExportUsage` rows as `revoked`.
- Added `/research/consent`:
  - `GET` returns required consents, status map, records, and eligibility.
  - `PUT` grants/revokes consent and writes a `DataAccessLog` audit event.

## Verification

```bash
cd backend && python3 -m py_compile app/models/research_consent.py app/signals/research_mode.py app/api/v1/research_consent.py app/api/v1/router.py tests/unit/test_research_consent_persistence.py
```

```bash
cd backend && /Users/brsama/code/GitHub/Sparkle-project/backend/.venv/bin/python -m ruff check app/models/research_consent.py app/signals/research_mode.py app/api/v1/research_consent.py app/api/v1/router.py app/models/__init__.py tests/unit/test_research_consent_persistence.py
# All checks passed!
```

```bash
cd backend && SECRET_KEY=test-secret-long-enough-for-unit-tests PYTHONPATH=/Users/brsama/code/GitHub/Sparkle-project-fv07-consent/backend /Users/brsama/code/GitHub/Sparkle-project/backend/.venv/bin/python -m pytest tests/unit/test_research_consent_persistence.py tests/unit/spine/test_specialized_features.py -k "consent" -q
# 6 passed, 56 deselected
```

```bash
cd backend && SECRET_KEY=test-secret-long-enough-for-unit-tests PYTHONPATH=/Users/brsama/code/GitHub/Sparkle-project-fv07-consent/backend /Users/brsama/code/GitHub/Sparkle-project/backend/.venv/bin/alembic heads
# c17_20260502 (head)
```

## Integration Note

This branch was built from the shared integration commit `73253cdc4`. It intentionally does not include FV-05 or other parallel FV branches; final merge will need a migration-order reconciliation.
