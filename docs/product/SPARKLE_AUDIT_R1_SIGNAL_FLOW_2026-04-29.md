# Sparkle 深度审查报告 #1 — 信号流、Outcome 闭环、Aurora↔Spine 集成

> **审查日期**: 2026-04-29
> **审查者**: Claude (审查角色)
> **范围**: Phase 1-2 信号流完整性、Outcome 闭环实际接线、UX 断点、Aurora↔Spine 集成状态
> **方法**: 全代码路径追踪 (orchestrator.py → spine_orchestrator.py → prompts.py → Flutter WS parser)
> **状态**: 待 Codex 处理

---

## 审查结论概览

| 级别 | 数量 | 说明 |
|------|------|------|
| **P0 Critical** | 3 | 核心功能死代码/未接线，影响路线图核心价值 |
| **P1 High** | 4 | 重要信号缺失/集成断裂 |
| **P2 Medium** | 3 | 功能部分缺失，可降级运行 |
| **OK** | 5 | 已正确实现 |

---

## P0 Critical — 必须修复

### C-01: OutcomeTracker 整个是生产环境死代码

**文件**: `backend/app/signals/outcome_tracker.py`
**严重性**: P0 Critical
**发现**:
- `register_expected()` 在整个 backend 中**只在测试文件中被调用**
- `record_actual()` 同样**只在测试和自身的 `verify_pending()` 内部调用**中被调用
- `verify_pending()` 声称"Called periodically by the scheduler"但 **scheduler_service.py 中没有任何 job 调用它**
- `OutcomeTracker` 在 Phase 1 中被实现并通过了 21 个单元测试，但**从未接入任何生产代码路径**

**影响**: 这意味着 Phase 1 Breakpoint #7 (Verification Loop) 的核心价值未实现。干预后有 expected outcome 定义，但没有地方注册它，也没有地方记录 actual outcome。整个归因→学习→策略调整链路在生产中不运转。

**修复方向**:
1. 在 `spine_orchestrator.py` 的 directive 发出后调用 `register_expected()`
2. 在 `task_event_consumer.py` 的 `task.completed`/`task.abandoned` 处理中调用 `record_actual()`
3. 在 `scheduler_service.py` 中添加定期 job 调用 `verify_pending()`
4. 在 `agent_grpc_service.py` 的用户反馈处理中调用 `record_actual()`

### C-02: CognitiveAdjustment / structured_adjustments 从未到达 LLM prompt

**文件**: `backend/app/orchestration/dual_core_router.py` → `prompts.py`
**严重性**: P0 Critical
**发现**:
- `dual_core_router.py` 正确计算 `structured_adjustments: list[CognitiveAdjustment]`
- `routing_engine.py` 正确透传到 dict
- `response_builder.py` 正确序列化到 `response_metadata`（给 API 响应用）
- `ux_envelope.py` 正确提取 `user_visible` 部分
- **但是 `prompts.py` 的 `build_system_prompt()` 函数完全没有任何对 `structured_adjustments` 的引用**
- 结果：结构化认知调整被计算、日志记录、返回给前端，但**从未影响 LLM 的实际行为**

**影响**: Phase 1 Breakpoint #6 (Structured CognitiveAdjustments) 的核心价值未实现。LLM 不知道认知调整的存在，所以它的回复风格、解释深度、挑战级别等不会根据调整变化。

**修复方向**:
1. 在 `prompts.py` 的 `build_system_prompt()` 中添加参数接收 `structured_adjustments`
2. 在 `standard_workflow.py` 中将 `structured_adjustments` 的 `to_text()` 输出注入到 system prompt
3. 在 `multi_agent_adapter.py` 的两个 `build_system_prompt` 调用中同样传递

### C-03: multi_agent_adapter 完全跳过所有 Spine 上下文

**文件**: `backend/app/orchestration/multi_agent_adapter.py`
**严重性**: P0 Critical（影响 Expert/Multi-Agent 模式用户）
**发现**:
- `standard_workflow.py` line 1562-1570 正确将 `spine_response_directive`, `spine_chronicle_summary`, `spine_fatigue_context` 传入 prompt
- 但 `multi_agent_adapter.py` 的两个 `build_system_prompt` 调用（lines 258 和 454）**不传递任何 Spine kwargs**
- 结果：Expert 模式和 Multi-Agent 模式的用户**完全不受 Spine 调制**，收到的回复不遵循任何 Directive 约束

**修复方向**:
1. 在 `multi_agent_adapter.py` 的两个 `build_system_prompt` 调用中传入 `request_extra_context` 中的 Spine 字段
2. 确保 Spine directives 与 Expert system prompt 的兼容性

---

## P1 High — 重要信号缺失

### H-01: 大量 EventBus 事件不经过 Spine

**文件**: `backend/app/core/event_bus.py` vs `backend/app/signals/spine_orchestrator.py`
**发现**: 以下已定义的事件 Spine 应该消费但没有：

| 事件 | 应该触发的 Spine 行为 | 当前状态 |
|------|----------------------|----------|
| `task.abandoned` | 行为信号（放弃模式检测） | ❌ task_event_consumer 只调 BehaviorSignalCollector，不调 Spine |
| `task.stuck` | 疲劳/瓶颈信号 | ❌ 事件已定义但 consumer 不处理 |
| `focus.session.completed` | 认知负荷/疲劳信号 | ❌ 无 Spine consumer |
| `plan.created` | ExamSprint 触发信号 | ❌ 无 Spine consumer |
| `srl.phase.transition` | 学习阶段变化信号 | ❌ 无 Spine consumer |
| `calendar.event.*` | 时间压力信号 | ❌ 无 Spine consumer |

**修复方向**: 在对应 event consumer 中添加 `spine.on_xxx()` 调用，或在 spine_orchestrator 中注册新的 EventBus consumer group。

### H-02: Aurora→Spine 反馈是只写日志

**文件**: `backend/app/orchestration/orchestrator.py` lines 1457-1466
**发现**:
- Aurora 的决策通过 `feed_aurora_decision()` 写入 Redis list `spine:aurora_decisions:{user_id}`
- 但**没有任何 Spine 策略评估读取这个数据**
- 这意味着 Aurora 的判断不会修正 Spine 的策略，Spine 也不会因为 Aurora 发现了新信息而调整

**修复方向**: 在 `PolicyEngine` 或 `signal_ranker.py` 中添加对 Aurora 决策日志的读取，作为信号源之一。

### H-03: Spine 静默降级无监控

**文件**: `backend/app/orchestration/orchestrator.py` line 2454
**发现**:
- 整个 Spine 调用块被 `except Exception` 包裹
- 异常只设置 `spine_degraded=True`，不发送 metric，不告警
- 如果 Redis 持续故障，Spine 会持续静默跳过，**无人知晓**

**修复方向**:
1. 在 except 中递增 Prometheus counter `spine_degradation_total`
2. 添加 Alertmanager 规则：`spine_degradation_total > 0 for 5m` 触发 P2 告警

### H-04: Context Receipt Bar 缺少用户行动按钮

**文件**: `mobile/lib/features/chat/presentation/widgets/context_receipt_bar.dart`
**发现**:
- 正确从 backend 获取 receipt 数据并渲染
- 但缺少愿景要求的行动按钮："按课件重讲"、"排除此资料"、"换成历年真题"
- 用户看到 receipt 后**无法采取任何纠正行动**

**修复方向**: 在 `_ReceiptDetailSheet` 中添加 action chips，点击后发送对应消息到 chat。

---

## P2 Medium — 功能部分缺失

### M-01: structured_cognitive_adjustments Flutter 完全未实现

**文件**: `mobile/lib/features/chat/` 全目录
**发现**:
- `websocket_chat_service_v2.dart` 解析了数十个 metadata key（spine_growth_card, spine_receipt, etc.）
- 但**零个文件**引用 `structured_cognitive_adjustments`
- 后端发来的结构化认知调整数据被静默丢弃在 `accumulatedRawMetadata` 中

**修复方向**: T1.2.5 需要实现。在 WS parser 中解析，在 chat_provider 中存储，在 chat UI 中渲染。

### M-02: dual_core_router 与 Spine 完全独立

**文件**: `backend/app/orchestration/dual_core_router.py` vs `backend/app/signals/`
**发现**:
- `dual_core_router` 处理 turn-level routing（execution vs cognitive mode）
- Spine 处理 lifecycle-level signals（timeout, mistake, achievement）
- **两者共享零数据**。dual_core_router 的判断不进入 Spine，Spine 的状态不影响 routing mode
- 愿景要求"Both cores collaborate via DualCoreRouter, not run in parallel isolation"

**修复方向**: Phase 3 (Aurora↔Spine convergence) 的核心任务。需要让 dual_core_router 消费 Spine StateRegister 数据。

### M-03: Spine 调用每轮新建实例

**文件**: `backend/app/orchestration/orchestrator.py` line 2366
**发现**:
- 每个 chat turn 都 `SpineOrchestrator(redis)` 新建实例
- 这意味着无内存缓存，每次都从 Redis 读取所有状态
- 对于高频用户，这增加了不必要的 Redis 负载

**修复方向**: 考虑在 orchestrator 级别缓存 SpineOrchestrator 实例，或让 SpineOrchestrator 支持 session-scoped 缓存。

---

## OK — 已正确实现

| 领域 | 状态 | 证据 |
|------|------|------|
| Spine Timeline API | ✅ 已存在 | `GET /api/v1/aurora/spine/timeline` — T2.3.4 已完成 |
| Push deep links | ✅ 完整实现 | `PushNavigationService` 支持 sparkle:// 协议 + entity_id fallback |
| Causal Timeline Panel | ✅ 接 API | 调用 `auroraSpineTimeline` endpoint，支持 corrections |
| GrowthCard | ✅ 真实数据 | 完整 pipeline: backend metadata → GrowthCardEvent → state → widget |
| Home Dashboard | ✅ 功能仪表盘 | 17 个 live 组件，非静态 feature grid |
| Trace ID 传播 | ✅ 三层贯通 | Flutter → Go (X-Trace-ID) → Python (gRPC metadata) |
| Push Scheduler | ✅ 接入 scheduler | `process_recall_queue()` 每 15 分钟执行 |
| Card Protocol DB | ✅ 迁移完整 | 5 张表已通过 Alembic 创建 |

---

## 路线图影响

### T2.3.4 已完成（无需再做）
Spine Timeline API 已存在于 `backend/app/api/v1/aurora.py` line 447+。路径是 `/api/v1/aurora/spine/timeline`。

### 需要新增的任务

| Task ID | 任务 | 来源 | 优先级 |
|---------|------|------|--------|
| C-01-FIX | 接线 OutcomeTracker 到生产代码路径 | 审查发现 C-01 | P0 |
| C-02-FIX | structured_adjustments 注入 prompts.py system prompt | 审查发现 C-02 | P0 |
| C-03-FIX | multi_agent_adapter 传入 Spine context | 审查发现 C-03 | P0 |
| H-01-FIX | 6 个 EventBus 事件接入 Spine consumer | 审查发现 H-01 | P1 |
| H-02-FIX | Aurora 决策反馈接入 Spine PolicyEngine | 审查发现 H-02 | P1 |
| H-03-FIX | Spine 降级 Prometheus counter + 告警 | 审查发现 H-03 | P1 |
| H-04-FIX | Context Receipt Bar 用户行动按钮 | 审查发现 H-04 | P1 |
| M-01-FIX | structured_cognitive_adjustments Flutter 解析 | 审查发现 M-01 | P2 |
| M-02-FIX | dual_core_router 消费 Spine StateRegister | 审查发现 M-02 | P2 |

### 已有路线图任务状态更新

| Task ID | 原状态 | 新状态 | 原因 |
|---------|--------|--------|------|
| T1.2.5 Flutter WebSocket 传递 | ⬜ 未开始 | ⬜ 未开始（但需补充：后端字段也未到达 LLM prompt，见 C-02-FIX） |
| T1.3.6 test_verification_loop.py | ✅ 完成 | ⚠️ 需补接线 | 测试通过但生产代码未调用，需加 integration test |
| T2.3.4 Spine Timeline API | ⬜ 未开始 | ✅ 已存在 | endpoint 已在 aurora.py 中实现 |
| T2.3.5 causal_timeline_panel.dart | ⬜ 未开始 | ✅ 已存在 | widget 已实现并调用 API |

---

> **关键发现总结**: Phase 1 的三个 Breakpoint 的后端模块都写了、测试了、通过了，但有两个在生产代码中是"孤儿"——OutcomeTracker 从未被调用，CognitiveAdjustment 从未到达 LLM。这不是代码质量问题，而是**接线问题**。模块存在但链路未闭合。
