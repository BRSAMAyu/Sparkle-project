# Rule AV - Engineering Hardening Governance

状态：路径兼容入口，当前权威实现由 Rule AV guard 与 Phase I Exit Gate 共同承载。

## 背景

`SPARKLE_VISION_ANCHOR_LIST_2026-04-19.md` 中登记过旧路径：

- `docs/aurora/rule_av_engineering_hardening.md`

Stage 36-40 收束后，Rule AV 没有保留独立同名正文，而是落到了可执行 guard 与 exit gate 中：

- `scripts/check_rule_av_kill_switch_mode_enum.py`
- `scripts/check_core_phase_header.py`
- `scripts/rule_guard_manifest.tsv`
- `docs/product/SPARKLE_AURORA_PHASE_I_EXIT_GATE_2026-04-22.md`
- `docs/product/SPARKLE_AURORA_STAGE40_HANDOFF_2026-04-22.md`

本文件用于保留愿景清单中的历史路径，避免路线文档断链。

## 当前规则语义

Rule AV 当前约束两个工程硬化面：

- Kill switch 必须统一使用三态 `off|shadow|live`，并覆盖已登记的 Stage 服务。
- Core/Phase 热点文件必须具备声明头覆盖，防止关键工程边界在后续阶段继续漂移。

## 验证入口

```bash
python scripts/check_rule_av_kill_switch_mode_enum.py
python scripts/check_core_phase_header.py
scripts/run_all_rule_guards.sh
scripts/stage40/drill_all.sh
```

## 当前验收结论

2026-04-24 主干收束复核中：

- Rule AV guard 已通过。
- Core/Phase Header guard 已通过。
- Stage40 kill-switch drill 已通过。
