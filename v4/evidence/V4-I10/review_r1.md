# V4-I10 一审 receipt（独立审查 R1）

- 审查会话：wtI10R1（未参与 I10 实现）
- 审查对象：分支 `agent/v4/i10` @ `2ad27c96f9d916902262bb518d6d322935e87b23`（基线 `c67e45a3`）
- 审查日期：2026-09-28 ｜ 方式：只读审查 + diff 全量核对 + 测试/静态检查独立复跑（零真模型，未烧预算）
- **总裁决：PASS_WITH_CHALLENGES（有保留通过）**——三靶闭环全部代码级核实、复跑全绿、零变更声明属实、limitations 如实；3 项记录性 CHALLENGE（R1-C1/C2/C3），均不阻塞集成。

## 1. 三靶闭环核验（逐靶读接线，全部属实）

**靶1｜两账统一核价权威——属实。**
- 内部账：`response_builder.py` `_cleanup` L1800-1805 经 `token_tracker.estimate_cost` → 委托 `estimate_model_cost_usd`（token_tracker.py L555-559，diff 实证）；run_ledger 面 L1476-1481 同权威。
- 回执：`standard_workflow.py` `_build_usage_receipt()`（L895-917）直接调用 `estimate_model_cost_usd`；流式 usage 帧接线 L2205-2228，`cost_micro_usd=receipt_cost_micro` 与 `metadata=receipt_meta` 挂在**同一个 ChatResponse**。unknown → 回执 0 + 同帧 `usage_cost_unpriced="true"`，wire 零变更（`Usage.cost_micro_usd` proto/agent_service.proto:752、`ChatResponse.metadata` map :790 均既有字段）。
- 回执模型键 `state.context_data["generation_model_key"]` 在流循环启动前回填（L2043-2049），先于 usage 帧到达，与内部账 `resolve_metering_model_key` 的首选取键在实测帧路径一致；selection 为 None 时两账同落未核价（回执标记 / 账本 `unattributed_model`→None），无新增不一致面。
- 网关透传抽验：`gateway/internal/handler/chat_orchestrator_protocol.go` L159-165 转发 `cost_micro_usd`，L83-84 metadata map 通用转发。

**靶2｜gpt-4 回落删除——属实。**
- diff 实证：原 L518-519 `if model not in pricing: model = "gpt-4"` 整块删除，替换为模块级 `estimate_model_cost_usd`：router 注册价 → 显式 legacy 三键（gpt-4/gpt-4-turbo/gpt-3.5-turbo）→ **None**。计量标签（no_generation_model/unattributed_model）与未知键绝不回落、绝不填 0；未核价键进程内告警一次（`_UNPRICED_MODEL_WARNED` 去重）。`estimate_cost` 返回类型 `float → float | None`，三处调用面（cleanup/run_ledger/receipt）None 语义同步。

**靶3｜FIX545 终结面——属实。**
- 纯函数检出器 `bisect_no_generation_with_tokens`（response_builder.py L77-100）：带 token 的 `no_generation_model` → `no_generation_model_estimated`，0-token 保持原标签，真实键放行。
- 三判定面接线核实：①`final_response_metadata`（L1010-1020，实测口径理论不可达，防回归挂面）；②`run_ledger`（L1471-1481）；③`cleanup` 产生面（L1762-1780，含 request_id warning 日志）。计数器 `sparkle_metering_no_generation_with_tokens_total{surface}` 三面齐全（metrics.py diff 实证）。
- **既有 resolve 语义未动**：`resolve_metering_model_key` 函数体零 diff；FIX-80 守卫在位——既有 `tests/unit/test_metering_model_attribution.py` 7 测（V3 a1587328 后未被本卡触碰）+ 新增 `test_resolve_metering_semantics_unchanged`，一审复跑 7+1 全绿。
- run_ledger 面 `estimated_cost` 0.0→None 进 event metadata（JSON null），无格式化崩溃面；`billing_worker` cost None 直传落 NULL（`record.get("cost", 0.0)` 键存在时返回 None，sqlite 实测锁定）。

## 2. rescue 计量正确性（属实，防双计成立）

- **计量面**：`_meter_generation_rescue_subcall`（standard_workflow.py L850-897）在 `_build_mode_rescue_response` 成功后按 tiktoken 估算（`estimate_tokens` = tiktoken encode，context_pack.py L114-123），累计写 `context_data["rescue_metering"]`；4 处 rescue 调用点全部接线 `state=state`（diff 实证），`METERING_GENERATION_RESCUE_CALLS` 只在发生面计数、cleanup 折账不重复计数。
- **折算防双计**：`_cleanup` 中合成估算仅当折入 rescue 后 `prompt_tokens<=0 AND completion_tokens<=0` 才触发——rescue 已计 token 时原主生成合成估算被排除（`test_cleanup_folds_rescue_subcall_and_attributes_truthfully` 断言总量恰为 120+60=180，无叠加）。主生成实测帧与 rescue 估算是加法聚合（部分消耗+替换消耗），非双计。
- **归因真实性**：主生成无实测帧（T3 形状）→ 整行归因 rescue 模型/层（lane/model/tier 与实际一致）；有实测帧 → 归因不变、rescue 入 `sub_calls` 切片。两形态均有测试锁定。
- **state 接线**：StateGraph 线性路径返回同一可变 state 对象（statechart_engine.py L497 return state；并行分支经 `_merge_context_data` 合并），`rescue_metering` 槽位可靠到达 `final_state.context_data`。
- **重放幂等约束真实存在**：`app/models/chat.py:150` `request_id` nullable=False unique=True（既有约束，本卡未改 schema）；`billing_worker.py` L226-227 撞唯一约束逐条跳过；`test_billing_replay_same_request_id_settles_once` sqlite 实库两份同 id 重放 → count==1。

## 3. proto/迁移零变更声明（属实）

- `git diff c67e45a3..2ad27c96 -- proto/` = 空；commit 11 文件全量核对无 proto/alembic/`*/gen/`/schema.sql；`cost_micro_usd`/`metadata` 均既有 proto 字段（行号见上）。无 DB 迁移，`token_usage` 表结构未动。redline_check 七项与实物一致。

## 4. 独立复跑（一审本机实跑，非转抄）

| 面 | 结果 |
|---|---|
| 新 19 测（test_v4_i10_metering_truth.py） | **19 passed**（含 `test_estimate_cost_unknown_key_returns_none_not_gpt4_price`） |
| FIX-80 既有守卫（test_metering_model_attribution.py） | 7 passed |
| test_billing_worker.py + tests/orchestration | **215 passed**, 7 warnings（与申报 208+7 一致） |
| ruff（app/ + 新测试） | All checks passed |
| mypy 4 文件 scope | base/HEAD 各 **31 条**，错误集合 diff 为空（临时 worktree @c67e45a3 独立对照）——零漂移独立复现 |
| mypy standard_workflow scope | base/HEAD 各 **30 条**——零漂移独立复现 |

（相邻计量面 1086 与 agents 5 未逐套复跑，抽样面全绿 + 静态检查零漂移支持其可信；phase5 北极星 1 skipped 与申报一致未复跑。）

## 5. limitations 8 项定性（逐项核对，全部如实、无掩盖）

1. M6 第二账本未收敛——属实：`llm_security_wrapper._record_usage`（L274-280）仍独立估算记账，无 root_request 关联。
2. rescue token 为估算——属实：非流式 `chat()` 仅返回 str（llm_client.py L262-283），usage 不外暴露。
3. 失败轮 provider 侧消耗不可测——属实且为 B06-T3 同源限制，如实保留。
4. fallback 逐 attempt 用量不可切片——与 `execute_with_fallback`（services/llm/fallback.py:522）返回面一致，属实。
5. reserve/settle 差额回补未实现——属实：`llm_quota.py` L566/579 `check_only=True`（reserve 休眠）、L570 `model="gpt-4"` 硬编码标签（M5）确未改；Lua 原子脚本在位，申报"未重建"成立。
6. S06 7 条样本未真链重放——属实，且明确口径为"机制面锁定"（见第 6 节裁决）。
7. 回执标记下游 UI 未验证——属实，网关透传已抽验，UI 消费如实留待后续卡。
8. `get_total_stats` 硬编码 gpt-4/gpt-3.5-turbo——属实（token_tracker.py L523-551），未顺手改符合最小增量。
- "既有失败/漂移"（mypy 31+30、warnings、1 skipped）与一审复跑实测一致。

## 6. 验收三条裁决

1. **7 条错挂检出且不靠改 label 消失**：PASS（机制面口径）。产生机制（合成估算后于归因判定）在 cleanup 判定面 3/3 被二分检出 + 计数 + 红绿测试端到端锁定；"不靠改 label 消失"由「显式新标签 + 三面计数器 + warning 日志」满足——标签改写是显式可查的检出动作而非隐匿。真链重放以 limitations 6 如实披露，零真模型红线下不降低验收实质。
2. **未核价 unknown 不填 0、重放不重复结算**：PASS。None/NULL 语义 + sqlite 实库两测 + 唯一约束实证。
3. **原子 reserve/settle、独立开销可切片**：PASS（差量举证 + 增量切片）。既有 Lua 面举证成立；rescue `sub_calls` 切片为可失败测试锁定的本卡增量。

## 7. CHALLENGES（记录性，不阻塞集成）

- **R1-C1（混合场景行级语义）**：主生成有实测帧 + 替换型 rescue（泄漏/低信息路径）时，行级 `usage_source` 仍为 "measured"，而行 token 总量含估算的 rescue 部分；行级 cost 以主模型单价折算整行 token（含 rescue），rescue 切片存在价差。`sub_calls` 已披露 estimated 切片（model_key/tokens/usage_source 齐全），归因不失真，但行级标签无 "mixed" 形态、切片无 per-slice 核价。建议后续收敛卡：行级 source 组合语义 + sub_calls 逐切片核价。不阻塞。
- **R1-C2（测试环境耦合）**：`test_cleanup_measured_row_real_key_passes_bisect` 依赖真实 router 注册表（`dashscope_chat` 注册价断言 cost 非 None）；注册表条目变动会带动该测试。属"价目真源"耦合（fail-loud 方向），可接受，记录知悉。
- **R1-C3（微观察）**：`_UNPRICED_MODEL_WARNED` 进程级去重集合无淘汰，按不同未知键数无上界增长；量级极小，不要求整改。

## 8. 裁决与后续

- I10 `implementation_state=REVIEW_READY` 证据实质成立；本 receipt 为一审（R1）依据。高风险卡需 2 份独立审查——R2（含集成 SHA 复验）完成后由协调面落 `review_receipt.json` VERDICT 与 DONE_REVIEWED。
- R1-C1 建议路由为后续计量收敛卡候选（不新建义务，由协调面裁量）；R1-C2/C3 随本 receipt 存档即可。
- 本审查未 push、未改产品代码、零真模型调用；基线对照经临时 worktree 已清除。

—— wtI10R1，2026-09-28
