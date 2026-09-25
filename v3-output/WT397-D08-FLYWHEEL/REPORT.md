# WT397 · 卡 D-08 REPORT — 数据飞轮纵向证明与 Regression Dashboard

**Status: READY_FOR_REVIEW**
**Base SHA:** `2d2336ea`（main HEAD，worktree `wt397-d08-face` 起点，clean）
**Final SHA:** 见单提交 `feat(eval): wt397 卡 D-08 …`
**产物：** `v3-output/WT397-D08-FLYWHEEL/{dashboard.json, DASHBOARD.md, REPORT.md, raw/{flywheel,no_feedback}.jsonl}`
**复跑：** `backend/.venv/bin/python scripts/devtools/d08_run_flywheel_eval.py --help`（`--summarize-only` 从 raw 程序化复算 dashboard；`--verify-repro` 全量双跑断言 per-persona 结果逐字节一致——本卡实测 OK）
**模型 judge 使用声明：0 次。** 全部指标为确定性程序计算；评估对象全部为真实生产服务面。

## 1. 结论（先说数字，口径在 §2-3，反例在 §5，不粉饰）

**在声明的 persona 模型与 Day0/Day3/Day7 双臂配对协议下，数据飞轮的"反馈→未来行为真实变化"闭环被逐 persona 证实：10/10 persona 各自产生 ≥1 条可解释 adaptation 因果链（纠正→旅程面诊断垫后 14 条 + 记忆否认→旧偏好停止注入 10 条）；同时 25 条无效/无效力/有害个性化全部保留在台账（patch 改序不改局 11、记忆否认后 Day3 未变安静 10、纠正垫后使匹配分低于对照 4）。理解五维在全部 10 persona 上从 Day0 的 unknown/基线迁移到 Day7 可计算值（coverage unknown→ok ×10、scope unknown→ok ×10、freshness unknown→ok ×10、utility unknown→ok ×10、correctness 1.0→0.33 因真实撤回落账）。**

### 1.1 10 persona 配对结果表（Day0 vs Day7，flywheel 臂；对照列 = no_feedback 臂同日探针）

| persona | 真值 | Day0 旅程判断 | Day7 旅程判断(fly) | Day7 旅程判断(对照) | 纠正生效 | 旧偏好注入 d0→d7 (fly/对照) | utility d7 | 验收 |
|---|---|---|---|---|---|---|---|---|
| p01_experience_reinforce | knowledge | dependency | energy（adjusted=True） | dependency（adjusted=False） | ✓×2 | True→False / True | 0.667 | PASS |
| p02_experience_hysteresis | knowledge | skill | dependency（adjusted=True） | skill（adjusted=False） | ✓×2 | True→False / True | 0.667 | PASS |
| p03_explicit_difficulty | difficulty | skill | difficulty（adjusted=True） | skill（adjusted=False） | ✓ | True→False / True | 0.667 | PASS |
| p04_ambiguous_weak | difficulty | skill | difficulty（adjusted=True） | skill（adjusted=False） | ✓ | True→False / True | 0.667 | PASS |
| p05_correction_loop | goal_drift | choice | entry（adjusted=True） | choice（adjusted=False） | ✓×2 | True→False / True | 0.667 | PASS |
| p06_structural_gap | time | dependency | energy（adjusted=True） | dependency（adjusted=False） | ✓×2 | True→False / True | 0.667 | PASS |
| p07_plan_drift_entry | plan_drift | dependency | energy（adjusted=True） | dependency（adjusted=False） | ✓×2 | True→False / True | 0.667 | PASS |
| p08_skill_repeat | skill | skill | skill（无纠正——诊断=真值） | skill | n/a | True→False / True | 0.667 | PASS |
| p09_choice_feedback | choice | choice（诊断=真值） | choice | choice | n/a | True→False / True | 0.667 | PASS |
| p10_quiet_then_tooling | goal_drift | choice | entry（adjusted=True） | choice（adjusted=False） | ✓×2 | True→False / True | 0.667 | PASS |

- **记忆面（10/10）**：Day1/Day4 的真实 deny（`record_memory_reference_outcome`）+ Day4 retract（删除级）之后，Day7 探针 flywheel 臂的旧偏好记忆不再被 surfacing（0/10），no_feedback 对照臂 10/10 依旧在同位注入——**记忆系统真的因用户反馈变安静了**。Day3 中程 10/10 尚未变安静（单次 deny 的 confidence 降幅未越过 surfacing 门）——如实进台账（`memory_not_quieter` ×10）。
- **决策面**：旅程面纠正垫后 14 条链全部 `adjusted_by_correction=True` + 与对照臂差分成立；chat 面 patch 全部"已激活、被 `patched_decision_inputs` 消费（applied_patch_ids 在案）、但不改变被选干预"（11 条 ineffective_patch）——与 A-08 结论（改序不改局）在纵向协议下复现，非回归。
- **理解五维（10/10 迁移）**：coverage unknown→ok(0.33)（3 个探针 judgment 落入 7 天滚动窗）；correctness 1.0→0.33（真实 retract 计入负向纠正）；scope unknown→ok(0.0)（deny/retract 计入 scope 负向，误用率 0.33 超过 SCOPE_TOLERANCE=0.25 归零——旧偏好被注入 2 次是被用户证实的真实 scope 误用）；freshness unknown→ok(0.2)（旧偏好存活 24 天才被替换）；utility unknown→ok(0.667)（accepted 4 / decisive 6）。**五维全部挂在真实表取数上，无一处缺数据给满分。**
- **outcome 面**：10 persona × 2 段 = 20 次 D-05 真实 exposure→accept→outcome 关联（flywheel+对照两臂各 20，admit 证据门全过）；personalization 面：active patch 每 persona 1-2 个（真实 A-05 证据门 single_observation→confirm）。

## 2. 评估协议（真源不重建；产品代码零改动）

### 2.1 评估对象 = 生产数据飞轮服务面（真实调用，无语义 mock）

| 面 | 真实服务 | 说明 |
|---|---|---|
| 决策 | `StuckJourneyService.start/answer/correct` + `FrictionChatWiringService.process_turn` | A-08 同款调用协议（truthful branch_key 直传） |
| 记忆 | `ContextPackBuilder.build`（M-03 预筛→词法 rank→语义门控 fallback→M-05 selfcheck 全漏斗）+ `MemoryService.record_memory_reference_outcome/retract_memory` | 真实 `ContextPackRun` telemetry；真实 `MemoryCorrection` 治理动作 |
| 理解 | `UnderstandingDimensionsService.collect_window_inputs` + D-03 core 五维纯函数 + `SufficiencyJudgeService.evaluate/persist_judgment`（Stage20 确定性 judge，非 LLM） | 缺数据 = unknown，永不默认 0/1 |
| outcome | `InterventionLifecycleService.record_exposure/record_response/record_outcome_association` | A-01 冻结契约载荷（rationale 含模拟日，decision_id 内容寻址跨事件唯一） |
| 个性化 | `PolicyPatchService.propose/admit/confirm`（真实证据门）+ `StuckJourneyCorrection` 纠正环 | prefer 方向 = A-03 提名表真值主干预 |

### 2.2 双臂 paired design（PERSONALIZATION_EVAL §paired 的确定性操作化）

- **flywheel 臂**：反馈事件全开（纠正 / patch 确认 / 记忆 deny+retract）；
- **no_feedback 臂**：同一世界、同探针、同世界事件（任务完成、探针话轮、pack 组装、judge 落行），**零反馈事件**（契约测试钉死缺席）；
- 行为差分（同 persona 同探针日跨臂对比）= 飞轮因果证据；链成立需三段齐备：**事件 → 服务读侧证据（applied_correction_ids / adjusted_by_correction / applied_patch_ids / surfaced 差异）→ 与对照臂行为差分**。

### 2.3 时间线与可控时钟

- 探针日 Day0/Day3/Day7 同构（同词牌、同 S/F、同 session 语义）；Day1/Day4 反馈事件日；Day5 对照话轮（over-personalization 探针）。
- 时钟：世界原点 t0（进世界的真实墙钟），sim day d = t0−(SPAN−1−d) 天——**Day0 最旧、Day7 最新**（纵向叙事沿真实时间正向积累）；A-08 `sim_clock` 经 `_wd` 反转复用；带 `now` 通道的服务直传模拟时刻，无 `now` 通道的写入（judge 落行/pack telemetry/memory correction）步末显式回填 `created_at`。
- 探针同构性保障：失败痕迹 Day0 一次 seeding（14 天窗口内恒 F 条）、当前 STUCK 任务每探针重建（dsp<5 恒不触发阈值）、经验 spine 不在协议内（其 TTL 读语义以真实墙钟判定，backdate 写入会产生死写/d7 单侧可见，破坏探针同构——A-08 V3-FIX-49 已登记该面侵入性；D-08 五面不含经验面，经验面归 A-08 权威）。

### 2.4 persona 与记忆种子（复用声明）

- 人口 = A-08 的 10 persona 原样复用（`tests.aurora_ablation.persona`）；探针组成 = 该 persona 首 episode 的摩擦真值/S/F/词牌——零新建模。
- 记忆种子 = 每 persona 3 条（2 稳定方法偏好 + 1 条已废弃旧习惯"以前 X 就先跳过这段"），值以该 persona 探针词牌的特异短语入词——真实记忆系统里用户偏好本就以其自述措辞存在；这也是 M-05 selfcheck 词面相关性门可放行的原因（与话轮零重叠的偏好会被 `selfcheck:irrelevant_to_query` 结构性切掉——真实产品行为，协议顺势利用而非绕过）。

### 2.5 persona 决策模型（seeded 显式声明）

旅程面误判（act 出口且 ≠ 真值）→ file「不是这个原因」；注入的旧偏好被察觉 → deny（Day1）/ retract（Day4）；其余注入 → accept；对引擎问题 truthful 作答（A-08 同款判据）。persona 决策是被声明的实验装置，量化结论是该模型与真实服务行为的联合结果，不是真人 RCT；效应方向可审计（判据全冻结），量级不可外推。

## 3. 指标口径（全部确定性；`D08_METRICS v1`）

- **paired result**：同臂 Day0/Day3/Day7 逐面配对（五面键序冻结）；Day7 vs Day0 delta 程序化计算。
- **adaptation 因果链**：`adaptation_chains()` 纯函数——`established` = 事件+读侧证据；`behavior_changed` = 与对照臂差分；**验收逐 persona 判定 = ≥1 条 established 且 behavior_changed**。
- **无效个性化台账**：`extract_invalid_personalization()` 纯函数——`ineffective_patch`（applied 但零差分）/ `patch_never_applied`（激活但 chat 结构性不可服务、零消费）/ `memory_not_quieter`（否认后仍同位注入）/ `harmful_correction_differential`（纠正垫后使旅程面匹配分低于对照）/ `correction_not_read`（落库未被读）。
- dashboard 的每个数字可从 raw 复算（`--summarize-only`）；`--verify-repro` 双跑一致（易变随机标识 uuid4/内容寻址 id 归一为占位符后比对——结构与存在性保留）。

## 4. 因果链证据（逐 persona 可引用到 raw 行）

raw 行示例（p01_experience_reinforce，flywheel 臂）：

1. `[probe d0]` journey `friction_type=dependency`（真值 knowledge）→ 误判；
2. `[event d1] journey_correction` 真实 `correct()` 落库（`correction_id` 在 raw）；
3. `[probe d3]` journey `adjusted_by_correction=True`、`friction_type=difficulty`（纠正把 dependency 垫后到后验下一位）——对照臂同日仍 `dependency`（差分成立，链 #1 changed=True）；
4. `[event d1/d4] memory_reference_outcome denied` ×2 + `[event d4] memory_retract`（真实 confidence 0.9→0.8→0.7、retract 删除级）；
5. `[probe d7]` pack surfaced 不含旧偏好（对照臂依旧 3 条含旧偏好同位 0）——**记忆变安静链 changed=True**；
6. 全部 10 persona 的链表见 `dashboard.json → per_persona.adaptation_chains`（每条带 event 引用、读侧证据、before/after）。

## 5. 无效/无效力个性化台账（25 条，保留不筛——验收红线）

| kind | 数量 | 语义 |
|---|---|---|
| ineffective_patch | 11 | patch 经真实证据门激活、被决策输入消费（applied_patch_ids 在案，含 p08/p09 的"消费后被 A-02 能力守卫结构性 no_action"形态），但行为与无反馈对照相同——改序不改局（A-08 结论纵向复现） |
| memory_not_quieter | 10 | Day1 单次 deny 后 Day3 旧偏好仍同位注入（confidence 降幅未过 surfacing 门）；Day4 追加 deny+retract 后 Day7 才消失 |
| harmful_correction_differential | 4 | p05/p10：对照臂误判 choice 但其干预 reflect 恰为真值 goal_drift 的主提名（1.0 分）；纠正垫后把类型挪走、干预变为 clarify/rescope（0 分）——**纠正让类型更对但行动更差**，真实代价如实入账 |

注：`patch_never_applied`（激活且零消费）与 `correction_not_read`（落库未被读）两判据在本轮 0 条——前者因 chat 面对 no_action 出口仍消费 patched 决策输入（applied ids 在案），后者因 skipped 纠正事件（诊断=真值）不入链；两判据作为契约保留在 metrics 中。

## 6. 验证证据

- **新测**：`backend/tests/unit/test_d08_flywheel_contract.py` 7/7 绿（协议形状锁 / no_feedback 反馈面缺席锁 / 因果链三段判据锁 / 无效台账保留锁 / paired 复算锁 / 版本锁）。
- **邻域回归**：A-08 契约 13 + D-03 理解契约 + friction chat wiring + policy patch + intervention lifecycle + memory service + A-03 诊断（sha 双钉）+ context pack + sufficiency judge = **264 passed**。
- **冷 mypy**：`mypy app` 口径（`scripts/ci/mypy_ratchet.sh`）= **1103 = 基线零推高**；新文件 scoped（`mypy tests/d08_flywheel tests/unit/test_d08_flywheel_contract.py`）= **0 错**。注：worktree 缺 `app.gen` 时该口径为 1106（+3 环境项，已按 wt387 先例以 gitignored 符号链接补齐环境后复测 =1103）。
- **守卫**：`bash scripts/run_all_rule_guards.sh` = **84/84 exit 0**（worktree 需先补齐 gen 符号链接环境项——AQ/BG 两守卫为存量环境败，A/B 实证：主仓同 base commit 84/84，worktree 补齐后 84/84；环境项未入库）。
- **ruff**：新改文件 0 违规。
- **可复现性**：`--verify-repro` 全量双跑，canonicalized per-persona 结果逐字节一致（exit 0）；`--summarize-only` 从 raw 复算 dashboard 一致。
- **评估不变量**：双臂探针 30+30=60（10 persona × 3 探针 × 2 臂）；no_feedback 臂零反馈事件（契约测试逐 event_type 断言）。

## 7. 改动清单（产品代码零改动；全部为新增评估面）

| 文件 | 内容 |
|---|---|
| `backend/tests/d08_flywheel/__init__.py` | 协议与评估对象声明 |
| `backend/tests/d08_flywheel/protocol.py` | 冻结协议常量（探针日/双臂/记忆种子/persona 短语表）+ 探针组成导出 |
| `backend/tests/d08_flywheel/engine.py` | 双臂纵向驱动器（真实服务驱动 + backdate 可控时钟 + 五面快照） |
| `backend/tests/d08_flywheel/metrics.py` | paired/因果链/无效台账/summary 纯函数（`D08_METRICS v1`） |
| `backend/tests/unit/test_d08_flywheel_contract.py` | 协议契约锁 7 用例 |
| `scripts/devtools/d08_run_flywheel_eval.py` | 无人值守 runner（--help / --persona / --summarize-only / --verify-repro） |
| `v3-output/WT397-D08-FLYWHEEL/` | raw ×2 + dashboard.json + DASHBOARD.md + REPORT.md |

## 8. 与依赖卡的衔接（不重建真源）

- **A-08**：人口/harness/词牌/判据/契约全部复用；本卡把 A-08 的"消融横向对照"升级为"反馈纵向配对"——A-08 的无效 patch 结论在本协议下复现（改序不改局），p07 记忆双刃反例的同族（harmful_correction_differential）在纵向面出现 4 条。
- **D-03**：理解五维走 D-03 服务+契约原样（含 unknown 语义）；本卡是其"真实数据上跑通"的纵向证明（dev 实测的 dark channel 在真实反馈写入后点亮）。
- **D-05/D-02**：outcome 关联走真实 lifecycle（SELF_REPORTED 口径与 A-08 一致）；utility 维度仍标 immediate-loop 边界（outcome 因果联动升级 reserved——与 D-03 契约注释一致，不抢跑）。
- **D-06/D-07**：dashboard 的 outcome 口径（goal-linked 正向 outcome 关联计数）与 D-06 WVPL fact 的 loop 腿同源（真实 OutcomeEntry + plan_id/goal 关联）；洞察面证据卡（D-07）消费的 D-05 聚合在本协议中被真实写入——Q-08 终局审计可直接引用本目录 dashboard.json 作为 D-08 gate 证据。

## 9. 已知限制与诚实声明

1. **persona 决策是显式模型**（seeded）：纠正倾向全员开启（A-08 的 correction_propensity 异质性不在本卡问题内）；量化结论是该模型与真实服务行为的联合结果。
2. **judge 解析面固定**：Stage20 judge 本身与落行路径全真实，但 `CurrentTurnParseResult` 由 harness 固定喂入（生产为模型解析面）——被隔离的是解析面波动。
3. **UserStateV1 为简化投影**：judge 的 state 信封取自世界真实行（STUCK 计数），非完整 state_aggregator 输出——coverage 值的绝对水平不可外推，迁移方向（unknown→ok）可信。
4. **经验 spine 不在协议内**（§2.3）；**对照话轮侵入率两臂均高**（8/20——与 A-08 的过度介入发现一致，Q-04 红队可引用）。
5. **worktree 环境项**：`backend/app/gen`、`mobile/lib/gen`（符号链接）与 `backend/gateway/gen`（拷贝）为运行/守卫环境补齐，gitignored/untracked，未入库；合并后需在 integration HEAD 重跑（那里 gen 面齐备）。
6. **10 静态时间线外推力有限**：与 A-08 同——效应方向可审计，量级不可外推为真人 RCT。

## 10. DEFERRED

- 经验面（spine）纵向证明：TTL 读语义与可控时钟的交互需引擎侧 now 注入（产品改动），本卡不做——A-08 已登记（V3-FIX-49）。
- utility 维度的 outcome 因果联动升级（D-02 truth-class 对比接入五维）：需 D-05 真实数据规模，契约已预留（bump 版本路径在案）。
- 10 persona 之外的人群扩展 / 更长时间线（Day14/30）：协议参数化已就绪（`PROBE_DAYS`/`EVENT_DAYS` 常量），收益存疑不抢跑。
- DASHBOARD.md 的 mobile 面可视化：Q-04/Q-08 消费 JSON 即可，无 UI 交付要求。
