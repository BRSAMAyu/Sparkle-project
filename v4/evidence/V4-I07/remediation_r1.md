# V4-I07 · 一审（R1）跟进项 F1-F4 整改 receipt

- 整改会话：wtI07（原实现分支续作，未 push）
- 整改对象：review_r1.md §D 的 F1-F4（PASS_WITH_CHALLENGES 的销账前置）；一审 receipt 文件与 review_receipt.json 的 review_state 未动
- 分支：`agent/v4/i07`，一审 receipt `8b9ed9ba` 之上
- 方法：每项读面后最小改法 + 一正一反测试 + **mutation 自证（删除该修法 → 对应测试红，复原后绿）**；回归面全量复跑；ruff/black/mypy 零新增

---

## F3（中-高）agent 工具完成断言不传 evidence_source → 结算门 BLOCK 分支生产面不可达

**处置：穿参（`evidence_source="agent"`）——按一审建议的最小改法，未在门侧另判。**

- **影响面（如实）**：`UpdateTaskStatusTool.execute` 的 completed 分支此前调 `TaskService.complete` 不传 `evidence_source`，落默认 `"user"`——agent 经对话工具完成任务时被记为**用户证据**，两处后果：(a) X-04 完成证据记录的无证据回落误用 `user_confirmation`（冒充用户确认）；(b) I07 结算门 `settlement_for_task_row` 把 completed_by 判成 user，`BLOCK.agent_completed_*` 分支在生产对话面不可达（空心门，与 I02-CHALLENGE-1 同型）。全仓 `TaskService.complete/complete_task` 调用点复查：REST（user bearer）= user 默认（保留）、focus_auto（focus 计时器）= 显式 focus_auto（保留）、本工具 = 本次唯一缺口，已补。
- **为什么标 "agent" 而非 "user"**：该工具由 agent 工具链执行，完成断言的产出者是 agent（哪怕由用户对话触发，工具层无法也无须甄别口吻真伪）——X-04 分级信任口径「非用户产出从严」：agent 无证据回落 `system_event`，绝不伪造 `user_confirmation`。真正亲手完成的 mastery 用户走移动端/REST 完成面（`evidence_source="user"`），照常结算，不误伤。
- **改动**：`backend/app/tools/task_tools.py` completed 分支穿参 + 注释写明依据。
- **测试（一正一反，接线级）**：
  - 反例集成 `test_chat_tool_agent_evidence_completing_mastery_task_does_not_settle`：经工具完成 legacy mastery（TRAINING）任务 → 掌握写面零触发（BLOCK）+ 完成事实照常 + 证据记录 source=="agent"；
  - 正例集成 `test_chat_tool_deliverable_task_via_agent_evidence_still_settles`：经工具完成声明 deliverable 任务 → 照常结算（验收②不因穿参误伤）；
  - 接线钉 `test_completed_passes_agent_evidence_source`（工具面 mock 级，断言 kwargs 穿参）。
- **mutation 自证**：把穿参还原为缺省（不传 evidence_source）→ 两集成测红（BLOCK 分支重新不可达、证据记录冒名 user）→ 复原后绿。

## F1（中）aurora 模型自判 correct_answer → 白名单 sprint 节点 +15/次无上限（门外第二 agent 可触发掌握写）

**处置：b) limitations 如实登记 + 频次守卫（不静默）。未接 `settlement_for_task_row`，理由如下。**

- **为什么不收口（a 路判定）**：`settlement_for_task_row(task, evidence_source=…)` 的输入是 **Task 行**（guide_json 策略块 / type+cognitive_ownership 推导），判定的是「这一次**任务完成**能否结算人类掌握」。aurora 的 `_apply_correct_answer_mastery_update`（`aurora/runtime_v1/service.py`）不存在 Task 行——它是 decision_loop 的 LLM 在对话轮里自判「用户答对了」后对 sprint pack 节点的**对话级掌握激励**，与任务完成语义不同型。硬接等于造一个假 Task 行或给函数加第二套分支（违反单一入口语义）。该写点属**既有行为**（非 I07 引入），中期方向维持一审建议：纳入 `human_mastery_settlement` 判定或改证据门（登记为已知债，见 limitations §9）。
- **守卫（非静默）**：`CORRECT_ANSWER_MASTERY_DAILY_NODE_CAP = 3`——每 `(user, node, UTC 日)` 进程级计数封顶，超限**跳过增量并 WARN**（写明 model self-attested surface、已应用次数、跳过事实）；审计留痕既有（mastery_audit_log，effect_kind=projection，可查询可重放）。既有单轮内 dedupe 不变。
- **边界（如实）**：计数是进程级的（服务实例重建即清零；长生命周期路径=orchestrator 单例面持续有效）；durable 频次门归中期已知债。呈现面有界：≤ 3 次 × 15 分/日/节点/进程。
- **测试（一正一反）**：`test_plan_turn_correct_answer_mastery_writes_still_apply_under_daily_cap`（未到封顶照常逐次应用，守卫不误伤正常完成检验）；`test_plan_turn_caps_correct_answer_mastery_writes_per_day`（超过封顶后零新增写）。
- **mutation 自证**：把守卫阈值改成永假（`10**9`）→ cap 反例测红 → 复原后绿。

## F2（中）C2 防漂移只钉单方向

**处置：补双向相等断言 + 消费路径逐成员/补集（`test_derive_goal_purpose_matches_x02_learning_types` 扩写）。**

- 字面集 ≡ X-02（一审已钉，保留）；新增：hybrid 内部集 `_X02_ALIGNED_LEARNING_TASK_TYPES`（`derive_goal_purpose` 实际消费）≡ X-02 `LEARNING_TASK_TYPES` 双向相等断言；新增消费路径逐成员断言（X-02 每个成员经 derive 必须 mastery）与补集断言（X-02 之外的 TaskType 不得经类型路径推导 mastery）——不依赖集合对象等值，钉真实行为。
- **mutation 自证（两方向）**：删内部集 `REFLECTION`（一审的原始探针，当时 29/29 全绿）→ 现在**红**；X-02 侧加杂员（`SOCIAL`）→ 同测**红**；两向复原后绿。

## F4（中）红化键集保留 `solution_steps`

**处置：该剥——键集补齐 `solution_steps` + 测试改向。判定依据：**

- 卡验收③原文「**独立检验答案**不出现在可见/可检索上下文」+ EXPERIENCE_AND_LEARNING「Agent 准备相近示例/提示/检查，**不提前泄露独立检验答案**」：契约本意保护的是**答案面**，而 `solution_steps` 是工作解（解题实质），与已在键集内的 `solution` 同面——独立检验段里模型上下文若带解题步骤，用户可从上下文抄得答案，独立验证失效。fixture 自己的 `solution_steps=["展开到二阶","e^x 的导数恒为自身"]` 即完整解法，构成构造性泄漏（一审 C4 弱点 1 判定成立）。
- 对照「判分权威原地保留、注入前剥除」口径：服务端 `tasks.guide_json` 本体的 `solution_steps` **保留**（判分/复核权威不动），任何上下文投影经 `redact_independent_check` 剥除。红化是投影面门，不是数据删除——口径两侧都守住。
- **改动**：`INDEPENDENT_CHECK_ANSWER_KEYS` +`solution_steps`（含键集注释写明 F4 依据）；投影测试改向（断言剥除+路径可观测+服务端本体保留）；冻结集测试同步。
- **mutation 自证**：从键集删 `solution_steps` → 投影测试与冻结测试双红 → 复原后绿。
- 同面相邻键（`worked_solution` 等未登记同义词）维持一审 C4 弱点 2 的登记口径（生产者写面唯一化 + 探针进守卫为后续项），本次不扩词表猜测。

---

## 测试计数（本整改后）

| 面 | 整改前 | 整改后 | 增量 |
|---|---|---|---|
| `tests/unit/test_hybrid_policy.py` | 29 | **31** | +2（F3 工具集成一正一反；F2/F4 为既有用例扩写/改向） |
| X-02 三文件（policy/guard/eval） | 112 | **112** | 0 |
| `tests/contract` | 352 | **352** | 0 |
| chat 面（4 文件） | 21 | **21** | 0 |
| `tests/unit/test_aurora_runtime_decision_loop.py` | 91 | **93** | +2（F1 一正一反） |
| `tests/test_plan_task_tools_production.py` | 72 | **73** | +1（F3 接线钉） |
| 受影响面集合（hybrid+X-02+契约/续接视图/选择器） | 277 | **279** | +2 |

全部复跑绿（本会话独立执行）；四项 mutation 全部 RED→复原绿（§各条）。

## 质量门（零新增口径，与一审同法）

- ruff：改动 app 文件 + 新增/改写测试文件 **All checks passed**；`tests/test_plan_task_tools_production.py` 存在 **14 项既有** F401/C408/UP017（HEAD 基线同为 14，本卡零新增——该文件本就不 clean，非本卡引入）
- black（line-length 120）：`hybrid_policy.py`、`test_hybrid_policy.py`、`test_aurora_runtime_decision_loop.py` clean；`task_tools.py`/`aurora service.py`/`test_plan_task_tools_production.py` 存在**既有漂移**（HEAD 基线同态；本卡增量行经 `black --diff` 核对为零命中，与一审 limitations §7 对 task_service.py 同口径——不重排无关行）
- mypy：`mypy app/core/hybrid_policy.py app/tools/task_tools.py app/aurora/runtime_v1/service.py` = **30 errors in 30 files**，HEAD 基线（stash 复跑）同为 30，改动三文件名下 0 命中；一审口径命令（+allocation/task_service/chat）= 30/30 与基线一致——零新增

## 行为变更声明（既有行为修改，如实）

1. **F3 是生产行为变更**：agent 经 `update_task_status` 完成 mastery 任务的掌握结算从「以 user 名义通过」变为「BLOCK 不结算」；完成事实、outcome、行动账本照常。deliverable/合法代办照常结算。移动端/REST 用户完成面零变化。
2. **F1 是呈现面收紧**：aurora 模型自判答对的节点掌握激励从无上限变为 ≤3 次/日/节点/进程（进程级）；超限 WARN 留痕。审计留痕语义不变（projection）。
3. **F4 是投影面收紧**：`solution_steps` 从投影面保留变为一律剥除；服务端数据零变化。既有生产者（本卡策略块约定，此前无生产者）不受数据迁移影响。
4. **F2 纯测试强化**，生产行为零变化。

—— wtI07 整改会话，2026-09-28
