# FV-04 · Skill/DomainPack Marketplace 上线 · 完成报告

**Agent**: codex-agent-04
**Branch**: codex/FV-04-marketplace
**Date**: 2026-05-02
**Status**: COMPLETED

## 1. 5/5 标准达成情况

| # | 标准 | 状态 | 证据 |
|---|------|------|------|
| 1 | 新建 marketplace_skills / marketplace_packs / user_skill_adoptions / pack_adoption_history | ✅ | `backend/alembic/versions/c15_20260502_marketplace.py:36` / `:87` / `:127` / `:156` |
| 2 | SQLAlchemy 模型 | ✅ | `backend/app/models/marketplace.py:14` / `:57` / `:92` / `:113`; exported in `backend/app/models/__init__.py` |
| 3 | REST API：列表、预览、采纳、撤销、影响追踪、回滚 | ✅ | `backend/app/api/v1/marketplace.py:97`, `:125`, `:140`, `:260`, `:405` |
| 4 | SkillLifecycleManager system_skill 自动注册 | ✅ | `backend/app/signals/skill_lifecycle.py:203` calls marketplace registration on `to_scope == "system"` |
| 5 | 用户采纳必须显式 confirm=true | ✅ | `backend/app/signals/marketplace.py:904`; API test rejects `confirm=false` |
| 6 | 影响追踪写 pack_adoption_history + trace_id | ✅ | `backend/app/signals/marketplace.py:967`; API endpoint `backend/app/api/v1/marketplace.py:254` |
| 7 | 质量评分基于 outcome / 负反馈 / 适用范围 | ✅ | `backend/app/signals/marketplace.py:673`, refreshed after outcomes at `:1272` |
| 8 | 上架前 PII 扫描 | ✅ | `backend/app/signals/marketplace.py:660`; API test covers PII rejection |
| 9 | 自动下架机制 | ✅ | `backend/app/signals/marketplace.py:694`, applied at `:1279` |
| 10 | Mobile UI marketplace 浏览页 | ✅ | `mobile/lib/features/seed_library/presentation/marketplace/marketplace_screen.dart:11`; route at `mobile/lib/features/seed_library/seed_library_routes.dart:15` |
| 11 | Prometheus + Grafana | ✅ | Metrics in `backend/app/core/metrics.py:271`; dashboard `monitoring/grafana/dashboards/marketplace.json` |
| 12 | 单测 + 集成测 | ✅ | `backend/tests/unit/test_marketplace_service.py:42`; `backend/tests/api/test_marketplace_api.py:70` |

## 2. 文件变更清单

```text
backend/alembic/versions/c15_20260502_marketplace.py       (new)
backend/app/api/v1/marketplace.py                          (new)
backend/app/api/v1/router.py                               (route append)
backend/app/core/metrics.py                                (metrics append)
backend/app/models/marketplace.py                          (new)
backend/app/models/__init__.py                             (model exports)
backend/app/signals/marketplace.py                         (production service + governance)
backend/app/signals/skill_lifecycle.py                     (system promotion handoff)
backend/tests/unit/test_marketplace_service.py             (new)
backend/tests/api/test_marketplace_api.py                  (new)
mobile/lib/core/network/api_endpoints.dart                 (marketplace endpoints)
mobile/lib/features/seed_library/presentation/marketplace/ (new UI)
mobile/lib/features/seed_library/seed_library_routes.dart  (route append)
mobile/lib/features/seed_library/presentation/screens/seed_library_list_screen.dart (entry action)
monitoring/grafana/dashboards/marketplace.json             (new)
```

## 3. 测试证据

### 单测 / API

```bash
cd backend && .venv/bin/pytest tests/unit/test_marketplace_service.py tests/api/test_marketplace_api.py -q
```

```text
collected 6 items
tests/unit/test_marketplace_service.py ....                              [ 66%]
tests/api/test_marketplace_api.py ..                                     [100%]
======================== 6 passed, 2 warnings in 2.33s =========================
```

### Lint / 类型 / Guard

```bash
cd backend && .venv/bin/python -m py_compile app/signals/marketplace.py app/api/v1/marketplace.py app/models/marketplace.py app/signals/skill_lifecycle.py tests/unit/test_marketplace_service.py tests/api/test_marketplace_api.py
```

```text
PASS (no output)
```

```bash
cd backend && .venv/bin/ruff check app/signals/marketplace.py app/api/v1/marketplace.py app/models/marketplace.py app/signals/skill_lifecycle.py tests/unit/test_marketplace_service.py tests/api/test_marketplace_api.py
```

```text
All checks passed!
```

```bash
cd mobile && dart format lib/features/seed_library/presentation/marketplace lib/features/seed_library/seed_library_routes.dart lib/features/seed_library/presentation/screens/seed_library_list_screen.dart lib/core/network/api_endpoints.dart && flutter analyze lib/features/seed_library/presentation/marketplace lib/features/seed_library/seed_library_routes.dart lib/features/seed_library/presentation/screens/seed_library_list_screen.dart lib/core/network/api_endpoints.dart
```

```text
Formatted 7 files (1 changed) in 0.02 seconds.
No issues found! (ran in 7.3s)
```

```bash
cd backend && .venv/bin/alembic heads
```

```text
c15_20260502 (head)
c16_20260502 (head)
c17_20260502 (head)
c18_20260502 (head)
c19_20260502 (head)
c20_20260502 (head)
c21_20260502 (head)
c22_20260502 (head)
fv14_20260502 (head)
fv15_20260502 (head)
fv17_20260502 (head)
```

## 4. 用户视角变化

> 在种子库的 Marketplace 入口中，用户现在能浏览经过证据、隐私和治理检查的 Skill / DomainPack，先查看会影响哪些任务、计划、资料和召回路径，再显式采纳。

具体场景：
- 之前：P4 marketplace 只有内存模型，用户无法预览、采纳、撤销或追踪影响。
- 之后：每次采纳必须确认，后续对 task/plan/source 的影响可带 trace_id 写入历史，负反馈或撤销率过高会自动 deprecated。

## 5. 与其他卡片的协调

- 与 FV-01/FV-02/FV-05/FV-07 共享 `backend/app/api/v1/router.py`、`backend/app/core/metrics.py`、`backend/app/models/__init__.py`：仅追加 FV-04 注册和指标。
- 触及 `backend/app/signals/skill_lifecycle.py` 是为了完成 FV-04 第 4 条自动注册要求；该文件不在原排他清单中，Architect 合并时请重点看这一处小型 handoff。
- 当前工作树已有大量其他 FV 卡片未提交变更，本报告只覆盖 FV-04 文件。

## 6. 已知限制 / 后续

- `alembic heads` 显示当前并行工作树存在多头迁移；FV-04 的 `c15_20260502` 已作为 marketplace head，最终需要 Architect 统一 merge heads。
- FastAPI / Starlette 对 `HTTP_422_UNPROCESSABLE_ENTITY` 给出弃用 warning，但现有代码库大量使用该常量；未在本卡片扩散替换。

## 7. 验收命令一键回放

```bash
cd backend
.venv/bin/python -m py_compile app/signals/marketplace.py app/api/v1/marketplace.py app/models/marketplace.py app/signals/skill_lifecycle.py tests/unit/test_marketplace_service.py tests/api/test_marketplace_api.py
.venv/bin/ruff check app/signals/marketplace.py app/api/v1/marketplace.py app/models/marketplace.py app/signals/skill_lifecycle.py tests/unit/test_marketplace_service.py tests/api/test_marketplace_api.py
.venv/bin/pytest tests/unit/test_marketplace_service.py tests/api/test_marketplace_api.py -q
.venv/bin/alembic heads
cd ../mobile
dart format lib/features/seed_library/presentation/marketplace lib/features/seed_library/seed_library_routes.dart lib/features/seed_library/presentation/screens/seed_library_list_screen.dart lib/core/network/api_endpoints.dart
flutter analyze lib/features/seed_library/presentation/marketplace lib/features/seed_library/seed_library_routes.dart lib/features/seed_library/presentation/screens/seed_library_list_screen.dart lib/core/network/api_endpoints.dart
```
