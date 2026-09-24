# GATEWAY-LIFECYCLE-AUDIT — 网关生命周期与韧性审查报告（wt275）

> 2026-09-22。范围：`backend/gateway/`（cmd/server + internal/{handler,middleware,agent}）+ k8s/compose 部署面。
> 方法：全量源读 + 部署清单对照；修复仅限实锤（高置信、可定向验证）；验证 `CGO_ENABLED=0 go build/vet` + 定向 `go test`。

## 一、五面审计结论

| 面 | 结论 | 关键证据 |
|---|---|---|
| a) 优雅停机 | **主体健壮（4 阶段链完整），但 /ws/stt 与 /ws/files 两个 WS 入口在停机链中无席位**——连接被进程退出直接杀死，客户端收 1006 而非 close frame（已修） | `cmd/server/main.go:127-180`（SIGTERM→bgCancel→限流器停→drain→Shutdown→收尾）；`defer dbh.pool.Close()/rdb.Close()/agentClient.Close()` `main.go:56-79`；缺陷证据：`internal/handler/stt_handler.go`、`internal/handler/file_events.go` 原无任何 drain/StartDraining，`main.go` 原 drain 只覆盖 wsProxy+chat registry |
| b) WS 泵 panic recovery | **chat/community proxy 路径有恢复；STT 三条泵 goroutine 无恢复（已修）；proxy 清理 goroutine 的 recover 位置错误，一次 panic 即永久哑火（已修）** | `websocket_proxy.go:365-378`（recoverProxyGoroutine ✓）；chat 主循环跑在 gin handler goroutine 内由 `gin.Default()` Recovery 兜底（`setup.go:471`）；STT 泵原无 recover；`websocket_proxy.go:826-846` 原顶层 defer recover |
| c) 限流一致性 | **HTTP /api/v1 面一致且键逃逸面已封死（GW-P3-1/6 在位）；但全部 WS 入口（/ws/chat、/ws/files、/ws/stt、community ws）没有任何连接级限流——现成的 `WebSocketRateLimitMiddleware` 是死代码** | `middleware/rate_limit.go:400-426`（未被任何路由引用，全库 grep 仅定义处）；`setup.go:498-507` WS 路由只挂 WsAuthMiddleware；`setup.go:567-570` api 组限流+超时对 WS 天然不生效（注册在其之外） |
| d) 健康探针 | **代码面 `/readyz` 已探真实依赖（DB Ping/Redis Ping/gRPC 健康检查器），但 k8s 清单 readiness 与 liveness 都指向静态 `/api/v1/health`——依赖感知探针在真实部署中从未生效** | `internal/handler/health.go:99-144`（readiness 三依赖）vs `k8s/base/gateway.yaml:35-46`（两个探针均 `/api/v1/health`）；`setup.go:529-535` 该路由是静态 200 |
| e) context 传播 | **chat 流链路传播完整（读泵错误→cancelStreams→gRPC 流取消，min 300s 兜底，semaphore 准入，终端持久化走 detached ctx）；缺口：agent client 全部 unary 重试改挂 `context.Background()`，调用方取消不传导（有界 30s 孤儿）；SSE 类 handler 会让 Shutdown 等满超时** | `chat_orchestrator.go:363-377`（GW-P1-2）；`chat_orchestrator_chatflow.go:303-329`（≥300s 超时+streamSem）；`chat_orchestrator_chatflow.go:122-124`（R2-GW-1 detachedPersistCtx）；`agent/client.go:432/451/469/...`（约 15 处 Background 重试）；`middleware/timeout.go:16-41` |

## 二、实锤缺陷清单

### 已修复（本次代码改动，5 文件 +226/−15）

| # | 缺陷 | 风险 | 修法 | 验证 |
|---|---|---|---|---|
| D1 | **/ws/stt、/ws/files 停机不排空**：两入口升级后的 socket 被 hijack，`http.Server.Shutdown` 不等待也不关闭它们；每次滚动重启，在线 STT 转写/文件推送客户端收到异常断开（1006），无 close frame、无排空等待 | 每次部署全量 STT/files 长连接体验损毁；客户端盲目重连放大重启风暴 | 新增共享 `wsConnDrainGroup`（`internal/handler/ws_registry.go`）：draining 时拒绝升级（503）、跟踪 live conn、`DrainAll` 发 `CloseGoingAway(1001)` frame 后关闭并等 handler 收尾；STTHandler/FileEventHandler 各自接入，`cmd/server/main.go` 把两者以 `endpointDrainer` 追加进既有共享 deadline 的 `drainWebSocketPhases`（variadic，原 R2-GW-6 单一绝对 deadline 语义不变） | 新增 `internal/handler/ws_shutdown_drain_test.go` 4 例（真实 WS 握手验证客户端收到 1001 frame、draining 拒新、空组即时返回）；drain 排空不访问上游（tracking 先于 Python dial） |
| D2 | **STT 三条泵 goroutine 无 panic recovery**：client→python、python→client、ping ticker 任一 panic = 整个网关进程崩溃（Go 语义：detached goroutine panic 不可恢复）；同库 community proxy 泵已有 `recoverProxyGoroutine` 先例，STT 是漏网点 | 单连接级异常升级为全站宕机 | `stt_handler.go` 增加 `recoverSTTPump`（panic→日志+errChan+closeDone），三个 goroutine 全挂 | build/vet + 既有 STT 测试套件全绿 |
| D3 | **proxy 重连清理 goroutine recover 位置错误**：`websocket_proxy.go` 原 `startReconnectTrackerCleanup` 把 recover 放在 goroutine 顶层 defer——一次 panic 后 goroutine 静默退出且不再重启，`reconnectTrackers` 从此无限增长（内存泄漏到重启），且与“恢复”的表象相反 | 慢性内存泄漏 + 清理机制静默失效 | recover 下沉到 per-tick 闭包：单次 panic 只跳过本轮清理，循环存活 | build/vet；`ProxyDrainAll` 清空 trackers 语义不变 |

### 留报告不动代码（风险大/面广/属部署语义决策）

| # | 发现 | 为什么不修 |
|---|---|---|
| D4 | **k8s readiness/liveness 均指向静态 `/api/v1/health`**（`k8s/base/gateway.yaml:37,43`），依赖感知的 `/readyz`（`health.go:99`）在真实部署从不被调用——DB/Redis/引擎全挂时 K8s 依旧认为 gateway ready | 改探针目标=改变滚动发布/故障摘除语义：若 readiness 切 `/readyz`，Redis 抖动即摘除网关，非 AI 路由连带不可用。需部署方拍板（建议：readiness→`/ready` 且对 gRPC agent 保持 degraded 容忍，liveness 维持静态） |
| D5 | **readiness 意图/行为背离**：`health.go:113-118` 注释明言“Agent unhealthy 不是 readiness 阻断（degraded）”，但代码对 message≠"agent client not configured" 的任何 unhealthy 都置 `allHealthy=false`→503 not_ready。引擎熔断打开时网关被摘，而网关其余功能健康 | 与 D4 是同一语义决策的两半；且 `isHealthy()` helper（health.go:325）已死代码。建议合并为一个 readiness 语义 PR |
| D6 | **WS 入口零连接限流**：`WebSocketRateLimitMiddleware`（rate_limit.go:400）及 `UserBasedRateLimit`/`AdaptiveRateLimitMiddleware` 全是死代码；/ws/chat 每次连接尝试都会触发 Redis JWT 校验，未认证 IP 可无限打 | 现成中间件默认 5/min/IP+burst10，直接接线会在 NAT 共享出口（宿舍/校园网）造成误杀，是产品阈值决策。建议按 ticket 模式（`/api/v1/ws/ticket` 已有专用限流）把 WS 升级收敛到短时效 ticket 后置 |
| D7 | **agent client 约 15 处 unary 重试挂 `context.Background()`**（client.go:432 起成片）：调用方取消/超时后重试仍孤跑到 30s | 有界（30s/次）且分散在 15 个包装函数；统一改造收益低、diff 大。建议引入带 ctx 透传的统一 retry helper 时一并清理 |
| D8 | **SSE/长传输 handler 使 Shutdown 等满超时**：`srv.Shutdown` 不取消在飞请求 context，`/api/v1/galaxy/events`、`/api/v1/chat/stream` 等（timeout.go:63-96 豁免清单）会拖满 15s shutdown 窗口 | 属 http.Server 语义；客户端断开时 SSE handler 是否监听 `c.Request.Context()` 决定实际时长，需按 handler 逐个核对，非本卡定向可修 |
| D9（备忘） | `WebSocketProxy.Close()`（含 stopCh 关闭）在 main.go 从未被调用——shutdown 只走 `ProxyDrainAll`；tracker 清理 goroutine 随进程退出消亡，无实际泄漏 | 行为无害；若未来 proxy 变成可热替换组件才需要修 |

## 三、验证记录

```
CGO_ENABLED=0 go build ./...   → exit 0（worktree 缺 gitignored gen/，已用 host buf 重新生成 backend/gateway gen）
CGO_ENABLED=0 go vet ./...     → exit 0
golangci-lint run internal/handler/ cmd/server/ → 仅既有告警（main.go:100 errcheck 等均为改动前存在），新增/改动行零告警
go test ./cmd/server/...                       → ok（含 R2-GW-6 drain deadline 回归）
go test ./internal/handler/ -run 'TestDrainWebSocketPhases|...|Registry|STT|FileEvent|Proxy|Reconnect|Health' → ok
新增 ws_shutdown_drain_test.go 4 例 → PASS（真实 WS 端到端：drain 后客户端收到 CloseGoingAway(1001)）
```

改动文件（worktree 内，本地 commit 不 push）：
- `backend/gateway/cmd/server/main.go`（drain 接线 + endpointDrainer 接口）
- `backend/gateway/internal/handler/ws_registry.go`（+wsConnDrainGroup）
- `backend/gateway/internal/handler/stt_handler.go`（drain + 泵 recovery）
- `backend/gateway/internal/handler/file_events.go`（drain）
- `backend/gateway/internal/handler/websocket_proxy.go`（per-tick recover）
- `backend/gateway/internal/handler/ws_shutdown_drain_test.go`（新增回归测试）

## 四、交接建议

1. **D4/D5 需主会话或部署 owner 拍板**：readiness 切 `/ready` 的故障摘除语义（建议同时修 health.go:113 的意图/代码背离与死代码 `isHealthy`）。
2. **D6 建议与 mobile 端对齐**：若 WS 升级收敛到 ticket 模式，Flutter 需先 POST /ws/ticket 再带 ticket 升级（ws_auth.go 已支持 Sec-WebSocket-Protocol ticket），限流即可钉在 ticket 签发口。
3. 滚动发布排空窗口实测建议：部署后观察 `sparkle_ws_active_connections` 归零时长与 1006 客户端告警是否消失（本卡 D1 的效果指标）。
4. `minReconnectGap`（agent/client.go:49）从未被赋值，恒走 2s 默认——如需调参先补 config 通道。
