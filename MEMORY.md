# Project Memory

## 2026-09-15 — 新阶段重置（Clean Slate Reset）

项目开启新阶段：仓库已做系统性重置，以单个干净的初始提交重新推送到远端。

- **历史**：旧历史（含全部阶段文档与过程产物）完整备份在仓库外 `~/code/GitHub/Sparkle-archive-20260915/`（`Sparkle-full-history-20260915.bundle` 为全量 git bundle；`docs-archive/` 为删除的文档；`paper-quarantine/` 为贝叶斯小论文相关材料——按负责人要求隔离，不入库）。
- **删除**：docs/_归档、product、audit、audit_reports、ux_audit、sgw、verification、presentations、ai_system_research、review（约 1290 个旧阶段文档）；artifacts 与 .claude 的跟踪内容；插件 fork 的 example 目录（19MB）。
- **保留**：全部代码与测试、工程必要文档（概览/模块/技术设计/实现指南/部署/工程规范/ADR/契约）、docs/competition 参赛材料、CI 守卫引用的 4 个 aurora 例外文件、BGM 音频与应用资产。
- **重写**：AGENTS.md / CLAUDE.md / GEMINI.md / README.md / docs/README.md / 编码代理深度指南，全部为新阶段口径。
- **效果**：协作者拉取从 1.8GB 历史变为当前工作区单提交。
- 已知未完成线头不变：统计模块 mock 数据、排行榜未挂路由、card_protocol 迁移集群（见 docs/engineering/KNOWN_CODE_DEBT_LEDGER.md）。
