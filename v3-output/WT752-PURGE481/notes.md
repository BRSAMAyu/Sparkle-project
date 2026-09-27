# WT752-PURGE481 — V3-FIX-481 BaseWorker.processedIDs 无界缓存改有界 LRU

- Agent: wt752 ｜ 分支: `agent/node-b/wt752/purge481`（worktree `/Users/brsama/code/GitHub/Sparkle-sysrev/wt752-purge481`，基线 main@cfedeedc）
- 日期: 2026-09-28（本机时钟）｜ 主线仓库只读 ｜ 任务: 处置 V3-FIX-481（P3，wt749 V3-FIX-469 收口顺审登记 2026-09-27）
- 产物: 修码 commit（本分支首 commit，sha 见台账 FIXED@）+ 台账 docs commit（本 commit）

## 病灶（481 登记面逐项对上）

`BaseWorker.processedIDs sync.Map`（`backend/gateway/internal/cqrs/worker/base.go`，修前 :65 声明/:400 Store/:381 Load）仅 Store 不淘汰，全包 grep 3 处、零 Delete/淘汰/加界。写查点与 DB 闸的关系：

- `markProcessed`（处理成功后调用）= 进程内 `Store(messageID)` + DB `ProcessedEventsRepository.MarkProcessed`（469 修后经 `normalizeEventKey` 真实落库）；
- `isProcessed`（处理前幂等检查）= 进程内 `Load` 命中即 true 跳过 DB，未命中回落 DB `IsProcessed`。

生命周期：`NewBaseWorker` 仅两处生产构造（`community_sync.go:67`、`galaxy_sync.go:111`），各持一个长活 `Run` 循环（ctx 取消才退、consumer 名固定）；进程不重启 map 永不倒空，驻留与累计消息量线性、无上界——stream ID "ms-seq" 约 15-20B/键 + sync.Map entry 开销，月级长跑百万条消息数十 MB 级（wt749 估算维持，本卡未改评估）。

## 修法与取舍（登记给了 A/「B 观察」/C 三向，择 A）

**采纳方向 A：有界 LRU 缓存**（`hashicorp/golang-lru/v2` v2.0.7，go.mod 既有直接依赖，零新依赖）：

1. `processedIDs sync.Map` → `processedCache *lru.Cache[string, struct{}]`，容量常量 `processedCacheSize = 1024`（台账明示「数百至数千条热键即可」）。语义定位写进字段注释：**纯加速层，权威重复闸 = processed_events 表**（469 修后真实吸收）——淘汰任何条目最多让一条重投旧事件多付一次 DB `IsProcessed` 等值查询（复合 PK 命中），绝不产生双重处理。
2. 容量 1024 的量级依据：真实进程内重复流量只有 461 PEL 回放中「markProcessed 成功后、XAck 前 crash」的窄窗重放——`processMessage` 成功即 XAck，`>` 只投组内未派发消息，稳态每消息进程内只投递一次，命中率天然趋近于零；1024 绰绰有余，最坏驻留 ~数百 KB（两 worker 计）。
3. 线程安全：`lru.Cache` 内置互斥（原 sync.Map 亦并发面，等价收口）。
4. 防御降级：`lru.New` 仅 size<=0 报错（常量正数不可达），报错即置 nil；nil 缓存 = 跳过缓存层永远走 DB 闸，语义仍正确（`isProcessed`/`markProcessed` 双 nil 守卫）。BaseWorker 唯一构造路径是 `NewBaseWorker`（grep 亲证零裸 `&BaseWorker{}`），守卫纯防未来。

**弃方向 B：彻底删除缓存、全查 DB**——B 的代价是给 100% 事件各加一次前置 DB SELECT（`isProcessed` 无缓存必落库），买到的只是删掉一个 1024 上限、~数百 KB 的结构；缓存稳态命中率本就趋零意味着 B 的「多付」发生在每一条事件上而非罕见回放上。事件量当前低（两组、BatchSize 10），但纯负收益；若未来证据表明该前置查询可省（如把幂等检查并进 handler 事务），应作为独立卡重新评估，本卡不扩面。

**弃方向 C：周期性清空重建**——清空瞬间整段缓存一次性失效（全部回落 DB，形成周期性小尖峰），且需额外 ticker/生命周期管理；LRU 逐条平滑淘汰、无新并发面、无新后台 goroutine，严格优于 C。

## 红→绿（契约测试，正式测试入库）

`backend/gateway/internal/cqrs/worker/base_processed_cache_test.go`（in-package，miniredis 构造 worker，`markProcessed`/`isProcessed` 直测单元面）：

| 测试 | 钉住的契约 | 修前红实录 | 修后 |
|---|---|---|---|
| TestProcessedIDsCacheStaysBounded | 连续标记 `processedCacheSize+64` 个不同消息 ID 后，缓存驻留 ≤ 容量 | FAIL：`processed cache holds 1088 entries after 1088 markProcessed calls, want <= 1024: cache grows without bound (V3-FIX-481)` | PASS |
| TestProcessedCacheStillServesHits | 容量内命中语义：markProcessed 后 isProcessed=true（加速层角色保留）；未标记 ID 不误报（nil repo 回落 false） | PASS（契约钉，修前即绿，钉住不回退） | PASS |

红→绿用同一份最终测试文件：红阶段生产码仅加 inert 常量 `processedCacheSize`（供测试引用，未动任何逻辑），断言对未修的 sync.Map 真实跑出 1088>1024 红实录；绿阶段换 LRU 后测试测量点 `Range` 计数 → `processedCache.Len()` 为唯一测试改动。

## 验证

- worktree 无 `gen/`（gitignore 生成产物不入库），`make proto-gen`：docker 工具链镜像不可用由脚本自动回落宿主 buf 工具链（WARN 在案，未拉起任何容器），生成后全仓可编译。
- `go test ./...`（backend/gateway）：**13 包 ok，零 FAIL**——含 gen 依赖的 cmd/server、internal/agent、internal/errorbook、internal/galaxy、internal/handler（本卡未触其码，仅补生成物使全包可跑）。
- **461 不回退**：base_pel_redelivery_test.go 两条 PEL 用例（重投滞留/先排空后新读）绿；**469 不回退**：outbox repository_test.go 四用例绿。
- `go test -race ./internal/cqrs/...`：ok（ld LC_DYSYMTAB 为 macOS 工具链噪声，469/wt743 同记）。
- `go vet ./...` 零告警；`gofmt -l .`（gateway 全仓）净。
- `python3 scripts/devtools/ledger_union_merge.py --verify v3/06_agent_fleet/DYNAMIC_ISSUES.md`：通过零 FAIL（见台账 commit）。
- 未动 docker/真实运行栈；本卡无真库依赖面（缓存淘汰回落 DB 的正确性由 469 已入库的转发形/真库门控用例背书）。

## 台账

- **V3-FIX-481 → FIXED@**（状态格含 A/B/C 取舍、红绿实录、边界注记）。
- 范围外新发现 **V3-FIX-487**（P3，OPEN）：**processed_events 表自身无保留清理接线**——`ProcessedEventsRepository.Cleanup`（repository.go:365，SQLC `CleanupOldProcessedEvents`）全仓零调用方（对照：outbox 的 `DeleteOld` 有 publisher.go:337 调、DLQ 清理有 dlq.go:401 调，唯 processed_events 的清理无人接）。469 修后 `MarkProcessed` 对每条已处理事件真实 INSERT 一行，表随时间无界增长——**481 的 DB 层镜像**：进程内缓存加界了，权威吸收层本身却无淘汰。修法方向：网关周期维护任务接 `Cleanup`（retentionDays 与 outbox publisher 的保留策略对齐；淘汰后重放旧事件回落路径 = 重新处理一次，at-least-once 语义内，无正确性风险但需在卡内论证保留窗 > 最大重放窗）。487/488 号 grep 亲证空闲（v3/ v3-output/ `V3-FIX-48[2-9]` 全 0 命中；备用 488 未动用）。

## 诚实注记

- **1024 容量为工程定值非压测定**：依据「稳态进程内重复仅 PEL 窄窗回放」的代码审读级论证（`processMessage` 成功即 XAck、`>` 只投新消息）；无生产命中率数据。真环境可观察既有 `metrics.RecordDuplicateEvent` 计数再校准容量，本卡不设调参面（YAGNI）。
- **淘汰回落 DB 的代价未基准化**：复合主键 `(event_id, consumer_group)` 等值查询，代价 O(log n) 索引命中；重放旧事件（超出保留窗的淘汰键）会被重新处理一次——461 已立 at-least-once + 投影可重建兜底，语义内非缺陷。
- **481 修复不改变 469 残差面**：handler 半执行（副作用已施、markProcessed 前 crash）的窄窗重复仍在（at-least-once 下界），与本卡无关不扩面。
- 进程内缓存命中/淘汰对本卡全部测试用例透明：461/469 用例事件量远小于 1024，不触发淘汰路径——淘汰行为由 TestProcessedIDsCacheStaysBounded 直接钉住。
