# P1-C 反思提交超时假失败修复（同步推断链出请求路径）

> 基线 f01f4ae8。每日流 R2 定位（daily-flow-eval-r2.md DF-1 残留）：`POST /tasks/{id}/feedback` 三日 26.7s / 0.97s / >30s(503)，D3 网关 30s 超时但 DB 已入库——"客户端失败、服务端成功"的假失败。

## 阻塞链定位（端点 → LLM）

`submit_task_feedback`（`backend/app/api/v1/tasks.py`）→ `TaskFeedbackService.submit_feedback`（`backend/app/services/task_feedback_service.py`）在**一个请求事务里同步串行**执行：

1. 落库前段（校验/反馈 upsert/偏好 delta/偏好更新）——快，DB only；
2. `TaskReflectionService.submit_reflection_answer`（结构化反思路径）：
   - `CognitiveService.create_fragment` → `embedding_service.get_embedding`（远程 embedding 调用）；
   - **`CognitiveService.analyze_behavior` →（`ANALYSIS_SYNC_ON_EVENT=True` 默认开）`UnifiedAnalysisService.analyze_fragment` → `AnalysisOrchestrator._run_behavior_pattern` → `analysis_llm.json_call`（带降级重试的 LLM 补全）——26.7s/30s 的主要来源**；
   - 另有 pgvector 相似检索、情节记忆写入、`MainChainArtifactService.refresh_for_legacy_plan`；
3. `AdaptiveReplanner.on_task_feedback` → `evaluate_plan_health_now`（重 DB，无 LLM）；
4. `_maybe_update_routing_profile_after_feedback`（redis+DB）；
5. fail-safe 补强任务插入（DB）。

非结构化分支 `maybe_enqueue_reflection_prompt` 为纯规则 + DB（模板/风格/冷却/系统通知），实测无 LLM，D2 的 965ms 即此形态——但它也陪绑在同一条重链后面。

## 修法（提交与推断解耦）

`submit_feedback(..., defer_heavy_followups: bool = False)`（默认 False 保持历史语义，HTTP 端点显式传 True）：

- **同步路径（<2s 契约）**：校验 → 反馈 upsert → 偏好 delta + 偏好更新 → 规则版反思引导卡片（`maybe_enqueue_reflection_prompt`，无 LLM，保住客户端卡片 UX）→ `commit` → `refresh` → 事件发布（`task.feedback_submitted` + SRL，均为 redis stream 快操作）→ 返回 200。
- **异步 followup（`loop.create_task` 模式，沿用仓内 `predictive_service._schedule_local_long_horizon_refresh` 同型）**：自适应重规划 → 路由画像 → 结构化反思（embedding + LLM 行为分析 + 记忆/工件）→ fail-safe 补强 → 独立会话 `commit`。
  - followup 用 `FOLLOWUP_SESSION_FACTORY`（生产 = `AsyncSessionLocal`）开**独立会话**——请求会话随快速响应关闭，且规避 `analyze_behavior` 内部 mid-flight `commit()`/补偿 `rollback()` 对请求对象的干扰；
  - `spawn_followup_task` 持强引用集防 GC（asyncio 已知坑）；协程体全量 try/except + `logger.exception`，main.py 已有全局 loop 异常兜底；
  - 调度发生在**commit 之后**，followup 重读已提交行，无脏读；
  - `join_followup()` 可观测性/测试钩子；调度失败（无 running loop，理论不到）降级为可 join 的挂起协程。

行为变化（有意，已记录）：deferred 模式下响应中 `reflection_payload`/`ai_response`/结构化 `reflection_prompt` 为 `null`（schema 本就 optional），产物随后台 followup 落库，移动端可经反馈行/系统通知后续获取；`task.feedback_submitted` 事件先于反思产物产生（消费者只依赖 feedback 行，不依赖 payload）。

## 红绿与回归

- 新增 `tests/api/test_task_feedback_async_reflection.py` 3 例：
  - **慢 LLM 红绿**：stub `TaskReflectionService.submit_reflection_answer` 睡 8s 模拟慢 LLM。修前（stash 修复跑同测）：`AssertionError: endpoint took 8.02s ... heavy inference is still blocking the request path`（红）；修后：200 + 0.02s 级 ack、请求内 0 次 LLM 调用、followup 恰好调度一次、反馈行同步落库（绿）。
  - **异步执行证明**：deferred 提交即时返回且 LLM stub 未被调用 → `join_followup()` 后 stub 恰好被调一次且参数逐字透传（feedback_id/stuck_point）。
  - **内联兼容**：默认 `defer_heavy_followups=False` 保持历史语义（reflection_prompt 回传、落库断言）。
- 既有 `tests/api/test_task_feedback_submit_api.py` 3 例（DF-1 回归）：夹具补 `FOLLOWUP_SESSION_FACTORY` 共享会话 + spawn 捕获，3/3 绿。
- 邻域回归：`test_task_feedback_service_phase4`（4，含补强/路由画像断言）+ `test_task_reflection_service`（3）+ `test_cognitive_loop` + `test_adaptive_replanning_integration` + `test_response_feedback_service` + `test_context_pack_feedback` + `test_card_protocol_phase4` + `test_progress_narrative_service` 共 **45 passed**；`tests/api` 全量 **185 passed**。
- 基线比对确认与本专项无关的存量红（干净树同红）：`test_skip_task_marks_task_abandoned`（`abandon_task` mock 缺 `route_history_decision_id` 形参）、`test_stage35_journey_smoke_main_path`（`trigger_replanning` 对 `SimpleNamespace` 调 `add_done_callback`）、`tests/api` 3 个收集错误文件（accountability/audit/profile_transparency）。
- 风格：black(120) + ruff 全过。

## 遗留与建议

- gRPC 侧 `ResponseFeedbackService.submit_feedback`（响应点赞点踩）是另一服务，未在本专项范围；若实测出现同型延迟再立项。
- `ANALYSIS_SYNC_ON_EVENT=True` 是全仓默认，其余 `analyze_behavior` 调用方仍同步；P1-C 只解反思提交主链，如需全局异步化建议另开专项评估各调用方的响应契约。
