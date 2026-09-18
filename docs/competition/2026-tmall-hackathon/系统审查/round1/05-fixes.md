# 05 · Go 网关第一轮审查·修复报告（5 号修复员）

- 工作树：`/Users/brsama/code/GitHub/Sparkle-sysrev/wt5`（冻结基线 90daac8a，未 commit）
- 修复范围：仅 `backend/gateway/`；对应审查报告：[05-gateway.md](05-gateway.md)
- 验证命令：`CGO_ENABLED=0 go vet ./...` 与 `CGO_ENABLED=0 JWT_SECRET=test-secret-0123456789abcdef go test ./...`

---

## 1. 修复清单（P0 + P1）

### GW-P0-1 FileEventHub 并发 map 迭代 + 裸写并发 → 进程级 fatal（P0）

**修复**
- `backend/gateway/internal/service/file_event_hub.go:13-19`：连接表改存 `JSONWriteCloser`（复用 `signal_hub.go` 已有接口，与 SignalHub 的 map 快照模式对齐），`Register/Unregister` 参数随之接口化；`*websocket.Conn` 天然满足。
- `backend/gateway/internal/service/file_event_hub.go:55-76`：`Send` 改为 **RLock 内快照成 slice 再锁外写**，消除锁外迭代共享 map。
- `backend/gateway/internal/handler/file_events.go:54-85`：升级后即包 `wsSafeWriter`（writeWait=10s 或配置值），hub 注册/注销 writer，限流 Close 帧与鉴权/连接上限 Close 帧全部经 writer 写 → hub.Send 与 handler 本地写不再对同一 conn 并发写。
- `backend/gateway/cmd/server/setup.go:389-397`：fileEventSubscriber goroutine 外层包 `recover`（panic 记日志，不再打挂进程）。

**测试（internal/service/file_event_hub_test.go、internal/handler/file_events_test.go）**
| 测试 | 红（修复前） | 绿（修复后） |
|---|---|---|
| `TestFileEventHub_SendWhileRegisterUnregister_ConcurrentStress`（64 条真 conn，4 goroutine Register/Unregister churn × 1 subscriber Send，1.5s 压测） | 进程级崩溃：`fatal error: concurrent map iteration and map write`，栈指向 `file_event_hub.go:56`（锁外 `for conn := range userConns`） | ok（2.4s） |
| `TestFileEventHandler_HubSendOverlapsRateLimitClose`（真 /ws/files 握手，hub.Send 风暴与限流 Close 帧重叠） | 临时回退 file_events.go 两处（writer→裸 conn）后复现：`panic: concurrent write to websocket connection` | ok |

注：`-race` 在本机被 Xcode license 阻塞（cgo 编译失败，见 §4），并发正确性由上述并发压测 + 静态论证：map 读写全部收敛到 `h.mu` 临界区内（快照在 RLock 内完成）；单 conn 写全部经 wsSafeWriter 的 channel 信号量串行。建议 CI 补跑 `-race`。

### GW-P1-1 StreamChat 重连重试分支 `defer retryCancel()` 使返回流必死（P1）

**修复**
- `backend/gateway/internal/agent/client.go:366-385`：retryCtx 父级从 `context.Background()` 改为调用方 `ctx`（保留 WS 断连传播）；去掉 `defer retryCancel()`——cancel 作用域收窄为"本次失败尝试"：失败即 cancel，成功则把 cancel 移交给 `cancelOnDoneStream`（client.go:394-412，Recv 返回 EOF/错误时一次性释放计时器）。go vet lostcancel 不接受条件 cancel 或弃用 `_`，该包装器是同时满足"流不被提前杀 + 不泄漏计时器 + vet 通过"的实现。

**测试（internal/agent/client_stream_retry_test.go，注入 fake API + 进程内 gRPC server 让 reconnect 短路）**
| 测试 | 红 | 绿 |
|---|---|---|
| `TestStreamChatRetryStreamAliveAfterReturn` | `returned stream context must still be alive after StreamChat returns`（收到 `context canceled`） | PASS |
| `TestStreamChatRetryHonorsCallerCancel`（先断言返回时流存活再 cancel 调用方，避免 defer-cancel 使断言空洞化） | `stream must be alive right after StreamChat returns, before any cancel` | PASS |

### GW-P1-2 客户端断开不取消上游流，孤儿流占满 streamSem（P1）

**修复**
- `backend/gateway/internal/handler/chat_orchestrator_connections.go:13-46`：`readWSMessages` 增加回调参数，读泵在 ReadMessage 出错瞬间（错误结果入 channel 之前）同步通知调用方——主循环此时通常阻塞在 `stream.Recv()` 上，回调是唯一可靠的断连信号通道。
- `backend/gateway/internal/handler/chat_orchestrator.go:344-351`：hijack 后 `c.Request.Context()` 不再随客户端断开取消，故派生 `streamCtx, cancelStreams := context.WithCancel(...)`，读泵错误回调触发 `cancelStreams()`，`defer cancelStreams()` 兜底。
- `chat_orchestrator.go` 消息循环内 9 处 `c.Request.Context()`（397/433/439/442/479/493/541/551/578，含 legacy、envelope、protobuf 三协议路径与 i18n）全部替换为 `streamCtx` → `handleChatMessage` 内 300s WithTimeout 的父链可被断连取消 → gRPC Recv 即时中断，streamSem 槽位随 handler 返回释放。

**测试（internal/handler/chat_orchestrator_disconnect_test.go）**
`TestChatOrchestrator_ClientDisconnectReleasesStreamSlot`：进程内 gRPC mock agent（发 1 个 delta 后挂起直至 ctx 取消）+ `StreamMaxConcurrent=1` + 真 WS 客户端。客户端先排空 ack+delta（保证断开时无 pending 写，避免写失败路径掩盖缺陷）再裸断开。
| 红（临时把 per-message ctx 回退为 `c.Request.Context()`） | 绿 |
|---|---|
| `stream slot must be released after the client disconnects`——5s 超时 FAIL（孤儿流持续占位，直到 300s 流超时） | 0.5s 内槽位释放，PASS（-count=5 稳定） |

### GW-P1-3 匿名遥测 ingest 白名单缺失（P1，基线红测试）

**修复**
- `backend/gateway/internal/handler/proxy_routes.go:733-747`：`POST /events`、`POST /events/batch` 移出鉴权（匿名批量上报直达后端），`GET /summary` 保留在 `authedTelemetry` 子组（挂 authMiddleware）——按既有测试契约实现白名单。

**测试**：既有 `TestProxyRoutesHandler_ClientTelemetryAuthBoundary`（proxy_routes_test.go:273）
- 红（基线即红）：`expected anonymous telemetry ingest to bypass auth middleware, got 1 calls`
- 绿：PASS；`go test ./internal/handler/ -run TestProxyRoutesHandler` 全绿（未破坏其余代理路由契约）。

### GW-P1-4 admin 投影 rebuild 用请求上下文，handler 返回即自取消（P1）

**修复**
- `backend/gateway/cmd/server/setup.go:123-141`：新增 `startDetachedRebuild(work)`——`context.Background()` + `projectionRebuildTimeout=10min`，goroutine 内 `defer cancel()`。
- setup.go rebuild（:716-731）与 rebuild/snapshot（:733-748）两个分支的 `go func(ctx)(c.Request.Context())` 均改为 `startDetachedRebuild(...)`，保留原日志与逻辑。

**测试（cmd/server/setup_detached_rebuild_test.go）**
| 红（临时文件复现旧模式：gin + httptest 中后台 goroutine 吃请求 ctx） | 绿：`TestStartDetachedRebuildContextSurvivesCallerReturn` |
|---|---|
| `RED (pre-fix defect reproduced): background rebuild ctx = context canceled` | 三断言：work 运行中 ctx 存活（handler 帧已返回）、deadline≈10min、work 返回后 ctx 被 cancel 释放。PASS |

---

## 2. P2 修复

| ID | 修复 | 测试/证据 |
|---|---|---|
| **GW-P2-1** NetworkResilience 注册顺序失效 | `cmd/server/setup.go:597-604`：`api.Use(NetworkResilienceMiddleware)` 移到 `RegisterProxyRoutes` **之前**（gin 在路由注册时快照 handler 链）；:848-851 在 `r.NoRoute` 注册前保留一处 engine 级 Use，兜住 NoRoute 回退代理的既有覆盖；删除原 :621-623 处对显式路由无效的 `r.Use`。swagger（dev）不再挂该中间件（无影响）。注意：api 组本就有 30s TimeoutMiddleware，中间件自身 30s ctx 超时不改变有效预算；WS 路由不在 api 组，不受影响 | `TestNetworkResilienceMiddleware_RegistrationOrderMatters`（middleware 包）：先注册的路由无 Keep-Alive 头、后注册的有——固化 gin 快照语义，防回归 |
| **GW-P2-2** STT 空 Origin 无条件放行 | `internal/handler/stt_handler.go:26-46`：NewSTTHandler 改用 `WebSocketFactory.checkOrigin`（生产拒绝空 Origin、dev 放行、按 AllowedOrigins 校验），保留原 HandshakeTimeout/缓冲区配置，不启用压缩 | `TestSTTUpgrader_OriginPolicyMatchesFactory`（stt_origin_test.go，4 子测试）。红：回退后 `production_rejects_empty_origin` FAIL（"empty Origin must be rejected in production"）；绿：4/4 PASS |
| **GW-P2-4** 日配额 Redis 故障静默 fail-open | 部分完成：`internal/metrics/ws_metrics.go:92-99` 新增 `sparkle_quota_daily_usage_load_errors_total`；`chat_orchestrator_chatflow.go:584-591` 加载失败时打点。fail-close/降级缓存涉及可用性与产品决策，未擅改（见剩余清单） | 编译期接线 + 指标语义注释；计数路径即审查指出的吞错分支 |

---

## 3. 剩余清单（未修，含建议）

| ID | 状态 | 说明与建议 |
|---|---|---|
| GW-P2-3 | 未修 | 生产两个 WS 入口拒绝空 Origin → 原生 Flutter（不发 Origin）经域名接入可能被拒。需移动端联调确认；如确认，方案是原生通道免 Origin（已过 WsAuth）或强制 ticket 子协议替代 Origin 校验——涉生产鉴权面，需产品/移动端共同决定，不宜网关单方放开 |
| GW-P2-4 | 半修 | 指标已加；是否改 fail-close（Redis 故障拒新流）或本地降级缓存，属可用性取舍，建议结合 Prometheus 告警运行一段时间后再定 |
| GW-P3-1～P3-7 | 未修 | 限流键可污染、内网白名单缺省跳过告警、gRPC 4xx 透传契约注释、dedup 无超时、重连限流非原子、tokens gauge 语义、outbox 幂等注释——均为 P3，成本/收益不适用本轮 |

## 4. 新发现（本轮修复过程中发现，未扩修）

1. **`ChatOrchestrator.saveMessage` 无 chatHistory nil 防护**（chat_orchestrator_feedback.go:71）：`h.chatHistory.SaveMessage` 直接解引用。生产接线恒传非空（setup.go:265-280），仅测试以 nil 依赖构造时会 panic；建议补 nil 判断或注释"测试须提供 chatHistory"。
2. **agent client 其余 RPC 重试分支同样以 `context.Background()` 为父**（client.go SubmitResponseFeedback/SubmitPlanReview/RetrieveMemory/GetUserProfile 等）：与 GW-P1-1 同款写法，但这些是一元调用、响应在返回前完全落地，无功能缺陷；仅是取消传播一致性问题（调用方取消后重试仍会完成一次后台调用），如需统一可后续批量收窄。
3. **`cancelOnDoneStream` 仅覆盖 Recv 终止路径**：若调用方既不 Recv 到 EOF 也不丢弃流（理论上的编程错误），计时器仍由 retryTimeout 兜底；不会泄漏超过 `GRPCTimeoutSeconds`（默认 120s）。
4. **已知债务 `TestChatOrchestrator_QuotaIntegration` 的失败根因**：并非"沙箱网络阻塞"——测试内 `ENVIRONMENT=prod` + 无 Origin 头拨号，被生产 checkOrigin 以 403 拒绝（GW-P2-3 同根因），`assert.NoError` 非致命后 nil conn panic（quota_integration_test.go:76-81）。与本次改动无关（基线同红），但测试补一个允许的 Origin 头即可修，建议债务台账更新根因描述。

## 5. 验证记录

```
$ CGO_ENABLED=0 go vet ./...
（零输出，通过）

$ CGO_ENABLED=0 JWT_SECRET=test-secret-0123456789abcdef go test ./... -count=1
ok   github.com/sparkle/gateway/cmd/server
ok   github.com/sparkle/gateway/internal/agent
ok   github.com/sparkle/gateway/internal/config        （JWT_SECRET 已设，基线环境红消除）
ok   github.com/sparkle/gateway/internal/cqrs
ok   github.com/sparkle/gateway/internal/cqrs/event
ok   github.com/sparkle/gateway/internal/db
FAIL github.com/sparkle/gateway/internal/handler      ← 仅剩已知债务 1 项：
  --- FAIL: TestChatOrchestrator_QuotaIntegration        （见 §4.4，基线同红，非本次引入）
ok   github.com/sparkle/gateway/internal/logsafe
ok   github.com/sparkle/gateway/internal/middleware
ok   github.com/sparkle/gateway/internal/service
```

与基线差异：handler 包从 2 红（telemetry 契约红 + quota 已知红）降为 1 红（仅 quota 已知红）；config 包设 JWT_SECRET 后转绿；新增 7 个回归测试（6 文件）全部绿。`go test -race` 因本机 Xcode license 阻塞（cgo 不可用，项目铁律本就 CGO_ENABLED=0），GW-P0-1 并发正确性以并发压测 + 静态论证代替（§1），建议 CI 补跑 -race。

---

*修复方法：全部按红-绿流程（先证红后修）；涉及 git 的操作仅在工作树内 add/diff/reset，未 commit。*
