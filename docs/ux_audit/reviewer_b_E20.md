# Reviewer B — E20: Go Gateway中间件链顺序与安全性
Timestamp: 2026-04-26T15:05:00+08:00
Chain Index: N/A (user override)

## Chain Flow Summary
Go Gateway 使用 Gin 框架，全局中间件链为: Recovery → OpenTelemetry → RequestContext → SecurityHeaders → CORS。API 路由组额外叠加 rate_limit → timeout。认证在路由级别按需挂载。所有 11 个中间件文件均已注册，顺序正确，安全实践到位。**此链路健康，无需修复。**

## Critical Issues 🔴
None.

## Major Issues 🟡
None.

## Minor Issues 🟢

**1. CORS 缺少 `Access-Control-Max-Age` 头**
- **File**: `backend/gateway/internal/middleware/cors.go:10-28`
- **Expected**: 预检请求可被浏览器缓存，减少 OPTIONS 飞行
- **Actual**: 未设置 `Access-Control-Max-Age`，浏览器每次跨域请求都会发送 preflight OPTIONS
- **Impact**: 低——仅增加少量网络开销，不影响功能或安全

## Working Well ✅

- **中间件顺序正确** (`setup.go:398-403`): SecurityHeaders → CORS → [rate_limit → timeout] → [auth per-route]。CORS 在 auth 之前处理 preflight，rate_limit 在 timeout 之前过滤恶意请求
- **Panic 安全**: `gin.Default()` 内含 Recovery 中间件，任何 handler panic 都会被捕获返回 500，不影响后续请求
- **Security Headers 全局覆盖** (`security.go:1-49`): CSP (无 unsafe-inline script)、X-Frame-Options DENY、HSTS (仅生产)、Referrer-Policy、Permissions-Policy——在全局中间件中设置，所有响应路径（含 NoRoute）都生效
- **Timing-attack 防护**:
  - Admin auth: `subtle.ConstantTimeCompare` (`auth.go:209`)
  - Internal API key: `subtle.ConstantTimeCompare` (`internal_api.go:20`)
- **CORS 生产安全**: 通配符 `*` 在生产环境被跳过 (`config.go:150-154`)，仅允许显式白名单域名
- **Auth 中间件健壮**: JWT HS256 验证 + Redis 黑名单 + 本地黑名单缓存（Redis 不可用时 fail-closed）
- **Rate limit 分层**: auth 5 RPS、API 30 RPS、internal 独立、admin 独立——不同路由不同阈值
- **所有 11 个中间件文件均已注册**: ab_test、chaos_guard、cors、internal_api、request_context、security、ws_auth、internal_ip_whitelist、distributed_rate_limiter、timeout、rate_limit、auth
- **Timeout 正确跳过长时请求** (`timeout.go:43-57`): STT、胶囊生成、预测、学习路径等长时 API 免超时
- **NoRoute 代理安全** (`setup.go:774-796`): 仅允许白名单 auth 路径（register/login/refresh 等）代理到 Python 后端，其余返回 404

## Files Examined
- `backend/gateway/cmd/server/setup.go`（setupRouter 函数，line 385-772）
- `backend/gateway/cmd/server/main.go`（全文 132 行）
- `backend/gateway/internal/middleware/security.go`（全文 50 行）
- `backend/gateway/internal/middleware/auth.go`（AdminAuthMiddleware + AuthMiddleware）
- `backend/gateway/internal/middleware/cors.go`（全文 29 行）
- `backend/gateway/internal/middleware/timeout.go`（全文 58 行）
- `backend/gateway/internal/middleware/internal_api.go`（全文 28 行）
- `backend/gateway/internal/config/config.go`（IsOriginAllowed, CORS config）

## Confidence: High — 中间件顺序、安全头、认证、限流均已通过源码直接验证。此链路设计合理，实现正确。
