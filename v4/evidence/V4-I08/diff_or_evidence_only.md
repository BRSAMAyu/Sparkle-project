# V4-I08 · 深任务返回控制与恢复一致性 — 差量与证据

- 卡：`v4/04_tasks/cards/V4-I08.md`（implementation · high · 独立审查 2 位）
- 分支：`agent/v4/i08`（worktree wtI08，base = main @ `33dc2223`）
- 性质：**复用既有 X-05/06/07/09 run 脊柱与工具账本的最小增量，不是重建 Runtime**；零新表、零迁移、零 proto 变更、零模型调用、无 UI 面。
- 差量总计：3 个产品文件 + 1 个新测试文件，+169/−5 行。

## 0. 一句话设计

深任务复用既有 `agent_runs` run 脊柱（X-05 状态机 + X-07 hybrid steps + X-09 工具账本），本卡补四个最小缺口：**用户步答案封闭词表门**（ack 类自动回应永不算人类有效答案）、**取消/预算暂停/unknown 终态的副作用对账物化**（复用 X-09 `partial_completion_evidence` 入 `run.result_ref`，不建第二真源）、**未答人步的成功终态伪造守卫**（AWAITING(user_step) → SUCCEEDED/PARTIAL 服务层钉死）、**5s 返回控制 deadline 常量与超时钉死测试**。

## 1. 现状盘点（哪些已满足——只举证，不重写）

I08 三条验收的大部分行为**在 base SHA 已存在**（X-05/X-06/X-07/X-09 各卡已落，回归测试见 §4 第 3 条命令）：

| 验收面 | 既有权威（base 已满足） | 证据 |
|---|---|---|
| 查看当前阶段产物 | `GET /runs/{id}` → `to_dict()`：`current_stage` + `steps` wire（含 `awaiting.prompt/artifacts`）+ `awaiting_step` 推导投影 | `run_steps.py::awaiting_step_projection`（既有） |
| 取消/离开 | `POST /runs/{id}/cancel`（幂等、归因白名单）+ 下游 intent 传播；离开后冷启动经持久态 + `episode_resume_view.v1`（I01）恢复 | `runs.py::cancel_run`（既有） |
| 重启/断网不双写 | `recover_inflight_runs` + `reconcile_stale_in_progress`（账本收敛单向）；transition FOR UPDATE+复查幂等；`(run_id, idempotency_key)` 审计唯一键 | `agent_run_service.py`（既有）+ `test_x09_failure_recovery.py` |
| 人类步骤显式等待 | `await_user_step`（AWAITING_USER + wait_kind=user_step + wait_expires_at）；`complete_agent_step` owner 纪律（Agent 不得完成 human 步） | X-07 既有 + 既有测试 |
| 预算终态 | `enforce_budget` → BUDGET_EXCEEDED（四维、审计+事件同事务） | X-06 既有 |

## 2. 本卡真实缺口与增量（对齐验收逐条）

### 验收 1「5s 内可查看/取消/离开；ack 不算有效答案」

- **缺口 1a（ack 门）**：`complete_user_step` 的 `action` 在服务层是自由串（仅截断 32 字符；API pattern `^(confirm|edit)$` 只守 wire 面而服务层是权威，hybrid journey 经服务层用 `decide`）——ack 类自动回应（传输/通知层确认标记）若被客户端当 action 提交，会被盖完成戳、**当作人类有效答案记账**。B05 合同 §9 反例「WS MessageAck：传输层确认，不证明业务 committed」在步骤面无落实。
  - 增量：`run_steps.py` 新增封闭词表 `USER_STEP_ANSWER_ACTIONS = {confirm, edit, decide}` 与冻结反例集 `ACK_CLASS_ANSWER_MARKERS`（ack/acked/acknowledge/acknowledged/acknowledgement/acknowledgment/received/read/seen）+ 纯函数 `normalize_user_step_action`（fail-closed：ack 类**显式点名拒绝**，不静默转写为 confirm）；`agent_run_service.py::complete_user_step` 取行锁前调门，新类型化错误 `InvalidUserStepAnswerError`（RunStateError 子类，API 422 显式映射）。
  - 可失败性：删掉 normalize 门 → `action="ack"` 会过 `step_completion_stamped`（只截断）→ `test_ack_action_cannot_complete_human_step` 在 `pytest.raises` 处红。
- **缺口 1b（延迟钉）**：查看/取消路径无任何延迟上限断言。
  - 增量：命名契约常量 `DEEP_TASK_RETURN_DEADLINE_SECONDS = 5.0`（agent_run_service，注明 LATENCY_COST_RUNTIME「深任务」节出处）；测试用 `asyncio.wait_for(..., timeout=常量)` 钉死查询与取消路径（超时即测试失败）+ 常量 `<= 5.0` 防静默放宽 + 跨用户 404 隔离面同 deadline。

### 验收 2「重启/断网/重试不双写，取消后外部副作用如实对账」

- **缺口 2a（取消不对账）**：用户取消路径 `AgentRunService.cancel` 直接落 CANCELLED，**不物化任何副作用对账**——深任务已发出的外部请求（succeeded 写效果工具调用）在 run 面不可见，呈现为「干净取消」＝假装回滚。X-09 的对账证据机制（`partial_completion_evidence`）只接在执行失败漏斗 `terminalize_execution_failure`，用户主动取消面没接。
  - 增量：新私有方法 `_side_effect_reconciliation(run)`——复用 X-09 既有账本证据（**不建第二真源**）：无账本行 → None（不造空证据）；run 已有 result_ref（如 journey 产物引用）→ None（不覆盖既有引用，账本仍可经 `GET /runs/{id}/tool-calls` 审计）；否则 `evidence.to_result_ref()`（scheme=partial_completion：succeeded/failed/interrupted 明细 + compensation_hints 含不可逆警示 + durable_progress）。接入 `cancel`（幂等：已 CANCELLED 早退，首次取消才物化）。
- **缺口 2b（恢复双写钉）**：inflight 恢复两轮的 run 级不双写（迁移/事件计数不变、账本 `already_resolved`、终态 `terminal_noop`）此前无显式测试钉。
  - 增量：`test_inflight_recovery_twice_no_double_write`（反例面）；`test_cancel_double_fire_single_transition_single_event`（取消重试恰一次迁移/一个事件、证据 first-wins 不重算）。

### 验收 3「人类步骤等待，不由 Agent 伪造完成；预算暂停与 unknown 终态显式对账」

- **缺口 3a（run 级伪造边）**：封闭迁移图允许 `AWAITING_USER → SUCCEEDED/PARTIAL`（合法边），`transition` 是唯一写入口——任何 worker/system/recovery/projection 直接调 transition 都能在人步**无完成戳**时把 run 落成成功类终态（步骤级 owner 纪律挡不住 run 级绕过）。
  - 增量：`transition` 内新增守卫：current ∈ {AWAITING_USER, AWAITING_APPROVAL} 且 `wait_kind=user_step` 且存在未完成步骤且 target ∈ {SUCCEEDED, PARTIAL} → `HumanStepNotCompletedError`（RunStateError 子类，API 409 经既有 ValueError 映射）。**图零改动**（不 bump 状态机版本、不加边）；诚实完成路径不受影响（`complete_user_step` 完成戳+resume 同事务后再终态化，hybrid journey `confirm_outcome` 流同构）；失败漏斗的 PARTIAL 升格若撞未答人步由其既有 `except ValueError` 收敛为 no-op（诚实：未答人步不允许成功类终态宣告）。wait_kind=approval 不守（approval 流走 intent 轨道真源，漂移修复需保留）。
  - 可失败性：守卫条件针对的边在 `ALLOWED_RUN_TRANSITIONS` 图内（冻结测试可证）——删守卫则 `test_no_path_succeeds_run_over_unanswered_human_step`（5 actor × 2 target 参数化）在 `pytest.raises` 处红。
- **缺口 3b（预算暂停/unknown 不对账）**：`enforce_budget` 落 BUDGET_EXCEEDED、sweep/inflight 落 UNKNOWN_OUTCOME 均不带副作用证据——「预算暂停」与「结局未知」都不呈现已发生的外部写。
  - 增量：`_side_effect_reconciliation` 同法接入 `enforce_budget`（BUDGET_EXCEEDED）与 `_terminalize_budget_exceeded`（resume 闸门）、`recover_stale_runs` 两处孤儿→UNKNOWN_OUTCOME 分支、`recover_inflight_runs` →UNKNOWN_OUTCOME；审计 details 带 `side_effect_reconciliation` 标记。

## 3. 不做的事（边界）

- 不重建 Runtime / 不加第二套 run 真源 / 不动 ExecutionIntent 状态机 / 不动 OpenClaw 适配器（深任务的执行器协议面已由 X-05 投影覆盖）。
- 不扩/改 proto，不加迁移（`agent_runs.steps`/`result_ref`/审计 details 均为既有 JSONB 列的既有形状内使用）。
- 不动 `episode_resume_view.v1`（I01 权威；本卡守卫保证 pending 人步不被伪造清除，resume 视图语义零改动）。
- API `RunStepCompleteRequest.action` wire pattern（confirm|edit）不扩（decide 走服务层是 journey 既有路径；扩 wire 面属契约变更，非本卡必需）。

## 4. 运行证据

命令、exit code、版本、受影响面分母见 `run_manifest.json` 与 `test_results.json`。要点：

1. 新契约测试 `tests/unit/test_v4_i08_deep_task_return_control.py`：**24 passed**（每验收面一正一反）。
2. 受影响面回归（12 文件，含 X-05/06/07/09、hybrid journey、runs API、wt392 复验）：**273 passed**。
3. `ruff` / `black`：改动 4 文件 All checks passed / unchanged。
4. `mypy app --ignore-missing-imports`：55 条 vs 基线 `quality/mypy_baseline.txt` = 77（零新增；改动三文件 grep = 0 条）。
5. `bash scripts/run_all_rule_guards.sh`：**86 rules 全过**（BG 初跑 FAIL 为 worktree 缺 proto 生成产物的环境缺项——从主检出复制 gitignored 生成产物后 PASS，本卡零 proto 变更；与 I01 run_manifest 同样记录）。

## 5. 审查挑战点预登记（预答辩，不代替审查）

1. **ack 词表封闭性**：`ACK_CLASS_ANSWER_MARKERS` 是冻结反例集而非启发式——挑战点：是否有漏语的 ack 变体（如 locale 化「收到」）？答：文本语义归类属模型/客户端层，服务端只钉结构化 action 字段位；`USER_STEP_ANSWER_ACTIONS` 是 allowlist，任何未列值（含中文串）都被拒——fail 方向是「宁可拒了再答一次」，不吞答案。
2. **伪造守卫的 approval 豁免**：wait_kind=approval 不守——理由：approval 流的终态真源在 intent 轨道（`INTENT_STATUS_TO_RUN_STATUS` 投影/漂移修复），守死会把 intent 已终态的诚实修复堵死；user_step 面才有「轮到用户」语义。审查可挑战 hybrid 场景是否需要 approval 面同守（登记为后续可靠性候选，不在本卡夹带）。
3. **对账证据不覆盖既有 result_ref**：run 已有 result_ref 时对账不物化（防覆盖 journey 产物引用）——挑战点：这会不会丢账？答：账本行永不删除，`GET /runs/{id}/tool-calls` 恒可审计；result_ref 是 run 面物化投影而非唯一账面。
4. **PARTIAL 升格撞守卫的收敛**：失败漏斗在人步未答时升格 PARTIAL 会被守卫挡回（except 收敛 no-op，run 保持等待直至 sweep 过期）——语义选择：未答人步连「部分成功」都不宣告；审查可挑战是否过严。
