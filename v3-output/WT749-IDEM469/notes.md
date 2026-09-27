# WT749-IDEM469 — V3-FIX-469 processed_events DB 幂等闸去 uuid.Parse 格式假设

- Agent: wt749 ｜ 分支: `agent/node-b/wt749/idem469`（worktree `/Users/brsama/code/GitHub/Sparkle-sysrev/wt749-idem469`，基线 main@ef3cb03e）
- 日期: 2026-09-27 ｜ 主线仓库只读 ｜ 任务: 处置 V3-FIX-469（P3，wt743 V3-FIX-461 收口顺审登记；上下文 `v3-output/WT743-PEL461/notes.md` 残差①）
- 产物: 修码 commit **060d541f**（`backend/gateway/internal/cqrs/outbox/repository.go` + 新回归测试 `repository_test.go` 4 用例）+ 台账 docs commit（本 commit）

## 病灶（469 登记面逐项对上）

`ProcessedEventsRepository.MarkProcessed/IsProcessed`（cqrs/outbox/repository.go，修前 :316/:298）对 eventID 先 `uuid.Parse` 再落 SQL，而唯一生产调用方 BaseWorker（`isProcessed`/`markProcessed`，base.go:387/:404）传入 redis stream 消息 ID（"ms-seq" 形如 "1758-0"）必败：MarkProcessed 返错仅 Warn，行永不落库；IsProcessed 返错降级 false——processed_events 对 community/galaxy 两组恒空，跨重启重复投递零吸收。schema 列本为 `varchar(100)`（PK (event_id, consumer_group)，ON CONFLICT DO NOTHING），闸死在 Go 层格式假设。本次亲证修前红实录即病灶本字：`parse event ID: invalid UUID length: 6`。

## 修法与取舍（登记给了两向，择 A）

**采纳方向 A：去掉格式假设，接受任意非空 ≤100 字符 event key。** 落点为新纯函数 `normalizeEventKey`（repository.go，两方法唯一入口）：

1. **UUID 形键照旧规范化**（`uuid.Parse` 成功 → 小写连字 canonical）——与修前落库形逐位一致，假想已入库 UUID 形行的 IsProcessed **继续命中不失效**（含大写/花括号等非规范拼法输入，规范化后仍命中旧行）；evt_ 前缀形过不了旧闸、库中本无此类行，透传即可与 D-01 引擎侧事件共存。
2. **其余键原样透传**——stream ID、evt_ ID、任意 ≤100 字符串逐字节转发 SQL（复合主键等值匹配依赖逐位一致，测试钉住转发参数）。
3. **守卫**：空串拒收（NOT NULL 列无意义输入）；>100 字符 Go 层快速失败（对齐 varchar(100) 列宽，不把 value-too-long 挤到 DB 层）。
4. **零 SQL/schema/SQLC 变更**：`query.sql` 的 IsEventProcessed/MarkEventProcessed 本就收 string，`gen/` 未触、未手改任何生成产物。

**弃方向 B（uuid5(namespace, streamID+组名) 派生确定性 UUID）**：

- B 的存储形齐整是伪收益：列本为 varchar(100)，schema 作者已选任意串；格式假设才是病灶，B 是把假设换个位置保留。
- B 为兼容假想旧行仍须保留 parse 规范化路径（旧行是 canonical UUID 形，uuid5 派生值对不上）→ 双轨并存，比 A 单轨更复杂。
- 有损变换：uuid5 派生后表内容不再直读（查 "1758-0" 要现算 hash），排障可调试性劣于 A 的行内即本字。
- 碰撞语义无增益：uuid5 128-bit 碰撞概率工程上可忽略，但 A 的透传连这点都不引入。

## 红→绿（fake DBTX 契约测试，正式测试入库）

`backend/gateway/internal/cqrs/outbox/repository_test.go`，in-package 以 fake `db.DBTX`（3 方法接口）构造 `&ProcessedEventsRepository{queries: db.New(fake)}`，捕获转发到 SQL 层的参数逐字节断言——不需要活 Postgres 即可钉「转发形」契约；真库端到端吸收另设 `TEST_DATABASE_URL` 门控用例（与 `internal/db/db_integration_test.go` 同 skip 约定）。

| 测试 | 钉住的契约 | 修前红实录 | 修后 |
|---|---|---|---|
| TestProcessedEventsGateAcceptsRedisStreamID | stream ID "1758-0" 必须 verbatim 落 MarkExec 参数并被 IsProcessed 吸收（含重放命中 true） | FAIL：`parse event ID: invalid UUID length: 6` | PASS 0.00s |
| TestProcessedEventsGateKeepsUUIDCanonicalization | 非规范拼法 UUID（大写）落库/查询均规范化为 canonical（兼容钉，修前即绿） | PASS（钉住不回退） | PASS 0.00s |
| TestProcessedEventsGateGuardsColumnWidth | 100 字符恰过 / 101 字符 Go 层拒（错误非 "parse event ID"）/ 空串拒 | FAIL：`parse event ID: invalid UUID length: 100` | PASS 0.00s |
| TestProcessedEventsRoundTripAgainstPostgres | 真库吸收往返：组内吸收/组间隔离/重标幂等（ON CONFLICT DO NOTHING） | SKIP（本机无 TEST_DATABASE_URL） | SKIP（同左，待有库环境门控跑） |

红→绿用同一份最终测试文件（先跑红后修 repository.go），非「先写绿再补红」。测试首版有处自身缺陷（兼容钉用例 fake 忘置 exists=true）已当轮修正——修正后重钉确认该用例修前即绿，作纯兼容钉。

## 验证

- `go test ./...`（backend/gateway）：**13 包 ok，零 FAIL**（gen/ 按先例 `cp -RL` 自主仓，.gitignore 不入库；其余 6 包 no test files）。
- `go test -count=1 ./internal/cqrs/... ./internal/db/...`：全绿——**461 两条 PEL 用例（base_pel_redelivery_test.go）不回退**。
- `-race`：触达包 `internal/cqrs/outbox` + `internal/cqrs/worker` 均 ok（ld LC_DYSYMTAB 为 macOS 工具链噪声，wt739/wt743 同记）。
- `go vet ./...` 零告警；`gofmt -l internal/cqrs/` 净。
- `python3 scripts/devtools/ledger_union_merge.py --verify v3/06_agent_fleet/DYNAMIC_ISSUES.md`：**通过零 FAIL**（325 行 V3-FIX 行，裸管分布 {8: 325}，无重号，状态枚举合法）。
- 未动 docker/真实运行栈；真库门控用例在本机如实 SKIP（禁触运行栈，见诚实注记）。

## 台账

- **V3-FIX-469 → FIXED@060d541f**（状态格含 A/B 取舍、红绿实录、残差三项）。
- 范围内评估收口：markProcessed/isProcessed 失败仅 Warn **维持**（评估记入 469 状态格：修前 Warn 恒淹因闸每调必败；修后 Warn 即真 DB 故障，且 461 已立 at-least-once+投影可重建兜底，吸收标记属 best-effort 面，不上告警通道）。
- 范围外新发现 **V3-FIX-481**（P3，OPEN）：`processedIDs` sync.Map Store 后零淘汰无界增长（base.go:65/:381/:400 三处，无 Delete）——469 修后 DB 闸为权威吸收层，内存表只是热路径缓存，无界纯代价；修法方向记 LRU 加界（hashicorp/golang-lru/v2 已是直接依赖）或 TTL，淘汰回落 DB 查询即正确、零正确性风险。481/482 号 grep 亲证空闲（v3/ v3-output/ 0 命中，在册最高 471；482 备用未动用）。

## 诚实注记

- **真库端到端往返未在本机实证**：TestProcessedEventsRoundTripAgainstPostgres 需要 TEST_DATABASE_URL，本机无库且按任务约束不触 docker/运行栈，如实 SKIP；其「转发形」等价面已由 fake DBTX 用例钉住（SQLC 层仅原样传参，无再变换），风险窄。
- **假想已入库行的兼容论证是审读级**：processed_events 在修前唯一写入路径即本闸（对 stream ID 必败），Python 引擎侧 grep 无对该表写入；即生产库该表大概率为空，「旧行继续命中」以规范化逐位一致 + 兼容钉用例保证，无运行级旧行实证对象（无从实证不存在的行，如实记）。
- **吸收闸语义边界**：本闸吸收的是「同 stream ID 重放」（461 回放/跨重启重投）；handler 半执行（副作用已施、markProcessed 前 crash）的窄窗重复仍在（与 461 残差同一窗，at-least-once 下界），非本卡扩面。
- BaseWorker Warn-only 与 processedIDs 加界均未改码（前者评估维持、后者独立成卡 481），不因顺手扩大 diff 面。
- 引擎侧既有描述随之半过期：`backend/app/core/event_registry.py:634` docstring（D-01 在册）记「repository.go IsProcessed 对 id 跑 uuid.Parse 拒收 evt_ 前缀、接线须先解决 id 格式」——本修复后 repository 层已接受任意 ≤100 字符键，该前提消除；docstring 属引擎侧 D-01 接线卡面，本卡不动码，留 D-01 接线时顺带刷新（本卡为其解除了 repository 层阻塞）。
