# wt301-wsq3-echo — WSQ-3：STT upgrader 子协议回显补齐（对齐 chat/files）

> 2026-09-24。C 线·网关安全 WSQ-3（S 级）。上游：v3-output/WS-TICKET-DESIGN/REPORT.md §WSQ-3（「stt upgrader subprotocol echo 补齐（对齐 chat/files）」，依赖=无）+ wt286 已合入的 WSQ-2。
> 分支 `wt301-wsq3-echo`（本地 commit，未 push）。交付即分支本身（含 REPORT），无独立 changes.patch（沿 wt281/wt286 同线先例；分支 diff 即 patch）。
> 采纳 wt286 交接口径：**网关只认单段前缀子协议**（`ticket,<uuid>` 双段实测不解析），回显实现按单段——直接复用 `selectWebSocketSubprotocol`（wt286 交接推荐的落点形制）。

## ① 实现（file:line）

- `backend/gateway/internal/handler/stt_handler.go:83-96` — `HandleWebSocket` 升级段：升级前经 `selectWebSocketSubprotocol(c.Request)`（`websocket_factory.go:78-103`，chat/files 同源）取客户端 offered 值，非空则置 `Subprotocols = []string{selected}`，gorilla 即在 101 响应回显该值（部分客户端库不回显即握手失败）。三处关键语义：
  - **单段口径与鉴权一致**：`selectWebSocketSubprotocol` 与 `middleware/ws_auth.go:157-185` 的 `extractWSTicket` 同为「按 `,` 切分后逐段前缀匹配（`ticket=`/`ticket:`/`ws-ticket=`/`ws-ticket:`…，大小写不敏感）」；多段 offer（如 `chat, ticket=<uuid>`）两边选中同一段，**回显值 ≡ 提取段**（测试 c 直接断言该一致性）。
  - **共享 upgrader 防竞态**：STT 的 upgrader 挂在 `h.upgrader` 结构体字段上跨并发连接复用（chat/files 是每请求新建，无此问题），故**先值拷贝再改副本**（`upgrader := h.upgrader`），不通过字段写入——直改字段是数据竞争，`-race` 可捕。
  - **无 offer 零扰动**：客户端不带子协议时 `selected == ""`，不置 `Subprotocols`，行为与改前逐字节一致。
- 不动 `setup.go` 路由区（零路由改动，AX route-tier 无涉）；不动 `ws_auth.go` 提取逻辑。

## ② 测试结果（3 例新增，全绿）

`backend/gateway/internal/handler/stt_subprotocol_echo_test.go`（新，3 例，真实 httptest 回环 + gorilla 客户端全握手）：

- **a) `TestSTTHandler_EchoesOfferedSubprotocol`** — 带 `Sec-WebSocket-Protocol: ticket=<uuid>` 握手 → 101 响应头与 `conn.Subprotocol()` 均逐字节回显 `ticket=<uuid>`；连接可用（读到 handler 首帧）。
- **b) `TestSTTHandler_NoOffer_NoEcho`** — 无 offer 握手 → 响应无 `Sec-WebSocket-Protocol`、协商子协议为空、升级照常成功且连接可用（**不受影响**）。
- **c) `TestSTTHandler_TicketSubprotocol_ExtractAndEchoAgree`** — **与 WSQ-2 ticket 通道端到端**：真 `WsAuthMiddleware` + miniredis 预置票，双闸门钉死（`ALLOW_WS_QUERY_TOKEN=false`、`ALLOW_WS_QUERY_TICKET=false`）仅靠单段子协议携带凭据 → ① 回显 `ticket=<uuid>`；② 票被 GETDEL 消耗（证 middleware 从**同一段**提取成功）；③ 首帧是 `STT service unavailable`（上游拨号失败）而非 `Unauthorized`（证 user_id 从票 payload 传入 handler）；④ 多段变体 `chat, ticket=<uuid2>`：回显选中前缀段而非首段，且该段即被提取消耗（**提取+回显一致**）。
- 回归面：`internal/handler`（29s）+ `internal/middleware`（9s）整包 `go test -race -count=1` 全 `ok`（含既有 `stt_handler_test.go`/`stt_origin_test.go`/WSQ-2 的 `ws_auth_query_ticket_test.go` 全部保持绿）。

## ③ build / vet / lint / 守卫

- `CGO_ENABLED=0 go build ./...` ✅ ＆ `CGO_ENABLED=0 go vet ./internal/handler/` ✅（全程 CGO_ENABLED=0）。
- `golangci-lint v1.64.8 run ./internal/handler/` → **exit=0 零告警**（改动文件过滤 grep 无输出；曾出现 bodyclose 告警，重构 helper 令 resp.body 不逃逸后清零）。
- `bash scripts/run_all_rule_guards.sh` → **GUARDS-EXIT=0，83 条全过**（exit 显式捕获）。首跑 AQ/BG 失败为新 worktree 缺 gitignored 生成物（`app.gen` Python 桩 / `mobile/lib/gen` Dart 桩——**非本卡代码问题**），按 `make proto-gen` 规范路径补齐三件套生成后复跑全绿；AX 路由守卫不涉（未动 setup.go，守卫自身跳过 `_test.go`）。
- `gofmt -l` 改动两文件无输出。

## ④ 资源峰值

LIGHT 卡：无模拟器/Gradle/浏览器/HEAVY。峰值为本卡进程组：go build/vet/test(-race) + buf generate 三件套 + dart pub global activate（**装在 `/tmp/wt301_pubcache` 隔离 PUB_CACHE，家目录零写入**）+ 83 条守卫。CPU 单核为主，内存峰值 <1G，swap 零占用，无新增常驻端口进程。收工即删：`/tmp/wt301_guards*.log`、`/tmp/wt301_pubcache`；生成物（gen/ 三目录）gitignored，留 worktree 随其生命周期回收。

## ⑤ WSQ-4/5 交接（mobile 迁 ticket）

- **服务端四条 WS 路由子协议回显现已齐**：chat（`chat_orchestrator.go:247-249`）、files（`file_events.go:79-81`）、**stt（本卡，`stt_handler.go:84-96`）**、community 走 `websocket_proxy.go:242-259`（透传后端协商）。客户端库可放心在 upgrade 请求带子协议，不会再因无回显握手失败。
- **客户端携票规约（wt286 §3.2 单段口径，本卡已验证服务端两侧一致）**：Flutter 侧用**单段前缀**——`WebSocketChannel/connect` 的 `protocols: ["ticket=<uuid>"]`（或 `ticket:` 变体）；**勿用 `ticket,<uuid>` 双段**（服务端不解析，实测确认）。多段 offer 亦可（`chat, ticket=<uuid>`），服务端选中的恰是前缀段。
- **WSQ-4（mobile STT 迁 ticket）**：`audio_recording_service` 换票逻辑接 `POST /ws/ticket`（WSQ-2 签发口，5rps/burst10）→ 拿 `ticket` 后以子协议通道（或 `?ticket=`，现生产默认放行）连 `/ws/stt`；顺带修掉现存 `?token=` 生产 401 潜伏 bug。真机语音输入回归 + API 级 E2E 建议覆盖「带子协议握手成功 + 回显头存在」两断言（本卡测试 a/c 的客户端侧镜像）。
- **WSQ-5（community 迁 ticket）**：community 代理是 TCP 级透传（`websocket_proxy.go`），子协议由后端协商透传，客户端迁票时验证 `backendConn.Subprotocol()` 透传链即可，无网关改动。
- 本卡零 DB/proto/config 改动，无迁移单头、无 env 新键，合入后无需运维动作。
