# REVIEW_RECEIPT · B-02「数据真实性、Mock 污染与指标 Lineage 基线」独立验收复核

- Reviewer: 独立复核 agent（wt4），不信任 Worker 自报，全部结论自行重算
- 复核日期: 2026-09-19
- 被审对象: 主仓 main @ a2d8a10c（B-02 产出由 commit 96004ea5 收编：`v3-output/B-02/` 共 5 文件）
- 复核方式: 主仓只读 + `docker exec sparkle_db psql` 只读 SELECT + mobile/backend/gateway 代码实证；未运行任何写路径/模拟器/构建（LIGHT 约束遵守）
- 方法声明: 排行榜复算 SQL 采用与 Worker 不同的构造（per-user 标量子查询 vs Worker 的 join+FILTER 笛卡尔去重），非沿用口径；表结构经 `\dt`/`\d users`/`\d understanding_depth_daily` 独立探明

---

## 断言 1 · 排行榜 top-50 = 100% 种子账号（无真实用户上榜）

**Verdict: ACCEPT**（并加强：top-100 同样 100% guest）

独立证据（本 Reviewer 自建 SQL，live DB 2026-09-19）：

```sql
-- 权重与语义先从代码取得: leaderboard_service.py:57-60 (1.0/0.5/2.0/1.5),
-- :241-245 UserNodeStatus 按 mastery_score>=50 join, :250-252 过滤 is_active + not_deleted_filter(=deleted_at IS NULL, models/base.py:79)
WITH per_user AS (
  SELECT u.id, u.username, u.registration_source,
    (SELECT count(*) FROM user_node_status uns WHERE uns.user_id=u.id AND uns.mastery_score >= 50) AS nodes,
    COALESCE(s.total_checkin_days,0) AS study_days,
    (SELECT count(*) FROM user_achievements ua WHERE ua.user_id=u.id) AS ach,
    COALESCE(s.longest_streak,0) AS streak
  FROM users u LEFT JOIN user_streak_stats s ON s.user_id=u.id
  WHERE u.is_active AND u.deleted_at IS NULL
), ranked AS (
  SELECT *, (nodes*1.0 + study_days*0.5 + ach*2.0 + streak*1.5) AS score,
         row_number() OVER (ORDER BY (nodes*1.0 + study_days*0.5 + ach*2.0 + streak*1.5) DESC, id) AS rn
  FROM per_user
)
SELECT registration_source, count(*) AS in_top50, round(max(score)::numeric,1) AS top_score, min(rn) AS best_rank
FROM ranked WHERE rn <= 50 GROUP BY registration_source;
```

实测输出：`guest | 50 | 132.5 | 1`（仅此一行 —— **top-50 100% guest，top_score 132.5，与 Worker 数字一致**）。

加强证据：
- top-100 同口径复算：`guest | 100 | best_rank 1`，无 email/seed 入榜。
- 全量排名分布：guest 166 人 best_rank 1 / seed 7 人 best_rank 164 / **email 75 人 best_rank 169（即全部真实用户结构性被挤出前 168 名之外）**；email 全 cohort 最高分 10.0 vs guest 最高 132.5。
- 代码确认无 cohort 过滤：`backend/app/services/leaderboard_service.py` 全文无 `registration_source`；过滤仅 `User.is_active` + `User.not_deleted_filter()`（:250-252）。默认 limit=50（`backend/app/schemas/leaderboard.py:101`）。

口径备注（不改结论）：Worker 的 F1 SQL 只写了 `u.is_active`，漏了服务实际生效的 `deleted_at IS NULL`（not_deleted_filter）。当前数据下两口径结果相同（本 Reviewer 两种都跑了），但作为"验收 SQL"应补上该条件。

## 断言 2 · 游客（guest/tourist）全量 is_pro=true

**Verdict: ACCEPT**

- DB（本 Reviewer 独立查询）：`users` 无 `is_pro` 列（`\d users` 探明）；is_pro 是网关派生值。
  `SELECT registration_source, count(*), min(flame_level), max(flame_level), count(*) FILTER (WHERE flame_level>=3) FROM users GROUP BY 1;`
  → `guest: 166 行, min=max=15, flame>=3 的 166/166`；`email: 75 行, min=max=1, 0/76`；`seed: 7 行, flame 9~20, 7/7`。
  即 **166/166 游客 flame_level=15 → 全量 is_pro=true**（7 个 seed 账号同样全部 is_pro=true；真实 email 用户反而全员 is_pro=false）。
- 代码链路逐环确认：
  - 种子写入: `backend/app/services/guest_seed_service.py:1486` `user.flame_level = 15`
  - 派生①: `backend/gateway/internal/service/user_context.go:129` `IsPro: user.FlameLevel >= 3`
  - 派生②: `backend/gateway/internal/handler/chat_orchestrator_chatflow.go:283-284` `if !profile.IsPro { profile.IsPro = fallbackUser.FlameLevel >= 3 }`
  - 契约: `proto/agent_service.proto:140` `bool is_pro = 4`
  - 引擎消费: `backend/app/core/llm_router.py:53-58` —— gRPC 入口按 `user_profile.is_pro` 设置 `set_request_user_tier`，对 free 层做 tier 钳制。游客被当作 pro 放行。
- 结论：商业/路由 entitlement 被游戏化字段劫持 + 被种子数据 100% 灌满，断言成立（F2/D17 定性正确）。

## 断言 3 · mock 写入 Isar / production cache 的路径存在且可复现

**Verdict: ACCEPT（路径断言成立，代码级独立复核）；但该断言的"红测已钉"证据缺失，见 CHANGES-C1**

代码路径逐行确认（全部本 Reviewer 自行读码）：
- 三个仓库继承 HybridStatisticsRepository：`focus_statistics_provider.dart:112` / `capsule_statistics_provider.dart:91` / `agent_statistics_provider.dart:91`。
- `fetchFromApi` 返回纯 mock：focus `:119-140`（`_generateMockTotal/Sessions/DailyData`，且 `isFromCache: false` :131）；capsule `:98-167`（`opened*1.5` :165、`*0.3` :167）；agent `:98-165`（`calls*500` :165）。
- 冷路径写缓存：`hybrid_statistics_repository.dart:147-161` `getStatistics()` cold → `_putInWarmCache(cacheKey, entity)`（:159）。
- **Isar 真实写事务**：`:330-354` `_putInWarmCache` → `database.isar.writeTxn(...cachedStatistics.put(model))`（:348-350）；TTL=`warmTtlSeconds=86400`（24h，:27）；`:346` `isFullySynced = !entity.isFromCache` —— 因 fetchFromApi 固定 `isFromCache:false`，**假数据落 Isar 且被标记"与服务器完全同步"**。
- 休眠确认：`grep -rln "FocusStatsRepository|CapsuleStatsRepository|AgentStatsRepository" mobile/lib` 在 `core/statistics` 之外无命中 → 无 UI 消费者，与 Worker"休眠未接线"判定一致。
- 按 LIGHT 约束未执行写路径/未跑 flutter test；本断言的机制由上述代码链路实证，不依赖 Worker 的红测。
- 次要口径观察：Worker 称"25 个 mock 标记（8/10/7）"；本 Reviewer 按 `_generateMock*` token 计数为 19（6/8/5），差异应是探针计数口径不同，不影响 RED 结论（任一 mock 返回即违反守卫）。

**证据缺陷**：FINDINGS.md、COMPLETION_RECEIPT.md、lineage.csv（focus_stats_core_scaffold 行）、data_truth_inventory.csv（INV-02）四处引用 `mobile/test/core/statistics/mock_statistics_guard_test.dart`（"当前 RED"）作为钉子。经查：该文件**不在 main**（`git ls-tree -r main` 无；96004ea5 仅含 5 个 v3-output 文件；f01f4ae8..main 无任何 mobile/test 改动；`git log --all -- "*mock_statistics_guard*"` 无结果；sysrev 各 worktree 亦无）。收编时红测丢失，验收方按 RECEIPT"建议 reviewer checks #3"执行会直接撞缺失文件 → CHANGES-C1。

## 断言 4 · seed/demo namespace 与真实 cohort 可用 SQL 区分

**Verdict: ACCEPT**（四类标记全部独立实测可查）

| 标记 | 本 Reviewer 实测 SQL 结果（live DB） |
|---|---|
| `users.registration_source` | guest 166 / email 75 / seed 7 |
| `knowledge_nodes.is_seed` | true 72 / false 85 |
| `knowledge_nodes.sector_classification_model='guest_seed'` | 54 行（另 expansion_fallback 10 / classifier 44 / glm_4_5_air_batch 6 / minimax_m3_batch 23 / sprint_pack 18 / 空 2） |
| `photon_transaction_history.source='guest_seed:welcome_bonus'` | 165 行 |

结论："可查询区分"成立；与 FINDINGS §四的判断一致（可区分但排行榜/社群/聚合未实际区分——由断言 1 的实证支撑）。

---

## 一致性抽查（lineage.csv / entity_map.csv 抽 5+ 项，全部自算）

| # | 抽查项 | 结果 |
|---|---|---|
| 1 | lineage·leaderboard 公式 | ✅ 权重 1.0/0.5/2.0/1.5 与 `leaderboard_service.py:57-60` 一致；mastery>=50 join（:244）；DB 复算 top_score 132.5 与 lineage 记载一致 |
| 2 | lineage·understanding_depth 公式与 DB | ✅ 权重 0.40/0.25/0.20/0.15 = `understanding_depth_metric_service.py:43-46`；DB 实测 **149 行 / 149 用户 / 2026-09-18 / 0.275–0.933 / avg 0.384，逐位吻合**（该表为每日批聚合，未漂移） |
| 3 | lineage·streak 种子注入 | ✅ `guest_seed_service.py:1560-1561` `longest_streak=30/total_checkin_days=45`；DB 实测 guest max longest=30、max checkin=45，**逐位吻合** |
| 4 | lineage·galaxy_mastery 污染 | ✅ 结构成立：live 实测 guest 占 user_node_status **98.7%**（8364/8478）；lineage 记 98.9%（8135 中 8050）为快照值，漂移方向一致 |
| 5 | lineage·home_flame | ✅ `guest_seed_service.py:1486` flame=15；`focus_service.py:98` 附近为 flame 升级逻辑，指针正确 |
| 6 | lineage 代码指针抽检 | ✅ `proxy_routes.go:461` 确为 `insights.GET("/understanding-depth", h.proxyWithHeaders)`；`llm_service.py:291/339-340/386-387` 确为 demo_mode 三处激活点；leaderboard_repository.dart 确有 demo mock 分支（:224/:282） |
| 7 | entity_map.csv DB 计数（注意：该文件实际属 B-06，不在 B-02 目录） | 结构性吻合 + live 漂移：tasks 1089→1219、plans 357→399、mem_prefs 59→89、mem_goals 7→12、episodic 209→235、event_outbox 102→106、direct_capture 166→183、inferred_extraction 43→52；**goals=4、cards=0、task_occurrences=0、intervention_records=1 四项逐位吻合** |
| 8 | INV-11 遗留疑问"149 用户含 guest?" | ✅ 已代答：**understanding_depth_daily 中 guest 138 / email 7 / seed 1 —— 92.6% 是游客**，污染坐实且比 Worker 预期更严重 |

## 数据快照漂移说明（不影响任何断言）

B-02 的"DB 事实"是 2026-09-19 时点快照；本复核时 live DB 已漂移：users 219→248（guest 160→166、email 52→75）、user_node_status 8135→8478、user_achievements guest 944→980 / email 3→23、seed streak checkin 25→52。所有结构性结论（100% guest 榜单、flame=15 全量、98.7% guest mastery、guest 成就约 40:1 压倒 email）在漂移后依然成立且方向一致。交付物提供了可复跑 SQL，但未标注"快照会漂移，复核请以重跑为准"。

---

## 总 Verdict: **CHANGES**

四条断言全部经独立重算成立（1/2/4 数字级复现，3 代码级实证），无一条被推翻；但交付物自身存在以下**必须修复**项（均为文档/证据完整性，不动业务代码）：

- **C1（必须）红测文件未随 B-02 收编进 main**：`mobile/test/core/statistics/mock_statistics_guard_test.dart` 在 main 不存在（96004ea5 仅收了 v3-output/B-02/ 5 个文件），而 FINDINGS.md §三、COMPLETION_RECEIPT"Files/components"与"建议 reviewer checks #3"、lineage.csv 第 11 行、data_truth_inventory INV-02 四处都以其为"已钉 RED"证据。二选一：把红测文件补交入库（允许 RED + 预期失败标注），或在上述四处改为"红测因 CI 阻断未随本卡入库，仅存工作树/探针记录"的如实表述。
- **C2（必须）data_truth_inventory.csv/JSON 的 INV-08、INV-09 两行字段错位**：location 字段内未加引号的逗号（`llm_service.py:291,339-340,386-387,542-549`）导致 CSV 列整体左移；JSON 转换继承了损坏（INV-08 出现 `truth_class:"339-340"`、`enterprises_production_path:"386-387"`、`gating_or_namespace:"542-549"`、`evidence:"demo"` 的乱序赋值；INV-09 的 remediation 提示被截断进伪 `null` 数组）。行内引用的行号本身经核实全部正确（291/339-340/386-387 均为真），修复 = 给该字段加 CSV 引号并重新生成 JSON。
- **C3（应当）快照值标注**：data_truth_inventory/FINDINGS 中的 DB 计数应加"live DB 时点快照、已观察漂移、复核以重跑 SQL 为准"的说明（本文档已附漂移对照，可直接引用）。
- **C4（应当）F1 验收 SQL 补 `deleted_at IS NULL`**：与 `_get_global_leaderboard` 实际过滤语义（`not_deleted_filter()`，models/base.py:79）对齐；当前数据下结果不变。

范围备注：任务书把 `entity_map.csv`（24 概念 + 8 组重复真源 D-PREF/D-CTX/D-INT/D-STATE/D-TASK/D-CONF/D-OUTBOX/D-ENTITLE）记在 B-02 名下；经查它是 **B-06 的产出**（`v3-output/B-06/`），B-02 目录实际只有 5 个文件。另 ENTITY_MAP.md 摘要行（:13）称"四组重复真源"而 §2 表列 8 组，属 B-06 文档内不一致，建议 B-06 侧修正，不计入本次 B-02 verdict。

收工清理：本次复核未产生 /tmp 文件、未起模拟器、未跑构建；唯一产出即本 RECEIPT（wt4 内）。无其他需回收项。
