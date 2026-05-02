# Sparkle 完全体达标路线图

> 版本：v1.0 | 日期：2026-05-02 | 基于：10 个并行 Exploration Agent 全代码库深度审计
>
> 用途：指导 coding agent 系统性地将每一项验收标准从当前状态提升至 5/5 满分。
> 本文档描述"需要做到什么"和"现在差在哪里"，不描述"具体怎么改代码"。

---

# 0. 使用说明

## 0.1 条目格式

每个条目包含：
- **现状**：代码库里现在是什么样的
- **5 分标准**：达到满分时应该是什么样（具体的、可验证的行为描述）
- **具体差距**：逐一列出当前不满足 5 分标准的点
- **涉及模块**：差距分布在哪些文件/目录

## 0.2 优先级定义

| 优先级 | 含义 | 目标时间 |
|--------|------|----------|
| **P0** | 阻塞完全体。不解决则相应领域无法达到 4+ 分 | 第一优先 |
| **P1** | 接近通过线。解决后 Core/Experience 可通过 | 第二优先 |
| **P2** | 体验显著提升。解决后用户体验达到愿景标准 | 第三优先 |
| **P3** | 锦上添花。长期竞争力的最后打磨 | 第四优先 |

## 0.3 5 分满分标准定义

```
5 分 = 长期稳定、可解释、可撤销、可观测、可降级、可用于 P4 研究级评估

具体意味着：
- 功能在生产环境中被真实用户路径消费（不是只有测试调用）
- 输出可追溯到输入，有完整审计链
- 错误判断可被系统或用户撤回
- 有 Prometheus 指标、Grafana 仪表盘、告警规则
- 有降级路径：依赖不可用时不会崩溃，而是安全回退
- 有关键行为的 E2E 测试和回归测试
- 对 P4 条目：生成结构化 episode 数据，可被反事实评估消费
```

---

# 1. P0：阻塞完全体

## P0-1：P4 研究系统接入生产管道

### P0-1.1：CounterfactualEvaluation 未被任何管道消费

**现状**：`backend/app/signals/counterfactual_evaluation.py`（797 行）完整实现了 `MatchedContextEvaluator`、`CounterfactualEstimate`、`PolicyComparisonReport`、`PolicyUpdateCandidateBuilder`、`CounterfactualIronLawEnforcer`。代码质量高。但没有任何生产管道、API 端点、或 Celery 定时任务调用它。唯一调用在 `SpineOrchestrator._run_counterfactual_shadow()` 中，仅写日志不产生效果。

**5 分标准**：
1. 存在定时任务（Celery Beat），每天/每周自动运行反事实评估
2. 评估结果（PolicyComparisonReport）写入可查询的存储（Redis + PG）
3. PolicyUpdateCandidate 满足门槛时，自动生成推广提案并进入审批队列
4. 反事实评估的覆盖率指标进入 Prometheus
5. 评估结果有 Grafana 仪表盘展示
6. CounterfactualIronLaw 的 6 条铁律在每次评估中强制执行，违规记录到审计日志
7. 存在回归测试，验证反事实评估管道端到端运行
8. 旧版 `research_grade.py` 中的 `CounterfactualEngine` 标记为 deprecated 并停止被导入

**具体差距**：
- 无定时调度触发评估
- 评估结果无处持久化
- PolicyUpdateCandidate 无晋升路径
- 无指标暴露
- 无仪表盘
- 旧版 v1 代码仍共存且被 `__init__.py` 导入

**涉及模块**：`backend/app/signals/counterfactual_evaluation.py`, `backend/app/signals/research_grade.py`, `backend/app/core/celery_schedule.py`

---

### P0-1.2：SafeExperimentRegistry 未被生产管道消费

**现状**：`backend/app/signals/safe_experiment_platform.py`（731 行）实现了 `SafePolicyExperiment`（7 阶段生命周期）、`SafeBanditController`（UCB1）、`SafeExperimentRegistry`、`ExperimentDesignValidator`、`ExperimentGuardrails`。但 `SafeExperimentRegistry` 无 API 端点、无定时任务自动管理实验生命周期、实验状态不持久化到 DB。

**5 分标准**：
1. `SafeExperimentRegistry` 有 REST API 端点用于创建、查看、暂停、终止实验
2. 实验状态持久化到 PostgreSQL（不仅是 Redis）
3. 存在定期检查所有活跃实验 guardrails 的 Celery 任务
4. guardrail 违规时自动暂停实验并记录 incident trace
5. shadow→canary→safe_live 晋升有明确的自动化门槛检查
6. 用户 opt-out 设置可阻止被纳入实验
7. 实验仪表盘在 Grafana 中可见
8. 禁止在高风险场景（D0、危机模式、疲劳 critical）中运行 bandit 探索

**具体差距**：
- 无 API 端点
- 无 DB 持久化
- 无定期 guardrail 检查
- 无自动暂停/回滚
- 无仪表盘
- 高风险场景禁止探索未强制执行

**涉及模块**：`backend/app/signals/safe_experiment_platform.py`, `backend/app/signals/policy_experiments.py`, `backend/app/api/v1/`

---

### P0-1.3：SparkleGoalBench 未被 CI/晋升管道调用

**现状**：`backend/app/signals/simulation_lab.py`（750 行）实现了 24 个回归场景（ExamSprintBench 12 + ProjectDeliveryBench 4 + JobSearchBench 4 + MultiGoalLifeBench 4）、`SyntheticPersonaSimulator`、`TraceReplaySimulator`、`SparkleGoalBench`。`PromotionGate` 引用 benchmark 结果但没有任何东西实际触发 `run_full_suite()`。

**5 分标准**：
1. CI 管道中有一个 job 在每次 PR 合并到 main 前运行 `SparkleGoalBench.run_full_suite()`
2. benchmark 结果与 baseline 比较，回归时阻止合并
3. 策略/Skill/DomainPack/Prompt 变更前必须通过相关 benchmark 场景
4. benchmark 结果可追溯（存储到可查询的存储，带上 git commit SHA）
5. 模拟覆盖 Flutter→Go→Python→EventBus 主路径
6. 模拟验证系统保留用户纠正与覆盖
7. 模拟检查错误写入 long_term 的情况
8. SyntheticPersona 不作为唯一评估依据（有明确的混合策略）
9. 极端场景（D0 危机、零基础、多目标冲突）必须全部通过
10. 有独立的 benchmark 报告可导出

**具体差距**：
- 无 CI 集成
- 无回归门禁
- 无变更前强制运行
- 无结果持久化和对比
- 无主路径覆盖验证
- 模拟仅覆盖 Python 层，未跨层

**涉及模块**：`backend/app/signals/simulation_lab.py`, `.github/workflows/ci.yml`, `scripts/`

---

### P0-1.4：Marketplace 未被生产管道消费

**现状**：`backend/app/signals/marketplace.py`（541 行）实现了 `SkillCard` v2、`DomainPackReview`、`MarketplaceRegistry`、`AdoptionRecord`、10 条 `MarketplaceIronLaws`。但无 API 端点、`SkillCard` 不被 `skill_selection_service.py` 使用。

**5 分标准**：
1. 存在 `/marketplace/skills` 和 `/marketplace/packs` REST API 端点
2. 用户可预览 Skill/Pack 影响范围后再采纳
3. 采纳后效果被追踪（Outcome → AdoptionRecord）
4. 质量基于 outcome/负反馈/适用范围，非下载量
5. 负反馈或回归时自动下架或降级
6. 版本回滚可用
7. 资产不得包含个人隐私（上架前自动扫描）
8. 高影响资产发布有审批流程
9. `SkillCard` 被 `skill_selection_service.py` 实际消费
10. 旧版 `strategy_marketplace.py` 标记 deprecated

**具体差距**：
- 无 API 端点
- 无采纳追踪闭环
- 无自动质量评分
- 无自动下架机制
- 无审批工作流
- SkillCard 未被消费
- 旧版 v1 代码共存

**涉及模块**：`backend/app/signals/marketplace.py`, `backend/app/signals/strategy_marketplace.py`, `backend/app/services/skill_selection_service.py`, `backend/app/api/v1/`

---

### P0-1.5：PrivacyPreservingCommunityEngine 未被生产管道消费

**现状**：✅ 2026-05-02 FV-05 已完成核心生产接入。`CommunitySignalBridge.build_privacy_preserving_cohort_signal()` 现在统一执行用户 opt-out、k>=5、DP Laplace 噪声、持久化预算账本、匿名聚合信号持久化、候选 soft-bias event 发布；新增 `/community/aggregates/*` 管理/用户洞察 API、Prometheus 指标与 Grafana dashboard。验收报告见 `docs/product/parallel_closeout/FV-05_privacy_community_intelligence_REPORT_2026-05-02.md`。

**5 分标准**：
1. `community_error_aggregation_service.py` 的聚合逻辑改用 `PrivacyPreservingCommunityEngine`
2. 所有社群信号的 k-anonymity 阈值提升到 ≥5（当前为 3）
3. `PrivacyBudget` 被实际追踪和限制（每用户每小时/每天/每周额度）
4. 差分隐私噪声在实际聚合中应用
5. 隐私审计追踪被记录并可查询
6. Cohort drift 检测触发自动刷新
7. 用户可查看"此洞察如何产生"的高层解释
8. 用户可关闭社群智能或特定类型的社群信号
9. 有 Prometheus 指标监控隐私预算消耗
10. 跨 cohort 信号不泄露（不同课程/目标隔离）

**具体差距**：
- ✅ 隐私引擎已被 `CommunitySignalBridge` 生产消费
- ✅ k-anonymity 阈值默认 5
- ✅ `privacy_budget_ledger` 持久化追踪预算消耗/拒绝
- ✅ 差分隐私 Laplace 噪声应用于实际聚合
- ✅ `community_aggregate_signals` + budget ledger 可审计查询
- ✅ `user_settings.community_intelligence_enabled` 提供用户关闭入口
- 🟡 后续集成项：将所有历史 `community_error_aggregation_service.py` 聚合入口逐步改为直接调用该 bridge，避免双轨维护

**涉及模块**：`backend/app/signals/privacy_community_intelligence.py`, `backend/app/services/community_error_aggregation_service.py`, `backend/app/services/community_service.py`

---

### P0-1.6：ConsentTracker 使用内存存储

**现状**：`backend/app/signals/research_mode.py` 中的 `ConsentTracker` 使用 `_consents: dict` 内存字典存储用户同意状态。服务重启后所有同意记录丢失。

**5 分标准**：
1. 同意状态持久化到 PostgreSQL
2. 与现有 `UserMemorySettings` 模型集成或创建独立的 `ResearchConsent` 模型
3. 用户可通过设置 UI 查看和修改同意
4. 同意撤销后，已导出数据的使用记录被标记
5. API 端点 `/research/consent` 支持 GET/PUT
6. 同意变更记录到审计日志

**具体差距**：
- 内存存储→服务重启丢失
- 无 DB 模型
- 无 UI 集成
- 无撤销追踪
- 无 API 端点

**涉及模块**：`backend/app/signals/research_mode.py`, `backend/app/models/user_memory_settings.py`, `mobile/lib/features/settings/`

---

## P0-2：基础设施权限隔离

### P0-2.1：Go Gateway 与 Python AI 引擎共用单一数据库凭据

**现状**：Go Gateway 和 Python 后端使用同一个 `DATABASE_URL` 连接字符串。没有读/写分离，没有服务账户区分。Gateway 只需要读聊天历史/写消息，AI 引擎需要读/写知识图谱/任务/状态——但它们共享完全相同的数据库权限。

**5 分标准**：
1. 至少两个数据库用户：`sparkle_gateway`（只读聊天/用户表，写消息/会话表）和 `sparkle_engine`（读/写知识图谱/任务/状态表）
2. 连接字符串使用 TLS
3. 凭据不在代码或配置文件中硬编码（使用环境变量或 secret manager）
4. 存在凭据轮换策略文档和自动化脚本
5. CI 中的 gitleaks 扫描验证无凭据泄露
6. 数据库权限变更记录到审计日志

**具体差距**：
- 无服务账户分离
- TLS 配置不可见
- 连接字符串在 `.env` 文件中以明文存储
- 无凭据轮换策略
- 无自动化轮换

**涉及模块**：`backend/gateway/.env`, `backend/.env`, `docker-compose.yml`, `docker-compose.prod.yml`

---

### P0-2.2：Redis 和 MinIO 同样缺乏权限隔离

**现状**：与数据库类似，Redis 和 MinIO 使用单一凭据，Gateway 和 Engine 共享完全访问权限。

**5 分标准**：
1. Redis 使用不同的 ACL 用户（Gateway 只读缓存 + 发布订阅，Engine 读/写所有键）
2. MinIO 使用不同的 access key（Gateway 只写文件，Engine 只读文件）
3. 生产环境中 Redis 和 MinIO 强制 TLS
4. 凭据轮换策略覆盖所有基础设施

**具体差距**：
- 无 ACL 用户分离
- 无读写权限区分
- TLS 非强制

**涉及模块**：`docker-compose.prod.yml`, `backend/gateway/.env`, `backend/.env`

---

### P0-2.3：DataMinimizationAuditor 覆盖不足且 fail-open

**现状**：`backend/app/core/data_minimization.py` 仅覆盖 3 个目标模型（`sprint_pack`、`chronicle`、`achievement`）。`check_before_store()` 对未知模型采用 fail-open（放行），意味着新增存储路径可能绕过审计。

**5 分标准**：
1. 覆盖所有写入长期存储的模型（至少 10+ 个）
2. 对未知模型采用 fail-closed（拒绝）或至少 warn + 人工审核
3. 敏感字段注册表覆盖所有已知 PII 字段
4. 每次 `check_before_store()` 调用记录到审计日志
5. CI 中有规则守卫验证新存储路径已被覆盖

**具体差距**：
- 仅 3 个模型被覆盖
- fail-open 机制不安全
- 无审计日志记录
- 无 CI 守卫

**涉及模块**：`backend/app/core/data_minimization.py`, `scripts/guards/`

---

## P0-3：移动端 CRDT 同步

### P0-3.1：Flutter CRDT 同步是占位符

**现状**：`mobile/lib/core/offline/crdt_sync_manager.dart` 包含明确的注释 `"STATUS: NOT YET IMPLEMENTED"`。方法体为空。后端 `CRDTPersistenceManager` + `CollaborativeGalaxyService`（基于 Yjs）已成熟，但移动端完全未接入。

**5 分标准**：
1. Flutter 端实现基于 Yjs 或 Automerge 的 CRDT 同步
2. 图谱节点掌握度离线更新后，恢复网络时自动合并（无冲突）
3. 冲突解决策略明确（如掌握度取最大值）
4. 离线任务状态同步后与后端状态一致
5. E2E 测试覆盖离线→在线同步场景
6. 同步状态在 UI 中可见（如同步中心屏幕中显示）

**具体差距**：
- `CRDTSyncManager` 完全空实现
- 无移动端 Yjs/Automerge 集成
- 无离线→在线合并测试
- 当前离线同步使用简单的出站队列，非 CRDT

**涉及模块**：`mobile/lib/core/offline/crdt_sync_manager.dart`, `mobile/lib/core/offline/sync_engine.dart`, `backend/app/services/galaxy/crdt_persistence.py`

---

# 2. P1：接近通过线

## P1-1：定时调度缺失

### P1-1.1：DailyGoalReflection 未接入定时调度

**现状**：`AsyncDeepLearner.run_daily_goal_reflection()`（Job 1）已完整实现：分析当日瓶颈、统计成败比、判断策略修正需求、决定是否建议 Aurora 校准。但触发条件是 L4 累积信号 ≥10 条，而非每日定时执行。

**5 分标准**：
1. Celery Beat 定时任务每天在用户活跃时段结束后自动执行
2. 产出存入 Redis（7 天 TTL）并可选持久化到 PG
3. 次日在用户首次打开时呈现（通过 `NextActionsCard` 或状态带）
4. 有指标监控执行成功率和延迟

**具体差距**：
- 无 Celery Beat 调度配置
- 触发依赖信号累积而非时间
- 无次日呈现机制

**涉及模块**：`backend/app/signals/async_deep_learner.py`, `backend/app/core/celery_schedule.py`

---

### P1-1.2：StateDecay 未定期执行

**现状**：`AsyncDeepLearner.run_state_decay_and_retraction()`（Job 6）实现了置信度时间衰减（48h 后因子 = max(0.1, 1.0 - (age-48)*0.01)）和矛盾检测。同样依赖 L4 累积触发，非定期。

**5 分标准**：
1. Celery Beat 定时任务每 6-12 小时执行一次
2. 衰减后的状态更新到 StateRegister
3. Retraction 产生的撤回事件写入 CausalTrace
4. 有指标监控衰减率和撤回率

**具体差距**：
- 无定期调度
- 撤回事件未入 CausalTrace
- 无指标暴露

**涉及模块**：`backend/app/signals/async_deep_learner.py`, `backend/app/core/celery_schedule.py`

---

### P1-1.3：OutcomeTracker.verify_pending() 未定期执行

**现状**：`OutcomeTracker.verify_pending()` 将超时未验证的预期结果标记为 "inconclusive"。方法已实现，注释说明"由调度器定期调用"，但 Celery Beat 中无此任务。

**5 分标准**：
1. Celery Beat 每 1-2 小时执行一次
2. 超时结果正确标记并对后续策略生效
3. 有 Grafana 面板展示待验证/已超时比例

**具体差距**：
- 无 Celery Beat 配置
- 无仪表盘

**涉及模块**：`backend/app/signals/outcome_tracker.py`, `backend/app/core/celery_schedule.py`

---

## P1-2：数据持久化

### P1-2.1：GrowthChronicle 仅存 Redis，无数据库持久化

**现状**：`GrowthChronicleService` 所有条目（`ChronicleEntry`）仅存 Redis（90 天 TTL）。TTL 过期后用户成长叙事丢失。

**5 分标准**：
1. 已确认（confirmed）的 `ChronicleEntry` 同步写入 PostgreSQL
2. 用户可查看完整成长历史，不受 TTL 限制
3. `build_return_case_file()` 从 PG 加载被确认条目
4. 支持分页查询（append-only，不全量加载）
5. 删除/隐藏操作同步到 PG

**具体差距**：
- 无 PG 持久化
- 90 天 TTL 后数据丢失
- 无分页查询

**涉及模块**：`backend/app/signals/growth_chronicle.py`, `backend/app/models/`

---

### P1-2.2：GoalWorldGraph 仅存 Redis，无数据库持久化

**现状**：`GoalWorldGraphService` 使用 Redis 存储完整的 `GoalWorldGraph`（含节点、依赖、瓶颈）。TTL 风险同 GrowthChronicle。

**5 分标准**：
1. `GoalWorldGraph` 同步到 PostgreSQL 表
2. 与现有 `KnowledgeNode` / `UserNodeStatus` 表关联
3. Redis 作为热缓存，PG 作为持久存储
4. 支持跨 session 的图状态恢复

**具体差距**：
- 无 PG 持久化
- 节点状态与 `UserNodeStatus` 表未关联
- TTL 过期风险

**涉及模块**：`backend/app/signals/goal_world_graph.py`, `backend/app/models/galaxy.py`

---

### P1-2.3：ConsentTracker 内存存储（同 P0-1.6）

已在 P0-1.6 中详细描述。

---

### P1-2.4：SpineSnapshot 无统一实现

**现状**：代码库中存在多种快照机制（`AuroraStateSnapshot` PG 模型、`CardSnapshotService`、`ReportSnapshotStore`），但没有统一的 Spine 管道快照。`session_end`/`daily`/`goal_checkpoint`/`pre_ttl_expiry` 四个关键快照点没有标准化实现。

**5 分标准**：
1. 定义 `SpineSnapshot` 数据模型（包含 user_id, goal_id, active_states, recent_policy_decisions, active_directives, pending_outcomes）
2. 在四个关键节点自动生成快照
3. 快照持久化到 PG
4. Redis 状态过期时从快照恢复（Rehydration）
5. 恢复过程产生 `ReturnCaseFile` 供用户确认

**具体差距**：
- 无统一快照模型
- 四个快照点无标准化触发
- 无自动恢复机制

**涉及模块**：`backend/app/signals/spine_orchestrator.py`, `backend/app/signals/stale_state_guard.py`

---

## P1-3：Skill 和 Learning 完善

### P1-3.1：SkillEntry 缺少 contraindications 字段

**现状**：`DistilledStrategy`（Aurora Pydantic 模型）有 `contraindications` 和 `retract_if`，但 Spine 管道的核心 `SkillEntry` dataclass 没有这些字段。这意味着技能提取后无法表达"什么情况下不适用"。

**5 分标准**：
1. `SkillEntry` 添加 `contraindications: list[str]` 和 `retract_if: list[str]` 字段
2. `SkillExtractionService.scan_for_extractions()` 在提取时从 PolicyEffectEntry 的负反馈中推导 contraindications
3. `SkillLifecycleManager.find_applicable_skills()` 在匹配时检查 contraindications 并排除不适用技能
4. `SkillLifecycleManager.auto_deprecate_check()` 在 retract_if 条件满足时自动废弃

**具体差距**：
- SkillEntry 缺字段
- 提取时未推导禁忌
- 匹配时未检查禁忌

**涉及模块**：`backend/app/signals/types.py` (SkillEntry), `backend/app/signals/skill_extraction.py`, `backend/app/signals/skill_lifecycle.py`

---

### P1-3.2：StrategyBelief 缺少 counter_evidence 字段

**现状**：`StrategyBelief` 使用 Bayesian Beta 分布（alpha/beta）融合所有证据，但不单独追踪反证。这意味着无法区分"证据不足所以不确定"和"有正面也有反面证据所以不确定"。

**5 分标准**：
1. `StrategyBelief` 添加 `counter_evidence: list[str]` 字段
2. `LearningBase.update_belief()` 在 attribution 为 "insufficient" 或 "harmful" 时追加反证
3. 反证列表有上限（≤10 条），超限时保留最新的
4. `compute_strategy_ranking()` 在信心接近时优先选择反证少的策略
5. 反证内容可被用户查看（通过 GrowthChronicle 或透明面板）

**具体差距**：
- StrategyBelief 缺字段
- update_belief 不区分正反证
- 排名不考虑反证

**涉及模块**：`backend/app/signals/learning_base.py`, `backend/app/signals/types.py`

---

### P1-3.3：SkillCandidate 不作为独立类型存在

**现状**：`SkillExtractionService.scan_for_extractions()` 直接创建 `SkillEntry`。没有中间的 `SkillCandidate` 阶段，无法区分"待验证的候选技能"和"已验证的正式技能"。

**5 分标准**：
1. 定义 `SkillCandidate` 类型（包含 candidate_id, source_episodes, proposed_skill, validation_status, created_at）
2. `SkillExtractionService` 先产出 `SkillCandidate`
3. `SkillLifecycleManager` 管理 candidate→personal_shadow→personal_live 的完整生命周期
4. 候选技能有验证期（如 7 天或 10 次使用），不达标自动废弃

**具体差距**：
- 无 SkillCandidate 类型
- 无验证期
- 生命周期跳跃

**涉及模块**：`backend/app/signals/types.py`, `backend/app/signals/skill_extraction.py`, `backend/app/signals/skill_lifecycle.py`

---

## P1-4：任务系统完善

### P1-4.1：缺少 PAUSED 任务状态

**现状**：`TaskStatus` 枚举只有 PENDING、IN_PROGRESS、STUCK、COMPLETED、ABANDONED。用户在任务中暂停（如临时有事离开 30 分钟）没有专属状态，只能保持 IN_PROGRESS 或手动 ABANDONED。

**5 分标准**：
1. `TaskStatus` 添加 `PAUSED` 枚举值
2. `TaskService` 添加 `pause()` / `resume()` 方法
3. 暂停时记录暂停时间，恢复时计算实际执行时长（扣除暂停时间）
4. 暂停超过阈值（如 4 小时）自动提示用户是否放弃或重排
5. 移动端任务执行屏幕支持暂停/恢复按钮

**具体差距**：
- 枚举缺值
- 服务缺方法
- 移动端缺 UI

**涉及模块**：`backend/app/models/task.py`, `backend/app/services/task_service.py`, `mobile/lib/features/task/`

---

### P1-4.2：缺少任务恢复工作流

**现状**：任务被 ABANDONED 后无结构化恢复路径。用户想重试时只能创建新任务，丢失与原任务/计划节点的关联。

**5 分标准**：
1. `TaskService` 添加 `restore(task_id)` 方法：将 ABANDONED→PENDING 并保留原任务关联
2. 恢复时保留原 `why_this_task`、`bound_nodes`、`materials_protocol`
3. 恢复卡在 UI 中展示（类似返回恢复卡）："你想恢复之前的任务吗？"
4. 恢复事件写入 CausalTrace

**具体差距**：
- 无 restore 方法
- 无 UI

**涉及模块**：`backend/app/services/task_service.py`, `mobile/lib/features/task/`

---

## P1-5：Goal 系统完善

### P1-5.1：GoalWorldGraph 无数据库持久化

已在 P1-2.2 中详细描述。

---

### P1-5.2：多目标 UI 缺失

**现状**：`MultiGoalArbitrator` 后端已完整实现（最多 5 个活跃目标，加权优先级），但移动端无对应的多目标管理 UI。`GoalArbitrationCard` 存在于聊天中但无独立的"目标管理"屏幕。

**5 分标准**：
1. 存在独立的多目标管理屏幕，显示所有活跃目标及其优先级
2. 用户可手动调整优先级（覆盖系统判断）
3. 用户可暂停/归档/删除目标
4. 目标间时间冲突时显示可视化解释
5. 目标切换时首页内容相应更新

**具体差距**：
- 无管理屏幕
- 无手动优先级调整
- 无目标生命周期管理 UI

**涉及模块**：`mobile/lib/features/home/`, `mobile/lib/features/chat/presentation/widgets/goal_arbitration_card.dart`

---

### P1-5.3：非考试目标类型的检测深度不足

**现状**：`ExamRescueDetector` 对考试目标的 FirstMinuteAha 检测很成熟（deadline_days、path_mode、subject）。但对项目交付、求职面试、健身习惯等目标类型的首次检测缺乏同等深度的模式匹配。

**5 分标准**：
1. `GoalTypeAdapter` 或新检测器对 6 种目标类型均有首次消息模式匹配
2. 每种类型有对应的 DomainPack 激活逻辑
3. 非考试类型的 FirstMinuteAha 体验与考试类型一致

**具体差距**：
- 仅考试类型有深度检测
- 非考试类型依赖通用的 GoalTypeAdapter 映射

**涉及模块**：`backend/app/signals/exam_rescue_detector.py`, `backend/app/signals/goal_type_adapter.py`, `backend/app/signals/domain_pack.py`

---

## P1-6：Source 资料生命周期

### P1-6.1：无正式的资料生命周期管理

**现状**：资料只有 hard delete（通过 `DocumentChunk` cascade）。无归档操作、无权限撤销、无 TTL 自动过期、无冷存储迁移。

**5 分标准**：
1. 定义 `SourceLifecycle` 状态机：active → archived → deleted
2. 归档操作：保留元数据和索引，暂停在检索中使用
3. 权限撤销：共享资料的访问权可在共享后被收回
4. 目标结束后关联资料自动降级（不自动删除，但优先级降低）
5. 资料 TTL 策略可配置（如目标完成后 90 天自动归档）
6. 用户可在 Source Tray 或文档库中管理资料生命周期
7. 删除操作有确认步骤和审计日志

**具体差距**：
- 无归档操作
- 无权限撤销流
- 无自动降级
- 无 TTL 策略
- 无 UI 管理

**涉及模块**：`backend/app/services/document_service.py`, `backend/app/models/document_chunks.py`, `mobile/lib/features/documents/`

---

## P1-7：审计与合规

### P1-7.1：管理操作、策略发布、实验推广无结构化审计

**现状**：`AuthAuditService` 和 `SecurityMonitor` 覆盖了登录和数据访问审计。但以下关键操作无审计：
- 策略变更（PolicyEngine 规则修改）
- 实验推广（shadow→live）
- DomainPack/Skill 上架/下架
- 数据导出请求
- Kill Switch 模式变更
- 用户数据删除

**5 分标准**：
1. 所有上述操作写入 `AdminAuditLog` 表
2. 包含：操作者、操作类型、目标对象、变更前后状态、时间戳、原因
3. 有 REST API 查询审计日志（仅管理员）
4. Grafana 仪表盘展示审计事件趋势
5. 异常操作（如批量删除、非工作时间操作）触发告警

**具体差距**：
- 审计事件类型不完整
- 无查询 API
- 无仪表盘
- 无异常检测

**涉及模块**：`backend/app/core/auth_audit_service.py`, `backend/app/core/security_monitor.py`, `backend/app/models/audit_log.py`

---

### P1-7.2：发布审批工作流缺失

**现状**：`KillSwitchReadinessService` 输出 `FeatureReadiness` 报告供人工审核，但无正式的多方审批工作流。`SkillShareModerationQueue` 使用 mock_approver。

**5 分标准**：
1. 高风险操作（策略变更、实验推广、Marketplace 上架）需审批
2. 审批工作流：提交→审核→批准/拒绝→执行→记录
3. 至少两级：自动门槛检查 + 人工审核（高风险项）
4. 审批记录写入审计日志
5. `SkillShareModerationQueue` 替换 mock_approver 为真实审核管道

**具体差距**：
- 无审批工作流引擎
- mock_approver 代替真实审核
- 无审批记录

**涉及模块**：`backend/app/services/kill_switch_readiness_service.py`, `backend/app/services/skill_share/service.py`

---

## P1-8：紧急与恢复

### P1-8.1：危机模式不是正式的 FSM 状态

**现状**：`SpineOrchestrator.detect_crisis_mode()` 是方法调用，设置 Redis 键 `spine:crisis:{user_id}:latest`。但没有正式的 FSM 状态转换（NORMAL→CRISIS→RECOVERY→NORMAL），没有进入/退出危机的标准化钩子。

**5 分标准**：
1. 定义 `CrisisState` 枚举（NORMAL, WARNING, CRISIS, RECOVERING）
2. 进入/退出危机有标准化条件
3. 危机期间自动触发的策略变更被记录
4. 危机状态变化事件写入 EventBus
5. 危机模式有 Prometheus 指标（当前处于危机的用户数、平均持续时间）
6. 有降级路径：危机解除后自动恢复正常策略

**具体差距**：
- 非 FSM
- 无标准化钩子
- 无事件发布
- 无指标

**涉及模块**：`backend/app/signals/spine_orchestrator.py`, `backend/app/signals/directive_quota.py`

---

### P1-8.2：缺少统一的热/温/冷状态分层架构

**现状**：每个组件独立管理自己的状态生命周期（Redis TTL 各不同）。没有一个统一的状态分层策略来决定"什么数据应该在热层（Redis）/温层（PG）/冷层（S3/归档）"。

**5 分标准**：
1. 定义 `StateTier` 策略：热层（<24h TTL, Redis）、温层（<90d, PG）、冷层（>90d, 归档存储）
2. 每个 StateEntry 在创建时被分配 tier
3. 存在数据迁移任务：热→温→冷 按 TTL 自动流转
4. 冷层数据在需要时可由用户请求恢复（Rehydration）
5. 有成本指标：各层数据量、迁移频率

**具体差距**：
- 无统一分层策略
- 无自动迁移
- 无冷存储集成

**涉及模块**：`backend/app/signals/state_register.py`, `backend/app/signals/causal_trace_store.py`, `backend/app/core/`

---

### P1-8.3：Blue-green 部署脚本缺失

**现状**：K8s 配置（blue/green kustomization）和 `BlueGreenHealthCheck` Python 类存在。但 CI 调用的 `scripts/deploy-prod.sh` 脚本不在代码库中。

**5 分标准**：
1. 部署脚本存在且可被 CI 调用
2. 支持蓝绿切换、健康检查、观察期（≥5min）、自动回滚
3. 回滚决策基于 `BlueGreenHealthCheck.evaluate_promotion()` 的结果
4. 部署事件记录到审计日志
5. 部署状态在 Grafana 中可见

**具体差距**：
- 部署脚本缺失
- 自动回滚未实现

**涉及模块**：`scripts/deploy-prod.sh`, `.github/workflows/deploy-prod.yml`

---

# 3. P2：体验显著提升

## P2-1：移动端 UX 完善

### P2-1.1：情绪自适应 UI 原始

**现状**：`CognitiveStateProvider` 可检测包含 'tired' 或 'fatigue' 的认知状态。`EmotionVisualBlendProvider` 存在但作用有限。没有根据压力/疲劳检测实质性简化 UI 的机制。

**5 分标准**：
1. 检测到高疲劳/压力时，UI 自动切换到低负荷模式：
   - 减少可见卡片数量
   - 简化导航选项
   - 降低信息密度
   - 推迟非紧急提醒
   - 任务推荐更保守（更短时长、更低难度）
2. 用户在设置中可开启/关闭自适应 UI
3. 模式切换有平滑过渡动画
4. 低负荷模式下不丢失功能，只是重新组织信息层级

**具体差距**：
- 无 UI 简化逻辑
- 无信息密度调整
- 无用户设置开关

**涉及模块**：`mobile/lib/features/home/presentation/providers/cognitive_state_provider.dart`, `mobile/lib/features/home/presentation/providers/emotion_visual_blend_provider.dart`, `mobile/lib/core/design/`

---

### P2-1.2：成长纪事非叙事体验

**现状**：成长洞察以结构化卡片形式呈现（`WeeklyGrowthNarrativeCard`、`InsightHubCard`、`RecentInsightsCard`）。但没有沉浸式的"纪事"叙事体验（按时间线讲述用户成长故事）。

**5 分标准**：
1. 存在 `GrowthChronicleScreen`：按时间线展示用户确认过的成长洞察
2. 叙事有章节感：里程碑→转折点→发现的模式→用户反思
3. 用户可编辑/隐藏/确认每一条
4. 非 AI 生成的模板化文本（基于聚合数据的安全叙述）
5. 支持按目标/时间段筛选
6. 返回用户首次打开时呈现"你不在时的变化"摘要

**具体差距**：
- 无时间线叙事屏幕
- 无章节结构
- 无编辑/隐藏交互

**涉及模块**：`mobile/lib/features/insights/`, `backend/app/signals/growth_chronicle.py`

---

### P2-1.3：通知卡片缺召回价值显式显示

**现状**：`UnifiedNotificationCard` 显示通知类型和操作按钮。但不解释"为什么现在提醒你这件事"。用户看不到召回背后的价值判断。

**5 分标准**：
1. `UnifiedNotification` 模型添加 `recall_reason: str` 和 `recall_value: str` 字段
2. 通知卡片渲染时显示简短的召回理由："你 3 天前上传了计网课件，还没开始诊断。现在只需 12 分钟。"
3. `RecallNotificationBuilder` 在构建时填充召回理由
4. 用户可反馈"这个提醒有用/没用"，反馈进入 Outcome 回流

**具体差距**：
- 模型缺字段
- 卡片不显示理由
- 无反馈闭环

**涉及模块**：`mobile/lib/features/notification_center/`, `backend/app/signals/recall_notification.py`

---

### P2-1.4：设置分散在三处，无统一入口

**现状**：用户设置分布在 `features/user/`（25 个屏幕）、`features/memory/`（记忆设置）、`features/settings/`（透明度设置）。没有统一的设置仪表盘将记忆控制、社群智能、资料权限、关系偏好集中在一起。

**5 分标准**：
1. 存在 `UnifiedSettingsScreen` 作为单一入口
2. 按类别组织：账户安全、AI 行为（Aurora 偏好）、隐私与数据（记忆/社群/资料）、通知、外观
3. 记忆控制（六项独立开关）与用户画像透明面板在同一流程中
4. 社群智能 opt-out 可直接在设置中切换
5. 关系偏好（少分析我/直接安排我/多解释原因/不用压力提醒）可在一个地方配置

**具体差距**：
- 无统一入口
- 关系偏好无独立 UI

**涉及模块**：`mobile/lib/features/user/presentation/screens/unified_settings_screen.dart`, `mobile/lib/features/memory/presentation/screens/memory_settings_screen.dart`, `mobile/lib/features/settings/`

---

### P2-1.5：集中式无障碍设置面板缺失

**现状**：无障碍功能嵌入在各个 widget 中（`Semantics` widget、`GalaxyAccessibilityService`）。但用户没有一个集中的无障碍设置面板来调整字体缩放、对比度、减少动效、屏幕阅读器偏好。

**5 分标准**：
1. 存在 `AccessibilitySettingsScreen`
2. 用户可调整：字体缩放（独立于系统设置）、高对比度模式、减少动效（覆盖系统设置）、触觉反馈强度
3. 设置持久化到本地存储并在下次启动时生效
4. 银河星空图有专门的无障碍模式（简化视觉、增大触摸目标）

**具体差距**：
- 无集中设置面板
- 字体缩放不可独立调整
- 无障碍依赖系统默认

**涉及模块**：`mobile/lib/features/settings/`, `mobile/lib/features/galaxy/data/services/galaxy_accessibility_service.dart`

---

## P2-2：社群系统完善

### P2-2.1：社群资源质量无评分/排名机制

**现状**：`SharedResource` 模型支持多态资源共享。`CommunitySignalDetector` 可推荐资源（"highly_rated_by_cohort"/"frequently_used"）。但没有实际的质量评分算法——没有基于使用效果、用户反馈、适用范围的排名。

**5 分标准**：
1. 资源质量分基于：采纳后任务完成率、用户显式反馈（有用/无用）、被引用次数、资料本身质量分
2. 质量分定期重新计算（Celery 定时任务）
3. 低质量资源自动降权或标记
4. 资源质量趋势可追踪
5. 用户可按质量排序浏览社群资源

**具体差距**：
- 无质量评分算法
- 无定期重算
- 无自动降权
- 无按质量排序

**涉及模块**：`backend/app/services/community_service.py`, `backend/app/signals/community_signal.py`, `backend/app/models/community.py`

---

### P2-2.2：社群错误聚合阈值偏低

**现状**：`community_error_aggregation_service.py` 使用 `MIN_USERS_FOR_AGGREGATION = 3`。这意味着 3 个用户犯同样错误就产生聚合信号——可能反推个人。

**5 分标准**：
1. `MIN_USERS_FOR_AGGREGATION` 提高到 ≥5（与 `PrivacyPreservingCommunityEngine` 三层隐私的 suppressed 阈值一致）
2. 聚合统计加上拉普拉斯噪声后再输出
3. 输出带有隐私保护等级标记
4. 用户可查看"此洞察如何产生"的隐私高层解释

**具体差距**：
- 阈值偏低
- 无噪声注入
- 无隐私等级标记

**涉及模块**：`backend/app/services/community_error_aggregation_service.py`, `backend/app/signals/privacy_community_intelligence.py`

---

## P2-3：召回系统完善

### P2-3.1：召回仅限于 4 个确定性触发器

**现状**：`RecallOpportunityDetector` 仅有 4 个硬编码触发器：undigested_material、task_not_started、task_missed、pre_exam_silence。没有基于学习内容衰减、用户行为模式、或预测性重参与评分的触发器。

**5 分标准**：
1. 增加基于知识衰减的召回：节点上次练习后超过推荐间隔
2. 增加基于行为模式的召回：用户通常在某个时段活跃但今天未出现
3. 增加基于目标进度的召回：目标推进速度低于预期
4. 召回机会有 `value_score` 字段：基于目标影响 × 成功概率 × 时效性
5. 多个召回机会按 value_score 排序，只推送最高的（受 DAILY_CAP 限制）

**具体差距**：
- 仅 4 个触发器
- 无 value_score 排序
- 无知识衰减触发器
- 无行为模式触发器

**涉及模块**：`backend/app/signals/recall_opportunity.py`, `backend/app/signals/recall_notification.py`

---

## P2-4：i18n 完善

### P2-4.1：部分 widget 混合使用运行时检测和 ARB

**现状**：大量 widget 使用 `I18nService.instance.isChinese ? '中文' : 'English'` 模式。约 128 个文件、~459 处硬编码字符串。虽然功能正常，但这增加了翻译维护成本，且不符合 Flutter i18n 最佳实践。

**5 分标准**：
1. 所有用户可见字符串通过 ARB 文件定义
2. 编译时可检测缺失翻译
3. 不再有 `isChinese ? '中文' : 'English'` 内联模式
4. ARB 文件覆盖率 ≥98%

**具体差距**：
- ~128 文件有内联双语字符串
- 无编译时缺失翻译检测

**涉及模块**：`mobile/lib/` (128 个文件), `mobile/lib/l10n/`

---

# 4. P3：锦上添花

## P3-1：高级稳定性

### P3-1.1：无 Saga/补偿事务模式

**现状**：事件总线有 DLQ + 重试机制。但没有跨服务的 Saga 模式来处理分布式事务（如"创建计划+分配任务+更新图谱+发通知"中途失败时的补偿）。

**5 分标准**：
1. 关键跨服务操作使用 Saga 模式编排
2. 每个步骤有对应的补偿操作
3. Saga 执行状态可查询
4. 失败的 Saga 可手动重试或取消
5. Saga 仪表盘展示执行历史和成功率

**涉及模块**：`backend/app/core/event_bus.py`, `backend/app/orchestration/`

---

### P3-1.2：无 Toxiproxy 集成

**现状**：混沌工程通过自定义 `ChaosTestRunner` + Go 网关的 `ChaosGuard` 中间件实现。没有使用 Toxiproxy 进行网络层故障注入。

**5 分标准**：
1. 开发/ staging 环境集成 Toxiproxy 进行网络层混沌测试
2. 覆盖场景：Redis 延迟/断开、DB 连接池耗尽、gRPC 超时、MinIO 不可用
3. 每种场景有验证预期降级行为的测试
4. CI 中定期运行（如每周）

**涉及模块**：`docker-compose.yml`, `backend/tests/chaos/`, `.github/workflows/chaos-drill.yml`

---

### P3-1.3：无正式长期存储归档策略

**现状**：所有数据生命周期管理依赖 Redis TTL 和 PostgreSQL 的自然增长。没有 S3/Glacier 冷存储集成，没有数据库分区策略，没有日志保留策略。

**5 分标准**：
1. 定义数据保留策略：按数据类型/年龄的归档规则
2. CausalTrace 超过 90 天的自动归档到冷存储
3. 日志按保留策略自动轮转
4. PostgreSQL 大表（chat_messages, events）按时间分区
5. 归档数据在需要时可恢复（有恢复 SLA）

**涉及模块**：`docker-compose.prod.yml`, `backend/app/core/`, `monitoring/`

---

## P3-2：全局优化

### P3-2.1：无自动化 SLO 违规响应

**现状**：7 项 SLO 告警为 P2（通知性），无自动响应。

**5 分标准**：
1. SLO 违规时自动触发分级响应：
   - 首次违规：记录+通知
   - 持续 5 分钟：自动降级非关键功能
   - 持续 15 分钟：触发 P1 告警+自动扩容/切换
2. 响应记录到 incident trace
3. 有事后复盘报告自动生成

**涉及模块**：`monitoring/sparkle_t6_slo_alerts.yml`, `backend/app/signals/safety_degradation.py`

---

### P3-2.2：服务端弱网支持极低

**现状**：弱网处理几乎全部依赖 Flutter 客户端的出站队列。服务端不做网络质量检测，不做自适应响应聚合。

**5 分标准**：
1. Go Gateway 检测 WebSocket 连接质量（RTT、丢包率）
2. 弱网时自动降低消息频率、压缩 payload、推迟非关键推送
3. 连接恢复后自动重放错过的消息
4. 弱网事件记录到 metrics

**涉及模块**：`backend/gateway/internal/handler/websocket_proxy.go`, `mobile/lib/core/offline/`

---

### P3-2.3：高并发压力测试缺失

**现状**：未发现针对考试前高峰、群体活动的高并发压力测试。

**5 分标准**：
1. 存在 Locust/k6 压力测试脚本
2. 模拟场景：500 并发用户同时聊天、100 人同时上传资料、群体事件触发大量通知
3. 压力测试在 CI 中定期运行
4. 有性能基线，回归时告警

**涉及模块**：`tests/load/`, `.github/workflows/`

---

## P3-3：长期研究能力

### P3-3.1：ResearchDatasetBuilder 无 API 端点

**现状**：`ResearchMode.ResearchDatasetBuilder` 可构建脱敏数据集，但无 API 端点触发。

**5 分标准**：
1. 管理员 API `/research/datasets` 支持创建、查看、下载脱敏数据集
2. 数据集包含版本、筛选条件、样本量、匿名化方法元数据
3. 下载有审计日志
4. 数据集不包含未确认洞察、伙伴私密观察、原始资料内容

**涉及模块**：`backend/app/signals/research_mode.py`, `backend/app/api/v1/`

---

### P3-3.2：ContinuousImprovementLoop 未持久化运行

**现状**：`ContinuousImprovementLoop` 是内存对象，非持久化服务。

**5 分标准**：
1. 作为 Celery Beat 定时任务运行
2. 提案和结论持久化到 PG
3. 改进效果可追踪（改进前后指标对比）
4. 仪表盘展示改进管道状态

**涉及模块**：`backend/app/signals/research_mode.py`, `backend/app/core/celery_schedule.py`

---

### P3-3.3：旧版 v1 代码与 v2 共存

**现状**：`research_grade.py` 中的 `CounterfactualEngine`、`UserSimulator`、`DomainPackMarketplace` 被 `__init__.py` 继续导出，与 v2 实现共存。这造成混淆：新代码该用哪个？

**5 分标准**：
1. v1 代码标记 `@deprecated` 并在文档中说明迁移路径
2. 所有生产管道切换到 v2 实现
3. v1 仅在测试中保留用于回归对比
4. `__init__.py` 优先导出 v2，v1 加 `_v1` 后缀

**涉及模块**：`backend/app/signals/research_grade.py`, `backend/app/signals/__init__.py`

---

# 5. 总结：从当前状态到完全体的路径

## 5.1 工作量估计

| 优先级 | 条目数 | 估计工作量 | 累计通过率变化 |
|--------|--------|-----------|----------------|
| P0 | 9 | 大型（需要架构决策+新 API+DB 变更） | Critical 100%→100%, Core 75%→85% |
| P1 | 15 | 中大型（需要新功能+DB 迁移+测试） | Core 85%→93%, Experience 70%→85% |
| P2 | 10 | 中型（主要是移动端 UI + 后端完善） | Experience 85%→92%, Research 33%→55% |
| P3 | 9 | 中小型（基础设施+优化） | Research 55%→80%, Infra 60%→85% |

## 5.2 建议实施顺序

```
Phase 1 (P0): P4 管道接入 + 权限隔离 + CRDT 同步
  → 解决阻塞项，打通研究级护城河

Phase 2 (P1): 定时调度 + 数据持久化 + Skill/Learning 完善 + 任务/Goal/Source 补充
  → Core 和 Experience 通过线达标

Phase 3 (P2): 移动端 UX + 社群系统 + 召回 + i18n
  → 用户体验达到愿景标准

Phase 4 (P3): Saga/混沌/归档/SLO响应/压测/研究工具
  → 长期稳定性和竞争力
```

## 5.2.1 Phase 2 Closeout Update — 2026-05-03

Phase 2 integration is now represented on `codex/phase2-integration-2026-05-02`.

Completed or integrated:
- TASK-002 paused/resume UI
- KG-005 error pattern → task template flow
- KG-009 why-this-today priority reasoning
- GOAL-012 strategy migration + goal creation wizard
- COM-011 similar goal pursuers + community resource quality badges
- Source lifecycle badge + TASK-014 directive audit UI
- A-003 i18n batch 2 cleanup
- A-006 gateway coverage expansion
- A-007 Flutter core-service test additions
- K/AS/AT/AX/I18N rule guard repair

Verification status:
- Rule guards: `64/64` passed.
- Tech-debt budget: passed.
- Backend contract focused rerun: `11 passed`.
- Gateway targeted race rerun for failed packages: passed.
- Focused P2 Flutter widgets: passed.
- Full Flutter suite: still requires environment/baseline cleanup because local IsarCore download/runtime failures and existing smoke-test drift block a clean run.

Conclusion: mark the Phase 2 functional items as integrated, with final release merge gated on shared-worktree ownership review and Flutter environment/full-suite stabilization.

## 5.3 完全体达标后的状态

当所有 P0-P3 条目完成后：
- Critical 项：10/10 达 5 分
- Core 项：93%+ 达 4+ 分（超过 90% 门槛）
- Experience 项：92%+ 达 4+ 分（超过 85% 门槛）
- Research/P4 项：80%+ 达 3+ 分（达到 80% 门槛）
- Infra/Governance 关键项：85%+ 达 4+ 分

**全部四条通过线达标。一票否决项 0 触发。Sparkle 达到完全体。**

---

> 本文档与 `SPARKLE_COMPLETE_EXPERIENCE_CHECKLIST_v1.0.md`（验收清单）配套使用。
> 验收清单定义"什么是满分"；本文档定义"如何从现状到满分"。
