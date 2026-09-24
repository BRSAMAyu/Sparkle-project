# wt290-outbox-race 交付报告

> C 线·真数据竞争修复。CI `go test -race`（run 35962100809，2026-09-24 06:03）在
> `github.com/sparkle/gateway/internal/cqrs/outbox` 实锤 race，本地不带 -race 一直绿——竞争潜伏在测试桩。
> 本地 commit `93df47d6`，未 push。

## ① 竞争对定位（变量 × goroutine × 堆栈）

CI 共报 6 组 WARNING: DATA RACE，全部同一对 goroutine，变量全部落在测试桩 `fakeRepo`：

| # | 写方（goroutine 38，测试主 goroutine） | 读方（goroutine 39，Run 轮询 goroutine） | 变量 |
|---|---|---|---|
| 1 | publisher_test.go:165 `repo.getUnpublishedErr = nil` | publisher_test.go:39 `return f.entries, f.getUnpublishedErr`（`fakeRepo.GetUnpublished`，经 publisher.go:196→123 `Run`） | `fakeRepo.getUnpublishedErr` |
| 2 | publisher_test.go:166 `repo.entries = …` | 同上 :39 | `fakeRepo.entries`（slice header） |
| 3-6 | publisher_test.go:166-169 复合字面量构造 `*event.OutboxEntry`（ID/EventType/Payload/CreatedAt） | publisher.go:210/212 `publishBatch` 迭代返回的 entries 并取 entry 字段（`entry.ToDomainEvent()`） | entry 对象字段 |

生产代码 `publisher.go`（`consecutiveFailures`/`firstFailureAt` 由 Run 循环独占，`running` 为 atomic.Bool）**无竞争**，在堆栈中仅作为被测试桩坑害的读者出现。缺陷 100% 在测试侧：测试 goroutine 在 Run 轮询进行中对 fake 字段裸写，无任何同步。读 `bus.publishes`/`repo.getCalls` 均发生在 `<-done` 之后，经 channel 建立 happens-before，本就安全，未改。

## ② 修法与同步原语选择依据

只改 `backend/gateway/internal/cqrs/outbox/publisher_test.go`（+21/-3）：

- `fakeRepo` 加 `sync.Mutex`，护住 `getUnpublishedErr`/`entries`/`getCalls`；`GetUnpublished` 锁内返回。
- 新增 `heal(entries ...*event.OutboxEntry)`：清错 + 换 entries 为**一次原子状态迁移**；测试由裸写字段改为调 `repo.heal(...)`。

**选择 mutex 而非 atomic/channel**：`heal` 需把 err 与 entries 作为一致状态发布（atomic 无法成组打包两个异构字段）；channel 会迫使 fake 重构成消息循环，超出最小修复面；mutex 是 Go 测试桩的惯用形制，且快照语义安全——`heal` 只替换 slice header、原位不动 entries 内容，锁外迭代旧快照无竞争。

## ③ race 验证结果

| 验证 | 命令 | 结果 |
|---|---|---|
| 修复前复现 | `CGO_ENABLED=1 go test -race -count=3 -run TestRun_Recovers…` | FAIL: race detected（与 CI 同一对） |
| 修复后钉测 | 同上 `-count=5` | ok，5/5 绿（macOS ld LC_DYSYMTAB warning 为无害链接器噪声） |
| 包全量 | `go test -race -count=2 ./internal/cqrs/outbox/...` | ok |
| 子树扫 | `go test -race ./internal/cqrs/...` | exit 0 全绿 |
| 常规面 | `CGO_ENABLED=0 go build/vet ./internal/cqrs/...` | OK（仓根 `./...` 因 worktree 缺 `gen/` 生成物红，非本卡改动，主仓复跑为准） |
| lint | `golangci-lint run internal/cqrs/outbox/` | exit 0 零告警 |
| 守卫 | `scripts/run_all_rule_guards.sh` | 仅 AQ/BG 红——均为 worktree 缺生成物环境红（AQ: `No module named 'app.gen'`；BG: `*.pb.go/pb2.py/pb.dart` missing），卡内已预告可注明；其余守卫全过 |

**回归断言判断**：未另加运行时断言——本测试在 CI 的 `-race` 执行本身就是回归钉（竞争由 detector 判决，普通断言无法钉竞争窗口）；恢复语义（recovery 日志、节奏复位）已有既有断言钉住。

## ④ 资源峰值

全程 LIGHT（无模拟器/Gradle/浏览器/构建缓存重压）：单包 go test -race 峰值约 1 核、数百 MB 内存；守卫套件一轮 Python 脚本。开工时 swap free 1.3G、load 8.1，未触发 HEAVY 门。`/tmp` 自产物仅 `wt290_ci_job.log`（CI 日志，已清）。

## ⑤ 交接建议

1. 合入后观察下一次 CI Backend Tests（-race）该包是否转绿；本修复不改生产行为，无需对比法回归。
2. 生产 `Publisher` 的 backoff 状态是"单 goroutine 独占"约定（注释已写明），若未来加第二个控制面入口（如 admin 触发 reset），须先把该状态收进 mutex/atomic——已有人踩过测试桩同类坑的模式。
3. 全仓其他带 goroutine 循环 + 测试桩中途改桩状态的测试可能存在同类潜伏竞争（`internal/cqrs/worker` 等），建议另开卡做一轮 `-race` 全量巡检（本次仅定向扫了 `internal/cqrs/`，已绿）。
4. worktree `gen/` 生成物缺失导致 AQ/BG 与仓根 build 红，属环境性：主仓复跑守卫为准（守卫脚本自身已钉 sqlite 规避 .env 形态差异，仅生成物缺口残留）。

## 交付物

- 本树 commit：`93df47d6 fix(outbox): make test fake race-free — mutex-guard fakeRepo, atomic heal transition (wt290)`（未 push）
- `v3-output/wt290-outbox-race/changes.patch`（对 HEAD~1 的 diff）
- 改动文件：`backend/gateway/internal/cqrs/outbox/publisher_test.go`（唯一）
