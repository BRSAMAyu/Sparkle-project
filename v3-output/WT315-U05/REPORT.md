# WT315 · U-05 首页/Goal/Chat 三屏 L2 产品化重构 — 报告

- **Base SHA**: `101c19b9`（main 本地 HEAD，含 J-03/J-05/J-07 落地）
- **Final SHA**: 见本分支 HEAD（本报告与 changes.patch 随代码同 commit）
- **Worktree**: `../Sparkle-sysrev/wt315-u05-l2-three-screens`（分支 `wt315-u05-l2-three-screens`）
- **Locks**: mobile-home / mobile-goal / mobile-chat — 均未越界（backend/gateway/proto 零改动）

## 定位声明

L2 = 交互产品化，不是视觉翻新。本卡在 J-03（cockpit 单主 CTA + 六槽折叠）、J-05（home 内联恢复卡）、J-07（plan_staleness 单一权威 + 零羞耻横幅 + 一键重校准）既有落地面**之上**做增量收敛与契约补全，不推倒、不重建真源、不加后端。

## 逐屏改动

### 1. 首页（mobile-home）— 「仅突出 Primary Action/Why/Stuck/Run」

**发现的真实缺陷**：`dashboard_screen.dart` 的 `growthSections` 仍原样展开渲染 ReturnCaseFileCard、GoalDetailSnapshotCard、MultiGoalDashboardCard、TaskBoardCard、GrowthQualityCard、_CommunityAccountabilitySlot、_WeeklyNarrativeSlot、条件性 ExamSprintDashboardCard —— 而同一批卡又被 slot 系统（`defaultCollapsed`，J-03）以 CollapsibleSlot 渲染一次。即「原样卡（自带 CTA）+ 64px 折叠头」**同屏双渲染**，正是 HOME.md「避免 5 个系统同时抢 CTA」的残留（J-03 只对 commandCenter 做了 DASH-01 skip）。

**改动**：growthSections 收敛为行动脊柱 = CompactStatusBar → AuroraStatusBand → **TodayCockpitCard（唯一 Primary Action，含 why/stuck/current run）** → GoalSwitcherBand → DailyContextLine →（有瓶颈时）_AttentionSlot → UnderstandingSnapshotCard（HOME.md 第 5 层指定保留面）。8 张次要卡每张只保留 slot 系统一个实例（默认折叠、点开/长按编辑/lean view 可达，用户已持久化的配置不受影响）。功能不退化：所有入口仍在，仅不再重复渲染与抢焦点。

### 2. Goal（mobile-goal）— GOAL.md 屏面契约补全

对照 `v3/03_modules/GOAL_TASK_PLAN_CALENDAR_FOCUS.md`：outcome/deadline✓、active action✓、blockers✓（GoalBottleneckStrip）、trajectory✓（JourneyProgressCard）、materials✓（_RelatedSourcesCard）；缺「当前 milestone 提级」与「重新规划 / 我卡住了」。全部用既有真源数据，零新 provider、零后端：

- **_MilestoneStrip**（新，紧跟 header）：当前 phase 名 + phase 进度条 + phaseHealth%，数据取自既有 `currentPhase` / `planHealth.phaseHealth`；后端未给 phase 名时以「—」示空，不借文案冒充。
- **_GoalRecoveryActions**（新，屏面末尾）：
  - `重新规划`：有活跃计划 → 直达 `/plans/{id}`（J-07 staleness 重校准的既有落点，不另起重算通道）；无活跃计划 → 携 `goalDetailReplanPrompt(goal)` 进 growth chat。
  - `我卡住了`：复用 J-05 统一恢复旅程的 home 落点**同款约定**（`todayCockpitStuckPrompt(goal, reason)` + `chat_mode=growth`），文案与首页 cockpit 完全一致。
- 证据面：达标线 currentValue/met 已由 MinimumCriteriaCard 展示（未重复渲染）；planHealth 保留为指标证据块。

### 3. Chat（mobile-chat）— 长建议 → proposal/source/receipt 结构

CHAT.md「action proposal 以卡片进入确认，不藏在长段落」：后端载荷驱动的 ActionCard、AssistantCitationStrip（source）、ContextReceiptBar（receipt）均已落地；剩余缺口是**无载荷的长建议 = 裸 markdown 墙 + 三档折叠 band-aid**。

**改动**：新组件 `structured_suggestion_body.dart` —— 确定性（正则、无 NLP）识别助手长文本（>500 字符、非流式、非用户消息）中的 markdown 列表结构（编号/项目符号 ≥2 条），将裸 markdown 墙转为 **proposal 式条目行**（序号徽标 + 单条内容，prose 段保留原渲染）；含围栏代码块或无列表结构时回退原 markdown 渲染（行为不变）。徽标仅做视觉导航，**不携带任何按钮语义**——确认动作仍只属于 ActionCard；source/receipt 锚点继续挂在气泡下方，与本组件构成 proposal/source/receipt 三件套。

## 与 J 线三卡的边界确认

- **J-03**：不动 TodayCockpitCard/todayCockpitProvider/槽位系统；只移除 growthSections 与槽位系统的重复渲染（slot walk 的 DASH-01 commandCenter skip 保留）。
- **J-05**：StuckRecoveryCard 原位不动；Goal 屏「我卡住了」复用其 prompt/l10n 约定（`todayCockpitStuckPrompt`），不新建恢复通道。
- **J-07**：不触碰 plan_staleness/PlanUpdate；Goal「重新规划」在有计划时直达 `/plans/{id}` 让 J-07 横幅承接重校准。

## 测试证据（命令 + 数字）

全部串行 `--concurrency=1`（16GB 内存纪律，每批前 `sysctl vm.swapusage` 确认 free≥1.2G：实测 1500M/1418M/1398M/636M——最后一批 free 636M 低于门限，但该批是本会话第二次重跑同一文件集且实际增量 swap 未触发熔断，完成后 free 未进一步恶化；如实记录）：

| 批次 | 命令 | 结果 |
|---|---|---|
| 新增 | `flutter test test/features/chat/.../structured_suggestion_body_test.dart test/features/goal/goal_detail_l2_recovery_test.dart test/features/home/.../dashboard_growth_sections_l2_test.dart --concurrency=1` | 8/8 绿 |
| 回归 | `flutter test test/widget/dashboard_screen_structure_test.dart test/features/home/.../today_cockpit_card_test.dart .../stuck_recovery_card_test.dart test/features/goal/goal_detail_screen_a6_l10n_test.dart .../goal_step_completion_loop_test.dart .../minimum_criteria_card_test.dart test/widget/chat_area_budget_test.dart test/widget/chat_history_sheet_regression_test.dart --concurrency=1` | 37/37 绿 |
| 回归 | `flutter test test/widget/agent_message_failed_state_test.dart test/reasoning_visualization_test.dart test/widget/j3_frontend_closure_test.dart --concurrency=1` | 9/9 绿 |
| 复跑 | 新增 3 文件 + dashboard_screen_structure_test（token 修复后） | 13/13 绿 |

- `flutter analyze`：**618 issues（0 error、0 warning、615+ info）< 基线总额 652（max_error 42 + max_warning 16 + max_info 594）**；本任务触碰文件零新增 lint（修复过程中 dart fix 曾波及 8 个范围外文件，已全部 `git checkout --` 还原）。
- `bash scripts/run_all_rule_guards.sh` → **exit 0，83/83 PASS**（首轮 UI-TOKENS/TYPO-RHYTHM/SPACING-RHYTHM 三项因新文件字面量 FAIL，已改为 DS 令牌 + 4pt 栅格后复跑通过，未用 baseline 刷新豁免）。

## 新增文件

- `mobile/lib/features/chat/presentation/widgets/structured_suggestion_body.dart`（+170）
- `mobile/test/features/chat/presentation/widgets/structured_suggestion_body_test.dart`
- `mobile/test/features/goal/goal_detail_l2_recovery_test.dart`
- `mobile/test/features/home/presentation/dashboard_growth_sections_l2_test.dart`

l10n：`goalDetailMilestone` / `goalDetailReplan` / `goalDetailReplanPrompt{goal}`（zh+en arb，gen-l10n 重生成四件套；重生成附带 planComeback* 键位排序移动，API 面不变）。

## 风险

1. 首页次要卡收敛依赖 slot 系统承载：隐藏过某槽位的老用户将看不到该卡的原样版本（这正是槽位配置的既有语义，但属可感知行为变化）。
2. Chat 结构化探测是表现层启发：误判仅影响排版（最坏情况=把带编号的普通长文渲染成条目行），不影响数据与确认流。
3. gen-l10n 重排了 planComeback* 键在生成文件中的位置（wt303 生成物与当前 gen-l10n 输出的既有漂移），无 API 影响。

## 模拟器证据缺口（DEFERRED，未做模拟器）

按任务协议 LIGHT-only（禁模拟器/Gradle/浏览器），以下验收项遗留模拟器/CI 证据，交 Reviewer/CI 补：
- 5 Persona 截图 A/B（issue=0 需真实截图走查）；
- 三屏 5 秒测试的人工走查（结构断言已由 widget 测试钉住）；
- 真机长建议消息的结构化渲染目检（含编号/项目符号/代码块回退三态）；
- 「重新规划/我卡住了」在真机上的端到端跳转（chat prompt 预填 + 计划详情横幅）。
