# Contract Guardrails (M3)

Last updated: 2026-02-07

## Objective

Prevent interface drift across backend/gateway/mobile by making contract changes explicit and reviewable.

## Guardrails

1. **OpenAPI snapshot gate**
- Snapshot file: `docs/contracts/openapi_snapshot.json`
- Export script: `scripts/export_openapi_snapshot.py`
- Check script: `scripts/check_openapi_contract.py`
- CI: backend-test job (`OpenAPI Contract Check`)

2. **Proto generated-code consistency gate**
- Existing CI gate: `.github/workflows/ci.yml` (`proto-check` job)
- Enforces buf breaking checks, generated code sync, migration docs/ADR updates.

3. **Technical debt no-regression gate**
- Existing M1 gate: `scripts/check_tech_debt_budget.py`

## Developer workflow

- Validate OpenAPI contract:

```bash
make openapi-contract-check
```

- If intentional API shape changes exist:

```bash
python3 scripts/check_openapi_contract.py --update
```

Then include in PR:
- changed endpoints/schemas summary,
- compatibility note,
- rollback strategy.
