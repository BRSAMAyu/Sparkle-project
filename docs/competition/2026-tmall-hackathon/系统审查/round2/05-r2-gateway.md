# 05 · Go 网关 R2 复审（全系统审查·第二轮）

- 复审员：5 号（DeepAudit：长调用链 / 并发 / 泄漏类深缺陷）｜切片：`backend/gateway/` 全量
- 基线：main@ca86bda8（R1 修复已集成），worktree `/Users/brsama/code/GitHub/Sparkle-sysrev/wt5`
- 输入：[round1/05-gateway.md](../round1/05-gateway.md)、[round1/05-fixes.md](../round1/05-fixes.md)
- 环境：macOS arm64，Go 1.25.7，`CGO_ENABLED=0`（项目铁律）；`go vet ./...` 零输出
- 基线噪音未重报：`TestChatOrchestrator_QuotaIntegration` 基线红（本轮已出根因修法，见 §4.2）、config 包需 JWT_SECRET、R1 台账项（GW-P2-3 除外——本轮有新证据升级，见 R2-GW-8）。

---

## 1. 修复验证结论（任务 A）

**9 项（P0×1、P1×4、P2×2、P2 半修×1）全部落地核实，R1 新增测试全绿。**

| ID | 核实点 | 结论 |
|---|---|---|
| GW-P0-1 | `file_event_hub.go:61-67` Send 在 RLock 内快照成 slice；`file_events.go:68` 升级后即包 wsSafeWriter；handler 3 处本地 Close 帧（:73/:88/:119）全部经 writer；hub 注册对象是 writer 而非裸 conn；`setup.go:395-401` 订阅者 goroutine 包 recover | **落地**。测试：`TestFileEventHub_SendWhileRegisterUnregister_ConcurrentStress`、`TestFileEventHandler_HubSendOverlapsRateLimitClose` 等 4 项全绿（本机复跑） |
| GW-P1-1 | `agent/client.go:366-385` retryCtx 父级改为调用方 ctx；cancel 移交 `cancelOnDoneStream`（Recv 终止时 once 释放计时器）；失败分支显式 retryCancel | **落地**。`TestStreamChatRetryStreamAliveAfterReturn` / `HonorsCallerCancel` 绿 |
| GW-P1-2 | `chat_orchestrator.go:347-349` streamCtx + 读泵错误回调 `cancelStreams()`；消息循环 9 处 ctx 全部替换为 streamCtx | **落地**。`TestChatOrchestrator_ClientDisconnectReleasesStreamSlot` 绿，断连 0.5s 内释放槽位。**但该修复引入一处回归，见 R2-GW-1（P1）** |
| GW-P1-3 | `proxy_routes.go:733-747` `/events`、`/events/batch` 匿名直达，`/summary` 留在 authedTelemetry 子组 | **落地**。契约测试绿 |
| GW-P1-4 | `setup.go:131-143` `startDetachedRebuild`（Background + 10min 上限），rebuild 两分支（:713/:750）均已接入 | **落地**。`TestStartDetachedRebuildContextSurvivesCallerReturn` 绿 |
| GW-P2-1 | `setup.go:606-607` `api.Use(NetworkResilience)` 在 `RegisterProxyRoutes`（:610）之前；engine 级 Use（:858）在 NoRoute（:859）之前 | **落地**（gin 快照语义正确） |
| GW-P2-2 | `stt_handler.go:26-46` STT upgrader 改用 factory.checkOrigin | **落地**。4 子测试绿 |
| GW-P2-4 | `ws_metrics.go:96` 新增 `sparkle_quota_daily_usage_load_errors_total`；`chat_orchestrator_chatflow.go:597` 加载失败时 Inc | **落地（半修符合 R1 声明）** |

### P0 专项复核：还有没有第三个写入口？

对一条 `/ws/files` 连接的全部可能写者做了穷举：

1. Redis 订阅者 → `hub.Send` → 快照后逐个 `WriteJSON` → 命中的是 wsSafeWriter（注册的就是 writer）✓
2. handler 本地 Close 帧 3 处 → 全部经 writer ✓
3. **不存在第三写入口**：/ws/files 无 ping ticker（对比 chat 有）；`FileEventSubscriber.Run` 唯一写动作是 `hub.Send`（file_event_subscriber.go:66）；hub 错误路径 `conn.Close()` 是 wsSafeWriter.Close（closeOnce 包裹，且 gorilla Close 与写并发安全）；handler `defer conn.Close()` 是裸连接关闭（非写）✓

`wsSafeWriter.withLockContext` 复核：超时未取得令牌的分支**不注册** defer 归还（无令牌泄漏/双归还）；取得后 defer 归还恰好一次；`fn` panic 时令牌仍归还。streamSem 同理：`chatflow.go:304-305` 单点获取 + 单 defer 释放，default 拒绝分支不占槽，**无双释放/漏释放分支**（E2E 亦验证断连后槽位归零）。

### recover 后订阅者状态一致性

recover 只保证进程存活。panic 展开时 `Run` 内 `defer pubsub.Close()` 会执行（订阅资源正确释放），hub 侧无残留（连接随客户端断开自行 Unregister，map 自愈）——**状态一致，但服务活性丢失**：订阅者 goroutine 退出后无人重启，/ws/files 推送静默死亡直到进程重启，仅一条 Error 日志、无指标（见 R2-GW-3）。注：单写者修复后 hub.Send 本身已几乎不可能 panic（WriteJSON 返回 error 而非 panic），recover 属纵深防御。

---

## 2. 端到端与深审结果（任务 B）

### 2.1 WS 全链路 E2E（新增测试，真实组件全链）

新增 `/Users/brsama/code/GitHub/Sparkle-sysrev/wt5/backend/gateway/internal/handler/ws_e2e_roundtrip_test.go`（**工作树新增、未 commit，可由修复员随 R2-GW-1 修复一并提交**）。链路：

```
真实 WS 拨号（JWT Bearer 头，dart:io 同款无 Origin）
  → 真实 WsAuthMiddleware（HS256 验签 + miniredis 黑名单查询）
  → 真实 ChatOrchestrator.HandleWebSocket（升级/wsSafeWriter/registry/streamSem）
  → 真实 agent.Client（gRPC 流式）
  → 进程内 mock 引擎 StreamChat（2 delta + usage + finish → EOF）
  → JSON 流回客户端 → 陡断 → 重连 → 第二轮流播 → idle 超时关闭
```

断言覆盖：伪造 JWT 401 且不注册连接；ack→delta 顺序与文本拼接 `Hello world`；用户消息落 history；`llm_tokens:*` 计量键出现；陡断后 registry 清零、streamSem 归零；重连后二轮流播、引擎恰好收到 2 次 StreamChat；idle 1s 服务端主动关闭。全部绿（-count=3 稳定，与既有 WS 测试合跑亦绿）。

**该 E2E 直接复现了一个 R1 未发现的 P1 缺陷（R2-GW-1，见 §3）。** 这是单文件单测无法暴露、只有全链组合才能出现的缺陷类型。

### 2.2 优雅关停四阶段自洽性

`main.go:114-171` 实际序列：`bgCancel`（CQRS/file subscriber/GC/outbox relay）→ `StopAllRateLimiters` → Phase1 `StartDraining`（chat+proxy 拒新）→ Phase2 `srv.Shutdown`（goroutine 中，hijacked 连接不受其等待，立即返回无碍）→ Phase3 `ProxyDrainAll` + `registry.DrainAll`（关帧+关conn+hub 原子清+wg 等待）→ Phase4 等 Shutdown 结果 → defer 链关 gRPC 客户端（上游）→ defer 关 DB/Redis（存储）。

**结论：停接收→排空→关上游→关存储的次序自洽**，与 F5 修复后预期一致。复核细节：
- DrainAll 对裸 conn 的 `WriteControl`/`Close` 与 handler 在途写（wsSafeWriter）并发安全（gorilla 语义允许）；
- 断连→cancelStreams→在途 handleChatMessage 的 gRPC Recv 即时中断→handler 返回（P1-2 修复使 WS 排空不依赖 300s 流超时）；
- CQRS 先停的语义：在途事件停留 outbox，重启后续发（at-least-once，消费端 position 幂等，可接受）；
- 小瑕疵（R2-GW-6，P3）：ProxyDrainAll 与 DrainAll **各拿满额** drainTimeout（T/3），最坏 2T/3，与总预算 T 的关系是"能塞下但不宽裕"；两处应共享同一 deadline。

### 2.3 goroutine 全静态扫描（45 处 `go` 启动点逐一核对）

出口完备性结论（ctx 取消 / channel 关闭 / ticker stop / conn 关闭驱动）：

| 类别 | 站点 | 结论 |
|---|---|---|
| 聊天生命周期 | ping ticker（orch:277）、读泵（connections:20） | ✓ pingDone/读错误退出；读有 90s pongWait 死线 |
| 社区代理 | 双向泵 + ping（proxy:375/440/475） | ✓ 双侧 read deadline + pong handler + closeOnce + 每 goroutine recover |
| **STT 中继** | stt:133/168 | **✗ 无 read deadline、无 ping/pong**（R2-GW-4） |
| 注册表 | ws_registry:90/136/271/322 | ✓ wg 跟踪 / stopCh；PublishConnectionEvent 用 Background 无超时但受 go-redis 默认超时约束（P3 注记） |
| 限流/黑名单清理 | rate_limit:82、auth:80/116、distributed:347 | ✓ Stop/stopCh/阈值触发自退出 |
| CQRS/后台 | setup.go 全部、health_checker:153 | ✓ 全部吃 bgCtx / stopCh+wg |
| chat_history | retryWorker:67/115、backfill:475/727 | retryWorker 有 Stop（main 未调用，进程退出无碍）；**backfill 为 fire-and-forget 无上限并发**（R2-GW-7） |
| user_context 扇出 | 386-410 | ✓ 缓冲 chan + 全收集 |
| ab_test | 214/230 | 每请求 2 个异步打点 goroutine，无并发上限（R2-GW-7 同类） |
| 语义缓存更新 | chatflow:939 | ✓ 5s 超时 + WithoutCancel |
| chaos/file_handler | chaos:94、file:253 | dev-only / WithoutCancel（单次 HTTP，受客户端超时约束） |

**streamSem 双释放/漏释放：无**（见 §1）；E2E 断连/完成两路径槽位均归零。

### 2.4 中间件叠放顺序实际语义

- `/api/v1/*` 代理路由实际链：engine(otelgin→I18n→RequestCtx→SecurityHeaders→CORS) → **apiRateLimit** → MaxBodySize → **Timeout(30s)** → NetworkResilience → **auth(组级)** → handler。限流先于鉴权（未认证洪泛按 IP 受限，正确）；Timeout 覆盖鉴权自身（无碍）。
- `/ws/*`（chat/files/stt）：engine 级中间件 → WsAuth → handler。**升级路径无 IP 限流**（鉴权前置使成本仅剩 RS256 验签；per-user 连接上限兜底——P3 注记，非绕过）。
- `/internal`：key → IP 白名单 → 限流（限流器只见已授权流量，密钥端点合理）；`/admin`：AdminAuth → 限流（同型）。未发现"顺序错=绕过"实例。
- WS 路由不在 TimeoutMiddleware 之下（community WS 直接注册在 `r` 而非 api 组，setup.go:496-502）——**无 hijack+超时中间件冲突**。
- NoRoute 兜底：engine 级 NetworkResilience 在 NoRoute 注册之前（:858→:859，P2-1 修复有效）。

### 2.5 长时运行残余面

有界性核查通过：限流 visitors（10k 淘汰）、JWT 黑名单（10k 硬限）、reconnectTrackers（ticker 清理）、registry/两 hub（Unregister 驱动删除）、dedup/request-id/usage 键（全部 SETNX/SETEX 带 TTL）、chat:history（LTrim -20）。残余风险即 R2-GW-4（STT 半开泄漏）与 R2-GW-7（无上限 fire-and-forget 扇出）、R2-GW-5（跨用户写阻塞）。

---

## 3. 复审发现表

| ID | 严重度 | 分类 | 位置 | 缺陷与链路 | 触发/证据 | 修法 |
|---|---|---|---|---|---|---|
| **R2-GW-1** | **P1** | 确认缺陷（E2E 复现 7/8） | `chat_orchestrator_chatflow.go:882→930` 配合 `chat_orchestrator.go:347-349` | **流完成后的助手消息持久化挂在 streamCtx 上，被客户端断连取消**。链路：meta 帧发出（:882）→ `h.saveMessage(ctx,…)`（:930）同步落 Redis → 客户端收到 meta 即断开（手机端"拿到答案即切后台/杀进程"的正常行为）→ 读泵报错 → `cancelStreams()`（P1-2 修复引入）→ saveMessage 的 LLen/pipeline 立即 `context canceled`（chat_history.go:262/314）→ **该轮助手回答永久丢失**（重试缓冲只接队列过载，不接 ctx 取消；无 DB 兜底——E2E 中 history 仅剩 `[user]`）。R1 P1-2 之前该 ctx 是 hijack 后永不取消的 request ctx，持久化"沾了缺陷的光"；修复泄漏时把这个隐式依赖打破了。同窗口内 `RecordUsage`（:809/:818，计费）也可能被取消（窗口更窄）。讽刺的是 :938 的**异步**语义缓存更新已用 WithoutCancel，而**同步关键持久化**没有 | 新增 E2E 子测 `client_close_immediately_after_meta_loses_assistant_turn`：meta 后立即 Close，8 次中 7 次 `history roles: [user]` + 日志 `Failed to save chat message: context canceled`（当前为信息性断言，未 gate CI） | 终局持久化改挂离连 ctx：`saveCtx,c := context.WithTimeout(context.WithoutCancel(ctx), 5*time.Second); defer c(); h.saveMessage(saveCtx,…)`；:712 的截断保存与 :809/:818 的最终 RecordUsage 同样处理（分段计量保持随流取消即可）。修后将 E2E 探针转为硬断言 |
| **R2-GW-8** | **P1** | 确认缺陷（组合证据，升级 R1 GW-P2-3） | `websocket_factory.go:42-44`、`websocket_proxy.go:84-103` + 移动端三个 WS 服务 | **生产环境原生移动端 WS 全被 403 拒绝**。证据链：①移动端 WS 仅设 Authorization 头、从不发 Origin（dart:io WebSocket 也不自动加；`websocket_chat_service_v2.dart:1715-1729`、`community_websocket_service.dart:156/207`、`web_socket_service.dart:71`）；②factory 生产拒空 Origin，community 代理仅放行 Host=localhost:8080/127.0.0.1:8080；③nginx/docker/k8s 全部配置无 Origin 注入；④生产 AllowedOrigins 若配 `*` 亦被 `IsOriginAllowed` 显式拒绝（config.go:164-168）。⇒ /ws/chat、/ws/files、/ws/stt、community WS 四条原生链路在生产域名下全部握手失败。R1 定级 P2"待移动端确认"，本轮三方证据（移动代码+网关代码+部署配置）闭合，升级 P1 | QuotaIntegration 基线红即此缺陷的测试形态（§4.2）；E2E 证明 dev 下无 Origin 可连（生产同款拨号被拒） | 原生客户端已经过 WsAuth（持有效 JWT/ticket），Origin 属浏览器 CSRF 防护、对非浏览器无意义：鉴权成功后放行空 Origin（保留非空 Origin 的白名单校验防浏览器跨站）；或强制 ticket 子协议路径。需网关+移动共同决策后落地 |
| R2-GW-4 | P2 | 确认缺陷（静态确证） | `stt_handler.go:77,133-192` | STT 中继双泵无 `SetReadDeadline`、无 ping/pong：客户端半开（移动网络 NAT 超时无 FIN）且 Python STT 无下行时，两个读泵 + handler（阻塞在 `<-errChan`）**无限期泄漏**（3 goroutine + 2 socket/会话），长期运行累积。chat（90s pongWait）与 community 代理（双侧 deadline）均有死线，唯 STT 缺失 | 对比三套 WS 实现的保活矩阵；静态确证 | 仿 community 代理：双侧 SetReadDeadline(pongWait) + PongHandler + ping ticker（或至少 handler 返回路径上已有 conn Close 兜底——问题是 handler 永不返回） |
| R2-GW-5 | P2 | 确认缺陷（静态确证） | `signal_hub.go:16,58-59` + `signal_push.go:127` | SignalHub.Send 持 **hub 级全局 sendMu** 贯穿所有用户的全部写：任一聊天慢连接（chat writeWait 下限 60s）可阻塞**所有用户**的 widget 推送，`/internal/signals/push` HTTP handler 成排堆积。per-conn 串行已由 wsSafeWriter 保证，sendMu 不增加安全性只增加队头阻塞。R1 修的 FileEventHub 无此全局锁（两 hub 模式不一致） | 写等待上限 = 慢连接数 × 60s（chat writeWait 下限）；/internal 有独立限流但 handler 仍会排队 | 删除 sendMu（对齐 FileEventHub 快照模式）；或按 userID 分锁 |
| R2-GW-3 | P2 | 确认缺陷（静态确证） | `setup.go:395-401` | file 订阅者 recover 后 goroutine 终止、**无重启/无指标/无告警**——/ws/files 推送静默死亡至进程重启（状态一致但活性丢失）。属 P0 修复的收尾缺口 | recover 在 goroutine 顶层 defer，Run 不会重入 | recover 后循环重启（带退避）+ `sparkle_file_event_subscriber_restarts_total` 指标；至少加 liveness 告警 |
| R2-GW-2 | P2 | 确认缺陷（当前死代码） | `internal/db/scripts/decr_quota.lua:10-13` | 见 §4.1 专项 | `result == current - 1` 恒真 | 见 §4.1 |
| R2-GW-6 | P3 | 结构风险 | `main.go:146-164` | ProxyDrainAll 与 DrainAll 各拿满 drainTimeout，最坏合计 2T/3 挤占总预算 | 静态 | 两 drain 共享一个 deadline 实例 |
| R2-GW-7 | P3 | 结构风险 | `chat_history.go:475/727`、`ab_test_middleware.go:214/230` | backfill/AB 打点 fire-and-forget 无并发上限、不进 WaitGroup；Redis/指标端故障时按请求速率堆积 goroutine（受底层 HTTP/Redis 客户端超时约束，最终会退，但无背压） | 静态 | 信号量限并发 + 计入 wg 或改批量异步队列 |
| R2-GW-9 | P3 | 观测缺口 | `internal/middleware/auth.go`（admin/internal 401 路径） | 密钥错误请求不进入限流器计数（key-auth 先于限流），高频爆破仅留日志 | 静态（密钥高熵，实际风险低） | 失败计数独立指标或纳入限流键 |
| — | P3 | 观测注记 | `chat_orchestrator_chatflow.go:589` 与 `isDevelopmentEnv()` | 配额门用全局 handlerConfig 判 dev 而非 h.cfg.Environment：测试进程内若其他用例调用过 InitHandlerConfig(dev) 会改变本用例行为（顺序耦合）；quota_integration_test 的 `os.Setenv("ENVIRONMENT","prod")` 是跨用例污染源（见 §4.2 修法一并处理） | 静态 | 判定统一走 h.cfg；测试移除 os.Setenv |

---

## 4. 专项诊断（任务 C）

### 4.1 F3：网关 Lua 配额族与 Q1（滑动 TTL 永不重置）同型判定

逐脚本判定（`backend/gateway/internal/db/scripts/`）：

| 脚本 | TTL 行为 | 判定 |
|---|---|---|
| `reserve_quota.lua` | **无任何 EXPIRE**（只 DECR + SETEX 请求键） | **与 Q1 不同型**——不存在滑动续期。副作用：配额键 TTL 完全依赖外部初始化者，而全仓无人初始化 `user:quota:*`（见下） |
| `refund_quota.lua` | 无任何 EXPIRE | **与 Q1 不同型**，同上 |
| `decr_quota.lua` | `if result == current - 1 then EXPIRE(ttl)` —— DECR 之后 `result` **恒等于** `current-1`，注释"on first decrement"的守卫是**空真**：每次扣减都滑动续期 | **Q1 同型缺陷成立**：若接线，活跃用户的每日配额键永不过期 → 每日配额永不重置（滚动终身预算）。当前无调用者（见下），属"埋雷死代码" |
| `record_usage.lua` | 每次用量 `EXPIRE(24h)`（字面滑动） | **无害**：键为 `llm_tokens:{uid}:{YYYY-MM-DD}` 日期后缀，跨日本身换键，滑动只延迟清理（最长约 48h），不影响重置语义 |

**关键事实（比 Lua 本身更重要）**：`ReserveRequest`/`RefundReservation`/`DecrQuota` 在网关内**零生产调用者**（实际调用仅为 GetDailyUsage/RecordUsage/RecordUsageSegment）；`user:quota:*` 键全仓（Go+Python+Lua）**无初始化者**——即便调用，GET 为 nil → current=0 → 直接 insufficient。R1 报告"验证良好清单"中"quota ReserveRequest/RefundReservation（Lua 原子 + requestID 幂等键）"实际是对**死代码**的背书；实际准入控制是"事前读用量（fail-open，GW-P2-4）+ 流中分段校验 + 事后记账"。

**修法（二选一）**：
1. **推荐：删除死代码**（三个 Lua + QuotaService 对应方法 + 测试），台账登记"实际配额链路为 usage 计量型"，消除 R1 误背书与 decr_quota 的埋雷；
2. 若计划接线：`decr_quota.lua` 守卫改为 `if redis.call("TTL", KEYS[1]) == -1 then redis.call("EXPIRE", …) end`（仅无 TTL 时设置），或整体改用 record_usage 的日期后缀键模式。

### 4.2 F5：saveMessage 无 nil 防护 + QuotaIntegration 根因修法

**saveMessage**（`chat_orchestrator_feedback.go:77`）：`h.chatHistory.SaveMessage` 无 nil 判断，而调用点 `chatflow.go:362`（用户消息）不在任何 chatHistory nil 检查之内。生产接线恒非空（setup.go:265-280），仅 nil 依赖构造的测试会 panic。最小修法：

```go
func (h *ChatOrchestrator saveMessage(...) {
	if h.chatHistory == nil {
		return // test-only wiring; production always provides the service
	}
	...
```

**QuotaIntegration 根因（复核确认 F5 诊断，并补第二重陷阱）**：
1. 测试设 `ENVIRONMENT=prod` + `DefaultDialer.Dial(wsURL, nil)` → **无 Origin 头** → factory.checkOrigin 返回 `!IsProduction()`=false → 升级 403；
2. 即便补 Origin，`AllowedOrigins:["*"]` 在生产被 `IsOriginAllowed` 显式跳过（config.go:164-168）——**双重必死**；
3. `assert.NoError` 非致命 → nil conn → `defer conn.Close()` nil 解引用 panic（基线红的确切形态）。

修法（保生产语义不变）：

```go
// 工厂配置改为精确 origin（httptest 端口随机，须在 ts 启动后取）：
origin := "http://" + ts.Listener.Addr().String()          // 如 http://127.0.0.1:54321
wsFactory := NewWebSocketFactory(&config.Config{Environment: "prod", AllowedOrigins: []string{origin}})
...
conn, _, err := websocket.DefaultDialer.Dial(wsURL, http.Header{"Origin": []string{origin}})
require.NoError(t, err)                                     // assert→require：拨号失败即中止，杜绝 nil conn panic
```

同时建议删除 `os.Setenv("ENVIRONMENT", "prod")`（quota 门走全局 `isDevelopmentEnv()`，测试进程内 handlerConfig 为 nil → 已按非 dev 生效，该 env 只制造跨用例污染）。此测试修复后，GW-P2-3/R2-GW-8 的生产行为判定不受影响——那是真实缺陷而非测试问题。

---

## 5. 测试记录

```
$ CGO_ENABLED=0 go vet ./...                                    → 零输出
$ export SECRET_KEY=x JWT_SECRET=test-secret-0123456789abcdef CGO_ENABLED=0

逐包 -count=1：
ok  internal/logsafe  0.587s     ok  internal/config  0.515s（JWT_SECRET 已设）
ok  internal/db       0.499s     ok  internal/cqrs/event  0.509s
ok  internal/cqrs     2.780s     ok  internal/agent  0.960s
ok  cmd/server        0.660s     ok  internal/middleware  5.619s
ok  internal/service  8.524s
internal/handler：唯一红 = TestChatOrchestrator_QuotaIntegration（已知基线噪音；
  panic 栈与 F5 根因一致：403 拒升级 → nil conn；修法见 §4.2）

R1 回归测试复跑（全绿）：
  TestFileEventHub_ConcurrentAccess / _SendRemovesBadConnections /
  _SendWhileRegisterUnregister_ConcurrentStress（1.52s 压测）
  TestFileEventHandler_HubSendOverlapsRateLimitClose
  TestStreamChatRetryStreamAliveAfterReturn / TestStreamChatRetryHonorsCallerCancel
  TestChatOrchestrator_ClientDisconnectReleasesStreamSlot
  TestSTTUpgrader_OriginPolicyMatchesFactory（4 子测试）
  TestProxyRoutesHandler_ClientTelemetryAuthBoundary
  TestStartDetachedRebuildContextSurvivesCallerReturn

新增（本轮产物，未 commit）：
  internal/handler/ws_e2e_roundtrip_test.go
    TestChatOrchestrator_WSFullChainE2E（3 子测试，含 R2-GW-1 复现探针，信息性）
    TestChatOrchestrator_WSE2E_IdleTimeout
  复跑稳定性：单跑 -count=3 绿；与既有 TestChatOrchestrator_WS* 合跑 -count=3 绿
  R2-GW-1 复现率：立即关闭场景 8 跑 7 复现（history=[user] + context canceled 日志）
```

-race 因 CGO_ENABLED=0 铁律不可用（本机 Xcode license），并发结论均为静态论证 + 并发压测；建议 CI 补跑 -race。

---

*复审方法：R1 修复逐项代码级核对 + 新旧测试复跑；45 处 goroutine 启动点全扫出口；四阶段关停序推演；三中间件叠放语义核对（含 /internal、/admin、NoRoute）；Lua 配额族逐脚本判定并回溯键初始化者与调用者；移动端 WS 头行为 + 部署层 Origin 注入双向核查；全链 E2E 以真实 WsAuth/真实 gRPC 客户端驱动并借以复现 R2-GW-1。工作树改动仅新增上述测试文件与本报告。*
