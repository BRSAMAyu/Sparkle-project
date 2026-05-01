# SPARKLE Aurora Runtime v1 — Adaptive Harness Engineering 实施规格

> **Status**: v2.0 DRAFT — 架构修正（LLM 认知核心 + 系统脚手架）
> **Date**: 2026-04-24
> **Scope**: Aurora Runtime v1 — LLM 驱动的认知核心，不是模板系统
> **North Star**: 小林注册后第一次建模时，立刻感觉到”这不是问卷，这是一个真的在理解我的朋友”
> **Supersedes**: 本文档 v1.1 及此前所有 Aurora Runtime 规格。v1.1 的模板实现必须被替换。

---

## §0 设计哲学（锁定）

1. **Aurora 不是分类器，不是规则路由器，不是模板引擎。**
   Aurora 是持续维护内部状态的 LLM 认知主体。它的动作来自整体推理，不来自关键词匹配或硬编码回复模板。

2. **Aurora 不直接和用户对话。**
   Aurora 的 LLM 上下文 100% 用于认知决策——感知、建模、前向因果模拟、分析、策略调整。它不做文本生成。用户看到的对话由独立的 Chat 层根据 Aurora 的决策输出生成。这保证 Aurora 的上下文不被冗长对话污染，同时控制 LLM 成本。

3. **系统是脚手架，Aurora 是驾驶员。**
   所有其他子系统（state aggregator、exam sprint policy、galaxy、task manager、achievement engine……）负责数据处理、管线、聚合，产出干净的仪表盘读数。Aurora 读这些读数，不处理原始数据。就像 API 层层封装——系统做重活，Aurora 只看接口。

4. **Aurora 能选择看什么、不看什么。**
   仪表盘上有各种读数和开关。Aurora 自己决定打开哪些、关闭哪些、优先看哪些。这种选择性感知就是 Adaptive Harness Engineering 的核心。

5. **多条消息不是拆句。**
   用户看到的多条连续消息是 Chat 层根据 Aurora 的决策意图生成的，不是把长文切碎。

6. **主动性不是固定触发表。**
   系统可以提供时间、事件、静默、外部状态变化等候选信号，但是否活跃、何时再来、跟进什么，由 Aurora 自己决定。

7. **未竟话题不是待办队列，而是信息缺失感。**
   Aurora 记住的不是”我还有三句话没说”，而是”这个人的哪一块我还没看清””哪一块判断还没闭合”。

8. **硬边界由系统强制，不可被 Aurora 覆盖。**
   用户设定的勿扰时段、隐私边界、禁用动作、安全红线，都属于系统约束，不属于 Aurora 自调空间。

---

## §0.5 架构修正：为什么模板实现必须替换

当前 `AuroraRuntimeV1Service` 的实现存在根本性问题：

| 问题 | 当前实现 | 正确实现 |
|------|---------|---------|
| 决策方式 | `_infer_agenda_priority` 关键词匹配 + `_build_message_plan` 模板 dict | LLM 整体推理 |
| 回复生成 | Aurora 直接生成用户看到的文本 | Aurora 只输出决策，Chat 层生成文本 |
| 状态感知 | 关键词列表感知用户状态 | 系统仪表盘提供预处理的读数，Aurora 读取 |
| 上下文用途 | 用来拼模板文本 | 100% 用于认知推理 |

**必须删除的代码**：
- `_build_message_plan()` — 硬编码回复模板
- `_infer_agenda_priority()` — 关键词匹配
- `_looks_like_modeling_complete()` — 完成检测关键词列表
- `_DEFAULT_ACTIVITY_PROFILE` 中的硬编码默认值
- `AuroraRuntimeTurnPlan.messages` 字段 — Aurora 不应直接产出消息

**必须新增的代码**：
- `AuroraDecisionLoop` — LLM 调用层，接收仪表盘读数，输出决策
- `DashboardReadout` — 系统脚手架产出的预处理读数接口
- `AuroraDecision` — Aurora 的决策输出（不含用户文本）
- `ChatLayerAdapter` — 把 Aurora 决策翻译成用户可见的对话

---

## §1 产品分层与范围

### 1.1 双层系统

| 层 | 优化目标 | 典型场景 | 交互形态 |
|---|---|---|---|
| **Aurora 层** | 真正的朋友感、长期理解、主动关怀、信息缺失闭环 | 冷启动建模、规划澄清、checkpoint 复盘、主动关怀 | 非回合式、可连续发多条、可带回话题 |
| **执行层** | 用最小阻力帮助用户实现目标 | 任务执行、具体答疑、计划落地、补强执行 | 轻量回合制、快、准、少废话 |

### 1.2 v1 要做

| 场景 | 当前状态 | v1 改造 |
|---|---|---|
| **P1 冷启动建模** | `ModelingChatScreen` 仍是 REST 回合制 | Aurora 驱动的流式、多消息、非问卷式建模 |
| **P0 规划澄清** | 追问逻辑仍偏回合制 | 支持被带走后自然带回，不重复问已获得信息 |
| **P3 checkpoint 复盘** | 主要是外部固定任务触发 | Aurora 可根据状态自行安排后续跟进 |
| **Aurora runtime substrate** | 还不存在 | 建立 AuroraState、Control Surface、Decision Loop、Transport、Wake 基础设施 |

### 1.3 v1 不做

- 不改任务执行聊天的主体交互形态，仍保持高效率回合制
- 不做 Aurora 独立全功能操作台 UI
- 不做 `context_assembly_strategy` 的完整自调体系
- 不做完整 `plan_density` 自动规划器
- 不做 Bayesian 学习回路与长期科研型实验指标
- 不新增 governance rule manifest

---

## §2 Aurora Runtime v1 总体架构

### 2.0 三层架构

```
┌──────────────────────────────────────────────────────────────┐
│  用户看到的对话                                                 │
│  Chat Layer — 根据 Aurora 决策 + 用户上下文生成自然语言          │
│  可以用另一个 LLM 调用（或模板 + LLM 混合）                      │
├──────────────────────────────────────────────────────────────┤
│  Aurora 认知核心                                               │
│  Decision Loop — 纯 LLM 推理，不生成用户文本                     │
│  输入：仪表盘读数（预处理的） + 当前状态 + 硬边界                   │
│  输出：决策（追哪个缺口、调什么参数、要不要唤醒、下一步意图）        │
│  成本控制：上下文只用于认知，不用于对话，每次调用 200-500 token     │
├──────────────────────────────────────────────────────────────┤
│  系统脚手架（Scaffolding）                                      │
│  State Aggregator、Exam Sprint Policy、Galaxy、Task Manager…  │
│  职责：数据处理、管线、聚合 → 产出干净的仪表盘读数                  │
│  Aurora 不处理原始数据，只读预处理后的接口                        │
└──────────────────────────────────────────────────────────────┘
```

### 2.1 数据流

```
用户消息 / 定时唤醒 / 系统事件
    │
    ├─→ 系统脚手架处理：
    │     State Aggregator → 用户状态摘要
    │     ExamSprintPolicy → 冲刺策略读数
    │     Task Manager → 任务进展读数
    │     Galaxy → 知识图谱读数
    │     Achievement Engine → 成就/动力读数
    │     Memory Service → 记忆摘要读数
    │     Checkpoint History → 复盘历史读数
    │     → 汇总成 DashboardReadout
    │
    ├─→ Aurora Decision Loop（LLM 调用）：
    │     输入：DashboardReadout + AuroraState + HardBounds + Skills
    │     LLM 推理：感知、建模、因果模拟、分析、策略调整
    │     输出：AuroraDecision（不含用户文本）
    │
    ├─→ 状态更新：
    │     更新 AuroraState（tensions、intent、profile）
    │     如有 harness 调整 → 更新 Control Surface
    │     如有 wake → 写入 ScheduledWake
    │
    └─→ Chat Layer 生成用户可见对话：
          根据 AuroraDecision 的意图 + conversation_style + 用户上下文
          生成 1-3 条自然消息
          通过 gRPC stream yield（CONTINUE → STOP）
```

### 2.2 6 个模块

1. `AuroraState` — 状态容器（已实现，保留）
2. `Control Surface` — 可调参数 + 硬边界（已实现，保留）
3. `Dashboard Readout` — 系统脚手架产出的仪表盘读数（**新增**）
4. `Aurora Decision Loop` — LLM 认知推理（**必须替换当前模板**）
5. `Chat Layer Adapter` — 把决策翻译成用户对话（**新增**）
6. `Skill-as-Manual` — 按需加载的开关说明书（已实现，保留）

### 2.3 一句话定义

- `AuroraState`：Aurora 当前”怎么看用户、怎么看情景、自己还缺什么”的状态容器
- `Control Surface`：Aurora 可读可调的最小控制面
- `DashboardReadout`：系统脚手架产出的预处理读数——Aurora 的仪表盘
- `Decision Loop`：Aurora 的 LLM 认知核心——读仪表盘、做决策、不说话
- `Chat Layer Adapter`：把 Aurora 的决策意图翻译成用户能看到的自然对话
- `Skill-as-Manual`：Aurora 按需读取的开关说明书

---

## §3 Module 1: AuroraState

AuroraState 分为两层：

- `Cognitive Snapshot`
  跨 session、跨 surface 存活，按用户维度维护相对稳定的认知状态
- `Runtime State`
  只属于当前交互面和当前会话，保存 Aurora 此刻正在进行的运行态

### 3.1 运行时数据模型

```python
@dataclass
class AuroraState:
    user_id: str
    surface: str                  # "aurora_modeling" | "aurora_planning" | "aurora_checkpoint"
    conversation_id: str
    runtime_session_id: str

    user_model_snapshot: dict[str, Any]
    informational_tensions: list["InformationalTension"]
    current_intent: "AuroraIntent | None"
    latent_threads: list["LatentThread"]
    activity_profile: "ActivityProfile"
    self_scheduled_wakes: list["ScheduledWake"]

    streaming_status: str         # "idle" | "emitting" | "waiting_user"
    ingress_events: list[dict[str, Any]]
    last_decision_at: datetime | None
    updated_at: datetime
```

### 3.2 核心子结构

```python
@dataclass
class InformationalTension:
    tension_id: str
    domain: str                   # e.g. "schedule", "motivation", "baseline", "exam_scope"
    description: str
    priority: float               # 0.0-1.0
    status: str                   # "open" | "partially_resolved" | "resolved" | "dropped"
    evidence: list[str]
    created_at: datetime
    last_attempted_at: datetime | None

@dataclass
class AuroraIntent:
    intent_type: str              # "pursue_tension" | "confirm_understanding" | "answer_detour"
                                  # "soft_return" | "encourage" | "schedule_follow_up" | "wait"
    target_tension_id: str | None
    payload: dict[str, Any]

@dataclass
class LatentThread:
    thread_id: str
    source_intent: AuroraIntent
    tension_links: list[str]
    salience: float               # 0.0-1.0，这个线程对 Aurora 当前仍有多重要
    context_snapshot: str
    created_at: datetime

@dataclass
class ActivityProfile:
    proactive_intensity: float
    next_wake_at: datetime | None
    conversation_style: str       # "warm" | "structured" | "exploratory"
    agenda_priority: str | None
    task_density_hint: float

@dataclass
class ScheduledWake:
    wake_id: str
    scheduled_at: datetime
    reason: str
    planned_action: str
    status: str                   # "pending" | "executed" | "cancelled" | "suppressed"
```

### 3.3 持久化分层

| 层 | 存储 | Key / 表 | 用途 | 生命周期 |
|---|---|---|---|---|
| Runtime State | Redis | `aurora:runtime:{user_id}:{surface}:{conversation_id}` | 当前会话态、streaming、ingress、当前 intent | TTL 24h |
| Surface Index | Redis | `aurora:surface-index:{user_id}` | 当前活跃 surface / 会话索引 | TTL 24h |
| Cognitive Snapshot | PostgreSQL | `aurora_state_snapshots` | tensions、activity profile、关键 latent threads | 持久 |
| Scheduled Wakes | PostgreSQL | `aurora_scheduled_wakes` | Aurora 自设唤醒、执行记录 | 持久 |
| Wake Queue | Redis Sorted Set | `aurora:wake_queue` | 快速扫描到期唤醒 | 到期移除 |

### 3.4 关键设计约束

1. **Runtime State 不能只按 `user_id` 存。**
   否则建模、规划、复盘等不同面会串台。

2. **Cognitive Snapshot 可以按 `user_id` 聚合，但 Runtime State 必须按 `surface + conversation_id` 隔离。**

3. **Aurora 页面与执行页面共享认知快照，不共享运行态。**

---

## §4 Module 2: Control Surface v1

v1 只开放 5 个可调参数，禁止继续扩张。

### 4.1 可调参数

| 参数 | 类型 | 说明 | 默认值 |
|---|---|---|---|
| `proactive_intensity` | `float(0.0-1.0)` | Aurora 主动追问、主动跟进的积极程度 | `0.6` |
| `next_wake_at` | `datetime \| null` | Aurora 自主设定的下次唤醒时间 | `null` |
| `conversation_style` | `warm \| structured \| exploratory` | Aurora 当前表层对话风格 | `warm` |
| `agenda_priority` | `str \| null` | 当前最优先追的信息缺口 domain | `null` |
| `task_density_hint` | `float(0.0-1.0)` | 给执行层的任务密度建议 | `0.7` |

### 4.2 硬边界来源

硬边界统一来自 `user_preferences_center.explicit` 的 JSON payload，不引入新的关系字段。

推荐 v1 合同：

```json
{
  "aurora_preferences": {
    "dnd_windows": [
      {"start": "22:30", "end": "07:30"}
    ],
    "privacy_boundaries": [
      "family_conflict",
      "mental_health_detail"
    ],
    "disabled_actions": [
      "proactive_follow_up"
    ]
  }
}
```

### 4.3 边界规则

| 边界 | 约束 |
|---|---|
| `dnd_windows` | Aurora 不能主动打扰；唤醒落入 DND 时自动 suppress 或顺延 |
| `privacy_boundaries` | Aurora 不主动追问被用户标记为隐私的域 |
| `disabled_actions` | Aurora 不能执行用户显式禁用的动作 |
| 安全红线 | 系统强制，Aurora 不可覆盖 |

### 4.4 读取方式

```python
async def read_control_surface(user_id: str) -> ControlSurfaceReading:
    adjustable = await redis.hgetall(f"aurora:control:{user_id}") or {}
    prefs = await profile_context_service.get_explicit_preferences(user_id)
    aurora_prefs = dict((prefs or {}).get("aurora_preferences") or {})

    return ControlSurfaceReading(
        adjustable=ActivityProfile(
            proactive_intensity=float(adjustable.get("proactive_intensity", 0.6)),
            next_wake_at=adjustable.get("next_wake_at"),
            conversation_style=adjustable.get("conversation_style", "warm"),
            agenda_priority=adjustable.get("agenda_priority"),
            task_density_hint=float(adjustable.get("task_density_hint", 0.7)),
        ),
        hard_bounds={
            "dnd_windows": aurora_prefs.get("dnd_windows", []),
            "privacy_boundaries": aurora_prefs.get("privacy_boundaries", []),
            "disabled_actions": aurora_prefs.get("disabled_actions", []),
        },
    )
```

### 4.5 Aurora 可以怎么调

Aurora 通过 `harness_updates` 建议改动，系统只负责校验合法性与不越界。

```json
{
  "action": "emit_message",
  "messages": [
    "今天先别压太满，我们把最关键的点吃透就够了。"
  ],
  "harness_updates": {
    "task_density_hint": 0.35,
    "conversation_style": "structured"
  }
}
```

---

## §5 Module 3: Dashboard Readout（新增）

**这是 Aurora 和系统脚手架之间的接口层。**

系统脚手架负责把原始数据加工成 Aurora 能直接读的仪表盘读数。Aurora 不处理原始数据管线。

```python
@dataclass
class DashboardReadout:
    “””系统脚手架产出的预处理读数——Aurora 的仪表盘”””

    # ── 用户状态读数（from State Aggregator）──
    user_state_summary: str           # 自然语言摘要，不是原始 JSON
    srl_phase: str | None             # 当前 SRL 阶段
    cognitive_load: float | None      # 0.0-1.0
    emotional_tone: str | None        # 最近情绪倾向

    # ── 学习进展读数（from Task Manager + Galaxy）──
    task_progress: TaskProgressReadout   # 任务完成率、卡点任务
    knowledge_coverage: str | None       # 知识图谱覆盖摘要
    weak_areas: list[str]                # 已识别的薄弱点

    # ── 冲刺策略读数（from ExamSprintPolicy）──
    sprint_policy_summary: str          # ExamSprintPolicy 的自然语言摘要
    days_remaining: int | None
    triage_level: str | None            # “emergency” / “high” / “balanced”
    retrieval_policy_note: str | None   # 检索优先策略的一句提示

    # ── 动力/成就读数（from Achievement Engine）──
    motivation_signal: str | None       # 最近动力信号摘要
    recent_wins: list[str]              # 最近的成就/进展

    # ── 复盘历史读数（from Checkpoint History）──
    last_checkpoint_summary: str | None  # 上次复盘的摘要
    unresolved_blockers: list[str]       # 未解决的卡点

    # ── 记忆读数（from Memory Service）──
    relevant_memories: list[str]         # 与当前情境相关的记忆片段

    # ── 当前对话上下文 ──
    conversation_so_far: str            # 当前对话的紧凑摘要
    user_latest_message: str            # 用户最新消息
```

### 5.1 读数由谁产出

| 读数 | 来源系统 | 处理方式 |
|------|---------|---------|
| `user_state_summary` | State Aggregator | 聚合 15+ 子系统 → 自然语言摘要 |
| `srl_phase` / `cognitive_load` | SRL Phase Tracker | 直接读 |
| `task_progress` | Task Manager | 查询任务表 → 聚合完成率 |
| `sprint_policy_summary` | ExamSprintPolicyEngine | `build()` → `to_dict()` → 自然语言摘要 |
| `motivation_signal` | Achievement Engine | 最近事件聚合 |
| `last_checkpoint_summary` | Checkpoint History | 查询最近 checkpoint 记录 |
| `relevant_memories` | Memory Service | 语义检索当前情境相关记忆 |

### 5.2 关键原则

1. **读数是预处理后的自然语言摘要，不是原始 JSON 或 SQL 结果。**
   Aurora 读的是”用户最近 3 天没完成任何任务，动力信号偏低”，不是 `{“completion_rate”: 0.0, “streak”: 0}`。

2. **每个读数对应一个系统接口，不是 Aurora 自己去查数据库。**
   Aurora 不执行 SQL、不调 API、不处理原始数据。

3. **Aurora 可以选择性忽略某些读数。**
   仪表盘上有很多表盘，驾驶员不需要同时看所有表。Decision Loop 的 LLM 自己决定关注哪些。

### 5.3 Milestone B 深化后的 Dashboard 合同

当前运行时实现里，`DashboardReadout` 至少必须显式携带以下 6 组读数，供 Decision Loop 做稳定判断：

1. **`covered_domains`** — 当前已经补齐的核心 domain（至少覆盖 `goal / scope / baseline / time`）
2. **`missing_domains`** — 当前仍缺失、仍值得追问的 domain
3. **`recently_asked_domains`** — 最近几轮已经问过的问题域，用于拦截重复追问
4. **`sprint_policy_summary`** — 冲刺策略摘要（mode / days_remaining / headline / non-negotiables）
5. **`explicit_user_constraints`** — 用户显式约束与系统硬边界（DND / privacy / disabled action / stated constraints）
6. **`latent_thread_recovery_candidates`** — 可被 `soft_return_topic` 回收的潜在线索候选，而不是原样暴露线程队列

这 6 组读数是 Decision Loop 的稳定控制面，不再允许退化成“只看最近一句 + 几个关键词”。

---

## §6 Module 4: Aurora Decision Loop（必须替换模板）

**核心：Aurora 的 LLM 调用只做认知推理，不生成用户文本。**

### 6.1 输入

```python
@dataclass
class DecisionInput:
    dashboard: DashboardReadout          # 系统仪表盘读数
    aurora_state: AuroraState            # Aurora 当前内部状态
    control_surface: ControlSurfaceReading  # 可调参数 + 硬边界
    relevant_skills: list[SkillAffordance]  # 按需加载的开关说明
    new_event: str                       # 触发本次决策的事件描述
```

### 6.2 输出（不含用户文本）

```python
@dataclass
class AuroraDecision:
    # ── Aurora 的认知判断 ──
    current_assessment: str          # Aurora 当前怎么看用户/情境
    information_gaps: list[str]      # Aurora 认为自己还缺什么信息
    suggested_intent: str            # Aurora 建议下一步做什么
                                     # “pursue_tension” | “confirm_understanding” |
                                     # “soft_return” | “encourage” | “schedule_follow_up” |
                                     # “wait” | “adjust_approach”
    suggested_tension_id: str | None  # 指向哪个缺口

    # ── 给 Chat 层的指令 ──
    chat_intent: str                 # 告诉 Chat 层应该表达什么意图（不是文本）
                                     # 例如：”温和地追问学习节奏”
                                     #      “确认你理解了用户的目标”
                                     #      “简短回应跑题，然后自然带回”

### 6.3 Decision Loop 的硬约束（Milestone B 深化）

1. **`modeling_complete` 只能由 Decision Loop 最终裁定。**
   它可以参考 dashboard coverage，但不能由前端轮次、固定轮数或“差不多了/就这些”等关键词触发。

2. **动作语义必须稳定区分。**
   - `emit_message`：当前轮要给用户可见响应
   - `wait`：当前轮不发用户可见消息
   - `soft_return_topic`：先接住 detour，再回收 latent thread
   - `drop_thread`：显式放弃一个已过时或无价值的 latent thread

3. **已补齐的 domain 不允许重复追问。**
   如果某个 tension 对应 domain 已进入 `covered_domains`，或者刚出现在 `recently_asked_domains`，Decision Loop 必须重定向到别的缺口，或直接进入完成态。

4. **越界建模继续硬拦截。**
   `clinical / personality / social-identity` 相关输出只要出现在 decision payload，就必须被系统拒绝，不能依赖 LLM 自觉。
    chat_tone: str                   # “warm” | “structured” | “exploratory”
    chat_urgency: str                # “relaxed” | “normal” | “urgent”

    # ── 状态更新 ──
    state_updates: dict[str, Any]    # 对 AuroraState 的更新
    harness_updates: dict[str, Any] | None  # 对 Control Surface 的调整
    wake_schedule: dict[str, Any] | None    # 如需安排唤醒

    # ── 元数据 ──
    surface_complete: bool
    modeling_complete: bool
    reasoning_trace: str             # Aurora 的推理过程（debug 用）
```

**关键区别：`chat_intent` 是意图描述，不是用户文本。**
例如 `chat_intent = “温和地追问用户一天中哪个时段最容易卡住”`，
Chat 层会根据这个意图 + conversation_style + 用户上下文生成实际的话。

### 6.3 LLM Prompt

```
你是 Aurora，Sparkle 的认知核心。

你的职责是理解用户、判断情境、做出认知决策。
你不直接和用户对话。你输出的是决策和意图，由 Chat 层翻译成用户能看到的话。

## 仪表盘读数
{dashboard_readout}

## 你的内部状态
信息缺口: {informational_tensions}
当前意图: {current_intent}
潜在线程: {latent_threads}
行为参数: {activity_profile}

## 触发事件
{new_event}

## 硬边界
{hard_bounds}

## 可用控制说明
{relevant_skills}

---

基于以上信息，做出你的认知判断。

输出 JSON：
{
  “current_assessment”: “你对当前用户/情境的整体判断”,
  “information_gaps”: [“你还缺什么信息”],
  “suggested_intent”: “下一步应该做什么”,
  “suggested_tension_id”: “指向哪个缺口（如有）”,
  “chat_intent”: “告诉 Chat 层应该表达什么意图（不是文本！）”,
  “chat_tone”: “warm/structured/exploratory”,
  “chat_urgency”: “relaxed/normal/urgent”,
  “state_updates”: { ... },
  “harness_updates”: { ... },
  “wake_schedule”: { ... },
  “surface_complete”: false,
  “modeling_complete”: false,
  “reasoning_trace”: “你的推理过程”
}
```

### 6.4 LLM 选型与成本控制

| 场景 | 模型 | 预估 token | 理由 |
|------|------|-----------|------|
| 建模对话 | claude-haiku-4-5 | 300-500 | 决策简单、频率高、要快 |
| 规划澄清 | claude-haiku-4-5 | 300-500 | 同上 |
| Checkpoint 复盘 | claude-haiku-4-5 | 300-500 | 同上 |
| 定时唤醒决策 | claude-haiku-4-5 | 200-400 | 上下文更少 |
| 用户情绪波动大 | claude-sonnet-4-6 | 400-600 | 需要更细致的推理 |

**成本优势**：因为 Aurora 不生成用户文本，每次 LLM 调用的 output 只有 200-400 token（JSON 决策），而不是完整对话。比让 LLM 直接聊天便宜 5-10x。

### 6.5 执行流程

```text
新输入/到时事件进入
    │
    ├─→ 系统脚手架处理原始数据 → DashboardReadout
    │
    ├─→ 读取 AuroraState（Redis + PG）
    │
    ├─→ 读取 Control Surface + 硬边界
    │
    ├─→ 按需加载 Skills
    │
    ├─→ 组装 DecisionInput
    │
    ├─→ 调用 LLM（Decision Loop）
    │     输入：DecisionInput
    │     输出：AuroraDecision（JSON）
    │
    ├─→ 校验决策合法性（不越界、不违反硬边界）
    │
    ├─→ 执行状态更新
    │     ├─ 更新 AuroraState（tensions、intent、profile）
    │     ├─ 如有 harness 调整 → 更新 Control Surface
    │     ├─ 如有 wake → 写入 ScheduledWake
    │
    ├─→ 把 AuroraDecision 传给 Chat Layer Adapter
    │     ├─ Chat 层根据 chat_intent + chat_tone + chat_urgency 生成用户文本
    │     ├─ 可能生成 1-3 条消息
    │     ├─ 通过 gRPC stream yield（CONTINUE → STOP）
    │
    └─→ 如果 surface_complete=false 且 Aurora 的 reasoning 表明还要继续
         → 用更新后的 state 再走一轮 Decision Loop（上限 3 轮）
```

---

## §7 Module 5: Chat Layer Adapter（新增）

**把 Aurora 的决策意图翻译成用户能看到的自然对话。**

这一层可以是 LLM 调用，也可以是 LLM + 模板混合。但它和 Aurora Decision Loop 是**完全分离**的两个调用。

### 7.1 接口

```python
@dataclass
class ChatLayerInput:
    chat_intent: str               # Aurora 的意图描述
    chat_tone: str                 # 风格
    chat_urgency: str              # 紧迫度
    user_context: dict[str, Any]   # 用户上下文
    conversation_history: str      # 对话历史摘要
    aurora_assessment: str         # Aurora 的当前判断（帮助 Chat 层理解为什么）
    surface: str                   # 当前 surface

@dataclass
class ChatLayerOutput:
    messages: list[str]            # 1-3 条用户可见的消息
    metadata: dict[str, Any]       # 传回前端的 metadata
```

### 7.2 Chat 层 Prompt

```
你是 Sparkle 的对话层。你的朋友 Aurora（认知核心）刚刚做出了判断，你需要把它的意图变成用户能听懂的话。

Aurora 的判断：{aurora_assessment}
Aurora 想让你表达：{chat_intent}
语气：{chat_tone}
紧迫度：{chat_urgency}
对话历史：{conversation_history}

规则：
- 你可以发 1-3 条消息。每条消息独立、自然、不像问卷。
- 不要用”回到刚才的话题””我们继续”这种机械用语。
- 不要把 Aurora 的内部术语（如 tension、surface）暴露给用户。
- 如果紧迫度高，消息要短、直接。
- 如果紧迫度低，可以更温和、更开放。

输出 JSON：
{
  “messages”: [“消息1”, “消息2”],
  “metadata”: { ... }
}
```

### 7.3 v1 的 Chat 层实现选项

| 选项 | 做法 | 成本 | 质量 |
|------|------|------|------|
| A：LLM 生成 | 每次调 claude-haiku-4-5 | ~200-300 token output | 最高 |
| B：LLM + 模板混合 | 常见意图用模板，复杂意图走 LLM | 最低 | 够用 |
| C：纯模板 | 根据 chat_intent 选模板 | 零 | 最低但可控 |

**v1 建议选 B**：建模和规划的常见意图（追问、确认、带回、鼓励）用高质量模板；复杂场景（用户情绪波动、多轮 detour）走 LLM。

### 7.4 关键：这是两个独立的 LLM 调用

```
Decision Loop（Aurora 认知）     Chat Layer（对话生成）
  模型：haiku                       模型：haiku 或模板
  输入：仪表盘 + 状态               输入：AuroraDecision + 用户上下文
  输出：决策 JSON                   输出：1-3 条消息
  成本：~300 token                  成本：~200 token 或 0（模板）
  上下文：100% 用于认知              上下文：100% 用于对话
```

---

## §7 Module 5: Skill-as-Manual / Affordance Registry

Skill 在这里的角色，不是“业务知识仓库”，而是 Aurora 的操作说明书。

Aurora 需要调哪个开关，就按需读取对应说明，而不是把所有控制规则常驻塞进上下文。

### 7.1 v1 技能范围

| Skill ID | 作用 |
|---|---|
| `aurora.proactive_intensity` | 主动强度调节说明 |
| `aurora.conversation_style` | 风格选择说明 |
| `aurora.task_density_hint` | 任务密度建议说明 |
| `aurora.wake_scheduling` | 自主唤醒说明 |
| `aurora.agenda_priority` | 议程优先级说明 |

### 7.2 候选加载，而非固定映射

v1 只允许系统做“候选过滤”，不允许写死“某个 trigger 一定加载某个 skill 并按某顺序执行”。

```python
async def load_candidate_affordances(surface: str) -> list[SkillBrief]:
    surface_candidates = {
        "aurora_modeling": [
            "aurora.proactive_intensity",
            "aurora.conversation_style",
            "aurora.agenda_priority",
        ],
        "aurora_planning": [
            "aurora.conversation_style",
            "aurora.agenda_priority",
            "aurora.task_density_hint",
        ],
        "aurora_checkpoint": [
            "aurora.conversation_style",
            "aurora.task_density_hint",
            "aurora.wake_scheduling",
            "aurora.agenda_priority",
        ],
    }
    return [SKILL_REGISTRY[x] for x in surface_candidates.get(surface, [])]
```

### 7.3 明确禁止

禁止在文档里写死：

- 建模初期必须 `schedule > motivation > learning_style > knowledge_level`
- 遇到某类事件就必须读取某个 skill
- 某个 domain 永远优先级最高

这些都应该来自 Aurora 结合状态的整体判断。

---

## §8 Outcome Layer（价值层）

这份规格不是为了做一个“更会聊天的 AI”，而是为了让这种新的交互形态真的转化为用户价值。

### 8.1 Aurora 层价值

Aurora 层主要负责：

- 让用户更愿意说真话
- 让系统更早拿到关键上下文
- 让用户感觉自己被理解、被持续跟着
- 降低问卷感和机械感

### 8.2 执行层价值

执行层主要消费 Aurora 的输出，目标是：

- 更快到达有效任务
- 更早发现卡点
- 更及时补强
- 更直接帮助小林 7 天不挂科

### 8.3 三条总价值约束

每个 Milestone 都必须回答：

1. **Goal Fit**
   这一步是否让用户更接近目标，而不是只更像人

2. **User Value Conversion**
   这一步是否至少做到以下之一：
   - 更容易学下去
   - 计划更贴合
   - 少走弯路

3. **Measurable Advantage**
   是否能在工程上观察到：
   - 信息收集更完整
   - 重复追问更少
   - 卡点更早发现
   - 有效任务更快到达

### 8.4 验收标准分层

从现在开始，文档里的 gate 分两类：

- `工程 gate`
  Codex 可直接交付、可自动化验证
- `产品验证`
  架构师/产品继续做体验评估，但不把主观研究问题写成阻塞工程上线的硬门槛

---

## §9 Milestone 重新切分

### Milestone A: Runtime Substrate + Protocol Groundwork

这是 v1 真正的起点，先搭地基，再做体验。

**定位澄清**：Milestone A 只验 substrate。它证明 Aurora 有状态、控制面、协议和 wake
基础设施，但不证明 Aurora 已经具备“朋友感”或认知主体感。任何基于模板回复的
“像朋友”验收都不算数。

#### 范围

- `AuroraStateService`
- `ControlSurfaceService`
- `AuroraDecisionLoop`
- `Skill/Affordance Registry`
- `aurora_state_snapshots` / `aurora_scheduled_wakes`
- `FinishReason.CONTINUE`
- Python / Go / mobile 的 stream 透传与解析适配
- `ENABLE_AURORA_RUNTIME_V1`

#### 工程验收

- migration 成功
- Runtime State 以 `user_id + surface + conversation_id` 存储
- `FinishReason.CONTINUE` 全链路透传成功
- mobile parser 不把 `CONTINUE` 当 `DoneEvent`
- `ENABLE_AURORA_RUNTIME_V1=false` 时现有流程完全不变

#### 价值验收

- Aurora 能维护并更新 `informational_tensions`
- 用户中途插话后，原本重要 tension 不丢失
- harness 调整能反映状态变化，而不是随机波动

### Milestone B: ModelingChatScreen 改造成 Aurora Surface

**Milestone B 的关键修正**：必须把 `_infer_agenda_priority`、`_build_message_plan`、
`_looks_like_modeling_complete` 这类关键词/模板职责替换为
`DashboardReadout -> AuroraDecisionLoop(LLM JSON decision) -> ChatLayerAdapter`。
Decision Loop 只做认知判断，不产出最终用户文本；用户可见短消息由 Chat Layer 根据
`chat_directive` 生成。

#### 范围

- `ModelingChatScreen` 切到流式链路
- onboarding modeling 走 Aurora path
- Aurora 可连续发 2-3 条自然消息
- 用户可在 CONTINUE 期间插话
- 建模完成由 Aurora Decision Loop 判定，不再靠固定 `_assistantTurns >= 4` 或关键词

#### 工程验收

- `context.mode=onboarding_modeling` 时走 Aurora runtime
- acceptance 脚本能看到真实 `CONTINUE -> CONTINUE -> STOP`
- 用户插话后，下一 micro-turn 可见新输入
- metadata 中存在 `modeling_complete`
- Decision Loop prompt 包含 dashboard readout、hard boundaries、candidate affordances
- Decision Loop prompt 不要求生成最终用户话术
- DND / privacy boundary / disabled action 能覆盖 LLM 决策

#### 价值验收

- 用户已回答的信息不再被重复追问
- 从建模到可规划，不超过 5 轮
- Aurora 建模覆盖至少 4 个有效 domain
- 连续消息每条都在推进理解，而不是机械拆句
- `modeling_complete` 不再依赖任何关键词，而是来自 Decision Loop 对 domain coverage 的闭合判断

#### 产品验证

- 非团队用户是否明显感觉“更像聊天，没那么像问卷”

### Milestone C: Planning Surface 的自然带回

#### 范围

- 规划澄清接入 Aurora runtime
- 支持 detour 后自然带回
- 用户已补充的信息自动填补 tension，不再回问

#### 工程验收

- 打断规划后能保留 latent thread
- 2-3 轮内可自然带回
- 规划 prompt 能消费 Aurora state 而非只看最近一轮消息

#### 价值验收

- 规划产出引用更多用户真实信息
- 不再对已给信息进行重复追问
- 带回不是固定模板，不靠“回到刚才的话题”硬拉回

### Milestone D: Checkpoint 的自设跟进

#### 范围

- checkpoint 复盘后由 Aurora 决定是否安排跟进
- Aurora 设定 `next_wake_at`
- wake 到时后进入 Aurora runtime
- DND 内 suppress 或顺延

#### 工程验收

- `aurora_scheduled_wakes` 可写、可触发、可执行、可 suppress
- 同一用户不同情境下可得到不同 wake 时间
- 到时触发后消息能落到正确 surface / 会话

#### 价值验收

- 跟进内容引用用户具体卡点，不是泛泛问候
- 不在勿扰时段打扰用户
- 进展顺利与卡住的用户得到不同跟进节奏

---

## §10 可重放验收脚本

必须提供：

`scripts/aurora_v1_acceptance.py`

最小覆盖：

1. **多消息验证**
   - AI 至少连续发 2 条
   - 不是单条长文

2. **插话验证**
   - 用户在 CONTINUE 期间插话

3. **建模价值验证**
   - `<= 5` 轮进入有效规划
   - `0` 次重复追问
   - 至少覆盖 `目标 / 范围 / 基础 / 时间` 4 个 domain
   - 连续消息不存在拆句和明显语义重叠
   - Aurora 后续行为既不丢话题，也不机械重复

3. **缺口关闭验证**
   - 用户补上系统正在缺的信息
   - Aurora 不再重复问同一个问题

4. **建模完成验证**
   - Aurora 自己决定结束
   - 输出 `modeling_complete=true`

5. **wake 验证**
   - Aurora 可以设未来唤醒
   - DND 内不触发

---

## §11 与现有系统的集成点

### 11.1 新增文件

```text
backend/app/aurora/runtime_v1/
├── __init__.py
├── state.py                    # 已存在，保留
├── persistence.py              # 已存在，保留
├── control_surface.py          # 已存在，保留
├── skills.py                   # 已存在，保留
├── wake_scheduler.py           # 已存在，保留
├── models.py                   # 已存在，保留
├── service.py                  # ⚠️ 必须重写：删除模板，改为 LLM Decision Loop
├── dashboard_readout.py        # 🆕 新增：仪表盘读数聚合层
├── decision_loop.py            # 🆕 新增：LLM 认知推理核心
├── chat_layer.py               # 🆕 新增：对话生成层
├── checkpoint_runtime.py       # 已存在，需适配新架构
├── planning.py                 # 已存在，需适配新架构
└── prompts/
    ├── decision_loop_prompt.py # 🆕 新增：Aurora 认知推理 prompt
    └── chat_layer_prompt.py    # 🆕 新增：对话生成 prompt

backend/alembic/versions/xxxx_aurora_runtime_v1.py  # 已存在
scripts/aurora_v1_acceptance.py                      # 已存在，需更新
```

### 11.2 必须重写的文件

| 文件 | 原因 |
|------|------|
| `service.py` | 删除 `_build_message_plan`、`_infer_agenda_priority`、`_looks_like_modeling_complete` 等全部模板代码。改为调用 `DecisionLoop` + `ChatLayer` |

### 11.3 修改文件

| 文件 | 变更 |
|---|---|
| `orchestrator.py` | `_stream_aurora_runtime_v1` 改为：调 DecisionLoop → 拿 AuroraDecision → 传 ChatLayer → yield 消息 |
| `checkpoint_runtime.py` | 复盘后调 DecisionLoop 而不是直接写固定消息 |

### 11.4 已正确实现、无需改动的部分

- `state.py` — AuroraState 数据模型正确
- `persistence.py` — Redis + PG 持久化正确
- `control_surface.py` — 5 参数 + 硬边界正确
- `skills.py` — 5 个 skill 注册正确
- `wake_scheduler.py` — DND suppress 正确
- `models.py` — ORM 模型正确
- Proto `FinishReason.CONTINUE=6` — 已正确
- Go gateway CONTINUE 透传 — 已正确
- Mobile CONTINUE 解析 — 已正确

---

## §12 Codex 执行约束

1. 每个 Milestone 单独 handoff：
   `docs/product/AURORA_V1_MILESTONE_{A|B|C|D}_HANDOFF.md`

2. `ENABLE_AURORA_RUNTIME_V1=false` 是红线：
   关闭时不得影响任何现有流程

3. 不能修改已有测试以“配合”新实现：
   只允许新增测试

4. proto 改动后必须：
   `make proto-gen`

5. 所有新代码必须能回答：
   - 这是 Aurora 层还是执行层
   - 它对北极星的直接价值是什么

---

## §13 北极星验收（最终）

最终不是验“像不像人”，而是验：

1. 建模是否更完整，从而让规划更贴用户真实情况
2. 卡点是否更早被发现，从而补强更及时
3. 主动跟进是否出现在最该出现的时候，而不是成为打扰

如果这三条不成立，Aurora Runtime v1 就不算成功。

---

**文档版本**: 2.1.0 — 明确 Milestone A 是 substrate，Milestone B 才是 LLM Decision Loop 落地
**核心变更**: Aurora 不再直接生成用户文本。Decision Loop（LLM）只做认知推理，Chat Layer 独立生成对话。模板代码必须删除。
**已完成的正确实现**: AuroraState、Persistence、Control Surface、Skills、Wake Scheduler、Proto CONTINUE、Go 透传、Mobile 解析 — 这些全部保留。
**Milestone B 实施口径**: service.py 调用 DashboardReadout + LLM Decision Loop + Chat Layer，模板只能作为失败兜底，不能作为价值验收依据。
