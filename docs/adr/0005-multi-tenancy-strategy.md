# ADR-004: 多租户隔离路线选择 (Phase 4)

| 属性 | 内容 |
| :--- | :--- |
| **状态** | Accepted (已决策) |
| **日期** | 2026-01-04 |
| **范围** | Backend (Go Gateway + DB Access Layer), 所有含业务数据的表 |
| **驱动目标** | Phase 4 (Month 25-36) 实现单区域多可用区高可用与可控运维复杂度 |
| **Owner** | Backend Lead |
| **Reviewers** | Arch Committe |
| **Next Review** | Month 24 (Phase 4 Start) |

## 背景

Sparkle Phase 4 需要支持多租户（学校/组织/团队），目标是隔离数据、降低单租户故障影响，并为未来多区域演进铺路。
PostgreSQL 可选方案包括：
1.  **应用层逻辑隔离**：所有查询显式加入 `tenant_id` 过滤（Repository Pattern / sqlc / ORM）。
2.  **数据库层 RLS**：启用 Row-Level Security，通过 session 变量/角色策略实现隔离。

## 决策

Phase 4 **采用应用层逻辑隔离为主 (Primary)**：

1.  **Schema 规范**：所有业务表必须包含 `tenant_id` (UUID, NOT NULL)，并建立组合索引策略（如 `tenant_id + 业务主键/查询字段`）。
2.  **代码规范**：所有 Repository/Query 必须显式携带 `tenant_id` 参数并在 WHERE 中过滤。
3.  **RLS 定位**：RLS **不作为** Phase 4 必选项，仅作为 Phase 5+ 的可选加固 (Defense in Depth) 或少数高合规客户的专用部署策略。

## 决策理由

1.  **连接池兼容性**：Go `sql.DB` 连接池复用导致 RLS 依赖 session 变量的方案更易产生“上下文污染/复用错误”的风险，且需要额外的连接池策略约束。
2.  **性能与可控性**：应用层过滤可直接命中索引，query plan 更可预测；RLS 可能带来额外 CPU 与不可控的性能回退。
3.  **工程落地成本**：Phase 4 目标是“务实交付 99.9%”，应用层隔离更易用静态检查/代码审计保证覆盖面。

## 影响与约束

*   **Schema 约束**：新增表必须有 `tenant_id` 且 `NOT NULL`；历史表迁移需补齐默认租户。
*   **索引约束**：所有高频查询必须包含 `tenant_id` 前缀索引。
*   **代码审计约束**：任何跨租户访问（例如管理员工具）必须显式声明，默认禁止。

## Non-goals (非目标)

*   本阶段 **不引入**：跨租户的数据共享机制（Data Sharing）。
*   本 ADR **不覆盖**：多区域（Multi-Region）的数据同步策略。
*   本阶段 **不承诺**：数据库层面的物理隔离（如分库分表）。

## Rollout (渐进上线策略)

1.  **Schema Update**: 全量表添加 `tenant_id` 列，允许 NULL (Month 25)。
2.  **Backfill**: 历史数据回填默认租户 ID，并将列设为 NOT NULL (Month 25)。
3.  **Dual Write/Read**: 更新代码层，所有写入带上 ID；读取时暂不强制过滤 (Month 26)。
4.  **Enforce**: 开启强制过滤，任何遗漏 `tenant_id` 的查询将在测试环境报错 (Month 26)。
5.  **Audit**: 上线静态代码扫描规则，阻断无 Tenant 上下文的 PR (Month 27)。

## Verification (验收与证据)

*   **必须产出证据**: 包含 `WHERE tenant_id = ?` 的 SQL 执行计划 (EXPLAIN ANALYZE) 截图。
*   **必须通过检查**: 自动化测试套件 (Test Suite) 中包含“租户 A 尝试读取租户 B 数据并返回空/错误”的用例。
*   **必须具备回滚**: 提供关闭强制过滤的 Feature Flag，以便在紧急情况下退回无隔离模式。