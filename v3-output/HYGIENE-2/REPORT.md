# HYGIENE-2 收工报告 — 运行噪音/测试基建债合并清理

- **Worker**：V3 舰队 HYGIENE-2 micro 卡
- **Worktree**：`/Users/brsama/code/GitHub/Sparkle-sysrev/wt151`（基线 `8407daec`）
- **交付物**：本报告 + `changes.patch`（4 个 diff，新文件头 `--- /dev/null`，已对基线 `git apply --check` 通过，零凭据）
- **改动面**（4 文件，零 commit）：
  - 改 `backend/app/core/tracing.py`
  - 改 `backend/tests/conftest.py`
  - 新增 `backend/tests/unit/test_tracing_export_config.py`（11 用例）
  - 新增 `backend/tests/unit/test_redis_fixture_isolation.py`（9 用例）

---

## ① 两债修法论证

### 债 1：otel trace export 噪音 + detach ValueError

**现状根因**：`backend/app/core/tracing.py` 无条件创建 `OTLPSpanExporter` + `BatchSpanProcessor`，endpoint 硬编码默认 `http://localhost:4317`。本机无 collector 时，每次 BatchSpanProcessor 刷批都对死端口做 gRPC export，产生 `Failed to export traces to localhost:4317, StatusCode.UNAVAILABLE` + `Transient error ... retrying` 无限重试噪音（已在 `/tmp/sparkle_grpc.log` 逐行核实）。初始化链路：`grpc_server.py:146`（serve() 内 `from app.core.tracing import tracer`）→ tracing.py 模块级副作用；早于 `GrpcAioInstrumentorServer.instrument()`（:238）。

**修法：默认关 export，保留 span 语义（`tracing.py` 重写）**

1. 新增纯函数 `resolve_export_settings(env)`：`OTEL_EXPORTER_OTLP_ENDPOINT` **未显式设置 → 不挂 exporter**。选"endpoint 显式配置"作为开关依据的证据：本仓**所有**有 collector 的环境都显式设置该变量——`docker-compose.yml`（sparkle_tempo:4317）、`docker-compose.prod.yml`（tempo:4317）、`docker-compose.celery.yml`、`k8s/base/backend.yaml`、`k8s/base/gateway.yaml`、`scripts/run_e2e_smoke.sh`、各 `.env*.example`。所以默认关只影响"裸本机无 collector"场景，collector 环境零行为变化。
2. 同时尊重 OTel 规范标准开关：`OTEL_SDK_DISABLED=true`（SDK 1.40.0 原生读取，`get_tracer` 返回 NoOpTracer——已读安装源码确认）与 `OTEL_TRACES_EXPORTER=none`，两者任一生效均不挂 exporter。为什么不把 `OTEL_SDK_DISABLED=true` 当默认：SDK 层禁用会把 span 降级为 no-op，而 `orchestrator.py:2165-2175` 的 O-02 trace spine **读取真实 span 的 `get_span_context().trace_id`** 作为全链 trace_id——no-op span 会砍断该语义。因此只关"无效 export"，TracerProvider/span 采集原样保留（红线达成，单元测试断言 `is_recording()` 与非零 trace_id）。
3. detach ValueError：定位到库层 `opentelemetry/context/__init__.py:155` 的 `logger.exception("Failed to detach context")`，异常链 `contextvars_context.py:53 reset(token) → ValueError: ... was created in a different Context`——opentelemetry instrumentation-grpc(aio) 跨 task detach 的**已知良性库层问题**（本仓 `orchestrator.py:2159-2164` 注释已记载同一机制）。**选择日志过滤器而非改库**：改库 = vendored patch，升级即丢且越权；suppress 噪音按"三条件全中才过滤"精确匹配（logger=`opentelemetry.context`、msg=`Failed to detach context`、exc=带该 marker 的 ValueError），其余 detach 失败照常记录。实现为 `OtelCrossContextDetachNoiseFilter`，在 tracing.py 导入时幂等挂载（引擎进程先 import tracing 后 instrument，覆盖全部噪音窗口）。债 1 的 export 错误噪音则随 exporter 不挂载而**根除**（无 BatchSpanProcessor → 永不尝试导出），无需过滤器。

### 债 2：根 conftest `redis_client` fixture `flushdb()` 清空 dev redis

**现状根因**：`backend/tests/conftest.py` fixture 直连 `REDIS_URL`（默认 db0，即 dev 数据所在库），teardown 无条件 `flushdb()`——主仓跑一次 redis 消费族测试即清光真实缓存/队列。

**修法：隔离 DB index（方案对比后选择）**

- **选择 db-index 隔离**：新增 `_isolate_test_redis_db()`，用 `urlparse` 把 fixture URL 的 db 段强制改写到 `TEST_REDIS_DB`（env 可覆盖，默认 **15**——redis 惯例测试库），保留 host/port/auth；teardown 仍是 `flushdb()`，但只 flush 隔离库。改动最小（+8 行）、对全部消费者透明（已核实 25 个消费文件全部走构造函数注入 fixture client，无一自行连 db0 再依赖 fixture 清理）。
- **不选 key 前缀+精确清理**：fixture client 是裸 client，业务代码自由写 key、多数据结构（stream/hash/set），前缀方案要求所有写入路径配合，侵入大且漏网即残留。
- **诚实边界**：本卡只修 fixture（卡面范围）。测试中仍有**测试自身**另建裸连直写 db0 的历史用例（如 `tests/test_context_pruner.py` 自带 client、`tests/integration/test_cache_consistency_integration.py` 自带 flushdb），以及服务代码从 `settings.REDIS_URL`（db0）自建 client 的写入路径——均超出本卡 fixture 范围，建议 TEST-DBGUARD 卡后续按域守卫精神收口（对照验证时已注意到 baseline 运行后 throwaway db0 出现 `sparkle_events` 残留 key，即服务自建 client 所写）。

---

## ② 红线面（全部达成）

| 红线 | 验证 | 结果 |
|---|---|---|
| 引擎可启动 | `SECRET_KEY=test python3.11 -c "import app.main"`（worktree 内 `make proto-gen` 后，host 工具链） | **SMOKE_MAIN_OK**，FastAPI app 构造成功 |
| tracing 单元级冒烟 | `import app.core.tracing`：`TRACE_EXPORT_ENABLED=False`、span processors=`[]`、detach 过滤器已挂、span 真实 trace_id 非零 | 通过 |
| 相关配置测试 | 新增 11 用例：export 关/开分支、`OTEL_SDK_DISABLED`、`OTEL_TRACES_EXPORTER=none`、`OTLP_INSECURE`、过滤器 4 态、幂等挂载 | 全绿 |
| 日志断言（无 collector 不刷 export 错） | `test_no_export_error_log_without_collector`：span end 后 caplog 监听 3 个 otel exporter logger，无 `Failed to export`/`Transient error` | 通过 |
| redis fixture 消费族全绿（对比法） | 6 个真 fixture 消费文件（state_manager_real_redis、distributed_lock_real_redis、event_bus_real_redis、event_ack_reliability、context_cache_versioning、orchestrator/mixins/test_session_state_mixin），一次性 redis 容器（:6399）上：**基线克隆 71 passed vs 本卡 71 passed（同族）+ 新增 20 守卫用例 = 91 passed，零新增失败** | 通过 |
| 不碰真 redis | 验证全程用一次性容器 `wt151-hygiene2-redis`（redis/redis-stack-server 本地已有镜像，未拉取）；真 dev redis（sparkle_redis:6379）零连接 | 达成 |
| **行为等价的活证据（金丝雀）** | db0 预埋 `hygiene2:canary:dev-data` 等 2 key：**基线（旧 fixture）跑完 canary 被 flushdb 销毁（债的活体复现）→ 本卡分支跑完 canary 完好、db0 dbsize 不变；测试数据全部落在 db15 且 teardown 后 db15 归零** | 通过 |
| 代码风格 | ruff 0 error（conftest 的 I001 为基线既有，未触碰）；两个新文件 black(120) 干净；tracing.py 保持基线原有风格（基线本身即非 black-clean，最小 diff） | 通过 |

## ③ 冲突面（零交集声明）

本卡改动：`backend/app/core/tracing.py`、`backend/tests/conftest.py`、2 个新增测试文件。

- **wt144（events）**：无交集（未动 events/eventbus 相关任何文件）。
- **wt149（proto+gateway）**：无交集（未动 `proto/`、`backend/gateway/`、`*/gen/`；worktree 内的 `make proto-gen` 产物仅为本地产出冒烟之用，gitignored，已清理）。
- **wt150（词库）**：无交集。
- `grpc_server.py` **未改动**（tracing 导入点原本就先于 instrument，无需改）。

## ④ 诚实申报

1. `import app.main` 冒烟在 worktree 需先 `make proto-gen`（`app/gen` 为 gitignored 生成物，裸 worktree 缺失）——这是环境前置，与本卡改动无关（主仓/CI 有生成物）。
2. detach 噪音过滤器只挂在**引擎进程**（tracing.py 被 grpc_server 导入）。FastAPI(uvicorn) 进程未设置 TracerProvider（instrumentors 走 proxy），未观测到同类噪音日志，故未动 `main.py`（也避免与在途卡的潜在冲突）；若日后 uvicorn 进程出现同形噪音，在 main.py 调 `suppress_otel_detach_noise()` 即可。
3. redis 隔离默认 db15；若某环境 db15 被占用，设 `TEST_REDIS_DB` 覆盖。fixture 强制改写 db 段（即使 REDIS_URL 显式带 db）——语义：该 fixture 拥有测试库，消费者测试无 db 假设（已核实）。
4. `TEST-DBGUARD` 的域守卫（db0 直写类用例、服务自建 redis client 路径）超出本卡 fixture 范围，见 ① 末段边界说明，未顺手扩权修改。
5. conftest.py 的 ruff I001（import 排序）为基线既有问题，本卡未修（不扩大 diff）。
6. 基线对照用 `git clone` 克隆（未 stash/reset/clean 原树）；克隆中补拷了 gitignored 的 `app/gen` 以便同族测试可导入，用后已删。

## ⑤ 收工核查

- [x] 一次性容器 `wt151-hygiene2-redis` 已停删（--rm）
- [x] `/tmp/wt151-baseline` 基线克隆已删除
- [x] worktree 内 `backend/app/gen`、`.pytest_cache`、`__pycache__` 构建产物已清理
- [x] 无残留进程（pytest 单进程已结束；未起模拟器/浏览器）
- [x] 零 commit / 零 push；交付物 = `v3-output/HYGIENE-2/REPORT.md` + `changes.patch`
- [x] patch 零凭据（扫描仅命中测试假 URL 与代码标识符）
- [x] `git status --short` 仅含 2 改 + 2 新增 + v3-output 交付物
- [x] swap 峰值纪律：全程定向单进程 + 单个小容器，未跑宽扫描
