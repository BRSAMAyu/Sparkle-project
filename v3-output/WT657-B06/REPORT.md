# WT657 · B-06 V3 核心实体映射与重复真源审计（round-1 增量）

- **Agent**: wt657 ｜ **工作树**: `Sparkle-sysrev/wt657-b06`（分支 `agent/node-b/wt657/b06`）｜ **base SHA**: `8a0a868f`（main HEAD，创建 worktree 时亲证）
- **日期**: 2026-09-25 ｜ **方法**: 只读静态审计（grep + 逐文件对照，file:line 亲证），零产品码改动、零 push
- **卡面**: `v3/07_tasks/cards/B-06.md`（Stream BASELINE / Gate V3-0 / high / LIGHT / Reviewers 2 / locks architecture-map）
- **前置基线**: wt534 `v3/06_agent_fleet/B06_ENTITY_TRUTH_BASELINE.md`（main 提交 `f46b60d7`，git log 双证）。**增量原则**：基线已覆盖的（9 实体枚举/状态机四面、身份链、v1/v2 遗留双源）不重做；本卡验收 1/3 未完成项（四分法映射、ENTITY_MAP 产物）与验收 2 的 Aurora/Runtime/Action owner 实证为本轮交付。

---

## 0. 一句话总评

**四分法可完整映射到现有实体且无需新建任何存储**：State/Memory/Knowledge/Events 各有单一权威（M-01 记忆契约、D-01 事件词表、A-01/X-02/X-03/X-05 契约族把 Aurora/Runtime/Action 的 owner 边界显式钉死，无双权威）；本轮唯一达到登记门槛的新发现是 **gateway 任务 CQRS 投影族零读面双投影器（V3-FIX-355）**——任务真源的写侧复制体，无人消费、双实现、无漂移检测面。

## 1. 卡面验收对照

| 验收项 | 判定 | 证据 |
|---|---|---|
| 四分法 State/Memory/Knowledge/Events 可映射到当前实体 | ✅ 完成 | `ENTITY_MAP.md` §1 + `ENTITY_MAP.json` quad_split：每象限实体/写入方/唯一权威契约 file:line 齐备 |
| Aurora/Agent Runtime/Action 不出现两个权威 owner | ✅ 通过（实证） | A-01 契约四边界声明（`core/aurora_decision.py:15-30`）；X-05 run 状态机唯一写入权威（`services/agent_run_service.py:1-33`，RunLedgerStore 观测定位显式）；X-03 action_command_service 单一 command path 自述（:1-30 文件头）；runtime_v1 L2 经契约桥接（`l2_intervention.py:19-39`）+ spine 真通道已接（`spine_orchestrator.py:2699`）；网关/移动端零状态机复制（wt534 已证，本轮复核未变） |
| 生成 ENTITY_MAP.md/json；后续任务必须引用 | ✅ 完成 | `v3-output/WT657-B06/ENTITY_MAP.md` + `ENTITY_MAP.json`（含十二概念 + NORTH_STAR 八机器 reuse/extend/retire/no-authority 判定与 permission/Milestone/Citation 三个 no-authority 显式标注） |

Required evidence：base/final SHA 见 §5；targeted tests——纯文档审计卡，验证面为 ENUM-PARITY 守卫在册性（manifest:90）与台账 `--verify` 零 FAIL（§4）；integration/simulator——不适用（未触碰运行面）；review receipt——按验收模型由独立会话补。

## 2. 相对 wt534 基线的进度判定（git log 双证）

- 基线提交：`git log main --oneline -- v3/06_agent_fleet/B06_ENTITY_TRUTH_BASELINE.md` → 仅 `f46b60d7`（wt534），此后无增量提交 → 卡面验收 1/3 在基线中**未完成**，本轮为真增量。
- 基线建议 1（mobile 枚举守卫）**已被后续波次落地**：`scripts/guards/check_enum_value_set_parity.py` 文件头自述即援引 B06 审计与 V3-FIX-259/260（基线 256/257 的集成重编号），现登记于 `scripts/rule_guard_manifest.tsv:90`（ENUM-PARITY，dual 55+passthrough 21=76 族，经 V3-FIX-289/291 扩表）→ 该结构性空档已闭合，基线遗留项不再开放。
- 基线登记 256/257 的修复归属 wt539（守卫头注），本轮不触碰。

## 3. 本轮新发现（达到登记门槛 1 项）

### V3-FIX-355 · gateway 任务 CQRS 投影族零读面双投影器（P3，OPEN）

**现象**：任务事件被两套独立投影器写入同一批 Redis 键，且全仓无任何读消费者。

- 写方 A（live）：`gateway/internal/worker/task_sync.go:189-348` 消费 `cqrs:stream:task`（:33-37），写 `task:view:*`/`user:tasks:pending|in_progress|completed:*`；`cmd/server/setup.go:396` 创建、`:462` 随 CQRS runner 运行。
- 写方 B（重放）：`gateway/internal/cqrs/projection/handlers.go:287-560` `TaskProjectionHandler` 从 event_store 重放，写同一批键 + `user:task:stats:*` HIncrBy（:417-514）；`setup.go:386-387` 注册。
- 零读面：`grep -rn 'task:view\|user:tasks\|user:task:stats' gateway/internal/{handler,service,agent}` 零命中；唯一 `Get("task:view:...")` 在 `task_sync.go:403`，是投影器读回自身写入做状态补丁（自维护，非消费）；引擎/mobile/scripts 零命中（`scripts/devtools/audit_community_readmodel.py:272` 仅 SCAN 计数键量）。
- 真实任务读面：mobile 走引擎 REST；gateway `internal/service/user_context.go` 直读 PG（wt534 基线 §1 task 行亲证，未变）。

**危害**：写侧成本与 Redis 内存持续发生；投影族陈旧/漂移无任何检测面（无读者=无对账）；后续任务若把它当读模型接线，即引入任务第二真源——恰是 B-06 卡面要防的事故形态。

**裁决建议（T-待裁决）**：删任务投影族（TaskSyncWorker 任务段 + TaskProjectionHandler 任务段 + 相关键），或先指定真实消费面再收敛为单投影器。community/galaxy 投影是否同病**不在本项范围**（独立面，建议随社区/星图域卡核查）。

**登记**：台账 `v3/06_agent_fleet/DYNAMIC_ISSUES.md`（V3-FIX-355，登记时 grep 验证 355 未占用；与 wt656 并行撞号由集成侧重编号）。

## 4. 观测项（未达登记门槛，ENTITY_MAP §5 全列）

1. `AuroraDecision` 同名双类（会话动作面 vs A-01 契约面）——同名异面导航隐患，桥接已声明。
2. user_state 五 plane（快照/活装配/路由信念/在场态/人格动力学）边界靠声明与 waiver 注释，无跨面一致性测试。
3. `decision_records` 通用留痕与 A-01 契约记录并存，用途不同。
4. Milestone / Citation 无独立实体——后续需要时按 extend 走新契约。
5. event_store 无 Python ORM 面——gateway 专用持久日志，D-01 词表权威仍在 backend，单向流健康。

## 5. 交付与验证

- **交付**：`v3-output/WT657-B06/REPORT.md`（本文件）、`ENTITY_MAP.md`、`ENTITY_MAP.json`；台账行 V3-FIX-355。final SHA = 本 worktree 提交 SHA（见提交说明）。
- **台账验证**：`scripts/devtools/ledger_union_merge.py --verify v3/06_agent_fleet/DYNAMIC_ISSUES.md` → 零 FAIL（登记后实跑，输出见提交前最后一次运行）。
- **守卫在册性**：ENUM-PARITY 于 `scripts/rule_guard_manifest.tsv:90` 在册（本轮未改动守卫，仅引用其闭合结论）。
- **Forbidden 自查**：未重建任何既有真源；无 mock/seed 冒充；未宣称任何用户体验通过；未弱化安全/幂等/隔离/审计守卫；未触碰 gen/、.env、运行态；未 push。

## 6. Top 3 风险（移交集成侧/后续卡）

1. **V3-FIX-355 投影族被误接线**：在修复裁决前，任何「任务读性能优化」类任务最容易把它当现成读模型消费——届时陈旧复制真源即刻生效。建议裁决优先级提前。
2. **user_state 五 plane 的隐性融合**：各 plane 单独有界，但无跨面一致性测试；未来任何「统一用户状态」任务若不引用 ENTITY_MAP 先做映射，极易把路由信念（7d TTL、可丢）当业务真值。
3. **AuroraDecision 同名双类**：V3 后续卡在「Aurora 决策」语境下 import 错面的概率随卡数增长（runtime_v1 的 `AuroraDecision` 与 A-01 `AuroraDecisionContract` 语义完全不同）；建议其中之一更名（属 extend，需随桥接点测试）。

---

*wt657 · B-06 round-1 审计轴 · locks=architecture-map · 基线 8a0a868f · 零产品码改动*
