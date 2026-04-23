# 深度审计：Rate Limiting 完整链路

> 日期：2026-04-22 00:30
> 范围：Go Gateway 限流中间件（rate_limit.go + distributed_rate_limiter.go）→ Redis Lua 原子操作 → 本地降级 → 配置 → setup.go 路由挂载 → 绕过路径

## 审计发现

### P0 — 阻断性问题（3 项）

#### P0-1: Token Bucket Lua 脚本令牌补充速率 1000 倍过快，分布式限流实质失效
- **位置**: `backend/gateway/internal/middleware/distributed_rate_limiter.go:88-89`
- **问题**: `elapsed` 单位为毫秒（来自 `time.Now().UnixMilli()`），`rate` 单位为 tokens/second（:33），但乘法未做单位转换
  ```lua
  -- :88-89
  local elapsed = now - tonumber(last)    -- 毫秒
  local new_tokens = math.min(burst, tonumber(tokens) + elapsed * rate)  -- ms * tokens/s
  ```
  **正确公式应为**: `elapsed / 1000.0 * rate`
- **实际效果**: rate=10 tokens/s, elapsed=1000ms → 补充 10,000 tokens 而非 10；burst=60 的桶在 6ms 内即可回满
- **影响范围**: **所有 4 个分布式限流器**均使用 token bucket 模式（`UseSlidingWindow: false`，distributed_rate_limiter.go:216），auth/api/ws/galaxy 限流全部失效
  ```go
  // setup.go:412-413,471,484 — 全部使用 token bucket
  authRateLimit := middleware.HybridRateLimitMiddlewareSimple(rdb, 5.0, 15)
  apiRateLimit  := middleware.HybridRateLimitMiddlewareSimple(rdb, 30, 60)
  ```
- **修复**: Lua 脚本第 89 行改为 `elapsed / 1000.0 * rate`

#### P0-2: Telemetry 端点完全绕过所有限流，无认证检查
- **位置**: `rate_limit.go:465-472`
  ```go
  func shouldBypassGlobalRateLimit(c *gin.Context) bool {
      if c.Request.Method != http.MethodPost {
          return false
      }
      path := c.Request.URL.Path
      return strings.HasSuffix(path, "/api/v1/client-telemetry/events") ||
             strings.HasSuffix(path, "/api/v1/client-telemetry/events/batch")
  }
  ```
- **问题**: `shouldBypassGlobalRateLimit` 在 `HybridRateLimitMiddleware` 的最顶部（:407-410）短路返回，不检查认证状态
- **影响**: 攻击者可通过 POST `/api/v1/client-telemetry/events` 无限制发送请求，绕过所有限流；可用于 DoS 后端服务或数据注入
- **修复**: (1) 移除 bypass 或 (2) bypass 前检查认证状态 (3) 为 telemetry 添加独立限流

#### P0-3: Admin 和 Internal 端点无限流保护
- **位置**: `setup.go:500-722`（admin 路由）+ `setup.go:491-496`（internal 路由）
- **问题**: `/admin/*` 仅用 `AdminAuthMiddleware` 认证，`/internal/*` 仅用 `InternalAPIMiddleware` 验证 API key，均无限流中间件
- **影响**: 已认证的管理员或持有 internal API key 的服务可无限调用敏感操作（CQRS 重建、DLQ 管理、混沌工程端点）
- **修复**: 为 admin 和 internal 路由组添加独立限流中间件（如 10 RPS）

---

### P1 — 重要问题（4 项）

#### P1-1: Redis 不可用时降级为单实例本地限流，可被分布式攻击绕过
- **位置**: `rate_limit.go:436-443`
  ```go
  allowed, remaining, err = distRL.Allow(...)
  if err != nil {
      log.Printf("[HybridRateLimiter] Redis error: %v, falling back to local", err)
      limiter := localRL.getVisitor(limitKey)
      allowed = limiter.Allow()  // 每实例独立计数
  }
  ```
- **问题**: N 个 Gateway 实例时，攻击者实际限流 = N × 单实例限流
- **影响**: 3 实例部署下，30 RPS 限制变为 90 RPS
- **修复**: (1) Redis 不可用时考虑 fail-closed（拒绝请求）(2) 或添加 Redis 恢复后的补偿限流

#### P1-2: Sliding Window 不可用 — 仅 Token Bucket 被使用
- **位置**: `distributed_rate_limiter.go:216`
  ```go
  UseSlidingWindow: false,  // 硬编码
  ```
- **问题**: Sliding Window 实现正确（真正的滑动窗口 + Lua 原子性），但 `HybridRateLimitMiddlewareSimple` 硬编码不使用它
- **影响**: 系统有正确的滑动窗口实现但被浪费；token bucket（有 bug）反而是唯一活跃的算法
- **修复**: P0-1 修复后，考虑切换到 sliding window 模式作为默认（更严格的流量控制）

#### P1-3: X-RateLimit-Reset Header 不准确
- **位置**: `rate_limit.go:174,219`
  ```go
  c.Header("X-RateLimit-Reset", time.Now().Add(time.Second).Format(time.RFC3339))
  ```
- **问题**: Reset 时间始终为 now+1s，不反映实际令牌回补时间；Hybrid 中间件甚至不发送 Reset header（:459-460）
- **影响**: 客户端无法根据 header 精确计算重试时间
- **修复**: 计算实际令牌回满时间或滑动窗口结束时间

#### P1-4: 限流在认证之前执行，未认证请求仅按 IP 限流
- **位置**: `setup.go:427-428`
  ```go
  api := r.Group("/api/v1")
  api.Use(apiRateLimit)  // 限流在前
  // auth middleware 在各路由内部应用
  ```
- **问题**: 未认证请求以 `ip:{ClientIP}` 为 key，攻击者可通过代理池分散 IP 绕过限流；已认证用户的 user_id 限流粒度无法在全局层生效
- **影响**: IP 轮换攻击可绕过 30 RPS 限制
- **修复**: 考虑将认证前移至限流之前，或在限流中间件内检测认证状态做分层限流

---

### P2 — 改进建议（3 项）

#### P2-1: 本地限流器 cleanup 持锁遍历全量 map
- **位置**: `rate_limit.go:88-107`
- **问题**: cleanup goroutine 在 `rl.mu.Lock()` 下遍历所有 visitor，高并发时阻塞新请求
- **修复**: 分片锁或分批清理

#### P2-2: 限流配置硬编码在 setup.go，不支持运行时调整
- **位置**: `setup.go:412-413,484`
  ```go
  authRateLimit := middleware.HybridRateLimitMiddlewareSimple(rdb, 5.0, 15)  // 硬编码
  ```
- **修复**: 迁移到 config，支持环境变量覆盖

#### P2-3: 开发模式禁用 IP 白名单保护
- **位置**: `internal_ip_whitelist.go:17`
- **问题**: `IsDevelopment()` 返回 true 时白名单检查完全跳过
- **修复**: 开发模式保留检查但扩大白名单范围

---

### 合规项（4 项）

1. **Redis Lua 脚本原子性** ✅ — Token bucket 和 sliding window 都使用 Lua 脚本，Redis 保证原子执行
2. **Sliding Window 实现正确** ✅ — 真正的滑动窗口（ZREMRANGEBYSCORE + ZCARD + ZADD），非固定窗口
3. **Prometheus 指标** ✅ — `sparkle_rate_limiter_redis_fallback_total` 和 `sparkle_rate_limiter_redis_errors_total` 覆盖关键路径
4. **路由级隔离** ✅ — 限流 key 包含 routePath（:419），防止嘈杂端点饿死其他路由

---

## 数据流图

```
请求 → Gin Router
  │
  ├── shouldBypassGlobalRateLimit? → YES (telemetry) → c.Next() ⚠️ 无限流
  │
  ├── HybridRateLimitMiddleware
  │   ├── clientID = user_id || "ip:" + ClientIP
  │   ├── limitKey = clientID + ":" + method + ":" + routePath
  │   │
  │   ├── [Token Bucket] distRL.Allow(key)
  │   │   ├── Redis Lua: elapsed(ms) * rate(tokens/s) → 1000x 补充 ⚠️ P0-1
  │   │   ├── 实质: 桶几乎永远满，限流失效
  │   │   └── OK: 返回 allowed=true, remaining=burst
  │   │
  │   ├── [Sliding Window] swRL — 从未使用 ⚠️ (UseSlidingWindow=false)
  │   │
  │   ├── Redis 不可用 → 本地限流 ⚠️ 单实例限制
  │   │
  │   ├── allowed=false → 429 {error: "rate_limit_exceeded"}
  │   └── allowed=true → c.Next() + X-RateLimit-* headers
  │
  ↓
路由处理 (Auth → Handler → gRPC → Python)
  │
  ├── /admin/* → AdminAuth → 无限流 ⚠️ P0-3
  ├── /internal/* → InternalAPI → 无限流 ⚠️ P0-3
  └── /api/v1/* → apiRateLimit (token bucket, 失效) → 继续
```

---

## 建议修复方案

| 优先级 | 问题 | 修复方案 | 工作量 |
|--------|------|---------|--------|
| P0-1 | Token bucket 1000x 补充 | Lua 脚本改为 `elapsed / 1000.0 * rate` | 低（1 行 Lua） |
| P0-2 | Telemetry 绕过限流 | 添加认证检查或移除 bypass | 低（~10 行 Go） |
| P0-3 | Admin/Internal 无限流 | 添加独立限流中间件 | 低（~5 行 Go/路由） |
| P1-1 | Redis 降级单实例限制 | 添加 fail-closed 选项 | 中（~30 行 Go） |
| P1-2 | Sliding Window 未启用 | 修复 token bucket 后评估切换 | 低（1 行配置） |
| P1-3 | Reset header 不准确 | 计算实际回补时间 | 低（~10 行 Go） |
| P1-4 | 限流在认证之前 | 调整中间件顺序或分层限流 | 中（~50 行 Go） |

---

## 复核笔记

> **复核日期**: 2026-04-24
> **复核员**: Claude Deep Auditor

### 复核方法

逐项验证原审计发现是否与当前代码一致。

### 逐项复核结果

| 编号 | 原发现 | 状态 | 备注 |
|------|--------|------|------|
| P0-1 | Token Bucket Lua 脚本 1000x 补充速率 | ✅ 已验证 | `distributed_rate_limiter.go:89` 仍为 `elapsed * rate`，无 `÷1000` 转换 |
| P0-2 | Telemetry 端点绕过限流无认证 | ✅ 已验证 | `rate_limit.go:407-410` `shouldBypassGlobalRateLimit` 仍存在，:465-472 仍仅检查路径后缀 |
| P0-3 | Admin/Internal 端点无限流 | ✅ 已验证 | 代码结构未变，admin/internal 路由组仍无限流中间件 |
| P1-1 | Redis 降级单实例本地限流 | ✅ 已验证 | `rate_limit.go:436-443` fallback 逻辑未变 |
| P1-2 | Sliding Window 未启用 | ✅ 已验证 | `UseSlidingWindow: false` 仍硬编码 |
| P1-3 | X-RateLimit-Reset 不准确 | ✅ 已验证 | 仍为 `now+1s` |
| P1-4 | 限流在认证之前 | ✅ 已验证 | `setup.go` 中 `apiRateLimit` 仍在 auth middleware 之前 |
| P2-1 | 本地限流器 cleanup 持锁遍历 | ✅ 已验证 | 未变 |
| P2-2 | 限流配置硬编码 | ✅ 已验证 | 未变 |
| P2-3 | 开发模式禁用白名单 | ✅ 已验证 | 未变 |

### 总结

- **0/10 已修复**
- 所有行号引用仍然准确
- P0-1 (1000x token 补充) 仍然是最严重的问题 — 所有分布式限流实质失效
- 代码自审计以来完全未动
