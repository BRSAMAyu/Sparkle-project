# 05 · Go 网关全量审查（全系统审查·第一轮）

- 审查员：5 号｜切片：`backend/gateway/` 全量（cmd / server / internal / locales / sqlc.yaml）
- 基线：main@90daac8a（冻结），worktree `/Users/brsama/code/GitHub/Sparkle-sysrev/wt5`
- 已知债务未重报：k8s 双探针 /health 排空、lint 185 项基线（P3-0）、统计/排行榜/card_protocol、P3b、CX-03、T14、RT-08、T22、T32、resolve_tier、test_signal_spine、EB-04、T16；AX admin 路由正则、/metrics 暴露、BI placeholder、serial_merger 均按已修复处理。

---

## 1. 总评

网关整体工程质量高于平均水平：WS 写路径有统一的 `wsSafeWriter` 串行化、连接注册表双存储（registry+signalHub）单锁不变量、鉴权中间件 fail-closed 可配、限流 Redis→本地双层降级、优雅关停分四阶段、生产配置硬化（强制 REDIS_FAIL_CLOSED、禁 query token、密钥校验）都做得扎实，路由-鉴权对照**未发现漏挂中间件的正式路由**。但本轮发现 **1 个 P0 进程级崩溃缺陷**（/ws/files 事件推送的 map 并发读写 + WS 并发写 panic，发生在无 recover 的订阅者 goroutine，足以打挂整个网关）和 **4 个 P1**（gRPC StreamChat 重连重试分支的 context 自我取消、客户端断开不取消上游流并占满流信号量、匿名遥测白名单缺失导致基线测试红、admin 投影 rebuild 用请求上下文导致必然自取消）。这些问题集中在"异常路径/生命周期路径"，主路径行为正确，修都不难。

---

## 2. 发现表

| ID | 严重度 | file:line | 触发场景 | 证据摘录 | 建议修复 |
|---|---|---|---|---|---|
| GW-P0-1 | **P0** | `internal/service/file_event_hub.go:51-61`（配合 `internal/handler/file_events.go:74-75, 101-104`） | 用户持有 /ws/files 连接期间，Redis `file_status` 订阅者 goroutine 调 `hub.Send`；同一时刻该用户的文件 WS 断开/重连（handler goroutine 走 `Unregister`/`Register` 改同一 map）。`Send` 只在取 map 引用时持 RLock，**迭代在锁外**；并发删除即触发 Go runtime `fatal: concurrent map iteration and map write`——这是不可 recover 的进程崩溃。另外 `Send` 用裸 `conn.WriteJSON` 写数据，而 handler 在限流路径 `file_events.go:102` 用裸 `conn.WriteMessage` 发 Close 帧 → 同一 conn 双 goroutine 并发写，gorilla panic（订阅者 goroutine 无 recover，`cmd/server/setup.go:372-376` 启动时未包 recover，panic 即 crash） | `h.mu.RLock(); userConns := h.connections[userID]; h.mu.RUnlock()`<br>`for conn := range userConns {`（锁外迭代共享 map）<br>`if err := conn.WriteJSON(payload); err != nil { h.Unregister(...)` | Send 在 RLock 内快照成 slice 再锁外写；写改走 `wsSafeWriter`；handler 的 Close 帧写也统一走 writer；订阅者 goroutine 包 recover（见 §3 diff） |
| GW-P1-1 | **P1** | `internal/agent/client.go:367-377` | `StreamChat` 初次调用失败且 `shouldReconnect(err)`（Unavailable/DeadlineExceeded）、reconnect 成功后走重试分支：`retryCtx` 以 `context.Background()` 为父（脱离 WS 生命周期，客户端断开不再传播），且 `defer retryCancel()` 在 **StreamChat 返回时立即执行**——返回的 server-stream 的 ctx 当场被 cancel，下一次 `Recv()` 必然 `Canceled`。即：重连重试分支生成的流 100% 立即死亡，用户看到 "Stream interrupted"； resilience 路径完全失效 | `retryCtx, retryCancel := context.WithTimeout(context.Background(), retryTimeout)`<br>`defer retryCancel()`<br>`stream, retryErr := c.currentAPI().StreamChat(retryCtx, req)`<br>`return stream, retryErr`（defer 在 return 时 cancel 流） | 父 ctx 改为调用方 `ctx`（保留取消传播），去掉 `defer cancel()`（流随父 ctx/300s 超时结束，见 §3 diff） |
| GW-P1-2 | **P1** | `internal/handler/chat_orchestrator_chatflow.go:686-790`（配合 `chat_orchestrator.go:343-361`、`chat_orchestrator_connections.go:13-34`） | WS 消息循环是串行的：`handleChatMessage` 同步消费整条 gRPC 流（最长 300s）。期间没人读 `readResults`（无缓冲），断线后读泵 goroutine 阻塞在 channel 发送；`stream.Recv()` 循环里**没有任何对 readResults/connDone 的 select**，唯一断点靠"写死连接失败"。升级后连接已被 hijack，`c.Request.Context()` 在客户端断开时**不会**被 net/http cancel → 客户端断开后上游流继续跑满 300s 或流自然结束；每条孤儿流占住一个 `streamSem`（默认 200）槽位。移动端弱网下成批断线 → 信号量耗尽 → 新消息全部 "Server busy" | `for { _, streamSpan := tracer.Start(ctx, "stream.receive"); resp, err := stream.Recv(); ... if err := r.SendChatResponse(resp); err != nil { return false } }`（无 connDone 分支） | 派生 `streamCtx, cancel := context.WithCancel(...)`；起 watcher goroutine：读到 readResults 出错即 `cancel()`；Recv 依赖 gRPC ctx 取消即中断（见 §3 diff） |
| GW-P1-3 | **P1** | `internal/handler/proxy_routes.go:734-742` vs `internal/handler/proxy_routes_test.go:307-326` | `TestProxyRoutesHandler_ClientTelemetryAuthBoundary`（初始提交 1722e6dc 即存在）断言 `POST /api/v1/client-telemetry/events/batch` **匿名可直达（绕过 auth）**，但实现把整个 `/client-telemetry` 组挂在 `authMiddleware` 下、无任何匿名白名单 → 测试确定性失败，**冻结基线 `go test ./internal/handler` 是红的**；同时未登录移动端的遥测批量上报被 401 丢弃（既定功能未实现）。二者必须有一个是错的 | 测试：`expected anonymous telemetry ingest to bypass auth middleware, got 1 calls`<br>实现：`clientTelemetry := api.Group("/client-telemetry"); clientTelemetry.Use(authMiddleware)` | 按测试意图为 `/events`、`/events/batch` 开匿名 ingest 白名单（summary 保持鉴权），或改测试断言——总之基线必须回绿（见 §3 diff） |
| GW-P1-4 | **P1** | `cmd/server/setup.go:678-691, 715-728` | `POST /admin/cqrs/projections/:name/rebuild`（及 `/rebuild/snapshot`）在后台 goroutine 里用 `c.Request.Context()` 跑长任务。net/http 语义：**ServeHTTP 返回即 cancel 请求 ctx**——handler 写完 200 "rebuild_started" 返回的瞬间 rebuild 被取消，`builder` 后续 DB 查询全部 `context canceled`，投影落 StatusError。管理端 rebuild 功能实际不可用 | `go func(ctx context.Context) { progress, err := cqrs.projectionBuilder.RebuildFromEventStore(ctx, name, aggregateType, opts) ... }(c.Request.Context())`<br>`c.JSON(http.StatusOK, gin.H{"status": "rebuild_started", ...})` | 改用 `context.WithoutCancel(c.Request.Context())`（Go 1.21+，本仓 Go 1.24）再传入 goroutine（见 §3 diff） |
| GW-P2-1 | P2 | `cmd/server/setup.go:588-590` + `internal/middleware/network_resilience.go` | Gin 在**路由注册时**快照 handler 链（`combineHandlers`）。`NetworkResilienceMiddleware` 在所有 /api 代理路由、internal、admin 组注册**之后**才 `r.Use(...)`，只有其后注册的 `/swagger`（dev）与 NoRoute 拿到它——FV-24 注释声称服务"upstream proxy routes"，实际对全部显式代理路由无效。且 `RetryableUpstreamProxy`（network_resilience.go:174-248）全仓**零调用**，其设置的 `client_disconnected`/`state_save_required` 两个 gin key 无任何消费者：断连状态保存机制整体是死代码 | `proxyRoutesHandler.RegisterProxyRoutes(api, authMiddleware)  // line 571`<br>`...`<br>`// FV-24: Network resilience middleware for upstream proxy routes`<br>`r.Use(middleware.NetworkResilienceMiddleware(resilienceCfg))  // line 590` | 移到路由注册前 `r.Use`；或删除该中间件与 `RetryableUpstreamProxy` 并在台账登记，避免"以为有重试/断连保护"的错觉 |
| GW-P2-2 | P2 | `internal/handler/stt_handler.go:29-34` | STT upgrader 对空 Origin **无条件放行**，与 `websocket_proxy.go:84-103`（仅 localhost 放行）、`websocket_factory.go:42-44`（生产拒绝）策略不一致，同一批 /ws 路由三套 Origin 政策，STT 成为最薄弱口（WS 鉴权仍在，但跨站面扩大） | `if origin == "" { return true }` | 统一走 `WebSocketFactory.checkOrigin`；至少生产环境拒绝空 Origin |
| GW-P2-3 | P2 | `internal/handler/websocket_proxy.go:84-103`、`websocket_factory.go:37-51` | 生产环境两个 WS 入口都要求非空 Origin。原生 Flutter（dart:io WebSocket）默认**不发送 Origin** 头，经域名接入时 `origin==""` 且 Host 非 localhost → 连接被拒。手机端 WS（聊天/社区）在生产不可用的风险，需实际验证或为原生客户端提供免 Origin 的显式通道（如 ticket 子协议已具备） | `if origin == "" { host := r.Header.Get("Host"); if host != "" && (host == "localhost:8080" || host == "127.0.0.1:8080") { return true } return false }`<br>`factory: return !f.config.IsProduction()` | 与移动端联调确认；原生客户端允许空 Origin（已过 WsAuth），或强制 ticket 子协议替代 Origin 校验 |
| GW-P2-4 | P2 | `internal/handler/chat_orchestrator_chatflow.go:578-591, 739-761` | 日配额执行依赖 `GetDailyUsage`：Redis 故障时 err 被吞、`dailyUsageStart=0`，mid-stream 段扣费继续基于 0 → 配额静默 fail-open，故障窗口内用户可无限超额（计费完整性缺陷；非安全问题） | `if usage, err := h.quota.GetDailyUsage(ctx, userID); err == nil { dailyUsageStart = usage } else { log.Printf("Failed to load daily usage: %v", err) }` | Redis 故障时选择 fail-closed（拒绝或降级为拒绝大请求）至少打点告警指标，别只写日志 |
| GW-P3-1 | P3 | `internal/middleware/rate_limit.go:509-524` + `cmd/server/setup.go:862-886` | 限流键含**具体 URL path**（wildcard 路由与 NoRoute 均回退具体 path）：匿名者可用 `/api/v1/auth/login` 前缀 + 随意后缀（`shouldProxyNoRoutePath` 是前缀匹配）制造任意桶。本地 visitors 上限 10000 有淘汰、Redis 有 PEXPIRE，有界但属廉价污染面 | `if strings.Contains(routePath, "*") { return c.Request.URL.Path }` | wildcard/NoRoute 场景改用"路由模板 + 截断后的 path 段数"或仅模板 |
| GW-P3-2 | P3 | `internal/middleware/internal_ip_whitelist.go:18` | 生产环境 `INTERNAL_IP_WHITELIST` 未配置时 IP 白名单层直接跳过（内部 API 仅剩静态 key 一层）。key 为必配（config 硬校验），但双层防御退化为单层 | `if cfg.IsDevelopment() \|\| len(allowedNets) == 0 { c.Next(); return }` | 生产未配置白名单时启动告警（或 fatal） |
| GW-P3-3 | P3 | `internal/handler/chat_orchestrator_chatflow.go:966-973` | gRPC `InvalidArgument/Unauthenticated/...` 等码把引擎侧 `st.Message()` 原样透传给客户端（200 字符截断）；`Internal/DataLoss/unknown` 已正确掩蔽为通用文案。4xx 类透传基本合理，但依赖引擎侧不在 message 里放内部细节 | `msg := st.Message(); if len(msg) > 200 { msg = msg[:200] + "..." }` | 维持，加注释明确"引擎 message 视为可对外"的契约 |
| GW-P3-4 | P3 | `internal/handler/websocket_proxy.go:413-427` | 消息去重 `dedupService.CheckAndMark(context.Background(), ...)` 不带超时/取消：Redis 抖动时该用户整条转发管道停摆（无泄漏，仅可用性） | `isDup, err := p.dedupService.CheckAndMark(context.Background(), userID, dedupKey)` | 用 `context.WithTimeout`（如 200ms），超时放行 |
| GW-P3-5 | P3 | `internal/handler/websocket_proxy.go:188-198` | 重连限流 `checkReconnectAllowed` 与 `recordReconnectAttempt` 两次独立加锁，非原子：并发重连可少量超限（有界，无危害） | 两函数各自 `p.mu.Lock()` | 合并为单次 `checkAndRecord` |
| GW-P3-6 | P3 | `internal/middleware/distributed_rate_limiter.go:226` | `rateLimiterTokensCurrent` Gauge 每请求被任意 key 的 remaining 覆盖，指标无语义 | `rateLimiterTokensCurrent.Set(remaining)` | 改为 Histogram/Counter 或删除 |
| GW-P3-7 | P3 | `internal/cqrs/outbox/publisher.go:135-153` | Outbox 发布与 MarkPublished 非事务（at-least-once，崩溃在 publish 后 mark 前会重发）。消费端需幂等——projection 侧有 position 语义，属可接受设计，登记备查（`GetUnpublished` 已用 `FOR UPDATE SKIP LOCKED`，多实例安全） | `publishedIDs` 循环后统一 `MarkPublished` | 无需改动；在投影消费端文档标注幂等要求 |

---

## 3. P0/P1 修复建议（diff，未落地）

### GW-P0-1：FileEventHub 崩溃

```diff
--- a/backend/gateway/internal/service/file_event_hub.go
+++ b/backend/gateway/internal/service/file_event_hub.go
@@ func (h *FileEventHub) Send(userID string, payload interface{}) {
 func (h *FileEventHub) Send(userID string, payload interface{}) {
 	h.mu.RLock()
 	userConns := h.connections[userID]
+	// Snapshot under the read lock: iterating the shared map after RUnlock
+	// races Register/Unregister deletes -> fatal concurrent map read/write.
+	conns := make([]*websocket.Conn, 0, len(userConns))
+	for conn := range userConns {
+		conns = append(conns, conn)
+	}
 	h.mu.RUnlock()
 
-	for conn := range userConns {
+	for _, conn := range conns {
 		if err := conn.WriteJSON(payload); err != nil {
 			h.Unregister(userID, conn)
 			_ = conn.Close()
 		}
 	}
 }
```

```diff
--- a/backend/gateway/internal/handler/file_events.go
+++ b/backend/gateway/internal/handler/file_events.go
@@ func (h *FileEventHandler) HandleWebSocket(
 	conn, err := upgrader.Upgrade(c.Writer, c.Request, nil)
 	if err != nil {
 		log.Printf("Failed to upgrade file WS: %v", err)
 		return
 	}
 	defer conn.Close()
+	// Serialize all writes (hub.Send + local close frames) through one writer.
+	writer := newWSSafeWriter(conn, 10*time.Second)
+	defer writer.Close()
@@
 	for {
 		if _, _, err := conn.ReadMessage(); err != nil {
 			break
 		}
 		if !msgLimiter.Allow() {
-			_ = conn.WriteMessage(websocket.CloseMessage, websocket.FormatCloseMessage(websocket.ClosePolicyViolation, "Message rate limit exceeded"))
+			_ = writer.WriteMessage(websocket.CloseMessage, websocket.FormatCloseMessage(websocket.ClosePolicyViolation, "Message rate limit exceeded"))
 			break
 		}
 	}
```
（配套：`hub.Register` 增加写入端（`service.JSONWriteCloser`），`Send` 改推 writer；以及 `cmd/server/setup.go` 中订阅者 goroutine 外层包 `defer func(){ if r:=recover(); ... }()` 兜底。）

### GW-P1-1：StreamChat 重试分支自我取消

```diff
--- a/backend/gateway/internal/agent/client.go
+++ b/backend/gateway/internal/agent/client.go
@@ func (c *Client) StreamChat(
 	// Use fresh context with fresh timeout after reconnection
 	retryTimeout := 120 * time.Second
 	if c.config.GRPCTimeoutSeconds > 0 {
 		retryTimeout = time.Duration(c.config.GRPCTimeoutSeconds) * time.Second
 	}
-	retryCtx, retryCancel := context.WithTimeout(context.Background(), retryTimeout)
-	defer retryCancel()
+	// The stream outlives this function: keep the caller's ctx as parent so
+	// WS disconnect / handler timeout still propagates, and do NOT cancel on
+	// return — a deferred cancel kills the stream before the first Recv.
+	retryCtx, _ := context.WithTimeout(ctx, retryTimeout)
 	retryCtx = c.injectMetadata(retryCtx, req.UserId)
 	stream, retryErr := c.currentAPI().StreamChat(retryCtx, req)
```

### GW-P1-2：客户端断开取消上游流

```diff
--- a/backend/gateway/internal/handler/chat_orchestrator.go
+++ b/backend/gateway/internal/handler/chat_orchestrator.go
@@ func (h *ChatOrchestrator) HandleWebSocket(
 	tracer := otel.Tracer("chat-orchestrator")
 	readResults := readWSMessages(conn, connDone)
+	// Cancel any in-flight upstream gRPC stream as soon as the client goes
+	// away: the request ctx is dead after hijack, so the read pump is the
+	// only disconnect signal. Bounded by connDone for handler exit.
+	streamCtx, cancelStreams := context.WithCancel(c.Request.Context())
+	defer cancelStreams()
+	go func() {
+		select {
+		case <-connDone:
+		case rr, ok := <-readResults:
+			if ok && rr.err != nil {
+				cancelStreams()
+			}
+		}
+	}()
 
 	// Message handling loop: each WebSocket message triggers a new StreamChat call
 	for {
@@
 		// P2: Support Binary Protobuf Protocol
 		if msgType == websocket.BinaryMessage {
-			h.handleProtobufMessage(writer, msg, userID, tracer, c.Request.Context())
+			h.handleProtobufMessage(writer, msg, userID, tracer, streamCtx)
 			continue
 		}
```
（同步把循环内各分支的 `c.Request.Context()` 替换为 `streamCtx`——注意 watcher 与主循环都会消费 `readResults`，watcher 需用带缓冲旁路或仅在 `rr.err != nil` 时 `cancelStreams()` 后继续把该结果送回：最简实现是把 readResults 改为缓冲 1 并让 watcher 只 peek 错误事件，或在 `readWSMessages` 内部出错时直接调用注入的 cancel 回调。核心要求：Recv 循环的 ctx 可被断线事件取消。）

### GW-P1-3：匿名遥测白名单（或修测试，二选一回绿）

```diff
--- a/backend/gateway/internal/handler/proxy_routes.go
+++ b/backend/gateway/internal/handler/proxy_routes.go
@@ func (h *ProxyRoutesHandler) RegisterProxyRoutes(
 	// ==================== Client Telemetry Routes ====================
 	clientTelemetry := api.Group("/client-telemetry")
-	clientTelemetry.Use(authMiddleware)
 	{
+		// Anonymous ingest: pre-login telemetry must be accepted
+		// (contract: TestProxyRoutesHandler_ClientTelemetryAuthBoundary).
+		clientTelemetry.POST("/events", h.proxyWithHeaders)
+		clientTelemetry.POST("/events/batch", h.proxyWithHeaders)
+		authed := clientTelemetry.Group("", authMiddleware)
 		clientTelemetry.POST("/events", h.proxyWithHeaders)
-		clientTelemetry.POST("/events/batch", h.proxyWithHeaders)
-		clientTelemetry.GET("/summary", h.proxyWithHeaders)
+		{
+			authed.GET("/summary", h.proxyWithHeaders)
+		}
 	}
```
（若产品决定遥测必须登录，则反向修改测试断言 `authCalls != 0 → ==1`；关键是一致 + 基线绿。）

### GW-P1-4：admin 投影 rebuild 脱离请求上下文

```diff
--- a/backend/gateway/cmd/server/setup.go
+++ b/backend/gateway/cmd/server/setup.go
@@ admin.POST("/cqrs/projections/:name/rebuild"
-			go func(ctx context.Context) {
+			// net/http cancels the request ctx as soon as this handler
+			// returns; detach so the background rebuild can finish.
+			go func() {
+				ctx := context.WithoutCancel(c.Request.Context())
 				opts := projection.DefaultRebuildOptions()
 				progress, err := cqrs.projectionBuilder.RebuildFromEventStore(ctx, name, aggregateType, opts)
 				if err != nil {
 					log.Printf("Projection rebuild failed: projection=%s err=%v", name, err)
 				} else {
-					log.Printf(
+					log.Printf(
 						"Projection rebuild completed: projection=%s processed=%d duration=%s",
 						name,
 						progress.ProcessedEvents,
 						progress.Duration,
 					)
 				}
-			}(c.Request.Context())
+			}()
```
（`/rebuild/snapshot` 分支 setup.go:715-728 同样处理。）

---

## 4. 验证良好清单

**路由-鉴权核对结论（逐组对照 setup.go 注册表）：全部正式路由均已挂鉴权，未发现漏挂。**
- WS 四入口（`/ws/chat`、`/ws/files`、`/ws/stt`、`/api/v1/community/groups/:id/ws`、`/api/v1/community/ws/connect`）均挂 `WsAuthMiddleware`（setup.go:475-484）；JWT header / 受控 query token / 一次性 ticket（Lua GET+DEL 原子消费，`middleware/ws_auth.go:20-26`）三通道，生产禁 query token（config.go:692-694）。
- `/api/v1` 组：apiRateLimit + MaxBodySize + Timeout 三件套；`/api/v1/auth/apple` 公开但有独立 5rps/15 限流；`/ws/ticket`、chat history、groups、galaxy（`galaxy_handler.go:64-67` 组级 auth）、error_book（组级）、file（组级）、data_consistency（逐条）、`ProxyRoutesHandler` 全部 ~40 个组逐组 `Use(authMiddleware)`，其中 `/api/v1/dlq`、`/api/v1/admin/*path` 追加 `RequireAdmin`（JWT is_admin）——**proxy_routes.go 全文核对无裸奔组**。
- `/internal` 组：常量时间比较的 `X-Internal-API-Key` + IP 白名单 + 独立限流（生产强制配置 key，config.go:695-697）。
- `/admin` 组：`X-Admin-Secret` 常量时间比较 + 独立 10/60rps 限流；chaos 子组再加 ChaosGuard。
- NoRoute 兜底仅代理 auth 白名单前缀（`path.Clean` + 前缀匹配，防 `..`），logout/upgrade-guest 强制鉴权（R5-G01），其余 404；`SetProxyUserContextHeaders` 只从 gin context（由鉴权中间件写入）取值，不信任客户端自带头。
- 鉴权上下文注入完整性：所有 handler 均从 `c.GetString("user_id")`/`c.Get("user_id")` 取身份，抽查 galaxy/file/group_chat/stt/ws 代理一致，无 handler 自行解析 token。

**其他验证良好项：**
- **WS 并发写**：`wsSafeWriter`（channel 信号量 + writeWait 超时）覆盖 chat/files 的写路径；WriteControl 与 WriteMessage 的 gorilla 并发约束使用正确；chat 双核路径未发现裸 conn 写。
- **连接生命周期**：ConnectionRegistry registry+signalHub 单写锁双删不变量、BroadcastToUser alive 复查、DrainAll 覆盖 close 帧+hub 清理+publish goroutine WaitGroup；`readWSMessages` 泵受 connDone 保护无泄漏；ping/pong + 读限 + 256KB 消息上限 + 消息级限流齐备。
- **JWT**：RS256 主 + HS256 迁移回退（算法显式 allowlist）、type=access、exp/nbf/skew、可选 iss/aud；黑名单三层（jti/user/session），生产强制 fail-closed，本地黑名单缓存有界（10k + 淘汰）。
- **限流降级**：Redis 故障 → 本地令牌桶继续限（非完全 fail-open），键 = user_id(或 ip)+method+路由模板，wildcard 用具体 path 防互相挤压（代价见 GW-P3-1）。
- **优雅关停**（main.go:114-171）：信号 → bgCancel（CQRS worker/file subscriber/file GC/outbox relay 全部吃 ctx）→ 停限流器清理 goroutine → WS 停止收新 → HTTP Shutdown 与 WS drain（1/3 超时预算）并行 → 等待收尾；顺序正确。
- **生产配置硬化**（config.go:682-713）：ADMIN_SECRET/INTERNAL_API_KEY/MinIO 凭据/RBAC/TLS 强校验，`REDIS_FAIL_CLOSED` 生产强制 true。
- **logsafe**：email/手机号/身份证/Bearer/sk-key/kv 秘密/URL 凭据全形状 redact + 240 截断；UserIDHash 贯穿 WS 日志；`abortWithAPIError`/`sanitizeErrorResponse` 双轨保证对外错误为 i18n 通用文案（dev 才回原文）；`gin.Default()` 自带 panic Recovery。
- **写路径幂等**：`TryAcceptRealtimeRequest`（request_id 去重）、quota `ReserveRequest/RefundReservation`（Lua 原子 + requestID 幂等键）、outbox `FOR UPDATE SKIP LOCKED`。
- **分层**：handler→service 边界整体干净（quota/chat_history/user_context/task_command/galaxy_command 等 service 化）；galaxy RecordStudy 走 Go CQRS 事件（设计内）；唯一挂"网关做内容处理"的是社区消息 bluemonday 清洗（websocket_proxy.go:629-660），属安全卫生而非 AI 推理，判不违规。

---

## 5. 测试执行记录

环境：macOS arm64，Go 1.25.7，`CGO_ENABLED=0`（按项目铁律）。

```
# 准备：gen/ 为 gitignored 生成物，worktree 缺失。核对 proto/ 与主仓（同 commit 90daac8a）diff 为空后，
# 从主仓复制 backend/gateway/gen（等价 make proto-gen 产物，buf 1.66.0 在本机可用）。

$ CGO_ENABLED=0 go vet ./...
（复制 gen 前）FAIL：4 个 "no required module provides package .../gen/..." setup failed
（复制 gen 后）通过，零输出

$ CGO_ENABLED=0 go test ./...
ok   github.com/sparkle/gateway/internal/cqrs          3.572s
ok   github.com/sparkle/gateway/internal/cqrs/event    0.888s
ok   github.com/sparkle/gateway/internal/db            2.091s
ok   github.com/sparkle/gateway/internal/logsafe       2.387s
ok   github.com/sparkle/gateway/internal/middleware    7.356s
ok   github.com/sparkle/gateway/internal/service       9.654s
FAIL github.com/sparkle/gateway/internal/config        （无 JWT_SECRET 环境：config.Load 的 log.Fatal，
                                                        环境依赖，非代码缺陷，CI 设密钥后绿）
FAIL github.com/sparkle/gateway/internal/handler      15.757s
  --- FAIL: TestProxyRoutesHandler_ClientTelemetryAuthBoundary   ← 本次新发现（GW-P1-3，确定性失败）
  --- FAIL: TestChatOrchestrator_QuotaIntegration                 ← 已知本地沙箱阻塞（债务台账已登记：
      测试内真实 localhost WS 拨号 nil conn panic，与代码改动无关，未计入新发现）
```

与"全绿基线"差异：**handler 包 2 红（1 新 1 已知）+ config 包环境红**。`-race` 因 CGO_ENABLED=0 不可用，并发问题均为静态审查结论（GW-P0-1 的 map 竞争在 `-race` 下可直接复现，建议 CI 补跑）。

---

*审查方法：server/ 与 internal/middleware、internal/handler 逐文件深读；internal/service、internal/agent、internal/cqrs 重点文件深读；`go func` 全量扫描（38 处）逐一核对 ctx 取消与退出路径；gen/ 与 SQLC 产物仅对照未审。*
