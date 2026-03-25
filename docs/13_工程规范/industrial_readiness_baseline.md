# Sparkle Industrial Readiness Baseline (M1)

Last updated: 2026-02-07

## Scope

This baseline is the execution anchor for the 10-week industrial readiness program under feature freeze.

## Current factual baseline

### Test status

- Backend: `pytest -q` => **897 passed, 180 skipped, 0 failed**
- Gateway: `go test ./...` => **pass**
- Flutter: `flutter test` => **pass**

### Warning / debt metrics (budget anchors)

- `datetime.utcnow(` occurrences in backend app/tests: **467**
- `class Config:` occurrences in backend app/tests: **61**
- `json_encoders` occurrences in backend app/tests: **1**
- `min_items=` occurrences in backend app/tests: **1**

Source of truth:
- `quality/tech_debt_budget.json`
- `scripts/check_tech_debt_budget.py`

### CI guardrails (current)

- Coverage thresholds currently enforced by CI:
  - Go: **4**
  - Python: **25**
  - Flutter: **8**
- New M1 gate: technical debt budget must not increase.

## M1 deliverables (done definition)

- Reproducible baseline snapshot script exists.
- Warning/debt budgets are codified and executable.
- CI blocks merges when debt increases above frozen budget.
- DoD and triage policy are documented.

## Execution cadence

- Weekly baseline refresh command:

```bash
python3 scripts/collect_quality_baseline.py --output quality/baseline_snapshot.json
```

- Optional full validation mode:

```bash
python3 scripts/collect_quality_baseline.py --run-checks --output quality/baseline_snapshot_full.json
```

- Debt budget enforcement:

```bash
python3 scripts/check_tech_debt_budget.py
```
