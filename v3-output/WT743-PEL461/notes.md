# WT743-PEL461 — V3-FIX-461 CQRS stream PEL 滞留永不重投修复

- Agent: wt743 ｜ 分支: `agent/node-b/wt743/pel461`（worktree `/Users/brsama/code/GitHub/Sparkle-sysrev/wt743-pel461`，基线 main@ccc98700）
- 日期: 2026-09-27 ｜ 主线仓库只读 ｜ 任务: 处置 V3-FIX-461（P3，wt739 执行中登记；上下文 `v3-output/WT739-DRAIN427/notes.md`）
- 产物: 修码 commit **8623ff9e**（cqrs/worker/base.go + 新回归测试 `base_pel_redelivery_test.go` 2 用例）+ 台账 docs commit（本 commit）

## 病灶（461 登记面逐项对上）

BaseWorker 消费循环 XReadGroup 只读 `>`（Redis 语义：仅派发组内从未派发过的消息）；进程崩溃或优雅关停 bgCancel 打断 in-flight 事件时（processWithRetry backoff select 命中 ctx.Done 即返，随后 sendToDLQ 与 `Always acknowledge` 的 XAck 均持已取消 ctx 失败仅 Warn），事件滞留 consumer PEL；重启后新循环仍只读 `>` → 永不重投。全 gateway 无 XAUTOCLAIM/XCLAIM、无 "0" 起 PEL 回放。consumer 名固定（community_worker_1 / galaxy_worker_1）恰使「同名重启自回收」可行。

## 修法与取舍（登记给了 a/b/c 三向，择 b）

**采纳 b：`processMessages` 每轮先 `drainOwnPending` 以 `"0"` 起始读自身 PEL**（base.go:189/:237@8623ff9e）——重放条目走与首投完全同一的 `processMessage` 门（幂等检查→解析→processWithRetry→markProcessed→ack；解析/处理失败面 DLQ+ack），排空才转阻塞 `>` 读；空 PEL（redis.Nil）与 PEL 读错误一律落回 `>` 读的既有错误路径（NOGROUP 自愈、退避、PROD-LOG #8 定级），零新增 goroutine、零新增配置项、关停序零耦合。排空优先同时保证恢复先于新消费（有专用用例钉住）。

- **弃 a（XAUTOCLAIM 定期回收）**：a 的核心增益是组内多副本收复，本部署 consumer 名固定、单网关实例，用不上；而 min-idle 阈值抢占会引入「从活 worker 手里抢在-flight 消息」的重复处理窗——galaxy HIncrBy(+1)、community incrLikeCount 等 Redis 投影并非重复安全，需先调阈值+幂等闸先立，面大于收益。真水平扩容时 a 仍是要走的路（届时与幂等闸 V3-FIX-469 一并）。
- **弃 c（关停路径 DLQ/XAck 换 detached ctx，与 427 flushOnShutdown 同形）**：c 只治优雅关停不治硬杀（SIGKILL/崩溃时进程根本无法补 XAck），单选 c 达不到本卡红测（重启重投）；而 b 落地后 c 想救的面（关停中断的 XAck/DLQ）由重启回放兜住——漏确认项回放后正确 ack 或 DLQ，**DLQ 转移从「丢失」变「延迟至下次重启」**。b 是三向中最小正确面，c 的残差收窄已如实写进台账 461 状态格。

## 红→绿（miniredis，正式测试入库）

`backend/gateway/internal/cqrs/worker/base_pel_redelivery_test.go` 2 用例。崩溃模拟零竞态：直接以同名 consumer XReadGroup 认领进 PEL 且不 XAck（PEL 归属由 consumer 名决定，与进程是否存活无关，即崩溃现场），再以同名 consumer 起 Run：

| 测试 | 钉住的契约 | 修前红实录 | 修后 |
|---|---|---|---|
| TestRunRedeliversAbandonedPendingEventAfterCrash | 认领后未 XAck 的事件，同名重启必须重投处理且处理成功后移出 PEL（XPending=0） | FAIL 5.01s：`handler was not called within 5s: abandoned PEL entry never redelivered` | PASS 0.00s |
| TestRunDrainsPendingBeforeNewMessages | 滞留 PEL 旧事件必须先于崩溃后新到达事件投递（恢复优先于新消费） | FAIL 5.01s：`expected delivery not observed within 5s`（evt-pending-old 恒不投） | PASS 0.00s |

红→绿用同一份最终测试文件（先跑红后改 base.go），非「先写绿再补红」。

## 验证

- `go test ./...`（backend/gateway）：**13 包 ok，零 FAIL**（含新测试）。
- `go vet ./...`：零告警；`gofmt -l` 触达目录净。
- `-race`：触达两包 `internal/cqrs/worker` + `internal/worker` 均 ok（ld LC_DYSYMTAB warning 为 macOS 工具链噪声，wt739 同记，与代码无关）。
- `scripts/devtools/ledger_union_merge.py --verify v3/06_agent_fleet/DYNAMIC_ISSUES.md`：**通过，零 FAIL**（321 行 V3-FIX 行，无重号，状态枚举合法）。
- gen/ 按先例 `cp -RL`（.gitignore:245 不入库）。

## 台账

- **V3-FIX-461 → FIXED@8623ff9e**（状态格含修法 a/b/c 取舍、红绿实录、残差两项）。
- 范围外新发现 **V3-FIX-469**（P3，OPEN）：processed_events DB 幂等闸对 BaseWorker 全部真实调用恒失效——`ProcessedEventsRepository.MarkProcessed/IsProcessed`（repository.go:317/:299）对 eventID 先 `uuid.Parse`，而唯一生产调用方 BaseWorker 传入 redis stream ID（"ms-seq" 形）必败 → 行永不落库、闸恒 false，跨重启重复投递零吸收；schema 的 event_id 本是 varchar(100) 可容任意串，死在 Go 层格式假设。与 D-01 REPORT §8 已记的「uuid.Parse 拒收 evt_ 前缀」同根（repository 层 id 格式假设）但独立成卡：彼是引擎侧接线阻塞项，本条是 gateway 自身消费面闸失效，且与本卡残差直接相关（461 的跨重启重放吸收不得声称依赖该闸）。附带同面卫生项：`processedIDs` sync.Map Store 后无淘汰无界增长。469/470 号 grep 亲证空闲（v3/ v3-output/ 0 命中，在册最高 461）。

## 诚实注记

- **461 修复的实际语义是 at-least-once**：跨重启重放的重复吸收当前不来自 processed_events（闸死，见 469），而靠 handler 投影可重建性吸收——community_sync 侧错误分支明示「Non-fatal, projection will be rebuilt」（incrLikeCount 失败即放弃返回 nil），galaxy view 为 24h TTL 的全量 Set 覆盖。窄窗重复面（handler 副作用已施、markProcessed 前 crash）与 a 案 XAUTOCLAIM 等价且小于「修复前事件整条丢失」的既有行为；严格 once 在该消费面从未存在。
- 未实测真实集群/多副本部署（无环境）；重投证据为 miniredis 单元级全链（认领→PEL→同名重启→重投→ack 清 PEL），未动真 Redis 实例。
- 关停中断的 DLQ 转移延迟至重启后才落——有重启即收敛，无重启则与修复前同样不落，未另加 detached 面（取舍见上）。
- 测试用 `IdempotencyCheck: true` + nil repo（isProcessed 恒 false）——与两 worker 生产形制的降级路径一致，不掩盖 469。

## verify 自检

- 台账 365 行（基线 364 + 新登记 469 一行）；461 状态格改 FIXED、469 新行均 7 列过检；重号 0；`--verify` 零 FAIL。
- 修码 commit 8623ff9e 与 docs commit 均在 `agent/node-b/wt743/pel461`；未 push；main 仓只读未动（worktree 命令本身仅写 .git/worktrees 元数据，未改 main 工作区）。
