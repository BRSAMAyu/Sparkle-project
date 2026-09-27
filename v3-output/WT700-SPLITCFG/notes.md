# WT700-SPLITCFG · V3-FIX-385① 修复笔记

- 分支：`agent/node-b/wt700/splitcfg`（worktree `/Users/brsama/code/GitHub/Sparkle-sysrev/wt700-splitcfg`）
- 代码 commit：`221daa0a`（fix(mobile): taskReminderConfigProvider 真分裂双定义收敛为单一事实源）
- 台账：`v3/06_agent_fleet/DYNAMIC_ISSUES.md` V3-FIX-385 行 Status 单元格内注记"①taskReminderConfigProvider 已修@221daa0a"，整行保持 OPEN（②~⑥ 未修）
- 台账 verify：`python3 scripts/devtools/ledger_union_merge.py --verify v3/06_agent_fleet/DYNAMIC_ISSUES.md` → 通过，290 行裸管分布 {8: 290}，零 FAIL

## 一、读写面全景（修前）

`taskReminderConfigProvider` 全 lib 共 2 处定义、5 个消费文件：

| 绑定 | 位置 | 角色 |
|---|---|---|
| `StateNotifierProvider<TaskReminderConfigNotifier, TaskReminderConfig>` | `mobile/lib/features/user/presentation/providers/settings_provider.dart:179` | 设置写面：`_loadFromSettings()` 经 `userRepositoryProvider.fetchUserSettings()` 从服务端装载（`task_reminders_enabled` / `task_reminder_times`）；`updateConfig()` 乐观更新 + `updateUserSettings` 服务端持久化 + 显式 `scheduler.refreshAllReminders(tasks, config: newState)` |
| `StateProvider<TaskReminderConfig>`（恒默认值） | `mobile/lib/core/services/task_notification_scheduler.dart:269` | 执行读面：全库无任何写入点（grep 无 `.notifier`），永为 `const TaskReminderConfig()`（enabled=true, [1440,60,15]） |

消费绑定（经 import show 子句决定各自绑到哪个容器）：

- `task_provider.dart:12-16` → scheduler 侧（show `taskReminderConfigProvider`）→ 执行面读取 `:231/:285/:819`（createTask/updateTask/snoozeTask 的 `scheduleTaskReminders/rescheduleTaskReminders(config:)`）——**读到的是永不更新的默认容器**
- `task_reminder_settings_screen.dart:13-14` → settings 侧（show）→ watch + `updateConfig` 写入
- `unified_settings_screen.dart:541` → settings 侧（settings_provider 整库导入）→ watch
- `settings_provider.dart:8-9` → scheduler show `TaskReminderConfig, taskNotificationSchedulerProvider`（类与调度器，非配置 provider）

两侧模型类型同型（同为 scheduler 定义的 `TaskReminderConfig`），但状态容器独立——即"真分裂双定义"：设置 UI 改提醒配置后，任务创建/更新/顺延的提醒调度永远用默认配置，配置静默失效；全库靠 3 处 show 子句压住编译期命名歧义。

## 二、修复方案（单一事实源）

- 删除 `task_notification_scheduler.dart` 的 `StateProvider` 重复定义（附注释指向单一源），`taskNotificationSchedulerProvider` 不变
- `task_provider.dart` 改从 `settings_provider.dart` show 导入 `taskReminderConfigProvider`，执行面三处读取改绑设置面容器
- 产品语义保持：设置改动经既有 `updateConfig` 的 `refreshAllReminders` 对存量提醒生效；新增/变更任务经执行面读取即时拿到当前配置；未引入新的全局可变态（被删 StateProvider 本就无写入点）
- show 子句清理：歧义源已删，`task_provider` 的 scheduler show 列表收窄为 `TaskNotificationScheduler, taskNotificationSchedulerProvider`；`unified_settings_screen`（`show TaskReminderConfig`）与 `task_reminder_settings_screen` 两处 show 均仍有真实使用，保留

## 三、红先行证据（修前真实输出）

测试：`mobile/test/features/task/presentation/providers/task_reminder_config_wiring_test.dart`
手法：容器注入假 scheduler 捕获 `scheduleTaskReminders` 实收 config——即 task_provider 内 `_ref.read(taskReminderConfigProvider)` 的真实返回值；设置面走真实 `TaskReminderConfigNotifier.updateConfig` 路径（乐观更新 + 假服务端持久化）。

修前运行（`flutter test test/features/task/presentation/providers/task_reminder_config_wiring_test.dart`）：

```
00:00 +0 -1: V3-FIX-385① taskReminderConfigProvider 单一事实源 设置面修改提醒配置后，执行面 task_provider 调度收到新配置 [E]
  Expected: false
    Actual: <true>
  用户在设置面关停提醒后，任务执行面调度必须读到关停（修前：执行面读 scheduler 侧独立 StateProvider，恒为默认 true，静默失效）
```

设置面已写 `enabled=false` 并持久化（`server.settings['task_reminders_enabled'] == false` 断言通过），执行面调度实收 `enabled=true`（默认容器）——split-brain 复现。

## 四、修后绿证据（真实输出）

```
00:00 +1: All tests passed!   （task_reminder_config_wiring_test.dart）
```

受影响面批量（9 文件 69 用例）：

```
flutter test \
  test/features/task/presentation/providers/task_reminder_config_wiring_test.dart \
  test/features/user/presentation/providers/settings_provider_test.dart \
  test/features/user/presentation/providers/notification_settings_p06_test.dart \
  test/features/user/presentation/providers/onboarding_pending_state_test.dart \
  test/features/task/presentation/providers/task_provider_test.dart \
  test/features/task/presentation/providers/task_offline_queued_test.dart \
  test/features/task/presentation/providers/task_complete_sync_test.dart \
  test/features/task/presentation/providers/task_chat_dormant_test.dart \
  test/features/task/presentation/screens/task_list_screen_test.dart
00:06 +69: All tests passed!
```

`flutter analyze`：`No issues found! (ran in 6.9s)`

## 五、diff 摘要（commit 221daa0a，3 files，+311/−7）

- `mobile/lib/core/services/task_notification_scheduler.dart`：删 `taskReminderConfigProvider` StateProvider 定义，留单一源指路注释
- `mobile/lib/features/task/presentation/providers/task_provider.dart`：scheduler show 子句移除 `taskReminderConfigProvider`；新增 `settings_provider.dart show taskReminderConfigProvider` 导入（读取点 :233/:287/:821 本体不动）
- `mobile/test/features/task/presentation/providers/task_reminder_config_wiring_test.dart`：新增回归测试（N35/P-06 既有 harness 风格：`extends` 桩 + provider override）

## 六、备注

- ②translationHistoryProvider、③sharedPreferencesProvider、⑤firebaseMessagingServiceProvider+fcmInitializedProvider、⑥死代码 4 名未动（不在本卡范围）
- 无新问题需登记（行为与 wt696 普查完全一致，未发现额外面）
