# FIX-573 独立审查 receipt（r1）— 引擎计量缺陷族（Q04 红项①②产品面闭环）

审查人：wtF573R1（独立会话，未参与 FIX-573 修复）｜日期：2026-09-29｜时区 +0800
被审对象：分支 `fix/v4/f573-metering` 代码 commit `105900e7` + 证据 commit `645c5372`（基线 `39553c6a`，审查时工作树干净）
方法：只读审查 + 亲跑复现（mutation 亲放、探针实证，探针用后即删）

## 裁决：**PASS_WITH_CHALLENGES**

两缺陷根因链成立、修法方向正确、Q04 红项①②主形状被确定性收口、I10 契约演进合规、不造第二计量权威成立。挑战三项（C-1 时序边界、C-2 超时路径残留、C-3 证据数字不实）不阻塞本卡过点，但 C-1/C-2 须在台账留痕并留待后续观测/收敛。

## 1. 根因链复核（首靶）— 均 **成立**（亲读基线与修后代码）

**缺陷①（no_generation 带 token）**：基线 `_cleanup` 判定先于估算亲读确认——`resolve_metering_model_key(context_data, has_real_usage=实测帧>0)`（基线 L1686-1690）先于合成估算块（基线 L1760-1778），无模型键回填（`standard_workflow.py:2083-2089` 仅 generation 节点 `selection` 非空时写 `generation_model_key/model_used`，亲读确认）→ `no_generation_model` + 估算 token>0 → bisect 二分为 `no_generation_model_estimated`。与 Q04 三行 216/216/277、无 usage 帧、77-112s 首 delta 形状吻合（`V4-Q04/review_r1.md` §2 归属表亲读核对）。

**缺陷②（取消轮次记账归零）**：基线 `_execute_graph` 的 `total_prompt_tokens/total_completion_tokens` 为生成器局部变量（基线 L1949-1950），仅在图正常完成后写 `result_holder`（基线 L2014-2016）；基线 `except GeneratorExit: graph_task.cancel(); raise`（L2017-2019）无任何收据回收——局部累积随生成器闭合同丢失。orchestrator finally 以 0/0 + `final_state=None` 进 `_cleanup` → `no_generation_model/0tok`。Q04 L2-CANCEL t=20.366s usage 帧 13,320 tok/$0.001332 早于 delta+取消（帧已消费后取消）实锤核对一致。

## 2. 修法行为面 — **成立**，附 C-1 时序挑战

- 缺陷①改桶（非归零）：`unattributed_model` 语义亲读确认恰为「有真实用量、模型键未知」（response_builder.py L47-48 + `resolve_metering_model_key` docstring，V3-FIX-80 既有语义）。诚实性核验：`usage_source=estimated` 降级如实保留；`cost=None` 未核价亲读确认（`token_tracker.py:555-573` → `estimate_model_cost_usd` 对计量标签含 `unattributed_model` 返回 None，`METERING_UNPRICED_USAGE` 可见计数）——真实成本不因改桶消失也不按 gpt-4 错价。
- 缺陷②三段亲读确认：(a) usage 帧消费即时落 `result_holder`（execution_engine.py，覆盖超时/图取消分支）；(b) GeneratorExit 排空已入队收据；(c) orchestrator finally `max()` 恢复 + 仅实际补账时 `METERING_CANCEL_RECEIPT_RECOVERED.inc()`（正常完成路径 L3851-3852 本就从 result_holder 取值，不误计）。上下文兜底亲读确认（`statechart_engine.py:243` `state = initial_state` 同对象；generation 节点 LLM 调用前回填模型键）。
- 排空语义边界亲核：排空仅取队列存量 usage 帧（不入队心跳帧，无双计）；`queue.task_done()` 不补调（全仓无 `queue.join()` 消费方，无悬挂风险）；取消后产生、未及入队的帧归零（与任务口径一致）。

**C-1（时序边界，挑战）**：生产链下「已入队未消费」收据的排空不与 finally 同步。实证探针（亲放亲删）：模拟 `agent_grpc_service` 的 `aclosing(process_stream)`（agent_grpc_service.py:492-537 亲读确认 aclosing 只包 process_stream，不包内层 `_execute_graph` agen）→ 帧1 已消费（即时落账）→ 帧2 已入队未消费 → break+aclose → **finally 恢复时点 holder=1100/13320（仅已消费帧）**；内层 agen 经 GC 终结排空后 holder 才到 1110/13340——排空值无人再读，本回合不入账。即：**确定性入账面=已消费帧（恰好覆盖 Q04 红项②主形状 13,320 已消费帧，主诉成立）；「已入队未消费」收据的恢复仅在测试的显式 aclose 时序下成立**。manifest `reproduction_vs_fix.defect_2.after` 的「排空(+10/+20) → finally 恢复」顺序在生产接线不成立，honesty_boundaries 未覆盖此点。建议后续：finally 内显式排空 queue 或对内层 agen 显式 aclose 后再恢复。

**C-2（超时路径残留，挑战）**：超时 break 路径不经过 GeneratorExit——队列中已入队未消费的 usage 帧被 RB-02 `_drain_queue` 冲洗给客户端但不入账（`observability_mixin.py:165-212` 亲读确认 `_drain_queue` 不累计 token）。与 C-1 同族，量级更窄。

## 3. I10 契约演进合规 — **成立**

`test_cleanup_synthetic_estimate_detected_and_relabeled` 落桶断言 `METERING_MODEL_DEGRADED_ESTIMATE → unattributed_model` 属任务令「该形态改记正确桶」的必然结果，docstring 注明缘由；**断言加强非削弱**：tokens>0 / `usage_source=estimated` / `cost=None` 全保留，新增改挂计数断言。检出防线亲核：`bisect_no_generation_with_tokens` 函数基线↔修后 **byte-identical**（diff 亲核）；3 个 bisect 契约测 + 0-token 真无生成测 + measured 放行测原样全绿。**mutation 实证防线未失能**：外科手术式移除改挂块后，该 I10 契约测与两个 f573 缺陷①测同红（3 failed），FIX545 检出日志复现基线形状。

## 4. 不造第二计量权威 — **成立**

`token_tracker.record_usage` 全仓调用面仅 `_cleanup` 一处（response_builder.py:1841）；execution_engine/orchestrator 改动只搬运数字（result_holder/局部变量 → finally 传参），账仍走 `_cleanup → TokenTracker → BillingWorker` 单链。

## 5. 回归与数字 — **全绿成立，三项数字不实（C-3）**

| 面 | manifest 声称 | 亲跑结果 | 裁决 |
|---|---|---|---|
| `test_v4_f573_metering_fixes.py` | 7/7 绿 | **7/7 绿**（0.7-0.9s，同命令同环境） | 一致 |
| I10+归因+I09+心跳+billing 批 | 96 绿（24/8/50/7/7） | **89 绿（19/7/49/7/7）**，collect-only=passed，无 skip | **数字不实**，全绿方向不变 |
| orchestrator 相邻 8 文件 | 61 绿 | **61 绿**（83.75s） | 一致 |
| 合计 | 157 | **150** | **数字不实** |
| mypy 四文件 | 修后 37 vs 基线 39 | **修后 37 vs 基线（同法）37** | 零新增成立；基线 39 不复现（疑环境/版本差） |
| ruff 六文件 | 零违例 | **All checks passed** | 一致 |
| black | 基线 4 文件 would-reformat（既有漂移） | **基线 4/4 exit=1（black 26.3.1 亲核）**；修后 3+1 | 声明成立（初核误读 pipeline 退出码已纠正重核） |

**mutation 亲放**（非声称复述）：①外科手术式注释改挂块（保签名）→ 3 红（`test_q04_red1_shape_lands_unattributed_not_no_generation`、`test_q04_red1_original_shape_is_red_invariant`、I10 契约测；`test_q04_red1_real_key_estimated_row_untouched` 绿=行为不变守卫有效）→ 复绿 7/7；②revert execution_engine+orchestrator → `test_q04_red2_cancel_keeps_frame_receipts` 红在确切缺陷形状（`{}.get`——result_holder 空、收据丢失）→ 复绿 7/7。全文件 revert 的 TypeError 噪声与 manifest「新签名不可调用」口径一致。

## 6. Q04 红项形态对照 — **一致**

修前形状（基线亲读 + mutation 反例复现）与 `V4-Q04/review_r1.md` §2 归属表吻合：红项①三行 `no_generation_model_estimated` 216/216/277；红项② L2-CANCEL 13,320 tok 帧级收据（已消费）终态 0tok。修后：①同输入落 `unattributed_model`+estimated+cost=None；②已消费帧确定性入账 + measured + `success=false` 成本照记（测试断言与形状逐项对应）。

## 边界注记（不阻塞）

- checkpoint 恢复轮（`_merge_checkpoint_state` → `fresh_state.clone()`，statechart_engine.py:393-421）被取消时，context 兜底取的是 orchestrator 侧 fresh state，可能缺恢复期写入的模型键 → 落 `unattributed_model`（诚实桶），可接受。
- 台账 `v3/06_agent_fleet/DYNAMIC_ISSUES.md` L451 FIX-573 行为 OPEN（登记态），与缺陷描述一致；销账属 fleet state 流程不在本审查范围。

## 探针清单（用后即删）

1. 外科手术 mutation（response_builder 改挂块注释）— 已还原，`git status` 干净
2. mutation ②（execution_engine+orchestrator revert）— 已还原
3. 生产链时序探针 `tests/unit/test_probe_timing_573.py` — 已删除
4. mypy 基线对比（4 文件 checkout 39553c6a → 跑 → 还原）— 已还原
5. black 基线对比（临时文件 /tmp）— 已删除
6. `.venv` symlink（指向主检出，工作树原无）— 已摘除

## 裁决口径

PASS_WITH_CHALLENGES：C-1/C-2 为修法边界（主形状已确定性收口、残余面窄且方向诚实——不会少记已消费成本，只会漏记极端时序下的已入队未消费帧），C-3 为证据数字纪律问题（不实数字须在后续 manifest 修订或台账勘误中订正：96→89、157→150、mypy 基线 39→37 同法）。建议 C-1/C-2 登记后续观测项（`sparkle_metering_cancel_receipt_recovered_total` 与生产取消轮账面对照），不阻塞本卡销账。
