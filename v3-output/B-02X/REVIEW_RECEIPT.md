# REVIEW_RECEIPT · B-02X 独立 Reviewer 验收

- Reviewer: 独立验收 agent（wt6）
- 复核日期: 2026-09-19
- 被审对象: 本目录三文件（lineage_extension.csv / REPORT.md / data_truth_inventory.csv 追加 INV-15 副本）；对照主仓 @ main `v3-output/B-02/`（lineage.csv / FINDINGS.md / REVIEW_RECEIPT_2.md，只读）
- 复核方式: 不信任 Worker 自报——csv 模块程序化结构校验 + mobile/gateway/backend 代码逐行重走 + `docker exec sparkle_db psql` 只读 SELECT 重跑 + `:8080` 未鉴权 curl 复测；LIGHT 约束遵守（无模拟器/Gradle/flutter/浏览器）；未 commit；主仓零写入

---

## 一、结构与口径校验（PASS）

- `lineage_extension.csv`：csv 模块解析，header 13 列，**9 数据行全部 13 列零错位**（主卡 C5 类缺陷在本文件不存在，自报属实）。
- `data_truth_inventory.csv`：header 9 列 15 数据行零错位；**header 与 INV-01..14 逐字节等于主卡版本**（纯追加，未篡改主卡行）；INV-15 行 schema 一致。
- 9 项清单与 REVIEW_RECEIPT_2.md §五 1-9 逐条对上，无缺漏、无偷换。
- 评级分布复算 = 自报：actual 4（weekly_narrative / growth_dashboard / understanding_snapshot / growth_status）+ actual-机制修正 1（focus_stats）+ seed_inflated 2（cognitive_patterns / photon_balance）+ estimated 1（home_predictive）+ cohort_polluted 1（community_feed）。
- wt6 HEAD `0cbfd777` 与 REPORT 声明一致；工作区仅本目录新增。

## 二、INV-15 独立重跑（PASS — 数值精确命中，非仅量级）

本 Reviewer 于 **04:39 UTC** 重跑（Worker as_of 04:28，漂移 ~11 分钟）：

```sql
SELECT u.registration_source, count(*) total,
       count(*) FILTER (WHERE p.deleted_at IS NULL AND p.visibility='public') AS public_not_deleted
FROM posts p JOIN users u ON u.id=p.user_id GROUP BY 1;
-- guest | 326 | 326 ； seed | 5 | 5 ； （email 无任何行）
-- users: 248 = guest 166 / email 75 / seed 7
```

即全部 331 帖均 public 且未删，真实邮箱用户发帖 **0** 条——与 Worker 报告**逐位一致**。代码侧：`backend/app/api/v1/community.py:276-408` 全文读毕——soft-delete 守卫（:293 `not_deleted_filter`）、public/friends 可见性 + 好友子查询、squad/goal_mates/following scope、block 屏蔽、`order_by(Post.created_at.desc())`（:384）全部属实；**全文件 grep `registration_source` 零命中**（api/v1/ 目录其余命中仅在 auth.py 注册路径）。mobile 侧 demo 门控（community_repository.dart:12-13 MockCommunityRepository / :24-46 getFeed）、端点 `/community/feed`（api_endpoints.dart:330）、gateway community 组 authMiddleware（proxy_routes.go:537-545）均核实。INV-15 定级 logic_gap/pollution 成立，P0 修复建议（按 cohort 过滤）与 INV-09 同构，采纳。

## 三、3/9 行完整链路复走（PASS，1 处 P3 引用瑕疵）

1. **community_feed**（cohort_polluted，必抽）：全链见 §二，DB 侧 SQL 独立重写重跑，truth_class 与 pollution_notes 全部证实。
2. **insights_weekly_narrative**（actual）：card:35 watch → provider:13-18 → repo:28-56（读 `/experience/growth-dashboard` 聚合的 `weekly_narrative` 字段；demo 分支 :29-31/:59-61 placeholder gated）→ :58-76 generate → dashboard_router.py:29-36/:109-115 → `ProgressNarrativeService.get_weekly_narrative`（:216-244）/`build_weekly_narrative`（:246+）。**全文件 imports（:1-23）仅 stdlib/sqlalchemy/models，grep llm/openai/chat_completion 零命中——规则模板零 LLM 证实**；真实 user_id 隔离 SQL（Task :457-508 / StudyRecord :511+ 等）；source_counts :324-334、is_placeholder :344；缓存 `_weekly_cache_key` :1344-1345、`WEEKLY_CACHE_GRACE=timedelta(days=2)`（:111）、TTL=max(week_end+2d−now, 3600)（:1350-1353）——**非固定 7d 证实**。
3. **cognitive_patterns**（seed_inflated）：dashboard_provider.dart:541-542 解析 `cognitive` 字段（逐行命中）；三卡 :63/:176、prism:47、curiosity:62 逐行命中；gateway dashboard 组 :679-685 authMiddleware；`DashboardService._get_cognitive_summary`（:232-282：最新未归档 :237-244、24h→new :247-254）；产出方 CognitiveService LLM 分析 + `cognitive_llm.call fallback=""` + EMA α=0.3（:604-607）；guest_seed `_ensure_behavior_pattern` :1134（触发 :2212/:2225）。**DB 重跑：behavior_patterns 332 = guest 327（98.5%，max 0.90）/ email 5（max 0.82）——与报告逐位一致，评级 actual BUT seed_inflated 成立**。
   - **P3（不阻断）**：CSV/REPORT 的 backend_entry 写 `api/v1/dashboard.py:96`——该文件仅 20 行，`:96` 实为 **services/dashboard_service.py** 的 `_get_cognitive_summary` 调用行；api/v1/dashboard.py 入口是 :11。文件前缀笔误，链路实质无误，建议顺手改为 `dashboard.py:11 + dashboard_service.py:96`。

## 四、四处主卡修正逐条定夺（4/4 成立）

| # | 裁定 | 证据（本 Reviewer 读码） |
|---|---|---|
| ① weekly_narrative 非规则/缓存 7d | **完全成立** | progress_narrative_service.py 全文件零 LLM token；:111 GRACE=2d、:1350-1353 TTL 公式；主卡 lineage row15「LLM 从真实周数据生成叙事 (Redis 缓存 7d)」两点均失实 |
| ② focus 机制方向 | **完全成立** | features/focus focus_statistics_provider.dart:230-260 loadTodayStats **API 优先**，:247 字面 `debugPrint('API failed, using local data')` 后落本地 Isar；:266-310 weekly 同构；sync() :441-459 单向上行；`mergeServerSessions`（repo:380）在 mobile lib/+test/ 全树 grep **仅定义零调用方**——主卡「本地优先+服务端合并」「本地为真源」与实现相反 |
| ③ predictive 顶层降级未透出 | **完全成立** | predictive_analytics.py:207-256 wrapper：engagement/dropout/optimal_time 子负载仅 confidence/data_status/sample_size，**无 fallback_used/prediction_tier**；该两字段仅在 next_intent_forecast 子负载（predictive_service.py:1630-1631）。主卡 row6「fallback_used 字段明示降级 / OK」对 dashboard 面为过誉 |
| ④ insights 入口 | **成立** | mobile insights 两 repo 均打 `/experience/growth-dashboard`（growth_dashboard_repository.dart:25、growth_narrative_repository.dart:22-56）；`/growth/dashboard` 仅 home_growth_provider.dart:323（首页面）消费；`_GrowthExperienceDashboardBuilder.build`（dashboard_router.py:82-107）中 GrowthDashboardService.build_snapshot 仅 :84 子调用。小保留：主卡 row16 的 api_endpoint 本已写对，失实点是 row15 读取路径与「GrowthDashboardService 聚合」粒度归因（R2 §五 item2），B-02X「主卡记到 /growth/dashboard」措辞略宽——但其所断言的代码事实全部为真，主卡 lineage 需要修订的结论不变 |

## 五、401 复测与附加 DB 抽查（PASS）

- 未鉴权 curl `:8080`（本 Reviewer 抽 4 个 ≥ 要求 2 个）：`/api/v1/{community/feed, experience/growth-dashboard, photons/balance, focus/stats/weekly}` 全 401 `authorization_token_required`；`/healthz` 200。
- focus_sessions 2431 行 100% guest（逐位一致）；photon：guest 166（100-1020，avg 994.2）/ email 75（0-10，avg 0.7）、welcome_bonus 流水 165 行、guest_seed_service.py:1493 赋 1000 + 流水写入（source=guest_seed:welcome_bonus）均逐位一致；photons.py:126-138 JWT `is_guest`→403 且注释明示旧常量比对漏洞已修——正面发现属实。

## 六、卫生与安全（PASS）

- 三交付物无密钥/口令/连接串（唯一 "token" 命中为 INV-01 门控描述文案）。
- wt6 仅新增本目录；主仓零写入（主仓预存未跟踪 `.fieldtest-shots/` 与 /tmp 下 `r5_review.json`、`review_nodes_initial.py` 非本轮产物，疑似其他 agent 所留，按红线不动、仅记录）。
- 本轮未起任何进程/模拟器，/tmp 零残留。

## 七、Verdict: **ACCEPT**

- 9 行 lineage 事实链经 3 行全链复走 + 4 项主卡修正逐条读码 + DB 重跑（INV-15 逐位命中），无一推翻；四处主卡修正全部成立，主卡 lineage row4/6/10/15/16 相应处应随本卡修订。
- 唯一 P3（不阻断）：cognitive_patterns 行 `api/v1/dashboard.py:96` 应为 `dashboard_service.py:96`（dashboard.py:11），下轮顺手修正。
