# 全系统审查·第一轮修复波 — 01 引擎·编排运行时修复记录

- 修复员：1 号（engine-orchestration 切片）
- 工作树：`/Users/brsama/code/GitHub/Sparkle-sysrev/wt1`（冻结基线 `90daac8a`，未 commit）
- 对应审查报告：[01-engine-orchestration.md](01-engine-orchestration.md)
- Patch：[01-fixes.patch](01-fixes.patch)

## 测试环境

`/opt/homebrew/bin/pytest`（python3.11）；`SECRET_KEY` / `DATABASE_URL`（共享 sparkle 库）/ `REDIS_URL` 以环境变量注入。`backend/app/gen` 为指向主仓的 symlink（测试脚手架，未入 patch）。

---

## P1 修复（红-绿证明）

### RB-01 `_build_final_response` 在 `focused_memory` 缺失时抛 UnboundLocalError — 已修复

- **修复**：`backend/app/orchestration/response_builder.py:1147` — 在 `isinstance(focused_memory, dict)` 分支前显式初始化 `semantic_meta = None`。下游 `if semantic_meta:` 对 None 天然容错（falsy 跳过），focused_memory 存在时行为不变。
- **测试**：`backend/tests/orchestration/test_response_builder_semantic_meta.py`
  - `test_build_final_response_survives_missing_focused_memory`
  - `test_build_final_response_still_emits_semantic_gating_when_present`（对照组，focused_memory 存在时元数据照常输出）
- **红**：修复前测试 1 在 `response_builder.py:1155` 精确复现 `UnboundLocalError: cannot access local variable 'semantic_meta'`；对照测试通过（`{}` 是 dict 所以原触发面为 overlay 跳过/DB 不可用场景）。
- **绿**：2 passed。

### RB-02 graph 300s 超时路径不发终止帧、不排空、误记 success、FSM 停滞 — 已修复

- **修复**：
  - `backend/app/orchestration/execution_engine.py:130` — 将 `GRAPH_TIMEOUT_SECONDS = 300` 从方法内局部变量提升为模块常量（纯重构，值不变，使其可观察/可测）。
  - `backend/app/orchestration/orchestrator.py:3459-3490`（process_stream Step 13 之后）— 新增超时出口：`result_holder["timed_out"]` 且无 `final_state` 时，① `_drain_queue` 尽力发已生成内容；② `_update_state(STATE_FAILED, "Graph execution timed out")` 推进 FSM；③ 记 `REQUEST_COUNT status="error"` 与 `COLLABORATION_SUCCESS outcome="error"`（与其他错误出口一致，不再误记 success）；④ yield `finish_reason=ERROR`、`error_code=ERROR_CODE_TIMEOUT`、`retryable=True` 的终止帧后 `return`。语义选择：超时 = 显式 ERROR 终止（retryable），与 C4 错误终止链对齐。
- **测试**：`backend/tests/orchestration/test_orchestrator_graph_timeout.py`
  - `test_graph_timeout_yields_error_terminal_frame_and_fails_fsm`（真实 `_execute_graph` 超时 + 真实 process_stream；断言恰好 1 个 ERROR 终止帧、`ERROR_CODE_TIMEOUT`、FSM=FAILED、`_build_final_response` 未被调用）
  - `test_graph_timeout_drains_already_generated_deltas`（超时前已入队的 delta 必须先于终止帧发出）
- **红**：基线运行 `assert 0 == 1`（超时后 0 个终止帧）。
- **绿**：2 passed。

---

## P2 修复（红-绿证明，测试位于 `backend/tests/orchestration/test_round1_p2_fixes.py`）

### RB-03 usage 事件覆盖而非累加 — 已修复
- **修复**：`backend/app/orchestration/execution_engine.py:1866-1873` — `total_prompt_tokens += item.usage.prompt_tokens`（同 completion）。usage chunk 为单次生成调用用量（`standard_workflow.py:1802-1820` 每次 generation stream 独立上报），多轮工具调用回合需求和。Prometheus `TOKEN_USAGE` 改为按事件自身值 inc，保持原有 per-event 语义不重复计数。
- **测试**：`test_rb03_execute_graph_accumulates_usage_events` — 队列预置 100/20、50/10 两个 usage 事件，断言 holder 汇总 150/30。红：50/10（只剩最后一次）；绿：150/30。

### RB-04 熔断器零样本即按失败率 trip — 已修复
- **修复**：`backend/app/orchestration/circuit_breaker.py:185-190` — 速率熔断前要求最小样本量 `min_samples = max(3, window_size // 2)`；连续失败阈值路径不变。
- **测试**：`test_rb04_single_failure_does_not_trip_rate_breaker`（1/1=100% 不再 trip）、`test_rb04_rate_breaker_trips_after_min_samples`（window=4 时 2 个样本 CLOSED、3 个样本 100% 仍会 OPEN）、`test_rb04_rate_breaker_healthy_window_stays_closed`（8/9 健康窗口不受影响；基线上即通过，属行为保持对照）。

### RB-05 `get_top_users` 对 str key 调 `.decode()` 必然 AttributeError — 已修复
- **修复**：`backend/app/orchestration/token_tracker.py:407-411` — `isinstance(key, bytes)` 判别后取值，兼容 `decode_responses=True/False` 两种客户端。
- **测试**：`test_rb05_get_top_users_handles_str_keys` — str-key 假 redis 下返回正确 Top 榜（基线：AttributeError）。

### RB-06 `_persist_context_plan` 中途 commit 外层共享事务 — 已修复
- **修复**：`backend/app/orchestration/session_state_mixin.py:865-868` — `commit()` → `flush()`。已核实提交所有权在 `app/services/agent_grpc_service.py`（stream 结束统一 `commit`、异常 `rollback`），flush 后由调用方提交，持久性不受影响，恢复"一轮一事务"原子性。
- **测试**：`test_rb06_persist_context_plan_uses_flush_not_commit` — 假 session 断言 `flush` 被调用、`commit` 未被调用。

### RB-07 Tier-3 空摘要静默丢弃中段历史 — 已修复
- **修复**：`backend/app/orchestration/context_pruner.py:144-148` — `_get_summarized_history` 在确有待总结消息（`summary_messages` 非空）但摘要为空白时，退回 `_compress_with_importance(history)` 并 `summary=None`，与异常路径同语义。`summary_messages` 为空（无更早消息）时不触发，避免无谓压缩。
- **测试**：`test_rb07_empty_summary_falls_back_to_compression`（空摘要 → 消息保留数 ≥ 50% 且不再静默截断）、`test_rb07_no_earlier_messages_keeps_full_history`（无更早消息时全量保留）。

### RB-08 规划失败把原始异常文本流给客户端 — 已修复
- **修复**：`backend/app/orchestration/execution_engine.py:2600-2605` — delta 改用 `build_safe_chat_error(e)` 的脱敏文案；保留原提示语前缀"规划失败，使用直接模式"（现有集成测试断言该文案，仅替换 `{str(e)}` 为安全信息）。
- **测试**：`test_rb08_planning_failure_streams_sanitized_message` — planner 抛 `RuntimeError("LEAK internal sql://postgres:secret@db:5432 failed")`，断言 delta 不含原文、降级 direct、`on_failure` 调用一次。红：基线输出原文完整可见。

### RB-09 工具回环后 router 把 ToolMessage 当用户提问 — 已修复
- **修复**：`backend/app/agents/graph/nodes/router.py:75-80` — 新增 `_resolve_router_user_query(messages)`：倒序取最近一条 `type == "human"` 的消息作为语义路由输入；`router_node` 改用该函数。
- **测试**：`test_rb09_router_resolves_last_human_message` — `[human, ai, tool]` 序列解析回 human 消息。红：基线无该函数（报告 RB-09 的 `recursion_limit` 建议涉及 `app/api/v2/agent_graph.py`，不在本切片，列入剩余清单）。

### RB-10 `high_cognitive_load` 参数键冲突（权重当阈值用）— 已修复
- **修复**：`backend/app/orchestration/dual_core_router.py:290` — `self._param("high_cognitive_load", 0.55)` → `self._param("high_cognitive_load_threshold", 0.55)`，与 305 行同键统一。
- **测试**：`test_rb10_high_cognitive_load_precedence_uses_threshold_key` — 注入"high_cognitive_load=5.0（权重语义）"的参数快照，`cognitive_load=0.9` 时 precedence 必须命中 5.0（0.9 ≥ 0.55 阈值）；基线把 5.0 当阈值导致永不触发、precedence=0。

### RB-11 statechart 容量驱逐可淘汰 session_id/user_id 等关键键 — 部分修复（①）
- **修复**：`backend/app/orchestration/statechart_engine.py:28-34,110-117` — 新增 `_CONTEXT_EVICTION_PROTECTED_KEYS` 白名单（session_id/user_id/request_id/workflow_id + 7 个 checkpoint 挥发键），`_merge_context_data` 的溢出驱逐只淘汰未保护的最老键。
- **测试**：`test_rb11_eviction_protects_session_and_runtime_keys`、`test_rb11_eviction_still_drops_unprotected_old_keys`（保护与淘汰能力双向验证）。
- ② `_merge_state` dict 含 `messages` 时整表替换（API footgun）、③ 并行分支按消息相等去重 — **未改动**（行为语义变更影响面大，列剩余清单）。

### RB-12 `update_state` 新建分支未知 kwarg 直接 TypeError — 已修复
- **修复**：`backend/app/orchestration/state_manager.py:200-215` — 按 `dataclasses.fields(FSMState)` 过滤 kwargs 后再构造，与 existing 分支的 `hasattr` 防护对齐。
- **测试**：`test_rb12_update_state_filters_unknown_kwargs` — 新建与更新两条路径传未知字段均返回 True 且状态正确落库。

### RB-13 shadow predictor 裸 create_task 不受管 — 已修复
- **修复**：`backend/app/orchestration/execution_engine.py:2590-2600` — 任务引用保存并经 `self._track_task`（getattr 防御，engine mixin 挂载于 ChatOrchestrator 时可用）登记，异常由 `_track_task` 的 done-callback 记录，避免 GC 回收与 "Task exception was never retrieved" 噪声。
- **测试**：`test_rb13_shadow_predictor_task_is_tracked` — 走通 `_plan_and_validate` langgraph 成功路径，断言 `_track_task` 被调用。红：基线不调用。

### RB-16 sufficiency / goal-quality 短路出口 FSM 停在 INIT — 已修复
- **修复**：`backend/app/orchestration/orchestrator.py:2836-2864` — 两个短路 return 前补 `_update_state(session_id, STATE_DONE, ...)`。
- **测试**：`test_rb16_sufficiency_short_circuit_sets_done`、`test_rb16_goal_quality_short_circuit_sets_done` — 断言 state_updates 中出现 DONE。红：基线停留 INIT。

---

## 未采纳（有据可查的提案否决）

### RB-14 空计划 STOP 后不写幂等缓存 — 提案不采纳
- 审查报告建议在 `_stream_aurora_runtime_v1` 空计划 STOP 帧后补 `return` 跳过 `_cache_response`。实现该修复后，现有绿测 `test_process_stream_aurora_wait_turn_emits_terminal_frame_and_caches_response`（基线即绿、非本波新增）立即变红：它断言空消息**必须**写入幂等缓存。
- 结论：空响应入缓存是 aurora "wait turn" 的有意产品语义——客户端重试时从幂等缓存回放"这轮什么都不说"的决策，而不是重新执行整轮。已回滚该改动，并把该契约固化为测试 `test_rb14_empty_aurora_plan_stop_is_cached_as_wait_turn`，便于后续重新评估时留痕。

---

## 剩余清单（未修，按优先级）

| ID | 内容 | 原因 |
|---|---|---|
| RB-09(部分) | 在 `sparkle_graph.ainvoke` 显式设 `recursion_limit`（涉及 `app/api/v2/agent_graph.py`） | 不在本切片（api 层）；依赖 LangGraph 默认 25 步兜底 |
| RB-11② | `_merge_state` 节点返回 dict 含 `messages` 时整表替换历史 → 改 append 或文档强约束 | 语义变更影响所有节点返回约定，需专门评审 |
| RB-11③ | 并行分支合并按消息相等去重（合法重复消息丢一条） | 同上，行为语义变更 |
| RB-11(杂) | `statechart_engine.py:126` 附近 `asyncio.get_event_loop()`（3.11 弃用告警，dataclass default_factory 场景无 running loop 替代） | 低危，需单独设计 |
| RB-15 | 工具 fallback 伪造 `ToolResult(success=True)` 的下游可见性（`ToolExecutor._resolve_layer_params` 识别 `fallback=True`） | 涉及 tool 执行协议变更，属后续切片/专项 |
| RB-06( follow-up) | 全仓审计其余中途 `commit()` 共享 session 的点 | 本波只修报告点位 |
| 新发现① | `_execute_graph` 超时 `graph_task.cancel()` 只能取消 `task_manager.spawn` 的包装任务（`_await_result`），worker 内实际 graph 协程不被取消、继续跑完（`app/core/task_manager.py:110-135`：worker `await task` 期间不监听 `result_future.cancelled()`） | 超出本波范围；需要 task_manager 提供可取消句柄（app/core 为公共切片） |

## 新发现（报告外，只记录不修复）

1. **`_plan_and_validate` 对 `user_context_payload=None` 不设防**：`backend/app/orchestration/execution_engine.py:2090` `locale = user_context_payload.get("profile", ...)` — langgraph 模式下若上游传入 None 会 AttributeError 并触发 except 降级（掩盖真实原因）。生产主链路当前总是传 dict，属潜伏缺陷。
2. **task_manager 跨事件循环污染（测试基建）**：全局 `task_manager` 单例的队列 worker 绑定首个事件循环，第二个 pytest-asyncio 测试的 spawn 会进入死队列（graph 任务永不执行）。本波 RB-02 测试用 `monkeypatch.setattr(execution_engine_module, "task_manager", ...)` 规避；单测基础设施可考虑提供 fixture 重置。
3. **`logger.error(..., exc_info=True)`（execution_engine.py:2607）为 loguru 无效用法**：loguru 需要 `logger.opt(exception=e).error(...)`（orchestrator.py 的通用 except 即如此），当前写法导致规划异常的堆栈不落日志，只有消息文本。
4. **超时路径不写 episodic error 事件**：新增的超时出口与通用异常出口行为对齐至"drain + FAILED + ERROR 帧"，但未补 `_write_turn_end_episodic_memory(event_kind="error")`（通用 except 有）。语义上超时未必是"错误回合"，留待产品确认。

## 验证汇总

- 新增回归测试：3 个文件 24 个测试全绿
  - `tests/orchestration/test_response_builder_semantic_meta.py`（2）
  - `tests/orchestration/test_orchestrator_graph_timeout.py`（2）
  - `tests/orchestration/test_round1_p2_fixes.py`（20）
- 红-绿证明：`git stash backend/app` 后全部 P2/P3 测试在基线运行，16 failed + 2 passed（2 个通过项为行为保持对照测试），错误内容逐条对应报告缺陷（如 RB-08 基线 delta 含完整 `sql://postgres:secret@db:5432` 异常文本）。
- 回归对比（`tests/orchestration` + pruner + dual-core + t34 + agents 全量）：基线 56 failed / 169 passed → 修复后 37 failed / 199 passed（最终集另含全绿的 tests/agents）；失败集合 diff 确认 **0 个新增失败**，19 个基线失败被本波修复顺带修复；剩余 37 failed + 31 errors 均为报告记载的 v1 基线失败/Redis 认证环境项。
- lint：新增/修改测试文件 black(120) + ruff 全绿；生产文件 ruff 发现数与基线持平（全部为债务台账中的存量项），black 在该 black 版本下基线即不通过（存量）。
