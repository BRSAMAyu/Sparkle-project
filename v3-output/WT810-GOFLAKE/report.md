# WT810 — Go deadline flake 族预算改造（FIX-551/552/553）报告

- 分支：`agent/wt810/goflake`（worktree `/Users/brsama/code/GitHub/wt810`，base main@1f62b36c）
- 上游依据：wt805 报告 `v3-output/WT805-FLAKEFIX/notes.md` §3 候选清单（13 组 Go 候选，FIX-544 同形改造）
- 号段预分配：**本卡只用 551/552/553**（协调方预分配；另一并行卡占用 548-550——若其落账在先，本卡三号为顺延预留，无撞号）。行内均注明预分配来源。
- 硬约束遵守：零产品码改动（`backend/gateway/internal/` 非 `_test.go` 零触碰）、零断言删除、零 `t.Skip` 新增、未 push。

## 1. 选组依据（13 组 → 3 组，CI 红风险排序）

| 排序 | 组 | 位置 | 选择理由 |
|---|---|---|---|
| 1 | base_pel_redelivery_test.go（FIX-551） | `internal/cqrs/worker/`，`time.After(5s)`×4 + PEL 轮询 2s | wt805 候选表标注**最高优**：与 CI 实红（FIX-544，CI 28 job 108763067538）同包同依赖（miniredis+BaseWorker 回环、go-redis 池 dial 重试吃预算）、同负载形态；且文件内 PEL 轮询窗 2s 是同文件第二紧预算 |
| 2 | base_test.go shutdown 测试（FIX-552） | `internal/cqrs/worker/`，`waitForLogEntry(2s)` + `time.After(5s)` | **CI 实红文件内**（FIX-544 修了同文件另一测试，wt805 明示本测试未动、列入候选）；`Worker started` 2s 与 FIX-544 修掉的 2s 同根因 |
| 3 | setup_detached_rebuild_test.go（FIX-553） | `cmd/server/`，`time.After(2s)` + `require.Eventually(2s)` | wt805 候选表标注「**2s 级最紧**」；等的是裸 goroutine 首次调度，CPU 饱和 runner 上调度延迟可秒级，2s 余量最小 |

**排除理由（其余 10 组，防后续重复排查）**：

- `internal/cqrs/event/redis_bus_test.go:88`、`internal/service/cache_integration_test.go:531`——**CI 红风险≈零**：两文件无真 Redis 即 `t.Skip`（`REDIS_URL`/`REDIS_ADDR` 探测），CI 无 Redis 环境（`redis_bus` 主测还自带 skip 闸门），永不执行等待路径。
- `internal/handler/chat_orchestrator_disconnect_test.go:123`、`internal/service/file_event_subscriber_restart_test.go:113`——中风险：`disconnect` 是 5s 预算但主链路为 localhost httptest+mock 流（无 redis 退避放大机制）；`file_event_subscriber_restart` 的 rdb 显式 `MaxRetries: -1`+短超时（退避放大被中和），主等待已是 `require.Eventually` 5s/10s 宽窗，仅尾部 cancel 等待 5s。次优先，可留后续卡。
- `internal/handler/ws_shutdown_drain_test.go:79`、`internal/middleware/ab_test_bounded_test.go:42`、`internal/service/{file_event_hub:230,chat_history_backfill:22,69,signal_hub:119}_test.go`——低风险：纯内存 channel/scheduling 等待，无 I/O 退避放大；2s 紧但健康路径微秒级。批量项，建议同形顺延卡。

## 2. 改造明细（同形原则：断言语义不变，只放宽等待预算；等待成立即返回，健康路径时长不受影响）

### FIX-551 — `backend/gateway/internal/cqrs/worker/base_pel_redelivery_test.go`

| 等待点 | 形态 | 修前 | 修后 |
|---|---|---|---|
| `waitForEvent`（:94） | select+timeout 兜底（事件到达即返回） | 5s | **30s** |
| `waitForEventID`（:105） | 同上 | 5s | **30s** |
| `drainWorker`（:116） | Run 退出等待（在途 XReadGroup/命令级超时收尾） | 5s | **30s** |
| `TestRunDrainsPendingBeforeNewMessages` done 等待（原 :243） | select+timeout 兜底 | 5s | **30s** |
| PEL 归零轮询 deadline（原 :169） | 相对轮询（10ms 间隔，成立即返回） | 2s | **10s**（间隔 10ms 不变） |

### FIX-552 — `backend/gateway/internal/cqrs/worker/base_test.go`（TestRunGracefulShutdownLogsNoError）

| 等待点 | 形态 | 修前 | 修后 |
|---|---|---|---|
| `waitForLogEntry(observed, "Worker started", …)`（原 :72） | 相对轮询（同 FIX-544 line 114 修法，2s→10s） | 2s | **10s** |
| Run 退出 select（原 :80） | select+timeout 兜底 | 5s | **30s** |

### FIX-553 — `backend/gateway/cmd/server/setup_detached_rebuild_test.go`

| 等待点 | 形态 | 修前 | 修后 |
|---|---|---|---|
| detached rebuild 启动 select（原 :38） | select+timeout 兜底（goroutine 首次调度） | 2s | **10s** |
| `require.Eventually` ctx 释放窗（原 :56） | 相对轮询（5ms 间隔不变，匹配窗口） | 2s | **10s** |

附注：FIX-553 的 deadline 下界断言 `projectionRebuildTimeout-time.Minute`（setup.go:132，`projectionRebuildTimeout=10min`）余量 1min ≫ 全部等待预算（10s 级），预算放宽不触及该断言。

**根因核查**：三组失败面均为「等待预算 vs 负载下真实到达时间」的测试侧失配，非产品缺陷（BaseWorker 退避、`startDetachedRebuild` 语义均为既有设计，FIX-461/GW-P1-4 契约测试钉的正是产品行为）。**未触发「根因在产品侧即停」条款。**

## 3. 验证

| 项 | 结果 |
|---|---|
| `go test ./internal/cqrs/worker/... -count=3 -race` | **ok 12.624s**（0 失败） |
| `go test ./cmd/server/... -count=3 -race` | **ok 1.777s**（0 失败） |
| `go vet ./internal/cqrs/worker/ ./cmd/server/` | 干净（重生成 gen/ 后） |
| `gofmt -l`（三改动文件） | **零输出** |
| 负载模拟（40×`yes` CPU 饱和，`-count=1` 不带 race） | worker **ok 4.229s**、cmd/server **ok 0.690s** |
| 生成物 | 本 worktree 缺 gitignored `backend/gateway/gen/`，从主 worktree rsync 拷贝（不入库，gitignore :245 实证）；`git status` 仅三测试文件改动 |

诚实注记：与 FIX-544 同判——本地健康路径远低于旧预算，本地红不可构造（flake 系 CI 负载形态），故交付依据 = 「改造前后语义等价论证（断言不变、只放宽预算、等待成立即返回）+ -count=3 -race 多跑 + 负载模拟」。预算取值沿用 FIX-544 先例标定（30s ≈ 健康路径实测的 ~19 倍量级，10s 为次级等待统一值）。

## 4. 台账

- 新增三行 `V3-FIX-551/552/553`（8 裸管、7 列，状态格 `FIXED@<fix commit sha>`，sha=本分支 fix 提交），插于 FIX-547 行后；预分配号段注记已写入行内。
- 自检：`python3 scripts/devtools/ledger_union_merge.py --verify v3/06_agent_fleet/DYNAMIC_ISSUES.md`（结果见台账提交）。
- 台账闭账独立成 commit（FIXED@ 指针指向 fix 提交 sha，避免自引用腐指针）。

## 5. 交付

- commit 1（fix）：`fix(tests): wt810 Go deadline flake 族 3 组预算改造`——三测试文件 + 本报告
- commit 2（ledger）：FIX-551/552/553 入账 + verify
- 未 push；worktree 保留。
