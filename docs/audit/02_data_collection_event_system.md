# 数据收集与事件系统深度审计报告

**审计日期**: 2026-05-15
**审计范围**: Event Bus, 信号聚合, 数据收集管道, 知识图谱数据流, 存储层
**审计员**: AI System Auditor

---

## 一、事件总线架构

### 1.1 Redis Streams 配置

事件总线核心实现在 `backend/app/core/event_bus.py`，基于 Redis Streams 构建。

**核心配置参数**:
| 参数 | 默认值 | 说明 |
|------|--------|------|
| `EVENT_BUS_STREAM_MAXLEN` | 50,000 | 单 Stream 最大消息数 |
| `EVENT_BUS_MAX_RETRIES` | 3 | 消费失败最大重试次数 |
| `EVENT_BUS_PUBLISH_BASE_DELAY_MS` | 200 | 发布重试基础延迟 |
| `EVENT_BUS_PUBLISH_MAX_DELAY_MS` | 2,000 | 发布重试最大延迟 |
| `EVENT_BUS_DLQ_SUFFIX` | `:dlq` | 死信队列后缀 |
| `EVENT_BUS_DLQ_MAXLEN` | 10,000 | DLQ 最大消息数 |
| `EVENT_BUS_DLQ_ENABLED` | True | DLQ 是否启用 |
| `EVENT_BUS_PENDING_RETRY_IDLE_MS` | 5,000 | 僵死消息认领阈值 |

**主要 Stream**:
- `sparkle_events` — 主事件总线，承载几乎所有业务事件
- `stream:tracking_events` — 前端埋点追踪事件
- `cqrs:stream:user` — Go Gateway 发布的 CQRS 偏好变更事件
- `community_events` — 社区事件子流
- `*:dlq` — 各 Stream 对应的死信队列

**连接管理**:
- 懒连接模式：首次 `_publish_once` 或显式 `connect()` 时建立
- 连接失败冷却：5 秒内不重复尝试连接（`_connect_cooldown_seconds`）
- 消费循环自动重启：`_restart_consume_loop` 在 Task 异常退出时自动重建

### 1.2 事件类型清单

事件定义分布在两个位置：

**核心事件类** (`event_bus.py`):
| 事件类 | event_type | 触发场景 |
|--------|------------|----------|
| `KnowledgeNodeUpdated` | `knowledge_node_updated` | 知识节点掌握度变更 |
| `NodeMasteryUpdatedEvent` | `node_mastery_updated` | 节点掌握度更新（含 old/new） |
| `ErrorCreated` | `error_created` | 错题创建 |
| `TaskCompleted` | `task.completed` | 任务完成 |
| `TaskAbandoned` | `task.abandoned` | 任务放弃 |
| `TaskStartedEvent` | `task.started` | 任务开始 |
| `TaskStuckEvent` | `task.stuck` | 任务卡住 |
| `PlanCreatedEvent` | `plan.created` | 计划创建 |
| `UserRegisteredEvent` | `user.registered` | 用户注册 |
| `ReflectionCompletedEvent` | `reflection.completed` | 反思完成 |
| `SRLPhaseTransitionEvent` | `srl.phase.transition` | SRL 阶段转换 |
| `ProfilePreferenceUpdated` | `profile.preference.updated` | 用户偏好更新 |
| `ProfilePreferenceDeleted` | `profile.preference.deleted` | 用户偏好删除 |
| `TraitObserved` | `trait_observed` | 特质观察 |
| `TraitsColdstartCompleted` | `coldstart_completed` | 冷启动完成 |
| `CalendarEventCreated` | `calendar.event.created` | 日历事件创建 |
| `CalendarEventUpdated` | `calendar.event.updated` | 日历事件更新 |
| `CalendarEventDeleted` | `calendar.event.deleted` | 日历事件删除 |
| `DocumentCitationFeedbackEvent` | `document.citation.feedback` | 文档引用反馈 |
| `FocusSessionCompletedEvent` | `focus.session.completed` | 专注会话完成 |
| `GroupFileSharedEvent` | `group.file.shared` | 群文件共享 |
| `GroupFileDeletedEvent` | `group.file.deleted` | 群文件删除 |
| `MasteryUpdatedFromError` | `mastery_updated_from_error` | 错题导致掌握度变更 |
| `InterventionRecorded` | `intervention_record.created` | 干预记录创建 |
| `InterventionOutcomeRecorded` | `intervention_outcome_recorded` | 干预后效记录 |

**扩展事件类型** (`event_types.py` + 服务内联发布):
| event_type | 生产者 |
|------------|--------|
| `execution.delegated` / `execution.status_changed` / `execution.result_ingested` | ExecutionService |
| `tool.execution.started/completed/failed/timed_out` | 执行引擎 |
| `plan.health.alerted` | PlanHealthEventConsumer |
| `capsule.feedback.submitted` | CapsuleFeedbackService |
| `community.group_task_completed` | CommunitySignalBridge |
| `community.resource_shared` | CommunitySignalBridge |
| `community.achievement_unlocked` | CommunitySignalBridge |
| `community.aggregate_signal.created` | CommunitySignalBridge |
| `galaxy.node.updated` | GalaxyService / CommunitySignalBridge |
| `achievement.unlocked` | AchievementEngine |
| `achievement.progress` | AchievementEngine |
| `aurora.calibration.completed` | AuroraSession |
| `behavior.pattern.updated` | BehaviorSignalCollector |
| `accountability.struggle_detected` | SocialSignalBridge |
| `occurrence.status_changed` | TaskOccurrenceService |
| `galaxy.document_attachment.changed` | GalaxyService |

### 1.3 生产者-消费者拓扑

**生产者来源**:
1. **FastAPI 路由** — `api/v1/calendar.py`, `api/v1/community.py`, `api/v1/accountability.py`, `api/v1/cards.py`
2. **gRPC 服务** — `agent_grpc_service.py` → `orchestrator.py` → LLM 决策链
3. **服务层** — `task_reflection_service.py`, `execution_service.py`, `focus_service.py`, `galaxy_service.py`, `capsule_feedback_service.py`, `discovery_manager.py`, `plan_review_service.py`
4. **事件桥接** — `community_signal_bridge.py`, `galaxy_event_bridge.py`, `srl_events.py`
5. **CQRS** — Go Gateway 通过 Redis Stream `cqrs:stream:user` 发布偏好变更

**消费者拓扑** (注册于 `main.py` lifespan):

| 消费者 | Stream | Group | 订阅事件 |
|--------|--------|-------|----------|
| `GalaxyEventConsumer` | sparkle_events | galaxy_event_consumer | error_created, galaxy.node.updated, task.completed, node_mastery_updated, SimulationGapRevealed |
| `TaskEventConsumer` | sparkle_events | task_event_consumer | task.completed, task.abandoned, task.stuck, task.feedback_submitted, plan.replanned, reflection.completed, behavior.pattern.updated, +12 种桥接事件 |
| `AchievementEventConsumer` | sparkle_events | achievement_event_consumer | task.completed, community.group_task_completed, galaxy.node.updated, focus.session.completed, community.resource_shared, achievement.unlocked, achievement.progress, execution.result_ingested, aurora.calibration.completed |
| `ExecutionEventConsumer` | sparkle_events | execution_event_consumer | execution 系列事件 |
| `GalaxyExecutionConsumer` | sparkle_events | galaxy_execution_consumer | execution.result_ingested |
| `GroupFileEventConsumer` | sparkle_events | group_file_event_consumer | group.file.shared, group.file.deleted |
| `InterventionEventConsumer` | sparkle_events | intervention_event_consumer | intervention_record.created |
| `PlanHealthEventConsumer` | sparkle_events | plan_health_event_consumer | plan.health 相关 |
| `PreferenceEventConsumer` | cqrs:stream:user | python_preference_consumer | user.preferences.updated, user.preferences.inferred |
| `ProfileEventConsumer` | sparkle_events | — | profile.preference.updated/deleted, trait_observed, coldstart_completed |
| `CognitiveEventConsumer` | sparkle_events | — | 认知相关事件 |
| `CapsuleEventConsumer` | sparkle_events | — | capsule 系列事件 |
| `DocumentFeedbackEventConsumer` | sparkle_events | — | document.citation.feedback |
| `NudgeEventConsumer` | sparkle_events | — | nudge 相关事件 |
| `SocialSignalEventConsumer` | sparkle_events | — | 社交信号事件 |
| `MainChainArtifactConsumer` | sparkle_events | — | 主链制品事件 |
| `GalaxyEventBridge` | sparkle_events | galaxy_sse_bridge | galaxy.node.updated, knowledge_node_updated, node_mastery_updated, error_created, task.started (→ SSE 推送) |
| `SRLPhaseTrackerService` | sparkle_events | — | srl.phase.transition |
| `WelcomeOnboardingConsumer` | sparkle_events | welcome_onboarding_consumer | user.registered |
| `UserProfileBootstrapConsumer` | sparkle_events | user_profile_bootstrap_consumer | user.registered |
| `UserMemorySeedConsumer` | sparkle_events | user_memory_seed_consumer | user.registered |
| `GalaxyPlanConsumer` | sparkle_events | galaxy_plan_consumer | plan.created |
| `AchievementPlanConsumer` | sparkle_events | achievement_plan_consumer | plan.created |
| `PlanTaskGenerationConsumer` | sparkle_events | plan_task_generation_consumer | plan.created |

---

## 二、信号聚合系统

### 2.1 6 维度聚合详解

`StateAggregatorService` (`backend/app/state_aggregator/service.py`) 实现了 **20 个状态维度** 的聚合，分为以下几大领域：

**维度 1: 承诺与策略 (Commitment & Policy)**
- `commitment_summary` (TTL 30s) — 待办承诺数量、最近到期时间
- `pending_policies` (TTL 30s) — 活跃策略数量、下次触发时间

**维度 2: 反思与场景 (Reflection & Scene)**
- `recent_reflections` (TTL 30s) — 最近 7 天反思次数、类别
- `recent_scenes` (TTL 30s) — 最近学习场景列表
- `foresight_hint` (TTL 30s) — 预测性洞察提示

**维度 3: 社交 (Social)**
- `recent_person_mentions` (TTL 300s) — 最近人物提及、关系数量
- `social_signals_summary` (TTL 300s) — 社交信号摘要、社区参与水平

**维度 4: 参与与学习 (Engagement & Learning)**
- `engagement_state` (TTL 60s) — 最近活跃时间、7天会话数、连胜
- `learning_state` (TTL 86400s) — 学习类别偏好
- `emotion_hint` (TTL 60s) — 情感分析（关键词匹配 + 认知碎片）

**维度 5: 任务与充分性 (Task & Sufficiency)**
- `working_memory_snapshot` (TTL 30s) — 当前活跃会话的工作记忆
- `task_sufficiency_summary` (TTL 30s) — 任务信息充分性评分
- `context_sufficiency_summary` (TTL 30s) — 上下文充分性评分
- `active_skills_summary` (TTL 30s) — 激活的技能匹配

**维度 6: 知识与成就 (Knowledge & Achievement)**
- `achievement_summary` (TTL 300s) — 最近解锁、进度、总分
- `calendar_context` (TTL 300s) — 今日时间块、即将到期截止日期
- `traits_prior` (TTL 30s) — 大五人格维度
- `srl_phase` (TTL configurable) — 自我调节学习阶段
- `metacognition_profile` (TTL configurable) — 元认知维度摘要
- `idiographic_summary` (TTL configurable) — 个体独特关联

### 2.2 State Aggregator 实现

**缓存机制**:
- 内存缓存 `_cache`: `dict[(UUID, FieldName, fingerprint), (envelope, expires_at)]`
- TTL 从 30 秒到 24 小时不等（`FIELD_TTLS_SECONDS`）
- 缓存淘汰：条目超过 500 时清理过期项
- 每个 field 的 cache key 包含 `turn_parse_fingerprint`，确保上下文敏感缓存

**Kill Switch 集成**:
- `aggregator_enabled` — Stage 18 总开关 (off/shadow/live)
- `social` — Stage 33 社交信号开关
- `sufficiency_judge` — Stage 20 充分性判断开关

**Shadow 模式**:
- `aggregator_mode == "shadow"`: 计算但不返回结果（数据收集测试）
- `stage33_social_mode == "shadow"`: 社交维度在 shadow 下不返回给调用方

**数据来源**:
- PostgreSQL: EpisodicMemory, CalendarEvent, FocusSession, ChatSession, UserPreferences, SRLPhaseStateRecord 等
- Redis: cache_service (achievement_events)
- 服务层: MemoryService, PredictiveService, WorkingMemoryService, SufficiencyJudgeService, SkillSelectionService, SocialSignalBridge, SceneConsolidationService, MetacognitionService, IdiographicAssociationService

**情感分析 (`_build_emotion_hint_summary`)**:
混合两种信号源：
1. CognitiveFragment 的 sentiment 字段（来自认知碎片）
2. 聊天消息关键词匹配（`_KEYWORD_MAP` 包含中英文关键词）

### 2.3 Context Orchestrator

`AggregatorBackedSocialContextProvider` (`backend/app/routing/aggregator_backed_social_context_provider.py`) 是聚合器与路由系统的桥梁：
- 受 `SPARKLE_AGGREGATOR_ENABLED` 和 `SPARKLE_ROUTER_USE_AGGREGATOR_PROVIDER` 开关控制
- 在 aggregator 关闭时降级到 `RouterContextReader`（直接 SQL 查询）

**SignalAggregator** (`backend/app/aurora/signal_aggregator.py`) 是另一套聚合系统，服务于 Aurora Runtime：
- 10 个信号源，分为 CORE / ENHANCED / OPTIONAL 三层
- 有 token 预算控制（默认 4000 tokens）
- 信号新鲜度检测和保留层级选择

---

## 三、事件消费者详解

### 3.1 Galaxy Event Consumer

**文件**: `backend/app/services/galaxy_event_consumer.py`
**Stream**: `sparkle_events` | **Group**: `galaxy_event_consumer`

**处理链路**:

1. `error_created`:
   - 查找/创建 UserNodeStatus（知识掌握度状态）
   - 如无关联节点，自动创建 Error Gap Node（限每日 3 个）
   - 调用 `GraphEvolutionService.handle_error_created()`（不修改 mastery_score）
   - 调用 `SeedExtractor.prewarm_for_scenarios()`（种子预热）
   - 调用 `ErrorReplanBridge.on_error_created()`（检查是否需要重新规划）
   - 调用 `ErrorMasteryBridge.on_error_created()`（卡片协议证据层）
   - 检查关联计划的知识前置条件就绪度
   - 触发 Spine `on_mistake_event()`（错误信号）
   - 生成 `knowledge_readiness_improved` 系统更新

2. `galaxy.node.updated`:
   - 检查活跃计划的前置知识节点掌握度
   - 更新 PlanState 的 `knowledge_readiness` 事实
   - 当就绪度跨越阈值时生成 AdaptationRecord 和系统更新

3. `task.completed`:
   - 调用 `GraphEvolutionService.handle_task_completed()`
   - 触发 `SeedExtractor.prewarm_for_scenarios()`

4. `node_mastery_updated`:
   - 调用 `GraphEvolutionService.handle_mastery_updated()`

5. `SimulationGapRevealed`:
   - 语义搜索匹配知识节点
   - 记录学习盲区到 UserNodeStatus.learning_path_snapshot
   - 若无匹配节点则创建 CognitiveFragment

**关键保护**: `_handle_error_created` 明确注释"绝不修改 mastery_score"，掌握度更新已迁移到 `ErrorBookMasterySyncService` 同步执行。

### 3.2 Achievement Event Consumer

**文件**: `backend/app/services/achievement_event_consumer.py`
**Stream**: `sparkle_events` | **Group**: `achievement_event_consumer`

**处理链路**:
- `task.completed` → AchievementEngine + StrategyMarketplace 策略发布 + FeedbackDrivenAdjustment + StateDrivenPush
- `focus.session.completed` → 累计学习时长成就 + 周末学习成就
- `galaxy.node.updated` → 节点解锁/精通/完美主义成就
- `community.resource_shared` / `achievement.shared` → 社区分享成就
- `aurora.calibration.completed` → 校准成就
- `execution.result_ingested` → 委托执行成就
- `achievement.unlocked` → 认知碎片记录 + 社区广播 + 里程碑通知 + Spine reinforcement + Chronicle 持久化
- `achievement.progress` → 进度通知 + ContextOrchestrator 记录

**策略市场集成**: 当任务效率 >= 0.7 时，将策略发布到 `StrategyMarketplace`，跨用户共享有效策略。

**Profile 信号写入**: `_refresh_achievement_profile_signals` 从最近 30 天成就中提取：
- 高峰学习时段
- 学习节奏风格 (steady/sprint/mixed)
- 激励响应类型 (progress_praise/milestone_celebration/mastery_affirmation)
- 奖励敏感度

### 3.3 Community Signal Bridge

**文件**: `backend/app/services/community_signal_bridge.py`

**核心能力**:
1. **群任务同步**: 将个人任务完成同步到群任务系统
2. **知识分享奖励**: 分享知识节点时给予 5.0 掌握度加成
3. **差分隐私聚合**: 通过 `PrivacyPreservingCommunityEngine` 构建匿名化社区信号
4. **成就广播**: 将成就解锁广播到社区频道

**隐私保护**:
- 每日 epsilon 预算（默认 3.0）
- 最小群体大小（默认 5）
- Opt-out 机制（`community_intelligence_enabled`）
- 禁止字段过滤（AURORA_FORBIDDEN_SOCIAL_KEYS: 用户名、邮箱等）
- `PrivacyBudgetLedger` 持久化记录每次查询的隐私花费

**Kill Switch**: `AuroraStage33KillSwitchService` 控制 community 模式 (off/shadow/live)

### 3.4 其他消费者

**InterventionEventConsumer** (`intervention_event_consumer.py`):
- 消费 `intervention_record.created`
- 通过模板系统渲染干预消息
- 投递到通知/推送通道
- 触发 ParameterCompiler 编译自适应调整

**GroupFileEventConsumer** (`group_file_event_consumer.py`):
- 消费 `group.file.shared` / `group.file.deleted`
- 委托 Celery 任务执行索引/清理

**PreferenceEventConsumer** (`preference_event_consumer.py`):
- 监听 `cqrs:stream:user`（Go Gateway 发布）
- 处理 `user.preferences.updated` / `user.preferences.inferred`
- 失效 Python 端用户缓存
- 完整的延迟指标（消费延迟、缓存失效延迟、端到端延迟）

**GalaxyExecutionConsumer** (`galaxy_execution_consumer.py`):
- 消费 `execution.result_ingested`（仅成功的 OpenClaw 执行）
- 将执行结果沉淀为知识节点
- 自动关联任务和知识节点

**Journey Consumers** (基于 `JourneyEventConsumerBase`):
- `WelcomeOnboardingConsumer` → user.registered → 欢迎通知
- `UserProfileBootstrapConsumer` → user.registered → 初始化偏好和档案
- `UserMemorySeedConsumer` → user.registered → 创建初始情景记忆
- `GalaxyPlanConsumer` → plan.created → 从目标引导知识图谱种子
- `AchievementPlanConsumer` → plan.created → 处理计划创建成就
- `PlanTaskGenerationConsumer` → plan.created → 异步生成计划任务

---

## 四、数据收集管道

### 4.1 行为数据收集

**任务行为**:
| 行为 | 事件 | 收集点 | 数据量 |
|------|------|--------|--------|
| 任务完成 | `task.completed` | TaskService | estimated/actual_minutes, difficulty, completion_rate, source |
| 任务放弃 | `task.abandoned` | TaskService | reason, time_spent, estimated_minutes |
| 任务开始 | `task.started` | TaskOccurrenceService | source, plan_id |
| 任务卡住 | `task.stuck` | (检测器) | stuck_point, recent_steps, elapsed_seconds, diagnosis |
| 任务反馈 | `task.feedback_submitted` | TaskReflectionService | category, difficulty_delta, feedback_text |
| 专注完成 | `focus.session.completed` | FocusService | duration_minutes, mastery_updates, started_at |

**挣扎信号** (`StruggleSignalAggregator`):
- 跳过率 (skip_rate) — 权重 0.30
- 短会话率 (short_session_rate) — 权重 0.20
- 错题趋势 (error_trend) — 权重 0.25
- 逾期任务权重 (overdue_weight) — 权重 0.15
- 挣扎连续天数 (streak_weight) — 权重 0.10
- 完成间隔权重 (completion_gap_weight) — 权重 0.35
- 特殊触发: 高跳过率 (>=0.7, >=5 任务) 强制 struggle_score >= 0.61

**行为信号收集器** (`BehaviorSignalCollector`):
- 处理任务完成/放弃/卡住/反馈/重规划/行为模式事件
- 作为 TaskEventConsumer 的子步骤运行

### 4.2 对话数据收集

**对话事件流**:
1. Flutter 发送消息 → Go WebSocket Proxy → gRPC → Python Orchestrator
2. Orchestrator (FSM) 处理消息 → LLM 调用 → 流式返回
3. 对话数据用于：
   - `CognitiveEventConsumer` 提取认知碎片
   - `CapsuleEventConsumer` 处理胶囊反馈
   - `StateAggregatorService._build_working_memory_snapshot` 获取活跃会话
   - `StateAggregatorService._classify_recent_chat_sentiment` 提取情感信号

**SRL 阶段跟踪**:
- `SRLPhaseTrackerService` 消费 `srl.phase.transition` 事件
- 跟踪 forethought / performance / self-reflection 阶段转换
- 受 `AuroraStage29SRLKillSwitchService` 控制

### 4.3 情感/状态数据

**数据来源**:
1. `CognitiveFragment.sentiment` — 认知碎片中的情感标签
2. 聊天消息关键词匹配 — 中英文情感词库（6 类: frustrated, anxious, overwhelmed, happy, motivated, neutral）
3. 用户偏好变更 — `ProfilePreferenceUpdated/Deleted` 事件
4. 特质观察 — `TraitObserved` 事件 → 大五人格维度更新

**聚合路径**: `StateAggregatorService._build_emotion_hint_summary`
- 取最近 24 小时的 CognitiveFragment.sentiment
- 取最近 30 条用户聊天消息进行关键词匹配
- 合并分布，识别 dominant sentiment
- 检测 emotional block（anxious/frustrated/overwhelmed）

### 4.4 日历事件

**事件流**:
1. `CalendarEventCreated/Updated/Deleted` → 发布到 sparkle_events
2. `TaskEventConsumer` 将日历事件桥接到 Spine
3. `StateAggregatorService._build_calendar_context` 聚合：
   - 今日时间块（7:00-22:00 减去已有事件）
   - 7 天内截止日期（task/plan 来源）
   - 工作密度 (low/medium/high)
   - 考试紧迫度（来自 PredictiveService）

**EventService** (`event_service.py`):
- 批量写入 TrackingEvent 到 PostgreSQL
- 去重（基于 event_id）
- 转发到 `stream:tracking_events`

**EventRetentionService** (`event_retention_service.py`):
- 软删除过期 TrackingEvent（payload + entities 置空）
- 清理过期 UserStateSnapshot

---

## 五、存储层分析

### 5.1 Redis 缓存策略

**事件总线**:
- Redis Streams 存储事件（maxlen 50,000，approximate trimming）
- DLQ Stream maxlen 10,000
- Idempotency store: 24 小时 TTL 的去重锁

**State Aggregator 缓存**:
- 内存缓存 `_cache`，TTL 30s - 86400s
- 缓存键: `(user_id, field_name, turn_parse_fingerprint)`
- 最大 500 条，超限时清理过期项

**Spine 系统**:
- `spine:directive:active:{user_id}` — 活跃指令
- `spine:state_index:{user_id}` — 状态索引集合
- `spine:state:{user_id}:{key}` — 状态条目
- `spine:effects:{user_id}` — 最近效果列表（保留 50 条）
- `spine:relationship:{user_id}` — 关系信任模型
- `spine:aurora_decisions:{user_id}` — Aurora 决策记录（保留 50 条，30 天 TTL）
- `spine:achievement_events:{user_id}` — 成就事件列表

**Struggle 缓存**:
- `struggle:score:{user_id}` — 6 小时 TTL

**CQRS 缓存**:
- PreferenceEventConsumer 失效用户偏好缓存

### 5.2 PostgreSQL 持久化

**事件相关表**:
| 表 | 用途 |
|----|------|
| `tracking_events` | 前端埋点事件（含去重 event_id 索引） |
| `event_bus_dlq` | 事件总线死信队列审计日志 |
| `user_state_snapshots` | 用户状态快照 |

**业务数据表**（消费者写入）:
| 表 | 写入者 |
|----|--------|
| `user_node_statuses` | GalaxyEventConsumer |
| `knowledge_nodes` | GalaxyEventConsumer (Error Gap Nodes) |
| `plan_states` | GalaxyEventConsumer (knowledge_readiness) |
| `tasks` | TaskEventConsumer (status updates) |
| `goals` | TaskEventConsumer (progress updates) |
| `user_achievements` | AchievementEventConsumer |
| `notifications` | AchievementEventConsumer, InterventionEventConsumer |
| `push_history` | InterventionEventConsumer |
| `episodic_memories` | UserMemorySeedConsumer |
| `cognitive_fragments` | AchievementEventConsumer (认知碎片) |
| `growth_chronicle_snapshots` | AchievementEventConsumer (编年史) |
| `privacy_budget_ledgers` | CommunitySignalBridge |
| `community_aggregate_signals` | CommunitySignalBridge |
| `intervention_records` | InterventionEventConsumer |
| `cards` | Card Protocol 相关 |

### 5.3 向量存储使用

**pgvector** 在数据收集系统中的使用：
- `KnowledgeNode` 表存储知识节点（向量嵌入用于语义搜索）
- `GalaxyExecutionConsumer` 使用 `ExpansionService.upsert_node_from_candidate` 创建节点（`generate_embedding=False`，嵌入生成延迟）
- `GalaxyEventConsumer._handle_simulation_gap_revealed` 使用 `galaxy_service.semantic_search_nodes` 进行语义匹配
- 向量搜索阈值: 0.16（正常）/ 0.08（宽松降级）

**Apache AGE (Graph)**:
- 知识图谱关系通过 `TaskKnowledgeLink` 表管理
- `GraphEvolutionService` 处理图结构演化
- `GraphStructureEvolutionService.record_engagement` 记录参与度

---

## 六、数据流完整图

```
用户行为 (Flutter)
    │
    ├─ 任务操作 ─────────────────→ Go Gateway (WebSocket/REST)
    ├─ 专注会话                       │
    ├─ 日历操作                       ↓
    ├─ 社区互动                gRPC / REST
    ├─ 对话消息                       │
    │                                 ↓
    │                          Python Engine
    │                                 │
    │                    ┌────────────┼────────────┐
    │                    ↓            ↓            ↓
    │              EventService   TaskService   FocusService
    │                    │            │            │
    │                    ↓            ↓            ↓
    │              ┌──────────────────────────────────┐
    │              │     Redis Streams (EventBus)       │
    │              │  sparkle_events / community_events  │
    │              │  cqrs:stream:user                   │
    │              │  stream:tracking_events             │
    │              └──────────┬───────────────────────┘
    │                         │
    │         ┌───────────────┼───────────────────────┐
    │         ↓               ↓                       ↓
    │   ┌──────────┐   ┌───────────┐          ┌──────────────┐
    │   │ Galaxy   │   │ Achievement│          │ Task Event   │
    │   │ Consumer │   │ Consumer  │          │ Consumer     │
    │   └────┬─────┘   └─────┬─────┘          └──────┬───────┘
    │        │               │                       │
    │        ↓               ↓                       ↓
    │   GraphEvolution  AchievementEngine    BehaviorSignal
    │   SeedExtractor   StrategyMarketplace  Metacognition
    │   ErrorReplan     ProfileSignals      AdaptiveReplanner
    │   CardProtocol    SpineReinforcement  CommunityBridge
    │        │               │               SpineOrchestrator
    │        ↓               ↓               OutcomeTracker
    │   ┌──────────────────────────────────────────────┐
    │   │          PostgreSQL (持久化)                    │
    │   │   knowledge_nodes, user_node_statuses         │
    │   │   plan_states, tasks, goals                   │
    │   │   user_achievements, notifications            │
    │   │   cognitive_fragments, episodic_memories      │
    │   │   intervention_records, growth_chronicle      │
    │   │   privacy_budget_ledgers                      │
    │   └──────────────────┬───────────────────────────┘
    │                      │
    │         ┌────────────┼────────────────┐
    │         ↓            ↓                ↓
    │   ┌──────────┐ ┌──────────┐   ┌──────────────┐
    │   │ State    │ │ Signal   │   │ Social       │
    │   │ Aggregator│ │Aggregator│   │ Signal Bridge│
    │   └────┬─────┘ └────┬─────┘   └──────┬───────┘
    │        │             │                │
    │        ↓             ↓                ↓
    │   ┌──────────────────────────────────────────┐
    │   │         AI 决策输入                         │
    │   │   UserStateV1 (20 维度)                     │
    │   │   SignalSnapshot (3 层 / 10 信号源)          │
    │   │   SocialSignals (差分隐私聚合)               │
    │   │   SpineDirective (活跃干预指令)              │
    │   └──────────────────┬───────────────────────┘
    │                      │
    │                      ↓
    │              ┌──────────────┐
    │              │  Orchestrator │
    │              │  (LangGraph)  │
    │              │  DualCoreRouter│
    │              └──────┬───────┘
    │                     │
    │                     ↓
    │              AI 回复 → 用户
    │
    └─ SSE 实时推送 ← GalaxyEventBridge (galaxy.node.updated, error_created, task.started)
```

---

## 七、问题报告

### P0 (Critical)

#### P0-01: 所有消费者共享同一 Stream，单消费者阻塞可能影响全局

**文件**: `backend/app/core/event_bus.py:1082-1117` 及 `backend/app/main.py:225-361`
**问题描述**: 所有 20+ 消费者都订阅 `sparkle_events` 这一个 Stream。每个消费者组的消费循环串行处理消息（`block=2000`, `count=1`）。任何一个慢消费者（如 GalaxyEventConsumer 的 `_handle_error_created` 包含 6+ 个数据库操作）不会阻塞其他消费者（因为 Redis Streams 的消费者组模型），但会产生以下问题：
- 高流量时，所有消费者组各自维护 pending messages，Redis 内存压力大
- 无流控机制，消费者崩溃时 pending messages 堆积
- 没有优先级区分——用户注册事件和知识图谱更新在同一个 Stream 竞争

**严重程度**: P1（设计缺陷，当前可运行但扩展性受限）

---

### P1 (High)

#### P1-01: StateAggregator 内存缓存无上限保证

**文件**: `backend/app/state_aggregator/service.py:110-113, 228-230`
**问题描述**: `_cache` 在超过 500 条时清理过期项，但如果所有条目都未过期，缓存将无限增长。在高并发场景下，每个用户每个维度都可能产生缓存条目。
**修复建议**: 添加 LRU 驱逐或硬上限（如 2000 条），超过时无条件淘汰最旧条目。

#### P1-02: GalaxyEventConsumer._handle_error_created 长事务风险

**文件**: `backend/app/services/galaxy_event_consumer.py:104-205`
**问题描述**: `_handle_error_created` 在单个 `async with AsyncSessionLocal() as db` 中执行了 6+ 个数据库操作（创建节点、图演化、种子预热、错误重规划桥、卡片协议桥、计划健康检查），最后才 `db.commit()`。如果中间任何步骤耗时长或失败，整个事务回滚，所有操作丢失。
**修复建议**: 将独立操作拆分为独立事务。种子预热和 Spine 信号可以独立执行，不受主事务影响。

#### P1-03: TaskEventConsumer._handle_task_completed 串行执行 7+ 个子操作

**文件**: `backend/app/services/task_event_consumer.py:92-243`
**问题描述**: 单个 `task.completed` 事件触发了 7 个独立的异步操作：BehaviorSignalCollector、Metacognition、CommunityBridge、OutcomeTracker、SpineOrchestrator、AutoFragmentCollector、AdaptiveReplanner、GoalProgress。虽然每个操作有独立 try/except，但它们串行执行，总延迟等于所有操作之和。
**修复建议**: 将独立操作改为 `asyncio.gather` 并行执行，显著减少处理延迟。

#### P1-04: EventService 发布到不同 Stream 但消费者未覆盖

**文件**: `backend/app/services/event_service.py:131-147`
**问题描述**: `EventService._publish_event` 将事件发布到 `stream:tracking_events`，但没有任何消费者订阅此 Stream。这些前端埋点事件仅被持久化到 PostgreSQL，不会触发任何后续处理。如果这是有意设计，则没问题；如果需要触发某些处理，则存在遗漏。
**修复建议**: 明确 `stream:tracking_events` 的消费者需求。如果仅用于存储，添加注释说明。

#### P1-05: PreferenceEventConsumer 独立实现消费逻辑，未复用 EventBus

**文件**: `backend/app/services/preference_event_consumer.py:55-85`
**问题描述**: `PreferenceEventConsumer` 直接使用 `redis.xreadgroup` 而非 `EventBus.subscribe`，拥有独立的 DLQ 和重试逻辑。这导致：
- 与 EventBus 的去重、idempotency、auto-restart 机制不一致
- 重复实现了 DLQ 和重试逻辑
- 无法被 `event_bus.list_consumer_streams()` 监控覆盖
**修复建议**: 迁移到使用 `EventBus.subscribe` 统一基础设施。

#### P1-06: AchievementEventConsumer 在 handle_event 中无 @reliable_consumer

**文件**: `backend/app/services/achievement_event_consumer.py:74`
**问题描述**: `GalaxyEventConsumer.handle_event` 有 `@reliable_consumer` 装饰器（设置 consumer label 用于 metrics），但 `AchievementEventConsumer.handle_event` 没有。这意味着 Rule AZ 的可靠性检查无法覆盖此消费者。
**修复建议**: 添加 `@reliable_consumer("AchievementEventConsumer")` 装饰器。

#### P1-07: GalaxyEventConsumer._create_error_gap_node 缺乏并发保护

**文件**: `backend/app/services/galaxy_event_consumer.py:225-291`
**问题描述**: 创建 Error Gap Node 时，先查询是否存在同名节点，再创建新节点。但在高并发下（同一用户快速创建多个错题），查询和创建之间可能被其他事务插入，导致重复节点。虽然有名称去重检查，但 `existing.scalar_one_or_none()` 查询在并发事务隔离级别下可能读到旧数据。
**修复建议**: 使用 PostgreSQL UNIQUE 约束或 `INSERT ... ON CONFLICT DO NOTHING` 保证原子性。

---

### P2 (Medium)

#### P2-01: Event Bus publish 失败时静默降级

**文件**: `backend/app/core/event_bus.py:1064-1080`
**问题描述**: `publish` 方法在所有重试失败后返回 `None`，调用方（如 `TaskService` 完成任务后发布事件）很少检查返回值。如果 Redis 持续不可用，事件会丢失，且只有 DLQ 持久化记录作为痕迹。
**修复建议**: 在关键路径（如任务完成）添加 publish 失败后的补偿逻辑，或至少添加告警。

#### P2-02: 情感分析仅使用关键词匹配

**文件**: `backend/app/state_aggregator/service.py:550-596`
**问题描述**: `_classify_recent_chat_sentiment` 使用硬编码的中英文关键词列表进行情感分类。这种方法：
- 无法捕捉讽刺、反讽等复杂语境
- 关键词列表可能不完整
- 不支持多语言扩展（只支持中英文）
**修复建议**: 考虑集成轻量级情感模型，或至少将关键词列表外部化为配置。

#### P2-03: StruggleSignalAggregator 的 _collect_signals 执行 7 个串行 DB 查询

**文件**: `backend/app/services/struggle_signal_aggregator.py:162-207`
**问题描述**: `_collect_signals` 串行执行 6 个独立的 SQL 查询（skip_counts, short_session_counts, error_counts, overdue_count, struggle_streak, completion_gap），总延迟为各查询之和。
**修复建议**: 使用 `asyncio.gather` 并行化独立查询。

#### P2-04: _build_achievement_summary 查询三次 user_achievements 表

**文件**: `backend/app/state_aggregator/service.py:766-870`
**问题描述**: `_build_achievement_summary` 执行了三个独立的查询（recent_unlocks, in_progress, all_for_score），每个都 JOIN Achievement 表。可以合并为一个查询。
**修复建议**: 使用一次查询获取所有数据，在内存中分类。

#### P2-05: Community Error Aggregation Service 无定时触发机制

**文件**: `backend/app/services/community_error_aggregation_service.py`
**问题描述**: `CommunityErrorAggregationService.aggregate_for_nodes_with_recent_errors` 没有被任何消费者或定时任务调用。它是一个完整的服务实现，但没有被接入到事件管道中。
**修复建议**: 将其连接到 Celery 定时任务或 `error_created` 事件处理链中。

#### P2-06: Journey Consumer Base 的 consumer_name 使用 timestamp，可能导致消费者堆积

**文件**: `backend/app/consumers/journey_consumer_base.py:50`
**问题描述**: `consumer_name=f"{self.CONSUMER_NAME_PREFIX}-{_utcnow().timestamp()}"` 每次启动都生成新的 consumer_name，导致 Redis 中遗留旧消费者的 pending messages 永远不会被重新认领（xautoclaim 基于闲置时间，但新消费者无法接触到旧消费者的 pending entries）。
**修复建议**: 使用稳定的 consumer_name（如 `f"{prefix}-{hostname}-{pid}"`），或在启动时清理旧消费者。

#### P2-07: EventBus 连接冷却日志不充分

**文件**: `backend/app/core/event_bus.py:937-946`
**问题描述**: `_publish_once` 在连接冷却期内直接 `raise RuntimeError` 而无详细日志。在调试时难以区分"Redis 完全不可用"和"连接正在冷却"。
**修复建议**: 在冷却期触发时记录 warning 级别日志，包含冷却剩余时间。

#### P2-08: SocialSignalBridge.build_social_signals_v1 引用但未在聚合器中展示

**文件**: `backend/app/state_aggregator/service.py:360-387`
**问题描述**: `_build_social_signals_summary` 调用 `SocialSignalBridge.build_social_signals_v1`，但该方法在 `community_signal_bridge.py` 中未直接定义——它是从 `social_signal_bridge.py` 引入的不同类。两个 SocialSignalBridge 类名相同但位于不同文件，可能导致混淆。
**修复建议**: 统一类名或明确文档说明两者的区别和职责。

---

## 八、总结

### 系统优势

1. **完整的事件生命周期管理**: 从生产、传输、消费到 DLQ，每个环节都有处理机制
2. **丰富的数据收集**: 20 维状态聚合覆盖了用户行为、情感、社交、知识等全面维度
3. **Kill Switch 集成**: 所有关键路径都有 tri-state 开关，支持灰度发布和安全回滚
4. **差分隐私**: 社区信号聚合使用 Laplace 噪声和 epsilon 预算，隐私保护到位
5. **自动恢复**: 消费循环自动重启、僵死消息自动认领、连接失败冷却
6. **可观测性**: Prometheus 指标覆盖 DLQ 深度、消费失败、发布重试等

### 关键风险

1. **串行处理瓶颈**: TaskEventConsumer 单事件触发 7+ 串行操作，是系统最大延迟瓶颈
2. **单 Stream 高负载**: 20+ 消费者组订阅同一 Stream，高流量时 pending messages 堆积风险
3. **长事务风险**: GalaxyEventConsumer 的 error_created 处理链过长
4. **消费者代码重复**: PreferenceEventConsumer 未复用 EventBus 基础设施

### 修复优先级建议

| 优先级 | 问题 | 投入 | 收益 |
|--------|------|------|------|
| P1-03 | TaskEventConsumer 并行化 | 中 | 高（延迟减 60%+） |
| P1-02 | GalaxyEventConsumer 拆分事务 | 中 | 高（可靠性） |
| P1-05 | PreferenceEventConsumer 统一 | 中 | 中（代码一致性） |
| P1-07 | Error Gap Node 并发保护 | 低 | 高（数据一致性） |
| P2-03 | Struggle 信号并行化 | 低 | 中（性能） |
| P2-04 | Achievement 查询合并 | 低 | 中（性能） |
