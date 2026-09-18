# 引擎恢复风暴专项（engine-restore-storm）

> 2026-09-18 深夜实测实证 → 根因定性 → 引擎侧修复 → 红绿压测对比。
> 基线：`b21dce46`。产出：本报告 + 同目录 `engine-restore-storm.patch`。

## 0. 一句话根因

**恢复风暴把 ~20 个并发请求打进引擎，galaxy/graph 在 `async def` 路径里同步调用 Celery `send_task`（星域回填投递），因 result store 故障触发 kombu 重连重试，每次同步冻结整个 asyncio 事件循环 ~19s；循环冻结使所有并发请求（aurora、user/settings、telemetry、community/ws 代理）排队超过网关 30s 超时 → 503/502 雪崩。**

次要放大因子：`get_current_user` 在请求事务内 upsert `user_sessions`（同一 session 行锁持有到请求结束），风暴下轻端点在行锁上二次串行化。

## 1. 根因画像（日志 + 代码走读实证）

### 1.1 时间线铁证

网关日志（`/private/tmp/gateway_server.log` 21:25-21:26 窗口）：

| 时刻 | 现象 |
|---|---|
| 21:25:46 | 客户端会话恢复，~20 请求在 1s 内涌入（users/me、user/settings、growth/dashboard、tasks、galaxy、aurora×N、community/ws、ws/ticket、telemetry batch…），首波 90-440ms 正常返回 |
| 21:25:49 | 第二波请求劣化到 2-3.5s（开始排队） |
| 21:26:20 | `community/ws/connect` **502（19.211s）** —— 与引擎事件循环冻结窗口精确吻合 |
| 21:26:26 | `galaxy/graph` **503（30.0018s）**；`galaxy/events` 30.0s 后才 200 |
| 21:26:35 | aurora/control-surface、aurora/core-session/current、user/settings、understanding-snapshot、comeback-context、telemetry batch ×3、galaxy/graph **连环 503，全部精确 30.0s**（网关 REQUEST_TIMEOUT_SECONDS=30） |
| 21:26:41 | `predictive/realtime-next-step` 500（LLM 400：`Unsupported model mimo-v2-flash`，独立配置问题，见 §6） |

引擎日志（`/private/tmp/engine_api.log`）——事件循环冻结的直接证据，全天共 4 次、每次 ~19.2s：

```
19:47:33.289  [GLMBatch] enqueue node_sector_backfill ...
19:47:52.520  enqueue failed ... "Retry limit exceeded while trying to reconnect to
              the Celery result store backend. The Celery application must be restarted."
              → 19.23s 冻结
20:03:29.783 → 20:03:48.936   19.15s 冻结
21:26:01.766 → 21:26:20.942   19.18s 冻结   ← 与网关 502/503 雪崩窗口精确吻合
21:26:21.069 → 21:26:40.239   19.17s 冻结
```

### 1.2 逐项定性（排查过的假设）

| 假设 | 结论 | 证据 |
|---|---|---|
| FastAPI 单进程？ | 非主因（单 uvicorn 进程属实，但 20 并发远未到 uvicorn/anyio 上限） | 风暴前首波 90-440ms 全部正常 |
| 同步阻塞占满事件循环？ | **是，主因** | `glm_batch_service.enqueue_node_sector_backfill`（galaxy graph 路径）与 `scheduler_service` 两处直接 `celery_app.send_task()`（同步 kombu 网络调用）；result store 故障时每次冻结 ~19s（engine log 4 次实测）；RED 压测中 `/health` 最大滞后 45,013ms |
| DB 连接池耗尽？ | 否 | 全天日志 0 条 `QueuePool limit`；池配置 20+40，风暴并发 ~20 |
| CPU 密集（galaxy 图计算）？ | 否 | galaxy 单次全量计算 ~50ms 级（GREEN 实测 p50 68ms 含首算）；瓶颈在投递不在计算 |
| Celery result store 为何坏？ | 引擎进程 REDIS_URL 指向错误密码/db 的 Redis（启动日志 `Redis Cache connection failed: invalid username-password pair`），celery `task_ignore_result=False` 使每次 `send_task` 绑定 AsyncResult → result backend 重连风暴 | grpc_server 19:44 崩溃栈 + engine_api.log 重连失败栈 |

### 1.3 代码走读（放大链）

```
Flutter 恢复 → 网关代理 → GET /galaxy/graph
  └─ GalaxyService.get_galaxy_graph()
      └─ NodeSectorService.ensure_backfill_for_user()        # pending 节点常在
          └─ glm_batch_service.enqueue_node_sector_backfill()
              └─ celery_app.send_task(...)                   # 同步！task_ignore_result=False
                  └─ kombu result-store 重连重试             # 冻结事件循环 ~19s
                      ↓ 事件循环冻结
      所有并发请求（含 /health）停摆 → 网关 30s 超时 → 503 雪崩
```

次级放大：`deps.get_current_user / get_optional_current_user` → `touch_session` 在**请求事务内** upsert `user_sessions`（`get_db` 在请求结束才 commit）→ 恢复风暴同 session 的 12+ 请求在行锁上串行化到请求时长（GREEN 中间态实测：非 galaxy 端点全部 45s 超时）。

## 2. 修复（引擎侧三道防线，15 个文件）

### 2.1 新增

| 文件 | 内容 |
|---|---|
| `backend/app/core/celery_dispatch.py` | `dispatch_task_async()`：`run_in_executor` 把同步 `send_task` 挪出事件循环 + `wait_for` 3s 超时熔断 + `ignore_result=True`（fire-and-forget 不绑定 result store）；永不抛出，失败记 WARNING |
| `backend/app/core/request_coalescing.py` | `EndpointShield`：① 同 key single-flight（在飞合并，恢复期重复拉取只算一次）② 短 TTL 结果缓存（5-10s，恢复场景等价）③ 端点级 semaphore 并发钳制（8/4）④ 过载 shedding：等待超 8s 抛 `EndpointOverloaded` → 全局 503 + Retry-After，快速失败优于无限排队 |
| `backend/tests/core/test_request_coalescing.py` | 7 测：20 并发合并为 1 次计算、TTL 命中/过期、失败不污染缓存、钳制峰值≤max、过载 shedding、观测计数 |
| `backend/tests/core/test_celery_dispatch_async.py` | 3 测：send_task 同步卡 5s 时事件循环心跳不冻结、超时熔断返回 False、成功路径必须 `ignore_result=True`、失败吞异常 |

### 2.2 修改

| 文件 | 变更 |
|---|---|
| `app/services/glm_batch_service.py` | `enqueue_node_sector_backfill` → async，走 `dispatch_task_async`（根因点） |
| `app/services/node_sector_service.py` | 调用点 await 适配 |
| `app/services/scheduler_service.py` | 两处直接 `send_task`（进程内周期 tick，空闲期 14-24s 周期性冻结的来源）→ `dispatch_task_async` |
| `app/services/auth_session_service.py` | 新增 `touch_from_payload_detached`（独立短事务 + 立即 commit，锁持有 ~ms）；`touch_session` 增加 freshness-skip（`SESSION_TOUCH_MIN_INTERVAL=5s` 内跳过重复 touch，A1 语义保持：跳过不写库不可能复活撤销会话） |
| `app/api/deps.py` | `get_current_user` / `get_optional_current_user` 的 touch 改为 detached 后台短事务（元数据在调度前同步提取，不跨生命周期持有 Request） |
| `app/main.py` | `EndpointOverloaded` 全局处理器 → 503 + `Retry-After: 2` |
| `app/api/v1/galaxy.py` | `/graph`：shield（per-user+查询参数 key，max_concurrency=8，TTL 10s） |
| `app/api/v1/aurora_status.py` | `/control-surface`：shield（TTL 8s） |
| `app/api/v1/aurora.py` | `/comeback-context`（TTL 8s）、`/core-session/current`（TTL 5s）：shield |
| `app/api/v1/predictive_analytics.py` | `/realtime-next-step`：shield（key 含 body 摘要，max_concurrency=4，TTL 5s；`EndpointOverloaded` 不降级为 500） |
| `tests/unit/test_auth_session_touch.py` | fake DB 适配 freshness-skip；新增 2 守卫：窗口内 touch 必须跳过 upsert、窗口外必须写库 |

## 3. 红绿压测（20 并发恢复风暴，同机同 env A/B）

方法：httpx AsyncClient 模拟会话恢复（8×galaxy/graph + 4×aurora/control-surface + 3×core-session + 3×comeback-context + 1×user/settings + 1×telemetry batch = 20 req/轮 × 3 轮），同时 50ms 间隔 `/health` 探针测事件循环滞后。**受控复现**：同机分别启动 原始 `b21dce46`（RED）与修复版（GREEN），env 完全一致，`CELERY_RESULT_BACKEND` 指向不可路由地址（10.255.255.1，复现生产 result-store 故障形态）；客户端超时 45s。

### 3.1 数字对比

| 指标 | RED（修复前） | GREEN（修复后） |
|---|---|---|
| TOTAL p50 | **45,000ms**（全部打满客户端超时） | **68ms** |
| TOTAL p99 / max | **45,000ms / 45,000ms** | **1,233ms / 1,233ms** |
| 5xx / 超时错误 | **45/60**（线上等价于网关 30s → 503 雪崩） | **0/60** |
| galaxy_graph（n=24） | 39,327ms（200 但全在冻结后返回） | p50 68ms / p99 803ms（24 请求 → **1 次计算 + 1 次投递**，其余 single-flight/TTL 命中） |
| user_settings / aurora / telemetry | 39.5-40.1s 或超时 | p99 ≤ 1,233ms |
| `/health` 最大滞后（事件循环冻结度量） | **45,013ms**（整窗冻结） | **401ms**（循环始终存活） |
| 每轮墙钟 | 45.01s ×3 | 1.24s / 0.10s / 0.08s（2-3 轮全走 TTL 缓存） |
| 引擎日志 GLMBatch 投递次数 | 1 次（19s 冻结）+ `Retry limit exceeded` | 1 次成功（`ignore_result` 不触 result store，无超时告警） |

线上佐证（修复前实测，未重启生产 dev 引擎）：引擎首拉 `/galaxy/graph` 单请求 **19.431s** 返回，与历史 4 次 19.1-19.2s 冻结一致。

判定阈值：`0 个 5xx && P99 < 5s && /health max lag < 1s` → RED 未过，GREEN 全过。

### 3.2 结论

事件循环冻结（19s→0）+ single-flight 合并（24→1）+ 钳制 shedding 兜底三者在同一故障注入下把 P99 从 45s（雪崩）压到 1.2s，且轻端点不再被重端点拖死。

## 4. 网关 30s 超时行为结论（不改动）

- `NetworkResilienceMiddleware`（`REQUEST_TIMEOUT_SECONDS` 默认 30s）为**总超时末路防护**，超时返回 503 —— 行为合理，保留。
- 主代理路径（`proxyWithHeaders → httputil.ReverseProxy`）**不做上游重试**（`RetryableUpstreamProxy` 仅显式选用），无重试放大 —— 合理，保留。
- ws 代理 19s → 502：合理（比 30s 更快失败）。
- 结论：网关配置不雪上加霜，修复责任在引擎侧（本次已修）；`MaxIdleConnsPerHost: 20` 与恢复突发相当，暂不调。

## 5. 验证与守卫

- 定向单测 15 个全绿：`tests/core/test_request_coalescing.py`（7）+ `tests/core/test_celery_dispatch_async.py`（3）+ `tests/unit/test_auth_session_touch.py`（5，含 A1 回归）。
- 事件循环冻结回归守卫：`test_event_loop_stays_responsive_while_send_task_blocks`（心跳计数断言，防同类问题回流）。
- 生产 dev 引擎未杀未动（本次全程只读参照）；A/B 用临时实例（:8010/:8011）已清理。

## 6. 遗留与建议（未列入本次 patch）

1. **LLM 模型配置错误**：`realtime-next-step` 500 的直接原因是 `mimo-v2-flash` 上游 400（"Unsupported model"），属模型路由配置问题，与风暴无关，建议单独修（`llm_service` 路由表）。
2. 其余请求路径上的同步 `send_task`（`api/v1/capsules.py` fallback、`services/milestone_handler.py`、`services/push_strategies/empty_capsule.py`、`aurora/tasks.py`）建议后续统一迁移到 `dispatch_task_async`；`core/celery_tasks.py` 内部为 worker 侧（独立进程），无事件循环风险。
3. `result store` 指向错误 Redis 是本次故障注入的环境根源：dev 引擎进程的 `REDIS_URL` 与 `CELERY_RESULT_BACKEND` 应对齐 discipline 约定（`redis://:sparkle_dev_redis_2026@localhost:6379/1`）。
4. 网关侧可选增强：对同 user 同 key 的恢复期 GET 做 single-flight 合并（客户端 20+ 请求去重可再降引擎一个量级负载）；本次未动网关。
