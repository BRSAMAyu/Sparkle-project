# WT733-WRITE419 — V3-FIX-419 社区写面闸门（软删+双向拉黑）修复实录

- 日期：2026-09-27
- 分支：`agent/node-b/wt733/write419`（base `dfc19e63`）
- worktree：`/Users/brsama/code/GitHub/Sparkle-sysrev/wt733-write419`
- 修复 commit：`59291208`（代码+测试）；台账与本文档另行走 docs commit
- 任务：V3-FIX-419（P3，wt713 猎缺登记，wt719 复核 CONFIRMED）

## 1. 问题（与台账行一致）

`create_post_comment` 与 `toggle_like_post` 帖定位只过 `_cohort_visible_post_clause`
（V3-FIX-08 cohort 护栏），对照 feed 读面（`Post.not_deleted_filter()` + :420-431
双向 block 排除）读写不对称：

- 软删帖仍可评论/点赞，`comment_count`/`like_count` 在已删行上继续自增（读面过滤后计数虚高）；
- 任一向拉黑关系下仍可按 post_id 直写对方帖，且触发 `NotificationPushService`
  向拉黑者落 Notification 并 WebSocket 推送（wt719 危害补强，本轮实录复证）。

## 2. 修法（与复核方向一致，FIX-192 写闸同构）

`backend/app/api/v1/community.py`（+34 −11）：

1. 新增 `_active_block_exclusion_clause(current_user)`：feed 读面 :420-431 双向
   block 谓词**原样抽取**为读写共享子句（我拉黑的 + 拉黑我的，软删拉黑行不回闸）；
2. `get_feed` 内联 block 段改调同一函数——谓词语义零变化，读侧零放松；
3. 两写端点帖定位补 `Post.not_deleted_filter()` + `_active_block_exclusion_clause()`，
   闸后按不存在处理（404，与 cohort 护栏同语义）；计数自增与通知推送随闸自然闭合。

## 3. 红→绿实录

新增 `backend/tests/api/test_post_write_gates_softdel_block.py`（11 测，双技术：
functional=conftest sqlite `db` fixture 真 DB 真 ORM 行；shape=FIX-08 族
statement-capture）。

修前（`59291208^`）：

```
FAILED test_comment_on_soft_deleted_post_is_404_and_landless        # DID NOT RAISE，评论落已删行
FAILED test_like_on_soft_deleted_post_is_404_and_landless           # DID NOT RAISE，点赞落已删行
FAILED test_comment_on_author_blocked_post_is_404_and_landless      # DID NOT RAISE
FAILED test_comment_on_reverse_blocked_post_is_404                  # DID NOT RAISE
FAILED test_like_under_block_either_direction_is_404                # DID NOT RAISE
FAILED test_like_lookup_sql_carries_softdel_and_bidirectional_block_gates
FAILED test_comment_lookup_sql_carries_softdel_and_bidirectional_block_gates
FAILED test_write_lookup_uses_same_block_clause_as_feed
8 failed, 3 passed
```

修前 captured stderr 实录（通知推送触达拉黑者，wt719 危害补强坐实）：

```
Created notification a242c961-... for user 0391ca1e-...: New comment on your post
Pushed notification a242c961-... via WebSocket
Created notification 09aa92c0-... for user d097bce9-...: Someone liked your post
```

修后：**11/11 绿**。3 个修前已绿的是防过闸正控：健康路评论/点赞照常（计数=1、
双 Notification 到作者，闸不是一刀切静音）、feed 过滤栈全在、cohort 子句未动。

## 4. 验证面

- community 既有面（find 先行选面）合跑 **114 passed 2 skipped**（skip 为既有
  条件跳过，FIX-192 同记）：
  - FIX-192 邻域：test_post_visibility_gate（7）+ test_s03_surface_convergence（4）
  - FIX-08 族：test_post_interaction_cohort_guard（3）+ test_post_comments_cohort_filter（2）
    + test_community_feed_cohort_filter（8）
  - 拉黑面：test_blocked_users_api（1）
  - 行为级：integration/test_community_integration（feed 软删/可见性行为零变化实证）
    + test_community_security + test_community_e2e + s04/s05 + accountability 两件
    + schemas/test_community_schema
- **读侧零放松**：`get_feed` 仅把内联 block 段换成同一函数，谓词逐字符同源；
  test_community_feed_cohort_filter 8/8 绿 + integration feed 行为级绿
  + 新钉测 `test_feed_read_face_filter_stack_unrelaxed`（DELETED_AT/VISIBILITY/
  REGISTRATION_SOURCE/USER_BLOCKS 双向形态全在）。
- **mypy**：`mypy app --ignore-missing-imports` 新鲜缓存对照
  （base `dfc19e63` 与本分支各自独立 MYPY_CACHE_DIR 冷跑）**base 133 = 修后 133，
  错误清单 diff 逐条 NO-DIFF**，触达 community.py 零新增。任务书基线 132 经证为
  暖缓存环境既有差：base 冷缓存同现 `app/aurora/policy_loader.py:9` yaml stub
  既有错（types-PyYAML 未装），同 wt730「147 vs 台账 146」先例。
- **ruff**：触达 2 文件 `ruff check` All checks passed；新测试文件已
  `ruff format`；community.py 的 format 漂移为 base 既有（base 单独 --check 同红，
  hunks 与新增行零重叠，按 wt730 判例不代整）。

## 5. 台账

- V3-FIX-419 → `FIXED@59291208`（证据全文见台账行）；
- 新发现 **V3-FIX-449**（P3，OPEN）：同邻域收口复核发现——
  ①`list_post_comments` 帖定位零闸（软删帖评论列表仍可读 + 评论作者仅 cohort
  单向过滤、无双向 block）；②`delete_post_comment` 的 comment_count 自减帖查找
  为裸 select（软删行上计数仍被改，419 计数污染删除半边）；
  449 号 grep 亲证空闲（全文 0 命中，在册最高 443）；
- `ledger_union_merge.py --verify`：**314 行 V3-FIX 行，裸管 {8: 314}，零 FAIL**。

## 6. 边界与诚实声明

- 未 push；未动主仓（主仓只读，worktree 隔离）；gen/ `.venv` 按先例本地拷贝/薄壳
  （python→homebrew 3.11），不入库。
- 修前红基于本分支真代码（`pytest` 8 failed 实录 + 通知 WebSocket 日志实录），
  无任何断言删改换绿；wt713 的 sqlite 探针 `repro_softdel_block_gate.py` 保留在
  v3-output/WT713-HUNT1/ 作登记时 RED 证据（其「写端点同型查询」为修前快照，
  修后等价断言由本测试文件 11 测承载）。
- V3-FIX-449 仅登记未修（属新发现，按猎缺惯例另卡执行）；本卡不扩面。
