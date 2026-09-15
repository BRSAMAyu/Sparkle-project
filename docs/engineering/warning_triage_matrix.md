# Warning Triage Matrix (M1)

Last updated: 2026-02-07

## Severity policy

## `P0` Blocking

Criteria:
- Can cause runtime failure/data corruption/type mismatch.
- Async errors that can drop writes/events (`never awaited` in production paths).
- Timezone-aware vs naive mismatch that breaks DB writes.

Required action:
- Must be fixed before release.
- New `P0` warning introduction is forbidden.

## `P1` High risk

Criteria:
- High-confidence deprecations with known removal timeline.
- Contract drift risk in API/proto/schema layers.
- Lint warnings that can hide correctness defects.

Required action:
- Tracked weekly with strict burn-down.
- No net increase allowed in feature-freeze period.

## `P2` Cleanup

Criteria:
- Style/readability/perf hygiene without direct correctness impact.

Required action:
- Fix after `P0/P1` is stable.

## Current hot spots (from repository scan)

Top `datetime.utcnow(` concentration:
1. `backend/app/learning/ab_test_framework_enhanced.py` (15)
2. `backend/app/services/knowledge_integration_service.py` (14)
3. `backend/app/services/achievement_engine.py` (12)
4. `backend/app/services/review_history_service.py` (10)
5. `backend/app/services/arbitration_service.py` (9)

Top migration debt (Pydantic v2):
- `class Config:` count: 61 (backend schemas/api modules)
- `json_encoders`: 1
- `min_items=`: 1

## Mapping rules

- `datetime.utcnow` in app runtime => `P1` (promote to `P0` if causes runtime mismatch)
- `class Config` / `json_encoders` / `min_items` => `P1`
- `AsyncMock was never awaited` in tests => `P1`
- `never awaited` in non-test runtime => `P0`

## Enforcement

- Budget gate:
  - `scripts/check_tech_debt_budget.py`
  - `quality/tech_debt_budget.json`
- Baseline collection:
  - `scripts/collect_quality_baseline.py`
