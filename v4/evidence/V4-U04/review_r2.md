# V4-U04 · 独立审查二审 receipt（reviewer_2 = wtU04R2）

- 审查人：wtU04R2（未参与 U04 实现与一审/整改；只读审查 + 临时探针，探针用后即删，工作树复原干净）
- 对象：`agent/v4/u04` @ `7cf02bfa`（实现 `a4fd656d` → 一审 receipt `40bd1821` → 整改 `be3d8c6a` → receipt 注记 `7cf02bfa`；base `30b94d42`）
- 卡标准：`Sparkle-project/v4/04_tasks/tasks.json` V4-U04（high · 双独立审查 · FIX535 接线）
- 日期：2026-09-29

## 裁决：APPROVE

一审全部条件（C-1/C-2）与新发现（R-2/F-1、F-B/F-3）及数字勘误（R-4/R-5/F-2）**逐项落地且亲验成立**；三条卡验收在本审全量复跑与代码级抽验下维持成立；无新阻断发现。合并落差（tasks.json 结构冲突）为集成面机械功课，非本卡缺陷，列合并条件供集成 owner。

---

## 一、整改复核（首靶）

### C-1 整屏 pump 挂载断言 —— **落地成立，RED 亲证**

- `mobile/test/features/task/presentation/screens/task_execution_hybrid_entry_mount_test.dart`（2 面）：整屏 pump 真实 `TaskExecutionScreen`，override `agentRunReadServiceProvider`（注释如实记录原因：区块"读取完成才渲染"，真实 Dio 在 fake-async 永不完成——与一审 CH-3 探针结论一致）+ `_UnusedRepository` 证明无隐藏仓库依赖；面 1 无 run → `journey_entry_start` 上树且 `journey_entry_resume` findsNothing；面 2 本任务 run → `journey_entry_resume`；两面 `hybrid_journey_entry_section` 键上树 + `takeException` null。有限帧推进替代 pumpAndSettle 的理由（整屏持续动画）如实注记。
- **Mutation C-1（本审探针，已复原）**：把挂载行 `HybridJourneyEntrySection(taskId: task.id)`（task_execution_screen.dart:1984）替换为 `SizedBox.shrink()` → C-1 测试 **2 面红**；复原复绿。挂载断言真实可失败，非摆设。
- 计数落位：task/shared/smoke 122→124 ✓（本审复跑精确命中）。

### C-2 入口零审批写钉 —— **落地成立，mutation ② 双注入点亲放均红**

- `_FakeRepository` 记录**全部四个仓库方法**（start/fetchState 白名单记账 + submitJudgment→judgmentRunIds / confirmOutcome→confirmRunIds 黑名单记账）+ `_FakeCommandService`（complete/cancel 全记账）override 命令面；`expectNoApprovalWrites()` 在①②交互面于 **pop 关闭 sheet 之后**断言（hybrid_journey_entry_section_test.dart:263-269, 298-311）。
- **Mutation ②-a（await 前注入 confirmOutcome，本审探针，已复原）**→ entry 测试 **2 面红**（①②交互面；③④非交互面不受染）。
- **Mutation ②-b（await 后、sheet 关闭后段注入，本审探针，已复原）**→ 同样 **2 面红**。
- **「await 后注入曾漏抓→补 pop」披露真实性核**：`_openSheet` 结构为 `await showHybridJourneySheet(...)` 后接 invalidate 段（hybrid_journey_entry_section.dart:48-58）——模态 sheet 的 Future 仅在关闭时完成，测试若不 pop，await 后段在测试窗口内**永不执行**，注入记账恒空（旧缺口机理成立）；补 pop 后关闭后段纳入观察面。本审 ②-b 亲放即该场景，实测必红。披露与代码结构、实测三方一致，**披露可信**。
- 复原复绿：entry 4 面全绿（本审复跑）。

### R-2/F-1 onRefresh 接线 + 挂载门根因 —— **落地成立，根因补充经推演属实**

- 代码：`_refreshRuns() => ref.invalidate(activeAgentRunsProvider)`（hybrid_workbench_screen.dart:103），经 `_RunCard.onRefreshRead` 接到 `AwaitingStepResumeCard.onRefresh`（:336）——刷新语义 = 重查读面。
- **根因补充（超出一审描述）核**：原门 `awaiting != null && awaiting.isAwaiting` 下，`AwaitingStepResumeCard` 只走 `step.isAwaiting` 分支（确认按钮），刷新按钮存在于 `!isAwaiting` else 分支（awaiting_step_resume_card.dart:143/203-216）——即原错接线 `onRefresh → onCancelRun(null)` 在旧门下**实际不可触发**（死代码），一审 R-2 "expired 步态下刷新按钮打开取消对话框"的描述高估了可达性。整改同时（i）放宽门为 `awaiting != null` 使 expired/cancelled 卡面真实可达、（ii）把刷新接真——可达面与语义同时修正，工程判断正确。
- **门放宽行为面亲验**（靶 2）：
  - 组件侧：`!step.isAwaiting` 分支只渲染 `proposalStatusExpired/Cancelled` 标题 + 过期/取消 hint + 刷新 TextButton，**无确认入口**（awaiting_step_resume_card.dart:203-216）——"不给确认入口"声明成立。
  - 测试侧：workbench 新增 expired 面（hybrid_workbench_screen_test.dart:430-461）断言强度高：`确认，继续` findsNothing、`刷新结果` 上树、读面重查计数 1→2、`workbench_cancel_confirm_yes` findsNothing（对话框不上树）、cancel/complete/start 全零、刷新后 run 卡仍在。
  - 误操作面评估：刷新为纯读面 invalidate；取消仍走显式对话框且仅在 `!run.isTerminal`（原行为不变）；无新增误操作面。
  - 观察 O-1（非阻断）：expired 步态下 run 级状态 Pill 仍按 `run.isAwaitingUser` 显示「等待用户」（hybrid_workbench_screen.dart:284,392-394），与步级「已过期」并存——两者各自如实投影服务端字段（run status 与 step state 本就可异），呈现无伪造，但同卡双状态文案存在轻度张力，属服务端投影语义域，不属本卡缺陷，登记给集成面知悉即可。

### F-B/F-3 task_id 死参数取消费侧 —— **落地成立，链路端到端亲验**（靶 3）

- 路由消费：`journey_routes.dart:42` `initialTaskId: query['task_id']` → `HybridWorkbenchScreen.initialTaskId` → `_openJourneySheet` 传 `taskId: widget.initialTaskId`（:71）→ sheet 启动键 `j06:start:<taskId>`。
- wiring 新增深链面（hybrid_workbench_wiring_test.dart:155-226）：真实 `routerProvider` `go('/journey/workbench?task_id=task-deep-1')` → 点 `workbench_start_journey` → 断言 `startKeys == ['j06:start:task-deep-1']` 且 `startTaskIds == ['task-deep-1']`。路由→screen→sheet→仓库全链被一条测试钉住，非各自为证。
- **CH-2 缓解声明如实性**：宣称"缓解"而非"解决"——准确。带 task_id 的深链与任务面入口均绕开 auto 键；workbench 无上下文空态启动（hub 按钮进入）仍走 `j06:start:auto`，锚点漂移边界原样保留且 limitations #2 已如实更新。缓解程度声明与事实相符。

### R-4/R-5/F-2 文档数字勘误 —— **全部可复现命中**（靶 7）

本审逐项重算（`git diff --numstat 30b94d42..a4fd656d` 族）：

| 声明（整改后文档） | 实测 | 判 |
|---|---|---|
| 全 commit +2782/-5 | +2782/-5 | ✓ |
| mobile +2380/-2（18 文件） | +2380/-2（18 文件） | ✓ |
| mobile/lib +1083/-2；test +1297/-0 | 同 | ✓ |
| l10n gen +384；arb 双语各 +39/-1 | 同（run_manifest 勘误行一致） | ✓ |
| v4 证据 +396/-0；tasks.json +6/-3 | 同 | ✓ |
| test_results total 224 = 31+31+122+4+10+26 | 算术与分项均实 | ✓ |

一审指出的"建议数字本身之误"（-4→-2）亦已在 diff 文档整改节说明。三份文档（diff/manifest/test_results）+ limitations 整改节口径互相一致，无残留失实。

## 二、一审已裁决项抽验（靶 4）

- **CH-1 幂等键双轨（维持解决）**：`CancelRunRequest.idempotency_key` optional（backend/app/api/v1/runs.py:103）；`AgentRunService.cancel` 对已 CANCELLED 直接 `applied=False` no-op（agent_run_service.py:1100 附近，本审读出 `run = await self.get_run(run_id, user_id=user_id)` 后 CANCELLED 短路），`transition()` 带 `FOR UPDATE` 行锁 + user_id 过滤 + 复查兜底（:656-668）——状态机为主保证、键为审计/唯一索引二次兜底的双轨结论维持。
- **CH-4 深链越权读面（维持解决）**：`GET /journey/hybrid/{run_id}` route-tier authed、透传 `user_id=current_user.id`（journey.py:334-344）；`get_run` SQL 级 `AgentRun.user_id == user_id` 过滤（agent_run_service.py:440-448）——跨用户 run_id 404，无越权读面。

## 三、全量复跑（靶 6，本审亲跑）

| 套件 | 命令（cwd=wtU04/mobile） | 声明 | 实测 |
|---|---|---|---|
| journey | `flutter test test/features/journey/` | 33 | **33 passed** ✓ |
| task/shared/smoke | `flutter test test/features/task/ test/shared/widgets/ test/app/router_smoke_test.dart` | 124 | **124 passed** ✓ |
| deep link + 既有整屏 | `flutter test test/app/router_deep_link_test.dart test/widget/exam_sprint_closed_loop_test.dart test/widget/task/test_task_execution_ux.dart` | 4 + 15 | **19 passed**（4+15）✓ |
| test/widget 全目录（加码回归） | `flutter test test/widget/` | — | **467 passed, ~4 skipped** ✓ |
| analyze | `flutter analyze` | 零新增 | **No issues found** ✓ |
| backend 零 diff | `git diff --numstat 30b94d42..HEAD -- backend/` + `git status --short backend/` | 0 | **0 / 0** ✓ |

探针后工作树 `git status` clean 复核 ✓。

## 四、合并落差（靶 5，main = 64fc2f4d）

`git merge-tree $(git merge-base HEAD 64fc2f4d) HEAD 64fc2f4d`（merge-base = base `30b94d42`，U04 自 base 干净分叉）：

- **tasks.json：唯一真冲突，结构性**——main 侧近乎全文件重写（+3734/-3705，U01 并集解先例 f28f157b），U04 侧仅 V4-U04 条目状态块 +6/-3。**合并条件 M-1**：按并集解把 U04 状态块（`in_progress/REVIEW_READY/PENDING_REVIEW` + progress/evidence 注记）重放到 main 重构后的 V4-U04 条目上，机械功课、语义风险低，但不可走自动合并。
- **l10n 5 文件（arb×2 + gen×3）：双侧改动、文本自动合并无冲突标记**——U04 +39/-1 arb 与 main +24/-0 arb 追加不同键区。**合并条件 M-2**：合并后必须 `flutter gen-l10n` 再生成（gen 文件勿手改红线），并以 journey 套件复跑验证。
- **mobile lib 代码零重叠**：main 侧改动集中于 chat/home/galaxy/design/l10n（U01 cockpit、U07 chat 等）；U04 的 journey/task/openclaw 挂载文件 main 侧零触碰——行级 rebase 冲突风险低，limitations #8 的行级登记维持。
- backend：main 侧亦无与 U04 相关面（U04 backend 零 diff），无冲突面。

## 五、新发现（非阻断）

- **N-1（记账缺口，已代补）**：`review_receipt.json` 的 `reviewer_1` 在一审完成后仍为 `null`（7cf02bfa 注记只加了 remediation 块）。本审按 r1 receipt 事实回填 reviewer_1 并新增 r2 条目。
- **O-1**：见 §一 R-2 节——expired 步态 run 级/步级状态文案双投影张力，服务端语义域，登记知悉。
- **O-2**：journey run 在 expired/cancelled 步态下经放宽门显示「继续旅程」入口——点击打开 sheet 幂等回放服务端实际状态（诚实呈现，无直接确认入口）；该面无专测，由 sheet 既有测试与后端投影钉住，可接受。

## 六、条件与跟进汇总

| 编号 | 内容 | 性质 |
|---|---|---|
| M-1 | 合并时 tasks.json 并集解：U04 状态块重放到 main 重构版（不可自动合并） | 合并条件（集成 owner） |
| M-2 | 合并后 `flutter gen-l10n` 再生成 + journey 套件复跑 | 合并条件（集成 owner） |
| F-4 | CH-2 auto 锚点改进（goal 锚定/启动前提示） | 跟进（非本卡，一审已登记，维持） |

## 复现命令索引

```bash
cd /Users/brsama/code/GitHub/wtU04
# 全量复跑
cd mobile && flutter analyze && flutter test test/features/journey/
flutter test test/features/task/ test/shared/widgets/ test/app/router_smoke_test.dart   # 124
flutter test test/app/router_deep_link_test.dart test/widget/exam_sprint_closed_loop_test.dart test/widget/task/test_task_execution_ux.dart  # 19
flutter test test/widget/                                                               # 467+4skip
cd .. && git diff --numstat 30b94d42..HEAD -- backend/                                  # 空 = 零 diff
git merge-tree $(git merge-base HEAD 64fc2f4d) HEAD 64fc2f4d | grep -ac '<<<<<<<'       # 1（tasks.json）
# 数字复核
git diff --numstat 30b94d42..a4fd656d | awk '{a+=$1;d+=$2} END{print "+"a" -"d}'        # +2782 -5
# Mutation 探针（本审已复原；复现后须 git checkout 复原对应文件）
# ②-a/②-b：在 hybrid_journey_entry_section.dart _openSheet 的 await 前/后注入
#   repository.confirmOutcome(runId:…, idempotencyKey:…) → entry 测试 2 面红
# C-1：task_execution_screen.dart:1984 挂载行替换 SizedBox.shrink → mount 测试 2 面红
```

## 裁决理由重述

双审齐备：R1 PASS_WITH_CHALLENGES 所列条件与跟进全部落地且经本审独立亲验（含两类 mutation 注入必红、挂载断言 RED 可失败、文档数字逐项可复现）；行为红线（入口零审批写、human 步幂等确定性、审批门在服务端）在测试与服务端两侧维持成立。无阻断证据，裁决 **APPROVE**。
