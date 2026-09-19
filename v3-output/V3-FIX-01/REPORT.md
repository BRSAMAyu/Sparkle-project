# REPORT · V3-FIX-01（P0）：全局排行榜排除 guest/seed cohort

- 执行: V3 Fleet Worker（wt7）
- 日期: 2026-09-19
- worktree: `/Users/brsama/code/GitHub/Sparkle-sysrev/wt7`，基线说明：任务简报写的是 1083f4f5，实际 HEAD 为 **51f5acd7**（B-02 review CHANGES remediation，比 1083f4f5 新，含 B-02 复核收编）。开工时 `backend/app/services/leaderboard_service.py` 与主仓逐字节一致（diff 验证 IDENTICAL），本任务改动完全叠加其上，未做任何 reset/历史改写。
- 约束遵守: 主仓与 sparkle_db 全程只读；无模拟器/Gradle/flutter/浏览器；pytest 定向串行；无 git commit/push；测试用 venv 建在 worktree 内（收工已删）。

---

## 1. 红测先行（RED）

新增 `backend/tests/services/test_leaderboard_global_cohort_filter.py`，沿用仓内既有模式（`tests/services/test_leaderboard_global_join.py` 的 `_StatementCaptureDB` + `stmt.compile()`，不触碰任何数据库）。三个用例：

1. `test_global_topn_query_excludes_guest_and_seed_cohorts` — 编译全局榜 top-N 语句，断言 WHERE 含 `registration_source NOT IN` 且绑定值为 guest/seed。
2. `test_existing_soft_filters_are_preserved` — 断言 `is_active` + `deleted_at` 语义保留（过滤是叠加而非替换）。
3. `test_own_score_fallback_is_not_cohort_filtered` — 断言"我的分数"回退查询（语句 2）**不**带 cohort 过滤（游客在体验模式下仍能看到自己的分数，只是不上榜——与 D05/D20 一致）。

RED 运行输出（修复前，`pytest tests/services/test_leaderboard_global_cohort_filter.py -x -q`）：

```
collected 3 items
tests/services/test_leaderboard_global_cohort_filter.py F
E   AssertionError: global top-N query has no registration_source predicate —
    guest/seed seed accounts (B-02 F1: 100% of top-100, top_score 132.5) pollute
    the user-visible ranking
E   assert 'REGISTRATION_SOURCE' in 'SELECT USERS.ID, ... ORDER BY COMPOSITE_SCORE DESC\n LIMIT :PARAM_1'
============================== 1 failed in 0.36s ===============================
```

## 2. 最小修复（GREEN）

`backend/app/services/leaderboard_service.py`，两处、共 9 行净变更：

- 新增类常量 `EXCLUDED_COHORT_REGISTRATION_SOURCES = ("guest", "seed")`（紧邻既有 `WEIGHT_*`，注明 D20/B-02 F1 依据）；
- 仅在 `_get_global_leaderboard` 的 **top-N 排名查询** where 尾部追加
  `User.registration_source.not_in(self.EXCLUDED_COHORT_REGISTRATION_SOURCES)`，
  保留既有 `User.is_active, User.not_deleted_filter()` 原语义与顺序。

未改动（语义差异说明，按任务要求保持不动）：
- **好友榜** `_get_friends_leaderboard`：成员集 = 用户主动缔结的 accepted 好友 ∪ 自己，属显式关系面，加 cohort 过滤反而会向用户隐藏其"好友列表里的真实存在"，保持不动；
- **群组榜** `_get_group_leaderboard` / `_get_my_groups_leaderboard`：成员 = 显式入群的账号，属小队语义，保持不动；
- **user_score 回退查询**：不过滤（游客本人分数可见，红测用例 3 已钉住该语义）；
- 其余榜单（weekly/streak/photon/photon_weekly/subject）未动——它们不在本卡范围，但作为波及面列入 §4。

GREEN 运行输出（修复后，同命令）：

```
collected 3 items
tests/services/test_leaderboard_global_cohort_filter.py ...              [100%]
============================== 3 passed in 0.29s ===============================
```

## 3. 定向回归（全部通过）

| 命令 | 结果 |
|---|---|
| `pytest tests/services/test_leaderboard_global_cohort_filter.py -x -q` | 3 passed |
| `pytest tests/services/test_leaderboard_global_join.py tests/test_leaderboard_percentile_guard.py -q` | 8 passed |
| `pytest tests/api/test_accountability_system_api.py -q -x`（accountability API 是 LeaderboardService 的另一个消费方） | 13 passed |

说明：accountability `_build_leaderboard_summary`（`app/api/v1/accountability.py:674`）只消费 friends/weekly/streak 三个榜，不消费 global，本修复对其零行为变更（测试全绿佐证）。

测试环境备注：仓内无现成 venv（`~/.venvs/creative` 缺 sqlalchemy），在 worktree 内 `uv venv backend/.venv` 安装 `requirements.txt`（其中 `python-lzo` 因本机缺 lzo C 头文件跳装，与被测代码无关）；pytest 需 `SECRET_KEY` 环境变量（内联注入，未创建任何 .env 文件）。

## 4. 波及面排查清单（只排查，未修改）

口径：把 guest/seed 账号混入**用户可见**聚合/列表的查询。DB 事实（只读实测）：guest 166 / email 75 / seed 7；**全部 248 个账号 searchable_by=everyone 且 is_active**。

| # | 位置 | 问题 | 风险 |
|---|---|---|---|
| R1 | `backend/app/services/leaderboard_service.py` `_get_streak_leaderboard`（:687 起） | 连胜榜无 cohort 过滤：seed current_streak 最高 11 / guest 30，email 全员仅 1 → 真实用户被结构性挤出连胜榜头部 | **HIGH** |
| R2 | 同文件 `_get_photon_leaderboard`（:757 起）/ `_get_photon_weekly_leaderboard`（:820 起） | 光子榜无 cohort 过滤：DB 实测 top-20 中 guest 占 166 名中的 20 席（guest 最高 1020 光子 vs email 最高 10） | **HIGH** |
| R3 | `backend/app/services/friend_match_service.py:729-752` `_load_public_candidates` | 好友推荐候选池 `where(is_active, searchable_by=EVERYONE).order_by(last_login_at desc, flame_level desc)`：guest flame=15 vs email flame=1，166+7 个 guest/seed 必然霸占候选池头部并被推荐给真实用户；且缺 `not_deleted_filter()` | **HIGH** |
| R4 | `backend/app/services/community_service.py:2986-3033` `UserSearchService.search_users` | 用户搜索无 cohort 过滤（也无 not_deleted_filter），guest/seed 账号可被真实用户搜到 | **MEDIUM** |
| R5 | 同文件 `_get_weekly_leaderboard`（:614 起） | 本周学习榜无 cohort 过滤；seed/guest 有本周 last_study_at（2026-09-18/19）→ 会入榜 | **MEDIUM** |
| R6 | `backend/app/services/collaborative_filtering_service.py:157-171,332-347` `get_similar_users` | "相似用户"把 UserSimilarity 关联到 User 返回用户名/头像，无 `registration_source`/`is_active` 过滤。当前 `user_similarity` 表**不存在**、`user_item_interactions` 0 行 → 功能休眠，风险暂不落地 | **LOW**（休眠） |
| R7 | 同文件 `get_similar_users`（公开版 :157-163） | 附带发现（非 cohort 问题）：join 条件只绑 `request.user_id` 未绑定 `User.id == user_id_1/2`，为 UserSimilarity × User 笛卡尔积，结果集语义错误（内部版 `_get_similar_users` 写法正确）。建议后续开卡 | **MEDIUM**（独立 bug） |
| R8 | `backend/gateway/internal/db/query.sql:48-61` `GetGroupMessages` | 群消息列表 LEFT JOIN users 展示 sender 昵称/头像，无 is_active/注册来源过滤；群内 guest 发言会展示（属消息流而非聚合，且群成员是显式关系） | **LOW** |
| R9 | `backend/app/core/celery_tasks.py:3614` `compute_understanding_depth_daily` → `understanding_depth_metric_service.compute_daily_all` | 按当日活动用户全量计算（含 guest），产物为**每用户每日一行**的 per-user 表，无跨用户可见聚合面 | **INFO** |
| R10 | north_star / analytics / dashboard / statistics / state_aggregator | 逐一核查：均为 per-user 作用域（`user_id ==` 过滤）或 admin 内部指标，无用户可见跨用户聚合 | **INFO**（无风险） |

（本卡的 global 榜已是 R0，本次修复闭环。）

## 5. DB 复算验证（只读）

与 B-02 REVIEW_RECEIPT 断言 1 完全同口径的 SQL（per-user 标量子查询 + `is_active AND deleted_at IS NULL` + 权重 1.0/0.5/2.0/1.5），**仅追加本次修复的过滤 `u.registration_source NOT IN ('guest','seed')`**：

```
 registration_source | in_top50 | top_score | best_rank
---------------------+----------+-----------+-----------
 email               |       50 |      10.0 |         1
(1 row)
```

对照修复前（B-02 F1 实测）：`guest | 50 | 132.5 | 1`（top-50 100% guest）。

**结论：修复后 top-50 = 100% 真实 email 用户，top_score = 10.0，与 B-02 FINDINGS F1 的预期完全一致。** 全局榜 `total_participants=-1` 哨兵与 my_rank 逻辑不受影响。

## 6. 交付物

- `v3-output/V3-FIX-01/changes.patch`（`git add -N` 后 `git diff` 生成，156 行：服务修复 9 行 + 红测 123 行）
- 代码改动：`backend/app/services/leaderboard_service.py`、`backend/tests/services/test_leaderboard_global_cohort_filter.py`

## 7. 收工清理

- [x] 删 `backend/.venv`（worktree 内 venv）
- [x] 删 `/tmp/reqs_nolzo.txt`
- [x] 无遗留进程/模拟器/构建产物；sparkle_db 全程只读 SELECT
- [x] 留：`v3-output/V3-FIX-01/`（REPORT.md + changes.patch）+ 正式代码改动
