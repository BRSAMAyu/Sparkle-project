# WT767-C465C497 — FIX-465 评论读面帖定位 block 闸 + FIX-497 daily_hours 类型收口

- Agent: wt767 ｜ 分支 `agent/node-b/wt767/c465c497`（base main@e9ec99d8）｜ 2026-09-28
- 台账: v3/06_agent_fleet/DYNAMIC_ISSUES.md 行 365（465，wt741 登记）/ 行 382（497，wt761 登记）
- 主线仓库只读；worktree `/Users/brsama/code/GitHub/Sparkle-sysrev/wt767-465497`
- 环境: venv `/Users/brsama/code/GitHub/sparkle-cosmos/backend/.venv`（Python 3.11.15，mypy 1.20.2，pytest 9.0.3）；`backend/app/gen` 按 wt761/wt369 先例自主仓 symlink 补齐（产物不入库，未 commit）；裸 worktree 无 `.env`，pytest 以 `SECRET_KEY=x` 进程 env 直跑（TEST-DBGUARD 会话门通过，测试全落内存 sqlite）

## FIX-465（P4，协调方裁决=补闸）评论读面帖定位未过 block 闸

**病灶**：`list_post_comments`（GET /posts/{post_id}/comments）449 批修后帖定位只带
`Post.not_deleted_filter()`（community.py:592-604@e83a33f8），未过
`_active_block_exclusion_clause`——feed 读面双向 block 隐藏的帖（我拉黑其作者/
作者拉黑我任一向）经评论线仍可达：第三方评论照常返回、帖存在性可按 post_id
探测（侧道=评论线可见性）。协调方裁决「补闸」：帖定位补
`_active_block_exclusion_clause(current_user)`（与 feed 同闸同词表，404 语义与
软删闸同形）。

**修法**：帖定位 `select(Post).where(...)` 追加第三个谓词
`_active_block_exclusion_clause(current_user)`（community.py:594-606，默认
author_column=Post.user_id 即帖作者列，419 共享子句零参数化改动）——feed 隐藏帖
在评论线按不存在处理（404，与同函数软删闸同一 `raise HTTPException(404,
"Post not found")` 出口，同形语义）。评论作者面（449 已修的双向排除）不动。

**红→绿**（新增 tests/api/test_comment_post_location_block_gate.py，5 用例；
functional=conftest sqlite db fixture 真 DB 真 ORM 行，shape=FIX-08 族
statement-capture，镜像 449 文件两技法）：

- 修前红 3：`test_list_comments_on_post_of_author_i_blocked_is_404` /
  `test_list_comments_on_post_of_author_who_blocked_me_is_404` 双向均 **DID NOT
  RAISE HTTPException**（修前返回评论列表=200 形，侧道实录）；
  `test_list_comments_post_lookup_sql_carries_block_gate` 帖定位 SQL 无
  USER_BLOCKS/BLOCKER_ID/BLOCKED_ID 标记。
- 随批绿 2（正控，钉不扩大面）：`test_list_comments_lifted_block_restores_comment_line`
  （软删拉黑行解除不回闸——同 feed 解除拉黑语义，钉子句内
  UserBlock.not_deleted_filter 词表）、`test_list_comments_unrelated_post_line_untouched`
  （无拉黑关系评论线照常，钉无过度隐藏）。
- 修后 5/5 绿。

## FIX-497（P4）plan_review daily_hours 无类型收口，字符串型 TypeError 500

**病灶**：`_validate_feasibility` :919 `daily_hours = params.get("daily_hours")`
裸取值（ToolCallSpec.params: dict[str, Any]，LLM 生成键集值型不保证）——492 修后
:934/:942/:951 的 `daily_hours and daily_hours < N` 守卫只防 None/0，字符串型
"2" 真值通过后 `str < int` 同型 TypeError；:960 `daily_hours * total_days`
字符串复合同炸。:833 `_resolve_daily_capacity_minutes` 对同键族已走
`_positive_float` 收口（TypeError/ValueError→None），:919 为平行裸取不一致点。

**修法**：对齐 :833 既有先例——:925 改
`daily_hours = self._positive_float(params.get("daily_hours"))`（plan_review_service.py:919-925
注释+一行替换）：数值字符串转 float 参与既有比较（"1"→1.0，既有守卫语义原样
生效）；垃圾值/缺键→None（与 492 缺参守卫语义衔接）。无新异常面。

**红→绿**（新增 tests/unit/test_plan_review_feasibility_daily_hours_type_coercion.py，
5 用例；工具名 `generate_study_material` 避开 SAFE_TOOL_CATEGORIES 短路与
_collect_feasibility_comments 的 plan/sprint/schedule/task token 过滤，确保病灶
就在 :919，同 492 判例）：

- 修前红 5（全部 `TypeError: '<' not supported between instances of 'str' and
  'int'` @:934 运行级实录）：`"1"` 文科专家拒（应 False）、`"3"` 边界放行（应
  True）、`"4"`×7 天走 28<50 总时门槛（应 False，证数值语义非字符串重复）、
  `"abc"` 垃圾值按缺参语义（应 True 不 500）、`_quick_rule_check` 快速审查通道
  端到端自动批准（应 `"high_confidence_simple_plan"` 不 500）。
- 修后 5/5 绿；492 既有 4 用例零回退。

## 验证

- **红先行**：两子项修前红均基于 base 真代码运行级实录（465=3 failed 2 passed、
  497=5 failed，见上），无断言删改换绿。
- **pytest 触达面**：
  - community 族合跑 **133 passed / 2 skipped / 0 failed**（419 写面 11 + 449
    面 12 + 本批 465 新 5 + FIX-192/FIX-08 cohort 族/拉黑面/可见性/integration/
    accountability/s03/s04/s05/friend_match/group_discovery/broadcast 族；skip 为
    既有条件跳过，同 wt741 批口径）。449/419 既有测试面零回退。
  - plan_review 族合跑 **88 passed / 1 failed**——该 1 failed 为
    `test_openclaw_phase5_10_followup.py::test_plan_review_auto_delegate_generated_tasks_uses_execution_batch`
    同批进程内既有互扰（该测不触 daily_hours/_validate_feasibility；**base 同批
    复跑同样 1 failed 83 passed 实录**，单文件隔离跑 passed——既有干扰非本卡
    回归；本分支同批 88 passed = base 83 + 本批 5 新测）。
- **mypy 同环境 BEFORE/AFTER**（`mypy app --ignore-missing-imports
  --no-error-summary`，独立 MYPY_CACHE_DIR 冷缓存）：BEFORE(base)=**202** /
  AFTER(本分支)=**202**，diff 逐条核对仅 1 行既有错误行号平移
  （plan_review_service.py:1804→:1810 arg-type，恰为本卡注释插入 +6 行），
  **零新增零消失**。环境注：任务口径基线 91 为 wt761 环境（venv mypy 版本差）
  既有数；本卡按 wt733/wt741/wt761 同环境对比纪律以 BEFORE/AFTER NO-DIFF 为准，
  触达两文件无本卡新增错误。
- **ruff**：触达 4 文件（community.py、plan_review_service.py + 2 新测试文件）
  `ruff check` All checks passed；2 新测试文件 `ruff format --check` 已收口。

## 顺审新发现（登记 V3-FIX-499，停手不顺手修）

- `_validate_feasibility` total_days 无类型收口（497 同族）：base :920
  `total_days = params.get("total_days", params.get("duration_days"))` 裸取值，
  :958（修后 :964）`if total_days and total_days <= 7:` 字符串型 "7" 真值过后
  `str <= int` TypeError；:960（修后 :966）`daily_hours * total_days` 在 497 修后
  daily_hours=float 下遇字符串 total_days 为 float*str TypeError。**运行级探针
  实录**（本分支修后代码，daily_hours=4 数值 + total_days="7"）：
  `TypeError: '<=' not supported between instances of 'str' and 'int'`。
- 499 号 grep 复核空闲：本 worktree（e9ec99d8）全仓 v3/ v3-output/ docs/
  backend/ `V3-FIX-499`/`V3-FIX-500` 0 命中；台账在册顺序最高 497，备用号
  500 未用（499 预占，500 保留备用）。

## 边界与诚实声明

- 未 push；未动主仓（只读，worktree 隔离）；未碰运行栈。
- `backend/app/gen` 为 symlink 补齐产物，不入库不 commit。
- 465 按协调方裁决「补闸」执行（非产品裁决的「评论线不受帖级 block 隐藏」分支）；
  497 语义选择=对齐 :833 `_positive_float` 先例（数值字符串转换、垃圾值→None），
  与台账修法方向栏逐字一致。
- 未运行全量守卫/全量测试（纯触达面验证）；openclaw 同批互扰为 base 既有（base
  复跑实录），未在本卡修（超卡边界，未登记新号——该现象属测试隔离债非产品 bug，
  如需处置应走测试基建卡）。
- mypy 202 vs 任务口径 91 的环境差已如实注记（同环境对比零新增为判定口径）。
