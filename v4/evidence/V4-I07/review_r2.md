# V4-I07 · 独立审查 R2 receipt（wtI07R2）

- 审查会话：wtI07R2（未参与 I07 实现、一审与整改，独立会话）
- 审查对象：branch `agent/v4/i07` @ `987b79ac`（实现 `c4da470e` → 一审 receipt `8b9ed9ba` → 整改 `987b79ac`），base `1063abb3`
- 卡：`v4/04_tasks/cards/V4-I07.md`（implementation · high · 双审）；本 receipt 为 r2（二审），一审见 review_r1.md
- 方法：只读审查 + 独立复跑（5 面 + chat 面）+ **四项独立 mutation**（F3 撤穿参 / F1 撤守卫 / F2 两方向漂移）+ 三个对抗探针 + F4 候选键猎测；未 push
- **总裁决：PASS（二审通过；整改四项全部核销，双审齐，可销账 DONE_REVIEWED）**
- CHALLENGED（不阻塞销账，须认领）：见 §E 三项移交 + §D 一项措辞精确化建议

---

## A. F3 整改核（中-高：agent 工具完成穿参 evidence_source="agent"）

**核验通过。**

1. **独立 mutation**：`task_tools.py` completed 分支撤穿参（还原为 `TaskService.complete(db_session, task, actual_minutes=actual_minutes)`）→
   `test_chat_tool_agent_evidence_completing_mastery_task_does_not_settle` /
   `test_chat_tool_deliverable_task_via_agent_evidence_still_settles` /
   `TestUpdateTaskStatusTool::test_completed_passes_agent_evidence_source` **3 failed**；复原后集成双测 **2 passed**。测试真实钉住穿参，非纯函数自测。
2. **REST/focus 面零变化声明复核（调用点全查）**：全仓 `TaskService.complete/complete_task` 调用点共 5 类，逐一核：
   - REST `api/v1/tasks.py:1408`（user bearer，`user_id=current_user.id`）→ 缺省 user，**未动**；
   - `hybrid_journey_service.py:902` → 显式 `evidence_source="user"`（AWAITING_USER 态用户 outcome 确认，语义正确），**未动**；
   - `task_service.py:674` focus 计时器 → 显式 `focus_auto`，**未动**；
   - `action_commands/task_commands.py:237`（X-03 action proposal 完成）→ 缺省 user：核 `action_authorization._AUTO_ALLOWED_RISK=frozenset({"low", None})` 且 COMPLETED 的 `status_change_semantics=("medium", False)`（不可逆）→ **该路径不可能走 auto，必须用户显式 approve**，user 名义成立，**非缺口**；
   - `tools/task_tools.py:186` → 本次唯一 agent 断言缺口，已穿参 "agent"。声明「本工具 = 本次唯一缺口」**经全查成立**。
3. **「agent 无证据回落 system_event」从严方向**：`task_completion_evidence.py:48` `"agent": "system_event"`（绝不落 `user_confirmation`）；X-04 分级信任口径「非用户产出从严」与穿参方向一致，**正确**。`EVIDENCE_SOURCES` 封闭集含 "agent"，无校验缺口。

## B. F1 判定复核（中：aurora 模型自判 correct-answer 掌握写封顶）

**判定：不接 `settlement_for_task_row` 的理由独立成立；封顶+WARN 为可接受的有界缓解。**

1. **不同型判定独立复核**：`settlement_for_task_row(task, evidence_source)` 的输入契约是 **Task 行**（guide_json 策略块 / type+cognitive_ownership 推导），判定「这次**任务完成**能否结算人类掌握」。aurora `_apply_correct_answer_mastery_update` 无 Task 行——是 decision_loop 的 LLM 在**对话轮**里自判「用户答对」后对白名单 sprint 节点的对话级激励，硬接等于伪造 Task 行或给单一入口函数加第二套分支（后者违反「等价语义不在调用方复制」的模块自声明）。**判定成立**。中期方向（纳入 human_mastery_settlement 或证据门 + durable 频次门）已在 limitations §9 登记，方向正确。
2. **CAP=3 边界如实性**：`(user, node, UTC 日)` 进程级 dict 计数；仅**成功写后**自增（`else` 分支，失败写不耗额度）；`_increment_mastery` 双标尺钳制（1.0/100.0 封顶）→ 呈现面上界 0.45/日/节点/进程（或 100 标尺 45）。limitations §9 如实写明「进程级」「服务实例重建即清零」「判定者仍是模型自判」；orchestrator 单例长生命周期路径已注明。**措辞精确化建议（§D-1）**：「多 worker 各自 3」的乘数效应（N 进程 → 3N/日/节点）未逐字写出，由「进程级」一词承载——建议销账时补一个数字从句，不影响如实性判定。
3. **封顶后跳过 + WARN 不静默——本会话实测**：独立探针（cap+2 轮 plan_turn）→ `writes=3`（封顶生效）+ **2 条 loguru WARNING** 直出（`capped for user … 3/3 increments applied today … skipped increment is NOT applied`），消息含面别、已应用次数与跳过事实。不静默成立。
4. **独立 mutation**：守卫比较改 `if False and …`（常量保持 3）→ `test_plan_turn_caps_correct_answer_mastery_writes_per_day` **FAILED**（5 次写未被拦）→ 复原绿。
   - 注：整改自证的 mutation 改常量为 `10**9`——该测试循环次数 import 同一常量，此改法会使测试循环不可终止（等效红但不可观测）。**测试自引用常量是轻微设计弱点**（§D-2），条件比较 mutation 才是可观测红；不影响守卫真实性判定。

## C. F4 判定复核（中：solution_steps 红化）+ 对抗面

**判定：该剥——成立。双侧口径守住。**

1. **依据链复核**：卡验收③「独立检验**答案**不出现在可见/可检索上下文」+ EXPERIENCE_AND_LEARNING「不提前泄露独立检验答案」；fixture（test_hybrid_policy.py:444）`solution_steps=["展开到二阶","e^x 的导数恒为自身"]` 即含答案实质的完整工作解——一审 C4 弱点 1 的「构造性泄漏」判定**成立**，剥除正确。
2. **双侧断言**：投影侧 `solution_steps not in inner` + 剥除路径可观测（`removed` 以 `solution_steps` 结尾路径）+ `contains_independent_check_answer(clean) is False`；服务端侧 `_guide_with_check()` 本体 `answer`/`solution_steps` 原样保留断言在。`redact_independent_check` 纯函数深拷贝、零副作用。**「判分权威原地保留、注入前剥除」两侧守住**。
3. **漏网答案键猎测（本审查独立，2 个候选键家族实测）**：构造 `independent_check` 标记节点携带——
   - `explanation`（解析/解答说明，含「逐项展开得 1 + x + x^2/2，这就是答案」）→ **穿透**（`removed=()`，全文进投影）；
   - `correct_option`（选择题正确项）与判分短键 `grading.correct` → **穿透**（`removed=()`）。
   判定：与一审 C4 弱点 2 同类（封闭键集可枚举绕开 + 未标记同义键不动，opt-in 纪律），**非 F4 处置缺陷**——`solution_steps` 在键集内的判定依据（工作解=答案面）同样适用于这些键，但整改明确「不扩词表猜测」并维持登记口径。当前 `independent_check` 生产写面仅本卡策略块约定（无既有生产者，一审 C4 核验），风险被生产者缺位压低。**移交 §E-1**：探针进守卫或生产者 schema 校验（封闭键集 → 生产者只准用冻结键）。

### C.4 对抗探针（三向，独立构造）

| 探针 | 构造 | 实测 | 判定 |
|---|---|---|---|
| a) mixed 下 agent 部分结算 | 策略块 mixed+human_required=F，agent 证据 | `OK.deliverable_delegation_settlement`（结算）；mixed+human_required=T → `BLOCK.agent_completed_human_required_mastery` | 与声明语义一致：mixed 非 human_required 部分结算=用户声明的合法代办；human_required 是硬闸 |
| b) 多步任务归因 | 同 plan 两行：agent 完成非末步（mastery 行）+ 用户完成末步 | 行 A `BLOCK.agent_completed_mastery_step`；行 B `OK.human_authored_settlement`——**逐行独立归因**；delegated 准备行+agent → 结算（合法），user_core 末行+agent → 结算（mixed 行级语义，步骤级消解归 resolve_step_purpose 下游） | 归因单元=Task 行完成动作，与验收①语义一致，无跨行冒记 |
| c) deliverable 混 learning 子步 | 策略块 deliverable + 各因子组合过 `_learning_guard_active` | LEARNING type 仅型 → 守卫解除（验收②）；`learning_goal=True` / `user_core` / `human_required` 任一 → 守卫仍 True | 与 docstring/limitations §6 一致：子步学习信号必须投影为分配因子（Planner 职责），门不被目的声明单方解除 |

- **对抗观察（记录，非洞）**：策略块存在时**覆盖** type 推导——`type=LEARNING + user_core` 行（无块必 mastery）可被声明 `deliverable` 后经 agent 完成结算。写面 = `TaskCreate/TaskUpdate.guide_json`（user bearer，一审 C3 已核 agent 注册工具无 guide_json 块写路径）→ 这是用户显式选择通道（「交给 Sparkle」），非 agent 自升级。结算门/X-02 G1/G5 的守卫组合对 agent 单方面绕过依然封闭。

## D. 措辞与测试设计建议（不阻塞，销账时顺手）

1. limitations §9 补乘数从句：「N 个服务进程 → 3N 次/日/节点」（「进程级」已逻辑承载，逐字更防误读）。
2. `test_plan_turn_caps_*` 的循环次数 import 被测常量——常量级 mutation 使测试不可终止；建议循环数改字面量 5（与常量解耦后阈值 mutation 才可观测红）。
3. F4 服务端本体保留断言重调 `_guide_with_check()` 构造新 fixture——建议改为「同一对象投影后断言原对象未变」（纯函数不可变性直接入断言）。

## E. 移交项（对齐一审 §D 口径，销账前置条件已满足，以下为后续认领）

| # | 内容 | 来源 | 严重度 |
|---|---|---|---|
| R2-1 | F4 封闭键集可枚举绕开（本审查实测 `explanation`/`correct_option`/`grading.correct` 穿透）： containment 探针进 rule guard 或生产者 schema 校验（independent_check 子树只准冻结键） | C.3 | 低-中（生产者缺位压低） |
| R2-2 | 一审 N2 未处置（F1-F4 范围外，合理）：`settlement_for_task_row` 的 `_degrade` 仍被丢弃不落日志，schema_version 不符静默降 legacy；建议 degrade WARN + 未知版本从严（hybrid_policy 一行级硬化） | 一审 C6 注记 | 低 |
| R2-3 | 一审 N3 备忘维持：REST `/node/{id}/spark` 客户端自报 quiz 级 outcome 属既有信任模型（G-01 面），登记不动作 | 一审 N3 | 备忘 |

一审 N1 已由整改**闭合**（limitations §9 末段补入 spark 活动面边界数字：LEGACY_TIME_MASTERY_CAP=40.0 / effect_kind=PROJECTION / task_complete ∈ NON_EVIDENCE_REASONS）。一审 F2 双向 mutation 本审查独立复证：删内部集 REFLECTION → **红**；X-02 侧 +OCR → **红**；复原绿。

## F. 复跑结果（本会话独立执行）

`cd backend && SECRET_KEY=ci-test-key DATABASE_URL=sqlite://` 前缀，全部与整改申报计数一致：

| 面 | 结果 |
|---|---|
| `tests/unit/test_hybrid_policy.py` | **31 passed** in 29.70s（29+2，与 remediation §测试计数一致） |
| `tests/unit/test_aurora_runtime_decision_loop.py` | **93 passed** in 1.22s（91+2） |
| `tests/test_plan_task_tools_production.py` | **73 passed** in 18.75s（72+1） |
| X-02 三文件（policy/guard/eval） | **112 passed** in 1.00s |
| `tests/contract` 全量 | **352 passed** in 11.55s |
| chat 面 4 文件 | **21 passed** in 22.12s |

**质量门（零新增口径逐项核验）**：
- mypy（6 改动文件）：`Found 30 errors in 30 files` = 基线 30；named hit 仅 `action_allocation_policy.py:781` arg-type——与 base:713 **同一行代码**（`CognitiveOwnership(decision.recommended_cognitive_ownership)`），仅行移，**零新增**；
- ruff：6 改动 app 文件 + 新改测试文件 **All checks passed**；`test_plan_task_tools_production.py` 14 项既有（base 同文件亦 14），零新增；
- black（line-length 120）：`hybrid_policy.py` + 2 测试文件 clean；`task_tools.py`/aurora `service.py` 漂移在 base 同态（stdin 核验 `1 file would be reformatted`），增量行 `black --diff` 命中 **0**。

四项 mutation 全部 RED → 复原绿（F3 撤穿参 3 红；F1 撤守卫 1 红；F2 两方向各 1 红），工作树 clean。

## G. 合并落差（base 1063abb3 vs main @ `934b420c`，merge-base=1063abb3）

- main 自 base 新增 88 文件：I08（`runs.py`/`run_steps.py`/`agent_run_service.py`）、D03、CI36 契约修复、mobile/docs/证据/台账。**与本卡 10 个 backend 触达文件零交集**（`git diff --name-only` 交集为空）。
- I08 面核查：其三个文件**无** `TaskService.complete`/`update_node_mastery` 调用——I07 对 I08 的移交前提（「若引入新掌握写点必须过 settlement_for_task_row」）未被 main 现状违反；`settlement_for_task_row` 在 main 尚不存在（本卡未合并），无双重权威。
- `v4/04_tasks/tasks.json` 两侧均改（本卡 I07 条目状态行+source_anchors vs main 其他卡状态行）；`git merge-tree` 模拟 **0 冲突标记**，任务书行级可解判定的预判成立——**合并预期干净**。
- 一审 §E 对 origin/main @ 71553984 的预判被本次核验更新为：main 已进至 934b420c（I08/D03/CI36 落地），结论不变且更强（backend 零交集经 88 文件清单复核）。

## H. 裁决

**PASS**。一审 F1-F4 整改逐项核销：F3 穿参经独立 mutation 与调用点全查成立且 REST/focus/X-03 用户面零变化；F1 不接判定独立成立、封顶边界如实、WARN 实测不静默；F4 该剥判定成立且双侧口径守住；F2 双向防漂移经两方向独立 mutation 复证。三条验收的机制层在整改后经复跑与对抗探针维持成立（验收① agent 代完成 mastery 不冒记——经工具层穿参后在生产对话面真实可达；验收② deliverable 合法代办照常结算；验收③ 投影面答案剥除+判分权威保留）。无虚报：复跑计数、质量门基线、既有漂移描述逐项与申报一致。

CHALLENGED 项（R2-1/R2-2/R2-3 + §D 三条建议）均为补强性质，不构成验收失效，按 §E 认领即可。**双审齐（r1 PASS_WITH_CHALLENGES + r2 PASS），可按接力机制销账 DONE_REVIEWED**；集成 SHA 复验随合并执行。

—— wtI07R2，2026-09-28
