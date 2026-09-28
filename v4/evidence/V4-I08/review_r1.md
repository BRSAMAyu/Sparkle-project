# V4-I08 一审 receipt（独立审查 R1）

- **审查会话**：wtI08R1（未参与 I08 实现）
- **审查对象**：branch `agent/v4/i08`，HEAD `aeca1bb6`（实现 SHA `23fe2c9c`，base `33dc2223`）
- **审查日期**：2026-09-28
- **方式**：只读审查 + 独立复跑 + 对抗性亲测（探针测试 7 例临时置于 worktree 跑完即删，终态不入库；本 commit 仅新增本 receipt）
- **总裁决**：**PASS_WITH_CHALLENGES（一审通过）**。CHALLENGED：**1 项（C-1，approval 豁免面无 intent 向量——可构造、不阻塞本卡、登记后续候选）**。观察项 2 条（O-1/O-2）。

## 复跑记录（本会话独立执行，非转录）

| 面 | 命令要点 | 结果 |
| --- | --- | --- |
| 新契约测试 | `pytest tests/unit/test_v4_i08_deep_task_return_control.py -q`（SECRET_KEY=ci-test-key DATABASE_URL=sqlite://，共享 venv 3.11.15） | **24 passed**（8.69s） |
| 受影响面 12 文件 | 与 run_manifest 同组合（X-05/06/07/09、hybrid steps+API、runs API×2、journey、状态机冻结、步骤投影、wt392） | **273 passed**（183.50s） |
| mypy 棘轮 | `mypy app --ignore-missing-imports` 全量 \| grep -c 'error:' | **55 ≤ baseline 77**；全量输出 grep 三个改动产品文件 = **0 条** |
| ruff / black | 4 改动文件 | **All checks passed / 4 files unchanged** |
| rule guards | `bash scripts/run_all_rule_guards.sh`（同 env） | **86 rules 全过，exit 0** |

## 逐靶判定

### 靶1｜验收①：5s 钉 + ack 门 — **PASS**

- **5s 口径一致性**：`DEEP_TASK_RETURN_DEADLINE_SECONDS = 5.0`（`agent_run_service.py`，注明 LATENCY_COST_RUNTIME 出处）；测试以 `asyncio.wait_for(timeout=常量)` 钉死查询（`get_run().to_dict()`：current_stage/steps_done/awaiting prompt+artifacts 一次可见）与取消两条服务路径 + `常量 <= 5.0` 防静默放宽 + 跨用户 404 同 deadline。**声明与断言口径一致**：limitations §1 诚实声明这是服务路径可测钉、非端到端实测——卡验收按服务层可失败面解释成立，「离开」路径为零交互（持久态+I01 视图），无可钉延迟面，声明未夸大。
- **ack 变体亲测（3+ 条，超出要求）**：构造 run（agent 步完成、human 步 await）后经 `complete_user_step` 真实通道提交——`好的`/`收到`/`嗯嗯` **全被拒**（`InvalidUserStepAnswerError`），且断言：无完成戳、run 保持 AWAITING_USER、投影仍 awaiting。阳性对照：同法 `action="confirm"` 合法通过、完成戳+resume 恰一次。
- **词表外方向 = fail-closed**：`yes`/`approve`/`同意`/`OK`/`  Ack  `（大小写+空白）全部拒绝；`ACK` 命中 ack-class 显式错误，locale 化中文命中 out-of-vocabulary——**无一条被静默转写为 confirm**。预登记①的「漏语」挑战结构性无虞：`USER_STEP_ANSWER_ACTIONS` 是封闭 allowlist，任何未列值（含一切 locale 化 ack）本就被拒；`ACK_CLASS_ANSWER_MARKERS` 只影响错误消息的显式点名，漏语代价 = 错误消息变泛、拒收方向不变。方向是「宁可拒了再答一次」，不吞答案。
- **API 面**：`InvalidUserStepAnswerError → 422` 显式映射已落 `runs.py`；wire pattern `^(confirm|edit)$` 未扩（decide 走 hybrid journey 服务层既有路径，`hybrid_journey_service.py:687` 核实）——服务层是权威，与声明一致。

### 靶2｜验收②：不双写 + 对账 — **PASS**

- **幂等**：cancel 双发恰一次迁移、恰一个 `run.status_changed` 事件、不写第二行审计、证据 first-wins（复跑绿）；底层 `transition` FOR UPDATE + `current is target → no-op` 早退（守卫/物化均在锁内复查之后）。
- **对账物化三面齐**：cancel / `enforce_budget`+resume 闸门（BUDGET_EXCEEDED）/ `recover_stale_runs` 两处 orphan→UNKNOWN_OUTCOME / `recover_inflight_runs` 全部接 `_side_effect_reconciliation`；审计 details 带 `side_effect_reconciliation` 标记。无账本行不造空证据（复跑绿）。
- **「不覆盖既有引用」亲测（预登记③丢账疑虑）**：预置 `result_ref={"scheme":"journey_artifact","ref":"artifact-9"}` + 账本 succeeded 写效果行 → cancel applied 后 **result_ref 原样保留未被覆盖**；同 run 账本行经 `ToolCallLedgerService.list_tool_calls_for_run`（即 `GET /runs/{id}/tool-calls` 数据面）**恒可审计**。丢账疑虑不成立：账本行是唯一账面、永不删除，result_ref 是 run 面物化投影——与声明逐字相符。
- **对账异常方向**：`_side_effect_reconciliation` 吞异常只 WARN 返 None——终态化不被证据故障阻塞，账本仍在，方向性已被 review_anchors 预登记，接受。

### 靶3｜验收③：人不被伪造 — **PASS**

- **参数化面核实**：`test_no_path_succeeds_run_over_unanswered_human_step` 为 5 actor（worker/system/recovery/projection/user）× 2 target（SUCCEEDED/PARTIAL）= 10 组合，含在 24 内全绿。
- **抽 2 组亲跑（不同 actor 串）**：`orchestrator_worker→SUCCEEDED`、`hybrid_journey→PARTIAL` 均 `HumanStepNotCompletedError`，等待态与事件面零变化。
- **守卫位置**：锁内、`assert_transition_legal` 之后——`AWAITING_USER→SUCCEEDED/PARTIAL` 是 `ALLOWED_RUN_TRANSITIONS` 冻结图内合法边（可失败性成立：删守卫必红）。诚实路径不受挡：显式作答后 RUNNING→SUCCEEDED 合法（复跑绿）；取消/过期（TIMED_OUT/CANCELLED）不在守卫 target 内。
- **过严疑虑（预登记④）边界实测**：构造人步未答 + 账本写效果已发生的 run，走 `terminalize_execution_failure`（FAILED 分类 + durable_progress → 升格 PARTIAL 路径）——实测**收敛 no-op**，日志 `failure terminalization converged ... PARTIAL is unreachable until the human step is answered`，run 保持 AWAITING_USER 直至 sweep 过期兜底。`RunStateError(ValueError)` 继承已核实（`run_state_machine.py:124`），`except ValueError` 收敛声明成立。判定：这是声明过的有意保守（未答人步连 PARTIAL 都不宣告），代价是终态化迟到且有 sweep 兜底——**非缺陷，接受**。

### 靶4｜状态机零改动 — **PASS**

`git diff 33dc2223..23fe2c9c -- backend/app/core/run_state_machine.py` = **0 行**；全分支 diff 仅 4 产品文件 + tasks.json + 证据文件。不 bump 版本、不加边、不删断言。

### 靶5｜复用而非重建 — **PASS**

- `_side_effect_reconciliation` → 委托 `ToolCallLedgerService.partial_completion_evidence` / `to_result_ref`（X-09 权威，零复制逻辑、无第二证据结构）；
- 词表门落 `run_steps.py`（X-07 步骤契约模块）并入 `__all__` 导出；
- 伪造守卫落 `transition` 单一写入口（X-05 脊柱），非旁路补丁；
- grep 全服务层：`partial_completion_evidence` 消费者 = terminalize_execution_failure（X-09 既有）+ 本卡 `_side_effect_reconciliation`，无第二 run 真源、无第二账本。

### 靶6｜approval 豁免面 — **CHALLENGED（C-1：向量已构造）**

- **探针实测**：worker actor 直调 `transition` 三步链 `RUNNING → AWAITING_APPROVAL → SUCCEEDED`（**无 intent 绑定、无任何 approval 动作**）→ **applied=True，run 落 SUCCEEDED/completed**。
- **无自愈**：`_intent_drift_target` 对 `intent_id is None` 恒返 None；终态 run 不再进 sweep 扫描面——伪造成功**永久成立**，预登记②的辩护理由（「终态真源在 intent 轨道漂移修复」）**只对有 intent 绑定的 run 成立**，对无 intent run 无修复路径。
- **边界评估（为何不阻塞本卡）**：(a) 向量需在 Python 引擎信任边界内直调 `AgentRunService.transition`——runs API **无通用 transition 端点**（仅 create/resume/cancel/steps×4/agent-complete/recover），无 wire 直达面；(b) approval 面行为相对 base **零变化**（本卡只收窄 user_step 面，未放宽任何面）；(c) 预登记已声明此为后续可靠性候选、不在本卡夹带；(d) 同构向量在 user_step 面本卡已封闭，证明该修复模式可行且低成本。
- **登记要求**：建议后续可靠性卡为 approval 等待面加同构守卫（或要求 AWAITING_APPROVAL run 必须有 intent 绑定校验）。**本卡不夹带，一审不因此否决。**

### 靶7｜复跑 — **PASS**（见复跑记录表；mypy 口径注意：以 3 个改动文件为**入口**跑 mypy 会报依赖侧 30 条，正确口径 = 全量 `mypy app` 后 grep 文件名 = 0 条，manifest 采用的后者正确）

### 靶8｜合并落差 — **PASS（无产品交集）**

- main 自 base `33dc2223` 已前移至 `1063abb3`（并入 I06/I03/D02/FIX-559）——I08 的 4 个产品文件（`run_steps.py`/`agent_run_service.py`/`runs.py`/测试）在 main 侧**零变更**，无冲突面。
- D03 分支（`agent/v4/d03`）现无独立实现提交、与 run 面零交集；tasks.json 双侧修改按舰队惯例集成时处理。
- 小注：run_manifest 记录「main 已前移至 150bc205」为证据时点快照，审查时 main 已再前移——结论不变（见 O-1）。

## CHALLENGED / 观察项汇总

- **C-1（CHALLENGED）**：approval 豁免面对无 intent 绑定的 run 存在可构造伪造向量（详见靶6）——不阻塞本卡，登记后续可靠性候选；集成审查时应确认该登记进入任务池。
- **O-1（观察）**：run_manifest 的 main 前移快照（150bc205）已过时（现 1063abb3），属证据时点差异非失实；集成 SHA 复验时以届时 main 为准。
- **O-2（观察）**：词表外合法语义的是/否类答案（"yes"/“同意”）会被 422 拒绝——有意 fail-closed（宁可拒了再答），但客户端作答 UX 需按封闭词表对齐（confirm/edit/decide），消费面（B05 合同/网关透传层）应知悉该契约。

## 诚实性抽查

- 「5s」未被表述为端到端实测（limitations §1 明确服务路径口径）——符合 AGENTS 纪律。
- honest_failures 三条（测试断言写错自修、guards 环境缺项、mypy 54/55 差异）如实登记，未发现粉饰。
- LLM usage=0、无 UI 面声明与 diff 事实一致（纯 backend 服务层+测试）。

## 裁决

**PASS_WITH_CHALLENGES**：三条验收全过、状态机零改动属实、X-05/06/07/09 复用关系属实、静态与守卫全绿；C-1 为预登记豁免面的已构造向量（零变化面+信任边界内+已声明候选），不阻塞一审通过。双审齐后按舰队验收模型在集成 SHA 复验（届时重点：C-1 登记入池 + O-1 时点口径）。
