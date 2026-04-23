# Stage40 → Main 集成回归报告

生成时间：2026-04-23
架构师：Claude Opus 4.7
执行分支：`claude/recover-stage40-into-main`（tip 见 §6）
基线：`integration/phase-i-exit` @ `2858f7fd`
移植源：local `main` @ `3397c2ef`

---

## 1. 上游背景

PROJECT_STATE_RECOVERY_REPORT_2026-04-23.md 与 STAGE40_MAIN_INTEGRATION_DECISION_2026-04-23.md 已经明确：

- `main` 相对 `origin/main` 超前 7 个提交，但仅承载审计恢复 + 少量安全/性能修复。
- Stage 34-40 的连续成果（含 Phase I Exit Gate、Kill Switch 三态化、Rule manifest 53 条等）在 `integration/phase-i-exit` 线。
- 两边都不干净：Stage 线混有 `.sgw_state/`、`.local_runtime/`、`.claude/worktrees/` 等运行产物；main 线缺 Stage40 主体。
- 治理结论：Stage40 线为主体基底，main 的 7 个提交作为 patch queue 移植进去；先打安全 tag，再生成干净集成分支。

本报告记录这条路径的实际执行与验证结果。

## 2. 安全 tag

已打，幂等，未覆盖已有引用：

| Tag | 指向 | 说明 |
| --- | --- | --- |
| `backup/main-audit-recovery-2026-04-23` | `3397c2ef` | 本地 main HEAD：7 个审计/安全提交 |
| `backup/phase-i-exit-stage40-2026-04-23` | `2858f7fd` | Stage 40 Phase I Exit Gate signed 的 integration/phase-i-exit |

任何时候都可以通过这两个 tag 回退到集成前状态。

## 3. 新集成分支

- 分支名：`claude/recover-stage40-into-main`
- 工作区：`/Users/brsama/code/GitHub/Sparkle-project/.claude/worktrees/stage40-recover`
- 基底：`integration/phase-i-exit` (2858f7fd)
- 提交线（oldest → newest，共 9 个 net 提交）：

```
9c9ebc88 chore(hygiene): remove tracked runtime artifacts + expand .gitignore
812be544 fix(security+perf): context_manager session fix, auth Celery migration, plans N+1 batch
4453a536 docs: restore audit reports and session tracker from integration branch
383dc0ff docs: update LOOP_SESSION_TRACKER with Session 9 (Chris S9) results
ca108451 fix(perf+cache): chat.py dead N+1 removal, profile_event_consumer cache fix
88a1a7b2 docs: update LOOP_SESSION_TRACKER with Session 10 (Chris S10) results
9dd66c02 fix(security): add TrustedProxies config + restore audit docs (#51 P1-1)
c283fa06 fix(gateway): drop unused cfg arg from NewSTTHandler call
5306af90 fix(gateway): add route-tier comments for data consistency routes (Rule AX)
```

`git diff --stat integration/phase-i-exit..HEAD`：178 files changed, 2659 insertions(+), 16097 deletions(-)。净删除行数 >> 新增主要源于 §4 的污染清理。

## 4. 污染清理（commit `9c9ebc88`）

从 Stage40 基底剔除 165 个原本不该进仓的文件：

| 目录 | 文件数 | 性质 |
| --- | --- | --- |
| `.sgw_state/` | 155 | SGW 运行时状态：`api_debug/*.json`、`claude_debug/latest`、`launch.out`、`sgw_checkpoint.json`、`stack_and_sgw.out` |
| `.local_runtime/minio-data/` | 3 | MinIO 内部二进制状态（`format.json`、`buckets/.heal`、tmp） |
| `.claude/worktrees/*` | 5 | gitlinks，指向 `origin/main` 的已失效 worktree 引用 |
| `.claude/scheduled_tasks.{json,lock}` | 2 | Claude Code 本地调度器状态 |

`.gitignore` 同步扩展，防止重入：

```
.sgw_state/
.local_runtime/
.codex-backups/
.claude/worktrees/
.claude/scheduled_tasks.{json,lock}
.claude/settings.local.json
.claude/ide/
2026-*-this-session-is-being-continued-from-a-previous-*.txt
```

保留 `.claude/plans/phase3_card_protocol_plan.md`（合法计划制品）。

## 5. 7 个 main 提交的处理结果

按时间序 cherry-pick `-x`，结果分类：

| # | Source (main) | 结果 | 净变化 vs 基底 | 说明 |
|---|---|---|---|---|
| 1 | `b44431d1` context/auth/plans/notification | `812be544` | 3 files / 27+/18- | 整合后只剩 context_manager N+1 batch + `self.db→db` 修复、auth 清掉冗余 `import asyncio`、notification `time_to_action` clamp。plans N+1 和 Celery 邮件迁移在 integration 线已有。conflict：`celery_tasks.py:788-794` 仅为格式分歧，保留 integration 风格 |
| 2 | `b31f036d` docs: restore audit | `4453a536` | 3 files / +1162 | 仅 3 份 integration 线尚未收录的审计文档 |
| 3 | `1c40f757` Session 9 tracker | `383dc0ff` | 1 file / +31 | clean |
| 4 | `ffbbceb3` chat/profile_event_consumer | `ca108451` | 1 file / 2+/2- | chat.py dead N+1 和 consumer 修复 integration 线已有，仅保留 DEEP_AUDIT_SUMMARY 状态更新 |
| 5 | `c66e57c3` Session 10 tracker | `88a1a7b2` | 1 file / +30 | clean |
| 6 | `e2c84585` security.py logger import | **SKIPPED（冗余）** | 0 | integration 线已有 `from loguru import logger`（line 11），patch empty |
| 7 | `3397c2ef` TrustedProxies + repair plan | `9dd66c02` | 4 files / +1382 | 主要是 `STRICT_REVALIDATED_GLOBAL_REPAIR_PLAN_RECONSTRUCTED_FROM_CONTEXT_*.md` 和 Go Gateway TrustedProxies |

所有 main 提交的意图已保留；冗余重复/格式分歧已被 merge 自动解决。

## 6. 集成期间发现并修复的 baseline 遗留问题

集成过程中触发，修复在本分支内闭合：

### 6.1 `NewSTTHandler` 签名不匹配（commit `c283fa06`）

```
cmd/server/setup.go:242:75: too many arguments in call to handler.NewSTTHandler
  have (string, *zap.Logger, *config.Config)
  want (string, *zap.Logger)
```

`integration/phase-i-exit` 已带着这个 build error 签了 Phase I Exit Gate。`NewSTTHandler` 本身不使用 `cfg`，调用侧把多余参数去掉即可，无行为变化。修复后 `go build ./...` 整 gateway 干净通过。

### 6.2 Rule AX 路由层级注释缺失（commit `5306af90`）

`scripts/run_all_rule_guards.sh --rule AX` 原始失败：

```
AX001 backend/gateway/internal/handler/data_consistency_handler.go:40
  missing adjacent route-tier comment :: api.GET("/chat/cache/check", authMiddleware, h.checkCache)
AX001 backend/gateway/internal/handler/data_consistency_handler.go:42
  missing adjacent route-tier comment :: api.GET("/chat/db/check", authMiddleware, h.checkDatabase)
```

把两条 `api.GET` 前的自由描述注释换成规范的 `// route-tier: authed`。

## 7. 验证矩阵

| 项 | 结果 | 证据 |
|---|---|---|
| Python 语法 (AST) | 8/8 pass | auth/context_manager/notification/chat/profile_event_consumer/security/celery_tasks/plans |
| `go build ./...` (gateway) | PASS | 修复 §6.1 后整 gateway 通过 |
| `go vet ./...` (gateway) | PASS | 无告警 |
| `go test ./internal/handler/... ./internal/config/...` | PASS | handler 包含 STT 代码编译+既有测试通过；config 无测试（与基线一致） |
| `scripts/run_all_rule_guards.sh` | 59/59 PASS | 含 Rule K/Y/Z/AX/AY/AQ/AV/BD 等；Phase I Exit Gate ready CONDITIONAL 标记保留 |
| `scripts/stage40/drill_all.sh` | PASS | 覆盖 stage29/30/31/40-calendar/33/34/35 的全部 bootstrap→off→shadow→live→shadow→off 过渡 |
| `pytest test_context_manager_community_context.py` | 1/1 PASS | 覆盖 §5 #1 中 context_manager 的主要 N+1 修复 |
| `pytest test_behavior_signal_collector.py` | 5/5 PASS | 覆盖 §5 #1 中新增的 mock |
| `pytest test_kill_switch_core.py + test_stage40_calendar_kill_switch.py` | 6/6 PASS | Stage40 核心能力 |

### 环境补齐（不计入代码更改）

- 临时将主仓 `.env` 拷入 worktree（`.env` 被 gitignore，不会进提交）。
- 为 `/opt/homebrew/opt/python/bin/python3.14`（Makefile 在非交互 shell 下解析到的 `python3`）安装 `grpcio-tools`，解除 `make proto-gen` 的 Python 端阻塞。这是 dev env setup，不是代码修改。

## 8. 工作树状态

```
$ git status --short
(clean)
```

生成物均已 gitignore：`backend/gateway/gen/`、`backend/app/gen/`、`.env`、`artifacts/*` 运行时产物、`tmp/`、`backend/.venv`。

## 9. 风险与遗留

### 9.1 Rule AQ 环境依赖

Rule AQ 需要 Python 端 proto stubs 已生成。在未安装 `grpcio-tools` 或未跑 `make proto-gen` 的 CI/新机器上会失败。**不是本集成分支的代码问题**，但建议：

- 把 `backend/requirements-dev.txt` 或 `pyproject.toml [dev]` 加入 `grpcio-tools`（若尚未）。
- CI pipeline 在跑 rule guards 前先 `make proto-gen`。

本报告不在此分支内做此补丁——它跨越开发环境治理边界，应单独评审。

### 9.2 Phase I Exit Gate 状态

`[Rule BD] PASS - PHASE_I_EXIT_READY: CONDITIONAL`。这个 CONDITIONAL 是 integration 线签字时的既有状态，本集成未改动。若要升级为 UNCONDITIONAL，需要按 Rule BD 定义补完 SGW dogfood 真跑等项，不在本次回主干整合范围内。

### 9.3 未推送

- 新分支 `claude/recover-stage40-into-main` 仅在本地；未推送 `origin`。
- 两个 `backup/*` tag 也仅在本地。
- **不建议**自动 fast-forward `main` 到本分支——应由用户人工最终拍板（选择 PR 评审 / squash merge / 直接 FF 三种路径之一）。

### 9.4 `.claude/worktrees/` 下尚有 prunable 记录

`git worktree list` 还列着若干 `prunable` 的老 worktree，指向已经在 §4 删除的 `.claude/worktrees/*` gitlink。可用 `git worktree prune` 清理，但这是用户本地状态，未执行。

## 10. 推荐下一步

1. 用户审阅本分支 diff：`git log integration/phase-i-exit..claude/recover-stage40-into-main` + `git diff integration/phase-i-exit..claude/recover-stage40-into-main`。
2. 选择合并路径：
   - A. 保留所有 9 个 commit → `git push origin claude/recover-stage40-into-main` + 开 PR 合入 main。
   - B. squash → 保留整一个「Stage40 → main 集成」commit。
   - C. 先把 `main` ref 强制指向本分支 tip（需 `--force-with-lease`，**会覆盖 main 当前 7 提交**，仅在确认两个 backup tag 到位时才可用）。
3. 合入后：
   - `git worktree prune` 清理 stale worktree 引用。
   - `make proto-gen` 后再跑一遍 `scripts/run_all_rule_guards.sh` 作为回归兜底。

## 11. 一句话判断

Stage40 线已作为干净、可编译、全量规则合规的主干候选就绪；main 的 7 个修复意图全部保留；两个 baseline 遗留 build/rule 问题已在回主干过程中顺手闭合。可以进入评审与发布决策阶段。
