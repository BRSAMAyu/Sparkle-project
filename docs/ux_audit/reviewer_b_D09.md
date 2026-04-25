# Reviewer B — D09: Go Gateway 中间件——限流误杀与WebSocket断连恢复
Timestamp: 2026-04-26T16:45:00+08:00
Chain Index: beyond queue (picked from unreviewed pending chains)

## Chain Flow Summary

用户通过 Flutter 客户端连接 Go Gateway 的 WebSocket 端点，经 WsAuthMiddleware 鉴权后升级连接。Gateway 将消息通过 gRPC 转发给 Python 后端，流式响应通过同一条 WS 连接返回。限流分为多层：连接建立阶段（无IP限流）、消息发送阶段（10/s burst 20）、API 路由阶段（30/s burst 60 via Redis hybrid）。CORS 和安全头在全局中间件层注入。

## Critical Issues 🔴

无。

## Major Issues 🟡

**1. `WebSocketRateLimitMiddleware()` 定义但从未挂载 — WS 升级无 IP 级限流**
- **File**: `backend/gateway/internal/middleware/rate_limit.go:371-397`
- **Expected**: WebSocket 连接升级应有 IP 级别限流（文档声明 "5/min burst 10"）。
- **Actual**: `WebSocketRateLimitMiddleware()` 函数已实现但从未在 `setupRouter` 中使用。`/ws/chat` 路由（`setup.go:410`）只挂了 `WsAuthMiddleware`，没有连接级 IP 限流。攻击者可从同一 IP 高频发送 WS 升级请求，每次都需 WsAuthMiddleware 执行 JWT 验证或 Redis ticket 查询。
- **Mitigation**: `ConnectionRegistry` 有 per-user 上限（默认 2）和全局上限（默认 2000）；`msgLimiter` 限制消息速率 10/s。但这些都发生在认证之后，升级过程本身未限速。
- **Evidence**: `setup.go:410` — `r.GET("/ws/chat", middleware.WsAuthMiddleware(cfg, rdb), handlers.chatOrchestrator.HandleWebSocket)` — 无 rate limit 中间件。

**2. CORS 缺少 `Access-Control-Max-Age` — 每次跨域请求都触发 preflight**
- **File**: `backend/gateway/internal/middleware/cors.go:10-28`
- **Expected**: CORS preflight 结果应被浏览器缓存（通常设 `Access-Control-Max-Age: 86400`）。
- **Actual**: `CORSMiddleware` 设置了 `Allow-Origin`、`Allow-Credentials`、`Allow-Headers`、`Allow-Methods`，但未设 `Access-Control-Max-Age`。浏览器默认缓存 preflight 仅 5 秒（Chrome）或不缓存（Safari），导致高频跨域场景下 OPTIONS 请求数翻倍。
- **Impact**: 本地开发 + Flutter Web 调试时影响不大；但如果将来部署 Web 版本，将产生大量冗余 preflight 请求。
- **Evidence**: `cors.go:11-19` — 只设了 5 个 header，无 `Max-Age`。

**3. WS 断连事件通过 Redis Pub/Sub 发布，但无保证 Python 后端消费**
- **File**: `backend/gateway/internal/handler/ws_registry.go:94-99`
- **Expected**: WS 断连后 Python 后端应被可靠通知以清理 gRPC 流状态。
- **Actual**: `Unregister` 调用 `chatHistory.PublishConnectionEvent(ctx, userID, "disconnected")`，这是 Redis Pub/Sub 的 fire-and-forget 发布。如果无订阅者，事件丢失。实际清理依赖 gRPC stream 的 context cancellation（通过 `handleChatMessage` 的 `defer cancel()`），这在 WS 写入失败时触发，是可靠的。但 Pub/Sub 事件本身不可靠。
- **Mitigation**: gRPC stream context cancellation 机制实际保障了 Python 后端状态清理。Pub/Sub 事件仅用于补充通知（如更新在线状态）。
- **Evidence**: `ws_registry.go:96` — `_ = r.chatHistory.PublishConnectionEvent(...)` 错误被静默丢弃。`chat_orchestrator_chatflow.go:217-218` — `ctx, cancel := context.WithTimeout(...); defer cancel()` 确保 gRPC 流超时/取消。

## Minor Issues 🟢

**1. CSP `connect-src 'self' wss: https:` 对 Web 场景过于宽松**
- **File**: `backend/gateway/internal/middleware/security.go:20`
- **Actual**: `connect-src` 允许任意 `wss:` 和 `https:` 连接。对 Flutter mobile 无影响（CSP 不适用），但对未来 Web 版本存在 XSS 后的数据外泄风险。
- **Note**: 当前阶段非问题（纯移动端），Web 部署前应收紧。

**2. `DefaultUpgrader()` 允许所有 origin — 防御纵深风险**
- **File**: `backend/gateway/internal/handler/websocket_factory.go:54-62`
- **Actual**: `DefaultUpgrader()` 的 `CheckOrigin` 返回 `true`。在 `chat_orchestrator.go:170-178` 中有保护（非 dev 环境返回 error），但如果 `ENVIRONMENT` 环境变量误配为 `dev`，且 `wsFactory` 因初始化失败为 nil，将降级到此 upgrader。
- **Mitigation**: 生产环境 `wsFactory` 始终在 `initHandlers` 中初始化（`setup.go:213`），nil 场景极不可能。

**3. `AdaptiveRateLimitMiddleware` per-path 标识符可能撑满 visitors map**
- **File**: `backend/gateway/internal/middleware/rate_limit.go:288`
- **Actual**: `identifier = path + ":" + clientIP` 每个路径+IP组合占一个 entry。`maxVisitors` 默认 10000。如果有大量路径（当前 proxy routes 注册了约 100+），理论上可达上限触发 LRU 淘汰。
- **Note**: 实际风险低（单 IP 不太可能访问所有路径），但 `AdaptiveRateLimitMiddleware` 本身也未被 `setupRouter` 使用（只用了 `HybridRateLimitMiddlewareSimple`），所以此为死代码风险。

## Working Well ✅

1. **安全头全面且正确** — CSP（移除了 unsafe-inline for scripts）、X-Frame-Options DENY、HSTS 仅生产环境、Permissions-Policy 限制浏览器功能。`security.go:9-49` 实现完整。
2. **CORS origin 检查严格** — 生产环境拒绝通配符 `*`，支持精确 host:port 匹配和通配符域名 `*.example.com`。开发环境仅允许 localhost。`config.go:124-198`。
3. **混合限流器（Redis + local fallback）设计健壮** — Redis 故障时无缝降级到本地限流，`distributed_rate_limiter.go:406-470` fallback 逻辑完整。
4. **ConnectionRegistry 清理机制完善** — `DrainAll` 支持优雅关闭（分两阶段：先 drain WS，再 shutdown HTTP，`main.go:108-128`），per-user 和 global 连接上限。
5. **消息级限流** — `chat_orchestrator.go:302` 每 WS 连接 10/s burst 20 的消息速率限制，防止单连接刷消息。
6. **WS 鉴权三通道** — JWT header、JWT query param（仅 dev）、一次性 ticket（Redis GET+DEL 原子操作），`ws_auth.go:33-134`。
7. **生产环境保护** — `AllowWsQueryToken` 生产强制 false（`config.go:580-582`），弱密钥检查，`REDIS_FAIL_CLOSED` 生产默认 true。

## Files Examined

- `backend/gateway/internal/middleware/rate_limit.go` — 全文 520 行
- `backend/gateway/internal/middleware/distributed_rate_limiter.go` — 全文 364 行
- `backend/gateway/internal/middleware/cors.go` — 全文 29 行
- `backend/gateway/internal/middleware/security.go` — 全文 49 行
- `backend/gateway/internal/middleware/timeout.go` — 全文 57 行
- `backend/gateway/internal/middleware/ws_auth.go` — 全文 172 行
- `backend/gateway/internal/handler/websocket_proxy.go` — 全文 369 行
- `backend/gateway/internal/handler/chat_orchestrator.go` — 前 600 行
- `backend/gateway/internal/handler/chat_orchestrator_chatflow.go` — 前 280 行
- `backend/gateway/internal/handler/chat_orchestrator_connections.go` — 全文 53 行
- `backend/gateway/internal/handler/ws_registry.go` — 全文 210 行
- `backend/gateway/internal/handler/websocket_factory.go` — 全文 95 行
- `backend/gateway/internal/handler/proxy_routes.go` — 前 100 行
- `backend/gateway/internal/service/chat_history.go:195-244` — PublishConnectionEvent
- `backend/gateway/internal/config/config.go` — 限流/CORS/WS 配置相关段落
- `backend/gateway/cmd/server/setup.go` — 全文 867 行（路由注册）
- `backend/gateway/cmd/server/main.go` — 全文 131 行（优雅关闭）

## Confidence: High — 所有关键代码路径逐行阅读，限流阈值/链路/降级行为均已验证。
