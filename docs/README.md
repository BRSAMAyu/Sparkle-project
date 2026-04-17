# Sparkle 开发文档

本页面向当前开发者，不承担项目宣传、比赛展示或历史存档功能。

## 快速导航

| 目的 | 去哪 |
|------|------|
| **第一次进入仓库** | [00_项目概览](./00_项目概览/) |
| **理解模块边界** | [01_核心模块文档](./01_核心模块文档/) |
| **改接口/协议/数据模型** | [02_技术设计文档](./02_技术设计文档/) |
| **实现特定功能或联调** | [03_功能实现指南](./03_功能实现指南/) |
| **启动环境与部署** | [05_部署与运维](./05_部署与运维/) |
| **产品方向与路线图** | [product](./product/) |
| **工程规范与质量门禁** | [engineering](./engineering/) |
| **验收基线与发布检查** | [verification](./verification/) |
| **架构决策记录** | [adr](./adr/) |

## 专题目录

| 目录 | 内容 |
|------|------|
| [state](./state/) | 状态协议、合并规则、事件协议 |
| [data](./data/) | 数据追踪规范、离线评估协议 |
| [contracts](./contracts/) | API/Proto 快照与冻结契约 |
| [openclaw](./openclaw/) | OpenClaw 集成：实施计划、连接指南、商业方案 |

## 核心产品文档（推荐阅读顺序）

1. [产品共识与6断点](./product/SPARKLE_PRODUCT_CONSENSUS_2026-04-02.md)
2. [产品论点与聚焦路线图](./product/SPARKLE_PRODUCT_THESIS_AND_REFOCUSED_ROADMAP_2026-04-05.md)
3. [增长系统路线图](./product/SPARKLE_GROWTH_SYSTEM_ROADMAP_2026-04-03.md)
4. [数据利用率分析](./product/SPARKLE_DATA_UTILIZATION_ANALYSIS_2026-04-06.md)
5. [Stage 2 产品连贯性计划](./product/SPARKLE_STAGE2_PRODUCT_COHERENCE_AND_LIVE_ALPHA_PLAN_2026-04-06.md)
6. [Codex 对齐与交接](./product/SPARKLE_CODEX_ALIGNMENT_AND_HANDOFF_2026-04-07.md)

## 使用原则

- 文档是否保留，以"今天的开发者是否需要它"为准
- 过程稿、阶段稿、对齐稿默认进入 `_归档/`，不再占用主文档区
- 需要长期保留的文档，应优先写成"当前状态 + 关键路径 + 已知边界"的工作文档
- 若某文档与代码现状冲突，以代码与当前协议定义为准
