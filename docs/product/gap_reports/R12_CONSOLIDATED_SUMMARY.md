# R12 — Sparkle (星火) 二次深度审查整合报告

**Date**: 2026-05-07
**Audit Round**: Round 12 (Independent Secondary Deep Audit)
**Reviewer**: Sparkle Chief Reviewer (Manual + Multi-Agent)
**Reference Baseline**: [R11 Reports](docs/product/gap_reports/R11_*.md), [Full Vision Audit](docs/product/SPARKLE_FULL_VISION_FINAL_AUDIT_2026-05-02.md)

---

## 1. 总体概览 (Executive Summary)

本次 R12 审计对 Sparkle 项目的 11 条关键用户旅程进行了全链路（Flutter → Go → Python → DB）的独立穿透审查。审计结果表明，尽管 R11 发现的许多 P0 级 UI 阻塞和路由问题已得到修复，但系统在**跨层协议一致性**、**核心引擎与业务逻辑对齐**以及**高级特性（如无障碍、推送、质量加权）**方面仍存在显著差距。

### 核心发现统计
| 优先级 | 数量 | 状态 | 关键区域 |
|--------|------|------|----------|
| **P0 (Launch Blockers)** | 12 | 必须修复 | gRPC 实现缺失, 消息协议不匹配, 推送丢失, 核心逻辑断裂 |
| **P1 (Important Gaps)** | 33 | 建议发布前修复 | 缓存策略, 无障碍支持, 批量操作, i18n 硬编码 |
| **P2 (Polish/Enhance)** | 28 | 发布后优化 | 性能监控, 复杂冲突解决 UI, 细节动画 |
| **Verified Working** | 45+ | 优势资产 | 认证链路, EventBus, 离线同步引擎, 3D 渲染性能 |

---

## 2. 关键 P0 问题汇总 (Top P0 Findings)

### A. 协议与跨层集成 (Cross-Layer Integration)
1. **[R3A9-P0-1] 80% 的 GalaxyService gRPC 方法是"幽灵方法"**：Proto 定义了 9 个 RPC，但 Python gRPC 仅实现 2 个，Go 仅调用 1 个。导致前端在扩展 3D 星图功能时面临"有接口无实现"的断路。
2. **[R3A9-P0-2] 成就解锁推送协议不匹配**：Python `NotificationService` 发出的成就推送类型为 `notification`（嵌套数据），但 Flutter `MainNavigationShell` 强制匹配顶层类型 `achievement_unlock`。导致**所有通过 WebSocket 的实时成就弹窗全部失效**。

### B. 核心业务逻辑断裂 (Core Logic Breaches)
3. **[R1A3-P0-1/2] 考点冲刺与计划阶段 API 在 Gateway 侧缺失**：Python 后端新增的考点冲刺和计划生成子路径未在 Go `proxy_routes.go` 中注册，导致相关功能点击即 404。
4. **[R2A7-P0-1] 成就引擎仍使用二进制连续天数**：尽管 `StreakQualityService` 已上线，但成就引擎仍根据简单的打卡事件计数，**无法区分高质量学习和低质量刷量**，违背了"质量加权成长"的愿景。
5. **[R2A7-P0-2] 每日反思功能完全缺失**：愿景中的核心反馈闭环"每日反思"在前后端均无实际代码实现。

### C. 基础架构与辅助功能 (Infrastructure & Accessibility)
6. **[R2A8-P0-1] 无障碍设置与渲染管线断连**：Settings UI 中的 9 个无障碍开关仅改变了本地状态，未注入到 Theme 或 Widget 渲染逻辑中。
7. **[R2A6-P0-1] 社区事件推送完全失效**：社区互动（点赞/评论/好友请求）未接入推送系统，用户无法感知他人的社交信号。

---

## 3. R11 P0 验证结果 (R11 Verification)

| R11 ID | 描述 | R12 验证结果 | 结论 |
|--------|------|--------------|------|
| COM-P0-01 | 无社区路由 | **FIXED** | 路由已在 GoRouter 注册 |
| CHAT-P0-01 | 快速消息流失 | **PERSISTS (P1)** | 竞态条件依然存在 |
| SEC-P0-01 | SQL 注入风险 | **FIXED** | 已转向 sqlc/SQLAlchemy 参数化查询 |
| UI-P0-01 | 默认红色错误页 | **FIXED** | `main.dart` 已覆盖 `ErrorWidget.builder` |

---

## 4. 优势资产 (Strengths & Verified Working)

- **高性能离线同步 (R3A11-V-2)**：基于 Isar 的 `SyncEngine` 实现了专业级的 Outbox 模式和自动重试，稳定性极高。
- **严密的认证体系 (R3A10-V-1)**：Go Gateway 的 JWT 校验链路完整支持了 JTI 黑名单、用户撤销和 Fail-Closed 策略，安全性达标。
- **可观测性基础 (R3A9-V-1)**：Python 侧的 `EventBus` 具备完善的 DLQ (死信队列) 和监控指标，支撑了分布式事务的可靠性。

---

## 5. 修复建议路径 (Strategic Recommendation)

1. **Phase 1 (Blocker Removal)**：
   - 统一成就推送协议，确保实时反馈可见。
   - 补全 Go Gateway 的缺失代理路由（Goals/Plans）。
   - 将 `StreakQuality` 正式接入成就判定逻辑。
2. **Phase 2 (Infrastructure Fix)**：
   - 彻底同步 GalaxyService 的 gRPC 合约与实现。
   - 注入无障碍设置到全局 Theme 渲染管线。
3. **Phase 3 (Feature Completeness)**：
   - 实现每日反思屏幕。
   - 补齐社区功能的批量操作与图片上传细节。

---
**Status**: Independent Audit Completed.
**Next Step**: Prioritize P0 fixes into the next engineering sprint.
