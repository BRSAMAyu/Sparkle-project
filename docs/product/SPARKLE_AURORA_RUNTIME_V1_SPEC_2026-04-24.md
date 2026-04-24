# SPARKLE Aurora Runtime v1 — Adaptive Harness Engineering 实施规格

> **Status**: DRAFT → Codex 执行令（待 Chief Architect 签发）
> **Date**: 2026-04-24
> **Scope**: Aurora Runtime v1 最小可运行骨架
> **North Star**: 小林注册后第一次建模时，立刻感觉到“这不是问卷，这是一个真的在理解我的朋友”
> **Supersedes**: 本文档替代此前关于 Aurora Runtime / Adaptive Harness 的零散讨论

---

## §0 设计哲学（锁定）

1. **Aurora 不是分类器，不是规则路由器。**
   Aurora 是持续维护内部状态的认知主体。它的动作来自整体推理，不来自“补充/打断/问题”这类硬分类分支。

2. **多条消息不是拆句。**
   Aurora 连续发多条消息，不是把一段长文切碎，而是它此刻确实还有想说的、想确认的、想追的信息。

3. **主动性不是固定触发表。**
   系统可以提供时间、事件、静默、外部状态变化等候选信号，但是否活跃、何时再来、跟进什么，由 Aurora 自己决定。

4. **未竟话题不是待办队列，而是信息缺失感。**
   Aurora 记住的不是“我还有三句话没说”，而是“这个人的哪一块我还没看清”“哪一块判断还没闭合”。

5. **Aurora 层与执行层追求不同局部最优。**
   Aurora 层追求朋友感、理解感、持续在场感；执行层追求最高效率帮助用户达成目标。两层相辅相成，不混成一个聊天壳。

6. **硬边界由系统强制，不可被 Aurora 覆盖。**
   用户设定的勿扰时段、隐私边界、禁用动作、安全红线，都属于系统约束，不属于 Aurora 自调空间。

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

v1 锁定 5 个模块，但这 5 个模块只覆盖 **交互运行时内核**，不是全部愿景。

1. `AuroraState`
2. `Control Surface v1`
3. `Aurora Decision Loop`
4. `Conversation Runtime`
5. `Skill-as-Manual / Affordance Registry`

### 2.1 一句话定义

- `AuroraState`：Aurora 当前“怎么看用户、怎么看情景、自己还缺什么”的状态容器
- `Control Surface`：Aurora 可读可调的最小控制面
- `Decision Loop`：Aurora 在每个时刻决定“说/停/改/记/约未来”的推理核心
- `Conversation Runtime`：把 Aurora 的决定变成真实可见的连续消息交互
- `Skill-as-Manual`：Aurora 按需读取的控制说明书，而不是写死在 prompt 里的大段规则

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

## §5 Module 3: Aurora Decision Loop

Decision Loop 是 Aurora 的推理内核。任何进入 Aurora 视野的新输入，先进入 Decision Loop，再决定下一动作。

### 5.1 输入

```python
@dataclass
class DecisionInput:
    aurora_state: AuroraState
    new_event: AuroraEvent
    control_surface: ControlSurfaceReading
    candidate_affordances: list[SkillBrief]
    surface_policy: dict[str, Any]
```

`AuroraEvent` 允许但不限于：

- 用户发送消息
- Aurora 刚发完一条消息
- 先前安排的 wake 到时
- 外部状态变化（任务完成、checkpoint 到达）
- 静默持续到某个程度

### 5.2 输出动作

```python
@dataclass
class DecisionOutput:
    action: str
    messages: list[str]
    state_updates: dict[str, Any]
    harness_updates: dict[str, Any] | None
    wake_schedule: dict[str, Any] | None
    metadata: dict[str, Any]
```

v1 锁定动作集：

- `emit_message`
- `wait`
- `schedule_wake`
- `update_harness`
- `update_state`
- `soft_return_topic`
- `drop_thread`

### 5.3 决策原则

1. 用户新消息进入后，**立即进入 Aurora 视野**。
2. 这不意味着 Aurora 必须立刻停下。
3. Aurora 可以先完成当前这一个 `micro-turn`，再基于更新后的状态决定下一步。
4. 所以这既不是客户端排队，也不是“立刻硬打断”，而是 Aurora 自己决定如何续。

### 5.4 Prompt 骨架

```
你是 Aurora，Sparkle 的认知驾驶舱。

你不是被动客服。你在维护一个持续的内部状态。

当前 surface: {surface}
当前用户状态摘要: {user_model_snapshot}
当前信息缺失感: {informational_tensions}
当前主要意图: {current_intent}
潜在线程: {latent_threads}
当前行为参数: {activity_profile}
最新输入事件: {new_event}
硬边界: {hard_bounds}
可选控制说明: {candidate_affordances}

请整体判断你的下一步。不要把用户消息机械分类。
你可以说、停、调整、记住、安排未来，但必须遵守硬边界。

输出 JSON：
{
  "action": "...",
  "messages": ["..."],
  "state_updates": {...},
  "harness_updates": {...},
  "wake_schedule": {...},
  "metadata": {
    "reasoning_summary": "...",
    "surface_complete": false
  }
}
```

### 5.5 执行流程

```text
新输入/到时事件进入
  -> 读取 Runtime State + Cognitive Snapshot
  -> 读取 Control Surface + 硬边界
  -> 装配候选 affordances
  -> 调用 Decision Loop LLM
  -> 校验输出是否合法
  -> 执行动作
  -> 更新 Runtime State / Snapshot / Wake
  -> 如果 action=emit_message 且 metadata.surface_complete=false
     可继续下一轮 micro-turn（上限 3 段）
```

### 5.6 v1 的“不是规则机”边界

系统可以做的只有：

- 提供状态
- 提供边界
- 提供候选 affordances
- 校验输出不越界

系统**不做**：

- 不把消息先分类成“补充/打断/跑题”
- 不写死“建模一定先问 A 再问 B”
- 不写死“某个 trigger 一定加载某个 skill”

---

## §6 Module 4: Conversation Runtime

这是 v1 的关键工程前提。没有这一层，Aurora 再聪明也只能退化成回合制。

### 6.1 当前问题

- `ModelingChatScreen` 当前仍走 `sendMessage()` 的一次请求一次回复链路
- 现有 `StreamChat` 语义默认是一段内容完成后结束
- 当前移动端把任何非 `NULL` 的 `finish_reason` 都视为本轮结束

所以，**协议升级必须放在 Milestone A，而不是拖到 Modeling UX 再做。**

### 6.2 v1 协议策略

v1 采用 **同一条 gRPC stream 内多段消息** 的最小改法。

不是新建专用 WebSocket server-push 语义，不是新开第二套 proto。

### 6.3 FinishReason 扩展

只能在保持现有编号不变的前提下扩展：

```protobuf
enum FinishReason {
  NULL = 0;
  STOP = 1;
  LENGTH = 2;
  TOOL_CALLS = 3;
  CONTENT_FILTER = 4;
  ERROR = 5;
  CONTINUE = 6;
}
```

### 6.4 多消息语义

```text
Aurora 决定连续发 3 条：
  第 1 条 -> finish_reason=CONTINUE
  第 2 条 -> finish_reason=CONTINUE
  第 3 条 -> finish_reason=STOP
```

其中：

- `CONTINUE` 表示“这一轮 Aurora 还没收完”
- `STOP` 表示“这一轮 Aurora 暂时收住，等待用户或外部事件”

### 6.5 用户插话语义

用户插话期间的正确语义是：

1. 用户消息**立刻到达 Aurora ingress**
2. Aurora 在当前运行态里看到了它
3. Aurora 决定：
   - 先把眼前这一个 micro-turn 收完
   - 或立刻改口
   - 或把新输入吸收进下一条

**禁止写法**：

- “缓存到客户端队列，等 STOP 后再交给 Aurora”
- “CONTINUE 期间输入框完全不可用，用户无法插话”

### 6.6 Flutter 端约束

`ModelingChatScreen` 在 v1 必须切到流式链路。

最低要求：

- 不再走纯 REST `sendMessage()`
- 能识别 `CONTINUE`
- `CONTINUE` 期间输入框允许用户发送
- 新输入进入后不强制中断当前显示，但必须上送到运行时

### 6.7 传输层改造范围

这不是“一行 proto + 小改客户端”。

至少涉及：

- `proto/agent_service.proto`
- Python gRPC server / stream handler
- Go gateway 透传
- mobile WebSocket / stream parser
- `ModelingChatScreen` 输入/显示逻辑

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

#### 范围

- `ModelingChatScreen` 切到流式链路
- onboarding modeling 走 Aurora path
- Aurora 可连续发 2-3 条自然消息
- 用户可在 CONTINUE 期间插话
- 建模完成由 Aurora 判定，不再靠固定 `_assistantTurns >= 4`

#### 工程验收

- `context.mode=onboarding_modeling` 时走 Aurora runtime
- acceptance 脚本能看到真实 `CONTINUE -> CONTINUE -> STOP`
- 用户插话后，下一 micro-turn 可见新输入
- metadata 中存在 `modeling_complete`

#### 价值验收

- 用户已回答的信息不再被重复追问
- 从建模到可规划，不超过 5 轮
- Aurora 建模覆盖至少 4 个有效 domain
- 连续消息每条都在推进理解，而不是机械拆句

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
backend/app/aurora/
├── __init__.py
├── state.py
├── persistence.py
├── control_surface.py
├── decision_loop.py
├── skills.py
├── wake_scheduler.py
└── prompts/
    └── decision_loop_prompt.py

backend/alembic/versions/xxxx_aurora_runtime_v1.py
scripts/aurora_v1_acceptance.py
```

### 11.2 修改文件

| 文件 | 变更 |
|---|---|
| `/Users/brsama/code/GitHub/Sparkle-project/proto/agent_service.proto` | 扩展 `FinishReason.CONTINUE=6` |
| `/Users/brsama/code/GitHub/Sparkle-project/backend/app/orchestration/orchestrator.py` | 新增 Aurora runtime path |
| `/Users/brsama/code/GitHub/Sparkle-project/backend/app/config/settings.py` | 新增 `ENABLE_AURORA_RUNTIME_V1` |
| `/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/user/presentation/screens/modeling_chat_screen.dart` | 切到流式链路 |
| `/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/chat/data/services/websocket_chat_service_v2.dart` | 识别 `CONTINUE` |
| `/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/checkpoint_nudge_service.py` | 与 wake runtime 衔接 |

### 11.3 不动的部分

- 不重构整个 `ChatOrchestrator` 骨架
- 不替换 `DualCoreRouter`
- 不改任务执行聊天为朋友式连发
- 不改 governance manifest

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

**文档版本**: 1.2.0 — 重写运行时边界、状态分层、协议前提与双层价值目标
**等待**: Chief Architect 签发 → Codex 按 Milestone A 开始执行
