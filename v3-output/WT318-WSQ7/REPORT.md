# WT318-WSQ7 — WS_TICKET_REQUIRED 收紧开关 + 死代码清理 实施报告

> 2026-09-24。分支 `wt318-wsq7-tighten`（worktree `../Sparkle-sysrev/wt318-wsq7-tighten`）。
> 设计依据：`v3-output/WS-TICKET-DESIGN/REPORT.md` §6.1、§7 WSQ-7、§四 Step 5、§1.4 死码判定。
> 状态：**READY_FOR_REVIEW**（守卫 83 全绿、gateway 全量测试绿、lint 干净）。

## 一、SHA

- **base**：`66954051410531ad3e79f760fa1352e1454939d0`（开卡时 main）
- **final**：分支 `wt318-wsq7-tighten` HEAD（commit 后见 `git rev-parse HEAD`；主仓合入以分支为准）
- 注：开卡后 main 已前进（cb022dad，wt315 mobile 卡），`main...HEAD` 三点 diff 只含本卡改动，无冲突面（本卡全部改动在 `backend/gateway/`，该提交在 `mobile/`）。

## 二、改动清单（7 文件改 + 1 新增，+78/−255）

| 文件 | 改动 |
|---|---|
| `backend/gateway/internal/config/config.go` | `WsTicketRequired bool` 字段（mapstructure `WS_TICKET_REQUIRED`）+ BindEnv + `SetDefault(false)` + 开启时启动日志一行 |
| `backend/gateway/internal/middleware/ws_auth.go` | ①②降级分支包进 `if !cfg.WsTicketRequired`；ticket 缺失时收紧态 401 `ws_ticket_required`（附旧凭证 attempted-method 指标），宽松态原 `authorization_token_required` 不变 |
| `backend/gateway/internal/middleware/rate_limit.go` | 删 6 项死码（净 −171 行） |
| `backend/gateway/internal/middleware/rate_limit_paths_test.go` | 删死码自有测试（UserBased 部分、Adaptive+WebSocket+GlobalConfig 整例），保留 EndpointSpecific 例（改名 `TestEndpointSpecificRateLimit`） |
| `backend/gateway/internal/middleware/ws_auth_ticket_required_test.go` | **新增**：开关两态 6 测 |
| `backend/gateway/locales/en.json` / `zh.json` | 删孤儿 key `ratelimit.websocket_exceeded`（唯一消费者是被删的 WebSocketRateLimitMiddleware；en/zh 同步删，JSON 校验过） |
| `backend/gateway/.env.example` | 登记 `WS_TICKET_REQUIRED=false` + 翻转警示注释 |

## 三、死代码清单 + 零引用证据（删除前全仓 grep，含 tests_e2e/scripts）

判定基线 = WS-TICKET-DESIGN §1.4/§四 Step 5 点名的 6 项。每项 grep 范围 `--include="*.go" backend/ tests_e2e/`（排除 gen 产物）：

| # | 符号（删除前位置） | 删除前全部引用 | 生产/路由引用 |
|---|---|---|---|
| 1 | `WebSocketRateLimitMiddleware`（rate_limit.go:399-426） | 定义处 + `rate_limit_paths_test.go:118`（自有测试） | **0** |
| 2 | `UserBasedRateLimit`（215-252） | 定义处 + `rate_limit_paths_test.go:72,76`（自有测试） | **0** |
| 3 | `AdaptiveRateLimitMiddleware`（284-344） | 定义处 + `rate_limit_paths_test.go:85`（自有测试） | **0** |
| 4 | `DefaultRateLimitMiddleware`（370-376） | **仅定义处**（连测试都没有） | **0** |
| 5 | `AuthRateLimitMiddleware`（378-385） | **仅定义处** | **0** |
| 6 | `GlobalRateLimitConfig`（346-368） | 定义处 + 上方 3 个死函数（372-374/382-383/403-404）+ `rate_limit_paths_test.go:109-115`（自有测试） | **0** |
| 7 | locales `websocket_exceeded`（en/zh.json:72） | 仅 `#1` 的响应体使用 | **0** |

删除后复核：`grep -rn "WebSocketRateLimitMiddleware|UserBasedRateLimit|AdaptiveRateLimitMiddleware|DefaultRateLimitMiddleware|AuthRateLimitMiddleware|GlobalRateLimitConfig" --include="*.go" backend/ tests_e2e/` → **零命中**（exit 1）。

### 未删的传递性死码（不在设计清单，留主会话决断）

- `IPBasedRateLimit`：本卡删除后全仓**零引用**（此前唯一引用是 `DefaultRateLimitMiddleware`）。
- `EndpointSpecificRateLimit`：生产零引用（此前唯一生产引用是 `AuthRateLimitMiddleware`），现仅自有测试引用。
- `RateLimitMiddleware`：仍被 `IPBasedRateLimit` + 自有测试引用。
- 三者均为设计文档未点名的存活辅助函数，按「外科手术级」约束不扩清单，主会话可另派小卡或随下次清理带走。

## 四、开关实现（WS_TICKET_REQUIRED）

- **配置链**：env `WS_TICKET_REQUIRED` → viper BindEnv → `Config.WsTicketRequired` → `WsAuthMiddleware`（setup.go 零改动——中间件本就接收 `*config.Config`）。
- **默认 false（观察期）**；开启时启动打一行日志便于运维确认翻转生效。
- **收紧语义**：开启后 ①`Authorization: Bearer` ②`?token=` 两条降级路径整体跳过——**旧凭证连验签都不花**（合法 JWT 同样被拒：是策略拒绝而非签名失败）；无票一律 `401 {"code":"ws_ticket_required"}`，message 指引 `POST /api/v1/ws/ticket`。
- **指标**：`ws_connection_error_total{endpoint, auth_method, reason="ticket_required"}`，auth_method 记录被拒客户端尝试的旧通道（jwt_header/jwt_query/unknown），供 §5-R4 翻转前的旧版流量测量。
- **ticket 双通道不受影响**：subprotocol 通道本就无门；`?ticket=` 仍由 `ALLOW_WS_QUERY_TICKET` 独立门管。

## 五、测试证据

命令均在 `backend/gateway/` 下、`CGO_ENABLED=0`（硬规则 4）：

1. **新增两态测试** `go test -run TestWsAuthMiddleware_TicketRequired -v ./internal/middleware/` → **6/6 PASS**：
   - `TicketRequiredOffKeepsDowngradePaths`（关：合法 Bearer JWT → 200 jwt_header，现状回归）
   - `TicketRequiredRejectsValidJWTHeader`（开：**合法** JWT 头 → 401 `ws_ticket_required`，且断言 NotContains `invalid_or_expired_token`——证明是策略拒、非验签拒）
   - `TicketRequiredRejectsQueryToken`（开：`?token=` 即使 AllowWsQueryToken=true 也 401 ticket_required）
   - `TicketRequiredRejectsMissingCredentials`（开：无凭据 → 401 `ws_ticket_required`）
   - `TicketRequiredStillAcceptsQueryTicket`（开：`?ticket=` 有效票核销 200 + GETDEL 单次）
   - `TicketRequiredStillAcceptsSubprotocolTicket`（开：subprotocol 票 200，且不受 query 门影响）
   - 既有 `ws_auth_test.go` 4 例 + `ws_auth_query_ticket_test.go` 3 例保持绿（宽松态行为零变化）。
2. **全量回归**：`CGO_ENABLED=0 go test -count=1 ./...` → **EXIT=0，12 包全 ok，0 FAIL**。
3. **风格**：`gofmt -l .`（排除 gen）→ 空；`CGO_ENABLED=0 golangci-lint run ./...` → **exit 0**。
4. **治理守卫**：`bash scripts/run_all_rule_guards.sh` → **all rule guards passed (83 rules)，exit 0**。前置：按舰队协议从主仓 `cp -RL` 拷贝 gitignored 的 `backend/gateway/gen`、`backend/app/gen`、`mobile/lib/gen` 三棵 gen 树（否则 AQ/BG 环境性假失败，AQ 报 `No module named 'app.gen'`、BG 报 pb2/pb.dart missing）。
5. 诚实记录：首轮全量测出本卡自写测试一处 bug（query-ticket 用例漏设 `AllowWsQueryTicket=true`，401 假阳性）——已修复，非产品代码问题。

## 六、协调约束执行情况（与 RS256 JWT 迁移卡隔离）

- **未触碰**：`internal/middleware/auth.go`（validateJWT/abortWithAPIError 只读复用）、一切 JWT 签发/验签逻辑、`internal/handler/*`、`cmd/server/setup.go`。
- 本卡改动的 `config.go` 是共享热点文件（RS256 卡可能也加配置项）：本卡在该文件只加了 1 个结构体字段行、1 行 BindEnv、1 个 SetDefault 块、1 个启动 notice 块，均为追加式局部改动，冲突面最小；若真冲突，保留双方追加即可。

## 七、风险

1. **翻转杀伤旧客户端**（设计 §5-R4，高杀伤）：开关默认关；翻转是运维决策，建议以 `ws_connection_error_total{reason="ticket_required"}` 归零为翻转前置信号。
2. **合并顺序**：与在航 RS256 卡若同窗合入，`config.go` 建议后合者 rebase（追加式改动，易解）。
3. **传递性死码未删**（见三）：非缺陷，仅提示——本卡遵守设计清单边界。
4. **收紧态 auth_method 指标粒度**：`Authorization: Basic xxx`（非 Bearer）会被记为 `unknown`（检测用 Bearer 前缀判定），不影响功能与主口径。
5. 本卡不涉及 proto/DB/分层边界，无 gen 重生成需求；`gateway/gen` 为运行拷贝不入库。
