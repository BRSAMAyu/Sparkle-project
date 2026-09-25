# WT393 · 卡 A-08 REPORT — Aurora Longitudinal / Ablation Evaluation

- base SHA: `b9bc60ae`（worktree `wt393-a08-ablation` 起点，clean）
- final SHA: 见单提交 `feat(eval): wt393 卡 A-08 …`
- 产物：`v3-output/WT393-A08-ABLATION/{summary.json, EVAL_RESULTS.md, REPORT.md, raw/{full,no_memory,no_experience,fixed_policy}.jsonl}`
- 复跑：`backend/.venv/bin/python scripts/devtools/a08_run_aurora_ablation_eval.py --help`（`--summarize-only` 从 raw 程序化复算 summary；`--verify-repro` 全量双跑断言 summary 一致，本卡实测 exit 0）
- **模型 judge 使用声明：0 次。** 全部指标为确定性程序计算（规则判据 + 引擎行为事实），summary 每个数字可从 raw 复算。

## 1. 结论（先说数字，口径在 §2-3，反例在 §5，不粉饰）

**在声明的 persona 模型与时间线下，完整 Aurora 显著优于固定模板；记忆面净收益为正但存在个体伤害反例；经验面（spine+A-05 patch）在本时间线未带来收敛收益、反增负担。目标指标部分达成，未达部分如实声明（§6）。**

| 指标 | full | no_memory | no_experience | fixed_policy |
|---|---|---|---|---|
| stuck accuracy（预算内收敛率，20 段） | **0.65**（13） | 0.55（11） | **0.65**（13） | 0.30（6） |
| 收敛会话数均值（仅 resolved） | 1.38 | 1.09 | 1.38 | 1.5 |
| 被跟随决策匹配分（1 主/0.5 次/0 错） | 0.32 | 0.28 | 0.32 | 0.12 |
| 旅程面匹配分 / chat 面匹配分 | 0.24 / 0.62 | 0.13 / 0.63 | 0.24 / **0.87** | —（零引擎面） |
| 对照会话侵入率（过度个性化判据） | 0.84（21/25） | 0.84 | **1.00（25/25）** | 0.0 |
| 问句总数 / 每段 / 问后收敛命中 | 0 / 0 / — | 0 / 0 / — | 3 / 0.15 / 0.33 | 0 / 0 / — |
| uncertain 行动数（B1 best-guess） | 21 | 28 | 22 | 0 |
| 每解决段会话成本 | 3.0 | 3.55 | 3.0 | **8.5** |
| 效用（冻结权重 §3） | **−16.2** | −21.4 | −19.05 | −24.8 |

- **vs 固定模板（目标达成）**：full 对 fixed_policy 是全面胜出——accuracy 0.65 vs 0.30、错位被跟随决策 24 vs 42、每解决段成本 3.0 vs 8.5 会话、效用 −16.2 vs −24.8。固定模板的「explain 一招鲜」只在 knowledge/skill 段蒙对（explain ∈ 提名表），其余 8 类摩擦全部错位重试。
- **vs 无记忆（方向达成，含反例）**：记忆面（DB 行为事实+纠正记忆）净收益 +0.10 accuracy、+5.2 效用、uncertain 行动 −7。逐 persona：p02（纠正记忆垫后救回同 tag 换型段 0→0.5）、p04（失败痕迹破局「做不下去」歧义 0→0.5）、p05（纠正环 0.5→1.0）。**反例不剪**：p07 full 0.0 vs no_memory 0.5——历史失败痕迹（ABANDONED≥3）把 entry 真值段系统性带偏到 skill（→V3-FIX-52）。
- **vs 无经验（目标未达，如实声明）**：no_experience 与 full 的 accuracy / 被跟随匹配分完全一致（0.65 / 0.32）——经验回路在本时间线**没有产出收敛收益**；代价面反而更差（侵入率 100% vs 84%、多 3 问句、效用 −19.05 vs −16.2）。机制：①chat 面仅消费词牌+spine+patch，词牌证据单独已足够 S1 命中 → patch 重排（15 次触发、7 个 active patch，真实服务链亲证）只改序不改局；②经验面的 spine 是对照侵入的主源头（→V3-FIX-49）；③patch 只重排不改可行集，chat 面结构性不可服务的类型（18 次）patch 无权救（→V3-FIX-51）。
- **结构性发现（两面不对称）**：本产品中两个消融面分居两个服务面——chat 面（FrictionChatWiring）消费经验（spine+patch）不消费行为记忆；旅程面（StuckJourney）消费行为记忆（事实+纠正）不消费经验（代码事实：stuck_journey_service 无 PolicyPatchService/StateRegister 依赖）。journey-first persona（5/10）的收敛完全不被经验面影响——「A-05 经验未接入旗舰恢复旅程」本身是接线缺口。

## 2. 评估协议（真源不重建；产品代码零改动）

### 2.1 评估对象 = 生产 Aurora 决策服务面（真实调用，无语义 mock）

- **恢复旅程面**：`StuckJourneyService.start/answer/correct`（J-05 生产旗舰恢复入口）——sqlite DB 真源读侧（Goal/Task + `load_recent_task_execution_signals` 失败信号 + StuckJourneyCorrection 纠正环）→ A-03 诊断 → 单问闭环 → 纠正垫后，全部真实服务。
- **chat 决策面**：`FrictionChatWiringService.process_turn`（WIRING-1 生产接线；orchestrator L2712 每消息无门调用同款）——spine 状态证据 + A-05 `patched_decision_inputs` 重排 + A-02 规则评估 + ask→branch_key 直传闭环。Redis 用 fakeredis（与 `tests/services/test_friction_chat_wiring.py` 同款基建绑定）。
- **经验回路**：真实 `InterventionLifecycleService`（exposure→accepted→outcome 关联；契约经 `AuroraDecisionContract` 冻结形状，decision_id 内容寻址 `aurora_*`）+ 真实 `PolicyPatchService`（propose fail-closed → admit 真实证据门（`decision://` 通道对 D-05 outcome_observed 行逐条核验 + scope 一致性）→ single_observation 走 persona confirm / repeated 自动激活）。实测 7 个 active patch 全部经真实证据门产生。
- **spine 经验**：真实 `StateRegister.upsert_from_signal`（信号→状态键→Redis set 指数）+ 真实 `expire_stale`/`_is_expired` TTL 判定。

### 2.2 四臂（同时间线同 seed；单因子输入投影消融，不改产品代码）

| 臂 | 消融面 | 实现位置 |
|---|---|---|
| full | 无 | — |
| no_memory | 失败痕迹/纠正不落库（旅程面读不到历史；当前任务停滞事实保留——它是当前状态非历史） | world 侧不写 ABANDONED 痕迹、段失败软删、纠正不调用 |
| no_experience | spine 不写、patch 不提议 | world/engine 侧短路（契约锁钉死缺席） |
| fixed_policy | 固定模板 bot：无诊断/无澄清/无适应/无纠正通道，任何卡点会话恒回 `explain` | engine 侧短路（契约锁钉死零引擎调用） |

### 2.3 可控时钟（backdate 口径，P-05 同款）

模拟日 → 真实时间戳换算：世界写入（Task 痕迹/spine `last_updated_at`/lifecycle `occurred_at`）按模拟时刻落；服务 `now` 通道直传模拟时刻；`onupdate` 墙钟戳用 Core update 显式值覆盖。spine 状态 TTL（48h day 档）在 backdate 时间戳上由真实过期判定生效——对照会话恰好落在「stale spine 窗口内外」两态，构成侵入探针。

### 2.4 persona 与时间线（10 persona × 14 模拟日，20 段卡点 + 25 对照会话）

persona 谱静态冻结（`persona.py`，import 期断言）：表达显性度（vague/mixed/explicit——weak 词牌如「做不下去」跨 difficulty/energy）× 纠正倾向 × 首选通道（chat_first ×5 / journey_first ×5——两面各消费一个消融面，协议设计判据见 §6 声明）。探针谱：同型重复（经验强化）、同 coarse-tag 换型（patch 滞后）、chat 结构缺口型（time/dependency）、歧义弱词牌、纠正依赖、长停滞 entry、stale spine 对照。

### 2.5 行动与结果模型（冻结规则，非随机数）

persona 对引擎问句 truthful 作答（真值恰落分支直答；不落任何分支时按「同摩擦族支持数最多」分支——确定性，见契约测试）；**被跟随决策 = 首选通道面的可行动决策，首选面静默时跟随另一面**（真实用户两面并存）。结果判据（`RESULT_RULES v1`）：主提名命中 → 当轮解决；次提名命中 → 次轮解决；错位/无行动 → 重试（词牌升级 + 旅程面纠正）；预算 3 会话（`EPISODE_SESSION_BUDGET`）。诚实声明：persona 决策是 seeded 显式模型，量化结论是该模型与真实 Aurora 行为的联合结果，不是真人 RCT；效应方向可审计（判据全冻结），量级不可外推。

## 3. 指标口径（全部确定性；`METRICS_RULES v1`）

- **stuck accuracy** = 预算内解决段 / 总段数（引擎实际重试收敛比例；解决必命中提名——契约锁钉死）。
- **allocation** = 分派与 persona 需求匹配规则分：主提名 1.0 / 次提名 0.5 / 错位·无行动 0（判据真源 = A-03 冻结提名表 `FRICTION_INTERVENTION_NOMINATIONS`）；分面报告旅程面与 chat 面各自均值。
- **overpersonalization** = 对照会话侵入率（无卡点会话中发出问句或非 inert 干预）+ uncertain 行动计数（B1 best-guess 面）。
- **clarification** = 问句总数 / 每段 / 问后收敛命中率（ask_precision）。
- **cost** = 引擎调用会话、chat 轮次、旅程启动、问句、每解决段会话成本。零真实 LLM（四臂皆 0——A-03/A-02 链是确定性规则；fixed 臂引擎调用为 0 已如实计入其成本优势）。
- **utility**（冻结权重）= 1.0×resolved − 1.0×unresolved − 0.4×被跟随错位决策 − 0.15×问句 − 0.6×对照侵入。

## 4. 复现性与质量门

- **可复现**：`--verify-repro` 全量双跑 summary 逐字段一致（exit 0 实测）。`PYTHONHASHSEED=0` 固定——注意这是**评估侧的补丁**：引擎 B1 tie 的 argmax 依赖 frozenset 迭代序（进程相关、无显式 tie-break），本身是已登记缺陷（→V3-FIX-50）。
- **pytest**（sqlite 内存口径）：本卡新测 13/13 绿（`tests/unit/test_a08_aurora_ablation_contract.py`：协议形状/匹配判据/结果模型冻结/消融臂能力面确实缺席/fixed 零引擎/经验回路真实服务链/summary 复算一致性/反例提取面/端到端人口跑通）。邻域：A-02/A-03/A-04/A-06 150+128 绿、policy_patch_service+friction_chat_wiring+lifecycle+experience_projector 147 绿、J-05 迁移+P-05 时序 8 绿、stuck_journey API 8 绿。
- **冷 mypy**：基线对照法——base `b9bc60ae` `mypy app tests` = 2413 errors/634 files，本 worktree = 2402/632（**零推高**；新文件 scoped mypy 0 错。注：2402/2413 为 homebrew mypy 1.20.2 + `app tests` 口径，与历史 1103 数字口径不同，故用同命令 base-vs-worktree delta 作为零漂移判据）。worktree 环境项：backend `app/gen`、gateway `gen`、mobile `lib/gen` 以 symlink 接主仓后 `make proto-gen` 全量重生成（工具链 exit 0）。
- **守卫**：84/84 exit 0（BG 守卫经 proto 重生成后通过）。
- **ruff**：新文件 0 违规（I001 零容忍口径含内）。

## 5. 失败边界与反例清单（保留不剪；逐条可引用 raw 行）

1. **对照侵入（过度个性化主源头；V3-FIX-49）**：full/no_memory 21 次（84%）、no_experience 25 次（100%）。两种机制：stale spine（48h 窗口内）→ S1 置信直出建议；零 spine + 零词牌 → U1 根分裂澄清问。生产 wiring 每消息无门触发是根因。
2. **B1 平权 tie（V3-FIX-50）**：full 21 / no_memory 36 次 uncertain 行动；journey-first 零事实段恒任意型（p06 time→dependency×3 → fail）；纠正环 6 个（p02 走 3 类未中真值）。tie-break 无显式序（进程相关）。
3. **chat 面结构缺口（V3-FIX-51）**：18 次诊断命中但 A-02 守卫结构性排除（time/energy/choice/goal_drift 等）——诊断对、交付断；patch 无权越守卫。
4. **记忆双刃（V3-FIX-52）**：p07 full 0.0 vs no_memory 0.5——历史失败痕迹把 entry 段带偏到 skill。记忆净收益为正但个体伤害可证。
5. **正控（非反例）**：fixed 臂对照侵入 0（模板只在卡点触发）、预算与解决判据全时间线零违例（契约锁）、fixed 零引擎调用、消融臂能力面确实缺席（契约锁双钉）。

## 6. DEFERRED 与诚实边界

- **经验面收益未证**：本时间线中 A-05 patch 重排未改变任何被跟随决策（重排发生在 journey-first persona 的 chat 轮——该轮建议未被跟随）。经验面在「chat-first + 诊断错型 + 同 tag 有历史」的交集下才可能救局，本 10-persona 谱未覆盖该交集（词牌证据单独已够 S1）。证伪/证实需扩充该交集的 persona 谱。
- **两面分居协议**：memory/experience 两消融面分属旅程/chat 两面，故引入 channel 特质（5/5）。这是对本产品接线现状的忠实建模，但也意味着两臂差异是「通道 × 消融」的联合效应；单因子解读须按通道分层（raw 全量保留通道字段）。
- **样本量**：20 段卡点 × 4 臂，确定性系统无抽样噪声，但 persona 谱是 10 个静态时间线——外推力限于该谱。效应量级不可当真人指标。
- 模型 judge 辅助评分：未使用（卡面允许作辅助；本卡判据全部可程序化，无需引入）。
- 旅程面 `correct()` 的 friction_type 来自被纠正诊断（产品 API 语义）；未构造「用户自报真值」通道（避免第二真源）。

## 7. 改动文件清单

- `backend/tests/aurora_ablation/__init__.py`（新增：harness 包 docstring/协议声明）
- `backend/tests/aurora_ablation/persona.py`（新增：10 persona 谱 + 时间线 + 匹配/回答/词牌判据 + friction→spine 投影，import 期断言）
- `backend/tests/aurora_ablation/world.py`（新增：PersonaWorld——sqlite ScenarioDB + fakeredis + backdate 时钟 + 世界侧种子/spine/收口）
- `backend/tests/aurora_ablation/engine.py`（新增：四臂会话循环——chat/journey 真实服务驱动 + 结果模型 + 纠正环 + D-05/A-05 经验回路 + 反例字段）
- `backend/tests/aurora_ablation/metrics.py`（新增：raw→summary 纯函数 + 对照表 + 反例提取 + Markdown 渲染）
- `backend/tests/unit/test_a08_aurora_ablation_contract.py`（新增：13 契约锁）
- `scripts/devtools/a08_run_aurora_ablation_eval.py`(新增：无人值守 runner，--help/--summarize-only/--verify-repro)
- `v3-output/WT393-A08-ABLATION/`（raw×4 + summary.json + EVAL_RESULTS.md + 本 REPORT）
- `v3/06_agent_fleet/DYNAMIC_ISSUES.md`（V3-FIX-49..52 登记）
- 环境项（不入库）：backend/app/gen、backend/gateway/gen、mobile/lib/gen symlink + `make proto-gen` 重生成
