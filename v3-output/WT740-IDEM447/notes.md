# WT740 · V3-FIX-447 修复笔记（IdempotencyInterrupted × /confirm 两面洗白收口）

- 日期：2026-09-27；分支 `agent/node-b/wt740/idem447`（base cbb92145=main）；worktree `/Users/brsama/code/GitHub/Sparkle-sysrev/wt740-idem447`
- 环境：主仓 venv `/Users/brsama/code/GitHub/Sparkle-project/backend/.venv/bin/python`（3.11）；`app/gen` 按先例主仓 `cp -RL` 拷贝不入库；裸 worktree 无 `.env`，pytest 以 `SECRET_KEY=x` 直跑（本任务测试全用内存 sqlite）；探针直跑需 `PYTHONPATH=<worktree>/backend`
- 台账：V3-FIX-447 P3（wt732 登记，当时「代码审读推理、未运行级复现」）→ **FIXED@2d82a628**

## 1. 复现（任务指令：先复现再修——RED 成立，wt732 定性运行级坐实）

沿 417 测试形态 + x09 interrupted 行构造（`test_x09_failure_recovery.py` 的内部 commit 桩 +
`_ledger_session_factory` 注入），全链真 executor：

1. attempt1（HITL 首轮 confirm）：持意图键 `hitl:{action_id}:{tool}` 执行，内部 commit 后崩溃
   → X-09 两阶段收敛把账本行置 `interrupted`（execute_count=1）；
2. attempt2（用户重放同 action_id）：同意图键 → `IdempotencyInterrupted` 恒拒（闸门本体正确）；
3. /confirm 面（chat.py :963 形态漏斗）：`should_retry(r2)` → **True**（Interrupted 错误文
   「was interrupted ... retrying requires a NEW idempotency key」关键词全不匹配走默认）→
   `handle_tool_error`（修正 LLM 桩回同工具新 id）→ executor 以 fresh 键放行 → **洗白**。

- 探针 `v3-output/WT740-IDEM447/repro_idem447_confirm_launder.py` 修前实录：
  `entered correction: True / final success=True / execute_count=2 / 账本 2 行（interrupted + fresh succeeded）`
  → **RED（VERDICT 行自判）**；
- 正式回归钉 `backend/tests/unit/test_v3_fix447_idem_interrupted_confirm_no_launder.py`
  修前 **4 failed / 2 控制绿**（红签名：should_retry True + 修正轮进入 + fresh 键新账本行）。

无 REFUTE：未被任何层拦住——`_find_ledger_row` 的 populate_existing 让重放如实看到 interrupted 行
并恒拒（这半边是对的），但拒绝体一进 /confirm 漏斗即被修正环换键洗掉。

## 2. 修法（与 417 同面统一：排除集并入第四类，chat.py 零改动）

`backend/app/orchestration/error_handler.py`：

1. `IDEMPOTENCY_GATE_ERROR_TYPES` 并入 `"IdempotencyInterrupted"`（三闸门类→四类）——
   Interrupted 本就是 executor 幂等闸门的第四类拒绝（executor.py :571-583 X-09 interrupted 分支），
   语义同源：同键重放恒拒 + 重试换新键是显式决策不由自动环代行；
2. `handle_tool_error` 早期拒绝（417 已有闸）对 Interrupted 命中；suggestion 按 Interrupted
   **差异化话术**：「本键永不重执行；重试必须显式决策并使用新幂等键」——三闸门类的
   「请等待在途调用结束后显式重试」对中断键不适用（在途永不结束）；
3. `should_retry` 排除集短路随之恒 False——/confirm 两面（:933/:963 同一
   `should_retry + handle_tool_error` 漏斗，单工具面收口即两面同批收口）不进修正环。

**统一 vs 分面裁决（任务评估点）**：把 Interrupted 加进排除集对 /stream **语义零影响**——
/stream（:797 行内过滤）与 /task 批量面（:566/:573 过滤集）已在漏斗**前**排除 Interrupted
（standard_workflow.py :3921 同），排除集扩展对这三面不可达 = 纯纵深防御；故择统一、不分面。
未采「/confirm 补 :797 行内过滤形态」：BudgetExceeded 在 /confirm 面不可达（该面
`execute_tool_call` 不传 `runtime_context` → 无 run 行 → executor 预算闸门 :588 `if run_row is not None`
整段跳过），行内过滤唯一新覆盖只剩 Interrupted，而排除集一处即覆盖且与 417 修法同面——最小且一致。

## 3. 测试面（红→绿）

- `tests/unit/test_v3_fix447_idem_interrupted_confirm_no_launder.py` 6 用例（修前 4 红 2 控制绿 → 修后全绿）：
  - e2e 主场景（真 executor X-09 两阶段收敛 + 真账本）：HITL 首轮崩溃→interrupted 行→同 action_id
    重放恒拒→/confirm 漏斗；绿=should_retry False、LLM 修正轮零调用、execute_count 恒 1、
    原始 IdempotencyInterrupted 原样上报（suggestion 含「自动修正已跳过」）、账本零新开行；
  - 计划面（:933 `__plan__` 循环）同漏斗钉；should_retry 逐类钉（Interrupted False）；handler 直证
    （suggestion 含「新幂等键」显式决策话术）；对照×2：干净回滚失败（side_effect_state=none）照常
    进修正环并重试成功（排除集不过宽的运行级证明——修前修后都绿）、暂态失败 should_retry True；
  - 账本读用 fresh-session 裸读（x09 同款）：两阶段收敛独立会话提交，调用方会话 identity map
    （expire_on_commit=False）不自动失效；
- 探针修后复跑 **GREEN**（entered False / count=1 / 账本零新开行）；
- 邻面全绿：417 既有 9 用例 + x09 恢复 + fix217/fix223/fix40/fix53×2/fix155 + x06×2 +
  failure_semantics + llm_wrapper + fix336 = **229 passed**（一条命令 220 + 417 侧 9）。

## 4. mypy / ruff

- 触达 `error_handler.py` + 新测试文件 mypy **0 错**（依赖图 67 错均既有、触达文件外）；
- fresh-cache 双仓（main vs 本分支）`mypy app` 全量 **133=133**，逐条 diff **零漂移**；
  与 wt732 批次「132=warm 口径 / fresh 双仓 133 一致」口径相同（环境 yaml-stub 类既有）；
- ruff：触达两文件 `check` + `format --check` 全过（新测试文件 format 一次后复验过）。

## 5. 台账与登记

- V3-FIX-447 → **FIXED@2d82a628**（台账行内含修法裁决/复现升级/验证面全录；
  wt732 登记时「未运行级复现」标注就此闭合）；
- **新发现：无**——463/464 grep 复核空闲（445 后 449/451 已占，452+ 未用），本任务未占用；
  范围外观察不占号留档：/confirm 响应 `status:"executed"` 字样对含拒绝 results 的语义性措辞
  （全部失败类共有的既有形态，非缺陷；如需产品级措辞调整另立卡）；
- `ledger_union_merge.py --verify`：**通过**（零 FAIL，见下）。

## 6. 提交

- `2d82a628` fix(orchestration): wt740 V3-FIX-447 IdempotencyInterrupted 不进自修正环——排除集并入第四类幂等闸门拒绝（代码+测试+复现探针）
- commit 2（本条）：台账 447 FIXED@2d82a628 + 本 notes
- 未 push（铁律）；main 仓只读未动。
