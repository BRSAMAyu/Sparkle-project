# wt303-j07-comeback · J-07 Return/Stale Plan/Comeback Recovery 交付报告

> A 线·V3 J-07（产品体验优先线）｜worktree `wt303-j07-comeback`｜base `742504d0`（wt301 提交）｜2026-09-22
> 卡面：v3/07_tasks/cards/J-07.md（Resource HEAVY；验收：回来 ≤2 actions 到 meaningful next step、陈旧建议不复用、comeback rationale 有真实变化依据、不做羞辱式累积）
> 弹药面：A-SPEC8A-SESSION-CONT 报告的会话连续性研究；按派卡令 **改造 #5（N47 last-route 冷启动恢复，M 级跨层）不做**，只做「回归接住面」。

## ① 现状审计（回归用户打开过期计划会看到什么）

**一句话：什么都不会看到——计划呈现与离开前完全一样，且会被继续喂「今天优先…」的陈旧建议。**

1. **stale 判定不存在**：mobile 计划域 grep `stale/expired/decay` 0 命中（仅 `goal_status_lexicon` 的 memory-goal expired、galaxy `stale_snapshot_banner` 等无关域）。`plan_detail_screen.dart` 唯一日期感知逻辑是 `_isLast24hMode`（targetDate 距今 ≤1 天即判「考前冲刺」）——**且它对已过期计划恒为真**（deadline 已过 ⇒ 差值 ≤1），过期用户会被永久挂在「考前最后 24 小时」框架里。
2. **scheduler/计划状态机现状**：celery 的 decay 全部是 L4 状态/记忆衰减（`run_l4_state_decay_and_retraction` 6h、`spine_expire_stale_states`），**计划域无任何过期/衰减作业**。计划状态机只有 `is_active` + `plan_stage`(sprint/daily/review/paused) + archive/restore，无 expired 态。
3. **后端健康度不含「离开」维度**：`PlanProgressService.evaluate_progress`（backend/app/services/plan_progress_service.py）severity=healthy/warning/critical，reasons 仅 time_overrun/difficulty/progress_lag；`recommended_action:"replan"` 只是个标签——**全链路不存在计划级 replan 执行端点**（api_endpoints 只有 plans CRUD/archive/restore/confirm/phases/generate-tasks/phase-schedule-regenerate 与任务级 `rescopeTask`）。
4. **陈旧建议双重复用（实锤）**：后端 `_build_day_highlights`（backend/app/api/v1/plans.py:328）**恒推 Day 1**（`highlight_day = 1 if day_groups.get(1) else min(day_groups)`），recommendation 文案固定「今天优先…」，完全不感知日期；mobile `_highlightDay` 兜底同样恒 Day 1。回归者离开 5 天回来，看到的第一屏仍是 Day 1 的「今天优先拿下 TCP」。
5. **wt302 边界核查**：wt302（J-05 卡住恢复）动 `dashboard_screen.dart:1344-1362` 的 OnboardingResumeCard/GuestConversionCard（home 卡位）与 chat 层；本卡改动全部落在 `features/plan` 域（plan_detail_screen + 新 domain 文件 + l10n），**零文件交集**，无打架面。

## ② 最小闭环与边界

**闭环：回归者打开过期/断档计划 → 页首接住横幅（真实变化依据）→ 一键重新校准（1 tap 进编辑面重锚 targetDate）——回来 ≤2 actions 到 meaningful next step。**

- **stale 判定显式化**：新增 `mobile/lib/features/plan/domain/plan_staleness.dart`，唯一判定点 `PlanStaleness.assess()`，常量 `kPlanComebackStaleDays = 3`（回归者视角「离开数日」≈ 一个周末+周一；1/3/7/14 天测试时钟覆盖）。两种形态：
  - **expired 超期**：targetDate 已过 ≥3 天；
  - **stalled 断档**：活动信号（plan.updatedAt 与已完成任务 updatedAt 取最大，宁松勿紧不误伤在学用户）停摆 ≥3 天且仍有未完成任务。
  - 边界全部按整日数（本地时区 date 截断），N-1/N/N+1 稳定可判；归档计划与全完成计划不判 stale（前者非回归目标、后者由既有 sprint completion 探针接管）。
- **呈现（不冷冰冰、不羞辱）**：过期 →「计划已过期 N 天 / 原定 {真实日期} 完成。断档不是清零，重新校准终点就能接上。」；断档 →「离开了 N 天 / 计划停在上次的地方…」。文案零惩罚语义（卡面 work item 3）；视觉复用既有 warning 语义槽横幅形制（与 `_Last24hSprintBanner` 同款 surface：0.10 底/0.28 边/图标瓦片），**未发明新视觉**。
- **动作复用既有链路**：「重新校准计划」按钮 → `context.push('/plans/:id/edit')`（既有 PlanUpdate/PATCH 链路重锚 targetDate）= 1 tap 到 meaningful next step。**引擎侧 Aurora 自动 rescope/replan 属跨层改造，按卡面令不做、见⑤交接。**
- **陈旧建议不复用（呈现层守卫，不改服务端真源）**：a) 高亮日被服务端指定为已完成日（或 Day-1 兜底撞上已完成日）时，焦点切到第一个仍有未完成任务的日子；b) stale 时隐藏「今天优先…」建议气泡；c) stale 时不再渲染「考前最后 24 小时」冲刺横幅与冲刺框架（过期计划上它原本恒真——顺手修掉这个既有 bug 面）。
- **Spec A 线合规**：横幅 surface 必达项 = 1（重新校准）；无新交互色；l10n zh/en 双语齐备。

## ③ 改动与测试

**改动清单（base 742504d0）**：
- 新增 `mobile/lib/features/plan/domain/plan_staleness.dart`（判定域，纯函数，now 注入可测）
- 改 `mobile/lib/features/plan/presentation/screens/plan_detail_screen.dart`（回归横幅 + 高亮日守卫 + 建议气泡/冲刺横幅 stale 门）
- l10n：`app_zh.arb`/`app_en.arb` 新增 5 键（planComeback*，带 @placeholders）；`app_localizations*.dart` 三件套按仓内格式手改（L10N-REGEN 先例：CP-01-MOBILE manual regen——gen-l10n 在 pub 解析后重跑会产生 ~255 行纯格式漂移，故不跑）
- 测试：新增 `mobile/test/features/plan/domain/plan_staleness_test.dart`（15 例）；扩 `plan_detail_screen_test.dart`（4 个 widget 用例 + pump helper 加 edit 路由捕获）

**测试面**：
- 域：超期 N-1(2d 不判)/N(3d 判)/N+1(4d 判)；断档 N-1/N；完成任务拉活（plan 旧但昨天有完成 → 不 stale）；全完成不 stale；归档不 stale；threshold 可覆盖（7 天口径）；1/3/7/14 天双形态单调性
- Widget：过期计划 → 横幅+标题+依据文案，tap 重新校准 → 断言路由到 `/plans/:id/edit`；断档计划 → 「离开了 5 天」+陈旧建议气泡不渲染；未过期计划 → 无横幅+建议气泡在+任务卡在（不受影响）；Day1 全完成/Day2 pending → 焦点切 Day2、完成日任务卡不在焦点位

## ④ 资源峰值

全程 LIGHT 作业（读码/编辑/l10n/python 脚本/analyze）：无模拟器/Gradle/浏览器；`flutter analyze` 3 次（29s/9s/8s）；定向 `flutter test` 单文件单进程、`--concurrency=1`、跑前 pgrep 错峰（每次均确认无 flutter_tester/gradle/emulator 并发）。**swap 门如实记录**：开工时 1211M 恰在 1.2G 门下，测试顺延约 60 分钟（期间只做 LIGHT 产出与守卫）；19:34 门开（free 1321M/load 5）跑域测试 15 例全绿——单次定向 test 工具链实测吃掉约 700M swap（1369→648M），印证门槛必要性；widget 测试再次等门（轮询哨兵 45s 间隔）后执行。收工清理：`mobile/build`、`.dart_tool`、/tmp 探针日志。

**测试结果（全绿）**：
- 域 `plan_staleness_test.dart`：**15/15 pass**（flutter test --concurrency=1，单文件单进程）。首跑抓出 1 个 fixture 缺陷（超期扫线未钉 updatedAt，overdue=1 误走 stalled 分支——恰证明判定按口径执行），修复后全绿
- Widget `plan_detail_screen_test.dart`：**9/9 pass**（存量 5 + 新增 comeback 4：过期呈现+重新校准路由断言、断档呈现+陈旧建议抑制、未过期不受影响、完成日焦点不复用）
- **复核者注意（l10n 漂移舞步）**：`pubspec.yaml generate:true` 使每次 `pub get`/`flutter test` 都会隐式 gen-l10n，本机工具链产出旧式格式（L10N-REGEN 登记的漂移形态），会把手改的三个生成文件刷成 ~400 行格式 churn。复核路径：跑完测试后 `git checkout -- mobile/lib/l10n/app_localizations*.dart` 再按仓内风格重插 5 键（arb 为唯一源，键不丢）；或容忍 churn 只验 arb。本次交付 patch 为纯增量 +127/-0（l10n 三件套）

## ⑤ 交接

1. **引擎侧 replan 链路（跨层，未做）**：「一键重新校准」当前落点是编辑面手动重锚 targetDate（诚实可用）。真正的 comeback rescope（按剩余天数压缩/重排未完成任务、`recommended_action:"replan"` 有了标签没有执行器）需要：a) 计划级 replan 端点（engine PlanStateService + gateway 透传 + proto）；b) `_build_day_highlights` 日期感知化（恒 Day 1 是双端陈旧建议的根因，mobile 已做呈现层守卫兜底）。建议 C 线开卡。
2. **后端 health 加「离开维度」**：`evaluate_progress` 可加 `days_since_last_activity` reason（`plan_state_service` 已有 task_summaries 时间戳），让回归判定从客户端呈现层守卫升级为服务端真源。
3. **`_isLast24hMode` 既有缺陷**：对过期计划恒真（本卡已做 stale 门兜底），根治应改判定式（`0 ≤ diff ≤ 1`）——涉 sprint 语义，留给 C 线 sprint 卡。
4. **wt302 协同**：本卡不动 home 卡位；OnboardingResumeCard 若需要「计划已过期」徽标，可直接复用 `PlanStaleness.assess()`（public 域函数，零依赖 UI）。

## 收工核查

- [x] 主仓只读未动；无 stash/reset/clean/push（仅 `git checkout --` 还原我自己触发的 l10n 格式 churn，单文件粒度、合纪律豁免条款）；改动全部在 wt303-j07-comeback 树内
- [x] flutter analyze 零新增（改动文件 0 条目；全库余量均为基线存量/环境性 mocks 缺失）
- [x] l10n zh/en 双语；arb JSON 校验通过；生成文件手改与仓内风格一致（L10N-REGEN 先例）
- [x] 守卫 exit 0（83 rules，终态重跑确认）。环境性前置：worktree 缺 gitignored 生成物会使 AQ/BG 红——已从主仓 rsync -aL 拷入 `backend/app/gen`、`backend/gateway/gen`（注意主仓 gen 内含指回主仓的符号链接，必须 -L 解引用，否则 K/Z 守卫 resolve 越界报错）
- [x] 定向测试全绿（域 15/15 + widget 9/9）；swap 门全程遵守（两次等门共约 55 分钟，轮询哨兵开门即跑；实测单次定向 test 吃 ~700M swap，印证门槛）
- [x] changes.patch 已生成（v3-output/wt303-j07-comeback/changes.patch，1229 行）
- [ ] 状态提交：**READY_FOR_REVIEW**（跨层交接项见⑤，不阻塞本卡 mobile 面）
