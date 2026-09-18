# 全系统审查·第二轮（R2）— 01 引擎·编排运行时与聊天 Agent 图谱

- 复审员：1 号（engine-orchestration 切片）
- 基线：`main@ca86bda8`（R1 修复已集成），工作树 `/Users/brsama/code/GitHub/Sparkle-sysrev/wt1`
- 对应 R1 修复记录：[round1/01-fixes.md](../round1/01-fixes.md)（R1 主报告 01-engine-orchestration.md 未入库，本次以 fixes.md 为核对基准）
- 方法：静态核对 + 运行时集成实验（假图谱驱动真实 `ChatOrchestrator.process_stream` 全链路，不经过网络；脚本存于 `/tmp/r2_experiments/`，未改动仓库代码）

---

## 一、修复验证结论（逐 ID）

三个 R1 新增测试文件在基线全部通过：`tests/orchestration/test_response_builder_semantic_meta.py`（2）+ `test_orchestrator_graph_timeout.py`（2）+ `test_round1_p2_fixes.py`（18）= **22 passed**。
注：fixes.md 声称"3 个文件 24 个测试"，实际收集 22（test_round1_p2_fixes.py 为 18 个，非 20），属文档计数笔误，测试本体无缺失（RB-03/04/05/06/07/08/09/10/11/12/13/14/16 均有对应测试）。

| ID | 结论 | 核对证据 |
|---|---|---|
| RB-01 | **确认** | `response_builder.py:1146` `semantic_meta = None` 显式初始化存在；2 个测试绿（含 focused_memory 存在的对照组） |
| RB-02 | **确认**（质量见 §2 R2-01/§3④） | `execution_engine.py:131` 模块常量 `GRAPH_TIMEOUT_SECONDS=300`；`orchestrator.py:3479-3512` 超时出口完整（drain→FAILED→error/error_timeout 帧→return）；2 个测试绿 |
| RB-03 | **确认**（质量佳） | `execution_engine.py:1865-1866` `+=` 累加存在；冒烟场景 A 集成验证：两个 usage 事件（100/20、50/10）经真实 `_execute_graph` 汇总 150/30 传入 `_cleanup` |
| RB-04 | **确认**（质量佳） | `circuit_breaker.py:187` `min_samples = max(3, window_size // 2)`，小窗口下界由 max(3,…) 兜底；连续失败路径独立不受影响；3 个测试绿（含行为保持对照） |
| RB-05 | **确认** | `token_tracker.py:410` `isinstance(key, bytes)` 判别；测试绿 |
| RB-06 | **确认** | `session_state_mixin.py:871` `await active_db.flush()`，注释明确提交所有权在 gRPC 服务层；测试绿。同族点见 §2 R2-09 |
| RB-07 | **确认** | `context_pruner.py:144-148` 空摘要退回 `_compress_with_importance`；2 个测试绿（双向） |
| RB-08 | **确认**（质量佳，运行时验证） | `execution_engine.py:2607-2612` `build_safe_chat_error` 脱敏；冒烟场景 C1：planner 抛含 `postgres://planner:pw@db:5432` 的异常，输出 delta 无原文、turn 最终 DONE |
| RB-09 | **确认** | `agents/graph/nodes/router.py:75` `_resolve_router_user_query`；测试绿 |
| RB-10 | **确认** | `dual_core_router.py:290-291` 统一用 `high_cognitive_load_threshold` 键；测试绿 |
| RB-11① | **确认**（②③未改，已在 R1 剩余清单列明，不算缺陷） | `statechart_engine.py:30-34,108` 白名单 + 插入序淘汰未保护键；2 个测试绿 |
| RB-12 | **确认** | `state_manager.py:199-210` 按 `fields(FSMState)` 过滤 kwargs；测试绿 |
| RB-13 | **确认** | `execution_engine.py:2599-2603` 保存引用 + `getattr(self, "_track_task")` 登记；测试绿 |
| RB-14 | **不采纳裁决确认** | `test_rb14_empty_aurora_plan_stop_is_cached_as_wait_turn` 存在且绿，拒绝理由（幂等缓存回放 wait-turn 是有意语义）有测试背书 |
| RB-16 | **确认** | `orchestrator.py:2836-2864` 两个短路出口 `_update_state(STATE_DONE)`；2 个测试绿 |

**总结论：14 项（RB-01/02 + 12 项 P2/P3，含 RB-14 不采纳裁决）全部在基线真实存在，0 存疑。** 抽查的 3 个关键修复（RB-02、RB-03、RB-08/RB-04）修法在运行时/边界下成立，不是只让测试过；RB-02 的残留边界（取消只达包装任务）为 R1 已记录的跨切片遗留，见 R2-01。

---

## 二、运行时复审发现（R2 主镜头）

全链路冒烟（假图谱 + 真实 orchestrator 机制）验证了以下**集成一致性为正面**：帧序（status_update → delta×N → usage → 终帧 STOP+full_text）、`_bind_response_id/session_id` 绑定、FSM INIT→DONE、usage 累加入 `_cleanup`、`REQUEST_COUNT`/`COLLABORATION_LATENCY`、异常路径的 drain→脱敏→FAILED→可复用（同会话下一轮正常）。以下为发现：

| ID | 严重度 | file:line | 场景 | 证据 | 建议 |
|---|---|---|---|---|---|
| R2-01 | **P1** | `app/orchestration/execution_engine.py:1843-1846` + `app/core/task_manager.py:110-135` | 超时/断连取消只能杀 task_manager 包装任务，内层 graph 协程继续执行至跑完 | 运行时实证（场景 E）：客户端断连触发 `GeneratorExit` → `graph_task.cancel()` 后等待 2s，**内层图谱 `inner_finished=True`**（照常跑完）。`_queue_worker` 在 `await task` 期间不监听 `result_future.cancelled()`。后果：客户端已收到 retryable ERROR 并重试后，旧轮仍继续消耗 LLM tokens、写共享 DB/Redis 达数百秒 | worker 循环改 `asyncio.wait({task, result_future取消事件}, FIRST_COMPLETED)` 或 spawn 提供可取消句柄；超时出口改为取消句柄直达内层。R1 遗留项升格：断连是高频事件，非低频超时 |
| R2-02 | **P2** | `app/orchestration/execution_engine.py:2111-2125` | planner 纯超时不计入熔断：持续超时的 planner 永不熔断，每轮固定损失 `_LANGGRAPH_PLANNER_TIMEOUT_SECONDS`=10s 延迟 | 运行时实证（场景 C2c）：6 连纯超时（timeout=0.2s，fallback 走真实 ExecutablePlan）后 `failure_count=0`、breaker 保持 CLOSED；对照组 C1 硬失败 5 连即 OPEN。`except TimeoutError` 分支只建 fallback，无 `on_failure` | 超时也计入失败（`await self.langgraph_breaker.on_failure(f"timeout_after_{_LANGGRAPH_PLANNER_TIMEOUT_SECONDS}s")`），或至少区分记数防止每轮满额超时 |
| R2-03 | **P2** | `app/orchestration/state_manager.py:177-215`；`orchestrator.py:178-181` | 会话 FSM 是"名义状态机"：①无任何转移校验；②THINKING/GENERATING/TOOL_CALLING 在生产代码零写入点 | 运行时穷举（场景 D）：真实 SessionStateManager 6×6=36 对转移**全部接受**（DONE→THINKING、FAILED→DONE 均接受）；grep 证实orchestration+agents 生产代码无任何 `STATE_THINKING/GENERATING/TOOL_CALLING` 写入。`test_orchestrator_state_transitions.py` 只测接受序列，未测拒绝 | 明确取舍：要么实现 `_VALID_TRANSITIONS` 校验（终态出/入受控），要么文档降级 FSM 为"生命周期标记"并清理死状态；外部消费方（`_DURABLE_RECOVERABLE_STATES` 恢复逻辑、网关展示）依赖状态值，需同步评估 |
| R2-04 | **P2** | orchestration 包 19+ 处（清单见 §3③） | loguru `exc_info=` 无效用法，关键异常堆栈不落日志 | 运行时证明：`logger.error(..., exc_info=True)` 输出不含 Traceback，`logger.opt(exception=e)` 正常输出 | 全部改为 `logger.opt(exception=e).error(...)`；建议加 CI grep 守卫防回潮 |
| R2-05 | **P2** | `app/core/task_manager.py:55,79-96,110` | 全局单例跨事件循环：第二循环上 `spawn` 直接 `RuntimeError: PriorityQueue is bound to a different event loop`（Python 3.11 `_LoopBoundMixin` 语义，比 R1 记录的"静默死队列"更响），且 spawn 异常在 `_execute_graph` 的 try 块之外，被 process_stream 通用 except 吞成"系统暂时不可用" | 运行时实证：两次 `asyncio.run` 复用单例，第二次 spawn 抛 RuntimeError | task_manager 改 per-loop 实例（ContextVar）或 spawn 前 fail-fast 带清晰错误；pytest 基建提供单例重置 fixture |
| R2-06 | P3 | `app/core/business_metrics.py:101` vs `app/core/metrics.py:766` | COLLABORATION_SUCCESS 双定义且 **Prometheus 导出名不同**（`sparkle_collaboration_success_total` vs `sparkle_collaboration_total`）；当前所有写入方都用 business_metrics 版，metrics 版是孤儿。`get_or_create_metric` 按名去重：同名（COLLABORATION_LATENCY 两处同名）静默别名，异名静默分叉——两种失败模式都存在 | 模块级核对：无任何文件从 `app.core.metrics` 导入 COLLABORATION_SUCCESS；运行时对象 id 对比 | 删除孤儿定义；给 `get_or_create_metric` 加"同名不同 label/文档"告警；冒烟实验中曾误测 core.metrics 版为 +0，正说明该分裂易踩 |
| R2-07 | P3 | `orchestrator.py:3726-3729`（CancelledError 出口）+ `_execute_graph` GeneratorExit 路径 | 客户端断连后会话 FSM 停留 INIT，不推进任何终态（对比异常出口推 FAILED、成功推 DONE）；断连轮在状态层面不可见 | 运行时实证（场景 E）：断连+等待后 `load_state` 返回 INIT | 断连出口补 `_update_state(session_id, STATE_FAILED/或 CANCELLED, "client disconnected")`；或确认 INIT 可被下一轮覆盖属可接受语义并记录 |
| R2-08 | P3 | `gateway/internal/handler/chat_orchestrator_protocol.go:159-164` | usage 帧透传到客户端为**有意设计**（网关显式转换为 `type:"usage"` JSON）——澄清项非缺陷，记录防止后续误报 | 网关代码显式 case 分支 | 无需动作 |
| R2-09 | P3 | `app/orchestration/context_builder.py:1497-1500` | `_build_full_context` 内 `await active_db.commit()` 持久化用户消息——与 RB-06 同族的中途 commit 共享 session 点 | 代码定位；属 R1 剩余清单"全仓审计其余中途 commit() 共享 session 的点"的一个实例 | 纳入 RB-06 follow-up 审计统一处置（改 flush + 调用方统一提交），本条为该审计提供具体坐标 |

---

## 三、F1 移交四项新发现·专项诊断

### ① `user_context_payload=None` 不设防 — 确认，潜伏缺陷（P2）

- **缺陷点**：`execution_engine.py:2090` `locale = user_context_payload.get("profile", {}).get("identity", {}).get("language", "en")`。同一函数内其他 payload 访问点均有 `isinstance(user_context_payload, dict)` 守卫（2038、2052 等），唯独此行裸 `.get`。
- **可达性**：`context_builder.py:1426` 初始化 `user_context_payload = None`；`_build_full_context` 在 `active_db/user_id` 缺失且无 grpc_context 的分支直接返回 None（1426→1512）；`_merge_user_contexts` 无 grpc 时返回 `local_context`（`_build_user_context` 返回值形态决定是否为 None）。当前主链路总是 dict，但 no-DB 降级路径与上下文为空的新用户路径可产生 None。
- **后果链**：None→`AttributeError` → 落入 RB-08 通用 `except Exception`（2601）→ ①被误记为 "LangGraph planning error" 并降级 direct（真实失败原因被脱敏文案掩盖，与 RB-08 的初衷相反）；②`langgraph_breaker.on_failure` 被多记一次——**非 planner 过错的失败污染熔断统计**。
- **修复方案**：函数入口归一 `user_context_payload = user_context_payload if isinstance(user_context_payload, dict) else {}`（一处修全函数），或最小改 `(user_context_payload or {}).get("profile", {})`；补 1 个 None 输入回归测试。

### ② task_manager 跨事件循环污染 — 确认，机制已精确化（P2）

- **精确机制**（Python 3.11 实测）：全局 `task_manager` 单例的 `asyncio.PriorityQueue` 首次使用时绑定事件循环；第二个循环上 `await self._queue.put(...)` 抛 `RuntimeError: <PriorityQueue> is bound to a different event loop`（`asyncio/mixins.py:20`）。注意：这不是 R1 描述的"静默死队列"，而是**响亮异常**，但落点更糟——`_execute_graph` 中 `task_manager.spawn` 位于 try 块之前（execution_engine.py:1843），RuntimeError 一路上抛至 process_stream 通用 except，会话 FAILED、用户只见"系统暂时不可用"，根因被脱敏吞掉。
- **影响面**：生产单循环主链路不触发；测试基建（pytest-asyncio 每测试新循环）、脚本工具、未来任何"每请求循环/多 worker 循环"嵌入必踩，且错误信息不指向真因。
- **修复方案**：①`BackgroundTaskManager` 改 loop-scoped（`ContextVar` 持有 per-loop 实例，`get_task_manager()` 工厂）；②保守方案：spawn 入口检测 `asyncio.get_running_loop()` 与 worker 循环不一致时抛带明确指引的错误；③tests/conftest 提供 autouse fixture 重置单例（R1 已建议）。

### ③ loguru `exc_info` 无效用法 — 确认，影响面远超单点（P2）

- **运行时证明**：`logger.error("...", exc_info=True)` 输出不含 Traceback（kwarg 被当作 extra 静默吞掉）；`logger.opt(exception=e).error(...)` 正常输出完整堆栈。
- **影响面清单**（orchestration 包内 grep，共 19+ 处），关键路径包括：`execution_engine.py:1401`（tool result continuation 失败）、`execution_engine.py:2606`（**LangGraph 规划失败——RB-08 同点的堆栈从未落日志**）、`executor.py:485`（工具执行错误）、`orchestrator.py:1543`（后台任务异常回调）、`orchestrator.py:2373-2426`（Redis/spine 指令读取 6 连）、`persistence_layer.py:167` 等。这些位置生产排障时只有消息文本、无堆栈。
- **修复方案**：机械替换为 `logger.opt(exception=e).error(...)`；建议加自定义 ruff 规则或 CI `grep -n "exc_info" app/ | grep -v gen` 守卫（loguru 项目内 exc_info 应零命中）。

### ④ 超时路径未写 episodic error 事件 — 确认，建议以新枚举补齐（P3）

- **缺陷点**：RB-02 新增的超时出口（orchestrator.py:3479-3512）与通用异常出口（3730-3757）对齐了 drain/FAILED/ERROR 帧/指标，但**没有** `_write_turn_end_episodic_memory(event_kind="error")`（通用 except 在 3743 有）。
- **后果**：超时回合在用户 episodic 记忆中不可见——学习画像/记忆聚合缺失该事件；同时超时轮的用户消息已入库（context_builder 内 persist）， assistant 侧无对应记忆，长期造成轻微不对称。
- **修复方案**：产品定夺"超时是否算错误回合"（R1 已留待确认）。建议折中：episodic 事件增加 `event_kind="timeout"` 枚举，超时出口写入，既补齐记忆可见性又不污染 error 语义统计；实现上照抄通用 except 的调用形态（turn_started_at/plan_context 等 locals 防护写法照搬）。

---

## 四、测试执行记录

| 项目 | 结果 |
|---|---|
| R1 新增修复测试（3 文件） | **22 passed**（fixes.md 写 24 为计数笔误：18+2+2） |
| `tests/orchestration` 新基线（正确 Redis 密码 `sparkle_dev_redis_2026`） | **9 failed / 160 passed / 0 error**（R1 时期 34 failed → 转 9，25 个假红确认为 Redis 认证问题） |
| 9 个失败定性 | 全部存量、非 R1 修复回归：6 个 `test_orchestrator_process_stream_integration`（老 `_GraphStub.invoke(self, state)` 不认 `resume_policy` kwarg——该调用形态自 initial commit `1722e6dc` 即存在，属桩签名漂移）；3 个 `test_planning_workflow`（v1 规划流断言，`assert result is not None` 家族）。44 个 v1 全局基线失败与 KNOWN_CODE_DEBT_LEDGER 项未重报 |
| 运行时实验 | 冒烟 A（成功轮）/B（异常轮）/C1（硬失败降级链）/C2c（纯超时×6）/D（FSM 36 对穷举）/E（断连取消语义）；跨循环 RuntimeError 演示；loguru exc_info A/B 证明。实验脚本 `/tmp/r2_experiments/`，未入仓库 |
| Redis 依赖测试 | 用真实密码后无新增假红 |

## 五、总评

R1 修复 14/14 全部确认落地且抽查质量成立（RB-03/RB-08 在真实集成链路复验通过）；运行时复审验证了主链路帧序/计量/脱敏/清理的集成一致性，未发现正确性回归。新发现问题集中在**异常与边界路径的资源语义**：P1 一项（取消只达包装任务，断连后图谱继续跑）、P2 四项（超时不计熔断、FSM 无校验且中间态为死状态、loguru 堆栈丢失 19+ 处、task_manager 跨循环）、P3 四项。F1 移交四项全部成立并给出修复方案（③影响面由 1 处扩至 19+ 处）。
