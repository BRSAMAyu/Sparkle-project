# ADR-0008: Full Vision Completion — 25 FV 卡片架构决策记录

**Status**: Accepted
**Date**: 2026-05-02
**Context**: FV-01 至 FV-25 完全体冲刺完成 (Sparkle Full Vision Dispatch)

## Context

Sparkle 完全体最终冲刺通过 25 张 FV (Full Vision) 卡片将系统从核心主链 4.0-4.3/5 推到完全体状态。所有卡片基于 `SPARKLE_FULL_VISION_FINAL_DISPATCH_2026-05-02.md` 派遣。本 ADR 记录架构层面的关键决策。

## Decision

### 1. P4 Research-Grade Layer Productionization (FV-01–05)

**决策**: 将 5 个之前 SHADOW_ONLY 的 P4 研究模块接入生产管道，每个模块获得独立的 DB 表、Celery 调度、API endpoints 和 Prometheus/Grafana 监控。

- FV-01 CounterfactualEvaluation: persistent reports + promote workflow
- FV-02 SafeExperimentPlatform: lifecycle state machine + guardrail monitoring
- FV-03 SimulationLab: CI gate integration + weekly benchmark
- FV-04 Marketplace: user opt-in adoption only + PII pre-scan
- FV-05 PrivacyCommunityIntelligence: k=5 anonymity + DP + budget ledger

**架构含义**: Pipeline 从 Shadow → Live 的灰度模式已验证可行。每个模块的 kill switch 独立控制。

### 2. Infrastructure Security Hardening (FV-06–10)

**决策**: 分层安全加固，通过环境变量 `SPARKLE_RBAC_ENABLED` 控制生产/开发差异。

- FV-06: PostgreSQL 4-role RBAC + Redis ACL + MinIO bucket IAM
- FV-07: ConsentTracker DB 持久化 (source-of-truth 在 DB, cache 为优化层)
- FV-08: 管理操作审计日志 (middleware 自动捕获 + @audit_admin_action 装饰器)
- FV-09: 发布审批工作流 (双人审批强制 + 状态机)
- FV-10: DataMinimizationAuditor fail-closed + 15 模型覆盖

**架构含义**: 安全从 dev-friendly → prod-hardened 的渐进路径已建立。RBAC 灰度通过单一开关控制。

### 3. Mobile-First UX Improvements (FV-11–15)

**决策**: 移动端保留离线优先 (CRDT) + 自适应 UX 双轨策略。

- FV-11: CRDT 从 last-write-wins 升级为真 CRDT 合并 (Yjs 兼容)
- FV-12: 情绪自适应 UI (字体/动画/色温/层级响应疲劳/压力信号)
- FV-13: 召回通知价值显式化 (value_reason + "为什么提醒你" 展开)
- FV-14: 集中式无障碍面板 (WCAG AA + 9 项设置)
- FV-15: 多目标仪表盘 + GoalSwitcher

**架构含义**: Mobile 架构从 "functionally complete" 进化到 "UX polished"。离线/在线同步有了真正的 CRDT 保障。

### 4. Execution & Learning Loop Completion (FV-16–22)

**决策**: 任务生命周期 + 学习闭环 + 社群质量三项补完。

- FV-16: PAUSED task status + 自动 PAUSED 检测 (离开 >50% 预期时长)
- FV-17: SourceAsset 生命周期 (active/archived/revoked/orphaned + GDPR 擦除)
- FV-18: StrategyBelief.counter_evidence (反证降权，最多 -0.3)
- FV-19: CrisisMode FSM (normal → warning → crisis → recovery)
- FV-20: Saga/补偿事务 (4 跨服务流程 + 自动补偿)
- FV-21: 召回 ML 触发器 (4→8 触发器 + decision tree ranker)
- FV-22: 社群资源质量评分 + k threshold 3→5

**架构含义**: 成长循环从 "Sense → Execute" 扩展到完整的 "Sense → Clarify → Plan → Execute → Reflect → Reinforce → Adapt"。

### 5. Resilience & Cleanup (FV-24–25)

**决策**: SLO 自动响应 + v1 代码正式弃用。

- FV-24: Alertmanager → webhook → kill switch auto-flip (5 类自动响应) + Go keepalive/retry + Python ClientDisconnectGuard
- FV-25: v1 模块 (CounterfactualEngine, UserSimulator, DomainPack, DomainPackMarketplace) → `_v1` 后缀导出，物理删除计划在下个 sprint

## Consequences

- **Positive**: 25 卡片全绿；0 一票否决触发；完全体验收 22 节抽样达 5/5；CI gates 全部通过
- **Negative/Neutral**: v1 模块仍未物理删除（保留到下个 sprint）；Toxiproxy 集成测未包含；Mobile CRDT 依赖 y_dart 库的长期维护
- **Migration path**: 生产部署通过 `SPARKLE_RBAC_ENABLED` 灰度；每个 FV 模块的 kill switch 独立可控

## FV Completion Matrix

| # | Card | Status | Kill Switch | Tests | Grafana |
|---|------|--------|-------------|-------|---------|
| FV-01 | Counterfactual Evaluation | ✅ | `aurora:stage_counterfactual:production` | ✅ | ✅ |
| FV-02 | SafeExperiment Platform | ✅ | `aurora:stage_safe_exp:production` | ✅ | ✅ |
| FV-03 | SimulationLab CI Gate | ✅ | N/A (CI-only) | ✅ | ✅ |
| FV-04 | Marketplace | ✅ | `aurora:stage_marketplace:production` | ✅ | ✅ |
| FV-05 | PrivacyCommunityIntelligence | ✅ | `aurora:stage_pci:production` | ✅ | ✅ |
| FV-06 | DB/Redis RBAC | ✅ | `SPARKLE_RBAC_ENABLED` | ✅ | N/A |
| FV-07 | ConsentTracker DB | ✅ | N/A (persistence only) | ✅ | N/A |
| FV-08 | Admin Audit Log | ✅ | `TRIGGER` (PG RLS) | ✅ | N/A |
| FV-09 | Release Approval | ✅ | N/A (workflow) | ✅ | N/A |
| FV-10 | DataMinimization fail-closed | ✅ | `SPARKLE_DATA_MINIMIZATION_MODE` | ✅ | N/A |
| FV-11 | Mobile CRDT | ✅ | N/A (mobile) | ✅ | N/A |
| FV-12 | Emotion Adaptive UI | ✅ | N/A (mobile) | ✅ | N/A |
| FV-13 | Recall Notification Value | ✅ | N/A (notification) | ✅ | N/A |
| FV-14 | Accessibility Settings | ✅ | N/A (mobile) | ✅ | N/A |
| FV-15 | Multi-Goal UI | ✅ | N/A (mobile) | ✅ | N/A |
| FV-16 | Task PAUSED Status | ✅ | N/A (task model) | ✅ | N/A |
| FV-17 | Source Lifecycle | ✅ | N/A (source model) | ✅ | N/A |
| FV-18 | Counter Evidence | ✅ | N/A (learning model) | ✅ | N/A |
| FV-19 | Crisis Mode FSM | ✅ | N/A (signals) | ✅ | N/A |
| FV-20 | Saga Compensation | ✅ | N/A (CQRS) | ✅ | N/A |
| FV-21 | Recall ML Trigger | ✅ | N/A (ML) | ✅ | N/A |
| FV-22 | Community Quality | ✅ | N/A (community) | ✅ | N/A |
| FV-23 | i18n Residual Cleanup | ✅ | N/A (i18n) | ✅ | N/A |
| FV-24 | SLO Auto-Response | ✅ | `aurora:slo_auto:*` (5 bindings) | ✅ | ✅ |
| FV-25 | v1/v2 Cleanup + Docs | ✅ | N/A (deprecation) | ✅ | N/A |

## Final Verdict

25/25 cards COMPLETED. 0 veto items triggered. Full vision status: **ACHIEVED**.
