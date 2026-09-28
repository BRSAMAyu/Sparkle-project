# V4-I10｜diff_or_evidence_only

**结论：DIFF（实现卡，基线 c67e45a3，产品代码 4 文件 +334/−31，新增测试 1 文件）**

## 做了什么（按 B06 三缺陷 + 验收三项）

### 靶2｜estimate_cost 未知键静默按 gpt-4 错价（token_tracker.py L518-519）

- 新增模块级单一核价权威 `estimate_model_cost_usd(prompt, completion, model_key) -> float | None`（`backend/app/orchestration/token_tracker.py`）：router 注册价 → 显式 legacy OpenAI 键 → **None（未核价 unknown）**。未知键/计量标签（`no_generation_model`/`unattributed_model`）绝不静默回落 gpt-4（B06-A4：42tok→$0.00126 错价路径删除），也绝不填 0 冒充免费；未核价键进程内告警一次（去重）。
- `TokenTracker.estimate_cost` 返回类型 `float → float | None`，委托单一权威；两处既有调用面（response_builder cleanup/run_ledger）同步 None 语义。
- `record_usage` 新增 additive 参数：`usage_source`（"measured"/"estimated"，降级计量显式化）、`sub_calls`（根请求调用树子调用切片）。随 billing 队列/Redis 明细行透传，DB 插入映射不变（向后兼容）。

### 靶3｜「带 token 的 no_generation_model」检出器缺失（V3 FIX-545 终结面）

- 新增 `METERING_MODEL_DEGRADED_ESTIMATE = "no_generation_model_estimated"` 与纯函数检出器 `bisect_no_generation_with_tokens()`（`backend/app/orchestration/response_builder.py`）：带 token 的 no_generation_model → 显式降级计量标签；0-token → 保持真无模型。标签二分 = 两形态分别可查，**不混桶、不静默改标签让缺陷面消失**。
- 检出计数器 `sparkle_metering_no_generation_with_tokens_total{surface}` 挂满 3 处判定面：cleanup（产生面，B06 §4.5 合成估算时序）、final_response_metadata、run_ledger（后两处为实测口径防回归挂面）；检出时同步 warning 日志（含 request_id 与 token 数）。

### 靶1｜cost_micro_usd=0 回执 vs 内部账不一致（B06-T1/T2）

- `backend/app/agents/standard_workflow.py` usage 帧回执：新增 `_build_usage_receipt()` 与内部账共用 `estimate_model_cost_usd`（同键同价同 token）→ 可核价时回执 `cost_micro_usd` = 内部账口径，两账统一；不可核价时回执 0 + 同帧 metadata `usage_cost_unpriced=true` 显式标记（wire 格式无法表达 unknown，以显式标记替代「0=免费」假语义）。proto 零变更。

### 靶4｜根请求全调用计量（B06-T3 rescue 双调用失真）

- rescue 链真实二次上游调用入根请求账：`_meter_generation_rescue_subcall()` 在 `_build_mode_rescue_response()`（新增可选 `state` 参数）成功后按 tiktoken 估算（非流式 `chat()` 无 usage 帧，`usage_source=estimated` 不冒充实测），累计写 `context_data["rescue_metering"]`；4 处 rescue 调用点全部接线。
- `_cleanup` 折算：rescue token 并入根请求行；主生成无实测帧时整行归因到真实成功面（rescue 模型/层，lane/model/tier 与实际一致，不再错挂失败的主生成选择）；主生成有实测帧时归因不变、rescue 开销以 `sub_calls` 独立切片（验收 3「独立开销可切片」）。
- 未核价可见性计数器 `sparkle_metering_unpriced_usage_total{surface}`、rescue 子调用计数器 `sparkle_metering_generation_rescue_calls_total`（`backend/app/core/metrics.py`）。

### 验收 2 其余面（重放幂等 + 原子 reserve/settle）

- 重放不重复结算：`token_usage.request_id` 既有唯一约束 + `_retry_individually` 跳过重复，sqlite 实库测试锁定；未核价落库 NULL ≠ 0（`cost` 列本就 nullable，billing_worker None 直传）。
- 原子 reserve/settle：既有 `LLMCostGuard._reserve_usage_atomic`（Redis Lua，`app/core/llm_quota.py`）+ `record_usage` settle 面举证满足，本卡不重建（`no_duplicate_rule`）。

## 验收逐条

1. **7 条已知错挂案例被检出且不再靠改 label 消失**：PASS（机制面）。产生机制（合成估算发生在归因判定之后）已终结：检出器 + 专用标签 + 计数器，`test_cleanup_synthetic_estimate_detected_and_relabeled` 端到端红绿锁定。S06 原始 7 条为 V3 历史样本，本卡零真模型约束下以可失败单测锁定检出机制，不重跑真链。
2. **未核价 unknown 不填 0，重复重放不重复结算**：PASS。None/NULL 语义 + sqlite 实库两测。
3. **并发预算原子 reserve/settle，独立开销可切片**：PASS（差量举证 + 增量切片）。

## 边界与不变式

- 纯 backend；零 HEAVY；全部测试 mock/stub/sqlite，0 次真实上游模型调用。
- proto 零变更（`metadata` map 与 `cost_micro_usd` 均为既有字段）；无 DB 迁移；无生成代码改动；`app/gen` 为 worktree 本地 `make proto-gen` 产物，不入库。
- V3 路径与数据向后兼容：`estimate_cost` 对可核价键行为不变（legacy 键/注册键价目原样）；`resolve_metering_model_key` 三分语义不变（回归守卫测试）；V3-FIX-80 标签继续存在，仅带 token 形态二分出独立标签。
- 回滚：单 commit 可整体 revert；无开关依赖（新增路径由 context_data 槽位驱动，rescue 不发生时零行为差异）。
