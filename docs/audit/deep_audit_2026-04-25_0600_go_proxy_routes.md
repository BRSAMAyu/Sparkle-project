# 深度审计 #59 — Go Gateway REST Proxy Routes 完整链路

> **日期**: 2026-04-25 06:00
> **模块**: Go Gateway REST Proxy Routes — 路由配置 → 认证守卫 → 代理转发 → 错误处理 → 安全过滤
> **范围**: `backend/gateway/cmd/server/`, `backend/gateway/internal/handler/`, `backend/gateway/internal/middleware/`
> **总计**: 23 个文件, ~6,232 行
> **审计员**: Claude Deep Auditor (Round 59)

---

## 审计范围

### 文件清单
| 文件 | 行数 | 职责 |
|------|------|------|
| `cmd/server/main.go` | 125 | 入口、graceful shutdown |
| `cmd/server/setup.go` | 811 | 路由注册、代理初始化、handler/CQRS 绑定 |
| `internal/handler/proxy_routes.go` | 738 | 代理路由注册（核心审计目标） |
| `internal/handler/proxy_routes_test.go` | 313 | 代理路由注册测试 |
| `internal/handler/websocket_proxy.go` | 291 | WS 双向代理（community group/personal） |
| `internal/handler/galaxy_handler.go` | 267 | Galaxy gRPC + 代理混合路由 |
| `internal/handler/health.go` | 324 | 健康检查（live/ready/detail） |
| `internal/handler/data_consistency_handler.go` | 164 | Redis/PG 一致性校验 |
| `internal/handler/auth.go` | 211 | Apple 登录、JWT 签发 |
| `internal/handler/error_book.go` | 329 | 错题本 gRPC handler |
| `internal/handler/file_handler.go` | 621 | 文件上传/存储 handler |
| `internal/middleware/auth.go` | 422 | JWT 认证 + token 黑名单 + Fail-Closed |
| `internal/middleware/internal_api.go` | 27 | Internal API Key 验证 |
| `internal/middleware/cors.go` | 28 | CORS 中间件 |
| `internal/middleware/security.go` | 49 | 安全头部注入 |
| `internal/middleware/rate_limit.go` | 521 | 速率限制（本地 + Redis） |
| `internal/middleware/timeout.go` | 54 | 请求超时 |
| `internal/middleware/ab_test_middleware.go` | 350 | A/B 测试变体分配 |
| `internal/middleware/request_context.go` | 43 | Request-ID / Trace-ID 注入 |
| `internal/middleware/internal_ip_whitelist.go` | 71 | 内部 IP 白名单 |
| `internal/middleware/chaos_guard.go` | 23 | Chaos 端点守卫 |
| `internal/middleware/ws_auth.go` | 171 | WebSocket 认证（JWT header / query / ticket） |
| `internal/middleware/distributed_rate_limiter.go` | 279 | 分布式限流（Token Bucket + Sliding Window） |

---

## 数据流图

```
Client Request
    |
    v
[gin.Engine]  <-- gin.Default()
    |
    +-- /metrics           --> Prometheus handler
    +-- otelgin middleware  --> OpenTelemetry tracing
    +-- RequestContextMiddleware  --> X-Request-ID, X-Trace-ID
    +-- SecurityHeadersMiddleware  --> CSP, X-Frame-Options, HSTS
    +-- CORSMiddleware (conditional)  --> OPTIONS preflight, origin check
    |
    +-- /healthz, /readyz, /live, /ready, /health  --> HealthHandler (no auth)
    |
    +-- /ws/chat, /ws/files, /ws/stt  --> WsAuthMiddleware --> ChatOrchestrator
    |
    +-- /api/v1/community/groups/:id/ws  --> WsAuthMiddleware --> WebSocketProxy
    +-- /api/v1/community/ws/connect     --> WsAuthMiddleware --> WebSocketProxy
    |
    +-- /api/v1  <-- api RouterGroup
    |   +-- apiRateLimit (30 rps, burst 60)
    |   +-- TimeoutMiddleware (30s default)
    |   |
    |   +-- /health, /health/cqrs       --> inline handler (no auth)
    |   +-- /auth/apple                  --> authRateLimit (5 rps, burst 15) --> AppleLogin
    |   +-- /ws/ticket                   --> authMiddleware + ticketRateLimit --> WSTicketHandler
    |   +-- /chat/sessions              --> authMiddleware --> ChatHistoryHandler
    |   +-- /chat/history/:id           --> authMiddleware --> ChatHistoryHandler
    |   +-- /groups/:id/messages        --> authMiddleware --> GroupChatHandler
    |   +-- /errors/*                   --> authMiddleware --> ErrorBookHandler (gRPC)
    |   +-- /files/*                    --> authMiddleware --> FileHandler
    |   +-- /chat/cache/check           --> DataConsistencyHandler (NO AUTH!)
    |   +-- /chat/db/check              --> DataConsistencyHandler (NO AUTH!)
    |   +-- /galaxy/*                   --> authMiddleware + rateLimit --> GalaxyHandler
    |   +-- [ALL proxy routes]          --> authMiddleware --> proxyWithHeaders --> ReverseProxy
    |       accountability, tasks, plans, learning-paths, chat, users/*, user/*,
    |       achievements, calendar, recommendations, suggestions, experiments/*,
    |       agent-stats/*, assets/*, multi-agent/*, capsules, seed-libraries,
    |       community, interventions/*, dashboard/*, background-tasks, reviews/*,
    |       stats/*, events/*, signals/*, preferences/*, notifications, notification-center,
    |       devices/*, omnibar/*, prediction/*, multi-intent/*, subjects, client-telemetry,
    |       predictive/*, ingestion/*, documents/*, stt, focus/*, vocabulary/*,
    |       translation/*, decay/*, ws/health+stats+metrics, leaderboards/*, cognitive/*,
    |       memory/*, visual-elements, profile/*, observability/*, theater, simulation/*,
    |       learning-reports/*, shop/*, photons/*, inventory/*
    |
    +-- /internal  <-- InternalAPIKeyMiddleware + InternalIPWhitelistMiddleware
    |   +-- /interventions/push  --> InterventionPushHandler
    |   +-- /signals/push        --> SignalPushHandler
    |
    +-- /swagger/*any  --> Swagger UI
    |
    +-- /admin  <-- AdminAuthMiddleware
    |   +-- /chaos/*    --> ChaosGuardMiddleware --> chaos handlers
    |   +-- /cqrs/*     --> projection/dlq/outbox management
    |
    +-- NoRoute fallback
        +-- /api/v1/auth*  --> authRateLimit --> proxy (unauthenticated proxy!)
        +-- /docs*, /redoc*, /openapi.json  --> proxy
        +-- else  --> 404 JSON
```

---

## 审计发现

### P0 -- 严重缺陷

#### P0-1: DataConsistencyHandler 端点缺少认证保护
- **文件**: `cmd/server/setup.go:481`
- **严重度**: P0 (数据泄露风险)
- **代码**:
```go
handlers.dataConsistencyHandler.RegisterRoutes(api)
```
`RegisterRoutes` 方法（`data_consistency_handler.go:38`）直接在 `api` group 上注册路由，但没有传入 `authMiddleware`：
```go
func (h *DataConsistencyHandler) RegisterRoutes(api *gin.RouterGroup) {
    api.GET("/chat/cache/check", h.checkCache)  // No auth!
    api.GET("/chat/db/check", h.checkDatabase)   // No auth!
}
```
这些端点需要 `message_id` 和 `conversation_id` 查询参数，允许未经认证的用户：
- 枚举聊天消息 ID（通过观察 exists/not-exists 差异）
- 读取缓存中的完整消息内容（`checkCache` 返回整个 `foundMessage` 对象）
- 通过数据库查询确认消息存在性
- **影响**: 任何未经认证的用户都可以通过暴力猜测 UUID 来读取其他用户的聊天消息
- **修复**: 传入 `authMiddleware` 并在 handler 中校验 `user_id` 与消息所有者一致

#### P0-2: NoRoute 回退将 auth 路径无认证代理到 Python 后端
- **文件**: `cmd/server/setup.go:733-751`
- **严重度**: P0 (认证绕过 + SSRF 风险)
- **代码**:
```go
r.NoRoute(func(c *gin.Context) {
    // ...
    if strings.HasPrefix(path, "/api/v1/auth") ||
        path == "/api/v1/health" ||
        strings.HasPrefix(path, "/docs") ||
        strings.HasPrefix(path, "/redoc") ||
        strings.HasPrefix(path, "/openapi.json") {
        if strings.HasPrefix(path, "/api/v1/auth") {
            authRateLimit(c)
            if c.IsAborted() {
                return
            }
        }
        proxy.proxy.ServeHTTP(c.Writer, c.Request)  // No auth!
        return
    }
    // ...
})
```
`/api/v1/auth` 前缀下的 **所有** 路径都直接代理到 Python 后端，不经过 JWT 认证。虽然 `/auth/apple` 确实不应需要 JWT，但 Python 后端可能注册了其他 `/auth/*` 端点（如 `/auth/admin/*`, `/auth/debug/*`）且没有独立的认证保护。如果 Python 后端的某些 auth 子路由缺乏内部保护，攻击者可以未认证访问。
- **影响**: 取决于 Python 后端 `/auth/*` 路径的安全性——如果存在任何内部/调试端点，则可能被滥用
- **修复**: 将 NoRoute 代理限制到明确已知的公开路径（如 `/api/v1/auth/apple`, `/api/v1/auth/refresh`），而非整个 `/auth` 前缀

#### P0-3: ReverseProxy Director 未设置 `X-Forwarded-For` 和 `X-Forwarded-Proto` 头
- **文件**: `cmd/server/setup.go:782-787`
- **严重度**: P0 (Python 后端无法获取真实客户端 IP，影响速率限制和审计)
- **代码**:
```go
proxy.Director = func(req *http.Request) {
    req.URL.Scheme = targetURL.Scheme
    req.URL.Host = targetURL.Host
    req.Host = targetURL.Host
    otel.GetTextMapPropagator().Inject(req.Context(), propagation.HeaderCarrier(req.Header))
}
```
`httputil.ReverseProxy` 的默认 Director **不会**自动添加 `X-Forwarded-For`、`X-Forwarded-Proto`、`X-Forwarded-Host` 头。Python 后端调用 `request.client.host` 将得到 Gateway 的内部 IP 而非真实客户端 IP。这影响：
- Python 端 IP 依赖的速率限制
- 审计日志中的客户端 IP
- 地理位置相关功能
- **修复**: 在 Director 中添加标准转发头

### P1 -- 重要问题

#### P1-1: 11 个 Python 后端路由组缺少 Go Gateway 代理路由
- **文件**: `proxy_routes.go` vs `backend/app/api/v1/router.py`
- **严重度**: P1 (前端无法访问这些 API)
- **缺失路由组**:

| Python 模块 | Python 前缀 | Go 代理状态 |
|-------------|-------------|-------------|
| `analytics` | `/analytics` | **缺失** |
| `executions` | `/executions` | **缺失** |
| `executions_admin` | `/executions-admin` (推测) | **缺失** |
| `subtasks` | 自包含（在 `/tasks/{id}/subtasks` 下） | **缺失** |
| `nightly_reviews` | 自包含前缀 | **缺失** |
| `feedback_admin` | 自包含前缀 | **缺失** |
| `dlq_admin` | 自包含前缀 | **缺失** |
| `audit` | `/audit` | **缺失** |
| `user_persona_batch` | 自包含前缀 | **缺失** |
| `memory_admin` | 自包含前缀 | **缺失** |
| `graph_monitor` / `graphrag_trace` | `/monitor/graph` | **缺失** (条件启用) |

- **影响**: 前端通过 Go Gateway 无法访问这些 API（会收到 404）。如果前端直接调用 Python 后端则绕过了 Gateway 的认证/速率限制。
- **修复**: 在 `RegisterProxyRoutes` 中添加缺失的代理路由组，或通过 NoRoute 回退的通配代理处理

#### P1-2: `users` 和 `user` 路由组使用 `Any("/*path")` 通配过于宽松
- **文件**: `proxy_routes.go:132, 139`
- **严重度**: P1 (潜在 SSRF / 意外代理)
- **代码**:
```go
users.Any("/*path", h.proxyWithHeaders)
// ...
user.Any("/*path", h.proxyWithHeaders)
```
这两个路由组将所有 HTTP 方法（GET/POST/PUT/PATCH/DELETE 等）的所有子路径全部代理到 Python 后端。如果 Python 端注册了任何管理/内部端点（如 `/users/admin/reset-password`），它们会被未经授权的路径暴露。同样的问题出现在 13 个其他路由组上（`experiments`, `agent-stats`, `assets`, `multi-agent`, `interventions`, `dashboard`, `reviews`, `stats`, `events`, `signals`, `preferences`, `devices`, `omnibar`, `prediction`, `multi-intent`, `focus`, `vocabulary`, `translation`, `decay`, `leaderboards`, `cognitive`, `memory`, `observability`, `simulation`, `learning-reports`, `shop`, `photons`, `inventory`, `profile`）。
- **影响**: 通配符代理降低了可观测性和安全审计粒度；Python 端任何新增端点自动暴露
- **修复**: 将 `Any("/*path")` 路由逐步替换为明确的路由定义，至少对写操作（POST/PUT/DELETE）列出明确路径

#### P1-3: `client-telemetry` POST 端点无认证且无输入验证
- **文件**: `proxy_routes.go:517-521`
- **严重度**: P1 (滥用风险)
- **代码**:
```go
clientTelemetry := api.Group("/client-telemetry")
{
    clientTelemetry.POST("/events", h.proxyWithHeaders)
    clientTelemetry.POST("/events/batch", h.proxyWithHeaders)
}
```
遥测写入端点完全无认证保护。虽然有 `shouldBypassGlobalRateLimit` 使其绕过全局速率限制，但攻击者可以：
- 发送大量伪造遥测数据淹没存储
- 注入恶意 payload 到遥测系统
- **影响**: 遥测数据可能被污染；存储可能被滥用
- **修复**: 考虑添加基本认证（至少验证设备 ID 或 API key），或添加请求体大小限制

#### P1-4: A/B 测试中间件在代理热路径上执行同步 HTTP 调用
- **文件**: `middleware/ab_test_middleware.go:102-146`
- **严重度**: P1 (延迟 + 可用性风险)
- **代码**:
```go
func (m *ABTestMiddleware) assignVariant(
    ctx context.Context,
    experimentID string,
    authHeader string,
) (*VariantInfo, error) {
    // ...
    resp, err := m.httpClient.Do(req)  // Synchronous HTTP call to Python backend!
```
`proxyWithHeaders` 方法（`proxy_routes.go:705-726`）在每个代理请求上调用 `h.abTestMiddleware.AssignVariant()(c)`，这会：
1. 同步调用 Python 后端的 `/api/v1/experiments/{id}/assign`
2. 如果 Python 后端慢或不可用，增加所有代理请求的延迟
3. 虽然 3s 超时存在，但 3s 对热路径来说是灾难性的
- **影响**: A/B 测试服务故障会级联到所有代理路由，增加 P99 延迟
- **修复**: 将 A/B 测试变体分配改为异步/缓存模式，或添加快速失败逻辑

#### P1-5: Galaxy handler 有独立的 ReverseProxy 实例，未设置 OTEL 传播
- **文件**: `handler/galaxy_handler.go:42-47`
- **严重度**: P1 (追踪断裂)
- **代码**:
```go
proxy := httputil.NewSingleHostReverseProxy(targetURL)
proxy.FlushInterval = -1
proxy.Director = func(req *http.Request) {
    req.URL.Scheme = targetURL.Scheme
    req.URL.Host = targetURL.Host
    // Missing: OTEL propagation, X-Forwarded-For, X-User-ID
}
```
与主代理（`setup.go:786`）不同，Galaxy 代理的 Director 不包含 `otel.GetTextMapPropagator().Inject()` 调用。通过 Galaxy 代理的请求在 Python 后端将无法与上游追踪关联。同时也不转发 `X-User-ID`（虽然在 `ProxyToBackend` 方法中手动设置，但如果 Director 被单独调用则不会）。
- **影响**: Galaxy 请求的分布式追踪链断裂
- **修复**: 在 Galaxy proxy Director 中添加 OTEL 传播

#### P1-6: 代理路由未设置请求体大小限制
- **文件**: `proxy_routes.go` (全文件), `cmd/server/setup.go`
- **严重度**: P1 (DoS 向量)
- 在 `setupRouter` 中，`api` group 没有全局请求体大小限制 middleware。`gin.Default()` 不限制请求体大小。只有 `file_handler.go` 有 `c.Request.Body = http.MaxBytesReader(c.Writer, c.Request.Body, ...)` 但这只适用于文件上传端点。
- 攻击者可以向任何代理路由（如 `/api/v1/chat`, `/api/v1/plans`）发送超大请求体，耗尽 Gateway 内存。
- **影响**: 任何代理端点都可以被用于 OOM 攻击
- **修复**: 在 `api` group 添加全局请求体大小限制 middleware（如 10MB）

### P2 -- 改进建议

#### P2-1: 路由注册使用 `Any("/*path")` 导致 Gin 路由表不可见
- **文件**: `proxy_routes.go` 多处
- 13+ 个路由组使用通配符匹配，使得 Gin 的路由调试端点（如 `r.Routes()`）无法显示实际可用的子路径。这降低了可观测性。
- **建议**: 考虑添加 `/api/v1/routes` 端点返回所有已注册路由的列表

#### P2-2: 超时中间件对长运行路由的豁免列表不完整
- **文件**: `middleware/timeout.go:43-54`
- **代码**:
```go
func isLongRunningRoute(path string) bool {
    if strings.HasPrefix(path, "/api/v1/learning-paths/") { return true }
    if path == "/api/v1/stt/transcribe" { return true }
    if path == "/api/v1/capsules/generate" || ... { return true }
    return strings.HasPrefix(path, "/api/v1/plans/") && strings.HasSuffix(path, "/generate-tasks")
}
```
缺少以下可能的长运行端点：
- `/api/v1/simulation/*` -- 模拟交互可能持续数分钟
- `/api/v1/theater/predictions/generate` -- 预测生成
- `/api/v1/ingestion/*` -- 文档摄取可能耗时
- `/api/v1/community/groups/:id/files` -- 文件上传

#### P2-3: `fmt.Printf` 在 A/B 测试中间件中用于日志记录
- **文件**: `middleware/ab_test_middleware.go:75, 259, 279, 289, 294`
- **代码**:
```go
fmt.Printf("A/B test assignment failed: %v\n", err)
```
生产代码使用 `fmt.Printf` 而非结构化日志。这在 Kubernetes 环境中会导致日志格式不一致、难以搜索和聚合。
- **建议**: 替换为注入的 `zap.Logger`

#### P2-4: Rate limiter 的 `RateLimiter.Stop()` 从未被调用
- **文件**: `middleware/rate_limit.go:59-66`
- 每个 `NewRateLimiter` 启动一个后台 goroutine（`cleanupVisitors`），但 `Stop()` 方法从未在 shutdown 流程中调用。这会导致 graceful shutdown 时 goroutine 泄漏。
- **影响**: 温和泄漏，不影响运行时
- **建议**: 在 shutdown 时清理所有 rate limiter 实例

#### P2-5: 测试覆盖率不足
- **文件**: `proxy_routes_test.go`
- 当前测试只验证路由注册数量和 `client-telemetry` 的认证边界。缺少：
  - 代理转发的集成测试
  - 错误场景测试（Python 后端宕机）
  - 超时测试
  - 头部转发正确性测试
  - 认证传播测试

#### P2-6: `seed-libraries` 路由有重复路径
- **文件**: `proxy_routes.go:257-260`
- **代码**:
```go
seedLibs.POST("/:id/subscribe", h.proxyWithHeaders)
seedLibs.DELETE("/:id/unsubscribe", h.proxyWithHeaders)
seedLibs.POST("/subscribe/:id", h.proxyWithHeaders)
seedLibs.DELETE("/subscribe/:id", h.proxyWithHeaders)
```
`/:id/subscribe` 和 `/subscribe/:id` 是两个不同的路径模式，指向相同的逻辑。这可能是 Python 后端 API 版本迁移的遗留物。不会造成功能问题，但增加了维护负担。

#### P2-7: 缺少 `/_internal` 路径前缀和 `/_admin` 的 HTTP 方法限制
- **文件**: `cmd/server/setup.go:491-495, 499`
- `/internal` 和 `/admin` 路径没有在标准互联网防火墙规则中常见的保留前缀下。如果使用 CDN 或反向代理，这些路径可能需要额外规则来阻止外部访问。
- **建议**: 考虑使用 `/_internal` 和 `/_admin` 前缀或确保上游代理阻止这些路径

---

## 合规项

| 检查项 | 状态 | 备注 |
|--------|------|------|
| 所有代理路由需要认证 | FAIL | P0-1: DataConsistency 无认证; P1-3: telemetry POST 无认证 |
| JWT 正确传播到后端 | PASS | `SetProxyUserContextHeaders` 正确设置 X-User-ID + Authorization |
| CORS preflight 正确处理 | PASS | OPTIONS 返回 204，Origin 匹配检查正确 |
| 速率限制覆盖 | PASS | 全局 30rps/60burst + auth 独立 5rps/15burst + Galaxy 独立 10/20 |
| 内部端点保护 | PASS | InternalAPIKey + IPWhitelist 双重保护 |
| Admin 端点保护 | PASS | AdminSecret + ChaosGuard 双重保护 |
| 请求超时 | PASS | 默认 30s，长运行路由豁免 |
| 连接池配置 | PASS | MaxIdleConns=100, MaxConnsPerHost=100, KeepAlive=30s |
| 安全头部 | PASS | CSP, X-Frame-Options, HSTS (prod), X-Content-Type-Options 等 |
| OTEL 追踪传播 | FAIL | P1-5: Galaxy handler 未传播 |
| 请求体大小限制 | FAIL | P1-6: 代理路由无全局限制 |
| X-Forwarded 头部 | FAIL | P0-3: Director 未设置转发头 |
| NoRoute 安全 | FAIL | P0-2: auth 前缀全量代理 |
| Python-Go 路由同步 | FAIL | P1-1: 11 个路由组缺失 |

---

## 统计

| 级别 | 数量 |
|------|------|
| P0 | 3 |
| P1 | 6 |
| P2 | 7 |
| **总计** | **16** |

---

## 修复优先级建议

### 立即修复 (P0)
1. **P0-1**: 给 `DataConsistencyHandler.RegisterRoutes` 添加 `authMiddleware` 参数，确保认证 + 所有者校验
2. **P0-2**: 收紧 NoRoute fallback 白名单，只代理 `/api/v1/auth/apple` 和 `/api/v1/auth/refresh` 等已知公开路径
3. **P0-3**: 在 proxy Director 中添加 `X-Forwarded-For`, `X-Forwarded-Proto`, `X-Forwarded-Host`

### 短期修复 (P1)
4. **P1-1**: 添加缺失的代理路由组（`/analytics`, `/executions`, `/subtasks` 等）
5. **P1-3**: 给 telemetry POST 添加基本认证或请求限制
6. **P1-4**: 将 A/B 测试变体分配改为异步或缓存模式
7. **P1-5**: Galaxy proxy Director 添加 OTEL 传播
8. **P1-6**: 添加全局请求体大小限制 middleware（建议 10MB）

### 中期改进 (P2)
9. 逐步将 `Any("/*path")` 替换为明确路由定义
10. 完善长运行路由豁免列表
11. 添加代理转发集成测试

---

## 跨轮次因果链

| 本轮发现 | 关联轮次 | 关联模式 |
|----------|---------|---------|
| P0-1 DataConsistency 无认证 | 所有 "我的" 页面审计 (2026-03-31) | 同类认证遗漏模式 |
| P0-3 缺少 X-Forwarded 头部 | Data Utilization Analysis (2026-04-06) | Python 端无法做 IP 级速率限制 |
| P1-1 Python-Go 路由不同步 | 产品价值共识 (2026-04-02) | executions 是核心执行闭环的一部分 |
| P1-4 A/B 测试同步调用 | 性能审计通用 | 热路径同步外部调用模式 |
| P1-5 Galaxy 追踪断裂 | CLAUDE.md 热路径分析 | Galaxy 是关键交互路径 |
