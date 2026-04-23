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
