# FV-05 Privacy Community Intelligence Closeout

Date: 2026-05-02
Branch: `codex/FV-05-privacy-community-production`

## Result

FV-05 is now production-wired instead of library-only. Cross-user community intelligence has a single privacy-preserving entry path:

`CommunitySignalBridge.build_privacy_preserving_cohort_signal()` → opt-out filtering → k-anonymity floor → persistent DP budget ledger → Laplace-noised aggregate → durable `CommunityAggregateSignal` → candidate/soft-bias community event.

The implementation intentionally keeps aggregate insights as candidate signals. They can bias community guidance softly, but they do not overwrite personal user state without confirmation.

## Changes

- Added durable models and migration:
  - `community_aggregate_signals`
  - `privacy_budget_ledger`
  - `user_settings.community_intelligence_enabled`
- Added configurable defaults:
  - `COMMUNITY_INTELLIGENCE_ENABLED=true`
  - `COMMUNITY_INTELLIGENCE_MIN_COHORT_SIZE=5`
  - `COMMUNITY_INTELLIGENCE_EPSILON=1.0`
  - `COMMUNITY_INTELLIGENCE_QUERY_EPSILON=0.5`
  - `COMMUNITY_INTELLIGENCE_DAILY_EPSILON=3.0`
- Added admin/user APIs:
  - `GET /community/aggregates`
  - `GET /community/aggregates/insights`
  - `POST /community/aggregates/analyze`
  - `GET /community/aggregates/budget-ledger`
- Added user setting exposure so users can opt out of producing and consuming community intelligence.
- Replaced the previous simplified uniform noise with inverse-CDF Laplace noise.
- Added Prometheus metrics and Grafana dashboard:
  - `sparkle_community_privacy_aggregate_total`
  - `sparkle_community_privacy_budget_spent_epsilon_total`
  - `sparkle_community_privacy_cohort_size`

## Verification

Passed in isolated worktree `/Users/brsama/code/GitHub/Sparkle-project-fv05-production`:

```bash
cd backend && python3 -m py_compile app/signals/privacy_community_intelligence.py app/services/community_signal_bridge.py app/models/community_privacy.py app/api/v1/community_aggregates.py app/models/user_settings.py app/schemas/user_settings.py app/services/user_settings_service.py app/api/v1/user_settings.py app/config/settings.py app/core/metrics.py app/api/v1/router.py tests/unit/test_privacy_community_production.py
```

```bash
cd backend && /Users/brsama/code/GitHub/Sparkle-project/backend/.venv/bin/python -m ruff check app/signals/privacy_community_intelligence.py app/services/community_signal_bridge.py app/models/community_privacy.py app/api/v1/community_aggregates.py app/models/__init__.py app/models/user_settings.py app/schemas/user_settings.py app/services/user_settings_service.py app/api/v1/user_settings.py app/config/settings.py app/core/metrics.py app/api/v1/router.py tests/unit/test_privacy_community_production.py
# All checks passed!
```

```bash
cd backend && SECRET_KEY=test-secret-long-enough-for-unit-tests PYTHONPATH=/Users/brsama/code/GitHub/Sparkle-project-fv05-production/backend /Users/brsama/code/GitHub/Sparkle-project/backend/.venv/bin/python -m pytest tests/unit/test_privacy_community_production.py -q
# 4 passed
```

```bash
python3 -m json.tool monitoring/grafana-dashboards/sparkle-community-privacy.json >/dev/null
git diff --check
```

```bash
cd backend && SECRET_KEY=test-secret-long-enough-for-unit-tests PYTHONPATH=/Users/brsama/code/GitHub/Sparkle-project-fv05-production/backend /Users/brsama/code/GitHub/Sparkle-project/backend/.venv/bin/alembic heads
# c16_20260502 (head)
```

## Remaining Integration Note

The main shared worktree had active FV-01/FV-02/FV-16 uncommitted changes, so this FV-05 implementation was done in an isolated clean worktree and branch. Final integration should merge this branch after resolving the parallel migration sequence with FV-01/FV-02/FV-07.
