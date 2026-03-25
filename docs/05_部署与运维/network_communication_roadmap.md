# 网络通信层阶段性升级方案

> **文档版本**: 1.0
> **最后更新**: 2026-03-16
> **状态**: Phase 1 已完成，Phase 2 进行中

---

## 背景

Sparkle 项目采用三层架构：
```
Flutter Mobile  ←→  Go Gateway  ←→  Python Engine (gRPC)
     ↓                   ↓
  WebSocket          Redis/PostgreSQL
```

网络通信层是整个系统的核心基础设施，直接影响用户体验和系统稳定性。经过全面审查，我们识别出多个需要修复的问题，并按优先级分为三个阶段。

---

## Phase 1 (P0) - 已完成 ✅

### 目标
修复影响用户体验的紧急问题

### 已完成的工作

#### 1. Go Gateway 健康检查与熔断器
**文件**: `backend/gateway/internal/agent/health_checker.go`

- ✅ 实现了 `AgentHealthChecker` 定期检查 Python gRPC 服务健康状态
- ✅ 实现了完整的熔断器状态机：
  ```
  Closed → Open → HalfOpen → Closed
  ```
- ✅ 配置项：
  - `AGENT_HEALTH_CHECK_INTERVAL` (默认 10秒)
  - `AGENT_HEALTH_CHECK_TIMEOUT` (默认 5秒)
  - `CIRCUIT_BREAKER_THRESHOLD` (默认 5次失败触发熔断)

**问题修复**: Python 服务不可用时，Go Gateway 现在可以返回降级响应而非完全失败

#### 2. Flutter 心跳超时检测
**文件**: `mobile/lib/features/chat/data/services/websocket_chat_service_v2.dart`

- ✅ 添加了心跳超时检测机制
- ✅ 连续 3 次心跳失败后自动重连
- ✅ 心跳指标监控 (RTT 计算)

**配置**:
- 心跳间隔: 30秒
- 心跳超时: 90秒
- 最大连续失败: 3次

#### 3. ACK/NACK 消息确认协议
**文件**:
- `proto/websocket.proto`
- `mobile/lib/features/chat/data/models/chat_stream_events.dart`

- ✅ 添加了 `MessageAck` 和 `MessageNack` 消息类型
- ✅ Flutter 端添加了 `AckEvent` 和 `NackEvent` 事件解析

**问题修复**: 断线期间发送的消息现在有确认机制，不会静默丢失

#### 4. Proto 定义更新
**文件**: `proto/websocket.proto`

- ✅ 添加了 `HeartbeatPing` 和 `HeartbeatPong` 消息类型
- ✅ 添加了 `MessageAck` 和 `MessageNack` 消息类型

### 遗留问题
1. **离线消息队列**: Flutter 端的本地持久化队列尚未完全实现
2. **服务端 ACK 发送**: Go Gateway 收到消息后发送 ACK 的逻辑未集成

---

## Phase 2 (P1) - 进行中 🔄

### 目标
提升系统可扩展性、性能和安全性

### 正在进行的工作

#### 1. 分布式限流 (Distributed Rate Limiting)
**文件**: `backend/gateway/internal/middleware/distributed_rate_limiter.go`

**已完成**:
- ✅ `DistributedRateLimiter` - Redis Token Bucket 实现
- ✅ `SlidingWindowRateLimiter` - Redis 滑动窗口实现
- ✅ `HybridRateLimitMiddleware` - Redis 优先，本地降级

**待完成**:
- ⏳ 修复编译错误（类型引用问题）
- ⏳ 配置项集成到 `config.go`
- ⏳ Python 端限流器更新

**算法对比**:
| 猑战桶 | 滑动窗口 |
|---------|---------|
| 允许突发流量 | 更平滑的限制 |
| 内存效率高 | 精度更高 |
| 宯现简单 | 錅要 Redis ZSET |

#### 2. WebSocket 消息压缩
**文件**: `backend/gateway/internal/handler/websocket_factory.go` (待创建)

**计划**:
- 使用 `gorilla/websocket` 的 `permessage-deflate` 扩展
- 仅压缩 >1KB 的消息
- 压缩级别可配置 (默认 BestSpeed)

**预期效果**: JSON 消息压缩率 40-70%

#### 3. 安全加固 (Security Hardening)
**文件**: `backend/gateway/internal/middleware/security.go`

**计划**:
- 启用 HSTS (生产环境)
- 增强 CSP 头部
- TLS 配置支持

**配置项**:
```bash
HTTPS_ENABLED=true
HTTPS_CERT_FILE=/path/to/cert.pem
HTTPS_KEY_FILE=/path/to/key.pem
HSTS_MAX_AGE_SECONDS=31536000
```

### 当前遇到的编译问题

```
internal/middleware/rate_limit.go:372:6: HybridRateLimitMiddleware redeclared
internal/middleware/distributed_rate_limiter.go:248:34: undefined: rate
```

**原因分析**:
1. `rate_limit.go` 和 `distributed_rate_limiter.go` 都定义了 `HybridRateLimitMiddleware`
2. `distributed_rate_limiter.go` 中引用了 `rate_limit.go` 的类型，但导入路径问题

**解决方案**:
- 保留 `distributed_rate_limiter.go` 中的高级版本
- 删除 `rate_limit.go` 中的重复定义
- 添加缺失的 `rate.Limit` 类型导入

---

## Phase 3 (P2) - 计划中 📋

### 目标
高级特性与长期稳定性

### 计划工作

#### 1. 离线消息队列 (Flutter)
**文件**: `mobile/lib/core/offline/chat_message_queue.dart`

- Isar 本地持久化
- 指数退避重自动重试
- 网络恢复后同步

#### 2. 服务端 ACK 集成
**文件**: `backend/gateway/internal/handler/chat_orchestrator.go`

- 收到消息后立即发送 ACK
- 处理失败时发送 NACK
- 支持消息去重

#### 3. 连接池优化
- WebSocket 连接池监控
- 连接生命周期管理
- 空闲连接回收

#### 4. 可观察性增强
- Prometheus 指标完善
- 分布式追踪集成
- 性能瓶颈告警

---

## 配置变量汇总

### Phase 1 配置
```bash
# 寴康检查
AGENT_HEALTH_CHECK_INTERVAL=10
AGENT_HEALTH_CHECK_TIMEOUT=5
CIRCUIT_BREAKER_THRESHOLD=5
CIRCUIT_BREAKER_SUCCESS_THRESHOLD=2
CIRCUIT_BREAKER_TIMEOUT=30
CIRCUIT_BREAKER_HALF_OPEN_REQUESTS=3
```

### Phase 2 配置
```bash
# 分布式限流
RATE_LIMITER_BACKEND=redis        # "local" or "redis"
RATE_LIMITER_TOKEN_RATE=10.0      # tokens/second
RATE_LIMITER_BURST=30             # burst capacity
RATE_LIMITER_WINDOW_SECONDS=60    # sliding window size
RATE_LIMITER_CLEANUP_SECONDS=30   # cleanup interval

# WebSocket 压缩
WS_COMPRESSION_ENABLED=true       # Enable compression
WS_COMPRESSION_LEVEL=1            # 0-9 (1=fastest)
WS_COMPRESSION_THRESHOLD=1024     # Min bytes to compress

# TLS/HTTPS
HTTPS_ENABLED=true
HTTPS_CERT_FILE=/path/to/cert.pem
HTTPS_KEY_FILE=/path/to/key.pem
HSTS_MAX_AGE_SECONDS=31536000
```

---

## 鯰鱼图

```
┌─────────────────────────────────────────────────────────────────────────┐──────────────────┐
│                     Phase 1 (P0)                    │     Phase 2 (P1)           │   Phase 3 (P2)          │
├─────────────────────────────────────────────────────────────────────────┴──────────────────┤
│ Flutter 心跳超时        │ ✅ 完成                              │   -                    │   -                    │
│ Flutter ACK/NACK        │ ✅ 协议定义                              │   离线队列              │   消息可靠性完善       │
│ Go 熔断器              │ ✅ 完成                              │   -                    │   -                    │
│ Go 健康检查              │ ✅ 完成                              │   -                    │   -                    │
├─────────────────────────────────────────────────────────────────────────┴──────────────────┤
│ 分布式限流              │   🔄 进行中                            │ 待完成             │   -                    │
│ WebSocket 压缩            │   📋 训划                            │   待实现          │   -                    │
│ HSTS 安全头              │   📋 计划                            │   待实现          │   -                    │
│ TLS 配置                │   📋 计划                            │   待实现          │   -                    │
├─────────────────────────────────────────────────────────────────────────┴──────────────────┤
│ 离线消息队列 (Flutter) │   -                    │   ⏳ Phase 3              │
│ 服务端 ACK              │   -                    │   ⏳ Phase 3              │
│ 连接池优化              │   -                    │   ⏳ Phase 3              │
│ 可观察性增强          │   -                    │   ⏳ Phase 3              │
└─────────────────────────────────────────────────────────────────────────┴──────────────────┘

---

## 注意事项

1. **向后兼容性**: 新的 ACK/NACK 协议使用 `requires_ack` 可选字段，旧客户端可以忽略
2. **HSTS Preload**: 一旦加入 preload 刦10，撤销很困难，先用短 max-age 测试
3. **Redis 故障**: 分布式限流器设计为自动降级到本地限流
4. **压缩开销**: 寋用 BestSpeed 级别，仅压缩 >1KB 的消息

5. **Proto 叀更**: 修改 proto 后必须运行 `make proto-gen`

---

## 黚验清单

```bash
# Phase 1 鯯熔器测试
cd backend/gateway && go test ./internal/agent/... -v

# Phase 2 分布式限流测试
cd backend/gateway && go test ./internal/middleware/... -v -run TestDistributedRateLimiter
go test ./internal/middleware/... -v -run TestSlidingWindow

# Phase 2 弋缩测试
curl -I http://localhost:8080/api/v1/health
# 检查 Sec-WebSocket-Extensions: permessage-deflate

# Phase 2 安全头测试
curl -I http://localhost:8080/api/v1/health
# 检查 X-Frame-Options: DENY
# 检查 X-Content-Type-Options: nosniff
```
