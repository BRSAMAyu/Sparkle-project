# Rule AT - Data Pipeline Governance

状态：路径兼容入口，当前权威实现见 `docs/aurora/rule_at_no_orphan.md`。

## 背景

`SPARKLE_VISION_ANCHOR_LIST_2026-04-19.md` 中登记过旧路径：

- `docs/aurora/rule_at_data_pipeline.md`

Stage 34 / Stage 36 收束后，Rule AT 的可执行定义落到了：

- `docs/aurora/rule_at_no_orphan.md`
- `scripts/guards/check_rule_at_no_orphan.py`
- `backend/tests/unit/test_rule_at_guard.py`
- `scripts/rule_guard_manifest.tsv`

本文件用于保留愿景清单中的历史路径，避免路线文档断链。

## 当前规则语义

Rule AT 当前锁定为 No Orphan Data / No Orphan Service：

- `backend/app/services/**/*.py` 和 `backend/app/consumers/**/*.py` 中的非 deprecated runtime 文件必须被至少一个非测试 runtime 文件引用。
- 允许例外，但必须同时满足代码注释 `# rule-at: orphan-by-design <reason>` 与 `docs/aurora/rule_at_exceptions.md` 登记。
- 目标是防止 Aurora 多阶段 wiring 后留下静默死代码、孤儿服务或孤儿消费者。

## 验证入口

```bash
python scripts/guards/check_rule_at_no_orphan.py
scripts/run_all_rule_guards.sh
```

## 当前验收结论

2026-04-24 主干收束复核中，`scripts/run_all_rule_guards.sh` 已通过，Rule AT 在 manifest 中保持绿灯。
