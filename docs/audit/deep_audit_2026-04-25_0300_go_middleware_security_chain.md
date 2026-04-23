# 深度审计 #51 — Go Gateway 中间件安全链完整审计

> **日期**: 2026-04-25 03:00
> **模块**: Go Gateway Security Middleware Chain — CORS + Security Headers + Timeout + RequestContext + InternalAPI + IP Whitelist
> **范围**: 7 中间件文件 (295 行) + setup.go 路由注册 (:385-515)
> **审计员**: Claude Deep Auditor (Round 51)

---

## 审计范围

Go Gateway 的安全中间件链是系统的第一道防线。每个 HTTP 请求都经过全局中间件链处理, 然后进入路由组特定的中间件。本次审计覆盖全局安全层（CORS/SecurityHeaders/RequestContext）和内部路由安全层（InternalAPI/IPWhitelist）。

### 文件清单

| 文件 | 行数 | 职责 |
|------|------|------|
| `gateway/internal/middleware/cors.go` | 28 | CORS 跨域策略 |
| `gateway/internal/middleware/security.go` | 49 | 安全响应头 (CSP/HSTS/X-Frame-Options 等) |
| `gateway/internal/middleware/timeout.go` | 54 | 请求超时保护 |
| `gateway/internal/middleware/request_context.go` | 43 | Request ID + Trace ID 注入 |
| `gateway/internal/middleware/internal_api.go` | 27 | Internal API Key 校验 |
| `gateway/internal/middleware/internal_ip_whitelist.go` | 71 | 内部端点 IP 白名单 |
| `gateway/internal/middleware/chaos_guard.go` | 23 | Chaos 路由开发模式守卫 |
| `gateway/cmd/server/setup.go:385-515` | 130 | 路由注册 + 中间件编排 |

**总计**: 7 核心文件 + 路由配置, ~425 行

---

## 数据流图

```
┌─────────────────────────────────────────────────────────────────────────┐
│  请求 → Go Gateway Middleware Chain                                     │
│                                                                         │
│  全局中间件 (setup.go:388-393):                                         │
│    1. OTel Tracing (:388)                     ✅ 追踪所有后续中间件      │
│    2. RequestContextMiddleware (:389)         ✅ request_id + trace_id   │
│       ❌ P1-4: X-Request-ID 从客户端接受无校验 → 日志注入风险          │
│    3. SecurityHeadersMiddleware(cfg) (:390)   ✅ CSP/HSTS/X-Frame-Options│
│       ❌ P1-2: CSP connect-src 'wss: https:' 过度宽松                   │
│       ⚠️ P2-1: HSTS 依赖 variadic cfg 参数 → 脆弱模式                 │
│    4. CORSMiddleware(cfg) (:391-392)          ✅ 基于 Origin 白名单      │
│       ❌ P1-3: 无 Access-Control-Max-Age → 浏览器每次预检              │
│       ⚠️ P2-2: 非 allowed origin 的 OPTIONS 也返回 204                │
│                                                                         │
│  WebSocket 路由 (setup.go:400-409):                                     │
│    r.GET("/ws/chat", WsAuthMiddleware, handler)                         │
│    r.GET("/ws/files", WsAuthMiddleware, handler)                        │
│    r.GET("/ws/stt", WsAuthMiddleware, handler)                          │
│    r.GET("/api/v1/community/groups/:group_id/ws", WsAuthMiddleware, ...) │
│    r.GET("/api/v1/community/ws/connect", WsAuthMiddleware, ...)         │
│    ❌ P1-5: 社群 WS 路由在 /api/v1/ 下但不在 api Group 中             │
│              → 绕过 API 组的 rate limit + timeout 中间件                │
│              → 路径前缀误导, 安全审计遗漏风险                          │
│                                                                         │
│  API 组中间件 (setup.go:427-429):                                       │
│    api.Use(apiRateLimit)                       ✅ 30 RPS / burst 60      │
│    api.Use(TimeoutMiddleware(30s))             ✅ 请求超时               │
│       ⚠️ P2-3: isLongRunningRoute 不完整                              │
│                                                                         │
│  内部路由 (setup.go:491):                                               │
│    InternalAPIKeyMiddleware(cfg)               ✅ subtle.ConstantTimeCompare│
│    InternalIPWhitelistMiddleware(cfg)          ❌ P1-1: ClientIP() 可伪造│
│                                                                         │
│  管理路由 (setup.go:499):                                               │
│    AdminAuthMiddleware(cfg)                    ✅ 管理员认证             │
│    ChaosGuardMiddleware(cfg)                   ✅ 仅开发模式允许         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 审计发现

### P0 — 严重缺陷

（无 P0 — 中间件链整体设计合理, 存在纵深防御, 单点缺陷不足以直接突破安全边界）

---

### P1 — 重要问题

#### P1-1: IP 白名单依赖 `ClientIP()` 但未配置 TrustedProxies — IP 可被伪造
**文件**: `internal_ip_whitelist.go:22`, `setup.go` (全局)
**严重性**: P1 — 纵深防御缺失（InternalAPIKeyMiddleware 提供了缓解）

```go
// internal_ip_whitelist.go:22 — 使用 Gin 的 ClientIP()
clientIP := net.ParseIP(strings.TrimSpace(c.ClientIP()))
```

**Gin 默认行为**: setup.go 中未调用 `r.SetTrustedProxies()`. Gin v1.7+ 默认 TrustedProxies 为空（不信任任何代理）, 此时 `ClientIP()` 返回 `RemoteAddr`. 但如果未来部署在反向代理后（Nginx/LB/CloudFlare）:
- `RemoteAddr` 返回代理 IP, 不是客户端真实 IP
- 需要配置 `SetTrustedProxies` + `X-Forwarded-For` 解析
- 如果错误配置为信任所有代理, 客户端可伪造 `X-Forwarded-For: 127.0.0.1` → 白名单绕过

**当前部署**: docker-compose 中 Gateway 直接暴露 8080 端口, ClientIP() 返回真实 IP. 但部署架构变化后此假设失效.

**缓解**: Internal API Key 校验在同一路由组, 即使 IP 伪造, 仍需正确 API Key.

**修复方向**: (1) 在 setup.go 中显式调用 `r.SetTrustedProxies([]string{"127.0.0.1"})` (或实际代理 IP); (2) 在 IP 白名单中间件中添加注释说明 TrustedProxies 依赖.

---

#### P1-2: CSP `connect-src 'wss: https:'` 过度宽松 — 允许连接任意 TLS 端点
**文件**: `security.go:19-20`
**严重性**: P1 — 数据泄露风险（与 Round #48 P0-1 SVG XSS 配合可构成完整攻击链）

```go
"connect-src 'self' wss: https:; " +
```

`connect-src` 指令控制浏览器允许发起的网络连接:
- `wss:` — 允许连接到 **任意** TLS WebSocket 服务器
- `https:` — 允许连接到 **任意** HTTPS 服务器

**攻击场景** (与 Round #48 P0-1 SVG stored XSS 组合):
1. 攻击者上传含 `<script>` 的 SVG 文件 (Round #48 P0-1)
2. 受害者浏览器加载 SVG → 执行恶意脚本
3. 恶意脚本建立 `wss://evil.example.com` WebSocket → CSP 允许 (`wss:` 无主机限制)
4. 脚本读取 localStorage/sessionStorage 中的 JWT Token → 通过 WebSocket 外泄

**修复方向**: `connect-src 'self' wss://sparkle.example.com https://sparkle.example.com;` — 限制为已知后端域名. 对于移动端 Flutter, CSP 不适用, 但 Web 版需要.

---

#### P1-3: CORS 缺少 `Access-Control-Max-Age` — 浏览器每次跨域请求都需预检
**文件**: `cors.go:10-28`
**严重性**: P1 — 性能影响 + 不必要的服务器负载

```go
// cors.go — 完整实现, 缺少 Max-Age
c.Header("Access-Control-Allow-Origin", origin)
c.Header("Access-Control-Allow-Credentials", "true")
c.Header("Access-Control-Allow-Headers", "Authorization, Content-Type, X-Requested-With")
c.Header("Access-Control-Allow-Methods", "GET, POST, PUT, PATCH, DELETE, OPTIONS")
// ❌ 缺少: c.Header("Access-Control-Max-Age", "86400")
```

没有 `Access-Control-Max-Age` 时, 浏览器默认缓存预检结果仅 5 秒 (Chromium 默认). Flutter Web 的每个跨域 API 请求前都会发送 OPTIONS 预检, 双倍请求量.

**量化影响**: 假设用户每分钟 10 次 API 调用, 每次需预检 → 20 请求/分钟. 加 `Max-Age: 86400` 后 → 首次预检后 24 小时内不再发送 → 10 请求/分钟.

**修复方向**: 添加 `c.Header("Access-Control-Max-Age", "86400")`.

---

#### P1-4: `X-Request-ID` 从客户端接受无校验 — 日志注入/污染风险
**文件**: `request_context.go:14`
**严重性**: P1 — 可观测性污染

```go
// :14 — 直接接受客户端提供的 request ID
requestID := headerOrDefault(c.GetHeader("X-Request-ID"), uuid.NewString())
```

客户端可发送 `X-Request-ID: <script>alert(1)</script>` 或 `X-Request-ID: \n\nFAKE LOG ENTRY`. 如果日志系统将 request ID 直接写入日志:
1. **日志注入**: 注入换行符伪造日志条目, 混淆审计追踪
2. **SIEM 污染**: 如果日志被 Splunk/ELK 索引, 恶意 request ID 可触发误报或污染查询
3. **关联断裂**: 使用非标准格式的 request ID 可能破坏请求追踪链

**修复方向**: 校验 `X-Request-ID` 格式 (仅允许 UUID v4 格式), 不符合则生成新 ID.

---

#### P1-5: 社群 WS 路由在 `/api/v1/` 路径下但绕过 API 组中间件
**文件**: `setup.go:404-409`
**严重性**: P1 — 安全审计遗漏风险

```go
// setup.go:404-409 — 在根路由注册, 不在 api Group 内
r.GET("/api/v1/community/groups/:group_id/ws",    // ← /api/v1/ 前缀
    middleware.WsAuthMiddleware(cfg, rdb),          // ← 仅 WsAuth
    handlers.wsProxy.HandleCommunityWS)
```

```go
// setup.go:427-429 — API Group 有额外中间件
api := r.Group("/api/v1")
api.Use(apiRateLimit)                              // ← WS 路由不经过
api.Use(middleware.TimeoutMiddleware(...))          // ← WS 路由不经过
```

社群 WS 路由 (`/api/v1/community/groups/:group_id/ws`, `/api/v1/community/ws/connect`) 路径以 `/api/v1/` 开头, 但注册在根路由而非 API 组. 安全审计人员看到 `/api/v1/` 前缀会假设这些路由有 rate limit + timeout 保护, 但实际上没有.

**双重缺失**: Round #50 已指出社区 WS 无每用户连接限制, 本次确认其根本原因是路由注册位置错误.

**修复方向**: (1) 将社群 WS 路由移入 API 组并添加 WS 感知的限流; (2) 或在根路由单独添加 WS 限流中间件.

---

### P2 — 改进建议

#### P2-1: SecurityHeadersMiddleware 使用 variadic cfg — HSTS 静默跳过

```go
// security.go:9 — variadic 参数, 允许不传 cfg
func SecurityHeadersMiddleware(cfg ...*config.Config) gin.HandlerFunc {
    // ...
    // :37 — 仅在 cfg 传入时设置 HSTS
    if len(cfg) > 0 && cfg[0] != nil && cfg[0].IsProduction() {
        c.Header("Strict-Transport-Security", ...)
    }
```

当前 setup.go:390 调用 `SecurityHeadersMiddleware(cfg)` 正确传入配置. 但 variadic 签名意味着未来重构时如果遗漏 cfg 参数, HSTS 会被静默跳过且无编译错误. 建议改为必需参数 `cfg *config.Config`.

---

#### P2-2: CORS OPTIONS 对非 allowed origin 返回 204 — 无服务端可观测性

```go
// cors.go:21-23 — 所有 OPTIONS 都返回 204
if c.Request.Method == http.MethodOptions {
    c.AbortWithStatus(http.StatusNoContent)
    return
}
```

非 allowed origin 的 OPTIONS 请求也返回 204 (只是不带 CORS 头). 浏览器正确阻止后续请求, 但服务端无法统计被阻止的跨域尝试. 建议对非 allowed origin 的 OPTIONS 记录 warning 级别日志.

---

#### P2-3: `isLongRunningRoute` 不完整 — 部分长运行路由可能被超时中断

```go
// timeout.go:43-54 — 仅排除 4 类路由
func isLongRunningRoute(path string) bool {
    // learning-paths, stt, capsules, plans/*/generate-tasks
}
```

未排除的长运行路由:
- `POST /api/v1/files/upload/complete` — 触发异步处理管道
- `POST /api/v1/reports/generate` — 学习报告生成
- `POST /api/v1/simulations/*` — 模拟引擎计算

如果这些路由的处理时间超过 requestTimeout (30s), 将被超时中断.

---

## 合规项

| 检查项 | 状态 |
|--------|------|
| 中间件顺序合理 | ✅ OTel → RequestContext → SecurityHeaders → CORS → RateLimit → Timeout → Auth |
| CORS Origin 白名单 | ✅ `IsOriginAllowed` 支持精确匹配 + 通配符 + scheme 校验 + port 校验 |
| Internal API Key 时序攻击防护 | ✅ `subtle.ConstantTimeCompare` 常量时间比较 (:20) |
| HSTS 仅生产环境 | ✅ `IsProduction()` 检查 (:37-39) |
| 超时 Context 传播 | ✅ `context.WithTimeout` + `c.Request.WithContext(ctx)` 正确传播 |
| 超时后清理 | ✅ `defer cancel()` 防止 context 泄漏 |
| IP 白名单支持 CIDR | ✅ `parseInternalWhitelist` 处理 IP + CIDR + IPv6 (:40-70) |
| 开发模式 IP 白名单旁路 | ✅ `IsDevelopment()` 时跳过 IP 检查 (:17) |
| Security Headers 完整 | ✅ CSP + X-Frame-Options + X-Content-Type-Options + X-XSS-Protection + Referrer-Policy + Permissions-Policy |
| X-XSS-Protection 兼容旧浏览器 | ✅ `1; mode=block` |
| RequestContext Trace ID 回退链 | ✅ OTel Span → 客户端 Header → UUID 生成 (三级回退) |

---

## 统计

| 级别 | 数量 |
|------|------|
| P0 | 0 |
| P1 | 5 |
| P2 | 3 |
| **总计** | **8** |

---

## 修复优先级建议

1. **P1-1** (TrustedProxies 未配置) — setup.go 添加 `r.SetTrustedProxies` — ~3 行
2. **P1-2** (CSP connect-src 过宽) — 限制为已知域名 — ~1 行
3. **P1-3** (无 Max-Age) — 添加 `Access-Control-Max-Age` — ~1 行
4. **P1-4** (X-Request-ID 无校验) — 添加 UUID 格式校验 — ~5 行
5. **P1-5** (WS 路由绕过 API 组) — 移入 API 组或单独加限流 — ~10 行
6. P2-1/P2-2/P2-3 — 随后续迭代修复

---

## 跨轮次因果链

| 本轮发现 | 关联轮次 | 关联模式 |
|----------|---------|---------|
| P1-2 (CSP connect-src 过宽) | Round #48 P0-1 (SVG stored XSS) | CSP 本应限制 XSS 影响, 但过宽的 connect-src 让 XSS 可外泄数据 |
| P1-5 (WS 路由绕过 API 组) | Round #50 P0-1 (WS 无连接限制) | 根本原因: 社群 WS 注册在根路由, 绕过 API 组中间件 |
| P1-5 (WS 路由绕过 API 组) | Round #6 P0-1 (Token Bucket 1000x) | Rate limit 中间件已实现但未应用到 WS 路由 — 同一部署缺陷 |
| P1-4 (Request ID 无校验) | Round #14 (输入校验/XSS防御) | 输入校验审计未覆盖中间件层的 header 注入 |

---

## Chris (Session 4) 复核 — 2026-04-23

> 逐条验证当前代码 vs 报告描述。2项已修复，3项确认仍存在。

| 原始发现 | 当前状态 | 复核结论 |
|----------|---------|---------|
| P1-1 (TrustedProxies 未配置) | setup.go 未调用 `r.SetTrustedProxies()`; docker-compose Gateway 直接暴露 8080 | **CONFIRMED REAL** — 当前部署无害，但部署架构变化后失效 |
| P1-2 (CSP connect-src 过宽) | security.go:20 `"connect-src 'self' wss: https:;"` 仍存在 | **CONFIRMED REAL** — 允许任意 WSS/HTTPS 端点 |
| P1-3 (无 Max-Age) | cors.go:19 `c.Header("Access-Control-Max-Age", "86400")` | **FALSE — 已修复** |
| P1-4 (Request ID 无校验) | request_context.go:14 调用 `sanitizedRequestID()` → UUID v4 格式校验; :45-56 `sanitizedTraceID()` → 32位hex校验 | **FALSE — 已修复** |
| P1-5 (WS路由绕过API组) | setup.go:404-409 社群WS在根路由; :428-430 API组有rateLimit+timeout | **CONFIRMED REAL** — 根本原因确认 |

**总结**: 5项P1中2项已修复(P1-3 Max-Age + P1-4 Request-ID校验)，3项确认仍存在。中间件安全链整体质量良好，无P0级问题。
