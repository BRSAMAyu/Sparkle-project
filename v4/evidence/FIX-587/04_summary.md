# FIX-587 summary（P2：任务列表页错误门——错误态与空态语义分离）

## 定谳结论

缺陷机制**确定性成立**，主线「偶发」与幽灵线「确定性」两观相容、同一机制：`TaskNotifier` 三个并行读共享一个 error 位且成功不清——任一兄弟读（today/recommended）失败一次，error 粘滞；列表自身成功为空时，全页门 `error!=null && tasks.isEmpty` 无法区分「列表失败」与「列表空但兄弟失败」→ 零任务新用户被全页错误态阻断创建路径。触发频率由环境决定（瞬时失败=偶发；环境性必败=确定性）。「合法空列表」本身不触发缺陷（T1 修前即绿：200 空载荷解析全兼容）。

## 修法

列表域错误位分离：`TaskListState.listError` 仅由 `loadTasks` 写/清（`_runWithErrorHandling(listScoped:)` 独占参数）；屏全页错误门只认 `listError`。列表失败→全页重试错误态（原语义保留）；兄弟失败+空→空态引导（创建入口可达）+ SnackBar 非阻断提示；兄弟失败+有行→既有部分失败横幅。其余 20+ 处 `_runWithErrorHandling` 调用点与共享 error 位消费方行为零漂移。

## 回归 + mutation

- mutation 双向亲跑：门回退修前逻辑 → 红（+1 -2）；还原 → 绿（+3）。日志四件齐全。
- 三 tier 261 测试全绿（--concurrency=1，EXIT=0）：直接家族 136 + 消费家族 85 + golden/style 40。既有 retry 测试 fixture 字段重指（`error:` → `listError:`，断言未删）。
- flutter analyze 4 变更文件零 issue；disk/swap 守卫通过。

## 绕行回正评估（只评估，不改 driver——归 Q01 遗产面）

- **结论：可回正。** driver v3.2 绕行（零任务用户直跳 `/tasks/new`，列表页只在创建后访问）所规避的阻断已消除：修后零任务新用户列表页 = 空态引导 + 「创建第一项任务」CTA（T1 钉死）；且兄弟读失败即使再现也不全页拦截。driver 现有「兜底：列表空态 CTA 路径」分支（v4_q01_vertical_journey_test.dart L1327 一带）即回正后的自然主径。
- **回正条件**：需 Q01 driver owner 以回正路径全栈重跑三轮定稳（校准「仅本次」锚点原按绕行路径校准），本卡不代行。
- 台账 `v3/06_agent_fleet/DYNAMIC_ISSUES.md` FIX-587 行已追加本状态。

## 变更清单（main 显式 pathspec）

- `mobile/lib/features/task/presentation/providers/task_provider.dart`
- `mobile/lib/features/task/presentation/screens/task_list_screen.dart`
- `mobile/test/features/task/presentation/screens/task_list_screen_test.dart`
- `mobile/test/features/task/presentation/screens/task_list_screen_zero_task_error_gate_test.dart`（新增）
- `v4/evidence/FIX-587/`（本目录四件 md + 8 份日志）
