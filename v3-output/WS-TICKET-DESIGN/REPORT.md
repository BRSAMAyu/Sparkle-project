# WS-TICKET-DESIGN — WS 入口 ticket 化 + 签发口限流 实施级设计（wt279-wsrl-design）

> 2026-09-24。C 线·网关安全设计卡（LIGHT 纯设计，不改产品代码）。
> 上游输入：wt275 GATEWAY-LIFECYCLE-AUDIT 缺陷 **D6**（WS 入口零连接限流，`WebSocketRateLimitMiddleware` 死代码）。
> 方法：gateway WS 全链源读（setup/ws_auth/ws_ticket/rate_limit/distributed_rate_limiter/ws_registry/ws_proxy/stt/file_events）+ mobile 端 5 处 WS 客户端源读 + 配置/部署面核对。
> 审计建议复述：把 WS 升级收敛到 ticket 模式后，把限流钉在 `/api/v1/ws/ticket` 签发口（避免按 IP 直连限流的 NAT 误杀）。

## 〇、一句话方案

**不新建票据体系——ticket 模式已存在八成**：现有 opaque-Redis 单次核销 ticket（签发口已挂 per-user 混合限流）只需三步收敛——①在 5 个 WS 路由最前面加一层 **pre-auth per-IP token bucket 握手限流**（挡未认证洪水，立即闭合 D6 主窟窿，客户端零改动）；②把 query-ticket 从 `ALLOW_WS_QUERY_TOKEN` 的 prod 禁令中**解耦放行**（ticket 短时效+单次核销，泄露面有界），使 mobile chat 已写好的 ticket 流在生产真正生效；③按 chat→stt/files→community 的顺序把各入口迁到 ticket-first，最后以 `WS_TICKET_REQUIRED` 开关收紧到「只收 ticket」。

---

## 一、现状精读

### 1.1 WS 入口全集（5 个，全部仅挂 `WsAuthMiddleware`，注册在 api 组之外）

`backend/gateway/cmd/server/setup.go:498-507`：

| # | 路由 | handler | 升级后准入/上限 | 停机排空（wt275） |
|---|---|---|---|---|
| 1 | `GET /ws/chat` | `chatOrchestrator.HandleWebSocket` | `ConnectionRegistry`：全局 max 2000（`WS_GLOBAL_MAX_CONNECTIONS`）+ per-user max 2（`WS_MAX_CONNECTIONS_PER_USER`）；subprotocol echo（`chat_orchestrator.go:247-248`） | registry `DrainAll` |
| 2 | `GET /ws/files` | `fileEventHandler.HandleWebSocket` | 无连接数上限；subprotocol echo（`file_events.go:79`） | `wsConnDrainGroup` |
| 3 | `GET /ws/stt` | `sttHandler.HandleWebSocket` | 无连接数上限；upgrader **不 echo subprotocol**（`stt_handler.go:41-47` 自建） | `wsConnDrainGroup` |
| 4 | `GET /api/v1/community/groups/:group_id/ws` | `wsProxy.HandleCommunityWS` | proxy 内 per-user 重连跟踪（10 次/30s 窗，超限 block 300s；`websocket_proxy.go:777-810`） | `ProxyDrainAll` |
| 5 | `GET /api/v1/community/ws/connect` | `wsProxy.HandlePersonalWS` | 同上 | `ProxyDrainAll` |

关键结构性事实：这 5 条挂在 gin 根引擎上，**api 组的三件套（apiRateLimit 15rps/burst30、MaxBodySize、Timeout）一概不生效**（audit 已指出 setup.go:567-570 的组边界）。根引擎全局中间件只有 otelgin/I18n/RequestContext/SecurityHeaders/CORS——即 **WS 握手是全站唯一从 TCP/TLS 一直打到 handler 都没有任何限流的入口**。

### 1.2 认证链（`middleware/ws_auth.go`，5 入口共用一条路径）

```
GET /ws/*  →  WsAuthMiddleware  →  handler
  ① Authorization: Bearer <JWT>
       → validateJWT（auth.go:490：RS256 主/HS256 过渡）
           签名通过后：Redis EXISTS token_blacklist:<jti> + Redis GET user_revoked_before:<user>
           （500ms budget；生产 RedisFailClosed=true，Redis 挂→拒绝）
       → set user_id / auth_token / ws_auth_method=jwt_header
  ② ?token=<JWT>   仅 ALLOW_WS_QUERY_TOKEN=true（生产启动即 Fatal 强制 false，config.go:708-712）
  ③ ticket：Sec-WebSocket-Protocol「ticket= / ticket: / ws-ticket= / ws-ticket:」或 ?ticket=
       （?ticket 同样被 ALLOW_WS_QUERY_TOKEN 连坐，extractWSTicket 第二参 = 该开关）
       → Redis Lua GET+DEL 原子核销（wsTicketGetDel，单次有效）→ 401 if miss
       → set user_id / auth_token(=ticket payload 内 token) / ws_auth_method=ticket
  ①②③ 全失败 → 401 abort；metrics：ws_connection_error_total{endpoint,auth_method,reason}
```

单次握手的真实成本（未认证攻击者视角）：
- 无凭据/垃圾 JWT：TCP+TLS+HTTP 处理 + gin 链 + `jwt.Parse`（失败路径便宜，不触 Redis）；
- **合法签名的 JWT（可离线批量铸造口径正确的假 payload）**：完整 RS256 验签（CPU 大头）+ 2 次 Redis 往返（fail-closed 下 Redis 打满即拒绝全体认证请求——**放大器打在认证依赖上**）。

### 1.3 现有 HTTP 限流器形制（活的）

`middleware/rate_limit.go` + `distributed_rate_limiter.go`：

- **`HybridRateLimitMiddlewareSimple(rdb, rps, burst)`**（现行唯一在用形制）＝ Redis Lua token bucket（`distributedTokenBucketScript`，跨实例一致）+ 本地 `rate.Limiter` 回退（Redis 错误→warn+本地）；键 = `user_id`（context 有则用）否则 `ip:<ClientIP>`，再拼 `:METHOD:路由模板`（`normalizeRateLimitRoutePath` 带 GW-P3-1 键逃逸防护）。挂载点：api 组 15/30、auth 5/15、admin 10/min、internal 60/120、galaxy 10/20、**ws/ticket 签发口 `cfg.WSTicketRateRPS`(2.0)/`burst`(5)**。
- 指标齐全：`sparkle_rate_limiter_redis_fallback_total`、`rate_limiter_rejections_total{reason}` 等。

### 1.4 死代码死因（D6 实锤复核）

`WebSocketRateLimitMiddleware`（rate_limit.go:400-426）+ `UserBasedRateLimit`/`AdaptiveRateLimitMiddleware`/`DefaultRateLimitMiddleware`/`AuthRateLimitMiddleware`/`GlobalRateLimitConfig` 全库 grep 仅定义处，**从未被任何路由引用**。死因三层（直接接线也不行，不只是忘了挂）：
1. **本地内存 only**：`RateLimiter.visitors` 是进程内 map，多副本部署不一致（k8s/base/gateway.yaml 意图为多副本）；现行体系已整体迁到 hybrid Redis 版。
2. **per-IP 键 + 硬编码阈值**：`WebSocketConnectionsPerMinute=5/60 per sec, burst=10` 写死在 `GlobalRateLimitConfig`，无 env 通道；per-IP 直连限流在校园网/宿舍 NAT（几百设备共享出口）下会成片误杀——这正是审计建议钉签发口的动机。
3. **钉位错误**：即使挂上，它挡的是已花掉 TCP+TLS+jwt.Parse 成本之后的请求；对「合法签名 JWT 洪水打 Redis 认证」这最大放大器，应该在**进认证前**挡。

### 1.5 已存在的 ticket 基建（重要发现：不是从零开始）

| 件 | 现状 | 位置 |
|---|---|---|
| 签发口 | `POST /api/v1/ws/ticket`：authMiddleware（JWT）→ HybridRateLimit(cfg.WSTicketRateRPS=2.0, burst=5) → uuid → Redis `SET ws:ticket:<uuid> {user_id, token} TTL=WS_TICKET_TTL_SECONDS(默认 120s)` | `handler/ws_ticket.go`；setup.go:573-578 |
| 核销 | Redis Lua `GET+DEL` 原子 → **单次有效、防重放天然成立**；TTL 由 Redis 单时钟管理 | `middleware/ws_auth.go:20-26,101` |
| 客户端（chat） | **已实现**：POST /ws/ticket → `?ticket=` 携带 + 失败回退 Authorization 头 | `mobile/.../websocket_chat_service_v2.dart:1709-1750,1830-1846` |
| 指标 | `ws_ticket_issued_total` / `ws_ticket_consume_success_total` / `ws_ticket_consume_failure_total{reason}` | `metrics/ws_metrics.go:10-25` |
| 测试 | `ws_ticket_test.go` 3 例（无 ctx 401 / nil Redis 503 / 签发需认证） | handler 包 |
| subprotocol 通道 | 网关解析 + chat/files 已做 upgrader echo | `websocket_factory.go:78-103` |

**但当前生产形态下 ticket 是死配置**，四个缺口：
1. ticket 只是第③顺位 fallback，JWT 直连全量接受 → 5 入口可被无限打握手（D6 主窟窿）。
2. **生产 query-ticket 被连坐禁掉**：`?ticket=` 与 `?token=` 共用 `ALLOW_WS_QUERY_TOKEN` 开关（生产强制 false）→ mobile chat 的 ticket 在生产被网关无视、静默退化为 Bearer 头，签发口白限流。
3. **mobile STT 把原始 JWT 放 `?token=`**（`audio_recording_service.dart:55`）→ 生产必然 401（潜伏 bug：STT 语音输入在生产不可用）。
4. mobile community 两入口直连 Bearer（`community_websocket_service.dart:241-242,307-308`），无 ticket 流。

### 1.6 现状图

```
                      未认证 IP / 假 JWT 洪水
                              │
   ┌──────────────────────────▼─────────────────────────────┐
   │ gin 根引擎（otelgin/I18n/ctx/sec/CORS —— 无限流）        │
   │   /ws/chat /ws/files /ws/stt /community×2 ←── 5 入口裸奔 │
   │     └─ WsAuthMiddleware：jwt.Parse(CPU) → Redis×2(放大器) │
   │   /api/v1 组 ── apiRateLimit(键=ip:*,认证前) 15/30        │
   │     └─ POST /ws/ticket ── authJWT ── ticket限流(键=user)  │
   │            2rps/burst5 ←── 生产的限流钉在没人用的路上      │
   └────────────────────────────────────────────────────────┘
```

---

## 二、方案设计

### 2.1 双钉限流架构（签发口为主钉 + 握手口 pre-auth 兜底钉）

审计建议「限流钉在签发口、避免 per-IP 直连限流 NAT 误杀」成立，但单钉不够：签发口只保护「拿着合法 JWT 来换票的人」，挡不住无凭据/假 JWT 直接打 WS 路由的洪水。因此两层各司其职：

| 钉位 | 位置 | 键口径 | 形制 | 挡什么 | 成本模型 |
|---|---|---|---|---|---|
| **主钉：签发口** | `POST /api/v1/ws/ticket`，authMiddleware **之后**（现状已挂，调阈值即可） | **per-user**（`user_id:POST:/api/v1/ws/ticket`） | hybrid token bucket（现状） | 单账号开连接的速率 = 连接洪水限到人；NAT 天然免疫 | 已认证请求，1 Redis eval |
| **兜底钉：握手口** | 5 条 WS 路由 `WsAuthMiddleware` **之前**（新增） | **per-IP** | hybrid token bucket（`HybridRateLimitMiddlewareSimple`，全库现行标准形制，Redis 挂→本地回退） | 未认证洪水在 TCP/TLS 之后、`jwt.Parse`/Redis 之前被 429 | Redis eval ×1 |
| （既有）api 组兜底 | `/ws/ticket` 在 api 组内已被 apiRateLimit 覆盖（键=ip:*,15/30，因认证在组中间件之后） | per-IP | 已在 | 签发口自身被无凭据洪打 | 无需改动 |

**为什么兜底钉的 NAT 误杀可接受**：兜底阈值只需盖住「合法客户端的 reconnect 风暴」，不需要盖住正常连接频率。mobile chat 重连预算 = 6 次退避（0.8s→12.2s，`websocket_chat_service_v2.dart:1344-1352`）；community 走 proxy 侧已有 per-user 10/30s 跟踪。最坏合理场景是一个宿舍 NAT 出口 200 台设备同时网络抖动：200×6=1200 次/分钟 = 20rps 均值。默认建议 **30 rps 持续 / burst 60**（token bucket）：NAT 风暴均值 20rps 畅通、瞬时 60 发不掐，而攻击者 100rps+ 的洪水从第 1 秒起就被钳到 30rps 桶速。且必须 env 可调（`WS_UPGRADE_RATE_*`）+ 429 带 `Retry-After`。对比死代码的 5/min/IP：那才会误杀（一个用户重连一次就烧掉预算的 1/5）。

**per-user 握手限流要不要**：不需要单独一层——ticket-first 迁移完成后，「认证用户建新连接」必须先过签发口 2rps/burst5（主钉），等价于 per-user 握手限流，不重复建。

### 2.2 票据结构定稿（保持 opaque-Redis，不引入签名票）

现状票据已是合理选型，**建议维持**，理由与强化：

| 维度 | 现状（opaque uuid + Redis） | 评估 |
|---|---|---|
| 防伪造 | 128-bit uuid 不可猜 + 服务端存储即真相源 | 足够。签名票（HMAC self-contained）**并不省事**：单次核销仍需 Redis GETDEL，否则 TTL 窗口内可重放；省掉的那次签发侧 Redis SET 换来的是「吊销困难+需要签名基础设施+时钟问题」，负收益 |
| 防重放 | Lua GET+DEL 原子核销，第二次必 401 | 已成立，压测口径见 §6 |
| 单次核销存储 | Redis `ws:ticket:<uuid>`，TTL=120s（默认） | 已成立。**附带红利：ticket 存 Redis 跨重启存活**——滚动发布前签的票在重启后仍可核销，客户端重连无缝（与 wt275 排空配合好） |
| 时钟漂移 | **不适用**：TTL 是 Redis 单时钟，签发/核销两端无时钟依赖 | 风险表降级为「客户端 expires_in 余量处理」 |
| payload | `{user_id, token(原始 JWT)}` | `token` 字段是**承载性的**：chat 转发引擎 gRPC、stt/proxy 转发 Python 都要 `auth_token`（`chat_orchestrator.go:328`、`stt_handler.go:134`、`websocket_proxy.go:151,179`），网关无法从 user_id 反推。保留；缓解见风险表 R3（TTL 有界 120s+单次核销+Redis 本就是黑名单/会话信任域） |
| TTL 配置 | 默认 120s；`.env.example` 写 3600s（**不当示范**，1 小时单次票=把 query 泄露窗口放大 30 倍） | 建议 config clamp：>300s 时启动告警或拒绝；示例文件改回 120s |

### 2.3 query-ticket 与 query-token 解耦（本设计的第一个关键闸门）

- 新增 `ALLOW_WS_QUERY_TICKET`（默认 **true**，生产也放行）：`extractWSTicket` 的 allowQuery 参数改读此开关；`?token=` 维持 `ALLOW_WS_QUERY_TOKEN`（生产禁）。
- 论证：`?ticket=` 泄露面（代理日志/历史记录里出现一个 120s 内单次有效的 opaque 串）≪ `?token=`（长寿 JWT）。浏览器 WS 无法带自定义头，此闸门同时是 web 端唯一可行通道。
- 效果：mobile chat 已写好的 ticket 流**在生产立即生效**（改动=一行配置+一个中间件参数）。

### 2.4 未认证握手的最小拒绝成本（目标链）

```
洪水打 /ws/chat
  → [新] pre-auth per-IP token bucket 限流：429 + Retry-After（jwt.Parse/Redis 之前）
  → WsAuthMiddleware：无凭据/坏 JWT → 401（便宜路径）
  → 合法签名 JWT → validateJWT（RS256 + Redis×2，fail-closed）
  → ticket 核销（Redis GETDEL ×1）
```

迁移完成态（`WS_TICKET_REQUIRED=true`）下合法路径成本从「RS256+Redis×2」降为「Redis GETDEL×1」，**认证面 Redis 压力减半**；未认证流量 100% 停在第一层。

### 2.5 五入口增量迁移路径（可增量，顺序有依据）

| 顺序 | 入口 | 理由 |
|---|---|---|
| P1 | 全部 5 条（限流层） | pre-auth 限流是纯网关侧新增，客户端零感知，立即闭合 D6 |
| P2 | `/ws/chat` | mobile 已实现 ticket 流，只差 §2.3 闸门打开；流量最大、收益最大 |
| P3 | `/ws/stt`、`/ws/files` | **stt 顺手修生产 401 潜伏 bug**（`?token=`→ticket）；files 移动端暂无 WS 消费方（grep 无 `ws/files` 客户端），网关侧改完即完；补 stt upgrader 的 subprotocol echo 对齐 chat/files |
| P4 | community 两入口 | mobile 需新增签发+携带代码（S 卡）；proxy 侧 per-user 重连跟踪保留，与其正交 |
| P5 | `WS_TICKET_REQUIRED` 收紧 | 可选硬ening：开关打开后 WsAuth 跳过 ①② 只走 ③；等强制更新覆盖后翻转 |

### 2.6 与 wt275 停机排空（wsConnDrainGroup）的交互

- **信号分层**：draining 中 handler 拒升级=**503**（已有），限流拒绝=**429**（新增）。两者语义不同，客户端重试策略应区分：503 → 长退避（实例在下线）；429 → 按 Retry-After。
- **顺序**：限流中间件在 auth 前、drain 检查在 handler 内 → draining 实例上被 503 的握手也会先消耗一次 per-IP 预算。可接受（预算盖重连风暴 150 倍），不做 drain 感知限流豁免（复杂度不值）。
- **签发口在 draining 时**：不强制 503——ticket 是 Redis 态，发布窗口前签的票重启后仍可核销，**照常签发反而让滚动发布更平滑**（作为设计注记，不做改动）。
- **核销失败与排空无耦合**：`wsConnDrainGroup.startTracking` 只管升级后的 conn，票务/限流均在升级前，互不进入对方路径。

---

## 三、API / 协议草案（现状为基线的增量）

### 3.1 REST 签发口（不变更响应契约，仅文档化 + 两处收紧）

```
POST /api/v1/ws/ticket          （api 组内：apiRateLimit[ip,15/30] → authJWT → ticketLimit[user,默认上调 5rps/burst10]）
→ 200 {"ticket":"<uuid>","expires_in":120,"token_type":"ws_ticket"}
→ 401 missing/invalid user context      （未认证）
→ 429 rate_limit_exceeded + Retry-After （per-user 签发超频）
→ 500/503 ticket service unavailable    （Redis 故障；签发 fail-fast，不发不可核销的票）
```

收紧项：① `WS_TICKET_RATE_RPS/BURST` 默认 2.0/5 → **5/10**（多端登录+重连风暴数学见 §5-R2）；② TTL clamp（>300s 启动警告）；③ 响应可选新增 `"endpoint_hint"`（不需要，弃）。

### 3.2 WS 握手携带协议（优先级即迁移完成态）

| 优先 | 方式 | 载体 | 适用端 | 配置门 |
|---|---|---|---|---|
| 1 | `GET /ws/chat?ticket=<uuid>` | query | Flutter 原生（现状 chat 已用）、STT（迁移后） | `ALLOW_WS_QUERY_TICKET`（新，默认 true，生产放行） |
| 2 | `Sec-WebSocket-Protocol: ticket,<uuid>（或 ticket=<uuid>）` | subprotocol | Web/浏览器（不能带头的场景） | 无门，网关已解析；chat/files 已 echo，**stt 需补 echo** |
| 3 | `Authorization: Bearer <JWT>` | header | 迁移过渡期全部客户端（`WS_TICKET_REQUIRED=false` 时） | 收紧开关翻转后移除 |

移动端规约：`expires_in - 5s` 内视为不可用；429/401 时读 `Retry-After`/错误码走既有退避表；**ticket 签发成功后保留 Authorization 头一个版本周期**（网关未收紧前双带无害，收紧后自然由服务端裁决）。

### 3.3 新增配置面（全部 env，viper）

```
WS_UPGRADE_RATE_RPS        默认 30.0   # 兜底钉 per-IP token bucket 持续速率（5 条 WS 路由共享一个限流器实例）
WS_UPGRADE_RATE_BURST      默认 60     # token bucket 突发容量
ALLOW_WS_QUERY_TICKET      默认 true   # 生产放行 ?ticket=；?token= 仍由 ALLOW_WS_QUERY_TOKEN 管（生产禁）
WS_TICKET_REQUIRED         默认 false  # per-entry 收紧开关：true 时 WsAuth 只走 ticket
WS_TICKET_TTL_SECONDS_MAX  默认 300    # TTL clamp（超限启动 Fatal，示例文件 3600 是坏示范）
```

### 3.4 新增指标

```
ws_upgrade_limited_total{endpoint}              # 兜底钉 429 计数（压测口径主指标）
ws_upgrade_admission_duration_seconds{result}   # pre-auth 限流层耗时直方图（证明拒绝成本最小化）
（复用既有）ws_connection_{success,error}_total{endpoint,auth_method,reason}、ws_ticket_*
```

---

## 四、迁移分步（实施顺序）

```
Step 0  （无依赖，先行合入即闭合 D6 主窟窿）
  网关：5 条 WS 路由前置 pre-auth per-IP hybrid token bucket 限流 + ws_upgrade_limited_total + 单测
        （本地回退语义继承 HybridRateLimitMiddlewareSimple；Redis 挂→本地，仍挡洪水）
Step 1  query-ticket 解耦
  网关：ALLOW_WS_QUERY_TICKET 闸门 + 单测（生产口径：?ticket= 通、?token= 拒）
  验证：mobile chat 生产构建实测 ticket 生效（ws_auth_method=ticket 上报到 ws_connection_success_total）
Step 2  stt/files 网关侧
  stt：upgrader 补 subprotocol echo；（不改认证，?token= 在生产本就被拒）
Step 3  mobile stt 迁 ticket
  audio_recording_service：连接前 POST /ws/ticket，?token=$jwt → ?ticket=$ticket
        （顺手修复生产 STT 401 潜伏 bug；voice_input_button/unified_omni_bar 两调用点不动，
         token 传递链改在 service 内部换票）
Step 4  community 迁 ticket（mobile community_websocket_service 两入口 + 网关零改动）
Step 5  （可选收紧，强制更新覆盖后）WS_TICKET_REQUIRED 灰度翻转 + 死代码清理
  删 rate_limit.go 死函数群（WebSocketRateLimitMiddleware/UserBasedRateLimit/
  AdaptiveRateLimitMiddleware/DefaultRateLimitMiddleware/AuthRateLimitMiddleware/GlobalRateLimitConfig）
```

每步独立可交付、可独立回滚（Step 0/1 纯网关配置+中间件，客户端零改动）。

---

## 五、风险表

| # | 风险 | 概率×影响 | 缓解 | 残余风险 |
|---|---|---|---|---|
| R1 | **NAT 共享出口误杀**（宿舍/校园网同出口 IP 多设备；兜底钉是 per-IP） | 中×高 | 阈值按最坏合理风暴留量：200 设备同时重连 = 20rps 均值 < 30rps 桶速、瞬时 < burst60；env 可调；429 带 Retry-After；`ws_upgrade_limited_total` 按 endpoint 告警阈值设在「持续 >0 且伴随正常连接成功率下降」 | NAT 后单 IP 定向洪水仍会被全出口连坐——接受（洪水本来就该连坐） |
| R2 | **多端登录/重连风暴被主钉限流**（手机+平板+Web 三端，网络抖动各 6 连击 = 18 次/分钟 > 现默认 burst5） | 中×中 | 签发口默认上调 5rps/burst10（60/min）；客户端尊重 Retry-After 并走既有退避表；签发 429 不烧 ticket（签发失败无副作用） | 极端场景用户晚几秒重连 |
| R3 | **ticket payload 携带原始 JWT 的 Redis 暴露面** | 低×中 | TTL 120s + 单次核销把窗口压到分钟级；Redis 已是 token 黑名单/会话存储信任域（同等暴露）；TTL clamp 拒绝 3600s 式配置 | Redis 被攻破时暴露的是本就在 Redis/DB 的同级信息 |
| R4 | **旧版本 App 兼容**（ticket-required 收紧会杀旧客户端 WS） | 高×高（若翻转过快） | P5 为可选步且排最后；`WS_TICKET_REQUIRED=false` 期间 JWT 直连保留；翻转前核对 mobile 版本分布（强制更新覆盖） | 收紧开关永不翻转也只是维持现状 |
| R5 | **Redis 故障 fail 语义**：签发 503、核销 err→401；Redis 抖动=全员无法建新连接 | 低×中 | 与生产 JWT fail-closed（RedisFailClosed=true）语义一致，不是新增单点；兜底钉 Redis 挂→本地回退仍限流；告警沿用 sparkle_rate_limiter_redis_fallback_total | 接受（与现状认证可用性等价） |
| R6 | 时钟漂移 | — | **不适用**：TTL 为 Redis 单时钟；仅需客户端 `expires_in-5s` 余量规约 | 无 |
| R7 | subprotocol 通道与 community `protocols:['json']` 冲突 | 低×低 | `extractWSTicket` 逐段解析，`ticket` 段与 `json` 段可共存；upgrader echo 取 selectWebSocketSubprotocol 首个匹配段 | 无 |

---

## 六、验收标准

### 6.1 功能验收（定向单测 + API 级 E2E）

1. 未认证（无凭据）打 5 条 WS 路由 → 401，且 `ws_upgrade_limited_total` 不增长、无 Redis 认证调用（可用 miniredis 计数断言）。
2. 生产口径：`ALLOW_WS_QUERY_TOKEN=false, ALLOW_WS_QUERY_TICKET=true` 下，`?token=` 401、`?ticket=`（有效票）升级成功。
3. 单次核销：同 ticket 第二次握手 100% 401（`ws_ticket_consume_failure_total{reason="invalid_or_expired"}` +1）。
4. TTL：签发 `expires_in` 后 +1s 握手 401；TTL 配置 3600 → 启动 Fatal。
5. per-user 签发限流：单账号第 burst+1 次 POST /ws/ticket → 429 + Retry-After。
6. draining（wt275 回归）：draining 中握手 503（非 429），存量 conn 收 1001 close frame（既有 ws_shutdown_drain_test 4 例保持绿）。
7. hybrid 回退：Redis 停机时兜底钉仍以本地 token bucket 拒绝超频（既有本地回退路径单测）。

### 6.2 压测口径（验收核心：未认证 IP 打握手被挡的比例）

> 被挡率是注入速率的函数：token bucket 预算 = burst60 + 30rps×时长。S1 的判定写「达到理论钳制的比例」而非拍脑袋 99%，避免阈值内部矛盾。

| 场景 | 注入 | 判定 |
|---|---|---|
| S1 未认证洪水（主验收） | 单 IP，100 conn/s × 60s（共 6000）打 `/ws/chat`，三种载荷各 1/3：无凭据 / 垃圾 JWT / **合法签名假 JWT** | ① **升级成功率 = 0%**；② 429 率 ≥ 理论钳制值 (6000−60−1800)/6000 = 69% 的 95%（即实测 ≥65.6%，证明桶速/桶容实现与配置一致）；③ 穿透进认证层的速率被钳在 ≤31 rps（对比无限流基线 100 rps，Redis 认证 QPS 增幅按穿透量计，相对降幅 ≥69%）；④ 第二档注入 1000 conn/s × 60s 时 429 率 ≥96.9%（同公式），网关 p99 CPU 增幅 <20% |
| S2 单账号签发洪打 | 1 账号 50 rps POST /ws/ticket | burst 外 100% 429；用其签到的票全部可正常建连（不误伤未超频部分） |
| S3 NAT 不误杀 | 模拟宿舍 NAT：50 认证用户共享出口 IP，各自正常节奏建连（人均 2 conn/分钟）；洪水来自另一独立 IP | 50 用户全程 0 次 429/401 异常；洪水 IP 按 S1 口径被钳 |
| S4 重连风暴 | 100 认证客户端（分布多 IP）同时断网 30s 恢复，各自 6 连击退避（约 600 票+600 握手 / 30s = 20rps 均值） | 0 429；全部在 15s 内重连成功（20rps < 30rps 桶速、瞬时并发 < burst60） |
| S5 滚动发布 | 500 live conn 中触发 drain（wt275 场景）+ 客户端重连 | 1001 close frame 收到率 100%；重连 429 率 0；发布窗口前签发 ticket 重连可用率 100%（Redis 态跨重启） |

指标源：`ws_upgrade_limited_total` / `rate_limiter_rejections_total{reason}` / `ws_ticket_*` / `ws_connection_*`；压测工具用仓库既有 API 级 E2E 通道（tests_e2e）+ gorilla 客户端脚本，**不跑全库测试**（资源纪律）。

---

## 七、实施卡面拆分（S/M 粒度，供主会话派卡）

| 卡 | 粒度 | 内容 | 依赖 | 验证 |
|---|---|---|---|---|
| WSQ-1 | **S** | 兜底钉：5 条 WS 路由 pre-auth per-IP hybrid token bucket 限流 + `WS_UPGRADE_RATE_*` 配置 + 指标 + 单测（=§四 Step 0，合入即闭合 D6 主窟窿） | 无 | §6.1-1/7、§6.2-S1/S3 |
| WSQ-2 | **S** | `ALLOW_WS_QUERY_TICKET` 解耦闸门 + TTL clamp + `.env.example` TTL 修正 + 签发口默认阈值上调 5/10（=§四 Step 1+§2.2 收紧） | 无（可与 WSQ-1 并行） | §6.1-2/4/5 |
| WSQ-3 | **S** | stt upgrader subprotocol echo 补齐（对齐 chat/files） | 无 | 定向单测 |
| WSQ-4 | **M** | mobile STT 迁 ticket（audio_recording_service 换票逻辑；顺带修复生产 STT 401 潜伏 bug）+ API 级 E2E | WSQ-2 | §6.1-2、真机语音输入回归 |
| WSQ-5 | **S** | mobile community 两入口迁 ticket（community_websocket_service 签发+携带） | WSQ-2 | §6.1-3、community 冒烟 |
| WSQ-6 | **M** | 压测卡：S1-S5 五场景脚本 + 基线数据 + `ws_upgrade_limited_total` 告警阈值提案 | WSQ-1/2 | §6.2 全表 |
| WSQ-7 | **S**（可选） | `WS_TICKET_REQUIRED` 收紧开关（WsAuth 只走 ticket）+ 死代码清理（rate_limit.go 死函数群 + GlobalRateLimitConfig） | WSQ-4/5 合入 + 版本覆盖确认 | §6.1 全表回归 |

排序建议：WSQ-1/2/3 同批（纯网关、互不依赖、合计约等于一个 M）；WSQ-4/5 随 mobile 批次；WSQ-6 在 1/2 合入后；WSQ-7 观察一轮再定。

---

## 附录 A：ticket 签发-核销时序验证脚本（原型，不入产品路径）

> 用途：无 Docker 环境下对「签发→单次核销→重放拒绝→TTL 过期」四步做最小闭环验证。依赖：curl + redis-cli + 一个网关实例（或 miniredis 等价物）。验证逻辑与 ws_ticket.go/ws_auth.go 的 Redis 协议一致（`ws:ticket:` 前缀、JSON payload、GETDEL 语义）。

```bash
#!/usr/bin/env bash
# ws_ticket_proto_check.sh — 放 /tmp 自清，禁止入库产品路径
set -euo pipefail
REDIS=${REDIS:-redis-cli}
TICKET="$(uuidgen | tr 'A-Z' 'a-z')"
KEY="ws:ticket:${TICKET}"

# 1) 模拟签发口写入（真实路径 = POST /api/v1/ws/ticket）
$REDIS SET "$KEY" '{"user_id":"proto-user","token":"proto-jwt"}' EX 2

# 2) 模拟网关核销（真实路径 = wsTicketGetDel Lua：GET+DEL 原子）
PAYLOAD=$($REDIS GET "$KEY"); $REDIS DEL "$KEY" >/dev/null
echo "consume#1 => ${PAYLOAD:-<nil>}（期望 JSON payload）"

# 3) 重放（单次核销验收）
PAYLOAD2=$($REDIS --raw GET "$KEY"); $REDIS DEL "$KEY" >/dev/null
[ -z "$PAYLOAD2" ] && echo "replay => <nil>（期望 nil，单次核销成立）" || { echo "replay LEAK"; exit 1; }

# 4) TTL 过期
$REDIS SET "ws:ticket:expired-proto" '{"user_id":"x"}' EX 1; sleep 2
[ -z "$($REDIS --raw GET ws:ticket:expired-proto)" ] && echo "ttl => expired（期望 expired）"
echo "PROTO CHECK DONE"
```

## 附录 B：现状证据索引（文件:行）

| 结论 | 证据 |
|---|---|
| 5 条 WS 路由仅挂 WsAuth、在 api 组限流之外 | `backend/gateway/cmd/server/setup.go:498-507,567-570` |
| 签发口已存在且挂 per-user hybrid 限流 | `setup.go:573-578`；`internal/handler/ws_ticket.go` |
| 认证链三顺位（JWT 头→query token→ticket）、GETDEL 原子核销、query 连坐开关 | `internal/middleware/ws_auth.go:48-141,152-180` |
| 生产强制 ALLOW_WS_QUERY_TOKEN=false | `internal/config/config.go:708-712,767-769`；`docker-compose.prod.yml:142` |
| validateJWT 成本（RS256 + Redis 黑名单×2 + fail-closed） | `internal/middleware/auth.go:490-620` |
| 死代码（定义即全部引用） | `internal/middleware/rate_limit.go:216-252,284-344,399-426` |
| 活限流形制（hybrid token bucket/滑窗 + per-user/ip 键 + GW-P3-1 键防护） | `internal/middleware/rate_limit.go:435-556`；`distributed_rate_limiter.go:47-108,303-340` |
| chat 连接上限（2000 全局/2 per-user） | `internal/config/config.go:549-550`；`internal/handler/ws_registry.go:58-76` |
| wt275 排空件（wsConnDrainGroup / ProxyDrainAll，draining 拒升级） | `internal/handler/ws_registry.go:283-412`；`stt_handler.go:86-89`；`websocket_proxy.go:125,741-756` |
| mobile chat ticket 流（已实现） | `mobile/lib/features/chat/data/services/websocket_chat_service_v2.dart:1709-1750,1830-1846` |
| mobile STT query JWT（生产 401 潜伏 bug） | `mobile/lib/features/chat/data/services/audio_recording_service.dart:52-56` |
| mobile community 直连 Bearer | `mobile/lib/features/community/data/services/community_websocket_service.dart:222-242,289-308` |
| subprotocol 解析/echo（chat、files 有，stt 无） | `internal/handler/websocket_factory.go:78-103`；`chat_orchestrator.go:247-248`；`file_events.go:79`；`stt_handler.go:41-47` |
| 票据/连接指标 | `internal/metrics/ws_metrics.go:10-33,159-198` |
| ticket 配置默认值 | `internal/config/config.go:542-550,602-608` |
