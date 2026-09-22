# SSE-EXEMPT：gateway 30s 组级总超时豁免补齐 — 施工报告

- 任务卡：SSE-EXEMPT（wt117，基于 main@d5cce684；SSE-HB-VERIFY 定位的断连真根因）
- 日期：2026-09-22
- 性质：gateway 纯超时策略修复（timeout 豁免清单 + resilience 同源豁免 + 1 条流式路由补注册），零 AI/业务逻辑、中间件顺序零变动
- 交付：`v3-output/SSE-EXEMPT/changes.patch`（6 文件，+303/−4）+ 本报告
- 红线遵守：30s 对普通 API 保护语义零变化（回归全绿 + 专项守护测试钉死）；鉴权/CORS/限流中间件顺序不动；galaxy SSE 鉴权（FIX-51/V23）未碰

## 1. 结论一句话

`/api/v1` 组级 `TimeoutMiddleware(30s)` 与 `NetworkResilienceMiddleware(RequestTimeout=30s)` 的**总时限型**超时对 7 类流式/长传输端点完成豁免补齐——含实测被 30.0s 掐断的 `GET /galaxy/events`，以及此前**从未被发现的 5 个嫌疑面**（其中 `/background-tasks/stream/events` 经审计确认在 gateway 侧因缺路由注册而整体 404，mobile 正在调用）；普通 API 的 30s 保护一条未动。

## 2. 修复内容（三处，全部在 gateway）

| # | 文件 | 改动 |
|---|---|---|
| 1 | `backend/gateway/internal/middleware/timeout.go` | `isLongRunningRoute()` 新增 6 条豁免规则（覆盖 7 条端点路径，见 §3）；补写函数级 doc 注释说明「总时限 vs 空闲时限」差异（心跳只能救空闲计时器，救不了总时限——SSE-HB 实测核心结论） |
| 2 | `backend/gateway/internal/middleware/network_resilience.go` | `NetworkResilienceMiddleware` 对 `isLongRunningRoute` 命中路径**跳过 deadline 注入**（Keep-Alive 头、disconnectWatcher、断连监控全部保留）。关键：所有 `RegisterProxyRoutes` 路由注册于 `setup.go:608` 的 `api.Use(NetworkResilience)` **之后**（gin 注册时快照链，FV-24 注释自证），只改 timeout.go 豁免清单的话，`/chat/stream`、`/simulation/*` 等仍会被 resilience 的第二个 30s 掐断（即 SSE-HB 报告提示的「双重 30s 嫌疑面」） |
| 3 | `backend/gateway/internal/handler/proxy_routes.go` | background-tasks 组补注册 `GET /stream/events`（`proxyWithHeaders`，随组走 authMiddleware）。审计发现：引擎 `background_tasks.py:65` 提供该 SSE，mobile `task_monitor_screen.dart:106` 正在调用，但 gateway 显式路由只有单段 `/:task_id`，两段路径落到 NoRoute——而 NoRoute 白名单只代理 `/api/v1/auth/*`，实际返回 404。不补这条路由，豁免毫无意义（404 先于超时发生） |

未动：`setup.go`（中间件顺序、`requestTimeout=30` 默认值、galaxy 注册位、`/ws/*` 注册位全部原样）；galaxy_handler 鉴权链；任何 engine/Python 代码（wt115/wt116 零冲突）。

## 3. 审计算（全列：流式/长连接代理端点 × 两个 30s 超时面判定）

超时面说明：**TM** = TimeoutMiddleware(30s, `setup.go:579`，覆盖 /api/v1 组全部路由)；**NR** = NetworkResilienceMiddleware(30s, `setup.go:608` 后注册的显式代理路由 + `setup.go:859` 的 NoRoute fallback)。

| # | 端点 | 类型 | 引擎源 | gateway 面 | TM | NR | 判定 → 处置 |
|---|---|---|---|---|---|---|---|
| 1 | `GET /api/v1/galaxy/events` | SSE | `galaxy.py:899`（20s 心跳） | galaxy_handler:138 显式路由（注册于 NR 之前，无 NR） | 30s 掐（SSE-HB 实测 23/23 连接 +30.0s EOF） | 不覆盖 | **应豁免未豁免** → TM 豁免（主修复目标） |
| 2 | `POST /api/v1/chat/stream` | SSE | `chat.py:597→751` | proxy_routes:322（NR 后，双重 30s） | 30s | 30s | **应豁免未豁免**（mobile `api_endpoints.dart:185`「SSE 流式聊天端点」）→ TM+NR 双豁免 |
| 3 | `POST /api/v1/simulation/run/stream` | SSE | `simulation.py:151` | simulation 通配组（NR 后，双重 30s） | 30s | 30s | **应豁免未豁免**（mobile `simulation_repository.dart:62` 在调）→ 双豁免 |
| 4 | `POST /api/v1/simulation/sessions/{id}/continue/stream` | SSE | `simulation.py:234` | 同上 | 30s | 30s | **应豁免未豁免**（mobile `simulation_repository.dart:100` 在调）→ 双豁免（模式：`/simulation/` 前缀 + `/stream` 后缀） |
| 5 | `GET /api/v1/background-tasks/stream/events` | SSE | `background_tasks.py:65` | **原缺显式路由 → NoRoute 404**（NoRoute 白名单仅 `/api/v1/auth/*`） | 不可达 | NR 30s（若可达） | **应豁免未豁免 + 路由缺失**（mobile `task_monitor_screen.dart:106` 在调）→ 补显式路由 + 双豁免 |
| 6 | `GET /api/v1/users/me/export` | 大文件流（ZIP） | `data_export.py:55`（`/users` 前缀挂载，StreamingResponse） | users `/*path` 通配（NR 后，双重 30s） | 30s | 30s | **应豁免未豁免**（`api_endpoints.dart:27 meExport` 在调；ZIP 体量随账号数据无上界）→ 双豁免 |
| 7 | `POST /api/v1/tts/synthesize` | 生成式音频 | `tts.py:24`；引擎上游预算 `QWEN_TTS_REQUEST_TIMEOUT_SECONDS=60`（settings.py:596） | tts 组（NR 后，双重 30s） | 30s（<引擎 60s，30–60s 区间必被早切） | 30s | **应豁免未豁免**（同 capsules/generate 等既有生成式豁免先例）→ 双豁免 |
| 8 | `POST /api/v1/chat`（同步 Agent 聊天） | 同步 LLM | `chat.py:347` | proxy_routes:321 | 30s | 30s | **标记不豁免**：非流式类目（请求-响应型），产品主链路是 `/ws/chat` WebSocket；无实测断连证据。建议后续卡评估（若保留此 REST 面且 LLM 尾延迟超 30s，可按生成式先例豁免） |
| 9 | `/ws/chat`、`/ws/files`、`/ws/stt` | WebSocket | — | `setup.go:507-509`（api 组外 + 注册于 NR :859 之前） | 不覆盖（组外） | 不覆盖（注册时序快照） | **天然豁免，无需改动**（timeout.go 既有注释已说明 hijack 语义） |
| 10 | `/api/v1/ws/health\|stats\|metrics` | 普通 JSON REST（名含 ws 实为监控 REST） | `monitoring.py`（prefix=/ws） | proxy_routes:970-972 | 30s | 30s | **不豁免**：短请求，30s 保护语义正确 |
| 11 | stt/transcribe、capsules/generate(+batch)、theater predictions generate/what-if、plans …/generate-tasks、learning-paths/* | 既有豁免（同步生成/大转录） | — | — | 已豁免 | NR 后注册的同样吃 NR 豁免（本次同源修复顺带补齐其 NR 面） | **保持** |
| 12 | 文件上传/下载 | 大文件 | — | gateway 只发 MinIO 预签名 URL（`PrepareUpload`/`PresignGet`），字节不经 gateway；`/internal/files/...` 组无 TM | — | — | **无需改动** |
| 13 | `/api/v2/agent`（agent_graph.py:78 SSE） | SSE | `app/api/v2/agent_graph.py:78` | gateway 无 /api/v2 面；NoRoute 仅代理 /api/v1/auth/* → **经 gateway 不可达** | 不可达 | 不可达 | **登记不改**（若未来网关化 /api/v2，需带豁免清单同步维护） |
| 14 | documents/ingestion 重处理 | 异步任务 | `documents.py:347`（Celery 派发即返回） | proxy_routes | 30s 合理 | 30s 合理 | **无需改动**（重活不占 HTTP 请求生命周期） |

审计算分母：gateway 侧扫描 `ReverseProxy/httputil`（3 文件）、`text/event-stream|EventSourceResponse|StreamingResponse`（engine api 层 7 处）、`Upgrade`（3 条 WS 路由）、预签名大文件路径（2 面）。

## 4. 测试统计（新增 19 条用例 / 3 个测试文件）

| 文件 | 新增 | 内容 |
|---|---|---|
| `timeout_test.go` | `TestIsLongRunningRoute` 扩充 | 表驱动：+7 命中（7 条豁免路径）、+14 近邻负例（`/simulation/run`、`/background-tasks/stream`、`/users/export`、`/tts/voices`、`/galaxy/graph` 等不得误豁免） |
| `timeout_test.go` | `TestTimeout_ExemptStreamingRoutesNoDeadline` | 12 子测试（7 条新豁免 + 5 条既有豁免钉死）：timeout=50ms 下 handler 跑 120ms 必须 200 完成，且 ctx **无 deadline**——正是 galaxy 实测 +30.0s EOF 的回归签名 |
| `timeout_test.go` | `TestTimeout_NonExemptRouteStillEnforced` | 红线守护：非豁免慢请求必须在 deadline 处被打断（ctx.Done 触发） |
| `network_resilience_test.go` | `TestNetworkResilienceMiddleware_ExemptRouteNoDeadline` | 7 子测试（每条新豁免一个）：resilience 50ms 下 exempt 路由 120ms 完成、无 deadline、disconnectWatcher 仍在位 |
| `network_resilience_test.go` | `TestNetworkResilienceMiddleware_NonExemptRouteKeepsDeadline` | 红线守护：普通路由仍带 resilience deadline（时限在 50ms±40ms 内） |
| `proxy_routes_test.go` | `TestProxyRoutesHandler_BackgroundTaskStreamRegistered` | 新路由注册断言 + 真 HTTP 服务代理往返（200 + SSE Content-Type 透传 + body 逐字节）+ `/:task_id` 兄弟路由不受影响 |

既有测试全数保留：`TestTimeout_LongRunningRouteSkipped`、`TestTimeout_SetsContextDeadline`、`TestNetworkResilienceMiddleware_RequestTimeout` 等（顺序/保护语义零变化的回归证明）。

## 5. 回归证明

`cd backend/gateway && CGO_ENABLED=0 go test ./...`：

```
ok   github.com/sparkle/gateway/cmd/server          0.645s
ok   github.com/sparkle/gateway/internal/agent      1.114s
ok   github.com/sparkle/gateway/internal/cqrs       3.794s
ok   github.com/sparkle/gateway/internal/cqrs/event 2.092s
ok   github.com/sparkle/gateway/internal/db         2.378s
ok   github.com/sparkle/gateway/internal/handler   29.329s   ← 路由注册 + 代理面
ok   github.com/sparkle/gateway/internal/logsafe    2.199s
ok   github.com/sparkle/gateway/internal/middleware 9.504s   ← 超时/豁免面
ok   github.com/sparkle/gateway/internal/service   11.288s
FAIL github.com/sparkle/gateway/internal/config    （预存环境缺失）
```

- 唯一 FAIL 为 `internal/config`：`JWT_SECRET must be set even in development`——**与本卡无关的预存环境依赖**。双证：① 在 `/tmp` 克隆干净 HEAD 基线（无本卡改动）复跑同 FAIL；② 同基线补 `JWT_SECRET=…` 即 `ok`。
- `go vet ./internal/middleware/ ./internal/handler/ ./cmd/...` 干净（`gen/` 为 gitignored 生成物，从主仓拷入仅用于编译，不入 patch）；改动文件 gofmt 全净（`ws_e2e_roundtrip_test.go` 的 gofmt 告警为 HEAD 预存、本卡未触碰）。

## 6. 真栈 idle 观察方案（主会话重启后统一执行）

1. 前置：活栈以含本 patch 的 main 重启（gateway :8080 + engine :8000）。
2. 复跑 SSE-HB 探针（零改动直接复用）：`python3.11 scripts/devtools/probe_galaxy_sse_heartbeat.py`（默认 360s 窗）。
3. 通过判据：
   - `disconnect_count == 0`（对照 SSE-HB Run2：360s 内 11 次断连）；连接全程保持（>300s）；
   - 心跳帧间隔统计 min=max≈20.0s 且**每连接多帧**（对照修复前：每连接仅 1 帧——30s 寿命内来不及第二帧）；
   - `probe-engine-direct.json` 对照组保持 20.0s 零断连不变。
4. 附加验证（可选）：对 `/simulation/run/stream` 起一条 >60s 的流（引擎仿真时长天然 >60s），验证双重 30s 面确实解除；对任一普通 API（如 `GET /chat/sessions`）确认无行为变化。
5. 若断连仍为 30s 周期：按 §2 排查顺序查 gateway 二进制是否确实重建（`docker compose build gateway`）。

## 7. 纪律与收工核查

- [x] 只写自己 worktree（wt117）；主仓只读（`gen/` 为只读拷贝源，未写主仓任何字节）
- [x] 未 commit / 未 push；patch 与报告在 `v3-output/SSE-EXEMPT/`
- [x] /tmp 已清：`/tmp/sse-exempt-baseline`（基线克隆）已删
- [x] 未起 docker/模拟器/Gradle/浏览器（LIGHT 任务）；`go test` 串行包级执行，无遗留进程
- [x] worktree 内构建产物：仅 gitignored 的 `backend/gateway/gen`（编译必需，不入库、随 worktree 回收）
- [x] 冲突面：零——只动 `backend/gateway/internal/middleware/{timeout,network_resilience}*.go` 与 `internal/handler/proxy_routes*.go`；wt115（engine memory）/wt116（engine goal）无交集
