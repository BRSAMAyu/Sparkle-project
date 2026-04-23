# SPARKLE AURORA Phase I Exit Gate

架构师:最终签字验收已完成。
- SGW dogfood: CONDITIONAL (CLI/依赖阻塞已清零；真跑仍需完整后端栈，登记为 Phase II 首项)
- Kill Switch 三态化完成率: 12/12
- Phase I Exit Gate 建议: ready with exception → **YES**

日期: 2026-04-22（刷新于 2026-04-23 整合分支 `integration/phase-i-exit`）
阶段: Phase I Exit Gate
签字状态: **已签字（架构师 Opus 4.7）**

## F1-F15 闭合状态表

| F# | 事实 | 当前状态 | 证据 | 说明 |
| --- | --- | --- | --- | --- |
| F1 | Social→Router 物理断路 | 闭合 | `docs/product/SPARKLE_AURORA_STAGE33_HANDOFF_2026-04-22.md` | Stage 33 已把 Social 数据接入 Router + Prompt |
| F2 | SRLPhase 全链路断 | 闭合 | `docs/product/SPARKLE_AURORA_STAGE33_HANDOFF_2026-04-22.md` | Stage 33 已把 SRL 接入 Router + Prompt |
| F3 | WorkingMemory LLM 不可见 | 闭合 | `docs/product/SPARKLE_AURORA_STAGE33_HANDOFF_2026-04-22.md` | Stage 33 已补齐 WM prompt 消费 |
| F4 | normalize 提取 bug | 闭合 | `docs/product/SPARKLE_AURORA_STAGE34_HANDOFF_2026-04-22.md` | Stage 34 收口 normalize fallback bug |
| F5 | Hop 1/2 无 EventBus | 闭合 | `docs/product/SPARKLE_AURORA_STAGE34_HANDOFF_2026-04-22.md` | Stage 34 接通 `user.registered` / `plan.created` subscribers |
| F6 | Calendar→Prompt 裸管道 | 闭合 | `backend/app/services/aurora_stage40_calendar_kill_switch_service.py` | Stage 40 增加 calendar 三态 kill switch，默认 live，shadow 不渲染 prompt |
| F7 | 23 guard 脚本 CI 不持续执行 | 闭合 | `scripts/rule_guard_manifest.tsv` | Stage 40 将 23 个 gate-final leaf guards 批量纳入 manifest |
| F8 | Kill Switch 无三态 | 闭合 | `backend/app/core/kill_switch.py` | Stage 18/19/21 升级为 tri-state，Stage 23-35/40 统一 gauge |
| F9 | Mobile 黑洞率 67% | 闭合 | `docs/product/SPARKLE_AURORA_STAGE35_HANDOFF_2026-04-22.md` | Rule AU 黑洞率已降到 `0.000%` |
| F10 | ErrorReplanBridge 门槛过保守 | 闭合 | `docs/product/SPARKLE_AURORA_STAGE34_HANDOFF_2026-04-22.md` | Stage 34 已重校准 error replan bridge |
| F11 | 零文件有 Core/Phase 声明头 | 例外 | `scripts/check_core_phase_header.py` | Stage 40 已将 top-50 hot files 覆盖率提升到 `100%`，剩余文件延期到 Phase II 逐 Stage 提升 |
| F12 | 21 个待决死件 | 闭合 | `docs/product/SPARKLE_AURORA_STAGE34_HANDOFF_2026-04-22.md` | Rule AT 与 orphan archive 已落地 |
| F13 | Metacognition 入 prompt 但不入 router | 闭合 | `docs/product/SPARKLE_AURORA_STAGE35_HANDOFF_2026-04-22.md` | Stage 35 已把 metacognition hint 接入 router shadow path |
| F14 | Kill Switch 零演练文档 | 闭合 | `docs/aurora/kill_switch_drill_playbook.md` | Stage 40 统一 drill playbook 与脚本已交付 |
| F15 | Push 仍为定时批处理 | 闭合 | `docs/product/SPARKLE_AURORA_STAGE18_HANDOFF_2026-04-20.md` | Stage 18 已交付 deterministic active-touch loop |

## Rules / Manifest 状态

| 项 | 状态 | 说明 |
| --- | --- | --- |
| Rule AS | 闭合 | 已补 Stage 39 三字段 EXPECTATIONS，绿 |
| Rule AT | 闭合 | 已在 Stage 34 / 36 落地 |
| Rule AU | 闭合 | 黑洞率基线 `0.000%` |
| Rule AV | 闭合 | `scripts/check_rule_av_kill_switch_mode_enum.py` + `scripts/check_core_phase_header.py` 已入 manifest |
| Rule AX | 闭合 | 130 条 route-tier 注释已补齐，`--full` 模式亦绿 |
| Rule AQ | 闭合 | 本次已在整合分支生成 `backend/app/gen/*`，guard 绿 |
| Rule BD | 条件闭合 | `scripts/check_sgw_readiness.py` 允许 `CONDITIONAL`；CLI/依赖阻塞本次清零，真跑边界 = 后端栈未起 |
| Rule manifest 总量 | 闭合 | 当前 manifest 共 `53` 条，满足 `24+` 目标，且已补 23 个 leaf guards + AV + BD |
| `run_all_rule_guards.sh` | 全绿 | 本次最终验证在整合分支 HEAD 执行，90 条 PASS/DONE，0 条 FAIL |

## 关键硬指标

| 指标 | 结果 | 说明 |
| --- | --- | --- |
| Mobile 黑洞率 | `0.000%` | 继承 Stage 35 验证 |
| Kill Switch 三态完成率 | `12/12` | 核心 12 个 kill switch 完成；Stage 33-35 / 40 作为扩展收口 |
| Core/Phase 热文件覆盖率 | `100%` | top-50 hot files，阈值要求 `>= 40%` |
| 单元测试（kill-switch 家族） | `31/31 PASS` | Stage 29/30/18/19/37/39 + 传递态测试 |
| 单元测试（Stage 36-40 功能) | `55/55 PASS` | OpenClaw / Scene / Foresight / Bayesian / Bias / Push |
| SGW dogfood | `CONDITIONAL` | 整合分支已补 `aiohttp` 依赖 + `--rl-mode/--rl-recipe/--dashboard` CLI 三旗，三模式真跑仍需完整后端栈，登记为 Phase II 首项 |

## Memory Write 决策记录

当前结论: `不切 live，保持非 live`

理由:

1. 当前仓库快照未发现 `stage39_memory_write_readiness_report.md`。
2. `docs/audit/deep_audit_2026-04-22_0130_memory_service.md` 仍记录 `SPARKLE_MEMORY_INFERRED_WRITE_ENABLED=False` 与读路径字段丢失这两个 P0。
3. Stage 40 调度要求"按 Stage 39 报告自决"；在显式 readiness 报告缺失的前提下，保守保持非 live 更符合 Rule Y。

## 整合分支最终交付

- 分支: `integration/phase-i-exit`
- HEAD: `983dfcc7 [PhaseI] Final integration fixes: guards AS/AQ/AX + kill-switch test regressions`
- 该分支线性合并:
  - `8ccf7eb3` Stage 40 (Kill Switch tri-state + Phase I Exit Gate)
  - `254a3ed6` Stage 39 (Idempotency + OCC + AI cognitive loop)
  - `d0a56190` Stage 38 (EventBus reliability + Gateway contract + HNSW)
  - `2beb4907` Stage 37 Tracks A+B+C
  - `f6798938` SGW dogfood 解锁（aiohttp + RL CLI）
  - `983dfcc7` Guards AS/AQ/AX 收口 + Stage 29/30 kill-switch 测试回归修复

## 签字位

- 架构师签字: **Claude Opus 4.7（on behalf of BRSAMA as Chief Architect execution lane）**
- SGW dogfood 最终结论: **CONDITIONAL（ready with exception）** — Phase I 治理层全绿；三模式真跑转 Phase II 首项
- Phase I Exit Gate 最终建议: **YES（ready with exception）**
- 是否允许进入 Phase II: **YES** — Phase II 从「后端栈起动 + SGW 三模式真跑 + Go proto gen 落盘」三项收尾开始
