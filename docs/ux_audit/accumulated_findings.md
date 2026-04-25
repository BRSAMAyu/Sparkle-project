# Sparkle UX Audit — Accumulated Findings

> **Purpose**: All validated UX issues found across the full system audit.
> **Updated by**: Validator agent after each review cycle.
> **Status**: 23 / 30 chains audited (C04, C20, D01, D05, D07, D09, D10 pending)

---

<!-- FINDINGS APPENDED BELOW BY VALIDATOR -->

---
## Round 1 — 2026-04-25
*Reviewer A: C01 — 冷启动建模→计划生成→首个任务可见 | Reviewer B: C06 — Galaxy节点点击→节点详情→开始复习进入chat携带context*

> **Note**: C02–C05 原始发现已被后续 reviewer 轮次覆盖丢失。C03/C04/C05 在 audit_state.json 标记 "done" 但无验证过的发现。需 architect 安排重新审查。

### C01: 冷启动建模→计划生成→首个任务可见 (Reviewer A)

**Critical Issues 🔴**
- **`planning_workflow.py:770` + `orchestrator.py:652-654` + `modeling_chat_screen.dart:729-732`**: 建模→规划桥接始终需要两轮"开始规划"才能产生 plan_id。第一轮：`from_modeling_complete=True` 导致 `fast_track_context` 保持 None（orchestrator.py:652 跳过 build、669 不注入），session 进入 AWAITING_CONFIRM（planning_workflow.py:770），返回策略提案无 plan_id。Mobile 端 line 731 抛异常"计划已经开始生成，但入口还没准备好"。第二轮："开始规划"匹配 PLANNING_CONFIRM_PATTERNS（line 58），触发 _handle_generating 成功。**影响：每个冷启动用户必现报错**。
- **`modeling_chat_screen.dart:744-748`**: 报错文案"计划生成遇到问题：Exception: 计划已经开始生成..."，实际是正常流程中间态。用户看到"遇到问题"以为失败。Expected: 显示"正在准备计划，点击确认"CTA。Actual: 错误卡片标题"计划生成没成功"（line 908-945）。

**Major Issues 🟡**
- **`modeling_chat_screen.dart:741` + `plan_routes.dart:163`**: 成功生成后 `context.go('/plans/{id}')`。plan_routes.dart:163 用 `parentNavigatorKey: navigatorKey`（root navigator），在 StatefulShellRoute 之外，底部 tab bar 消失。PlanDetailScreen:92 的 `context.pop()` 回到 root redirect → `/home`，断开了建模上下文。
- **`modeling_chat_screen.dart:738-740`**: 仅 invalidate `planDetailProvider` + `planListProvider`，遗漏 `learningPortfolioProvider`。用户导航到学习档案页看到旧数据。

**Minor Issues 🟢**
- **`modeling_chat_screen.dart:888-895`**: 第一轮加载文案"正在生成你的第一份冲刺计划"+"马上就会带你进入任务页"——但第一轮必定失败，设定错误预期。
- **`modeling_chat_screen.dart:615-624`**: `_finish()` 跳过路径直接 `context.go('/home')` 或 `/chat`，planning session 留在 AWAITING_CONFIRM 状态，无恢复机制。

**Working Well ✅**: Aurora 建模对话多轮追踪正确（conversationId、stream events、modeling_complete 检测）；plan_detail_screen 加载骨架屏、错误重试、自动检测冲刺完成均有；错误恢复 UI 有重试按钮。

---

### C06: Galaxy节点点击→节点详情→开始复习进入chat携带context (Reviewer B)

**Critical Issues 🔴**
- None

**Major Issues 🟡**
- **`chat_screen.dart`（全文件 grep `review_node` 无匹配）**: 复习 session 与普通 chat UI 完全相同，无 review header/banner/indicator。`chat_mode='study_plan'` 仅影响 prompt starters（line 1746），不影响 UI 布局。用户多轮对话后无法辨别自己在复习哪个节点。
- **`node_detail_sheet.dart:129-132` + `service.py:765-777`**: `initial_context` 仅包含 `{review_node, node_label}`，不传 mastery、学习次数、错题列表。后端 `_review_focus_from_context()` 也仅读 `review_node` 和 `node_label`。Aurora 无法基于掌握度定制复习内容。

**Minor Issues 🟢**
- **`node_detail_sheet.dart:342-348`**: "开始复习"按钮在 mastery=0 时仍可用且文案不变。Sheet 在 mastery=0 时显示"尚未学习"（line 278），但按钮未做条件适配（应显示"开始学习"）。
- **`node_detail_sheet.dart:206-254`**: Sheet 仅渲染节点名称、ID、掌握度百分比、统计 chips、错题预览。API 返回的 `description` 和 `keywords` 字段未被渲染（grep `description|keywords` 无匹配）。

**Working Well ✅**: 端到端导航链路完整（NodeDetailSheet → GoRouter → routes.dart query+extra 合并 → ChatScreen → WebSocket → Aurora `_review_focus_from_context()`）；Aurora 自动检测复习模式生成定点复习首条消息；0 mastery 友好处理（"尚未学习"而非"0%"）；Sheet 有 loading/error/retry 状态。

---

### Confirmed by Both Reviewers
无交叉确认（不同 chain）

---

## Round 2 — 2026-04-25
*Reviewer A: C09 — 每日启动消息个性化（昨日完成率+今日任务） | Reviewer B: C10 — 跨会话记忆注入（新会话Aurora引用旧内容）*

### C09: 每日启动消息个性化（昨日完成率+今日任务） (Reviewer A)

**Critical Issues 🔴**
- None

**Major Issues 🟡**
- **`chat_screen.dart:424`**: daily startup API 失败被 `catch (_) { return false; }` 静默吞掉，无重试无反馈，用户直接看到通用开场白。Expected: 轻量"加载今日概览"+重试。Actual: 无感知降级。
- **`chat_screen.dart:369-371`**: `examSprintDashboardProvider.future.timeout(const Duration(seconds: 5))` 硬超时。弱网/冷启动时 dashboard 加载慢于 5 秒则整个 daily startup 跳过。Expected: 用缓存或 activePlanProvider 降级。Actual: 超时直接 return false。

**Minor Issues 🟢**
- **`aurora_daily_startup_repository.dart:22-29`**: demo 模式返回硬编码"计算机网络"+"TCP 流量控制"消息。非计算机网络用户会看到错误学科。
- **`chat_screen.dart:490-500`**: `_canShowAuroraOpenerOver` 允许 Day 2 的 daily_startup 替换 Day 1 的（正确行为但无法回看历史启动消息）。

**Working Well ✅**: 后端个性化完整（昨日完成率实时计算、时间段问候、表现适配语气、Day 1 特殊处理）；SharedPreferences 按天去重；优先级链 comeback > daily startup > generic 正确；消息显示为普通 AI 消息；有测试覆盖。

---

### C10: 跨会话记忆注入（新会话Aurora引用旧内容） (Reviewer B)

**Critical Issues 🔴**
- **`settings.py:596` — `SPARKLE_MEMORY_INFERRED_WRITE_ENABLED: bool = False`**: 最丰富的记忆来源（per-turn 推断写入）被关闭。`memory_inferred_write_lane.py:443-445` 检查 flag 后直接返回 `status="disabled"`。对话中用户说的"明天要考高数"、"TCP 很难"等信息不会被捕获。其他写入路径仍活跃（错题分析、任务反思、专注模式、orchestrator 直接写入共 6+ 条路径），但覆盖面远低于 per-turn 推断。**补救：设为 True 即可启用，已有 kill switch + 用户级禁用保护**。

**Major Issues 🟡**
- **`prompts.py:3407-3433`**: `_format_past_session_memory_section()` 仅格式化 bullet list（"你之前了解的关于用户的信息："），无引导指令告诉 AI 在适当时机主动引用。LLM 可能忽略这些信息。
- **`context_manager.py:267` + `prompts.py:3419-3421`**: 仅获取最近 3 条 episodic memory 的 summary 文本。context_manager.py:281-292 获取了 `subject_type`、`source_type`、`occurred_at`、`tags`，但 prompts.py:3419-3421 仅提取 `summary`/`text`/`content`/`title` 字段。丰富上下文被丢弃。

**Minor Issues 🟢**
- **`prompts.py:3412-3413`**: 记忆 bullet list 不显示时间框架。`occurred_at` 在 context_manager.py:287-289 已获取，但 `_format_past_session_memory_section()` 未使用。AI 无法判断记忆新鲜度。

**Working Well ✅**: 记忆注入路径完整接线（ContextOrchestrator → memory_service → CognitiveContext → build_system_prompt → system prompt 顶部前置）；最高优先级位置（prompts.py:1540-1541 prepend）；空状态优雅降级（返回空字符串不崩溃）；去重机制（seen set）；ENABLE_CONTEXT_FOCUSING/ENABLE_CONTEXT_BRIEFING 已启用；kill switch 保护完善。

---

### Confirmed by Both Reviewers
无交叉确认（不同 chain）

---

## Round 3 — 2026-04-25
*Reviewer A: C11 — 间隔重复提醒链路（Celery→推送→复习chat） | Reviewer B: C14 — 学习档案页完整性（历史冲刺+Galaxy摘要展开）*

### C11: 间隔重复提醒链路（Celery→推送→复习chat） (Reviewer A)

**Critical Issues 🔴**
- None

**Major Issues 🟡**
- **`celery_tasks.py:1150`**: `_spaced_repetition_due_interval_days()` 用 `elapsed_days in (1,3,7,14,30)` 精确匹配。Celery 扫描若在 day 7 因宕机/队列积压被跳过，day 8 不匹配任何间隔，day-7 复习永久丢失，下次机会是 day 14。无容差窗口（应有 `>= interval and < interval + grace`）。对间隔重复学习科学而言，漏间隔直接影响记忆留存。
- **`celery_tasks.py:1105`**: `SPACED_REPETITION_INTERVAL_DAYS = (1,3,7,14,30)` 对所有 mastery 30-80% 的节点使用相同间隔。31% mastery（几乎不会）和 79%（较好掌握）获得相同复习计划。标准间隔重复算法（SM-2、Anki）应按掌握度调整间隔长度。

**Minor Issues 🟢**
- **`celery_tasks.py:1250/1265`**: 每次扫描限 500 用户（`limit=500`）。超过 500 活跃用户时部分用户当天无复习提醒，造成 UX 不一致。
- **`celery_tasks.py:1195`**: `mastery < 0.3` 的节点被完全跳过。这些最弱节点可能最需要复习，30% 阈值过于激进（低于此值的节点可能需要重新学习而非复习，但阈值值得重新评估）。

**Working Well ✅**: 端到端链路完整（Celery Beat 9:30 → per-user task → notification payload 含 deep link → push_navigation_service → DeepLinkService → routes.dart query 提取 → ChatScreen → Aurora review prompt）；24h cooldown 防重复；有测试覆盖（payload + 路由集成测试）。

---

### C14: 学习档案页完整性（历史冲刺+Galaxy摘要展开） (Reviewer B)

**Critical Issues 🔴**
- None

**Major Issues 🟡**
- **`exam_sprint_review_service.py:374` vs `:397`**: 已完成冲刺用 `covered_topics_after`（mastery≥60% 的节点数，来自复习归档），进行中冲刺用 `plan.mastery_level * 100`（Plan 表聚合百分比换算）。两者含义不同：前者是节点计数，后者是百分比值转换。用户比较"掌握 5 节点"vs"掌握 3 节点"时，数字不可比。
- **`exam_sprint_review_service.py:61+1044`**: `MAX_ARCHIVE_ENTRIES = 10` + `entries[-10:]` 截断。学习 10+ 门课程后最早冲刺的详细 Galaxy 摘要（weakest_points、proud_nodes 等）变为空值。

**Minor Issues 🟢**
- **`learning_portfolio_screen.dart:247-280`**: ExpansionTile 展开后仅显示聚合计数"掌握 X 节点"和摘要文本，无节点级下钻。用户需离开档案页去星图查看每个节点的具体 mastery。

**Working Well ✅**: 三组分类（进行中/已完成/计划中）视觉清晰；ExpansionTile 内联展开无需跳转；展开内容丰富（headline/chips/最薄弱点/骄傲节点/成绩备注）；全屏空状态有 CTA；错误处理三层（loading/error+retry/SnackBar）；Profile 入口可见。

---

## Round 4 — 2026-04-25
*Reviewer A: (stale, no new findings) | Reviewer B: C16 — 导航死路检查（完成页/庆祝页/建模完成后）*

### C16: 导航死路检查（完成页/庆祝页/建模完成后） (Reviewer B)

**Critical Issues 🔴**
- **`modeling_chat_screen.dart:80-81`**: `RouteResilienceScope(fallbackRoute: UserRoutes.personaOnboarding)` — 建模完成后按系统返回键回退到 `/onboarding/persona` 而非 `/home`。与 `_finish()` 方法（line 615-624 导航到 `/home` 或 `/chat`）行为不一致。新用户完成建模按返回键 → 回到 onboarding 造成困惑或循环。**修复仅需改一行 `fallbackRoute: HomeRoutes.home`**。与 Round 1 C01 Major #3（同一文件成功路径导航断裂）互为补充。

**Major Issues 🟡**
- **`sprint_completion_screen.dart:300-316`**: 三个 CTA—"分享"、"记录考试结果"（→ review）、"查看学习档案"（→ portfolio），均不导航到 home。`_closeScreen()` (line 159-161) 回退到 `PlanRoutes.learningPortfolio`。用户完成冲刺后无法直接返回首页，需额外步骤。
- **`modeling_chat_screen.dart:856-945`**: `_PlanningBridgeStatus` 是 `StatelessWidget`，错误状态仅有"重试生成计划"+"稍后再说"按钮，无 Timer 或自动跳转。用户不操作则界面无限停留在错误状态。

**Minor Issues 🟢**
- **`sprint_completion_screen.dart`**: Confetti 动画播放完毕后界面静止（grep Timer/Future.delayed/autoNavigate 无匹配），无自动过渡到下一个逻辑页面。用户可能出现短暂的"然后呢？"困惑。

**Working Well ✅**: 三个页面均有 RouteResilienceScope（不会白屏）；三个页面均有明确关闭按钮；Sprint completion 用 `RouteResilience.popOrGo()` 智能导航；Milestone celebration "继续学习" → `/home` 引导清晰；Modeling 成功路径自动导航无摩擦；PopScope 处理 Android 返回手势。

---

### Confirmed by Both Reviewers
- **`modeling_chat_screen.dart` 导航问题**: C01 Major #3（成功路径 root navigator 断裂）+ C16 Critical（返回键 fallback 路由错误）共同指向同一文件的导航缺陷。两轮独立确认。
- **周报通知到达后 UI 不展开**: C13 Major #1（insights 页不识别 `initialPanel=weeklyNarrative`）+ C18 表格第 5 行（路由存在且导航正确）共同验证——导航成功但目标页未响应参数。
- **Celery 500 用户扫描上限**: C11 Minor #3（间隔重复）+ C13 Minor #3（周报）独立发现同一模式。
- **`chat_screen.dart:424` daily startup 静默降级**: C09 Major #1（首次发现）+ C17 Major #1（独立确认）。两轮交叉验证。

---

## Round 5 — 2026-04-25
*Reviewer A: C13 — 每周报告生成→推送→周报卡展示亮点 | Reviewer B: C18 — 所有推送通知路由正确性（6种类型）*

### C13: 每周报告生成→推送→周报卡展示亮点 (Reviewer A)

**Critical Issues 🔴**
- None

**Major Issues 🟡**
- **`celery_tasks.py:1689` + `learning_insights_overview_screen.dart:25-27`**: 后端推送携带 `destination_route=/learning/insights?initialPanel=weeklyNarrative`，但 insights 页仅定义 `panelSimulation`/`panelTheater`/`panelReport` 三个常量（line 25-27），无 `panelWeeklyNarrative`。switch 表达式（line 351-353）匹配不到任何 case，无模块卡高亮。周报卡默认收起（`_expanded = false`，card line 17），用户需手动展开才能看到 highlights/biggest_improvement。
- **`weekly_growth_narrative_card.dart:17`**: `bool _expanded = false` 硬编码初始值，无 `initialExpanded` 参数，不从路由参数控制。通知驱动的场景无法自动展开。

**Minor Issues 🟢**
- **`celery_tasks.py:1757-1817`**: 500 用户扫描上限（与 C11 Minor #3 同模式）。
- **`progress_narrative_service.py:551-606`**: `biggest_improvement` 在无掌握度增长时返回 None。设计如此，移动端 `hasBiggestImprovement` getter 正确处理，影响极小。

**Working Well ✅**: Celery 周日 18:00 调度合理；三级降级叙事生成；24h 去重防重复；`FutureProvider.autoDispose` 保证数据新鲜；highlights 有 fallback 文案；卡片 loading/error/空状态完善。

---

### C18: 所有推送通知路由正确性（6种类型） (Reviewer B)

**Critical Issues 🔴**
- None — 所有 6 种通知类型的目标路由均存在于 GoRouter 配置中。

**Major Issues 🟡**
- **`notification_list_screen.dart:87`**: 通知列表点击用 `context.push(destinationRoute)` 而非 `RouteResilience.openExternalRoute()`（对比 `notification_service.dart:387-393` 推送点击路径）。深链进入后点击列表通知可能因导航栈无效而失败。
- **`notification_list_screen.dart:94`**: 列表深链接用 `DeepLinkService.handleDeepLink()` 而非 `handleExternalDeepLink()`（后者含 RouteResilience 回退）。列表导航路径比 push handler 更脆弱。
- **`celery_tasks.py:907-923`**: `send_task_reminders` 已返回 `{"status": "disabled"}`，服务端每日提醒停用。移动端 `TaskNotificationScheduler` 创建的 payload 无 `destination_route`，走 fallback 路径 `/tasks/$taskId/execute`。当前可工作但依赖 fallback 稳定性。

**Minor Issues 🟢**
- **`celery_tasks.py:1387,1392,1529,1530`**: Sprint reminder 和 comeback nudge 的 `deep_link` 字段使用原始路由路径（如 `/plans/{id}?source=...`）而非 `sparkle://` 协议，与 milestone 的 `sparkle://milestone/...` 格式不一致。`destination_route` 优先匹配不影响功能。
- **`notification_list_screen.dart:29-30`**: 空通知列表仅显示 "No new notifications" 纯文本，无解释或操作引导。对比 C15 全局空状态质量要求。

**Working Well ✅**: 全部 5 种服务端通知路由正确且可被目标页解析；双通道投递（WebSocket+FCM/JPush）；Milestone payload 解析支持三种入口方式；所有类型 24h 去重保护；RouteResilience 回退路由完整（chat→home, plans→plan home）；间隔重复通知携带完整复习 context 对接 C06 路径；有 intervention action tracking。

---

## Round 6 — 2026-04-25
*Reviewer A: C15 — 全局空状态质量（6个关键页面） | Reviewer B: (re-auditing, no current file)*

### C15: 全局空状态质量（6个关键页面） (Reviewer A)

**Critical Issues 🔴**
- None

**Major Issues 🟡**
- **`memory_panel_screen.dart:430-438`**: 筛选后无结果时 `_buildEmptyState()` 仅显示裸文本"暂无符合条件的记忆"（`TextStyle(color: DS.textSecondary)`），无"清空筛选"按钮。对比同文件 `_buildGuidedEmptyState()`（line 440-448）有完整 `EmptyState` widget 含 icon/标题/描述/CTA"去开始对话"→`/chat`。

**Minor Issues 🟢**
- None — 其余 5 个页面（任务列表/错题本/Galaxy星图/成就页/学习洞察）全部达标，各有上下文感知的引导文案和 CTA。

**Working Well ✅**: 任务列表有 `EmptyState.noResults()` 变体和 CTA"创建第一项任务"；错题本有双 tab 差异化空状态+CTA"添加第一道错题"；Galaxy 有自定义 orb 动画+action highlight chips+CTA"去创建学习任务"；成就页有筛选/非筛选双空状态+CTA"清空筛选"；学习洞察有多数据源联合检测+CTA"去创建学习任务"；记忆面板主空状态有标准 EmptyState widget。

---

## Round 6.1 — 2026-04-25 (Recovered from git commit 11997100)
*Reviewer A: C03 — 任务卡点(stuck)→卡点帮助面板→Aurora诊断内容*

### C03: 任务卡点(stuck)→卡点帮助面板→Aurora诊断内容 (Reviewer A — recovered)

**Critical Issues 🔴**
- **`backend/app/models/task.py:47-51` + `task_execution_screen.dart:452-466`**: TaskStatus enum 仅有 `PENDING`, `IN_PROGRESS`, `COMPLETED`, `ABANDONED`，无 `STUCK` 状态。无 API 端点标记任务为 stuck。Mobile 端打开 help sheet 为纯本地 UI 动作——无 API 调用、无状态更新、无事件。后端永远不知道用户卡住了。`decision_loop.py:641` 的 `_is_stuck_task_scene()` 检查 `task_state.stage == "stuck"` 但无任何代码设置此值。Expected: 点击"卡住了?"应设置 task status 为 STUCK 并通知后端。Actual: 纯本地 UI 无后端通信。
- **`stuck_help_sheet.dart:27-31` + `task_card_generator.py:256-283`**: Sheet 内容来自 `task.guideJson`——plan 创建时由 `task_card_generator.py` 生成的静态元数据，非基于用户当前状态的 Aurora 实时诊断。唯一的 Aurora 交互是"和Sparkle聊聊这个问题"按钮，需用户手动对话。Expected: Sheet 显示 Aurora 基于当前状态的上下文诊断。Actual: Sheet 显示任务创建时的静态帮助内容。

**Major Issues 🟡**
- **`task_execution_screen.dart:477`**: `_openStuckChat` 使用 `context.go()` 替换整个导航栈。任务执行页被销毁，运行中的计时器丢失。用户无法从 chat 返回任务。chat 的返回按钮到 `/home`，而非回到任务。Expected: Chat 以 overlay 或 push 方式打开，保留任务执行上下文。Actual: 任务执行页被销毁。
- **`task_execution_screen.dart:480-493`**: `_sendAuroraTrigger` 发送消息时不包含 `task_state.stage="stuck"` 或任何卡点上下文。Aurora 的 decision loop 无法激活卡点诊断模式（`_is_stuck_task_scene` 返回 False）。响应将是通用内容，非 `decision_loop.py:727-740` 描述的 micro-teaching 诊断。

**Minor Issues 🟢**
- None

**Working Well ✅**: StuckHelpSheet widget 设计精良（渐进式内容回退 micro_teaching → fallback_if_stuck → if_stuck → genericSuggestions，读取 5+ 字段名变体增强韧性）；双步 micro-teaching 卡片（诊断问题 + 针对修复）；Stuck chat prompt 结构良好（含任务标题、预估时间、聚焦提示、步骤、成功标准）；FAB 位置恰当不遮挡计时器；后端卡点诊断基础设施完整（STUCK_TASK_STAGE_TOKENS 检测、standard_layer_contract、micro-teaching 模式激活、规则注入）。

---

### C17: API失败恢复（加载→错误→重试） (Reviewer A — from reviewer_a_C17.md)

**Critical Issues 🔴**
- None

**Major Issues 🟡**
- **`chat_screen.dart:424-426`**: `_hydrateDailyStartupIfNeeded()` 在 `getDailyStartup()` 失败时 `catch (_) { return false; }` 静默吞掉。上游 `examSprintDashboardProvider.future` 超时也在 line 372 静默返回 false。后端不可用时用户看到空白而非错误提示。**[已与 C09 Major #1 交叉确认 — 两轮独立验证]**
- **`galaxy_screen.dart:2710`**: `contributionStats.when(...)` 的 error 回调返回 `const SizedBox.shrink()`。贡献统计 API 失败时 banner 完全消失，无错误提示无重试入口。与 Galaxy 主加载错误处理（GalaxyErrorSnackBar + 重试）形成对比。

**Minor Issues 🟢**
- None

**Working Well ✅**: 计划详情页三态完整（data/loading/error 含重试按钮），错误消息可识别 404/超时/网络错误；Galaxy 主加载区分首次/后台刷新错误，SSE 断线 5 秒自动重连；Chat WebSocket 断线自动重连。

---

## Round 7 — 2026-04-26
*Reviewer A: C19 — Aurora建模对话质量 | Reviewer B: C02 — Galaxy mastery双刻度bug + C05 — 冲刺完成状态*

### C02: 任务完成→Galaxy节点mastery更新→星图颜色变深 (Reviewer B — re-audit, recovered)

**Critical Issues 🔴**
- **`task_service.py:477` + `galaxy_service.py:1396` + `galaxy_llm_protocol.g.dart:88`**: Sprint Pack 使用 0-1 刻度写入 mastery（line 477: `min(1.0, current_mastery + 0.25)`），`update_node_mastery` 夹到 0.25 写入 DB。Mobile 端 `galaxy_llm_protocol.g.dart:88` 用 `(json['mastery_score'] as num?)?.toInt()` 将 0.25 截断为 0，`galaxyMasteryRatio(0) = 0/100 = 0`。Sprint pack 节点 mastery 在 mobile 端始终显示为 0，颜色永远灰色。Expected: 完成 4 个 sprint 任务后 mastery 到 1.0，颜色变深。Actual: Sprint pack 节点在移动端始终显示灰色。普通 Galaxy 节点（0-100 刻度）不受影响。

**Major Issues 🟡**
- None

**Minor Issues 🟢**
- None

**Working Well ✅**: 任务完成后 galaxy 刷新触发正确（`galaxyRefreshTriggerProvider.state++` + `refreshForTaskCompletion`）；颜色映射 4 级逻辑正确（0-25%→25-50%→50-75%→75-100%）；后端 `_mastery_ratio` 归一化一致。

---

### C05: 7天冲刺完成→庆祝页→学习档案状态变completed (Reviewer B — re-audit)

**Critical Issues 🔴**
- None

**Major Issues 🟡**
- **`exam_sprint_review_service.py:393-414` vs `173-255`**: 如果用户跳过"记录考试结果"按钮（直接点"查看学习档案"或关闭庆祝页），冲刺计划不会被 archive，portfolio 中仍显示 `status="active"`（line 396: `status = "active" if plan.is_active else "planned"`）。只有完成考后评估（`submit_post_exam_review`）才会归档并显示 `completed`。Expected: 冲刺所有任务完成后 portfolio 状态变为 completed。Actual: 用户永远不做考后评估则冲刺永远显示 active。

**Minor Issues 🟢**
- None

**Working Well ✅**: `_invalidateLinkedViews()` 正确刷新 portfolio/weeklyGrowth/planDetail providers；RouteResilienceScope + PopScope 确保退出触发 invalidate；summary 为 null 时有 loading/error/retry 状态；三个 CTA 按钮清晰无导航死路。

---

### C19: Aurora建模对话质量（不重复/上下文感知/自然过渡） (Reviewer A)

**Critical Issues 🔴**
- None

**Major Issues 🟡**
- **`chat_adapter.py:113-137`**: `_infer_context_answers()` 使用简单关键词匹配推断用户回答。`_BASELINE_LIGHT_PATTERNS` 包含 "不太会"、"不太懂" 等模式，可能将特定知识点困难（如"TCP有点难懂"）误分类为整体 baseline="不太稳"。推断用 `setdefault` 语义不覆盖明确回答，但推断本身误报率可能偏高。实际影响有限——推断只影响问题措辞，不影响 tension 解析。
- **`planning.py:884`**: `_recompute_tensions()` 判断 resolved 的逻辑为 `field_value not in (None, "", [], {})`。任何非空字符串（含"不知道"、"随便"等敷衍回答）都被视为有效回答并标记 resolved，后续不再追问。设计权衡——严格验证可能导致循环追问。

**Minor Issues 🟢**
- None

**Working Well ✅**: Tension 追踪系统完整（4 域独立 tension + 每轮重算 + 自动识别已回答域）；上下文感知问题生成（零基础/有scope/Sprint Pack 各有专用措辞）；Chat adapter 双层降级（LLM→静态→fallback）；Modeling complete 基于域全覆盖集合运算非关键词匹配；每个域有高质量 fallback 问题。

---

## Round 8 — 2026-04-26
*Reviewer B: C07 — 成就里程碑链路 + C08 — Comeback 消息 + C12 — 自适应压缩*

### C07: 成就里程碑解锁→推送通知→点击打开庆祝页 (Reviewer B — re-audit)

**Critical Issues 🔴**
- None

**Major Issues 🟡**
- None

**Minor Issues 🟢**
- None

**Working Well ✅**: 完整链路已确认——achievement_event_consumer 24h 去重 + stats 收集全面；`_build_milestone_route` 和 `_build_milestone_deep_link` 正确传递所有 stats；DeepLinkService milestone 路由映射正确；MilestoneCelebrationScreen `fromQueryParameters` 工厂方法容错解析；`_dismissToAchievements` 和 `_continueLearning` 使用 `RouteResilience.popOrGo` 无导航死路。

---

### C08: 用户≥3天未活跃→comeback消息出现在chat首屏 (Reviewer B — re-audit)

**Critical Issues 🔴**
- None

**Major Issues 🟡**
- **`service.py:306`**: Comeback 检测基于 `user.last_login_at` 而非真实最后活跃时间。变量名 `last_activity_at` 暗示应是活跃时间，但实际取自 JWT 认证时更新的 `last_login_at`。Expected: 基于用户最后一次有意义操作（完成任务、发消息等）。Actual: 基于登录时间。用户持续活跃但未重新认证时可能误触发 comeback 消息。多数场景下不影响（多日未开 app 确实会重登），但语义不精确。

**Minor Issues 🟢**
- None

**Working Well ✅**: `get_comeback_context` 逻辑完善（活跃状态检查 + 活跃计划查找 + 剩余天数计算 + 下一个未完成任务 + 个性化消息生成）；前端去重逻辑（signature check）+ 5 秒超时保护 + 多层 `_canShowAuroraOpenerOver` 防覆盖；自动切换到 comeback 关联的计划 session；comeback 消息不会被通用欢迎覆盖。

---

### C12: 低完成率+临近截止→自适应压缩→计划页显示精简 (Reviewer B — re-audit)

**Critical Issues 🔴**
- None

**Major Issues 🟡**
- None

**Minor Issues 🟢**
- None

**Working Well ✅**: `should_compress` 逻辑清晰（50% + 5 天参数合理）；`build_compressed_sprint_day_spec` 生成完整保底任务含 method_steps/fail_safe_rule/compression_reason；mobile `_compressionSummary` 四重检测覆盖所有压缩标记来源；`_AdaptiveCompressionBanner` 橙色+剪刀图标视觉清晰；compression_reason 含具体数字（完成率%、剩余天数）。

---

### C04: 错题录入→修复任务插入→计划页橙色卡可见
**Status**: ⚠️ 无 reviewer 文件 — 原始发现丢失，重新审查未产出文件。仍需审查。

### C20: Sprint Pack端到端集成（节点→任务spec→mastery回写）
**Status**: ⚠️ 无 reviewer 文件 — 原始发现丢失，无重新审查记录。仍需审查。但 C02 Critical 已间接覆盖 mastery 回写路径（0-1 刻度 bug）。

---

## Round 9 — 2026-04-26 (Phase 2 D-chains)
*Reviewer A: D03 — 专注模式→任务联动 | Reviewer B: D02 — 错题修复→Galaxy闭环 + D04 — 日历→Aurora感知 + D06 — 长期用户退化 + D08 — 社区→个人AI*

### D02: 错题修复→Galaxy掌握度闭环——修了错题星图真的变亮吗 (Reviewer B)

**Critical Issues 🔴**
- **`error_book_mastery_sync_service.py:243-246`**: `apply_review_feedback` 直接修改 `UserNodeStatus.mastery_score`（line 246），绕过了 `GalaxyService.update_node_mastery`（后者有 Outbox 写入、审计日志、WebSocket 推送）。Expected: 复习错题后 Galaxy 星图实时更新。Actual: mastery 写入 DB 但不推送 Outbox/WebSocket。用户需重新打开 Galaxy 页面才能看到变化。

**Major Issues 🟡**
- **`error_book_mastery_sync_service.py:170-172`**: `linked_knowledge_node_ids` 为空时直接返回空列表，mastery 不更新。前端不提示用户关联节点。
- **`error_book_provider.dart:454-464`**: `submitReview` 成功后 invalidate 了 error/plan/task/weekly providers，但未 invalidate `galaxyProvider` 或递增 `galaxyRefreshTriggerProvider`。

**Minor Issues 🟢**
- None

**Working Well ✅**: REVIEW_PERFORMANCE_IMPACT 映射合理（remembered→+4, fuzzy→+1, forgot→-2）；最多更新 3 个节点防过大变化；DB commit 后发布事件保证一致性；StudyRecord 记录每次变化有审计追踪。

---

### D03: 专注模式→计划/任务联动——专注完成是否更新任务进度 (Reviewer A)

**Critical Issues 🔴**
- **`focus_service.py:174-186`**: `focus.session.completed` 事件 payload 含 `session_id`、`duration_minutes`、`mastery_updates`，但**不含 `task_id`**。`event_bus.py` 中零 `focus` 相关事件类定义。专注完成是数据孤岛——记录了但不被任何下游系统消费。Expected: 专注完成后任务进度更新。Actual: 只记录 FocusSession 行，任务进度不变。
- **`plans.py:1391`**: `"total_minutes_spent": 0,  # Would be calculated from focus sessions` 硬编码。注释直接说明集成未实现。计划进度页永远显示 0。

**Major Issues 🟡**
- **`mindfulness_provider.dart`**: 专注完成后不 invalidate 任何 task provider（grep 确认 0 匹配）。如果后端更新了关联数据，用户需手动离开再返回才能看到变化。

**Minor Issues 🟢**
- None

**Working Well ✅**: 专注会话记录完整（saveSession 正确传递 taskId/taskTitle）；Galaxy mastery 集成有效（task 关联节点时触发 mastery boost）；完成 UI 有 mastery 更新 dialog；离线保存降级有本地标记。

---

### D04: 日历→Aurora感知——AI教练知道用户日程吗 (Reviewer B)

**Critical Issues 🔴**
- None

**Major Issues 🟡**
- **`adaptive_replanner.py` + `planning_workflow.py`**: 自动化计划生成和自适应压缩完全不引用 calendar context（grep 确认零匹配）。`should_compress` 仅看 `completion_rate < 0.5 && days_left <= 5`，不看当日考试/上课冲突。Expected: 计划考虑用户当日可用时间。Actual: Aurora 在 chat 中能看到【时间约束】并口头建议，但自动生成的计划完全忽略日历。

**Minor Issues 🟢**
- **`service.py`**: 每日启动个性化消息不参考 calendar context，首屏缺失时间上下文。

**Working Well ✅**: `_get_calendar_context` 实现完整（4 维数据推导 + kill switch + 空数据降级）；`_format_calendar_context_lines` 双路径渲染（完整/仅考试紧迫度）；任务自动同步到日历事件；kill switch 默认 "live"。

---

### D06: 长期用户（30天+）体验——记忆/归档/推送是否退化 (Reviewer B)

**Critical Issues 🔴**
- None

**Major Issues 🟡**
- **`exam_sprint_review_service.py:61,1043-1044`**: `MAX_ARCHIVE_ENTRIES = 10` 硬截断归档。**[已与 C14 Major #2 交叉确认]**。约 70 天后（10 个冲刺）最早的冲刺数据永久丢失。无导出/分页/警告机制。
- **`progress_narrative_service.py:916-936`**: `_compose_weekly_narrative_sentences` 使用固定句式模板，不参考之前周叙事内容。第 4 周和第 12 周叙事结构完全一致。无去重逻辑。

**Minor Issues 🟢**
- **`memory_service.py:610-633`**: `list_recent_episodic` 默认返回最近 10 条，DB 无上限无驱逐。注释 `# TRACKED(TD-008)` 但未实现 rate limits。
- **`notification_center_service.py:80-85`**: 间隔重复提醒标题固定 "Aurora 复习提醒"，框架句式不变。对 10+ 节点的用户消息结构高度重复。

**Working Well ✅**: 每日冲刺提醒使用动态数据（含完成率、任务名）；重复提醒抑制和节点去重机制；空数据有占位文案；记忆状态过滤正确。

---

### D08: 社区→个人AI体验——伙伴活动影响教练吗 (Reviewer B)

**Critical Issues 🔴**
- None

**Major Issues 🟡**
- **`settings.py:320` + `prompts.py:3276`**: `AURORA_STAGE33_SOCIAL_MODE` 默认 `"shadow"`。社交信号在 `SocialSignalBridge` 中被正确计算，在 `context_manager` 中被正确收集，但最终因 kill switch 处于 shadow 模式而不进入 prompt。Aurora 完全不知道用户有活跃的学习伙伴。Expected: 伙伴活跃度影响 AI 建议。Actual: 数据计算但不注入。
- **`dashboard.py`**: Dashboard 零社交信号引用（grep 确认）。即使 kill switch 切到 "live"，dashboard 层面的 AI 个性化也不含社交维度。

**Minor Issues 🟢**
- None

**Working Well ✅**: `build_social_signals_v1` 多维度聚合完善；集成路径通畅（只等 kill switch 切 live）；`_format_stage33_social_signal_section` 含边界感提示符合 Rule Z；accountability_screen 伙伴展示完整。

---

### D01: 离线/弱网行为
**Status**: ⚠️ 无 reviewer 文件 — audit_state 标记 "done" 但无审查产出。仍需审查。

### C04: 错题录入→修复任务插入→计划页橙色卡可见
**Status**: ⚠️ 无 reviewer 文件 — 仍需审查。D02 Critical 间接覆盖了错题→mastery 链路。
