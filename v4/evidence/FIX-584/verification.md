# FIX-584 verification — G5 校准投影缺口（向导直达分支）

被测：`agent/v4/f584` @ 本地工作树（base `146feddf`，未 push）· 2026-09-29 · wtF584
所有命令 exit code 均记录；macOS 无 `timeout` 命令，长跑用 flutter test 直写日志 + 后台任务。

## 1. 取证定性（读证 → 代码链，先证后修）

| # | 证据 | 结论 |
|---|---|---|
| 1 | Q01 `diff_or_evidence_only.md` §3 G5 + limitations §3 | 校准区锚点只读 `taskListProvider` 投影；向导直达执行面时投影未含新任务 → baselineMinutes=null →「调整这次行动」hasAnchor 门如实结构性缺席 |
| 2 | Q01 `db/r1_attempt10` 与 `db/r5_part1`：calibration_runs 1 行 + tasks 4 行 estimated_minutes=25 | 服务端数据在场，缺的是**客户端投影填充** |
| 3 | `git grep` 链路实查：`stuck_journey_sheet._resolveBaselineMinutes`（:121）→ `goal_creation_wizard_screen` `onStartFirstTask`（:474）直接 `router.go('/tasks/<id>/execute')` | 向导直达分支全链**零** `taskListProvider` 填充调用；pilot 种子面无此缺口（任务先于 TaskNotifier 构造存在，构造期 loadTasks 即含锚点） |
| 4 | `backend/app/api/v1/tasks.py:338` list_tasks 全量分页（无 today 过滤） | **证伪**姐妹会话「投影按 today 过滤」猜想：只要投影刷新过，向导任务必达 |
| 5 | Q01 r5 console（`attempt12_r5_console.log` :6470→6485）时间线 | 水化绕道 step 标 PASS 但期间**零 `GET /tasks` 请求**——driver 拖拽未真正触发 `RefreshIndicator.onRefresh`，绕道从未生效；Q01 limitation §3 的「r5 仍 null」由此解释，投影口径无需产品改 |

定性一句话：**缺口 = 向导直达分支独有的投影填充缺失，非服务端数据缺失、非投影口径过滤。**

## 2. 修复（收敛单一填充函数）

`mobile/lib/features/goal/presentation/screens/goal_creation_wizard_screen.dart` `_createGoal()` 创建成功分支（`onCreated` 分流之前，两分支共覆盖）：

```dart
unawaited(ref.read(taskListProvider.notifier).refreshTasks());
```

- 唯一填充函数 `TaskNotifier.refreshTasks()`（与任务列表下拉刷新同源，零第二实现）；
- `unawaited` 裁决见 run_manifest.json `fix.design_rationale`（await 形态被邻域既有测试 + UX 双重否决，实证见 §3.3）。

## 3. 回归与 mutation（可失败测试双向亲跑）

### 3.1 新增回归（`goal_creation_wizard_projection_fill_test.dart`，2 例）

- ① **填充钉**：真向导屏 + 真仓库 + 传输 mock，创建成功后 `taskListProvider.tasks` 含新任务（25min，due_date=null）；
- ② **锚点钉（G5 面端到端）**：同容器水化后挂真实 `StuckJourneySheetBody`，纠正提交进 scopeChoice 相 → `调整这次行动` 在场 + 无锚点说明文案不在场。

### 3.2 Mutation：回退修前形态红 / 还原绿

| 步骤 | 命令 | 结果 | exit |
|---|---|---|---|
| 修前形态 | `git checkout -- <wizard 屏>` 后 `flutter test <新测试>` | `0 passed / 2 failed`；①`Actual: WhereIterable<TaskModel>:[]`（投影空）；②`Found 0 widgets with text "调整这次行动"` | **1** |
| 还原修复 | `git apply /tmp/fix584_fix_final.patch` 后同测试 | `+2: All tests passed!` | **0** |

关键行摘录：`raw/mutation_red_key_lines.log`。

### 3.3 邻域回归（含一次真实返修记录）

- 初版 `await refreshTasks()` 形态：邻域跑 `goal_creation_wizard_screen_test` 红（`Expected: 'goal-1' / Actual: <null>`——onCreated 被真实网络时延推迟出 250ms pump 窗）。**不以删断言/放宽既有测试换绿**：改 `unawaited` 终形态后该测试恢复绿。
- 终形态全量邻域（recovery 5 文件 + goal 4 文件 + semantic_motion_wiring_f569）：`+64: All tests passed!` exit **0**（`raw/green_neighborhood_key_lines.log`）。
- 新测试 + 既有向导屏测试合跑：`+7: All tests passed!` exit **0**。

### 3.4 静态检查

`dart analyze`（两变更文件）→ `No issues found!` exit 0。

## 4. 边界

- 运行中 Q01 栈（50051/8000/8080）全程未动；本卡全部为 flutter test 级。
- FIX-583 零文件交集纪律：本卡只触 `mobile/lib/features/goal/` 与 `mobile/test/`，backend 零改动。
- 未做真端复测（真设备/真栈端到端归 Q01 姊妹卡复测轨）；本卡锚点面已被测试②以真实组件树端到端复现。
