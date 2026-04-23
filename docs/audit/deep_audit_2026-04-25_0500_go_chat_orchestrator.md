# 深度审计 #53 — Go Chat Orchestrator WebSocket→gRPC 完整链路

> **日期**: 2026-04-25 05:00
> **模块**: Go Gateway Chat Orchestrator — Flutter WebSocket 接入 → 消息校验 → gRPC 代理 → 响应流回传
> **范围**: 13 文件, ~5,166 行
> **审计员**: Claude Deep Auditor (Round 53)

---

## 审计范围

Go Gateway Chat Orchestrator 是 Flutter 客户端与 Python gRPC 后端之间的核心桥接层。每个用户聊天消息都经过此路径：WebSocket 接收 → 输入校验 → gRPC 流式调用 → 响应回传。

### 文件清单

| 文件 | 行数 | 职责 |
|------|-------|------|
| `handler/chat_orchestrator.go` | 566 | 主 WebSocket handler：升级、生命周期、消息循环 |
| `handler/chat_orchestrator_chatflow.go` | 653 | 核心聊天流：配额、缓存、gRPC 流、持久化 |
| `handler/chat_orchestrator_connections.go` | 52 | 连接注册/注销薄委托 |
| `handler/chat_orchestrator_protocol.go` | 644 | envelope 解析、protobuf handler、响应转换 |
| `handler/chat_orchestrator_responder.go` | 354 | envelope/protobuf 响应器实现 |
| `handler/chat_orchestrator_feedback.go` | 841 | action/intervention/response/plan review feedback handlers |
| `handler/ws_safe_writer.go` | 62 | Channel-based WebSocket 写锁 |
| `handler/ws_registry.go` | 166 | 连接注册表，带排空功能 |
| `handler/websocket_proxy.go` | 291 | 社群/个人 WS 双向代理 |
| `handler/websocket_factory.go` | 94 | 带源检查的 WS 升级器工厂 |
| `agent/client.go` | 230 | 带 circuit breaker 的 gRPC 客户端 |
| `agent/health_checker.go` | 432 | Circuit breaker + health probe |
| `middleware/rate_limit.go` | 521 | HTTP 级别速率限制 |

**总计**: 13 核心文件, ~5,166 行

---

## 数据流图

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Flutter Client → WebSocket → Go Chat Orchestrator → gRPC → Python    │
│                                                                         │
│  HandleWebSocket (chat_orchestrator.go:144)                             │
│    ├── Upgrade + Auth check + Register                                  │
│    ├── ❌ P0-1: Legacy feedback paths use raw conn (race condition)    │
│    └── Message Loop (line 286)                                         │
│         ├── Binary Protobuf → handleProtobufMessage → protobufResponder│
│         ├── Envelope JSON → parseEnvelopeJSON → envelopeResponder      │
│         └── Legacy JSON → msgMap routing:                              │
│              ├── ping/pong                                              │
│              ├── action_feedback → handleActionFeedback (RAW conn!)    │
│              ├── intervention_feedback                                  │
│              ├── response_feedback                                     │
│              ├── plan_review_feedback                                   │
│              ├── focus_completed                                        │
│              └── message → handleChatMessage                            │
│                                                                         │
│  handleChatMessage (chatflow.go:141)                                    │
│    ├── Sanitize (bluemonday) + Persist user msg                        │
│    ├── User context fetch                                              │
│    ├── Semantic cache check                                            │
│    ├── Quota check + reserve                                           │
│    │   └── ⚠️ P1-7: CJK token estimation 1.5x (should be 2.5x)       │
│    └── Build ChatRequest proto                                         │
│                                                                         │
│  agentClient.StreamChatWithFallback (agent/client.go:169)              │
│    ├── Circuit breaker check                                           │
│    └── gRPC StreamChat (server-streaming)                              │
│         └── ❌ P0-2: Health probe uses StreamChat with empty msg       │
│                                                                         │
│  Stream Loop (chatflow.go:416)                                         │
│    ├── Recv() each response                                            │
│    ├── Accumulate text, track tokens                                   │
│    ├── Segment-based quota enforcement                                 │
│    ├── Forward to responder (envelope/protobuf/legacy)                 │
│    └── On EOF: send done + meta                                        │
│                                                                         │
│  Async: semantic cache update (context.Background!), chat history      │
│    └── ⚠️ P1-6: Detached context for async goroutines                  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 审计发现

### P0 — 严重缺陷（3 项）

#### P0-1: Legacy 反馈路径直接在原始 conn 上写入 — 并发写竞态条件
**文件**: `chat_orchestrator.go:347,350,353,356,362` + `chat_orchestrator_feedback.go:77,608,833`
**严重性**: P0 — WebSocket 帧交错导致数据损坏或 panic

```go
// chat_orchestrator.go:347 — 传递 raw conn 而非 writer
h.handleActionFeedback(conn, msgMap, userID, authToken)

// chat_orchestrator_feedback.go:77 — raw conn.WriteJSON，无锁
s.conn.WriteJSON(statusMsg)

// chat_orchestrator_feedback.go:608
conn.WriteJSON(statusMsg)

// chat_orchestrator_feedback.go:833
conn.WriteJSON(map[string]interface{}{...})
```

gorilla/websocket 文档明确声明："Connections support one concurrent writer and one concurrent reader." Legacy 反馈路径传递 `*websocket.Conn` 而非 `*wsSafeWriter`，与主读循环和 ping goroutine 并发写入同一连接。

**受影响的类型**: `legacyActionStatusSender`, `legacyUpdateNodeResponder`, `legacyInterventionResponder`, `legacyResponseFeedbackResponder`, `legacyPlanReviewStatusSender`

**修复方向**: 将 `*wsSafeWriter` 传递给所有 legacy 反馈 handler，替换 `legacyXxxSender` 结构体封装 `*wsSafeWriter`。

---

#### P0-2: Health Checker 探测使用 StreamChat + 空消息 — 泄漏 gRPC 流 + 污染数据
**文件**: `agent/health_checker.go:171-175`
**严重性**: P0 — 每次探测泄漏一个服务端流

```go
_, err = h.client.api.StreamChat(ctx, &agentv1.ChatRequest{
    UserId:    "__health_check__",
    SessionId: "__health_check__",
    Input:     &agentv1.ChatRequest_Message{Message: ""},
})
```

**问题**:
1. 空消息可能触发 Python orchestrator 的 LLM 调用或错误路径
2. `__health_check__` 作为 user/session ID 可能被持久化到 Redis/PG
3. 响应流从未被消费（`_, err = ...` 忽略了流）——每次探测泄漏一个 gRPC 流
4. 30 秒间隔 × 24 小时 = 每天 2,880 个泄漏流

**修复方向**: 实现专用的轻量 `Health` RPC，或使用 gRPC 标准 health checking protocol。至少在接收第一个响应后立即关闭流。

---

#### P0-3: 消息级速率限制器默认值过于激进 — 1 RPS / burst 1 导致合法连接被断开
**文件**: `chat_orchestrator.go:281` + 默认值 fallback
**严重性**: P0 — 过度限制，用户发送反馈后 1 秒内发下一条消息即被断开

```go
msgLimiter := rate.NewLimiter(rate.Limit(msgRate), msgBurst)

// 当配置未设置时:
if msgRate <= 0 { msgRate = 1 }    // 1 RPS
if msgBurst <= 0 { msgBurst = 1 }  // burst of 1
```

**影响**: 用户在发送 feedback 后 1 秒内发送下一条聊天消息，连接被关闭。配置默认值使这极易发生。且速率限制事件无指标、无日志——完全静默。

**修复方向**: (1) 将默认值提高到至少 5 RPS / burst 10；(2) 接近限制时记录 warning；(3) 发送错误消息而非立即关闭连接。

---

### P1 — 重要问题（7 项）

#### P1-1: `shouldClose` 闭包中 `span.End()` 生命周期过长
**文件**: `chat_orchestrator.go:410-418, 431-437`
**严重性**: P1 — 长时间跨度的 span 对遥测后端施压

```go
ctx, span := tracer.Start(msgCtx, "HandleMessage")
defer span.End()
return h.handleChatMessage(ctx, writer, userID, input, input.RequestID)
```

对于聊天消息，span 保持打开直到 chatflow 完成（可达 300 秒），在 OTel 后端产生超长持续时间的 span。

**修复方向**: 在循环顶部为每条消息创建独立 span，调用 `handleChatMessage` 前结束外层 span。

---

#### P1-2: 流接收循环创建无用 span — 无属性记录
**文件**: `chat_orchestrator_chatflow.go:418-419, 489`
**严重性**: P1 — 无用 span 产生收集开销

```go
_, streamSpan := tracer.Start(ctx, "stream.receive")
resp, err := stream.Recv()
streamSpan.End()  // 无任何属性，无错误状态
```

**修复方向**: 添加有意义的属性（响应类型、字节数、错误），或删除这些 span。

---

#### P1-3: ping goroutine 关闭连接后 defer 再次 Close — 双重关闭
**文件**: `chat_orchestrator.go:192-195, 234`
**严重性**: P1 — 关闭路径上嘈杂的错误日志

```go
// 空闲计时器触发时直接 Close
conn.Close()  // line 234

// defer 再次尝试写入 Close frame + Close
defer func() {
    _ = writer.WriteMessage(websocket.CloseMessage, ...)  // 在已关闭连接上写
    _ = conn.Close()  // 二次关闭
}()
```

**修复方向**: 使用 `sync.Once` 或原子布尔值确保只执行一次关闭序列。

---

#### P1-4: 无基于 request_id 的去重 — 重试导致配额超额扣减
**文件**: `chat_orchestrator_chatflow.go:233-236`
**严重性**: P1 — 幂等性缺失

```go
reqID := requestID
if reqID == "" {
    reqID = fmt.Sprintf("req_%s", uuid.New().String())
}
```

客户端重试时无检测重复请求机制。无 request_id 的客户端始终获得新 ID。重复请求导致配额超额扣减。

**修复方向**: 在配额键中添加基于 reqID 的 Redis 去重检查 `quota:used:{userID}:{reqID}`。

---

#### P1-5: 语义缓存 scope 使用 SHA-1 12 字符哈希 — 碰撞导致跨用户污染
**文件**: `chat_orchestrator_chatflow.go:35-44`
**严重性**: P1 — 安全降级

```go
func shortHash(parts ...string) string {
    h := sha1.New()
    // ...
    return hex.EncodeToString(h.Sum(nil))[:12]  // 48-bit
}
```

12 字符（48 位）哈希在百万级 scope 中碰撞概率不可忽略。碰撞导致错误的缓存命中——用户 A 获取用户 B 的缓存响应。

**修复方向**: 使用 SHA-256，至少提取 16-24 个 hex 字符（64-96 位）。

---

#### P1-6: 异步保存和缓存更新使用 `context.Background()` — 追踪链断裂 + goroutine 泄漏风险
**文件**: `chat_orchestrator_chatflow.go:169, 627-634`
**严重性**: P1 — 无超时 + 无追踪传播

```go
// :169 — 异步保存用户消息
go h.saveMessage(userID, sessionID, "user", message)  // context.Background()

// :627-634 — 异步更新语义缓存
go func() {
    if h.semantic != nil {
        if err := h.semantic.SetExact(context.Background(), ...); err != nil {
```

**影响**: Redis 阻塞时 goroutine 无限期挂起。分布式追踪链断裂。

**修复方向**: 使用 `context.WithTimeout` (5 秒超时) 代替 `context.Background()`。

---

#### P1-7: CJK 文本配额估算使用 1.5x 乘数 — 低估 30-50%
**文件**: `chat_orchestrator_chatflow.go:415, 464, 640-649`
**严重性**: P1 — 中文用户配额消耗被少报

```go
func estimateTokensFromRunes(runes int) int64 {
    estimated := int64(float64(runes) * 1.5)
```

CJK 文本每个 rune 产生 2-3 个 token，而非 1.5。中文文本的配额段过早触发，可能导致响应流被提前截断。

**修复方向**: 对 CJK 文本使用 2.5 乘数，或强制 Python 始终发出 `usage` 字段。

---

### P2 — 改进建议（7 项）

#### P2-1: `msgType` 变量遮蔽 WebSocket 消息类型
**文件**: `chat_orchestrator.go:288, 336`
Go 作用域规则使功能正确，但内部 `msgType`（string JSON type）遮蔽外部 `msgType`（int WebSocket frame type）。

#### P2-2: `chatInputPool` sync.Pool 残留数据风险
**文件**: `chat_orchestrator.go:80-89`
`Reset()` 将 `ExtraContext` 设为 nil，阻止旧 map 的 GC 回收。

#### P2-3: DefaultUpgrader 允许所有 Origin — 生产环境风险
**文件**: `websocket_factory.go:54-62`
`isDevelopmentEnv()` 在 `ENVIRONMENT` 为空时返回 true。未设置环境变量时所有 WebSocket 连接使用不安全升级器。

#### P2-4: Tool Call Arguments 未经过 sanitizer 清洗
**文件**: `chat_orchestrator_protocol.go:96-103`
Delta 文本经过 `sanitizer.Sanitize()` 清洗，但 `ToolCall.Arguments` 直接通过，潜在 XSS 向量。

#### P2-5: wsSafeWriter 使用 buffered channel 而非 sync.Mutex — 性能较低
**文件**: `ws_safe_writer.go:16-32`
Buffered channel 作为互斥锁比 `sync.Mutex` 慢，高争用下增加延迟。

#### P2-6: ws_registry DrainAll 未从 signalHub 注销 — 关闭时资源泄漏
**文件**: `ws_registry.go:135-166`
`DrainAll` 关闭所有连接但未调用 `signalHub.Unregister()`，关闭时残留 writer。

#### P2-7: 配额限制从环境变量读取绕过结构化配置
**文件**: `chat_orchestrator_chatflow.go:306`
`getEnvInt64("DAILY_QUOTA", 100000)` 直接读环境变量，绕过 config struct 及其验证。

---

## 合规项

| 检查项 | 状态 | 备注 |
|--------|------|------|
| WebSocket 输入清洗 | ⚠️ 部分 | Chat messages 有 bluemonday 清洗；tool arguments 未清洗 (P2-4) |
| 消息长度限制 | ✅ | 4,000 字符限制 (chat_orchestrator.go:102) |
| 读取大小限制 | ⚠️ 条件 | 仅在 `WS_MAX_MESSAGE_BYTES` 设置时生效 |
| 认证检查 | ✅ | handler 顶部检查 user_id |
| 源检查 | ⚠️ 条件 | 依赖配置，回退到不安全 (P2-3) |
| 速率限制 | ⚠️ 条件 | 存在但默认过于激进 (P0-3) |
| Circuit Breaker | ✅ | 通过 health_checker.go 实现 |
| 资源清理 | ⚠️ 条件 | 双重关闭 (P1-3), DrainAll 未注销 signalHub (P2-6) |
| 并发写安全 | ❌ | Legacy 路径绕过 wsSafeWriter (P0-1) |
| 错误传播 | ✅ | 所有错误路径发送响应并记录日志 |
| 分布式追踪 | ⚠️ 条件 | 断裂的 span (P1-2) + 脱离的 context (P1-6) |
| 配额强制执行 | ⚠️ 条件 | CJK 乘数错误 (P1-7), 无去重 (P1-4) |

---

## 统计

| 级别 | 数量 |
|------|------|
| P0 | 3 |
| P1 | 7 |
| P2 | 7 |
| **总计** | **17** |

---

## 修复优先级建议

1. **P0-1** (Legacy 写竞态) — 替换所有 `legacyXxxSender` 封装 `*wsSafeWriter`，~6 个调用点
2. **P0-2** (Health probe 流泄漏) — 实现专用 Health RPC 或立即取消流
3. **P0-3** (速率限制默认值) — 默认值提高到 5 RPS / burst 10
4. **P1-6** (脱离 context) — `context.Background()` → `context.WithTimeout` (5s)
5. **P1-4** (请求去重) — Redis 去重检查
6. **P1-5** (SHA-1 哈希) → SHA-256, 16+ hex chars
7. **P1-7** (CJK token 估算) — 乘数提高到 2.5 或强制 actual token count
8. P1-1/P1-2/P1-3 — span 生命周期 + 双重关闭清理
9. P2 项 — 随后续迭代修复

---

## 跨轮次因果链

| 本轮发现 | 关联轮次 | 关联模式 |
|----------|---------|---------|
| P0-1 (Legacy 写竞态) | Round #14 P0-1 (WS proxy 零校验) | Chat orchestrator 比代理好（有校验），但 legacy feedback 路径仍有并发写 bug |
| P0-3 (速率限制默认值) | Round #6 P0-1 (Token bucket 1000x) | Token bucket 修复了，但现在默认 1 RPS/1 burst — 反向极端 |
| P0-2 (Health probe 流泄漏) | Round #49 (gRPC Client + CB) | Circuit breaker 改进了，但 health probe 泄漏流 |
| P1-7 (配额估算) | Round #47 (ChatOrchestrator chatflow) | Python 侧 quota/estimation 问题在 Go 侧同样存在 |
| P2-4 (Tool args 未清洗) | Round #14 P2-2 (Flutter 无 maxLength) | 后端有了 maxLength，但 tool arguments 未清洗 |

---

## 复核笔记

> **复核日期**: 2026-04-25
> **复核轮次**: 第十四次唤醒 (Round #60 并行复核)
> **复核方式**: 代码验证 — 对比 MAIN 分支当前代码与原始审计发现
> **复核员**: Claude Deep Auditor

### 文件行数核对

| 文件 | 原报告行数 | 当前行数 | 行号偏移 |
|------|-----------|---------|---------|
| `chat_orchestrator.go` | 566 | 566 | 无偏移 |
| `chat_orchestrator_chatflow.go` | 653 | 653 | 无偏移 |
| `chat_orchestrator_connections.go` | 52 | 52 | 无偏移 |
| `chat_orchestrator_protocol.go` | 644 | 644 | 无偏移 |
| `chat_orchestrator_responder.go` | 354 | 354 | 无偏移 |
| `chat_orchestrator_feedback.go` | 841 | 841 | 无偏移 |
| `ws_safe_writer.go` | 62 | 62 | 无偏移 |
| `ws_registry.go` | 166 | 166 | 无偏移 |
| `websocket_proxy.go` | 291 | 291 | 无偏移 |
| `websocket_factory.go` | 94 | 94 | 无偏移 |
| `agent/client.go` | 230 | 230 | 无偏移 |
| `agent/health_checker.go` | 432 | 431 | -1 行 |

**注意**: 审计报告中列出总计 "~5,166 行"，但实际 12 文件合计 4,384 行（不含 `middleware/rate_limit.go`）。加上 `rate_limit.go` 521 行 = 4,905 行，仍与报告声称的 5,166 有 ~261 行差异。原报告文件清单和行数计算存在小误差，但不影响审计发现的有效性。

---

### P0 发现复核

#### P0-1: Legacy 反馈路径直接在原始 conn 上写入 — 并发写竞态条件
**状态**: CONFIRMED — 未修复

代码验证:
- `chat_orchestrator.go:347,350,353,356,362` — 所有 legacy 路径仍传递 `conn *websocket.Conn`（而非 `writer *wsSafeWriter`）
- `chat_orchestrator_feedback.go:63-168` — 所有 `legacyXxxSender` 结构体仍然封装 `*websocket.Conn`，调用 `s.conn.WriteJSON()` 而非 `wsSafeWriter`
- 具体受影响的 5 个 sender 全部存在: `legacyActionStatusSender` (L63), `legacyUpdateNodeResponder` (L84), `legacyInterventionResponder` (L111), `legacyResponseFeedbackResponder` (L130), `legacyPlanReviewStatusSender` (L149)
- Envelope 路径（L464-515）使用 `responder` 接口（通过 `wsSafeWriter`），不受影响
- 只有 legacy JSON 解析路径（`wsModeLegacy` 分支）受此 bug 影响

**行号偏移**: 无，原报告行号精确匹配。

---

#### P0-2: Health Checker 探测使用 StreamChat + 空消息 — 泄漏 gRPC 流 + 污染数据
**状态**: CONFIRMED — 未修复

代码验证:
- `health_checker.go:171-175` — `check()` 方法仍使用 `h.client.api.StreamChat(ctx, &agentv1.ChatRequest{...Message: ""})` 进行健康探测
- `health_checker.go:425-429` — `GRPCHealthClient.Check()` 方法也有同样问题
- `_, err = h.client.api.StreamChat(...)` — 返回的 stream 赋值给 `_`，即接收的 stream 被完全忽略，不做 `Recv()` 也不做 `CloseSend()`
- `__health_check__` 作为 user/session ID 未变

**行号偏移**: 文件总行 431（报告声称 432），-1 行偏移，但关键行号 171-175 和 425-429 位置未变。

---

#### P0-3: 消息级速率限制器默认值过于激进 — 1 RPS / burst 1
**状态**: CONFIRMED — 未修复

代码验证:
- `chat_orchestrator.go:275-281` — 默认值逻辑未变:
  ```go
  if msgRate <= 0 { msgRate = 1 }
  if msgBurst <= 0 { msgBurst = 1 }
  msgLimiter := rate.NewLimiter(rate.Limit(msgRate), msgBurst)
  ```
- 超限处理（L308-311）直接发送 Close 帧并 `break`，无 warning 日志
- 配置值从 `h.cfg.WSMessageRateRPS` 和 `h.cfg.WSMessageRateBurst` 读取，但这两个值若未配置则 fallback 到 1

**行号偏移**: 无。

---

### P1 发现复核

#### P1-1: shouldClose 闭包中 span.End() 生命周期过长
**状态**: CONFIRMED — 未修复

代码验证:
- `chat_orchestrator.go:410-418` — Legacy 路径: `ctx, span := tracer.Start(msgCtx, "HandleMessage")` 然后 `defer span.End()` 包裹整个 `handleChatMessage` 调用（最长 300 秒）
- `chat_orchestrator.go:431-437` — Envelope 路径: 同样模式
- 两条路径的 span 都会跨越完整 chatflow 处理时间

**行号偏移**: 无。

---

#### P1-2: 流接收循环创建无用 span — 无属性记录
**状态**: CONFIRMED — 未修复

代码验证:
- `chat_orchestrator_chatflow.go:418-420`:
  ```go
  _, streamSpan := tracer.Start(ctx, "stream.receive")
  resp, err := stream.Recv()
  streamSpan.End()
  ```
- 同样 `L489`: `_, respSpan := tracer.Start(ctx, "stream.process_response")` + `respSpan.End()`
- 两个 span 均不设置任何 attribute，不记录错误状态

**行号偏移**: 无。

---

#### P1-3: ping goroutine 关闭连接后 defer 再次 Close — 双重关闭
**状态**: CONFIRMED — 未修复

代码验证:
- `chat_orchestrator.go:222-238` — idle timer goroutine 在超时时调用 `writer.WriteControl(CloseMessage)` + `conn.Close()`
- `chat_orchestrator.go:192-195` — defer 块也调用 `writer.WriteMessage(CloseMessage)` + `conn.Close()`
- 无 `sync.Once` 或原子标志保护
- 注意: ping goroutine（L203-217）使用 `writer.WriteControl`，这是安全的（通过 wsSafeWriter 加锁），但 idle timer goroutine 混合使用 `writer.WriteControl` 和 `conn.Close()`（后者不经过 writer 锁），仍构成竞态

**行号偏移**: 无。

---

#### P1-4: 无基于 request_id 的去重 — 重试导致配额超额扣减
**状态**: CONFIRMED — 未修复

代码验证:
- `chat_orchestrator_chatflow.go:233-236` — 空 requestID 直接生成新 UUID，无去重检查
- `chat_orchestrator_chatflow.go:318-341` — `h.quota.ReserveRequest(quotaCtx, userID, reqID, ...)` 使用 reqID 作为参数，但未检查该 reqID 是否已被使用过
- 客户端重试相同请求（相同消息，无 request_id）每次生成新 UUID，绕过去重

**行号偏移**: 无。

---

#### P1-5: 语义缓存 scope 使用 SHA-1 12 字符哈希 — 碰撞导致跨用户污染
**状态**: CONFIRMED — 未修复

代码验证:
- `chat_orchestrator_chatflow.go:34-45`:
  ```go
  func shortHash(parts ...string) string {
      h := sha1.New()
      // ...
      return hex.EncodeToString(h.Sum(nil))[:12]  // 48-bit
  }
  ```
- SHA-1 + 12 hex 字符（48 位）未变
- `semanticCacheScope` 函数（L47-67）使用此 shortHash 生成缓存 key

**行号偏移**: 无。

---

#### P1-6: 异步保存和缓存更新使用 context.Background() — 追踪链断裂 + goroutine 泄漏风险
**状态**: PARTIALLY FIXED

代码验证:
- `chat_orchestrator_chatflow.go:168` — `go h.saveMessage(userID, sessionID, "user", message)` — 用户消息保存已改为**异步但调用 `saveMessage` 方法**，该方法内部创建自己的 `context.Background()` span（`chat_orchestrator_feedback.go:44`）
- `chat_orchestrator_chatflow.go:625` — 助手消息保存已改为**同步**: `h.saveMessage(userID, sessionID, "assistant", result)` — 这是一个改进，不再使用 `go` 启动 goroutine
- `chat_orchestrator_chatflow.go:627-634` — 语义缓存更新仍使用 `go func()` + `context.Background()`，无超时

**评估**: 助手消息的保存已从异步改为同步（修复了部分问题），但用户消息保存（L168）和语义缓存更新（L627-634）仍使用脱离的 context。原报告引用的行号 L169 对应当前 L168（一行偏移），L627-634 对应当前 L627-634（无偏移）。总体评级: 部分改善但核心问题未解。

---

#### P1-7: CJK 文本配额估算使用 1.5x 乘数 — 低估 30-50%
**状态**: CONFIRMED — 未修复

代码验证:
- `chat_orchestrator_chatflow.go:640-649`:
  ```go
  func estimateTokensFromRunes(runes int) int64 {
      estimated := int64(float64(runes) * 1.5)
  ```
- 乘数仍为 1.5，未改为 2.5

**行号偏移**: 无。

---

### P2 发现复核

#### P2-1: msgType 变量遮蔽 WebSocket 消息类型
**状态**: CONFIRMED — 未修复
- `chat_orchestrator.go:288` 外部 `msgType` (int) vs L336 内部 `msgType` (string) 仍存在变量遮蔽。Go 作用域规则使功能正确。

#### P2-2: chatInputPool sync.Pool 残留数据风险
**状态**: CONFIRMED — 未修复
- `chat_orchestrator.go:80-89` — `Reset()` 仍设置 `c.ExtraContext = nil`，但旧 map 的引用可能在外部持有。实际风险较低（map 设为 nil 后旧数据可被 GC），但理论上不完美。

#### P2-3: DefaultUpgrader 允许所有 Origin — 生产环境风险
**状态**: CONFIRMED — 未修复
- `websocket_factory.go:54-62` — `DefaultUpgrader` 仍返回 `CheckOrigin: func(r *http.Request) bool { return true }`
- `websocket_factory.go:64-67` — `isDevelopmentEnv()` 在 `ENVIRONMENT` 为空时返回 true
- 但 `chat_orchestrator.go:147-158` 有保护: 当 `wsFactory == nil` 且非开发环境时拒绝连接。风险降低为: 如果 `ENVIRONMENT` 未设置但 `wsFactory` 已配置，则走 `wsFactory.CreateUpgrader()`（安全路径）。只有 `wsFactory` 缺失时才 fallback 到 DefaultUpgrader。

**评估修正**: 实际风险比原报告描述的低。正常部署中 `wsFactory` 始终通过 DI 注入，DefaultUpgrader 只在缺少注入时作为开发 fallback。但 `isDevelopmentEnv` 的空字符串=开发行为仍是一个潜在风险。

#### P2-4: Tool Call Arguments 未经过 sanitizer 清洗
**状态**: CONFIRMED — 未修复
- `chat_orchestrator_protocol.go:97-103` — `arguments` 字段直接透传:
  ```go
  "arguments": content.ToolCall.Arguments,
  ```
- Delta 文本经过 `sanitizer.Sanitize()` 但 Arguments 不经过

#### P2-5: wsSafeWriter 使用 buffered channel 而非 sync.Mutex — 性能较低
**状态**: CONFIRMED — 未修复
- `ws_safe_writer.go:16-32` — 仍使用 buffered channel (`chan struct{}`) 作为互斥锁

#### P2-6: ws_registry DrainAll 未从 signalHub 注销 — 关闭时资源泄漏
**状态**: CONFIRMED — 未修复
- `ws_registry.go:133-166` — `DrainAll` 遍历连接并关闭，但不调用 `r.signalHub.Unregister()` 或 `r.Unregister()` 方法（后者会正确注销 signalHub）
- `Unregister()` 方法（L65-92）正确处理了 signalHub 注销，但 `DrainAll` 绕过了它

#### P2-7: 配额限制从环境变量读取绕过结构化配置
**状态**: CONFIRMED — 未修复
- `chat_orchestrator_chatflow.go:306` — `getEnvInt64("DAILY_QUOTA", 100000)` 仍直接读环境变量

---

### 合规项复核

| 检查项 | 原报告状态 | 复核状态 | 变更 |
|--------|-----------|---------|------|
| WebSocket 输入清洗 | 部分 | 部分 | 无变化 |
| 消息长度限制 | OK | OK | 无变化 |
| 读取大小限制 | 条件 | 条件 | 无变化 |
| 认证检查 | OK | OK | 无变化 |
| 源检查 | 条件 | 条件 | 无变化（P2-3 风险略低于描述） |
| 速率限制 | 条件 | 条件 | 无变化 |
| Circuit Breaker | OK | OK | 无变化 |
| 资源清理 | 条件 | 条件 | 无变化 |
| 并发写安全 | FAIL | FAIL | 无变化 |
| 错误传播 | OK | OK | 无变化 |
| 分布式追踪 | 条件 | 条件 | 无变化 |
| 配额强制执行 | 条件 | 条件 | 无变化 |

---

### 复核总结

| 发现 | 原状态 | 复核状态 | 说明 |
|------|--------|---------|------|
| P0-1 (Legacy 写竞态) | OPEN | CONFIRMED | 5 个 legacy sender 仍使用 raw conn |
| P0-2 (Health probe 流泄漏) | OPEN | CONFIRMED | check() 和 GRPCHealthClient.Check() 均未修复 |
| P0-3 (速率限制默认值) | OPEN | CONFIRMED | 默认 1 RPS / burst 1 未变 |
| P1-1 (Span 生命周期过长) | OPEN | CONFIRMED | span 仍跨完整 chatflow |
| P1-2 (无用 span) | OPEN | CONFIRMED | stream.receive span 无属性 |
| P1-3 (双重关闭) | OPEN | CONFIRMED | 无 sync.Once 保护 |
| P1-4 (请求去重) | OPEN | CONFIRMED | 无去重机制 |
| P1-5 (SHA-1 短哈希) | OPEN | CONFIRMED | 仍为 SHA-1 + 12 hex chars |
| P1-6 (脱离 context) | OPEN | PARTIALLY FIXED | 助手消息保存改为同步，但缓存更新仍用 context.Background() |
| P1-7 (CJK token 估算) | OPEN | CONFIRMED | 乘数仍为 1.5 |
| P2-1 (变量遮蔽) | OPEN | CONFIRMED | |
| P2-2 (Pool 残留数据) | OPEN | CONFIRMED | |
| P2-3 (Origin 检查) | OPEN | CONFIRMED | 风险略低于原描述 |
| P2-4 (Tool args 未清洗) | OPEN | CONFIRMED | |
| P2-5 (Channel vs Mutex) | OPEN | CONFIRMED | |
| P2-6 (DrainAll 泄漏) | OPEN | CONFIRMED | |
| P2-7 (绕过配置) | OPEN | CONFIRMED | |

**修复进度**: 17 项发现中，1 项部分修复（P1-6 助手消息保存改为同步），16 项未修复。0 项完全修复。

**整体评估**: 审计报告准确且高质量。所有行号与当前代码精确匹配（仅 health_checker.go 有 -1 行微小偏移）。P1-6 有微小改善。P2-3 的实际风险比原报告描述略低（wsFactory 正常注入时走安全路径）。其余发现均与原始审计一致，代码未发生变更。
