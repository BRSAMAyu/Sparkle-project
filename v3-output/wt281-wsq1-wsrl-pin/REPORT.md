# wt281-wsq1-wsrl-pin — WSQ-1 兜底钉：5 条 WS 路由 pre-auth per-IP token bucket 限流

> 2026-09-24。C 线·网关安全 WSQ-1（S 级）。上游：v3-output/WS-TICKET-DESIGN/REPORT.md §2.1/§3.3/§四 Step 0。
> 分支 `wt281-wsq1-wsrl-pin`（本地 commit，未 push）。合入即闭合 wt275 缺陷 D6 主窟窿。

## ① 实现摘要（file:line）

**新文件**

- `backend/gateway/internal/middleware/ws_upgrade_rate_limit.go:28` — `WSUpgradeRateLimitMiddleware(rdb, rps, burst)`：形制复刻现行标准 `HybridRateLimitMiddlewareSimple`（Redis Lua token bucket `DistributedRateLimiter` 跨实例一致 + Redis 错误→本地 `rate.Limiter` 回退，回退时 warn 日志）。键恒为 `ip:<ClientIP>`（pre-auth 无用户态，空 IP 落 `unknown`）；`wsUpgradeRateLimitKeyPrefix="wsupgrade"`（ws_upgrade_rate_limit.go:19）与 per-route hybrid 键（`ratelimit:*:METHOD:路由`）命名空间隔离。拒绝→429 + `Retry-After` 头 + JSON 体（`error`/`message`/`retry_after`，头体同值）+ `ws_upgrade_limited_total{endpoint}` 计数。
- `backend/gateway/internal/middleware/ws_upgrade_rate_limit.go:97` — `wsUpgradeRetryAfterSeconds`：按 `(1-remaining)/rate` 向上取整、下限 1s（杜绝 `Retry-After: 0`）。

**修改**

- `backend/gateway/cmd/server/setup.go:498-516` — 一个共享中间件实例（`cfg.WSUpgradeRateRPS/BURST`）钉在全部 5 条 WS 路由 `WsAuthMiddleware` 之前：`/ws/chat`、`/ws/files`、`/ws/stt`、`/api/v1/community/groups/:group_id/ws`、`/api/v1/community/ws/connect`。共享实例=五入口单一 per-IP 预算，换入口不能绕过（报告 §3.3「共享一个限流器实例」）。
- `backend/gateway/internal/config/config.go:62-63`（结构体）、`:471-472`（envKeys 绑定）、`:547-554`（默认值 30.0/60 + NAT 预算注释）— 新配置 `WS_UPGRADE_RATE_RPS`（默认 30.0）/`WS_UPGRADE_RATE_BURST`（默认 60），名字与报告 §3.3 一致。
- `backend/gateway/internal/metrics/ws_metrics.go:34-41` — 新指标 `ws_upgrade_limited_total{endpoint}`（报告 §3.4；§6.2-S1 压测主指标，WSQ-6 直接消费）。
- `backend/gateway/.env.example:35-38` — 两键登记 + 用途注释（§2.1 兜底钉说明）。

**测试**

- `backend/gateway/internal/middleware/ws_upgrade_rate_limit_test.go` — 7 例：阈值内放行（burst 内全 200）；超阈 429+`Retry-After`≥1s+体表一致；五路由共享预算（打满两个入口后第三入口仍 429）；per-IP 隔离；钉位序（预算外 429 先于 WsAuth、预算内照常 401 missing_credentials）；**已认证正常握手穿过钉层到 handler（`ws_auth_method=jwt_header`）不受影响**；Retry-After 估算函数边界。
- `backend/gateway/internal/config/config_ws_upgrade_test.go` — 2 例：默认 30/60；env 覆盖 7.5/13 生效（`viper.Reset`+`t.Setenv`，自包含不依赖 .env）。

**刻意不做**（与报告/卡面口径对齐）

- 不做 per-user 握手限流（§2.1：ticket-first 后签发口主钉即等价）；
- 不加 `ws_upgrade_admission_duration_seconds` 直方图（§四 Step 0 只点名 `ws_upgrade_limited_total`；WSQ-6 压测卡若需可一行补上）；
- `config.go` 整文件 gofmt 不齐为**预存**（主仓同文件同样不过 gofmt，字段间注释切断对齐组所致）；本卡新增行与邻行列对齐一致，不整文件重排以免 diff 膨胀撞其他在飞卡。

## ② 测试结果（原样）

```
$ CGO_ENABLED=0 go test -run 'TestWSUpgrade|TestLoadWSUpgrade' -v ./internal/middleware/ ./internal/config/
--- PASS: TestWSUpgradeRetryAfterSeconds (0.00s)
--- PASS: TestWSUpgradeRateLimit_AllowsWithinBurst (0.00s)
--- PASS: TestWSUpgradeRateLimit_RejectsBeforeAuthWhenExhausted (0.00s)
--- PASS: TestWSUpgradeRateLimit_SharedBudgetAcrossFiveRoutes (0.00s)
--- PASS: TestWSUpgradeRateLimit_AuthenticatedHandshakeUnaffected (0.00s)
--- PASS: TestWSUpgradeRateLimit_PerIPBudgetIsolation (0.00s)
--- PASS: TestWSUpgradeRateLimit_RejectsOverBurstWithRetryAfter (0.00s)
PASS  ok github.com/sparkle/gateway/internal/middleware (cached)
--- PASS: TestLoadWSUpgradeRateDefaults (0.00s)
--- PASS: TestLoadWSUpgradeRateEnvOverride (0.00s)
PASS  ok github.com/sparkle/gateway/internal/config 0.507s
```

改动三包全量回归（middleware 8.1s 含全部既有 rate_limit/ws_auth/auth 测试；cmd/server 0.97s 含 setup/drain 测试）：

```
$ CGO_ENABLED=0 JWT_SECRET=... go test ./internal/middleware/ ./internal/config/ ./cmd/server/
ok  github.com/sparkle/gateway/internal/middleware  (cached)
ok  github.com/sparkle/gateway/internal/config     0.514s
ok  github.com/sparkle/gateway/cmd/server          (cached)
```

**环境注记（非本卡引入）**：worktree 无 `.env`（不入库、不随 worktree 传播），`config.Load()` 对缺失 `JWT_SECRET` 直接 Fatal——导致 config 包在不设该 env 时整包 FAIL（预存 rbac 测试同样中招，主仓有 `.env` 故不复现）。合入主仓后无此问题；CI 若无 `.env` 需注意该预存坑。

## ③ build/vet 结果

```
$ CGO_ENABLED=0 go build ./...   → BUILD_OK（无输出）
$ CGO_ENABLED=0 go vet ./...     → VET_OK（无输出）
```

golangci-lint（已装）：改动文件零告警；仅两条**预存**问题与本次无关——`cmd/server/main.go:100` errcheck（`chatPersister.Run` 未检错，未动该文件）、`internal/config/config.go:82` gofmt（见上）。

## ④ 资源峰值

全程 LIGHT：无模拟器/Gradle/浏览器；`go build`+`go vet`+三包定向测试，单进程 go 编译常规水平、测试段 wall <15s。/tmp 自产物：无（主仓 `gen/` 目录以**拷贝**方式进 worktree 的 `backend/gateway/gen/`，gitignored，随 worktree 生命周期回收）。内存纪律（swap/load 门）未触发 HEAVY。

## ⑤ WSQ-2+ 交接建议

1. **WSQ-2（可立即并行）**：`ALLOW_WS_QUERY_TICKET` 闸门 + TTL clamp + 签发口默认上调 5/10。落点：`middleware/ws_auth.go:90`（`extractWSTicket(c, cfg.AllowWsQueryToken)` 的 allowQuery 参数换读新开关）、`config.go` 生产 Fatal 段旁新增开关、`handler/ws_ticket.go`。与本卡仅 config.go 同文件不同区块，建议 WSQ-2 rebase 本卡。
2. **WSQ-3**：stt upgrader subprotocol echo（`stt_handler.go:41-47`），独立无冲突。
3. **WSQ-6 压测**：`ws_upgrade_limited_total{endpoint}` 已就位；S1 判定公式 (6000−60−1800)/6000 的钳制数学依赖本卡实现语义（bucket 初满、429 后余量递补），压测脚本直接对 `/ws/chat` 打即可，无需 mock。若需「拒绝成本最小化」证明，可在本卡 `ws_upgrade_rate_limit.go` 的 Allow 调用处补 `ws_upgrade_admission_duration_seconds{result}` 直方图（§3.4 预留，约 5 行）。
4. **WSQ-7 死代码清理**：本卡新文件独立于 `rate_limit.go`，届时删 `WebSocketRateLimitMiddleware`/`GlobalRateLimitConfig` 等死函数群不影响兜底钉。
5. **合入注意**：`internal/config/config.go` 是多卡热点文件（WSQ-2 也要动）；建议 Leader 合入窗口按 WSQ-1→WSQ-2 串行 apply，`--3way` 冲突预期在 envKeys 数组与 SetDefault 两处相邻行。
