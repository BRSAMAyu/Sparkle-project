# WT651-D04 · 真实 Analytics 接线调查 + 生产 Mock 缓存污染清点（首批低风险收口）

- 会话：wt651（D-04 第一批）｜日期：2026-09-27｜基线：main@dc9575c4｜分支：agent/node-b/wt651/d04
- 方法：worktree 审计+清点为主，接线实施仅限低风险首批（≤3 项）。红线：不以 Mock 冒充模型/统计结果。
- 参照：V3-FIX-330（agent-stats 如实化）/331（残轨删除）/333（五态能力宣称）/337-339（死链清理）；WT639-B01 lifecycle.md 生死簿。

## 总判（污染面统计）

| 轨道定性 | 数量 | 说明 |
|---|---|---|
| 真轨（真实上报/真实聚合） | 12 | 见「二、接线现状图」，端到端可达（网关代理组全在） |
| 受控 demo 轨（门控+自述，非污染） | 4 | 编译期/显式开关或产品化游客演示，见「三、附1」 |
| Mock/失真混入生产宣称面（污染点） | 5 | V3-FIX-345～349；本批收口 345/346/347，348/349 留第二批 |
| 实验台轨（零生产消费但自述实验，非不诚实） | 1 族 | services/analytics 包 6408 行仿真/评估框架 |

网关层：纯代理零统计聚合、零 mock 数据面（galaxy_handler 的 placeholder 是显式中性占位、无排名信号伪造）；缓存预热无 demo 数据注入（bootstrap.sh 演示种子为 `--with-demo-seed` 显式选择且自带清场脚本）。

## 一、排查面与方法

- mobile：`AnalyticsService`/埋点（core/analytics、client_observability_service、aurora_telemetry_service、notification_analytics）、mock/demo 文件（demo_data_service、mock_cognitive/community_repository）、统计 provider（core/statistics）。
- gateway：proxy_routes.go 全部统计/分析组注册（stats:834、client-telemetry:946、predictive:966、missing-loop /analytics:1256）、warmup/mock 关键词全扫。
- backend：api/v1 全统计路由（analytics/statistics/client_telemetry/predictive_analytics/insights/agent_stats/north_star_wvpl）、services/analytics 包、analytics_service、predictive_service、galaxy/stats_service、north_star_metrics_service、notification_analytics_service、business_metrics、guest_seed_service、celery 任务面。
- 形态猎取：random 值入统计路径、硬编码统计值、「模拟数据/示例/占位」自述、.env mock 开关（仅 SPARKLE_SKILL_SHARE_MOCK_REVIEW_ENABLED=false，未接线无碍）、fallback 假数据、缓存预热 demo。

## 二、真实 Analytics 轨道接线现状图

| # | 轨道 | 链路 | 状态 |
|---|---|---|---|
| 1 | 客户端遥测 | mobile ClientObservabilityService（api_interceptor 自动埋点+性能/crash/screen_view，:177/:302/:364/:388）→ POST /client-telemetry/events[/batch] → Redis 日聚合+recent 队列（client_telemetry.py:117,144）→ superuser /summary；网关组 proxy_routes.go:946 | 真轨，端到端通；断网 SharedPreferences 离线队列重放 |
| 2 | 专注统计 | mobile focus_statistics_provider → /focus/stats[/weekly|monthly|heatmap] → FocusService 真 FocusSession 聚合，streak_days=_calculate_current_streak（focus_service.py:655/:723） | 真轨（本批 P2 的对照真源） |
| 3 | 每日/周/热力图 | /stats/daily、/stats/weekly、/stats/activity/heatmap（statistics.py 真 DB 聚合，双源 study_records+已完成任务 fallback，口径注释完备） | 真轨 |
| 4 | 北极星趋势 | /analytics/north-star/trends → NorthStarMetricsService.get_trends | 真轨 |
| 5 | 洞察面 | /insights/recent-directives（Redis 审计）、/insights/evidence-cards（真源现算，无数据不出卡）、/insights/understanding-depth（每日离线聚合） | 真轨 |
| 6 | 预测分析 | /predictive/*（engagement/difficulty/optimal-time/dropout-risk/dashboard/next-intent/realtime-next-step/analytics）→ PredictiveService 真 StudyRecord/任务计算；insufficient-data 走显式缺省（confidence=0.3 + risk=unknown + 「数据不足」自述）；long-horizon 走 celery glm_batch | 真轨（本批 P3 收口其 4 个硬编码空承诺键） |
| 7 | 通知分析 | /notification-center/analytics → NotificationAnalyticsService 真 Notification/InterventionRecord 聚合；写侧经 FIX-337（网关 /push 组）后可达 | 真轨（337 修复前为无源统计，已闭） |
| 8 | 周报 | LearningReportAgent（/learning-reports/generate）+ WeeklyLearningReportService（celery beat）双真轨；weekly_digest_service→WeeklyStatsService（analytics 包内真聚合） | 真轨（331 删 mock 周报残轨后口径已清） |
| 9 | Aurora 遥测 | aurora_telemetry_service → /aurora/telemetry/chip-selected（aurora.py:541） | 真轨 |
| 10 | Agent 执行统计 | /agent-stats/* 四端点（FIX-330 裁决=如实 unavailable，write_side_unwired 标记；agent_execution_stats 表零生产写入方） | 真零如实化（非假零） |
| 11 | 星图统计 | galaxy/stats_service.py（掌握度证据融合真源 mastery_evidence） | 真轨 |
| 12 | 平台指标 | business_metrics/prometheus、token_tracker、cost_wvpl_metrics、north_star_wvpl（frozen schema，自述「不加默认值、不造假数据」） | 真轨 |

断点标注：全仓唯一结构性断链已被 FIX-337（/push 网关组）闭合；本批未发现新的「mobile 上报→网关 404」型断链。

## 三、污染面清单（V3-FIX-345～349）

### P1｜V3-FIX-345（P2，本批 FIXED）
- **位置**：backend/app/agents/enhanced_orchestrator.py（原 :230-278 `_build_enhanced_context`）
- **定性**：休眠残轨自供 mock（331 同形态）。硬编码假知识图谱 `{"total_nodes":50,...}`、假掌握度 `{"高数-极限":0.85,...}`、假遗忘风险、假学习风格 `study_time_preference="evening"`、假常见错误——自述「模拟数据（实际应调用真实服务）」（TD-008 挂账）。全仓零生产调用方（multi-agent/chat 实走 orchestrator_agent.create_multi_agent_workflow）；但经 AGENT_REGISTRY 被 GET /multi-agent/agents 宣称为可用专家；345 行测试固化 mock 行为。
- **清污方案**：删除模块+注册表项+包导出+rule-bj 守卫 ENTRY_POINT_MODULES 项+mock 行为测试；新增退役守卫测试（tests/agents/test_enhanced_orchestrator_retired.py）。
- **风险**：低——/multi-agent/agents 响应少一个从未可执行的宣称项（mobile 零消费面，FIX-330 已证）；真实数据路径已由 enhanced_agents.StudyPlannerAgent（GalaxyKnowledgeService 真源，:149-215）覆盖。
- **裁决依据**：不接线——该类词表/数据面与标准工作流重复，接线即第二套记账（同 330 裁决逻辑）。

### P2｜V3-FIX-346（P3，本批 FIXED）
- **位置**：backend/app/api/v1/statistics.py:152（修前）`"streak_days": current_user.flame_level or 0,  # Using flame_level as proxy`
- **定性**：无关字段冒充统计值——连续学习天数=火花等级，/stats/overview 活端点对外输出假 streak。mobile 对该端点/字段零消费（api_endpoints.dart:232 定义后全仓无引用）；真 streak 由 FocusService 提供。
- **清污方案**：删除冒充字段+注释留痕；新增断言（tests/unit/test_analytics_truth_batch1.py）。
- **风险**：低——零 wire 消费方、无 response_model（快照仅 docstring 面）、后端测试零断言该键。

### P3｜V3-FIX-347（P3，本批 FIXED）
- **位置**：backend/app/api/v1/predictive_analytics.py（修前 :65-67/:112）
- **定性**：硬编码统计值冒充——/predictive/engagement 恒返 `typical_weekdays:[] / typical_hours:[] / prediction_factors:[]`、/predictive/difficulty 恒返 `difficulty_factors:[]`，而 docstring 宣称「典型活跃日/典型活跃时段/难度因素分析」。全仓（mobile/scripts/tests/tests_e2e）零消费方。
- **清污方案**：删除 4 个未接线承诺键+docstring 同步；新增断言同上测试文件。
- **风险**：低——纯删键+docstring，快照重刷后契约绿；service 层真实计算不受影响。

### P4｜V3-FIX-348（P3，OPEN，留第二批）
- **位置**：backend/app/services/analytics_service.py:23（calculate_daily_metrics）/:156（get_user_profile_summary）；backend/app/models/analytics.py:14（UserDailyMetric）
- **定性**：写侧真空（330 同形态）——`calculate_daily_metrics` 全仓零调用方（api/orchestration/agents/tasks/scripts/tests_e2e 全扫），UserDailyMetric 表结构性零写入；而 `get_user_profile_summary` 被 chat.py:1075、cognitive_service.py:54、analysis/unified_analysis_service.py:26 活消费，读恒空表后把 `[Recent Activity (Last 7 Days)] Total Focus Time: 0 minutes / Recent Anxiety Index: 0.00` 当测量值格式化进 LLM 上下文。
- **清污方案（候选）**：接线每日聚合任务（celery beat）或按 330 形态如实化（data_status=unavailable/摘要降级为仅用户本体字段）。
- **风险**：中——消费面在 chat 主链上下文装配，需红测+上下文面回归。

### P5｜V3-FIX-349（P4，OPEN，留第二批）
- **位置**：mobile/lib/core/analytics/models/user_analytics_event.dart（Isar 集合 uae_815 + 双索引 i_uae_et_106/i_uae_ts_1220）；mobile/lib/core/offline/local_database.dart:180/:223
- **定性**：死轨——UserAnalyticsEvent 本地事件集合注册进 Isar schema 但全 app 零写零读（`analyticsEvents` 仅 getter 定义）；真实遥测已由 ClientObservabilityService（SharedPreferences 队列）承担，本集合是被绕开的死设计。
- **清污方案（候选）**：删集合+schema 项（需 build_runner 重生成 .g.dart+存量安装兼容评估）。
- **风险**：中低——Isar schema 变更需真机/模拟器回归，工作树无 flutter 构建 venv，留第二批。

### 附1｜受控 demo 轨（门控+自述，判非污染，留观）
1. **DemoDataService.isDemoMode**（mobile/lib/main.dart:127-129）：编译期 `DEMO_MODE` 常量 ∥ 用户 pref `demo_guest_mode_enabled`（auth_provider.dart:19）→ 约 40 个 repo/provider 分支走 demo fixtures（chat/task/galaxy/insights/leaderboard 全 feature 覆盖）。生产构建可经游客演示入口翻转且 pref 持久——比赛演示产品特性；风险注记：翻转后用户全程看 mock 数据，若与真数据混清需 UI 显式标记（现有 demo 标识面未逐屏核验）。
2. **游客播种**（auth.py:954-979 → guest_seed_service，:1678 自述 best-effort 演示数据）：游客账号播种演示任务/星图——产品化体验轨；注记：这些演示行会进入该游客账号自身的统计聚合（/stats/* 只按 user_id 过滤），游客升级为正式用户后演示数据随账号保留，统计面含播种值（产品裁决项，不构成本批登记）。
3. **bootstrap.sh step7.5**（--with-demo-seed 默认关 + LOCAL_SMOKE_PASSWORD + clean_demo_data.py 清场指引）。
4. **scripts/dev/up.sh** demo seed（开发环境轨）。

### 附2｜实验台轨（非生产宣称，不动）
services/analytics 包（6408 行）：belief_recovery_simulator、dual_core_decision_bench、sim_real_diagnostics、probe_validation、ope_gatekeeper、signal_inventory、bkt/irt、contextual_bandit 等——生产消费仅 contextual_bandit（经 orchestration/rl/routing_mdp）与 weekly_stats_service（经 weekly_digest_service），其余仅测试引用；README 自述「experimental framework for evaluating the DualCore Router」，仿真器无生产宣称面。建议将来给仿真族加 `# lab-bench` 头注（未列卡）。

### 附3｜排查过判非污染的样本
- error_book_service.py:126 random.uniform 间隔抖动（SM-2 类间隔模糊，非统计造假）；capsule_generation/curiosity_capsule/push_strategies 的 random 为产品随机选择非统计值。
- routing_parameter_registry/semantic_router 的 "hardcoded defaults" 为配置缺省自述。
- workflow_experience.py:598 种子库示例数据已围栏化（FIX-68）。
- north_star_wvpl.py 显式「不加默认值、不造假数据」；capsules.py:481 显式「无数据来源返回 0/None，绝不以假数据填充」。

## 四、首批实施记录（本批 3 项，全部删 Mock/断轨收口）

| 项 | 变更 | 红→绿 |
|---|---|---|
| V3-FIX-345 | 删 enhanced_orchestrator.py+tests/agents/test_enhanced_orchestrator.py；agents/__init__.py 摘 import/注册表/__all__；rule-bj 守卫摘 ENTRY_POINT_MODULES 项；test_llm_wrapper_signature_contract a9 占位改退役说明 | 新守卫 3 用例修前 3 红（module 存在+registry 含键）→修后绿 |
| V3-FIX-346 | statistics.py 删 streak_days 冒充字段+留痕注释 | test_overview_has_no_flame_proxy_streak_days 修前红（键在）→绿 |
| V3-FIX-347 | predictive_analytics.py 删 4 空承诺键+docstring 同步 | engagement/difficulty 2 用例修前红（键在）→绿 |

## 五、验证记录

- 新守卫测试 6 用例：修前 6 红 → 修后 6 绿（tests/agents/test_enhanced_orchestrator_retired.py + tests/unit/test_analytics_truth_batch1.py，sqlite in-memory）。
- 触达回归：tests/agents/ + 契约/统计/预测 11 文件 74 passed；multi-agent 邻接 3 文件 11 passed；agent-stats 真值 5 passed；tests/unit/test_llm_wrapper_signature_contract.py + tests/api 全目录 413 passed 5 skipped。
- 守卫：scripts/guards/check_rule_bj_dead_imports.py PASS（no dead imports）。
- ruff 0.15.12（/tmp/ruff112）触达 7 文件：修后仅剩 1 处 HEAD 既有 F841（check_rule_bj_dead_imports.py:413，非本卡引入）；顺手收口同文件 HEAD 既有 F401 与契约测试 HEAD 既有 I001/B009（B009 以 noqa 保 getattr 动态语义）。
- mypy 触达 3 app 文件：归因修前后均 0 错误；全闭包对照 HEAD 180→181，唯一增量 `app/aurora/core_session.py:757 self.redis`（=已登记 V3-FIX-343，wt645 辖区，本卡零触达该文件，系闭包分析集差异非本卡引入，如实披露）。
- 契约：check_openapi_contract.py 修前 drift（含 330 既有 agent-stats docstring 漂移+本批 346/347 docstring 变更）→ 官方 `--update` 重刷快照（纳入 HEAD 既有 330 漂移，如实披露，同 331 先例）→ 复检 exit=0。
- 纪律：未碰 gen/、.env、mobile 构建产物；未 push；并行卡避让核验（wt645 aurora core_session / wt646 similarities+graphrag+onboarding / wt648 mypy 簇 / wt650 gateway gosec——触达文件零交叠）。

## 六、第二批建议（按优先级）

1. V3-FIX-348 UserDailyMetric 写侧接线或摘要如实化（chat 主链上下文，需产品裁决+红测）。
2. V3-FIX-349 UserAnalyticsEvent Isar 死集合删除（需 flutter 工具链+存量安装回归）。
3. DemoDataService 游客翻转的 UI 显式标记审计（demo 标识逐屏核验，产品面）。
4. 游客播种数据对升级用户统计面的产品裁决（播种行保留/清理策略）。
