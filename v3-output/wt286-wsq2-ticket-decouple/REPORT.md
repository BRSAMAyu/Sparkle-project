# wt286-wsq2-ticket-decouple — WSQ-2：query-ticket 解耦闸门 + TTL clamp + 签发口阈值上调

> 2026-09-24。C 线·网关安全 WSQ-2（S 级）。上游：v3-output/WS-TICKET-DESIGN/REPORT.md §2.2/§2.3/§3.3/§5-R2/§6.1-2/4/5（=§四 Step 1 + §2.2 收紧）。
> 分支 `wt286-wsq2-ticket-decouple`（本地 commit，未 push）。交付即分支本身（含 REPORT），无独立 changes.patch（沿 wt281 同线先例）。
> 注：本卡不动 setup.go（签发口读 `cfg.WSTicketRateRPS/BURST`，阈值改在 config 默认值层），AX route-tier 注释已由 WSQ-1 就位、无需新增。

## ① 三项落地摘要（file:line）

**a) `ALLOW_WS_QUERY_TICKET` 解耦闸门（报告 §2.3/§3.3）**

- `backend/gateway/internal/middleware/ws_auth.go:90-95` — `extractWSTicket(c, allowQuery)` 的实参从 `cfg.AllowWsQueryToken` 换成 **`cfg.AllowWsQueryTicket`**（带 WSQ-2 注释块：query 通道独立门控、subprotocol 通道不设门、`?token=` 仍归 `AllowWsQueryToken`）。当下 ticket 在生产被连坐禁用的死配置就此解死：生产口径 `ALLOW_WS_QUERY_TOKEN=false + ALLOW_WS_QUERY_TICKET=true` 下 `?ticket=` 放行、`?token=` 仍拒（§6.1-2）。
- `backend/gateway/internal/config/config.go:59`（结构体）、`:469`（envKeys 绑定）、`:555`（默认 **true**，生产也放行）— 新配置 `ALLOW_WS_QUERY_TICKET`，命名与报告 §3.3 一致。

**b) TTL clamp（报告 §2.2/§3.3/§6.1-4）**

- `backend/gateway/internal/config/config.go:61`（结构体）、`:470`（envKeys）、`:557-560`（默认 **300**）— 新配置 `WS_TICKET_TTL_SECONDS_MAX`。
- `backend/gateway/internal/config/config.go:755-760` — `Load()` 内**无条件**（含 dev）校验：`wsTicketTTLExceedsMax` 非 nil 即 `log.Fatal`（报告口径「超限启动 Fatal」；§2.2 的「告警或拒绝」两可写法取 §3.3/§6.1-4 定稿的 Fatal）。
- `backend/gateway/internal/config/config.go:806-819` — 纯函数 `wsTicketTTLExceedsMax(ttl, max)`：**含边界相等放行**（300==300 过，301 拒），报错信息同时带两个 env 名供运维定位；提纯为可测函数以免单测触发 `os.Exit`。
- `.env.example` 坏示范同步修（报告 §2.2「示例文件改回 120s」）：`backend/gateway/.env.example:36-40`（`WS_TICKET_TTL_SECONDS=120` + `WS_TICKET_TTL_SECONDS_MAX=300` + 注释点明 3600 是坏示范）；`backend/gateway/.env.local.example:35-38` 同步。生产 posture 显式化：`.env.production.example:357-359` 增 `ALLOW_WS_QUERY_TICKET=true`（默认即 true，显式登记防默认漂移）。

**c) 签发口默认阈值上调（报告 §3.3/§5-R2：2.0/5 → 5/10）**

- `backend/gateway/internal/config/config.go:561-565` — `WS_TICKET_RATE_RPS` 默认 2.0 → **5.0**、`WS_TICKET_RATE_BURST` 默认 5 → **10**（R2 数学：三端 × 6 连击 = 18 次签发/分钟，旧 burst5 直接掐死合法重连）。签发口 `setup.go:588` 读 cfg 值，零路由改动即生效。
- `.env.example:42-44` / `.env.local.example:38-39` — 示例值同步为 `WS_TICKET_RATE_RPS=5` 并**补登** `WS_TICKET_RATE_BURST=10`（原示例 `RPS=10` 且漏 burst，与任何口径都对不上）。

**测试（9 例，全绿）**

- `backend/gateway/internal/middleware/ws_auth_query_ticket_test.go`（新，3 例）— ①**开关两态**：`ALLOW_WS_QUERY_TICKET=false` 时 `?ticket=` 401 且**票不被消耗**；翻 true 后同一张票核销 200（`ws_auth_method=ticket`、payload token 透传），单次核销重放 401（miniredis 预置票）。全程 `ALLOW_WS_QUERY_TOKEN=false`，证解耦。②**生产口径**（§6.1-2）：token=false + ticket=true 下 `?token=`（有效 JWT）401、`?ticket=` 200。③闸门只盖 query 通道：subprotocol 携带（`ticket=<uuid>`）在关门态照常核销（§3.2）。
- `backend/gateway/internal/config/config_ws_ticket_test.go`（新，3 例）— ①默认口径断言（gate=true、TTL 120、MAX 300、RPS 5.0、BURST 10，且默认 TTL 过自家上限）。②**env 覆盖**：六键覆盖生效 + 上限上调后 480<600 过检。③**TTL clamp 边界**：120<300 过、300==300 过、301 拒、3600 坏示范必拒、报错含两 env 名。
- `backend/gateway/internal/config/config_rbac_test.go` — 2 例既有 `Load()` 测试补 `t.Setenv("JWT_SECRET", …)`（**预存基线缺陷**：新 worktree 无 gitignored `.env` 时这两例直接 Fatal 死掉整个包测试；沿 wt281 config_ws_upgrade_test.go 同款自包含模式修复，非本卡功能改动）。

## ② 测试结果

- 新增 6 例逐例 `-run -v` 全 PASS；`config/middleware/handler/cmd/server` 四包 `go test -count=1` 全 `ok`，exit=0。
- 回归面：既有 `ws_auth_test.go` 4 例（JWT 头/query-token 两态）不受影响（同包 ok 覆盖）；WSQ-1 的 7+2 例全部保持绿。

## ③ build / vet / lint / 守卫

- `CGO_ENABLED=0 go build ./...` ✅ ＆ `CGO_ENABLED=0 go vet ./...` ✅（gen/ 已在工作树内 `buf generate` 现场重生：Go/Dart/Python 三件套，gitignored 不入库）。
- `golangci-lint v1.64.8 run ./internal/config/... ./internal/middleware/...` ✅ 零告警（exit=0）。
- `bash scripts/run_all_rule_guards.sh` → **GUARDS-EXIT=0，83 条全过**（exit 显式捕获门住判断；完整日志 /tmp 自清）。首跑 AQ/BG 失败为**新 worktree 缺 gitignored 生成物**（`app.gen` Python 桩 / Dart 桩），补齐本地生成后复跑全绿——非代码问题。

## ④ 资源峰值

LIGHT 卡：无模拟器/Gradle/浏览器/HEAVY。峰值为本卡进程组：go build/test + buf generate + 83 条守卫（sqlite 内存库），CPU 单核为主、内存峰值 <1G、swap 零占用、无新增端口进程。/tmp 两份守卫日志收工即删；生成物留在 worktree 随其生命周期回收。

## ⑤ WSQ-3+ 交接

- **WSQ-3**（stt upgrader subprotocol echo 补齐）：落点 `internal/handler/stt_handler.go:41-47`（自建 upgrader 不 echo）；对齐 chat/files 形制（`websocket_factory.go:78-103` 的 `selectWebSocketSubprotocol`）。与本卡零耦合。
- **WSQ-4/5**（mobile stt/community 迁 ticket）依赖本卡闸门：现生产口径 `?ticket=` 已放行（默认 true，无需运维动作）；客户端侧读 `expires_in-5s` 余量 + 429/401 走退避表（§3.2 移动端规约）。stt 现状 `?token=` 仍是生产 401 潜伏 bug，迁移时顺手修。
- **运维提示**：若任何环境显式配 `WS_TICKET_TTL_SECONDS>300`，升级后**启动即 Fatal**（报错点名两个 env）——上线说明需带一句；TTL 真需放宽用 `WS_TICKET_TTL_SECONDS_MAX` 抬顶。
- **观测到的小账**（不属本卡）：①`.env.production.example:359` 的 `WS_ALLOW_QUERY_TOKEN=false` 是拼错的死键（config 读的是 `ALLOW_WS_QUERY_TOKEN`），建议 WSQ-7 清理时顺带删；②报告 §3.2 称 subprotocol 支持 `ticket,<uuid>` 双段形式，实测网关 `extractWSTicket`（ws_auth.go:157-180）只认 `ticket=/ticket:/ws-ticket=/ws-ticket:` 单段前缀，双段形式（`ticket, <uuid>`）不解析——web 端接入时按单段前缀实现，或 WSQ-7 补双段解析。
- **守卫基线注记**：config 包既有 2 例 `Load()` 测试在无 `.env` 的检出上原本就 Fatal（本卡已修）；其余卡若遇同类「config 包整包 FAIL 且只有一行 JWT_SECRET Fatal」即为同因。
