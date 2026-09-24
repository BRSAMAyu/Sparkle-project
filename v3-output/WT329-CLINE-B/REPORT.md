# WT329 — mobile C 线批 B：数据口径一致性（F-9）+ 刷新横幅（F-11）

- 工号：wt329
- 分支：`wt329-mobile-cline-b`（基于 main @ a9a2e993；main 随后推进的 wt328 提交与本卡文件零交集）
- 日期：2026-09-25
- 工作树：/Users/brsama/code/GitHub/Sparkle-sysrev/wt329-mobile-cline-b
- 内存档位：LIGHT（无模拟器 / 无 Gradle / 无浏览器；`flutter analyze`、`flutter gen-l10n` 短进程）

---

## 一、F-9 口径考古（先考古后动手，逐处列数据源与计算式）

| 展示位 | Widget / 文件 | 数据源链路 | 计算式 |
|---|---|---|---|
| 多目标看板「100%」 | `_GoalRow` → `_HealthPill` / `_MetaPill(pie)`（multi_goal_dashboard_card.dart） | `multiGoalOverviewProvider` ← spine `mastery/health_score`（兜底 `1-bottleneck`）或 plan `healthScore ?? progress`；timeFraction ← arbitration `time_split` | `(healthScore*100).round()%`、`(timeFraction*100).round()%`——**均非任务进度**；单目标时 timeFraction 恒 1.0 → 恒显「100%」，被用户读成进度 |
| cockpit chip「0/1」 | `_GoalContextRow`（today_cockpit_card.dart） | `todayCockpitProvider` → `homeGrowthStateProvider.tasksTotal/tasksCompleted` ← GET `/tasks/today` | 后端该端点返回**裸列表**（`response_model=list[TaskDetail]`，无聚合字段），客户端回落 `total=list.length`、`completed=list.count(isCompleted)`。而列表构成由 `DailyTaskSelectionService._is_today_relevant` 逐日漂移（已完成仅当日、无日期任务仅创建当日/计划日内）→ **chip 在 1/4 与 0/1 间漂移的根因** |
| 任务面板「完成 0/1」 | `_summaryLabel`（task_board_card.dart） | `taskBoardTodaySummaryProvider` → `taskListProvider`（GET /tasks 账本）经 `tasksDueOn(now)` 过滤 | `今日{total}项·已完成{completed}`，只计 due_date==今天——账本同屏可见「共 4 项、已完成 1」，头部却说 0/1 → **自相矛盾** |
| 任务真相 1/4 | `taskListProvider`（GET /tasks，无 status 过滤=全量含 completed） | — | 任务账本 |

### 裁决：权威真源 = 任务账本（taskListProvider）

理由：`/tasks/today` 是「现在做什么」的**选择流**（ranked、capped、构成逐日漂移），不是账本；due-today 是「今日分组」口径（引擎 goal_today_view.py 单一事实源，S7 保留），不是进度口径。三处进度数字必须同源。

### 最小化对齐（修复后三处同一状态同一数字）

1. **task_board_provider.dart**：新增口径单一定义点 `ledgerProgressOf(tasks, {planId})`（total=非 abandoned、completed=status==completed）+ `taskBoardLedgerSummaryProvider`（全账本）+ `ledgerProgressByPlanProvider`（按计划）。删除旧 `taskBoardTodaySummaryProvider`/`TaskBoardTodaySummary`（唯一消费面就是旧头部，见下）。
2. **task_board_card.dart**：头部汇总改用 `taskBoardLedgerSummaryProvider`，l10n 换 `taskBoardProgressSummary`（zh「共{total}项·已完成{completed}」/ en「{total} tasks · {completed} done」）与 `taskBoardNoTasksYet`（暂无任务）。**S7 的 `tasksDueOn` 与今日/逾期分组原样保留**；S7 注释同步改写（分组仍共用 tasksDueOn，进度不再经今日过滤派生）。
3. **today_cockpit_provider.dart**：VM 新增 `goalTasksTotal/goalTasksCompleted`（选中目标名下账本进度，目标无账本任务时回落全账本；goal.id 与 task.plan_id 同一 id 空间），文档真源表同步；`dependencies:` 追加两个新 provider。旧 `tasksTotal/tasksCompleted` 保留但**只**用于 fresh/active 态判定与 why 文案，不再渲染为进度。
4. **today_cockpit_card.dart**：进度 chip 改渲染 `goalTasksCompleted/goalTasksTotal`。
5. **multi_goal_dashboard_card.dart**：goal 行新增第一枚进度 pill `x/y`（账本按 planId 口径，total=0 不渲染）。health%/timeFraction% 保留（真实指标、图标区分），但进度信号不再缺位——「100% 被读成进度」的错位由显式 x/y 化解。
6. l10n：app_en.arb / app_zh.arb 新增两键并 `flutter gen-l10n` 再生成（旧键 `taskBoardTodaySummary`/`taskBoardNoTasksToday` 已无 lib 引用，暂留 arb 作回滚余地，下批可收割）。

## 二、F-11：401→refresh→重放两分支

排查结论：`AuthInterceptor.onError`（core/network/api_interceptor.dart）**已实现** 401 → `TokenRefreshCoordinator.refreshOnce`（全局单飞）→ 用新 token 经 `_getRetryDio()` 重放原请求；重放成功 `handler.resolve`（横幅无条件不出现）；重放仍失败时原 401 冒泡（横幅才被允许）。任务列表三条加载路径（loadTodayTasks/loadTasks/loadRecommendedTasks）均走同一 apiClient，无旁路。transient 横幅与「refresh 自身可重试失败（网络/5xx/429 限速）→ 原 401 放行」的路径吻合，属设计内行为。

本卡补齐的是**拦截器级测试缺口**（原只有 header-less 变体回归）：新增 `mobile/test/core/network/auth_interceptor_401_replay_test.dart`，fake dio adapter 三分支：
- A：带头 401 → refresh → 重放 200 → 调用方拿 200，refreshCalls=1，logout=0；
- B：重放仍 401 → 错误冒泡（横幅允许），refresh 恰一次（无循环），**不登出**（会话有效，AUTH-DEEP B-3）；
- C：重放 5xx → 同 B。

## 三、测试与验收状态

| 项 | 状态 |
|---|---|
| 新增 `progress_consistency_f9_test.dart`（ledgerProgressOf 纯函数 ×3 + 三面同数 widget test：同屏断言 chip=goal 行=`1/4`、头部=`4 tasks · 1 done`、且 `/tasks/today` 漂移快照 `0/1` 与 due-today 口径 `1 tasks · 0 done` 退场） | 已交付，**执行 DEFERRED** |
| `today_cockpit_card_test.dart`「active」用例改账本供数（锁新契约），harness 增 `extraOverrides` 透传与 `staticTaskListOverride` 帮助器 | 已交付，**执行 DEFERRED** |
| `auth_interceptor_401_replay_test.dart` 两分支 | 已交付，**执行 DEFERRED** |
| `flutter analyze` gate（容差 5） | **PASS**：E0 / W15 / I598（预算 594+5）；改动文件自身 0 告警 |
| `bash scripts/run_all_rule_guards.sh` | **PASS**：83 rules exit 0（AQ/BG 曾因 worktree 缺 gen 假失败，cp -RL 三处 gen 后全绿） |
| mypy 棘轮 1615 | 本卡零 backend 改动，不触碰 |
| 定向 `flutter test --concurrency=1` | **DEFERRED**：swap 门不达（实测 955M→1075M free，门限 ≥1.2G），代码照常完成；同 wt328 先例 |

**DEFERRED 风险注记**：测试未执行，三面同数断言的首轮跑绿由主会话在内存窗口复验（建议 `cd mobile && flutter test test/features/home/progress_consistency_f9_test.dart test/core/network/auth_interceptor_401_replay_test.dart test/features/home/presentation/widgets/today_cockpit_card_test.dart --concurrency=1`）。

## 四、本卡触碰文件清单（供主会话合并态复验，尤其 today_cockpit_card.dart 战区）

代码（7）：
- mobile/lib/features/home/presentation/providers/task_board_provider.dart
- mobile/lib/features/home/presentation/providers/today_cockpit_provider.dart
- mobile/lib/features/home/presentation/widgets/task_board/task_board_card.dart
- mobile/lib/features/home/presentation/widgets/today_cockpit_card.dart（**wt326/wt327 战区**：仅 `_GoalContextRow` 内 chip 一处 5 行改动，未触碰 316 行附近 F-6 调用点/CTA 结构；未碰 chat 长建议渲染与 J-02 CTA）
- mobile/lib/features/home/presentation/widgets/multi_goal_dashboard_card.dart
- mobile/lib/l10n/app_en.arb、app_zh.arb + 三个 app_localizations*.dart（gen-l10n 产物）

测试（3 改 2 新）：
- mobile/test/features/home/dashboard_test_harness.dart（删旧 summary override、加 extraOverrides 参数与 staticTaskListOverride）
- mobile/test/features/home/presentation/widgets/today_cockpit_card_test.dart（active 用例账本供数）
- mobile/test/core/network/auth_interceptor_401_replay_test.dart（新）
- mobile/test/features/home/progress_consistency_f9_test.dart（新）

## 五、沿途记录（未修、留档）

1. **GET /tasks 分页 50 上限**：账本进度取自客户端内存列表，>50 任务时计数封顶（旧 today 汇总同样受限，非本卡回归）。后续可用 `meta.total` + completed 专用查询加固。
2. **多目标场景 scope 差异**：goal 行/cockpit chip=选中目标口径，任务板头部=全账本口径；单目标（F-9 证据态）三处严格同数，多目标下头部为「所有目标总进度」——已在 provider 注释声明，如需逐目标头部再拆。
3. **arb 旧键遗留**：`taskBoardTodaySummary`/`taskBoardNoTasksToday` 已无引用，暂留 arb，下批 l10n 清理时收割。
4. **健康度/时间占比 pill 仍在**：多目标行保留 health%（雷达语义）与 timeFraction%（饼图语义），进度语义由新增 x/y pill 承担；若产品侧仍认为歧义，可后续给 % pill 加文字标签（未动，避免超卡面）。
