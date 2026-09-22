# SSE-HB-VERIFY：galaxy SSE 心跳实机观察 — 实测报告

- 任务卡：SSE-HB-VERIFY（wt112，基于 main@1d42786a；关闭 SSE-HB 卡「需实机验证」挂账）
- 日期：2026-09-22（活栈当晚 21:08 重启到含 SSE-HB 修复 `fd85f9b5` 的 main）
- 性质：纯观察卡，零产品代码改动；LLM 零调用、不发 chat、单条只读 SSE 连接（含自动重连序列）
- 交付：`scripts/devtools/probe_galaxy_sse_heartbeat.py`（可复跑探针，已登记 devtools README）+ `evidence/`（4 份日志 + 2 份 JSON）+ 本报告

## 1. 结论一句话

**挂账部分关闭**：SSE-HB 心跳机制本身实机验证通过——引擎空闲期每 **20.0s 精确**产出 `: heartbeat` 注释帧、经 gateway 逐字节透传到达客户端、无缓冲吞帧；但 gateway 链路「空闲连接保持 ≥5 分钟」**未达成**——实测每条连接在 **t=30.0s 整被确定性掐断**（两轮 360s 共 23 连接全部如此），根因已定位：gateway `/api/v1` 组级 `TimeoutMiddleware(30s)` 总超时对 SSE 长流无豁免，心跳帧对「总超时型」掐断无效。修复前 V26 观测的 ~35s 周期断连与本次实测 30s 同源（30s 服务端切断 + 旧客户端 ~5s 检测/重连延迟）。

## 2. 验证方法与链路

- 账号：`northstar_sse_hb_b842879d`，经 **gateway :8080** `POST /api/v1/auth/register` + `/login` 注册获取 Bearer token（沿用 northstar_* 先例；凭据仅存 `/tmp`（0600），复跑幂等复用）
- 端点：`GET /api/v1/galaxy/events`（`Authorization: Bearer`；gateway `galaxy_handler.go:138` rateLimit + `ProxyToBackend`（`httputil.ReverseProxy`，`FlushInterval=-1`）反代至引擎 `app/api/v1/galaxy.py:899`）
- 探针：`scripts/devtools/probe_galaxy_sse_heartbeat.py`（纯 stdlib；idle 只读；断连自动重连并计数，复现修复前客户端静默重连行为；`--subscribe-url` 可直连引擎做对照）
- 判帧：`: heartbeat` 注释帧 / `event:`·`data:`·`id:` 事件行 / 空行分隔，逐行打时间戳

## 3. 实测结果

### 3.1 gateway 链路（生产路径，360s × 2 轮）

| 指标 | Run1（25s 窗冒烟扩程） | Run2（360s，`probe-gateway.json`） |
|---|---|---|
| 观察时长 | 361.2s（实际收满 360s 窗） | 361.2s |
| 连接建立次数 | 12 | 12 |
| 服务端断连次数 | 11 | **11** |
| 断连时刻（连接内） | 全部 **+30.0s 整** | 30.01 / 61.03 / 92.05 / … / 340.18s（间隔恒 31.02s = 30s 寿命 + 1s 重连退避） |
| 断连形态 | EOF（服务端关闭流，无错误帧） | 同左，11/11 `EOFError` |
| 心跳帧 | 12/12 连接各 1 帧，**+20.0s 准点** | 同左 |
| 事件帧/其它帧 | 0 / 0（纯空闲） | 0 / 0 |
| 响应头 | `Server: uvicorn`、`X-Accel-Buffering: no`、`Transfer-Encoding: chunked` 透传正常 | 同左 |

时间线样例（Run2）：

```
t=0.0    连接#1 建立 HTTP 200 text/event-stream
t=20.0   ': heartbeat'  ← 引擎 20s 心跳经 gateway 到达
t=30.0   EOF，服务端掐断（无任何前置错误帧）
t=31.0   连接#2 建立（自动重连）
t=51.0   ': heartbeat'
t=61.0   EOF   …… 周期精确重复至观察窗结束
```

**稳态断连频率：每 ~31s 一次 ≈ 9.7 次/5 分钟**（对照修复前预期 ~8 次/5min @35s 周期）。

### 3.2 对照实验：直连引擎 :8000（绕过 gateway，160s 窗）

| 指标 | 结果 |
|---|---|
| 连接 | 1 条保持全程，**0 断连** |
| 心跳 | 8 帧，间隔 **min=max=20.0s**（`probe-engine-direct.json`） |
| 事件帧 | 0（纯空闲） |

心跳路径本身（引擎产出 → 链路传输 → 客户端接收）完全符合 SSE-HB 设计。

## 4. 根因定位（30s 掐点，静态代码 + 实测时序互证）

掐断因果链（与 23/23 连接 +30.0s 整 EOF 的实测时序吻合）：

1. `backend/gateway/cmd/server/setup.go:524` `requestTimeout := 30`（默认，可被 `cfg.RequestTimeoutSeconds` 覆盖）→ `:579` `api.Use(middleware.TimeoutMiddleware(30s))`
2. 该 `Use` 在 galaxy 路由注册（`:600`）**之前**——按 gin 路由链注册时快照语义（FV-24 注释 `:602-607` 自证此机制），`TimeoutMiddleware` **在 `/galaxy/events` 处理链内**
3. `backend/gateway/internal/middleware/timeout.go`：对请求 ctx 施加 30s `context.WithTimeout`；长流豁免清单 `isLongRunningRoute()`（learning-paths / stt / capsules / theater / plans）**不含 `/api/v1/galaxy/events`**
4. `backend/gateway/internal/handler/galaxy_handler.go:931` `h.proxy.ServeHTTP(c.Writer, c.Request)`——ReverseProxy 出站流继承入站 ctx，30s `DeadlineExceeded` 到期即中止出站流 → 客户端 EOF
5. 另：`NetworkResilienceMiddleware`（`RequestTimeout=30s`，`setup.go:608-609`）注册于 galaxy **之后**，不覆盖 galaxy（但覆盖注册于其后的代理路由，如 `/simulation/*` ——这些路由身背双重 30s）

**为何心跳救不了**：SSE-HB 心跳重置的是「读空闲计时器」（nginx/LB 空闲超时类）；而 `TimeoutMiddleware` 是**总时限**（自请求进入起算，不看是否有字节流动），20s 心跳无法阻止 30s 到期。修复前 V26 的 ~35s 观测周期 = 30s 服务端切断 + 客户端 ~5s 检测/重连延迟（FIX-51 前 mobile receiveTimeout 30s + 5s 重连 Timer）；本次探针重连退避 1s，故实测周期 31s。

## 5. 结论：对照任务三问

1. **连接是否保持**：gateway 链路**不保持**——确定性 30.0s 掐断（5.5 分钟 11 次）；引擎直连保持（160s 零断连，观察窗内）。
2. **心跳帧到达**：**通过**——注释帧 `: heartbeat` 每 20.0s 精确到达（引擎直连 min=max=20.0s；gateway 链路每连接 +20.0s 准点 1 帧，透传无缓冲）。但 gateway 30s 寿命内每条连接只来得及发 1 帧。
3. **断连对照修复前**：同源同量级——真实服务端掐点 30s（V26 观测 35s = 30s + 客户端延迟）。SSE-HB 消除了「空闲超时型」断连成因（引擎/中间层读空闲），但 gateway `TimeoutMiddleware(30s)` 是**另一独立掐点**，心跳对其无效——断连未消除，实测频率 ~9.7 次/5min（修复前口径 ~8 次/5min）。

**挂账判定：部分关闭。**
- ✅ 关闭：心跳机制实机验证（形态/间隔/透传/引擎链路空闲保持）
- ❌ 未关闭（新精确挂账，建议开新卡）：gateway 对 SSE 长流路由缺超时豁免——`isLongRunningRoute()` 应豁免 `/api/v1/galaxy/events`（建议同时复核引擎侧其它 SSE 透传端点：`/api/v1/background-tasks` 流、`/simulation/*`、chat REST 流，及注册于 NetworkResilience 之后身背双重 30s 的代理路由）；修复为路由清单级小改，gateway 侧行为零变化

## 6. 产物与复跑

- 探针：`scripts/devtools/probe_galaxy_sse_heartbeat.py`（`--duration` 默认 360s；`--subscribe-url http://localhost:8000` 做引擎直连对照；凭据 `/tmp/sse_hb_probe_creds.json` 0600 收工自清，复跑自动重建）
- 证据：`v3-output/SSE-HB-VERIFY/evidence/`——`probe-gateway.json`（Run2 结构化）、`probe-gateway-run1.log`、`probe-gateway-run2.log`、`probe-engine-direct.json`、`probe-engine-direct.log`
- 复跑：活栈在跑前提下 `python3.11 scripts/devtools/probe_galaxy_sse_heartbeat.py`；修复落地后重跑，预期 `disconnect_count=0` 且心跳间隔统计 ~20s

## 7. 纪律与收工核查

- [x] 只写自己 worktree（wt112）；主仓只读未动
- [x] 纯观察：零 LLM、零 chat、零业务写入；单条 SSE 只读连接（含自动重连序列，无并发双开）
- [x] 测试账号 `northstar_sse_hb_b842879d` 留共享 dev 库（沿 BP-3B 先例不做级联删除，按前缀 `northstar_sse_hb_` 可定位清理）
- [x] /tmp 已清：凭据 JSON、冒烟/三轮运行日志全部删除
- [x] 未起 docker/模拟器/Gradle/浏览器（LIGHT）；无遗留进程（探针为前台客户端，已退出）
- [x] 持久产物仅：探针脚本（已登记 `scripts/devtools/README.md`）+ evidence + 本报告
