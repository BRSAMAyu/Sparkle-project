# REVIEW_RECEIPT · V3-FIX-01（P0）：全局排行榜 guest/seed cohort 过滤

- Reviewer: 独立 Reviewer（wt7）
- 日期: 2026-09-19
- 被审对象: `v3-output/V3-FIX-01/REPORT.md` + `changes.patch`；worktree 未 commit 改动（`leaderboard_service.py` + 新测试）
- 结论: **ACCEPT**（Worker 自报 4 项结论全部独立重验通过，无阻断项）

---

## 1. Diff 复核（读 diff）

- ✅ **最小性**：净变更 9 行 = 类常量 `EXCLUDED_COHORT_REGISTRATION_SOURCES`（带 D20/B-02 F1 依据注释）+ top-N 查询 where 尾部一条 `not_in` 谓词。diff 仅触及 :59-64 与 :254-259。
- ✅ **语义保留**：`User.is_active` 与 `User.not_deleted_filter()` 原样保留（`not_deleted_filter` 定义于 `app/models/base.py:79`，实存）。
- ✅ **路径覆盖**：`_get_global_leaderboard` 只有**一条** top-N 查询（`.limit(request.limit)`），无独立分页/offset 路径；`get_my_rank`（limit=100）与 `get_summary`（limit=10）均路由到该方法，全部继承修复。
- ✅ **无误伤**：friends/group/weekly/streak/photon/subject 榜方法零改动；`user_score_q` 回退查询（:275-291）确认未加过滤，为有意决策且被测试 3 钉住。
- ✅ **测试非空跑**：RED 输出含真实编译 SQL（`SELECT USERS.ID, ... ORDER BY COMPOSITE_SCORE DESC LIMIT :PARAM_1`），证明断言的是 SQLAlchemy 编译产物；模式与仓内 `test_leaderboard_global_join.py` 逐一同构。

## 2. 测试重跑（独立执行）

执行环境：`/opt/homebrew/bin/python3.11`（sqlalchemy 2.0.48 / pytest 9.0.2），cwd=wt7/backend，`SECRET_KEY` 内联注入（未创建任何 .env）；未重建 venv。

| 套件 | 结果 |
|---|---|
| `tests/services/test_leaderboard_global_cohort_filter.py` | **3 passed** (0.33s) |
| `test_leaderboard_global_join.py` + `test_leaderboard_percentile_guard.py` | **8 passed** (0.34s) |
| `tests/api/test_accountability_system_api.py -q -x` | **13 passed** (9.59s) |

**RED 独立复现**：将新测试拷至 /tmp，对主仓（`Sparkle-project` @ main，已验证与 wt7 HEAD 基线逐字节一致、无修复代码）运行，`PYTHONDONTWRITEBYTECODE=1 -p no:cacheprovider`（主仓零写入）：test 1 以与 Worker 报告**逐字相同**的断言失败（`REGISTRATION_SOURCE not in compiled SQL`）。测试 2/3 在未修复代码上通过属预期（钉住既有语义的守护断言）。

## 3. DB 复算（只读 SELECT，sparkle_db）

同 B-02 F1 口径（per-user 标量子查询 + `is_active AND deleted_at IS NULL` + 权重 1.0/0.5/2.0/1.5）自写 SQL：

| variant | registration_source | in_top50 | top_score |
|---|---|---|---|
| FIXED（NOT IN guest/seed） | email | 50 | **10.0** |
| BEFORE（全 cohort 对照） | guest | 50 | **132.5** |

与 Worker §5 及 B-02 F1 基线**完全一致**。cohort 计数复核：guest 166 / email 75 / seed 7，248 账号全部 `is_active AND searchable_by='everyone'`。

## 4. 波及面抽查（3 HIGH 各一 + R7）

| 项 | 我的独立复核 | 结果 |
|---|---|---|
| R1 连胜榜 | `users ⋈ user_streak_stats` 按 source 聚合：email max current/longest = **1/1**；seed 11/25；guest 7/30 → 真实用户被结构性挤出 | ✅ 属实 |
| R2 光子榜 | 按 `photon_balance DESC LIMIT 20` 实测：**20 席全 guest**，max 1020；email 全体 max 仅 **10** | ✅ 属实 |
| R3 好友推荐候选池 | `friend_match_service._load_public_candidates`（:729-752）代码确认仅 `is_active + searchable_by=EVERYONE`、**无 `not_deleted_filter()`**；DB 实测 guest 166 + seed 7 = **173** 个候选 | ✅ 属实 |
| R7 CF 笛卡尔积 | 公开版 `get_similar_users` join 仅绑 `request.user_id` 未绑 `User.id == user_id_1/2`，确认语义错误；`user_similarity` 表不存在（休眠） | ✅ 属实（独立 bug，建议后续开卡） |

微瑕（不影响验收）：R1 描述"guest 30"实为 `longest_streak`（current 为 7），实质结论不变。

## 5. patch 完整性

- ✅ `changes.patch` 与 `git diff` **逐字节一致**（diff 比对通过，含新测试文件的 intent-to-add 条目）。
- ✅ 无 .env/密钥/无关文件；worktree 改动仅 2 个目标文件（`v3-output/B-01/` 为其他任务未跟踪产物，不在本 patch 内）。
- ✅ `registration_source` 的 guest/seed 值为真实业务值（`auth.py:878` 写入 "guest"、`guest_seed_service.py:233` 写入 "seed"）；User 模型 :104 行注释"email, google, apple, wechat"已过时（与本卡无关，可留待后续）。

## 6. 收工清理（Reviewer 自查）

- [x] `/tmp/review_red_test.py` 已删
- [x] 无我启动的遗留 pytest 进程（前台运行已退出，pgrep 复核为空）
- [x] 未创建 venv/构建产物；未动主仓任何文件（RED 验证用 no-write 标志）；DB 全程只读 SELECT
