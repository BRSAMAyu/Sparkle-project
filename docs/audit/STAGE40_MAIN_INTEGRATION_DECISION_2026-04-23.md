# Stage40 与 main 集成决策说明

生成时间：2026-04-23 22:45 Asia/Shanghai  
目的：在 `main` 与 Stage34-40 / `integration/phase-i-exit` 分叉后，确定工程真相源、文档真相源、修复继承策略和后续集成路线。

## 1. 直接结论

不能简单说“以 main 为准”，也不能无脑说“以 integration/phase-i-exit 全量覆盖 main”。

正确判定是：

- **产品愿景、阶段规划、handoff、Aurora/SGW 多阶段教学链路：以 `integration/phase-i-exit` / Stage40 线为准。**
- **当前 main 上后补的安全/性能修复和审计恢复：作为必须移植的 patch queue。**
- **最终目标：建立一个新的、干净的集成分支，把 Stage40 线作为主体，把 main 的 7 个修复提交选择性移植进去，然后清理运行产物并验证。**

换句话说：

- `integration/phase-i-exit` 是“项目阶段成果和愿景连续性”的主事实源。
- 当前 `main` 是“远端旧主线 + 后补修复”的补丁源。
- 最终应该产出第三个干净分支作为新的主干候选，而不是在两边二选一。

## 2. 为什么不能以当前 main 为准

当前 `main` 不包含 Stage34-40 的连续历史。

证据：

- `main` 与 `codex/stage34-impl` 的共同祖先是 `bf9adc9c 修复打磨`。
- `main` 与 `claude/stage40-impl` 的共同祖先也是 `bf9adc9c 修复打磨`。
- `claude/stage40-impl` 相对 `main` 有 257 个独有提交。
- `integration/phase-i-exit` 相对 `main` 有 301 个独有提交。

当前 `main` 只是在 `origin/main = 9011f356` 后继续补了 7 个提交，包括审计恢复和少量安全/性能修复。

因此，如果以当前 `main` 作为最终基准，会丢失或绕开：

- `docs/product/SPARKLE_VISION_ANCHOR_LIST_2026-04-19.md`
- Stage4-40 的大量 handoff / dispatch / rule definition / closeout 文档
- `docs/aurora/stage*` 系列设计材料
- Aurora 多阶段实现
- SGW / rule guard / stage guard 脚本
- Stage34-40 的迁移、测试、服务、kill switch 和 Phase I exit gate 成果

这会破坏你最初一阶段一阶段推进出来的教学链路和愿景一致性。

## 3. 为什么也不能无脑以 integration/phase-i-exit 覆盖 main

`integration/phase-i-exit` 是正确的主体方向，但它也不是可以直接粗暴覆盖的干净主干。

原因：

- 它相对 `main` 有 4000+ 文件级差异。
- 其中包含 `.sgw_state/`、`.local_runtime/`、tmp 截图、debug JSON、运行输出等明显不应进入最终主干的产物。
- 当前 `main` 的 7 个本地修复提交也有价值，不能丢。
- main 上刚恢复的审计基线和重建版 1-107 审查成果需要保留。

所以 `integration/phase-i-exit` 应作为主体基底，但必须经过清理和补丁移植。

## 4. 权威性分层

### 4.1 产品/愿景权威源

以 Stage40 / integration 线为准。

代表文件：

- `docs/product/SPARKLE_VISION_ANCHOR_LIST_2026-04-19.md`
- `docs/product/SPARKLE_AURORA_STAGE*_HANDOFF_*.md`
- `docs/product/SPARKLE_AURORA_STAGE*_DISPATCH_PLAN_*.md`
- `docs/product/SPARKLE_AURORA_PHASE_I_EXIT_GATE_2026-04-22.md`
- `docs/product/SPARKLE_AURORA_PHASE_II_RL_OPTIMIZATION_KICKOFF_2026-04-22.md`
- `docs/product/SPARKLE_AURORA_ROADMAP_v2_1_*.md`
- `docs/aurora/*`
- `docs/verification/*`

这些文档代表项目“为什么这样做、每个阶段在解决什么、每个阶段的验收和教学意图”。它们必须保留为工程治理的一等公民。

### 4.2 工程实现主体源

以 `integration/phase-i-exit` 为准。

原因：

- 它包含 Stage34-40 的连续合并路径。
- 它包含 Stage37-40 的安全、事件、LLM 安全层、idempotency/OCC、kill switch、Phase I exit 等核心工程成果。
- 它包含多个 stage guard 和 drill 机制。

### 4.3 修复补丁源

当前 `main` 的 7 个本地提交作为 patch queue。

包括：

- `b44431d1 fix(security+perf): context_manager session fix, auth Celery migration, plans N+1 batch`
- `b31f036d docs: restore audit reports and session tracker from integration branch`
- `1c40f757 docs: update LOOP_SESSION_TRACKER with Session 9 (Chris S9) results`
- `ffbbceb3 fix(perf+cache): chat.py dead N+1 removal, profile_event_consumer cache fix`
- `c66e57c3 docs: update LOOP_SESSION_TRACKER with Session 10 (Chris S10) results`
- `e2c84585 fix(security): add missing logger import in blacklist_token`
- `3397c2ef fix(security): add TrustedProxies config + restore audit docs (#51 P1-1)`

这些不能丢，但也不应反过来把当前 `main` 定义为最终基线。

### 4.4 审查/验收源

当前可用的审查源分两类：

- 原始可追溯源：`docs/audit/DEEP_AUDIT_SUMMARY.md` 及已恢复的 `deep_audit_*.md`。
- 上下文重建源：`docs/audit/STRICT_REVALIDATED_GLOBAL_REPAIR_PLAN_RECONSTRUCTED_FROM_CONTEXT_2026-04-24_rounds_1_107.md`。

后者不是原始 107 轮报告全集，但应保留为恢复后的验收基线。

## 5. 集成路线

### Step 1：冻结两边

建议创建保护分支：

- `backup/main-before-stage40-recovery-2026-04-23`
- `backup/integration-phase-i-exit-2026-04-23`

目的：

- 防止继续在当前 `main` 上叠加新业务改动。
- 防止 Stage40 线被误删或覆盖。

### Step 2：建立新集成分支

建议新建：

- `codex/recover-stage40-mainline`

基底选择：

- 从 `integration/phase-i-exit` 开始，而不是从当前 `main` 开始。

理由：

- Stage40 线是阶段成果和愿景连续性的主体。
- 当前 main 的 7 个修复提交数量少，适合移植。
- 反过来把 Stage40 merge 到 main 会处理巨大差异和大量污染文件，风险更高。

### Step 3：清理污染文件

必须从新集成分支中清理或加入 ignore：

- `.sgw_state/`
- `.local_runtime/`
- `.claude/worktrees`
- 临时 debug JSON
- tmp/acceptance 截图
- 运行输出文件
- 误提交的本地环境产物

这些不是产品成果，也不是教学/规划文档。

### Step 4：移植 main 的修复提交

把当前 `main` 的 7 个本地提交逐个 cherry-pick 或手工移植。

移植原则：

- 安全修复优先。
- 审计文档恢复保留。
- 与 Stage40 已修复内容冲突时，以 Stage40 代码为主体，保留 main 修复的意图。
- 文档重复时，不删除 Stage handoff，只补充恢复/审查说明。

### Step 5：恢复文档体系

必须保留：

- 愿景锚定清单
- Stage handoff
- Stage dispatch plan
- Rule definition
- Gate / drill / closeout
- Verification / audit

文档不是杂物。它们是这个项目多阶段工程推进的教学轨迹和治理证据。

建议建立一个索引：

- `docs/product/SPARKLE_AURORA_STAGE_INDEX.md`

索引内容：

- Stage 4-40 每阶段的 handoff、dispatch、rule、gate、主要代码入口、测试入口。
- 当前阶段状态：`merged / needs-verification / superseded / archived`。

### Step 6：验证新主干候选

最少验证：

- `cd backend && pytest`
- `cd backend/gateway && go test ./...`
- `scripts/run_all_rule_guards.sh`
- `scripts/stage40/drill_all.sh`
- 审计文档链接检查

若完整测试太重，至少先跑：

- Stage40 kill switch unit tests
- EventBus / LLM safety / idempotency 相关 guard
- main 7 个修复对应的回归测试

## 6. 不应做的事情

不要：

- 直接把当前 `main` 当最新事实继续推进。
- 直接 reset main 到 Stage40。
- 直接把 `integration/phase-i-exit` 整体 merge 到 main 然后手动祈祷。
- 删除愿景锚定清单、handoff、dispatch、rule、gate 文档。
- 把运行产物和 debug 数据当成 Stage 成果提交。
- 只 cherry-pick `9df6934f Stage40` 单个提交，因为它依赖 Stage34-39 的前置系统。

## 7. 最终准则

以“愿景连续性 + 工程可验证性”为准，而不是以某个分支名为准。

实践上：

- 以 `integration/phase-i-exit` 作为阶段成果主体。
- 以当前 `main` 的 7 个提交作为修复补丁源。
- 以审查重建文档作为临时验收基线。
- 以测试/guard/drill 结果决定是否成为新 main。

## 8. 一句话决策

当前应该把 `integration/phase-i-exit` 视为真正的 Stage40 项目主体，把当前 `main` 视为后补修复补丁源；新建干净集成分支完成清理、补丁移植和验证后，再把它作为新的 main 候选。
