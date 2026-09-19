# B-02X · 9 项用户可见数字 lineage 补全（B-02 续卡）

- Worker: wt6 @ `0cbfd777`（B-02 第二路 Reviewer REVIEW_RECEIPT_2.md §五「后续卡建议」9 项，实际清单正好 9 项，无缺漏）
- 日期: 2026-09-19 ｜ 方式: mobile/gateway/backend/proto 静态走读（全链文件:行号）+ `docker exec sparkle_db psql` 只读 SELECT + Redis 只读 scan（因口令不可得未遂，缓存结论以代码为证）+ `:8080` 未鉴权 curl 探测。LIGHT 硬约束遵守（无模拟器/Gradle/flutter/浏览器自动化；DB 只读；未 commit）。
- live DB as_of: **2026-09-19 04:28 UTC**（users=248 = guest 166 / email 75 / seed 7，与 R2 复核时一致）
- 交付: `lineage_extension.csv`（与主 lineage.csv 同 13 列 schema，csv 模块写入，程序化自检 header+9 行全 13 列零错位——主卡 C5 的 5 行错位在本扩展中不存在）
- 评级口径沿用 FINDINGS.md §一（actual / actual BUT seed_inflated / estimated / demo / mock）。

---

## 结论速览

| # | metric_id | 评级 | 对主卡 lineage 的修正 |
|---|---|---|---|
| 1 | insights_weekly_narrative | actual（规则生成于真实周数据；**非 LLM**） | **「LLM 生成」「缓存 7d」两处失实** |
| 2 | insights_growth_dashboard | actual | insights 实际入口是 `/experience/growth-dashboard` 聚合，非 `/growth/dashboard` |
| 3 | understanding_snapshot | actual | 原判成立；self-model 为 Redis 状态机 + Bayesian 校准，链路补全 |
| 4 | home_predictive | estimated（明示置信度） | confidence 透出属实；**fallback_used 仅 next_intent 子负载有**，顶层降级未明示（R2 问号部分成立） |
| 5 | home_growth_status | actual | rule/ai source 后端明示、mobile 已解析但 **UI 未渲染**该标签 |
| 6 | community_feed | actual computation BUT cohort_polluted | 定量实锤：公开帖 331/331 全为 guest/seed 作者，email 用户 0 帖 → 新增 **INV-15** |
| 7 | cognitive_patterns | actual BUT seed_inflated | 原判成立且污染加重（guest 327/332 = 98.5%）；产出方为 LLM 分析（有 rule 兜底）补全 |
| 8 | focus_stats | actual（双路皆真实记录） | **「本地优先+服务端合并」与实现相反**：实为 API 优先/本地兜底 + 单向上行；mergeServerSessions 全库无调用方（休眠） |
| 9 | photon_balance | seed_inflated（D05 边界内） | 主卡空位补正：专属 `/photons/balance` 链路已在位；游客转账已被 is_guest JWT 403 服务端拦截 |

---

## 1 · insights_weekly_narrative — actual（规则生成于真实周数据；非 LLM）

**链路**：`WeeklyGrowthNarrativeCard`（`weekly_growth_narrative_card.dart:35` watch provider；页面 `learning_insights_overview_screen.dart:68`）→ `weekly_growth_narrative_provider.dart:13-18` → `GrowthNarrativeRepository.getWeeklyNarrative`（`growth_narrative_repository.dart:28-56`，读 `GET /experience/growth-dashboard` 响应中的 `weekly_narrative` 字段，:40-48 解析；demo 分支 :29-31 返回 `placeholder()`，gated）→ gateway `/api/v1/experience/*`（`proxy_routes.go:989-994`，authMiddleware；未鉴权 401 实测）→ `api/v1/experience/dashboard_router.py:29-36` → `_GrowthExperienceDashboardBuilder._weekly_narrative`（:109-115）→ `ProgressNarrativeService.get_weekly_narrative`（`progress_narrative_service.py:216-244`）→ `build_weekly_narrative`（:246-395）。再生路径：`generateWeeklyNarrative`（repo :58-76）→ `POST /growth/weekly-narrative/generate`（`api/v1/growth.py:57-65`，同一 service force=True）。

**数据源与公式**：九类真实周数据 SQL（Task :457-508 / StudyRecord :511-543 / ErrorRecord / MemoryCorrection / BehaviorPattern / Plan / TaskFeedback，imports :16-27，全部 user_id 隔离）→ 规则模板句组装（`_compose_weekly_narrative_sentences`）；空数据走明示 placeholder 文案（:336-344，`is_placeholder=True`）；`source_counts` 透出来源计数（:324-334）。缓存：Redis 周一锚 key（:1344-1348），TTL = week_end + **2 天 grace**（最短 3600s，:1350-1355）。

**评级与风险**：actual。**主卡两处失实**（「LLM 从真实周数据生成叙事」+「Redis 缓存 7d」）：全文件无 llm import、无 LLM 调用——叙事是规则模板；缓存非固定 7d。风险面：guest 账号的周数据输入本身为种子数据（本卡各 DB 查询佐证），但叙事机制真实。

## 2 · insights_growth_dashboard — actual

**链路**：`LearningDashboardScreen`（`learning_dashboard_screen.dart:19`）/ `GrowthChronicleScreen`（`growth_chronicle_screen.dart:17`）→ `growth_dashboard_provider.dart:8` → `GrowthDashboardRepository.getGrowthDashboard`（`growth_dashboard_repository.dart:19-38`；demo 分支 :20-22 placeholder，gated）→ `GET /experience/growth-dashboard` → gateway :989-994 → `dashboard_router.py:29-36` → `_GrowthExperienceDashboardBuilder.build`（:82-107）。

**数据源与公式**：五组纯 SQL 聚合——time_distribution（FocusSession×Task :136-161，share≥0.34 记 trend=up :158）、efficiency（Task 完成时长/准时率 :163-186）、weakness_radar（UserNodeStatus×KnowledgeNode 最弱 6 项 :188-209，bkt 优先归一化 :333-337）、knowledge_changes（StudyRecord before/after :211-236）、plan_stability（中断/放弃率 :238-263）；外加 `GrowthDashboardService.build_snapshot`（:84）与 Redis chronicle（:117-134）。

**评级与风险**：actual，无 mock/random 分支。修正：主卡把 insights 面记到 `/growth/dashboard` + GrowthDashboardService——那只是其中的子调用；真实入口是 experience 聚合路由。风险：guest 账号的 radar/knowledge 输入为种子预写（对游客演示失真，per-user 无跨用户污染）。

## 3 · understanding_snapshot — actual

**链路**：`UnderstandingSnapshotCard`（`dashboard_screen.dart:1124` 挂载）/ `UnderstandingPanel`（`understanding_panel.dart:31`）/ `UnderstandingDrawer` → `understanding_snapshot_provider.dart:178-185` GET `/experience/understanding-snapshot`；corrections :187-210 POST（claim/correction/effect_scope）。**文件无 DemoDataService import——主卡「无 demo 短路」声明属实**。gateway :989-994（401 实测）→ `understanding_router.py:196-222` → `SparkleSelfModelService.get_readout_summary`（`aurora/runtime_v1/self_model.py:110-127`：Redis 状态 `_load_or_initialize` + 上下文注水 `_hydrate_assumptions_from_context` + Bayesian 策略校准挂载）+ `AuroraControlSurfaceService.build_snapshot`（:204）。corrections → `record_user_correction`（:232-236）+ Redis effect 键 24h（:190 附近）。

**公式**：claims = known_assumptions；confidence≥0.75 计 high（:206-207）；`high_confidence_ratio = round(high/total, 4)`（:208-210）。

**评级与风险**：actual（可解释 claims，符合 D06）。风险：数据极冷——DB `memory_corrections` 全库仅 1 行（as_of 04:28），数字真实但样本近零，属早期态而非造假。

## 4 · home_predictive — estimated（明示置信度）

**链路**：`LearningForecastScreen`（`learning_forecast_screen.dart:53-61` 经 `core/services/predictive_service.dart:35-48 getDashboardData`——demo 分支 :37-39 `_getMockDashboardData()` gated；:218 渲染 engagement_forecast）+ `dashboard_repository.dart:187-313 getPredictiveDashboard`——**demo 分支 :188-305 硬编码 confidence 0.76/0.34/0.72（DemoDataService.isDemoMode gated，与主卡 exam_sprint 同款门控）**，正常路径 :306-313 → `GET /predictive/dashboard` → gateway `proxy_routes.go:857-861`（401 实测）→ `predictive_analytics.py:205-256` → `PredictiveService`（`predictive_service.py:171`）：predict_engagement :332-420 / detect_dropout_risk :676+ / recommend_optimal_time :559+ / get_next_intent_forecast :795-819。

**公式**：StudyRecord 近 30 天真实查询（:342-351）；间隔 mean/stdev + 星期/小时模式；confidence = max(0.5, 1−std/avg) clamp 0.95（:394-396）；<2 条记录 → confidence=0.3 默认 + 明示「数据不足」intervention（:357-363）。

**评级与风险**：estimated。**R2 问号「confidence/fallback_used 是否如实透出」的答案：部分成立**——confidence 如实透出（engagement :232；optimal_time :247 还带 data_status/sample_size :245-246），但 `fallback_used`/`prediction_tier` 只存在于 next_intent_forecast 子负载（:1630-1631）；/predictive/dashboard 包装层（:227-252）对 engagement/dropout/optimal_time **无降级标记**，LLM 失败静默回落 rule_based（:805-819）。风险：DB 实测 30d StudyRecord 仅 27 行/9 用户（as_of）——样本极薄时的置信度语义需 UI 谨慎呈现。

## 5 · home_growth_status — actual

**链路**：`TodayGrowthStatusCard`（`today_growth_status_card.dart`）+ 顶部的 DailyContextLine（`dashboard_screen.dart:1053` watch、:1136 渲染 text）→ `home_growth_provider.dart:319-329`（GET `/growth/dashboard`）与 :331-345（GET `/growth/daily-context-line`）；source 解析 :260-272（网络失败静默回落 `local_rule` 文案 :250-258，无 isDemoMode 分支）→ gateway `proxy_routes.go:688-695`（401 实测）→ `api/v1/growth.py:18-25` / :29-41 → `GrowthDashboardService.build_snapshot`（`growth_dashboard_service.py:77-119`）/ `get_daily_context_line`（:121-163）。

**rule|ai 双路**：规则行 :139-141；AI 行 :143-146 经 `safe_llm_json_call`（:266）且过 `_is_valid_context_line` 校验（:144）防幻觉；重复检测回落规则（:147-148）；payload **`source` 字段明示**（:152）；Redis 缓存 TTL=min(至午夜, 1800s)（:157-161，P2-F 注释 :67-71）。

**评级与风险**：actual。**R2 问号「source 标注」答案：后端明示、mobile 已解析（:268），但 daily-context-line 的 UI 只渲染 text 不渲染 source 标签**；用户可见的 source 位置只有 briefing 块的 `growth_signal.source`（`dashboard_screen.dart:2587`）——而那是「N 次学习记录 / M 分钟投入」证据字符串（`growth_dashboard_service.py` `_get_growth_signal` :690+ 内 :31/:36），不是 rule/ai 枚举。风险：AI 文案与统计数字的来源区分对用户不可见。

## 6 · community_feed — actual computation BUT cohort_polluted（新增 INV-15）

**链路**：feed provider（`community_providers.dart:37/:54`）→ `community_repository.dart:11-22`（demo → `MockCommunityRepository`，gated）/ :24-46 `getFeed` → `GET /community/feed?page&limit&scope` → gateway `proxy_routes.go:537+`（401 实测）→ `api/v1/community.py:276-408`（router 内联 SQL，无独立 service 层中转）。

**查询语义**：soft-delete 守卫（:293）、可见性（public/friends + 好友子查询 :295-369）、scope 过滤（squad/goal_mates/following :325-361）、block 屏蔽（:371-382）；排序为**纯 created_at 倒序分页（:384）**，无热度/推荐模型；**全链无 registration_source 过滤**。

**DB 实证（as_of 2026-09-19 04:28 UTC）**：未删公开帖 **331 条 = guest 326 + seed 5；email 用户发帖 0 条**。⇒ 真实邮箱用户的全局 feed 在当前库态下 **100% 由游客种子内容构成**。这是 INV-09（排行榜无 cohort 过滤）同款 logic_gap 在社群表面的翻版，但种子密度更极端，按 INV-15 追加（见 data_truth_inventory.csv 副本）。

## 7 · cognitive_patterns — actual BUT seed_inflated

**链路**：`CognitiveToolHubCard`（`cognitive_tool_hub_card.dart:63/:176/:257`）、`PrismCard`（`prism_card.dart:47`）、`CuriosityCard`（`dashboard_curiosity_card.dart:62`）消费 `CognitiveData.weeklyPattern`（`dashboard_provider.dart:541-542` 解析 `GET /dashboard/status` 的 `cognitive` 字段）→ gateway `proxy_routes.go:679-685`（401 实测）→ `api/v1/dashboard.py:96` → `DashboardService._get_cognitive_summary`（`dashboard_service.py:232-282`：最新未归档 BehaviorPattern :237-244；24h 新 pattern → status=new :247-254）。

**产出方（补全）**：`CognitiveService` 对真实 cognitive_fragments 做 LLM 分析（`cognitive_service.py:271`；LLM 失败回落 `cognitive_llm.call fallback=""` :276-278，即失败不产 pattern）；confidence 以 EMA α=0.3 递归更新（:604-607）；另 `guest_seed_service._ensure_behavior_pattern`（:1134-1190，触发 :2212/:2225）为游客预写 pattern。

**DB 实证（as_of）**：behavior_patterns 332 行 = **guest 327（98.5%）/ email 5**（max confidence 0.90/0.82）。评级 actual BUT seed_inflated 维持且污染较主卡时点加重。风险：真实用户路径真实；游客卡内容为种子文案（D05 标注义务）。

## 8 · focus_stats — actual（双路皆真实记录）；主卡机制声明需修正

**链路**：`FocusStatisticsScreen`（`focus_statistics_screen.dart`）→ `focus_statistics_provider.dart`：`loadTodayStats`（:230-260）**先 `GET /focus/stats`，API 失败才回落本地 Isar**（:248-257 debugPrint 'API failed, using local data'）；`loadWeeklyStats`（:266-310）对 `/focus/stats/weekly` 同构；`sync()`（:441-459）把本地未同步会话 `POST /focus/sessions` 上行（`getUnsyncedSessions` `focus_statistics_repository.dart:345-349` → `markAsSynced` :352-363）。gateway `proxy_routes.go:905-910`（401 实测）→ `api/v1/focus.py`（:81 stats / :125 weekly / :134 monthly / :156 heatmap / :48 POST sessions）。

**R2 点名的 mergeServerSessions 复核**：机制存在于 `focus_statistics_repository.dart:380-417`（按 serverId 去重合并 :389-394）——但**全 mobile/lib grep 无任何调用方（休眠代码）**。

**评级与风险**：actual（服务端 focus_sessions SQL 聚合与本地 Isar 真会话记录皆非 mock）。**主卡「本地优先计算+服务端合并同步」与实现相反**：展示层是 API 优先/本地兜底，记录层是本地先行/单向上行，服务端→本地对账从未接线 ⇒ 跨设备/重装场景下用户看到的数字真源是服务端（DB as_of：focus_sessions 2431 行全部 guest——污染面与主卡一致）；本地与服务端数字可能不一致。INV-14「本地为准」口径建议随本卡修正。

## 9 · photon_balance — seed_inflated（显式体验设计，D05 边界内）

**链路（主卡空位补正）**：`PhotonBalanceCard`（`features/photon/presentation/widgets/photon_balance_card.dart`）→ `photon_repository.dart:30-48 getBalance`（endpoints `api_endpoints.dart:623-625`）→ `GET /photons/balance` → gateway `proxy_routes.go:1060-1065`（401 实测）→ `api/v1/photons.py:25-45` → `PhotonService.get_balance`（`photon_service.py:380-400`：`users.photon_balance` 列直读 + Redis 缓存 300s）。交易流水 :48-78；转账 :107-159。

**转账守卫（正面发现）**：`photons.py:126-138` 游客以 **JWT `is_guest` 声明**被 403 拦截，注释明示旧实现仅比对演示常量 `GUEST_USER_ID`、真实游客可绕过——已修复。

**DB 实证（as_of）**：guest 166 人余额 100–1020（avg 994.2）vs email 75 人 0–10（avg 0.7）；`guest_seed:welcome_bonus` 流水 165 行；注册即赋 1000（`guest_seed_service.py:1493`，流水写入 :1509）。评级 seed_inflated 维持；UI「体验积分/不可转账」标注仍缺（D05 跟进项维持）。

---

## 程序化校验与探测记录

- `lineage_extension.csv`：csv 模块写读往返，header+9 数据行**全部 13 列零错位**（主卡 C5 类缺陷在本文件不存在）。
- curl `:8080`（未带 token）：`/healthz` 200；9 项对应端点 `/api/v1/{experience/growth-dashboard, growth/weekly-narrative, experience/understanding-snapshot, predictive/dashboard, growth/daily-context-line, community/feed, dashboard/status, focus/stats/weekly, photons/balance}` 全部 **401** `authorization_token_required`——鉴权隔离与 FINDINGS §六一致。
- DB 全部只读 SELECT；Redis 因口令不可得未做缓存键实测（weekly narrative TTL、daily-context-line TTL 以代码 :1350-1355 / :157-161 为证）。

## 对后续卡的映射建议

1. **T-truth-community-cohort（P0）**：INV-15——feed/社群聚合按 registration_source 排除 guest/seed（验收 SQL 即 §6 的 cohort 分布）。
2. **T-truth-focus-direction（P2）**：mergeServerSessions 接线或删除；INV-14 口径修正；「本地为准」改为「服务端展示真源 + 本地兜底」或真正实现双向对账。
3. **T-truth-predictive-honesty（P2）**：/predictive/dashboard 顶层透出 fallback_used/prediction_tier（复用 :1630-1631 既有字段）。
4. **T-truth-narrative-copy（P3）**：对外文案勿称「AI 成长故事」——现实现为规则模板（is_placeholder/source_counts 已备好诚实呈现的素材）。
5. **D05 跟进（维持）**：photon/游客体验标注；daily-context-line 的 rule|ai source 标签渲染。

收工清理：/tmp 无残留文件（本轮未落 /tmp）；无启动进程/模拟器；唯一持久产出为本目录三文件（worktree 内，未 commit）。
