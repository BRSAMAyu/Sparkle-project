# SSE-HB：引擎 SSE 心跳补齐 — 实测报告

- 任务卡：SSE-HB（wt92-v3，基于 main@f119a9c0）
- 日期：2026-09-22
- 交付：`v3-output/SSE-HB/changes.patch`（4 个文件，203 行）+ 本报告
- 红线遵守：未 commit / 未 push

## 1. 结论一句话

引擎 `event_generator` 空闲期每 20s（可配置 `PHASE5_SSE_HEARTBEAT_INTERVAL`）产出 SSE 注释帧 `: heartbeat\n\n`，gateway ReverseProxy 逐字节透传、mobile 解析器天然忽略，全链路保持字节流动，消除空闲期静默断连；gateway 与 mobile **零改动**。

## 2. 心跳形态与间隔选择依据

**形态：注释帧（`: heartbeat\n\n`）**，非 `event: heartbeat` 事件。逐层验证：

| 层 | 实现 | 对注释帧的行为 |
|---|---|---|
| Engine | `app/core/sse.py::event_generator`（本次改动点） | 主动产出 |
| Gateway | `backend/gateway/internal/handler/galaxy_handler.go` `ProxyToBackend` = `httputil.ReverseProxy` + `FlushInterval: -1` | **逐字节透传，不解析 SSE**，注释帧原样到达客户端 |
| Mobile | `mobile/lib/features/galaxy/data/repositories/galaxy_repository.dart` `_parseSSE` | 按 `\n\n` 分帧后逐行找 `event:`/`data:`，纯注释帧两字段皆 `None` → 返回 `None`，事件被**静默忽略**，不触发任何业务处理 |

注释帧是 SSE 规范推荐的心跳形态，且本链路三层代码实证兼容——因此 gateway/mobile 均无需改动（若 gateway 是"解析事件再重组"型代理就必须改用它端转发轻量事件，实际代码证实不需要）。

**间隔：默认 20s**。依据：
- TRIAGE 实测断连周期 ~35s，对齐 mobile 侧历史成因（全局 receiveTimeout 30s + 5s 重连 Timer；FIX-51 已置 `receiveTimeout: null`，但 nginx/LB 等中间层读空闲超时仍在，常见值 60s）；
- 20s < 一切已知中间层空闲阈值（30s/60s），留有 ≥1 次心跳的冗余；
- 不至于过频（空闲连接每 20s 一次 13 字节写入，开销可忽略）。
- 可配置：`phase5_config.SSE_HEARTBEAT_INTERVAL: float = 20.0`（pydantic，env 键 `PHASE5_SSE_HEARTBEAT_INTERVAL`），`backend/.env.example` 已加注释段说明。

## 3. 超时链路归因（谁在掐）

- mobile：FIX-51 后 `receiveTimeout: null`，客户端不再掐（本任务未触碰）。
- gateway：`ReverseProxy` 无自定义 `http.Transport` 超时，不掐。
- 引擎：uvicorn/http.h11 无写空闲超时，不掐。
- 剩余掐点：部署链中间层（nginx `proxy_read_timeout` 默认 60s / 云 LB 空闲超时）——服务端心跳以 20s 周期喂活所有读计时器，是标准兜底。35s 周期的历史观测（30s receiveTimeout + 5s 重连）已被 FIX-51 消除客户端侧成因；服务端心跳补上服务端侧的最后一块。

## 4. 改动文件（gateway/mobile 零改动）

| 文件 | 改动 |
|---|---|
| `backend/app/core/sse.py` | `event_generator`：`queue.get()` → `asyncio.wait_for(queue.get(), timeout=SSE_HEARTBEAT_INTERVAL)`；超时 yield `: heartbeat\n\n` 后 continue。事件路径逐字节不变 |
| `backend/app/config/phase5_config.py` | 新增 `SSE_HEARTBEAT_INTERVAL: float = 20.0`（SSE 配置段） |
| `backend/.env.example` | 新增 SSE 段注释（键说明 + 默认值 + 覆盖方式） |
| `backend/tests/core/test_sse_heartbeat.py` | 新增，6 个用例（见 §5） |

鉴权面（FIX-51/V23 的 `/galaxy/events` 鉴权与 `Last-Event-ID` 重放）未触碰；`sse_manager` 的连接管理/重放逻辑未改动。

## 5. 红→绿 + 回归统计

**红**（实现前）：`tests/core/test_sse_heartbeat.py` **6/6 FAILED**——配置键不存在 + 空闲期 generator 永久阻塞无输出（`asyncio.wait_for` 收帧超时）。

**绿**（实现后）**6/6 PASSED**：
1. `test_event_generator_emits_heartbeat_when_idle` — 空闲期按配置间隔产出心跳帧
2. `test_heartbeat_is_safe_comment_frame` — 纯注释帧（无 `event:`/`data:` 行，mobile 必然忽略）
3. `test_real_events_frame_order_untouched_and_heartbeat_only_when_idle` — 红线面：事件帧与旧实现**逐字节一致**、帧序不变；队列清空后才出现心跳
4. `test_event_during_heartbeat_wait_is_not_lost` — 心跳等待期到达的事件不丢（wait_for 完成语义）
5. `test_heartbeat_interval_is_configurable` — 间隔可配置生效
6. `test_default_heartbeat_interval_is_twenty_seconds` — 默认 20s 锚定

**回归**（pytest 绝对路径 `/opt/homebrew/bin/pytest`，`SECRET_KEY` 进程内哑值，worktree 无 .env，零 docker/零模拟器）：
- SSE 直接相关：`tests/core/test_sse_heartbeat.py` + `tests/services/test_evidence_pack_sse.py` + `tests/test_v2_agent_integration.py` = **8 passed**；
- 扩面（`tests/core/` 全目录 + `test_phase4_galaxy_services.py` + `test_f16_galaxy_weak_node_injection.py`）：出现 53 项 FAILED/ERROR，用纪律规定的 `/tmp` HEAD 克隆基线对照（`git clone wt92 /tmp/sse-hb-baseline`，含 HEAD@f119a9c0），**失败集合与 HEAD 基线逐项相同（diff 为空）**——全部预先存在（celery beat 守卫依赖、`TaskEventListener` 签名漂移等已知债务），本次改动**零回归**；
- 附注：基线对照需先本地 `grpc_tools.protoc` 生成 `backend/app/gen/`（gitignored 产物，worktree 原缺失）；`test_evidence_pack_sse` 在生成前因 `ModuleNotFoundError: app.gen` 无法收集，同为环境缺口非代码问题。

## 6. 端到端保活效果推断与需实机验证点

**推断**：engine 20s 注释帧 → gateway `FlushInterval=-1` 立即刷出 → mobile Dio stream 收到字节 → `_parseSSE` 返回 None 静默忽略。任何中间层读计时器每 20s 被重置一次，空闲断连应消失。有真实事件时事件帧先行、心跳仅在空闲期出现（测试 3 佐证），帧序与事件语义不受影响。

**需实机验证**（本任务 LIGHT 纪律未起栈）：
1. 真机/模拟器连 dev 栈，idle >5 分钟观察 `/galaxy/events` 是否仍断（改前 ~35s~60s 断一次）；
2. 抓包或网关日志确认 `: heartbeat` 帧经 nginx/反代后确实到达 mobile（验证部署链无额外缓冲吞帧——引擎已带 `X-Accel-Buffering: no`，理论上无缓冲）；
3. 若生产 nginx 有独立 `proxy_read_timeout < 20s` 的特殊配置，相应调小 `PHASE5_SSE_HEARTBEAT_INTERVAL`。

## 7. 收工核查声明

- [x] 只写 worktree（wt92）；主仓只读未动
- [x] 未创建 .env；测试用 `SECRET_KEY` 进程内哑值
- [x] LIGHT：未起 docker 栈、未跑全量、零模拟器、零 Gradle/浏览器
- [x] /tmp 已清：`sse-hb-baseline/`、`sse-hb-patchtest/`、`sse-hb-*-failures.txt` 全部删除
- [x] 持久产物仅：`v3-output/SSE-HB/changes.patch` + `REPORT.md`（changes.patch 已在干净 HEAD 克隆上验证 `git apply` 成功且 6/6 绿）
- [x] 未 commit / 未 push；worktree 内工作区改动即 patch 所含 4 文件
