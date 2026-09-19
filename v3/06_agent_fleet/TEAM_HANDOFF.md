# 组员协作交接单（2026-09-19 晚）

> Fleet 已转入「高杠杆专攻」模式：Leader 舰队（并发 4）只做最深壁垒/跨模块/高难度卡。
> 以下工作**难度适中、边界清晰、验收标准明确**，适合组员认领。认领前请读 `AGENTS.md`（尤其磁盘与工作区纪律、并发验收第 6 条）与 `v3/06_agent_fleet/DYNAMIC_ISSUES.md`（台账全文）。

## 协作规则（必读）

1. **工作树隔离**：在自己的 fork/worktree 里做，PR 指向 main；不要直接 push main。
2. **避让区**：Leader 舰队正在改的区域见下表「在途避让」，认领前核对最新 main。
3. **验收证据**：每个修复交付 = 改动 + 测试（红绿）+ live 只读复算（涉及 DB 语义时）+ REPORT.md；不接受「看起来对了」。
4. **dev DB 只读**：`sparkle_db`（docker）对所有人只读 SELECT；写测试用 sqlite/mock。
5. 跑后端测试：`cd backend && SECRET_KEY=test /opt/homebrew/bin/python3.11 -m pytest <定向文件>`（不要全量跑，有已知预存失败，见 FIX-19）。

## 可认领清单（按价值排序）

| 项 | 台账/出处 | 内容与验收 | 难度 |
|---|---|---|---|
| **V3-FIX-21 kill-switch 劫持** | DYNAMIC_ISSUES.md | `resolve_settings_mode` 被默认 True 的 `SPARKLE_AGGREGATOR_ENABLED` 劫持：显式 "off" 被静默回 "live"；连带 FIX-09 的 governance_off 码不可达。修：legacy bool 默认 False 或显式优先级裁决 + 测试钉住（显式 off 必须 off） | 低-中（一个配置裁决+测试） |
| **V3-FIX-22 测试隔离 bug** | DYNAMIC_ISSUES.md | `test_stage38_d3_persistence` 覆写 `sys.modules["app.gen"]` 不恢复，同进程砸后续 collection。修：fixture 加 restore | 低 |
| **V3-FIX-03 mock 统计污染** | DYNAMIC_ISSUES.md | core/statistics 三仓库 fetchFromApi 纯 mock 且落 Isar 标记已同步。修：接真实 API 或删除；先补红测（B-02 验收时红测丢失） | 中 |
| **V3-FIX-05 shop 空入口** | DYNAMIC_ISSUES.md | /shop 注册+唯一入口暴露空目录。修：移除入口（mobile 侧） | 低 |
| **V3-FIX-06 aurora lane 登记** | DYNAMIC_ISSUES.md | correction_feedback 写未登记 lane。需产品裁决二选一：登记 lane 或迁移写入点 | 低-中（先问产品） |
| **V3-FIX-14 遥测 waiver 收编** | DYNAMIC_ISSUES.md | 17 个 per-user 第二跳读方入 waiver 登记册 + 防抖原子化 | 中 |
| **V3-FIX-15 M-02 gate 打磨** | DYNAMIC_ISSUES.md | 否定守卫绕过/工作日锚点/稳定性词表/评测集 | 中 |
| **B-04 视觉基线**（HEAVY） | v3/07_tasks/cards/B-04.md | 9 surfaces×三端截图+manifest+视觉问题 ledger；**B-03 journey harness 已在 main**（scripts/devtools/journey_harness/），复用它；HEAVY 纪律见 AGENTS.md 内存节 | 中（体力活，纪律要求高） |
| **X-01 F5 矛盾集双副本对账** | X-02 R2 回执 F4 | X-01 docstring/X-02 模块/测试三处硬编码副本合一（X-02 为真源 import） | 低-中 |
| **E-05 live 窗口补验** | DYNAMIC_ISSUES.md FIX-16 | live 隔离测试+rebuild --execute 全量+N1 事务顺序（与 Leader 约静默窗口） | 中 |
| 预存测试失败残项 | FIX-19 交付后看其 REPORT | FIX-19 修完后剩余的环境性 skip 显式化 | 低 |

## 在途避让（Leader 舰队占用，认领前核对）

- `backend/app/aurora/` + `orchestration/` 决策面 —— A-01（Aurora 契约）
- `backend/app/services/` memory 检索/个性化面 —— M-05（自检）
- `backend/app/core/llm_router.py`、`services/llm*` —— E-02（能力路由，验收中）
- `backend/tests/` aggregator/com011/c03 家族 —— FIX-19（测试修复，收尾中）

## 已完成不可重做（今日已合入，供参考勿重复）

四大契约（C-01/M-01/D-01/X-01）+ 记忆流（M-01/02/03/04/07）+ C-02/C-03 + X-02 + D-02 + E-05 + B-02/03/05/06 + FIX-01/02/04/07/08/09/11/13/18。25 卡 DONE，41+ commit。词表冻结状态：event_registry 35 名 @26cf482d。
