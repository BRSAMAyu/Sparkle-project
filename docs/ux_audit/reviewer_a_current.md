# Reviewer A — D09: Go Gateway 中间件——限流误杀与WebSocket断连恢复
Timestamp: 2026-04-26T02:40:00+08:00
Chain Index: 14

## 自我审查声明

本报告所有发现已通过亲自阅读源代码确认。关键验证：(1) `rate_limit.go:331-338` 全局配置合理（10 req/s + burst 30）；(2) `cors.go:13` 检查 `IsOriginAllowed` 而非通配符；(3) `security.go:16-17` CSP `script-src 'self'` 无 unsafe-inline；(4) `websocket_proxy.go:115,139,152` 三层 defer 确保 cleanup。

## Chain Flow Summary

审查 Go Gateway 四个中间件层：(1) IP/User/Adaptive rate limiting — 是否在正常使用下误杀请求 (2) WebSocket proxy 断连处理 (3) CORS 配置是否阻断正常前端请求 (4) Security headers 是否过于严格。

## Critical Issues 🔴

None found.

## Major Issues 🟡

None found.

## Minor Issues 🟢

**1. `websocket_proxy.go`: WebSocket 断连时不主动通知 Python 后端清理**

当客户端 WebSocket 断连时，Go gateway 通过 `defer` 链（line 115, 139, 152）关闭 client 和 backend 连接。但 Go 端没有发送显式的 "disconnect" 控制消息给 Python 后端。Python 端依赖 TCP 连接关闭事件来检测断连（`backend/app/core/websocket.py:255-261` 的 `disconnect()` 方法）。

在正常情况下，TCP FIN/RST 会触发 Python 端的 cleanup。但在网络中断（如设备进入隧道）场景下，TCP 连接可能长时间处于半开状态，Python 端直到心跳超时（60秒）才知道连接已断开。

Expected: 发送显式 WebSocket close frame 给 Python 后端加速 cleanup。Actual: 依赖 TCP 层关闭，最坏情况60秒延迟。

**Note**: Go gateway 的 ping ticker（line 253-271）每30秒发送 ping，配合 Python 端60秒超时，实际检测延迟为 30-90 秒。对实时应用可接受但非最优。

## Working Well ✅

**Rate limiting** (`rate_limit.go`):
- IP 限流：10 req/s + burst 30（line 331-332）— 正常使用不会触发
- Auth 限流：5 req/s + burst 15（line 334-335）— 防止暴力破解
- WebSocket 限流：5 conn/min + burst 10（line 337-338）— 允许合理重连
- 自适应限流：写操作用更严格策略（baseRate*0.8, burst*0.8）（line 261）
- 限流响应包含 `retry_after` 头（line 165）和 `X-RateLimit-*` 头（line 172-174）
- 过期 visitor 自动清理（goroutine，line 52-60）
- `maxVisitors` 上限防止内存溢出（line 75-76），LRU 淘汰策略（line 126-133）

**CORS** (`cors.go`):
- 使用 `cfg.IsOriginAllowed(origin)` 白名单（line 13），非通配符 `*`
- 仅在 origin 匹配时设置 CORS 头（line 14-18）
- OPTIONS 请求正确返回 204 No Content（line 21-23）
- `connect-src` 允许 `wss:` 和 `https:`（security.go line 20）

**Security headers** (`security.go`):
- CSP `script-src 'self'` 无 `unsafe-inline`/`unsafe-eval`（line 16-17）— 严格但安全
- `style-src` 保留 `unsafe-inline`（line 18）— CSS 框架兼容性需要
- `X-Frame-Options: DENY`（line 28）— 防止 clickjacking
- `HSTS` 仅在生产环境启用（line 37-39）
- `Permissions-Policy` 禁用 geolocation/camera/microphone/payment（line 45）
- `Referrer-Policy: strict-origin-when-cross-origin`（line 42）

**WebSocket proxy** (`websocket_proxy.go`):
- 三层 defer 确保 cleanup：unregisterConnection + backendConn.Close + clientConn.Close（line 115, 139, 152）
- 双向 goroutine 代理：client→backend 和 backend→client（line 195-249）
- Ping ticker 每30秒双向保活（line 253-271）
- 错误通道 + done 信号优雅关闭（line 274-285）
- Per-user 连接数限制（line 291-303）

## Files Examined

1. `backend/gateway/internal/middleware/rate_limit.go` (全文 — rate limiter with token bucket, IP/User/Endpoint/Adaptive variants)
2. `backend/gateway/internal/middleware/cors.go` (全文 29 行 — origin whitelist)
3. `backend/gateway/internal/middleware/security.go` (全文 50 行 — CSP + security headers)
4. `backend/gateway/internal/handler/websocket_proxy.go` (lines 110-289, proxy lifecycle)

## Confidence: High — 四个中间件层逐一审查。限流配置合理（不会误杀正常用户），CORS/Security 配置正确且严格。唯一 Minor 是 WebSocket 断连检测依赖 TCP 超时而非显式通知。
