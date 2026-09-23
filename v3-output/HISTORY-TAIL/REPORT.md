# HISTORY-TAIL 收工报告 — 重启后历史尾部截断（Redis 10 vs DB 13）

> 卡：V13-RETEST REPORT 残留 Major 1（B-01「重启可见性」部分通过的成因面）
> Worker：C 纵队修复 Worker（北极星主链线）｜worktree：wt219｜基线：a555047f
> 交付物：本报告 + `changes.patch`（零 commit/push，零凭据）

---

## ① 方案裁决链

**裁决：采纳报告建议①——读路径水位校正（纯网关实现）；否决②与③。**

| 方案 | 裁决 | 理由 |
|---|---|---|
| ① 读路径合并/水位回源 | **采纳** | 见下三条理由链 |
| ② 缓存 append 与引擎落库同源（引擎 ack 后 append + 幂等校验） | 否决 | 需引擎→网关 ack 事件通道 + 网关订阅器 + append 幂等去重：跨服务改动、触碰 Redis 契约，且卡片明令不动引擎（若动须声明并最小化——本卡声明：**不采纳即不动**） |
| ③ `chat:session_meta` 与 DB sessions 表二选一为恢复卡事实源 | 否决（移出本卡） | 只修「恢复卡标题双源矛盾」这一表现，不修尾部截断本体；「二选一」是 mobile+网关契约级产品决策，超出本卡最小改动面。本修复以 `refreshSessionMetaTail` 顺带把 meta 的 `last_message_at/last_preview` 刷成真尾部，**缓解**双源矛盾，产品级归一留给派卡 |

**理由链**：

1. **一致性保证**：P2-D 之后引擎是唯一权威 DB 写者（`chat_history.go` P2-D 注释 + persister 默认关闭），完备性真值只在 DB。报告明言 append 缺口触发面「与 run 收束事件/缓存写入时机相关，**待修卡定位**」——写侧修复只能覆盖已定位的成因，而读路径校正是对**一切缺口成因**（杀 app 时机/断网恢复/收束事件丢失）的兜底。取证还发现 `GetMessages` 的第二个生产消费方：chatflow 的 AI 上下文裁剪（`chat_orchestrator_chatflow.go:497`，每轮读取 limit=20）——截断同样在污染 AI 上下文，读路径修复让两处一并痊愈。
2. **改动面**：单文件 `chat_history.go` + 测试，网关内闭环；无 proto/迁移/引擎接触。
3. **故障模式**：分级退化——探测失败→今日行为（纯缓存，可用性不降）；DB 整体不可用→同上；水位 30s 窗口内→零 DB 成本；探测到缺口→事务化重写缓存并返回合并视图。**诚实边界**：缺口产生后若 30s 水位仍新鲜，下一次读最多再陈旧一个水位周期（≤30s + 一次探测），相比原缺陷的 ~15min TTL 自愈收窄 30 倍。

**实现要点（身份难题的解法）**：网关 append（自生成 UUID + append 时刻时间戳）与引擎落库（自生成 ID + 引擎 created_at）是同逻辑消息的双源、**ID 不通约**——故配对按 `(role, content)` 精确内容相等 + 时间邻近（容差 2min，最近优先）进行；合法的重复重发（V13 B-02 的「重试=重发」重复 USER 行）按时间序最近配对，不误并入。**零配对**时判定两源内容形态不通约（防整段重复渲染），退化为 DB 权威视图 + 缓存事务化重写。

## ② 实现清单

全部改动：`backend/gateway/internal/service/chat_history.go`（+304/−12）+ 新测试 `chat_history_tail_test.go`（268 行）。净效果 `git diff --stat`：2 files, +572/−12。

`chat_history.go`：

1. **读路径重构**（`GetMessages`）：`getMessagesFromRedis` 改为返回全量过滤列表（原 offset/limit 切片原样抽为 `sliceMessagesPage`，语义逐字保留）；缓存命中后先过 `repairTailFromDB` 再统一分页——分页窗口算在合并视图上，offset 语义不漂移。
2. **水位探测**（`repairTailFromDB`）：`chat:session_meta:<sid>.tail_checked_at` 水位，30s 内纯缓存（零 DB 成本）；过期先盖章后探测（慢/挂 DB 不会把每次读都变成探测），探测带 2s 超时。
3. **DB 尾部探测**（`probeTailFromDB`）：`created_at > cache最旧−5s` 升序取 ≤50 行，走 `idx_chat_user_session_created_at` 索引范围扫描；session label 走 P2-E 的 `resolveSessionUUID` 伪 UUID 解析（与 `getMessagesFromDB` 同源）；行扫描抽为 `scanChatMessageRows` 与 `getMessagesFromDB` 共享（消除重复，行为等价）。
4. **合并**（`mergeCacheAndDBTail`，纯函数）：如上配对规则；缺尾部合并按时间戳稳定排序（中段缺口也能归位）。
5. **缓存修复**（`replaceRedisMessages`）：TxPipeline 事务化 `DEL+RPUSH+LTRIM(−20)+EXPIRE`，修复永不叠加在旧列表上（强于既有 `backfillRedisMessages` 的裸 RPush——后者未动，零回归）。
6. **元数据对齐**（`refreshSessionMetaTail`）：合并尾部的最后一条刷 `last_message_at/last_preview/last_message`（title 留给 SaveMessage 写者，不动标题语义）。
7. **接线**：`tailProbeFn` 函数缝仅在 `NewChatHistoryServiceWithPool` 且 pool 非 nil 时注入；nil（测试/无 DB 部署）保持历史行为逐字节不变。

**测试**（`chat_history_tail_test.go`，5 测试全绿）：

- `TestGetMessagesRepairsTruncatedTailFromDB`——**红证**：Redis 10 旧 + DB 13（前 10 同逻辑异 ID 异时间戳漂移 +1s）→ 读出 13、缓存被重写为 13、meta `last_message_at` 对齐；第二次读零探测（修复落地后纯缓存服务）。
- `TestGetMessagesFreshWatermarkSkipsProbe`——性能契约：新鲜水位命中不探测、不回源；过期后恰好探测一次。
- `TestMergeCacheAndDBTail`——配对语义：全覆盖漂移、合法重复最近配对、中段缺口时序归位、零配对发散信号、2min 容差边界（±1s）。
- `TestSliceMessagesPage`——分页语义锚定（13 条视窗 = 事发形态；offset 尾/越界/最老边缘部分窗口）。
- `TestReplaceRedisMessagesRewritesInsteadOfAppending`——修复写原语为重写非追加。

**红证突变验证**：临时把 `repairTailFromDB` 调用替换为旧短路行为（单文件粒度突变）→ 红证测试转红 → 已从备份还原（`grep -c MUTATION = 0`，还原后全绿）。

**回归（对比法零新增）**：基线先行存档 → 修复后同 filter 复跑比对——

| 包 | filter | 基线 | 修复后 | diff |
|---|---|---|---|---|
| internal/service | `ChatHistory\|Backfill\|DataConsistency\|ResolveSessionUUID` | 27 PASS | 27 PASS | 空 |
| internal/handler | `ChatHistory\|Conversation\|Realtime\|Roundtrip\|Citation\|OrchestratorFeedback` | 9 PASS | 9 PASS | 空 |

兜底：`./internal/service` + `./internal/handler` **全量** `CGO_ENABLED=0 go test` 双 ok（9.4s / 28.6s）；`go build ./...` 净；改动文件 `gofmt` 净（`gofmt -l` 标出的 `chat_history_persister_sql_test.go` 为**存量未格式化**，本卡未触碰，保持零 diff）。

注：worktree 缺 gitignore 的 `backend/gateway/gen/`，已按硬规则 1 跑 `make proto-gen`（docker 工具链缺失自动回退 host）生成后 handler 包方可测试；gen 产物不入 patch。

## ③ 冲突面声明

本卡只动 `backend/gateway/internal/service/chat_history.go` + 新增同目录测试文件 + `v3-output/HISTORY-TAIL/`。

- **wt217（llm_router 考证）**：无交集。
- **wt218（引擎 agents 面）**：无交集（本卡零引擎改动；裁决②时已声明不采纳）。
- **wt220（社群 token）**：无交集。
- **wt221（mobile 杂项）**：无交集。
- 同文件潜在并发：无已知卡在动 `chat_history.go`。合入顺序无敏感度；若上游也动了 `GetMessages`，冲突点集中在 501-546 行读路径块。

## ④ 诚实申报

1. **30s 水位内的残余窗口**：缺口发生后若水位仍新鲜，下一次读最多再陈旧 ≤30s（+一次探测时延）。要零窗口需每次命中都探测 DB（每读一查）或引擎 ack 同源（方案②，跨服务）——按「正常命中不回源不退性能」的卡面要求选择了有界陈旧。30s/探测行数/容差均为未配 config 的常量，调参无需动结构。
2. **首次探测的时延面**：水位过期的那一次命中增加一次索引范围扫描（常规 ~ms 级，封顶 2s 超时）。chatflow 每轮读上下文同样受此影响，但被 30s 水位摊薄到每会话至多 1 次/30s。
3. **内容配对的形态依赖**：配对假设「同一逻辑消息在网关 append 与引擎落库中 content 逐字相同」。若引擎侧对 content 做过改写（脱敏/markdown 归一），配对失败 → 逐行退化为 dbOnly 或触发零配对保护（DB 权威视图）——**正确性不破**，但该会话会走 DB 路径（缓存命中率下降）。未在真实 DB 上跑过双源集成验证（本卡测试用 miniredis + 函数缝伪造 DB 尾，无 Docker 依赖）；建议合入后由主会话活体探针复核一次真实会话的历史读。
4. **并发小窗口**：缓存重写（TxPipeline 原子）与既有异步 backfill 理论上可交错产生重复缓存条目——该风险类在既有代码中已存在并被接受（「缓存下次读自愈」），本修复的原子重写实际收窄了它。
5. **`matched==0` 保护分支**未被端到端测试覆盖（需真 DB 池），仅由 `TestMergeCacheAndDBTail` 的零配对单测覆盖判定信号；分支体是既有 `getMessagesFromDB` 路径的组合，风险低。
6. 测试曾两处断言写错（offset 窗口方向、12 号索引角色），修正的是测试预期而非实现——实现语义经与旧切片代码逐字比对及既有 `TestChatHistory_GetMessages_Offset` 锚定。

## ⑤ 收工核查

- [x] 零 commit / 零 push（`git status` 仅为工作树改动 + intent-to-add 的测试文件 + 未跟踪 v3-output/HISTORY-TAIL/）
- [x] 零凭据（无 .env 接触、无密码入库；测试用 miniredis，无外部服务依赖）
- [x] 主仓只读未触碰（`make proto-gen` 仅在本 worktree 内生成 gitignore 的 gen/ 产物）
- [x] /tmp 清理：`wt219_chat_history.go.bak`（突变备份）、`wt219_baseline_*.txt`、`wt219_after_*.txt` 已删
- [x] 无模拟器/浏览器/Gradle 等重负载残留；本卡全程 LIGHT（代码 + 定向 Go 测试），无内存尖峰
- [x] 交付物：`v3-output/HISTORY-TAIL/REPORT.md`（本文件）+ `v3-output/HISTORY-TAIL/changes.patch`（683 行，含新测试文件完整 diff）
