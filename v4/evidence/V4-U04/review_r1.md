# V4-U04 · 独立审查一审 receipt（reviewer_1 = wtU04R1）

- 审查人：wtU04R1（未参与 U04 实现；只读审查 + 临时探针，探针用后即删，工作树已复原干净）
- 对象：`agent/v4/u04` @ `a4fd656d`（base `30b94d42`；`git status` clean 复核于审查时点）
- 卡标准：`Sparkle-project/v4/04_tasks/tasks.json` V4-U04 条目（high · 双独立审查 · FIX535 接线）
- 日期：2026-09-29

## 裁决：PASS_WITH_CHALLENGES

三条验收实质成立（证据可复现、RED 可失败、行为红线在代码与服务端两侧成立）；存在 1 个断言强度缺口（R-1）、2 个接线语义错位（R-2/R-3）与 2 组数字口径瑕疵（R-4/R-5），均不构成阻断，列条件与跟进项供二审与集成面裁决。

---

## 一、预登记挑战逐项独立下判

### CH-1 取消幂等键双轨 vs 后端 optional-key —— **解决（无冲突面）**

- 客户端两轨：awaiting 态下 workbench 回退推导 `run.awaitingStep?.stepId ?? 'run'`（hybrid_workbench_screen.dart:124-125）与卡内推导（awaiting_step_resume_card.dart:90，`runStepIdempotencyKey` 同构式）**恒同键** `x07:<runId>:<stepId>:cancel`——`awaiting_step` 是服务端投影（agent_run_read_service.dart:147,171），两轨同源不同写。非 awaiting（RUNNING 中取消）回退 `x07:<runId>:run:cancel`。
- 后端：`CancelRunRequest.idempotency_key` optional（backend/app/api/v1/runs.py:106）；幂等**主保证是状态机复查**——`AgentRunService.cancel` 对已 CANCELLED 直接 `applied=False` no-op（agent_run_service.py:1099-1101），`transition()` current==target 同样 no-op（agent_run_service.py:662-667）；键只落 transition 审计行 + `(run_id, idempotency_key)` 唯一索引二次兜底（模块头 16-17 行）。双轨键不一致的并发场景被状态复查收敛，不产生重复取消；即使某步恰名 `run`，两键同指同一取消意图，first-wins 无语义分叉。
- 复现：`sed -n '106p;414,431p' backend/app/api/v1/runs.py`；`sed -n '1076,1120p;656,668p' backend/app/services/agent_run_service.py`。

### CH-2 `j06:start:auto` 锚点漂移 —— **边界真实，本卡可接受（维持登记）**

- 推演：后端 `start_hybrid_journey` 先 `_resolve_anchor`（无 taskId → 最近触碰在飞任务，hybrid_journey_service.py:266-283）**再**按 `(user_id, idempotency_key)` 幂等回放（agent_run_service.py:548 → `_find_by_idempotency_key` user-scoped，:2155-2158）。第二次 `j06:start:auto` 命中既有活跃 run → 原样回放**第一次**的 run——锚点解析结果在回放分支被忽略。即漂移方向是"回放旧 run"而非"锚到新任务"：同 run 不重复工件成立；期望锚到新任务的用户得到旧 run（run 卡与任务面入口都可见，可用取消+任务面入口纠正）。终态键释放（wt392 F1，:484-492）保证死 run 不钉死。
- 裁决：同 run 语义边界成立，limitations #2 描述准确，可接受。跟进建议（非本卡）：auto 键改 goal 锚定，或工作台空态启动前提示既有 auto run。
- 复现：`sed -n '455,500p' backend/app/services/hybrid_journey_service.py`。

### CH-3 任务面回归广度 —— **缺口确认；审查已补证，留一条永久断言为条件**

- 事实：`test/features/task/` 无 TaskExecutionScreen 整屏 pump（仅 list 屏）；现存整屏 pump 在 `test/widget/task/test_task_execution_ux.dart`、`test/widget/exam_sprint_closed_loop_test.dart`——**不在实现者的套件清单内**。
- 审查补跑：`flutter test test/widget/exam_sprint_closed_loop_test.dart test/widget/task/test_task_execution_ux.dart` → **15 passed**（挂载未破坏整屏渲染）。
- 审查探针（临时文件，已删）：整屏 pump TaskExecutionScreen + `agentRunReadServiceProvider` stub → `hybrid_journey_entry_section` 键上树、无 run 时 `journey_entry_start`（非 resume）、`takeException` null。注意：真实 Dio 在 fake-async 永不完成 → 区块停在"读取中不渲染"（设计行为），故**连现存 test/widget 整屏测试也实际看不到该区块**——挂载点至今无永久性整屏断言。
- 条件 C-1（集成面/二审裁决）：在 test/widget 整屏测试加一条带读面 override 的挂载断言（探针写法已在本 receipt 记录，成本约 30 行）。

### CH-4 run_id 深链越权读面 —— **解决（无越权面）**

- `GET /journey/hybrid/{run_id}` → `get_hybrid_journey_state` → `get_run(run_id, user_id=current_user.id)`（journey.py:334-344；hybrid_journey_service.py:1001-1005；get_run user-scoped，agent_run_service.py:440-448）+ `trace_id != hybrid_journey` 拒绝。跨用户 run_id → 404。
- `GET /runs` → `list_runs(user_id=current_user.id)`（runs.py:215-232）；`GET /runs/{run_id}` 同 user-scoped（runs.py:237-249）。全部 `route-tier: authed`。客户端 `fetchActiveRuns/fetchRun` 均走认证 ApiClient，无匿名面。

### CH-5 step_replay 呈现 vs X-07 挂载义务 —— **满足**

- 义务原文（agent_run_command_service.dart:31-34，V3-FIX-379① 撤承诺裁决）："未来挂载面必须消费 `step_replay`——true 时呈现「已经确认过了」而非报错"。
- 落位：workbench `_completeAwaitingStep` 消费 `result['step_replay']` → 中性 Pill `workbench_replay_notice`（hybrid_workbench_screen.dart:89-95,160-168）；workbench 测试第 5 面断言 replay=true 时 notice 出现且零 cancel。非错误面、不伪装首次成功。小口径勘误（R-3）：清除时机实为"下次 confirm 返回非 replay 时"，非 receipt 所写"下次列表重建"。

---

## 二、行为红线（本卡最重）

1. **入口零审批写动作——代码级成立，测试未钉住（本审最重要发现）**
   - 代码核对：`HybridJourneyEntrySection._openSheet` 仅 `showHybridJourneySheet` + provider invalidate（hybrid_journey_entry_section.dart:43-58）；两处 V3 挂载与路由均为纯导航；workbench 命令面仅 confirm/cancel 两动作。
   - **Mutation ②（探针，已复原）**：向 `_openSheet` 注入 `repository.confirmOutcome(...)` 审批写 → `hybrid_journey_entry_section_test.dart` **4 面全绿**。原因：`_FakeRepository` 只记录 start/fetchState，submitJudgment/confirmOutcome 是无记录 stub。diff 文档"第 2 面证明入口唯一写动作……零 approve/reject/complete 调用"属**过度声明**——测试证明了 start/fetchState 记账，未证明零审批写。
   - 定性：非行为违规（服务端门独立成立：submitJudgment 强制 selected_refs+幂等键 :633-635；confirm_outcome 同 :862-864；complete_user_step 拒 agent-owned 步 :1469-1474、非 awaiting 409、非下一序步拒绝——客户端回归也绕不过服务端校验），属**断言强度缺口**。
   - 条件 C-2：entry 测试 fake 记录全部四个仓库方法并断言 `submitJudgmentCalls/confirmOutcomeCalls` 为空（约 6 行改动）。二审/集成前完成或接受为已知债务登记。
2. **human 步幂等键确定性**：推导式 `'x07:$runId:$stepId:$action'` 纯函数（agent_run_command_service.dart:71-72）；workbench 测试 7（重建同键逐字一致）+ 测试 5（confirm 键 `x07:run-g1:step-2:confirm`、action='confirm'）断言在案 ✓。
3. **判断/审批门全在服务端**：见上；`judgment_required` 422 与空选择结构性禁用（sheet 既有 3 面 + 截图 2 呈现）不变 ✓。

## 三、续跑语义推演（验收 ③）

| 状态 | 工作台列表 | 入口/深链行为 | 覆盖 |
|---|---|---|---|
| run 活跃+awaiting | 显示 | resume 按 runId fetchState 同一段 run（start=0） | workbench 2、entry 1 |
| run 已完成/已取消 | 不显示（active=true 过滤） | 深链 fetchState 幂等回放终态原样投影（`_replay_payload` :379-397，不重算）；任务面入口变启动，终态键释放开新 attempt（wt392 F1） | 后端 j06 5 passed + I08 24 passed（实现者跑，本审复跑 j06） |
| awaiting 不同步（列表陈旧） | — | 恢复唯一锚 runId，sheet 渲染服务端实际状态；操作后 invalidate | workbench 8（深链）+ 架构上客户端非 runtime owner |

结论：同 run 声明成立；测试覆盖充分（终态 workbench 级无专测，由后端钉住，可接受）。

## 四、RF-06 零触碰与 V3 只增

- `git diff --numstat 30b94d42..a4fd656d` 28 文件与 manifest `files_changed` 完全一致；理解读出/校准族（memory/understanding_overview、context_receipt、aurora_calibration 等 RF-06 冲突面）零 diff ✓。
- V3 两文件只增：task_execution_screen +6/-0（注释 3 + import 1 + 挂载块 2 行内的 1 组件行+注释）、openclaw_hub_screen +11/-0（注释 2 + import 1 + 按钮 8）；routes.dart +4（注释+import+注释+spread），五 Tab 结构零改动。行级 rebase 冲突风险：低（各一个连续挂载块 + 单行 import）。
- backend 零 diff ✓（numstat 无 backend 文件；本审另复核 `git status --short backend/` 干净）。

## 五、测试质量与 RED 证据链

- **Mutation ①（wiring RED 独立复现）**：`git checkout 30b94d42 -- mobile/lib/app/routes.dart` → wiring 测试红，失败形态 `Found 0 widgets with key [<'hybrid_workbench_screen'>]` 与 run_manifest 声明**逐字一致** → 复线 `git checkout a4fd656d -- ...` 复绿。wiring 测试走真实 `routerProvider`（routes.dart:116），非自制 router，RED 证据链可信 ✓。
- 新测 14 面（workbench 8 + entry 4 + wiring 1 + copy 1）断言强度总体高：幂等键逐字断言、对话框拦截前零命令、start=0 计数、他任务 run 不冒充、重建同键、错误面诚实。唯一强度缺口见 R-1/C-2。
- 审查自跑：journey 31 ✓、task+shared+smoke 122 ✓、test/widget 两整屏 15 ✓、pytest j06 5 ✓（SECRET_KEY 一次性，sqlite 口径，无 .env）。

## 六、数字诚实性

- 相符：journey 31、122、j06 5（三套本审自跑精确复核）；14 新测；copy 31 键 zh+en；三截图 sha256 与 manifest 一致；截图内容与 ui_evidence 描述逐项吻合（2 段运行卡+ownership 词表、判断段"这一步需要你决定"+空选择禁用提交、取消对话框终态如实文案）；semantics txt 与截图文本一致。
- **R-4：`test_results.json total.flutter_passed: 228` ≠ 列套件之和 224**（31+31+122+4+10+26；差 4，疑 deep-link 重复计入）。各分项计数均实，聚合数错。
- **R-5：diff 文档头部"+579/-2，全部 mobile"不可复现**：实测 mobile +2380/-4（lib +1083/-0，其中 l10n gen 384、arb 78/-2；test +1297），全 commit +2782/-5。manifest 的逐文件行数（+4/+8/+11/+7/+6）与 numstat 全部吻合；diff 文档内"+4/+9"（task/openclaw）是不含 import/注释的挂载块口径、arb"+40/-1"实为 +39/-1。定性：聚合口径不精确，逐文件声明诚实，非实质误导；建议修正文档头部两处数字。

## 七、新发现（非预登记）

- **R-2（接线语义错位，低危）**：workbench 把 `AwaitingStepResumeCard.onRefresh` 接到 `onCancelRun(null)`（hybrid_workbench_screen.dart:319）——expired/cancelled 步态下的「刷新」按钮实际打开「取消这段运行？」对话框。有显式确认拦截、无误取消风险，但语义错位；建议改 `ref.invalidate(activeAgentRunsProvider)` 或独立刷新回调。
- **R-3（小口径）**：`_replayNotice` 清除时机实为"下次 confirm 返回非 replay"（setState 置 null），非 receipt 所写"下次列表重建"；无行为影响。
- **F-B（死参数）**：`JourneyRoutes.workbenchUri(taskId:)` 生成的 `task_id` 查询参数路由侧无人消费（journey_routes.dart:39 只读 run_id）——深链进 workbench 的启动恒走 `j06:start:auto`（CH-2 边界适用）。建议二选一：路由消费或删参数。

## 八、条件与跟进汇总

| 编号 | 内容 | 性质 |
|---|---|---|
| C-1 | test/widget 整屏挂载断言一条（探针写法见 §五/CH-3） | 条件（建议集成前） |
| C-2 | entry fake 记录全仓库方法 + 零审批写断言（mutation ② 教训） | 条件（建议集成前；若延后须登记已知债务） |
| F-1 | R-2 onRefresh 接线修正 | 跟进 |
| F-2 | R-5/R-4 文档数字修正（diff 文档头部、test_results total） | 跟进 |
| F-3 | F-B workbenchUri task_id 死参数取舍 | 跟进 |
| F-4 | CH-2 auto 锚点后续改进（goal 锚定/启动前提示） | 跟进（非本卡） |

## 复现命令索引

```bash
cd /Users/brsama/code/GitHub/wtU04
git diff --numstat 30b94d42..a4fd656d                     # §四 全清单
cd mobile && flutter test test/features/journey/           # 31
flutter test test/features/task/ test/shared/widgets/ test/app/router_smoke_test.dart  # 122
flutter test test/widget/exam_sprint_closed_loop_test.dart test/widget/task/test_task_execution_ux.dart  # 15
cd ../backend && SECRET_KEY=<一次性> pytest tests/unit/test_j06_hybrid_journey.py -q   # 5
# Mutation ①（复现后须复原）：git checkout 30b94d42 -- mobile/lib/app/routes.dart && (cd mobile && flutter test test/features/journey/hybrid_workbench_wiring_test.dart)
```
