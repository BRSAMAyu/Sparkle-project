# WT732 · V3-FIX-417 修复笔记（幂等闸门拒绝×自修正环洗白）

- 日期：2026-09-27；分支 `agent/node-b/wt732/idem417`（base dfc19e63=main）；worktree `/Users/brsama/code/GitHub/Sparkle-sysrev/wt732-idem417`
- 环境：主仓 venv `/Users/brsama/code/GitHub/Sparkle-project/backend/.venv/bin/python`（3.11）；`app/gen` 按先例主仓 `cp -RL` 拷贝不入库；裸 worktree 无 `.env`，pytest 以 `SECRET_KEY=x` 直跑（DB 会话门降级为告警横幅，本任务测试全用内存 sqlite）
- 台账：V3-FIX-417 P2（wt713 登记 / wt719 复核 CONFIRMED）→ **FIXED@df51a731**

## 1. 根因（与台账/wt719 复核一致，逐条亲证）

- `should_retry`（error_handler.py）按 error_message 关键词匹配，三类幂等闸门拒绝
  （IdempotencyConflict / IdempotencyArgsMismatch / IdempotencyKeyRequired）全不命中 → 默认 `return True`；
- `handle_tool_error` 修正轮以 LLM 新生成 tool_call_id 重调 `executor.execute_tool_call` 且不带 idempotency_key；
- executor（X-06）`key = idempotency_key or tool_call_id` → 新键无账本行 → 写副作用放行 →闸门拒绝被「洗白」成第二次真执行；
- chat.py 四喂入面全部漏斗进该环：`/task` :583（handle_batch_errors）、`/stream` :804、`/confirm` :935/:967。

## 2. 修法（按复核方向择「排除集」，X-09 同族最小面；chat.py 零改动）

`backend/app/orchestration/error_handler.py`：

1. 模块级 `IDEMPOTENCY_GATE_ERROR_TYPES = ("IdempotencyConflict", "IdempotencyArgsMismatch", "IdempotencyKeyRequired")`；
2. `handle_tool_error`：身份闸（FIX-217 语义原样保留）之后新增早期拒绝——命中排除集即诚实跳过
   （suggestion 追加「幂等闸门拒绝不能用换键重试自动绕过」）并原样返回原始失败。此一处即覆盖全部四喂入面
   （含不经 should_retry 的 `/task` 批量面）与修正轮递归；
3. `should_retry`：对三闸门类恒 `False`（/stream、/confirm 两面的调用点在进 handler 前即短路，语义一致）。

未采「修正轮透传原意图键」方向：问题根源在自动环代行了显式决策（executor X-09 注释自证），排除集是更小且
不需要 chat.py 四面各自配合的正确面。「不重试换键」语义与 X-06/X-09 既有裁决同源。

X-09 既有排除（BudgetExceeded/IdempotencyInterrupted，chat.py :566/:573/:797）语义原样未动。

## 3. 红先行与测试面

- 正式回归钉 `backend/tests/unit/test_v3_fix417_idem_gate_no_launder.py`（9 用例）：
  - e2e 三场景（真 executor 闸门 + 真账本唯一索引 + stub write 工具，场景固化为可长期运行形态）：
    Conflict 在飞（repro 主场景）/ KeyRequired fail-closed / ArgsMismatch；
  - 修前红（7 failed / 2 控制绿）：红签名 = `should_retry` True + 修正轮进入 + fresh 键 `execute_count=2`，
    与 repro_idem_launder.py 及 wt719 复核完全一致；KeyRequired 场景红 = fail-closed 被洗成执行（count 0→1）；
  - 修后绿（9/9）：`execute_count` 恒 1、原始拒绝原样上报（error_type 保留 + suggestion 人话反馈）、
    LLM 修正轮零调用、账本零新开行；
  - 对照组：非闸门失败（ValidationError/read 工具）修正链照常工作（排除集不过宽）、
    `should_retry` 既有语义逐条保留（验证失败重试/默认重试/权限不重试/无错误信息不重试）；
- 原探针 `v3-output/WT713-HUNT1/repro_idem_launder.py` 对修后分支复跑：**GREEN**
  （attempt2 Conflict → entered correction: False → count=1）；
- 邻面既有测试全绿：fix217 自修正身份闸 / fix223 账本归因 / fix40 同事务 / fix53 流式两面 / fix155 EOF 哨兵 /
  x06 闸门本体 / x09 恢复 / failure_semantics / llm_wrapper 签名，共 **183 passed**；
  tool_preference_router + orchestrator_real_engine 共 **47 passed, 4 skipped**。

## 4. mypy / ruff

- 触达文件 `error_handler.py` mypy **0 错**；
- 「合并态 132」口径核对：main 仓 warm-cache 实测 132，worktree 133——逐条 diff 后唯一新增为
  `app/aurora/policy_loader.py:9` types-PyYAML stub 环境类（与本次改动无关，main 仓同文件同内容）；
  **双仓各清 `.mypy_cache` 后 fresh 复跑：逐条 diff 零漂移（两仓均 133，输出完全一致）**，
  即 132/133 差异纯为缓存状态，本任务 mypy 零回涨（与 wt734/420 批次「133=133 环境既有」口径一致）；
- ruff：触达两文件 lint + format 全过。

## 5. 台账与登记

- V3-FIX-417 → FIXED@df51a731（台账行内含修法取舍与验证面全录）；
- 新发现 **V3-FIX-447**（P3，OPEN）：幂等洗白同族残余——IdempotencyInterrupted 在 /confirm 两面
  （chat.py :933/:963）无 X-09 过滤，should_retry 默认 True + 修正轮换键仍可洗成真执行
  （触发链：HITL 首轮崩溃→账本行 interrupted→同 action_id 重放）。417 裁决排除集只含三闸门类、
  X-09 既有面按指令不动，故登记不顺带修；修法方向与触发条件见台账行。**代码审读推理，未运行级复现，如实标注**；
  - 号位：447 在分支基（max=443）与主链（max=451）台账均空闲，448 按指令备用未占；
- `ledger_union_merge.py --verify`：**通过**（314 行 V3-FIX 行，8 裸管形态合法，零冲突标记，ID 无重号，零 FAIL）。

## 6. 提交

- `df51a731` fix(orchestration): wt732 V3-FIX-417 幂等闸门拒绝不进自修正环——error_handler 排除集补三类闸门异常（代码+测试）
- commit 2（本条）：台账 417 FIXED@df51a731 + V3-FIX-447 登记 + 本 notes
- 未 push（铁律）；main 仓只读未动。
