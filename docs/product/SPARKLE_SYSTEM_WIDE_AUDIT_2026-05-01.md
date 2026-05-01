# Sparkle 全系统深度审计报告

**日期**: 2026-05-01
**范围**: Aurora 双核体验 / Flutter UX / 后端服务 / Go 网关 / 增长闭环 / 个性化 / 数据利用 / 跨层集成
**方法**: 8 个并行只读审计 Agent，覆盖 8 个维度，读取实际实现代码

---

## 总览

| 维度 | P0 | P1 | P2 | 总计 |
|------|----|----|-----|------|
| Aurora 双核体验 | 2 | 5 | 5 | 12 |
| Flutter 移动端 UX | 5 | 5 | 3 | 13 |
| 后端服务完整性 | 1 | 3 | 5 | 9 |
| Go 网关安全可靠 | 5 | 5 | 5 | 15 |
| 增长闭环端到端 | 0 | 2 | 1 | 3 |
| 用户画像个性化 | 0 | 3 | 3 | 6 |
| 数据利用效率 | 0 | 3 | 2 | 5 |
| 跨层集成 | 3 | 3 | 1 | 7 |
| **合计** | **16** | **29** | **25** | **70** |

---

## P0 — 致命级（必须修复）

### Aurora 双核

**P0-1: strategy_adjustments 生成后从未被消费**
- 文件: `backend/app/orchestration/dual_core_router.py:216-233`
- Router 调用 `recommend_strategy()` 生成策略调整（session_mode, explanation_style, difficulty_level 等），但下游 `experience_actuator` 期望从 `system_adjustments` 读取，而 Router 写入的是 `strategy_adjustments`。字段名不匹配导致所有策略调整静默丢弃。
- 影响: 用户不会感知到任何路由策略差异。

**P0-2: 用户纠正不更新路由行为**
- 文件: `backend/app/aurora/runtime_v1/correction_feedback.py:138-213`
- `CorrectionFeedbackProcessor` 更新 StateRegister 置信度和 self-model，但**不存在**从纠正到路由 profile 更新的路径。纠正数据持久化了，但不影响未来路由决策。
- 影响: 用户纠正 100 次"Aurora 太激进"，路由阈值不会改变。

### Flutter UX

**P0-3: Plan Review Card 提交后可能卡死**
- 文件: `mobile/lib/features/chat/presentation/widgets/plan_review_card.dart:299-329`
- `_isSubmitting` 设置后无错误处理。`onDecision()` 失败时用户看到永久 loading，无错误提示，无重试按钮。
- 影响: 用户点击"批准/驳回"后 app 似乎卡死。

**P0-4: Achievement 解锁无自动庆祝**
- 文件: `mobile/lib/features/achievement/presentation/screens/milestone_celebration_screen.dart`
- 庆祝屏幕只在特定导航 payload 时触发，achievement provider 不会自动导航到庆祝界面。用户达成重大里程碑可能完全不知道。
- 影响: 核心正向反馈回路断裂。

**P0-5: Galaxy 知识图谱后端事件流未实现**
- 文件: `mobile/lib/features/galaxy/data/repositories/galaxy_repository.dart:64-74`
- `getGalaxyEventsStream()` 返回 `Stream.empty()`，仅 debug print。知识图谱没有实时更新。
- 影响: 知识图谱是静态死 UI，与愿景严重不符。

**P0-6: Task 完成无视觉反馈**
- 文件: `mobile/lib/features/task/presentation/providers/task_provider.dart:164-198`
- Task 创建/完成只有静默状态更新，无确认动画，无庆祝效果。`_syncCalendarForTask()` 可静默失败。
- 影响: 用户完成关键任务后无成就感。

**P0-7: 大量 catch 块静默吞掉错误**
- 分布: `mobile/lib/features/vocabulary/`, `visual_elements/`, `chat/data/services/websocket_chat_service_v2.dart` 等 30+ 文件
- `catch (_) {}` 或 `catch (e) { debugPrint('$e'); }` 模式广泛存在。
- 影响: 功能静默失败，用户点击按钮无反应，无法排查。

### Go 网关

**P0-8: Token 刷新竞态条件**
- 文件: `backend/gateway/internal/middleware/auth.go:289-370`
- 多个并发请求使用过期 token 时，可在 Redis 验证和本地缓存更新之间的窗口绕过黑名单检查。
- 影响: 被吊销的 token 仍有短暂有效窗口。

**P0-9: WebSocket 无消息排序保证**
- 文件: `backend/gateway/internal/handler/chat_orchestrator.go:319-624`
- 并发 WebSocket 消息无序列化机制，可能乱序处理。
- 影响: 对话流混乱，AI 回复出现在用户消息之前。

**P0-10: 无背压机制**
- 文件: `backend/gateway/internal/handler/chat_orchestrator.go:319-624`
- gRPC 流式无 backpressure，Python 引擎慢时消息无限排队。
- 影响: 高负载下内存耗尽，OOM。

**P0-11: WebSocket 重连无状态管理**
- 文件: `backend/gateway/internal/handler/websocket_proxy.go:117-122`
- 重连无 rate limit，无 session 状态验证，无 stale 连接清理。
- 影响: 潜在 session 劫持，资源泄漏。

**P0-12: 连接清理竞态**
- 文件: `backend/gateway/internal/handler/ws_registry.go:73-100`
- `Unregister` 与清理操作之间存在竞态。
- 影响: goroutine 泄漏，内存泄漏。

### 跨层集成

**P0-13: 后端硬编码中文绕过 Flutter i18n**
- 文件: `backend/app/api/grpc_auth.py:62,83`, `agent_grpc_service.py:248`, `adapters/openclaw/intent_translator.py:11-24`
- 20+ 处硬编码中文字符串直接返回给客户端。Flutter i18n 系统有对应翻译但被绕过。
- 影响: 英文用户看到中文错误消息和进度提示。

**P0-14: gRPC 错误码映射丢失语义**
- 文件: `backend/app/services/agent_grpc_service.py:53-58`
- 15 种错误码中只有 2 种映射到具体 gRPC status，其余全部 → `INTERNAL`。
- 影响: Flutter 无法区分 UNAUTHORIZED（跳登录）、TIMEOUT（重试）等场景。

**P0-15: 15 个仲裁 RPC 已实现但 Flutter 完全未接入**
- 文件: `proto/agent_service.proto` (SubmitReviewOverride, SubmitReviewAppeal, GetArbitrationQueue 等)
- 后端完整实现了 Plan 仲裁流程（appeal, override, arbitration queue），但 Flutter 没有任何 UI 或服务调用。
- 影响: 完整的功能子系统不可达。

**P0-16: WebSocket 消息类型 Flutter 未处理**
- 文件: `mobile/lib/features/chat/data/services/websocket_chat_service_v2.dart:168-184`
- Go 网关发送 `action_feedback`, `focus_completed`, `update_node_mastery` 等消息类型，Flutter 的事件解析器静默忽略。
- 影响: 关键状态更新丢失，用户看不到任务完成确认等。

---

## P1 — 高优先级

### Aurora 双核

- **structured_adjustments 不持久化为状态变更** — 每轮对话从头开始，不累积调整
- **AdaptationRecord 未反馈进路由 profile** — 偏好学习记录了但不更新阈值
- **Growth Loop 阶段间数据不流通** — Reflection 不触发 Adapt，Achievement 不影响 Planning
- **State Aggregator kill switch 不一致** — 主开关 off 但 social 信号仍流
- **多个路由决策源可冲突** — legacy router, Aurora projection, stage overlays 无明确优先级

### Flutter UX

- **WebSocket 断连反馈仅 "Reconnecting..."** — 无手动重试，无数据丢失说明
- **消息排序在断连后无重排** — 对话流混乱
- **离线消息队列无可见性** — 用户以为已发送，实际卡在队列
- **表单验证不一致** — Task 可创建空标题，Plan 接受不现实日期
- **通知权限无解释直接弹系统对话框** — 用户不理解价值而拒绝

### 后端服务

- **Memory 存储后未接入 prompt 组装** — 记忆系统收集了但 AI 看不到（TD-008 TODO）
- **Event Bus 5+ 事件类型无消费者** — UserRegistered, ReflectionCompleted, CalendarEvents 等
- **Community visibility 执行不一致** — `_is_visible_to()` 未在所有消息检索路径强制执行

### Go 网关

- **Redis 不可用时安全行为不一致** — Fail-Closed/Fail-Open 混合
- **Circuit breaker 状态转换有竞态** — 可卡在错误状态
- **Chat history cache 无写穿透/失效** — 用户看到过时对话
- **敏感端点缺少 rate limit** — 文件上传、设置变更等
- **CORS Origin 反射无格式验证** — 潜在 header 注入

### 增长闭环

- **Reflection → Adapt 断开** — 反思洞察不自动触发计划调整
- **Reflect 阶段 24h cooldown 太长** — 错过反思时机

### 个性化

- **Cognitive Prism 数据仅作"背景知识"** — 不是行为指令，AI 可以忽略
- **学习风格检测完全缺失** — 无 VARK 或任何风格检测机制
- **SRL 阶段检测不影响响应策略** — 收集了但不驱动任何行为变化

### 数据利用

- **State Aggregator 19 个字段仅 2-3 个持续进入 prompt** — 85% 数据损失
- **Aurora 纠正 → Prompt 组装链断裂** — StateRegister 更新不同步到 Aggregator
- **行为模式收集后 0% 进入 prompt** — 85% 损失

### 跨层集成

- **User ID 提取方式不一致** — 部分 RPC 用 metadata，部分用 request body，存在安全隐患
- **Session ID 未验证** — Go 网关不检查 Python 返回的 session_id 是否为空
- **Aurora 特征开关仅 Python 检查** — Go/Flutter 无感知，可能展示已关闭的功能

---

## P2 — 中等优先级

### Aurora 双核

- Aurora user preferences 无独立 kill switch
- `emotion_hint` 字段从未填充
- State fields collected but not used in routing (recent_scenes, learning_state)
- 无 Dual-Core Router 独立 kill switch
- capsule_preferences 和 working_memory_snapshot 利用不充分

### Flutter UX

- Legal documents 仍是 placeholder
- Loading states 缺少 skeleton screens
- Accessibility 标签不完整

### 后端服务

- Achievement 事件到成就映射不完整
- Tool registry 无实现验证
- Galaxy graph evolution 集成不完整
- DLQ 无监控/告警
- Orchestrator.py 28,690 行，技术债严重

### Go 网关

- 缺少现代安全 headers (COOP, COEP)
- API 契约漂移风险
- gRPC 连接池饱和处理
- Message size 验证不一致
- `context.Background()` 未传播请求上下文

### 增长闭环

- 无主动触发（系统等待用户而非检测模式）

### 个性化

- Agent persona 与 user preference 不连通
- 多层个性化 (SESSION/EPISODE/PROFILE) 无清晰冲突解决
- Prompt 中个性化仅占 4% token 空间

### 数据利用

- Token 预算限制导致 50% 已收集数据被截断
- 40% event bus 事件类型无有意义消费者

### 跨层集成

- 分布式追踪在 WebSocket → gRPC → Python 链路中断裂

---

## 与愿景的关键差距

| 愿景承诺 | 现实 | 缺口 |
|---------|------|------|
| "双核协作" | Router 生成的策略调整被静默丢弃 | P0-1 |
| "自适应学习" | 用户纠正不影响未来行为 | P0-2, P0-15 |
| "知识星图可视化" | 事件流为空，静态 UI | P0-5 |
| "成就与庆祝" | 解锁不自动庆祝 | P0-4 |
| "个性化 AI 教练" | 收集数据仅 15% 到达 AI 推理层 | P1 数据利用 |
| "7 阶段成长闭环" | 阶段间数据不流通，无闭环 | P1 Aurora |
| "理解你的学习风格" | 无学习风格检测机制 | P1 个性化 |

---

## 建议修复顺序

### 第 1 周（P0 致命级）
1. P0-1: 修复 strategy_adjustments 字段名不匹配
2. P0-2: 建立纠正 → 路由 profile 更新路径
3. P0-3: Plan Review Card 错误处理 + 重试
4. P0-13: 后端硬编码中文改为返回 error code
5. P0-14: 完整 gRPC 错误码映射

### 第 2 周（P0 继续）
6. P0-4: Achievement 自动庆祝导航
7. P0-6: Task 完成视觉反馈
8. P0-8: Token 刷新竞态修复
9. P0-9: WebSocket 消息序列化
10. P0-15: 评估仲裁 RPC 是否需要 Flutter 接入或标记 deprecated

### 第 3-4 周（P1）
11. 数据利用: State Aggregator → Prompt 组装桥接
12. 个性化: Cognitive Prism 从"背景知识"升级为"行为指令"
13. 跨层: User ID 提取标准化
14. 增长闭环: Reflection → Adapt 自动触发

---

## 验证 & 修复追踪 (2026-05-01 第二轮)

### P0 验证结果

| ID | 审计原文 | 验证结果 | 修复状态 |
|----|---------|---------|---------|
| P0-1 | strategy_adjustments 字段不匹配 | **误报** — strategy_adjustments 和 system_adjustments 是两个独立来源，各自正确流入 experience_actuator | N/A |
| P0-2 | 纠正不更新路由行为 | **确认** — CorrectionFeedbackProcessor 不调用 RoutingProfileService | ✅ 已修复 (commit 4f104289b) |
| P0-3 | Plan Review 卡死 | **误报** — try-catch-finally 正确处理错误，_isSubmitting 总被重置 | N/A |
| P0-4 | Achievement 不自动庆祝 | **误报** — 完整链路已实现: WS→chat notifier→pendingAchievementUnlockProvider→ShellNavigation→dialog | N/A |
| P0-5 | Galaxy 事件流为空 | **确认** — Flutter getGalaxyEventsStream() 直接返回空流，但后端 SSE 完整 | ✅ 已修复 (commit 5803e09f0) |
| P0-6 | Task 完成无视觉反馈 | **误报** — 多感官反馈已实现 (confetti, haptic, audio, dialog) | N/A |
| P0-7 | 静默吞错误 | **待验证** — 部分场景合理 (debugPrint)，部分需要加用户提示 | Deferred |
| P0-8 | Token 刷新竞态 | **误报** — RWMutex + Redis 检查提供纵深防御 | N/A |
| P0-9 | WebSocket 无消息排序 | **确认** — 无序列号或排序机制 | Deferred (架构级变更) |
| P0-10 | 无背压 | **确认** — 无流控 | Deferred (架构级变更) |
| P0-11 | WS 重连无状态管理 | **确认** — 无会话恢复 | Deferred (架构级变更) |
| P0-13 | 硬编码中文 | **确认** — grpc_auth, agent_grpc_service, intent_translator | ✅ 已修复 (commit cdb92a8a6) |
| P0-14 | gRPC 错误码映射 | **部分确认** — 仅2种映射，其余有意回退 INTERNAL | ✅ 已修复 (commit 9963328a2) |
| P0-15 | 15 个仲裁 RPC 未接入 | **确认** — 但为管理员功能，非用户流程 | Deferred (等管理面板) |
| P0-16 | WS 消息类型被忽略 | **确认** — 5 种消息类型返回 UnknownEvent | ✅ 已修复 (commit 403879fef) |

### P0 汇总

- **已修复**: 5 (P0-2, P0-5, P0-13, P0-14, P0-16)
- **误报**: 5 (P0-1, P0-3, P0-4, P0-6, P0-8)
- **延迟**: 5 (P0-7, P0-9, P0-10, P0-11, P0-15)

---

**审计完成时间**: 2026-05-01
**第二轮验证时间**: 2026-05-01
**下一步**: P1 优先级验证与修复
