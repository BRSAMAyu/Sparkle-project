# PROD-FIX-3 — 巡检剩余 4 小件（可诊断性 + 降噪）

- 卡号：PROD-FIX-3（北极星全旅程战役 · C 纵队生产级线）
- Worker worktree：`/Users/brsama/code/GitHub/Sparkle-sysrev/wt182`（基线 `a338d989`，未 commit/push）
- 缺陷依据：`v3-output/PROD-LOG/REPORT.md`（wt175，基线 2b2bb68c）②-4 / ②-7 / ②-8 / ②-9 + ③降噪建议段
- 交付物：本报告 + `changes.patch`（`git diff` 生成，含 5 个修改文件 + 4 个新增文件，零凭据）
- 日期：2026-09-23

---

## ① 四件修法（对照报告验收）

### 1.（报告 ②-4）ReviewerAgent 超时空错误消息 —— 修法与验收

**报告裁决**：`reviewer_agent.py:392-400` 的 `asyncio.wait_for` 抛出的 `asyncio.TimeoutError` `str()` 为空串，`:462` `logger.error(f"... {e}")` 落出 `[ReviewerAgent] Review failed: ` 空尾巴，6 条 ERROR 不可诊断；R6-P0-3 fail-closed 使超时=审查失败。

**修法**：三层收口。
1. `_chat_json_with_timeout` 增加 `operation` 参数（调用方传 `"response review {review_id}"` / `"plan review {review_id}"`），捕获 `TimeoutError` 后测实际等待时长，re-raise 带完整上下文的 `TimeoutError`：`reviewer LLM timeout on {operation}: waited {elapsed}s > threshold {threshold}s (reviewer_model=...)`——py311 下 `asyncio.TimeoutError` 即内建 `TimeoutError`（ruff target=py311，UP041），类不变、所有 `except` 行为不变。
2. `review_llm_response` / `review_plan` 各增加独立 `except TimeoutError` 分支：ERROR 日志带哪个 review（review_id）、等了多久（elapsed）、阈值、模型，并显式标注 `fail-closed -> FAILED`；问题单 description 同步带超时细节（保留既有 `"审查过程出错"` / `"计划审查出错"` 前缀契约）。
3. 通用 `except Exception` 分支：`str(e).strip() or type(e).__name__` 空消息兜底，日志与 description 均不再出现空尾巴。

**验收**：新测试 4 条全绿——超时 ERROR 必含 review_id/timed out after/threshold=/reviewer_model=；包装消息含 operation+waited+threshold 且 `str()` 非空；`ValueError()`（str 为空）场景日志 `Review failed: ValueError`、description 含类名；plan review 路径同钉。既有 `test_reviewer_agent_phase62.py`（R6-P0-3 fail-closed 契约，含超时场景断言 `"审查过程出错"`）6 条全绿，fail-closed 语义零回退。卡内"评估超时重试"属报告修复思路的建议项，本卡不改 fail-closed 语义（见 ④）。

### 2.（报告 ②-7）checkpoint 允许清单过期 —— 修法与验收

**报告裁决**：`redis_checkpointer.py:37` 硬编码豁免 `["db_session","stream_callback","tools_schema"]`，新增非序列化 context key 走 `:43` WARNING，5 天 585 条（key 集：run_ledger / transparency_generator / emit_transparency_event / redis_client / grounding_validator）；报告修复思路=静态"已知不可序列化"清单（模块级常量）+已知 key 静默/DEBUG，未知 key 才 warn。

**修法**（按"清单需对齐当前代码面"的真实刷新，非照抄日志）：
- 模块级常量 `KNOWN_NON_SERIALIZABLE_CONTEXT_KEYS`（frozenset）：旧 3 key + 日志实证 5 key，每个 key 都在当前代码面核实过写入点——`execution_engine._inject_runtime_dependencies`（execution_engine.py:1824-1838：db_session/stream_callback/tools_schema/transparency_generator/emit_transparency_event/redis_client/run_ledger）、`orchestrator.py:2807`（run_ledger）、`routing_engine.py:2236`（grounding_validator），均为有意注入的运行期依赖对象/回调，本就不应入档。
- 已知 key → `logger.debug`（生产 INFO 面静默，调试可开）；**清单外** key 序列化失败仍 `logger.warning`，并提示"若是运行期依赖请登记"——保留"真有该序列化却坏掉的对象"的信号（降噪建议段原文语义）。
- 顺带全 context_data 写入点扫描：其余写入均为可序列化 payload（dict/list/str/数值），无漏网运行期对象。

**验收**：新测试 3 条——8 key 全量注入（不可序列化对象/lambda）时零 WARNING、payload 正确剔除且可序列化 key 照常入档、DEBUG 留痕；未知 key 场景 WARNING 仍在且带 key 名；常量覆盖 8 key 的对齐断言。

### 3.（报告 ②-8）关停期 `context canceled` 记 ERROR —— 修法与验收

**报告裁决**：`worker/base.go:145-148` processMessages 返回后不判 `ctx.Err()` 即 ERROR+1s 退避；`cmd/server/setup.go:405-451` 四个后台任务关停 error 同理——每次重启 ~13 条假 ERROR。报告修复思路=`if ctx.Err() != nil { log.Info("stopping"); return }` 模式套用到 worker/base.go 与 setup.go 关停分支。

**修法**（证据与根因全部在网关 Go 侧，逐点落地）：
- `worker/base.go` Run 循环：processMessages 失败后先判 `ctx.Err() != nil` → INFO `Worker stopping` 并立即 `return ctx.Err()`（不打错误指标、不再 1s 退避）；ctx 仍存活时的失败保持原 ERROR+指标+退避——即"仅非关停期 canceled 保持 ERROR"的卡语义。
- `worker/base.go` 新增导出助手 `LogRunnerStopped(log, ctx, name, err)`：err==nil → INFO；ctx 已取消（关停窗口）→ INFO `(graceful shutdown)`；ctx 存活时失败（含非关停期 canceled）→ ERROR。
- `cmd/server/setup.go` 全部 8 个 "stopped" 站点接入助手：File GC(:411)、Outbox publisher/cleaner、DLQ cleaner（cqrsBundle 三闭包）、Community/Task/Galaxy sync worker（startCQRSWorkers 三站点）——与报告"每次重启 ~13 条"的构成（4 runner + 3 sync worker + base.go 内部 ×3 组）一一对应。
- **main.py 关停段未动**：报告 ②-8 的证据/根因不含 Python 侧；main.py 关停段已由 R2-EI 系列与 PROD-FIX-1 改造为 `task.cancel() + suppress(asyncio.CancelledError)` 模式（20+ 消费者任务），不存在 canceled-as-ERROR 路径。wt179（9ba67176）的 SecurityMonitor shutdown 段原样保留。

**验收**：新 Go 测试 3 条（miniredis + zap observer）——①graceful 关停：取消 ctx 后 Run 返回 `context.Canceled` 且全程零 ERROR 级日志；②活进程故障：miniredis 关闭而 ctx 存活时 `Error processing messages` ERROR 仍在（分级不误伤）；③`LogRunnerStopped` 四态分级表（nil/INFO、关停 canceled/INFO、boom/ERROR、非关停 canceled/ERROR）。`CGO_ENABLED=0 go build ./...` 与 `go vet` 零输出。

### 4.（报告 ②-9）scheduler `%s` 参数被 loguru 静默丢弃 —— 修法与验收

**报告裁决**：`scheduler_service.py:233-237` 用 stdlib logging 的逗号参数风格调 loguru（只认 `{}`/f-string），`due=%s dispatched=%s` 两个字面量每分钟一条，调度吞吐不可见。

**修法**：改 loguru `{}` 位置参数形制（对齐 fleet achievement_engine %s→{} 批先例，如 achievement_engine.py:65/324），并留 PROD-LOG #9 注释。

**验收**：新测试 1 条——monkeypatch `AsyncSessionLocal`/`ExecutionScheduleService` 后跑 `run_execution_schedule_tick`，断言完成日志含 `due=3`、`dispatched=2` 真实数值且不含字面量 `%s`。

---

## ② 实现清单

修改（5）：
- `backend/app/agents/reviewer_agent.py` —— #4：`import time`；`_chat_json_with_timeout` 超时包装（operation/elapsed/threshold/model）；两个 review 方法独立超时分支 + 空消息类名兜底；共享 fail-closed 返回（R6-P0-3 语义不变）
- `backend/app/checkpoint/redis_checkpointer.py` —— #7：`KNOWN_NON_SERIALIZABLE_CONTEXT_KEYS`（8 key，含代码面对齐注释）；已知 key DEBUG 跳过、未知 key WARNING 保留
- `backend/app/services/scheduler_service.py` —— #9：`%s,` → `{}` 位置参数（1 处）
- `backend/gateway/internal/cqrs/worker/base.go` —— #8：Run 循环关停分支（ctx.Err() 判定，免 ERROR/免退避）；新增 `LogRunnerStopped` 分级助手
- `backend/gateway/cmd/server/setup.go` —— #8：8 个 runner 停止站点接入 `cqrsWorker.LogRunnerStopped`

新增（4，全为测试）：
- `backend/tests/unit/test_reviewer_agent_timeout_diagnostics.py`（4 测试）
- `backend/tests/unit/test_redis_checkpointer_allowlist.py`（3 测试）
- `backend/tests/unit/test_scheduler_execution_tick_log.py`（1 测试）
- `backend/gateway/internal/cqrs/worker/base_test.go`（3 测试）

## ③ 冲突面声明（逐个）

- **wt176/wt178（mobile）**：本卡零 mobile 文件，零重叠。
- **wt180（event_bus.py + chat_orchestrator.go + outbox）**：本卡文件=reviewer_agent.py / redis_checkpointer.py / scheduler_service.py / worker/base.go / setup.go + 测试，与三者零交集（outbox/publisher.go 只读未动；其 :99 的无退避缺陷属 wt180 卡，未触碰）。
- **wt181（community 模型/service + 迁移）**：零重叠。
- **main.py 关停段（wt179/9ba67176 刚改）**：本卡 #3 经核实为纯网关 Go 侧缺陷（报告 file:line 全部指向 worker/base.go 与 setup.go），**未改 main.py**；其关停段 `suppress(CancelledError)` + SecurityMonitor shutdown 现状完整保留，无回退。

## ④ 诚实申报

1. **报告 ②-9 "本仓 loguru 面上唯一一例"结论不准确**：全仓扫描发现 loguru+`%s` 同型缺陷面远不止 scheduler 一例——`core/celery_tasks.py`（28 处，如 :1112/:1843/:1846/:1902 抽验均为真丢参）、`services/profile_write_service.py`（9）、`services/chat_signal_collector.py`（6）、`services/task_event_consumer.py`（5）、`api/v1/growth.py`、`orchestration/orchestrator.py`（3）等 30+ 文件（部分需逐条甄别 f-string/printf 预格式化的假阳性）。stdlib logging 的 `%s`（pending_actions/budget_matrix 等）为正确用法不属缺陷。**本卡按卡面只修 scheduler 一处**（其余多在他人活跃域，超范围批量改动有冲突风险），建议开后续 `%s→{}` 批量卡（同 achievement_engine 先例）。
2. **checkpoint 域基线既有失败**：`tests/orchestration/test_orchestrator_state_transitions.py` 在基线 a338d989 即有 25 failed + 26 errors（对基线克隆复跑同一集合，失败名单 diff 为空、完全一致）。非本卡引入、也非 checkpoint 修复破坏；该文件失败集建议舰队另行立卡排查。
3. **black 状态**：仓库无 `[tool.black]` 配置（默认 88 列，与 AGENTS 的 120 列现状不符），基线 3 个 app 文件 `black --check` 本就不通过；本卡改动后与基线同态（非新引入）。ruff（项目配置 120 列）改动文件全绿，且修掉了自己引入的 4 处 UP041；gofmt/go vet 零违规。
4. **LogRunnerStopped 行为增量**：原 8 站点在 err==nil 时静默，现在会打一行 INFO "X stopped"（对齐同文件 :407 File event subscriber 既有模式），属降噪/可观测改进，非语义破坏。
5. **超时重试未做**：报告 ②-4 修复思路中"评估超时阈值/重试一次"涉入 R6-P0-3 fail-closed 语义变更（有 phase62 契约测试钉住），超出本卡"可诊断性+降噪"边界，未实施；现日志已带阈值数据，后续卡可据此评估。
6. **gen/**：worktree 缺 `backend/app/gen`、`backend/gateway/gen`，已从主仓拷贝用于测试/构建；gen/ 均 gitignored，不入 patch。
7. 本卡未改 proto/DB schema/分层边界；零凭据；未 commit 未 push。

## ⑤ 收工核查

**对比法回归（基线 = `git clone wt182` → /tmp 基线克隆，仅含 HEAD a338d989；双侧同集合）**：

| 域 | 基线 | 本卡 worktree | 新增失败 |
|---|---|---|---|
| reviewer（5 文件） | 23 passed / 0 failed | 27 passed / 0 failed（+4 新测试） | **0** |
| checkpoint（orchestrator_state_transitions + statechart_engine + 新测试） | 25F/39P/26E | 25F/42P/26E（失败名单 diff 为空，+3 新测试） | **0** |
| scheduler（5 文件） | 15 passed / 0 failed | 16 passed / 0 failed（+1 新测试） | **0** |
| lifespan/main（3 文件，含 PROD-FIX-1 回归） | 23 passed | 23 passed | **0** |
| Go `go build ./...` + `go test ./internal/cqrs/...` | build ok / 全 ok（worker 无测试） | build ok / 全 ok（worker 3 新测试 ok） | **0** |

**测试统计**：新增 Python 8 条 + Go 3 条全绿；既有 reviewer 域 23、scheduler 域 15、lifespan 域 23 条全绿；`SECRET_KEY=test DATABASE_URL="sqlite+aiosqlite:///:memory:" python3.11 -m pytest` 环境逐命令显式 cd。

**tmp 清理**：/tmp/prodfix3-baseline（基线克隆）、/tmp/prodfix3-wt-fails.txt、/tmp/prodfix3-base-fails.txt、backend/.pytest_cache（worktree 与克隆内）均已删除；未起模拟器/浏览器/Gradle，无 HEAVY 资源占用。

**交付物**：`v3-output/PROD-FIX-3/REPORT.md`（本文件）+ `v3-output/PROD-FIX-3/changes.patch`。
