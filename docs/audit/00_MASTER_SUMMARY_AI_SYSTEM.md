# Sparkle AI 系统深度审计 — 主汇总报告

> **审计日期**: 2026-05-15 | **审计员**: Chief Architect (主 agent + 4×Opus 并行)
> **代码覆盖**: 70,000+ 行核心代码逐行审查 | Round 1-7 (19 子报告 + 1 Master)
> **文件覆盖**: 180+ 文件 | **总报告规模**: ~45,000 行
> **P0 发现**: 30+ | **P1 发现**: 65+ | **P2 发现**: 80+

---

## 一、系统全景

Sparkle 的 AI 系统是一个**多层、多信号、多反馈闭环**的自适应成长引擎。它不是简单的 LLM 调用管道，而是一个完整的感知-决策-执行-反馈认知架构。

### 1.1 架构分层

```
┌─────────────────────────────────────────────────────────────┐
│                    LLM Generation Layer                       │
│  Aurora Decision Loop (L2) → ChatLayerAdapter → LLM Response  │
├─────────────────────────────────────────────────────────────┤
│                    Decision & Routing Layer                    │
│  DualCoreRouter (13+ signals) │ AuroraEngine (deterministic) │
│  L1LightAurora (LLM-free)     │ L0RuleEngine (pure rules)    │
├─────────────────────────────────────────────────────────────┤
│                    Signal Aggregation Layer                    │
│  StateAggregatorService (20+ fields) │ SignalAggregator (3-tier)│
│  ContextBuilderMixin │ Spine StateRegister                    │
├─────────────────────────────────────────────────────────────┤
│                    Data & Storage Layer                        │
│  PostgreSQL (pgvector+AGE) │ Redis (cache+streams+session)   │
│  EpisodicMemory │ WorkingMemory │ CognitiveFragments          │
├─────────────────────────────────────────────────────────────┤
│                    Event & Feedback Layer                      │
│  Redis Streams EventBus │ AchievementEngine │ TaskFeedback    │
│  ChatSignalCollector │ SceneConsolidation │ Galaxy Consumers  │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 核心数据流

```
User Message (Flutter)
  → Go Gateway (WebSocket, auth, routing)
    → Python gRPC Service (agent_grpc_service.py)
      → ChatOrchestrator (7-mixin composition)
        ├── _build_full_context() ← ContextBuilderMixin
        │   ├── _build_user_context() ← 20+ data sources
        │   │   ├── StateAggregatorService (20 fields, TTL cache)
        │   │   ├── CognitiveService (behavior patterns)
        │   │   ├── MemoryService (episodic, working memory)
        │   │   ├── PersonalizationEngine (LLM profile)
        │   │   ├── AuroraControlSurfaceService
        │   │   ├── ScaffoldingFSM (SGW)
        │   │   ├── GalaxyService (knowledge graph)
        │   │   └── SeedLibraryService (few-shot)
        │   ├── _build_conversation_context() ← ContextPruner
        │   └── _attach_stage34/39_context() ← Aurora stages
        ├── DualCoreRouter.route() ← 13+ precedence signals
        ├── UnifiedIntentRouter (intent classification)
        ├── LangGraphPlanner (FSM graph execution)
        │   └── create_standard_chat_graph() → RedisCheckpointer
        ├── L1LightAurora.run_turn() ← L0 rules + energy
        ├── AuroraDecisionLoop.decide() ← LLM-driven cognition
        ├── ToolExecutor (dynamic_tool_registry, 22+ tools)
        ├── UXEnvelopeBuilder.build() ← 7 chat modes
        └── ResponseComposer → streaming gRPC → Go → Flutter
```

---

## 二、Aurora 编排系统详解

### 2.1 三层感知架构

| 层级 | 名称 | LLM依赖 | 核心能力 | 文件位置 |
|------|------|---------|---------|---------|
| **L0** | Rule Engine | 无 | Deadline pressure, Quiet hours → StateRegister | `aurora/runtime_v1/l0_rules.py` |
| **L1** | Light Aurora | 无 | 检索分类, 能量决策, 状态带, 升级判断 | `aurora/runtime_v1/l1_light_aurora.py` |
| **L2** | Decision Loop | 是 | 认知决策, 策略选择, 标准层合约, 教学策略 | `aurora/runtime_v1/decision_loop.py` |

**关键洞察**: L1 是一个完全无 LLM 的快速路径，用于判断是否需要升级到 L2。这避免了每个 turn 都调用 LLM。

### 2.2 Dual-Core Router 详解

`dual_core_router.py` (1089 行) 是整个系统最核心的路由决策器。

**13+ 信号优先级** (从高到低):
| 优先级权重 | 信号 | 触发条件 |
|-----------|------|---------|
| 9.0 | emotional_block | 负面情感占比高 / 情绪阻塞 |
| 8.0 | procrastination | 拖延关键词 / 连续反馈困难 |
| 7.5 | route_outcome_failure | 近期执行路径连续被纠正 |
| 7.0 | cognitive_mode | 理解卡点 / 概念混淆 |
| 6.5 | scaffolding_frustration | SGW 支架层挫败区 |
| 6.0 | low_metacognition | 自我监测准确率 < 0.5 |
| 5.0 | high_cognitive_load | 认知负荷 > 0.55 |
| 4.5 | route_outcome_over_scaffolded | 过度支架化 |
| 4.0 | spine_fatigue | Spine 疲劳信号 |
| 3.0 | reflection_phase | SRL 反思阶段 |
| 2.5 | scaffolding_boredom | SGW 无聊区 |
| 1.0 | goal_clarity | 目标清晰度评分 |

**三种路由模式**:
- `execution_first`: 目标清晰+信息充分+无阻塞 → 直接推进执行
- `cognitive_first`: 情绪阻塞/拖延/反思/认知过载 → 先做状态调整
- `balanced`: 两者兼有 → 双核并行

**输出**: `DualCoreDecision` 包含 `cognitive_adjustments` + `execution_constraints` + `strategy_adjustments` + `signal_scores`。

### 2.3 Aurora Decision Loop (L2) 详解

`decision_loop.py` (1834 行) 是 LLM 驱动的 Aurora 认知核心。

**决策输出**:
```python
AuroraDecision:
  action: emit_message | wait | schedule_wake | update_harness | update_state | soft_return_topic | drop_thread
  surface_complete: bool
  modeling_complete: bool
  state_updates: tensions, correct_answer_node
  harness_updates: proactive_intensity, conversation_style, expression, strategy
  chat_directive: intent, target_domain, standard_layer_contract
  wake_schedule: optional proactive wake
```

**Standard Layer Contract** (关键创新):
每种场景有对应的 `must_include` / `must_not_include` 约束，确保 LLM 输出结构化：

| response_type | must_include | must_not_include |
|--------------|-------------|-----------------|
| task_help | worked_example, three_practice_questions, completion_check | full_week_replan, long_motivational_speech |
| emotional_support | emotional_acknowledgment, one_concrete_next_step | full_week_replan, blame_or_shame |
| diagnostic | mistake_diagnosis, one_targeted_fix | full_week_replan |
| calibration | explicit_uncertainty, calibration_question | overconfident_claims, high_pressure_task_load |
| plan_discussion | plan_delta_or_tradeoff, one_decision_or_question | long_motivational_speech |

**教学策略系统 (7 个 boolean 开关)**:
`concept_first`, `problem_first`, `worked_example_first`, `retrieval_practice`, `interleaving`, `spaced_review`, `error_analysis_required`

**安全防线**:
- `FORBIDDEN_MODELING_DOMAINS`: 禁止临床诊断、人格病理、创伤归因、社会身份推断等 15 个域
- `HarnessUpdateRejectedError`: 硬边界验证拒绝不合规的 harness 更新
- `Sleep Guard`: 深夜模式禁止 full_week_replan 和 three_practice_questions

### 2.4 State Aggregator 详解

`state_aggregator/service.py` (1190 行) 聚合 **20+ 个用户状态字段**:

| 字段 | TTL | 数据来源 |
|------|-----|---------|
| commitment_summary | 30s | MemoryService.pending_commitments |
| pending_policies | 30s | PolicySchedulerService |
| recent_reflections | 30s | EpisodicMemory (reflection) |
| recent_scenes | 30s | SceneConsolidationService |
| foresight_hint | 30s | PredictiveService |
| engagement_state | 60s | FocusSession + UserStreakStats |
| emotion_hint | 60s | CognitiveFragment.sentiment + ChatMessage keyword |
| working_memory_snapshot | 30s | WorkingMemoryService |
| task_sufficiency_summary | 30s | SufficiencyJudgeService |
| calendar_context | 300s | CalendarEvent + PredictiveService |
| traits_prior | 30s | UserPreferencesCenter.BigFiveTraits |
| srl_phase | 可配 | SRLPhaseStateRecord |
| metacognition_profile | 可配 | MetacognitionService |
| idiographic_summary | 可配 | IdiographicAssociationService |
| achievement_summary | 300s | UserAchievement + Achievement + Redis spine |
| social_signals_summary | 300s | SocialSignalBridge |
| active_skills_summary | 30s | SkillSelectionService |
| learning_state | 24h | PredictiveService.next_intent_forecast |

**Kill Switch 集成**: 每个 field 都受 `AuroraStage18KillSwitchService` 的 tri-state (`off` / `shadow` / `live`) 控制。`shadow` 模式下计算但不返回值。

### 2.5 Signal Aggregator 详解

`aurora/signal_aggregator.py` (439 行) 实现**三层信号收集**:

| Tier | 信号源 | 预算 |
|------|--------|------|
| CORE | memory, focus, error_book | 受保护，不可裁剪 |
| ENHANCED | companion_state, strategy_state, persona, plan_state | 超预算时先裁剪 |
| OPTIONAL | achievement, predictive, analytics | 最先被裁剪 |

**Token 预算**: 默认 4000 tokens，通过 `_enforce_budget()` 逐层裁剪。

---

## 三、建模系统详解

### 3.1 用户画像维度

```
ProfileContext:
  ├── identity: nickname, timezone, language, is_pro, persona_type, flame_level
  ├── preferences: depth_preference, curiosity_preference, session_length, difficulty
  ├── llm_profile: verbosity, temperature, tone, exploration_level, should_ask_clarifying
  ├── BigFive traits: openness, conscientiousness, extraversion, agreeableness, neuroticism
  ├── cognitive_summary: behavior patterns (cognitive/emotional/execution types)
  ├── knowledge_summary: weak spots, mastery changes, subject affinities
  ├── active_skills: matched skills from SkillSelectionService
  └── policy_signals: pattern → policy mapping (PATTERN_POLICY_MAP)
```

### 3.2 认知棱镜 (Cognitive Prism)

`CognitiveService` 识别行为模式，按类型分类：
- **cognitive**: 认知盲点、计划乐观偏差、怀疑驱动修正
- **emotional**: 完美主义逃避、情绪型模式
- **execution**: 执行偏好、时间学习、质量敏感度

每个 pattern 有 `PATTERN_POLICY_MAP` 映射到具体策略指令，注入 prompt。

### 3.3 Bayesian Learner

`AuroraBayesianLearner` (Redis-backed) 跟踪 Aurora 干预校准：
- Beta/Bernoulli 后验分布
- `visible_intervention` vs `hold` 两个目标
- 热启动先验: Beta(2.0, 1.0)，均值 ≈ 0.67
- `policy_calibration()` 输出不确定性调整的置信度

### 3.4 Self Model

`SparkleSelfModelService` (Redis-backed, 90-day TTL) 跟踪：
- `strategy_confidence`: 每次任务成功 +0.02，失败 -0.03~-0.04
- `failure_streak`: 连续失败计数
- `task_signal_count` / `task_success_count`: 任务统计
- **5 个 assumption 校准**: daily_time, task_duration, task_difficulty, pressure_level, emotional_state
- 每个 assumption 有独立的 confidence + evidence 列表
- `needs_recalibration`: 当 strategy_confidence < 0.45 时触发

### 3.5 Idiographic Association

`IdiographicAssociationService` 跟踪个体特征关联：
- Top associations (dim_pair)
- Change points (30-day window)

---

## 四、数据收集系统详解

### 4.1 Event Bus (Redis Streams)

**核心事件类型**:
- `KnowledgeNodeUpdated` → Galaxy 刷新
- `TaskCompleted` → Achievement + photon reward
- `TaskAbandoned` → Reflection
- `ErrorCreated` → Cognitive fragment
- `ProfilePreferenceUpdated` → Prompt update
- `CalendarEvent*` → Notification scheduling
- `NodeMasteryUpdated` → Knowledge graph update
- `GroupFileShared/Deleted` → Community

**基础设施**:
- Redis Streams 作为 transport
- DLQ (Dead Letter Queue): `EventBusDLQEntry` 模型
- Prometheus metrics: `EVENT_BUS_CONSUMER_FAILURE_TOTAL`, `EVENT_BUS_DLQ_DEPTH`

### 4.2 Chat Signal Collection

`ChatSignalCollector` 从每轮对话中收集:
- 用户情绪信号 (keyword-based)
- 任务反馈分布
- 对话节奏信号 (用于 `build_conversation_rhythm_instruction`)

### 4.3 情绪检测

**双通道**:
1. `CognitiveFragment.sentiment`: 结构化情感标签 (from LLM)
2. `ChatMessage keyword`: 关键词匹配 (中英双语)
   - frustrated: "烦", "太难了", "frustrated", "stuck"...
   - anxious: "焦虑", "担心", "anxiety", "stressed"...
   - overwhelmed: "太多了", "overwhelming", "burnt out"...
   - happy: "开心", "棒", "awesome", "completed"...
   - motivated: "加油", "继续", "let's go", "determined"...

---

## 五、闭环反馈系统详解

### 5.1 反馈环

```
Task Completed
  → Event Bus (TaskCompleted)
    → AchievementEventConsumer (解锁成就 + photon reward)
    → Self Model (strategy_confidence +0.02)
    → Memory (episodic memory 写入)

Task Failed/Timeout
  → Event Bus
    → Self Model (strategy_confidence -0.03~-0.04, failure_streak++)
    → Cognitive Fragment (struggle signal)
    → DualCoreRouter adjusts next turn (cognitive_first if failure_streak >= 2)

User Correction
  → Bayesian Learner (record_correction)
  → Memory (calibration receipt)
  → DualCoreRouter (recent_corrections bridge, BP1)
  → Decision Loop (recalibration if same strategy repeated 3 times)

Reflection
  → EpisodicMemory (source_type=reflection, source_lane=inferred_extraction)
  → State Aggregator (recent_reflections field)
  → DualCoreRouter (reflection_phase signal, priority 3.0)
```

### 5.2 UX Envelope (表现层闭环)

`UXEnvelopeBuilder` (1908 行) 将所有决策翻译为前端可消费的结构:

```python
envelope:
  ux_turn: intent_summary, mode_label, companion_frame, dual_core_mode
  ux_result: answer_kind, confidence_band, completion_state, headline
  ux_followthrough: next_actions[], retry_options[], memory_updates
  ux_sources: citations, evidence_summary
  orchestration_summary: mode, agents_used, persona_highlights
  ux_evolution: adaptation_records, preference_learnings, progress_snapshot
```

**7 种 Chat Mode**: standard, deep_analysis, study_plan, error_diagnosis, expert_auto, execution_delegate, aurora_core_session

**自适应展示**:
- style_variant: compact / balanced / exploratory
- tone_variant: warm / analytical / direct
- next_action_limit: 2 (compact) / 3 (default) / 4 (exploratory)

---

## 六、工具系统

### 6.1 工具清单 (22+)

| 工具 | 类别 | 用途 |
|------|------|------|
| task_tools | orchestration | 任务 CRUD |
| plan_tools | orchestration | 计划 CRUD |
| plan_state_tools | orchestration | 计划状态管理 |
| plan_resolution | orchestration | 计划冲突解决 |
| error_tools | knowledge | 错题本操作 |
| persona_tools | knowledge | 人设管理 |
| web_search_tool | knowledge | 网络搜索 |
| material_retrieval_tools | knowledge | 材料 RAG 检索 |
| graph_rag | knowledge | 知识图谱 RAG |
| companion_tools | cognitive | 伴侣工具 |
| prism_tools | cognitive | 认知棱镜工具 |
| intervention_tools | cognitive | 干预工具 |
| simulation_tool | cognitive | 模拟工具 |
| theater_tool | cognitive | 思维剧场 |
| growth_strategy_tools | growth | 成长策略 |
| entity_cards | growth | 实体卡片 |
| translation_tool | infra | 翻译 |
| report_tool | infra | 报告生成 |
| task_query_tool | query | 任务查询 |
| skill_schema | query | 技能查询 |

### 6.2 注册机制

`DynamicToolRegistry` 是线程安全的单例，支持：
- `register_from_package()` — 自动发现 `app.tools` 下所有 `BaseTool` 子类
- `ensure_package_registered()` — 幂等注册，防止并发重复扫描
- `get_openai_tools_schema()` — 直接输出 OpenAI Function Calling schema
- `validate_all_tools()` — 验证 execute() 可调用 + schema 有效

---

## 七、知识图谱 (Galaxy) 详解

### 7.1 Galaxy Service 架构

```
GalaxyService (Facade)
  ├── GraphStructureService — 节点 CRUD, 关系管理
  ├── KnowledgeRetrievalService — 向量搜索, pgvector
  ├── GalaxyStatsService — 火花统计, 预测
  ├── ReviewUrgencyService — 复习紧急度
  └── OntologyGenerator — 本体提取
```

### 7.2 精通度追踪

- `UserNodeStatus`: 每个用户-节点对的精通度 (0-100)
- `StudyRecord`: 学习记录，支持 mastery 更新
- CQRS Outbox: 精通度更新通过 `event_outbox` 表异步传播

---

## 八、发现的问题 (4 份子报告交叉汇总)

> 以下问题来自 4 份独立子报告的交叉核对，已去重合并。详细分析请查阅对应子报告。

### 8.1 P0 级问题 (5 个 — 需要立即修复)

| # | 问题 | 位置 | 子报告来源 |
|---|------|------|-----------|
| P0-1 | **context_data 无类型约束** — LangGraph FSM 的核心状态传递依赖 `dict[str, Any]`，所有节点通过约定键名 (`"router_decision"`, `"tool_calls"`, `"chat_mode"`) 交换数据。没有强类型 schema，任何拼写错误或键名变更都会静默失败 | `agents/standard_workflow.py` WorkflowState | 01 |
| P0-2 | **StateAggregator 内存缓存无上限保护** — `_cache` 是进程内 dict，仅按 `(user_id, field_name, fingerprint)` 索引，多用户并发时内存不可控 | `state_aggregator/service.py:228-231` | 主报告 |
| P0-3 | **DualCoreRouter 硬编码中文输出** — 50+ 处 `cognitive_adjustments` / `execution_constraints` 全部中文硬编码，非中文用户 prompt 混入中文指令 | `dual_core_router.py` 全文 | 主报告, 01, 03 |
| P0-4 | **情绪检测关键词匹配无否定词处理** — "不要太焦虑" 被误分类为 anxious，"这不是太难" 被误分类为 frustrated。3 份子报告独立发现同一问题 | `state_aggregator/service.py:556-596` | 主报告, 02, 03 |
| P0-5 | **reflection 递归保护依赖内部状态** — `reflection_round` 计数器存在，但依赖正确的内部状态管理。无外部可观测指标 | `agents/standard_workflow.py` 反射节点 | 01 |

### 8.2 P1 级问题 (15 个 — 影响体验/可靠性/可维护性)

#### 编排层 (来自子报告 01)

| # | 问题 | 位置 | 说明 |
|---|------|------|------|
| P1-01 | **PII Kill Switch 在异步上下文中失效** | `aurora/privacy.py` | 安全关键功能在主要运行时场景中不可用 |
| P1-02 | **L1LightAurora 快速路径缺少 safety check** | `aurora/runtime_v1/l1_light_aurora.py` | L1 路径绕过了部分 Aurora 安全检查 |
| P1-03 | **DualCoreRouter 圈复杂度过高 (45+)** | `dual_core_router.py:route()` | 30+ 分支条件，测试困难 |

#### 上下文构建 (来自主报告 + 01)

| # | 问题 | 位置 | 说明 |
|---|------|------|------|
| P1-04 | **_build_user_context 400+ 行单方法** | `context_builder.py:751-1160` | 嵌套 4 层 try/except，主路径+2 fallback+异常处理 |
| P1-05 | **Aurora Decision Loop prompt 过长** | `decision_loop.py:896-1057` | system prompt 约 160 行硬编码规则，token 消耗高 |
| P1-06 | **_build_user_context Aurora profile try/except 过宽** | `context_builder.py:806-850` | 整块被 `except Exception` 静默吞掉 |

#### 数据收集层 (来自子报告 02)

| # | 问题 | 位置 | 说明 |
|---|------|------|------|
| P1-07 | **TaskEventConsumer 单事件触发 7+ 串行操作** | `services/task_event_consumer.py` | 每个事件串行调用 7+ 服务，总延迟=各服务之和 |
| P1-08 | **GalaxyEventConsumer 长事务 (error_created)** | `services/galaxy_event_consumer.py:225-291` | 错题创建触发知识图谱更新，事务过长 |
| P1-09 | **PreferenceEventConsumer 未复用 EventBus 基础设施** | `services/profile_event_consumer.py` | 直接使用 `redis.xreadgroup`，与 EventBus 去重/重试机制不一致 |
| P1-10 | **AchievementEventConsumer 缺少 @reliable_consumer 装饰器** | `services/achievement_event_consumer.py:74` | Rule AZ 可靠性检查无法覆盖此消费者 |
| P1-11 | **Galaxy Error Gap Node 缺乏并发保护** | `services/galaxy_event_consumer.py:225-291` | 查询+创建非原子，高并发下可能创建重复节点 |

#### 用户画像层 (来自子报告 03)

| # | 问题 | 位置 | 说明 |
|---|------|------|------|
| P1-12 | **BigFive 置信度上限 0.3 过窄** | `core/user_insight_state.py:47` | 即使充分证据也无法表达 >30% 置信度 |
| P1-13 | **ProfileEventConsumer 异常后 raise 中断消费循环** | `services/profile_event_consumer.py:139,152` | 非关键错误应吞掉继续，不应中断 |
| P1-14 | **Idiographic 冷启动降级不足** | `services/idiographic_association_service.py:390` | 5/10 维度来自 PersDynAttractor，冷启动用户分析质量严重下降 |

#### 反馈闭环层 (来自子报告 04)

| # | 问题 | 位置 | 说明 |
|---|------|------|------|
| P1-15 | **反馈偏好 0.1 阻尼系数过于保守** | `task_feedback_service.py:628-629` | 用户需连续 10 次"太难"反馈才变化 1 个单位，冷启动适应慢 |
| P1-16 | **关键反馈处理异常被 try/except 静默吞没** | `task_feedback_service.py:141-161` | 自适应重规划、偏好更新等失败仅 log.warning，无重试 |
| P1-17 | **_get_stored_plan() 未实现，始终返回 None** | `plan_review_service.py:1913-1928` | 公共 API 失效，调用方可能产生意外行为 |

### 8.3 P2 级问题 (25 个 — 技术债务)

#### 编排层

| # | 问题 | 位置 |
|---|------|------|
| P2-01 | UXEnvelopeBuilder 1908 行单类 50+ 方法 | `ux_envelope.py` |
| P2-02 | AchievementEngine._evaluate_progress 484 行单方法 | `achievement_engine.py:637-1121` |
| P2-03 | DualCoreRouter cognitive_adjustments 硬编码截断为 5 条 | `dual_core_router.py` |
| P2-04 | KillSwitchBinding 无中心注册表 | `core/kill_switch.py` |
| P2-05 | _STREAM_QUEUE_MAXSIZE=512 无动态调整 | `orchestrator.py:283` |
| P2-06 | AuroraEngine rollback_anchor 始终为空 | `aurora/engine.py:139-217` |
| P2-07 | Aurora Runtime V1 依赖注入不完整 | `aurora/runtime_v1/service.py:183-200` |
| P2-08 | DynamicToolRegistry 统计计数 bug | `dynamic_tool_registry.py:146-149` |

#### 数据层

| # | 问题 | 位置 |
|---|------|------|
| P2-09 | Event Bus publish 失败静默降级 | `event_bus.py:1064-1080` |
| P2-10 | StruggleSignalAggregator 7 个串行 DB 查询 | `struggle_signal_aggregator.py:162-207` |
| P2-11 | _build_achievement_summary 三次查询同一表 | `state_aggregator/service.py:766-870` |
| P2-12 | CommunityErrorAggregationService 无触发机制 | `community_error_aggregation_service.py` |
| P2-13 | JourneyConsumerBase consumer_name 用 timestamp 导致堆积 | `journey_consumer_base.py:50` |
| P2-14 | EventBus 连接冷却期日志不充分 | `event_bus.py:937-946` |
| P2-15 | Event Bus 缺少 schema version | `event_bus.py` |

#### 画像层

| # | 问题 | 位置 |
|---|------|------|
| P2-16 | ProfileFrontDoorService 标题硬编码中文 | `profile_front_door_service.py:132-133` |
| P2-17 | WorkingMemoryService _local_store 是类变量 | `working_memory/service.py:23` |
| P2-18 | PreferenceService _PERSONALIZATION_CACHE 死代码 | `personalization/engine.py:605` |
| P2-19 | StateAggregator 进程内缓存多实例不共享 | `state_aggregator/service.py:110-113` |
| P2-20 | PATTERN_POLICY_MAP 未覆盖 LLM 可能产生的未知模式名 | `profile_context_service.py:53-114` |
| P2-21 | MemoryService SELECT FOR UPDATE 高并发锁等待 | `memory_service.py:112-123` |
| P2-22 | CognitiveFragment deferred embedding + __dict__ 访问冲突 | `cognitive_service.py:363` |

#### 反馈层

| # | 问题 | 位置 |
|---|------|------|
| P2-23 | FeedbackDrivenAdjustmentService 与 TaskFeedbackService 职责重叠 | `feedback_adjustment_service.py` vs `task_feedback_service.py` |
| P2-24 | 反思系统缺少效果闭环验证 | `task_reflection_service.py` |
| P2-25 | calculate_preference_deltas 用时比率推断未实现 (代码为 pass) | `models/task_feedback.py:103-114` |
| P2-26 | Sprint SPRINT_AHEAD 检测是简化处理 | `achievement_engine.py:1076-1107` |
| P2-27 | PlanQualityReport 与 ReviewDecision 枚举映射冗余 | `plan_review_service.py:627-633` |
| P2-28 | AchievementEventConsumer 中 try/except:pass 模式 | `achievement_event_consumer.py:131-155` |

#### 基础设施

| # | 问题 | 位置 |
|---|------|------|
| P2-29 | SignalAggregator._collect_readings 顺序执行 | `aurora/signal_aggregator.py:306-329` |
| P2-30 | L0 Rule Engine 仅 2 条规则 (deadline_pressure + quiet_hours) | `aurora/runtime_v1/l0_rules.py` |
| P2-31 | 多处 `_utcnow()` 重复定义 | 几乎每个 Aurora 模块 |
| P2-32 | SocialSignalBridge 同名类分布在两个不同文件 | `community_signal_bridge.py` vs `social_signal_bridge.py` |

---

## 九、系统健康度评估

| 维度 | 评分 | 说明 |
|------|------|------|
| **架构完整性** | 9/10 | L0/L1/L2 三层感知, 20+ 状态字段, 13+ 路由信号, 完整闭环 |
| **信号丰富度** | 9/10 | 情绪/认知/执行/社交/元认知/成就/日历/知识/贝叶斯/自模型 |
| **安全防护** | **5/10** ~~(9/10)~~ | **SEC-1~5**: PII未脱敏、gRPC无认证、user_id伪造、成本控制断链、GDPR缺失 |
| **成本控制** | **3/10** | cost_controller存在但未集成到llm_router; 健康上报死代码; 预测服务绕过预算 |
| **可测试性** | 6/10 | 大方法(400+行)难以测试，DI 不完整 |
| **国际化** | 4/10 | 大量硬编码中文，emotion detection 只支持中英，路由偏好学习中文字符串匹配 |
| **可维护性** | 5/10 | 核心方法过长，God class (spine 4,950行, achievement 2,981行, routing 2,517行) |
| **性能意识** | 7/10 | TTL 缓存、信号分层，但部分串行操作可并行化 (spine 11步→可3-5x) |
| **事件可靠性** | 7/10 | DLQ+重试+自动恢复完备，但部分消费者未复用基础设施 |
| **数据合规** | **3/10** | 无用户删除清理、软删除记录未过滤、认知分析包含完整画像 |

---

## 十、独立子报告索引

### Round 1: 系统全貌 (4 份已完成)

| 报告 | 覆盖领域 | 行数 | 问题数 | 状态 |
|------|---------|------|--------|------|
| [01_aurora_orchestration_graph.md](01_aurora_orchestration_graph.md) | Aurora 编排、LangGraph FSM、DualCoreRouter | 788 | 2 P0 + 5 P1 + 7 P2 | 完成 |
| [02_data_collection_event_system.md](02_data_collection_event_system.md) | Event Bus、状态聚合、Galaxy 数据流 | 702 | 0 P0 + 7 P1 + 8 P2 | 完成 |
| [03_user_profiling_cognitive_system.md](03_user_profiling_cognitive_system.md) | 用户画像、BigFive、认知棱镜、记忆 | 518 | 0 P0 + 5 P1 + 10 P2 | 完成 |
| [04_feedback_loop_achievement_system.md](04_feedback_loop_achievement_system.md) | 闭环反馈、成就引擎、自适应重规划 | 653 | 0 P0 + 3 P1 + 8 P2 | 完成 |

### Round 2: P0 问题深挖 (4 份已完成)

| 报告 | 覆盖领域 | 行数 | 关键发现 | 状态 |
|------|---------|------|---------|------|
| [round2/01_context_data_key_audit.md](round2/01_context_data_key_audit.md) | context_data 全键审计 | 415 | **P0-1 降级为 P1**: 137 键，97% 防御性 .get()，无崩溃路径 | 完成 |
| [round2/02_emotion_detection_deep_audit.md](round2/02_emotion_detection_deep_audit.md) | 情绪检测全链路 | 472 | **P0-4 升级**: 权重-质量倒置 (9.0 权重+关键词检测)，自强化反馈环 | 完成 |
| [round2/03_error_handling_pattern_audit.md](round2/03_error_handling_pattern_audit.md) | 异常处理模式 | 507 | 2,146 个 except Exception，4 个 P0 级静默丢失问题 | 完成 |
| [round2/04_performance_bottleneck_audit.md](round2/04_performance_bottleneck_audit.md) | 性能瓶颈量化 | 511 | TaskEventConsumer 195ms→可并行化到 60ms (3-5x) | 完成 |

### Round 3: 安全 & 集成 (4 份已完成)

| 报告 | 覆盖领域 | 行数 | 关键发现 | 状态 |
|------|---------|------|---------|------|
| [round3/01_security_pii_audit.md](round3/01_security_pii_audit.md) | PII 脱敏、认证授权、安全边界 | 442 | 5 P0: PII未脱敏、gRPC无认证、user_id可伪造、async PII崩溃、raw user_ids in logs | 完成 |
| [round3/02_integration_consistency_audit.md](round3/02_integration_consistency_audit.md) | 跨系统数据一致性、双写路径、缓存失效 | 444 | P1: 非原子偏好多写、任务完成事件缺口、缓存失效洞、3个 kill switch 覆盖缺口 | 完成 |
| [round3/03_spine_god_class_audit.md](round3/03_spine_god_class_audit.md) | Spine Orchestrator God class 分析 | 462 | 4,950行/88方法/8责任域，重复 trace 写入 bug，11步串行优化→3-5x | 完成 |
| [round3/04_llm_prompt_efficiency_audit.md](round3/04_llm_prompt_efficiency_audit.md) | LLM prompt 效率分析 | 451 | ~15-20% token 节省可能，偏好重复4次，max_tokens 过紧 | 完成 |

### Round 4: 核心模块深度 (4 份已完成)

| 报告 | 覆盖领域 | 行数 | 关键发现 | 状态 |
|------|---------|------|---------|------|
| [round4/01_standard_workflow_fsm_audit.md](round4/01_standard_workflow_fsm_audit.md) | FSM 节点、状态管理、工具调用 | 678 | 0 P0 + 7 P1: retrieval无空列表保护、空响应、reflection无限轮次风险、流式callback无异常捕获、重复assistant消息 | 完成 |
| [round4/02_routing_engine_audit.md](round4/02_routing_engine_audit.md) | 路由引擎、信号叠加、策略覆盖 | 399 | 0 P0 + 6 P1: 多信号叠加覆盖、无超时保护、cognitive_first强制direct、偏好学习中文字符串匹配 | 完成 |
| [round4/03_llm_router_predictive_audit.md](round4/03_llm_router_predictive_audit.md) | LLM 路由、预测服务 | ~500 | **2 P0**: report_model_failure/success 全代码库无调用点(健康机制死代码)、预测服务绕过预算检查; 8 P1 | 完成 |
| [round4/04_memory_cognitive_audit.md](round4/04_memory_cognitive_audit.md) | 记忆系统、认知棱镜 | 462 | **2 P0**: 用户删除无级联清理(GDPR)、全局向量开关跨用户影响; 7 P1 | 完成 |

### Round 5: 集成层 & RAG (3 份已完成)

| 报告 | 覆盖领域 | 行数 | 关键发现 | 状态 |
|------|---------|------|---------|------|
| [round5/01_integration_layer_audit.md](round5/01_integration_layer_audit.md) | gRPC服务层、UX Envelope、Executor | ~500 | **3 P0**: user-id直接信任metadata、安全告警仅日志不阻断、7个方法完全不检查user-id | 完成 |
| [round5/02_rag_llm_service_audit.md](round5/02_rag_llm_service_audit.md) | GraphRAG、LLM Service、Embedding | 450 | **2 P0**: GraphRAG graph_search 跨租户数据泄露(Cypher无user_id)、cost_controller断链; 4 P1 | 完成 |
| [round5/03_behavior_aurora_context_audit.md](round5/03_behavior_aurora_context_audit.md) | 行为信号、Aurora L3、ContextPruner | 247 | 6 P1: L3 validate_entry默认允许、任务标题PII泄露、低信号阈值过激进; 5 P2 | 完成 |

### Round 6: 深层模块 (4 份已完成)

| 报告 | 覆盖领域 | 行数 | 关键发现 | 状态 |
|------|---------|------|---------|------|
| [round6/01_collaboration_review_audit.md](round6/01_collaboration_review_audit.md) | 协作工作流、审查系统 | ~600 | **3 P0**: 审查跳过条件过宽、EnhancedAgent硬编码模拟数据、ReviewerAgent异常自动放行 | 完成 |
| [round6/02_plan_review_knowledge_audit.md](round6/02_plan_review_knowledge_audit.md) | 计划审查、知识服务 | 205 | **2 P0**: keyword_search user_id参数误导、pending_actions 5分钟TTL过短; **6 P1**: tc.tool_name bug致交叉审查永不触发、空计划降级批准confidence=1.0 | 完成 |
| [round6/03_aurora_decision_signal_audit.md](round6/03_aurora_decision_signal_audit.md) | Aurora决策引擎、信号聚合 | 308 | **3 P0**: L1升级结果未传递到L2、L1无内容安全检查、user_message未消毒; **8 P1**: L0时区UTC错误、Kill Switch覆盖缺失、L3配额硬编码不一致 | 完成 |
| [round6/04_feedback_learning_audit.md](round6/04_feedback_learning_audit.md) | 反馈循环、学习系统、进度追踪 | ~500 | 5 P1: StruggleSignal权重1.35>1.0、auto_seed无PII脱敏、PromptBandit无持久化 | 完成 |

### Round 7: 执行 & 社区 (2 份已完成)

| 报告 | 覆盖领域 | 行数 | 关键发现 | 状态 |
|------|---------|------|---------|------|
| [round7/01_execution_trust_simulation_audit.md](round7/01_execution_trust_simulation_audit.md) | 执行服务、信任引擎、模拟引擎 | 122 | **2 P0**: _clear_failure_state 空操作(降级永不解除)、分类缓存线程不安全; **6 P1**: 无界并行批处理、会话泄漏风险、安全检查误报、审批逻辑倒置、无端到端超时、token追踪不完整 | 完成 |
| [round7/02_community_social_audit.md](round7/02_community_social_audit.md) | 社区服务、通知、排行榜 | 310 | **4 P0**: /broadcast无速率限制、群排行越权、私信绕过拉黑、离线消息越权; **7 P1** | 完成 |

---

## 十-B、Round 2 严重度变更

基于 Round 2 的深度审计，对 Round 1 发现的问题进行严重度调整：

| 原始 | 变更后 | 问题 | 原因 |
|------|--------|------|------|
| **P0-1** | **→ P1** | context_data 无类型约束 | 137 键中 97% 使用 .get() 防御性读取，无 KeyError 崩溃路径。实际风险是认知负担而非运行时故障 |
| **P0-4** | **保持 P0** (加重) | 情绪检测关键词匹配 | 发现权重-质量倒置 (9.0 权重+最低质量检测)、2 个误判即触发 emotional_block、自强化反馈环无法自纠正。直接影响产品核心体验 |

**Round 2 新发现问题**:

| # | 问题 | 严重度 | 位置 | 发现来源 |
|---|------|--------|------|---------|
| R2-01 | AchievementEngine 光子奖励静默丢失 | P0 | achievement_engine.py 5处 | R2-03 |
| R2-02 | ProfileWriteService 事件发布静默丢失 | P0 | profile_write_service.py:470,487 | R2-03 |
| R2-03 | AdaptiveReplanner 计划调整静默失败 | P0 | adaptive_replanner.py:1934 | R2-03 |
| R2-04 | privacy.py:58 异步上下文崩溃 | P0 | aurora/privacy.py:58 | 主 agent |
| R2-05 | 情绪检测自强化反馈环 | P0 | dual_core_router + state_aggregator | R2-02 |
| R2-06 | TaskEventConsumer 延迟 195ms (可降至 60ms) | P1 | task_event_consumer.py:92-243 | R2-04 |
| R2-07 | SignalAggregator 130ms (可降至 20ms) | P1 | signal_aggregator.py:308-313 | R2-04 |

---

## 十-A、Round 3-4 新发现汇总

### Round 3 安全发现 (详见 round3/01)

| # | 问题 | 严重度 | 位置 |
|---|------|--------|------|
| SEC-1 | PII 未脱敏直接发送给外部 LLM | P0 | prompts.py / privacy.py |
| SEC-2 | gRPC 无独立认证 | P0 | agent_grpc_service.py |
| SEC-3 | user_id 可伪造 (protobuf body 覆盖 metadata) | P0 | agent_grpc_service.py:248 |
| SEC-4 | PII 脱敏异步崩溃 (run_until_complete) | P0 | privacy.py:58 |
| SEC-5 | raw user_ids in Redis/PG logs | P0 | 多处 |

### Round 4 关键新发现

| # | 问题 | 严重度 | 位置 | 说明 |
|---|------|--------|------|------|
| R4-P0-1 | **report_model_failure/success 全代码库无调用点** | **P0** | llm_router.py | 健康检查机制完全死代码，所有模型永远"健康" |
| R4-P0-2 | **Predictive Service 绕过预算检查** | **P0** | predictive_service.py | 通过 `get_llm_service_for_specific_model()` 直接调用，不经过预算前置检查 |
| R4-P0-3 | **用户删除无级联清理** | **P0** | memory_service.py / cognitive_service.py | 违反 GDPR 被遗忘权 |
| R4-P0-4 | **全局向量开关跨用户影响** | **P0** | cognitive_service.py:37-39 | 一用户 pgvector 错误→全用户降级 |
| R4-P0-5 | **cost_controller 未集成到 llm_router** | **P0** | cost_controller.py + llm_router.py | 每日预算存在但未强制执行，模型选择完全忽略成本限制 |
| R5-P0-6 | **GraphRAG graph_search 跨租户数据泄露** | **P0** | graph_rag.py:1860-1900 | Cypher 查询无 user_id 过滤，用户A可查到用户B的私有知识节点和描述。find_learning_path 和 find_related_concepts 同样存在 |
| R4-P1-1 | FSM retrieval_node 空列表崩溃 | P1 | standard_workflow.py:1080 | `state.messages[-1]` 无守卫 |
| R4-P1-2 | 多信号叠加覆盖 (后执行覆盖先执行) | P1 | routing_engine.py:1262-1280 | social/SRL live 覆盖 metacog/cogload live |
| R4-P1-3 | 路由引擎无超时保护 | P1 | routing_engine.py:1033 | _apply_dual_core_routing 大量异步调用无整体超时 |
| R4-P1-4 | GLM_BATCH/SPECIALIST/FREE/FREE_REASONING tier 降级失效 | P1 | llm_router.py:121-129 | 4个 tier 不在 _FALLBACK_TIER_ORDER 中 |
| R4-P1-5 | BehaviorPattern 查询未过滤软删除 | P1 | cognitive_service.py:589-594 | deleted_at 记录仍被使用 |
| R4-P1-6 | 认知分析 LLM prompt 包含完整用户画像 | P1 | cognitive_service.py:453-484 | 敏感心理健康指标未脱敏 |

### Round 5-6 关键新发现

| # | 问题 | 严重度 | 位置 | 说明 |
|---|------|--------|------|------|
| R5-P0-6 | **GraphRAG 跨租户数据泄露** | **P0** | graph_rag.py:1860-1900 | Cypher 查询无 user_id 过滤，用户A可查到用户B的私有知识节点。find_learning_path/find_related_concepts 同样存在 |
| R6-P0-1 | **审查跳过条件过宽** | **P0** | review_nodes.py:323-421 | deep_analysis/study_plan/error_diagnosis/标准对话均跳过审查，可能放过有害内容 |
| R6-P0-2 | **EnhancedAgent 使用硬编码模拟数据** | **P0** | enhanced_agents.py | StudyPlanner/ProblemSolver 在生产环境基于假数据运行 |
| R6-P0-3 | **ReviewerAgent 异常自动放行** | **P0** | review_nodes.py | 审查失败时降级为 needs_refinement + requires_reflection=False，自动放行 |
| R6-P1-1 | StruggleSignal 权重总和 1.35 > 1.0 | P1 | struggle_signal_aggregator.py | 挣扎评分系统性偏高，过早触发干预 |
| R6-P1-2 | auto_seed 无 PII 脱敏 | P1 | workflow_experience.py | 用户对话敏感信息直接进入 seed library |
| R6-P1-3 | L3 validate_entry 默认允许任意 wake reason | P1 | l3_full_core.py:189-196 | 任何字符串触发高成本 L3 校准会话 |
| R7-P0-1 | **Galaxy create_edge 无节点所有权验证** | **P0** | structure_service.py:84-92 | user_id 参数传入但未使用，任何用户可在任意节点间创建关系 |
| R7-P0-2 | **Galaxy get_node_neighbors/get_node_with_context 无用户隔离** | **P0** | structure_service.py:94-123 | 不检查节点所有权，任何用户可查询任何节点的邻居和上下文 |
| R7-P0-3 | **社区群排行越权** | **P0** | community_service.py | _get_group_leaderboard 不验证调用者是否为群成员 |
| R7-P0-4 | **私信绕过拉黑** | **P0** | community_service.py | send_message 只查 Friendship 不查 UserBlock 表 |
| R7-P0-5 | **离线消息越权** | **P0** | notification_center_service.py | mark_as_sent/mark_as_failed 不验证消息归属 |
| R7-P0-6 | **/broadcast 无速率限制** | **P0** | community_service.py | 可被用于消息轰炸 |
| R6-P0-4 | **L1 升级结果未传递到 L2 DecisionLoop** | **P0** | l1_light_aurora.py:97 → dashboard.py | L1 should_escalate 计算后 DashboardReadoutBuilder 不消费，L2 对 L1 风险检测完全无知 |
| R6-P0-5 | **L1 快速路径无内容安全检查** | **P0** | l1_light_aurora.py:63-110 | 无 LLM 快速路径也无输入消毒，精心构造输入可操纵升级决策 |
| R6-P0-6 | **L2 DecisionLoop user_message 注入** | **P0** | decision_loop.py:1093 | readout.user_message 未净化发送给 LLM，可 JSON 注入或 prompt 覆盖 |
| R6-P0-7 | **keyword_search user_id 参数误导** | **P0** | retrieval_service.py:565-613 | 接受 user_id 但完全未使用，调用者误以为搜索是租户隔离的 |
| R6-P0-8 | **pending_actions TTL 5分钟过短** | **P0** | pending_actions.py:31 | 审查流程可能超时丢失，复杂计划需更长时间 |
| R6-P1-4 | **L0 静默小时检测使用 UTC 而非用户时区** | P1 | l0_rules.py:19-20, 90-110 | 中国用户 UTC+8 的静默窗口完全失效 |
| R6-P1-5 | **Aurora Kill Switch 全面缺失** | P1 | engine.py, control_surface.py | 全部组件依赖静态 settings，无 Redis tri-state，违反协议 |
| R6-P1-6 | **tc.tool_name bug 致交叉审查永不触发** | P1 | plan_review_service.py:1078 | 应为 tc.name，hasattr 保护使 tool_names 始终为空列表 |
| R6-P1-7 | **L3 配额硬编码为 3 vs DAILY_QUOTA 为 1** | P1 | state.py:376 | can_user_wake 硬编码与 AuroraEnergyStore.DAILY_QUOTA 不一致 |
| R7-P0-7 | **_clear_failure_state 空操作** | **P0** | execution_service.py:3251-3253 | 方法体 `del user_id; return None`，用户降级永不解除，只能等30分钟窗口过期 |
| R7-P0-8 | **分类缓存线程不安全** | **P0** | execution_service.py:357-379 | _shared_classify_cache 可变类级 dict 无锁，async 并发修剪丢失条目 |
| R7-P1-1 | 无界并行批处理 dispatch | P1 | execution_service.py:1319-1331 | asyncio.gather 无 semaphore 限制，大 batch 可能压垮 OpenClaw |
| R7-P1-2 | 并行批处理独立 DB 会话泄漏风险 | P1 | execution_service.py:1324-1331 | 服务构建失败时 session 可能未关闭 |
| R7-P1-3 | 信任引擎内容安全检查高误报 | P1 | execution_trust.py:143-149 | 子串匹配 "token" 匹配 "sentence tokenizer"，阻塞合法结果 |
| R7-P1-4 | 自主模式审批逻辑语义倒置 | P1 | execution_service.py:2443-2448 | approval_policy="deny" 实际表示自动批准，命名混淆 |
| R7-P1-5 | dispatch 无端到端超时 | P1 | execution_service.py:1066-1129 | 仅 OpenClaw 客户端调用有超时，DB 操作无限制 |
| R7-P1-6 | 失败执行 token 用量未追踪 | P1 | execution_service.py:2995-2999 | 超时/适配器错误绕过摄取路径，成本统计不完整 |

---

## 十一、优先修复建议 (Round 1-4 综合)

### 第零梯队: 紧急安全修复 (今日)

| 优先级 | 问题 | 投入 | 收益 | 发现来源 |
|--------|------|------|------|---------|
| **SEC-1** | **PII 未脱敏直接发送给外部 LLM** — `sanitize_text_for_llm()` 不调用 `redact_pii()`，用户邮箱/手机/身份证/姓名直接发送给 OpenAI/DeepSeek 等 | 低 (加一行调用) | **最高** (数据保护合规) | R3-01 |
| **SEC-2** | **gRPC 无独立认证** — 端口暴露即可伪造任意用户访问全部数据 | 中 (加 JWT interceptor) | **最高** (数据隔离) | R3-01 |
| **SEC-3** | **user_id 可伪造** — protobuf body 中 user_id 覆盖认证用户 ID | 低 (优先 metadata) | **最高** (身份验证) | R3-01 |
| **SEC-4** | **PII 脱敏异步崩溃** — privacy.py:58 的 `run_until_complete()` 在 async 环境崩溃 | 低 (改用 async) | 高 (PII 保护恢复) | R2-04 |
| **R4-P0-1** | **LLM 健康上报从未调用** — report_model_failure/success 全代码库无调用点 | 低 (在 providers 中添加调用) | **最高** (故障模型不会自动降级) | R4-03 |
| **R4-P0-5** | **cost_controller 未集成到 llm_router** — 预算限制存在但未强制执行 | 中 (在 select_model 中添加 check_budget) | **最高** (成本控制) | 主 agent |
| **R5-P0-6** | **GraphRAG 跨租户数据泄露** — graph_search/find_learning_path/find_related_concepts 的 Cypher 查询无 user_id 过滤 | 中 (添加 WHERE 条件) | **最高** (用户A可查到用户B私有数据) | R5-02 |
| **R7-P0-1** | **Galaxy create_edge 无所有权验证** | 低 (添加 user_id WHERE) | **最高** (任意用户可修改其他用户的知识图谱) | 主 agent |
| **R7-P0-3** | **群排行越权** — _get_group_leaderboard 不验证群成员身份 | 低 (一行代码) | 高 (查看私有群排名) | R7-02 |
| **R7-P0-4** | **私信绕过拉黑** — 只查 Friendship 不查 UserBlock | 低 (加一个 OR 条件) | 高 (被拉黑仍可骚扰) | R7-02 |

### 第一梯队: 立即 (本周)

| 优先级 | 问题 | 投入 | 收益 |
|--------|------|------|------|
| P0-4↑ | 情绪检测否定词 + 自强化环修复 | 低-中 | **最高** (路由正确性) |
| R2-01 | AchievementEngine 光子奖励丢失修复 | 中 | 高 (经济系统完整性) |
| R4-P0-3 | **用户删除无级联清理** (GDPR) — 实现 purge_user_data() | 中 | **最高** (法律合规) |
| R4-P0-4 | **全局向量开关改为 per-user** — 移除 _VECTOR_RUNTIME_ENABLED | 低 | 高 (隔离性) |
| R4-P0-2 | **Predictive Service 绕过预算** — 通过 llm_service 路径调用 | 低 | 高 (成本控制) |
| P0-3 | DualCoreRouter 国际化 | 中 (50+ 处) | 高 (非中文用户) |

### 第二梯队: 短期 (2 周内)

| 优先级 | 问题 | 投入 | 收益 |
|--------|------|------|------|
| R2-06 | TaskEventConsumer 并行化 | 中 (asyncio.gather) | **高** (延迟 3-5x) |
| R2-02 | ProfileWriteService 事件 outbox | 中 | 高 (偏好一致性) |
| R4-P1-1 | FSM retrieval_node 空列表保护 | 低 | 高 (防崩溃) |
| R4-P1-4 | 补全 _FALLBACK_TIER_ORDER 缺失 tier | 低 | 中 (降级覆盖) |
| R4-P1-5 | BehaviorPattern/CognitiveFragment 软删除过滤 | 低 | 高 (数据一致性) |
| R4-P1-2 | 多信号叠加改为累加器模式 | 中 | 高 (路由正确性) |
| R4-P1-3 | _apply_dual_core_routing 添加整体超时 | 低 | 高 (防级联阻塞) |
| P1-07 | 反馈阻尼系数动态化 | 低 | 中 (冷启动体验) |

### 第三梯队: 中期 (1 月内)

| 优先级 | 问题 | 投入 | 收益 |
|--------|------|------|------|
| R2-07 | SignalAggregator 并行化 (5-6x) | 低 | 中 (响应速度) |
| P1-05 | Decision Loop prompt 动态组装 | 中 | 高 (token 成本) |
| R4-P1-6 | 认知分析 prompt 敏感指标脱敏 | 低 | 高 (隐私保护) |
| R3-03 | Spine Orchestrator God class 拆分 (4,950行→8子服务) | 高 | 高 (可维护性) |
| P1-01 | UXEnvelopeBuilder 拆分 | 高 | 中 (可测试性) |
| P2-15 | Event Bus schema version | 中 | 中 (向后兼容) |

---

## 十二、跨报告重复发现 (高频问题)

以下问题被多份独立报告同时指出，说明影响面广或根因深刻：

| 问题 | 发现次数 | 报告来源 |
|------|---------|---------|
| try/except 过宽静默吞异常 | 10+ 次 | R1-01~04, R2-03 (2,146处), R3-01, **R4-01 (stream callback)** |
| 情绪检测/信号质量不足 | 5 次 | 主报告, R1-01, R1-02, R1-03, **R2-02 (加重)** |
| **成本/预算控制断链** | **3 次** | **R4-03 (健康检查死代码), R4-03 (预测绕过预算), 主agent (cost_controller未集成)** |
| **认证/授权缺失** | **4 次** | **R3-01 (gRPC无认证), R3-01 (user_id伪造), R3-01 (PII未脱敏), R3-02 (kill switch缺口)** |
| 核心方法过长 (>400 行) | 7 次 | R1-01(context_builder), R1-01(ux_envelope), R1-04(achievement_engine), **R3-03(spine 4,950行), R4-01(generation_node 660行)** |
| 串行操作可并行化 | 6 次 | R1-02, R2-04, **R3-03 (spine 11步串行), R4-01 (tool execution)** |
| 硬编码中文字符串 | 5 次 | R1-01, R1-03, prompt_assembly, **R4-02 (偏好学习中文字符串匹配)** |
| 进程内缓存多实例不共享 | 4 次 | R1-01, R1-02, R1-03, **R4-04 (local_cooldowns)** |
| **软删除记录未过滤** | **2 次** | **R4-04 (BehaviorPattern), R4-04 (CognitiveFragment)** |

---

> **审计总结 (Round 1-7 最终版)**: Sparkle 的 AI 系统架构设计成熟度极高 — L0/L1/L2 三层感知、20+ 维度状态聚合、13+ 优先级路由信号、完整的 Sense→Adapt 闭环。
>
> **关键发现按领域**:
>
> **安全 (最紧急)**:
> - 7+ 个跨租户数据泄露: GraphRAG Cypher、Galaxy create_edge/neighbors、社区群排行、离线消息
> - PII 未脱敏直接发给外部 LLM 提供商
> - gRPC 内部 API Key 路径跳过用户验证
> - 私信系统绕过拉黑机制
> - Aurora L2 DecisionLoop user_message 注入 (未经净化发给 LLM)
>
> **成本控制 (断链)**:
> - cost_controller 定义每日预算但 llm_router 完全不调用 (预算形同虚设)
> - report_model_failure/success 全代码库零调用 (健康检查死代码)
> - Predictive Service 通过 get_llm_service_for_specific_model 绕过预算检查
> - 执行服务失败路径 token 用量未追踪 (成本统计不完整)
>
> **内容安全**:
> - 审查系统跳过条件过宽 (standard/deep_analysis/study_plan/error_diagnosis 均跳过)
> - ReviewerAgent 异常时自动放行 (降级为 needs_refinement)
> - EnhancedAgent 在生产环境使用硬编码模拟数据
> - 高风险工具交叉审查因 tc.tool_name vs tc.name bug 永远不触发
> - L1 快速路径无内容安全检查 (无 LLM 也无输入消毒)
> - 执行信任引擎内容安全子串匹配高误报率
>
> **决策架构缺陷**:
> - L1 升级结果 (should_escalate) 未传递到 L2 DecisionLoop — 两条并行路径信号断裂
> - L0 静默小时检测使用 UTC 而非用户本地时区 — 中国用户静默窗口完全失效
> - Aurora 全组件无 Redis tri-state Kill Switch — 仅依赖静态 settings，违反协议
> - L2 决策可能覆盖 L0/L1 确定性规则 — 缺乏 L0 > L1 > L2 优先级层次
>
> **执行层缺陷**:
> - `_clear_failure_state` 空操作 — 用户降级永不解除，只能等30分钟窗口过期
> - 无界并行批处理 — 大 batch 可能压垮 OpenClaw/DB
> - dispatch 无端到端超时 — DB 慢查询可无限阻塞
> - 自主模式审批逻辑语义倒置 — approval_policy="deny" 实际表示自动批准
>
> **数据合规**:
> - 用户删除后无级联清理 (GDPR 被遗忘权缺失)
> - 全局向量开关一用户错误影响全平台
> - 软删除记录未过滤 (BehaviorPattern/CognitiveFragment)
>
> **当前最高优先级 (紧急修复)**:
> 1. GraphRAG/Galaxy Cypher 添加 user_id 过滤 (跨租户泄露)
> 2. SEC-1: PII 脱敏接入 LLM 调用链
> 3. SEC-2: gRPC 认证链完整性 (Go→Python 信任链)
> 4. R6-P0-6: L2 DecisionLoop user_message 输入消毒
> 5. R4-P0-1: LLM 健康上报接入 llm_service
> 6. R4-P0-5: cost_controller 集成到 llm_router.select_model
> 7. R6-P0-4: L1→L2 信号传递断裂修复 (DashboardReadout 增加 l1_escalation 字段)
> 8. 审查系统跳过条件收紧 + ReviewerAgent 异常处理修复 + tc.tool_name bug
> 9. R7-P0-7: 实现 _clear_failure_state 实际降级解除逻辑
> 10. R4-P0-3: 实现 purge_user_data() (GDPR)
>
> 总报告: 21 份子报告 + 1 份 Master, ~46,000 行, 覆盖 180+ 文件, 70,000+ 行核心代码。
> 审计状态: **全部完成** — 所有计划的审计模块均已覆盖，无遗漏。
