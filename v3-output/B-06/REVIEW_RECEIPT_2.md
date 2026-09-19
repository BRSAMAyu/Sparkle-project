# B-06 · REVIEW_RECEIPT_2（第二路独立 Reviewer · 对抗/结构性路线）

- Reviewer: #2（B-06 high risk 需 2 Reviewer；本卡为补验）
- 被审对象：主仓 `v3-output/B-06/`（ENTITY_MAP.md、entity_map.csv、COMPLETION_RECEIPT.md），commit `faaae378` 引入、`51f5acd7` 后状态
- 评审基线：主仓 `main @ 566517a2`（只读）；产出写本 worktree
- 方法：与第一路逐项实证互补，本路专攻**结构性问题**——概念清单盲点、收敛建议与冻结决策/债务账本冲突、no-authority 判定反证、MD↔CSV 残留不一致、后续任务可引用性。全部发现均经代码 grep + live DB 只读 SELECT（`docker exec sparkle_db psql`）复核
- 复核时间：2026-09-19（与 B-06 实测同日，行数漂移见 C4）

---

## 0. 总 verdict

**CHANGES**。

骨架判定成立：24 概念落点基本正确、八组 D-* 权威真源指定与 DECISIONS_V3 冻结决策**无方向冲突**、两个关键 0 行证据（cards/task_occurrences、execution_intents）复核为真。但作为 V3-0 锁定的「后续任务必须引用」真源，存在 4 处会实际误导后续 Agent 的结构性缺陷（C1–C4），须修订后才可锁定。

---

## 1. 逐项对抗检查

### 检查 1｜四分法覆盖完备性 —— 「四分法够用」成立，「24 行已全覆盖」不成立

四分法本身是 D09 冻结决策，B-06 无权也无需重判，其对五层模型「epistemic layer 非第五类」的处理与 USER_WORLD_MODEL §末节一致。✅

但对照 MASTER_DESIGN.md §1 三个 Plane 的组件清单与 `v3/02_core_systems/` 12 份文档逐一点名，发现 **4 个盲点**：

| # | 缺口 | 证据 |
|---|---|---|
| 1a | **Model Router / Cognition Ladder 无映射行**。MASTER_DESIGN Intelligence Plane 列五组件（Context Compiler / Conflict Resolver / Aurora / **Model Router** / RAG-Reranker），B-06 只映射了四个。代码中 `orchestration/dual_core_router.py`、`routing_engine.py`（债账 #5：26 处 legacy 标记）、`routing_parameter_registry.py` 均存在；`AI_ROUTING_LATENCY.md`（L0–L3 阶梯=D15）是 core-system 文档之一却无对应行。**风险**：Aurora 行写「engine.py 路由/降级」，后续 Agent 易误以为 Aurora engine 兼管模型路由——决策路由与模型路由是两个 owner | grep 证实 dual_core_router 存在且消费 BeliefState |
| 1b | **Tool Registry 无映射行**。MASTER_DESIGN Execution Plane 与 AGENT_RUNTIME.md §1（「Agent 只能通过 Tool Registry 读写」）均点名。代码 `backend/app/tools/registry.py` 是显式 back-compat wrapper 委托给 `orchestration/dynamic_tool_registry.py`（单一权威其实已收敛——这本是 map 该记录的「收敛已完成」正面案例）。map 只有「Tool Call / Receipt」账面行，无 Registry 行 | 两文件头注实测 |
| 1c | **cognitive_ownership 全仓 0 命中、map 0 提及**。D13 + HUMAN_AGENT_HYBRID.md §2（8 维分配，Cognitive Ownership 列第 1 维）要求每个 step 标 `execution_mode` **与** `cognitive_ownership`。`backend/app/models/execution_intent.py` 只有 execution_mode/TrustLevel，无 cognitive 字段；backend 与 B-06 产出内 grep 均零命中。这是一个真实的**字段级 no-authority 缺口被漏判**——HUMAN_AGENT_HYBRID 后续任务照 map 行事会以为只差扩展 execution_mode | grep 双零实测 |
| 1d | **Artifact 未显式映射**。USER_WORLD_MODEL Current State 清单含 Artifact，§1.1 无对应行，仅 `planning_artifacts` 在 Plan 行捎带。若 planning_artifacts 即真值应明示归属 | 文档比对 |

结论：四分法结论成立；映射完备性约 90%，缺的恰是「会新建平行系统」风险最高的组件行。

### 检查 2｜「迁移/收敛而非重写」可行性 —— 方向无冲突，D-TASK 治理表述过强

- ✅ D-ENTITLE ↔ D17（flame_level 降展示层、entitlement 独立）一致；D16 ↔「OpenClaw 仅枚举值」一致；D-CTX ↔ 契约版「单一 ContextPack contract」一致；D-CONF ↔ CONFLICT_RESOLVER.md（Resolution Tuple / ask once / 全程留痕）一致，`unresolved_conflicts` 即 ask once 机制的读法正确（0 行复核 ✓）。
- ⚠️ **C2（结构性）：D-TASK「两态并存是受治理的迁移，非腐化」表述过强**。map 引了债账 #4/#6 说明 mid-flight，但**漏引债账 2026-09-18 节两条关键事实**：① CARD-DUAL-WRITE 守卫规则**已停用**；② 其 import 的 `app.services.card_protocol.consistency_validator` **自初始提交就不存在于仓库**。即双写一致性校验这个「治理」本体从未落地。方向上与 #4「先查 shadow 验证状态再行动」不冲突，但「受治理的迁移」+「shadow 验证通过后切流」会给后续 Agent 一种治理已在位的错觉，在 consistency_validator 缺席下切流 = 静默分叉。**修订要求**：D-TASK 迁移路径加前置条件「补齐 consistency_validator 并恢复 CARD-DUAL-WRITE 规则」。
- 小项：D-CONF 建议扩展 Stage20 比较键，但 V3 Resolution Tuple 七元组含 epistemic class / validity(TTL)，而 map 自己承认 epistemic class 未显式标注——存在未回链的字段前置依赖。

### 检查 3｜两个 no-authority 判定 —— 一个确认且更强，一个被实质削弱

**3a. Experience Memory 聚合体 = 判定确认，且证据比 map 更强。**
- `situation_signature` 全仓 0 命中（MEMORY_V3 §5 payload 核心字段不存在）。
- **候选资产在 live DB 全部零行**：`distilled_strategy_cache`=0、`intervention_strategy_outcomes`=0、`behavioral_outcomes`=0、`nightly_reviews`=1。map 只说「有表」未披露零行，后续任务会误以为有存量经验数据可聚合。
- `InterventionStrategyOutcome` 模型有 intervention→outcome→context_snapshot，但无 situation signature / user feedback / repeated evidence count / execution mode；`AuroraExperiencePacket`（experience_packets.py）是 per-turn 瞬时契约非持久存储。map「在此之上聚合，不新造平行学习系统」的方向正确。
- 判定：**no-authority 成立**（缺口甚至大于 map 表述）。

**3b. UserWorldSnapshot = 判定被实质削弱，存在漏判（C1，本次评审最实质发现）。**
- `backend/app/state_aggregator/schema.py:285` 存在 **`UserStateV1`** 聚合 dataclass（`schema_version="user_state.v1.13"`，20 个 `StateFieldEnvelope` 字段），经 gRPC（`user_state_pb2.py`）出线，消费方含 push_policy_compiler / sufficiency_judge_service。
- `StateFieldEnvelope` 自带 `value / computed_at / source_snapshot_ids / freshness_seconds` —— 正是 USER_WORLD_MODEL 对 UserWorldSnapshot 每字段 `source_ref / observed_at / TTL` 要求的**既有机制化实现**。
- **契约版 `v3/00_context/ENTITY_MAP.md` 明文点名 "orchestration/context_builder/UserStateV1" 为 Context 优先查找区**——而 `UserStateV1` 在 ENTITY_MAP.md 与 entity_map.csv 中 **0 次出现**。map 只点名了同文件的 `StateFieldEnvelope`（归属也不准：20 字段属 UserStateV1，信封本身是 4 属性泛型）。
- 公平认定：三处扩展点（context_pack.py / state_aggregator / situation_brief.py）今天确实**互不接线**（context_pack.py 0 处引用 state_aggregator），9 轴快照中 memories candidates / material candidates / recent events / outcome summary / capabilities-permissions 五轴确实无聚合体——所以「完整 no-authority」勉强可辩。但 map 行的写法（「无单一快照聚合体」+ 不提 UserStateV1）**违反 map 自己的铁律**（§5：先证明现有对象不能扩展）——状态轴上恰恰存在一个现成聚合体，且是契约文档指定优先查的对象。后续 Context Compiler 任务照此行事，最可能的结果就是新造平行快照服务，恰是铁律要防的事故。
- **修订要求**：UserWorldSnapshot 行改写为「UserStateV1 为状态轴既有骨架（缺五轴），残余缺口在其上扩展」，并把 D-STATE 行的「StateFieldEnvelope（20 字段）」更正归属。

### 检查 4｜MD↔CSV 一致性 + DB 抽查

- ✅ CSV 结构：25 行（含头）× 8 列齐整；24 概念与 MD 覆盖面一致；context_pack 5 importer vs ContextBuilderMixin 1 importer 复核属实；`outbox_events` 表确认已不在 live DB（D-OUTBOX「遗留表已消失」属实）；galaxy_service.py:142 fallback 分支实际存在（注：是 `_table_exists` 运行时守卫的防御分支，「死代码」表述可接受但不精确）。
- ⚠️ **C3（残留不一致）：no-authority 计数三处口径不一**。§0 说「缺口只有**两个** no-authority 概念」；§3 实列**三项**；CSV 有**三行** no-authority 类判定（UserWorldSnapshot=no-authority；Experience Memory=no-authority→extend；Trajectory=no-authority）。B-02 修订修掉了「四组→八组」，却留下这处新的。Trajectory 可辩护为读模型缺口非存储缺口，但摘要、正文、机器可读文件必须统一口径。
- ⚠️ **C4（时效性）：`db_table_live` 列无 as_of 标注，行数已漂移**。同日复核：tasks 1089→**1219**、plans 357→**399**、memory_preferences 59→**89**、user_preferences_center 216→**248**、memory_goals 7→**12**、decision_records 947→**2527**（×2.7）、event_outbox 102→**106**、episodic 209→**235**。**决策关键的 0 值全部成立**：cards=0、task_occurrences=0、execution_intents=0、user_state_snapshots=0、conflict_resolution_records=0、unresolved_conflicts=0；goals=4、understanding_depth_daily=149、intervention_records=1 也一致。结论不受影响，但 machine-readable 文件里裸数字无时间戳会被后续任务当作当前值引用。
- 小项：CSV row 18 候选清单含 `plan_outcome` —— DB 无此表（实为 `plan_outcome_service` 服务概念），表名与服务名在 CSV 中无区分；row 12 状态机枚举列 10 态，实际代码 12 态（漏 `READY`、`DISPATCHED`；V3 契约的 AWAITING_USER/EXECUTING/UNKNOWN_OUTCOME 与 CANCELLED 拼写差异未标注）——「几乎一一对应」总括成立，但 CSV 自己给出的清单不全。

### 检查 5｜后续任务可引用性 —— 最小补齐清单

作为被锁定引用的真源，按致误导程度排序：
1. **C1**：UserWorldSnapshot 行纳入并裁决 `UserStateV1`（含 D-STATE 归属更正）。
2. **C2**：D-TASK 加前置条件（补 consistency_validator + 恢复 CARD-DUAL-WRITE，引债账 2026-09-18 节）。
3. **C3**：统一 §0/§3/CSV 的 no-authority 口径（建议：2 个存储缺口 + 1 个读模型缺口，或 3 个，三处一致即可）。
4. **disposition 枚举表**：CSV 有 6 个自由文本值（extend / extend+收敛 / no-authority / no-authority→extend / extend(候选清单交 D-02) / reuse），无语义定义；消费脚本按 `=="no-authority"` 精确匹配会漏行。需 4–5 个封闭枚举 + 每个枚举的「允许动作」一句话。
5. **补行或显式豁免**：Model Router、Tool Registry、cognitive_ownership（1a–1c），Artifact（1d）可并入 Current State 行备注。
6. **`db_table_live` 加 `as_of` 列**（或降级为定性：exists / zero-row / populated），消除 C4。
7. **D-\* 补 owner 卡号与优先级**：目前仅 Outcome Ledger→D-02 有归属；D-INT 写「后续 D-卡」无编号，无法被 Fleet 调度引用。
8. no-authority 行补一列「为什么现有对象不能扩展」的证据指针（map 自己铁律的要求；§3 的「最接近资产」算部分满足）。

以上 1–3 为必须（CHANGES 触发项），4–8 为建议（可与 1–3 同一修订回合完成）。

---

## 2. 与第一路 Reviewer 的分工确认

本路未做第一路的逐项代码实证复核（其负责），专注结构性/对抗性。两条路线在 D-TASK 与 DB 证据上结论交叉可对照：本路证实 cards/task_occurrences/execution_intents/user_state_snapshots 四个 0 行证据均真实，B-06 的核心事实底座可靠。

## 3. 纪律与清理

- 主仓零写入；wt5 内仅本 receipt；DB 仅 SELECT；无模拟器/Gradle/浏览器；无 /tmp 产物；无残留进程（sparkle_db 为既有共享容器，未动其状态）。

## 4. 结论

| 项 | 结论 |
|---|---|
| 四分法 + 全部唯一 owner + 迁移非重写总方向 | 成立（与冻结决策零冲突） |
| 八组 D-* 权威真源指定 | 7.5/8 成立（D-TASK 治理表述需加前置条件；其余方向复核无冲突） |
| 两个 no-authority 判定 | Experience Memory 确认（证据更强）；UserWorldSnapshot 需改写（漏判 UserStateV1） |
| MD↔CSV 一致性 | 存在 no-authority 计数口径与行数时效两处残留问题 |
| 后续任务可引用性 | 修订 C1–C3 + 枚举表后可用 |

**VERDICT: CHANGES**
