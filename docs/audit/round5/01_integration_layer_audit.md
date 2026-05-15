# Sparkle 集成层深度审计报告

> 审计范围: `agent_grpc_service.py` (1,791行) | `ux_envelope.py` (1,907行) | `executor.py` (942行)
> 审计日期: 2026-05-15
> 审计员: Claude Agent (Round 5)

---

## 第一部分: 架构分析

### 1.1 gRPC 服务 (`agent_grpc_service.py`)

#### 方法清单

| 方法 | 类型 | 行号 | 认证要求 |
|------|------|------|----------|
| `StreamChat` | 服务端流 | 232-405 | metadata user-id (未验证) |
| `SubmitResponseFeedback` | 一元 | 407-500 | metadata user-id (未验证) |
| `RetrieveMemory` | 一元 | 550-619 | 无认证 |
| `GetUserProfile` | 一元 | 621-675 | 无认证 |
| `GetWeeklyReport` | 一元 | 677-716 | 无认证 |
| `SubmitPlanReview` | 一元 | 718-877 | metadata user-id (未验证) |
| `SubmitContentReviewFeedback` | 一元 | 879-1008 | metadata user-id (未验证) |
| `SubmitReviewOverride` | 一元 | 1014-1085 | metadata user-id (未验证) |
| `SubmitReviewAppeal` | 一元 | 1087-1171 | metadata user-id (未验证) |
| `GetAppealStatus` | 一元 | 1173-1219 | 无认证 |
| `SubmitReviewFeedback` | 一元 | 1225-1313 | request user_id (未验证) |
| `RequestRegeneration` | 一元 | 1315-1412 | request user_id (未验证) |
| `GetFeedbackStatistics` | 一元 | 1414-1458 | request user_id (未验证) |
| `GetArbitrationQueue` | 一元 | 1464-1546 | `_require_admin` (DB 验证) |
| `AssignArbitrationCase` | 一元 | 1548-1632 | `_require_admin` (DB 验证) |
| `SubmitArbitrationDecision` | 一元 | 1634-1747 | `_require_admin` (DB 验证) |
| `GetArbitrationQueueStats` | 一元 | 1749-1791 | `_require_admin` (DB 验证) |

#### 认证流程

gRPC 服务端存在两层认证架构:

1. **AuthInterceptor** (`app/api/grpc_auth.py`): 注册为 gRPC server interceptor, 支持两种认证:
   - **内部 API Key** (`x-internal-api-key`): 使用 `secrets.compare_digest` 做时序安全比较, 验证通过后跳过 user-id 校验
   - **JWT Bearer Token** (`authorization: Bearer xxx`): 解码 JWT, 验证 metadata 中 `user-id` 与 token `sub` claim 一致

2. **方法级认证** (`agent_grpc_service.py`): 各方法自行从 metadata 提取 `user-id`, 但**不调用任何验证函数**

**关键发现**: Go Gateway 使用内部 API Key 调用 Python gRPC (`injectMetadata` 注入 `x-internal-api-key`), 所以 AuthInterceptor 会走内部 Key 路径直接放行。这意味着:
- 内部路径信任所有从 Gateway 转发的请求
- Gateway 负责验证用户 JWT — 如果 Gateway 被绕过, Python 层完全无法检测

#### 流式生命周期 (StreamChat)

```
请求进入 → metadata 提取 → chat_mode 解析 → PromptBandit 选择
→ DB session 创建 → orchestrator.process_stream() (async generator)
→ aclosing 包装 → 逐条 yield response → commit/rollback
→ 后台: PushScheduler fire-and-forget
```

`aclosing` 确保客户端断连时 generator 的 finally 块会执行, 这是正确的资源清理模式。

#### 错误传播

- orchestrator 异常 → `build_safe_chat_error()` 转换为用户安全消息 → yield error response
- 外层 try/except 捕获所有异常, 不会让 gRPC 框架看到原始错误
- `safe_error_messages.py` 正确区分 LLM provider 错误、超时、连接错误等, 返回通用消息

### 1.2 UX Envelope (`ux_envelope.py`)

#### 展示档案体系

9 个预定义 `PresentationProfile`: standard, deep_analysis, study_plan, error_diagnosis, expert_auto, execution_delegate, aurora_core_session, 以及运行时生成的 expert:: 动态 profile。

每个 profile 定义:
- `mode_label`: 模式标签
- `companion_frame`: 伴侣框架语
- `answer_kind`: 回答类型 (direct_answer/synthesis/plan/diagnosis/...)
- `default_retry_options`: 重试选项
- `blocked_title/message`: 阻塞态文案
- `next_action_limit`: 动作数量限制

#### 自适应展示决策

`_presentation_style_decision()` 基于以下维度:
1. **verbosity** → style_variant: compact/balanced/exploratory
2. **tone** → tone_variant: warm/analytical/direct
3. **exploration level** → 影响样式
4. **session feedback signal** → simplify/expand 触发样式切换
5. **social context** → accountability contract 存在时自动切 warm
6. **soul runtime** → 关系阶段影响 companion frame

#### 阻塞态管理

`BlockedPresentationHistoryStore` 使用 Redis 记录阻塞历史:
- TTL 30 天
- 记录 `failure_kind` 出现次数
- 根据 `repeat_count` 和情感信号计算 `blocked_temperature`: gentle/guided/direct
- Redis 不可用时回退到内存 `_local_state`

#### Envelope 结构

最终 envelope 包含 4 个核心分区 + 5 个可选分区:

```
ux_turn: 意图摘要、模式、伴侣框架、双核模式
ux_result: 回答类型、置信度、完成状态、标题
ux_followthrough: 下一步动作、重试选项、恢复消息、记忆更新
ux_sources: 引用、证据、置信度
[orchestration_summary]: 编排摘要
[ux_evolution]: 系统进化信息
[continuity_banner]: 连续性横幅
[mode_explanation]: 模式解释
[collaboration_summary]: 协作摘要
```

### 1.3 工具执行器 (`executor.py`)

- DAG 分层执行: 层内并发 (Semaphore 限流 `_DAG_LAYER_MAX_CONCURRENCY=10`)
- 层间串行: 前层输出通过 `output_store` 传递给后续层
- `$ref:step_id:key` 参数占位符替换
- 工具调用上限: `_MAX_TOOL_CALLS_PER_REQUEST=20`
- 超时保护: `asyncio.wait_for` + 可配置 `timeout_seconds`
- 确认保护: `requires_confirmation` 工具需 `user_approved=True`
- 补偿机制: 工具失败时可执行补偿工具

---

## 第二部分: 问题报告

### P0 级问题 (安全/数据丢失/崩溃)

#### P0-01: StreamChat 认证绕过 — user-id 被 Metadata 直接信任

- **严重度**: P0
- **位置**: `agent_grpc_service.py:248` + `grpc_auth.py:47-59`
- **描述**: AuthInterceptor 在收到有效 `x-internal-api-key` 时直接放行, 不验证 `user-id`。Go Gateway 的 `injectMetadata` (client.go:339) 注入 `user-id` 为 `req.UserId`, 而 `req.UserId` 来自客户端请求。如果攻击者能直接访问 gRPC 端口 (50051), 只需知道 INTERNAL_API_KEY 即可伪造任意 user-id。
- **影响**: 任意用户身份冒充, 可访问/修改其他用户的对话、记忆、计划等所有数据。
- **现状缓解**: 网络层隔离 (gRPC 端口不对外暴露) + TLS/mTLS 选项存在。但在开发环境或网络配置错误时完全暴露。
- **修复建议**: 
  1. AuthInterceptor 在内部 Key 路径中应额外验证 `user-id` 格式和有效性 (如检查用户是否存在)
  2. 将 `get_verified_user_id()` 实际集成到各 gRPC 方法中 (当前已定义但从未被调用)
  3. 考虑在内部路径中将 JWT token 也透传到 Python, 进行双重验证

#### P0-02: 安全告警仅记录日志, 不阻断未认证请求

- **严重度**: P0
- **位置**: `agent_grpc_service.py:251-256`
- **描述**: 当 metadata 中没有 `authorization` 且 `request.user_id` 为空时, 仅打印 `SECURITY ALERT` 警告日志, 但请求继续正常处理。这个检查位于 AuthInterceptor 之后, 本身是冗余的 — 如果 AuthInterceptor 正常工作, 未认证请求应已被拦截。但问题在于:
  1. 这个检查逻辑暗示存在绕过 AuthInterceptor 的可能性
  2. 即使检测到无认证, 也不采取任何阻断措施
- **影响**: 如果 AuthInterceptor 存在绕过路径, 这个"安全检查"形同虚设。
- **修复建议**: 
  1. 在无认证时立即 `context.abort(grpc.StatusCode.UNAUTHENTICATED, "...")` 并 return
  2. 或完全依赖 AuthInterceptor, 删除这段冗余逻辑 (避免安全假象)
  3. 添加 Prometheus counter 追踪未认证请求

#### P0-03: get_verified_user_id 已定义但从未被使用

- **严重度**: P0
- **位置**: `grpc_auth.py:100-118`
- **描述**: `get_verified_user_id()` 函数已实现 (返回 metadata 中已由 AuthInterceptor 验证的 user-id), 但全代码库无任何调用点。所有 17 个 gRPC 方法均直接从 metadata 提取 `user-id`, 未使用此验证函数。
- **影响**: 即使 AuthInterceptor 验证了 user-id 与 JWT 一致, 下游代码仍然信任 metadata 中的原始值。如果 interceptor 实现有漏洞或被绕过, 下游完全没有二次验证。
- **修复建议**: 所有 gRPC 方法统一调用 `get_verified_user_id()` 获取用户 ID, 而非直接读取 metadata。

---

### P1 级问题 (正确性/可靠性)

#### P1-01: 内部路径跳过 user-id 验证导致冒充风险

- **严重度**: P1
- **位置**: `grpc_auth.py:47-59`
- **描述**: 当请求携带有效 `x-internal-api-key` 时, interceptor 注释写 "internal services are trusted", 直接放行而不验证 user-id。但在当前架构中, Go Gateway 转发用户请求时会带上内部 Key + 用户 user-id — interceptor 信任内部 Key 后就不再校验 user-id 合法性。
- **影响**: 如果 INTERNAL_API_KEY 泄露, 攻击者可以伪造任意 user-id 访问所有用户数据。
- **修复建议**: 内部路径也应至少验证 user-id 是否是有效 UUID, 最好检查用户是否存在于数据库。

#### P1-02: 无 process_stream 超时保护

- **严重度**: P1
- **位置**: `agent_grpc_service.py:301-310` — `self.orchestrator.process_stream()` 调用无超时
- **描述**: StreamChat 调用 `orchestrator.process_stream()` 时没有设置 `asyncio.timeout()` 或 `asyncio.wait_for()`, 完全依赖 gRPC 框架的 deadline 和 LLM 请求自身的超时。如果 orchestrator 在某个步骤卡死 (如 DB 查询死锁、Redis 连接挂起), 整个流会无限等待。
- **影响**: 
  - DB session 泄漏 (async with 管理的 session 无法释放)
  - Redis 分布式锁无法释放 (依赖锁续期任务, 但如果 event loop 被阻塞, 续期也失败)
  - 客户端看到连接挂起, 无任何错误反馈
- **修复建议**: 在 `process_stream` 调用外层包裹 `asyncio.timeout(settings.STREAM_CHAT_TIMEOUT_SECONDS)`, 默认建议 120-180 秒。

#### P1-03: SubmitContentReviewFeedback 后台任务未追踪

- **严重度**: P1
- **位置**: `agent_grpc_service.py:981` — `asyncio.create_task(run_learning())`
- **描述**: 学习分析任务通过 `asyncio.create_task()` 在后台执行, 返回的 Task 对象未被保存。如果任务抛出未捕获异常, 会被 asyncio 静默吞掉 (Python 3.11+ 会打印警告, 但不中断)。
- **影响**: 学习分析静默失败, 用户反馈无法驱动系统学习, 且无法监控任务状态。
- **修复建议**: 
  1. 将 task 保存到实例变量 (如 `self._background_tasks.add(task)`, task 完成时自动移除)
  2. 或使用 `asyncio.TaskGroup` (Python 3.11+)
  3. 添加 try/except 确保所有异常被记录

#### P1-04: 多个方法缺少 gRPC metadata 认证

- **严重度**: P1
- **位置**: 以下方法不从 metadata 提取 user-id, 仅依赖 request body:
  - `RetrieveMemory` (行 550): 仅使用 `request.user_id`
  - `GetUserProfile` (行 621): 仅使用 `request.user_id`
  - `GetWeeklyReport` (行 677): 仅使用 `request.user_id`
  - `SubmitReviewFeedback` (行 1225): 仅使用 `request.user_id`
  - `RequestRegeneration` (行 1315): 仅使用 `request.user_id`
  - `GetFeedbackStatistics` (行 1414): 仅使用 `request.user_id`
  - `GetAppealStatus` (行 1173): 完全无认证
- **描述**: 这些方法不检查 metadata 中的 user-id, 完全信任请求体中的 user_id。虽然 AuthInterceptor 验证了 JWT 或内部 Key, 但内部 Key 路径跳过了 user-id 验证 (见 P1-01), 因此这些方法的 user_id 可以被伪造。
- **影响**: 通过 Go Gateway 调用时, request.user_id 来自客户端; 攻击者可修改 request body 中的 user_id 访问其他用户数据。
- **修复建议**: 所有方法统一从 `get_verified_user_id(metadata)` 获取用户 ID, 并与 request body 中的 user_id 做交叉验证。

#### P1-05: SubmitPlanReview 错误信息泄漏

- **严重度**: P1
- **位置**: `agent_grpc_service.py:862-869`
- **描述**: `SubmitPlanReview` 的 `AioRpcError` 分支将 `e.details()` 原样返回给客户端:
  ```python
  context.set_details(e.details())
  return ... message=str(e.details())
  ```
  gRPC 内部错误详情可能包含服务名、方法名、内部状态等信息。
- **影响**: 客户端可能看到内部实现细节, 辅助攻击者理解系统结构。
- **修复建议**: 使用 `build_safe_chat_error()` 或统一返回 "Internal error"。

#### P1-06: SubmitContentReviewFeedback 错误信息泄漏

- **严重度**: P1
- **位置**: `agent_grpc_service.py:993-999`
- **描述**: 与 P1-05 相同模式, `AioRpcError` 的 `e.details()` 直接暴露给客户端。
- **修复建议**: 同 P1-05。

#### P1-07: BlockedPresentationHistoryStore 内存泄漏

- **严重度**: P1
- **位置**: `ux_envelope.py:116` — `self._local_state: dict[str, dict[str, Any]] = {}`
- **描述**: 当 Redis 不可用时, `_local_state` 作为回退存储, 但永不清除过期数据。每对 (user_id, failure_kind) 生成一个 key, 永远不会被删除。长期运行后, 内存使用量会持续增长。
- **影响**: 在 Redis 长期不可用的场景下, 进程内存会逐渐耗尽。模块级单例 `ux_envelope_builder` (行 1907) 意味着此状态在整个进程生命周期内持续累积。
- **修复建议**: 
  1. 为 `_local_state` 添加 LRU 淘汰 (如 `functools.lru_cache` 或手动限制大小)
  2. 定期清理超过 TTL 的条目
  3. 添加大小上限 (如 max 10000 条)

#### P1-08: fire-and-forget PushScheduler 使用独立 DB session 但未处理异常

- **严重度**: P1
- **位置**: `agent_grpc_service.py:363-379`
- **描述**: StreamChat 结束后, 创建独立 DB session 调用 `PushScheduler.enqueue_session_end_recall()`。虽然外层有 try/except 捕获 `SQLAlchemyError` 等, 但如果 session 创建失败 (如 DB 连接池耗尽), `AsyncSessionLocal()` 本身可能抛出异常, 且此异常在 `async with` 语句中不会被上述 except 捕获。
- **影响**: 在 DB 高负载时, StreamChat 主流程可能在 session 创建阶段报错 — 虽然这段代码在流已经结束后执行, 但会在日志中产生大量错误。
- **修复建议**: 将整个 fire-and-forget 块包裹在 `try/except Exception` 中, 确保不影响主流程。

---

### P2 级问题 (性能/质量)

#### P2-01: gRPC 方法统一 try/except 过于宽泛

- **严重度**: P2
- **位置**: 所有 gRPC 方法的最外层 `except Exception as e`
- **描述**: 每个方法的最外层 try/except 捕获所有 Exception, 包括 `TypeError`, `KeyError` 等编程错误。这会掩盖 bug, 让本应暴露的编程错误变成 "Internal error"。
- **影响**: 编程错误被隐藏, 难以在开发和测试阶段发现。
- **修复建议**: 区分业务异常 (如 `ValueError`, `SQLAlchemyError`) 和编程错误 (如 `TypeError`, `KeyError`, `AttributeError`), 编程错误应直接传播或至少触发告警。

#### P2-02: DB session 工厂每次调用创建新 session

- **严重度**: P2
- **位置**: `agent_grpc_service.py:296` — `async with self.db_session_factory() as db_session`
- **描述**: StreamChat 为每个流创建独立 DB session。在高并发场景下, 每个并发流都占用一个 DB 连接。orchestrator 内部可能还会创建额外 session。加上 fire-and-forget 的 `recall_db` session, 单次 StreamChat 最多可能占用 2-3 个 DB 连接。
- **影响**: DB 连接池 (默认通常是 10-20) 在高并发时容易耗尽。
- **修复建议**: 
  1. 增大连接池大小
  2. 为流式请求使用共享 session (需评估事务隔离级别)
  3. fire-and-forget 使用单独的小连接池

#### P2-03: UX Envelope 决策链过深

- **严重度**: P2
- **位置**: `ux_envelope.py:235-453` — `build()` 方法
- **描述**: `build()` 方法调用 20+ 个内部方法, 每个方法都从 `final_state.context_data` 中反复解析相同的字段 (`getattr(final_state, "context_data", {}) or {}`)。整个方法体约 220 行, 职责过重。
- **影响**: 维护成本高, 测试困难, 性能微劣 (重复解析)。
- **修复建议**: 
  1. 在 `build()` 入口处一次性解析 context_data, 传递给子方法
  2. 将 `build()` 拆分为更小的方法 (如 `build_turn()`, `build_result()`, `build_followthrough()`)

#### P2-04: SubmitPlanReview 多次创建 DB session

- **严重度**: P2
- **位置**: `agent_grpc_service.py:778, 804, 823`
- **描述**: `SubmitPlanReview` 在一次请求中可能创建 3 个 DB session:
  1. `handle_review_feedback` (行 778)
  2. `track_rejection` (行 804)
  3. `resume_plan_after_approval` (行 823)
- **影响**: 不必要的 DB 连接开销。
- **修复建议**: 使用单个 DB session 处理整个 review 流程, 或使用嵌套事务。

#### P2-05: executor.py 工具参数解析容错过于宽松

- **严重度**: P2
- **位置**: `executor.py:136-163` — `_coerce_arguments()`
- **描述**: 参数解析尝试 4 种候选格式 (原始、替换单引号、引用裸词值、组合), 每种都 try/except。最终如果全部失败, 返回 `{"_parse_error": "...", "_raw_preview": text[:500]}`。这个 fallback 字典会被传递给工具的 `parameters_schema(**arguments)`, 导致 ValidationError, 但原始错误信息已被吞掉。
- **影响**: 调试困难 — 需要追踪多层才能找到 JSON 解析失败的根因。
- **修复建议**: 在 `_parse_error` 场景下, 直接返回 `ToolResult(success=False)` 而非传递损坏的参数。

#### P2-06: BlockedPresentationHistoryStore 无大小上限

- **严重度**: P2
- **位置**: `ux_envelope.py:116`
- **描述**: 与 P1-07 相同问题的性能维度。`_local_state` 字典无大小限制, 每次 `record()` 调用只增不减。
- **修复建议**: 添加 `MAX_LOCAL_STATE_SIZE = 10000` 限制, 超出时淘汰最旧条目。

#### P2-07: _local_state 跨请求共享的线程安全问题

- **严重度**: P2
- **位置**: `ux_envelope.py:142-144`
- **描述**: `_local_state` 是实例变量, 在 asyncio 事件循环中被多个协程并发访问。虽然 Python 的 GIL 保证 dict 操作的原子性, 但 `get` + `set` 的组合不是原子的:
  ```python
  payload = self._local_state.get(key) or {"count": 0}  # 读取
  count = int(payload.get("count") or 0) + 1
  self._local_state[key] = {"count": count, ...}  # 写入
  ```
  两个协程可能读到相同的 count 值, 导致计数丢失。
- **影响**: 在高并发场景下, 阻塞历史计数可能不准确 (偏低)。
- **修复建议**: 此为 asyncio 单线程模型, 实际上在 `await` 之前的同步代码不会被中断。但 `_coerce_arguments` 等处有 await, 如果未来有人在这段代码中间加入 await, 就会出现竞态。建议添加注释标记为 "sync-only between get and set"。

#### P2-08: 零散的错误消息不一致

- **严重度**: P2
- **位置**: 多处
- **描述**: 不同方法对相同错误类型的错误消息不一致:
  - `SubmitReviewOverride` ValueError → "Internal error processing request" (行 1073-1074, 掩盖了 INVALID_ARGUMENT)
  - `SubmitReviewAppeal` ValueError → "Internal error processing request" (行 1159-1160, 同上)
  - 多数方法 ValueError 返回 INVALID_ARGUMENT, 但这两处返回 INTERNAL
- **影响**: 客户端无法正确处理参数错误。
- **修复建议**: 统一 ValueError → `grpc.StatusCode.INVALID_ARGUMENT`。

#### P2-09: UX Envelope 硬编码中文文案

- **严重度**: P2
- **位置**: `ux_envelope.py` 全文
- **描述**: 所有展示文案 (companion_frame, blocked_title, next_actions_title, headline 等) 均为硬编码中文。根据项目 i18n 策略 (MEMORY.md: "isChinese ? '中文' : 'English'"), 应使用 ARB l10n 系统。
- **影响**: 非中文用户看到全中文界面, 体验差。
- **修复建议**: 逐步迁移到 ARB l10n, 或至少支持中英文双语 map。

#### P2-10: _normalize_v2_response 中 event_time 使用 datetime.now() 而非 _utcnow()

- **严重度**: P2
- **位置**: `agent_grpc_service.py:152`
- **描述**: `datetime.now(UTC)` 和 `_utcnow()` 的行为差异: `_utcnow()` 使用 `datetime.now(UTC).replace(tzinfo=None)`, 而 `_normalize_v2_response` 使用 `datetime.now(UTC)` 保留时区信息。Protobuf Timestamp 的 `FromDatetime` 对有/无时区的 datetime 行为不同。
- **影响**: 可能导致时间戳不一致。
- **修复建议**: 统一使用 `_utcnow()` 或 `datetime.now(UTC)`, 保持全代码库一致。

---

## 问题汇总

| 级别 | 数量 | 问题编号 |
|------|------|----------|
| P0 | 3 | P0-01, P0-02, P0-03 |
| P1 | 5 | P1-01 ~ P1-04, P1-05 ~ P1-08 |
| P2 | 10 | P2-01 ~ P2-10 |

### 最高优先修复建议 (P0)

1. **P0-01 + P0-03**: 将 `get_verified_user_id()` 集成到所有 gRPC 方法, 替换直接的 metadata 读取。内部 Key 路径应增加 user-id 格式和存在性验证。
2. **P0-02**: 移除冗余的 SECURITY ALERT 日志, 改为 `context.abort()`, 或完全依赖 AuthInterceptor。

### 关键架构建议

1. **认证统一化**: 所有 gRPC 方法应使用统一的认证中间件或装饰器, 而非每个方法自行从 metadata 提取 user-id
2. **超时保护**: `StreamChat` 的 `process_stream` 调用必须增加整体超时 (建议 180s)
3. **后台任务管理**: 使用 TaskGroup 或 task set 管理所有 fire-and-forget 任务
4. **UX Envelope 国际化**: 逐步将硬编码中文迁移到 i18n 系统
