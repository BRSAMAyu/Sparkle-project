# FIX-573 修复回执 — 引擎计量缺陷族（Q04 红项①②产品面闭环）

日期：2026-09-29 ｜ 分支：`fix/v4/f573-metering`（worktree `wtF573`，基于 main@39553c6a ⊃ 简报基线 a75a7b99）｜ 代码 commit：`105900e7` ｜ 台账：FIX-573（P2，Q04 验收揪出的产品面缺陷闭环）

证据定性：`v4/evidence/V4-Q04/review_r1.md` §2 四红项归属表——红项①②=产品面（本卡）；③遗留 main-12 行无计量、④queue:billing 双消费者/驻留栈凭据失效=fleet 环境面（另派卡，不阻塞本卡）。

## 红项① no_generation 带 token（L2-r1/r3/r4-08 三行 216/216/277 tok）

**根因（引擎计量面）**：`response_builder.py::_cleanup` 的产生链——
1. `resolve_metering_model_key(context_data, has_real_usage=实测帧>0)`：轮次无 usage 帧 → `has_real_usage=False`，且模型键未回填（回填点 `standard_workflow.py:2083-2088` 仅在 generation 节点 `selection` 非空时写 `generation_model_key/model_used`）→ 判为 `no_generation_model`；
2. 合成估算块随后由 assistant/user 文本估出 216/216/277 token（`usage_source=estimated`）——判定先于估算，行成「no_generation 家族标签 + token>0」自相矛盾形状；
3. FIX545 bisect 检出二分为 `no_generation_model_estimated`——I10 使其**可见**，但底层缺陷仍把 token 计入 no_generation 行。

**修法**（择「改记正确桶」而非「零 token」：真实生成发生过，归零会掩盖真实成本）：估算块后、bisect 前插入改挂——`no_generation_model` + 估算 token>0 → **`unattributed_model`**（既有语义恰为「有真实用量但无模型归因」），新计数器 `sparkle_metering_no_generation_reattributed_total{surface=cleanup}` + warning。`usage_source=estimated` 降级如实保留；计量标签无价目 → `cost=None` 未核价（I10 未知键语义不变）。no_generation 家族行自此恒零 token；FIX545 检出器语义原样保留为回归防线（正常路径改挂后不再触发，再触发=新产生面）。

**边界**：I09 fastlane 0tok 承诺面（deterministic lane 跳估算 → 0 tok 行）不动；I10 bisect 函数契约测原样全绿；I10 cleanup 产生面测 `test_cleanup_synthetic_estimate_detected_and_relabeled` 的落桶断言随任务令「该形态改记正确桶」更新（cost/usage_source/检出防线断言全保留，docstring 注明缘由——契约演进非删断言取绿）。

## 红项② 取消轮次记账归零（L2-CANCEL 13,320 tok 收据被记 0tok）

**根因**：`execution_engine.py::_execute_graph`（修前 L1949-2019）的 `total_prompt_tokens/total_completion_tokens` 是**生成器局部变量**，仅在图正常完成后写入 `result_holder`；客户端取消触发 GeneratorExit，局部累积随生成器闭合同丢失。orchestrator `finally` 以 0/0 + `final_state=None` 进 `_cleanup` → 账面 `no_generation_model/0tok`。Q04 实锤时序：t=20.366s usage 帧 13,320 tok/$0.001332 **早于** delta+取消——取消前已产生的真实成本未入账。

**修法**（取消前已产生的 token 必须入账；取消后的才可归零）：
1. usage 帧消费时**即时落 `result_holder`**（超时路径同受益）；
2. GeneratorExit 时**排空队列中已入队未消费的 usage 收据**再退出（取消前已产生帧必入账）；
3. orchestrator `finally` 从 `result_holder` **恢复收据**入账（仅实际补账时 `METERING_CANCEL_RECEIPT_RECOVERED.inc()`，正常完成路径不误计），并以共享 `WorkflowState.context_data` 兜底模型归因（`statechart_engine.py:243` `state=initial_state` 同对象语义；generation 节点在 LLM 调用前已回填模型键）——取消轮落账从 `no_generation_model/0tok` 变为真实模型键或 `unattributed_model` + measured 收据 + `success=false` 成本照记。

不造第二计量权威：仍走 `_cleanup → TokenTracker.record_usage → BillingWorker` 单链。

## 测试与守卫

| 面 | 结果 |
|---|---|
| 新增 `tests/unit/test_v4_f573_metering_fixes.py` | 7/7 绿（每缺陷一正一反；反例=复现 Q04 原始红项形态必须被拒） |
| mutation 自验（stash 修复跑同套） | 修前 **6/7 红**（5 个缺陷形状测全红 + 1 个新签名不可调用；唯一绿=bisect 语义守卫，按设计）→ pop 复绿 7/7 |
| I10 契约 + 归因 + I09 快慢分层 + 心跳 + billing | 96 绿 |
| orchestrator/stream/_cleanup 相邻 8 文件 | 61 绿 |
| mypy | 37 errors（基线同法 39；门 ≤77；本卡一处新错已修，**零新增**） |
| ruff | 零违例 |
| black | 格式化后对比法：既有代码零新增偏离（仓库基线在 black 26 下本就 4 文件 would-reformat，与本卡无关；差异全落本卡新增区域） |

## 诚实边界

- 本卡为引擎计量面单测闭环；未重跑 Q04 端到端采样（共享库凭据失效面属红项④ fleet 环境卡），端到端效果以下次 Q 线重测为准。
- 红项①「模型键为何未回填」的上游具体触发路径未展开——改挂后无论上游成因如何均落正确桶；上游收敛留待 `sparkle_metering_no_generation_reattributed_total` 观测。
- 取消后才产生、未及入队的 usage 帧不可恢复（无收据即无账）——符合任务口径「取消后的才可归零」。

复核命令（`run_manifest.json` `commands` 节含全部 exit codes）：`cd backend && DATABASE_URL=postgresql+asyncpg://postgres:placeholder@127.0.0.1:5432/sparkle_test <venv-python> -m pytest tests/unit/test_v4_f573_metering_fixes.py -q`
