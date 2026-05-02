# FV-02 · SafeExperimentRegistry 接入生产管道 · 完成报告

**Agent**: codex-agent-FV-02  
**Branch**: codex/FV-02-safe-experiments  
**Date**: 2026-05-02  
**Status**: PARTIAL - implementation complete; pytest/import validation is blocked by an unrelated dirty-worktree SQLAlchemy model error in `backend/app/models/community_privacy.py`.

## 1. 5/5 标准达成情况

| # | 标准 | 状态 | 证据 |
|---|------|------|------|
| 1 | `safe_experiments` + `safe_experiment_episodes` migration | Done | `backend/alembic/versions/c14_20260502_safe_experiments.py:35` creates `safe_experiments`; `:78` creates `safe_experiment_episodes`; `:110` adds `user_settings.safe_experiments_opt_out`. |
| 2 | SQLAlchemy 模型挂到 `models/__init__.py` | Done | `backend/app/models/safe_experiment.py:11` and `:49` define models; `backend/app/models/__init__.py` imports/exports them. |
| 3 | CRUD + lifecycle + opt-out API | Done | `backend/app/api/v1/safe_experiments.py:180` create; `:236` list; `:257` get; `:267` update; `:291` delete; `:304` transition; `:407`/`:418` opt-out. |
| 4 | 30 分钟 guardrail monitor 自动暂停 + incident trace | Done | `backend/app/core/celery_tasks.py:2815` sweeps active experiments, pauses canary/live violations, and writes incident traces; `backend/app/celery_schedule.py` registers every 1800s. |
| 5 | Promotion gate bridge to FV-09 | Done | `backend/app/signals/safe_experiment_promotion_gate.py` evaluates shadow/canary/concluded gates and enqueues Redis approval candidates. |
| 6 | 高风险场景禁止 bandit | Done | `backend/app/signals/safe_experiment_platform.py:439` blocks opt-out, D0, crisis, critical deadline, and fatigue-critical contexts; `:616` adds `select_arm()`. |
| 7 | 用户 opt-out 写入 `user_settings` 并选择前检查 | Done | API writes `UserSettings.safe_experiments_opt_out`; `backend/app/signals/spine_orchestrator.py:2859` checks Redis opt-out before bandit selection. |
| 8 | Prometheus + Grafana | Done | `backend/app/core/metrics.py` adds FV2 counters/gauge; `monitoring/prometheus.yml` adds `sparkle_safe_experiments`; `monitoring/grafana/dashboards/safe_experiments.json` adds the dashboard. |
| 9 | Tests | Partial | Added unit/API tests, but pytest is blocked before collection by an unrelated `community_privacy.py` reserved `metadata` attribute error. |
| 10 | Remove silent SHADOW try/except | Done | `backend/app/signals/spine_orchestrator.py:2882` now logs and propagates a `RuntimeError` instead of swallowing the failure. |

## 2. 文件变更清单

```text
backend/alembic/versions/c14_20260502_safe_experiments.py
backend/app/api/v1/safe_experiments.py
backend/app/api/v1/router.py
backend/app/api/v1/user_settings.py
backend/app/celery_schedule.py
backend/app/core/celery_tasks.py
backend/app/core/metrics.py
backend/app/models/__init__.py
backend/app/models/safe_experiment.py
backend/app/models/user_settings.py
backend/app/schemas/user_settings.py
backend/app/services/user_settings_service.py
backend/app/signals/safe_experiment_platform.py
backend/app/signals/safe_experiment_promotion_gate.py
backend/app/signals/spine_orchestrator.py
backend/tests/api/test_safe_experiments_api.py
backend/tests/unit/test_safe_experiment_platform.py
monitoring/grafana/dashboards/safe_experiments.json
monitoring/prometheus.yml
```

## 3. 测试证据

### 单测 / API

```text
$ cd backend && pytest tests/unit/test_safe_experiment_platform.py tests/api/test_safe_experiments_api.py
ImportError while loading conftest '/Users/brsama/code/GitHub/Sparkle-project/backend/tests/conftest.py'.
sqlalchemy.exc.InvalidRequestError: Attribute name 'metadata' is reserved when using the Declarative API.
Source: backend/app/models/community_privacy.py:36
```

### Lint / 类型 / Guard

```text
$ cd backend && python3 -m py_compile app/signals/safe_experiment_platform.py app/signals/safe_experiment_promotion_gate.py app/models/safe_experiment.py app/api/v1/safe_experiments.py app/api/v1/user_settings.py app/schemas/user_settings.py app/services/user_settings_service.py app/core/celery_tasks.py app/celery_schedule.py tests/unit/test_safe_experiment_platform.py tests/api/test_safe_experiments_api.py
PASS (exit code 0, no output)
```

```text
$ cd backend && /opt/homebrew/opt/python@3.11/bin/python3.11 - <<'PY' ...
sqlalchemy.exc.InvalidRequestError: Attribute name 'metadata' is reserved when using the Declarative API.
Source: backend/app/models/community_privacy.py:36
```

## 4. 用户视角变化

In adaptive learning flows, risky experimentation is now explicitly bounded. A student who is on D0 exam day, in crisis/fatigue-critical state, or opted out receives the primary conservative strategy instead of exploration. Admins can create, inspect, advance, pause, and monitor experiments through `/api/v1/safe-experiments`.

## 5. 与其他卡片的协调

- Shared files touched by FV-01/FV-03/FV-04/FV-05/FV-07/FV-09 were append-only for FV2 content: `router.py`, `celery_tasks.py`, `celery_schedule.py`, `models/__init__.py`, `prometheus.yml`.
- FV-09 coordination: promotion candidates are queued as Redis payloads under `safe_experiment:promotion_candidates` and persisted on `SafeExperiment.promotion_candidate`; FV-09 can consume these without schema coupling.
- Architect handoff: resolve the unrelated `community_privacy.py` SQLAlchemy `metadata` mapping blocker before running full backend pytest/import validation.

## 6. 已知限制 / 后续

- Validation is blocked by a dirty-worktree model from another FV card, not by FV2 code paths.
- The orchestrator uses the Redis opt-out cache for hot-path selection. If a user settings row is changed outside the FV2 endpoint, a cache refresh hook should be added in final integration.

## 7. 验收命令一键回放

```bash
cd backend
python3 -m py_compile app/signals/safe_experiment_platform.py app/signals/safe_experiment_promotion_gate.py app/models/safe_experiment.py app/api/v1/safe_experiments.py app/api/v1/user_settings.py app/schemas/user_settings.py app/services/user_settings_service.py app/core/celery_tasks.py app/celery_schedule.py tests/unit/test_safe_experiment_platform.py tests/api/test_safe_experiments_api.py
pytest tests/unit/test_safe_experiment_platform.py tests/api/test_safe_experiments_api.py
```
