# SPARKLE Aurora Roadmap v2.2 Final Lock

状态：恢复型索引文档。原始同名文件未在当前 Git 可达历史中找到；本文件根据当前主干中已保留的愿景锚定清单、Stage handoff、治理规则和 gate 证据恢复最终锁定入口。

## 1. Source Of Truth

v2.2 final lock 的权威证据分散在以下当前可打开文件中：

- `docs/product/SPARKLE_VISION_ANCHOR_LIST_2026-04-19.md`
- `docs/product/SPARKLE_AURORA_STAGE22_HANDOFF_2026-04-21.md`
- `docs/product/SPARKLE_AURORA_STAGE23_HANDOFF_2026-04-21.md`
- `docs/product/SPARKLE_AURORA_STAGE24_HANDOFF_2026-04-21.md`
- `docs/product/SPARKLE_AURORA_STAGE25_HANDOFF_2026-04-21.md`
- `docs/product/SPARKLE_AURORA_STAGE26_HANDOFF_2026-04-21.md`
- `docs/product/SPARKLE_AURORA_STAGE27_HANDOFF_2026-04-21.md`
- `docs/product/SPARKLE_AURORA_STAGE28_HANDOFF_2026-04-21.md`
- `docs/product/SPARKLE_AURORA_STAGE29_HANDOFF_2026-04-21.md`
- `docs/product/SPARKLE_AURORA_STAGE29_5_HANDOFF_2026-04-21.md`
- `docs/product/SPARKLE_AURORA_STAGE30_HANDOFF_2026-04-22.md`
- `docs/product/SPARKLE_AURORA_PHASE_I_EXIT_GATE_2026-04-22.md`

## 2. Locked Stage Scope

| Stage | Theme | Current Evidence |
| --- | --- | --- |
| 22 | Prompt / context visibility and loop closure | Stage22 handoff + `scripts/stage22/gate_final.sh` |
| 23 | Bayesian wire-on | Stage23 handoff + `scripts/stage23/gate_final.sh` |
| 24 | Accountability policy compiler | Stage24 handoff + `scripts/stage24/gate_final.sh` |
| 25 | Reflection wire-on | Stage25 handoff + `scripts/stage25/gate_final.sh` |
| 26 | Scene consolidation | Stage26 handoff + `scripts/stage26/gate_final.sh` |
| 27 | Foresight / PersDyn / JITAI | Stage27 handoff + `scripts/stage27/gate_final.sh` |
| 28 | Traits weak prior layer | Stage28 handoff + Stage28 guards in rule manifest |
| 29 | SRL three-phase extension | Stage29 handoff + `scripts/stage29/gate_final.sh` |
| 29.5 | SRL / metacognition bridge stabilization | Stage29.5 handoff |
| 30 | Metacognition extension | Stage30 handoff + `scripts/stage30/gate_final.sh` |
| 31 | Idiographic Lite | Vision anchor and Phase I exit evidence |
| 32 | Track B CL SQAM closeout | Rule AR SQAM suite in `scripts/run_all_rule_guards.sh` |

## 3. Governance Rules

The v2.2 chain is guarded by:

- Rule AH: source-state dimension registry.
- Rule AI: policy compiler purity.
- Rule AJ: route history and reflection user isolation.
- Rule AK: scene algorithm constraints.
- Rule AL: foresight isolation and SDT language.
- Rule AM: traits confidence cap and diagnostic-label ban.
- Rule AN: SRL orchestrator isolation.
- Rule AR: SQAM governance.

## 4. Current Verification Snapshot

2026-04-24 主干收束复核中，以下与 v2.2 直接相关的 gate 已复跑通过：

- `scripts/stage22/gate_final.sh`
- `scripts/stage23/gate_final.sh`
- `scripts/stage24/gate_final.sh`
- `scripts/stage25/gate_final.sh`
- `scripts/stage26/gate_final.sh`
- `scripts/stage27/gate_final.sh`
- `scripts/stage29/gate_final.sh`
- `scripts/run_all_rule_guards.sh`

## 5. Final Lock Statement

v2.2 的工程主体已在当前主干中实现并可验证。本文档恢复的是原清单中的 final-lock 入口；具体实现与验收事实以各 Stage handoff、guard manifest、Phase I Exit Gate 和 2026-04-24 主干复核报告为准。
