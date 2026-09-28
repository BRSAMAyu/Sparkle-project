# FIX-560 修复回执 — approval 等待态源头 intent 门（无解除通道的死态逐源拒绝）

日期：2026-09-28 ｜ 分支：`agent/v4/fix560`（worktree `wtF560`，基于 main@d46fe337）｜ 台账：V3-FIX-560（P2，I08 双审 C-1 升格）

## 1. 向量（I08 双审 C-1，独立复现见 v4/evidence/V4-I08/review_r1.md C-1 + review_r2.md 靶1）

- `AgentRunService.transition` 是 run 状态机唯一写入权威（引擎信任边界内）。直调三步链
  `RUNNING → AWAITING_APPROVAL → SUCCEEDED`（无 intent、无任何 approval 动作）修复前 `applied=True`
  且无自愈：`_intent_drift_target` 对 `intent_id=None` 的 run 恒 `None`（agent_run_service.py 漂移判据首行），
  恢复 sweep 只剩 wait_expired→TIMED_OUT / 孤儿→UNKNOWN_OUTCOME 兜底，伪造的「审批暂停」审计行永不纠正。
- 危害面：伪造等待态既为审批豁免提供掩盖审计，又属死态——approval 等待的解除通道是 intent 状态漏斗
  （approve/reject 经 execution_service 变更 intent → `project_intent_status` 投影），无 intent 绑定就没有任何解除通道。
- in-tree 生产者盘点（修复时 grep 全仓复核）：生产代码唯一 AWAITING_APPROVAL 生产者是
  `project_intent_status`（run 即由 intent 查找/创建，天然绑定）；`create_run(initial_status=…)` 非守卫面
  （X-05 迁移图允许，仅投影传入且携 intent_id）；API 层零直调。向量需**未来调用方误用**才成活——本修把误用
  钉死在源头。

## 2. 修法（R2 建议 b 案，已入台账；未被实现事实否决）

**transition 进入 AWAITING_APPROVAL 时要求 `run.intent_id` 非空**，逐源头拒绝（任何 actor）：

- 唯一改动点 `backend/app/services/agent_run_service.py`：
  1. 新增 `ApprovalWaitRequiresIntentError(RunStateError)`——与 I08 的 `HumanStepNotCompletedError` 同族
     （ValueError 子类 → API 层 409 同映射先例）；
  2. `transition()` 在 `assert_transition_legal` 之后（图判定优先：`AWAITING_USER→AWAITING_APPROVAL`
     禁边仍先抛 `IllegalRunTransitionError`，错误族不变）、状态落库之前插守卫：`target is AWAITING_APPROVAL
     and run.intent_id is None` → 拒绝，错误信息写明「无 intent 的 approval 等待无解除通道，属死态」。
- 择 b 案（逐源头拒）而非 a 案（出边守卫 AWAITING_APPROVAL+intent_id None→SUCCEEDED/PARTIAL 拒）的理由：
  台账/R2 既定；且实现复核支持——死态的危害不限于伪造成功（死等 6h 才被判孤儿同样是病），从入口杜绝优于
  在出边逐个补洞。**无保守替代启用**。
- 图零改动：`ALLOWED_RUN_TRANSITIONS` / `RUN_STATE_MACHINE_VERSION` / 冻结 sha 均不变；守卫形态与
  I08 user_step 守卫同构（服务层钉死，actor 无关）。
- 意外影响面（诚实记录）：盘点发现 **X-10 harness GJ06 分支**（`tests/v3_action_eval/executors.py`）是树内
  唯一无 intent 直调 transition 进 AWAITING_APPROVAL 的调用方（测试侧仿真，非生产代码；pytest 套件不执行
  GJ06，仅 CLI 全量轮会走到）。按执行轨道生产真实形状修 harness：GJ06 先落真实 `ExecutionIntent` 行
  （FK 硬约束，随机 UUID 不可行）再绑定 `create_run(intent_id=…)`；GJ07（user-step 交棒）无需 intent，不动。
  判定器（verdicts.py）按 DB 审计行断言 `approval_gate_visited`，不受影响。

## 3. 验证（本机实跑，SECRET_KEY=ci-test-key DATABASE_URL=sqlite://）

| 面 | 结果 | 备注 |
|---|---|---|
| 新契约测 `tests/unit/test_v4_fix560_approval_intent_gate.py` | **10 passed** | 反例×3（5 actor 参数化无 intent 入口拒 / QUEUED 入口拒 / 原三步链第二步即断+无审计行无事件）、正例×2（intent 绑定合法链含 resume 解除+终态化 / project_intent_status 唯一生产者照常）、图优先×1；变异红证见 §4 |
| I08 双审 24 契约测 | **24 passed** | 守卫不误伤合法路径（user_step 守卫全绿） |
| 受影响面 20 模块 sweep（agent_run_service 及全部 import 方：agent_run_service / run_state_machine / run_step_projection / run_projection_consumer / hybrid_run_steps(+api) / runs_api(+hardening) / x05b / x06 / x07 / x09(+e2e) / j06 / o07 / action_command / execution_run_producer / event_bus_first_deploy / wt392 / i08 / fix560） | **254 passed, 4 skipped** | skip 全为环境性（Redis 认证不可用，pre-existing） |
| X-10 gate 套件 `tests/v3_action_eval/test_x10_action_eval_gate.py` | 12 passed（含 GJ07 真实端到端抽检） | worktree 缺 gitignored `app/gen/`，从主检出 symlink 后实跑（symlink 不入库） |
| GJ06 场景 CLI 实跑 `journey_gj06_agent_approval_run_receipt` | **verdict=pass** | 修后 harness 审批门链 RUNNING→AWAITING_APPROVAL(intent 绑定)→resume(EXECUTING) 全通 |
| ruff | 与 main 基线逐项持平 | 改动文件 0 违规；executors.py 19=19（同分布，全 pre-existing），无新增 |
| black | 改动文件 clean；executors.py 重排 diff 不触及新增块 | executors.py 在 main 本就 would-reformat（pre-existing） |
| mypy | 计数持平、行号平移 | service 30=30（30 files）；executors 23=23（逐行比对仅为插入位移）；新测试文件 0 |

## 4. 变异红证（守卫本体失效 → 契约测必红）

将守卫条件改为 `if False and …`（保留异常类，隔离守卫本体）后重跑新契约测：
**7 failed / 3 passed**（3 个通过面恰为不依赖守卫的正例/图优先）。恢复后 10/10 全绿。

## 5. 产物 diff 摘要

- `backend/app/services/agent_run_service.py`：+异常类（8 行）+守卫块（17 行，含注释）；零删改既有逻辑。
- `backend/tests/unit/test_v4_fix560_approval_intent_gate.py`：新增契约测（10 用例）。
- `backend/tests/v3_action_eval/executors.py`：GJ06 分支 intent 绑定（+34 行；import 归序满足 isort）。
- `v3/06_agent_fleet/DYNAMIC_ISSUES.md`：V3-FIX-560 行 OPEN → FIXED@<fix sha>（state 提交）。
- 图/契约冻结物零触碰：`run_state_machine.py`、迁移图 sha、D-01 词表、proto 均未动。

## 6. 残留与边界

- `create_run(initial_status=AWAITING_APPROVAL)` 不在本守卫面（非 transition；全仓仅投影调用且携 intent_id）。
  若未来出现绕过投影的初始等待建档需求，应先扩契约再放行——不在本卡扩面。
- 用户 `resume()` 对 approval 等待的解除语义（自批面）属 R2-2/R2-3 低优先随账项，本卡不扩审。
