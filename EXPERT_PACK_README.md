# Sparkle V3 专家分析资料包（2026-09-28）

**唯一入口文档**：`v3/V3-COMPLETE-STATUS-FOR-V4.md`（v0.8，文首有终门结果与版本线；§0.5 名词表建议先读）

## 包内结构

| 路径 | 内容 |
|---|---|
| `v3/V3-COMPLETE-STATUS-FOR-V4.md` | **主文档**：V3 真实意图/14 线深挖/107 卡全景（104/107）/FIX 台账/度量快照/V4 设计建议输入 |
| `v3/V3_DEFINITION_OF_DONE.md` | DoD V3-0..V3-10 逐 gate 验收标准（V3-0 含 B-01Δ 42→43 决议注） |
| `v3/07_tasks/tasks.json` | 107 卡规格权威（状态+验收字段） |
| `v3/06_agent_fleet/DYNAMIC_ISSUES.md` | FIX 台账 377 行（P0/P1 全清；状态格行首枚举口径机器可复算） |
| `v3/.sparkle_v3_fleet_state.json` | 舰队执行日志 notes 流（#1-#313 轮记） |
| `v3/08_operations/` | HUMAN_INBOX（H-001~009 真机/人工面）/OPS_SURFACE（O-06 运维面） |
| `v3-output/` | 全部工作产物：14 线深挖详章（WT769~WT779-DOC-*）、三源核验（WT759-RECON）、E-08 终判（WT798/801/803）、J-02 全量证据（WT792/802）、门后手册（WT788-POSTGATE）、B-01 权威矩阵、各审查 receipt、度量实测（WT780-METRICS）、408 张证据截图与原始数据 |

## 关键事实速览（详见主文档）

- day7 终门 PASS（2026-09-28 08:19，JOURNEY 七日 7/7）
- CI 四绿两红全归因（23/25/27/29 绿；mypy 922→55；基线 77 对齐）
- 台账 P0/P1 全清零、deep-strict 零红（机器可审计）
- 最重 V4 负面输入：Q-04 uplift 0.0pp + A-08 no_memory 双指标反超（两个独立 eval 同向：记忆/个性化面净贡献未证明为正）
