# Sparkle Roadmap v3 — 从当前状态到生产部署

> **版本**: v3.0
> **日期**: 2026-04-28
> **状态**: ACTIVE BLUEPRINT — 所有后续工作朝此收敛
> **目标**: 产品正式部署服务器上线
> **前置文档**: 愿景验收清单 (200+ 项, 20 章节), Causal Control OS Final, Full Vision v1, Aurora Roadmap v2.2
> **验收标准**: 愿景验收清单 Critical 项 100% 达 4+ 分, Core 项 90% 达 4+ 分

---

## 当前项目真实状态 (2026-04-28 基线)

### 已完成 ✅

| 领域 | 状态 | 证据 |
|------|------|------|
| Aurora Stages 4-40 | 全部 landed | Phase I Exit Gate 通过, 53 治理规则 |
| 33 Aurora Kill Switches | 全部 live | 76/76 kill switch tests 通过, activation smoke PASS |
| Signal-to-Action Spine | 9/9 directive types | 17 production files 集成, orchestrator→response_builder→planning_workflow 全链路 |
| 6 神性时刻 Flutter UI | 全部 live | GrowthCard, SpineReceiptCard, ContextReceiptBar, StaleRecoveryCard, StrategyInterventionCard, CommunityInsightCard — 全部 wired into chat_screen.dart |
| Flutter 核心功能 | 全部实现 | Galaxy, Task, Community, Source Tray, Aurora Status Band, Causal Timeline, Settings/Memory, Offline (Isar+Outbox+CRDT), Accessibility |
| Go Gateway | 生产级 | 16 中间件, JWT+黑名单+fail-closed, 分布式限流, 安全头, WebSocket 编排 |
| Python AI Engine | 生产级 | LangGraph FSM, Dual-Core Router, LLM 9 级路由, EventBus, 30+ services |
| 测试 | 7,402+ | 6,045 Python + 205 Go + 1,152 Flutter |
| 可观测性栈 | 已部署 | Prometheus, Grafana, Loki, Tempo, Alertmanager, 11 SLO 告警 |
| Card Protocol DB | 迁移存在 | cards, card_edges, task_occurrences, planning_artifacts, intervention_records |
| Error Replan Bridge | 已连接 | EventBus error_created → GalaxyEventConsumer → ErrorReplanBridge, 13 triggering types |
| StateAggregator | 19 _build methods | 连接 context_builder.py → routing_engine.py |
| Offline Mobile | 完整 | Isar DB, Outbox pattern, CRDT, Sync Engine, Network Monitor (13 files) |
| 99 Alembic 迁移 | 存在 | 含 Card Protocol tables |

### 未完成 ❌

| 领域 | 问题 | 优先级 |
|------|------|--------|
| TLS/HTTPS | Nginx 只监听 80, 无 SSL | P0 |
| Sentry | 未初始化, 仅有注释代码 | P0 |
| 24 placeholder secrets | .env.example 中 24 个 "your_xxx" 占位, 无启动校验 | P0 |
| MinIO 硬编码 | settings.py 默认 minioadmin/minioadmin | P0 |
| Flutter API URL | 仅 localhost, 无生产 URL | P0 |
| Grafana 默认密码 | admin/admin | P0 |
| Push JPush 占位 | mobile push_config.dart "YOUR_JPUSH_APPKEY" | P0 |
| Email 服务 | SMTP 全空, EMAIL_ENABLED=false | P1 |
| 3 Breakpoints 未关闭 | push time-only, cognitive_adjustments text-only, no verification loop | P1 |
| Spine 深度 | 多项 SPINE-* 验收项在 2-3 分, 需达 4 分 | P1 |
| P4 研究平台 | 几乎未开始 (Evaluation-grade logging, Counterfactual, Simulation Lab) | P2 |
| Outcome 回流闭环 | 部分 module 有 actual_outcome 记录, 但未形成 Attribution→Model Update 链 | P1 |
| Skill Lifecycle | candidate→shadow→live pipeline 存在, 但 cohort/system 晋升未实现 | P2 |
| DomainPack | ExamSprint 存在, 其他领域包未实现 | P2 |
| 蓝绿部署 | docker-compose.prod.yml 存在, 但蓝绿切换脚本未实现 | P1 |
| 混沌测试 | chaos_guard.go 存在, 但 Toxiproxy 集成未完成 | P2 |

---

## Phase 0: 生产基础设施硬化 (第 1-2 周)

**目标**: 消除所有 P0 阻塞项, 让系统能安全部署到生产服务器

### 0.1 TLS/HTTPS 终止

**问题**: Nginx 只监听 80, 无 443/SSL; gRPC 生产模式已有 TLS 校验但无证书挂载路径

**任务清单**:
- [ ] **T0.1.1** `nginx/nginx.conf` — 添加 443 server block, 配置 SSL 证书路径, HTTP→HTTPS 重定向
- [ ] **T0.1.2** `docker-compose.prod.yml` — 挂载 SSL 证书 volume, 暴露 443 端口
- [ ] **T0.1.3** `scripts/ssl/` — 创建证书生成脚本 (Let's Encrypt certbot + self-signed for dev)
- [ ] **T0.1.4** `backend/app/config/settings.py` — 添加 CORS allowed origins 的 HTTPS 生产域名
- [ ] **T0.1.5** `mobile/lib/core/constants/api_constants.dart` — 添加生产 HTTPS base URL, 从 String.fromEnvironment 读取

**验收**: `curl https://sparkle.example.com/api/v1/health` 返回 200; gRPC TLS 握手成功

### 0.2 崩溃报告 (Sentry)

**问题**: Sentry SDK 仅注释代码, 无初始化

**任务清单**:
- [ ] **T0.2.1** `backend/app/core/sentry.py` — 新建 Sentry 初始化模块
- [ ] **T0.2.2** `backend/app/main.py` — startup 时调用 sentry init
- [ ] **T0.2.3** `backend/app/services/agent_grpc_service.py` — gRPC server 启动时 init sentry
- [ ] **T0.2.4** `backend/.env.example` — 添加 `SENTRY_DSN=`, `SENTRY_ENVIRONMENT=`, `SENTRY_TRACES_SAMPLE_RATE=`
- [ ] **T0.2.5** `backend/app/config/settings.py` — 添加 Sentry settings 字段
- [ ] **T0.2.6** `mobile/` — Flutter Sentry plugin 初始化 (sentry_flutter pubspec + main.dart init)

**验收**: 手动触发异常后 Sentry dashboard 收到 event; Python/Go/Flutter 三层错误都上报

### 0.3 秘钥启动校验

**问题**: 24 个 placeholder secrets, 无启动校验

**任务清单**:
- [ ] **T0.3.1** `backend/app/config/settings.py` model_post_init — 添加 production 环境下关键 secret 非空校验:
  - SECRET_KEY, JWT_SECRET, POSTGRES_PASSWORD, REDIS_PASSWORD
  - 至少一个 LLM API_KEY (Qwen/DeepSeek/Zhipu 之一)
  - INTERNAL_API_KEY
- [ ] **T0.3.2** `backend/app/config/settings.py` — MinIO 默认值改为空字符串, 生产环境必须设置
- [ ] **T0.3.3** `backend/.env.example` — 所有 placeholder 添加注释说明和推荐最小值
- [ ] **T0.3.4** `scripts/check_production_secrets.py` — 新建预部署校验脚本

**验收**: `python scripts/check_production_secrets.py` 在 placeholder 未替换时 exit 1; 生产启动时 ValueError

### 0.4 基础设施安全加固

**任务清单**:
- [ ] **T0.4.1** `docker-compose.prod.yml` — Grafana admin password 从必填 env 读取, 无 fallback
- [ ] **T0.4.2** `mobile/lib/core/constants/push_config.dart` — 移除 "YOUR_JPUSH_APPKEY" 硬编码, 改为 String.fromEnvironment
- [ ] **T0.4.3** `docker-compose.prod.yml` — MinIO credentials 从 env 读取, 无默认值
- [ ] **T0.4.4** `backend/app/config/settings.py` — 添加 PRODUCTION_URL setting 用于 Flutter deeplink
- [ ] **T0.4.5** `monitoring/grafana/provisioning/` — 预配置 8 个 dashboard (Product, Spine, Aurora, RAG, Learning, Infra, Cost, P4)

**验收**: `docker compose -f docker-compose.prod.yml config` 验证所有 secret 必填; 无硬编码凭据

### 0.5 邮件服务配置

**任务清单**:
- [ ] **T0.5.1** `backend/app/services/email_service.py` — 确认 email 发送逻辑完整
- [ ] **T0.5.2** `backend/.env.example` — 添加 SMTP 配置说明 (推荐 Mailgun/Resend/SendGrid)
- [ ] **T0.5.3** `backend/app/config/settings.py` — EMAIL_ENABLED 生产环境默认 false, 需手动开启

**验收**: 设置 SMTP 后能发送测试邮件; 未配置时优雅降级

---

## Phase 1: 核心闭环关闭 (第 2-5 周)

**目标**: 关闭 3 个 open breakpoints, 补齐 Outcome 回流链, 完成 Card Protocol 迁移

### 1.1 Breakpoint #5: Push 通知从 time-only 升级为 behavior-driven

**现状**: 推送仅基于时间触发, 不考虑用户行为、目标状态、知识瓶颈
**目标**: 推送基于 RecallOpportunity (NUDGE-001 ~ NUDGE-010)

**任务清单**:
- [ ] **T1.1.1** `backend/app/services/notification_service.py` — consume_spine_notification_directive() 已存在, 需增强:
  - 从 ActionableStatePacket 读取 deadline_pressure, cognitive_load, affective_pressure
  - 从 PolicyArbitration 读取 RecallOpportunity
  - 替代纯时间触发逻辑
- [ ] **T1.1.2** `backend/app/orchestration/orchestrator.py` — session_end 时生成 RecallOpportunity 并写入 DB
- [ ] **T1.1.3** `backend/app/core/push_scheduler.py` — 新建推送调度器:
  - quiet hours 检查
  - 疲劳保护 (连续无行动降频)
  - 低成本下一步生成
  - value_reason 字段 ("你上次卡在 TCP 三次握手, 试试这个 5 分钟练习?")
- [ ] **T1.1.4** `backend/app/services/jpush_sender_service.py` — 推送内容包含 goal_context + suggested_action
- [ ] **T1.1.5** `mobile/lib/features/notification_center/` — 推送点击跳转到对应 goal/task/recall 上下文
- [ ] **T1.1.6** `backend/tests/unit/test_behavior_driven_push.py` — 新建测试: 时间触发 vs 行为触发 vs 疲劳保护

**验收**: 推送内容含 value_reason + suggested_action; 连续 3 次无行动自动降频; quiet hours 不推送

### 1.2 Breakpoint #6: cognitive_adjustments 从 text 升级为 structured

**现状**: dual_core_router 输出的 cognitive_adjustments 是纯文本描述
**目标**: 结构化 CognitiveAdjustment 对象, 可被下游消费

**任务清单**:
- [ ] **T1.2.1** `backend/app/orchestration/dual_core_router.py` — cognitive_adjustments 从 str 改为 TypedDict/dataclass:
  ```python
  @dataclass
  class CognitiveAdjustment:
      dimension: str  # tone, verbosity, challenge_level, explanation_depth, ...
      value: str | int | float
      reason: str
      evidence: list[str]
      scope: str  # turn, session, sprint
      user_visible: bool
      ttl: str | None
  ```
- [ ] **T1.2.2** `backend/app/orchestration/orchestrator.py` — 消费 CognitiveAdjustment 列表, 传递给 prompt assembly
- [ ] **T1.2.3** `backend/app/orchestration/ux_envelope.py` — PresentationProfile 从 CognitiveAdjustment 生成
- [ ] **T1.2.4** `backend/app/orchestration/prompts.py` — 从结构化调整生成 prompt 参数
- [ ] **T1.2.5** Flutter WebSocket 消息中传递 cognitive_adjustments 结构化数据
- [ ] **T1.2.6** `backend/tests/unit/test_structured_cognitive_adjustments.py` — 新建测试

**验收**: CognitiveAdjustment 可被下游模块直接消费; 结构化字段进入 trace; 用户可见部分有 receipt

### 1.3 Breakpoint #7: Verification Loop — 干预后验证

**现状**: 干预产生后无 outcome 回流验证链
**目标**: 每个干预定义 expected_outcome, 记录 actual_outcome, 进入 Attribution

**任务清单**:
- [ ] **T1.3.1** `backend/app/spine/outcome_tracker.py` — 新建:
  - register_expected_outcome(directive_id, expected: OutcomeVector)
  - record_actual_outcome(directive_id, actual: OutcomeVector)
  - compute_attribution(directive_id) → AttributionResult
  - OutcomeVector 包含: task_completion, learning_gain, goal_progression, user_agency, load, trust, persistence
- [ ] **T1.3.2** `backend/app/orchestration/orchestrator.py` — 在发出 directive 后调用 register_expected_outcome
- [ ] **T1.3.3** `backend/app/orchestration/orchestrator.py` — 在任务完成/失败/用户反馈时调用 record_actual_outcome
- [ ] **T1.3.4** `backend/app/spine/attribution.py` — 新建 Attribution 引擎:
  - attribution_type: effective / insufficient / inconclusive / harmful / needs_confirmation
  - counter_evidence 收集
  - 写入 StrategyBelief 或标记 retraction
- [ ] **T1.3.5** `backend/app/spine/learning_guard.py` — 新建学习守卫:
  - 单次成功/失败不直接变长久结论
  - 需要多个 episode 或低风险标记才可沉淀
- [ ] **T1.3.6** `backend/tests/unit/test_verification_loop.py` — 端到端测试: directive → expected → actual → attribution → learning

**验收**: 每个干预有 expected + actual outcome; attribution 结果写入 trace; StrategyBelief 更新有 evidence 约束

### 1.4 Outcome 回流闭环 — 全系统补齐

**现状**: 部分 module (ErrorReplanBridge, SkillExtraction) 有 outcome 概念, 但未统一
**目标**: 所有 9 类 directive 都有 outcome 回流

**任务清单**:
- [ ] **T1.4.1** 为每个 directive 消费点添加 outcome 记录:
  - ResponseDirective → 聊天反馈/用户纠正
  - ExecutionDirective → 任务完成/失败/卡住
  - PlanDirective → 计划接受/修改/拒绝
  - RetrievalDirective → 资料使用效果/用户排除
  - ModelWriteDirective → 用户确认/拒绝
  - NotificationDirective → 推送打开/忽略/行动
  - UXDirective → 用户交互数据
  - SkillDirective → 策略有效/无效
  - CommunityDirective → 社群反馈
- [ ] **T1.4.2** 统一 outcome 写入 CausalTrace
- [ ] **T1.4.3** Outcome dashboard (Grafana panel): DirectiveApplicationRate, OutcomeFeedbackRate, AttributionRate

**验收**: 9 类 directive 各有至少 1 个 outcome 回流测试; Grafana 可看到指标

### 1.5 Card Protocol 迁移完成

**现状**: 8 张 Card Protocol DB 表存在, 但 Plan/Task 仍用旧模型
**目标**: 关键路径迁移到 Card 模型, 保持向后兼容

**任务清单**:
- [ ] **T1.5.1** `backend/app/services/card_service.py` — 完善 Card CRUD, CardEdge 关系, CardSnapshot 版本
- [ ] **T1.5.2** `backend/app/orchestration/planning_workflow.py` — 新计划生成 Card + CardEdge (同时保留旧 Plan 表写入)
- [ ] **T1.5.3** `backend/app/services/task_service.py` — TaskOccurrence 从 Card 生成
- [ ] **T1.5.4** `backend/app/services/intervention_service.py` — InterventionRecord 记录 Aurora 干预
- [ ] **T1.5.5** Flutter 端适配 Card 模型 (plan_review_card.dart 等)
- [ ] **T1.5.6** 双写期间的一致性校验脚本

**验收**: 新计划同时写入 Card + Plan 表; Card 可追溯到 Plan; TaskOccurrence 正确生成

---

## Phase 2: Causal Control Spine 深化 (第 4-7 周)

**目标**: 愿景验收清单 SPINE-001~SPINE-020 全部达到 4 分

### 2.1 Signal Ranking & Conflict Arbitration

**现状**: 信号排序和冲突仲裁逻辑分散, 无统一引擎
**目标**: 统一 SignalRankingEngine + PolicyArbitrationEngine

**任务清单**:
- [ ] **T2.1.1** `backend/app/spine/signal_ranking.py` — 新建信号排序引擎:
  - 输入: ActionableSignal 列表
  - 排序维度: goal_impact, decision_relevance, urgency, confidence, freshness, contradiction, cost_of_inaction, reversibility, user_visibility, privacy
  - 输出: RankedSignal 列表 (带排序理由)
- [ ] **T2.1.2** `backend/app/spine/policy_arbitration.py` — 新建策略仲裁引擎:
  - 优先级: 安全/隐私 > deadline生存 > 用户显式目标 > 行为证据 > 学习证据 > 资料证据 > 成就信号 > 社群信号
  - 冲突检测: 互斥信号自动标记
  - 仲裁结果: PolicyDecision (含选择理由、被拒绝的候选、置信度)
- [ ] **T2.1.3** `backend/app/spine/state_register.py` — Actionable State Register:
  - 状态词汇表: goal_mode, deadline_pressure, execution_consistency, task_granularity_fit, cognitive_load, affective_pressure, knowledge_bottleneck, transfer_failure, source_relevance, retrieval_risk, model_conflict, strategy_confidence, intervention_effectiveness, relationship_stance, user_agency_preference
  - 每个状态有: value, confidence, scope, ttl, evidence, counter_evidence, can_affect, user_visible
  - 作用域纪律: turn/session/task/day/sprint/goal/domain/relationship/long_term
- [ ] **T2.1.4** `backend/app/orchestration/orchestrator.py` — 主链接入: RawEvent → SignalRanking → PolicyArbitration → StateUpdate
- [ ] **T2.1.5** `backend/app/spine/orphan_detector.py` — 孤儿信号检测: 统计未被消费的高价值信号, 超阈值告警
- [ ] **T2.1.6** Prometheus metrics: signal_to_state_rate, state_to_policy_rate, policy_to_directive_rate, orphan_signal_count

**验收**: SPINE-001~SPINE-007 达 4 分; Grafana 可看到信号流指标; 孤儿信号有阈值告警

### 2.2 Directive 审计与 Receipt 补齐

**任务清单**:
- [ ] **T2.2.1** 9 类 directive 的 DirectiveApplicationAudit 全部补齐:
  - ResponseDirective: 审计 prompt 参数是否真的改变
  - ExecutionDirective: 审计任务生成是否遵循硬约束
  - PlanDirective: 审计计划变更是否可追溯
  - RetrievalDirective: 审计资料是否按 ContextPlan 使用
  - ModelWriteDirective: 审计模型写入是否有 evidence
  - NotificationDirective: 审计推送是否遵循疲劳保护
  - UXDirective: 审计 UX 变更是否用户可见
  - SkillDirective: 审计 Skill 应用是否记录
  - CommunityDirective: 审计社群信号是否经过隐私检查
- [ ] **T2.2.2** UserVisibleReceipt — 每个关键变化产生 receipt:
  - 为什么改变任务/计划/资料/推送
  - 用户纠正入口
  - receipt 写入 CausalTrace
- [ ] **T2.2.3** `mobile/lib/features/chat/presentation/widgets/context_receipt_bar.dart` — 增强 receipt 展示

**验收**: SPINE-008~SPINE-016 达 4 分; 每条 directive 有 audit; 关键变化有 receipt

### 2.3 CausalTrace 端到端

**任务清单**:
- [ ] **T2.3.1** `backend/app/spine/causal_trace.py` — 统一 trace 存储:
  - trace_id 贯穿 Flutter → Go → Python → EventBus
  - 分层存储: recent (7天, 完整) / detail (30天, 关键节点) / summary (长期, 压缩) / archive (归档)
  - compaction 策略: 日终聚合, sprint 结束总结
- [ ] **T2.3.2** Go Gateway 传递 trace_id: request_context middleware 注入
- [ ] **T2.3.3** Flutter 上报 trace_id: 关键行为带 turn_id/trace_id
- [ ] **T2.3.4** `backend/app/api/v1/spine.py` — Timeline API: GET /spine/timeline/{user_id}/{goal_id}
- [ ] **T2.3.5** `mobile/lib/features/chat/presentation/widgets/causal_timeline_panel.dart` — 从 API 加载完整链路

**验收**: SPINE-017~SPINE-020 达 4 分; 跨层 trace_id 一致; Timeline API 返回可渲染数据

### 2.4 降级与恢复主链

**任务清单**:
- [ ] **T2.4.1** Redis 降级: spine 在 Redis 不可用时使用本地 fallback 状态
- [ ] **T2.4.2** LLM 降级: LLM 超时时使用 rule-based fallback (L0 级别响应)
- [ ] **T2.4.3** RAG 降级: 资料检索失败时 no_retrieval 模式
- [ ] **T2.4.4** SpineSnapshot: session_end / daily / pre_ttl_expiry 生成快照
- [ ] **T2.4.5** Rehydration: Redis 状态过期后从 snapshot 恢复
- [ ] **T2.4.6** ReturnCaseFile: 老用户回归时生成历史摘要

**验收**: STAB-001~STAB-005 达 4 分; Redis down 时系统仍可响应 (降级模式); 回归用户有连续性

---

## Phase 3: Aurora↔Spine 收敛 (第 6-9 周)

**目标**: Aurora L0-L4 能级运行; Aurora 输出进入 PolicyArbitration; AUR-001~AUR-049 达 4 分

### 3.1 Aurora 能级实现

**任务清单**:
- [ ] **T3.1.1** L0 (规则感知): 无 LLM — deadline 检查, 勿扰, 基础事件响应
  - 已有: kill_switch + settings 检查
  - 补齐: deadline_pressure 自动计算, quiet_hours 强制执行
- [ ] **T3.1.2** L1 (Light Aurora): 每轮参与 — 路由, 上下文, 语气, 策略参数
  - 已有: dual_core_router + ux_envelope
  - 补齐: 从 ActionableStatePacket 直接生成 ResponseDirective 参数
- [ ] **T3.1.3** L2 (Mid Aurora): 失败/错因重复/计划偏离时介入
  - 已有: ErrorReplanBridge, adaptive_replanner
  - 补齐: 从 StateRegister 的 knowledge_bottleneck + transfer_failure 触发
- [ ] **T3.1.4** L3 (Full Aurora Core): 稀缺交互式建模会话
  - 需要: CaseFile 压缩加载, 多消息 agenda, 用户打断/暂停/恢复
  - Session lifecycle: active → paused → completed → reflected
  - 输出: state_patches, policy_changes, directives_to_regenerate, user_visible_summary
- [ ] **T3.1.5** L4 (Async Deep Learning): 后台运行, 产出候选
  - 已有: Celery tasks + GLM Batch
  - 补齐: 候选策略必须进入 PolicyUpdateCandidate, 不直接改 live state
- [ ] **T3.1.6** 能级升级判断: 每轮记录 Aurora 能级与升级/不升级理由 (写入 trace)
- [ ] **T3.1.7** 成本控制: L3/L4 有配额、冷却 (最小间隔)、fallback

**验收**: AUR-001~AUR-010 达 4 分; 每轮 trace 记录 Aurora 能级; L3 有冷却机制

### 3.2 Aurora↔Spine 合流

**任务清单**:
- [ ] **T3.2.1** Aurora 输入: 必须消费 ActionableStatePacket + recent PolicyDecision + recent Outcome + user corrections
- [ ] **T3.2.2** Aurora 输出: hypotheses, policy proposals, directive proposals, experience outputs — 全部进入 PolicyArbitration
- [ ] **T3.2.3** Spine 覆盖 Aurora 建议时必须记录原因 (AUR-024)
- [ ] **T3.2.4** Aurora 自我修正: 承认误判后改变 State/Policy/Directive/Task (AUR-025)
- [ ] **T3.2.5** Aurora 自我模型: 维护当前假设、开放问题、近期误判、策略信心 (AUR-026)
- [ ] **T3.2.6** 共同 trace: Aurora 影响系统时写入同一 CausalTrace

**验收**: AUR-020~AUR-027 达 4 分; Aurora 提案不绕过 PolicyArbitration

### 3.3 Predicted Reply Options & 用户纠正

**任务清单**:
- [ ] **T3.3.1** 每轮响应附带 PredictedReplyOption 列表 (3-4 个选项):
  - label, semantic_value, effect, confidence, telemetry_id
  - 必须包含 "都不对, 我解释一下" 自由纠正
- [ ] **T3.3.2** 用户点击选项或自由纠正写入 telemetry (AUR-044)
- [ ] **T3.3.3** 纠正数据回流: 降低错误假设置信度, 更新 StateRegister
- [ ] **T3.3.4** Flutter chat UI: 选项渲染 + 自由纠正输入

**验收**: AUR-042~AUR-044 达 4 分; 纠正数据回流到策略学习

### 3.4 Aurora 状态带 & 用户设置

**任务清单**:
- [ ] **T3.4.1** 状态带 6 状态完整实现: 轻量感知中, 已校准, 发现风险, 需要确认, 深度校准可用, 冷却中
- [ ] **T3.4.2** 展开内容: 当前判断 + 依据 + 可纠正选项 + L3 唤醒入口
- [ ] **T3.4.3** 冷却体验: 冷却中提供快速校准 fallback (AUR-048)
- [ ] **T3.4.4** 用户偏好设置: 少分析我 / 直接安排我 / 多解释原因 / 不用压力提醒

**验收**: AUR-040~AUR-049 达 4 分; 状态带非装饰品, 用户可交互

---

## Phase 4: 活体验打磨 (第 8-11 周)

**目标**: 6 神性时刻全部达到用户可感知的 live 状态; UX-001~UX-015 达 4 分

### 4.1 首页重构 — 目标推进仪表盘

**现状**: 首页有功能入口, 但非目标推进导向
**目标**: 围绕 "今天该做什么" 组织

**任务清单**:
- [ ] **T4.1.1** `mobile/lib/features/home/presentation/` — 首页重构:
  - 今日任务预览 (来自 ExecutionDirective)
  - 目标进度 (来自 StateRegister)
  - 下一步建议 (来自 PolicyArbitration)
  - 神性时刻触发点
- [ ] **T4.1.2** 后端 API: GET /api/v1/home/dashboard — 聚合今日状态

**验收**: UX-001 达 4 分; 用户 3 秒内知道今天该做什么

### 4.2 神性时刻深化

**任务清单**:
- [ ] **T4.2.1** MAGIC-001 (看见坚持): GrowthCard 增强策略影响说明 + 疲劳检测
- [ ] **T4.2.2** MAGIC-002 (承认误判): SpineReceiptCard 增强误判→改判→策略变更全链路
- [ ] **T4.2.3** MAGIC-003 (知道不用资料): ContextReceiptBar 增加 "为什么不用" + "按课件重讲" 入口
- [ ] **T4.2.4** MAGIC-004 (记得时间): StaleRecoveryCard 增强时间感知 + 任务状态过期检测
- [ ] **T4.2.5** MAGIC-005 (阻止低收益): StrategyInterventionCard 增加 deadline pressure 检测 + override 保留
- [ ] **T4.2.6** MAGIC-006 (社群经验转策略): CommunityInsightCard 增加匿名共性错因→任务模板链路
- [ ] **T4.2.7** 每个神性时刻的 outcome 记录与学习

**验收**: MAGIC-001~006 全部 live; 每个时刻有 telemetry 和 outcome 回流

### 4.3 Source Tray & ContextPlan 深化

**任务清单**:
- [ ] **T4.3.1** SRC-001~SRC-018 逐项审查:
  - SourceAsset 结构化元数据 ✅
  - SourceSlice 节点映射 — 确认
  - ContextPlan 模式 (no_retrieval / graph_only / task_bound_rag / ...) — 实现
  - Pollution Guard — 实现
  - Token Budget — 实现
  - Source Tray UI ✅
  - Context Receipt ✅
  - SourceEffectiveness — 实现
  - 资料排除 + 作用域 — 实现
- [ ] **T4.3.2** 用户说 "按课件讲" → source-grounded 模式切换
- [ ] **T4.3.3** 多资料冲突标注与确认

**验收**: SRC-001~SRC-018 达 4 分; 用户能控制资料进入上下文

### 4.4 Growth Chronicle

**任务清单**:
- [ ] **T4.4.1** `backend/app/services/growth_chronicle_service.py` — 长期成长档案:
  - append-only + 分页加载
  - 用户确认/编辑/拒绝/隐藏
  - 证据 + 作用域 + 置信度
  - 撤回条件
- [ ] **T4.4.2** `mobile/lib/features/insights/` — 成长页 UI:
  - 展示用户确认过的长期洞察
  - 不展示黑箱标签
  - 用户可编辑/删除/导出
- [ ] **T4.4.3** 情绪边界: 不把心理状态病理化
- [ ] **T4.4.4** 老用户回归: 引用被确认洞察, 不硬套

**验收**: GROW-001~GROW-010 达 4 分; 长期洞察有用户确认流程

### 4.5 Community Intelligence v1

**任务清单**:
- [ ] **T4.5.1** CommunityDirective pipeline: cohort_mistake → PolicyEngine → CommunityDirective → TaskTemplate
- [ ] **T4.5.2** k-anonymity: 社群聚合满足最小群体阈值 (COM-008)
- [ ] **T4.5.3** 资源质量账本: 使用效果 + 用户反馈 + 适用范围
- [ ] **T4.5.4** 用户 opt-out: 可关闭社群智能或某类信号
- [ ] **T4.5.5** 社群信号隐私审计

**验收**: COM-001~COM-012 达 4 分; 社群信号不绕过 PolicyArbitration

---

## Phase 5: P4 研究平台 (第 10-14 周)

**目标**: P4 研究级护城河基础框架; P4-EVID/CF/EXP/SIM/MKT/PCI/QG/RES 核心项达 3 分

### 5.1 Evaluation-Grade Logging

**任务清单**:
- [ ] **T5.1.1** `backend/app/spine/intervention_episode.py` — InterventionEpisode 数据模型:
  - context_signature, candidate_policies, selection_reason, selection_probability
  - risk_level, outcome_vector, evidence_quality
  - 关联 CausalTrace + DirectiveAudit + Outcome
- [ ] **T5.1.2** 在每个策略性干预点生成 episode
- [ ] **T5.1.3** 数据完整性校验: 缺少关键字段的 episode 不参与高等级评估

**验收**: P4-EVID-001~010 达 3 分; episode 数据可导出

### 5.2 Counterfactual Evaluation 基础

**任务清单**:
- [ ] **T5.2.1** `backend/app/spine/counterfactual.py` — 按相似上下文比较策略效果
- [ ] **T5.2.2** 输出: 实际策略 vs 替代策略 + 估计效果 + 不确定性 + 限制
- [ ] **T5.2.3** 不直接 live: 只生成 PolicyUpdateCandidate
- [ ] **T5.2.4** 小样本保护: 样本不足时只产生 hypothesis

**验收**: P4-CF-001~008 达 3 分; 反事实结果不直接改 live policy

### 5.3 Safe Experiment Platform

**任务清单**:
- [ ] **T5.3.1** `backend/app/spine/experiment_registry.py` — 实验注册:
  - hypothesis, eligible_context, excluded_context, policies, guardrails
- [ ] **T5.3.2** Shadow First: 默认先 shadow, 不直接 live
- [ ] **T5.3.3** Kill Switch: 每个实验可单独关闭
- [ ] **T5.3.4** 高风险场景禁止探索: D0/crisis/fatigue_critical

**验收**: P4-EXP-001~010 达 3 分; 实验有 kill switch + 回滚策略

### 5.4 Simulation & Benchmark Lab

**任务清单**:
- [ ] **T5.4.1** `backend/app/spine/benchmark.py` — SparkleGoalBench: 固定 benchmark 套件
- [ ] **T5.4.2** Trace Replay: 用历史 trace 回放新策略
- [ ] **T5.4.3** 回归门禁: 重大改动前必须跑 benchmark

**验收**: P4-SIM-001~010 达 3 分; benchmark 可自动运行

### 5.5 Skill Marketplace v1

**任务清单**:
- [ ] **T5.5.1** Skill lifecycle: candidate → personal_shadow → personal_live → cohort_candidate → cohort_live
- [ ] **T5.5.2** SkillCard: 版本, 证据等级, 适用范围, 禁忌, 撤回条件
- [ ] **T5.5.3** 用户可预览/采纳/撤销 Skill
- [ ] **T5.5.4** 质量评分基于 outcome + 负反馈, 非下载量
- [ ] **T5.5.5** 下架机制: 负反馈/回归/隐私风险自动下架

**验收**: SKILL-001~010 达 3 分; P4-MKT-001~010 达 3 分

### 5.6 Quality Guard

**任务清单**:
- [ ] **T5.6.1** SystemHealthInsight: Spine/Aurora/Source/Community/Learning 健康指标
- [ ] **T5.6.2** 自动刹车: 异常时暂停实验/降级策略/回滚 skill
- [ ] **T5.6.3** Release Gate: 关键指标失败阻止发布
- [ ] **T5.6.4** Admin Dashboard: 管理端质量洞察

**验收**: P4-QG-001~010 达 3 分; 质量异常可自动刹车

---

## Phase 6: 稳定性与规模化 (第 12-16 周)

**目标**: STAB-001~020 达 4 分; OBS-001~020 达 4 分

### 6.1 性能 SLO

**任务清单**:
- [ ] **T6.1.1** 聊天首 token: < 2s (P95)
- [ ] **T6.1.2** 任务生成: < 5s (P95)
- [ ] **T6.1.3** 资料检索: < 1s (P95)
- [ ] **T6.1.4** 图谱加载: < 3s (P95)
- [ ] **T6.1.5** Aurora Core (L3): < 15s (P95)
- [ ] **T6.1.6** 压力测试: 模拟 100 并发用户 + 考试前高峰

### 6.2 蓝绿部署

**任务清单**:
- [ ] **T6.2.1** `scripts/deploy/blue_green_switch.sh` — 蓝绿切换脚本
- [ ] **T6.2.2** 健康检查 + 冒烟测试 + 观察期 (10 min) + 自动回滚
- [ ] **T6.2.3** 数据库迁移回滚方案

### 6.3 混沌工程

**任务清单**:
- [ ] **T6.3.1** Toxiproxy 集成: 模拟 Redis/DB/LLM/MinIO/网络故障
- [ ] **T6.3.2** 定期自动演练 (CI job)
- [ ] **T6.3.3** 事故复盘模板 + incident trace

### 6.4 成本守卫

**任务清单**:
- [ ] **T6.4.1** LLM 调用成本监控 (per user per day)
- [ ] **T6.4.2** RAG 成本监控
- [ ] **T6.4.3** Aurora Core 成本监控
- [ ] **T6.4.4** 预算熔断: 超预算自动降级

### 6.5 存储增长管理

**任务清单**:
- [ ] **T6.5.1** TraceCompaction: 日终聚合 + sprint 总结 + 归档
- [ ] **T6.5.2** Metrics buckets: 日/周/月滚动窗口
- [ ] **T6.5.3** 文件归档: 超期资料归档到冷存储
- [ ] **T6.5.4** 日志轮转: Loki retention policy

---

## Phase 7: 全面验收与上线 (第 15-18 周)

**目标**: 愿景验收清单全部通过; 产品正式部署

### 7.1 愿景验收清单逐项审查

**任务清单**:
- [ ] **T7.1.1** Section 1: 产品身份与北极星 (VISION-001~010)
- [ ] **T7.1.2** Section 2: 端到端目标闭环 (E2E-001~049)
- [ ] **T7.1.3** Section 3: Causal Runtime & Spine (SPINE-001~020, METRIC-001~010)
- [ ] **T7.1.4** Section 4: Aurora (AUR-001~049)
- [ ] **T7.1.5** Section 5: 目标建模 (GOAL-001~012)
- [ ] **T7.1.6** Section 6: 计划与 Exam Sprint (PLAN-001~012)
- [ ] **T7.1.7** Section 7: 任务卡 (TASK-001~016)
- [ ] **T7.1.8** Section 8: 知识星图 & 资料管理 (KG-001~010, SRC-001~018)
- [ ] **T7.1.9** Section 9: UX & 神性时刻 (UX-001~015, MAGIC-001~006)
- [ ] **T7.1.10** Section 10: 反馈、Outcome、Skill (OUT-001~010, LEARN-001~010, SKILL-001~010)
- [ ] **T7.1.11** Section 11: 成就与成长 (GROW-001~010)
- [ ] **T7.1.12** Section 12: 社群 (COM-001~012)
- [ ] **T7.1.13** Section 13: 召回与 JITAI (NUDGE-001~010)
- [ ] **T7.1.14** Section 14: P4 研究级 (P4-* ~100 项)
- [ ] **T7.1.15** Section 15: 架构 (APP/GW/AI/EVT ~40 项)
- [ ] **T7.1.16** Section 16: 稳定性 (STAB-001~020)
- [ ] **T7.1.17** Section 17: 安全与治理 (GOV-001~020)
- [ ] **T7.1.18** Section 18: 可观测性 (OBS-001~020)

### 7.2 内测用户体验验证

**任务清单**:
- [ ] **T7.2.1** 招募 5-10 名内测用户 (大学生, 目标: 考试冲刺)
- [ ] **T7.2.2** 7 天内测: 完整目标闭环 (输入→诊断→计划→执行→复盘)
- [ ] **T7.2.3** 内测访谈: USER-001~012 问卷
- [ ] **T7.2.4** 问题修复 + 体验优化

### 7.3 生产部署

**任务清单**:
- [ ] **T7.3.1** 服务器准备: K8s 集群 / Docker Swarm
- [ ] **T7.3.2** 域名 + SSL 证书配置
- [ ] **T7.3.3** 生产 .env 配置 (所有 secret 替换)
- [ ] **T7.3.4** 数据库迁移 + 种子数据
- [ ] **T7.3.5** 蓝绿部署: 先部署到 green, 冒烟, 切换
- [ ] **T7.3.6** 监控验证: 所有 dashboard + alert 正常
- [ ] **T7.3.7** 备份恢复演练

---

## Phase 依赖关系与并行可能性

```
Phase 0 (基础设施) ──────────────────────────────────
     │
     ├── Phase 1 (核心闭环) ────────────────────────
     │       │
     │       ├── Phase 2 (Spine 深化) ──────────────
     │       │       │
     │       │       └── Phase 3 (Aurora↔Spine) ───
     │       │
     │       └── Phase 4 (活体验) ─────────────────
     │               │
     ├── Phase 5 (P4 平台) ──────── (可与 3/4 并行)
     │
     └── Phase 6 (稳定性) ──────── (可与 5 并行)
             │
             └── Phase 7 (验收上线) ────────────────
```

**并行组 A**: Phase 2 + Phase 4 (Spine 后端 + Flutter 前端)
**并行组 B**: Phase 3 + Phase 5 (Aurora 深化 + P4 基础)
**并行组 C**: Phase 6 各子任务 (性能/部署/混沌/成本/存储)

---

## 时间线总览

| Phase | 周数 | 日历 | 核心交付 | 并行度 |
|-------|------|------|----------|--------|
| 0 | 2 | W1-W2 | 生产安全基础设施 | 低 (串行) |
| 1 | 4 | W2-W5 | 3 breakpoints + outcome 闭环 | 中 |
| 2 | 4 | W4-W7 | Spine 排序/仲裁/trace/降级 | 高 (与 4 并行) |
| 3 | 4 | W6-W9 | Aurora L0-L4 + 合流 | 高 (与 5 并行) |
| 4 | 4 | W8-W11 | UX 深化 + 神性时刻 + Chronicle | 高 (与 2 并行) |
| 5 | 5 | W10-W14 | P4 研究/实验/Simulation/Skill | 高 (与 3 并行) |
| 6 | 5 | W12-W16 | 性能/部署/混沌/成本/存储 | 高 (与 5 并行) |
| 7 | 4 | W15-W18 | 全面验收 + 内测 + 上线 | 中 |

**总日历时间**: ~18 周 (约 4.5 个月)

---

## 人员分工建议 (Codex 并行 Dispatch)

| Agent 组 | 负责范围 | 典型任务数 |
|----------|----------|-----------|
| **Agent A: Infra** | Phase 0 + Phase 6 | TLS, Sentry, secrets, 蓝绿部署, 混沌 |
| **Agent B: Spine** | Phase 2 + Phase 3 | SignalRanking, PolicyArbitration, Aurora L0-L4 |
| **Agent C: Mobile** | Phase 4 | UX 深化, 神性时刻, Source Tray, Chronicle |
| **Agent D: Backend Loops** | Phase 1 | Breakpoints, Outcome 回流, Card Protocol |
| **Agent E: P4** | Phase 5 | Episode logging, Counterfactual, Simulation, Skill |
| **Agent F: QA** | Phase 7 | 验收清单审查, 内测, 压测 |

每个 Agent 可并行 dispatch, 由主 agent (我) 做集成与审查。

---

## 关键风险与缓解

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| LLM API 成本超预算 | 高 | 高 | 成本守卫 + 预算熔断 + L0 规则感知减少 LLM 调用 |
| Aurora L3 交互设计复杂 | 中 | 高 | 先 shadow 运行, 观察用户反应再 live |
| Card Protocol 迁移数据丢失 | 低 | 高 | 双写期间 + 一致性校验 + 回滚方案 |
| P4 实验绕过安全边界 | 中 | 极高 | Kill switch + 高风险场景禁止 + 人审 |
| 移动端性能瓶颈 | 中 | 中 | 性能 SLO + 压测 + 懒加载 |
| 内测用户流失 | 中 | 中 | 缩短内测周期 + 紧密反馈循环 |
| LLM Provider 下线 | 低 | 高 | 多 provider fallback (Qwen/DeepSeek/Zhipu/GLM) |

---

## 验收总表: 愿景验收清单通过线

```text
Critical 项 (10 项): 100% 达到 4 分及以上
Core 项 (~120 项):   90% 达到 4 分及以上
Experience 项 (~30 项): 85% 达到 4 分及以上
Research/P4 项 (~80 项): 80% 达到 3 分及以上
Infrastructure 项 (~40 项): 100% 关键项达到 4 分
```

**一票否决项** (任一失败不能上线):
1. Aurora 与 Spine 割裂
2. 关键模块未接入生产主链
3. 用户反馈只记录不改变行动
4. 任务/资料/计划/社群闭环无 outcome 回流
5. 高影响判断不可解释/纠正/撤销
6. 资料污染上下文且用户无法控制
7. 长期模型把短期状态写成人格标签
8. 生产环境缺少降级/回滚/kill switch/观测
9. P4 实验绕过安全边界
10. 多目标状态互相污染

---

> **最终目标**: 用户把目标、资料、限制、失败和反馈交给 Sparkle 后，Sparkle 能持续把这些信息编译成更好的下一步，并且每一次重要改变都可解释、可纠正、可验证、可回流、可长期沉淀。
