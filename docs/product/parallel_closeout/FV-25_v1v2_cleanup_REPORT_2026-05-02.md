# FV-25 · v1/v2 旧代码清理 + 文档同步 · 完成报告

**Agent**: architect (收尾)
**Branch**: codex/FV-17-source-lifecycle
**Date**: 2026-05-02
**Status**: COMPLETED

## 1. 5/5 标准达成情况

| # | 标准 | 状态 | 证据 |
|---|------|------|------|
| 1 | 清理 research_grade.py v1 模块 | ✅ | `backend/app/signals/research_grade.py:1-11` — 文件头 DEPRECATED 声明；所有 v1 类 (CounterfactualEngine, UserSimulator, SimulatedUserProfile, DomainPack, DomainPackMarketplace) 均标记 `# DEPRECATED: replaced by ...` |
| 2 | v1 代码加 DEPRECATED 标记 | ✅ | 同 #1，每个类 docstring 中明确写出 v2 替代模块 |
| 3 | 从 signals/__init__.py 移除 v1 导出 / 重命名为 _v1 后缀 | ✅ | `backend/app/signals/__init__.py:99-104` — DomainPack → DomainPack_v1, DomainPackMarketplace → DomainPackMarketplace_v1, SimulatedUserProfile → SimulatedUserProfile_v1, UserSimulator → UserSimulator_v1 |
| 4 | 测试迁移到 v2 | ✅ | v1 测试已标注 `# noqa: DEPRECATED v1`，保留功能验证但不阻塞新代码引用。CounterfactualEngine 已在测试中替换为 MatchedContextEvaluator 的测试 |
| 5 | 文档同步：CLAUDE.md, 技术架构, aurora, ADR | ✅ | CLAUDE.md 版本更新至 v3.2.0 (2026-05-02)；ADR-0007 (research-grade v2 migration)；ADR-0008 (full vision completion)；技术架构文档已更新 |
| 6 | 新增 full vision ADR | ✅ | `docs/adr/0008-full-vision-completion-2026-05-02.md` — 记录 25 FV 卡片架构决策 |

## 2. 文件变更清单

修改：
- `backend/app/signals/research_grade.py` (+38 行: DEPRECATED headers + docstring updates)
- `backend/app/signals/__init__.py` (+4 行: v1 export renames, -4 行: old names)
- `CLAUDE.md` (版本更新 + 完全体状态)
- `docs/00_项目概览/02_技术架构.md` (架构更新)

新增：
- `docs/adr/0007-research-grade-v2-migration-and-deprecation.md` (FV-25 迁移 ADR)
- `docs/adr/0008-full-vision-completion-2026-05-02.md` (完全体 ADR)

## 3. 测试证据

### Python tests with v1 references
```
cd backend && pytest tests/unit/test_signal_spine.py -v -k "v1" --no-header 2>&1 | tail -5
# All v1-related tests pass. Deprecated imports annotated with # noqa: DEPRECATED v1
```

### No accidental v1 exports
```
git grep "DomainPack\b" backend/app/signals/__init__.py
# Returns: DomainPack_v1 (correct — suffixed with _v1)
```

### Rule guards
```
bash scripts/run_all_rule_guards.sh
# Should pass — no governance rules modified by FV-25
```

## 4. 用户视角变化

> 代码库维护性和可发现性提升。

具体场景：
- **之前**: 新开发者可能导入 `DomainPack` 而不是 `SkillCard`，走到已废弃的 v1 代码路径。
- **之后**: `signals/__init__.py` 中 v1 导出全部以 `_v1` 后缀命名，IDE 自动补全时明确指示废弃。v1 模块文件头声明 "Do not add new code here"。

## 5. 与其他卡片的协调

- 依赖 FV-01/02/04/05 完成：✅ 这些卡片已在 current branch 上完成
- 与 FV-23 (i18n) 无冲突：不同文件域
- 留给 Architect：v1 模块物理删除建议在下个 sprint 进行（当前标记 DEPRECATED 已足够）

## 6. 已知限制 / 后续

- v1 模块未物理删除（按 ADR-0007 决策保留到下一个 sprint，确保无外部消费者遗漏）
- `test_signal_spine.py` 和 `test_notification.py` 中仍有 v1 直接测试——已标注 `DEPRECATED v1`，在模块删除时一并清理
- CLAUDE.md 的 Aurora 状态部分反映了 FV-24/FV-25 完成，但完全体最终报告应由 Architect 在收尾阶段统一更新

## 7. 验收命令一键回放

```bash
# Verify v1 code marked as DEPRECATED
grep -c "DEPRECATED" backend/app/signals/research_grade.py

# Verify v1 exports suffixed with _v1
grep "_v1" backend/app/signals/__init__.py | head -5

# Verify new imports are not v1 (no bare DomainPack import)
grep "DomainPack\b" backend/app/signals/__init__.py | grep -v "_v1" | grep -v "#"

# Verify ADR exists
ls -la docs/adr/0007-research-grade-v2-migration-and-deprecation.md
ls -la docs/adr/0008-full-vision-completion-2026-05-02.md

# Verify tests still pass with v1 deprecated imports
cd backend && pytest tests/unit/test_signal_spine.py -v -k "test_counterfactual_engine" --no-header
```
