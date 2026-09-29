# FIX-587 复现定谳（Q01 偶发 vs 确定性）

## 错误门真实位置（find/grep 实查，非推测）

- 屏门：`mobile/lib/features/task/presentation/screens/task_list_screen.dart` `_buildTaskList`（修前 L362）
  `if (state.error != null && state.tasks.isEmpty) → CustomErrorWidget.page(...)`；空态引导在其后 `if (tasks.isEmpty)` 分支（EmptyStateType.noTasks + 「创建第一项任务」→ `/tasks/new`）。
- 污染源：`mobile/lib/features/task/presentation/providers/task_provider.dart`
  `TaskNotifier` 构造器并行 `Future.wait([loadTodayTasks(), loadRecommendedTasks(), loadTasks()])`，三者共享同一 `error` 位；`loadTasks` 成功路径不写/不清 error → 兄弟读（today/recommended）失败置位后**粘滞**。

## 最小复现（真实 TaskNotifier 流水线，仅仓库打桩）

测试文件 `mobile/test/features/task/presentation/screens/task_list_screen_zero_task_error_gate_test.dart`（Completer 控制完成时序，双时序钉死）：

| 用例 | 场景 | 修前 | 修后 |
|---|---|---|---|
| T1 | 三读全 200-空（后端 `/tasks`={data:[],meta}、`/today`=[]、`/recommended`=[] 的客户端等价形，unwrapList/parsePaginated 全兼容） | **绿**：空态引导，无 error | 绿 |
| T2 | today 失败一次（败先序）+ 列表成功为空 | **红**：全页错误态（「今天还没有待办事项」Found 0） | 绿：空态引导 + SnackBar 非阻断提示，`error!=null && tasks.isEmpty` 但 `listError==null` |
| T3 | 列表先成功，today 后失败（败后序·粘滞竞态） | **红**：同上 | 绿：同上 |

修前红跑日志：`repro_prefix_red.txt`（EXIT=1，T1 过 / T2、T3 红；该轮为修复前置文件版，行号与最终版略有偏移，行为结论不受影响）。

## 定谳

**机制确定性成立，两线观察相容，同一机制：**

1. 「合法空列表」本身**不**触发错误门——T1 修前即绿：三接口全 200 空载荷在客户端解析干净，不置 error。「门把空误判为错误」的准确表述是：**门无法区分「列表自身失败」与「列表成功为空但兄弟读失败」**（共享 error 位 + 粘滞）。
2. 任一兄弟读失败一次（无论先于还是后于列表成功）→ 全页错误态**确定性**渲染；重试（refreshTasks 顺序重跑三读）期间兄弟读持续失败则错误态持续（重试无效）。
3. 主线 r6「偶发」= 兄弟读**瞬时**失败（如冷启动首包超时/鉴权时序一次性失败）；幽灵线 r6/r7 三轮「确定性」= 该环境兄弟读**每轮必败**。渲染对前置条件（error 位置位 ∧ 列表空）是确定性的，触发频率由环境决定——两线不矛盾。
4. 真实环境触发源（integration 全栈跑、网关 /tasks* 三接口 200 仍置 error）在客户端单测不可观测，最可能为 today/recommended 读的请求级失败（超时/鉴权时序），见 limitations。
