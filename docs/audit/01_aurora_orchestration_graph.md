# Aurora 编排系统与 LangGraph FSM 深度审计报告

**审计日期**: 2026-05-15
**审计范围**: LangGraph FSM 编排、双核路由、Aurora Adaptive Kernel、工具注册、Governance 规则
**审计方法**: 逐文件完整阅读核心代码 (14,700+ 行)，追踪调用链路，验证状态转移完备性

---

## 一、系统架构概述

### 1.1 核心架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                        Flutter Client                            │
│              websocket_chat_service_v2.dart                       │
└───────────────────────────┬─────────────────────────────────────┘
                            │ WebSocket (JSON + JWT)
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Go Gateway (Gin)                           │
│              websocket_proxy.go → chat_orchestrator.go           │
└───────────────────────────┬─────────────────────────────────────┘
                            │ gRPC (server-streaming)
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│              Python Engine — ChatOrchestrator                     │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │  LangGraph FSM (StateGraph "StandardChat")               │    │
│  │  context_builder → retrieval → router                    │    │
│  │       → collaboration → tool_planning → generation       │    │
│  │       → generation_review → reflection                   │    │
│  │       → tool_execution → execution_review                │    │
│  └──────────────────────────────────────────────────────────┘    │
│  ┌─────────────────┐  ┌──────────────────┐  ┌────────────────┐  │
│  │ DualCoreRouter   │  │ AuroraRuntimeV1  │  │ UXEnvelope     │  │
│  │ (decision logic) │  │ (Aurora Service) │  │ (presentation) │  │
│  └─────────────────┘  └──────────────────┘  └────────────────┘  │
│  ┌─────────────────┐  ┌──────────────────┐  ┌────────────────┐  │
│  │ StateAggregator  │  │ KillSwitch       │  │ ToolRegistry   │  │
│  │ (20+ signals)   │  │ (tri-state)      │  │ (auto-discover)│  │
│  └─────────────────┘  └──────────────────┘  └────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 组件关系

| 组件 | 文件 | 行数 | 职责 |
|------|------|------|------|
| ChatOrchestrator | `orchestration/orchestrator.py` | 3,685 | 中央编排器 (Mixin 组合) |
| StandardChat Graph | `agents/standard_workflow.py` | 3,538 | LangGraph FSM 定义与节点实现 |
| DualCoreRouter | `orchestration/dual_core_router.py` | 1,089 | 双核路由决策 |
| UXEnvelope | `orchestration/ux_envelope.py` | 1,907 | UX 表现层适配 |
| AuroraRuntimeV1 | `aurora/runtime_v1/service.py` | 2,755 | Aurora Runtime 主服务 |
| AuroraEngine | `aurora/engine.py` | 264 | 确定性控制平面 facade |
| StateAggregator | `state_aggregator/service.py` | 1,189 | 20+ 维度用户状态聚合 |
| KillSwitch | `core/kill_switch.py` | 154 | 三态开关机制 |
| PII Privacy | `aurora/privacy.py` | 148 | PII 脱敏与差分隐私 |
| DecisionLoop | `aurora/runtime_v1/decision_loop.py` | ~800 | Aurora LLM 决策循环 |
| DynamicToolRegistry | `orchestration/dynamic_tool_registry.py` | 371 | 工具自动发现与注册 |
| Schemas | `orchestration/schemas.py` | 529 | 核心数据结构定义 |

### 1.3 ChatOrchestrator Mixin 分解

ChatOrchestrator 通过 Python MRO (Method Resolution Order) 组合 8 个 Mixin:

```python
class ChatOrchestrator(
    ContextBuilderMixin,       # 用户/会话上下文装配
    RoutingEngineMixin,        # 意图路由 + 双核决策
    ValidationEngineMixin,     # 请求/计划验证门控
    SessionStateMixin,         # 会话状态、反馈、版本管理
    ExecutionEngineMixin,      # 工具执行、规划、多 Agent 工作流
    ResponseBuilderMixin,      # 最终响应组装
    PersistenceLayerMixin,     # DB 持久化 + 反馈记录
    ObservabilityMixin,        # 追踪、日志、指标流
)
```

---

## 二、LangGraph FSM 详细分析

### 2.1 状态定义与上下文

FSM 使用 `WorkflowState` (`statechart_engine.py`) 作为共享状态黑板:

```python
@dataclass
class WorkflowState:
    messages: list[dict[str, str]]  # 对话历史
    context_data: dict[str, Any]    # 上下文数据 (核心黑板块)
    next_step: str | None           # 条件路由信号
    errors: list[str]               # 错误收集
    is_finished: bool               # 终止标志
    trace_id: str                   # 执行追踪 ID
```

**关键观察**: `context_data` 是一个大字典，所有节点通过它交换数据。它没有强类型 schema，完全依赖约定键名（如 `"router_decision"`, `"tool_calls"`, `"chat_mode"`, `"dual_core_decision"` 等）。

### 2.2 节点功能详解

| 节点 | 功能 | 输入 | 输出 |
|------|------|------|------|
| `context_builder` | 构建 LLM 系统提示词、注入偏好、工具 schema、上下文窗口 | user_message, conversation_context | state.messages (含 system prompt) |
| `retrieval` | 文档检索 (GraphRAG + Knowledge) | messages | 检索到的文档片段注入 messages |
| `router` | 意图路由：决定走 generation / collaboration / tool_execution | state | context_data["router_decision"] |
| `collaboration` | 多 Agent 协作 (专家选择、团队模式) | state | 协作结果 / state.next_step |
| `collaboration_post_process` | 协作结果后处理 | state | state.next_step → tool_planning / __end__ |
| `tool_planning` | 工具调用规划 | state | tool_calls 列表 |
| `generation` | **核心 LLM 推理**：流式生成 + 工具调用 | state | 流式文本 / tool_calls |
| `generation_review` | 生成质量审查 | state | pass / fail → reflection |
| `reflection` | 反思节点（最多 3 轮递归） | state | 修正后的输出 |
| `tool_execution` | 工具执行（支持 DAG 并行） | tool_calls | tool_results |
| `execution_review` | 执行结果审查 | state | 需要解释 → generation / 终止 |

### 2.3 条件边与路由逻辑

**完整状态转移图**:

```
ENTRY → context_builder → retrieval → router
                                    ├── [math/code/knowledge_agent] → generation
                                    ├── [generation] → generation
                                    ├── [tool_execution] → tool_execution
                                    └── [default] → collaboration

collaboration → collaboration_post_process
                                ├── [next_step set] → (根据 next_step)
                                └── [default] → __end__

generation → generation_router
                        ├── [next_step == tool_execution] → tool_execution
                        └── [default] → generation_review

generation_review → generation_review_condition
                        ├── [next_step == tool_execution] → tool_execution
                        ├── [has tool_calls] → tool_execution
                        ├── [next_step == reflection] → reflection
                        └── [default] → __end__

reflection → reflection_condition
                        ├── [reflection_round >= 3 + has tools] → tool_execution
                        ├── [reflection_round >= 3] → __end__
                        ├── [next_step == reflection] → reflection (递归)
                        ├── [has tool_calls + reflection_completed] → tool_execution
                        └── [default] → __end__

tool_execution → execution_review
                        ├── [next_step == generation] → generation
                        └── [default] → __end__
```

### 2.4 关键常量与约束

| 常量 | 值 | 含义 |
|------|------|------|
| `_MAX_TOOL_LOOPS_PER_TURN` | 2 | 每轮最大工具循环次数 |
| `_GENERATION_FIRST_CHUNK_TIMEOUT_SECONDS` | 18 | 首个 chunk 超时 |
| `_GENERATION_CHUNK_TIMEOUT_SECONDS` | 45 | 后续 chunk 超时 |
| `_STREAM_DELTA_FLUSH_CHARS` | 96 | 流式刷新阈值 |
| `_STREAM_DELTA_FLUSH_SECONDS` | 0.12 | 流式时间阈值 |
| `MAX_ROUNDS` (reflection) | 3 | 反思最大轮次 |

---

## 三、双核路由系统

### 3.1 路由输入 (DualCoreRoutingInput)

`DualCoreRouter.route()` 接收一个 frozen dataclass，包含 30+ 维度信号:

| 信号维度 | 类型 | 来源 |
|----------|------|------|
| `intent` / `intent_confidence` | str / float | UnifiedIntentRouter |
| `information_sufficient` | bool | SufficiencyChecker |
| `emotional_block_detected` | bool | StateAggregator |
| `procrastination_pattern` | bool | 行为模式检测 |
| `recent_sentiment_distribution` | dict | CognitiveFragment |
| `has_active_plan` / `plan_health_status` | bool / str | PlanService |
| `cognitive_load` | float | Aurora 认知负荷估算 |
| `social_signals` | SocialSignalsV1 | SocialSignalBridge |
| `srl_phase_hint` | SRLPhaseHint | SRLPhaseTracker |
| `metacognition_hint` | MetacognitionHintV1 | MetacognitionService |
| `capsule_preferences` | dict | 用户偏好胶囊 |
| `spine_active_states` | list | Spine 状态寄存器 |
| `scaffolding_snapshot` | dict | SGW 脚手架状态 |
| `aurora_preferences` | dict | Aurora 用户偏好 |
| `recent_corrections` | list | Aurora 校正历史 |
| `recent_route_outcomes` | list | 路由结果历史 |

### 3.2 路由决策逻辑

路由输出三种模式:

| 模式 | 含义 | 触发条件 |
|------|------|----------|
| `execution_first` | 直接推进执行路径 | 目标清晰 + 信息充分 + 无情绪阻塞 + 无拖延模式 + 无认知模式建议 + 无高认知负荷 + 无疲劳 |
| `cognitive_first` | 先做状态澄清再执行 | 信息不足 OR 情绪阻塞 OR 拖延 OR 低元认知准确性 OR 极高认知负荷 OR 脊柱疲劳 OR 知识瓶颈 |
| `balanced` | 双核并行 | 不满足上述两种极端条件 |

### 3.3 优先级权重矩阵

```
emotional_block:         9.0  (最高优先级)
procrastination:         8.0
route_outcome_failure:   7.5
cognitive_mode:          7.0
scaffolding_frustration: 6.5
low_metacognition:       6.0
high_cognitive_load:     5.0
route_outcome_over_scaffolded: 4.5
spine_fatigue:           4.0
reflection_phase:        3.0
scaffolding_boredom:     2.5
goal_clarity:            1.0  (最低优先级)
```

**评分方法**: 每个维度根据布尔标志激活，取得分最高的作为 `dominant_signal`。

### 3.4 策略调整推荐

路由器通过 `recommend_strategy()` 内部函数输出结构化策略调整:

| 字段 | 可选值 | 来源条件 |
|------|--------|----------|
| `session_mode` | recovery, reflection | 情绪阻塞 / 反思阶段 |
| `intervention_intensity` | low | 情绪阻塞 / 高认知负荷 / 低元认知 / 脊柱疲劳 |
| `explanation_style` | step_by_step, concise | 目标不清晰 / 认知模式 / 高认知负荷 |
| `planning_granularity` | startup_ready | 拖延 / 高认知负荷 / 脊柱执行低 |
| `push_vs_support` | 0.2-0.6 | 情绪 / 低元认知 / 偏好 |
| `check_in_frequency` | minimal | 强元认知 / 过度脚手架 |
| `execution_method` | 用户偏好方法 | 胶囊偏好历史 |

### 3.5 硬编码阈值

| 阈值 | 默认值 | 可配置性 |
|------|--------|----------|
| `procrastination_threshold` | 0.6 | 通过 RoutingParameterSnapshot |
| `emotional_sensitivity` | 0.5 | 通过 RoutingParameterSnapshot |
| `directness_preference` | 0.5 | 通过 RoutingParameterSnapshot |
| `high_cognitive_load` | 0.55 | 通过 _param() |
| `very_high_cognitive_load` | 0.78 | 通过 _param() |
| `spine_state_confidence_min` | 0.45 | 通过 _param() |
| `corrections_threshold` | 3 | 通过 _param() |

---

## 四、Aurora Adaptive Kernel

### 4.1 State Aggregator

**服务**: `StateAggregatorService` (`state_aggregator/service.py`)

支持 20+ 维度的用户状态聚合，每个维度独立 TTL 缓存:

| 维度 | TTL (秒) | 数据来源 |
|------|----------|----------|
| `commitment_summary` | 30 | EpisodicMemory |
| `pending_policies` | 30 | PolicySchedulerService |
| `recent_reflections` | 30 | EpisodicMemory |
| `recent_scenes` | 30 | SceneConsolidationService |
| `foresight_hint` | 30 | PredictiveService |
| `engagement_state` | 60 | FocusSession + UserStreakStats |
| `recent_person_mentions` | 300 | EpisodicMemory |
| `social_signals_summary` | 300 | SocialSignalBridge |
| `learning_state` | 86400 | PredictiveService |
| `working_memory_snapshot` | 30 | WorkingMemoryService |
| `achievement_summary` | 300 | UserAchievement + Achievement |
| `calendar_context` | 300 | CalendarEvent |
| `traits_prior` | 30 | UserPreferencesCenter |
| `srl_phase` | configurable | SRLPhaseStateRecord |
| `metacognition_profile` | configurable | MetacognitionService |
| `idiographic_summary` | configurable | IdiographicAssociationService |
| `emotion_hint` | 60 | CognitiveFragment + ChatMessage |

**Kill Switch 集成**: 支持 Stage 18 (aggregator_enabled) 和 Stage 33 (social) 的三态开关。

**缓存策略**: 内存缓存 (字典)，最多 500 条，按 TTL 自动淘汰过期条目。当 `aggregator_mode == "shadow"` 时返回 None（影子模式）。

**情绪检测**: 混合使用 `CognitiveFragment.sentiment`（来自 NLP 分析）和关键词匹配（从最近 30 条用户消息中检测中文/英文情绪关键词）。

### 4.2 Metacognition

元认知系统通过 `MetacognitionService` 提供:
- `accuracy`: 用户对自身状态/耗时判断的准确性 (0.0-1.0)
- `awareness`: "strong" | "weak" — 自我觉察能力

在 DualCoreRouter 中的影响:
- **低元认知** (accuracy < 0.5): 切换到认知优先模式，降低推送强度
- **强元认知 + 高准确性** (accuracy > 0.8, awareness == "strong"): 减少确认频率，允许更直接的执行路径

### 4.3 SRL Phase Tracker

基于 `SRLPhaseStateRecord` 模型追踪用户当前的自主学习阶段:

| 阶段 | DualCoreRouter 响应 |
|------|---------------------|
| `forethought` | 帮助明确目标、约束和启动标准 |
| `performance` | 维持连续执行，给出短步动作 |
| `reflection` | 帮助总结有效/失灵，再决定下一轮改进 |

### 4.4 Kill Switch 机制

**实现**: `core/kill_switch.py` — 三态 (off → shadow → live) 开关

**核心组件**:

| 组件 | 功能 |
|------|------|
| `KillSwitchBinding` | 定义开关绑定: stage, feature, redis_key, settings_attr, fallback_mode |
| `normalize_mode()` | 归一化模式值，支持别名 ("0"→"off", "1"→"live" 等) |
| `read_mode()` | 异步读取: 先查 settings，再查 Redis，最终回退到 fallback |
| `write_mode()` | 异步写入 Redis |
| `record_mode_gauge()` | 记录 Prometheus 指标 `kill_switch_mode` |

**模式值映射**:
- `0` = off, `1` = live, `true` = live, `false` = off
- `live_canary` → `live` (别名)
- 数值: off=0, shadow=1, live=2

**Redis 键格式**: `{prefix}{binding.redis_key}`

**指标**: `KILL_SWITCH_MODE.labels(stage=X, feature=Y).set(mode_value)`

### 4.5 PII Privacy

**实现**: `aurora/privacy.py`

**脱敏能力**:

| 类型 | 正则 | 替换 |
|------|------|------|
| 邮箱 | RFC-compliant email | `[REDACTED_EMAIL]` |
| 手机号 | +86 格式中国手机号 | `[REDACTED_PHONE]` |
| 身份证 | 15/18 位中国身份证 | `[REDACTED_CN_ID]` |
| 银行卡 | 12-19 位数字序列 | `[REDACTED_BANK_CARD]` |
| 中文姓名 (标签) | "姓名：XXX" 格式 | `[REDACTED_NAME]` |
| 中文姓名 (自称) | "我叫/叫我 XXX" 格式 | `[REDACTED_NAME]` |
| 英文姓名 | "my name is XXX" 格式 | `[REDACTED_NAME]` |

**差分隐私**: `laplace_noise()` 函数提供 Laplace 机制噪声注入:
- 参数: `value`, `epsilon` (默认 0.3), `sensitivity` (默认 1.0)
- 用途: 对数值型用户数据添加噪声以保护隐私

**Kill Switch 集成**: 通过 `AuroraPrivacyKillSwitchService` 控制脱敏模式:
- `off`: 不脱敏
- `shadow`: 仅记录但不实际脱敏
- `live`: 正常脱敏

---

## 五、Aurora Runtime V1 深度分析

### 5.1 AuroraEngine (确定性控制平面)

`aurora/engine.py` 是一个小型确定性 facade:

**核心方法**:
- `materiality_check()`: 检查信号快照是否达到路由阈值
- `decide_backbone_route()`: 决定是否保持在当前节点或转移到新节点
- `dispatch_trigger()`: 触发器调度
- `safe_route()`: 带回退的安全路由包装器
- `build_fallback_decision()`: 异常回退决策

**Backbone 路由**:
```python
classify_routing_mode(snapshot) → RoutingMode:
  - TASK_ASSISTANT: 检测到任务卡关键词 ("当前任务", "drill" 等)
  - WORKFLOW: 检测到规划关键词 ("计划", "plan", "replan" 等)
  - DIRECT: 默认模式

decide_backbone_route(snapshot, policy, current_node, candidate_node):
  1. 检查 materiality (信号是否达到阈值)
  2. 若 materiality 不够 → stay
  3. 若有 candidate_node 且 materiality 够 → transition
  4. 若 materiality 够但无 candidate → stay (strong_signal_without_candidate)
```

**Materiality 评分**:
- `_STRONG_SIGNAL_KEYWORDS`: commitment_conflict, deadline, "没法继续" 等 → 1.0 分
- 软阻力关键词 ("不想", "疲劳", "pause") → 0.35 分
- 其他文本 → 0.15 分
- partner_report 存在 → 直接 1.0 分

### 5.2 AuroraRuntimeV1Service (运行时主服务)

**Surface 类型**:
| Surface | 场景 | 风格 |
|---------|------|------|
| `aurora_modeling` | 用户建模 | warm, tone_warmth=0.84, directness=0.34 |
| `aurora_planning` | 规划对话 | structured, directness=0.84, brevity=0.82 |
| `aurora_checkpoint` | 检查点 | warm, tone_warmth=0.68 |

**plan_turn() 流程**:
1. 加载先前运行时状态 (Redis)
2. 策略再校准检测
3. 上次会话情绪注入
4. Surface 状态注入
5. Last-24h 考试策略应用
6. 睡眠守卫检测 (23:00-06:00 CST)
7. Galaxy 基线加载
8. 控制面读取
9. 活动配置构建
10. Dashboard Readout 构建
11. **Decision Loop 决策** (LLM 驱动)
12. Chat Adapter 渲染消息
13. Inference Claims 提交
14. Wake Policy 记录
15. 遥测记录
16. 运行时状态持久化

**DecisionLoop 输出 (AuroraDecision)**:
```python
@dataclass
class AuroraDecision:
    action: str           # emit_message | wait | schedule_wake | update_harness |
                          # update_state | soft_return_topic | drop_thread
    surface_complete: bool
    modeling_complete: bool
    state_updates: dict
    harness_updates: dict
    wake_schedule: dict
    chat_directive: dict
    metadata: dict
```

**安全约束 — Forbidden Domains**:
```
clinical_diagnosis, personality_pathology, unconscious_interpretation,
inferred_social_identity, trauma_attribution, mental_disorder,
stable_trait_label, gender_identity, sexual_orientation, race_inference,
ethnicity_inference, religion_inference, class_inference, diagnosis,
pathology, personality_disorder
```

### 5.3 考试冲刺 Last-24h 策略

当检测到考试日期在 24h 内时，强制应用:
- `worked_example_first: True`
- `retrieval_practice: True`
- `spaced_review: True`
- `error_analysis_required: True`
- `drop_low_roi_topics: True`
- `new_topic_allowed: False`

对新主题请求直接拒绝并建议复习薄弱点。

### 5.4 睡眠守卫

检测中国时间 23:00-06:00，注入:
- `sleep_guard_active: True`
- 禁止: `full_week_replan`, `three_practice_questions`
- 策略: 简短回复，鼓励设置次日计划后休息

---

## 六、工具系统

### 6.1 工具基类

`tools/base.py` 定义:
- `ToolCategory`: TASK, PLAN, KNOWLEDGE, QUERY, FOCUS, GROWTH
- `BaseTool` (ABC): name, description, category, parameters_schema, requires_confirmation
- `ToolResult`: success, data, error_message, widget_type, widget_data, suggestion
- `ToolContext`: user_id, db_session

### 6.2 工具注册表

**双重注册**:
- `DynamicToolRegistry` (`dynamic_tool_registry.py`): 自动发现，从 `app.tools` 包递归扫描
- `ToolRegistry` (`tools/registry.py`): 向后兼容包装器

**自动发现流程**:
1. `ensure_package_registered("app.tools")` — 确保只注册一次
2. `register_from_package()` — 使用 `pkgutil.iter_modules` 递归扫描
3. `register_from_module()` — 对每个模块查找 `BaseTool` 子类
4. 实例化并注册到 `_tools` 字典

**线程安全**: 使用 `threading.RLock` 保护所有注册/查询操作。

**验证**: `validate_all_tools()` 检查每个工具的 execute 方法、name、parameters_schema、to_openai_schema()。

### 6.3 工具清单

| 文件 | 类别 | 推测用途 |
|------|------|----------|
| `task_tools.py` | TASK | 任务 CRUD |
| `plan_tools.py` | PLAN | 计划 CRUD |
| `plan_state_tools.py` | PLAN | 计划状态管理 |
| `plan_resolution.py` | PLAN | 计划解决 |
| `error_tools.py` | QUERY | 错题管理 |
| `knowledge_tools.py` | KNOWLEDGE | 知识检索 |
| `companion_tools.py` | QUERY | 伴侣工具 |
| `entity_cards.py` | QUERY | 实体卡片 |
| `growth_strategy_tools.py` | GROWTH | 成长策略 |
| `intervention_tools.py` | GROWTH | 干预工具 |
| `persona_tools.py` | QUERY | 角色工具 |
| `prism_tools.py` | QUERY | 棱镜分析 |
| `report_tool.py` | QUERY | 报告生成 |
| `simulation_tool.py` | QUERY | 模拟工具 |
| `task_query_tool.py` | QUERY | 任务查询 |
| `theater_tool.py` | QUERY | 情境模拟 |
| `translation_tool.py` | QUERY | 翻译 |
| `web_search_tool.py` | QUERY | 网络搜索 |
| `material_retrieval_tools.py` | KNOWLEDGE | 学习材料检索 |

---

## 七、UX Envelope 系统

### 7.1 表现层架构

UXEnvelope 输出结构化的 UX 元数据包:

```
envelope = {
    "ux_turn":          // 当前轮次元数据
    "ux_result":        // 结果状态与置信度
    "ux_followthrough": // 下一步行动 + 重试选项
    "ux_sources":       // 引用来源信息
    "orchestration_summary": // 编排摘要 (可选)
    "ux_evolution":     // 进化/适应信息 (可选)
    "continuity_banner": // 连续性横幅 (可选)
    "mode_explanation": // 模式解释 (可选)
    "collaboration_summary": // 协作摘要 (可选)
    "adaptation_summary": // 适应摘要 (可选)
    "session_adaptation": // 会话适应 (可选)
}
```

### 7.2 呈现模式配置

7 种内置模式:
| 模式 | 标签 | 回答类型 |
|------|------|----------|
| `standard` | 标准对话 | direct_answer |
| `deep_analysis` | 深度解析 | synthesis |
| `study_plan` | 学习计划 | plan |
| `error_diagnosis` | 错题分析 | diagnosis |
| `expert_auto` | 专家自动 | synthesis |
| `execution_delegate` | 执行委派 | delegation_brief |
| `aurora_core_session` | Aurora 深度校准 | core_session_entry |

### 7.3 自适应表现层

通过 `settings.ENABLE_ADAPTIVE_PRESENTATION` 控制:

- **Style variants**: compact / balanced / exploratory
- **Tone variants**: warm / analytical / direct
- **Next action limits**: compact=2, balanced=3, exploratory=4
- **Conversation stages**: explore → plan_ready → executing → blocked → completed → reflect

### 7.4 Blocked 温度

当回复被阻塞时 (缺少信息、工具失败、超时)，UX Envelope 使用"温度"概念:
- `gentle`: 情绪焦点模式或负面信号时
- `guided`: 默认
- `direct`: 重复阻塞 >= 2 次时

---

## 八、Governance 规则体系

### 8.1 规则总览

Rule Guard Manifest 包含 67+ 条规则，覆盖:

| 规则族 | 数量 | 关注领域 |
|--------|------|----------|
| K/Y/Z | 3+ | 写入路径约束 |
| AB/AC/AD/AE/AF | 5 | 聚合器完整性、工作记忆、充分性拆分 |
| AG/AH/AI/AJ/AK/AL/AM/AN/AO/AP/AQ | 11 | 算法纯度、隔离性 |
| AS/AT/AU/AV | 4 | 视觉合规、无孤立、移动端对等 |
| AW/AX/AY/AZ | 4 | 安全、路由所有权、LLM 安全、事件总线 |
| BB/BC/BD/BE/BF/BG/BH/BI/BJ | 9 | 金融原子性、幂等性、影子语义、数据最小化 |
| S21-S29 | 20+ | 各 Stage 专项规则 |
| AR | 1 | SQAM 套件 |
| I18N | 1 | 国际化覆盖 |

### 8.2 规则执行

所有规则通过 `scripts/run_all_rule_guards.sh` 执行:
- 每条规则是独立的 Python 脚本
- 脚本退出码: 0 = 通过, 非 0 = 失败
- 支持单规则执行: `--rule XX`

### 8.3 关键安全规则

| 规则 | 检查内容 |
|------|----------|
| K | 写入路径约束 (确保数据只写入授权位置) |
| Y | 推断提取约束 |
| Z | 社交边界约束 |
| AO | 无诊断标签 + 不在路由中使用 + 元认知与脚手架解耦 |
| AW | 速率限制器健全性 |
| AY | LLM 安全检查 |
| BB | 金融操作原子性 |
| BI | 硬编码密钥检测 |
| FME | Kill Switch 注册完整性 |

---

## 九、问题报告

### P0 — Critical

#### P0-01: WorkflowState.context_data 无类型约束，存在运行时 KeyError 风险

**位置**: `backend/app/orchestration/statechart_engine.py:34-46`, 全部 FSM 节点
**原因分析**: `WorkflowState.context_data` 是 `dict[str, Any]`，所有节点间通信依赖约定键名（如 `"router_decision"`, `"tool_calls"`, `"dual_core_decision"` 等）。没有类型检查、没有必需键验证、没有默认值保护。任何一个节点拼写错误或遗漏键都会导致下游节点 `KeyError` 或静默使用 `None`。
**影响范围**: 全部 FSM 节点间通信 (11 个节点)
**修复建议**: 
1. 定义 `ContextData` TypedDict 或 Pydantic model，列出所有约定键
2. 在每个节点入口添加必需键检查
3. 在 `context_data.update()` 时验证键名合法性

---

#### P0-02: reflection 节点递归无总深度上限保护

**位置**: `backend/app/agents/standard_workflow.py:3162-3185`
**原因分析**: `reflection_condition` 检查 `reflection_round >= MAX_ROUNDS (3)`，但 `reflection_round` 来自 `review_context.get("reflection_round", 0)`。如果 `generation_review_node` 或 `reflection_node` 内部逻辑重置了 `review_context` 而不是递增 `reflection_round`，可能导致无限递归。此外，`MAX_ROUNDS` 是函数局部常量，无法从外部配置或调优。
**影响范围**: reflection 节点，可能导致无限循环
**修复建议**:
1. 在 `WorkflowState` 层面增加 `total_reflection_rounds` 计数器，由 `statechart_engine` 框架级强制
2. 将 `MAX_ROUNDS` 提升为可配置参数

---

### P1 — High

#### P1-01: DualCoreRouter.route() 函数过长 (约 500 行)，存在高圈复杂度

**位置**: `backend/app/orchestration/dual_core_router.py:205-863`
**原因分析**: `route()` 方法包含约 20 个条件分支，每个分支内部又有多层嵌套。预估圈复杂度 > 30。这使得:
1. 难以测试所有路径组合
2. 新增信号维度需要修改同一函数
3. 维护成本高
**修复建议**: 将每个信号处理提取为独立的策略函数，通过策略注册表组合

---

#### P1-02: StateAggregatorService 缓存驱逐策略可能导致内存压力

**位置**: `backend/app/state_aggregator/service.py:228-231`
**原因分析**: 缓存驱逐仅在 `len(self._cache) > 500` 时触发，且仅删除已过期条目。如果 TTL 较长（如 `learning_state` 为 86400 秒），500 条限制可能在用户量大时被频繁达到。此外，缓存是实例级的，不是进程级的 — 如果创建多个 `StateAggregatorService` 实例，缓存不共享。
**影响范围**: 内存使用、缓存命中率
**修复建议**: 考虑使用 LRU 缓存替代简单的过期检查，或引入 Redis 分布式缓存

---

#### P1-03: AuroraRuntimeV1Service.plan_turn() 中 L1 快速路径判断依赖外部注入

**位置**: `backend/app/orchestration/orchestrator.py:502-505`
**原因分析**: L1 快速路径 (`_l1 = request_extra_context.get("aurora_l1")`) 在 orchestrator 内部检查，但 `aurora_l1` 数据由外部注入。如果外部注入 `{"should_escalate": false}` 但实际上存在需要 escalation 的信号，L1 路径会跳过整个 Aurora decision loop，导致用户得不到应有的干预。
**影响范围**: Aurora 决策质量
**修复建议**: L1 快速路径应该至少验证基本安全信号 (emotional_block, crisis) 后再跳过

---

#### P1-04: PII 脱敏正则存在边界情况

**位置**: `backend/app/aurora/privacy.py:16-26`
**原因分析**:
1. `_PHONE_RE` 只匹配 `1[3-9]\d{9}` 格式，不覆盖虚拟号码或国际号码
2. `_BANK_CARD_RE` 使用 `(?:\d[ -]?){12,19}` 会匹配任何 12-19 位数字序列，误杀率较高（如订单号、跟踪号）
3. `_CN_NAME_LABEL_RE` 只匹配 2-4 字中文名，不覆盖复姓（如 "欧阳修"）
**影响范围**: PII 保护覆盖度
**修复建议**: 
1. 增加银行卡的 Luhn 校验
2. 扩展中文姓名到 2-5 字
3. 增加误杀白名单（如已知非 PII 数字模式）

---

#### P1-05: privacy.py 中 `pii_redaction_mode()` 使用 `asyncio.get_event_loop().run_until_complete()`

**位置**: `backend/app/aurora/privacy.py:53-65`
**原因分析**: `pii_redaction_mode()` 是同步函数，但内部调用 `AuroraPrivacyKillSwitchService().get_mode()` (异步)。使用 `asyncio.get_event_loop().run_until_complete()` 在已有事件循环的上下文中会抛出 `RuntimeError: This event loop is already running`。虽然 catch 了 Exception，但会每次都回退到 settings 值，Kill Switch 的 Redis 动态控制实际上在异步上下文中失效。
**影响范围**: PII 脱敏的 Kill Switch 动态控制在异步请求中不可用
**修复建议**: 提供 `async def pii_redaction_mode_async()` 版本，供异步调用者使用

---

### P2 — Medium

#### P2-01: DynamicToolRegistry 单例使用类变量导致跨测试污染

**位置**: `backend/app/orchestration/dynamic_tool_registry.py:36-38`
**原因分析**: `_tools`, `_tool_info`, `_registered_packages` 是类变量而非实例变量。虽然 `__new__` 在创建实例时会初始化，但如果在测试中调用 `clear_all()`，会影响同一进程中所有使用该单例的测试。
**影响范围**: 测试隔离性
**修复建议**: 在测试中提供 fixture 级别的隔离机制

---

#### P2-02: DualCoreRouter 策略调整输出被截断为最多 5 条

**位置**: `backend/app/orchestration/dual_core_router.py:809, 843, 856` (多处 `[-5:]` 和 `[:5]`)
**原因分析**: `cognitive_adjustments[-5:]`, `execution_constraints[:5]`, `strategy_adjustments[:5]` 硬编码截断。当存在多个并发信号时（如情绪阻塞 + 拖延 + 高认知负荷 + 脊柱疲劳），有效调整可能超过 5 条被丢弃。
**影响范围**: 多信号并发时 LLM 指令不完整
**修复建议**: 将截断阈值提升为可配置参数，或在截断时保留最高优先级的调整

---

#### P2-03: KillSwitchBinding 未注册到中心注册表

**位置**: `backend/app/core/kill_switch.py`
**原因分析**: `KillSwitchBinding` 是一个 frozen dataclass，没有中心注册机制。各个 Kill Switch 的 Binding 分散在各个 service 文件中（如 `AuroraStage18KillSwitchService`, `AuroraPrivacyKillSwitchService` 等）。没有单一地方可以看到所有已注册的 Kill Switch。规则 FME (`check_rule_fme_kill_switch_registered.py`) 存在来检查这一点，但它只能事后验证。
**影响范围**: Kill Switch 运维可见性
**修复建议**: 建立中心 Kill Switch 注册表，启动时自动发现所有 Binding

---

#### P2-04: UXEnvelope 中 `_MODE_PROFILES` 包含中文硬编码字符串

**位置**: `backend/app/orchestration/ux_envelope.py:148-228`
**原因分析**: 所有 `PresentationProfile` 的 `mode_label`, `companion_frame`, `blocked_title`, `blocked_message` 等字段都使用中文硬编码。没有使用 ARB l10n 机制。虽然这些字符串主要是面向 LLM 的 (作为 prompt 注入)，但 `mode_label` 和 `blocked_title` 等字段可能被传递到前端展示。
**影响范围**: 国际化覆盖
**修复建议**: 区分 LLM 注入字符串 (可保留中文) 和用户可见字符串 (应使用 l10n)

---

#### P2-05: AuroraEngine 的 `_build_stay_decision` 和 `_build_transition_decision` 存在大量硬编码

**位置**: `backend/app/aurora/engine.py:139-217`
**原因分析**: 这两个方法硬编码了 `rollback_anchor` 结构、`evidence_refs`、`aurora_presence` 等字段。特别是 `rollback_anchor` 中的 `prev_focus_contract_version: 0` 和 `prev_active_commitment_ids: []` 始终为空，没有从实际状态恢复。
**影响范围**: Aurora 回滚能力可能在 rollback_anchor 不准确时受限
**修复建议**: 从当前状态快照中读取实际的 rollback_anchor 值

---

#### P2-06: orchestrator.py 中 `_STREAM_QUEUE_MAXSIZE = 512` 无动态调整

**位置**: `backend/app/orchestration/orchestrator.py:283`
**原因分析**: 流式队列大小硬编码为 512，压力阈值为 0.75。在长对话或工具密集型场景中，如果 LLM 生成速度远快于 WebSocket 推送速度，队列可能满载导致背压。
**影响范围**: 长对话场景的流式响应稳定性
**修复建议**: 将队列大小设为可配置参数

---

#### P2-07: standard_workflow.py 中 `_resolve_generation_agent_role` 有遍历 bug

**位置**: `backend/app/agents/standard_workflow.py:160-179`
**原因分析**: 在 `_resolve_generation_agent_role` 和 `_resolve_generation_task_type` 中，循环使用 `for expert in answer_experts` 但内部使用 `cleaned = str(expert).strip()` — 变量名是 `expert` 但使用的是 `str(expert)` 而不是 `str(expert_item)`。仔细看:
```python
for expert in answer_experts:
    cleaned = str(expert).strip()  # expert 是单个元素
```
实际上 `expert` 就是遍历变量，所以逻辑正确。但命名 `expert` 在外层和内层不同含义可能造成混淆。更重要的是，代码检查的是 `not cleaned.startswith("custom_expert:")`，但没有检查 `cleaned` 是否为有效角色名。
**影响范围**: 低 — 逻辑正确但可读性差
**修复建议**: 重命名遍历变量为 `expert_name` 提高可读性

---

## 十、总结

### 系统成熟度评估

| 维度 | 评分 | 说明 |
|------|------|------|
| **架构设计** | ★★★★☆ | Mixin 组合解耦良好，FSM 结构清晰 |
| **路由完备性** | ★★★★★ | 30+ 维度信号，12 级优先级权重，3 种模式 |
| **安全治理** | ★★★★☆ | 67+ 规则覆盖，Kill Switch 三态，PII 脱敏 |
| **可观测性** | ★★★★☆ | Prometheus 指标、遥测记录、路由调试输出 |
| **类型安全** | ★★☆☆☆ | context_data 无类型约束是主要风险点 |
| **可测试性** | ★★★☆☆ | DualCoreRouter 圈复杂度高，缓存策略需改进 |
| **国际化** | ★★☆☆☆ | UXEnvelope 有中文硬编码 |

### 核心优势

1. **DualCoreRouter 的信号维度和优先级权重设计非常精细** — 覆盖情绪、拖延、认知负荷、元认知、SRL 阶段、脊柱状态、脚手架状态、路由历史等 12+ 维度，每个维度有明确的权重和阈值
2. **Aurora Runtime 的安全边界清晰** — Forbidden Domains 列表、L1/L2/L3/L4 分层、睡眠守卫、Last-24h 策略
3. **FSM 节点职责单一** — 每个节点有明确的功能边界，条件路由逻辑可追溯
4. **Governance 规则体系完善** — 67+ 规则、自动发现、CI 集成

### 核心风险

1. **P0-01 (context_data 无类型约束)** — 这是系统最大的技术债，所有节点间通信依赖约定键名
2. **P1-05 (PII Kill Switch 在异步上下文中失效)** — 安全关键功能在主要运行时场景中不可用
3. **P0-02 (reflection 递归保护)** — 虽然 `reflection_round` 计数器存在，但依赖正确的内部状态管理

### 修复优先级建议

1. **立即**: P0-01 (context_data 类型化), P0-02 (reflection 递归保护强化)
2. **短期**: P1-05 (PII 异步修复), P1-03 (L1 快速路径安全检查)
3. **中期**: P1-01 (DualCoreRouter 重构), P1-04 (PII 正则改进), P2-03 (Kill Switch 注册表)
4. **长期**: P2-04 (UX 国际化), P2-01 (测试隔离)
