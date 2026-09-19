# REPORT · V3-FIX-07（P1）：榜单/推荐同族污染面批量修复

- 执行: V3 Fleet Worker（wt6，general 路线）
- 日期: 2026-09-19
- worktree: `/Users/brsama/code/GitHub/Sparkle-sysrev/wt6`（基线 origin/main @ **86454bbb**，与任务简报一致，开工时 working tree clean）
- 上游依据: 主仓 `v3/06_agent_fleet/DYNAMIC_ISSUES.md` FIX-07 行 + `v3-output/V3-FIX-01/REPORT.md` §4（R1–R10）
- 约束遵守: 主仓与 sparkle_db 全程只读（所有 SQL 均在 `BEGIN TRANSACTION READ ONLY` 内执行）；无模拟器/Gradle/flutter/浏览器（LIGHT 任务）；无真实 LLM 调用；无 git commit/push/stash/reset/clean；测试用 venv 建在 worktree 内（收工已删）

---

## 0. 处置总表（逐项）

| # | 位置（FIX-01 §4） | 基线复算（2026-09-19 复跑） | 处置 | 修法 |
|---|---|---|---|---|
| R1 | `leaderboard_service.py` `_get_streak_leaderboard` | **成立（HIGH）**：连胜榜 top-20 = 16 guest + 3 seed + 1 email（email 最高 current_streak 已从 1 涨到 9，仍被结构性压头） | **已修** | 排名查询追加 `registration_source.not_in(("guest","seed"))`，口径与 FIX-01 逐字一致；本人连胜回退查询保持不过滤 |
| R2 | 同文件 `_get_photon_leaderboard` / `_get_photon_weekly_leaderboard` | **成立（HIGH）**：光子总榜 top-20 = 20/20 guest（guest 最高 1020 vs email 最高 50）；本周光子收入榜 top-20 亦 20/20 guest | **已修**（两处） | 同上口径；本人余额/本人周收入回退查询保持不过滤 |
| R3 | `friend_match_service.py` `_load_public_candidates` | **成立（HIGH）**：候选池头部 60 席（MAX_CANDIDATES=60）= 58 guest + 2 seed、0 email；guest flame 15 / seed flame 20 vs email flame 1，按 last_login_at/flame 排序真实用户完全进不了池 | **已修** | 追加 cohort 过滤 + **补齐缺失的 `not_deleted_filter()`**；cohort 词表 import 自共享常量 `app.core.telemetry_boundary.EXCLUDED_COHORT_REGISTRATION_SOURCES`（D-02 同款，与 leaderboard_service 常量逐字等值） |
| R4 | `community_service.py` `UserSearchService.search_users` | **成立（MEDIUM）**：170 guest + 7 seed 全部 searchable_by=everyone 且 active，任何命中用户名片段的搜索都会带回 demo 账号 | **已修** | 搜索查询追加 cohort 过滤 + 补齐 `not_deleted_filter()`；唯一调用方是用户侧搜索 API（`api/v1/community.py:1468`），无 admin 消费方，无行为回归 |
| R5 | `leaderboard_service.py` `_get_weekly_leaderboard` | **成立（MEDIUM）**：本周有 last_study_at 的账号 = 26 email + 167 guest + 5 seed，guest/seed 会入榜 | **已修** | 本周学习榜查询追加 cohort 过滤 |
| R7 | `collaborative_filtering_service.py` `get_similar_users`（公开版） | **成立（MEDIUM，独立 bug）**：join 只绑 `user_id_1/2 == request.user_id`，未把 `User.id` 绑到另一侧 → UserSimilarity × User 笛卡尔积（内部版 `_get_similar_users` 写法正确）。**数据面休眠**（`user_similarities` 0 行、`user_item_interactions` 0 行、无 collaborative 缓存），live 无法复算，以编译期单测钉住 | **已修** | ON 条件改为与内部版完全一致的双侧绑定（`or_(and_(user_id_1==me, User.id==user_id_2), and_(user_id_2==me, User.id==user_id_1))`） |
| R6 | 同文件 `get_similar_users` 无 cohort/is_active 过滤 | **休眠确认（LOW，记录不修）**：`user_similarities` 表存在但 0 行。⚠️ 修正 FIX-01 的一处笔误：该表实际名为 `user_similarities`（复数），FIX-01 写"表不存在"是查了单数名 `user_similarity`；休眠结论本身成立 | **记录** | 一旦定时任务开始产出相似度行，R6 会立刻升级为实际污染面（推荐卡直接展示 guest/seed 的用户名头像），建议开后续卡 |
| R8 | `gateway/internal/db/query.sql` GetGroupMessages | 未复核 SQL 细节（LOW，群成员属显式关系面，FIX-01 已论证非聚合污染） | **记录不修** | — |
| R9/R10 | celery 统计 / north_star / analytics 等 | 未逐项复跑（INFO，per-user 作用域，FIX-01 已核查无用户可见聚合面） | **记录不修** | — |

**台账命名勘误**：FIX-07 台账行写的 "streak join 笛卡尔积独立 bug"，经核对应为 FIX-01 §4 R7 —— 唯一被标注"独立 bug"的笛卡尔积位于 `collaborative_filtering_service.get_similar_users`（协同过滤，与 streak 无关）。连胜榜自身的 join 已核验为 1:1（`UserStreakStats.user_id` 是主键，见 `app/models/achievement.py:216`），不存在笛卡尔积；历史上全局榜的三表 outerjoin 笛卡尔积已由 gamification-eval P1-3 修复并有回归测试（`test_leaderboard_global_join.py`）。

## 1. 基线复算（只读，数据漂移后以复跑为准）

账号普查（口径 `is_active AND deleted_at IS NULL`）：**guest 170 / email 106 / seed 7**（FIX-01 时为 166/75/7，真实用户增长 41%）。

| 榜单/面 | FIX-01 §4 断言 | 本次复跑 | 结论 |
|---|---|---|---|
| 连胜榜 top-20 | "seed current_streak 最高 11 / guest 30，email 全员仅 1" | top-20 = guest 16 + seed 3 + email 1；email 最高 current_streak 已到 9，但头部仍 19/20 非真实用户 | 成立 |
| 光子总榜 top-20 | "guest 占 20 席，1020 vs 10" | top-20 = 20/20 guest；guest max 1020 vs email max 50（email 涨了 40，仍被压死） | 成立 |
| 本周光子收入 top-20 | （含在 R2 内） | top-20 = 20/20 guest；guest 本周收入合计 169,060 vs email 110 | 成立 |
| 好友推荐候选池 | "173 个 guest/seed 按 flame15 压头" | 池内 guest/seed 合计 177（170+7，涨 4）；头部 60 席 = 58 guest + 2 seed + **0 email** | 成立（更严重） |
| 用户搜索 | "guest/seed 可被搜到" | 177 个 guest/seed 全部 everyone+active，可被任何片段命中 | 成立 |
| 本周学习榜 | "seed/guest 有本周 last_study_at" | 本周 guest 167 / seed 5 / email 26 | 成立 |
| 协同过滤 | "user_similarity 表不存在、interactions 0 行" | 表名为 `user_similarities`（复数），**存在但 0 行**；interactions 0 行；无 collaborative 缓存 | 休眠结论成立，表名笔误已修正 |

（复算 SQL 全文见附录 A，均在 `BEGIN TRANSACTION READ ONLY` 内执行。）

## 2. 红测先行（RED）

新增 4 个测试文件（16 用例），沿用仓内既有 statement-capture 模式（`_StatementCaptureDB` + `stmt.compile()`，不触碰任何数据库）：

| 文件 | 用例数 | 覆盖 |
|---|---|---|
| `tests/services/test_leaderboard_family_cohort_filter.py` | 8 | R1/R2/R5：四榜排名查询必须带 `NOT IN (guest, seed)` 且绑定值正确、is_active+deleted_at 语义叠加保留；本人分数回退查询（连胜/余额/周收入）必须**不过滤**（钉住 FIX-01"游客可见自己分数、只是不上榜"语义）；词表常量与 FIX-01 逐字一致 |
| `tests/services/test_friend_match_public_candidates_cohort_filter.py` | 3 | R3：候选池 NOT IN guest/seed、searchable_by/is_active 保留、补齐 deleted_at；共享常量与 leaderboard 常量逐字等值 |
| `tests/services/test_user_search_cohort_filter.py` | 3 | R4：搜索语句 NOT IN guest/seed、is_active/deleted_at/匹配列保留 |
| `tests/services/test_collaborative_similar_users_join_binding.py` | 2 | R7：公开版 join 双侧绑定 `users.id = user_similarities.user_id_1/2`；与内部版 `_get_similar_users` 的绑定逐字对齐 |

RED 运行（修复前）：**9 failed, 7 passed** —— 9 个失败全部是预期中的断言（各面缺 cohort 谓词 / join 未绑定）；7 个 pre-fix 即绿的是语义钉子（回退查询不过滤、既有过滤器保留、常量词表），用于防止修复过度。

## 3. 修复内容（GREEN）

- `backend/app/services/leaderboard_service.py`：`_get_weekly_leaderboard` / `_get_streak_leaderboard` / `_get_photon_leaderboard` / `_get_photon_weekly_leaderboard` 四处排名查询，在 `User.is_active, User.not_deleted_filter()` 之后追加 `User.registration_source.not_in(self.EXCLUDED_COHORT_REGISTRATION_SOURCES)`（复用 FIX-01 引入的类常量，零新词表）。
- `backend/app/services/friend_match_service.py`：`_load_public_candidates` 追加 `User.registration_source.not_in(EXCLUDED_COHORT_REGISTRATION_SOURCES)`（import 自 `app.core.telemetry_boundary`，纯策略模块无循环依赖）+ 补齐 `User.not_deleted_filter()`。
- `backend/app/services/community_service.py`：`UserSearchService.search_users` 搜索语句追加同款 cohort 过滤 + `not_deleted_filter()`。
- `backend/app/services/collaborative_filtering_service.py`：公开版 `get_similar_users` 的 join ON 条件改为与内部版 `_get_similar_users` 一致的双侧绑定，消除笛卡尔积。

GREEN 运行（修复后）：新增 16 用例全绿；连同 FIX-01 红测/global join/percentile 守卫合计 **27 passed**。

**语义边界说明（非回归，明示给 reviewer）**：连胜/光子/周光子三榜的"本人分数"走独立回退查询，保持不过滤（红测钉住）。本周学习榜的 my_score/my_rank 此前就派生自榜单行集本身（无独立回退查询），过滤后 guest 在该榜 my_score 显示为 None —— 与"游客不上榜"口径一致；如产品要求游客在周榜也看到自己的分数，属新增需求（需加一条不过滤的回退查询），本卡未扩scope。

## 4. 定向回归（全部通过；两处失败为 HEAD 既有，与本次无关）

| 命令 | 结果 |
|---|---|
| 新增 4 文件 + `test_leaderboard_global_cohort_filter.py`(FIX-01) + `test_leaderboard_global_join.py` + `test_leaderboard_percentile_guard.py` | **27 passed** |
| `tests/api/test_accountability_system_api.py` + `test_friend_match_api.py` + `test_recommendation_feedback_api.py` + `test_community_accountability_new_guest_500.py` + `test_community_group_file_sharing_api.py` + `test_community_security.py` + `test_community_e2e.py` + `test_fv22_resource_quality.py` | **67 passed** |
| `tests/unit/test_com011_similar_goal_pursuers.py` | 3 failed / 7 passed —— **HEAD 既有失败**（/tmp 基线克隆复现同样 3 失败；test 内 `_ScalarVal` mock 与 `find_users_with_similar_goals` 的 execute 次数漂移，本次未触碰该函数） |
| `tests/api/test_community_accountability_route_shadowing.py` | 1 failed / 1 passed —— **HEAD 既有失败**（/tmp 基线克隆同样复现） |

## 5. 修后 DB 复算对照（只读；修法是 SQL 谓词，故在各榜口径上"仅追加本次过滤"复算，与 FIX-01 §5 同法）

| 面 | 修复前（复跑） | 修复后（追加过滤） |
|---|---|---|
| 连胜榜 top-20 | guest 16 + seed 3 + email 1 | **email 2 席（top_streak 9），guest/seed 0** |
| 光子总榜 top-20 | guest 20（max 1020） | **email 7 席（top_balance 50），guest/seed 0** |
| 本周光子收入 top-20 | guest 20 | **email 7 席，guest/seed 0** |
| 本周学习榜入榜 | email 26 + guest 167 + seed 5 | **email 26，guest/seed 0** |
| 好友推荐池头部 60 席 | guest 58 + seed 2 + email 0 | **email 60/60，guest/seed 0** |
| 用户搜索可见全集 | 283（含 guest 170 / seed 7） | **email 106，guest/seed 0** |
| 协同过滤（R7） | 数据面 0 行，无法 live 复算 | 编译期单测钉住 join 绑定（`test_collaborative_similar_users_join_binding.py` 2 用例） |

## 6. 留 OPEN / 产品裁决项（本卡只修可确定项）

1. **R6（协同过滤 cohort 过滤，LOW/休眠）**：未修。修正了 FIX-01 的表名笔误（`user_similarities` 存在但 0 行）。一旦 `user_item_interactions` 开始积累数据、每日相似度任务产出结果，公开版"相似用户"会把 guest/seed 展示给真实用户——届时属 MEDIUM。建议开后续卡，修法同款一行 `not_in`。
2. **好友推荐是否保留少量种子内容做"社区感"（产品决策）**：本卡按 FIX-01 口径将 guest/seed 全部移出候选池。若产品希望新用户冷启动时不至于"无推荐可看"，可选项：
   - A. 维持本卡现状（全排除），冷启动依赖 accepted 好友/同群成员等显式关系面（`_load_existing_friends` 不受影响）；
   - B. 保留少量 seed 账号仅用于展示（不提供互动入口），需产品明确配额与标记（如"官方账号"徽标）；
   - C. 新建专职"官方示例账号"cohort（第三种 registration_source），与 guest/seed 词表区分。
   本卡未替产品做选择，R3 修复按 D20"cohort 不得混入用户可见面"的既定决策执行。
3. **本周学习榜游客 my_score=None**（见 §3 语义边界说明）：如需保持游客自见分数，属小改动新需求。

---

## 附录 A · 复算 SQL（口径：`is_active AND deleted_at IS NULL`，与 FIX-01 §5 一致）

```sql
-- 周起始：榜单代码用 Python 本地周一 00:00，复算用 date_trunc('week', now()) 等价近似。

-- R1 连胜榜 top-20 席位构成（修复前：去掉 NOT IN 一行；修复后：如下）
WITH top20 AS (
  SELECT u.registration_source AS src, s.current_streak AS streak FROM users u
  JOIN user_streak_stats s ON s.user_id = u.id
  WHERE u.is_active AND u.deleted_at IS NULL AND s.current_streak > 0
    AND u.registration_source NOT IN ('guest','seed')
  ORDER BY s.current_streak DESC LIMIT 20)
SELECT src, count(*) AS seats, max(streak) AS top_streak FROM top20 GROUP BY src;

-- R2a 光子总榜 top-20
WITH top20 AS (
  SELECT registration_source AS src, photon_balance FROM users
  WHERE is_active AND deleted_at IS NULL AND photon_balance IS NOT NULL AND photon_balance > 0
    AND registration_source NOT IN ('guest','seed')
  ORDER BY photon_balance DESC LIMIT 20)
SELECT src, count(*) AS seats, max(photon_balance) AS top_balance FROM top20 GROUP BY src;

-- R2b 本周光子收入 top-20
WITH weekly AS (
  SELECT u.id, u.registration_source AS src,
         sum(CASE WHEN p.amount > 0 THEN p.amount ELSE 0 END) AS income
  FROM users u JOIN photon_transaction_history p ON p.user_id = u.id
  WHERE u.is_active AND u.deleted_at IS NULL
    AND p.created_at >= date_trunc('week', now())
    AND u.registration_source NOT IN ('guest','seed')
  GROUP BY u.id, u.registration_source),
top20 AS (SELECT src, income FROM weekly ORDER BY income DESC LIMIT 20)
SELECT src, count(*) AS seats, max(income) AS top_income FROM top20 GROUP BY src;

-- R5 本周学习榜入榜账号
SELECT u.registration_source, count(DISTINCT u.id) AS n
FROM users u JOIN user_node_status s ON s.user_id = u.id
WHERE u.is_active AND u.deleted_at IS NULL AND s.last_study_at >= date_trunc('week', now())
  AND u.registration_source NOT IN ('guest','seed')
GROUP BY u.registration_source;

-- R3 好友推荐池头部 60 席（MAX_CANDIDATES=60，排序与代码一致）
WITH top60 AS (
  SELECT registration_source AS src FROM users
  WHERE is_active AND deleted_at IS NULL AND searchable_by = 'everyone'
    AND registration_source NOT IN ('guest','seed')
  ORDER BY last_login_at DESC NULLS LAST, flame_level DESC LIMIT 60)
SELECT src, count(*) AS seats FROM top60 GROUP BY src;

-- R4 搜索可见全集（cohort 过滤后）
SELECT registration_source, count(*) AS visible_accounts FROM users
WHERE is_active AND deleted_at IS NULL AND searchable_by = 'everyone'
  AND registration_source NOT IN ('guest','seed')
GROUP BY registration_source;

-- R6/R7 休眠核查
SELECT count(*) FROM user_similarities;         -- 0
SELECT count(*) FROM user_item_interactions;    -- 0
```

## 7. 交付物与收工清理

- 交付物：`v3-output/V3-FIX-07/REPORT.md`（本文）+ `v3-output/V3-FIX-07/changes.patch`（4 个 service 修复 + 4 个测试文件；untracked 测试以 `git add -N` 纳入 diff）
- 代码改动：`backend/app/services/{leaderboard_service,friend_match_service,community_service,collaborative_filtering_service}.py` + `backend/tests/services/test_{leaderboard_family_cohort_filter,friend_match_public_candidates_cohort_filter,user_search_cohort_filter,collaborative_similar_users_join_binding}.py`
- 清理清单：
  - [x] 删 worktree 内 `backend/.venv`（测试 venv）
  - [x] 删 `/tmp/fix07_reqs.txt`、`/tmp/fix07_baseline1.sql`、`/tmp/fix07_postfix.sql`、`/tmp/fix07_r67.sql`、`/tmp/fix07-baseline/`、`/tmp/fix07-baseline-pytest/`
  - [x] 无遗留进程/模拟器/构建产物；sparkle_db 全程 `BEGIN TRANSACTION READ ONLY` 只读 SELECT
  - [x] 无 git commit/push；收工 `git status` 与开工基线比对：4 个 service 文件 M + 4 个测试文件 ?? + v3-output/V3-FIX-07/ ??，无其他漂移

**STATUS: READY_FOR_REVIEW**
