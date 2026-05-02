# Sparkle 完全体最终冲刺 · 25-Agent 并行派遣计划

> **版本**: v1.0 final-vision-dispatch | **日期**: 2026-05-02
> **基于**: 现状深度核查（10 agent 审计 + 主干代码实地验证）
> **配套**: `SPARKLE_COMPLETE_VISION_ROADMAP_2026-05-02.md`（差距清单）+ 用户提供的完全体愿景与验收清单
> **范围**: 在 `codex/final-closeout-integration-2026-05-02` 分支已完成 CXP-01..28 + 闭环修复后，剩余的全部完全体差距
> **派遣容量**: 25 个并行 coding agent
> **总指挥**: 用户（派遣）+ Architect（本文档作者，负责最终收尾与冲突仲裁）

---

## 0. 给所有 Agent 的强制阅读清单

每位 agent 在执行任务前 **必须** 完成以下阅读，否则任务无效：

1. **本文档**（`docs/product/SPARKLE_FULL_VISION_FINAL_DISPATCH_2026-05-02.md`）— 找到自己的 FV-XX 卡片
2. **完全体愿景**：用户在 2026-05-02 对话中提供的"Sparkle 完全体最终愿景文档"（22 节，铁律 10 条）
3. **验收清单**：用户在 2026-05-02 对话中提供的"Sparkle 完全体验收清单 v1.0"（22 节，一票否决 10 条）
4. **差距路线图**：`docs/product/SPARKLE_COMPLETE_VISION_ROADMAP_2026-05-02.md`（与本文档配套）
5. **项目 CLAUDE.md**：`/Users/brsama/code/GitHub/Sparkle-project/CLAUDE.md`（架构、命令、护栏）

> ⚠️ **路线图文档有部分失真**：多个被标为"未做"的 P0/P1 项实际已在最近提交完成（spine_durable_snapshots 迁移、L4 reflection 调度、SkillEntry.contraindications、GoalWorldGraph/GrowthChronicle DB 持久化等）。本文档的任务卡是**核查后**的真实剩余差距。

---

## 1. 派遣目标

将 Sparkle 从当前状态（核心主链 4.0-4.3/5、P4 研究层 2.4/5、基础设施安全 3.2/5）推到**完全体**：

- Critical（10 项）：100% 达 5/5
- Core（~100 项）：90%+ 达 4+/5
- Experience（~50 项）：85%+ 达 4+/5
- Research/P4（~75 项）：80%+ 达 3+/5（关键安全项 4+/5）
- Infra/Governance 关键项：100% 达 4+/5
- 一票否决：0/10 触发

---

## 2. 并行执行铁律

每位 agent 必须遵守以下规则，否则其工作将被 architect 在收尾时回滚：

### 2.1 分支与提交
1. 每个 agent 工作在独立分支：`codex/FV-XX-<short-name>`，从 `codex/final-closeout-integration-2026-05-02` 出发
2. 完成后将分支推到远端，**不要**直接合并到 integration 分支（架构师统一收口）
3. 每张卡片只允许提交相关变更；不要跨卡片携带"顺手改的"修改
4. 提交信息格式：`feat(FV-XX): <一句话>` 或 `fix(FV-XX): <一句话>`

### 2.2 文件边界（防冲突）
本文档的"涉及文件/目录"字段对每张卡片是**排他性**的：
- 卡片 A 列出某文件 = 只有 A 可以修改它
- 如发现需要改另一张卡片的文件，**停下来**，在自己的报告中写清楚需求，不要擅自修改
- 共享基础设施文件（如 `__init__.py`、`router.py`、`celery_schedule.py`、`MEMORY.md`）有特殊规则，见各卡片"共享文件协议"

### 2.3 工作产物
每位 agent 必须产出：
1. **代码变更**（具体见各卡片的"5/5 标准"）
2. **测试**：单测 + 集成测 + 必要时 E2E
3. **报告**：`docs/product/parallel_closeout/FV-XX_<short_name>_REPORT_2026-05-02.md`，按统一模板（见 §10）
4. **进度标记**：`.claude/fix-progress/FV-XX.done`（标准格式见 §10）

### 2.4 禁止行为
- 不得修改其他 FV-XX 卡片所属的文件
- 不得修改 `docs/product/SPARKLE_FULL_VISION_FINAL_DISPATCH_2026-05-02.md`（本文档）
- 不得修改 `docs/product/SPARKLE_COMPLETE_VISION_ROADMAP_2026-05-02.md`（差距路线图）
- 不得跳过 hooks（`--no-verify` / `--no-gpg-sign` 禁用）
- 不得引入新的"已实现但未接线"模块——所有新代码必须有生产消费路径
- 不得为了过测试而 mock 关键依赖（FakeRedis 仅限单测；集成测必须用真 Redis）
- 不得为了通过类型检查而广撒 `# type: ignore`

### 2.5 验证标准
- 单测全绿
- `make sync-db` 不报错（如改了 schema）
- `make proto-gen` 不报错（如改了 proto）
- `bash scripts/run_all_rule_guards.sh` 全绿（如触及治理域）
- `cd backend && pytest` 在受影响目录全绿
- 报告中必须粘贴关键命令的实际输出（不允许"通过"两个字了事）

---

## 3. 任务分配总表

| ID    | 名称                                       | 优先级 | 主要文件域                                | 风险 |
|-------|--------------------------------------------|--------|-------------------------------------------|------|
| FV-01 | Counterfactual Evaluation 接入生产管道     | P0     | signals/counterfactual_evaluation.py + 新调度 | 中 |
| FV-02 | SafeExperiment 接入生产管道                | P0     | signals/safe_experiment_platform.py + API | 中 |
| FV-03 | SimulationLab/GoalBench CI 门禁           | P0     | signals/simulation_lab.py + scripts/      | 中 |
| FV-04 | Skill/DomainPack Marketplace 上线         | P0     | signals/marketplace.py + api/v1/marketplace.py | 高 |
| FV-05 | PrivacyCommunityIntelligence 接入         | P0     | signals/privacy_community_intelligence.py | 高 |
| FV-06 | DB/Redis 权限隔离 + RBAC                  | P0     | docker-compose*.yml + alembic migration   | 高 |
| FV-07 | ConsentTracker DB 持久化                  | P0     | signals/research_mode.py + migration      | 低 |
| FV-08 | 管理操作审计日志                           | P0     | api/v1/*_admin.py + middleware            | 中 |
| FV-09 | 发布审批工作流                             | P1     | 新增 release_approval.py + UI             | 中 |
| FV-10 | DataMinimizationAuditor 扩覆盖 + fail-closed | P1   | core/data_minimization.py                 | 低 |
| FV-11 | Mobile CRDT 真实合并 + ACK                 | P1     | mobile/lib/core/offline/                  | 高 |
| FV-12 | 情绪自适应 UI                              | P1     | mobile/lib/core/design/ + features/chat/  | 中 |
| FV-13 | 召回通知价值显式显示                       | P1     | mobile/lib/features/notification_center/  | 低 |
| FV-14 | 集中式无障碍设置面板                       | P1     | mobile/lib/features/settings/             | 低 |
| FV-15 | 多目标 UI（仪表盘 + 切换器）              | P1     | mobile/lib/features/home/ + plan/          | 中 |
| FV-16 | 任务 PAUSED 状态 + 恢复工作流             | P1     | backend/app/services/task_service.py + mobile | 中 |
| FV-17 | 资料生命周期管理                           | P1     | backend/app/services/source_service.py    | 中 |
| FV-18 | StrategyBelief.counter_evidence + 反证降权 | P1     | signals/learning_base.py + types.py       | 低 |
| FV-19 | 危机模式 FSM 化                            | P1     | signals/exam_rescue_detector.py           | 中 |
| FV-20 | Saga/补偿事务 + Outbox 一致性              | P2     | backend/gateway/internal/cqrs/            | 中 |
| FV-21 | 召回 ML 触发器 + value_reason             | P2     | signals/recall_opportunity.py             | 中 |
| FV-22 | 社群资源质量评分 + cohort 阈值上调        | P2     | services/community_service.py             | 低 |
| FV-23 | i18n 残余 459 字符串清零                   | P2     | mobile/lib/features/* (按 P2-4 范围)      | 低 |
| FV-24 | SLO 自动响应 + 服务端弱网                  | P3     | gateway middleware + alertmanager         | 中 |
| FV-25 | v1/v2 旧代码清理 + 文档同步                | P3     | signals/research_grade.py + docs/         | 低 |

**总计 25 张卡片**。可一次性全部派遣（已通过文件域设计避免冲突）。

---

## 4. 详细任务卡片

### FV-01 · Counterfactual Evaluation 接入生产管道

**愿景对应**：验收清单 §14.2（P4-CF-001..008），完全体愿景 §3.9（Outcome & Causal Attribution）

**当前状态**（已核查）：
- `backend/app/signals/counterfactual_evaluation.py`（796 行）质量高，5 个核心类齐全
- 仅在 `spine_orchestrator.py:2957` 被 SHADOW_ONLY 调用，try/except 静默吞错
- 无 DB 持久化、无定时任务、无 API、无指标

**5/5 标准**（agent 必须全部完成）：
1. 新建 `backend/alembic/versions/c13_*_counterfactual_reports.py` 创建表 `counterfactual_evaluation_reports`（字段：id、user_id、context_signature、policy_a、policy_b、estimate、confidence、evidence_grade、generated_at、replaced_by_id 等）
2. 新建 `backend/app/aurora/runtime_v1/models.py` 中追加 SQLAlchemy `CounterfactualReport` 模型（参照 `GoalWorldGraphSnapshot` 的写法）
3. 在 `backend/app/core/celery_tasks.py` 新增 `run_counterfactual_evaluations` 任务，每日扫描合格 InterventionEpisode 群体并生成报告
4. 在 `backend/app/celery_schedule.py` 注册 `run-counterfactual-evaluations-every-day`（86400s）
5. 新建 `backend/app/api/v1/counterfactual.py` 暴露 GET `/api/v1/counterfactual/reports`、GET `/api/v1/counterfactual/reports/{id}`、POST `/api/v1/counterfactual/promote/{report_id}`（仅 admin）
6. 在 `backend/app/api/v1/__init__.py` 或 `router.py` 注册路由
7. 暴露 Prometheus 指标：`sparkle_counterfactual_reports_generated_total`、`sparkle_counterfactual_evidence_grade_histogram`、`sparkle_counterfactual_promotion_pending`（在 `backend/app/core/metrics.py`）
8. 在 `monitoring/prometheus.yml` 加 scrape；在 Grafana JSON dashboard `monitoring/grafana/dashboards/counterfactual.json` 新建仪表盘
9. **撤掉** `spine_orchestrator.py:2957` 的 SHADOW try/except 静默 — 改为正常错误传播 + 指标计数
10. 单测 + 集成测覆盖：调度触发 → 报告写库 → API 返回 → 推广候选生成 → 6 条 CounterfactualIronLaw 强制
11. 旧版 `backend/app/signals/research_grade.py` 中的 `CounterfactualEngine` 标记 `# DEPRECATED: replaced by counterfactual_evaluation.py`，从 `signals/__init__.py` 移除导出

**涉及文件**（排他）：
- `backend/app/signals/counterfactual_evaluation.py`
- `backend/app/aurora/runtime_v1/models.py`（与 FV-07 协调，见共享文件协议）
- `backend/app/core/celery_tasks.py`（与 FV-02/03/05/07 协调）
- `backend/app/celery_schedule.py`（与 FV-02/03/05 协调）
- `backend/app/api/v1/counterfactual.py`（新建）
- `backend/alembic/versions/c13_*_counterfactual_reports.py`（新建）
- `monitoring/grafana/dashboards/counterfactual.json`（新建）

**共享文件协议**：
- `models.py` / `celery_tasks.py` / `celery_schedule.py` / `prometheus.yml`：每个 FV-0X 只追加自己的内容，不删改他人。Architect 收尾时合并冲突
- `signals/__init__.py` 导出表：仅追加新导出，不修改现有

**禁止**：不得修改 `spine_orchestrator.py` 除指定那一段以外的代码。

---

### FV-02 · SafeExperimentRegistry 接入生产管道

**愿景对应**：验收清单 §14.3（P4-EXP-001..010）

**当前状态**：
- `backend/app/signals/safe_experiment_platform.py`（731 行）完整
- `spine_orchestrator.py:2854` SHADOW_ONLY 调用 SafeBanditController
- 无 API、无 DB、无定期 guardrail 检查

**5/5 标准**：
1. 新建 alembic 迁移 `c14_*_safe_experiments.py` 表：`safe_experiments`（生命周期状态机字段齐全）+ `safe_experiment_episodes`
2. 新建 SQLAlchemy 模型，挂到 `models/__init__.py`
3. 新建 `backend/app/api/v1/safe_experiments.py`：CRUD + lifecycle 转换 + opt-out 端点
4. Celery 任务 `monitor_safe_experiment_guardrails`，每 30 分钟检查 guardrail 违规、自动暂停 + 写 incident_trace
5. shadow→canary→safe_live 自动晋升门禁：写 `safe_experiment_promotion_gate.py`，门槛通过 → 写候选审批队列（与 FV-09 对接）
6. 高风险场景禁止 bandit：`SafeBanditController.select_arm()` 加前置检查（D0、crisis_mode、fatigue_critical 直接返回 primary）
7. 用户 opt-out 写入 `user_settings`，bandit 选择前查
8. Prometheus 指标 + Grafana 仪表盘
9. 单测 + 集成测：guardrail 违规自动暂停 / opt-out 阻止 / 高风险场景禁探索
10. 撤掉 `spine_orchestrator.py:2854` 的静默 try/except

**涉及文件**（排他）：
- `backend/app/signals/safe_experiment_platform.py`
- `backend/app/signals/safe_experiment_promotion_gate.py`（新建）
- `backend/app/api/v1/safe_experiments.py`（新建）
- `backend/alembic/versions/c14_*_safe_experiments.py`（新建）
- `monitoring/grafana/dashboards/safe_experiments.json`（新建）

**共享文件协议**：与 FV-01 同。

---

### FV-03 · SimulationLab/SparkleGoalBench CI 门禁

**愿景对应**：验收清单 §14.4（P4-SIM-001..010）

**当前状态**：
- `backend/app/signals/simulation_lab.py`（750 行）实现了 SparkleGoalBench、24 场景、TraceReplaySimulator、Scenario DSL
- 表 `simulation_runs` 存在但无写入路径
- 无 CI 集成、无定期 benchmark 跑

**5/5 标准**：
1. 写 `backend/app/services/simulation_runner.py` 实现 `run_benchmark_suite(suite_name)` —— 调用 SparkleGoalBench、写 `simulation_runs` 表、产生 BenchmarkReport
2. CLI 入口：`python -m backend.scripts.run_simulation_benchmark --suite=full`（新建 `backend/scripts/run_simulation_benchmark.py`）
3. CI 门禁：在 `.github/workflows/ci.yml` 加新 job `simulation-benchmark`，对触及 `backend/app/signals/policy_engine.py`、`backend/app/aurora/`、`backend/app/signals/marketplace.py`、`backend/app/signals/skill_*.py` 的 PR 自动跑回归基准
4. 失败规则：高风险场景失败 → CI 阻断；中等场景失败 → CI 警告；趋势退化 >10% → 阻断
5. 报告产出：`docs/benchmarks/<date>_<commit>.md`，含场景通过率、回归项、成本/延迟估计
6. Celery 周任务 `run_weekly_benchmark`（每周日 03:00）写历史数据
7. Prometheus 指标 + Grafana
8. 单测 + 集成测

**涉及文件**（排他）：
- `backend/app/signals/simulation_lab.py`
- `backend/app/services/simulation_runner.py`（新建）
- `backend/scripts/run_simulation_benchmark.py`（新建）
- `.github/workflows/ci.yml`（仅追加新 job）
- `monitoring/grafana/dashboards/simulation_lab.json`（新建）

---

### FV-04 · Skill/DomainPack Marketplace 上线

**愿景对应**：验收清单 §14.5（P4-MKT-001..010），完全体愿景 §14（Skill Extraction）

**当前状态**：
- `backend/app/signals/marketplace.py`（541 行）实现了 SkillCard v2、PackRegistry
- 零生产调用
- 无 API、无 DB 表、无 UI

**5/5 标准**：
1. 新建 alembic 迁移 `c15_*_marketplace.py`：`marketplace_skills`、`marketplace_packs`、`user_skill_adoptions`、`pack_adoption_history`
2. SQLAlchemy 模型
3. `backend/app/api/v1/marketplace.py`：列表、预览、采纳、撤销、影响追踪、版本回滚端点
4. 接入 SkillLifecycleManager：personal→cohort→system 晋升的 system_skill 自动注册到 marketplace
5. 用户采纳必须显式（POST 带 confirm=true），自动采纳禁止
6. 影响追踪：每次采纳后的 task/plan/source 影响写 `pack_adoption_history` 并关联 trace_id
7. 质量评分：基于 outcome（OutcomeRecorder）+ 负反馈 + 适用范围；不基于下载量
8. 隐私守卫：上架前自动 PII 扫描（复用 `backend/app/aurora/privacy.py`），含 PII 拒绝上架
9. 下架机制：负反馈率 > 30% / 隐私警报 / 用户撤销率 > 50% → 自动降级为 deprecated
10. **Mobile UI**：与 FV-XX UI agent 协调（marketplace 浏览页归本卡片，覆盖 `mobile/lib/features/seed_library/` 的扩展）
11. Prometheus + Grafana
12. 单测 + 集成测：上架/采纳/撤销/下架/PII 扫描全路径

**涉及文件**（排他）：
- `backend/app/signals/marketplace.py`
- `backend/app/api/v1/marketplace.py`（新建）
- `backend/alembic/versions/c15_*_marketplace.py`（新建）
- `mobile/lib/features/seed_library/presentation/marketplace/`（新建子目录）
- `monitoring/grafana/dashboards/marketplace.json`（新建）

---

### FV-05 · PrivacyPreservingCommunityEngine 接入

**愿景对应**：验收清单 §14.6（P4-PCI-001..010），完全体愿景 §7.2（Cohort Mistake Loop）

**当前状态**：
- `backend/app/signals/privacy_community_intelligence.py`（668 行）实现了 PrivacyBudget、AnonymizedCohortStat、PrivacyPreservingCohort、DP、k-anonymity、联邦聚合
- 零生产调用

**5/5 标准**：
1. 新建迁移 `c16_*_community_aggregates.py`：`community_aggregate_signals`、`privacy_budget_ledger`
2. SQLAlchemy 模型
3. 改造 `backend/app/services/community_signal_bridge.py`，让所有跨用户聚合走 PrivacyPreservingCommunityEngine
4. k 阈值默认 5（与 FV-22 协调，从 3 上调到 5）
5. DP 噪声添加（Laplace 机制）默认开启，ε 配置在 `settings.py`
6. PrivacyBudgetLedger 持久化：每个查询消耗 ε，预算耗尽 → 拒绝聚合
7. API：`/api/v1/community/aggregates`（仅 admin 查统计，普通用户看到匿名洞察）
8. CommunityDirective 路径：聚合信号 → CommunityDirective → PolicyEngine（soft bias only，禁止硬覆盖）
9. 用户关闭社群智能：在 `user_settings` 加 `community_intelligence_enabled`，默认 true，关闭后该用户数据不进入聚合也不消费聚合
10. Prometheus + Grafana
11. 单测：k 阈值不达标拒绝聚合 / 预算耗尽拒绝查询 / opt-out 双向隔离 / 跨 cohort 隔离

**涉及文件**（排他）：
- `backend/app/signals/privacy_community_intelligence.py`
- `backend/app/services/community_signal_bridge.py`
- `backend/alembic/versions/c16_*_community_aggregates.py`（新建）
- `monitoring/grafana/dashboards/community_privacy.json`（新建）

---

### FV-06 · DB/Redis 权限隔离 + RBAC

**愿景对应**：验收清单 §17 GOV-019（权限隔离最小化），完全体愿景铁律 8（生产降级/回滚/kill switch/观测）

**当前状态**：Go Gateway 与 Python 后端共用 `POSTGRES_USER` / `POSTGRES_PASSWORD`，无 role 分离

**5/5 标准**：
1. 新建迁移 `c17_*_create_service_roles.py`：创建 PostgreSQL 角色 `sparkle_gateway`、`sparkle_engine`、`sparkle_celery`、`sparkle_readonly`，分配最小权限
2. 表级 GRANT 设计：
   - `sparkle_gateway`：仅可访问 chat/auth/session/cqrs 相关表
   - `sparkle_engine`：可访问 signals/aurora/galaxy/source 相关表
   - `sparkle_celery`：与 engine 同，加上 outbox 写权限
   - `sparkle_readonly`：所有表只读，给 Grafana/admin 读
3. Redis ACL 启用：在 `docker-compose.prod.yml` + `redis.conf` 配置 ACL，三个角色独立密码
4. MinIO 桶级 IAM：`uploads`、`exports`、`backups` 三桶 + 对应服务账号
5. 更新 `docker-compose.yml`、`docker-compose.prod.yml`、`.env.production.example`：每个服务用对应账号
6. 更新 Go Gateway 的 `internal/db/db.go` 和 Python 的 `core/database.py`：用对应 DSN
7. 文档：`docs/engineering/SECURITY_RBAC_2026-05-02.md` 解释架构、迁移路径、回滚步骤
8. **回滚脚本**：迁移含完整 `downgrade()`
9. **本地兼容**：开发环境 `docker-compose.yml` 默认仍用单账号（避免破坏开发体验），仅 prod 启用 RBAC，由 `SPARKLE_RBAC_ENABLED` 环境变量控制
10. 集成测：用各账号尝试越权访问 → 应失败

**涉及文件**（排他）：
- `backend/alembic/versions/c17_*_create_service_roles.py`（新建）
- `docker-compose.yml`
- `docker-compose.prod.yml`
- `.env.production.example`
- `backend/gateway/internal/db/db.go`
- `backend/app/core/database.py`
- `redis.conf`（新建）
- `docs/engineering/SECURITY_RBAC_2026-05-02.md`（新建）

**风险标识**：⚠️ **此卡片高风险**。错误的 RBAC 配置会导致所有服务启动失败。Agent 必须：
- 在 PR 前本地完整跑通 `make local-final-signoff`
- 提供回滚步骤
- 明确标注 `SPARKLE_RBAC_ENABLED=false` 的兼容路径
- 不强制 prod 立即启用，提供文档让运维灰度

---

### FV-07 · ConsentTracker DB 持久化

**愿景对应**：验收清单 §14.8（P4-RES-005 同意），路线图 P0-1.6 / P1-2.3

**当前状态**：`backend/app/signals/research_mode.py:837-916` ConsentTracker 仅内存存储

**5/5 标准**：
1. 新建迁移 `c18_*_consent_records.py`：表 `research_consent_records`（user_id、protocol_id、granted_at、revoked_at、scope、evidence、version）
2. SQLAlchemy 模型挂 `models/__init__.py`
3. 重写 `ConsentTracker`：所有 grant/revoke/check 走 DB（保留内存缓存做性能优化但 source-of-truth 在 DB）
4. 服务重启后状态保持
5. 撤销立即生效：撤销后 `is_consented()` 必须返回 false（即使缓存未刷新）
6. 审计字段：每次变更记录 reason、initiator（user/system/admin）、IP hash
7. 用户可见 API：`GET /api/v1/research/consent` 看自己授予了哪些、`POST /api/v1/research/consent/revoke`
8. 单测 + 集成测：DB 重启 / 并发授予/撤销 / 撤销立即生效

**涉及文件**（排他）：
- `backend/app/signals/research_mode.py`（仅 ConsentTracker 部分）
- `backend/alembic/versions/c18_*_consent_records.py`（新建）
- `backend/app/api/v1/research_consent.py`（新建）

---

### FV-08 · 管理操作审计日志

**愿景对应**：验收清单 §17 GOV-014

**当前状态**：`backend/app/models/audit_log.py` 表存在，但 admin 操作未写入

**5/5 标准**：
1. 新建 `backend/app/middleware/admin_audit.py` FastAPI middleware，自动捕获所有 `/api/v1/*_admin*` 路由的请求 + 用户 + 结果 + 耗时 → 写 `admin_audit_log` 表
2. 装饰器 `@audit_admin_action(category="policy_publish", risk="high")` 用于关键端点
3. 改造以下端点接入审计：
   - `backend/app/api/v1/admin_dashboard.py`
   - `backend/app/api/v1/feedback_admin.py`
   - `backend/app/api/v1/dlq_admin.py`
   - `backend/app/api/v1/executions_admin.py`
   - `backend/app/api/v1/memory_admin.py`
   - 新加的 FV-01/02/04/05 admin 端点（与对应 agent 协调，对方实现端点时调用 `@audit_admin_action`）
4. 策略发布、实验晋升、Marketplace 下架、Skill 推广 → 高风险审计
5. 审计查询 API：`/api/v1/audit/admin_actions`（仅 super_admin 可查）
6. 不可篡改：审计表无 UPDATE 权限（用 PG row-level security 或 trigger）
7. 90 天保留 + 归档到对象存储
8. 单测 + 集成测

**涉及文件**（排他）：
- `backend/app/middleware/admin_audit.py`（新建）
- `backend/app/models/audit_log.py`
- `backend/alembic/versions/c19_*_admin_audit_extensions.py`（新建）
- `backend/app/api/v1/audit.py`（仅扩展，不冲突 FV-07）

**协调点**：FV-01/02/04/05 在自己的 admin 端点上加 `@audit_admin_action` 装饰器（FV-08 提供）。FV-08 在卡片实施完成后留 5 行示例代码给其他 agent 参考。

---

### FV-09 · 发布审批工作流

**愿景对应**：验收清单 §17 GOV-020，完全体愿景 §3.6（PolicyDecision 仲裁）

**当前状态**：完全缺失

**5/5 标准**：
1. 新建 `backend/app/services/release_approval.py`：定义 ApprovalRequest 状态机（draft → pending_review → approved/rejected → applied）
2. 迁移 `c20_*_release_approvals.py`：表 `release_approval_requests`
3. 适用对象：
   - 策略发布（PolicyEngine 规则变更）
   - 实验从 canary → safe_live（与 FV-02 对接）
   - Skill 从 cohort_live → system_skill（与 SkillLifecycleManager 对接）
   - DomainPack 上架/版本升级（与 FV-04 对接）
   - 高风险配置变更（kill switch from shadow → live）
4. 审批人配置：`settings.py` 中 `RELEASE_APPROVERS_BY_CATEGORY`
5. 双人审批强制（policy_publish、experiment_promote、skill_systemize）
6. API：`/api/v1/release_approvals` CRUD + `/approve` + `/reject`
7. **简化的 admin UI**：在 `admin_dashboard.py` 新增审批 tab（不要求做完整前端，HTML 模板足够）
8. 通知集成：审批请求 → 邮件 + admin dashboard 红点
9. 单测 + 集成测

**涉及文件**（排他）：
- `backend/app/services/release_approval.py`（新建）
- `backend/app/api/v1/release_approvals.py`（新建）
- `backend/alembic/versions/c20_*_release_approvals.py`（新建）

---

### FV-10 · DataMinimizationAuditor 扩覆盖 + fail-closed

**愿景对应**：验收清单 §17 GOV-013

**当前状态**：`backend/app/core/data_minimization.py` 仅覆盖 3 模型，fail-open

**5/5 标准**：
1. 扩展 `TARGET_MODEL_SCOPES` 至少覆盖 15 个跨用户/跨 sprint/长期模型，包括但不限于：sprint_pack、chronicle、achievement、growth_chronicle、user_profile、skill_entry、policy_decision、causal_trace、cohort_aggregate、return_case_file、relationship_model、knowledge_node、source_asset、recall_opportunity、intervention_episode
2. 改 fail-open → 配置化：`SPARKLE_DATA_MINIMIZATION_MODE` = `audit` | `enforce`，prod 默认 `enforce`
3. enforce 模式下未注册模型 → 抛 `DataMinimizationViolation`（被上层捕获后写审计、降级 prompt）
4. CI guard：新建 `scripts/guards/check_data_minimization_coverage.py`，扫描所有跨用户模型，未注册即失败
5. 注册到 `scripts/rule_guard_manifest.tsv`
6. 单测 + CI 集成测

**涉及文件**（排他）：
- `backend/app/core/data_minimization.py`
- `scripts/guards/check_data_minimization_coverage.py`（新建）
- `scripts/rule_guard_manifest.tsv`（仅追加一行）

---

### FV-11 · Mobile CRDT 真实合并 + ACK

**愿景对应**：验收清单 §15 APP-005，完全体愿景 §2.5（任务卡离线执行）

**当前状态**：`mobile/lib/core/offline/crdt_sync_manager.dart` 95 行 + sync_engine.dart 481 行，已有出站队列与重试，但：
- CRDT 合并是 last-write-wins，非真正 CRDT
- 无 ACK 验证机制（只对 mastery 有）
- 后端用 Yjs 但前端发 base64 binary

**5/5 标准**：
1. 引入 Dart Yjs 兼容库（`y_dart` 或自建 minimal CRDT，前者优先）
2. KnowledgeMastery / TaskState / ChatMessage 三类对象的合并改用真正的 CRDT 操作（CmRDT 或 deltas）
3. 双向 ACK：后端处理后回 ACK，前端收到后从 outbox 删除（参考现有 mastery ACK 模式 sync_engine.dart:392-416）
4. 冲突解决：纯 CRDT 操作（不再 last-write-wins）
5. 离线 → 在线：恢复网络后自动重放未 ACK 操作；测试 100+ 操作堆积也能正确回放
6. 多端测试：模拟两端同时编辑同一对象 → 合并结果可预期
7. 集成测覆盖：网络抖动、ACK 丢失、并发编辑、长时间离线
8. 性能：单端 1000 操作积累 < 200ms 合并

**涉及文件**（排他）：
- `mobile/lib/core/offline/` 整个目录
- `mobile/test/core/offline/`（测试）
- `mobile/pubspec.yaml`（仅追加依赖）
- 后端契约：与 FV-XX 不冲突，因为后端 CRDT 已存在

**风险**：高。可能需要后端配合调整 CRDT 协议，agent 在报告中明确列出后端 API 期望（不直接改后端，留给 architect 收尾决策）。

---

### FV-12 · 情绪自适应 UI

**愿景对应**：验收清单 §9.1 UX-015、MAGIC-001..006，完全体愿景 §2.5（执行过程持续感知）

**当前状态**：完全缺失（无 EmotionState、无 fatigue_mode UI）

**5/5 标准**：
1. 后端已有疲劳/压力/情绪信号（`backend/app/signals/types.py` 中 fatigue_level、cognitive_load、stress_signal）
2. 前端新增 `mobile/lib/core/design/adaptive/emotion_responsive_theme.dart`：根据后端推送的 emotion/fatigue 状态调整：
   - 字体大小 +1
   - 减少动画
   - 简化卡片层级
   - 调暗色温
   - 隐藏挑战 badge
3. WebSocket message handler 新增 `aurora_state_band` 类型监听，更新 EmotionStateProvider
4. 在 chat、task、home、plan 4 个核心页面应用
5. 用户可手动覆盖（设置中加"情绪适应模式": auto/always_low/always_normal）
6. 单测：状态变化触发样式变化
7. Golden 测试：3 种状态各一张快照
8. 文档：`mobile/docs/EMOTION_ADAPTIVE_UI.md` 解释设计

**涉及文件**（排他）：
- `mobile/lib/core/design/adaptive/`（新目录）
- `mobile/lib/features/aurora/presentation/providers/emotion_state_provider.dart`（新建）
- 4 个核心页面的"集成点"加 wrapper（具体文件 agent 自查，但每文件改动 < 20 行）

**协调点**：与 FV-13/14 无冲突（不同目录）。

---

### FV-13 · 召回通知价值显式显示

**愿景对应**：验收清单 §13 NUDGE-002、NUDGE-009

**当前状态**：`unified_notification_card.dart` 缺 `recall_reason`、`value_reason`、`recall_score` 字段

**5/5 标准**：
1. 后端 `backend/app/signals/recall_notification.py` 输出新增字段：`value_reason`（"为什么这次提醒对你目标有价值"）、`effort_estimate`（一句话）、`deadline_pressure_label`
2. 同步更新 `proto/agent_service.proto`（如 RecallOpportunity 在 proto 中）→ `make proto-gen`
3. 前端 `unified_notification_model.dart` 反序列化新字段
4. `unified_notification_card.dart` 新增"为什么提醒你"展开区
5. 用户可点"这个提醒不准确" → 写入 OutcomeRecorder（与 FV-21 协调）
6. Golden 测试 + 单测

**涉及文件**（排他）：
- `backend/app/signals/recall_notification.py`
- `mobile/lib/features/notification_center/`
- `proto/agent_service.proto`（如改 proto，需通知 architect）

**协调点**：FV-21 也改 `recall_opportunity.py`，FV-13 仅改 `recall_notification.py`（不冲突）。

---

### FV-14 · 集中式无障碍设置面板

**愿景对应**：验收清单 §9.1 UX-013

**当前状态**：无障碍设置散落在 theme_settings、unified_settings、per-feature

**5/5 标准**：
1. 新建 `mobile/lib/features/settings/presentation/screens/accessibility_settings_screen.dart`
2. 集中以下设置：字体缩放、对比度、屏幕阅读优化、触控目标尺寸、动画减弱、色盲友好、TTS、震动反馈、低负荷模式
3. 在 `unified_settings_screen.dart` 加入口（链接而非内嵌）
4. 各 per-feature 设置（如 GalaxyAccessibilityService）保留作为高级覆盖，但同步默认值
5. 全部设置写入 `user_settings` 表（与后端同步，跨设备生效）
6. WCAG AA 合规检查清单文档
7. 单测 + Golden 测试

**涉及文件**（排他）：
- `mobile/lib/features/settings/presentation/screens/accessibility_settings_screen.dart`（新建）
- `mobile/lib/features/settings/presentation/providers/accessibility_provider.dart`（新建）
- `mobile/lib/features/user/presentation/screens/unified_settings_screen.dart`（仅加链接，不改其他）

---

### FV-15 · 多目标 UI（仪表盘 + 切换器）

**愿景对应**：验收清单 §5 GOAL-007/008，完全体愿景 §3.4（Actionable State Register）

**当前状态**：后端 `MultiGoalArbitrator` 完整，UI 缺失

**5/5 标准**：
1. `mobile/lib/features/home/presentation/widgets/multi_goal_dashboard_card.dart`：显示用户所有活跃目标，每个目标显示 deadline、当前阶段、健康度、本周冲突
2. 顶部 GoalSwitcher：选择"当前关注目标"，影响所有 chat/task/galaxy 页面
3. 多目标冲突提示：当系统判断时间/能量冲突时，显示一个"今天我建议先做 X，因为..."的解释卡，用户可覆盖
4. 后端协调：`current_goal_id` 写 user_settings，所有 API 调用带这个 header
5. 与 FV-12 协调：状态卡片样式自适应
6. Golden + 单测

**涉及文件**（排他）：
- `mobile/lib/features/home/presentation/widgets/multi_goal_dashboard_card.dart`（新建）
- `mobile/lib/features/home/presentation/widgets/goal_switcher.dart`（新建）
- `mobile/lib/features/plan/presentation/providers/active_goal_provider.dart`（新建）
- 后端：`backend/app/api/v1/users.py` 增加 `current_goal_id` 字段读写

---

### FV-16 · 任务 PAUSED 状态 + 恢复工作流

**愿景对应**：验收清单 §7 TASK-011/012

**当前状态**：任务支持 start/stuck/complete/abandon，缺 PAUSED 和正式恢复

**5/5 标准**：
1. 后端 `backend/app/services/task_service.py` 加 `pause_task(task_id, reason)` / `resume_task(task_id)`
2. TaskStatus enum 加 PAUSED
3. 数据库迁移：`tasks.status` 加新值
4. PAUSED → resume 时显示恢复卡（"你 2 小时前暂停了 X，现在还要继续吗？"）— 复用现有 StaleRecoveryCard 组件
5. 离开超过预期任务时长 50% → 自动 PAUSED + 推送恢复提醒（与 FV-13 协调）
6. 前端：任务卡片新增 pause 按钮 + paused 状态展示
7. Outcome：PAUSED 不算失败也不算成功，但 OutcomeTracker 记 paused_count
8. 单测 + 集成测

**涉及文件**（排他）：
- `backend/app/services/task_service.py`
- `backend/app/models/task.py`
- `backend/alembic/versions/c21_*_task_paused_status.py`（新建）
- `mobile/lib/features/task/`（pause UI）

---

### FV-17 · 资料生命周期管理

**愿景对应**：验收清单 §8.2 SRC-018，路线图 P1-6

**当前状态**：上传/解析齐全，缺归档/权限撤销/目标结束清理

**5/5 标准**：
1. 新建 `backend/app/services/source_lifecycle.py`：实现 archive/restore/permission_revoke/goal_close_cleanup
2. SourceAsset 加生命周期状态：active / archived / revoked / orphaned
3. 目标关闭时自动 orphaned（用户可一键 archive 或 delete）
4. 共享资料权限撤销立即生效（缓存失效）
5. archived 资料不进 RAG 上下文，但可恢复
6. 90 天 archived → 提醒用户决定 delete or keep
7. delete 走加密擦除（符合 GDPR）
8. API：`/api/v1/sources/{id}/archive` / restore / delete
9. 前端：seed_library 加生命周期管理 UI
10. 单测 + 集成测

**涉及文件**（排他）：
- `backend/app/services/source_lifecycle.py`（新建）
- `backend/app/services/source_service.py`
- `backend/app/models/source.py`
- `backend/app/api/v1/assets.py` 或 `documents.py`（按现有归属）
- `mobile/lib/features/seed_library/`（生命周期 UI）

---

### FV-18 · StrategyBelief.counter_evidence + 反证降权

**愿景对应**：验收清单 §10.2 LEARN-001、OUT-005

**当前状态**：StrategyBelief 缺 counter_evidence 字段

**5/5 标准**：
1. `backend/app/signals/types.py` 中 StrategyBelief 加 `counter_evidence: list[CounterEvidence]`
2. `learning_base.py` 中：用户拒绝 / outcome=harmful / 用户纠正 → 写 counter_evidence
3. `belief_score` 计算引入 counter_evidence 权重（每条 -0.05，最多 -0.3）
4. PolicyEngine 消费 belief 时同时看 counter_evidence 数量，超过阈值 → 不再作为 soft bias
5. 数据库迁移加字段
6. 单测：3 次反证后 belief 失效

**涉及文件**（排他）：
- `backend/app/signals/types.py`
- `backend/app/signals/learning_base.py`
- `backend/app/signals/policy_engine.py`（仅 belief 消费段）
- `backend/alembic/versions/c22_*_counter_evidence.py`（新建）

---

### FV-19 · 危机模式 FSM 化

**愿景对应**：验收清单 §16 STAB-011

**当前状态**：CrisisMode 检测散落，非正式 FSM

**5/5 标准**：
1. `backend/app/signals/crisis_mode_fsm.py`：明确状态机 normal → warning → crisis → recovery → normal
2. 触发条件：deadline_pressure=critical + (knowledge_gap=major OR fatigue=critical OR stress=high)
3. crisis 模式下 PolicyEngine 强制：
   - 任务时长 ≤ 15 分钟
   - 不开新章节
   - 资料调用走 minimal_pass 模式
   - 关闭挑战类成就提醒
   - Aurora L3 不主动召唤（避免增加压力）
4. crisis → recovery 的退出条件：deadline 过 OR 用户主动声明"我恢复了"
5. 用户可见：状态带显示"危机模式中"，含解释
6. 单测 + 集成测

**涉及文件**（排他）：
- `backend/app/signals/crisis_mode_fsm.py`（新建）
- `backend/app/signals/exam_rescue_detector.py`（仅集成 FSM）
- `backend/app/signals/policy_engine.py`（仅 crisis 规则段）

**协调点**：与 FV-18 都改 policy_engine.py — 限制各自只改新增段，不互改。

---

### FV-20 · Saga/补偿事务 + Outbox 一致性

**愿景对应**：验收清单 §16 STAB（高级稳定性）

**当前状态**：CQRS 与 Outbox 已有，无显式 Saga 模式

**5/5 标准**：
1. `backend/gateway/internal/cqrs/saga.go`：实现 SagaCoordinator + CompensationStep 接口
2. 4 个跨服务流程接入 Saga：
   - 任务创建 → 通知 → CRDT 同步
   - 资料上传 → 解析 → 节点挂载
   - 实验晋升 → 通知 → 审计
   - Skill 上架 → Marketplace 注册 → 通知
3. 每步可重试 + 补偿
4. 失败 → 自动补偿 → 恢复一致性
5. 监控：每 saga 实例可追踪
6. 单测 + 集成测：模拟中间步骤失败

**涉及文件**（排他）：
- `backend/gateway/internal/cqrs/saga.go`（新建）
- `backend/gateway/internal/cqrs/saga_test.go`（新建）

---

### FV-21 · 召回 ML 触发器 + value_reason

**愿景对应**：验收清单 §13 NUDGE-001/002/003

**当前状态**：仅 4 个确定性触发器，无 ML 评分

**5/5 标准**：
1. 改 `backend/app/signals/recall_opportunity.py`：触发器从 4 增到 8（加：long_silence、context_window_optimal、material_decay、cohort_pattern_alert）
2. RecallScore 计算：基于 goal_value + decay_curve + user_response_history + fatigue_state
3. 每个 RecallOpportunity 必须输出 `value_reason`、`effort_estimate`、`deadline_pressure`
4. 与 FV-13 对接：通知卡片显示这些字段
5. ML 评分轻量：决策树或 logistic regression（不引入大模型）
6. 训练数据来自历史 OutcomeRecorder（用户响应/忽略历史）
7. 模型版本管理：`backend/app/services/ml/recall_ranker.py` + 模型文件
8. A/B 测试支持：与 FV-02 SafeBandit 对接
9. 单测 + 集成测

**涉及文件**（排他）：
- `backend/app/signals/recall_opportunity.py`
- `backend/app/services/ml/recall_ranker.py`（新建）
- `backend/app/services/ml/__init__.py`（新建）

---

### FV-22 · 社群资源质量评分 + cohort 阈值上调

**愿景对应**：验收清单 §12 COM-007

**当前状态**：cohort 阈值 3（偏低），无质量排名

**5/5 标准**：
1. `backend/app/services/community_service.py`：cohort_aggregation_min_k 默认从 3 → 5
2. 资源质量评分：基于 adoption_count + outcome_effectiveness + negative_feedback_rate + scope_match
3. 排名 API：`/api/v1/community/resources?sort=quality`
4. 低质量资源（评分 < 0.3）自动隐藏（不删除）
5. 用户可标记"误导我" → 立即降权
6. Prometheus 暴露质量分布
7. 单测 + 集成测

**涉及文件**（排他）：
- `backend/app/services/community_service.py`
- `backend/app/api/v1/community.py`

**协调点**：与 FV-05（PrivacyCommunityIntelligence）的 k 阈值同步上调到 5。

---

### FV-23 · i18n 残余清零

**愿景对应**：验收清单 §9 UX-014，路线图 P2-4

**当前状态**：约 128 文件、~459 个硬编码字符串待转

**5/5 标准**：
1. 完成所有剩余 ~459 字符串的 i18n 转换
2. 运行时 `isChinese ? '中文' : 'English'` 模式（项目既定策略，见 MEMORY.md）
3. CI 守卫：`scripts/guards/check_i18n_coverage.py` 扫描 mobile/lib，硬编码中文字符串数为 0
4. 注册到 `rule_guard_manifest.tsv`
5. 双语完整：每个新字符串中英对照
6. 报告中列出转换的文件清单

**涉及文件**（排他）：
- 用户提供的"128 个 widget 文件"清单（具体由 agent 自查，遵循已转换 85 文件的模式）
- `scripts/guards/check_i18n_coverage.py`（新建）

**风险防护**：i18n 改动接触面广。规则：每文件 PR 描述列出，CI 自动 diff 检查。

---

### FV-24 · SLO 自动响应 + 服务端弱网

**愿景对应**：验收清单 §16 STAB-014/STAB-018，路线图 P3-2

**当前状态**：11 SLO 告警规则但无自动响应

**5/5 标准**：
1. `monitoring/alertmanager.yml`：高优先级告警 → webhook 触发自动降级
2. 新建 `backend/app/api/internal/auto_degrade.py`：接收 webhook，根据告警类型自动调整 kill switch（LLM 慢 → 切换到便宜模型，Redis 满 → 启用磁盘缓存等）
3. 5 类自动响应：LLM_LATENCY_HIGH / REDIS_NEAR_FULL / DB_CONNECTION_EXHAUST / EVENT_BUS_LAG / GW_HIGH_5XX
4. 每次自动降级写审计 + 通知运维
5. 服务端弱网容忍：Go Gateway 加请求保活机制 + Python 引擎对 client 断连自动保存中间状态
6. 集成测：用 Toxiproxy 模拟降级

**涉及文件**（排他）：
- `monitoring/alertmanager.yml`
- `backend/app/api/internal/auto_degrade.py`（新建）
- `backend/gateway/internal/middleware/network_resilience.go`（新建）

---

### FV-25 · v1/v2 旧代码清理 + 文档同步

**愿景对应**：验收清单维护性

**当前状态**：`research_grade.py` 中 v1 模块（CounterfactualEngine、ExperimentRegistry v1）与 v2 共存

**5/5 标准**：
1. 在 FV-01/02/04/05 完成后（**等待依赖**），清理 `backend/app/signals/research_grade.py`
2. v1 代码加 `# DEPRECATED: removed in next sprint, use v2 from <module>`
3. 从 `signals/__init__.py` 移除 v1 导出（或重命名为 `_v1` 后缀）
4. 测试中如还引用 v1，迁移到 v2
5. 文档同步：
   - `CLAUDE.md` 反映完全体状态
   - `docs/00_项目概览/02_技术架构.md` 更新
   - `docs/aurora/` 下相关文档同步
6. ADR：新增 `docs/adr/0004_full_vision_completion_2026-05-02.md` 记录架构决策

**依赖**：必须在 FV-01/02/04/05 完成后运行（Architect 收尾时统一调度）

**涉及文件**（排他）：
- `backend/app/signals/research_grade.py`
- `backend/app/signals/__init__.py`（移除 v1 导出）
- `docs/adr/0004_full_vision_completion_2026-05-02.md`（新建）
- `docs/00_项目概览/`、`docs/aurora/`（同步）

---

## 5. 推荐派遣顺序

### 5.1 一次性派遣可行性

**全部 25 卡片可以同时派遣**（已通过文件域设计避免冲突）。

如分两批为更安全，按下列顺序：

**第一批（20 卡片，无依赖）**：
FV-01, FV-02, FV-03, FV-04, FV-05, FV-06, FV-07, FV-08, FV-10, FV-11, FV-12, FV-13, FV-14, FV-15, FV-16, FV-17, FV-18, FV-19, FV-20, FV-22, FV-23, FV-24

**第二批（依赖第一批）**：
- FV-09（释放审批工作流，需 FV-01/02/04 端点已存在以挂审批 hook）
- FV-21（召回 ML 需 FV-13 通知字段已定义；二者轻量，可并行）
- FV-25（清理 v1 必须在 FV-01/02/04/05 完成后）

### 5.2 一次派遣 25 个的协调原则

如果选一次性派遣 25 个，遵守：
- FV-09 / FV-21 / FV-25 中如发现依赖文件未就绪 → **写明依赖、跳过冲突部分、在报告中标记"等待 FV-XX 完成后补完"**
- Architect 收尾时为这三张做最后一公里集成

---

## 6. 共享文件冲突解决（Architect 收尾职责）

以下文件会被多 agent 同时追加修改。Architect 在收尾阶段统一合并：

| 文件 | 涉及卡片 | 合并策略 |
|------|----------|----------|
| `backend/app/celery_schedule.py` | FV-01, FV-02 | 按 ID 顺序追加 add_periodic_task 块 |
| `backend/app/core/celery_tasks.py` | FV-01, FV-02, FV-03, FV-05, FV-07 | 按 ID 顺序追加 task 函数 |
| `backend/app/aurora/runtime_v1/models.py` | FV-01 (CounterfactualReport)，FV-07（间接） | FV-01 追加；FV-07 用独立模型表 |
| `backend/app/api/v1/__init__.py` 或 `router.py` | FV-01, FV-02, FV-04, FV-07, FV-09 | 按 ID 顺序追加路由 include |
| `monitoring/prometheus.yml` | FV-01, FV-02, FV-03, FV-04, FV-05, FV-21 | 追加 scrape_config |
| `monitoring/alertmanager.yml` | FV-24 | FV-24 全权 |
| `backend/app/signals/__init__.py` | FV-01, FV-25 | FV-01 追加；FV-25 移除 v1 |
| `backend/app/signals/policy_engine.py` | FV-18, FV-19 | FV-18 改 belief 段，FV-19 加 crisis 段 |
| `backend/app/models/__init__.py` | FV-01, FV-02, FV-04, FV-05, FV-07, FV-16, FV-18 | 追加新模型 import |
| `scripts/rule_guard_manifest.tsv` | FV-10, FV-23 | 追加新规则行 |

每位 agent 的报告中如果触及上述文件，**只追加自己的内容、不删改他人**。Architect 在最终合并时使用 `git diff` 校验。

---

## 7. Agent 完成后的 Architect 收尾任务

Architect（Claude/我）在所有 agent 完成后负责：

1. **冲突解决**：合并 §6 的共享文件冲突
2. **依赖兜底**：完成 FV-09 / FV-21 / FV-25 中因依赖未就绪而跳过的部分
3. **集成验证**：
   - `make local-final-signoff` 全绿
   - `bash scripts/run_all_rule_guards.sh` 全绿
   - `cd backend && pytest` 全绿
   - `cd backend/gateway && go test ./...` 全绿
   - `cd mobile && flutter test` 全绿
   - `cd mobile && flutter analyze` 全绿
4. **真实 E2E 验证**（Three Illusions 防护，参考 MEMORY.md）：
   - 启动完整 docker-compose stack
   - 跑 5 个核心场景：考试冲刺、资料上传、任务执行、卡住分流、Aurora L3 唤醒
   - 录屏存档
5. **完全体验收 22 节扫描**：每节随机抽 3 项，跟 5/5 标准对比
6. **一票否决项 10 项**：逐项 grep 验证证据
7. **最终报告**：`docs/product/SPARKLE_FULL_VISION_COMPLETION_2026-05-02.md`，含：
   - 25 卡片完成状态矩阵
   - 22 节验收实测分数
   - 一票否决核查清单
   - 已知缺口（如有）+ 建议
   - 完全体宣告（YES/NO + 理由）
8. **生产准备**：
   - 提供运维 runbook 更新
   - kill switch 默认状态确认
   - 灰度发布建议
9. **MEMORY.md 更新**：新增完全体达成记录
10. **commit + 推 PR 到 main**：分批合并 25 个分支到 integration → main

---

## 8. 报告模板（每个 FV-XX 必须按此格式）

文件位置：`docs/product/parallel_closeout/FV-XX_<short_name>_REPORT_2026-05-02.md`

```markdown
# FV-XX · <名称> · 完成报告

**Agent**: codex-agent-XX
**Branch**: codex/FV-XX-<short-name>
**Date**: 2026-05-02
**Status**: COMPLETED / PARTIAL / BLOCKED

## 1. 5/5 标准达成情况

按本卡片的 5/5 标准逐项打勾或说明：

| # | 标准 | 状态 | 证据 |
|---|------|------|------|
| 1 | <标准 1> | ✅ | <文件路径:行号 + 一句话> |
| 2 | <标准 2> | ✅ | ... |
| ... | ... | ... | ... |

## 2. 文件变更清单

```
<git diff --stat 输出>
```

## 3. 测试证据

### 单测
```
<pytest 输出关键行>
```

### 集成测
```
<集成测输出>
```

### Lint / 类型 / Guard
```
<相关命令输出>
```

## 4. 用户视角变化

> 在 <场景> 中，用户现在能 <做什么/感受到什么>，这是之前做不到/感受不到的。

具体场景：
- 之前：...
- 之后：...

## 5. 与其他卡片的协调

- 与 FV-XX 共享文件 <path>：仅追加，未改动 FV-XX 部分。
- 依赖：等待 FV-XX 完成（如有）。
- 留给 Architect：<具体哪些集成点需要架构师收尾>

## 6. 已知限制 / 后续

- ...

## 7. 验收命令一键回放

```bash
<可被 architect 复制粘贴运行的验证命令序列>
```
```

---

## 9. 进度标记格式

每个 agent 完成后写 `.claude/fix-progress/FV-XX.done`：

```
FV-XX: <名称>
Status: DONE
Branch: codex/FV-XX-<short-name>
Modified files:
- <file 1>
- <file 2>
Verification:
- <command 1>: PASS
- <command 2>: PASS
User-visible change: <一句话>
Architect handoff: <如有，否则 N/A>
```

---

## 10. 给 Architect（最终收尾人）的预案

### 10.1 验收失败的处理

如果某个 FV-XX 报告通过但实际验证失败：
1. 不直接回滚（agent 已工作）
2. 创建 `FV-XX-fix` 子任务，由 architect 直接修复或派新 agent
3. 在最终报告中标注

### 10.2 一票否决触发的应急

如发现任一一票否决项：
1. **不宣告完全体**
2. 紧急派新 agent 修复
3. 重新走完 §7 全流程
4. 记入 MEMORY.md

### 10.3 完全体达成判据

必须全部满足：
- [ ] 25 卡片状态矩阵：全 COMPLETED 或 PARTIAL（带明确缺口说明）
- [ ] 22 节验收清单：每节抽样 3 项达 5/5
- [ ] 一票否决：0/10 触发
- [ ] 全部 CI gates 绿
- [ ] 真实 E2E 5 场景通过
- [ ] 性能 SLO 不退化
- [ ] 运维 runbook 已更新

---

## 11. 完全体愿景对照表

每张卡片对应的愿景章节，方便 agent 快速回到原始要求：

| FV-XX | 愿景章节 | 验收清单 | 路线图 |
|-------|---------|----------|--------|
| FV-01 | §3.9 因果归因 | §14.2 P4-CF | P0-1.1 |
| FV-02 | §3.6 仲裁 | §14.3 P4-EXP | P0-1.2 |
| FV-03 | §10 学习闭环 | §14.4 P4-SIM | P0-1.3 |
| FV-04 | §14 Skill 沉淀 | §14.5 P4-MKT | P0-1.4 |
| FV-05 | §7.2 Cohort | §14.6 P4-PCI | P0-1.5 |
| FV-06 | 铁律 8 | §17 GOV-019 | P0-2.1 |
| FV-07 | §10 反馈闭环 | §14.8 P4-RES-005 | P0-1.6 |
| FV-08 | 铁律 8 | §17 GOV-014 | P1-7.1 |
| FV-09 | §3.6 仲裁 | §17 GOV-020 | P1-7.2 |
| FV-10 | §10 数据最小化 | §17 GOV-013 | P1 |
| FV-11 | §2.5 离线 | §15 APP-005 | P0-3 |
| FV-12 | §2.5 / MAGIC | §9.1 UX-015 | P2-1.1 |
| FV-13 | §13 召回 | §13 NUDGE-002 | P2-1.3 |
| FV-14 | §9 UX | §9.1 UX-013 | P2-1.5 |
| FV-15 | §3.4 多目标 | §5 GOAL-007/008 | P1-5.2 |
| FV-16 | §2.5 任务 | §7 TASK-011 | P1-4 |
| FV-17 | §8 资料 | §8.2 SRC-018 | P1-6 |
| FV-18 | §10.2 学习 | §10.2 LEARN-001 | P1-3.2 |
| FV-19 | §2.5 危机 | §16 STAB-011 | P1-8.1 |
| FV-20 | 铁律 8 | §16 STAB | P3-1.1 |
| FV-21 | §13 召回 | §13 NUDGE-001 | P2-3.1 |
| FV-22 | §7.3 资源 | §12 COM-007 | P2-2.1/2.2 |
| FV-23 | §9 UX | §9 UX-014 | P2-4 |
| FV-24 | 铁律 8 | §16 STAB-018 | P3-2.1/2.2 |
| FV-25 | 维护性 | — | P3-3.3 |

---

## 12. 总结：派遣到完全体的关键路径

```
Step 1: 用户派遣 25 个 agent（一次性或分两批）
  → 每个 agent 读完整愿景文档 + 验收清单 + 本派遣文档
  → 每个 agent 在自己的分支独立工作
  → 工作产物：代码 + 测试 + 报告 + 进度标记

Step 2: Architect 收尾（本对话的下一轮）
  → 合并共享文件冲突
  → 完成依赖型卡片（FV-09/21/25）
  → 跑完整 CI + E2E
  → 22 节验收抽查
  → 一票否决核查
  → 写最终完全体报告

Step 3: 用户审阅 + main 合并
  → 灰度发布
  → 监控 SLO
  → 完全体宣告
```

完全体的标准只有一句话：

> **用户把目标、资料、限制、失败和反馈交给 Sparkle 后，Sparkle 能持续把这些信息编译成更好的下一步，并且每一次重要改变都可解释、可纠正、可验证、可回流、可长期沉淀。**

25 个 agent 各司其职，Architect 统一收口。这是从当前状态到完全体的最短路径。

---

> **本文档不可修改**。所有 agent 仅追加自己的报告到 `docs/product/parallel_closeout/`。
> Architect（Claude）保留最终修订权限，任何对本文档的更新必须以新版本号发布。
