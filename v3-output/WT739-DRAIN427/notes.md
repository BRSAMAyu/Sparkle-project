# WT739-DRAIN427 — V3-FIX-427 ChatHistoryPersister 优雅关停批不丢

- Agent: wt739 ｜ 分支: `agent/node-b/wt739/drain427`（worktree `/Users/brsama/code/GitHub/Sparkle-sysrev/wt739-drain427`，基线 main@cbb92145）
- 日期: 2026-09-27 ｜ 主线仓库只读 ｜ 任务: 修复 V3-FIX-427（P2，复核 CONFIRMED@wt735，证据 `v3-output/WT735-VERIFY3/notes.md`）
- 产物: 修码 commit **23e813a3**（chat_history_persister.go + 新回归测试 4 用例）+ 台账 docs commit（本 commit）

## 病灶与修法

修前三条丢批路径（wt716 登记 + wt735 复核全对上，本次逐条收口）：

1. **Run ctx.Done/stopCh 分支以已取消 ctx 调 flushWithRetry**（main.go:142 `bgCancel()` 先于全部 drain；:105 `defer Stop()` 殿后）——`pool.Acquire` 首试即败，批已换出（:278-279）既未写库也未 requeue。
2. **flushWithRetry backoff select 命中 ctx.Done 裸 `return ctx.Err()`**（原 :289-290）——复核草案未点名，同属换出后零 requeue 的丢批路径，本次一并收口。
3. **requeueMessages LPush 错误整体丢弃**（原 :416）——即便走到 requeue，Redis 不可达时零信号丢失。

修法（采复核草案「detached 显式不受 cancel 影响」支路）：

- 新增 `flushOnShutdown(ctx)` = `context.WithTimeout(context.WithoutCancel(bgCtx), PersisterShutdownFlushTimeout=5s)`，ctx.Done/stopCh 两分支改挂（先例 `handler/chat_orchestrator_chatflow.go:123-125` detachedPersistCtx，R2-GW-1）；Run 仍报 `ctx.Err()`，`LogRunnerStopped` 的 INFO 定级不变。
- backoff select 的 ctx.Done 支路：`requeueMessages(context.WithoutCancel(ctx), batch)` 归队后再报错——flushWithRetry 从此任何路径都不再吞批。
- `requeueMessages` 签名改返回 `int`（失败计数）：逐条查 `LPush(...).Err()`、逐条日志、累计 `requeue_failed` 指标（`GetStats()` 新键）。
- **main.go 关停序未动**：bgCancel 后移到 drain 完成之后会改变全部 bg worker（CQRS workers、file event subscriber、file GC）的退出时机，影响面大；detached flush 达成同等耐久且与关停序零耦合，属复核草案明示的等价选项。

## 红→绿（双路径 + 真库，正式测试入库）

`backend/gateway/internal/service/chat_history_persister_shutdown_test.go` 4 用例，修前跑全红、修后全绿：

| 测试 | 钉住的契约 | 修前红实录 | 修后 |
|---|---|---|---|
| TestFlushWithRetryCancelledContextDoesNotDropBatch | 已取消 ctx 直入 flushWithRetry 不得丢批（backoff 路径归队） | FAIL 0.00s，队列长 0 | PASS，队列 1 |
| TestRunShutdownFlushSurvivesContextCancel | Run 关停最终 flush 脱离已取消 bgCtx；Run 仍报 context.Canceled | FAIL 0.00s，队列长 0 | PASS 1.51s |
| TestRequeuePushFailureIsObservable | LPush 失败逐条可观测（GetStats requeue_failed） | FAIL 7.89s，requeue_failed=nil（静默吞） | PASS，=3 |
| TestShutdownFlushWritesBatchToDB | 真库写路径：关停后行落 chat_messages | FAIL 0.05s，rows=0（日志复现 `Write failed (attempt 1): failed to acquire connection: context canceled`，与 wt735 实验一致） | PASS，rows=1 |

- hermetic 3 用 bad-DSN pgxpool（`127.0.0.1:1` 即刻拒连）+ miniredis，同 wt735 实验形制：库不可达时「不丢」只可能=「归队」。
- 真库用例按 `internal/db/db_integration_test.go` 先例 `TEST_DATABASE_URL` 门控（未设即 skip，hermetic 套件不依赖库）；本次对本地 dev PG 实跑，users 种子行 + chat_sessions/chat_messages/users 三级 t.Cleanup 清理，跑后残留复查 0 行。

## 验证

- `go test ./...`（backend/gateway）：13 包 ok，零 FAIL（含新测试；真库用例带 TEST_DATABASE_URL 实跑）。
- `go vet ./...`：零告警。
- `-race` 触达包新测试：绿（ld LC_DYSYMTAB warning 为 macOS 工具链噪声，与代码无关）。
- `gofmt -l` 触达两文件：净。
- gen/ 按先例 `cp -RL` 不入库。

## 台账

- V3-FIX-427 → FIXED@23e813a3（状态格追加修法四点+红绿实录+关停序裁决）。
- 范围外新发现 **V3-FIX-461**（P3，OPEN）：CQRS BaseWorker stream 消费只读 `>`、无 XAUTOCLAIM/`"0"` 回放——崩溃/关停打断 in-flight 事件时 PEL 滞留永不重投（DLQ 与 XAck 同持已取消 ctx 失败）；与 427 同窗但消息本体滞留 PEL 可恢复，非硬丢失故 P3。461 号 grep 亲证空闲（在册最高 451）。不阻塞本卡。

## 诚实注记

- 未实测真实部署（无集群环境）；关停行为以单元级 Run/cancel 全链 + 真库 round-trip 为证。
- `GetStats` 对 `totalFailed/requeueFailed` 的读取沿袭既有无锁模式（Run 单 goroutine 写），未在本卡改表；与 `pending_batch`（有锁）不一致属既有卫生项，量级无害，不立卡。
- pre-fix 红跑确认无测试残留进 dev 库（users 0、chat_messages 0）。

## verify 自检

- 台账 362 行（基线 361 + 新登记 461 一行）；427 行状态格追加、461 新行均 7 列 9 字段过检；重号 0。
- 修码 commit 23e813a3 与 docs commit 均在 `agent/node-b/wt739/drain427`；未 push。
