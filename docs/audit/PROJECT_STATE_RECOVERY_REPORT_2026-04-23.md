# Sparkle 项目分支状态与恢复复盘报告

生成时间：2026-04-23 22:30 Asia/Shanghai  
当前工作区：`/Users/brsama/code/GitHub/Sparkle-project`  
当前分支：`main`  
当前 HEAD：`3397c2ef fix(security): add TrustedProxies config + restore audit docs (#51 P1-1)`  
远端 main：`origin/main = 9011f356 Merge pull request #73 from BRSAMAyu:本地全量收尾`

## 1. 最重要结论

Stage34-40 的成果没有丢，但没有完整融入当前 `main`。

当前项目实际上分成了两条主要线：

- `main` 线：从 `origin/main` / PR #73 继续推进，后来又补了 7 个本地提交，主要是审计恢复和少量修复。
- `stage/integration` 线：从更早的共同祖先分出，包含 Stage34、Stage35、Stage36、Stage37、Stage38、Stage39、Stage40，以及 `integration/phase-i-exit` 上后续的 Phase I exit 和审计 closeout 修复。

这意味着：

- 之前 Stage34-40 的工作不是白做了，它们仍在分支里。
- 但 `main` 当前不是 Stage40 的延续。
- 直接基于当前 `main` 继续开发，会缺失大量 Stage34-40 架构、迁移、脚本、测试、文档和 guardrail。
- 刚刚恢复/重建的审查文档不是白做了：它们已经出现在当前 `main` 本地提交历史中，但它们只是文档和部分审计修复，不能替代 Stage40 代码合并。

## 2. 当前分支拓扑事实

关键分支与提交：

- `main`: `3397c2ef`
- `origin/main`: `9011f356`
- `codex/stage34-impl`: `5476e896`
- `codex/stage35-impl`: `85eba758`
- `codex/stage20-execution`: `eae7d070`
- `claude/stage40-impl`: `9df6934f`
- `integration/phase-i-exit`: `2858f7fd`

共同祖先：

- `main` 与 `codex/stage34-impl` 的 merge-base 是 `bf9adc9c 修复打磨`
- `main` 与 `codex/stage35-impl` 的 merge-base 是 `bf9adc9c 修复打磨`
- `main` 与 `codex/stage20-execution` 的 merge-base 是 `bf9adc9c 修复打磨`
- `main` 与 `claude/stage40-impl` 的 merge-base 是 `bf9adc9c 修复打磨`
- `main` 与 `integration/phase-i-exit` 的 merge-base 是 `bf9adc9c 修复打磨`

这说明 Stage34-40 并不是从当前 `main` 派生后又合回来的线，而是从 `bf9adc9c` 之后平行推进出来的一条大分支。

提交计数差异：

- `codex/stage34-impl` 相对 `main` 有 244 个独有提交。
- `codex/stage35-impl` 相对 `main` 有 248 个独有提交。
- `codex/stage20-execution` 相对 `main` 有 255 个独有提交。
- `claude/stage40-impl` 相对 `main` 有 257 个独有提交。
- `integration/phase-i-exit` 相对 `main` 有 301 个独有提交。
- `main` 相对这些 stage 分支也有 8 个独有提交。

## 3. 为什么会这样

根因不是某一次代码“丢失”，而是分支治理发生了错位：

1. Stage34-40 在 `codex/stage20-execution`、`claude/stage37-*`、`claude/stage38-impl`、`claude/stage39-impl`、`claude/stage40-impl`、`integration/phase-i-exit` 这条线持续推进。
2. `main` 后来进入的是 `origin/main` / PR #73 的线，即 `9011f356 Merge pull request #73 from BRSAMAyu:本地全量收尾`。
3. `origin/main` 并没有包含 Stage34-40 那条完整历史。
4. 后续又有人/agent 在 `main` 上直接做了审计恢复和若干修复提交，让 `main` 比 `origin/main` 多 7 个本地提交。
5. 于是当前形成了三层状态：
   - 远端 `origin/main`：旧主线。
   - 本地 `main`：旧主线 + 7 个本地修复/审计恢复。
   - Stage40 / integration：真正包含 Stage34-40 成果的大分支。

所以“之前推进到 Stage34 都正常”的感觉是对的：Stage34 以后在 stage/integration 线上是连续的；混乱发生在“是否把这条线合回 main”的阶段。

## 4. 当前 main 里有什么

`main` 当前比 `origin/main` 超前 7 个提交：

- `b44431d1 fix(security+perf): context_manager session fix, auth Celery migration, plans N+1 batch`
- `b31f036d docs: restore audit reports and session tracker from integration branch`
- `1c40f757 docs: update LOOP_SESSION_TRACKER with Session 9 (Chris S9) results`
- `ffbbceb3 fix(perf+cache): chat.py dead N+1 removal, profile_event_consumer cache fix`
- `c66e57c3 docs: update LOOP_SESSION_TRACKER with Session 10 (Chris S10) results`
- `e2c84585 fix(security): add missing logger import in blacklist_token`
- `3397c2ef fix(security): add TrustedProxies config + restore audit docs (#51 P1-1)`

这些提交有价值，但它们不是 Stage40 合并。

它们主要做了：

- 恢复部分审计报告和 session tracker。
- 恢复/重建严格复核总方案。
- 修了一些从审计中抽出的安全/性能问题。
- 补了 `TrustedProxies` 等安全配置。

## 5. Stage40 线里有什么

`claude/stage40-impl` 顶点是：

- `9df6934f [Stage40] Kill Switch 三态化 + Core/Phase headers + Phase I Exit Gate 交付`

Stage40 关键内容包括：

- `backend/app/core/kill_switch.py`
- `backend/app/services/aurora_stage40_calendar_kill_switch_service.py`
- `backend/tests/unit/test_kill_switch_core.py`
- `backend/tests/unit/test_stage40_calendar_kill_switch.py`
- `scripts/stage40/drill_all.sh`
- `scripts/stage40/drill_calendar.sh`
- `scripts/stage40/run_kill_switch_drills.py`
- `scripts/stage40/run_sgw_dogfood.py`
- `artifacts/stage40/kill_switch_drill_audit.jsonl`
- `artifacts/stage40/sgw/dogfood_summary.json`
- `docs/product/SPARKLE_AURORA_STAGE40_HANDOFF_2026-04-22.md`
- `docs/product/SPARKLE_AURORA_PHASE_I_EXIT_GATE_2026-04-22.md`
- `docs/product/SPARKLE_AURORA_PHASE_II_RL_OPTIMIZATION_KICKOFF_2026-04-22.md`
- 大量 Stage18-39 的前置服务、迁移、guard scripts、Aurora/SGW/规则检查体系。

`main..claude/stage40-impl` 的文件差异非常大：

- 约 4274 个文件发生变化。
- 约 539857 行新增。
- 约 202137 行删除。

`main..integration/phase-i-exit` 的差异也非常大：

- 约 4321 个文件发生变化。
- 约 549261 行新增。
- 约 194707 行删除。

这些数字说明不能把 Stage40 当成一个“小补丁”直接 cherry-pick 到 main；必须做正式集成。

## 6. 审查文档现在是什么状态

当前能打开的关键审查文档：

- `docs/audit/DEEP_AUDIT_SUMMARY.md`
- `docs/audit/AUDIT_RESTORE_MANIFEST_2026-04-23.md`
- `docs/audit/STRICT_REVALIDATED_GLOBAL_REPAIR_PLAN_2026-04-24_rounds_1_107.md`
- `docs/audit/STRICT_REVALIDATED_GLOBAL_REPAIR_PLAN_RECONSTRUCTED_FROM_CONTEXT_2026-04-24_rounds_1_107.md`

当前事实：

- Git 可恢复的原始审查归档主要到 `Round 64`。
- `65-107` 原始审查报告没有在当前 Git、stash、reflog、dangling object 或 worktree 中找到。
- 我已经基于上下文重建了 `1-107` 的有效成果文档，但它不是原始 107 轮报告全集。

刚刚做的审查恢复不算白做，因为：

- 审查恢复文件已经出现在当前 `main` 的提交历史里。
- 重建版总方案已经能打开，并且保留了 `65-107` 的上下文复核成果。
- 它能作为后续验收基线。

但它不能解决 Stage40 没进 main 的问题。

## 7. 当前未提交/未跟踪内容

当前 `git status -sb` 显示：

- `main...origin/main [ahead 7]`
- 未跟踪：`.claude/`
- 未跟踪：`.codex-backups/`
- 未跟踪：`2026-04-23-221746-this-session-is-being-continued-from-a-previous-c.txt`

含义：

- 当前 `main` 本地已有 7 个提交尚未推到 `origin/main`。
- `.claude/` 和 `.codex-backups/` 是本地运行/恢复痕迹，不应直接无脑提交。
- session 文本文件也应先确认用途，通常不应进入主仓库。

## 8. 是否白做了

不白做。

已经做过的工作分三类：

### A. Stage34-40 代码成果

没有丢，在分支里：

- `codex/stage34-impl`
- `codex/stage35-impl`
- `codex/stage20-execution`
- `claude/stage40-impl`
- `integration/phase-i-exit`

但没有完整进入 `main`。

### B. 审查和修复成果

部分已经进入本地 `main`：

- 审计恢复
- session tracker 更新
- TrustedProxies
- logger import
- 部分安全/性能修复

这些当前在 `main` 的 7 个本地提交里。

### C. 107 轮审查原始报告

原始报告没有完整找回。

但我已经重建了有效成果：

- `STRICT_REVALIDATED_GLOBAL_REPAIR_PLAN_RECONSTRUCTED_FROM_CONTEXT_2026-04-24_rounds_1_107.md`

这份应当作为临时验收基线，而不是原始报告归档。

## 9. 风险判断

当前最大的风险不是代码本身，而是基线混乱：

- 如果继续在当前 `main` 上开发，会绕过 Stage34-40 的大量成果。
- 如果直接把 `integration/phase-i-exit` 硬合进 `main`，会遇到巨大 diff、生成文件、运行产物、`.sgw_state`、`.local_runtime`、tmp 截图、可能还有 vendor/cache 类文件污染。
- 如果只 cherry-pick Stage40 单提交，会缺少 Stage34-39 前置依赖，风险很高。
- 如果把当前 `main` 的 7 个提交丢掉，又会丢掉刚修复的审计恢复和安全修复。

所以必须先建立一个新的集成基线，而不是继续在混乱状态下修问题。

## 10. 推荐恢复路线

### 第一阶段：冻结当前状态

1. 不要再直接往 `main` 上继续堆业务改动。
2. 给当前 `main` 打保护分支，例如 `backup/main-audit-recovery-2026-04-23`。
3. 给 `integration/phase-i-exit` 打保护分支，例如 `backup/phase-i-exit-stage40-2026-04-23`。
4. 不提交 `.claude/`、`.codex-backups/`、session txt。

### 第二阶段：建立新的集成分支

建议新建：

- `codex/recover-stage40-into-main`

推荐基底：

- 如果目标是保留 Stage40 成果：从 `integration/phase-i-exit` 开新分支，再把当前 `main` 的 7 个提交逐个 cherry-pick / 手工移植进去。
- 不建议从当前 `main` 直接 merge `integration/phase-i-exit`，因为 diff 太大且污染文件多。

原因：

- `integration/phase-i-exit` 已经包含 Stage34-40 的连续历史。
- 当前 `main` 的 7 个提交相对少，更适合作为补丁移植。
- 这样可以避免把 Stage40 拆碎。

### 第三阶段：清理集成分支

必须重点清理：

- `.sgw_state/`
- `.local_runtime/`
- `.claude/worktrees`
- tmp 截图和运行产物
- 生成文件重复/过时目录
- 不该进入仓库的缓存、debug JSON、临时输出

### 第四阶段：验证

最少验证：

- `cd backend && pytest` 或选定核心 unit tests
- `cd backend/gateway && go test ./...`
- 关键 guard scripts：`scripts/run_all_rule_guards.sh`
- Stage40 drill：`scripts/stage40/drill_all.sh`
- 审计文档链接检查

### 第五阶段：再决定 main

验证通过后，再把新的集成分支作为真正 main 候选。

不要直接把当前 `main` 视为项目最新事实。

## 11. 建议下一步

我建议下一步做一个“只读集成预案”，不立刻合并：

1. 生成 `integration/phase-i-exit` 与当前 `main` 的文件分类 diff。
2. 标出必须保留、必须丢弃、需要人工决策的文件组。
3. 列出当前 `main` 7 个提交如何移植到 Stage40 基线。
4. 输出一份 `STAGE40_MAIN_INTEGRATION_PLAN_2026-04-23.md`。

等这个预案确认后，再让执行型 Codex 开始真正集成。

## 12. 一句话判断

项目没有白做，但 `main` 不是最新主事实。真正的 Stage40 成果在 `integration/phase-i-exit` / `claude/stage40-impl` 线上；当前 `main` 只是旧主线加 7 个本地修复。现在应该暂停直接在 `main` 上推进，先做 Stage40 回主干的正式集成。
