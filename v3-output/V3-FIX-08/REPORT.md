# REPORT · V3-FIX-08（P1）：社区 Feed cohort 污染修复

- 执行: V3 Fleet Worker（wt6，general 路线，MEDIUM）
- 日期: 2026-09-19
- worktree: `/Users/brsama/code/GitHub/Sparkle-sysrev/wt6`（基线 origin/main @ **820c0203**，开工时 working tree clean）
- 上游依据: 主仓 `v3/06_agent_fleet/DYNAMIC_ISSUES.md` V3-FIX-08 行（B-02X INV-15）+ `v3-output/V3-FIX-07/REPORT.md`（家族修法范本，commit 55a64d4b）
- 约束遵守: 主仓与 sparkle_db 全程只读（所有 SQL 均在 `BEGIN TRANSACTION READ ONLY` 内执行）；无模拟器/Gradle/flutter/浏览器（LIGHT 任务）；真实 LLM 0 次（OPENAI/ZHIPU/ANTHROPIC 仅 dummy 环境变量，未发起任何调用）；无 git commit/push/stash/reset/clean；测试 venv 建在 worktree 内（收工已删）；无 `.env` 文件创建（SECRET_KEY 等全部内联注入）

---

## 0. 污染面清单（逐项处置总表）

Post/PostComment 的**唯一读取实现**在 `backend/app/api/v1/community.py`（Go 网关仅 proxy——`proxy_routes_test.go` 证明无第二实现；移动端消费 `/community/feed`）；服务层 `community_service.py` 无 Post 查询（FIX-07 的 R4 改的是 UserSearchService，与本次无交集、已验证共存）。

| # | 面 | 位置（修前行号） | 基线复算（2026-09-19） | 处置 | 修法 |
|---|---|---|---|---|---|
| S1 | `GET /feed` 全局分支（scope=None） | `community.py:368-369` | **成立（HIGH）**：未删公开帖 **341 = guest 336 + seed 5，email 0**（B-02X 记录 331，漂移 +10 guest，结论不变）。真实用户 feed 100% 是游客种子内容 | **已修（主修面）** | 追加作者 cohort 谓词：`or_(posts.user_id == 本人, posts.user_id IN (registration_source NOT IN 共享词表))`；本人帖始终可见（FIX-07「游客可见自己分数」同款 parity） |
| S2 | `GET /feed` scope=squad / goal_mates / following | `community.py:325-361` | 关系面：查询按显式关系（同群/搭子/好友）圈定作者，非聚合发现面 | **不修（边界明示）** | 保持显式关系语义——与 FIX-07 对好友列表不过滤同一边界。⚠️ 相邻风险：seed 用户是种子群成员（见 §5 相邻面） |
| S3 | `GET /posts/{post_id}/comments` | `community.py:489-501` | prospective 污染：评论作者无 cohort 过滤（修时 `post_comments` 0 行，种子账号一旦产生评论即上浮） | **已修** | 评论作者子查询过滤 `User.registration_source NOT IN (共享词表)`；该端点本无 auth 依赖（保持契约不变），guest 自见评论能力随之取消，已在 §6 明示 |
| S4 | like_count / comment_count 聚合计数 | `Post.like_count/comment_count` 反范式列 + `_post_to_response` | `post_likes` 0 行；计数仅经 feed 行暴露 → 随 S1 过滤后不再上浮；无 top-liked 类独立聚合端点（全仓已核） | **随 S1/S3 覆盖，无需独立修** | — |
| S5 | `POST /posts/{post_id}/like`、`POST /posts/{post_id}/comments`（直连 UUID 命中 cohort 帖） | `community.py:437-444, 514-526` | 防御性：feed 过滤后真实用户拿不到新 UUID，但陈旧 UUID 仍可给隐形帖点赞/评论并回读 like_count | **已修（防御护栏）** | 取帖语句加 S1 同款可见性谓词，cohort 帖对非本人按 404 处理；`delete_post_comment`（:648）为作者自查清理路径，不属读面，未动 |
| S6 | 删帖/删评论/发帖 | `community.py:412, 572, 597` | 写路径，owner 自查（发帖人即本人） | 不需修 | — |

**相邻面（不在本卡，记录供开卡）**：`GET /groups/search`、`GET /groups/directory`、`GET /groups/recommendations`、群火焰/打卡统计——guest_seed_service 播种了公开群「算法冲刺小队」等（seed 群主 + seed 成员 + seed 帖），真实用户加入种子群后在 S2 关系面与群目录里仍会看到 seed 内容。属「社群群组 cohort」范畴，建议独立开卡（修法同款：目录/搜索/推荐面加同词表过滤；群内关系面可讨论保留或标注）。

## 1. 基线复算（只读，数据漂移后以复跑为准）

账号普查（`deleted_at IS NULL`，未筛 is_active 以贴 feed 现状；active 版本见 FIX-07 §1）：**email 106 / guest 171 / seed 7**。

| 断言（B-02X INV-15） | 本次复跑 | 结论 |
|---|---|---|
| 公开未删帖 331 = guest 326 + seed 5，email 0 | **341 = guest 336 + seed 5，email 0**（全库 341 帖、0 软删、全部 visibility=public） | 成立且漂移加重（+10 guest） |
| post_comments 有游客内容 | 0 行（评论面为 prospective 污染） | 面存在、当前空 |
| post_likes 计数失真 | 0 行 | 随 S1 覆盖 |

复算 SQL 见附录 A；全部在 `BEGIN TRANSACTION READ ONLY` 内执行。

## 2. 红测先行（RED）

新增 3 个测试文件（13 用例），沿用 FIX-07 确立的 statement-capture 模式（`Rec` capture + `stmt.compile()`，全程不触碰数据库）。**RED 证据取自 /tmp 基线克隆**（`git clone` HEAD 820c0203，天然修复前基线；克隆内补拷 gitignore 的生成产物 `app/gen/` 使 import 可用，测试文件原样拷入）：

| 文件 | 用例数 | 覆盖 |
|---|---|---|
| `tests/api/test_community_feed_cohort_filter.py` | 8 | S1：全局 feed 谓词 NOT IN (guest, seed) 且绑定值正确；visibility/soft-delete/排序语义钉；本人帖 or 分支钉；三个关系 scope **不过滤**（边界钉，防修复外溢）；产品裁决槽默认关 + 只放行指名 cohort |
| `tests/api/test_post_comments_cohort_filter.py` | 2 | S3：评论作者谓词 NOT IN + post_id/排序语义钉 |
| `tests/api/test_post_interaction_cohort_guard.py` | 3 | S5：like/comment 直连 UUID 命中 cohort 帖 → 404 且语句带谓词；作者本人 or 分支钉 |

RED 运行（基线克隆，修复前代码）：**4 failed, 1 passed**——4 个失败全部是缺 cohort 谓词的预期断言（评论 1 + 互动 3）；1 个 pre-fix 即绿的是语义钉（post_id+排序保留）。feed 文件在基线克隆上因 import 新常量 `FEED_EXAMPLE_CONTENT_SOURCES` 无法收集（修复引入的符号，RED 语义由 S1 断言同构的互动护栏用例承载），如实记录。

## 3. 修复内容（GREEN）

全部位于 `backend/app/api/v1/community.py`（6 处编辑，`git diff` 见 changes.patch）：

1. **共享词表 import**：`from app.core.telemetry_boundary import EXCLUDED_COHORT_REGISTRATION_SOURCES`——与 FIX-01/07 的 leaderboard/friend-match/search 逐字同词表，零新词表。
2. **产品裁决槽（默认关）+ 两个 helper**：`FEED_EXAMPLE_CONTENT_SOURCES: tuple = ()`；`_excluded_feed_cohorts()` 返回 `词表 − 裁决槽`（默认空槽 = 与全排除完全等价）；`_cohort_visible_post_clause(user)` 产出 `or_(本人帖, 非cohort作者帖)` 子句。
3. **S1**：全局 feed 分支 `Post.visibility=='public'` 后追加可见性子句。
4. **S3**：评论列表加作者 cohort 过滤（用全量词表，不经理由：裁决槽语义是「示例帖回投」，不是「示例评论」）。
5. **S5**：`toggle_like_post` / `create_post_comment` 取帖语句加同款可见性谓词（404 语义）。

GREEN 运行（wt6，修复后）：**新增 13 用例全绿**。

**语义边界说明（非回归，明示给 reviewer）**：S2 三个关系 scope 不过滤（红测钉住，防止修复外溢到显式关系面）；S5 护栏使真实用户对 cohort 帖的陈旧 UUID 交互得 404（与删除帖一致）；guest 查看者本人在全局 feed/互动面仍可见并操作自己的帖子。

## 4. 产品裁决面处理

**核查结论：代码中没有「官方示例内容」机制可低成本挂接。** 逐项查证：
- `app/models/seed_content.py`（SeedLibrary/SeedItem）是 LLM few-shot/教学内容库（服务 prompt 生成），非用户可见 feed 内容源；
- 官方触达通道是 `BroadcastMessage`（公告广播），与 Post 帖子流不同面；
- Post 模型无 is_official/pinned/徽标字段。

因此按任务要求**不造机制**，只留开关位：`FEED_EXAMPLE_CONTENT_SOURCES` 默认 `()`（空 = guest/seed 全排除，D20 口径）。若产品未来裁决保留带官方标识、无互动入口的示例帖（即 V3-FIX-07 REPORT §6 的选项 B/C），把对应 registration_source（如 `"seed"`）加入该元组即可生效，无需再动查询逻辑；单测 `test_example_content_switch_*` 钉住默认值与只放行指名 cohort 的行为。

## 5. 定向回归（1 处失败为 HEAD 既有，与本次无关）

| 命令 | 结果 |
|---|---|
| 新增 3 文件（13 用例） | **13 passed** |
| `test_accountability_system_api.py` + `test_community_accountability_new_guest_500.py` + `test_community_accountability_route_shadowing.py` + `test_community_group_file_sharing_api.py` + `test_friend_match_api.py` + `test_recommendation_feedback_api.py` + `tests/services/test_user_search_cohort_filter.py`（FIX-07 R4，验证与 main 共存） | **25 passed, 1 failed** —— 唯一失败 `route_shadowing::test_community_accountability_registered_with_response_model` 为 FIX-07 REPORT §4 已记录的 HEAD 既有失败；已在 /tmp 基线克隆复核**同样 1 failed / 1 passed**，与本次改动无关 |

## 6. 修后 DB 复算对照（只读；修法是 SQL 谓词，故在各面口径上「仅追加本次过滤」复算，与 FIX-07 §5 同法）

| 面 | 修复前（复跑） | 修复后（追加过滤） |
|---|---|---|
| S1 全局 feed | guest 336 + seed 5 + email 0（341 帖） | **guest 0，seed 0**；email 0 帖 → feed 为空集，直到真实用户发帖（D20「不造假数据」语义下的诚实结果，与 FIX-01 对 leaderboard 的 HIDDEN 建议精神一致） |
| S3 评论列表 | 0 行（prospective） | **guest/seed 评论作者 0** |
| S5 可交互帖集合 | 341（全部 cohort 帖可被直连 UUID 交互） | **guest/seed 0**（非本人） |

产品注记：① 空 feed 的冷启动体验属产品裁决——本卡维持「默认过滤」，未替产品选择 B（示例帖回投）或 C（新官方 cohort）；如选 B/C 走 §4 的开关位 + 官方标识/无互动入口配套。② S3 端点无 auth（既有契约），cohort 过滤后 guest 无法在评论列表看到自己的评论；guest 社区可见面被逐卡收缩是既定方向（FIX-01/07/08 一致），如产品要求 guest 自见，属新需求。③ 本人帖在全局 feed 始终可见（含 guest 查看者看自己的帖）。

## 7. 交付物与收工清理

- 交付物：`v3-output/V3-FIX-08/REPORT.md`（本文）+ `v3-output/V3-FIX-08/changes.patch`（6 处 community.py 修复 + 3 个测试文件；untracked 测试以 `git add -N` 纳入 diff，FIX-07 同法）
- 代码改动：`backend/app/api/v1/community.py` + `backend/tests/api/test_{community_feed_cohort_filter,post_comments_cohort_filter,post_interaction_cohort_guard}.py`
- 清理清单：
  - [x] 删 worktree 内 `backend/.venv`（测试 venv）
  - [x] 删 `/tmp/fix08_reqs.txt`、`/tmp/fix08-baseline/`
  - [x] 无遗留进程/模拟器/构建产物；sparkle_db 全程 `BEGIN TRANSACTION READ ONLY` 只读 SELECT
  - [x] 真实 LLM 0 次；无 `.env` 创建；主仓零写入
  - [x] 无 git commit/push；收工 `git status` 与开工基线比对：1 M（community.py）+ 3 A（intent-to-add 测试）+ 1 ?? （v3-output/V3-FIX-08/），无其他漂移

---

## 附录 A · 复算 SQL（口径与 B-02X §6 / FIX-07 §5 一致）

```sql
BEGIN TRANSACTION READ ONLY;

-- 账号普查
SELECT registration_source, count(*) FROM users WHERE deleted_at IS NULL GROUP BY 1;
-- => email 106 / guest 171 / seed 7

-- S1 修复前：feed 可见面 cohort 分布（代码原谓词仅 visibility+soft-delete）
SELECT u.registration_source AS src, count(*) AS posts
FROM posts p JOIN users u ON u.id = p.user_id
WHERE p.deleted_at IS NULL AND p.visibility = 'public'
GROUP BY 1 ORDER BY 2 DESC;
-- => guest 336 / seed 5（email 0；漂移自 B-02X 的 326+5=331）

-- S1 修复后：仅追加 NOT IN ('guest','seed') 谓词
SELECT u.registration_source AS src, count(*) AS posts
FROM posts p JOIN users u ON u.id = p.user_id
WHERE p.deleted_at IS NULL AND p.visibility = 'public'
  AND u.registration_source NOT IN ('guest','seed')
GROUP BY 1;
-- => 0 rows（feed 空集；guest/seed 归零）

-- S3 修复后：评论作者追加过滤
SELECT u.registration_source, count(*)
FROM post_comments c JOIN users u ON u.id = c.user_id
WHERE c.deleted_at IS NULL AND u.registration_source NOT IN ('guest','seed')
GROUP BY 1;
-- => 0 rows

-- S5 修复后：直连交互可达帖集合追加过滤（404 语义）
SELECT u.registration_source, count(*)
FROM posts p JOIN users u ON u.id = p.user_id
WHERE p.deleted_at IS NULL AND u.registration_source NOT IN ('guest','seed')
GROUP BY 1;
-- => 0 rows

COMMIT;
```

**STATUS: READY_FOR_REVIEW**
