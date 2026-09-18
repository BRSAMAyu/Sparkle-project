# gRPC 桥 metadata 注入全量审计（user-id / authorization）

> 基线 efb1567a（2026-09-18）。781c0280 修复了 error_book.go 漏注入 `user-id` 导致引擎 401 的问题（同类第一例）；本审计对网关**全部出站 gRPC 调用点**做同型排查，确认并修复其余缺失点。

## 结论速览

- 全仓出站 gRPC 桥只有 3 个 client：`internal/agent`、`internal/error_book`、`internal/galaxy`（STT 是 WebSocket 直通代理、chaos.go 仅为 toxiproxy 命名，均非 gRPC 桥）。
- **缺失 12 处**：galaxy 桥全部调用点（gin 10 处 + WebSocket 离线掌握度同步 2 处）均未注入任何认证 metadata。
- **实际影响**：引擎侧 `AuthInterceptor`（全局注册，`backend/grpc_server.py:151`）对无 `authorization`/`x-internal-api-key` 的调用直接 abort `UNAUTHENTICATED`：
  - gin 10 处：gRPC 永远失败 → 静默降级走 REST 反向代理（高性能路径死代码、双份负载）；
  - WS 2 处：无 fallback → 用户可见失败（"Sync service unavailable"），离线掌握度同步整链路不可用。
- **P0 检查通过**：所有注入的 `user_id` 均取自 gin context（`AuthMiddleware` → `validateJWT` RS256 验签 + jti 黑名单后的 `sub`），不存在从客户端 header 直取透传的路径；引擎侧还校验 metadata `user-id` 与 JWT `sub`/请求体 `user_id` 的一致性（防伪造）。
- 修复 12 处 + 补红绿测试 13 个子用例。**未发现新的 P0**。

## 一、调用点清单

### A. agent 桥（`internal/agent/client.go`）— ✅ 全部合规

client 内部 `injectMetadata` 统一注入 `x-internal-api-key` + `user-id`（取自 `req.UserId`/`req.ArbitratorId`）+ 可选 trace id；14 个带用户语义的 wrapper（StreamChat、SubmitResponseFeedback、SubmitPlanReview 等）全部经它注入。网关侧调用方：

| 调用点 | RPC | req.UserId 填充 | 注入 | 引擎侧校验 | 影响 |
|---|---|---|---|---|---|
| chat_orchestrator_chatflow.go:694 | StreamChat | ✅ :645 | ✅ client 内 | 拦截器 + servicer SEC-3 | — |
| chat_orchestrator_feedback.go:790 | SubmitResponseFeedback | ✅ | ✅ | 同上 | — |
| chat_orchestrator_feedback.go:929 | SubmitPlanReview | ✅ | ✅ | 同上 | — |
| agent/health_checker.go | 仅连接态检查（无 RPC） | — | — | — | — |
| 14 个其余 wrapper（arbitration/memory/profile/weekly-report/review-* 等） | 各 RPC | — | ✅（含 s2s key） | 拦截器 | **无生产调用方**（预留代码），合规 |

### B. error_book 桥（`internal/error_book/client.go`，裸传 ctx，注入责任在 handler）— ✅ 781c0280 已修

| 调用点 | RPC | 注入 | 引擎侧校验 | 影响 |
|---|---|---|---|---|
| handler/error_book.go 全部 10 个端点（CreateError/ListErrors/GetError/GetSemanticSummary/UpdateError/DeleteError/AnalyzeError/SubmitReview/GetReviewStats/GetTodayReviews） | errorbookv1.* | ✅ `injectAuthContext`（authorization + user-id） | `error_book_grpc_service.py:_resolve_authenticated_user_id`：请求体 user_id 无 metadata → 401 "missing authentication metadata"；不一致 → 阻断 | — |

### C. galaxy 桥（`internal/galaxy/client.go`，裸传 ctx）— ❌ 12 处全缺（本次修复）

| # | 调用点 | 端点 / 来源 | RPC | 修复前注入 | 引擎侧校验 | 修复前影响 |
|---|---|---|---|---|---|---|
| 1 | galaxy_handler.go SparkNode | POST /galaxy/nodes/:id/spark | RecordNodeInteraction | ❌ 无 | `galaxy_grpc_service.py` SEC-3 + 全局拦截器 | 401 → 静默降级 REST 代理 |
| 2 | galaxy_handler.go UpdateMastery | POST /galaxy/nodes/:id/mastery | UpdateNodeMastery | ❌ | 同上 | 401 → 降级 |
| 3 | galaxy_handler.go GetNodeDetailGPRC | GET /galaxy/nodes/:id | GetNodeDetail | ❌ | 同上 | 401 → 降级 |
| 4 | galaxy_handler.go SearchNodesGPRC | GET·POST /galaxy/search | SearchNodes | ❌ | 同上 | 401 → 降级 |
| 5 | galaxy_handler.go GetGalaxyStatsGPRC | GET /galaxy/stats | GetGalaxyStats | ❌ | 同上 | 401 → 降级 |
| 6 | galaxy_handler.go GetRecommendedGPRC | GET /galaxy/predict | GetRecommendedNodes | ❌ | 同上 | 401 → 降级 |
| 7 | galaxy_handler.go GetGraph | GET /galaxy/graph | GetUserGalaxy | ❌ | 同上 | 401 → 降级 |
| 8 | galaxy_handler.go SyncGalaxy | POST /galaxy/sync | SyncCollaborativeGalaxy | ❌ | 同上 | 401 → 降级（CRDT 同步走慢路径） |
| 9 | galaxy_handler.go GetLearningPath | GET /galaxy/learning-path | GetLearningPath | ❌ | 同上 | 401 → 降级 |
| 10 | galaxy_handler.go GetNodeDependencies | GET /galaxy/nodes/:id/dependencies | GetNodeDependencies | ❌ | 同上 | 401 → 降级 |
| 11 | chat_orchestrator_feedback.go:614 handleUpdateNodeMasteryWithResponder | WS update_node_mastery（JSON 协议） | UpdateNodeMastery | ❌（WS 路径无 gin handler） | 同上 | **用户可见失败**："Sync service unavailable"，无 fallback |
| 12 | chat_orchestrator_protocol.go:642 handleUpdateNodeMasteryProto | WS update_node_mastery（protobuf 协议） | UpdateNodeMastery | ❌ | 同上 | 同上 |

（galaxy_handler.go RecordStudy 走 Go CQRS 不出 gRPC；ProxyToBackend 为 HTTP 代理，设置 X-User-ID + Authorization，非本审计对象。）

## 二、引擎侧校验事实（判定影响依据）

- `backend/grpc_server.py:151`：`grpc.aio.server(interceptors=[AuthInterceptor()])` — **全局**拦截，覆盖 agent/error_book/galaxy/STT/inference 全部服务。
- `backend/app/api/grpc_auth.py`：无 `x-internal-api-key` 时必须有 `authorization: Bearer <JWT>`，否则 `UNAUTHENTICATED`；有 key 但无效 → `UNAUTHENTICATED`；user 路径下 metadata `user-id` ≠ JWT `sub` → `PERMISSION_DENIED`。
- `galaxy_grpc_service.py` / `error_book_grpc_service.py` / `agent_grpc_service.py` 均实现 SEC-3 `_resolve_authenticated_user_id`：请求体 `user_id` 存在而 metadata `user-id` 缺失 → 抛 "missing authentication metadata"（R5-P0-2 阻断）；不一致 → "user_id spoofing detected" 阻断。

因此 galaxy 桥 12 处修复前**从未真正成功过**（拦截器层即 401）。

## 三、修复内容（照 error_book.go 模式）

1. `internal/handler/galaxy_handler.go`：10 个 gin handler 在 userID 校验后调用 `injectAuthContext(c)`（复用 error_book.go 的既有函数，同包）。
2. `internal/handler/error_book.go`：新增 `grpcUserAuthContext(ctx, userID, authToken)` — WS 路径版注入 helper（authorization + user-id），与 `injectAuthContext` 同一契约。
3. `internal/handler/chat_orchestrator.go`：WS streamCtx 构造后 `streamCtx = grpcUserAuthContext(streamCtx, userID, authToken)`，一处覆盖两条 WS mastery 调用链（JSON + protobuf）。agent client 的 `injectMetadata` 会整组替换 outgoing metadata，不产生重复。

## 四、红绿证据

新增测试（`internal/handler` 包）：

- `galaxy_handler_test.go`：`TestGalaxyGRPCEndpoints_InjectAuthMetadata` — in-process `capturingGalaxyServer`（模拟引擎拦截器语义：无 user-id → UNAUTHENTICATED）+ 真实 `galaxy.NewClient` + 全 10 个端点表驱动，断言引擎侧收到的 `user-id`/`authorization` metadata 且响应走 gRPC 路径（非代理 fallback）；`TestGRPCUserAuthContext_*`（error_book_test.go）×3 覆盖 helper。
- **RED**（回滚 galaxy_handler.go + chat_orchestrator.go 注入）：10/10 子用例失败 — `engine saw user-id metadata [], want [user-42] (SEC-3: missing metadata → engine 401)`。
- **GREEN**（修复在位）：13/13 PASS。
- 全量：`CGO_ENABLED=0 go build ./...` ✅；`CGO_ENABLED=0 go test ./internal/handler/` → `ok 27.9s` ✅。

## 五、P0 检查：注入值来源

- 网关：`middleware/auth.go AuthMiddleware` 只从 `Authorization` 头取 token → `validateJWT`（RS256 公钥验签，HS256 仅迁移期且需显式 secret；jti 黑名单；query `user_id` 必须与 sub 一致）→ `c.Set("user_id", …)` / `c.Set("auth_token", …)`。全部 12 处修复点与既有 error_book/agent 路径均消费这两个 key，**无任何从客户端 header/query 直取 user-id 透传给引擎的路径**。
- 引擎：即便网关被攻破，servicer 侧仍有 metadata ↔ JWT sub ↔ 请求体三方一致性校验。纵深防御成立。
- 结论：**无 P0**。

## 附：范围外备注

- `agent.Client` 中 14 个尚无调用方的 wrapper（arbitration 队列等）已按 s2s 契约注入 key；`GetArbitrationQueue`/`GetArbitrationQueueStats` 固定不注入 user-id（无用户语义），若未来接线需复核引擎侧 admin 要求。
- galaxy 桥 10 个 gin 端点在 gRPC 失败时的 REST 降级路径保留不变；修复后 gRPC 路径恢复可用，降级退化为真正的兜底。
