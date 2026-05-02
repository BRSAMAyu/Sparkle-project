# FV-05 · PrivacyPreservingCommunityEngine 接入 · 完成报告

**Agent**: codex-agent-FV-05
**Branch**: codex/FV-05-privacy-community-intelligence
**Date**: 2026-05-02
**Status**: PARTIAL - code complete; pytest is blocked by unrelated FV-04 mapper state in the shared worktree

## 1. 5/5 标准达成情况

| # | 标准 | 状态 | 证据 |
|---|------|------|------|
| 1 | 迁移创建 `community_aggregate_signals`、`privacy_budget_ledger` | Done | `backend/alembic/versions/c16_20260502_community_aggregates.py:18` creates c16 revision and both tables. |
| 2 | SQLAlchemy 模型 | Done | `backend/app/models/community_privacy.py:11` and `backend/app/models/community_privacy.py:36`; exported from `backend/app/models/__init__.py`. |
| 3 | `community_signal_bridge.py` 聚合走隐私引擎 | Done | `backend/app/services/community_signal_bridge.py:82` computes group task aggregates via `PrivacyPreservingCommunityEngine`. |
| 4 | k 阈值默认 5 | Done | `backend/app/config/settings.py:141`; bridge enforces `max(5, setting)` at `backend/app/services/community_signal_bridge.py:106`. |
| 5 | DP 噪声默认开启，epsilon 可配置 | Done | `backend/app/config/settings.py:142`; Laplace path at `backend/app/signals/privacy_community_intelligence.py:234`. |
| 6 | PrivacyBudgetLedger 持久化 | Done | `backend/app/services/community_signal_bridge.py:232` writes accepted/denied ledger rows. |
| 7 | API `/api/v1/community/aggregates` | Done | `backend/app/api/v1/community_aggregates.py:26`, router include in `backend/app/api/v1/router.py`. |
| 8 | CommunityDirective soft-bias-only path | Done | Bridge builds `ActionableSignal -> PolicyDecision -> CommunityDirective` and stores `hard_override_allowed=False` at `backend/app/services/community_signal_bridge.py:151`. |
| 9 | 用户关闭社群智能双向隔离 | Done | `backend/app/models/user_settings.py:20`, schema/API exposure, and bridge opt-out checks at `backend/app/services/community_signal_bridge.py:72`. |
| 10 | Prometheus + Grafana | Done | Metrics at `backend/app/core/metrics.py:1053`; scrape at `monitoring/prometheus.yml:45`; dashboard at `monitoring/grafana/dashboards/community_privacy.json`. |
| 11 | 单测覆盖 | Added, blocked | `backend/tests/unit/test_community_privacy_fv05.py:28` covers k floor, budget exhaustion, opt-out exclusion, user opt-out. Running pytest currently fails before tests execute due FV-04 `MarketplaceSkill.adoptions` mapper missing FK. |

## 2. 文件变更清单

```
backend/alembic/versions/c16_20260502_community_aggregates.py
backend/app/api/v1/community_aggregates.py
backend/app/models/community_privacy.py
backend/app/services/community_signal_bridge.py
backend/app/signals/privacy_community_intelligence.py
backend/app/core/metrics.py
backend/app/config/settings.py
backend/app/models/user_settings.py
backend/app/schemas/user_settings.py
backend/app/services/user_settings_service.py
backend/app/api/v1/user_settings.py
backend/app/api/v1/router.py
backend/app/models/__init__.py
backend/app/signals/__init__.py
monitoring/prometheus.yml
monitoring/grafana/dashboards/community_privacy.json
backend/tests/unit/test_community_privacy_fv05.py
```

## 3. 测试证据

### 单测
```
./.venv/bin/pytest tests/unit/test_community_privacy_fv05.py -q
collected 4 items
ERROR tests/unit/test_community_privacy_fv05.py::...
sqlalchemy.exc.NoForeignKeysError: Could not determine join condition between parent/child tables on relationship MarketplaceSkill.adoptions
```

### Smoke / Lint
```
./.venv/bin/python -m py_compile app/models/community_privacy.py app/api/v1/community_aggregates.py app/services/community_signal_bridge.py app/signals/privacy_community_intelligence.py
PASS

./.venv/bin/python -m py_compile alembic/versions/c16_20260502_community_aggregates.py
PASS

Privacy engine direct smoke:
small cohort suppressed, large cohort reliable, budget exhaustion raises PrivacyBudgetExceeded
PASS

Grafana JSON parse:
dashboard ok
```

## 4. 用户视角变化

在冲刺群任务完成率等社群洞察场景中，Sparkle 现在只会跨用户使用匿名、k>=5、带 DP 噪声且预算受控的聚合信号。关闭社群智能的用户不会贡献到聚合，也不会消费聚合洞察。

## 5. 与其他卡片的协调

- 共享文件 `backend/app/core/metrics.py`、`backend/app/api/v1/router.py`、`monitoring/prometheus.yml`：只追加 FV-05 内容。
- 与 FV-22：k 阈值已经默认上调到 5。
- 与 FV-04：当前 pytest 阻塞来自 marketplace mapper，需要 FV-04/Architect 修复后重跑 FV-05 单测。

## 6. 已知限制 / 后续

- 当前实现先覆盖 group task completion aggregate；后续可继续把更多跨用户统计入口迁到 `CommunitySignalBridge` 的同一隐私预算路径。
- `monitoring/grafana/dashboards/community_privacy.json` 按任务卡指定路径创建；如部署只加载 `monitoring/grafana-dashboards/`，Architect 需要在收尾时同步 provisioning。

## 7. 验收命令一键回放

```bash
cd backend
./.venv/bin/python -m py_compile app/models/community_privacy.py app/api/v1/community_aggregates.py app/services/community_signal_bridge.py app/signals/privacy_community_intelligence.py
./.venv/bin/python -m py_compile alembic/versions/c16_20260502_community_aggregates.py
./.venv/bin/pytest tests/unit/test_community_privacy_fv05.py -q
```
