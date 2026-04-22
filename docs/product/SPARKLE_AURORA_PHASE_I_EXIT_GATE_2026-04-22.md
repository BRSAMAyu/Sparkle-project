# SPARKLE AURORA Phase I Exit Gate

架构师:请做最终签字验收。
- SGW dogfood: CONDITIONAL
- Kill Switch 三态化完成率: 12/12
- Phase I Exit Gate 建议: patch

日期: 2026-04-22  
阶段: Phase I Exit Gate  
签字状态: 待架构师填写

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
| Rule AS | 闭合 | 已在先前阶段入 manifest |
| Rule AT | 闭合 | 已在 Stage 34 / 36 落地 |
| Rule AU | 闭合 | 黑洞率基线 `0.000%` |
| Rule AV | 闭合 | `scripts/check_rule_av_kill_switch_mode_enum.py` + `scripts/check_core_phase_header.py` 已入 manifest |
| Rule BD | 条件闭合 | `scripts/check_sgw_readiness.py` 允许 `CONDITIONAL`，等待 SGW CLI / 环境差异由架构师裁决 |
| Rule manifest 总量 | 闭合 | 当前 manifest 共 `53` 条，满足 `24+` 目标，且已补 23 个 leaf guards + AV + BD |

## 关键硬指标

| 指标 | 结果 | 说明 |
| --- | --- | --- |
| Mobile 黑洞率 | `0.000%` | 继承 Stage 35 验证 |
| Kill Switch 三态完成率 | `12/12` | 核心 12 个 kill switch 完成；Stage 33-35 / 40 作为扩展收口 |
| Core/Phase 热文件覆盖率 | `100%` | top-50 hot files，阈值要求 `>= 40%` |
| SGW dogfood | `CONDITIONAL` | Phase A `failed_assertion`（`aiohttp` 缺失，0 个有效 run，0 个 iterations）；Phase B/C 被 CLI 缺口阻塞 |

## Memory Write 决策记录

当前结论: `不切 live，保持非 live`

理由:

1. 当前仓库快照未发现 `stage39_memory_write_readiness_report.md`。
2. `docs/audit/deep_audit_2026-04-22_0130_memory_service.md` 仍记录 `SPARKLE_MEMORY_INFERRED_WRITE_ENABLED=False` 与读路径字段丢失这两个 P0。
3. Stage 40 调度要求“按 Stage 39 报告自决”；在显式 readiness 报告缺失的前提下，保守保持非 live 更符合 Rule Y。

## 签字位

- 架构师签字:
- SGW dogfood 最终结论:
- Phase I Exit Gate 最终建议:
- 是否允许进入 Phase II:
