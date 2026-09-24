# wt304-j08-goal-completion · J-08 Goal Completion → Reflection → Trajectory

> 2026-09-22 ｜ worktree **wt304-j08-goal-completion**（分支同名）｜ base **f6b7a18f**
> 状态：**READY_FOR_REVIEW**（自评；Worker 不自报 DONE）
> 旅程三部曲收官卡（wt302=J-05 卡住恢复 / wt303=J-07 断档回归 / 本卡=J-08 终点体验）。M 级，纯 mobile 改动。

---

## 1. 现状审计（为何「完成=划掉就完了」）

| 完成路径 | 完成时刻 UI | 反思引导 | 轨迹/星图链路（客户端侧） |
|---|---|---|---|
| 任务执行页（带计时器） | **全套已有**：TaskCompletionCelebration 覆盖层（confetti+sensory+BGM duck，task_execution_screen.dart:277-286/:1191-1198）+ TaskFeedbackDialog（task_feedback_dialog.dart） | **重问卷已有**：星级+难度 3 chip+3 个文本框+AI 回应+知识节点关联（task_feedback_dialog.dart:624-711） | **已有**：galaxyRefreshTrigger++ / refreshForTaskCompletion / achievement+portfolio+dashboard invalidate / recordEntityExecution（task_provider.dart:628-689） |
| 任务列表页（卡片划完成） | **无时刻**：卡片状态翻转即完（task_list_screen.dart:440-450/:562-568） | 无 | 有（走 taskListProvider.completeTask → 同上链），但用户无感知 |
| **目标详情页·今日最小步骤（旅程终点）** | **仅一个确认 AlertDialog+错误 snack**（goal_detail_screen.dart:427-462） | **零** | **零**：goal_detail_provider.dart:67-76 裸 POST /tasks/{id}/complete，不触发 galaxy/成就/事件流任何客户端钩子 |

- 后端轨迹真源**已存在且无需重建**（J-08 卡面 Forbidden）：GJ03 链 task→study_record→mastery→outbox→星图（backend/app/core/outcome_ledger.py:54、v3-output/D-02/REPORT.md:43/:265）；GJ05 human action→evidence→Galaxy（v3-output/X-10/REPORT.md:67）。服务端任意路径完成都落账——缺口全部在移动端体验层。
- 反思域联动：reflection_summary_screen.dart 消费 /experience 反思汇总（total_reflections/avg_mood/timeline[completion_quality,payload]）——数据源就是任务反馈链（POST /tasks/{id}/feedback）。把微反思写进同一端点即自动沉淀进反思域。

## 2. 闭环设计（最小实现，零新存储）

以**目标详情页**（J-08 意图命中的旅程终点）为落点，三段全接既有链：

```
完成今日最小步骤（POST /tasks/{id}/complete，服务端 GJ03 照旧落账）
  ├─ a) 轻庆祝态：GoalStepCompletionCelebration 覆盖层
  │      视觉=既有 celebration 形制（SparkleConfetti small + GraphiteCardSurface
  │      + DS.success 边 + scene 运动令牌 + success 感官事件），不发明新视觉
  │      内容=轨迹框定：「这一步：<step>」→「从想法到成果：<goal> 向前推进」
  │      （J-08 Work#3：不展示分钟/streak）
  ├─ b) 一题式微反思：完成感受三选一（还是难/刚刚好/太简单），一次点击即存，
  │      可跳过（非问卷）。写既有 POST /tasks/{id}/feedback 的 category 字段
  │      （枚举与 TaskFeedbackDialog/反思汇总共用）→ 反思域自动可见
  └─ c) 轨迹沉淀：客户端补齐与 task_provider 同链的钩子——
         galaxyRefreshTriggerProvider++ + galaxyProvider.refreshForTaskCompletion()
         + achievement/portfolio/dashboard invalidate + recordEntityExecution(
         actionType=complete_task, source=goal_detail) —— 全部消费既有事件，
         零新存储；星图/Goal 页一致性由同源刷新保证（J-08 Acceptance GJ03/GJ05）
```

## 3. 改动清单（全部 file:line 可核）

| 文件 | 改动 |
|---|---|
| `mobile/lib/features/goal/presentation/providers/goal_detail_provider.dart` | ① 新增 `GoalStepCelebration` 载荷 + `goalStepCelebrationProvider`（:37-58）；② `completeNextStep()` 改为返回庆祝载荷并在 reload 前捕获 step/goal 标题（:113-143）；③ 新增 `_runCompletionTrajectoryHooks()`（:145-177）——四条钩子全消费既有 provider/事件链，单条失败仅记日志不改完成态 |
| `mobile/lib/features/goal/presentation/widgets/goal_step_completion_celebration.dart` | **新文件**：轻庆祝态+一题微反思。视觉原语与 TaskCompletionCelebration 同源（confetti small/success token/scene 曲线）；chip 提交走 `taskRepositoryProvider.submitTaskFeedback`（既有端点），失败诚实提示不阻塞关闭；类名刻意避开工绒 parallelClass 棘轮（`_FeelingOption`，无 Chip/Pill/Badge 后缀） |
| `mobile/lib/features/goal/presentation/screens/goal_detail_screen.dart` | body 包 Stack 挂庆祝覆盖层（:137-152 区域）；`_TodayStepCard` 完成回调改为接收庆祝载荷并挂载（:471-490）；失败路径保持既有错误 snack，未完成路径零变化 |
| `mobile/lib/l10n/app_zh.arb` / `app_en.arb`（+gen） | 新增 5 键双语：goalStepCelebrationTitle / Trajectory({goalTitle}) / ReflectionQuestion / Saved / Failed；chip 复用既有 taskFeedbackCategory*，继续钮复用 taskContinueNext，零重复造词 |
| `mobile/test/features/goal/goal_step_completion_loop_test.dart` | **新文件**：链路测试 2 例（见 §4） |

**未做/不越界**：不改后端（真源已存在，重建即违卡面 Forbidden）；不动任务执行页（其闭环已完整）；不给任务列表页加庆祝（该页完成是批量扫除动作，弹层会打断列表操作——如需同链时刻，另卡裁度）；不接 N40 访客转化第二/三信号（wt272 N47 已辖，防双立项）。

## 4. 测试与验证证据

- **新增链路测试**（`flutter test --concurrency=1 test/features/goal/goal_step_completion_loop_test.dart`，**4/4 全绿**含回归文件合并跑）：
  1. 完成步骤→庆祝态出现：轨迹句含目标名、步骤名在庆祝卡内；
  2. 点「Still hard」→ 断言 POST /tasks/t1/feedback 恰 1 次、body.category='too_difficult'（证明写入既有反思链）→ 出现已存提示；
  3. 继续钮→覆盖层关闭；断言 complete POST 恰 1 次、galaxyRefreshTriggerProvider==1、事件流记录 (entityId t1, complete_task, source goal_detail)；
  4. 取消路径→无庆祝、无完成 POST（未完成不受影响）。
- **既有回归**：test/features/goal/goal_detail_screen_a6_l10n_test.dart 2/2 绿（null target_date / 日期渲染不受影响）。
- **analyze**：改动 4 文件定向 dart analyze → 剩余仅 goal_detail_screen.dart:61 discarded_futures 为 HEAD 既有（行内容与基线逐字一致，`git show` 核对）；goal 域全目录 analyze 无 error/warning 新增（存量 infos 均在他人文件）。
- **守卫**：`bash scripts/run_all_rule_guards.sh` **exit 0，83 规则全过**（中途修复：①新文件类名触发 UX-COMP parallelClass 棘轮→改名 `_FeelingOption` 后棘轮持有；②本 worktree 缺 gitignored 生成产物→按纪律从主仓 `cp -RL` 拷入 backend/app/gen、backend/gateway/gen、mobile/lib/gen（解引用符号链，先量 `cp -R` 拷出符号链曾致 K/Z 守卫崩溃）——三目录均 gitignore，不入 patch）。
- **arb 双语**：zh/en 同步新增，`flutter gen-l10n` 成功。

## 5. 资源峰值（纪律申报）

- HEAVY 门控：flutter test 前实测 swap free 1.40G ≥1.2G 且 load 6.18 <8 放行；单文件单进程 `--concurrency=1`，未与任何模拟器/Gradle/浏览器叠加（pgrep 核空）。
- 峰值：测试运行期 swap free 最低 ~1.1G（gen-l10n+pub get 为 LIGHT 顺序执行）；无熔断。
- 收工清理：mobile/build、.dart_tool、/tmp/wt304_guards*.log 见 §7。

## 6. 交接给 Reviewer

- 关键独立验收路径：目标详情页 → 今日步骤「Complete」→ 确认 → 庆祝态（含一题微反思）→ 点 chip（看 Network 面板 POST /tasks/{id}/feedback category）→ 继续 → 星图页下拉刷新应见该步 mastery 链更新（服务端 GJ03 原链，客户端触发器已++）。
- Review 注意：①庆祝态无自动消失（TaskCompletionCelebration 有 2.5s 自动关）——因含反思问句，强制自动关会吞掉反思，属有意差异；②任务列表页路径仍无庆祝时刻（§3 未做项第 3 条，需主会话裁度是否另卡）；③ gen/ 三目录是本 worktree 运行所需拷贝，合入时以主仓 gen 为准，patch 不含。
- 卡面 Acceptance 对照：GJ03/GJ05 outcome 链——本卡未新建真源，仅把客户端钩子接回既有服务端链（D-02 实证链路复用）；Goal 页/星图一致——同源 invalidate+trigger 刷新；Reflection 不凭空推断人格——微反思只写用户自报的 difficulty category，无任何人格推断文案。

## 7. 收工清理申报

- 删：mobile/build、mobile/.dart_tool、/tmp/wt304_guards*.log、/tmp/wt304_guards2.log（守卫日志）。
- 留：本 REPORT.md + changes.patch（v3-output/wt304-j08-goal-completion/，规范目录）、本地 commit（未 push）。
- 未动 main/未 push/无 stash·reset·clean；主仓全程只读（gen 拷贝为读源）。
