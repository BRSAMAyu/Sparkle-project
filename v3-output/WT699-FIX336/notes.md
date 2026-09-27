# WT699 · V3-FIX-336 修复实录（per-tool-call 幂等键意图稳定）

- 工位：wt699 ｜ 卡：V3-FIX-336（P2，wt631 猎缺登记、wt634 round-2 CONFIRMED 含运行级实证）
- worktree：`/Users/brsama/code/GitHub/Sparkle-sysrev/wt699-idem`，分支 `agent/node-b/wt699/idem`（base main `36fddd4e`）
- 日期：2026-09-27 ｜ 方法：台账/产物溯源 → 三处键源对码 → 行为级红测（修前红实录）→ 意图稳定键修复 → 红→绿 + 既有护栏零放松

---

## 1 · 定位证据（对码亲证，wt634 verdicts.md §4.2 三键源逐一复核）

wt634 复验（`v3-output/WT634-VERIFY2/verdicts.md` §4.2）所列三处尝试唯一键源，本次逐一打开亲证：

| wt634 所列 | 本次亲证结论 |
|---|---|
| chat 轨直执行 `standard_workflow.py:2774` `tool_call_id=tc.tool_call_id or str(uuid.uuid4())` | **溯链修正（新发现，登记 V3-FIX-389）**：`_execute_single_tool`（唯一调用点 ：2771）签名收 `tool_call_id` 但**从未转发给 `executor.execute_tool_call`**（:3853-3891 的 kwargs 无 tool_call_id/idempotency_key），id 只用于 UI 流帧（:3986/:4013）。故 chat 轨 Phase-1 写工具实际恒吃 `IdempotencyKeyRequired`（fail-closed）→ 被 P1 降级包装吞成 `success=True` fallback（`IdempotencyKeyRequired` 不在终态豁免清单 ：3900）。wt631/wt634 把 :2774 当"uuid 回落键源"系误溯——真实通道是**写静默降级**，非 uuid 键翻倍 |
| bridge 轨 `execution_engine.py:252` `bridge_{tool}_{uuid4().hex[:12]}` | 亲证在场（现 ：256）：fresh uuid 每次全新，executor 键回落 tool_call_id → 同 request 重试必翻倍。**这是 336 余下活性 duplicate 通道** |
| 计划轨 `executor.py:1666/:1696` spec.id 与 retry 派生键 | spec.id 恢复轴已由 V3-FIX-335 轨道 A 闭合（FIXED@e1d2fb8d，计划入 checkpoint → 恢复合并计划优先 → spec.id 跨中断稳定）；`{spec.id}:retry:{n}` 是文档化 deliberate design（:1637 docstring：仅 side_effect_state=none 可证明无残留的失败进重试，开新账本行不改写原 id 历史）。本卡不动计划轨 |

wt641 轨道裁决（台账 336 行证据格在案）维持有效：恢复路径轨道 A 严格更强；跨 run 显式重试（mobile 刻意换新 request_id）= 用户显式再执行决策 = 新键为设计语义（X-06「重试必须换新幂等键——那是显式决策」）。本卡产品面裁决：**采纳"轮次锚"意图稳定键（run_id 或 request_id），不升级跨 run 全局意图键**——与该裁决完全相容。

## 2 · 修前红（根证，真实输出）

新测 `backend/tests/unit/test_v3_fix336_intent_stable_idempotency.py`（行为级：chat 轨经真 `tool_execution_node` + sqlite in-memory 真账本；bridge 轨经 mixin 桩捕获到达 executor 的有效键）：

```text
tests/unit/test_v3_fix336_intent_stable_idempotency.py FFF.              [100%]

__ TestChatTrackIntentStableKey.test_same_intent_retry_reuses_key_and_executes_once _
    assert len(rows1) == 1
E   assert 0 == 1
E    +  where 0 = len([])
2026-09-27 18:13:52.901 | ERROR | app.agents.standard_workflow:_execute_single_tool:3929 -
    Tool 'stub_create_task' execution exception: 'NoneType' object is not callable
    （桩修正后第二轮红：IdempotencyKeyRequired——掉落缺陷的直证，见下）

__ TestChatTrackIntentStableKey.test_different_request_is_new_intent_new_key ___
E   AssertionError: new explicit request must be a new execution decision
E   assert 0 == 2

__ TestBridgeTrackIntentStableKey.test_same_request_retry_produces_equal_keys __
E   AssertionError: same request retried in-process must reuse one key,
    got 'bridge_launch_prediction_6aa51a3a8bc4' vs 'bridge_launch_prediction_a6bdd6bc16c3'
========================= 3 failed, 1 passed in 2.11s ==========================
```

- bridge 红 = 336 本体直证：同 request 两次调用两把 fresh uuid 键。
- chat 红（第二轮，桩补 `parameters_schema` 后）＝ `IdempotencyKeyRequired` 恒失败 → 0 账本行 = V3-FIX-389 掉落缺陷直证（写根本没执行，何谈键稳定）。

## 3 · 修复（diff 摘要，4 文件 +66/-1 后又 +缩进修正）

1. `backend/app/tools/metadata.py`（+34）：新增 `derive_tool_intent_idempotency_key(tool_name, arguments, anchor)`——键 = `intent:{锚[:80]}:{工具名[:100]}:{canonical_args_hash}`（≤253 < 列宽 255）。参数经既有 `canonical_args_hash`（键排序稳定 JSON → sha256），字典键序不敏感；**仅当锚点/工具名/参数确实不同时键才不同**；锚点缺失返回 None（调用方回落 tool_call_id 既有语义，绝不制造跨 run 全局键）。
2. `backend/app/agents/standard_workflow.py`（+21）：Phase-1 循环传 `idempotency_key=derive_tool_intent_idempotency_key(..., anchor=run_id or request_id)`；`_execute_single_tool` 新增 `idempotency_key` 形参并**补传 `tool_call_id`**（V3-FIX-389 掉落修复）。tool_call_id 继续承担追踪身份（模型 call id/uuid），幂等键走意图派生。
3. `backend/app/orchestration/execution_engine.py`（+12/-1）：bridge 短路传 `idempotency_key=derive(..., anchor=request_id)`；`bridge_{tool}_{uuid}` 保留作追踪 id。
4. `backend/tests/unit/test_v3_fix336_intent_stable_idempotency.py`（新，8 测）：助手纯函数 4（确定性/键序不敏感、异意图异键、空锚 None、列宽预算）+ chat 轨 2（同 request 两次尝试同键且副作用恰一次、异 request 新键再执行）+ bridge 轨 2（同 request 两调有效键相等、异 request 异键）。

计划轨不动（§1 第三行；恢复轴已闭、retry 派生键是设计）。

## 4 · 修后绿（真实输出）

```text
$ pytest tests/unit/test_v3_fix336_intent_stable_idempotency.py -q
tests/unit/test_v3_fix336_intent_stable_idempotency.py ........          [100%]
============================== 8 passed in 11.61s ==============================

$ pytest tests/unit/test_x06_tool_call_safety.py tests/unit/test_v3_fix223_ledger_gate_attribution.py \
       tests/unit/test_v3_fix335_plan_checkpoint_resume.py -q
======================== 53 passed in 69.08s (0:01:09) =========================

$ pytest tests/unit/orchestrator tests/unit/test_x06_tool_call_safety.py tests/unit/test_v3_fix223_ledger_gate_attribution.py \
       tests/unit/test_v3_fix335_plan_checkpoint_resume.py tests/unit/test_v3_fix336_intent_stable_idempotency.py \
       tests/unit/test_q06_resilience_fastfail.py tests/unit/test_confirmation_gate_messaging.py -q
================== 210 passed, 5 warnings in 87.48s (0:01:27) ==================

$ pytest tests/orchestration -q
======================= 208 passed, 7 warnings in 46.79s =======================

$ pytest tests/unit/orchestrator/mixins/test_execution_engine_mixin.py -q
============================== 10 passed in 1.04s ==============================
```

X-06 同键重放恰一次/异参拒/in-progress 拒/interrupted 拒/并发撞唯一索引 fail-closed 全部原样（53 测护栏零放松）；FIX-335 计划入 checkpoint 10 测零回退。

## 5 · 门禁数字

- mypy：`mypy app --ignore-missing-imports` → **Found 159 errors in 129 files (checked 1384 source files)** —— 基线 159，零回涨。触达文件仅 `tools/metadata.py:154/:160` 两条，与 main 逐字相同（既有，stash 对照亲证）。
- ruff：`/tmp/ruff112/bin/ruff check <4 触达文件>` → **All checks passed!**（测试文件 I001 已 --fix）。

## 6 · 语义边界（如实声明）

- 同 request/turn 内同工具同参的第二次调用（含模型复诵、降级重试、恢复重入）→ 同键重放返回首次结果，不再执行——这是本卡有意的产品语义（DoD duplicate side effect=0 从"单次尝试内"扩展到"单轮次内"）。
- 跨 request（mobile 重试刻意换新 request_id、用户重发同文本）→ 新锚新键，照常再执行——wt641 裁决的显式决策语义不变。
- chat 轨 Phase-1 写工具因 V3-FIX-389 修复**开始真正执行**（此前恒降级 fallback 伪装成功）——恢复 X-06/X-05 设计意图；该路径上线后写能力从"静默不可用"转为"可用且受幂等闸门约束"，属缺陷修复的必然后果而非语义放松。
