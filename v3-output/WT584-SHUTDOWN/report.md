# WT584-SHUTDOWN — `test_shutdown_cancels_tracked_background_tasks` ~62s 空窗根因诊断

- 工位：wt584 ｜ 分支：`agent/node-b/wt584/shutdown`（基线 = main 头 63d4e67a）
- 日期：2026-09-25（本地）｜ 诊断卡：先诊断后定夺；**未改任何产品代码/测试**（根因在测试基建第三方插件，修法属 CI 配置范畴，超出本卡授权面，只留证+建议）
- 上游依据：[WT577-PROFILE](../WT577-PROFILE/report.md) §1/§4——CI run 36253679384 job 108452479615 日志中，`backend/tests/workflow/test_orchestrator_resilience_workflow.py::test_shutdown_cancels_tracked_background_tasks` 相邻结果行差 **61.9s**（全 suite 第 2 大空窗，且是最后一个用例），测试体与被测 `ChatOrchestrator.shutdown()` 均无 sleep。

---

## 0. 结论先行

**62s 空窗与被测 shutdown 路径完全无关，也不是该测试慢（其真实生命周期 0.31s）。** 根因是 **pytest-cov 的覆盖率报告生成税**：pytest-cov 给 `pytest_runtestloop` 挂了一个 old-style hookwrapper，其 **post-yield**（全部用例跑完后）调用 `CovController.summary()` → `coverage report() + xml_report()` → 对**每个被测过的源文件**做 `ast.parse` + CodeType/arc 分析。全量 marathon 后堆达 ~2.8GB、GC 高频触发，这段解析在本地 10 核机实测 **35.95s**、CI 4 核 runner 为 **61.9s**。它发生在"最后一个用例结果行已写"与"session 收尾输出"之间，零日志输出，被 WT577 的"相邻结果行差法"记到**收集顺序最后一个用例**（字母序 `tests/workflow/…` 恰好殿后）头上。

**生产影响面裁决：无。** 被测 `ChatOrchestrator.shutdown()` 与生产 gRPC 关停链无 60s 量级挂起点（§5）。这是纯 CI 时长画像/分片方案的输入，不是产品缺陷单。

## 1. 被测代码事实

- 测试：`backend/tests/workflow/test_orchestrator_resilience_workflow.py:62`（全文件 3 例，本例最后）。`FakeTask.cancel()` 只置 flag，`__await__` 为 no-op；fixture patch 了 `orchestrator.asyncio.create_task`（即全局 `asyncio` 模块属性）与 graph 工厂，`ChatOrchestrator(db_session=MagicMock(), redis_client=MagicMock())` 全程无真实 IO。
- 被测：`ChatOrchestrator.shutdown()`（`backend/app/orchestration/orchestrator.py:1657`）= 对 `_bg_tasks` 逐个 `cancel()` 后 `asyncio.gather(..., return_exceptions=True)`，**无超时**。
- `_track_task` 委托 `backend/app/core/background_tasks.py:register_tracked_task`（强引用 + done-callback 异常日志）；FastAPI 侧收口 `shutdown_tracked_tasks(timeout=5)`：先 5s 宽限后 cancel，最后 gather 同样无超时。
- 生产关停链：`backend/grpc_server.py:110 GracefulShutdown.shutdown()` → `server.stop(grace=5.0)` → `orchestrator.shutdown()`（无超时 gather）→ `galaxy_event_bridge.stop()` → `cache_service.close()`。FastAPI 侧（`app/main.py` lifespan）是另一进程，关停链自带逐步 cancel+await 与 5s 宽限 drain。

## 2. 本地复现

**2.1 单例（不可复现，证明与测试体无关）**

`DATABASE_URL='sqlite+aiosqlite:///:memory:' SECRET_KEY=v TZ=UTC`，Sparkle-project venv，3 次：

| run | pytest 自报 | 墙钟 | setup/call/teardown |
|---|---|---|---|
| 1 | 4.28s | 6.90s | 全部 <5ms |
| 2 | 2.47s | 4.77s | 全部 <5ms |
| 3 | 2.11s | 4.05s | 全部 <5ms |

自报时长 ≈ collection/导入开销；被测生命周期毫秒级。

**2.2 CI 同构全量跑（复现成功，35.95s）**

命令与 ci.yml:283 逐字对齐（`pytest backend/tests -v --cov=backend/app --cov-report=xml --timeout=300 --timeout-method=thread`，本地 postgres/redis 容器 + `sparkle_test` 已迁移），外加会话产物级探针（`/tmp/wt584-shutdown-run/`，不入库）：`-p wt584_plugin` 以文件实时记录生命周期边界 + 静默看门狗（`phase.log` 停更 ≥5s 即 `sample` 抓 native 栈；py-spy 在 macOS 需 root 不可用）。结果 35:45 跑完（本地机快于 CI）：

```
2110.014s  shutdown 测试 setup        dur=0.005s
2110.313s  shutdown 测试 teardown     dur=0.298s   ← 测试真实生命周期 0.31s
2110.313s  runtestloop EXIT
2146.260s  sessionfinish ENTER                     ← ★ 35.95s 零日志静默段
2146.289s  sessionfinish EXIT        (29ms)
2146.325s  terminal_summary ENTER→EXIT (16ms)
2156.449s  atexit                                 ← ★ 解释器退出另花 10.1s
```

`--durations=60` 里**没有** shutdown 测试（它 0.3s）；第 2 名的 61.9s"净时长"实为上面 ★ 段。35.95s ÷ CI 61.9s 同一位置、同一量级（4 核 vs 10 核），且**与用例数无关**：仅 4 例的子集跑（`pytest backend/tests/workflow` 同 flags）同样复现——两轮分别为 23.4s（runtestloop EXIT +5.444s → sessionfinish ENTER +28.804s）与 25.9s（带打点轮，`CovController.summary ENTER +5.548s → EXIT +31.417s`）。

**2.3 栈级定罪（compile 探针 + native sample）**

用第二个探针插件 wrap `builtins.compile` 并给 `CovController.finish/summary` 打点，静默段内每次 compile 均落日志。第一发全栈（截取关键链）：

```
_main (main.py:372)  → pluggy _multicall:152（old-style wrapper post-yield）
→ pytest_cov/plugin.py:362 pytest_runtestloop        ← pytest-cov 给 runtestloop 挂的 hookwrapper
→ pytest_cov/engine.py:143 summary（post-yield 执行）
→ coverage/control.py:1172 report → coverage/report.py:210 report
→ coverage/report_core.py:98 get_analysis_to_report → coverage/control.py:1013 _analyze
→ coverage/python.py:192 parser → coverage/parser.py:264 parse_source → ast.py:50 parse
```

4 例子集的静默段内：**5,090 次 compile（ast.parse + CodeType 双遍解析）+ 30,232 次 GC 事件**，无一单独大头（最大 inter-compile gap 0.25s）——纯"每个被测文件一遍 AST/arc 分析 × 2.8GB 堆上高频 GC"的死亡千刀。native `sample` 同窗口显示主线程深陷 `builtin_compile → ast2obj_stmt/ast2obj_expr`（AST→Python 对象转换），与探针互证。

版本差异核对：本地 pytest 9.0.2 / coverage 7.13.5 / pytest-cov 7.1.0 vs CI 9.0.3（requirements.lock）——同代插件架构，行为一致。

## 3. CI 日志深度取证（`/tmp/wt577-profile/backend_tests_a2_108452479615.log` 原始件复核）

1. 62s 空窗 = `19:03:28.455`（文件内第 2 例结果行）→ `19:04:30.3499`（本例结果行）；其后 0.1ms 即 `=== FAILURES ===` 头，"Coverage XML written to file coverage.xml"（19:04:30.445 批次）证明 CI 的 coverage 报告生成确实在收尾窗口内执行。
2. **尾段时间戳不可信的独立证据**：short summary 区内 `FAILED …test_daily_stats_denominator… - AssertionError:`（19:04:30.4486）与其续行 `assert 0 == 1`（19:04:48.511）间隔 **18.1s**——同一次 pytest 写入序列的两行，只能是缓冲/管道冲刷伪影；step 退出标记也比 pytest 末行晚 17.3s。因此"相邻行差"画像在套件尾部会把**所有静默尾税**记给最后一个用例。
3. 时间轴重构（与本地实测一一对应）：
   - 19:03:28.5 最后用例结果行写入缓冲（测试本身 0.3s）；
   - **pytest-cov runtestloop-wrapper post-yield：coverage 报告 AST 解析风暴，静默 61.9s**（CI 版 §2.2 ★ 段）；
   - 19:04:30.35 终端 summary（FAILURES/coverage 表/short summary）写满缓冲 → 冲刷成 .3499-.445 批次；
   - 19:04:30.45→19:04:48.5 `Py_FinalizeEx → _PyGC_CollectNoFail` 解释器退出全量 GC（本地实测 10.1s，CI ~18s；本地 atexit 段 native sample 主线程即在 `finalize_modules → _PyGC_CollectNoFail → gc_collect_main`）；
   - 19:05:05.78 runner 侧退出标记。

## 4. 裁决与修法建议（不实施）

**裁决：测试装配/基建问题（coverage 报告税 + 解释器退出 GC 税），非产品问题。** `ChatOrchestrator.shutdown()` 生产语义无恙（§5），该测试 0.3s 真身清白。不删断言、不改产品代码、不动 ci.yml（修法属 CI/分片卡范畴，交主会话与 WT577 后续卡决策）。

修法选项（供 WT577 分片方案参考，按侵入度排序）：

1. **观测面修正（零风险）**：WT577 画像脚本的"相邻行差"法应在说明中标注"套件最后一个用例的时长含 coverage 报告税 + 退出 GC 税（约 CI 62s + 18s）"，避免再立错案；`--durations` 不受此污染（它按 phase 计时，本次已证）。
2. **把报告生成挪出 pytest 进程（-CI 62s + 18s 中的 62s）**：ci.yml:283 改 `--cov-report=`（只落 `.coverage` 数据），随后独立步跑 `coverage xml`。CPU 总量不变，但 (a) pytest 退出更早、失败反馈更早；(b) 3-shard 方案下每片都要出的这份税可与别的片并行；(c) 失败即红的片不必再花 62s 生成没人看的 XML。**注意税不会消失，只搬家**——是否值得取决于分片方案的整体编排。
3. **治本面（更大工程，不建议现在做）**：coverage 的 AST 分析成本随被测代码规模增长；缩减 `--cov=backend/app` 面（如排除 `app/gen`）可线性减税。`app/gen` 是生成物，理应排除在覆盖率统计外（现 ci.yml `--cov=backend/app` 把 gen/ 也测了）。

## 5. 生产影响面（顺带核查，全部无恙）

- `_bg_tasks` 真实来源：`breaker.initialize()`（orchestrator.py:375）、turn 收尾 `finalize_task`（:3883）、stream 后处理 task（:3973）、`_extract_and_persist_skill`（:4016）。均为纯 asyncio 协程；无 `shield()`、无 `except BaseException`（grep 全 orchestration/ 为空）；`except Exception` 在 py3.11 不吞 `CancelledError`（继承 `BaseException`）→ cancel 后 gather 正常收敛。
- `background_tasks.shutdown_tracked_tasks` 的宽限 drain 有 `timeout` 上界；最后的 gather 无超时但对象均为已 cancel 任务，收敛语义成立。
- 风险备注（登记不修）：两处收尾 `gather` 无超时是隐式约定（"被追踪协程必须可被干净取消"）。未来谁加了 shield/阻塞 IO/`except BaseException`，SIGTERM 就会拖到 K8s `terminationGracePeriod` 兜底 SIGKILL。低成本加固：gather 包 `asyncio.wait_for(..., 5~10s)` 并对残留者记 warning。属独立小卡素材，非本空窗根因。

## 6. 证据清单

- CI 原始日志：`/tmp/wt577-profile/backend_tests_a2_108452479615.log`（27,701 行，会话产物；本卡复核了 62s 空窗上下文、18s mid-summary 伪影、Coverage XML 行、退出标记时序）
- 本地复现产物：`/tmp/wt584-shutdown-run/`（会话产物不入库）：
  - `pytest_v.log` 全量跑输出（含 `--durations=60`）；`phase.log` 生命周期边界（★ 35.95s 段出处）
  - `postloop_subset.log` compile/GC 打点（5,090 compile + 30,232 gc；FIRST-COMPILE 全栈定罪 pytest_cov/engine.py:143 summary → coverage parser）
  - `phase_subset.log` 4 例子集（summary ENTER→EXIT = 23.4s/25.9s 两次实测）
  - `sample_*.txt` native 栈（静默段 ast2obj、atexit 段 `_PyGC_CollectNoFail`）；`wt584_plugin*.py`、`watchdog.sh`、`runner.sh` 探针脚本
- 代码：`backend/tests/workflow/test_orchestrator_resilience_workflow.py`、`backend/app/orchestration/orchestrator.py:1648-1663,375,3883,3973,4016`、`backend/app/core/background_tasks.py`、`backend/grpc_server.py:102-128`、`backend/app/main.py:600-880`
- 插件源码：pytest-cov 7.1.0 `plugin.py`（`pytest_runtestloop`/`pytest_sessionfinish` hookwrapper，`pytest_sessionfinish` post-yield 调 `finish()`+`summary()`）与 `engine.py:143 summary()`（`cov.report` + `xml_report`）
