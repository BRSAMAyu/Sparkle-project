# 深度审计 #49 — gRPC Client 连接管理 + Circuit Breaker + Health Check 完整链路

> **日期**: 2026-04-25 01:00
> **模块**: Go Gateway Agent Client — gRPC 连接建立 → 重试策略 → 健康检查 → 断路器保护 → 流式调用完整链路
> **范围**: `agent/client.go`（230 行）+ `agent/health_checker.go`（432 行）
> **审计员**: Claude Deep Auditor (Round 49)

---

## 审计范围

`Client` + `AgentHealthChecker` 是 Go Gateway 与 Python Engine 之间的唯一桥梁。所有聊天请求、计划审核、反馈提交都经过此客户端。断路器和健康检查决定了系统在后端不稳定时是优雅降级还是全面宕机。

### 文件清单

| 文件 | 行数 | 职责 |
|------|------|------|
| `gateway/internal/agent/client.go` | 230 | gRPC 连接 + 元数据注入 + RPC 方法 |
| `gateway/internal/agent/health_checker.go` | 432 | 健康检查 + 三态断路器 + 指标 |

**总计**: 2 核心文件, 662 行

---

## 数据流图

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Go Gateway → agent.Client → Python Engine                              │
│                                                                         │
│  连接建立:                                                              │
│    NewClient (:54-113)                                                   │
│      grpc.DialContext(cfg.AgentAddress,                                 │
│        WithBlock()              ❌ P1-2: 阻塞启动                       │
│        WithDefaultServiceConfig(retryPolicy)                            │
│          retryPolicy.MaxAttempts=4                                      │
│          RetryableStatusCodes: [UNAVAILABLE, RESOURCE_EXHAUSTED]        │
│          ❌ P1-1: RESOURCE_EXHAUSTED 不应重试(配额耗尽)                 │
│        WithKeepaliveParams(20s/10s)                                     │
│        ❌ P2-3: 无 MaxRecvMsgSize — 默认4MB                             │
│      )                                                                  │
│                                                                         │
│  健康检查 (每 10s):                                                     │
│    AgentHealthChecker.check (:152-197)                                   │
│      ctx, cancel := WithTimeout(bg, h.timeout)                          │
│      _, err = api.StreamChat(ctx, {                                     │
│        UserId: "__health_check__",                                      │
│        SessionId: "__health_check__",                                   │
│        Message: ""                                                      │
│      })                                                                 │
│      ❌ P0-1: 使用生产 StreamChat 端点做健康检查                        │
│               → Python 处理完整 FSM 流程                                │
│               → 创建 DB session                                         │
│               → 可能触发 LLM 调用                                       │
│               → 返回的 stream 未调用 CloseSend()                        │
│                                                                         │
│  断路器状态机:                                                          │
│    Closed → [failures >= 5] → Open → [timeout 30s] → HalfOpen          │
│    HalfOpen → [3 probe requests] → [success >= 2] → Closed             │
│    HalfOpen → [1 failure] → Open                                        │
│                                                                         │
│  请求路径:                                                              │
│    StreamChatWithFallback (:169-183)                                     │
│      if !AllowRequest() → ErrCircuitOpen                                │
│      stream = StreamChat(ctx, req)                                      │
│      RecordRequestResult(err)                                           │
│      ❌ P1-3: RecordRequestResult 对 stream err != nil                  │
│               但 stream 可能已部分成功（半打开状态误判）                 │
│                                                                         │
│  元数据注入:                                                            │
│    StreamChat (:185-202)                                                 │
│      md = {user-id, x-internal-api-key}                                 │
│      ✅ x-trace-id 从 OTel Span 自动提取                               │
│      ✅ otelgrpc 拦截器处理 TraceContext 传播                           │
│                                                                         │
│  全局问题:                                                              │
│    ❌ P1-4: 无 Prometheus 指标 — 断路器状态/健康延迟/请求结果不可观测   │
│    ❌ P2-1: 自定义 traceIDKey{} — 应使用 OTel 标准传播                  │
│    ❌ P2-2: onStateChange goroutine 无 panic recovery                   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 审计发现

### P0 — 严重缺陷

#### P0-1: 健康检查使用生产 StreamChat 端点 — 每 10 秒触发完整 FSM 处理流程
**文件**: `health_checker.go:152-197`
**严重性**: P0 — 健康检查本身成为系统最大负载源

```go
// :171-175 — 使用 StreamChat 做 health probe
_, err = h.client.api.StreamChat(ctx, &agentv1.ChatRequest{
    UserId:    "__health_check__",
    SessionId: "__health_check__",
    Input:     &agentv1.ChatRequest_Message{Message: ""},
})

// :424-430 — GRPCHealthClient 也用 StreamChat
func (c *GRPCHealthClient) Check(ctx context.Context) error {
    _, err := c.client.StreamChat(ctx, &agentv1.ChatRequest{
        UserId:    "__health_check__",
        SessionId: "__health_check__",
        Input:     &agentv1.ChatRequest_Message{Message: ""},
    })
    return err
}
```

**Python 端无特殊处理**：`agent_grpc_service.py:132-191` 的 StreamChat handler 对 `__health_check__` userId 没有任何短路逻辑。每个健康检查请求经过：

| 处理步骤 | 资源消耗 |
|----------|---------|
| DB session 创建 (:188) | PostgreSQL 连接 |
| Prompt bandit 选择 (:174) | Redis 查询 |
| `orchestrator.process_stream()` (:191) | FSM 初始化 + 状态加载 |
| 上下文组装 | Redis + DB 查询 |
| 可选 LLM 调用 | API Token 消耗 |

**量化影响**:
- 默认间隔 10 秒 → **6 次/分钟 × 60 = 360 次/小时**
- 每次 DB session + Redis 查询 + FSM 初始化
- 返回的 stream 对象赋值给 `_` (丢弃)，**未调用 `CloseSend()`** → Python 端 stream 资源直到 context 超时才释放
- 如果 Python 端 LLM 调用了空消息，每次消耗 tokens（取决于 orchestrator 对空消息的处理）

**与 Round #2 P0-2 的关联**: 健康检查请求的 `context_data` 也会在 FSM 中累积，如果 FSM 创建了 `__health_check__` 用户的 session，这些 session 也会被持久化到 DB。

**修复方向**: (1) 实现 gRPC 标准 `grpc.health.v1.Health` 服务（Python 端返回 SERVING）；(2) 或在 Python StreamChat 中添加 `__health_check__` 短路（直接返回空响应而不经过 FSM）。

---

### P1 — 重要问题

#### P1-1: gRPC 重试策略包含 RESOURCE_EXHAUSTED — 配额耗尽时重试是反生产
**文件**: `client.go:81-93`
**严重性**: P1 — 加剧配额问题

```go
retryPolicy := `{
    "methodConfig": [{
        "name": [{"service": "agent.v1.AgentService"}],
        "waitForReady": true,
        "retryPolicy": {
            "MaxAttempts": 4,
            "RetryableStatusCodes": ["UNAVAILABLE", "RESOURCE_EXHAUSTED"]
        }
    }]
}`
```

`RESOURCE_EXHAUSTED` 在 Sparkle 系统中通常表示用户日配额耗尽（见 Round #47 P0-1）。重试配额耗尽请求：
1. 不会成功（配额不变）
2. 浪费 4 次重试的延迟（总计 ~21s 退避）
3. 在 Round #47 的配额泄漏问题下，可能进一步加速配额耗尽

**修复方向**: 从 `RetryableStatusCodes` 中移除 `RESOURCE_EXHAUSTED`，仅保留 `UNAVAILABLE`。

---

#### P1-2: `WithBlock()` 在连接建立中阻塞 Gateway 启动
**文件**: `client.go:95-97`
**严重性**: P1 — 启动顺序耦合

```go
conn, err := grpc.DialContext(ctx,
    cfg.AgentAddress,
    grpc.WithBlock(),  // ← 阻塞直到连接建立或超时
)
```

`WithBlock()` 使 `NewClient` 阻塞直到 gRPC 连接建立（或 `GRPCTimeoutSeconds` 超时，默认 5s）。如果 Python 后端启动慢于 Go Gateway：
- Gateway 启动失败 → 整个系统无法启动
- Docker Compose 中 `depends_on` 仅保证容器启动，不保证服务就绪

**修复方向**: 移除 `WithBlock()`，依赖 `WithKeepaliveParams` 的连接管理。健康检查器会在后台探测连接状态。

---

#### P1-3: `RecordRequestResult` 对 stream 调用仅检查初始错误 — 半成功 stream 被误判
**文件**: `client.go:169-183`, `health_checker.go:313-334`
**严重性**: P1 — 断路器状态不准确

```go
// client.go:175-179
stream, err := c.StreamChat(ctx, req)
if c.healthChecker != nil {
    c.healthChecker.RecordRequestResult(err)  // ← 仅检查 err，不检查 stream 中途失败
}
```

`StreamChat` 是 server-side streaming。`err == nil` 仅表示 stream 成功建立，不代表 stream 传输完成。如果：
1. Stream 建立成功 (`err == nil`) → `RecordRequestResult(nil)` → 记录成功
2. Stream 传输过程中 Python 崩溃 → 断路器不感知

断路器会认为请求成功，即使客户端只收到了部分响应。连续的 Python 崩溃不会触发断路器打开。

**修复方向**: 在 `chat_orchestrator_chatflow.go` 的流处理循环中，对流中断/错误也调用 `RecordRequestResult`。

---

#### P1-4: 断路器状态和健康检查指标未暴露给 Prometheus — 不可观测
**文件**: `health_checker.go:360-387`
**严重性**: P1 — 运维盲区

```go
// :360-387 — 仅提供 JSON 结构体，无 Prometheus 导出
type HealthCheckerMetrics struct {
    IsHealthy       bool          `json:"is_healthy"`
    CircuitState    string        `json:"circuit_state"`
    FailureCount    int           `json:"failure_count"`
    ...
}
```

`GetMetrics()` 返回结构体用于 HTTP API，但没有导出为 Prometheus gauge/counter：
- 断路器何时打开/关闭 → 无告警
- 健康检查延迟趋势 → 无基线
- 请求成功/失败率 → 无仪表盘

**修复方向**: 添加 `sparkle_grpc_circuit_state` (Gauge: 0=closed, 1=half-open, 2=open) + `sparkle_grpc_health_check_latency` (Histogram) + `sparkle_grpc_request_result_total` (Counter by status)。

---

### P2 — 改进建议

#### P2-1: 自定义 `traceIDKey{}` 上下文键 — 应使用 OTel 标准传播

```go
// :36-52 — 自定义 context key 传递 trace ID
type traceIDKey struct{}
func WithTraceID(ctx context.Context, traceID string) context.Context {
    return context.WithValue(ctx, traceIDKey{}, traceID)
}
```

但 `StreamChat` (:193-195) 已经从 OTel span 自动提取 trace ID：
```go
if span := trace.SpanFromContext(ctx); span.SpanContext().IsValid() {
    md.Set("x-trace-id", span.SpanContext().TraceID().String())
}
```

自定义 `traceIDKey` 是冗余的。otelgrpc 拦截器已自动传播 trace context。

---

#### P2-2: `onStateChange` 回调在 goroutine 中运行无 panic recovery

```go
// :251
if h.onStateChange != nil {
    go h.onStateChange(oldState, newState)  // ← 无 recover()
}
```

如果回调 panic，goroutine 静默崩溃，后续状态变更不再触发回调。

---

#### P2-3: 无 `MaxRecvMsgSize` 配置 — 默认 4MB 限制

```go
// :95-105 — DialContext 选项中无 MaxCallRecvMsgSize
conn, err := grpc.DialContext(ctx, cfg.AgentAddress,
    grpc.WithTransportCredentials(creds),
    grpc.WithBlock(),
    // 缺失: grpc.WithDefaultCallOptions(grpc.MaxCallRecvMsgSize(8*1024*1024))
)
```

如果 Python 发送的 `ChatResponse` 超过 4MB（见 Round #2 P0-2 context_data 增长），gRPC 客户端会报 `RESOURCE_EXHAUSTED`。

---

## 合规项

| 检查项 | 状态 |
|--------|------|
| TLS 支持 | ✅ 可选 TLS + CA cert + ServerName 验证 (:64-78) |
| Keepalive 配置 | ✅ 20s ping / 10s timeout / permit without stream (:100-104) |
| OTel 追踪集成 | ✅ otelgrpc client handler 自动传播 trace context (:98) |
| 断路器三态 | ✅ Closed/Open/HalfOpen 完整实现 (:17-26) |
| 断路器参数可配置 | ✅ FailureThreshold/SuccessThreshold/Timeout/HalfOpenRequests 均可配置 (:42-51) |
| 内部 API Key 传递 | ✅ 所有 RPC 方法注入 x-internal-api-key (:189, :208, :222) |
| 连接优雅关闭 | ✅ Close() 先停健康检查再关连接 (:136-143) |
| Panic recovery | ✅ 健康检查中有 recover() 处理 (:163-166) |

---

## 统计

| 级别 | 数量 |
|------|------|
| P0 | 1 |
| P1 | 4 |
| P2 | 3 |
| **总计** | **8** |

---

## 修复优先级建议

1. **P0-1** (健康检查用 StreamChat) — 实现 `grpc.health.v1.Health` 或 Python 端短路 `__health_check__` — ~50 行 Python + ~20 行 Go
2. **P1-1** (重试包含 RESOURCE_EXHAUSTED) — 从 RetryableStatusCodes 移除 — ~1 行
3. **P1-2** (WithBlock 阻塞启动) — 移除 WithBlock — ~1 行
4. **P1-3** (RecordRequestResult 仅检查初始 err) — 在 chatflow 流中断时也记录失败 — ~10 行
5. **P1-4** (无 Prometheus 指标) — 添加 Gauge/Counter/Histogram — ~30 行
6. P2-1/P2-2/P2-3 — 随后续迭代修复

---

## 跨轮次因果链

| 本轮发现 | 关联轮次 | 关联模式 |
|----------|---------|---------|
| P0-1 (健康检查触发完整 FSM) | Round #2 P0-2 (context_data 无限增长) | `__health_check__` 用户的 context_data 也在累积 |
| P1-1 (重试 RESOURCE_EXHAUSTED) | Round #47 P0-1 (配额不退还) | 重试配额耗尽请求加剧配额泄漏 |
| P1-3 (stream 中途失败不记录) | Round #2 P1-6 (无 DoneEvent) | stream 中断时断路器不感知 + Flutter 不收到完成信号 |
| P2-3 (无 MaxRecvMsgSize) | Round #2 P0-2 (context_data 无限增长) | 5MB context_data 超过 4MB gRPC 默认限制 |

---

## 复核笔记

> **复核日期**: 2026-04-25
> **复核轮次**: 第十次唤醒 (Round #56 并行复核)
> **复核方式**: 代码验证 — 逐条对照当前 main 项目源码

### 复核结果: 0/8 已修

| 原始编号 | 描述 | 状态 | 备注 |
|----------|------|------|------|
| P0-1 | 健康检查使用生产 StreamChat 端点 | ❌ 未修 | `health_checker.go:171-175` 仍用 `StreamChat` + `__health_check__` userId 做探针。Python 端 `agent_grpc_service.py` 无任何 `__health_check__` 短路逻辑。无 `grpc.health.v1.Health` 标准服务实现。返回的 stream 赋值给 `_` 仍无 `CloseSend()` 调用。`GRPCHealthClient.Check()` (line 424-430) 同样使用 StreamChat。行号与原报告一致（check 在 :152-197，GRPCHealthClient 在 :424-430）。 |
| P1-1 | 重试策略包含 RESOURCE_EXHAUSTED | ❌ 未修 | `client.go:90` `RetryableStatusCodes` 仍为 `["UNAVAILABLE", "RESOURCE_EXHAUSTED"]`。行号与原报告一致（:81-93）。 |
| P1-2 | WithBlock() 阻塞 Gateway 启动 | ❌ 未修 | `client.go:97` 仍有 `grpc.WithBlock()`。行号与原报告一致（:95-97）。 |
| P1-3 | RecordRequestResult 仅检查初始 err | ❌ 未修 | `client.go:178-179` 仍在 StreamChatWithFallback 中仅对初始 `err` 调用 `RecordRequestResult(err)`。`chat_orchestrator_chatflow.go:426-436` 流中断处理（`stream.Recv()` 错误）中无任何对 `RecordRequestResult` 的调用。断路器无法感知中途 stream 失败。 |
| P1-4 | 断路器指标未暴露给 Prometheus | ❌ 未修 | `health_checker.go:360-387` `HealthCheckerMetrics` 仍仅为 JSON 结构体。agent 包中无任何 `prometheus`、`NewGauge`、`NewCounter`、`NewHistogram` 导入或定义。Go Gateway 其他模块（`wsmetrics`）已有 Prometheus 集成，但 agent 包完全没有。 |
| P2-1 | 自定义 traceIDKey{} 冗余 | ❌ 未修 | `client.go:36-52` `traceIDKey{}`、`WithTraceID()`、`traceIDFromContext()` 仍存在。`StreamChat` (:191-195) 已有 OTel span 自动提取。两套机制共存。 |
| P2-2 | onStateChange goroutine 无 panic recovery | ❌ 未修 | `health_checker.go:251` `go h.onStateChange(oldState, newState)` 仍无 `recover()`。对比：同文件 :163-166 的 `check()` 函数有 panic recovery，但状态变更回调没有。 |
| P2-3 | 无 MaxRecvMsgSize 配置 | ❌ 未修 | `client.go:95-105` `grpc.DialContext` 选项中仍无 `grpc.WithDefaultCallOptions(grpc.MaxCallRecvMsgSize(...))`。无任何搜索命中 `MaxRecvMsgSize` 或 `MaxCallRecvMsgSize`。 |

### 复核附加发现

#### AF-1: 文件行数与原报告一致但行号标签微调
- `client.go`: 原报告标注 230 行，实际 230 行 ✅
- `health_checker.go`: 原报告标注 432 行，实际 431 行（差 1 行，可能是末尾换行差异）
- 所有原报告引用的行号范围经验证仍准确匹配当前代码

#### AF-2: chat_orchestrator_chatflow.go 中存在语义相关但不完整的断路器标记
- `chat_orchestrator_chatflow.go:576-580` 有 `breaker_status` 元数据字段（基于 `chatHistory.GetQueueLength` 阈值），但这是 **chat history 队列**的断路器，与 agent client 的 **gRPC 断路器**（`AgentHealthChecker.CircuitState`）是完全不同的系统
- gRPC 断路器状态未注入到此 metadata 中，运维层面无法区分两种断路器的触发源

#### AF-3: health.go 消费 AgentHealthChecker 但仅用于 HTTP 健康端点
- `handler/health.go:274-290` 读取 `healthChecker.GetStatus()` 用于 `/api/v1/health` HTTP 端点
- 该端点返回 JSON 格式的健康状态，但无 Prometheus metrics 导出
- 确认 P1-4 的观测：有结构化状态数据，但无时间序列指标

#### AF-4: GRPCHealthClient 独立连接存在 WithBlock 问题
- `health_checker.go:401-408` `NewGRPCHealthClient` 同样使用 `grpc.WithBlock()` + `grpc.DialContext` 带 5s 超时
- 这是 P1-2 (WithBlock) 的重复实例，但此处用于专用健康检查客户端连接
- 如果 Python 后端不可达，此客户端创建也会阻塞 5s

### 跨轮次因果链更新

| 因果链 | 状态 | 备注 |
|--------|------|------|
| P0-1 ↔ Round #2 P0-2 (context_data 增长) | ⚠️ 仍活跃 | 健康检查每 10s 触发 StreamChat，Python 端仍无短路。若 FSM 为 `__health_check__` 创建 session，session 数据仍在累积。需 Python 端确认是否创建 session。 |
| P1-1 ↔ Round #47 P0-1 (配额不退还) | ⚠️ 仍活跃 | RESOURCE_EXHAUSTED 重试未移除。如果配额耗尽仍会触发 4 次重试（约 21s 退避）。 |
| P1-3 ↔ Round #2 P1-6 (无 DoneEvent) | ⚠️ 仍活跃 | stream 中断时断路器不感知。chat_orchestrator_chatflow.go 有 `FinishReason_STOP` 的 doneResp 发送（:595-614），但这是正常完成路径。中断路径（:426-436）仅发 error 无 doneResp，也不通知断路器。 |
| P2-3 ↔ Round #2 P0-2 (context_data 超限) | ⚠️ 仍活跃 | 无 MaxRecvMsgSize 配置。如果 context_data 超过 4MB gRPC 默认限制，客户端会收到 RESOURCE_EXHAUSTED，又因 P1-1 会触发重试，形成恶性循环。 |

### 综合评估

8 项发现全部未修。代码与原审计时完全一致（行号精确匹配）。优先级建议不变：

1. **P0-1** 仍是最紧急项 — 每 10s 触发完整 FSM 的健康检查是系统最大的隐式负载源
2. **P1-1 + P2-3** 组合形成恶性循环风险 — 大 payload 触发 RESOURCE_EXHAUSTED → 重试 4 次 → 加剧负载
3. **P1-3** 使断路器形同虚设 — 流式调用中途失败不记录，断路器无法对真实的 Python 崩溃做出反应
