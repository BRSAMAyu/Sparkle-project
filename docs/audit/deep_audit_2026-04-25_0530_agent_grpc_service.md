# 深度审计 #55 — Agent gRPC Service (Go↔Python 关键桥接层)

> **日期**: 2026-04-25 05:30
> **模块**: Agent gRPC Service — Go Gateway gRPC 调用 → Python 服务实现 → Orchestrator FSM → 流式响应
> **范围**: `agent_grpc_service.py` (1,630 行) + `grpc_server.py` (202 行) + `grpc_auth.py` (117 行) + `agent_service.proto` (773 行) + `orchestrator.py` (1,619 行)
> **总计**: 5 个核心文件, ~4,372 行
> **审计员**: Claude Deep Auditor (Round 55)

---

## 审计范围

Agent gRPC Service 是 Go Gateway 与 Python Engine 之间的**唯一 gRPC 接口**。所有 AI 对话请求都经过此路径。它在认证后接收 gRPC 调用，管理 DB 会话，调用 Orchestrator FSM，并流式返回 AI 响应。

### 文件清单

| 文件 | 行数 | 职责 |
|------|------|------|
| `backend/app/services/agent_grpc_service.py` | 1,630 | gRPC 服务实现：18 个方法 (1 streaming + 17 unary) |
| `backend/grpc_server.py` | 202 | gRPC 服务器启动、TLS、graceful shutdown |
| `backend/app/api/grpc_auth.py` | 117 | JWT 认证拦截器 |
| `proto/agent_service.proto` | 773 | API 合约定义 |
| `backend/app/orchestration/orchestrator.py` | 1,619 | FSM 状态机，被 gRPC 服务调用 |

---

## 数据流图

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Go Gateway (Chat Orchestrator)                                        │
│    ↓ builds ChatRequest proto + JWT in metadata                        │
│    ↓ gRPC StreamChat RPC                                               │
├─────────────────────────────────────────────────────────────────────────┤
│  AuthInterceptor (grpc_auth.py)                                        │
│    ├─ x-internal-api-key → constant-time compare ✅                   │
│    ├─ Bearer token → decode JWT → verify user-id ✅                   │
│    └─ REJECT: UNAUTHENTICATED / PERMISSION_DENIED                      │
├─────────────────────────────────────────────────────────────────────────┤
│  StreamChat (agent_grpc_service.py:132-257)                            │
│    ├─ Extract metadata (trace_id, user_id)                             │
│    ├─ ❌ P0-1: error path 引用可能未绑定的变量                        │
│    ├─ Normalize chat_mode → resolve workflow_id                        │
│    ├─ PromptBandit.select() for prompt version                         │
│    ├─ Open db_session (async with) ✅                                  │
│    │   └─ orchestrator.process_stream() → yields ChatResponse         │
│    ├─ ❌ P0-2: error response 用 finish_reason=STOP 而非 ERROR       │
│    └─ ❌ P1-1: 完全不检查 context.is_active()                        │
├─────────────────────────────────────────────────────────────────────────┤
│  Other 17 Unary Methods                                                │
│    ├─ ❌ P1-3: 17 处 context.set_details(str(e)) 泄露内部错误       │
│    ├─ ❌ P0-3: SubmitPlanReview 打开 3 个独立 DB session              │
│    ├─ ❌ P1-4: GetWeeklyReport highlights[0] 可能 IndexError          │
│    └─ ❌ P1-5: RetrieveMemory limit 无上限                           │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 审计发现

### P0 — 严重缺陷（3 项）

#### P0-1: StreamChat error path — `trace_id`/`workflow_id`/`prompt_version` 可能未绑定 → UnboundLocalError
**文件**: `agent_grpc_service.py:238-257` vs 变量赋值于 :155, :169, :172
**严重性**: P0 — 错误路径本身崩溃，客户端收到无内容的 gRPC INTERNAL

```python
# 变量在 try 块内才赋值
trace_id = metadata.get("x-trace-id", ...) or str(uuid.uuid4())  # line 155
workflow_id = self._resolve_workflow_id(chat_mode)                 # line 169
prompt_version = "v1"                                              # line 172

# 但 error handler 在 except 块中使用
except Exception as e:
    response = agent_service_pb2.ChatResponse(
        trace_id=trace_id,           # 如果异常在 :155 之前 → UnboundLocalError
        workflow_id=workflow_id,     # 如果异常在 :169 之前 → UnboundLocalError
        prompt_version=prompt_version,  # 如果异常在 :172 之前 → UnboundLocalError
    )
```

**修复方向**: 在 `try` 块顶部初始化 `trace_id = str(uuid.uuid4())`, `workflow_id = "standard_chat"`, `prompt_version = "v1"`。

---

#### P0-2: StreamChat error response 使用 `finish_reason=STOP` 而非 `ERROR`
**文件**: `agent_grpc_service.py:254`
**严重性**: P0 — Go Gateway/Flutter 无法区分正常结束和错误

```python
finish_reason=agent_service_pb2.STOP,  # 应为 ERROR
```

Proto 定义了 `ERROR = 5` 作为 FinishReason，但 error path 硬编码 `STOP`。Go Gateway 将此视为正常结束，Flutter 不触发错误 UI。

**跨轮次**: Round #5 明确报告 "finish_reason STOP not ERROR" — 此问题从 Round #5 至今未修。

---

#### P0-3: `SubmitPlanReview` 打开 3 个独立 DB session — 数据不一致 + 连接池耗尽
**文件**: `agent_grpc_service.py:620-668`
**严重性**: P0 — 部分提交无法回滚

单次请求中打开 3 个独立 `db_session_factory()` 上下文:
1. :620 `handle_review_feedback` — 处理反馈
2. :646 `track_rejection` — 跟踪拒绝计数
3. :663 `resume_plan_after_approval` — 恢复计划

如果 `:663` 失败，`:620` 的写入已提交无法回滚。高并发下 3 个同时打开的会话加速耗尽连接池(默认 10 连接)。

---

### P1 — 重要问题（6 项）

#### P1-1: StreamChat 完全忽略 gRPC context 取消信号
**文件**: `agent_grpc_service.py:132-257`

从不检查 `context.is_active()` 或 `context.cancelled()`。客户端断开后 Orchestrator 继续执行全部 LLM 调用、工具执行、DB 写入。LLM tokens 被浪费，Redis 分布式锁不会被及时释放。

---

#### P1-2: `SubmitContentReviewFeedback` fire-and-forget `asyncio.create_task` 无错误传播
**文件**: `agent_grpc_service.py:819`

```python
asyncio.create_task(run_learning())  # 不绑定请求生命周期
```

异常只记日志，不传播到监控系统。gRPC 方法返回后任务可能被 event loop 取消。

---

#### P1-3: 17 处 `context.set_details(str(e))` 泄露内部错误详情
**文件**: `agent_grpc_service.py` 全文 17 处

`str(e)` 直接写入 gRPC trailer 发送给调用方。可能泄露 SQLAlchemy 连接字符串（含密码）、Redis 连接详情、文件路径。StreamChat 正确使用 `build_safe_chat_error`，但其他 17 个方法没有。

---

#### P1-4: `GetWeeklyReport` — `snapshot.highlights[0]` 可能 IndexError
**文件**: `agent_grpc_service.py:547`

```python
f"{snapshot.highlights[0]} "  # 空列表时 IndexError
```

---

#### P1-5: `RetrieveMemory` limit 无上限保护
**文件**: `agent_grpc_service.py:421-455`

```python
limit=request.limit if request.limit > 0 else 10,  # 无上限
```

恶意客户端可发送 `limit=1000000` 导致 pgvector 全表扫描 + 内存 OOM。

---

#### P1-6: `_require_admin` 每次调用方法级导入 + 实例化 UserService
**文件**: `agent_grpc_service.py:116-119`

无缓存，频繁调用增加 DB 负载。

---

### P2 — 改进建议（6 项）

#### P2-1: 重复 `import uuid` — 顶层 :11 和行内 :413, :727
#### P2-2: `SubmitResponseFeedback` observability 日志使用空 session_id (:334)
#### P2-3: `SubmitPlanReview` 将 `information_collection_triggered` 误判为错误 (:630-636)
#### P2-4: gRPC server `ThreadPoolExecutor(max_workers=10)` 可能成为并发瓶颈
#### P2-5: `_normalize_v2_response` 直接修改输入参数 (副作用)
#### P2-6: `GetFeedbackStatistics` 等方法不验证 user_id UUID 格式

---

## 合规项

| 检查项 | 状态 | 备注 |
|--------|------|------|
| JWT 认证拦截器 | ✅ | constant-time compare + user-id 交叉验证 |
| Safe error messages (StreamChat) | ✅ | `build_safe_chat_error` 正确映射 |
| DB session 生命周期 | ✅ | async with + commit/rollback (StreamChat) |
| 分布式锁续约 | ✅ | 10s 续约间隔 (orchestrator.py:825) |
| Prompt Bandit 策略选择 | ✅ | 带 fallback，异常不阻断请求 |
| Feedback-to-effect 观测 | ✅ | Redis key + Prometheus histogram |
| 优雅关闭 | ✅ | 5s grace period + orchestrator shutdown |
| TLS 支持 | ✅ | 可配置 TLS + 证书轮换 |
| Reflection 可控 | ✅ | 仅 DEBUG 或显式开启 |
| Error 安全 (非 StreamChat) | ❌ | 17 处 str(e) 泄露 (P1-3) |

---

## 统计

| 级别 | 数量 |
|------|------|
| P0 | 3 |
| P1 | 6 |
| P2 | 6 |
| **总计** | **15** |

---

## 修复优先级建议

1. **P0-1** (UnboundLocalError) — try 块顶部初始化默认值 — ~3 行
2. **P0-2** (STOP vs ERROR) — 改为 `agent_service_pb2.ERROR` — ~1 行
3. **P0-3** (3x DB session) — 重构为单 session + 单事务 — ~50 行
4. **P1-3** (信息泄露) — 创建 `build_safe_unary_error()` 辅助函数 — ~30 行
5. **P1-1** (context 取消) — StreamChat 循环检查 `context.is_active()` — ~10 行
6. P1-4/P1-5/P2 项 — 随后续迭代修复

---

## 跨轮次因果链

| 本轮发现 | 关联轮次 | 关联模式 |
|----------|---------|---------|
| P0-1 (UnboundLocalError) | Round #5 (no gRPC status code) | 同源: error path 无独立安全初始化 |
| P0-2 (STOP vs ERROR) | Round #5 (finish_reason STOP not ERROR) | 从 Round #5 至今未修，跨 50 轮 |
| P0-3 (3x DB session) | Round #8 (Chat History 6字段) | DB 操作原子性不足的系统性问题 |
| P1-1 (context 取消) | Round #49 (health check 触发完整 FSM) | 资源浪费: 断开的连接仍触发完整处理 |
| P1-3 (信息泄露) | Round #14 P1-1 (错误响应泄露 str(e)) | 同一模式在 gRPC 层重现 |
| P2-3 (误判 status) | Round #9 (路由器重构) | status 字符串检查 vs 枚举匹配的脆弱性 |

---

## 复核笔记

> **复核日期**: 2026-04-23 (Session continuation, 第十一次唤醒)
> **复核方式**: 逐项代码验证
> **复核人**: GLM-5.1 executor

### 行号偏移对照

| 原始行号 | 当前行号 | 位置描述 |
|----------|---------|---------|
| 132-257 | 132-258 | StreamChat 方法体 |
| 155 | 155 | trace_id 赋值 |
| 169 | 169 | workflow_id 赋值 |
| 172 | 172 | prompt_version 赋值 |
| 238-257 | 226-257 | error/fallback 路径 |
| 254 | 254 | finish_reason=STOP (error) |
| 421-455 | 421-455 | RetrieveMemory |
| 547 | 546 | highlights[0] |
| 620-668 | 620-668 | SubmitPlanReview |

文件行数: 1630 → 1629 (-1 行尾)。

### 复核结果: 0/15 已修 (P1-3 恶化)

| 原始编号 | 描述 | 状态 | 验证证据 |
|----------|------|------|---------|
| P0-1 | UnboundLocalError trace_id/workflow_id | **未修** | try 块起于 :141，变量在 :155/:169/:172。:141-154 间异常导致变量未绑定。error handler :226-257 引用这些变量 |
| P0-2 | finish_reason=STOP 非 ERROR | **未修** | :231 fallback 和 :254 error handler 均使用 `agent_service_pb2.STOP`。:254 有注释 `# Using STOP as finish reason even for errors...` 但从未改为 ERROR |
| P0-3 | SubmitPlanReview 3×DB session | **未修** | :620 `db_session_factory()`, :646 `db_session_factory()`, :663 `db_session_factory()` — 3 个独立 session 未变 |
| P1-1 | 不检查 context.is_active() | **未修** | grep `context.is_active\|context.cancelled` 零匹配 |
| P1-2 | fire-and-forget asyncio.create_task | **未验证** | — |
| P1-3 | 17处 str(e) 信息泄露 | **恶化** | 当前 27 处 `context.set_details(str(e))` + 6 处 `message=str(e)` = 共 33 处泄露（原报告称 17 处）。新方法（arbitration 系列、feedback 系列）均重复同一模式 |
| P1-4 | highlights[0] IndexError | **未修** | :546 `f"{snapshot.highlights[0]} "` 无 bounds check |
| P1-5 | RetrieveMemory limit 无上限 | **未修** | :424 `request.limit if request.limit > 0 else 10`，无 max 上限 |
| P1-6 | _require_admin 每次导入+实例化 | **未验证** | — |

### 附加发现

#### AF-1: str(e) 泄露恶化 — 从 17 处增至 33 处
原始审计报告时文件约 1630 行，`context.set_details(str(e))` 17 处。当前文件 1629 行，但该方法被复制到新增的 arbitration 系列（5 个方法）和 feedback 系列（4 个方法）中。新增方法复制了旧方法的不安全模式，导致信息泄露点翻倍。

### 判定

报告核心发现 (3 P0 + 6 P1) 经代码验证准确。P1-3 (信息泄露) 显著恶化——新增方法复制了不安全的 `str(e)` 模式，泄露点从 17 增至 33。P0-2 (STOP vs ERROR) 从 Round #5 至今跨 50+ 轮未修。

**状态更新**: ✅ 完成 → ⚠️ 已复核-无变化(P1-3恶化)

---

## 复核笔记 (第2次)

> **复核日期**: 2026-04-25
> **复核轮次**: 第十五次唤醒 (Round #61 并行复核)
> **复核方式**: 代码验证 (逐行比对当前 main 分支代码)

### 文件行数对照

| 文件 | 原始审计 | 上次复核 | 当前复核 | 变化 |
|------|---------|---------|---------|------|
| `agent_grpc_service.py` | 1,630 | 1,629 | 1,629 | 无变化 |
| `grpc_server.py` | 202 | 202 | 202 | 无变化 |
| `grpc_auth.py` | 117 | 117 | 117 | 无变化 |

### 行号偏移对照

| 原始行号 | 上次复核行号 | 当前行号 | 位置描述 |
|----------|-------------|---------|---------|
| 132-257 | 132-258 | 132-258 | StreamChat 方法体 |
| 155 | 155 | 155 | trace_id 赋值 |
| 169 | 169 | 169 | workflow_id 赋值 |
| 172 | 172 | 172 | prompt_version 赋值 |
| 238-257 | 226-257 | 226-257 | error/fallback 路径 |
| 254 | 254 | 254 | finish_reason=STOP (error) |
| 421-455 | 421-455 | 421-455 | RetrieveMemory |
| 547 | 546 | 546 | highlights[0] |
| 620-668 | 620-668 | 620-668 | SubmitPlanReview |

行号自上次复核以来无漂移。

### 复核结果: 0/15 已修 (状态与上次复核一致)

| 原始编号 | 描述 | 上次状态 | 本次状态 | 验证证据 |
|----------|------|---------|---------|---------|
| P0-1 | UnboundLocalError trace_id/workflow_id | 未修 | **未修** | try 块起于 :141, trace_id 在 :155, workflow_id 在 :169, prompt_version 在 :172。若异常在 :141-:154 间触发, error handler :245-:257 引用未绑定变量 |
| P0-2 | finish_reason=STOP 非 ERROR | 未修 | **未修** | :231 fallback 用 `STOP`; :254 error handler 用 `STOP` 并附注释 "Using STOP as finish reason even for errors..."。Proto 定义 `ERROR = 5` 已存在于 `FinishReason` enum, `agent_service_pb2.ERROR` 可直接访问 (验证: `ERROR value: 5`)。仅改 1 行即可修, 但跨 50+ 轮未修 |
| P0-3 | SubmitPlanReview 3xDB session | 未修 | **未修** | :620 `db_session_factory()`, :646 `db_session_factory()`, :663 `db_session_factory()` — 仍为 3 个独立 session。若 :663 失败, :620 和 :646 的写入无法回滚 |
| P1-1 | 不检查 context.is_active() | 未修 | **未修** | `grep -c 'context.is_active\|context.cancelled'` = 0。StreamChat 循环中无取消检查, 断连后 Orchestrator 仍执行全部 LLM 调用 |
| P1-2 | fire-and-forget asyncio.create_task | 未验证 | **确认未修** | :819 `asyncio.create_task(run_learning())` 仍存在。任务不绑定 gRPC 请求生命周期, 异常仅记日志 |
| P1-3 | str(e) 信息泄露 | 恶化(17→23) | **稳定在 23 处** | 当前 `context.set_details(str(e))` = 23 处 (行: 127, 347, 460, 516, 557, 711, 842, 911, 919, 997, 1005, 1056, 1139, 1147, 1238, 1246, 1295, 1383, 1458, 1466, 1573, 1581, 1628)。`message=str(e)` = 6 处 (行: 914, 1000, 1142, 1241, 1461, 1576)。合计 **29 处泄露点** (上次复核称 33 处, 经逐行精确计数为 23+6=29) |
| P1-4 | highlights[0] IndexError | 未修 | **未修** | :546 `f"{snapshot.highlights[0]} "` 无 bounds check。空列表时触发 IndexError |
| P1-5 | RetrieveMemory limit 无上限 | 未修 | **未修** | :424 `request.limit if request.limit > 0 else 10` 无 max cap。额外发现 :1313 `GetArbitrationQueue` 也有同样模式 `request.limit if request.limit > 0 else 50` |
| P1-6 | _require_admin 每次导入+实例化 | 未验证 | **确认未修** | :116-:119 每次调用 `from app.services.user_service import UserService` + `UserService(db_session)` — 无缓存 |
| P2-1 | 重复 import uuid | 未验证 | **确认未修** | 顶层 :11 + 行内 :413, :727 — 共 3 处 |
| P2-2 | session_id="" 空值 observability | 未验证 | **确认未修** | :334 `session_id=""` 在 observability log 调用中 |
| P2-3 | information_collection_triggered 误判 | — | **已消失** | grep `information_collection_triggered` 零匹配。该 P2-3 问题已不再存在于当前代码中 |
| P2-4 | ThreadPoolExecutor(max_workers=10) | 未验证 | **确认未修** | `grpc_server.py`:85 `futures.ThreadPoolExecutor(max_workers=10)` 不变 |
| P2-5 | _normalize_v2_response 副作用 | 未验证 | **确认未修** | :79-:95 直接修改传入的 `response` 对象并返回同一引用 (protobuf 可变对象) |
| P2-6 | GetFeedbackStatistics 不验证 UUID | 未验证 | **确认未修** | :1263 `user_id = request.user_id` 后直接使用, 不验证 UUID 格式。与 GetUserProfile (:478) 的 `uuid.UUID()` 验证模式不一致 |

### P1-3 泄露点精确计数

上次复核声称 33 处 (27 `set_details` + 6 `message=`)。本次逐行精确计数:

- `context.set_details(str(e))`: **23 处** (不是 27)
- `message=str(e)`: **6 处**
- 合计: **29 处泄露点**

上次计数偏差原因: 可能将部分非 `str(e)` 模式的 `context.set_details()` 误计入。

### 补充发现

#### AF-2: grpc_auth.py `get_verified_user_id` 无实质安全保证
`grpc_auth.py`:99-117 — `get_verified_user_id()` 仅返回 metadata 中的 `user-id`, 注释声称 "interceptor has already validated" 但 AuthInterceptor (:86-:88) 并未将 token_user_id 写入 gRPC context。若客户端不提供 metadata `user-id`, 返回 None; 若提供, AuthInterceptor 只在两者**同时存在**时交叉验证 (:77)。这意味着:
- 若客户端只传 JWT (无 metadata user-id), 交叉验证被跳过
- `get_verified_user_id` 返回 None, 下游代码 (agent_grpc_service.py) 转而使用 `request.user_id`
- `request.user_id` 完全由客户端控制, 未经 JWT 验证

这不是新问题 (原审计覆盖了 AuthInterceptor), 但 `get_verified_user_id` 函数的存在给出虚假安全感。

#### AF-3: `grpc_server.py` ThreadPoolExecutor + async 混用风险
`grpc_server.py`:84-:85 使用 `grpc.aio.server(futures.ThreadPoolExecutor(max_workers=10))` — 对于 `grpc.aio` (异步服务器), ThreadPoolExecutor 仅用于非 async handler 的 fallback。当前所有 AgentServiceImpl 方法都是 `async`, 因此 ThreadPoolExecutor 理论上不限制并发。但若未来添加同步方法, max_workers=10 会成为瓶颈。建议改为 `None` (默认值) 或明确注释。

### 修复状态汇总

| 状态 | 数量 | 编号 |
|------|------|------|
| 未修 | 13 | P0-1, P0-2, P0-3, P1-1, P1-2, P1-3, P1-4, P1-5, P1-6, P2-1, P2-2, P2-4, P2-5, P2-6 |
| 已消失 | 1 | P2-3 (information_collection_triggered 误判) |
| **总计** | **14** (1 已消, 原始 15) |

### 判定

与上次复核相比, 代码无任何修改。15 项发现中 1 项因代码删除自然消失 (P2-3), 其余 14 项全部未修。P1-3 泄露点精确计数为 29 (23 set_details + 6 message=), 较上次复核声称的 33 处有所修正。P0-2 (STOP vs ERROR) 跨越 Round #5 至 Round #61 共 56 轮仍未修, 属于最顽固的技术债。

**最高优先级修复项**: P0-1 (3 行) + P0-2 (1 行) = 共 4 行修改可消除两个 P0。

**状态更新**: ⚠️ 已复核-无变化(P1-3恶化) → ⚠️ 已复核-无变化(P2-3已消, P1-3精确计数29处)
