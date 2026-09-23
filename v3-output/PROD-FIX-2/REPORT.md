# PROD-FIX-2 · 事件总线锁域修复 + 两处假告警/退避（#3+#5+#6）— 收工报告

- Worker：C 纵队修复 Worker（生产级线，PROD-FIX-2 卡）
- Worktree：`/Users/brsama/code/GitHub/Sparkle-sysrev/wt180`（基线 a2506361，开工时干净）
- 日期：2026-09-23
- 依据：主仓 `v3-output/PROD-LOG/REPORT.md` 缺陷 #3 / #5 / #6 + ③降噪建议段
- 交付物：6 文件（3 修改 + 3 新测试）+ `changes.patch`（733 行）+ 本报告；未 commit / 未 push；零凭据；gen/ 已按纪律从主仓拷贝（gitignore 覆盖，不入 patch）
- 基线对照：`git clone` 至 `/tmp/prodfix2-baseline`（纯 HEAD a2506361，收工已删），同命令同集对比

---

## 0. 结论一句话

三处生产缺陷全部修复并带红证交付：**#3** 幂等锁/去重标记从 stream 作用域改为 `(stream, consumer group, event)` 三元组作用域（同一修复同时消解锁互斥与跨组误判重复两个病灶）+ 抢锁失败降 DEBUG；**#5** WS close 1000（normal）归入 DEBUG 通道，仅真异常 warn；**#6** outbox publisher 对持续失败引入指数退避（pollInterval 倍增、60s 封顶）+ 同因错误日志限频（首条+每第 10 条）+ 恢复复位并报恢复日志。回归面 event_bus 域 + EVENT-ACK 系 + Go 全量 **零新增失败**；patch 已在干净基线克隆上完成 apply→编译→定向测试 三重合入预演。

## ① 三处修法 + 红证复现说明

### #3 事件总线幂等锁不按消费组隔离（M）— `backend/app/core/event_bus.py`

**修前行为**（`_process_stream_message`）：`idempotency_key = f"evt:{stream}:{effective_id}"` 仅按 stream 作用域。`sparkle_events` 上 30+ 消费组每条消息各得一份投递，却共享同一把 SET-NX 锁与同一个 done 标记：
- **锁互斥面**：组 A 持锁期间组 B `lock()` 失败 → `return` 不 ACK → 消息滞留 B 的 PEL 等 `pending_retry_idle_ms=5000` autoclaim → 每条事件对多数组引入 ≥5s 扇出延迟（生产 129 条 "Could not acquire lock" 假告警）。
- **误判重复面**（比锁更深的语义 bug）：组 A 完成处理后写入 done 标记，组 B 随后的投递在 `idempotency.get()` 命中 → "Skipping duplicate" 直接跳过——**组 B 的回调从未执行**。即 fan-out 语义被破坏：每条事件实际只有一个消费组真正处理。

**修法**：键改为 `evt:{stream}:{group_name}:{effective_id}`（锁与 done 标记同键派生，一并隔离）；抢锁失败 WARNING → DEBUG（组内竞争是正常态，降噪表对应项）。

**红证复现**（`backend/tests/unit/test_event_bus_group_scoped_idempotency.py`，修前实测 4 红 1 绿）：
1. `test_two_groups_both_consume_same_event` — 组 A 处理完后组 B 顺序投递：修前 `calls_b == 0`（日志实证 "Skipping duplicate message"）→ 红；修后两组各消费一次。
2. `test_two_groups_concurrent_same_event_no_mutual_block` — 组 A 慢回调持锁（`asyncio.Event` 同步起点，确定性），组 B 并发投递：修前 `calls_b == 0` 且不 ACK → 红；修后 `calls_b == 1`、xack 两次。
3. `test_lock_failure_log_is_not_warning` — loguru sink 捕获，修前存在 WARNING "Could not acquire lock" → 红；修后无。
4. `test_idempotency_keys_are_group_scoped` — 键形状钉死：两组键集合前缀含各自组名且不相交 → 修前红。
5. `test_same_group_duplicate_still_skipped` — 组内重复投递（`_original_message_id` 重试副本）仍幂等跳过 + ACK：修前即绿（基线语义），修复后保持绿 = **组内 at-least-once 去重不回退的护栏**。

**诚实语义说明**：幂等主体从"stream×事件"变为"消费组×事件"。这正是 Redis Streams fan-out 的应有语义——每个组本就该独立消费全量事件；组内（同 group_name）幂等语义一字未变。

### #5 WebSocket 正常断连被当异常告警（S）— `backend/gateway/internal/handler/chat_orchestrator.go`

**修前行为**（读循环 ：386）：`IsUnexpectedCloseError(err, CloseGoingAway, CloseAbnormalClosure)`——gorilla 只把**列出的** code 视为预期，`1000 (normal)` 不在列 → 每次用户主动退出都 warn（生产 223 条 / 5 天）。

**修法**：抽出包级函数 `logWebSocketReadError(err)`：close 1000 → `Debug("WebSocket closed normally by client")`；GoingAway/AbnormalClosure 保持历史静默（沿用原语义）；其余 close code 与非 close 读错误保持原样（不发明新日志）。调用点一行替换，行为面其余不动。

**红证**：单测 `chat_orchestrator_closelog_test.go` 4 条（zap observer 断言分级）。突变红证：临时把 helper 的 1000-DEBUG 分支短路为恒 warn（等价旧行为）→ `TestLogWebSocketReadError_NormalCloseIsDebugNotWarn` 红（报错即钉子文案 "close 1000 (normal) must never warn — it is the alert-baseline defect"），还原后绿。注：helper 为新符号，对基线无编译红可打，突变法即其红证。

### #6 Outbox publisher 无失败退避（S-M）— `backend/gateway/internal/cqrs/outbox/publisher.go`

**修前行为**（Run）：固定 `time.NewTicker(pollInterval=0.1s)`，`publishBatch` 失败仅逐条 Error + 计数器 → DB 宕 16h = 10 条/s × 8,494 条实证刷屏。

**修法**（对照 file_event_subscriber 的 RunWithRestart 模式）：
- 循环改 `time.After(delay)` 变节拍：连续失败时 `backoffDelay()` = pollInterval 逐次倍增，`DefaultMaxBackoff=60s` 封顶（0.1s 基调下第 10 次失败触顶；故障稳态 1 次/分钟 vs 修前 10 次/秒，约 **600×** 降噪）；ctx 取消在任意节拍即时响应。
- 同因日志限频 `noteFailure`：第 1 条 + 每第 10 条连续失败打 Error（带 `consecutive_failures` + `next_retry_in`）；中间失败静默（`OutboxPublishErrors` 指标仍逐次递增，速率观测不丢）。
- `noteSuccess`：任一成功即复位节拍，且若此前有失败串，打 `Info("Outbox publish recovered")` 带 `consecutive_failures` + `failure_duration`（直接回应报告"区分不了抖一下和宕 16 小时"）。
- `PublisherConfig` 新增 `MaxBackoff`（零值回退默认 60s）；唯一调用点 `setup.go:374` 无 config 覆盖，零波及。

**红证**：单测 `publisher_test.go` 5 条。突变红证：`backoffDelay` 突变为恒返 `pollInterval`（等价旧固定节拍）→ `TestRun_BacksoffDuringOutageAndKeepsContextCancellationResponsive` 红（"got 13 attempts in 150ms"），还原后绿。

## ② 实现清单

| 文件 | 状态 | 内容 |
|---|---|---|
| `backend/app/core/event_bus.py` | M | `_process_stream_message`：幂等键加 `group_name` 维度（:1237 区）+ 抢锁失败 WARNING→DEBUG（带 PROD-FIX-2 依据注释） |
| `backend/gateway/internal/handler/chat_orchestrator.go` | M | 读循环 warn 分支替换为 `logWebSocketReadError(err)` + 新 helper（分级注释） |
| `backend/gateway/internal/cqrs/outbox/publisher.go` | M | 退避状态字段、`MaxBackoff` 配置、Run 变节拍循环、`noteFailure/noteSuccess/backoffDelay` 三 helper、恢复/限频日志 |
| `backend/tests/unit/test_event_bus_group_scoped_idempotency.py` | 新 | #3 红证/绿证 5 测试（black 120 通过） |
| `backend/gateway/internal/handler/chat_orchestrator_closelog_test.go` | 新 | #5 分级语义 4 测试 |
| `backend/gateway/internal/cqrs/outbox/publisher_test.go` | 新 | #6 退避曲线/日志限频/恢复复位/Run 循环行为 5 测试 |

验证命令（全部单进程、显式 cd）：
- Python：`SECRET_KEY=test DATABASE_URL="sqlite+aiosqlite:///:memory:" python3.11 -m pytest ... --timeout=60`
- Go：`cd backend/gateway && CGO_ENABLED=0 go test ...`（本机 Xcode 许可问题规避 cgo）

## ③ 冲突面声明（逐个核对，零重叠）

本卡改动 6 文件：`app/core/event_bus.py`、`gateway/internal/handler/chat_orchestrator.go`、`gateway/internal/cqrs/outbox/publisher.go` + 3 个新测试文件。

| 声明卡 | 其文件面 | 与本卡重叠 |
|---|---|---|
| wt170 | achievement + Alembic + photon | **零重叠**（worktree 已合入移除，不存在；其声明的文件面与上列 6 文件无交集） |
| wt179 | main.py / security_monitor / predictive_service | **零重叠**（同上，已不存在；文件面无交集） |
| wt176/177/178 | mobile | **零重叠**（176/177 已移除；wt178 实测 `git status` 无任何与本卡 6 文件匹配的条目） |

补充：event_bus.py 的 EVENT-ACK / EVENT-ACK-2 / IDEM-GAPS 语义面（消费端上抛契约、pending 回收、DLQ）本卡**只改键字符串与一处日志级别**，未触碰消费异常传播、requeue/DLQ、XAUTOCLAIM 任何逻辑——回归面零红实证见下。

## ④ 诚实申报

1. **#3 键语义变更后的 Redis 旧键过渡**：旧键两族——`idempotency:evt:{stream}:{id}`（done 标记，TTL 86400=24h）与 `idempotency:lock:evt:{stream}:{id}`（锁，ex=30s）。新代码**只读新形状键**，旧键自然过期：锁 30s 内消失，done 标记 ≤24h 内消失，**无需迁移/清理**。过渡期唯一语义后果：部署前 ≤24h 内已被处理的事件，部署后按组各补一次消费——这正是修复要恢复的 fan-out 语义，不构成重复副作用（各消费组内仍有组作用域幂等）。
2. **预存（非本卡） hang**：`tests/unit/test_eventbus_subscribe_raise.py` 3 测试中 2 条（`test_busygroup_proceeds_to_consume_loop`、`test_consumer_pattern_receives_exception`）**在基线 a2506361 干净克隆上同样无限挂起**（实测复现；机制：subscribe 成功后 `_consume_loop` 任务在 AsyncMock 下异常退出，F3 自动重启回调 `_restart_consume_loop` 在 `asyncio.run` 关停期无限重生任务）。与本卡改动无关（本卡未触碰 subscribe/_consume_loop/重启回调）。已 `--deselect` 并如实记录；建议后续开小卡：重启回调加关停护栏（如 `self._running` 检查时机）或该测试文件改用更逼真的 redis 桩。
3. **其余预存差异（基线逐一复现同一集合，零新增）**：
   - Go `internal/config` 失败：环境缺 `JWT_SECRET`（基线克隆同错；补 env 即绿，最终全量 11 包全绿）。
   - pytest `test_event_bus_real_redis.py` 6 skip：需活 Redis（纪律：不动活栈），基线同 skip。
4. **black 预存 hunk 未动**：`event_bus.py:970/:1039` 有两处 black 预存格式差异（`import time as _time` 后空行，非本卡改动行）。为保持 patch 最小未顺手格式化；本卡新增/修改行全部 black-120 干净。
5. **pytest-timeout 对该 hang 失效**：挂起点在 asyncio 任务区，signal 超时无法回收，表现为进程级挂起——排查时以 `--deselect` 规避，非测试失败。
6. **日志面变化申报**：#5 后 close 1000 从 warn 消失（新增 DEBUG 行，生产 log 级别通常不输出）；#6 后 "Failed to publish batch" 从每 attempt 一条变为 1+⌊n/10⌋ 条（新增 "Outbox publish recovered" Info）；#3 后 "Could not acquire lock" 从 warn 变 debug。告警基线相应下降为**预期效果**，值班同学知悉。
7. **未动面**：未动 proto、未动迁移、未动活栈/活 Redis、未动 `gen/`（本地拷贝仅测试用，gitignore 覆盖，`git status` 实证不入 patch）、未 commit/push。

## ⑤ 收工核查

- [x] 红证先行：#3 并发/顺序双面红证（4 红）+ #5/#6 突变红证，修后全绿
- [x] #3 特别验：多消费组并行互不阻塞（含 ACK 面断言）、组内幂等不回退护栏、EVENT-ACK 系全绿（17+12+1+…）
- [x] 回归对比法：event_bus 域 + EVENT-ACK 系 pytest 零新增失败；Go 定向包（handler 29.8s / cqrs 系）+ 全量 `CGO_ENABLED=0 go test ./...` 11 包全绿（唯一 fail=预存 JWT_SECRET env，基线同错）
- [x] patch 合入预演：干净基线克隆 `git apply --3way` → 标记 grep → Python 修复测试 5/5 → Go build+定向测试全绿
- [x] 风格：ruff 全过；black 120（本卡行）；gofmt clean
- [x] 纪律：未 commit/push；主仓只读；单测试进程；零凭据；HEAVY=0（纯单测）
- [x] 收工清理：`/tmp/prodfix2-baseline`、`/tmp/wt180-co-backup.go`、`/tmp/wt180-pub-backup.go`、`/tmp/prodfix2-*.log`、`/tmp/prodfix2-sample.txt` 全部删除（见下方清理命令执行记录）；无独立端口进程残留（Go/pytest 均前台短命）；无模拟器/浏览器实例

### 附：回归结果明细

| 命令面 | 基线（a2506361 克隆） | 修后 worktree | 判定 |
|---|---|---|---|
| `tests/unit/test_event_bus_group_scoped_idempotency.py`（新） | —（不存在） | **5 passed**（修前 4 failed） | ✅ 红转绿 |
| `tests/unit/test_event_bus_reliability.py` | 4 passed | 4 passed | ✅ |
| `tests/unit/test_event_bus_regression.py` | 3 passed | 3 passed | ✅ |
| `tests/unit/test_event_ack_reliability.py` | 17 passed | 17 passed | ✅ |
| `tests/unit/test_event_ack2_reliability.py` | 12 passed | 12 passed | ✅ |
| `tests/unit/test_eventbus_subscribe_raise.py` | 1 passed + 2 挂起（实测） | 同基线（1 passed，2 条 deselect） | ✅ 零差异（预存 hang，见 ④-2） |
| `first_deploy` + `lag_monitor` + `real_redis` + `spine_event_bridge` + `srl_event_consume` + `test_event_bus_shutdown.py` | — | 19 passed, 9 skipped（活 Redis skip） | ✅ |
| `go test ./internal/handler/ ./internal/cqrs/...`（CGO_ENABLED=0） | — | 全 ok（handler 29.8s / outbox 含新 5 测试） | ✅ |
| `go test ./...`（CGO_ENABLED=0，JWT_SECRET 补齐） | config 包 env fail（预存） | **11 包全 ok，0 fail** | ✅ 零新增 |
| 干净克隆 `git apply --3way changes.patch` | — | 6 文件干净落盘 + Python 5/5 + Go build/test 全绿 | ✅ 合入预演通过 |
