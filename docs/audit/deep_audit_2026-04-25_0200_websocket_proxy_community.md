# 深度审计 #50 — WebSocket Proxy 社群连接代理完整链路

> **日期**: 2026-04-25 02:00
> **模块**: Go Gateway WebSocketProxy — 社群群聊/个人 WebSocket 双向代理 → Python 后端
> **范围**: `websocket_proxy.go`（291 行）+ `setup.go` 路由注册
> **审计员**: Claude Deep Auditor (Round 50)

---

## 审计范围

`WebSocketProxy` 负责社群群聊（`/api/v1/community/groups/:group_id/ws`）和个人连接（`/api/v1/community/ws/connect`）的双向 WebSocket 代理。采用先连后升策略：先 dial Python 后端，再 upgrade 前端客户端，确保后端不可用时客户端收到明确错误。

### 文件清单

| 文件 | 行数 | 职责 |
|------|------|------|
| `gateway/internal/handler/websocket_proxy.go` | 291 | WebSocket 双向代理 |
| `gateway/cmd/server/setup.go:404-409` | 6 | 路由注册（含 WsAuthMiddleware） |

**总计**: 1 核心文件 + 路由注册, ~297 行

---

## 数据流图

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Flutter → WebSocket Proxy → Python Backend                             │
│                                                                         │
│  连接建立:                                                              │
│    1. WsAuthMiddleware → 验证 JWT ✅                                    │
│    2. HandleCommunityWS (:54-94) / HandlePersonalWS (:98-131)           │
│       提取 token: Authorization header → Bearer token ✅                │
│       fallback: query parameter "token"                                 │
│       ❌ P1-1: token 同时放入 URL query param + Authorization header    │
│                                                                         │
│    3. proxyWebSocket (:134-250)                                         │
│       a. Dial backend (:149) → 先连接后端                               │
│          ✅ 后端不可用时返回 502，不升级前端连接                         │
│       b. Upgrade client (:164) → 再升级前端                             │
│          ✅ 复用后端确认的子协议                                         │
│                                                                         │
│  双向转发:                                                              │
│    goroutine 1: client → backend (:188-209)                             │
│      ReadMessage → WriteMessage                                         │
│      ❌ P1-2: 无消息大小限制 — 客户端可发送 MB 级帧                    │
│      ❌ P0-1: 无 read deadline — 空闲连接永不超时                       │
│                                                                         │
│    goroutine 2: backend → client (:212-233)                             │
│      ReadMessage → WriteMessage                                         │
│      ❌ P0-1: 无 read deadline — 后端静默断开不感知                     │
│                                                                         │
│    等待关闭:                                                            │
│      <-done → 任一 goroutine 退出即结束 (:236)                          │
│      ❌ P1-3: 不发送 WebSocket Close Frame → 对端收到异常断开           │
│      ❌ P2-2: errChan(2) 只读 1 个错误 → 第二个错误丢失               │
│                                                                         │
│  全局问题:                                                              │
│    ❌ P0-1: 无每用户连接数限制 + 无空闲超时 → 无界资源泄漏             │
│    ❌ P1-4: CheckOrigin 允许空 Origin (:36-38)                         │
│    ❌ P1-5: 无 Prometheus 指标 — 连接数/字节数/错误率不可观测         │
│    ❌ P2-1: Close() 是 no-op — 无法优雅关闭活跃连接                   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 审计发现

### P0 — 严重缺陷

#### P0-1: 无每用户连接数限制 + 无空闲超时 → 无界资源泄漏
**文件**: `websocket_proxy.go:134-250`, `setup.go:404-409`
**严重性**: P0 — 单用户可耗尽 Gateway 和 Python 后端资源

```go
// setup.go:404-409 — 社群 WS 路由无速率限制
r.GET("/api/v1/community/groups/:group_id/ws",
    middleware.WsAuthMiddleware(cfg, rdb),  // ← 仅认证，无限流
    handlers.wsProxy.HandleCommunityWS)
r.GET("/api/v1/community/ws/connect",
    middleware.WsAuthMiddleware(cfg, rdb),  // ← 仅认证，无限流
    handlers.wsProxy.HandlePersonalWS)

// websocket_proxy.go — 无连接计数、无 read deadline
// goroutine 1: client → backend
for {
    messageType, data, err := clientConn.ReadMessage()  // ← 无 deadline
    ...
}
// goroutine 2: backend → client
for {
    messageType, data, err := backendConn.ReadMessage()  // ← 无 deadline
    ...
}
```

**双重缺失**:

| 缺失 | 后果 |
|------|------|
| 无每用户连接数限制 | 单用户可打开无限连接 |
| 无 read deadline | 空闲连接永不关闭 |
| 无 ping/pong keepalive | 中间代理/TCP 超时不会被检测 |

**资源消耗链路**:
```
每个 WS 连接消耗:
  - 2 goroutines (client→backend + backend→client) → ~8KB stack each
  - 1 gorilla/websocket client connection → ~4KB buffers
  - 1 gorilla/websocket backend connection → ~4KB buffers
  - 1 Python backend WS handler goroutine + DB session

单用户 1000 连接:
  - Go Gateway: ~24MB goroutine + ~8MB buffers = ~32MB
  - Python Backend: 1000 async handlers + DB sessions
  - 无上限 → 可耗尽文件描述符或内存
```

**攻击场景**: 恶意用户循环调用 `new WebSocket(url)` 1000 次，每个连接建立但不发送数据。由于无 idle timeout，连接永远不会关闭。Gateway 和 Python 后端资源持续泄漏。

**修复方向**: (1) 添加 per-user 连接计数器（如 `sync.Map` + atomic），限制每用户 ≤5 个社群 WS 连接；(2) `SetReadDeadline(60 * time.Second)` + ping/pong keepalive；(3) 添加 `SetPingHandler` 回复 pong。

---

### P1 — 重要问题

#### P1-1: Token 同时放入 URL 查询参数和 Authorization header — 冗余 token 暴露于后端日志
**文件**: `websocket_proxy.go:90, 128, 271-285`
**严重性**: P1 — token 冗余暴露

```go
// :90 — 将 token 追加到 URL
backendURL += "?token=" + token

// :274 — 同时在 header 中发送
headers.Set("Authorization", "Bearer "+authToken)
```

`buildBackendWebSocketHeaders` (:271-285) 已经将 token 放入 `Authorization` header。Python 后端的 WebSocket 处理器应该能从 header 中获取 token。URL 中的 token 是**冗余的**，但会导致：
1. Python 框架访问日志记录完整 URL（含 token）
2. 中间代理/CDN 缓存可能记录 URL
3. 异常追踪系统（Sentry）在 URL 中捕获 token

**修复方向**: 移除 `:90` 和 `:128` 的 URL query parameter token。仅依赖 `Authorization` header。

---

#### P1-2: 无消息大小限制 — 客户端可发送超大 WebSocket 帧
**文件**: `websocket_proxy.go:191, 201, 215, 225`
**严重性**: P1 — 内存消耗攻击

```go
messageType, data, err := clientConn.ReadMessage()  // ← data 可为任意大小
if err := backendConn.WriteMessage(messageType, data); err != nil {  // ← 直接转发
```

gorilla/websocket 默认无消息大小限制。客户端可发送 100MB WebSocket 帧，Go 将在内存中分配 100MB buffer 然后转发到 Python 后端。

**修复方向**: `clientConn.SetReadLimit(64 * 1024)` — 限制单帧 64KB。

---

#### P1-3: 连接断开时不发送 WebSocket Close Frame — 对端收到异常断开
**文件**: `websocket_proxy.go:188-209, 212-233`
**严重性**: P1 — 不优雅关闭

```go
// :188-209 — client→backend goroutine
for {
    messageType, data, err := clientConn.ReadMessage()
    if err != nil {
        // ← 不发送 Close Frame 给 backend，直接退出
        errChan <- err
        return
    }
}
```

当一端断开时，代理直接退出 goroutine，不向另一端发送 WebSocket Close Frame。这导致：
- 对端收到 `CloseAbnormalClosure` 而非正常关闭
- Python 后端无法区分"用户正常离开"和"网络异常"
- 后端可能触发不必要的重连逻辑

**修复方向**: 在退出前调用 `backendConn.WriteMessage(websocket.CloseMessage, websocket.FormatCloseMessage(websocket.CloseNormalClosure, ""))`。

---

#### P1-4: CheckOrigin 允许空 Origin header — 非浏览器客户端可绕过源检查
**文件**: `websocket_proxy.go:33-38`
**严重性**: P1 — CSRF 防护缺口

```go
CheckOrigin: func(r *http.Request) bool {
    origin := r.Header.Get("Origin")
    if origin == "" {
        return true  // ← 无 Origin 的请求全部允许
    }
    ...
}
```

虽然 `WsAuthMiddleware` 提供了 JWT 认证保护，但空 Origin 检查意味着：
- 非浏览器客户端（curl, Postman）不受 Origin 限制
- 如果 JWT 存储在 cookie 中，CSRF 攻击者可以从任意源建立 WS 连接

**修复方向**: 移除空 Origin 允许，或明确记录为设计意图。

---

#### P1-5: 无 Prometheus 指标 — 连接数/错误率/字节数不可观测
**文件**: `websocket_proxy.go` 全文
**严重性**: P1 — 运维盲区

当前仅有 zap 日志，无 Prometheus 指标：
- 无法监控当前活跃社群 WS 连接数
- 无法追踪连接平均生命周期
- 无法监控客户端/后端断开原因分布
- 无法检测异常连接数增长（攻击指标）

**修复方向**: 添加 `sparkle_ws_proxy_active_connections` (Gauge by type) + `sparkle_ws_proxy_errors_total` (Counter by direction/reason) + `sparkle_ws_proxy_connection_duration` (Histogram)。

---

### P2 — 改进建议

#### P2-1: Close() 是 no-op — 无法优雅关闭活跃连接

```go
// :289-291
func (p *WebSocketProxy) Close() error {
    return nil  // ← 无法通知活跃连接关闭
}
```

Gateway 优雅关闭时无法关闭已有的社群 WS 连接。应维护活跃连接集合，Close() 时遍历发送 Close Frame。

---

#### P2-2: errChan 容量 2 但只读 1 个错误

```go
errChan := make(chan error, 2)   // :180
...
select {
case err := <-errChan:          // :238 — 只读第一个错误
    ...
default:
}
```

两个 goroutine 可能几乎同时报错。第二个错误被静默丢弃，可能丢失有用诊断信息。

---

#### P2-3: backendConn 写入错误不反馈给客户端

```go
// :201 — backend 写入失败
if err := backendConn.WriteMessage(messageType, data); err != nil {
    p.logger.Warn("Backend write error", ...)
    errChan <- err
    return  // ← 客户端不知道后端已断开
}
```

后端写入失败时客户端不会被通知。客户端可能继续发送消息，全部静默丢失。

---

## 合规项

| 检查项 | 状态 |
|--------|------|
| 认证中间件 | ✅ WsAuthMiddleware 验证 JWT（setup.go:405, 408） |
| 后端不可用时明确错误 | ✅ Dial 失败返回 502，不升级前端连接 (:150-155) |
| 子协议透传 | ✅ 后端确认的子协议回显给客户端 (:160-163) |
| 结构化日志 | ✅ zap 日志带 user_id, conn_type, resource_id |
| Origin 检查 | ✅ 基于 config 的 Origin 白名单 (:39) |
| 前端 token 优先 header | ✅ 优先 Authorization header，query token 降级 (:72-83, 111-121) |
| 双向 proxy | ✅ client→backend + backend→client 并行转发 |

---

## 统计

| 级别 | 数量 |
|------|------|
| P0 | 1 |
| P1 | 5 |
| P2 | 3 |
| **总计** | **9** |

---

## 修复优先级建议

1. **P0-1** (无连接限制 + 无超时) — per-user 连接计数 + SetReadDeadline + ping/pong — ~30 行
2. **P1-1** (Token 冗余暴露) — 移除 URL query parameter token — ~2 行
3. **P1-2** (无消息大小限制) — SetReadLimit(64KB) — ~1 行
4. **P1-3** (无 Close Frame) — 退出前发送 Close Frame — ~5 行
5. **P1-5** (无指标) — 添加 Prometheus Gauge/Counter/Histogram — ~20 行
6. P1-4/P2-1/P2-2/P2-3 — 随后续迭代修复

---

## 跨轮次因果链

| 本轮发现 | 关联轮次 | 关联模式 |
|----------|---------|---------|
| P0-1 (无连接限制+无超时) | Round #6 (Rate Limiting) | WebSocketRateLimitMiddleware 已实现但未应用到社群 WS 路由 |
| P1-1 (Token 在 URL) | Round #1 P0-2 (WS Token 泄露) | 同一反模式 — token 作为 URL query parameter |
| P1-2 (无消息大小限制) | Round #48 P1-5 (Message 无长度限制) | Go Gateway 对客户端输入信任过度 |
| P1-3 (无 Close Frame) | Round #2 P1-6 (无 DoneEvent) | WebSocket 断开时无优雅终止信号 |

---

## Chris (Session 4) 复核 — 2026-04-23

> 逐条验证当前代码 vs 报告描述，确认报告基于旧版代码。

| 原始发现 | 当前状态 | 复核结论 |
|----------|---------|---------|
| P0-1 (无连接限制+无超时) | 代码已大幅增强: idleTimer(5min)+CloseFrame, configureProxyConn SetReadDeadline+PongHandler, runProxyPingLoop ping/pong, WSMaxMessageBytes SetReadLimit | **大部分 FALSE** — 超时/心跳/消息限制均存在。仅缺 per-user 连接数计数器，降级为 **P1** |
| P1-1 (Token URL暴露) | HandleCommunityWS:81-86 显式 REJECT query token + warn log; buildBackendWebSocketHeaders 仅 Authorization header | **FALSE** — Token 不再出现在 URL |
| P1-2 (无消息大小限制) | proxyWebSocket:163-166 `clientConn.SetReadLimit(p.config.WSMaxMessageBytes)` + backendConn | **FALSE** — 当 WSMaxMessageBytes > 0 时有限制 |
| P1-3 (无CloseFrame) | idleTimer:209-216 主动发送 ClosePolicyViolation Close Frame | **PARTIALLY FALSE** — idle 超时发送 CloseFrame，但正常退出仍不发送 |
| P1-4 (空Origin允许) | upgrader CheckOrigin :44 `if origin == "" { return true }` | **CONFIRMED REAL** — 设计决策（移动端无 Origin） |
| P1-5 (无Prometheus) | 无新增指标代码 | **CONFIRMED REAL** — 运维盲区 |
| P2-1 (Close no-op) | :387 `return nil` | **CONFIRMED REAL** |
| P2-2 (errChan只读1) | done+doneOnce模式替代纯errChan | **PARTIALLY STALE** — 新同步机制但仍只读第一个错误 |

**总结**: 9项发现中4项 FALSE，1项降级(P0→P1)，2项 CONFIRMED，2项 PARTIALLY。代码质量显著改善。
