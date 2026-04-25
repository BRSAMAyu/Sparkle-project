# Sparkle 对齐文档 — 项目全貌与愿景锚定

> **Status**: LIVE — 本文档是 Sparkle 项目的唯一对齐锚点
> **Date**: 2026-04-25
> **Maintainer**: BRSAMA (Chief Architect)
> **Version**: 1.0.0
> **Purpose**: 当任何人（新成员、评审、投资人、合作伙伴）想要了解 Sparkle 的全貌和进展时，这份文档是入口。所有子文档从这里索引。

---

## §0 愿景锚定（不可变）

### 创始人原话

> Sparkle 的本质是帮助用户跨越"理想中的自己"和"现实中的自己"之间鸿沟的 AI 学习成长系统。

这不是一个聊天机器人。不是学习助手。不是功能很多的学习 App。

Sparkle 要做的事情只有一个：**让用户成为更好的自己**。学习只是成长的载体。

### 北极星

**一个零基础的大学生（小林），用 Sparkle 7 天后通过考试。**

在这 7 天里，他从第一天建模时就能感觉到——这不是一个在填问卷的产品，这是一个真的在理解他的朋友。系统不会问无意义的问题，不会重复已经获得的信息，不会在他偏航时强行拉回，也不会在他卡住时无动于衷。

### 需求五层结构

| 层级 | 需求 | 用户内心表达 |
|------|------|-------------|
| 1 | 行为发生 | "我今天真的做了" |
| 2 | 卡点可见 | "我终于知道自己卡在哪里" |
| 3 | 路径清晰 | "我知道接下来该怎么走" |
| 4 | 自我效能 | "我知道自己是能做到的" |
| 5 | 自我实现 | "我正在成为更好的自己" |

第 5 层是北极星。第 4 层"自我效能感"是最核心的长期体验。第 2 层"卡点可见"是当前最关键的中枢。

### 成长循环：7 阶段

```
感知(Sense) → 澄清(Clarify) → 规划(Plan) → 执行(Execute)
     ↑                                              ↓
  适应(Adapt) ← 强化(Reinforce) ← 反思(Reflect)
```

所有模块必须映射到其中一个阶段。

### 6 步规划循环（设计愿景）

1. **Goal Clarification** — 理解目标是什么、为什么
2. **Goal Structuring** — 把抽象目标转化为可追踪、可审计的结构化指标
3. **Status Modeling** — 自我模型（会什么/不会什么）+ 外部模型（资源、约束、日程）
4. **Bottleneck Analysis** — 当前状态与目标之间的具体、结构性差距
5. **Path Selection** — 策略层：阶段划分、节奏、检查点、何时调整
6. **Task Decomposition** — 具体任务卡，含指南、材料、成功标准

---

## §1 产品定义

### 一句话口径

`Sparkle 是一个围绕学习场景构建、帮助用户持续走向更好自己的 AI 学习成长系统。`

### 完整定义

`Sparkle 是一个通过感知、诊断、干预、验证和再优化，帮助用户跨越理想与现实落差的 AI 学习成长系统。`

### 定位演进

| 阶段 | 定位 | 时间 |
|------|------|------|
| 短期 | AI 学习教练 | 用户可感知到的角色 |
| 长期 | AI 成长操作系统 | 系统的真正本质 |

### 产品分层

| 层 | 优化目标 | 典型场景 | 交互形态 |
|---|---------|---------|---------|
| **Aurora 层** | 朋友感、长期理解、主动关怀 | 建模、规划澄清、checkpoint 复盘 | 非回合式、可连续多条、可带回话题 |
| **执行层** | 最小阻力帮用户实现目标 | 任务执行、具体答疑、计划落地 | 轻量回合制、快、准、少废话 |

> 参见 [`docs/product/SPARKLE_PRODUCT_CONSENSUS_2026-04-02.md`](product/SPARKLE_PRODUCT_CONSENSUS_2026-04-02.md)

---

## §2 技术架构全景

### 三明治架构

```
┌──────────────────────────────────────────────────────────────┐
│  FLUTTER (表现层)                                             │
│  732 .dart files | Riverpod | GoRouter | 多感官 UX            │
├──────────────────────────────────────────────────────────────┤
│  GO GATEWAY (协调层)                                          │
│  24 .go files | 16 middleware | Gin + WebSocket               │
├──────────────────────────────────────────────────────────────┤
│  PYTHON ENGINE (智能层)                                       │
│  319+ .py files | LangGraph FSM | FastAPI + gRPC | 30+ 服务    │
└──────────────────────────────────────────────────────────────┘
         ↕ PostgreSQL 16 + pgvector + AGE
         ↕ Redis Stack (缓存 + Streams + Rate Limit)
         ↕ gRPC / WebSocket
```

### 规模

| 指标 | 数量 |
|------|------|
| 源代码文件 | 1,200+ |
| 数据库表 | 143 |
| 后端服务 | 26 |
| Go 中间件 | 16 |
| Flutter 功能模块 | 24 |
| Docker 容器 | 17 |
| Proto 定义 | 6 |
| Alembic 迁移 | 52 |
| 治理规则 | 53 |
| 测试通过 | 3,214+ (Python) + 34 (Go) + 131+ (Flutter) |

### 核心请求流

```
Flutter WebSocket → Go Gateway → gRPC → Python Orchestrator → LLM
                                              ↓
                                    Dual-Core Router (执行 vs 认知)
                                              ↓
                                    Tool Execution / RAG / Memory
                                              ↓
                                    Stream Response → Flutter UI
```

### 关键技术决策（ADR 记录）

| ADR | 标题 | 状态 |
|-----|------|------|
| 0002 | Proto v1 Single Source | Accepted |
| 0003 | Proto v2 Dual Stack Migration | Accepted |
| 0004 | Card Protocol Architecture | Accepted |
| 0005 | Multi-tenancy Strategy | Accepted |
| 0006 | Exam Prediction Data Strategy | Accepted |

> ADR 全部在 [`docs/adr/`](../adr/)

---

## §3 Aurora 认知核心

### §3.1 Aurora 是什么

**Aurora 是 Sparkle 的认知心脏。** 它不是分类器、不是规则路由器、不是模板引擎。它是一个持续维护内部状态的 LLM 认知主体。

Aurora 的动作来自整体推理，不来自关键词匹配或硬编码回复模板。

### §3.2 设计哲学（8 条锁定原则）

1. **Aurora 不是分类器。** 它是持续维护内部状态的 LLM 认知主体。
2. **Aurora 不直接和用户对话。** 它的 LLM 上下文 100% 用于认知决策。用户看到的对话由独立的 Chat 层生成。
3. **系统是脚手架，Aurora 是驾驶员。** 所有子系统负责数据处理，产出干净的仪表盘读数。Aurora 读这些读数，不处理原始数据。
4. **Aurora 能选择看什么、不看什么。** 仪表盘上有各种读数和开关，Aurora 自己决定优先看哪些。
5. **多条消息不是拆句。** 用户看到的多条连续消息是 Chat 层根据 Aurora 的决策意图生成的。
6. **主动性不是固定触发表。** 是否活跃、何时再来、跟进什么，由 Aurora 自己决定。
7. **未竟话题不是待办队列，而是信息缺失感。** Aurora 记住的是"这个人的哪一块我还没看清"。
8. **硬边界由系统强制，不可被 Aurora 覆盖。** 勿扰时段、隐私边界、禁用动作属于系统约束。

### §3.3 三层架构（v2.0）

这是 Aurora Runtime 最核心的架构决策：

```
┌──────────────────────────────────────────────────────────────┐
│  Chat Layer（对话层）                                         │
│  ChatLayerAdapter.render(decision, readout) → 1-3 条消息      │
│  独立 LLM 调用 | temperature 0.45 | 最多 3 条 | 每条 ≤260 字    │
│  Aurora 的决策意图 → 用户可见的自然对话                          │
├──────────────────────────────────────────────────────────────┤
│  Aurora Decision Loop（认知层）                                │
│  AuroraDecisionLoop.decide(readout) → AuroraDecision          │
│  纯 LLM 推理 | temperature 0.15 | 每次调用 200-500 token       │
│  输入：仪表盘读数 + 硬边界 + 技能候选                            │
│  输出：决策（action + chat_directive + harness_updates 等）     │
│  不生成用户文本！chat_directive 只描述意图                       │
├──────────────────────────────────────────────────────────────┤
│  System Scaffolding（系统脚手架）                              │
│  DashboardReadoutBuilder.build() → DashboardReadout           │
│  State Aggregator | ExamSprintPolicy | Galaxy | Task Manager  │
│  数据处理、管线、聚合 → 产出干净的仪表盘读数                      │
│  Aurora 不处理原始数据，只读预处理后的接口                        │
└──────────────────────────────────────────────────────────────┘
```

### §3.4 核心数据流

```
用户消息 / 定时唤醒 / 系统事件
    │
    ├─→ 系统脚手架 → DashboardReadout
    │
    ├─→ Aurora Decision Loop (LLM)
    │     输入：DashboardReadout + HardBounds + Skills
    │     输出：AuroraDecision（不含用户文本）
    │
    ├─→ 状态更新：AuroraState / ControlSurface / ScheduledWake
    │
    └─→ Chat Layer (LLM)
          输入：AuroraDecision + DashboardReadout
          输出：1-3 条用户可见消息
          传输：gRPC stream (CONTINUE → STOP)
```

### §3.4.1 当前锁定的运行时口径（2026-04-25）

- `DashboardReadout` 不是“最近消息摘要”，而是带有 `covered_domains / missing_domains / recently_asked_domains` 的控制面
- `Decision Loop` 必须自行裁定 `modeling_complete`，不能依赖关键词、固定轮数或上游模板信号
- `soft_return_topic` 只能用于回收真实 latent thread 候选；`drop_thread` 只能用于显式放弃线程
- Chat 层连续消息最多 3 条；每条都是完整句子；相邻消息不能只是改写同一句话
- `clinical / personality / social-identity` 越界建模继续由系统强拦截

### §3.5 关键文件

| 文件 | 职责 |
|------|------|
| `backend/app/aurora/runtime_v1/decision_loop.py` | LLM 认知核心：决定下一步做什么 |
| `backend/app/aurora/runtime_v1/dashboard.py` | 仪表盘读数：系统脚手架产出的预处理数据 |
| `backend/app/aurora/runtime_v1/chat_adapter.py` | Chat 层：决策意图 → 用户对话 |
| `backend/app/aurora/runtime_v1/service.py` | 三层编排：脚手架 → 认知 → 对话 |
| `backend/app/aurora/runtime_v1/control_surface.py` | 控制面板：5 参数 + 硬边界 |
| `backend/app/aurora/runtime_v1/state.py` | 状态容器：tensions、intent、profile |
| `backend/app/aurora/runtime_v1/planning.py` | 规划面：tension 管理 + latent thread |
| `backend/app/aurora/runtime_v1/checkpoint_runtime.py` | 检查点面：debrief → wake → follow-up |
| `backend/app/aurora/runtime_v1/skills.py` | 技能系统：5 技能 + 面向面加载 |
| `backend/app/aurora/runtime_v1/wake_scheduler.py` | 唤醒调度：DND suppress + Redis Sorted Set |
| `backend/app/aurora/runtime_v1/persistence.py` | 持久化：PG snapshots + scheduled wakes |
| `backend/app/orchestration/exam_sprint_policy.py` | 冲刺策略引擎：7 天生存 / 14 天巩固 |
| `backend/app/orchestration/orchestrator.py` | 入口：FSM 状态机 + Aurora path |

### §3.5.1 当前 acceptance 的价值锚点

`scripts/aurora_v1_acceptance.py` 现在至少验证 4 件事：

1. 建模在 `<= 5` 轮内进入可规划状态
2. 不会对同一已补齐 domain 重复追问
3. 建模至少覆盖 `目标 / 范围 / 基础 / 时间` 四个核心 domain
4. 连续消息不拆句、不语义重叠

### §3.6 Control Surface v1（5 参数锁定）

| 参数 | 范围 | 含义 |
|------|------|------|
| `proactive_intensity` | 0.0-1.0 | 主动介入强度 |
| `next_wake_at` | datetime or null | 下次主动唤醒时间 |
| `conversation_style` | warm/structured/exploratory | 对话风格 |
| `agenda_priority` | string or null | 当前优先追问的领域 |
| `task_density_hint` | 0.0-1.0 | 任务密度建议 |

### §3.7 建模边界

**允许的建模维度**：`dynamic_state`, `srl_phase`, `metacognitive_delta`, `task_self_efficacy`, `behavior_pattern`, `context_constraint`, `explicit_social_role`

**禁止的建模维度**：`clinical_diagnosis`, `personality_pathology`, `unconscious_interpretation`, `inferred_social_identity`, `trauma_attribution`, `mental_disorder`, `stable_trait_label`

社会角色策略：`explicit_or_user_confirmed_only`
稳定特质策略：`weak_prior_low_confidence_not_user_visible`

### §3.8 Exam Sprint Policy

| 模式 | 触发条件 | 策略核心 |
|------|---------|---------|
| `seven_day_survival` | ≤7 天 | 闭卷检索优先、禁止深度学习、低 ROI 标记 defer_or_skip |
| `fourteen_day_build_and_retrieve` | 8-14 天 | 学习-检索-间隔三轮、允许少量 deep learn、阶段模拟校准 |
| `standard_exam_sprint` | >14 天 | 常规检索循环、诊断-检索-反馈循环 |

### §3.9 规格文档

> [`docs/product/SPARKLE_AURORA_RUNTIME_V1_SPEC_2026-04-24.md`](product/SPARKLE_AURORA_RUNTIME_V1_SPEC_2026-04-24.md) — v2.0, 991 行

---

## §4 治理体系

### Aurora 治理规则（53 条）

通过 `scripts/rule_guard_manifest.tsv` 注册，CI 自动执行 `scripts/run_all_rule_guards.sh`。

| 规则族 | 规则编号 | 领域 |
|--------|---------|------|
| 写入隔离 | K, N, P, S, T | 聚合器写入隔离、推断提取、社交边界 |
| 评估/安全 | L, R, AM, AN, AO, AP, AQ | 置信度上限、用户隔离、诊断标签禁令、关联纪律 |
| 闭环 | G, I, J | 单次提交、交接完整性、用户价值闭环 |
| 边界 | H, M, O | 允许列表、编译器限制、静默扩展防护 |
| 可读性 | Q | 证据可读性 |
| 验证 | U, V | 可操作性证明、审计回归证明 |
| 质量 | W | 源状态映射保真度 |
| 推断 | Y | 推断提取写入治理 (Stage 16) |
| 社交 | Z | 跨用户隐私边界 (Stage 17) |
| 聚合器 | AB | 聚合器完整性 + push 证据治理 (Stage 18) |
| 工作记忆 | AC | WM session-scoped + LLM 提取器 Rule Y 门控 (Stage 19) |
| 充分性 | AD | 任务/上下文充分性分离 (Stage 20) |
| 冲突 | AE | 冲突覆盖审计 (Stage 20) |
| 技能 | AF | 技能 PII 管道 + 共享隔离 (Stage 21) |
| 视觉合规 | AS, AT, AU, AV | 信号消费者、孤儿检测、移动黑洞率 (0%)、kill switch 枚举 |
| 金融 | BB, BC | 原子光子授予、幂等键 |
| 安全 | AW, AX, AY, AZ | 速率限制器、路由所有权、LLM 安全层、EventBus 可靠性 |

### Kill Switch 三态协议

每个 Aurora 功能都有三态开关：`off`（禁用）→ `shadow`（计算但不影响线上）→ `live`（激活）。

全部开关暴露 `sparkle_kill_switch_mode{stage,feature}` 给 Prometheus。

完成率：**12/12**（核心）+ Stage 33-40 扩展。

### Rule Guard 运行方式

```bash
bash scripts/run_all_rule_guards.sh                    # 全部 53 条
bash scripts/run_all_rule_guards.sh --rule AO          # 单条
```

---

## §5 阶段进展

### Phase I：代码正确性与治理（已完成）

| 阶段 | 核心成就 | 基线测试 |
|------|---------|---------|
| Stage 4 | Dual-Core Router + 上下文组装 + FSM 集成 | 71+8+37+31 |
| Stage 5 | 用户模型分层架构 (L0-L3+UC), Rule K | Stage 4+5 |
| Stage 6 | 规范 UserInsightState + 投影契约 + 透明循环 | 143 backend |
| Stage 7 | 编译器适配器规范化 + 评估运行器 + 移动端透明消费 | 143+35+10 |
| Stage 8 | 断点 #3/#4/#5 闭合, Rule K CI guard | 144+50+13 |
| Stage 9 | Chat Profile 前门 + 纠正通道 + 评分评估器 | 144+27+15 |
| Stage 10 | LLM Judge 附件 + 可点击 L0 证据引用 + 图诊断面 | 144+31+17 |
| Stage 11 | 证据二次路由 + Judge 配置 + CL0 审计 | 144+14+51 |
| Stage 12 | Bayesian 关键修复 + save_state 修复 + 策略持久化 | 144+20+26+3skip |
| Stage 13 | Persistent Bayesian SQAM | 144+23+50 |
| Stage 14 | INTEG/SCALE/SHADOW 三轴验证 | 144+8+35/0+23+50 |
| Stage 15 | 分类内有限接线 + 仅仪表盘 + 影子守护 | 144+8+35/0+24+50+23+6+4 |
| Stage 16 | Memory Write Lane + Rule Y | 144+8+35/0+24+53+16+8 |
| Stage 17 | Social→Router 只读 + Accountability MVP + Rule Z | 97+15+51 |
| Stage 18 | User State Aggregator + 确定性 Push + Rule AB | 97+38+4+51 |
| Stage 19 | Working Memory + LLM Extractor + Consolidation + Rule AC | — |
| Stage 20 | Sufficiency Judge + Conflict Resolver + Route History | 31+10+4 |
| Stage 21 | Skill Store/Extract/Selection/Share + Rule AF | 31+10+4 |
| Stage 22 | Baseline Repair（Prompt 覆盖率审计 + 精度缺口闭合） | — |
| Stage 23-40 | Bayesian wire-on + Accountability + Reflection + Scene + Foresight + Traits + SRL + Metacognition + Idiographic + CL SQAM 收口 + EventBus + Gateway + HNSW + Kill Switch 三态化 | — |

### Phase I Exit Gate 签字状态

| 指标 | 结果 |
|------|------|
| Mobile 黑洞率 | `0.000%` |
| Kill Switch 三态完成率 | `12/12` |
| Core/Phase 热文件覆盖率 | `100%` (top-50) |
| Rule manifest 总量 | `53` 条，全部 PASS |
| SGW dogfood | CONDITIONAL (Phase II 首项收尾) |
| Phase I Exit Gate | **YES (ready with exception)** |
| 签字人 | Claude Opus 4.7 (on behalf of BRSAMA) |

> 完整 Exit Gate 文档：[`docs/product/SPARKLE_AURORA_PHASE_I_EXIT_GATE_2026-04-22.md`](product/SPARKLE_AURORA_PHASE_I_EXIT_GATE_2026-04-22.md)

### Phase II：体验优先（进行中）

#### 战略转型 (2026-04-23)

从 "有没有 bug" 转向 "有没有用"。技术成熟度 ≠ 用户感知价值。

#### 4 个关键缺口诊断

| 缺口 | 问题 | 影响 |
|------|------|------|
| P0 | SufficiencyChecker 只检查 CRUD 字段存在，跳过瓶颈分析 | 输出不比原始 ChatGPT 好 |
| P1 | 冷启动建模是表单式，不是 AI 会话式建模 | 缺少考试范围、知识地图、可用时间 |
| P2 | 任务卡是 DB 记录，缺少用户指南、AI 提示、任务级上下文 | 用户不知道怎么做 |
| P3 | AdaptiveReplanner 存在但无触发路径 | 用户跳过/卡住时系统无反应 |

#### Aurora Runtime v1（当前焦点）

Aurora Runtime v1 是 Phase II 的核心基础设施。它建立了三层架构（Chat Layer → Decision Loop → Scaffolding），让 Aurora 成为真正的认知引擎而非模板系统。

**Milestone 验收状态**：

| Milestone | 内容 | 状态 |
|-----------|------|------|
| A | 架构 + 规格 + Control Surface + Exam Sprint Policy | PASS |
| B | 三层核心实现：decision_loop + dashboard + chat_adapter | PASS CLEAN |
| C | Planning/Checkpoint 面集成 | CONDITIONAL PASS |
| D | Exam Sprint Mode 端到端验证 | PASS |

---

## §6 系统诊断：关键发现

### "连接断裂"而非"功能缺失"

2026-04-19 的五维度代码级审查发现：**Sparkle 不是缺功能，而是已有子系统之间的信号流断裂**。

| 发现 | 状态 | 影响 |
|------|------|------|
| Memory 读路径已通，**写路径断开** | Stage 16 修复写路径 | 对话中新偏好/目标不会被记录 |
| PushService 有 5 种策略但无**状态驱动唤醒** | Aurora Wake Scheduler 补齐 | 只有定时+事件触发，无偏离唤醒 |
| LLM Router 已是**生产级分层路由**（10+ tier, 5+ provider） | 保持 | 不是"单一 LLM 调用" |
| 社交系统完整但数据**不约束 AI 行为** | 待修复 | Accountability 数据不进入 AI 推理 |
| Skill/Procedural Store **完全缺失** | Stage 20-21 修复 | 无技能沉淀机制 |

### 数据利用率（修正后基线）

- 旧评估 "~5.0/10" 已过时
- Stage 22 起始基线：**~82% prompt 覆盖率**
- Stage 22 定位：精度缺口闭合 + 循环激活（不再是"从 30 行修复"）

> 完整诊断：[`docs/product/SPARKLE_ADVANCED_CONCEPTS_INTEGRATION_ANALYSIS_2026-04-19.md`](product/SPARKLE_ADVANCED_CONCEPTS_INTEGRATION_ANALYSIS_2026-04-19.md)

---

## §7 路线图总览

### Aurora Stage Roadmap

| Stage | 名称 | 状态 |
|-------|------|------|
| 4-8 | Dual-Core Router + User Model + Breakpoint Closure | DONE |
| 9-12 | Chat Profile + Judge + Bayesian Foundation | DONE |
| 13-15 | SQAM + Within-Category Wire-On | DONE |
| 16 | Memory Write Lane + Rule Y | DONE |
| 17 | Social→Router + Accountability MVP + Rule Z | DONE |
| 18 | User State Aggregator + Deterministic Push + Rule AB | DONE |
| 19 | Working Memory + LLM Extractor + Rule AC | DONE |
| 20 | Sufficiency Judge + Conflict Resolver | DONE |
| 21 | Skill System MVP + Rule AF | DONE |
| 22 | Baseline Repair | DONE |
| 23 | Bayesian Wire-On + SS-AUDIT | Locked |
| 24 | Accountability Policy Compiler | Locked |
| 25 | Reflection Wire-On (extension) | Locked |
| 26 | Scene Consolidation | Locked |
| 27 | Foresight (provisional) | Locked |
| 28 | Traits Weak Priors | Locked |
| 29 | SRL Phase Tracker + ScaffoldingFSM | Locked |
| 30 | Metacognition Expansion | Locked |
| 31 | Idiographic Lite (association only) | Locked |
| 32 | CL SQAM Tail Closeout | Locked |

> Roadmap 文档：
> - [`docs/product/SPARKLE_AURORA_ROADMAP_v2_1_AMENDMENT_2026-04-21.md`](product/SPARKLE_AURORA_ROADMAP_v2_1_AMENDMENT_2026-04-21.md)
> - [`docs/product/SPARKLE_AURORA_ROADMAP_v2_1_FAST_DEV_LOCK_2026-04-21.md`](product/SPARKLE_AURORA_ROADMAP_v2_1_FAST_DEV_LOCK_2026-04-21.md)

### Growth System Roadmap（3 Era, 6 Phase）

| Era | Phase | 重点 | 时间 |
|-----|-------|------|------|
| Foundation | 1 | 接通 Memory 注入、Error→Plan Replan、扩展 Context 预算 | 0-20 天 |
| Foundation | 2 | 接通 Calendar → AI Context、Achievement → AI Profile | 21-50 天 |
| Intelligence | 3 | 闭环 Outcome→Strategy、接通 Cognitive→Dual-Core Router | 51-70 天 |
| Intelligence | 4 | 接通 Social → Policy Compiler | 71-90 天 |
| Experience | 5 | 首屏改造为 Growth Dashboard、AI 感知个性化 | 后续 |
| Experience | 6 | Demo 打磨 | 后续 |

> [`docs/product/SPARKLE_GROWTH_SYSTEM_ROADMAP_2026-04-03.md`](product/SPARKLE_GROWTH_SYSTEM_ROADMAP_2026-04-03.md)

---

## §8 安全架构

### 认证

- JWT (HS256)：Access + Refresh tokens，含 exp/iat/jti/type/iss/aud claims
- Token Blacklist：JTI-based revocation + user-level revocation
- Fail-Closed：非开发环境默认 `REDIS_FAIL_CLOSED=true`

### 多层速率限制

- IP：10 req/s, burst 30
- Auth 端点：5 req/s, burst 15
- WebSocket 连接：5/min, burst 10
- 分布式：Redis sliding window + local fallback

### 安全头（自动注入）

`Content-Security-Policy` | `X-Frame-Options: DENY` | `X-Content-Type-Options: nosniff` | `Strict-Transport-Security` | `Referrer-Policy` | `Permissions-Policy`

### 生产守护

- `DEBUG=True` 在生产环境触发 `ValueError`
- 弱 `SECRET_KEY` 被拒绝
- `BACKEND_CORS_ORIGINS=["*"]` 被拒绝
- HTML 净化 via bluemonday in Go Gateway

---

## §9 监控与可观测性

```
Prometheus (9090) → Metrics + Alerting
Grafana (3000)    → Dashboards (Prometheus + Loki + Tempo)
Loki (3100)       → Log Aggregation
Tempo (4317)      → Distributed Tracing (OTLP)
Alertmanager (903)→ Alert Routing
```

### SLO 告警规则（11 条）

| 告警 | 严重性 | 条件 |
|------|--------|------|
| SparkleGatewayDown | P1 Critical | 不可达 2 分钟 |
| SparkleBackendDown | P1 Critical | 不可达 2 分钟 |
| SparkleBackendHigh5xxRate | P2 Warning | 5xx > 2% 持续 10 分钟 |
| SparkleBackendP95LatencyHigh | P2 Warning | P95 > 1.5s 持续 10 分钟 |
| SparkleEventStreamLagHigh | P2 Warning | Lag > 120s |

> Runbook：[`monitoring/runbooks/incident_response.md`](../monitoring/runbooks/incident_response.md)

---

## §10 CI/CD

### 主 CI Pipeline

| Job | 内容 |
|-----|------|
| lint | golangci-lint (22 linters) + ruff + mypy + flutter analyze |
| backend-test | Go tests (race + coverage) + Python tests + proto/dependency 检查 |
| flutter-test | Flutter tests + coverage + smoke + regression |
| security-scan | Trivy + Gitleaks |

### 附加工作流（9 个）

E2E nightly/smoke | Quality baseline weekly | Benchmark | UI lint | Deploy prod | K8s CD | Gemini review/triage

---

## §11 文档地图

### 核心（必读）

| 文档 | 路径 | 内容 |
|------|------|------|
| **本文档** | `docs/product/SPARKLE_ALIGNMENT_2026-04-25.md` | 项目全貌与愿景锚定 |
| CLAUDE.md | `CLAUDE.md` | 工程指导（命令、架构、反模式、导航） |
| 产品共识 | `docs/product/SPARKLE_PRODUCT_CONSENSUS_2026-04-02.md` | 产品定义、需求层级、90 天计划 |
| Aurora Runtime v1 Spec | `docs/product/SPARKLE_AURORA_RUNTIME_V1_SPEC_2026-04-24.md` | 三层架构、模块定义、Milestone |
| Phase I Exit Gate | `docs/product/SPARKLE_AURORA_PHASE_I_EXIT_GATE_2026-04-22.md` | Phase I 签字验收、F1-F15 闭合 |
| Aurora Roadmap v2.1 | `docs/product/SPARKLE_AURORA_ROADMAP_v2_1_AMENDMENT_2026-04-21.md` | Stage 22-32 路线图 |
| Fast-Dev Lock | `docs/product/SPARKLE_AURORA_ROADMAP_v2_1_FAST_DEV_LOCK_2026-04-21.md` | Stage 23-32 锁定执行表 |
| Growth System Roadmap | `docs/product/SPARKLE_GROWTH_SYSTEM_ROADMAP_2026-04-03.md` | 3 Era 成长系统路线图 |

### 设计与规格

| 文档 | 路径 | 内容 |
|------|------|------|
| Card Protocol | `docs/product/SPARKLE_CARD_PROTOCOL_TAXONOMY_2026-04-02.md` | 卡片协议冻结分类（FROZEN） |
| Advanced Concepts | `docs/product/SPARKLE_ADVANCED_CONCEPTS_INTEGRATION_ANALYSIS_2026-04-19.md` | 五维度融合分析（v4.0, 代码验证） |
| Intervention Language | `docs/product/SPARKLE_INTERVENTION_LANGUAGE_SYSTEM_2026-04-02.md` | 干预语言系统 |
| Six Breakpoint Alignment | `docs/product/SPARKLE_SIX_BREAKPOINT_ALIGNMENT_2026-04-03.md` | 6 断点对齐 |
| Stage Dispatch Plans | `docs/product/SPARKLE_AURORA_STAGE{N}_DISPATCH_PLAN_*.md` | 各 Stage 执行计划 |
| Stage Handoffs | `docs/product/SPARKLE_AURORA_STAGE{N}_HANDOFF_*.md` | 各 Stage 交接文档 |

### 工程标准

| 文档 | 路径 |
|------|------|
| Quality Guardrails | `docs/engineering/quality_guardrails.md` |
| Tech Debt Register | `docs/engineering/technical_debt_register_2026-03-22.md` |
| SLI/SLO Targets | `docs/engineering/sli_slo_targets.md` |
| Flutter Quality Gate | `docs/engineering/flutter_quality_gate.md` |
| Contract Guardrails | `docs/engineering/contract_guardrails.md` |
| Definition of Done | `docs/engineering/definition_of_done_industrial.md` |
| Mobile Architecture | `docs/engineering/MOBILE_ARCHITECTURE_GOVERNANCE.md` |
| ADR Records | `docs/adr/` (7 个) |

### 验证与验收

| 文档 | 路径 |
|------|------|
| 本地签收清单 | `docs/verification/本地发布前最终启动与验收Checklist_2026-03-31.md` |
| 系统模块验收 | `docs/verification/系统模块验收清单_2026-03-31.md` |
| Semantic Control Vocab Audit | `docs/verification/SPARKLE_AI_SEMANTIC_CONTROL_VOCABULARY_AUDIT_2026-04-06.md` |
| Phase B/C/D 基线 | `docs/verification/SPARKLE_PHASE_{B,C,D}_*.md` |
| 用户交互链路总清单 | `docs/verification/全量用户交互链路总清单_2026-03-28.md` |

---

## §12 关键命令速查

```bash
make dev-all                  # 启动基础设施
make proto-gen                # proto 变更后重新生成
make sync-db                  # DB 变更后同步
make env-check                # 配置 + 连通性自检
make smoke                    # 全服务健康检查
make local-signoff-preflight  # 完整预检
make local-final-signoff      # 完整签收

cd backend && pytest                                    # Python 测试
cd backend/gateway && go test ./...                     # Go 测试
cd mobile && flutter test                               # Flutter 测试

bash scripts/run_all_rule_guards.sh                     # 53 条治理规则
bash scripts/run_all_rule_guards.sh --rule AO           # 单条规则

docker compose logs -f gateway                          # Go 日志
docker compose logs -f sparkle_agent                    # Python 日志
```

---

## §13 当前焦点

### 正在进行

- **Aurora Runtime v1 三层架构落地** — Milestone A-D 已验收，进入集成测试与端到端验证
- **Phase II 首项收尾** — SGW 三模式真跑 + 后端栈起动

### 下一步

1. Aurora Runtime v1 端到端验收（`scripts/aurora_v1_acceptance.py`）
2. Exam Sprint Mode 7 天体验端到端走通
3. Planning surface sidecar detour prompt 改造为 Decision Loop 驱动（post-v1）
4. Stage 23 (Bayesian Wire-On) 执行

### 已知的 post-v1 债务

1. Planning sidecar detour prompt 应通过 DecisionLoop
2. `service.py:132-133` 硬编码 fallback 与 `ChatLayerAdapter._fallback_messages()` 重复
3. `TENSION_PROMPTS` 硬编码可改为 LLM 生成
4. `integration/phase-i-exit` 分支需合并到 main

---

## §14 角色分工

| 角色 | 谁 | 职责 |
|------|-----|------|
| Chief Architect | BRSAMA | 决策、验收、方向 |
| 诊断 + 规格 | Claude / GLM-observer | 不碰代码，产出诊断文档和规格 |
| 实现执行 | Codex | 按规格写代码 |
| 验证 | CI + acceptance scripts | 自动化验证 |

---

## 附录 A：8 子系统审计结果（2026-03-31）

27 P0 blockers, 43 P1 UX gaps, 35+ P2 items across:

- 专注模式 + 计时 + 呼吸练习 (Phase 1-3 DONE)
- 错题本编辑/筛选/图片上传闭环 (Phase 2 DONE)
- 种子库质量评分+筛选+聊天集成 (Phase 2 DONE)
- 认知模式 PatternType 枚举+前后端同步 (Phase 2 DONE)
- 学习预测闭环 (Phase 3 DONE)
- 剧场预测 + 仿真 + 最优学习时间 (Phase 4 DONE)

**27 项声明全部 VERIFIED**

---

## 附录 B：验收测试覆盖（21 个验收脚本）

| 验收脚本 | 场景 |
|---------|------|
| `ai_chat_multiturn_acceptance.py` | AI 对话多轮 |
| `accountability_acceptance.py` | 责任伙伴 |
| `galaxy_plan_acceptance.py` | 星图计划 |
| `achievement_visual_acceptance.py` | 成就视觉 |
| `seed_library_acceptance.py` | 种子库 |
| `insights_acceptance.py` | 学习洞察 |
| `cognitive_capsule_acceptance.py` | 认知胶囊 |
| `community_acceptance.py` | 社群 |
| `focus_acceptance.py` | 专注系统 |
| `calendar_weather_acceptance.py` | 日历天气 |
| `memory_acceptance.py` | 记忆系统 |
| `notes_errorbook_acceptance.py` | 错题本 |
| `translation_dictionary_acceptance.py` | 翻译词典 |
| `document_stt_acceptance.py` | 文档语音 |
| `long_term_plan_acceptance.py` | 长期计划 |
| `celery_acceptance.py` | Celery 队列 |
| `security_acceptance.py` | 安全 |
| `api_contract_acceptance.py` | API 契约 |
| `community_admin_acceptance.py` | 社群管理 |
| `ai_expert_acceptance.py` | AI 专家模式 |
| `aurora_v1_acceptance.py` | Aurora Runtime v1 |

---

*Document Version: 1.0.0 | Last Updated: 2026-04-25 | Next Review: when milestones shift*
