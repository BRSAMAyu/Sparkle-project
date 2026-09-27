# WT624-TRUTH · 指标数据真实性 / Mock 污染 / Lineage 基线（只读审计）

- 工位：wt624 ｜ 卡池卡 B-02「数据真实性、Mock 污染与指标 Lineage 基线」（LIGHT，锁 analytics-truth）
- 基线：main 头 `eed665f78660d99f10438c55a2a376ed8d42d2af`（分支 `agent/node-b/wt624/truth`）
- 日期：2026-09-25 ｜ 方法：只读对码（数据源表 → 计算路径 → 出口逐族溯源）+ 全仓写入方/消费方 grep 反查 + 前序 B-02/WT587/WT594 证据对照
- 在案不重报：V3-FIX-286（guest 种子观测面）、292–299（掌握度族确定性重放/影子行，299 甄别机制在案待修卡）、303（fallback 实际服务模型记账归位，已验 `7ef8e4ae` 在 HEAD）。亦不重报已闭账的 V3-FIX-01/07/08/20（cohort 排除族）、11/14（遥测边界封顶）、287/257/258（demo origin 标记/转正清洗）、D-04（mobile core/statistics legacy mock 缓存清除——本次复核 `hybrid_statistics_repository.dart:126-139` legacy purge + fabricated 永不入缓存在位，老 B-02 F3 已闭环）。
- 严重度口径：P2 = 用户可见数字失真/口径漂移；P3 = 断产字段、休眠 mock、窄面 cohort 缺口、文档债。

---

## 一、指标族盘点（数据源 → 计算路径 → 出口）

20 族。评级：**actual** = 真实数据源真实计算；**estimated(明示)** = 模型/规则估计且命名或字段声明；**demo(门控)** = 体验模式门控内；**dead** = 出口在、数据源断。

| # | 族 | 数据源表/键 | 计算路径 | 出口 | 评级 / 状态 |
|---|---|---|---|---|---|
| 1 | 全局/分项排行榜 | users + user_node_status + user_streak_stats + user_achievements | 权重和（mastery≥50×1.0+checkin×0.5+成就×2.0+longest×1.5） | `GET /leaderboards/*` + self-anchor | actual；guest/seed 排除在位（FIX-01/07，`leaderboard_service.py:62-65,258-259,648,717,787,865`）；my-score 有意不过滤（钉住） |
| 2 | 社群面（群发现/搜索/squad board） | groups/group_members/users | SQL + `_seed_cohort_group_clause` | `community.py` | actual；种子群不进发现面（FIX-20）、搜索排 cohort（FIX-07/08） |
| 3 | 匿名社群聚合 | CommunityAggregateSignal（privacy budget） | opt-in 过滤 + k-匿名 | `/community/aggregates*`（user 见 candidate；admin 全量） | actual；**唯一天然聚合口无 cohort 排除 → F4** |
| 4 | Growth dashboard / 首页每日一句 | tasks + focus_sessions + study_records + user_streak_stats + user_node_status + plans | 窗口聚合 + AI/rule 双路（`source=ai/rule` 标注） | `GET /growth/*` | actual；plan chip `is_example` 标种子演示（FIX-142）；本地日钟已修（FIX-209/211） |
| 5 | Dashboard status（weather/flame/sprint/cognitive） | tasks + plans + cognitive_fragments/behavior_patterns + user.flame_level | 规则计算 | `GET /dashboard/status` → home metrics_row/focus_card/cognitive_state | actual 计算但 **双断点 → F2**（UTC 日界 + focus 命名口径） |
| 6 | 统计 API | tasks + focus_sessions + study_records + user_achievements + user_node_status | 窗口聚合（daily/weekly/heatmap 本地日钟已修 FIX-37/197） | `/statistics/daily|weekly|heatmap` | actual（移动端经 focus 域消费 heatmap/streak） |
| 7 | 统计 overview/learning-summary | 同上 + users.flame_level | 计数 + proxy | `/statistics/overview`、`/statistics/learning-summary` | **字段级口径断点 → F1**（streak_days=flame_level；study_days=日历跨度）；当前无第一方消费者（休眠 API） |
| 8 | 连续性族 | user_streak_stats/user_streak_day + tasks + study_records + accountability_checkins | 质量加权 streak（`streak_quality.py`，本地日+UTC 瞬间双钟，FIX-320 定界） | experience/streak_router + accountability | actual；搭档打卡为 partnership 内真实行 |
| 9 | 经验/XP 读出面 | goals/plans/tasks + demo/seed 值域差异 | SSOT goal_today_view + readouts | `/experience/*` | actual；demo/seed 产 percent/count/days/time 值域差异被读侧标注（`experience_readouts.py:176`） |
| 10 | 光子族 | photon_transaction_history + users | 幂等发放/扣除 + REDEEMABLE_INCOME_TYPES 可兑换词表 | `/photons/*` + boards | actual；guest_seed 交易 `source='guest_seed:*'` 可追溯；mint-fix/boards cohort 已修 |
| 11 | 成就族 | achievement 引擎事件消费 + user_achievements | 事件驱动解锁 + 进度 | `/achievements/*` counters | actual；guest 种子 944 行只在 guest 自身体验面可见，跨用户面已排 cohort |
| 12 | 掌握度/星图族 | user_node_status + mastery_evidence 审计行 | Kalman 融合 + 确定性重放 | galaxy API/星图 | 已修族（FIX-292-298）；299 影子行甄别在案（WT594 裁决材料），本卡不重报 |
| 13 | 理解深度/五维/校准 | context_pack_runs + chat_messages + memory_corrections + aurora_judgment_records 等 | Celery 每日离线聚合（幂等 upsert）→ `understanding_depth_daily`/`understanding_dimension_daily` | `/insights/understanding-depth|understanding-dimensions` | actual；lineage 元数据齐（`definition_version: v0.1`、unknown 如实、漂红 withhold）；**聚合计算不排 guest/seed（注记 N2）** |
| 14 | 北极星（per-user trends） | north_star_metric_events | 事件 upsert + 日桶聚合 | `/analytics/north-star/trends` | actual；exam_pass_probability 命名即声明 estimated |
| 15 | 北极星 WVPL fact | users + tasks/study_records/focus_sessions/quiz + outcome ledger | 周窗构建 + cohort 排除 + `definition`/`generated_by` 元数据 | `north_star_wvpl_service.build_fact` | actual，**lineage 范本**（`build_fact:150-156,287,293`） |
| 16 | 真实结果账本（O-02 面） | task completions + run receipts + study_records + focus_sessions + quiz_feedbacks + behavioral | 五流分类 TruthClass（actual/self_reported/unknown） | `outcome_ledger.query/truth_coverage` | actual；`_cohort_filter` 内建（`outcome_ledger_service.py:447-452`）；截断窗语义 docstring 自证 |
| 17 | token/成本/trace 记账 | llm usage 帧 → Prometheus + `llm_tokens:{uid}:{date}`（网关 QuotaService 真源，budget_matrix 对齐）+ TokenTracker 模式键 + `queue:billing` → TokenUsage 表 | 实际服务模型记账（FIX-303 已修，`llm_service.py:1458-1483,1822-1840`）+ O-02 spine span | `/metrics`、`/settings/ai-usage*`、run ledger | actual；**断产分量 → F3**（first_token/stream latency 无生产者）；合成 token 估算经 `resolve_metering_model_key` 区分（FIX-80） |
| 18 | Agent 执行统计 | `agent_execution_stats` 表（+ 物化视图 agent_stats_summary） | SQL 聚合 | `/agent-stats/*` + mobile `agent_statistics_provider` | **dead 族 → F5**：全仓零生产写入方 |
| 19 | 周报族（三轨） | ① LearningReportAgent：mastery/error_patterns/timeline/chat 推断（诚实 fallback，`verified:false`）② WeeklyLearningReportService：ProgressNarrative 快照（无证据不出报+skip 计数）③ WeeklySynthesisService：真实 stats + **硬编码 mock AI 洞察** | 见左 | ① `/learning-reports/generate`（mobile 消费）② celery `weekly-learning-report` beat→system updates ③ `/analytics/reports/generate`（休眠） | ①② actual；③ **mock → F6** |
| 20 | 考试冲刺/预测 | sprint intake + diagnostic | 模型估计 | exam_sprint dashboard / prediction API | estimated(明示)：`estimated_score_now`/`pass_probability`/`confidence` 字段名声明 |

运营注记面（非用户真相面）：`admin_dashboard._user_counts` 与 `DashboardService.generate_daily_report.active_users` 不排 guest/seed（160 游客种子账号计入 total/active）→ 注记 N1。

## 二、发现清单

### F1（P3）｜`/statistics/overview` 的 `streak_days` 字段拿 flame_level 冒充，`study_days` 是日历跨度非学习天数

- **file:line**：`backend/app/api/v1/statistics.py:152`（`"streak_days": current_user.flame_level or 0,  # Using flame_level as proxy`）、`:134-140`（`study_days = (now - first_task).days + 1`）。
- **机制**：字段名声明「连续打卡天数」，实际值是 gamification 等级（guest 种子 flame=15 → 恒显 15）；`study_days` 是首任务以来的日历跨度，非活跃日去重计数。同文件 `/overview` 的 `flame_level` 字段已经返回同值——同屏两键同值异名。
- **用户可见影响**：当前为 **休眠 API**（mobile `api_endpoints.dart` 无 `/statistics` 常量、全仓无第一方消费者）；但端点活、被 `/learning-summary` 兼容聚合携带，第三方/验收脚本一接即假。与 FIX-01 后 guest flame=15 叠加会产出「streak 15 天」假数字。
- **修复建议**：返回真实 streak（`user_streak_stats.current_streak` 或 `streak_quality.current_streak`）；`study_days` 改活跃日去重或更名 `days_since_first_task`。量级 **S**。

### F2（P2）｜首页 dashboard flame 卡与 sprint 卡是「同族修漏」：UTC 日界 + "focus" 命名口径漂移

- **file:line**：`backend/app/services/dashboard_service.py:206-218`（`_get_today_focus_minutes`：`_utcnow().replace(hour=0,...)` UTC 零点 + 注释自认「focus time from completed tasks」，源是 `Task.actual_minutes` 非 FocusSession）、`:220-230`（`_get_today_completed_tasks` 同 UTC 界）、`:156-179`（`_get_active_sprint` 的 `days_left` 用 `_utcnow().date()` UTC date）。
- **机制**：V3-FIX-37/197（statistics daily 本地日）、209/211（growth dashboard days_left/streak 本地日）、318-323/327（calendar/streak_quality/ledger/guest_seed 各面同钟）逐面修过，`dashboard_service.py` 全文件无任何 FIX 标记——首屏 flame 卡被整族修复漏掉。UTC+8 用户本地 00:00–08:00「今日」桶归属前一日；本地晚间已完成任务在次日凌晨被甩出「今日」。
- **用户可见影响**：home `metrics_row.dart:58`、`focus_card.dart:64`、日历 `daily_detail_screen.dart:492` 直接渲染该值；`cognitive_state_provider.dart:24` 以 `todayFocusMinutes >= 90` 驱动首页认知态分支；sprint `days_left` 偏一日会翻转 weather 规则（`dashboard_service.py:322-327` 的 rainy/cloudy 阈值）。同屏 `growth_status.streak_days`（本地日）与 flame 卡「今日」数值互相矛盾（老 B-02 复核过的「daily line 与 live dashboard 打架」同型）。
- **修复建议**：三处对齐 `time_utils.local_midnight_as_utc_naive` / `local_date`（同族先例照抄）；`today_focus_minutes` 改源 FocusSession（或更名 `today_task_minutes` 并与 statistics/daily 的 due_date 口径对齐）。量级 **S**。

### F3（P3）｜AI 额度面板的 `avg_first_token_ms`/`avg_stream_duration_ms` 是「有字段、有 UI、无生产者」的恒 0

- **file:line**：唯一生产写入点 `backend/app/orchestration/response_builder.py:1690`（`timing_stats={"total_duration_ms": ...}`——全仓唯一 `record_usage` 调用，只传总时长）；读写契约 `backend/app/orchestration/token_tracker.py:135-149`（`first_token_ms`/`stream_duration_ms` 键族）与 `:560-562,575`（读侧平均）；UI 渲染 `mobile/lib/features/user/presentation/screens/unified_settings_screen.dart:3608,3634`（`aiUsageLatency(avgFirstTokenMs, totalMs)`）。
- **机制**：`get_chat_mode_timing_summary`（`ai:daily_timing` 聚合）与 `get_mode_usage_summary` 的首 token/流时长分量在 schema、Redis 键族、移动端文案（「首 token Xms」）三层齐备，但生产链从未传过这两帧——`grep first_token_ms orchestration/ services/` 除读写两端外零命中。数字不是错值，是**永远 0ms 的假零**。
- **用户可见影响**：设置页「今日 AI 额度与消耗」面板对真实用户恒显「首 token 0ms」；`/settings/ai-usage/export` 的 timing 摘要同染。
- **修复建议**：llm_service 流式链已有真实 TTFT 采样（span `llm.first_token_ms` 埋点存在），回填进 `record_usage(timing_stats=...)`；或读侧对未产出分量返回 null 并让 UI 走「不可用」分支。量级 **S**。

### F4（P3）｜匿名社群聚合是 cohort 排除词表先例下唯一漏网的跨用户聚合口：缺省 opted-in 且无 EXCLUDED_COHORT 过滤

- **file:line**：`backend/app/services/community_signal_bridge.py:418-455`（`_filter_opted_in_values`：无 settings 行的用户**缺省并入 opted-in** `unknown_ids → opted_in.update`，且只查 opt-in 不查 registration_source）；对照先例 `backend/app/core/telemetry_boundary.py:95`（`EXCLUDED_COHORT_REGISTRATION_SOURCES`）。
- **机制**：所有其它跨用户面（排行榜 FIX-01、streak/photon/weekly boards+友缘池+搜索 FIX-07、群发现 FIX-20、outcome ledger、WVPL）都按词表排 guest/seed；唯 community aggregates 只靠 opt-in。guest（demo 模式下发起真实 API 操作：完成群任务 claim 等）行会进 k-匿名 cohort pattern，真实用户在 `/community/aggregates/insights` 看到「同侪平均」被演示账号行为稀释。
- **用户可见影响（当前面窄）**：生产信号构建被 `_community_mode() != "live"` 门（`community_signal_bridge.py:122-125`）+ admin `/analyze` 手动触发双闸；mode=live 一开即暴露。demo/游客操作缺省计入（opt-in 缺省为入）扩大了暴露面。
- **修复建议**：`_filter_opted_in_values` 的 settings 批查 join/补一个 `users.registration_source NOT IN EXCLUDED_COHORT` 谓词（词表 import，与 FIX-01 措辞对齐）；缺省方向翻为 opt-out（另议）。量级 **S**。

### F5（P3）｜Agent 执行统计是「全链接线、数据源真空」的 dead 族：`agent_execution_stats` 全仓零生产写入方，API 恒返真零且不带 degraded 标

- **file:line**：表模型 `backend/app/models/agent_stats.py:14-16`；唯一写入口 `backend/app/services/agent_stats_service.py:29-87`（`record_agent_execution`——全仓零调用，`grep AgentStatsService` 出自身与 API 外无命中）；读出口 `backend/app/api/v1/agent_stats.py:23-63`（router 已挂载 `api/v1/router.py:250`）；降级标志 `agent_stats.py:20-22` 只在**表/物化视图缺失**时置 `degraded: true`，表在无行时返回的 0 无任何标记；mobile 侧 `api_endpoints.dart:582-583` 注释声称「Agent Statistics (real DB aggregation via /agent-stats)」。
- **机制**：与 mock 污染相反的失真方向——管线全部真实（真实 SQL、真实计数），但写侧从未接线，产出的是**被冒充为测量值的结构性零**。UI 消费面当前休眠（`core/statistics/agent_statistics_provider.dart` 无屏幕 watch，与老 B-02「休眠脚手架」结论一致），但 API 面活。
- **用户可见影响**：直连 API 的验收/第三方看「总执行 0 次、成功率 0%」；mobile 一旦把休眠 provider 接上屏即假零上屏。
- **修复建议**：二选一——orchestrator/standard_workflow 的 agent 边界补 `record_agent_execution` 埋点；或整族下线（router+表+provider），别让「永远 0 的真表」留在出口面上。量级 **S**（补埋点）/ **M**（含清表下线）。

### F6（P3）｜休眠周报轨 `WeeklySynthesisService` 的「AI 洞察」是自供硬编码 mock，与真实周报双轨并存

- **file:line**：`backend/app/services/analytics/weekly_synthesis_service.py:145-157`（注释自供 "Return Mock for speed/reliability in this MVP step"；`ai_insight` 是模板串——"with good focus consistency" 无条件拼接，不看真实 focus 数据）；`:126-143` 提示词 f-string 是**未赋值的死表达式**（连 mock 也没喂它）；出口 `backend/app/api/v1/analytics.py:41-58`（`POST /analytics/reports/generate` + PDF 落 `/tmp`）。
- **机制**：真实周报有两轨——`LearningReportAgent`（诚实 fallback+`verified:false` 溯源，mobile 消费）与 `WeeklyLearningReportService`（celery beat、无证据不出报+skip 计数器）；本服务是第三条 MVP 时代残轨，响应字段名 `ai_insight`/`ai_suggestion` 字面冒充模型产出，触碰「不以 Mock 冒充模型结果」红线，只是当前休眠（无第一方消费者、route-tier internal）。
- **用户可见影响**：现状无；一旦被误接（字段名与真实周报高度相似，双轨易混）即把模板文案当 AI 洞察上屏/进 PDF。
- **修复建议**：删除该服务+路由（真实周报已两轨覆盖）；或把 `_generate_llm_insights` 接 `analysis_llm` 并删死 f-string。量级 **S**。

### 注记（不计发现）

- **N1**：`admin_dashboard._user_counts`（`api/v1/admin_dashboard.py:63-77`）与 `DashboardService.generate_daily_report`（`dashboard_service.py:45-47`）的 total/active 计数含 guest/seed（live 比例 historic ~73% guest）。运营口径面，建议报表按 cohort 分列。
- **N2**：`understanding_depth/dimensions` 每日聚合（`understanding_depth_metric_service.compute_daily_all`）不排 guest/seed cohort——出口为 per-user 趋势故无用户可见污染，但种子账号行进聚合表：未来任何 cohort 级读面（如「产品平均理解深度」）接上即污染，建议在 `compute_daily_all` 用户集上加词表过滤（S）。
- **N3**：`statistics/overview.flame_level` 本身是 gamification 字段直出（guest=15），entitlement 侧派生已被 `core/entitlement.py` 防复发闸钉住（在案），本注记只覆盖展示面。

## 三、guest/seed 排除矩阵（任务项 2 汇总）

| 跨用户面 | 排除状态 |
|---|---|
| 全局/分项排行榜 | ✅ FIX-01（`leaderboard_service.py` 五处） |
| streak/photon/weekly 榜、友缘池、用户搜索 | ✅ FIX-07 |
| 群发现/内容面 | ✅ FIX-20（`_seed_cohort_group_clause`） |
| outcome ledger / WVPL fact | ✅（`_cohort_filter` / `build_fact:150`） |
| 遥测→决策（estimator/replanner/emotion） | ✅ V3-FIX-11（`telemetry_boundary.py` 常量+契约守卫） |
| 匿名社群聚合 | ❌ 仅 opt-in、缺省入 → F4 |
| understanding 每日聚合计算 | ❌（出口 per-user，见 N2） |
| admin/运营计数 | ❌（见 N1） |
| demo 数据回真指标（服务端） | ✅ persistence origin=DEMO 单点+读侧过滤（FIX-258，WT587 复核一致） |
| mobile demo 面回真指标 | ✅ 门控（`main.dart:127-129` 编译期/prefs 双闸；insights repos repo 级 gating；core/statistics D-04 后 fabricated 永不落 Isar） |

## 四、Lineage 评价

- **范本**：WVPL fact（`definition`/`generated_by` 元数据随行）、`/insights/understanding-dimensions`（unknown 如实、漂红 withhold、校准块随行）、outcome ledger（truth 分类+截断语义自证）、growth daily line（`source=ai/rule`）。
- **断点集中带**：本次 6 条发现中 3 条（F1/F2/F3）都是「字段名/schema/UI 声明了 A，计算/生产链实际给 B/0」——即 lineage 断点不在治理缺位，而在**老残面与新契约不同步**：statistics overview（残）、dashboard flame 卡（同族修漏）、ai-usage timing 分量（半接线）。建议后续卡优先按「出口字段 → 生产者存在性」反向扫描一遍 `dashboard_service.py`/`statistics.py`/`token_tracker.py` 三个文件，同类残面大概率收干净。

## 五、后续任务映射建议

| 建议编号 | 对应 | 量级 |
|---|---|---|
| T-truth-flame-clock | F2：dashboard flame/sprint 卡本地日同钟 + focus 口径对齐 | S |
| T-truth-statsproxy | F1：/statistics/overview streak_days/study_days 口径 | S |
| T-truth-aiusage-latency | F3：first_token/stream latency 回填或读侧 null | S |
| T-truth-aggregate-cohort | F4 + N2：community aggregates 与 understanding 聚合补词表过滤 | S |
| T-truth-agentstats | F5：agent-stats 补埋点或下线 | S/M |
| T-truth-weeklymock | F6：WeeklySynthesisService 删除或接真 | S |
