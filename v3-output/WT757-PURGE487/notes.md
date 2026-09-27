# WT757-PURGE487 — V3-FIX-487 processed_events 保留清理接线

- Agent: wt757 ｜ 分支: `agent/node-b/wt757/purge487`（worktree `/Users/brsama/code/GitHub/Sparkle-sysrev/wt757-purge487`，基线 main@c428c485）
- 日期: 2026-09-28（本机时钟）｜ 主线仓库只读 ｜ 任务: 处置 V3-FIX-487（P3，wt752 登记 2026-09-28，台账 v3/06_agent_fleet/DYNAMIC_ISSUES.md 行 V3-FIX-487）
- 产物: 修码 commit `5614f25e`（本分支首 commit，台账 FIXED@ 同此 sha）+ 台账/notes docs commit（本分支第二 commit）

## 病灶（487 登记面逐项对上）

`ProcessedEventsRepository.Cleanup`（`backend/gateway/internal/cqrs/outbox/repository.go:365`，SQLC `CleanupOldProcessedEvents :execrows`，SQL 按 `processed_at < NOW() - INTERVAL '1 day' * $1` 全组删除）全仓零调用方——对照：outbox 的 `DeleteOld` 有 `publisher.go` Cleaner 周期调、DLQ 清理有 `dlq.go:401` DLQCleaner 调，唯 processed_events 的保留清理无人接线。469 修后 `MarkProcessed` 对每条已处理事件真实 INSERT（ON CONFLICT DO NOTHING），processed_events 随消费量单调增长无上界——481（进程内 LRU 加界）的 DB 层权威闸自身无淘汰。

表结构（gateway schema.sql :4637-4641，migration 9c4d7e8f1a2b 同构）：`(event_id varchar(100), consumer_group varchar(100), processed_at timestamp)`，复合 PK，`processed_at` 无索引。写方全仓唯一：BaseWorker `markProcessed`（469 修后两 worker：community_projection_group / galaxy 组）；engine 侧零写方（event_registry.py 自证 engine 键不入此表）。因此**跨组一刀切 DELETE 对本表所有行语义同质**，无需按组筛选。

## 接线设计与取舍（登记给了 BaseWorker 循环内定期 / 启动+周期 ticker 两向，择后者）

**采纳：独立周期清理器 `ProcessedEventsCleaner`**（新文件 `backend/gateway/internal/cqrs/outbox/processed_events_cleaner.go`），沿 `outbox.Cleaner`（publisher.go:266-349）/`DLQCleaner`（dlq.go:366-411）既有先例：专跑 goroutine + `time.Ticker`，`cmd/server/setup.go` 的 `initCQRS` 构造、`startCQRSWorkers` 以 `LogRunnerStopped` 同款 go 语句起跑（shutdown 降级日志同姿势）。

弃 BaseWorker 循环内联清理的理由：
1. **两张嘴一张表**：community/galaxy 两个 BaseWorker 共享 processed_events，各嵌清理逻辑即每 worker 各跑一遍 DELETE 全表扫（重复 DB 负载、双份节律配置面）；
2. **保留策略被单流活性绑架**：内联「每 N 批清理」只在对应 stream 有流量时推进，闲流 worker 的表面永不清理；
3. **先例一致性**：本包同型维护面（outbox 保留、DLQ 保留）均为专跑 cleaner，审查与运维心智一致。

节律：**启动首扫 + 24h ticker**（`DefaultProcessedEventsCleanerConfig`：RetentionDays=7，CleanInterval=24h）。
- 首扫价值：本修复部署即回收 487 前历史堆积（表自 469 上线即单调涨，存量非空），不等第一个 24h；
- 24h 而非 outbox Cleaner 的 1h：清理 SQL 按 `processed_at` **无索引全表扫**，保留窗本身已把表规模 bound 在 ~7 天写入量，日频扫即可保上界（同 DLQCleaner 24h 先例），把扫描代价压到最低；
- 错误姿势与兄弟 cleaner 一致：记 Error、下一 tick 重试，瞬断不杀循环；
- misconfig 守卫：`RetentionDays <= 0` 回落缺省（否则 `INTERVAL '1 day' * 0/negative` 把 cutoff 推到未来＝**清空全表**）、`CleanInterval <= 0` 回落缺省（`time.NewTicker` 对非正值 panic）。

## 保留窗论证（任务明示：必须 > 最大重放窗，宁可保守）

吸收闸的存在意义：`IsProcessed(eventID, group)` 吸收「已处理成功消息」的重放。清理的唯一风险＝**删掉一行，而该行对应的消息之后仍被重投**→重放回落为重新处理一次（吸收闸对该键失效直至重标）。故窗只需覆盖「markProcessed 成功后消息仍可能重投」的最大时长。逐路径枚举重投面：

| 重投路径 | markProcessed 后仍重投的窗 | 是否构成窗约束 |
|---|---|---|
| 461 自身 PEL 排空（markProcessed 成功、XAck 因 crash/Redis 抖动丢失） | 健在进程：≈秒级（每轮 processMessages 先 `drainOwnPending`）；跨 crash：＝进程宕机时长（consumer 名固定，重启第一动作排空自身 PEL） | **是，主约束**：窗须 > 最大可信宕机时长 |
| `>` 新消息读（XReadGroup） | 组内只投从未派发的消息，已派发者永不走此路 | 否 |
| DLQ 重试（RetryEntry） | XAdd **新** stream ID（新 ms-seq），从不复用旧 ID | 否 |
| DR 全量回放（consumer group 被删后 `XGroupCreateMkStream` @0） | 任何有限窗下超窗行都会重处理——该路径本意即重处理（运维明示动作） | 否（与窗取值无关） |

**取 7 天**：主约束的实操上界＝网关进程宕机时长。7d 超常现部署窗（分钟级）3 个量级以上，且与同包兄弟保留策略精确对齐（`outbox.Cleaner` RetentionDays=7、DLQ MaxAge=7d）——487 台账修法方向明示「retentionDays 与 outbox publisher 保留策略对齐」。残余明示（写入代码注释与本 notes，不藏账）：网关连续宕机 >7d 且 Redis stream/group/PEL 完整存活、且该消息恰在宕机前最后一刻被标——复活时该键至多一次 at-least-once 重处理，在 publisher.go 交付契约既定的 at-least-once 语义内，投影 handler 可重建兜底；再保守（30d）只是把一个更不可信的场景（月级宕机且 PEL 完整存活）的窗再拉长 4 倍，同时线性放大无索引扫描面，不换回实质安全。

## 红→绿（契约测试，正式测试入库）

红阶段先写测试后实现，两处红均为真实执行实录：

| 文件/用例 | 钉住的契约 | 修前红实录 | 修后 |
|---|---|---|---|
| processed_events_cleaner_test.go ×4（SweepsAtStartupThenPerTick / KeepsSweepingAfterErrors / StopsOnContextCancel / GuardsMisconfiguration） | 启动首扫+tick 节流且 retention 逐字转发；注入故障不杀循环；取消即停；misconfig 回落缺省 | outbox 包 **build FAIL**：`undefined: NewProcessedEventsCleaner / ProcessedEventsCleanerConfig / DefaultProcessedEventsRetentionDays`（实现缺席的 Go 红） | 全 PASS |
| cmd/server setup_processed_events_cleaner_guard_test.go | 结构守卫钉三点：bundle 字段 / initCQRS 构造 / startCQRSWorkers go 语句（防静默脱线，沿 V3-FIX-356 retired-guard 先例） | **FAIL**：`setup.go missing "processedEventsCleanerRun func()": processed_events retention cleanup is not wired into periodic maintenance (V3-FIX-487)` | PASS |
| processed_events_cleanup_test.go：ForwardsRetentionDays | Cleanup 转发钉：retention 以 int32 逐字达 SQL（`[]any{int32(7)}`）、SQL 触 processed_events；int32 溢出 fail-fast 不达 SQL | 既有 Cleanup 行为钉（绿，防回归面） | PASS |
| processed_events_cleanup_test.go：RetentionPurgeAgainstPostgres（TEST_DATABASE_URL 门控，469 同款 skip 约定） | 真库三钉：超窗行（8d）被清、窗内行保留、清理后重标同键幂等往返完好（ON CONFLICT DO NOTHING 不受 purge 影响）+跨组新行不误伤 | 本机无栈（不碰 docker/运行栈）SKIP，如实标注；用例入库供有栈环境执行 | SKIP（门控） |

绿阶段实现：`processed_events_cleaner.go`（新）+ `setup.go` 三点接线。测试零改动转绿（misconfig 用例倒逼出 retention<=0/interval<=0 双守卫——测试先行在这里直接改变了实现形状）。

## 验证

- `go test ./...`（backend/gateway）：**13 包 ok，零 FAIL**。
- `go test -race ./internal/cqrs/...`：ok（4 包含 worker/outbox）。
- **三代卡回归点名重跑零回退**：461 两 PEL 用例（TestRunRedeliversAbandonedPendingEventAfterCrash / TestRunDrainsPendingBeforeNewMessages）PASS；469 四用例（GateAcceptsRedisStreamID / KeepsUUIDCanonicalization / GuardsColumnWidth PASS + RoundTripAgainstPostgres 门控 SKIP）不回退；481 两缓存用例（TestProcessedIDsCacheStaysBounded / TestProcessedCacheStillServesHits）PASS。
- `gofmt -l .`：净（修掉一次 perl 批改留下的 struct 对齐漂移后复检净）。
- **`~/go/bin/goimports -l .`**：非 gen 零输出；`gen/` 下命中均为 gitignore 生成产物（worktree 按 wt369/J-05 先例自主仓 `cp -RL` 补齐、不入库、永不手改——硬规则 1），非本卡引入面。本卡新增/触达文件导入全标准+具名，无别名面。
- `~/go/bin/golangci-lint run ./...`：过（exit 0，零输出）。
- `go vet ./...`：零告警。
- `python3 scripts/devtools/ledger_union_merge.py --verify v3/06_agent_fleet/DYNAMIC_ISSUES.md`：**verify 通过零 FAIL**（332 行、8 裸管形态、ID 无重号、状态枚举合法）。
- 未碰 docker/运行栈/.env；未 push。

## 台账

- 487 行：OPEN（wt752 登记 2026-09-28）→ **FIXED@5614f25e**（修法/取舍/保留窗论证/红绿实录/验证全记入状态格）。
- 新发现预占：**V3-FIX-493**（P4）＝`backend/app/core/event_registry.py:635-637` 模块 docstring 仍断言 gateway IsProcessed「runs uuid.Parse…REJECTS the evt_ prefix、wiring 前须先解决 id 格式」——469 已修（normalizeEventKey 非 UUID 键逐字接受），docstring 对未来 engine 侧消费者接线判断构成失实前提；grep 复核主仓+worktree 台账 493/494 双 0 命中、在册最高 490（489/490 为并行 agent 新占）；修法方向 T-event-registry-gate-doc-sync（纯文档面）。494 留空未占（无第二个够格发现，不凑数）。
- 残余留记（不占号）：processed_at 无索引（仅复合 PK），sweep 全表扫——表被 7d 窗 bound 后日频扫代价可忽略；事件量级上台阶再议加索引（Alembic 迁移＝跨层变更，本卡不扩面）。

## 边界与残余

- 本机为 macOS/arm64（AGENTS.md「当前工作区在 Windows」为旧执行包表述，本机事实以本 notes 为准）：`go test -race` 的 ld LC_DYSYMTAB 噪声同 481/wt743 在案记录，不影响 verdict。
- 真库保留窗 purge 用例与 469 round-trip 用例同门控（TEST_DATABASE_URL），本机 SKIP 与 469 合并时状态一致——有栈环境的端到端吸收+purge 语义由该两用例背书。
- 首扫对历史巨表的首次 DELETE 为单事务全量删（PG 可承受、一次性）；若某部署存量达千万级可考虑分批，本卡不预优化。
