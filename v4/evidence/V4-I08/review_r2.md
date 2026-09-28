# V4-I08 二审 receipt（独立审查 R2）

- **审查会话**：wtI08R2（未参与 I08 实现与一审）
- **审查对象**：branch `agent/v4/i08`，一审 receipt commit `653d3e0b`（实现 SHA `23fe2c9c`，base `33dc2223`）——一审材料已读但独立下判
- **审查日期**：2026-09-28
- **方式**：只读审查 + 独立复跑 + 恢复对抗面探针亲测 11 例（临时测试文件置于 worktree 跑完即删，终态不入库；本 commit 仅新增本 receipt）
- **总裁决**：**PASS_WITH_CHALLENGES（二审通过，与一审裁决一致）**。CHALLENGED 合计 **2 项**：C-1（一审已构造，本审独立复核维持）+ **C-2（本审新增：取消撞 in-flight 写时 run 面对账证据把 in_progress 误标为 failed）**。观察项复核 2 条（O-1 时点更新 / O-2 维持）。

## 二审靶逐条判定

### 靶1｜C-1 approval 豁免向量独立裁决 — **向量成立，维持 CHALLENGED（不阻塞）**

- **API 面不可达声明复核（独立清点）**：runs API 全端点 = list/get/transitions(只读审计)/tool-calls/create/resume/cancel/steps×3(记录/计划/await)/complete/agent-complete/recover——**无通用 transition 端点**；`GET /runs/{id}/transitions` 是只读审计投影；`POST /runs/recover` 内部只落 UNKNOWN_OUTCOME（非任意 target）；网关 `/runs` 是通用 auth 代理（`registerREST`），无 transition 透出面。wire 不可达**属实**。
- **向量独立构造（亲测）**：无 intent 绑定 run 经 `RUNNING → AWAITING_APPROVAL`（默认落 `wait_kind=approval`）→ `transition(SUCCEEDED, actor=worker)`，**零 approval 动作、零 intent → applied=True，run 落 SUCCEEDED**。独立复现一审结论。
- **无自愈亲测**：伪造终态后心跳回拨 2h 跑 `recover_stale_runs` → 该 run 零 action（终态不进 sweep）；`recover_inflight_runs` → `terminal_noop`；`_intent_drift_target` 对 `intent_id is None` 恒 None（代码核）——伪造成功**永久成立**。
- **豁免精确性亲测**：`wait_kind=user_step` 的 run 处于 AWAITING_APPROVAL（显式 wait_kind 覆盖构造）时守卫仍挡（`HumanStepNotCompletedError`）——豁免面精确等于 `wait_kind=approval`，不是整个 AWAITING_APPROVAL 状态。
- **approval 无 run 级解除通道（结构性佐证）**：`complete_user_step` 对 approval 等待显式拒绝——approval 等待的合法解除只能走 intent 轨道投影；grep 全树证实 **AWAITING_APPROVAL 的 in-tree 生产者只有 `project_intent_status`（强制 intent 绑定）**，当前不存在无绑定 approval 等待的合法制造者。向量需未来调用方误用直调 transition 才成活。
- **独立处置建议（入池登记）**：同意一审「登记后续可靠性卡，本卡不夹带」。登记内容建议取**更根本的 (b) 案**：直调 `transition` 进入 `AWAITING_APPROVAL` 时要求 `intent_id` 非空（无 intent 的 approval 等待没有解除通道、属构造死态，逐源头拒绝优于出边守卫）；保守替代 (a) 案：`AWAITING_APPROVAL + intent_id is None → SUCCEEDED/PARTIAL` 拒绝（保留 intent 绑定 run 的漂移修复通路）。两案均 ~10 行 + 反例测试，模式与 I08 user_step 守卫同构（可行性已被本卡证明）。理由重述：信任边界内、零 wire 面、零 in-tree 生产者、approval 面行为相对 base 零变化——不阻塞本卡，但入池前该豁免是图能力上的敞口。

### 靶2｜恢复对抗面（乱序/duplicate/崩溃窗口） — **PASS（全部亲测，无双写）**

- **重启中途 cancel（run 终态化与 intent 传播间崩溃窗口）**：intent 绑定 run 取消后（`user_cancelled`），迟到终态投影（intent 侧已 succeeded）→ `converged to existing terminal` no-op；迟到非终态投影（复位假象）→ `refuses resurrection`（`user_cancelled` 在 NON_RESURRECTABLE）——**无双终态、无复活、迁移/事件计数不变**。
- **重试撞 sweep 双向**：cancel 先落 → sweep 跳过终态 run、`user_cancelled` 归因不被覆盖；sweep 先判 UNKNOWN_OUTCOME → 后到 cancel 得 `IllegalRunTransitionError`（cancel endpoint 已有 409 映射，核实）、归因保持 `worker_restart_orphan`。两向均恰一次迁移/一个事件。
- **断网重连 duplicate transition**：同 key 重试、换 key 重试均 no-op（终态早退 + FOR UPDATE 复查）；迟到 resume 撞 CANCELLED → 拒绝（终态无出边 + 不可复活词表）。无第二审计行、无第二事件。
- 判定：恢复乱序面**不双写、不复活、归因不被覆盖**，与验收②一致。

### 靶3｜预算暂停语义 — **PASS（附口径注记）**

- **终态性质亲测**：BUDGET_EXCEEDED 是**终态**（封闭图无出边）——「预算暂停」是命名习惯，resume **不可原位恢复**（探针拒绝）；**暂停恢复后 run 的去向 = 新 run**（新 attempt、独立预算面亲测成立），原 run 终态留档、对账证据不被扰动。
- **与 unknown 终态区分度**：`budget_exceeded`（terminal_reason + error_category 双载）vs `worker_restart_orphan`（terminal_reason 载、error_category **None**）——靠 terminal_reason 可区分。**口径注记（本审观察）**：sweep 的 orphan 分支不设 error_category，与 `recover_inflight_runs` 分支（设 `unknown_outcome`）不一致——X-05 既有形状、非本卡引入，不阻塞；后续可靠性卡可顺手对齐。
- 两类终态均带 `_side_effect_reconciliation` 物化（`budget_exceeded` 维度名入审计 details、`side_effect_reconciliation` 标记亲测在），语义分离清楚：预算=「钱花完且已写的如实」，unknown=「结局不可核实且已写的如实」。

### 靶4｜5s 契约边界如实性 — **PASS（附措辞 nit）**

- 设计原文核对（`v4/03_intelligence/LATENCY_COST_RUNTIME.md:7,12`）：「**以上是目标**，需按网络、模型、硬件报告，失败就保持未通过」「run卡5s内**应**可查看真实范围、取消、离开」——设计自身即目标语气，非实测承诺。
- I08 证据链无整链宣称：常量注释钉的是 GET/POST **服务路径**（括号内明示）；`limitations.md §1` 明示「服务层可测面钉死，非端到端实测」「不得将 5s 表述为已实测整链成绩」。**没有把 5s 说成整链的风险表述——如实性成立**。
- 措辞 nit（不阻塞）：常量 docstring「三条路径的**界面响应上限**」若脱离上下文可被误读为 UI 层承诺——已被同句括号（GET /runs、POST /runs/{id}/cancel 服务路径）与 limitations §1 圈住；网关（通用 auth 代理）与 Flutter 渲染侧耗时面未测且未宣称。集成材料引用该常量时建议沿用「服务路径口径」措辞。

### 靶5｜X-09 复用边界：取消撞 in-flight 写 — **CHALLENGED（C-2，本审新增，不阻塞）**

- **亲测构造**：run 有 1 条 succeeded 写行 + 1 条 **in_progress** 写行（写工具在途）时取消 → `result_ref` 物化为 `succeeded=1, failed=1, interrupted=0`——**in_progress 行被 `build_evidence` 落入 failed 桶**，无补偿提示、不计入 durable_progress。可能已落地/未落地的写效果在 run 面呈现为「失败」，诚实标签应是 X-09 自己的崩溃语义「interrupted / outcome unknown（不可核实）」。
- **误标持久性亲测**：恢复 pass 事后把账本行收敛 `interrupted`（真值修正、账本权威面不失真、`GET /runs/{id}/tool-calls` 恒可审计——探针验证），但 run 面 `result_ref` **first-wins 不重算**（`interrupted_steps=0, failed_steps=1` 恒保持）——误标投影终身驻留。
- **归因（为何不阻塞）**：桶化是 X-09 `build_evidence` **既有语义**（`terminalize_execution_failure` 同暴露，非本卡新引入）；`recover_inflight_runs` 路径因先跑 `reconcile_stale_in_progress` 证据正确，**唯独本卡新接入的 cancel/`enforce_budget` 路径不先跑账本收敛**——in-flight 竞窗（工具在途时长，≤~120s tool timeout）内取消/超限的 run 面投影误标。`limitations.md §3` 声明的账本边界未被突破（行不删、可审计），但与「如实对账」精神在竞窗内有张力。
- **处置建议（入池登记）**：登记可靠性候选——`_side_effect_reconciliation` 在物化前先跑 `reconcile_stale_in_progress`（与 `recover_inflight_runs` 同构，改动局限本卡引入的方法），或由 X-09 单一 owner 把 `build_evidence` 的 in_progress 桶改为 interrupted/outcome-unknown。后者更根本但属 X-09 域契约。

### 靶6｜复跑 — **PASS（本会话独立执行）**

| 面 | 命令要点 | 结果 |
| --- | --- | --- |
| 新契约测试 | `pytest tests/unit/test_v4_i08_deep_task_return_control.py -q`（SECRET_KEY=ci-test-key DATABASE_URL=sqlite://，共享 venv 3.11.15 / pytest 9.0.2） | **24 passed**（8.90s） |
| 受影响面 12 文件 | 与 run_manifest 同组合（X-05/06/07/09、hybrid steps+API、runs API×2、journey、状态机冻结、步骤投影、wt392） | **273 passed**（192.54s，exit 0） |
| mypy 棘轮 | `mypy app --ignore-missing-imports` 全量 → grep 'error:' | **55 ≤ baseline 77**（`quality/mypy_baseline.txt`=77 核实）；3 个改动产品文件 = **0 条** |
| ruff / black | 4 改动文件 | **All checks passed / 4 files unchanged** |
| 对抗探针 | 11 例（C-1 构造×4 + 乱序/duplicate/崩溃窗×4 + 预算终态×2 + in-flight 竞窗×1） | **11 passed**（跑完即删） |

### 靶7｜limitations 与一审观察定性复核 — **PASS（O-1 时点更新 / O-2 维持）**

- **limitations 7 条逐条核对**：与代码事实一致（§4 自declare approval 豁免、§1 服务路径口径、§3 账本边界、§5 PARTIAL 收敛保守、§6 分支时点）。§3「executor 正确落账的调用如实入对账」声明与 C-2 的张力已在靶5 如实标注（C-2 是账本**内 in_progress 行的标签**问题，不是账本外泄漏）。
- **O-1（更新）**：main 现 `48f8b9f7`（一审时 1063abb3，实现期快照 150bc205）；merge-base 仍为 base `33dc2223`；`git diff 33dc2223..main` 对 I08 的 3 个产品文件**零变更**——集成无冲突面，结论逐次核实不变。
- **O-2（维持，附消费面核实）**：wire `action` pattern `^(confirm|edit)$` 使 ack/「yes」在 API 面本就 422（FastAPI 先拒）；服务层封闭词表是纵深防御 + 非 wire 路径（hybrid `decide`）的权威。grep 网关/mobile：**当前不存在 user-step 完成动作的网关特化或移动端消费面**（/runs 为通用代理）——消费面对齐是未来客户端建设的登记义务，fail-closed（拒而不吞）方向无回归风险。维持「观察」级。

## 诚实性抽查

- 「5s」全证据链无整链宣称（靶4）；LLM usage=0、无 UI 面声明与 diff 事实一致。
- C-2 所在行为未被实现方粉饰或宣称（diff 文档只声明 succeeded/failed/interrupted 三桶，未宣称 in_progress 处理）——挑战点在「未声明的竞窗行为」，非「虚假声明」。
- 一审 receipt 结论经本审独立探针全部复现，无过度声明。

## 裁决

**PASS_WITH_CHALLENGES（二审通过）**：三条验收在对抗面下成立（恢复乱序无双写/不复活/归因保持；预算终态语义与去向清楚；5s 如实为服务路径口径；人步伪造守卫在豁免面之外精确有效）；C-1 维持一审处置（登记后续可靠性卡，建议 intent 绑定要求 (b) 案）；**C-2 新增登记**（cancel/budget 面对账物化前先收敛账本 in_progress，或 X-09 桶化语义修正）。两项 challenged 均不阻塞本卡。集成 SHA 复验时重点：C-1/C-2 登记入池确认 + O-1 时点口径 + 受影响面在合并 SHA 上复跑。
