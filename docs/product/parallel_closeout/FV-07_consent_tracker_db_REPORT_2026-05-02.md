# FV-07 · ConsentTracker DB 持久化 · 完成报告

**Agent**: codex-agent-FV-07
**Branch**: codex/FV-07-consent-tracker-db
**Date**: 2026-05-02
**Status**: PARTIAL - code complete, validation blocked by unrelated shared-tree import error

## 1. 5/5 标准达成情况

| # | 标准 | 状态 | 证据 |
|---|------|------|------|
| 1 | 新建迁移 `c18_*_consent_records.py` | Done | `backend/alembic/versions/c18_20260502_consent_records.py:41` creates `research_consent_records`. |
| 2 | SQLAlchemy 模型挂 `models/__init__.py` | Done | `backend/app/models/research_consent.py:12`, `backend/app/models/__init__.py:194`. |
| 3 | `ConsentTracker` grant/revoke/check 走 DB | Done | `backend/app/signals/research_mode.py:962`, `backend/app/signals/research_mode.py:1052`, `backend/app/signals/research_mode.py:1106`. |
| 4 | 服务重启后状态保持 | Done | Source of truth is PostgreSQL; tests cover a second tracker instance in `backend/tests/unit/test_research_consent_tracker.py`. |
| 5 | 撤销立即生效 | Done | `has_consent_async()` always queries active DB rows, bypassing stale positive cache. |
| 6 | 审计字段 reason/initiator/IP hash | Done | Migration fields at `backend/alembic/versions/c18_20260502_consent_records.py:51`; hashing at `backend/app/signals/research_mode.py:903`. |
| 7 | 用户可见 API | Done | `backend/app/api/v1/research_consent.py:73`, `backend/app/api/v1/research_consent.py:90`, router include at `backend/app/api/v1/router.py:169`. |
| 8 | 单测 + 集成测 | Blocked | Tests were written, but pytest cannot load shared `app.models` because FV-05-owned `community_privacy.metadata` is a reserved SQLAlchemy name. |

## 2. 文件变更清单

```
 M backend/alembic/env.py
 M backend/app/api/v1/router.py
 M backend/app/models/__init__.py
 M backend/app/signals/research_mode.py
 M backend/tests/conftest.py
 M backend/tests/unit/spine/test_e2e_pipeline.py
 M backend/tests/unit/spine/test_specialized_features.py
?? backend/alembic/versions/c18_20260502_consent_records.py
?? backend/app/api/v1/research_consent.py
?? backend/app/models/research_consent.py
?? backend/tests/unit/test_research_consent_tracker.py
```

## 3. 测试证据

### 单测

```
cd backend && pytest tests/unit/test_research_consent_tracker.py ...
ImportError while loading conftest
sqlalchemy.exc.InvalidRequestError: Attribute name 'metadata' is reserved when using the Declarative API.
File: backend/app/models/community_privacy.py:36
```

### 集成测

```
Not reached: same shared app.models import error blocks pytest collection before FV-07 tests execute.
```

### Lint / 类型 / Guard

```
python3 -m compileall -q backend/app/models/research_consent.py backend/app/signals/research_mode.py backend/app/api/v1/research_consent.py backend/tests/unit/test_research_consent_tracker.py
# PASS, no output

cd backend && alembic heads
sqlalchemy.exc.InvalidRequestError: Attribute name 'metadata' is reserved when using the Declarative API.
File: backend/app/models/community_privacy.py:36
```

## 4. 用户视角变化

用户现在可以通过 `/api/v1/research/consent` 查看自己当前研究同意状态，并通过 `/api/v1/research/consent/revoke` 立即撤销某个研究协议的授权。撤销后研究管道的 `has_consent_async()` 会直接读 DB active row，立刻返回 false。

## 5. 与其他卡片的协调

- 共享文件 `backend/app/api/v1/router.py`、`backend/app/models/__init__.py`、`backend/alembic/env.py`：仅追加 FV-07 import/include。
- 与 FV-05 冲突点：当前共享树的 `backend/app/models/community_privacy.py` 在 SQLAlchemy 声明式模型中使用保留名 `metadata`，阻塞 Alembic 和 pytest collection。FV-07 未修改该文件。
- 留给 Architect：FV-05 修复后，重跑本文第 7 节命令。

## 6. 已知限制 / 后续

- 本卡只实现后端 API，移动端设置页入口不在 FV-07 文件边界内。
- 同步兼容方法保留给脚本使用；生产路径应使用 `*_async` 并传入请求作用域 DB session。

## 7. 验收命令一键回放

```bash
python3 -m compileall -q backend/app/models/research_consent.py backend/app/signals/research_mode.py backend/app/api/v1/research_consent.py backend/tests/unit/test_research_consent_tracker.py
cd backend && alembic heads
cd backend && pytest tests/unit/test_research_consent_tracker.py tests/unit/spine/test_specialized_features.py::test_consent_grant_and_check tests/unit/spine/test_specialized_features.py::test_consent_revoke_blocks_research tests/unit/spine/test_specialized_features.py::test_consent_check_all_types tests/unit/spine/test_e2e_pipeline.py::test_e2e_consent_required_before_research_inclusion
```
