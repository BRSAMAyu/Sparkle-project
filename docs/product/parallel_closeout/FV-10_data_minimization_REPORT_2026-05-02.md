# FV-10 · DataMinimizationAuditor 扩覆盖 + fail-closed · 完成报告

**Agent**: codex-agent-10
**Branch**: codex/FV-10-data-minimization
**Date**: 2026-05-02
**Status**: COMPLETED_WITH_EXTERNAL_BLOCKER

## 1. 5/5 标准达成情况

| # | 标准 | 状态 | 证据 |
|---|------|------|------|
| 1 | 扩展 `TARGET_MODEL_SCOPES` 至少覆盖 15 个跨用户/跨 sprint/长期模型 | DONE | `backend/app/core/data_minimization.py:51` 注册 15 个愿景指定 canonical scope，并扩展到 27 个长期/跨用户 scope |
| 2 | `SPARKLE_DATA_MINIMIZATION_MODE=audit/enforce`，prod 默认 enforce | DONE | `backend/app/core/data_minimization.py:536` 根据显式模式或 `ENVIRONMENT/APP_ENV/SPARKLE_ENV` 解析；production/prod 默认 enforce |
| 3 | enforce 未注册模型抛 `DataMinimizationViolation` | DONE | `backend/app/core/data_minimization.py:505` 提供带 `audit_record`/`fallback_data` 的异常；`backend/app/core/data_minimization.py:669` enforce 阻断未知模型 |
| 4 | CI guard 扫描跨用户模型，未注册即失败 | DONE | `scripts/guards/check_data_minimization_coverage.py:174` 检查必需 canonical scope 和 AST 发现的高风险跨用户模型 |
| 5 | 注册到 `scripts/rule_guard_manifest.tsv` | DONE | `scripts/rule_guard_manifest.tsv:64` 新增 `GOV-DATA-MIN` |
| 6 | 单测 + CI 集成测 | DONE | `backend/tests/unit/test_data_minimization.py:19` 覆盖 scope、strip、alias、audit/enforce、prod 默认、manifest guard |

## 2. 文件变更清单

```
backend/app/core/data_minimization.py                 | 606 +++++++++++++++++++++++++++++++++-
scripts/guards/check_data_minimization_coverage.py    | 212 ++++++++++++
backend/tests/unit/test_data_minimization.py          | 127 +++++++
scripts/rule_guard_manifest.tsv                       |   1 +
docs/product/parallel_closeout/FV-10_data_minimization_REPORT_2026-05-02.md | new
.claude/fix-progress/FV-10.done                       | new
```

## 3. 测试证据

### 单测

```
cd backend && ../backend/.venv/bin/python -m pytest --confcutdir=tests/unit tests/unit/test_data_minimization.py -q
collected 7 items
tests/unit/test_data_minimization.py .......                             [100%]
7 passed in 2.99s
```

### 集成 / Guard

```
bash scripts/run_all_rule_guards.sh --rule GOV-DATA-MIN
[Rule GOV-DATA-MIN] START
[GOV-DATA-MIN] PASS - 15 canonical scopes and 44 high-risk model aliases covered
[Rule GOV-DATA-MIN] DONE
all rule guards passed (1 rules)
```

### Lint / 类型 / 编译

```
backend/.venv/bin/python -m py_compile backend/app/core/data_minimization.py scripts/guards/check_data_minimization_coverage.py
PASS
```

格式化：

```
backend/.venv/bin/python -m black backend/app/core/data_minimization.py scripts/guards/check_data_minimization_coverage.py backend/tests/unit/test_data_minimization.py
All done; 3 files reformatted.
```

### 外部阻塞

普通 pytest 入口会加载 `backend/tests/conftest.py`，当前被已有模型问题阻塞：

```
cd backend && ../backend/.venv/bin/python -m pytest tests/unit/test_data_minimization.py -q
ImportError while loading conftest ...
sqlalchemy.exc.InvalidRequestError: Attribute name 'metadata' is reserved when using the Declarative API.
```

阻塞点来自现有 `backend/app/models/community_privacy.py`，不是 FV-10 修改文件。FV-10 使用 `--confcutdir=tests/unit` 验证自身测试，避免加载该全局 fixture。

## 4. 用户视角变化

之前：新增跨用户或长期记忆类存储路径如果没有注册数据最小化 scope，会在未知模型路径上 fail-open，可能把额外字段直接透传。

之后：生产默认 enforce。未知模型会被阻断并携带可审计 `audit_record`，已注册模型只保留 scope 内字段；CI guard 会在新增高风险跨用户模型但未注册 scope 时失败。

## 5. 与其他卡片的协调

- `scripts/rule_guard_manifest.tsv` 是共享文件：仅追加 `GOV-DATA-MIN` 一行。
- 工作树中存在大量其他 FV 卡片未提交改动；本卡未回滚、未修改其内容。
- 留给 Architect：解决 `community_privacy.metadata` 的全局 pytest collection blocker 后，可去掉本报告中的外部阻塞备注。

## 6. 已知限制 / 后续

- Guard 以 AST 扫描高风险跨用户/长期模型别名，覆盖 44 个当前模型别名；如果未来新增风险模型命名完全不含 guard 词根，需要同步扩展 `HIGH_RISK_MODEL_TERMS`。
- `DataMinimizationViolation.audit_record` 已提供上层写审计和 prompt 降级所需事实；具体审计落库由调用方捕获后执行。

## 7. 验收命令一键回放

```bash
backend/.venv/bin/python -m py_compile backend/app/core/data_minimization.py scripts/guards/check_data_minimization_coverage.py
cd backend && ../backend/.venv/bin/python -m pytest --confcutdir=tests/unit tests/unit/test_data_minimization.py -q
cd .. && bash scripts/run_all_rule_guards.sh --rule GOV-DATA-MIN
```
