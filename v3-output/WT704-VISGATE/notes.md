# WT704-VISGATE — V3-FIX-192 写侧可见性闸（闭账实录）

- 卡：V3-FIX-192（P3，wt695 日终盘点 A1 队列项）
- 分支：`agent/node-b/wt704/visgate`（worktree `/Users/brsama/code/GitHub/Sparkle-sysrev/wt704-visgate`）
- 修复 commit：`ae3dec70`（fix commit）；台账/产出 commit 见分支尾
- 基点：main `c0b36730`

## 1. 问题定位（先 find 后动手）

- 写侧：`backend/app/api/v1/community.py` `create_post`（原 :461-482）——`visibility="public"` 硬编码，
  完全不读请求体；`@limiter.limit("5/minute")`。
- 读侧：同文件 `get_feed`（:322-457）——全局流仅 `Post.visibility == "public"`；
  scope 流（squad/goal_mates/following）为 `public OR friends（含作者本人）`；
  另有 cohort（V3-FIX-08）、拉黑、软删护栏。
- 取值域权威：`backend/app/models/community.py:887` `Post.visibility` 列注释 `# public, friends, private`，默认 public。
- 结论：读写不对称成立——请求带 `friends`/`private` 一律被静默升格 public 落库；
  非法值也不拒（任何值都写 public，等于没有校验层）。

## 2. 修法（写侧按请求值闸，默认口径不擅改）

- 新增模块常量 `POST_VISIBILITY_VALUES: tuple[str, ...] = ("public", "friends", "private")`（=列域）。
- `create_post` 读 `body.get("visibility")`：
  - 缺省（None）→ `"public"`：既有产品默认口径保持，不擅自改；
  - 提供时 `strip().lower()` 归一后必须落在取值域，域外 → `422`，detail 人话
    （`visibility 仅支持 public/friends/private，收到: '...'`），且零落库；
  - 读侧过滤零放松：`get_feed`/`toggle_like_post`/`create_post_comment`/cohort 护栏一行未动。
- 留守产品裁决（本卡不代决，台账行已如实登记）：
  1. 「缺省=公开、用户无选择权」的口径本身是否要变；
  2. `RELEASE_ENABLE_PUBLIC_COMMUNITY=False`（当前默认）时写侧是否 403 或强制 friends。
  两项原计划随 `T-release-gate-public-surfaces` 卡落。

## 3. 红→绿实录（真实运行）

环境：worktree backend + `.venv` 薄壳（同主仓形制，python→homebrew 3.11）；`DATABASE_URL=sqlite+aiosqlite:///:memory: SECRET_KEY=v`。

红（修前 /tmp 一次性探针，不入库）：

```
FAILED ../../../../../../../tmp/wt704_red_probe.py::test_friends_visibility_stored
FAILED ../../../../../../../tmp/wt704_red_probe.py::test_private_visibility_stored
FAILED ../../../../../../../tmp/wt704_red_probe.py::test_invalid_visibility_rejected
3 failed, 1 warning in 1.69s
```

断言细节：

```
AssertionError: stored 'public'          # requested=friends
AssertionError: assert 'public' == 'private'
Failed: DID NOT RAISE <class 'fastapi.exceptions.HTTPException'>   # visibility=everyone
```

（注：另一版带 `POST_VISIBILITY_VALUES` 导入的红测在修前是收集期 ImportError——`cannot import
name 'POST_VISIBILITY_VALUES'`，同样先红；上面取的是行为级红证据。）

绿（修后，`tests/api/test_post_visibility_gate.py` 7 用例）：

```
tests/api/test_post_visibility_gate.py .......   [100%]
7 passed in 0.74s
```

用例覆盖：域常量=列域、friends 落库、private 落库、显式 public、缺省默认 public、
域外 422 且 `db.added == []`、`" Public "` 归一为 public。
技术：recording-db 捕获 `db.add()` 的 ORM 对象（FIX-08 家族形制，不触库）；
slowapi 限流端点用真实 starlette Request(scope, receive)，每次调用唯一对端 IP 隔离内存桶。

## 4. community 既有测试（合跑）

```
tests/api/test_post_visibility_gate.py .......                           [ 8%]
tests/api/test_community_feed_cohort_filter.py ........                  [ 42%]
tests/api/test_post_interaction_cohort_guard.py ...                      [ 51%]
tests/integration/test_community_integration.py ...ss........            [ 88%]
tests/api/test_s03_surface_convergence.py ....                           [100%]
33 passed, 2 skipped in 21.58s
```

skip 为既有条件跳过（非本卡引入；读侧 public/friends/private 过滤语义由 integration 文件背书，零回退）。

## 5. 门禁

- mypy（`mypy app --ignore-missing-imports`）：worktree **159** errors / 129 files。
  任务书基线 158 是旧合并态数字；对 main 同基点 `c0b36730` 复测同样 159，
  错误清单（去行号排序后）**逐条 NO-DIFF**——本卡零新增，+1 为基点既有漂移。
  `app/api/v1/community.py` 本身零 mypy 错误。
- ruff：`app/api/v1/community.py` + `tests/api/test_post_visibility_gate.py` → `All checks passed!`。

## 6. 台账

- `v3/06_agent_fleet/DYNAMIC_ISSUES.md` V3-FIX-192 → `FIXED@ae3dec70（…闭账实录…）`（Status 列，7 列形制不变）。
- 无新缺陷发现，未启用备用号 V3-FIX-399/400；产品裁决项随原行 Owner task 文字保留。
- verify：`python3 scripts/devtools/ledger_union_merge.py --verify v3/06_agent_fleet/DYNAMIC_ISSUES.md`（结果见台账 commit 前的最后运行，要求零 FAIL）。

## 7. 未动清单（铁律自查）

- 未 push；未动主仓；gen/ 与 .venv 按 gitignore 不入库（worktree 本地拷贝/薄壳）。
- 未动读侧任何过滤、未动 `_post_to_response` 响应形状（Flutter 契约零变化）、未动限流。
- 一次性红探针放 /tmp，未入仓库。
