# WT805 — CI 负载敏感测试族处置卡（FIX-544+546）实施记录

- 卡：**V3-FIX-544（Go）+ V3-FIX-546（Flutter）**，CI-only flake 族统一处置，纯测试韧性改造，零产品码改动
- 分支：`agent/node-b/wt805/flakefix`（worktree `/Users/brsama/code/GitHub/Sparkle-sysrev/wt805-flakefix`，base main@3fac2d30）
- 证据源：CI 28 job 108763067538（Go 5.00s 超时实录，已下载复核）；CI 29 run 36372459978 attempt 1/2 全量日志（job 108772804580）；近 100 run 失败 Flutter job 全量扫描
- 硬约束遵守：不改产品码、不碰运行栈与 ns001、不 push、不改台账（闭账归主会话）

## 1. FIX-544（Go）：`TestRunLiveProcessFailureStillLogsError` 5s 预算放宽

**实录复核（CI 28 job 108763067538 原始日志）**：

```
base_test.go:118: log entry "Error processing messages" not observed within 5s
--- FAIL: TestRunLiveProcessFailureStillLogsError (5.00s)
```

失败点即 `base_test.go:118` 的 `waitForLogEntry(..., 5*time.Second)`。健康路径实测 ~1.6s：`mr.Close()` 后 go-redis 连接池 5 次 dial 重试 + 命令级退避吃掉大半预算（CI 通过 run 中该测试稳定 1.59-1.60s），5s 余量仅 ~3.4s，共享 runner 负载下失守。CI-28 失败日志可见 dial 失败横跨 02:28:05→08+，真实到达晚于 5s 预算。

**修法（`backend/gateway/internal/cqrs/worker/base_test.go`）**：

- `waitForLogEntry` 本就是相对等待先例（10ms 轮询至断言成立），5s 是预算不是固定 deadline。line 118 预算 **5s → 30s**（V3-FIX-544 注释：健康路径时长不受影响，等待成立即返回，只消负载假阴性；30s ≈ 健康路径 19×，覆盖 CI 实测最坏形态）。
- 同测试内 line 114 `waitForLogEntry(..., "Worker started", 2s → 10s)`：同根因（负载拖慢 goroutine 启动与日志落表）、同测试、同语义保持，一并放宽防同类新形态。
- 同文件另一测试（`TestRunGracefulShutdownLogsNoError`）未动，列入候选清单。

**验证**：

- `go test ./internal/cqrs/worker/ -count=5` → **ok，18.743s**（0 失败）
- 负载模拟（40×`yes` CPU 饱和 + `nice -n 20`）：新版全包 **ok 4.590s**；旧版（main worktree 原样）单测 10/40 loader 两档均 1.59-1.60s 过——**本地红不可构造**（dial 失败路径 I/O 型，本地调度仍及时），与「CI-only」定性一致，按卡预案以「改造前后语义等价论证+本地多次跑」交付：断言语义不变（仍要求 ERROR 日志真实出现），只放宽到达预算；CI-28 实测到达时间 >5s，30s 覆盖。
- `gofmt -l` 空、`go vet` 干净。

## 2. FIX-546（Flutter）：startup_error_screen_test「fake 30s 窗」排查结论——**前提不成立**

**排查过程（全量证据，非抽样）**：

1. 台账所指 CI 29 job 108772804580：attempt 1 原始日志（`gh api jobs/108772804580/logs`）显示 startup_error_screen_test 三测**全部 ✅**，`2636 tests passed, 1 failed`——唯一红是 `chat_value_signal_test.dart`（"failed after test completion"）。attempt 2 rerun 全绿。
2. 近 100 个 run 的失败 Flutter job 全量扫描（108537080209 / 108317401600 / 107916115667 / 107905868267 / 108772804580）：失败测试分别为 history-sheet×3、evidence_cards×2、understanding_overview、group_chat_index_shift、chat_value_signal——**startup_error_screen_test 在扫描窗内从未红过**。
3. CI 日志里的 `❌ STARTUP RETRY FAILED: TimeoutException-marker after 30000ms (fake)` 及 `#0` 堆栈，是**产品码 `_handleRetry` catch 块的 debugPrint**（main.dart:293，A-3 设计：debug 构建落原始异常进日志），**通过的测试也会打**。CI 29 轮的主会话归因把这段噪声误读为测试失败形态。
4. 「30s 窗」定性：既非 fake-async 窗也非真实计时——`after 30000ms` 是 `_FakeTimeoutFailure.toString()` 里的**死文本**，测试无任何 Timer/pumpUntil；全部交互走 tester.pump（fake-async 虚拟时间），对 runner 负载免疫。**不存在可放宽的窗。**

**处置（`mobile/test/app/startup_error_screen_test.dart`）**：

- 测试断言流零改动（确定性、CI 零败绩，无可修缺陷）。
- 韧性改造落在**消除误导性时间信号**：fixture 文案 `TimeoutException-marker after 30000ms (fake)` → `TimeoutException-marker (fake fixture text; no timer, no window)`，并留 V3-FIX-546 复核注释。分类键 `TimeoutException` 前缀保持（timeout 类判定依赖它），断言 `textContaining('TimeoutException-marker')` 前缀兼容。目的：杜绝下次把 fixture 死文本 + 产品 debugPrint 噪声再误诊成时窗超时。

**CI 29 真红另案建议（超本卡范围，只列证）**：`chat_value_signal_test.dart`「访客收到规划类 AI 输出→记录 firstDiagnosisOutput」failed after test completion——栈：`chat_provider.dart:1388 ChatNotifier.sendMessage` 后台续延经测试 `_ContainerForwardingRef.read` 触发 `subscriptionsProvider` 建，`SubscriptionsNotifier.loadSubscriptions` 在容器 dispose 后写 state → `Bad state: Tried to use SubscriptionsNotifier after dispose`。干净修法大概率在产品侧（dispose 后读保护/取消）或测试容器生命周期治理，测试单侧修不彻底，建议独立卡（findings 已具备：job/attempt/完整栈）。

**验证**：`flutter test test/app/startup_error_screen_test.dart` **3× 全过**（每次 +3）；`flutter analyze`（限改动文件）No issues；ruff 不适用（无 Python 改动）。

## 3. 同类「固定预算 + CI 负载敏感」候选清单（只列不修）

Go（backend/gateway，`*_test.go` 短预算 select/轮询等待）：

| 位置 | 形态 | 风险注记 |
|---|---|---|
| `internal/cqrs/worker/base_pel_redelivery_test.go:94,105,116,243` | `time.After(5s)`×4（waitForEvent/waitForEventID/drainWorker） | **最高优**：与 FIX-544 同包同依赖（miniredis+worker 回环），同负载形态 |
| `internal/cqrs/worker/base_test.go:80` | `time.After(5s)`（shutdown 测试 Run 返回等待） | 同文件同类 |
| `internal/handler/chat_orchestrator_disconnect_test.go:123` | `time.After(5s)` | |
| `internal/service/file_event_subscriber_restart_test.go:113` | `time.After(5s)` | |
| `cmd/server/setup_detached_rebuild_test.go:38` | `time.After(2s)` | 2s 级最紧 |
| `internal/handler/ws_shutdown_drain_test.go:79`、`internal/middleware/ab_test_bounded_test.go:42`、`internal/cqrs/event/redis_bus_test.go:88`、`internal/service/{file_event_hub:230,chat_history_backfill:22,69,signal_hub:119,cache_integration:531}_test.go` | `time.After(2s)` 批 | 同族批量 |

Flutter（mobile/test，真 wall-clock 窗优先）：

| 位置 | 形态 | 风险注记 |
|---|---|---|
| `test/app/cold_start_release_test.dart:165-177` | `waitFor` 谓词轮询，**真时钟** `DateTime.now()` 2s 预算 | 启动链路 + 真时窗，CI 负载敏感最典型 |
| `test/widget/group_chat_index_shift_reparent_test.dart:57` | `Hive.close().timeout(3s)` 真窗 | 同族 `group_chat_search_locate_test` 已于 9/27 CI 红过一例（job 107905868267） |
| `test/core/network/token_refresh_coordinator_test.dart:554` | timeout 默认参 2s | |
| `test/core/services/websocket_service_test.dart:165,200`、`websocket_service_reconnect_budget_test.dart:140,217` | 10s/3s 预算 | 中风险 |
| `test/integration/full_stack_e2e_test.dart`（多处 10s） | 真网络栈 | 集成面，视 CI 纳入情况 |

另案（非固定 deadline 族）：`chat_value_signal_test.dart`（见 §2 真红）。

## 4. 交付

- 分支 `agent/node-b/wt805/flakefix` @ base 3fac2d30，commit：`fix(tests): wt805 V3-FIX-544/546 CI 负载敏感测试族韧性改造`
- 改动文件：`backend/gateway/internal/cqrs/worker/base_test.go`、`mobile/test/app/startup_error_screen_test.dart`、本 notes
- 未 push；台账未动；worktree `mobile/lib/gen/` 为本地构建所需生成物拷贝（gitignored，不入库）
