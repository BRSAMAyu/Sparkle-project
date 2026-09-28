# V4-U08 差量与证据说明（diff_or_evidence_only）

## 0. 一句话设计

同一动作（完成/放弃/删除/改期）在任务/计划/日历/目标四个页面收敛到同一条写入链
（`TaskListNotifier` / `GoalDetailNotifier` 各自唯一权威点），在飞写入按「任务+操作」
合流保证重复点击一次落库；日历改期补键盘/按钮路径（拖拽不再是唯一入口）；
专注与分享证据只认实测时长，估时回归计划意图；删除与放弃维持两种可区分的结局。

## 1. 行为差量（相对 main@a8f46650）

### 验收1：四页面看到同 task/version；重复点击一次写入
- `task_provider.dart`：`TaskNotifier` 新增 `_inFlightWrites` 合流表（键=`操作:taskId`），
  `completeTask` / `abandonTask` / `deleteTask` 在飞时重复触发返回同一次写入的
  Future；在飞结束即摘除（`identical` 防误摘并发新写）。守卫只存在于写入窗口，
  不吞掉后续合法重试。
- 新增 `rescheduleTaskDueDate(id, dueDate)`：改期唯一写入口（键=`reschedule:taskId`），
  内部走既有 `updateTask(TaskUpdate(dueDate))` 全链（提醒重排/日历联动/读模型刷新
  零重复实现）。
- `goal_detail_provider.dart`：`GoalDetailNotifier` 同制守卫 `_coalesceStepWrite`，
  `startNextStep` / `undoStartNextStep` / `completeNextStep` 双击合流为一次 POST。
- 读模型面零改动：四页面任务数据本来就同源于 `taskListProvider`（任务列表/日历
  agenda/计划详情）与服务端 goal-detail 读模型（目标页），本卡未造第二权威。

### 验收2：改日程有键盘/按钮路径，不仅拖动
- `calendar_stats_screen.dart`：
  - 日历 agenda 任务卡新增「改期」`SparkleIconButton`（`calRescheduleAction`
    语义名，48 触控档，焦点/键盘可达），点击打开标准 `showDatePicker`
    （普通控件，可键盘导航）→ 确认后写入。
  - 拖拽确认（`_handleTaskDropped`）与按钮路径收敛到同一 `_rescheduleTask` →
    `rescheduleTaskDueDate` 单一写入链 + 同源月聚合刷新；拖拽本身保留不删。
  - 终态任务（完成/放弃）不渲染改期按钮（改期语义只对未完成任务成立）。

### 验收3：计划时长不作为完成证据；删除/放弃不同语义
- `unified_calendar_provider.dart`：月聚合 `focusMinutes` 从
  `actualMinutes ?? estimatedMinutes` 改为 `actualMinutes ?? 0`——估时不再顶替
  实测进热力/概要（X-04 红线在读取侧的延伸；无实测不造专注）。
- `task_detail_screen.dart`：分享卡 metadata `duration` 只在 `actualMinutes` 存在时
  携带；海报端 `_durationMinutes(null)` 本就跳过该指标，无海报侧改动。
- 删除/放弃语义已有区分（不同端点/不同确认文案/不同结局），本卡以测试钉死：
  放弃保留记录仅置终态（星图/日历历史可见），删除移除条目并清日历联动事件，
  且互不降级（abandon 不触发 delete 写入、delete 不降级为 abandon）。

### l10n
- `app_zh.arb` / `app_en.arb` 各 +1 键：`calRescheduleAction`（改期 / Reschedule）。
  `flutter gen-l10n` 再生，零既有键改动（L10N-REGEN-PARITY 10180 键 PASS）。

## 2. 证据面（本目录）

- `screenshots/u08_calendar_reschedule_button.png`：日历月视图 + agenda 原始态——
  待办卡带「改期」按钮（trailing 图标对），已完成卡同屏无该按钮（反面同帧可对照）。
  CJK 字形为测试环境 Ahem 方块（F04/U01/U05 同先例）。
- `screenshots/u08_calendar_reschedule_button_semantics.txt`：RenderParagraph 全量
  dump（待办/已完成标题、`待办 · 2026年9月29日 00:00` 等原文）+ 关键语义节点段
  （`label="改期" rect 48×48 actions=tap`）。交互闭环（点击→日期选择器→确认→
  写入反馈）由同测断言承载。

## 3. 红线自检

- 「统一行动语义」不造第二权威：合流守卫内嵌在既有唯一 provider 写入口；
  未新增任何 repository/service/存储；数据面只读既有读模型。
- RF-06 三冲突面（dashboard_screen / compact_status_bar / task_execution_screen）
  与五 Tab 路由、classic 通道：零 diff。
- backend / proto / 迁移 / 路由：零触碰（无 OpenAPI/BA-ROUTES、无 sync-db 义务）。
- 参考图未充当批准：本卡无新视觉档，全部既有 DS 组件（SparkleIconButton/ListTile/
  showDatePicker），UI 消费 core/design 令牌，屏幕命名规范未破坏。
- 参考实现事实核对：合流守卫不改变离线入队（OfflineEnqueuedException）与
  M6-03 同步状态语义（task_complete_sync_test 等既有 119 测全绿回归证明）。

## 4. 已知限制与预登记挑战

见 `limitations.md` 与 `review_receipt.json`（5 条挑战点）。
