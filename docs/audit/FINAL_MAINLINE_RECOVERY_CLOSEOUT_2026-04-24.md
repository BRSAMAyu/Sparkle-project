# Sparkle 主干收束最终收尾说明

生成时间：2026-04-24 Asia/Shanghai

## 1. 最终判定

本次收束以 `integration/phase-i-exit` / Stage40 线为工程主体，以旧 `main` 上 7 个审计、安全、性能修复提交为 patch queue。最终候选主干为：

- 分支：`claude/recover-stage40-into-main`
- 基底：`integration/phase-i-exit` @ `2858f7fd`
- 原候选 tag：`candidate/stage40-main-recovered-2026-04-23`
- 安全备份：`backup/main-audit-recovery-2026-04-23`、`backup/phase-i-exit-stage40-2026-04-23`

这个判定解决的是“以哪条线为准”的问题：Stage40 线保留多阶段愿景、handoff、Aurora/SGW、guard、drill 与 Phase I Exit 成果；旧 `main` 的本地修复全部被逐项移植或确认为冗余。

## 2. 已纳入的关键报告

以下文档共同构成后续验收和追溯入口：

- `docs/audit/PROJECT_STATE_RECOVERY_REPORT_2026-04-23.md`
- `docs/audit/STAGE40_MAIN_INTEGRATION_DECISION_2026-04-23.md`
- `docs/audit/STAGE40_MAIN_INTEGRATION_REPORT_2026-04-23.md`
- `docs/audit/STRICT_REVALIDATED_GLOBAL_REPAIR_PLAN_RECONSTRUCTED_FROM_CONTEXT_2026-04-24_rounds_1_107.md`
- `docs/audit/DEEP_AUDIT_SUMMARY.md`
- `docs/audit/LOOP_SESSION_TRACKER.md`

其中 `PROJECT_STATE_RECOVERY_REPORT` 解释分叉原因，`STAGE40_MAIN_INTEGRATION_DECISION` 固定权威源分层，`STAGE40_MAIN_INTEGRATION_REPORT` 记录实际集成、污染清理、cherry-pick 与验证结果。

## 3. 已完成的工程动作

- 从 Stage40 / `integration/phase-i-exit` 建立干净候选线。
- 清理 `.sgw_state/`、`.local_runtime/`、`.claude/worktrees/*`、本地调度状态等误入仓的运行产物。
- 扩展 `.gitignore`，防止同类运行产物重新进入版本库。
- 按时间序处理旧 `main` 的 7 个本地提交：6 个成功移植，1 个确认为 Stage40 线已包含的冗余修复。
- 修复集成基线遗留的 Go gateway build error：`NewSTTHandler` 调用签名不匹配。
- 修复 Rule AX 对 data consistency routes 的 route-tier 注释要求。
- 恢复并纳入此前散落在旧 `main` 工作区的项目状态复盘与集成决策文档。

## 4. 验证状态

`STAGE40_MAIN_INTEGRATION_REPORT_2026-04-23.md` 记录的验证矩阵已经闭合：

- Python AST 检查：8/8 通过。
- Go gateway：`go build ./...` 通过。
- Go gateway：`go vet ./...` 通过。
- Go gateway handler/config 测试通过。
- Rule guards：59/59 通过。
- Stage40 kill switch drill 通过。
- 关键 Python pytest 样本 12/12 通过。

本收尾提交只新增审计/决策文档，不改变运行时代码；因此代码验证结论继承上述报告。

## 5. 剩余治理原则

- 不再以旧 `main` 作为产品和工程主体事实源。
- 不再把 `.claude/worktrees/`、`.sgw_state/`、`.local_runtime/` 之类本地运行状态视为项目成果。
- 后续任何新审查问题应先落到 `docs/audit/DEEP_AUDIT_SUMMARY.md` 或严格复核总方案，再由独立实现分支修复。
- 后续验收以本候选主干为起点，重点复跑 rule guards、Stage40 drill、gateway build/test 与对应审查问题回归测试。

## 6. 一句话结论

Stage34-40 的工程成果、愿景文档、审查恢复和旧 `main` 的有效修复已经被收束到同一条候选主干；接下来应把这条候选线作为新的本地主干基准继续推进。
