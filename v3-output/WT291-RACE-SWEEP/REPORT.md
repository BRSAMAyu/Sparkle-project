# wt291-race-sweep 交付报告

> C 线·gateway 全仓 `-race` 巡检（wt290 交接建议卡）。背景：wt290 在
> `internal/cqrs/outbox` 实锤测试桩中途裸改竞争后，怀疑全仓存在同类潜伏项。
> 本卡结论先行：**三轮 -race（含压力抖动）+ 全量静态审查 = 0 实锤竞争，
> 桩/生产双双零发现，无代码改动**。wt290 的 heal 修复经 count=5 复钉保持绿。

## ① 巡检覆盖面

- **包数**：`backend/gateway` 全模块 `go list ./...` = **34 包**，其中 **12 包含测试**（cmd/server、agent、config、cqrs、cqrs/event、cqrs/outbox、cqrs/worker、db、handler、logsafe、middleware、service），其余 22 包无测试文件（编译面覆盖）。
- **跳过数**：0（`grep SKIP` 两轮全量日志均为 0，无环境跳测——Redis/miniredis 走真实栈，DB 集成测试在本环境可用）。
- **轮次与耗时**（全程 `-p 1` 串行）：

| 轮次 | 命令形制 | 耗时 | 结果 |
|---|---|---|---|
| 预热编译 | `CGO_ENABLED=1 go test -race -run ZZZ ./...`（只编译不跑） | 16s | exit 0 |
| 第 1 轮全量 | `go test -race -count=1 -p 1 ./...` | 83s | 12 包 ok，0 race |
| 第 2 轮全量抖动 | `go test -race -count=3 -p 1 ./...` | 186s | 12 包 ok，0 race |
| 第 3 轮定向压力 | `GOMAXPROCS=2 go test -race -count=2`：handler/service/cqrs…/agent 四个并发密集包 | 103s | ok，0 race |
| wt290 复钉 | `go test -race -count=5 -run TestRun_ ./internal/cqrs/outbox` | 13s | ok，heal 修复保持绿 |

- **静态审查面**：29 个含 `go func` 的测试文件逐一核对同步形制（mutex/channel/WaitGroup/sync.Once/httptest-Close 的 WaitGroup happens-before），未发现 wt290 家族（「测试桩中途裸改状态无同步」）残留。

## ② 发现计数（桩/生产分叉）

**实锤竞争 0 项（测试桩 0 / 生产 0）**。静态审查中的三类「形似嫌疑」复核后均确认有 happens-before 边，属误报排除而非修复：

1. `internal/service/file_event_hub_test.go` 的 `serverConn` 在 HTTP handler goroutine 裸写、测试主 goroutine 裸读——安全，因写侧随后 `hub.Register`、读侧先 `hub.Count`，共享 `hub.mu` 建立 HB 边；`serverConns` 切片另有 `serverConnsMu` 护住。
2. `internal/service/signal_hub_test.go` 的 `Send` 后裸读 `conn.writes`——安全，`SignalHub.Send` 是同步直写（不起新 goroutine），函数返回即 HB。
3. `internal/cqrs/worker/base_test.go` 的 `mr.Close()` 中途关 miniredis——安全，miniredis 内部有锁且读写走真实网络栈，非共享内存竞争。

wt290 交接怀疑的 `internal/cqrs/worker` 专项核查：其测试经 log observer（线程安全）与 `<-runResult` channel 同步，干净。

## ③ 修法与验证

- **无需修复**（零发现），故无代码 diff、无 changes.patch、无业务 commit；本卡唯一交付为本报告（docs commit）。
- **wt290 前任修复复验**：`-race -count=5` 定向钉测 outbox `TestRun_*` 全绿——heal 模式（fake 加 mutex + 原子 heal 迁移）经受住本机 5 连跑。
- **环境验证**：`CGO_ENABLED=0 go build ./...` exit 0；`go vet ./...` exit 0；`golangci-lint run`（cqrs/service/agent/cmd 四域）exit 0 零告警。
- **守卫**：`scripts/run_all_rule_guards.sh` exit 1，仅 **AQ/BG 红**——与 wt290 记录完全同源（worktree 缺 `app.gen` Python 模块与 `*_pb2.py`/`*.pb.dart` 生成物），卡内已预告属环境红，**主仓复跑为准**；其余全部守卫 PASS（含 alembic 单头 gseed_20260923）。
- 本 worktree 的 `gen/` 缺口已从主仓只读拷贝补齐（`backend/gateway/gen`，1.1M，gitignore 内，无 git 污染），34 包得以全量编译。

## ④ 资源峰值

全程 **LIGHT**（无模拟器/Gradle/浏览器；`-p 1` 单测试二进制串行）。开工时 swap free 866M < 1.2G HEAVY 启动门未开 → 按卡内预案先做 LIGHT 准备（补 gen/、预热编译、静态审查），race 全程串行分批，未触发熔断（swap 全程 >860M）；收工时 swap free 回升至 1.46G、load 3.5。/tmp 自产物 5 个日志（`wt291_*.log`），收工已清。

## ⑤ 交接建议

1. **gateway 竞争面可关闭**：三轮抖动（count=1/3/压力 GOMAXPROCS=2）+ 静态全查双保险，本机 16GB 环境下未复现任何 race。wt290 的 CI 实锤是时序概率性的，本卡置信度等级为「三轮全绿」，不宣称绝对无竞争。
2. **CI `-race` 是长期 ratchet**：本卡未改任何代码，CI Backend Tests 无需对比法回归；建议维持 CI -race 常开即可捕获未来潜伏项（wt290 正是被它抓住的）。
3. **生产侧单一写入者约定仍在**：`Publisher` backoff 状态单 goroutine 独占、`SignalHub.Send` 同步直写等约定目前靠注释与测试钉住；未来若加第二个控制面入口（admin reset 等），须先收进 mutex/atomic（wt290 报告第 5.2 条继续有效）。
4. **Python 引擎侧未在本卡范围**：若需同等置信度，建议另开卡跑 `pytest` 并发/竞态面（本卡为 C 线 gateway 范围）。
5. **worktree 环境红模板**：AQ/BG 红因 `gen/` 生成物缺口——本卡用「主仓只读拷贝 gen/」先补齐再跑测试的做法可复用（gen/ 在 gitignore 内，不污染交付）。

## 交付物

- 本报告：`v3-output/WT291-RACE-SWEEP/REPORT.md`（唯一改动，docs commit，本地不 push）
- changes.patch：不适用（零代码改动）
- 本树 HEAD 继承 wt290 修复 commit `eab2a62b`，测试基线即「wt290 修复后」状态
