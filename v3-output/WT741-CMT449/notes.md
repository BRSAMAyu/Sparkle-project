# WT741-CMT449 — V3-FIX-449 社区评论读/删两面闸门修复实录

- 日期：2026-09-27
- 分支：`agent/node-b/wt741/cmt449`（base `65a1bab0`）
- worktree：`/Users/brsama/code/GitHub/Sparkle-sysrev/wt741-cmt449`
- 修复 commit：`0a1fd024`（代码+测试）；台账 449 置 FIXED 与 465 新登记、本文档另行走 docs commit
- 任务：V3-FIX-449（P3，wt733 登记；419 修复 `2ae4495d` 已在 main，`_active_block_exclusion_clause`
  共享子句基建在位，本批直接复用）

## 1. 问题（与台账行一致）

- `list_post_comments`（GET /posts/{post_id}/comments）：帖定位零谓词——软删帖的评论
  列表照常可读（419 计数污染同族的读半边）、缺失帖返回 200 空列表；评论作者仅
  cohort 词表单向过滤（EXCLUDED_COHORT_REGISTRATION_SOURCES），无 feed 读面同款
  双向 UserBlock 排除——被拉黑/拉黑我的作者的评论照常可见。
- `delete_post_comment`：comment_count 自减的帖查找为裸
  `select(Post).where(Post.id==post_id)`——软删行上计数仍被自减（419 计数污染的
  删除半边）。

## 2. 修法（与 419 同构最小面；删除面按 wt733 notes §5 裁决口径）

`backend/app/api/v1/community.py`（+33 −11）：

1. `_active_block_exclusion_clause` 参数化：加 `author_column=Post.user_id` 关键字
   参数——feed/写面全部调用点不变、编译 SQL 零变化；评论面传
   `author_column=PostComment.user_id` 复用同一子句（同一闸同一词表）。
2. `list_post_comments`：端点补 `current_user: User = Depends(get_current_user)`
   （mobile 走全局 AuthInterceptor 已带凭据，/feed 同为 authed 读面）；帖定位补
   `Post.not_deleted_filter()`，软删/缺失帖按不存在处理（404，与 419 写面同语义）；
   评论查询补双向 block 作者排除。
3. `delete_post_comment`：计数自减帖查找补 `Post.not_deleted_filter()`——自减仅对
   活跃帖行生效，软删行跳过自减；**删除动作本身保留**（wt733 裁决：不扩成 404，
   拉黑面维持仅删自己评论、危害低留档）。

## 3. 红→绿实录

新增 `backend/tests/api/test_comment_faces_gates_softdel_block.py`（12 测，
functional=conftest sqlite `db` fixture 真 DB 真 ORM 行+计数器断言；shape=FIX-08 族
statement-capture）。

修前（`0a1fd024^` 即 base 代码）：

```
FAILED test_list_comments_on_soft_deleted_post_is_404            # TypeError: unexpected keyword 'current_user'（闸不存在）
FAILED test_list_comments_on_missing_post_is_404                 # 同上
FAILED test_list_comments_hides_comment_of_author_i_blocked      # 同上（闸不存在→评论可见）
FAILED test_list_comments_hides_comment_of_author_who_blocked_me # 同上
FAILED test_list_comments_soft_deleted_block_row_restores_comment# 同上
FAILED test_list_comments_healthy_post_shows_all_commenters      # 同上
FAILED test_delete_comment_on_soft_deleted_post_keeps_counter    # AssertionError: comment_count must not decrement on the deleted row（1→0 实录）
FAILED test_list_comments_post_lookup_sql_carries_softdel_gate   # TypeError
FAILED test_list_comments_comment_sql_carries_bidirectional_block_and_cohort  # TypeError
FAILED test_list_comments_block_clause_shares_feed_helper_shape  # TypeError
FAILED test_delete_comment_counter_lookup_sql_carries_softdel_gate  # AssertionError: 裸 select 无 DELETED_AT IS NULL
10 failed, 2 passed
```

修前已绿的 2 个是正控基线：健康路删除自减照常、（格式化前）delete 计数查找形状
测试曾以 DELETED_AT 弱标记平凡通过——已收紧为 `DELETED_AT IS NULL`（WHERE 闸
本体；`select(Post)` 列清单恒含 deleted_at 列，弱标记无鉴别力）。

修后：**12/12 绿**。含软删拉黑行解除不回闸（feed 解除拉黑同语义）、健康路评论
全见+活跃帖删除自减照常两正控（闸不是一刀切）。

FIX-08 `test_post_comments_cohort_filter.py` 契约更新随形（**断言全保留，非删断言
换绿**）：REGISTRATION_SOURCE / NOT IN / guest+seed 词表界 / POST_ID / ORDER BY
CREATED_AT 全部在位，按新两语句布局重索引（statements[0]=帖定位，补
`DELETED_AT IS NULL` 钉测；statements[1]=评论列表），调用补 `current_user`
（旧签名直调与新端点签名不兼容，属契约变更非断言弱化）。

## 4. 验证面

- 419 既有 11 测（test_post_write_gates_softdel_block.py）：**11/11 绿，零回退**。
- community 既有面合跑（find 先行选面，与 wt733 同清单+本批新文件）：
  **126 passed 2 skipped**（=wt733 批 114 基线+本批 12 新测；FIX-192
  test_post_visibility_gate+test_s03_surface_convergence、FIX-08 族
  test_post_interaction_cohort_guard/test_post_comments_cohort_filter/
  test_community_feed_cohort_filter、test_blocked_users_api、
  integration/test_community_integration、test_community_security、
  test_community_e2e、s04/s05、accountability 两件、schemas/test_community_schema；
  skip 为既有条件跳过，419 批同记）。
- **mypy**：`mypy app --ignore-missing-imports` 冷缓存对照（base `65a1bab0` 主仓与
  本分支各自独立 MYPY_CACHE_DIR）**133=133，错误清单 diff 逐条 NO-DIFF**，触达
  community.py 0 错误。任务书基线 132 经证为暖缓存环境既有差（base 冷缓存同现
  `app/aurora/policy_loader.py:9` yaml stub 既有错），同 wt733「133 vs 台账 132」、
  wt730「147 vs 146」先例。
- **ruff**：`ruff check` 触达 3 文件（community.py+两测试文件）All checks passed；
  新测试文件已 `ruff format`。community.py `ruff format --check` 漂移为 **base 既有**
  （base 单独 --check 同红；base 13 hunks ↔ 本分支 12 hunks 逐条对应，本修复反而
  消去 base 在 delete_post_comment 裸 select 处的既有漂移 hunk）；唯一与新增行
  同语句的重排 hunk 在 list_post_comments 的 `scalars().all()` 链——该语句在 base
  同位置即被要求同型重排（pre-existing drift statement），按 wt730/wt733
  「既有漂移不代整」判例不扩面。

## 5. 台账

- V3-FIX-449 → `FIXED@0a1fd024`（证据全文见台账行）；
- 顺审新发现 **V3-FIX-465**（P4，OPEN）：评论读面帖定位未过 block 闸——feed 双向
  block 隐藏的帖经评论 GET 仍可达（第三方评论+帖存在性侧道；评论作者本身已双向
  过滤，危害低）。wt733 修法方向栏即只要求帖定位补软删闸，block 闸不在其中，
  本批按裁决最小面执行，留档备产品裁决。465 号 grep 亲证空闲（全仓 v3/ v3-output/
  docs/ 0 命中，在册顺序最高 461；备用号 466 未用）。
- `ledger_union_merge.py --verify`：**319 行 V3-FIX 行，裸管 {8: 319}，零 FAIL**
  （本分支 base 口径；main 在本任务期间已前移，集成时 union-merge 处理）。

## 6. 边界与诚实声明

- 未 push；未动主仓（主仓只读，worktree 隔离）；`app/gen` 按先例主仓 `cp -RL`
  拷贝不入库；裸 worktree 无 `.env`，pytest 以 `SECRET_KEY=x` 直跑（TEST-DBGUARD
  会话门通过，测试全落内存 sqlite，同 wt732 先例）。
- 修前红基于 base 真代码（pytest 10 failed 2 passed 实录，计数污染与闸缺失均为
  运行级断言失败），无任何断言删改换绿；cohort filter 文件的改动为契约随形
  （断言保留+重索引+新增帖定位钉测），详见 §3。
- delete 面拉黑闸未加系 wt733 裁决明确口径（删除动作保留、危害低留档），
  非本批遗漏；其产品侧 residual（帖级 block 与评论线可达性）另立 465。
- 465 仅登记未修（按猎缺惯例另卡执行）；本卡不扩面。
