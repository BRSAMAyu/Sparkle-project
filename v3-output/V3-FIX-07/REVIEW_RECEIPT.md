# REVIEW_RECEIPT · V3-FIX-07「榜单/推荐同族污染面批量修复」

- 验收人: V3 Fleet R1（全新重验，不信任 Worker 自报；前任评审员宿主重启阵亡无回执）
- 日期: 2026-09-19
- 对象: `/Users/brsama/code/GitHub/Sparkle-sysrev/wt6/`（工作树基线 **86454bbb**；主仓 main @ **e7ef4d32** 为只读参照）
- 方法: 独立 diff 比对、口径逐字比对、变异实验、/tmp 基线克隆复跑（红测 + HEAD 既有失败）、live DB 只读复算（`BEGIN TRANSACTION READ ONLY`，收尾 ROLLBACK）、`git apply --3way --check` 合入预演

---

## 0. 交付面核对

| 项 | 声称 | 实测 | Verdict |
|---|---|---|---|
| 改动面 | 4 M service + 4 A 测试，+532/−6 | `git status --short` 恰为 8 文件 + `v3-output/V3-FIX-07/`；`git diff HEAD --stat` = +532/−6，逐文件吻合 | ✅ 无夹带 |
| patch↔树一致 | changes.patch = 树内 diff | 剔除 `index` 行后 `diff` 全等 | ✅ |
| 工作树基线 | REPORT 称 origin/main @ 86454bbb | wt6 HEAD=86454bbb，为 main@e7ef4d32 的祖先（wt6 落后主仓 2+ 提交，合入预演按 e7ef4d32 验） | ✅（注：任务卡面写「HEAD e7ef4d32」系指主仓参照，非 wt6 HEAD） |

## 1. 逐断言 Verdict

### 断言 1 — R1/R2/R5：四榜排名查询加 cohort 过滤，口径与 FIX-01 逐字一致；本人分数回退不过滤 → **ACCEPT**

- 四处新增（`leaderboard_service.py` 周榜 :648 / 连胜 :717 / 光子 :787 / 周光子 :865）均为 `User.registration_source.not_in(self.EXCLUDED_COHORT_REGISTRATION_SOURCES)`，与主仓 e7ef4d32 FIX-01 全局榜实现（:259）**逐字相同**；插在既有 `User.is_active, User.not_deleted_filter()` 之后，纯追加。
- 词表：`LeaderboardService.EXCLUDED_COHORT_REGISTRATION_SOURCES = ("guest","seed")`（:65）与 `app/core/telemetry_boundary.py:87` 共享常量 `("guest","seed")` 两树等值；friend/community 走 **import 共享常量**（非抄字面量），类常量来自 FIX-01 既有定义，本卡零新词表。
- **my_score 不过滤红测实证（变异实验）**：向连胜回退查询（:752）注入同款 join+not_in 过滤（cp 备份后单文件变异）→ `test_streak_own_streak_fallback_is_not_cohort_filtered` 立即 **RED**（1 failed / 7 passed），还原后全绿。钉子真实有效。
- live 只读复算（2026-09-19）：连胜 top-20 修前 guest16+seed3+email1 → 加过滤后 **email 2 席（top=9），guest/seed 0**；光子 top-20 修前 guest 20（max 1020）→ **email 7 席（top=50），guest/seed 0**；周学习榜 guest 168+seed 5+email 26 → **email 26，guest/seed 0**。与 REPORT §5 全部吻合（guest 168 vs 报告 167 为数据漂移，方向一致）。

### 断言 2 — R3：好友推荐池 cohort 过滤 + 补 not_deleted_filter；import 共享常量 → **ACCEPT（附 1 条测试加强建议，不阻塞）**

- `friend_match_service.py:752` 追加 `not_in(EXCLUDED_COHORT_REGISTRATION_SOURCES)`（import 自 `app.core.telemetry_boundary`，:12）+ `User.not_deleted_filter()`（:754），均在 WHERE 内（diff 实证）。
- live 复算：池头 60 席修前 seed2+guest58（**0 email**）→ 加过滤后 **email 60/60**。与报告一致。
- ⚠️ 附注（非阻塞）：`test_public_candidates_keep_soft_delete_and_visibility_filters` 的 `"DELETED_AT" in sql` 断言在基线（无修复）也通过——`select(User)` 的 SELECT 列表本就含 `USERS.DELETED_AT`，该断言对 WHERE 级软删过滤**不构成区分**（空判）。修复代码本身真实，但此测试对"补齐 not_deleted_filter"无回归保护力。建议后续改为断言 `"DELETED_AT IS NULL"` 出现在 WHERE 片段。user_search 同款断言同样空判。

### 断言 3 — R4：用户搜索同款 + 软删过滤；唯一调用方用户侧、无 admin 消费方 → **ACCEPT**

- `community_service.py:3012` 追加同款 not_in + `not_deleted_filter()`（:3014）；import 共享常量（:29）。
- 调用链 grep：`UserSearchService.search_users` 全库（`app/`，排除测试）**唯一调用方** `app/api/v1/community.py:1468`（用户侧端点，`current_user.id`）；无 admin 消费方。行为回归风险排除。

### 断言 4 — R7 勘误：台账「streak join 笛卡尔积」应为协同过滤 get_similar_users ON 缺陷；连胜 join 1:1 → **ACCEPT，背书 Leader 更新台账**

- 主仓 `DYNAMIC_ISSUES.md` FIX-07 行（:13）原文确为「streak join 笛卡尔积独立 bug」。
- 连胜榜 join = `join(UserStreakStats, UserStreakStats.user_id == User.id)`（:708-709）；`UserStreakStats.user_id` 为主键成分（`app/models/achievement.py:216` primary_key=True；live schema 实证 PK=`(user_id, id)`）。脚注：user_id 为**复合**主键前缀列，单列唯一性非约束强制，但 live 数据 185/185 distinct user_id + 服务层 `scalar_one_or_none` 用法证实 1:1，无笛卡尔积。勘误成立。
- 真 bug 实证：公开版 `get_similar_users` 修前 ON 仅绑 `user_id_1/2 == request.user_id`（diff 删除行），构成 UserSimilarity × User 笛卡尔积；修后与内部版 `_get_similar_users`（HEAD 上即双侧绑定的正确参照）逐字一致，且有 parity 红测钉住（基线克隆实测该 2 用例修前双红）。
- 休眠复核：live `user_similarities`=0 行、`user_item_interactions`=0 行；`to_regclass`：单数 `user_similarity` 不存在、复数存在 → REPORT 对 FIX-01「表不存在」系表名笔误的更正**准确**。R6 留 OPEN 合理（0 行休眠，定时任务产出后会立即升级，建议开后续卡）。

### 断言 5 — 测试与回归数字 → **ACCEPT（附 2 处 REPORT 记载更正，均不阻塞）**

| 项 | Worker 声称 | R1 独立复跑 | Verdict |
|---|---|---|---|
| 新增用例 | 16 | 16 collected，修后 **16 passed**（1.37s） | ✅ |
| 修前红测 | 9 failed / 7 passed | /tmp 基线克隆（纯 HEAD 86454bbb）= **8 failed / 8 passed** | ⚠️ 差 1：见更正① |
| GREEN 汇总 | 27 passed | 22（六文件）+ 5（`tests/test_leaderboard_percentile_guard.py`，位于 tests/ 根非 services/）= **27** | ✅ |
| API 定向回归 | 67 passed | **67 passed**（22.9s） | ✅ |
| 终局 | 94/94 | 27+67=**94/94** | ✅ |
| com011 3F 既有 | HEAD 既有 | 基线克隆复现**同 3 用例红**（test_returns_scored_pursuers / embedding_failure_graceful_fallback / respects_limit_parameter）；wt5（FIX-19）恰在修此文件 | ✅ |
| route_shadowing 1F 既有 | HEAD 既有 | **不可复现**：基线克隆与 wt6 单独/组合跑均 2/2 绿 | ⚠️ 见更正② |
| ruff 持平 | 与基线持平 | 改动 8 文件 4 errors（I001/E712/B905×2，全在 community_service 既有行）= 基线同 4 errors，仅行号位移，零新增 | ✅ |

**更正①（红测计数 off-by-one）**：Worker 的 9F/7P 无法复现，实测 8F/8P。差值即断言 2 附注的 friend 软删断言——修前即因 SELECT 列表含 DELETED_AT 而空判通过，Worker RED 运行时该用例记红的原因无法回溯（疑为 RED 运行用了后经微调的测试草稿）。**不影响修复正确性**（8 个真红覆盖全部 cohort/join 缺口，修复后全绿）。
**更正②（route_shadowing 行失实）**：REPORT §4 称该文件 1F/1P 为 HEAD 既有，验收环境（/opt/homebrew/bin/python3.11，SECRET_KEY=test）基线与 wt6 均 2/2 绿。属过时/环境差异记载，非本卡回归掩盖（方向相反：实际比报告更好）。

## 2. 合入预演

- `git apply --3way --check changes.patch` 对主仓 **e7ef4d32**：**通过**（4 个 service 文件 cleanly；`--check` 全程只读未触碰主仓）。
- 与在途 **FIX-19（wt5）文件级重叠：零**。wt5 仅改 `tests/api/test_task_quick_actions_api.py`、`tests/contract/test_event_registry_contract.py`、`tests/unit/test_c03_adaptive_replanner_wiring.py`、`tests/unit/test_com011_similar_goal_pursuers.py`（后者与 com011 既有 3F 交给 FIX-19 处理，与本卡无冲突）。

## 3. 必修分级

| 级别 | 项 |
|---|---|
| **必修（阻塞合入）** | 无 |
| **建议修（不阻塞，可随合入或在后续卡）** | ① REPORT.md 更正两处：§2 红测计数 9F/7P → 实测 8F/8P（并注明软删断言空判）；§4 删除或更正 route_shadowing「1F/1P HEAD 既有」行。② friend/user_search 的 `DELETED_AT` 断言加强为 WHERE 级（如断言 `"DELETED_AT IS NULL"`），否则"补齐 not_deleted_filter"无回归保护。 |
| **台账动作（背书）** | Leader 将 FIX-07 行「streak join 笛卡尔积独立 bug」更正为「collaborative_filtering `get_similar_users` ON 单侧绑定笛卡尔积（已修）；连胜榜 join 1:1 无笛卡尔积」；可一并记 FIX-01 表名笔误（`user_similarity`→`user_similarities`，存在但 0 行）。R6 开后续卡建议成立。 |

## 4. 总 Verdict

**ACCEPT（可合入）**。四处过滤口径与 FIX-01/共享常量逐字一致且为 import 复用；my_score 不过滤语义有红测钉住并经变异实验实证；R7 勘误两条独立证据链（复合 PK + 内部版参照）均成立；live 只读复算六面修前污染、修后 guest/seed 全零与报告吻合；94/94 回归独立复跑通过；对 main@e7ef4d32 合入预演干净、与 FIX-19 零重叠。两处 REPORT 记载偏差（红测计数、route_shadowing 行）与一条测试加强建议不构成合入阻塞。

## 附：R1 实跑命令清单（全部只读/可逆）

1. `git -C wt6 status --short` / `rev-parse HEAD` / `diff HEAD --stat`；`git -C 主仓 rev-parse HEAD`、`merge-base --is-ancestor e7ef4d32 86454bbb`（NO→wt6 落后）
2. `git -C wt6 diff HEAD > /tmp/r1fix07_tree.diff`；剔 index 行与 changes.patch `diff` 比对（全等）
3. grep 两树 `EXCLUDED_COHORT_REGISTRATION_SOURCES`（telemetry_boundary:87 / leaderboard:65 / 四处调用点）；主仓 :259 FIX-01 原型比对
4. `SECRET_KEY=test /opt/homebrew/bin/python3.11 -m pytest <4 新测试文件> -q` → 16 passed
5. 变异：`cp` 备份 → Edit 连胜回退查询加 join+not_in → 重跑 → 1 failed（钉子红）→ `cp` 还原 → `git diff --stat` 复核 +14/−4
6. 27 服务层回归（6 文件 + tests/test_leaderboard_percentile_guard.py）→ 22+5 passed；8 文件 API 回归 → 67 passed
7. `git clone wt6 /tmp/r1fix07-baseline`（symlink app/gen）→ 新 4 文件红测 → 8F/8P；com011+route_shadowing → 3F/9P；route_shadowing 单独/组合复跑（基线与 wt6 均 2/2 绿）
8. live：`docker exec -i sparkle_db psql -U postgres -d sparkle`（BEGIN READ ONLY…ROLLBACK）三面修前/修后 SQL + dormancy count + PK/重复 user_id 检查（185/185）+ `to_regclass` 单复数
9. `grep -rn search_users app/`、`UserSearchService` 调用链；`DYNAMIC_ISSUES.md` FIX-07 行原文
10. `git -C 主仓 apply --3way --check changes.patch`（通过）；`git -C wt5 status --short`（4 测试文件，零重叠）
11. ruff（改动 8 文件 vs 基线 4 service 文件）→ 4=4 同款持平
12. 收工清理：`rm -rf /tmp/r1fix07-baseline /tmp/r1_fix07_lb_backup.py /tmp/r1fix07_tree.diff`；wt6 `git status --short` 复核与开工一致（8 文件 + v3-output，无漂移）
