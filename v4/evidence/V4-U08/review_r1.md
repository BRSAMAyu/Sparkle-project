# V4-U08 一审 receipt（R1）

- 审查会话：wtU08R1（未参与 U08 实现，独立会话）
- 审查对象：实现 `98dd980d` + 证据 `a6a2d513`，基线 `a8f46650`，分支 `agent/v4/u08`（审查时工作树干净）
- 卡标准：`v4/04_tasks/tasks.json` 的 `V4-U08` 条目（normal / independent_reviewers=1 / locks=ui-plan-task）
- 裁决：**APPROVE_WITH_CONDITIONS**
  - 三条卡面验收全部独立复核通过、可失败性亲验成立、红线零触碰；
  - 唯一条件项 **C-1**：`_coalesceStepWrite` 的 `unawaited(future.whenComplete(...))` 阴影 Future 在 goal 拒绝路径泄漏未处理异步错误（R1 亲证，见 F-1）——合入前在本分支补一行影子 Future 错误处理并复验（机械修复，不需要重审全卡）。

---

## 1. 卡面验收逐条独立判定

### 验收① 四页面看到同 task/version；重复点击一次写入 —— **PASS**

写入点收敛独立 grep（R1 亲跑，`grep -rn "\.completeTask(|\.abandonTask(|\.deleteTask(|rescheduleTaskDueDate(" lib/` 排除 provider/repo/test）：
- `completeTask` UI 调用面 6 处（home `next_actions_card` / home `interactive_task_card` / task `task_list_screen`×2 / `task_execution_screen` / community `group_tasks_screen`）**全部**经 `taskListProvider.notifier` → 合流点覆盖；
- `abandonTask` 2 处（interactive_task_card / task_execution_screen）同上；`deleteTask` 1 处（task_detail_screen）同上；`rescheduleTaskDueDate` 1 处（calendar_stats_screen:132）同上；
- plan 页任务卡无直写（`plan_detail_screen.dart:1296` `onTap → context.push('/tasks/{id}')` 导航进 task 面；phase onComplete 是计划 phase 非任务写）——plan 页经共享读模型+导航收敛，同链成立；
- goal 页走 `GoalDetailNotifier` 自有链（见 CH-3 裁决：同制即满足）。

「重复点击一次落库」mutation 亲放两向：
- 拆合流（`_inFlightWrites[key]` 查找置 null 透传 `run()`）→ `unified_action_semantics_test` **+7 -2**（验收①任务双击合流测与改期双击合流测变红）——合流测是承重测；
- 复原后 +9 全绿。「不吞合法重试」边界由反面测钉死（在飞结束后同任务新写入照常发起，`unified_action_semantics_test.dart:442-464`），R1 探针 A2 佐证顺序重试真实可达。

### 验收② 改日程有键盘/按钮路径，不仅拖动 —— **PASS**

- `calendar_stats_screen.dart:1235-1247` 待办 agenda 卡挂 `SparkleIconButton`（ValueKey `calendar-reschedule-{id}`、语义名 `calRescheduleAction`、ghost 档）→ `_showReschedulePicker`（:153）→ 标准 `showDatePicker`；
- 证据测试亲跑通过：按钮存在 + `find.bySemanticsLabel('改期')` + 终态卡 `findsNothing` 反面 + 点击后 `find.byType(CalendarDatePicker)`（真实 showDatePicker 产物非 stub）+ 确认闭环无异常；
- 语义 dump 落盘核对：`label="改期" rect 48×48 actions=4194305(tap)`（`screenshots/u08_calendar_reschedule_button_semantics.txt` 末节）；
- 拖拽确认与按钮路径收敛 `_rescheduleTask`（:124）→ `rescheduleTaskDueDate` 单一写入口；SCREEN_FAMILIES「拖动须有键盘/按钮替代」落地。
- 注意（F-3，不阻塞）：**拖拽源当前是死代码**——全库唯一 `LongPressDraggable`（`DraggableTaskCard`）零调用点，日历 DropTarget 实际无物可拖，按钮路径事实上是唯一活改期入口（详见 CH-4）。

### 验收③ 计划时长不作为完成证据，删除/放弃不同语义 —— **PASS**

- `unified_calendar_provider.dart:157` `focusMinutes += task.actualMinutes ?? 0`——估时切断亲验：R1 亲放突变复旧 `?? task.estimatedMinutes` → **+8 -1**（反面测「估时不得顶替」变红），与自述完全一致；还原后 +9 绿；
- 分享卡切断链核实：`task_detail_screen.dart:465` `if (task.actualMinutes != null) 'duration': ...` → `share_poster_service._durationMinutes`（:407）null/非正整数返回 null → `addMetric` 缺席，海报侧确无改动必要；
- 「预计 X 分钟」计划意图展示保留（arb 既有键零触碰），展示位与证据位分离成立；
- 删除/放弃互不降级：双向反面断言在测（abandon→deleteCalls==0 / delete→abandonCalls==0 + 日历联动清理断言），R1 亲跑通过；
- 现有文案面无「专注=估时」类误导标签（`calFocusDuration`="专注时长"/`calFocusDurationDetail`="本月累计专注"，中性），数值走低不构成既有文案变谎言（CH-2 裁决依据）。

## 2. 预登记挑战 CH-1~CH-5 逐项独立下判

### CH-1 在飞合流×离线入队竞态 —— **裁决：窗口内无双写面；窗口外残余由回放端 409 幂等兜底，可接受，无需本卡整改**

R1 构造双写场景探针（临时探针已删，结论在此）：
- 门控真并发（第一次 repo 调用挂起→第二次点击→释放走 `OfflineEnqueuedException`）：repo 调用=1、入队=1、两调用者 `identical` 同 Future——**在飞窗口内（含离线入队+异常路径）不存在双写**；
- 窗口后顺序两次调用：repo 调用=2、入队=2——`SyncEngine.enqueue`（`lib/core/offline/sync_engine.dart:74-97`）**每次无条件 put 新 OutboxItem，dedupeKey 只落库不入队期查重**，故同操作可产生两条 outbox 条目；
- 收敛面：`_sendTaskOperation`（sync_engine.dart:381-424）对 409 按成功处理（"already in target state"），服务端终态收敛，完成奖励不双发（409=拒绝重复迁移）；
- 可达性：离线入队后任务乐观置位 completed，完成按钮隐藏；`retryCompleteTask`（task_provider.dart:750）有 completed+synced 幂等跳过（M6-03），与在飞合流互补不重叠。残余面属**既有离线链行为**（非本卡引入，本卡反而收窄窗口）；outbox 入队期按 dedupeKey 查重如需补强属离线链另卡，不阻塞本卡。

### CH-2 专注数值走低的用户可见口径 —— **裁决：诚实优先正确，无需本卡整改说明面**

卡面验收文本就是「计划时长不作为完成证据」——`actualMinutes=null` 计 0 正是该验收的直接落地。既有标签（"专注时长"/"本月累计专注"）中性，无既有文案因此变谎言。热力图例注明「专注=实测时长」属可选 UX 润色，**归视觉/文案另卡**（非阻塞建议，不派义务）。

### CH-3 goal 第二写入入口未并入 —— **裁决：同语义同制即满足，不要求并入**

`GoalDetailNotifier.completeNextStep` 走 `POST /tasks/{id}/complete` 同一服务端终态端点，任务身份归属服务端单一真源；本地读模型经 `load()` 回源收敛，不存在第二数据权威。验收文本要求的是「看到同 task/version」（数据收敛）+「重复点击一次写入」（写入合流），两者都满足。并入 TaskListNotifier 反而要把 goal 奖励链/事件 source 搬家，制造新风险；J-08 自有链保持是保守侧正确选择。limitations #2 如实登记。**不阻塞，架构动作留待有真实需求时另立 ADR。**

### CH-4 终态任务拖拽路径未封禁 —— **裁决：风险降级为 latent，本卡不整改；一行守卫列为廉价加固建议**

R1 独立核实：`DraggableTaskCard`（`lib/shared/widgets/draggable_task_card.dart:19`，全库唯一 `LongPressDraggable`）**零调用点**（lib/ 与 test/ 均无）——拖拽源从未接线，`CalendarDayDragTarget` 挂在网格上但无物可拖，终态拖拽路径当前不可达。按钮侧封禁（`isTerminal` :1195-1197）已覆盖唯一活入口。服务端对终态 updateTask 的行为无需在本卡裁决。建议：若未来接线拖拽源，在 `_handleTaskDropped` 补同一 `isTerminal` 守卫（一行，可并入 C-1 修复提交，非义务）。

### CH-5 证据测试 harness 强度 —— **裁决：充分**

对照 diff 独立核实 u08_evidence_test：挂真实 `CalendarStatsScreen`（非抽私有函数）、`_SilentApiClient` 全动词禁真网、Hive/secure_storage 触点打桩、断言链=按钮存在→语义名→终态反面→真实 `CalendarDatePicker`（showDatePicker 产物）→确认闭环走 `_rescheduleTask`→`rescheduleTaskDueDate`→fake repo `updateTask`。未被 harness 短路。唯一弱点：确认闭环未断言 `repo.lastUpdate`（写入断言由 provider 侧统一测承载）——可接受。对照「拖拽路径无同等级 widget 测试」的现状，本测证据等级只高不低（且拖拽是死 UI，见 CH-4）。

## 3. R1 自有发现

### F-1（条件项 C-1，唯一阻塞合并的整改）：`_coalesceStepWrite` 影子 Future 未处理异步错误

- 位置：`goal_detail_provider.dart:64-70`（`_coalesceStepWrite` 内 `unawaited(future.whenComplete(...))`；task_provider.dart:186-198 同构但见下）。
- 机理：`future.whenComplete(cb)` 返回的 Future 在原 Future reject 时携带同一错误；`unawaited()` 只压制 lint 不挂监听 → 该错误成为 zone 未处理异步错误。goal 三步进（start/undo/complete）`rethrow`，**每次失败的 goal 步进写都会在调用方 catch 之外多产生一个未处理 zone 错误**。
- R1 亲证：探针（已删，可按 §5 复现）——门控并发双击 + API post 抛错：`posts==1`、`identical(e1,e2)==true`（合流本身正确）三个 expect 全过，但测试因 `Exception: network down` 未处理错误报告失败，栈经 `goal_detail_provider.dart:62 _coalesceStepWrite`。
- 影响面界定：TaskNotifier 四写路径的 coalesced Future **永不 reject**（completeTask 全 catch 返 null；delete/abandon/reschedule 经 `_runWithErrorHandling` 全 catch）→ 影子不泄漏；泄漏**仅限 GoalDetailNotifier 三方法**。无数据/双写后果，调用方错误处理不受影响；危害=错误卫生 + **测试毒性**（任何未来覆盖 goal 失败路径的测试都会被该影子错误误杀）。
- 修复（一行/处，两处同改保持同构）：`future.whenComplete(() { ... }).ignore();`（或 `.catchError((Object _) {})`）。注释里对 `Map.remove` 返回值已显式 `.ignore()`，同款处理即可。
- 复验义务：修复后跑 §5 命令组（原 +9/+1 两套件绿 + analyze 零 + 若按 §5 重建探针应无未处理错误报告）。

### F-2（登记，不阻塞）：outbox 入队期无 dedupeKey 查重——见 CH-1，属既有离线链行为，如需 belt-and-braces 另卡。

### F-3（登记，不阻塞）：拖拽源死代码——见 CH-4。顺带指出：SCREEN_FAMILIES 的「拖动」在日历页目前无真实实现面，本卡的「键盘/按钮替代」实际是唯一入口，卡验收②因此以更强姿态满足。

### F-4（记账口径，无红藏风险）：「回归 task/calendar/goal +119」是证据测试文件入箱前的快照（110 基线 + unified 9）；R1 现跑同命令 **+120**（含 u08_evidence_test 1 测），方向为多绿非少绿。

### F-5（既有面观察，非本卡引入）：`_rescheduleTask` 对内吞错误的 `updateTask` 仍会 `AppFeedback.success`（失败落 state.error 但弹成功 snack）——旧拖拽路径同构行为，非 U08 退化；建议随手在 C-1 提交里给 `_rescheduleTask` 补失败分支（非义务）。

## 4. 红线与数字复核

- RF-06 三冲突面（dashboard_screen / compact_status_bar / task_execution_screen）+ backend/ + proto/：`git diff a8f46650..98dd980d --` 上述路径**空输出**（R1 亲跑）✓
- l10n：双语 arb 各 +1 键 `calRescheduleAction`，既有键零漂移（diff 逐行核对）；gen 三件与 arb 一致；L10N-REGEN-PARITY 10180 键 PASS（R1 亲跑）✓
- 五守卫 R1 亲跑全 PASS（L10N/i18n-coverage/ui-tokens/spacing/AU）✓；`flutter analyze --no-pub lib test` 零 issue（R1 亲跑）✓
- 证据 artifacts sha256 与 run_manifest 一致（R1 亲算）✓；tasks.json 证据提交仅 status/evidence_summary 手术改动，验收文本零弱化 ✓
- 10 新测分解：unified_action_semantics_test 9（3+2+4，每验收面一正一反）+ u08_evidence_test 1 ✓
- 回归亲跑：task/calendar/goal +120 全绿；widget 467 / home+plan+offline 198 / app 39 / 金标 1 未全数重跑（抽一大类已覆盖本卡全部触碰面；其余信任在册并在合并后 integration SHA 复验清单内）。
- 零模型调用、无凭据/私密材料、无 Mock 冒充 ✓

## 5. 复现命令（R1 全部亲跑）

```bash
cd /Users/brsama/code/GitHub/wtU08/mobile
flutter test test/features/task/presentation/providers/unified_action_semantics_test.dart   # +9
flutter test test/features/calendar/presentation/screens/u08_evidence_test.dart            # +1
flutter test test/features/task/ test/features/calendar/ test/features/goal/               # +120（自述 119=证据文件入箱前口径）
flutter analyze --no-pub lib test                                                          # No issues found!
cd .. && python3 scripts/guards/check_l10n_regen_parity.py                                  # OK 10180
# 突变1：unified_calendar_provider.dart:157 `?? 0` → `?? task.estimatedMinutes` → unified 测 +8 -1；还原
# 突变2：task_provider.dart:182 `final existing = _inFlightWrites[key]` → `= null` → unified 测 +7 -2；还原
# F-1 探针：临时 _FailingGoalApiClient(post 抛错+门控) 挂 goalDetailProvider('goal-1')，
#   门控并发双击 startNextStep → posts==1/identical 错误实例成立，但测试收到未处理 Exception 报告（栈经 _coalesceStepWrite）
```

## 6. 合并落差

- U08 12 个改动文件 vs fleet main（含 S01 收口 39a2bbf0，当前 fcbc4494）自基线以来的 mobile 改动（5 文件，全在 core/design + 其测试）：**交集为空**；`git merge-tree` 冲突标记 **0**。协调方提示的 U04 task 面已在基线 a8f46650 内，无落差。
- 行为近邻（非冲突）：S01 改 `sparkle_pressable.dart`，U08 新增按钮消费 `SparkleIconButton`（底层可能经 pressable）——文本合并干净，行为交互按 integration_reverify 清单在集成 SHA 复验。

## 7. 裁决落地

- **APPROVE_WITH_CONDITIONS**：C-1 = F-1 一行修复（两处 `.ignore()`）+ §5 复验，在本分支完成即可合并；不需二次独立审查（修复机械、判定标准客观：探针无未处理错误报告 + 两套件绿 + analyze 零）。
- 非阻塞建议（不派义务）：outbox 入队期 dedupeKey 查重（另卡）、日历拖拽源接线时补终态守卫、热力图例「专注=实测」文案、`_rescheduleTask` 失败分支。
- 临时探针已全部删除（工作树仅余本 receipt）。

— wtU08R1，2026-09-29
