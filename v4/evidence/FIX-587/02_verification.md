# FIX-587 修复与验证（含 mutation）

## 修法：列表域错误位分离（空 ≠ 错误）

1. `task_provider.dart`
   - `TaskListState` 新增 `listError`（UiErrorCategory?）+ `copyWith(clearListError:)`——语义：**只归 loadTasks 自身写/清**，兄弟读与各写操作不触碰（默认参数零行为漂移）。
   - `_runWithErrorHandling` 增加 `listScoped` 参数：仅 `loadTasks` 传 true——失败写 `listError`、开始清本域旧错；其余调用点行为与修前逐字一致。
   - `loadTasks` 成功路径 `clearListError: true`（列表自身读成功即清，粘滞断根）。
2. `task_list_screen.dart` `_buildTaskList`
   - 全页错误门改认 `state.listError != null && state.tasks.isEmpty`（只对列表自身失败渲染全页错误 + 重试）。
   - 兄弟读失败且列表为空 → 落空态引导（`EmptyStateType.noTasks` + 创建入口 → `/tasks/new`），失败信号经既有 SnackBar 监听器非阻断呈现；兄弟失败且有行 → 既有部分失败横幅（L289）不变。
3. 既有测试 `task_list_screen_test.dart`：「retry state」fixture 从共享 `error:` 位重指到 `listError:`（FIX-587 新权威；测试钉死的语义「列表自身失败→全页重试错误态→重试恢复」与全部断言不变，仅字段重指，未删断言）。

## mutation 双向亲跑

- 回退修前门（`listError` → 共享 `error` 位，脚本置换断言生效）：`mutation_gate_reverted_red.txt` EXIT=1，`+1 -2`（T2/T3 红=缺陷重现，T1 绿）。
- 还原修复：`mutation_restored_green.txt` EXIT=0，`+3` 全绿。

## 回归（flutter test --concurrency=1，三 tier，find 实查清单）

| tier | 范围 | 结果 |
|---|---|---|
| 1 直接家族 | `test/features/task`（全目录）+ err_canal_provider_error_category + app/router_smoke + widget/h9_ui_sync + widget/j2_frontend_closure | `regression_tier1.txt` EXIT=0，**136 全绿**（首跑 135+1 挂=上述 fixture 字段重指，复跑全绿） |
| 2 消费家族 | home/progress_consistency_f9、today_cockpit_card、stuck_recovery_card、plan_provider、plan_create_guard、u09×3、recovery×2、guest_conversion×2、review_plan_hub、exam_sprint×2 | `regression_tier2.txt` EXIT=0，**85 全绿** |
| 3 golden/style | g01_four_style_golden、g05_family_four_style、g01_four_style_sweep | `regression_tier3_goldens.txt` EXIT=0，**40 全绿** |

合计 261 测试全绿。最终屏级两文件复跑 `final_screen_tests.txt` EXIT=0（+5）。

## 静态检查

`flutter analyze`（4 变更 dart 文件）：No issues found。

## 资源自查

`scripts/devtools/disk_swap_guard.sh`：guard-ok free=39G swap=0MB（回归前后各一轮）。
