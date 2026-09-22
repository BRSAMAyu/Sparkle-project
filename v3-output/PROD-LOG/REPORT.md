# PROD-LOG — 活栈真实日志巡检报告（生产缺陷挖掘）

- 卡号：PROD-LOG（北极星全旅程战役 · C 纵队生产级打磨线）
- 基线：`2b2bb68c`（worktree wt175）；主仓运行实例同 commit（`git log` 双侧核对一致）
- 日期：2026-09-23；巡检方式：**纯只读**（grep/docker logs/redis 只读命令/curl GET），未改任何产品代码、未重启进程、未写 DB
- 日志源与覆盖：
  - 引擎当前实例（06:52 起）：`/tmp/grpc_server.log`（117 行）、`/tmp/uvicorn_engine.log`（97 行）
  - 引擎此前实例（09-22 19:2x ～ 09-23 06:26）：`/tmp/sparkle_engine.log`、`/tmp/sparkle_fastapi.log`、`/tmp/grpc_engine.log`
  - 网关 PID 79057（06:11 起）：stdout=`/tmp/sparkle_gateway.log`；应用日志=主仓 `backend/gateway/logs/local/gateway.log`（29MB，2026-09-18 18:59 → 09-23 06:26，另 3 个 09-18 18:58-59 的 ~940KB `.gz` 轮转档）
  - 容器：`sparkle_db`、`sparkle_redis`、`sparkle_minio` 的 docker logs（近 24h）
- 脱敏说明：日志中未发现明文 key/token/密码（引擎日志以 `Password=Yes, PasswordSource=url` 掩码，网关 auth 日志仅记 `user_hash`）；本报告只报字段名不报任何凭据值。
- 证据标注约定：`log:` 后为真实日志行摘录；`code:` 后的 文件:行号 均已在 wt175 基线逐行核对（非凭日志猜测）。

---

## ① 错误/警告聚类表

### 网关（gateway.log，5 天窗口；全部为 zap 结构化日志）

| 簇 | 频次 | 时间分布 | 样例（摘录） | 根因判定 | 置信度 |
|---|---|---|---|---|---|
| `service/file_event_subscriber.go:49` warn "File status subscriber error: dial tcp 127.0.0.1:6379 connect: connection refused" | **101,071** | 全部集中在 09-18 18:59:02–07（**约 5 秒，≈2 万条/秒**）；3 个 .gz 轮转档即此洪峰产物 | 见左 | **历史缺陷（已修）**：pre-fix 二进制在 Redis 不可达时 pubsub 循环 warn+continue 热转。现行基线已含 R2-GW-3 修复（`file_event_subscriber.go:128-132` 改为上抛给 `RunWithRestart` 退避 250ms→5s，:43-46/:56-87） | 高 |
| `outbox/publisher.go:99` error "Failed to publish batch … dial tcp 127.0.0.1:5432 connect: connection refused" | **8,494**（09-18: 579 / 09-19: 6,409 / 09-20: 1,506） | DB 宕机窗口内每 100ms 一条（poll_interval=0.1s） | 见左 | **真缺陷（开放）**：固定 tick 轮询对连续失败无退避——DB 不可达时 10 条 error/秒，刷日志刷指标。`code: gateway/internal/cqrs/outbox/publisher.go:89-103` | 高 |
| `worker/base.go:146` error "Error processing messages" | 1,928 | 09-18~20 为 xreadgroup i/o timeout / connection refused / MISCONF；**09-23 仍有 9 条，全部为 "xreadgroup: context canceled"（00:45:28 重启期）** | `{"error":"xreadgroup: context canceled"}` @ 06:11/00:45 重启点 | 双根因：事故期网络错误（合理）+ **关停噪音（缺陷）**——`context canceled` 是主动关停却记 ERROR（worker 有 1s 退避但无 ctx 判断）。`code: gateway/internal/cqrs/worker/base.go:139-149` | 高 |
| `worker/base.go:170` warn "Consumer group missing, attempting to recreate" + NOGROUP | 630 | 09-19 事故期为主 | `NOGROUP No such key 'cqrs:stream:task' …` | 噪音（自愈设计正常）：group 被清后自动重建，但每次重建前都先打 NOGROUP error 级明细。`code: worker/base.go:168-180` | 高 |
| `middleware/auth.go:393` warn "auth failed: missing token" / `:287` "middleware error response"(401) | 439 / 512 | 全程均匀 | 06:26:53 实证（无 token 探测） | 噪音（预期客户端行为/负向测试）：401 未认证流量逐条 warn | 高 |
| `middleware/rate_limit.go:479` warn "Hybrid rate limiter Redis failed; falling back to local" | 338 | 09-19 08:4x（MISCONF 窗口） | MISCONF RDB 快照失败 | 噪音（降级设计正确且生效）；可指标化 | 高 |
| `handler/chat_orchestrator.go:387/381` warn "WebSocket read error: websocket: close 1000 (normal)" | 129+94 | 09-22~23 持续 | 09-23 05:17:03 实证 | **真缺陷（开放）**：`IsUnexpectedCloseError(err, CloseGoingAway, CloseAbnormalClosure)` 未把 `CloseNormalClosure(1000)` 列入预期白名单→每次客户端正常断连都告警。`code: gateway/internal/handler/chat_orchestrator.go:386-388` | 高 |
| `cmd/server/setup.go:4xx` error "File GC/Outbox cleaner/DLQ cleaner/Outbox publisher stopped … context canceled" | 每次 ~10 条（09-18 起 44+ 条） | 每次网关重启（09-23 06:11:40 实证） | 见左 | 噪音（缺陷级）：主动关停路径记 ERROR。`code: cmd/server/setup.go:405-451` | 高 |
| `service/chat_history.go:498` error "Chat history DB fallback failed: invalid session_id: cannot parse UUID" | 15 | 09-19 | `session_id:"df2-d1-s1"`、`"nonexistent-session"` | 轻缺陷：非法 session_id 未在校验层拦住、以 error 级进 DB fallback 路径 | 高 |
| `middleware/auth.go:581` warn "Redis unavailable with Fail-Closed mode, rejecting token" | 8 | 09-19 08:48 | i/o timeout | 设计取舍观察：fail-closed 下 Redis 抖动=全员 401（见 ②-10 讨论） | 高 |
| `level=fatal` "bind: address already in use"（server/main.go:110） | 6 | 09-19 00:22–02:42 | 见左 | 运维噪音：事故夜重复拉起撞端口，非代码缺陷 | 高 |
| MISCONF（Redis RDB stop-writes）散布于 rate_limit/worker 等簇 | 141 行 | 最后一次 09-19 08:42:03 | "unable to persist to disk" | **基础设施历史事故（磁盘耗尽）**，已恢复（当前 `rdb_last_bgsave_status:ok`）；但暴露 Redis 仅 RDB 无 AOF 的持久化短板（见 ④） | 高 |
| `handler/websocket_proxy.go:240` error "Failed to dial backend: bad handshake"（community ws） | 6 | 09-18 21:43 | ws://127.0.0.1:8000/api/v1/community/ws/connect | 观察项：引擎侧当时未就绪/拒绝升级，样本过少 | 中 |

### 引擎（loguru；三个此前实例 + 当前实例启动段）

| 簇 | 频次 | 样例 | 根因判定 | 置信度 |
|---|---|---|---|---|
| `profile_context_service:_populate_user_state_v1_payload:342` warn "Failed to populate user_state_v1 payload: type object 'KnowledgeNode' has no attribute 'importance'" | 50（fastapi 37 + grpc 13；09-23 06:25:59–06:26:01 两秒内 37 条） | 见左 | **真缺陷（开放，高价值）**：`predictive_service.py:496` 引用了不存在的列 `KnowledgeNode.importance`（实际列为 `importance_level`，`models/galaxy.py:138`）；异常沿 `state_aggregator/service.py:438 → get_user_state(:122)` 上抛后在此被吞 → **整个 user_state_v1 上下文缺失**。详见 ②-2 | 高 |
| `checkpoint.redis_checkpointer:save:43` warn "Skipping non-serializable context key: run_ledger/transparency_generator/emit_transparency_event/redis_client/grounding_validator" | 585（sparkle 218 + grpc 367） | 见左 | 噪音（缺陷级）：允许清单只有 3 个旧 key（`redis_checkpointer.py:37`），新增非序列化 key 每次存档都告警。详见 ②-7 | 高 |
| `core.event_bus:_process_stream_message:1246` warn "Could not acquire lock for message: …" | ~129（fastapi 33 + grpc ~96） | 同一 message id 可连续 9 次（1790115130714-0） | **真缺陷（开放）**：幂等锁键 `evt:{stream}:{message_id}`（`event_bus.py:1237`）**不按消费组隔离**，而 sparkle_events 上挂 30+ 消费组，跨组互抢锁→输者不 ACK 留 PEL、等 5s autoclaim（`pending_retry_idle_ms=5000`，:722）重试→扇出延迟+刷 warn。详见 ②-3 | 高 |
| `orchestration.context_sources:detect_merge_overrides:579` "context source override: grpc_context replaced local_context key=next_actions/focus_stats/active_plans" | 60 | 每 chat 3 条 | 噪音：预期合并语义，应 INFO/DEBUG | 高 |
| `services.llm_fallback_utils:safe_llm_call` warn "Timeout (attempt 1/2)" + error "All attempts failed … timed out after 12.0s" | warn ~13 / error 3 | 09-21~09-22 零星 | 观察项：LLM 供应商 12s 超时，fallback 生效（有兜底），暂不需修 | 高 |
| `agents.reviewer_agent:review_llm_response:462` error "[ReviewerAgent] Review failed: "（**空错误消息**） | 6 | 19:29:25→19:30:10（45s 后失败） | **真缺陷（开放）**：`asyncio.wait_for` 超时抛 `TimeoutError()`，str 为空→日志无法诊断；且 R6-P0-3 fail-closed 使审查超时=审查失败。详见 ②-4 | 高 |
| `services.galaxy_grpc_service:GetUserGalaxy:344` error "'dict' object has no attribute 'nodes'" | 3（09-22 19:27-19:34）+ 代码注释另记 4 次（09-23 01:42-01:44） | 见左 | **历史缺陷（已修）**：`@cached` 缓存命中返回 dict 后直接访问属性。现行基线已有 COLDSTART fix（`galaxy_grpc_service.py:353-368` isinstance 再水化） | 高 |
| `orchestration.orchestrator:_bind_response_session_id:1503` warn "response missing session_id; bound active session_id" | 19 | 09-22 19:22 | 观察项：兜底绑定生效，但说明上游某路径漏带 session_id，低优 | 中 |
| 启动期 `dynamic_tool_registry:register_from_module:124` warn "No valid tools found in app.tools.{base,entity_cards,metadata,plan_resolution,registry,schemas}" | 每次启动 6 条 | 当前实例 06:52:44 | 噪音：扫描到非工具模块，应静默跳过 | 高 |
| 启动期 `app.main:lifespan:206` warn "Failed to initialize Security Monitor: SecurityMonitor.initialize() takes 1 positional argument but 2 were given" | 每次启动 1 条 | 当前实例 06:52:44.971 | **真缺陷（开放，安全面）**：`main.py:203` 传参调用 vs `security_monitor.py:97` 无参签名→**安全监控后台任务从未启动**。详见 ②-1 | 高 |
| 启动期 "MDX dictionary dependencies unavailable, feature disabled: python-lzo" | 每次启动 1 条 | 当前实例 06:52:44 | 观察项：PRODUCTION 环境特性静默降级，依赖未入清单 | 高 |
| LangChain UserWarning "RunnableConfig … not dict"（`agents/graph/workflow.py:87,89,90,231,233,235,236`） | 每次启动 7 条 | 当前实例 | 噪音：节点 handler 类型注解改 `RunnableConfig` 即消 | 高 |
| `services.scheduler_service:run_execution_schedule_tick:233` info "due=%s dispatched=%s"（字面量） | 每分钟 1 条 | 当前实例 06:53:45 | **真缺陷（微）**：loguru 不支持 %s 位置参数，参数被静默丢弃，调度量永远不可见。详见 ②-9 | 高 |

---

## ② 真缺陷清单（按 生产级影响 × 修复成本 排序 top10）

> 「已修/开放」以基线 2b2bb68c 代码为准；历史错误仅为证据。

### 1. SecurityMonitor 自启动起全死（安全监控裸奔）——影响：高 / 成本：S（开放）
- **证据**：`log: uvicorn_engine.log:20 "2026-09-23 06:52:44.971 | WARNING | app.main:lifespan:206 - Failed to initialize Security Monitor: SecurityMonitor.initialize() takes 1 positional argument but 2 were given"`（每次启动必现，被 try/except 吞成 warning 后照常启动）。
- **根因**：`backend/app/main.py:203` 调用 `await security_monitor.initialize(cache_service.redis)`；而 `backend/app/core/security_monitor.py:97` 签名为 `async def initialize(self):`（redis 在 `__init__` :87 已自取）。签名漂移后无人发现——因为失败被降级为非致命 warning。
- **影响**：登录爆破阈值告警、可疑 IP 监控、旧数据清理三个后台协程（security_monitor.py:103-105）从未运行；`record_login_attempt` 等记录逻辑虽在，但监控/告警面为零。网关侧 439 条 "missing token" 探测正说明边界在被打。
- **修复思路**：`initialize()` 接受可选 redis 参数（或调用处去参）；把该初始化失败从非致命 warning 升级为启动失败或显式 metrics 告警；补一条启动断言测试。
- **规模**：S

### 2. `KnowledgeNode.importance` 坏引用 → user_state_v1 上下文整体缺失——影响：高 / 成本：S（开放）
- **证据**：`log: sparkle_fastapi.log "2026-09-23 06:25:59.577 | WARNING | app.services.profile_context_service:_populate_user_state_v1_payload:342 - Failed to populate user_state_v1 payload: type object 'KnowledgeNode' has no attribute 'importance'"`（50 次，两秒内 37 次=每次构建上下文必炸）。
- **根因链**：`profile_context_service.py:342`（catch-all）← `state_aggregator/service.py:122 get_user_state` ← 字段构建器 `:196 "foresight_hint"` → `:432 _build_foresight_hint_summary` → `:438 build_foresight_snapshot` → `backend/app/services/predictive_service.py:496` `KnowledgeNode.importance > topic.importance`。模型实际列名为 `importance_level`（`backend/app/models/galaxy.py:138`）；混淆源可能是同名的另一数据类 `models/graph_models.py:38`（`KnowledgeNodeVertex.importance`，那个才有 `importance` 字段）。
- **影响**：AttributeError 中断 `get_user_state` 全流程 → `profile_context_service.py:324-343` 的 try 吞掉 → **user_state_v1 payload 整体为空**（不止缺 foresight_hint），AI 对话拿不到用户状态向量；且只留一行 warning，无 error、无指标。
- **修复思路**：predictive_service.py:496 两处改为 `importance_level`；`_populate_user_state_v1_payload` 失败时至少 error 级+指标；补一条 `get_user_state` 冒烟测试（本例 50 次 warning 竟无人发现，说明该路径无测试覆盖）。
- **规模**：S

### 3. 事件总线幂等锁键不按消费组隔离 → 扇出延迟 + 告警刷屏——影响：中高 / 成本：M（开放）
- **证据**：`log: sparkle_fastapi.log "2026-09-23 06:11:31.984 | WARNING | app.core.event_bus:_process_stream_message:1246 - Could not acquire lock for message: 1790115091978-0"`（同簇 ~129 条；同一 message 连续 9 条）。
- **根因**：`backend/app/core/event_bus.py:1237` `idempotency_key = f"evt:{stream}:{effective_id}"` 仅按 stream 作用域；`sparkle_events` 上有 30+ 个消费组（uvicorn_engine.log:43-81 启动实证），每条消息投递给每个组，各组在同一把锁上串行互斥。抢锁失败方 `return` 不 ACK（:1245-1247），消息留本组 PEL，等 `pending_retry_idle_ms=5000`（:722）的 autoclaim 重试。
- **影响**：①每条事件对多数消费组引入 ≥5s 的额外扇出延迟（事件驱动链路整体被拖慢）；②每条消息放大出几十条假告警；③若持锁消费者在 unlock 前崩溃，其他组要等 idle 重试才接管。
- **修复思路**：锁键加组维度 `evt:{stream}:{group}:{id}`（幂等 set 同理），或以 consumer group 为幂等主体重新设计；同时把"抢锁失败"降为 DEBUG（同组竞争是正常态）。
- **规模**：M（需回归至少-一次语义相关测试，参考 IDEM-GAPS/EVENT-ACK 卡）

### 4. ReviewerAgent 超时以空消息失败且 fail-closed——影响：中 / 成本：S（开放）
- **证据**：`log: grpc_engine.log "2026-09-22 19:30:10.908 | ERROR | app.agents.reviewer_agent:review_llm_response:462 - [ReviewerAgent] Review failed: "`（错误消息为空；触发点 19:29:25→失败点恰 45s）。
- **根因**：`backend/app/agents/reviewer_agent.py:392-400` 用 `asyncio.wait_for(..., timeout=self.llm_timeout_seconds)`；`asyncio.TimeoutError` 的 str() 为空串，`:462` `logger.error(f"... {e}")` 打出空尾巴。
- **影响**：①线上无法区分超时/解析失败/网络错误（6 条 error 全部不可诊断）；②按 R6-P0-3 fail-closed 逻辑（:463-469），超时即判 FAILED → 强制用户走 reflection，LLM 稍慢就劣化主链路体验。
- **修复思路**：单独 `except asyncio.TimeoutError` 分支记录 `review timeout after {llm_timeout_seconds}s`；评估超时阈值（45s 内未回的 review 是否应重试一次而非直接 FAILED）。
- **规模**：S

### 5. WebSocket 正常断连被当异常告警——影响：中 / 成本：S（开放）
- **证据**：`log: gateway.log "…chat_orchestrator.go:387","msg":"WebSocket read error","error":"websocket: close 1000 (normal)"`（129+94 条，09-22~23 持续）。
- **根因**：`backend/gateway/internal/handler/chat_orchestrator.go:386` `websocket.IsUnexpectedCloseError(err, websocket.CloseGoingAway, websocket.CloseAbnormalClosure)`——gorilla 只把**列出的** close code 视为预期；`1000 (normal)` 不在列→判为 unexpected→`:387` warn。
- **影响**：核心聊天通道的每次用户主动退出都产生 warn，抬高告警基线、淹没真异常（狼群效应）。
- **修复思路**：varargs 加 `websocket.CloseNormalClosure`（并评估 CloseNoStatusReceived/CloseProtocolError 是否同列）。
- **规模**：S（一行）

### 6. Outbox publisher 对持续失败无退避——影响：中 / 成本：S-M（开放）
- **证据**：`log: gateway.log "…outbox/publisher.go:99","msg":"Failed to publish batch","error":"…dial tcp 127.0.0.1:5432: connect: connection refused"`（8,494 条；09-19 单日 6,409 条=DB 宕机 16h × 10 条/s 量级）。
- **根因**：`backend/gateway/internal/cqrs/outbox/publisher.go:89-103` 固定 `time.NewTicker(poll_interval=0.1s)`，`publishBatch` 失败仅记日志+计数器，无连续失败退避。
- **影响**：下游故障时错误日志/指标以 10/s 刷屏（讽刺的是磁盘事故期间加剧了磁盘压力）；错误指标失真（区分不了"抖一下"和"宕了 16 小时"）。
- **修复思路**：连续失败计数→指数退避（如 0.1s→30s 封顶），成功后复位；失败率本身出指标。对照 file_event_subscriber 的 RunWithRestart 模式（:56-87）照抄即可。
- **规模**：S-M

### 7. checkpoint 允许清单过期 → 每次存档 2-4 条假告警——影响：低中 / 成本：S（开放）
- **证据**：`log: sparkle_engine.log "2026-09-22 23:26:41.682 | WARNING | app.checkpoint.redis_checkpointer:save:43 - Skipping non-serializable context key: run_ledger"`（585 条；key 集：run_ledger/transparency_generator/emit_transparency_event/redis_client/grounding_validator 等）。
- **根因**：`backend/app/checkpoint/redis_checkpointer.py:37` 硬编码豁免 `["db_session","stream_callback","tools_schema"]`，新增的非序列化 context key 走到 `:43` warning。
- **影响**：每个 chat 会话每个节点存档都刷 2-4 条，是引擎日志最大噪音簇；也掩盖了"真有该序列化却坏掉的对象"的信号。
- **修复思路**：维护静态"已知不可序列化"清单（模块级常量）+降 DEBUG；新增未知 key 才 warn。
- **规模**：S

### 8. 关停路径把 `context canceled` 记为 ERROR——影响：低 / 成本：S（开放）
- **证据**：`log: gateway.log '00:45:28.038 … worker/base.go:146,"error":"xreadgroup: context canceled"' ×3 组`；`06:11:40.400 server/setup.go:413 "File GC stopped","error":"context canceled"`（每次重启 ~13 条 error）。
- **根因**：`backend/gateway/internal/cqrs/worker/base.go:145-148` processMessages 返回后未判 `ctx.Err()` 即 ERROR+1s 退避；`cmd/server/setup.go:405-451` 四个后台任务的关停 error 同理。
- **影响**：每次发版/重启制造一批假 ERROR，破坏"ERROR=需要人看"的纪律（这 5 天 10,592 条 error 里相当比例是它）。
- **修复思路**：`if ctx.Err() != nil { log.Info("stopping"); return }` 模式套用到 worker/base.go 与 setup.go 关停分支。
- **规模**：S

### 9. 调度 tick 日志 %s 参数被 loguru 静默丢弃——影响：低 / 成本：S（开放）
- **证据**：`log: uvicorn_engine.log:97 "2026-09-23 06:53:45.404 | INFO | app.services.scheduler_service:run_execution_schedule_tick:233 - Execution schedule tick completed: due=%s dispatched=%s"`（每分钟一条，数字永远是字面 %s）。
- **根因**：`backend/app/services/scheduler_service.py:233-237` 用 stdlib logging 的逗号参数风格调 loguru（loguru 只认 `{}` 或 f-string），两个参数被丢弃。
- **影响**：执行调度器的吞吐完全不可观测（due/dispatched 恒不可见）。
- **修复思路**：改 f-string；顺手全仓 grep `logger\.(info|warning|error)\(.*%s` 排查同类（本仓 loguru 面上唯一一例）。
- **规模**：S

### 10. 已修确认区（供回归验收，不必再开卡）
- **FileEventSubscriber 热循环**（历史 101,071 warn/5s）：基线已修——`file_event_subscriber.go:122-133` 失败上抛 + `:56-87` RunWithRestart 退避+重启计数器。建议：历史洪峰日志（29MB 主文件+3 个 gz）归档清理，防二次误导。
- **GetUserGalaxy dict 崩溃**（历史 7 次 error）：基线已修——`galaxy_grpc_service.py:353-368` isinstance 再水化（COLDSTART fix）。
- **chat_history 非法 session_id**（15 条 error）：低价值补充——`service/chat_history.go:498` 前置 UUID 校验并降 warn（现状是进 DB fallback 才报 error）。

---

## ③ 降噪建议（该降级别/删/指标化）

| 项 | 现状 | 建议 |
|---|---|---|
| file_event_subscriber 历史洪峰日志 | 主仓 logs/local/ 下 29MB + 3×940KB gz，5 秒洪峰占 5 天日志量 ~90% | 归档或清理（主仓侧操作，本卡未动）；确认 logs/ 在 .gitignore |
| event_bus 抢锁失败 warn（~129） | WARNING | 降 DEBUG（跨组竞争在 ②-3 修复后应消失；组内竞争是正常态） |
| WS close 1000 warn（223 条） | WARNING | ②-5 修复后自然消失 |
| checkpoint 非序列化 warn（585 条） | WARNING ×每节点 | 已知 key 静默/DEBUG，未知 key 才 warn |
| 关停 context canceled error | ERROR ×每次重启 ~13 | 降 INFO（②-8） |
| NOGROUP recreate 前置 NOGROUP error 明细（630 组） | warn+error 明细 | 首次重建 warn、连续重建降 DEBUG；保留重建成功 INFO |
| auth 401 "missing token"（439 条） | 逐条 warn | 按 IP/路由聚合为指标 + 采样日志 |
| detect_merge_overrides（60 条） | WARNING | 降 INFO/DEBUG（预期合并语义） |
| 启动期 6 条 "No valid tools found" | WARNING | 非工具模块静默跳过，仅汇总一行 |
| GIN debug 路由表 | stdout 100+ 行 [GIN-debug] | `GIN_MODE=release`（生产环境已提示） |
| 工具注册逐条 INFO（38 条） | 每次启动逐工具一行 | 汇总一行 "Auto-registered 38 tools"（已有汇总行，逐条删） |
| LangChain RunnableConfig UserWarning ×7 | stderr | handler 注解改 `RunnableConfig`，一次性消除 |

---

## ④ 健康面快照（2026-09-23 ~07:00）

| 层 | 状态（一句话） |
|---|---|
| Flutter 移动端 | 未巡检（无运行实例，本卡范围外） |
| Go 网关 :8080（PID 79057，06:11 起） | alive——`/healthz` 200；重启后 outbox/DLQ/file-subscriber 错误计数全 0；356ms 内最慢请求为 `/errors/today-review`（334ms，尚可）；无结构化告警自 06:26 后 |
| Python 引擎 gRPC :50051（06:52 起） | 启动干净：38 tools 注册、6 个空工具模块 warning、LangChain 注解 warning ×7；无运行期错误（运行仅 1 分钟） |
| Python 引擎 FastAPI :8000（06:52 起） | `/health` healthy；SecurityMonitor 初始化失败（②-1，安全监控死）；MDX 词典因缺 python-lzo 静默禁用；scheduler tick 每分钟正常跳（数字显示 bug ②-9） |
| PostgreSQL 16（sparkle_db，healthy） | 容器 healthy，但 **stdout 自 09-17 10:33 UTC 后零日志**——PG 日志输出去向需单独确认（不排除 log_destination 指向容器内文件），慢查询面本卡无法从容器日志评估 |
| Redis（sparkle_redis，healthy） | `rdb_last_bgsave_status:ok`、changes_since_last_save=23、57 连接；**AOF 关闭**（纯 RDB，事件总线数据最多丢一个快照间隔；09-19 磁盘事故时 stop-writes MISCONF 已实证该模式的全局拒绝写风险）——建议生产评估开 AOF |
| MinIO（sparkle_minio，healthy） | 24h 无错误日志 |

**与四层架构对位的慢面结论**：唯一成规模的超时在 LLM 出口（12s×~13 次，有 fallback 兜底）；网关→引擎 gRPC 与 DB/Redis 面在日志窗口内未见慢查询/重试风暴（09-19 事故期的 xreadgroup timeout/refused 均已归因基础设施）；引擎→DB 链路当前日志面干净。

---

## 附：巡检纪律执行说明
- 全程只读：未修改产品代码、未重启进程；docker 仅 `ps/logs/exec redis-cli(只读 INFO/DBSIZE)`；Redis 密码仅从主仓 `.env` 读入 shell 变量用于只读认证，未落盘未外传。
- 未创建任何巡检脚本文件（全部单行命令）；/tmp 无本卡产物需清理。
- 本报告为唯一交付物：`v3-output/PROD-LOG/REPORT.md`（worktree wt175）。
