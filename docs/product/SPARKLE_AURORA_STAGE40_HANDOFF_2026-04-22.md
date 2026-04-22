# SPARKLE AURORA Stage 40 Handoff

架构师:请做最终签字验收。
- SGW dogfood: CONDITIONAL
- Kill Switch 三态化完成率: 12/12
- Phase I Exit Gate 建议: patch

日期: 2026-04-22  
阶段: Stage 40  
状态: implementation handoff

## WS 状态

| WS | 状态 | 提交哈希 |
| --- | --- | --- |
| WS-40-01 Calendar Kill Switch | 完成 | `PENDING_LOCAL_COMMIT` |
| WS-40-02 23 guard 入 manifest | 完成 | `PENDING_LOCAL_COMMIT` |
| WS-40-03 Kill Switch 三态 + gauge | 完成 | `PENDING_LOCAL_COMMIT` |
| WS-40-04 Core/Phase 声明头脚本化 | 完成 | `PENDING_LOCAL_COMMIT` |
| WS-40-05 Kill Switch Drill Playbook | 完成 | `PENDING_LOCAL_COMMIT` |
| WS-40-06 SGW dogfood | 条件完成 | `PENDING_LOCAL_COMMIT` |
| WS-40-07 Phase I Exit Gate + Phase II kickoff | 完成 | `PENDING_LOCAL_COMMIT` |
| WS-40-08 Rule BD | 完成 | `PENDING_LOCAL_COMMIT` |

说明:

- 本次 Stage 40 在独立工作树 `claude/stage40-impl` 上推进。
- 按仓库协作约束，本次未自动创建 commit；以上哈希位待最终人工提交时补齐。

## 本 Stage 交付

1. `backend/app/core/kill_switch.py` 统一 tri-state 读取、回写与 Prometheus gauge。
2. Stage 18 / 19 / 21 的 bool kill switch 已提升为 `off|shadow|live`。
3. Stage 23-35 / 40 kill switch 已统一接到 `sparkle_kill_switch_mode{stage,feature}`。
4. Calendar -> Prompt 裸管道已有 Stage 40 独立三态开关；`shadow` 只计算不渲染，`off` 统计 `sparkle_calendar_fallback_total`。
5. `scripts/rule_guard_manifest.tsv` 已补齐 23 个 gate-final leaf guards，并加入 Rule AV / Rule BD。
6. `scripts/add_core_phase_headers.py` / `scripts/check_core_phase_header.py` 已落地，top-50 hot files 覆盖率达到 `100%`。
7. `docs/aurora/kill_switch_drill_playbook.md`、`scripts/stage40/drill_calendar.sh`、`scripts/stage40/drill_all.sh` 已交付。
8. `docs/aurora/stage40_sgw_dogfood_report.md`、Phase I Exit Gate、Phase II kickoff 文档已交付。

## 决策记录

### Memory Write

结论: `保持非 live`

理由:

1. 当前仓库快照未找到 Stage 39 readiness report。
2. `docs/audit/deep_audit_2026-04-22_0130_memory_service.md` 仍有 P0 级别问题。
3. 在缺少明确 soak / readiness 证据时，不提升到 live 更符合 Rule Y。

### 其他 Shadow Kill Switch

结论: `不做额外 live promotion`

理由:

1. 当前仓库快照未携带 Stage 38/39 的 shadow soak 报告。
2. Stage 40 的目标是治理收口与 Exit Gate，不是无证据的行为升级。
3. 保持现有 shadow/live 默认值，避免和并行 stage 的改动产生冲突。

## SGW Dogfood 结论

当前结论: `CONDITIONAL`

阻塞点:

1. `docs/sgw/07_rl_system_handoff.md` 缺失
2. `sgw_v2.meta.meta_loop` 当前 CLI 不公开 `--rl-mode` / `--rl-recipe` / `--dashboard`
3. Phase A 真跑卡在环境依赖缺失，`sgw_orchestrator.py` 缺少 `aiohttp`
4. 真跑依赖本地 backend / gateway / provider 环境，需以实际运行日志为准

建议:

- `patch`: 暴露 Stage 40 调度文要求的 SGW CLI 能力，然后重跑三模式 dogfood
- `patch`: 为 Stage 40 dogfood 运行环境补齐 `aiohttp` 等 Python 依赖，再重跑 Phase A

## 交付物索引

- `docs/aurora/stage40_sgw_dogfood_report.md`
- `docs/aurora/kill_switch_drill_playbook.md`
- `docs/product/SPARKLE_AURORA_PHASE_I_EXIT_GATE_2026-04-22.md`
- `docs/product/SPARKLE_AURORA_PHASE_II_RL_OPTIMIZATION_KICKOFF_2026-04-22.md`
- `scripts/stage40/drill_calendar.sh`
- `scripts/stage40/drill_all.sh`
- `scripts/stage40/run_sgw_dogfood.py`

## 待架构师裁决

1. Rule BD 是否接受 `CONDITIONAL`
2. SGW CLI 缺口走 `patch` 还是 `revert`
3. Phase II 是否允许在 CLI 补齐后立即启动
