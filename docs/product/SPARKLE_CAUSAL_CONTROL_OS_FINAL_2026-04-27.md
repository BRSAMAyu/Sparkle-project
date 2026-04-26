# Sparkle 最终定稿方案 v1.0

> **日期**: 2026-04-27
> **版本**: v1.0 定稿
> **状态**: FINAL — 用户最终拍板

## Causal Control OS：把 Aurora、知识星图、任务卡、资料、社群、时间感知、主动建模全部接成一个可执行系统

我最终拍板：**Sparkle 下一阶段不应该再按"功能模块"推进，而应该按一个系统主脊柱推进。**

这条主脊柱不是普通的 Signal-to-Action，也不是普通 RAG，也不是普通用户画像，而是：

> **Causal Control Spine / 因果控制主脊柱**
> 让 Sparkle 的每一个重要观察，都能以可验证、可解释、可纠正、可审计的方式，改变它接下来如何帮助用户。

另一位专家的核心判断是对的：Sparkle 当前真正缺的不是"再多一个能力"，而是从信号到状态、从状态到裁决、从裁决到执行、从执行到结果、从结果再回到模型的 **可验证因果控制**。这也是我最终采纳的架构方向。

同时，Stage 3 的愿景基线也必须保留：Sparkle 不是考试 App，也不是聊天机器人，而是以 Exam Sprint 为第一个证明场的 AI-native 目标实现系统。Aurora 不是普通聊天人格，而是认知控制层；任务卡不是 todo，而是策略执行协议；知识星图不是展示页，而是可计算资产。

---

# 0. 最终裁决：Sparkle 到底是什么

Sparkle 的最终产品定义：

> **Sparkle 是一个 AI-native 的目标实现操作系统。**
> 它持续理解用户、目标、时间、材料、知识状态、执行行为、情绪负荷、社群信号和系统自身策略效果，并把这些理解转化为更好的计划、任务卡、资料调用、反馈、召回、纠偏和成长闭环。

Sparkle 不是：

```text
聊天机器人
RAG 知识库
学习计划生成器
任务清单 App
知识图谱展示页
成就系统
社群打卡工具
```

Sparkle 是：

```text
目标建模系统
+ 知识状态系统
+ 任务执行系统
+ Aurora 认知控制系统
+ 自适应 Context / Harness Engineering 系统
+ 因果反馈学习系统
+ 社群共调节系统
```

一句话：

> **别人让 AI 回答用户；Sparkle 让 AI 持续理解用户，并把理解转化成现实推进。**

这就是最终主线。

---

# 1. 总体架构：Sparkle Causal Control OS

最终系统分成两个平面：

```text
A. 交互平面 / Interaction Plane
用户真正感受到的界面、对话、任务卡、状态带、知识星图、资料托盘、社群、复盘。

B. 控制平面 / Control Plane
后台事件、信号、状态、Aurora 裁决、directive、审计、因果归因、技能沉淀。
```

这两个平面必须严格区分。

交互平面负责：

```text
让用户感觉 Sparkle 懂我、帮我、推我、记得我、会纠正自己。
```

控制平面负责：

```text
让系统真的知道为什么这么做、怎么做、有没有做成、做错后怎么改。
```

最终主链：

```text
Raw Event
→ Actionable Signal
→ State Patch
→ Actionable State Register
→ Policy Arbitration
→ Aurora Control Signal
→ Directives
→ Actuation
→ User-visible Receipt
→ Outcome
→ Causal Attribution
→ Model Update
→ Skill Extraction
```

这是 Sparkle 的操作系统总线。

---

# 2. 核心判断：不要做"大画像"，要做"可行动状态寄存器"

过去容易走偏的方向是：

```text
收集更多数据
→ 汇总成更完整用户画像
→ 塞进 prompt
→ 期待 LLM 自己变聪明
```

这个方向不够。

最终定稿改成：

```text
收集关键数据
→ 提取少量高价值 ActionableSignal
→ 更新可行动状态位
→ Aurora 进行策略仲裁
→ 输出结构化 directive
→ 下游模块必须执行并审计
```

也就是说，Sparkle 不追求"画像多完整"，而追求：

> **哪些状态足以改变下一步行动。**

不能改变行动的状态，不进核心状态寄存器。

---

# 3. 最终系统分层

## Layer 1：Raw Event Layer / 原始事件层

记录事实，不做判断。

来源包括：

```text
用户输入
AI 输出
任务开始
任务完成
任务放弃
任务超时
小测结果
错题
资料上传
资料使用
知识节点变化
成就解锁
计划修改
召回发送
召回打开
用户反馈
用户纠正
伙伴反馈
社群聚合信号
Aurora 校准
```

示例：

```json
{
  "event_id": "evt_001",
  "event_type": "task_completed",
  "user_id": "u_123",
  "goal_id": "goal_cn_exam_7d",
  "timestamp": "2026-04-26T20:12:00+08:00",
  "payload": {
    "task_id": "task_tcp_001",
    "expected_duration_min": 45,
    "actual_duration_min": 72,
    "quiz_accuracy": 0.5
  }
}
```

注意：Raw Event 只是事实。

它不能直接写成：

```text
用户执行力差
用户焦虑
任务太难
```

这些都是解释，必须进入下一层。

---

## Layer 2：Actionable Signal Layer / 可行动信号层

这一层把事件解释成"可能意味着什么"。

示例：

```json
{
  "signal_id": "sig_001",
  "source_event_ids": ["evt_001"],
  "source_system": "task_service",
  "claim": "用户完成了任务，但当前任务颗粒度可能偏大",
  "state_key": "task_granularity_fit",
  "confidence": 0.68,
  "scope": "current_sprint",
  "ttl": "72h",
  "evidence": [
    "任务预计 45 分钟，实际 72 分钟",
    "小测正确率 50%"
  ],
  "counter_evidence": [],
  "alternative_explanations": [
    "用户中途被打断",
    "题目比预估难",
    "资料解释不适合用户"
  ],
  "possible_effects": [
    "reduce_next_task_duration",
    "avoid_new_chapter",
    "use_worked_example"
  ],
  "priority": "high"
}
```

一个事件可以生成多个信号。

例如任务超时可能意味着：

```text
任务太大
知识点没掌握
用户真实时间不足
用户今天状态差
资料讲解不适合
计划估时模型错误
```

所以 ActionableSignal 必须有：

```text
claim
confidence
scope
ttl
evidence
counter_evidence
alternative_explanations
possible_effects
```

没有这些，就是伪智能。

---

## Layer 3：Signal Ranking & Conflict Layer / 信号排序与冲突层

所有信号不能全部进 Aurora。

必须排序。

排序维度：

| 维幕 | 含义 |
|------|------|
| goal_impact | 是否影响当前目标达成 |
| decision_relevance | 是否会改变本轮行动 |
| urgency | 是否受 deadline 压力影响 |
| confidence | 信号可信度 |
| freshness | 是否新鲜 |
| contradiction_level | 是否和已有状态冲突 |
| cost_of_inaction | 不处理的代价 |
| reversibility | 判断错了是否容易纠正 |
| user_visibility_need | 是否应该让用户知道 |
| privacy_sensitivity | 是否涉及隐私或外部反馈 |

冲突必须显式处理。

典型冲突：

```text
七连胜信号：用户执行稳定性提升，可以略微提高挑战
焦虑信号：用户压力升高，不宜提高难度
deadline 信号：考试快到了，必须推进
错因信号：同一节点重复错，不能推进新章节
用户偏好：不要太多提醒
系统判断：需要主动召回
```

第一版仲裁优先级定为：

```text
1. 安全 / 隐私 / 勿扰 / 用户硬边界
2. 高风险 deadline 生存策略
3. 用户显式目标与偏好
4. 直接行为证据
5. 学习结果与错因证据
6. 资料与知识星图证据
7. 成就 / 动机信号
8. 社群聚合信号
9. 视觉反馈与游戏化信号
```

重要原则：

> **成就信号永远不能压过焦虑、超时和错因信号。**

用户七连胜不等于可以盲目加难度。它只表示"当前冲刺下存在连续完成行为"，还要结合任务价值、小测结果、超时情况判断。

---

## Layer 4：Actionable State Register / 可行动状态寄存器

这是 Aurora 的核心输入之一。

它不是完整用户画像，而是类似操作系统寄存器，只保存会影响控制决策的状态位。

第一版必须定义以下状态词汇表。

### 4.1 核心状态 ontology

| 状态键 | 含义 | 可能影响 |
|--------|------|----------|
| `goal_mode` | 当前目标模式，例如 exam_rescue / deep_mastery / project_delivery | 计划策略、任务类型 |
| `deadline_pressure` | 时间压力 | 任务粒度、召回强度 |
| `execution_consistency` | 执行稳定性 | 任务挑战度、催促方式 |
| `task_granularity_fit` | 任务大小是否适配 | 下一张任务卡时长 |
| `cognitive_load` | 认知负荷 | 解释长度、是否推进新内容 |
| `affective_pressure` | 情绪压力 | 语气、提醒、难度 |
| `knowledge_bottleneck` | 当前主知识瓶颈 | 任务主题、资料调用 |
| `transfer_failure` | 是否从概念迁移到题型失败 | worked example / drill |
| `source_relevance` | 资料是否适合当前问题 | RAG 策略 |
| `retrieval_risk` | 检索资料是否可能污染上下文 | 是否加载资料 |
| `model_conflict` | 系统内部模型是否冲突 | 是否唤醒 Aurora |
| `strategy_confidence` | 当前策略信心 | 是否继续执行或重规划 |
| `intervention_effectiveness` | 上次干预是否有效 | 策略学习 |
| `relationship_stance` | Sparkle 与用户当前关系姿态 | 语气、解释深度 |
| `user_agency_preference` | 用户希望被安排还是自主选择 | UI 与任务推荐方式 |

每个状态必须有：

```json
{
  "state_key": "task_granularity_fit",
  "value": "too_large",
  "confidence": 0.72,
  "scope": "current_sprint",
  "ttl": "72h",
  "supporting_evidence": [],
  "counter_evidence": [],
  "last_updated_at": "",
  "can_affect": [
    "ExecutionDirective",
    "PlanDirective",
    "ResponseDirective"
  ],
  "user_visible": true,
  "requires_confirmation_if_high_impact": true
}
```

### 4.2 作用域纪律

这是铁律。

同一个观察在不同作用域下意义完全不同。

```text
turn：本轮
session：当前会话
task：当前任务
day：今天
sprint：当前 7 天冲刺
goal：当前目标
subject：当前学科
relationship：用户与 Sparkle 的关系
long_term：长期模型
```

例如：

```text
用户连续 7 天完成计网任务
```

不能写成：

```text
用户长期执行力强
```

只能写成：

```text
在当前计网 7 天冲刺下，用户近期任务完成稳定性上升。
```

否则长期画像会被污染。

---

## Layer 5：Policy Arbitration Layer / 策略仲裁层

这是最终定稿里最关键的新层。

Aurora 不应该直接从状态生成回复。

中间必须经过 Policy Arbitration。

输入：

```text
Actionable State Register
GoalModel
TimeContext
KnowledgeState
TaskState
SourceState
UserPreferences
Hard Boundaries
RelationshipState
SparkleSelfModel
CommunitySignals
Recent Outcome
```

输出：

```text
本轮主策略
副策略
硬约束
软倾向
需要哪些 directive
是否需要用户确认
是否需要 Aurora 显性介入
是否需要写入模型
是否需要用户可见回执
```

示例：

```json
{
  "policy_decision_id": "pd_001",
  "primary_strategy": "recover_execution_rhythm",
  "secondary_strategy": "repair_tcp_congestion_bottleneck",
  "reasoning_summary": "用户连续两张任务超时，且 TCP 窗口题重复错误；当前优先恢复可完成节奏，而不是推进新章节。",
  "hard_constraints": {
    "max_task_duration_min": 25,
    "avoid_new_chapter": true
  },
  "soft_biases": {
    "prefer_task_type": "worked_example_then_drill",
    "tone": "direct_but_reassuring"
  },
  "requires_user_confirmation": true,
  "visibility": "receipt",
  "risk_level": "medium"
}
```

这层决定 Sparkle 是否像成熟教练，而不是一个热情但混乱的 AI。

---

## Layer 6：Directive Layer / 指令层

Aurora 不直接控制所有模块。

Aurora 输出一个总控 envelope：

```json
{
  "aurora_control_signal": {
    "control_id": "acs_001",
    "energy": "light",
    "policy_decision_id": "pd_001",
    "response_policy": "task_recovery_support",
    "directives": {
      "response": "rdsp_001",
      "execution": "ed_001",
      "retrieval": "rtd_001",
      "plan": "pld_001",
      "model_write": "mwd_001",
      "notification": "nd_001",
      "ux": "uxd_001",
      "skill": "skd_001"
    }
  }
}
```

必须拆成多个 directive，不能全塞进一个 prompt。

### 6.1 ExecutionDirective

控制任务卡和执行系统。

```json
{
  "directive_id": "ed_001",
  "scope": "today",
  "hard_constraints": {
    "max_task_duration_min": 25,
    "avoid_new_chapter": true,
    "required_task_type": "worked_example_then_drill"
  },
  "soft_biases": {
    "difficulty": "medium_low",
    "success_probability_min": 0.7
  },
  "user_visible_reason": "最近两张长任务都明显超时，我会先把今晚任务压小，帮助你回到可完成节奏。"
}
```

### 6.2 RetrievalDirective / ContextPlan

控制资料、RAG、知识星图、社群信号如何进入上下文。

```json
{
  "directive_id": "rtd_001",
  "retrieval_mode": "task_bound_graph_rag",
  "source_scope": "task_bound",
  "must_load": [
    "current_task_card",
    "knowledge_node:cn.tcp.congestion_control",
    "mistake_cluster:tcp_window_transition",
    "source_slice:transport_layer_slides_p32_p45"
  ],
  "may_load": [
    "past_exam_2023_q4"
  ],
  "do_not_load": [
    "full_course_slides",
    "unrelated_chat_history",
    "raw_long_term_profile"
  ],
  "token_budget": 3600,
  "citation_required": true,
  "pollution_guard": "strict",
  "user_visible_receipt": true,
  "reason_for_user": "我只取当前任务相关资料，避免完整课件污染解释。"
}
```

### 6.3 ResponseDirective

控制标准交互层如何表达。

```json
{
  "directive_id": "rdsp_001",
  "tone": "calm_direct",
  "length": "medium",
  "must_acknowledge": [
    "recent_overrun",
    "current_goal"
  ],
  "avoid": [
    "generic_encouragement",
    "pressure_language"
  ],
  "include_user_options": true
}
```

### 6.4 PlanDirective

控制计划和重规划。

```json
{
  "directive_id": "pld_001",
  "plan_action": "local_replan",
  "scope": "next_48h",
  "constraints": {
    "do_not_rebuild_entire_plan": true,
    "preserve_deadline_strategy": true,
    "insert_recovery_task": true
  }
}
```

### 6.5 NotificationDirective

控制提醒和主动召回。

```json
{
  "directive_id": "nd_001",
  "allowed": true,
  "channel": "push",
  "respect_quiet_hours": true,
  "trigger": "first_task_not_started",
  "message_strategy": "low_effort_next_step",
  "max_frequency": "1_per_day"
}
```

### 6.6 ModelWriteDirective

控制写入哪个模型、写入多深。

```json
{
  "directive_id": "mwd_001",
  "writes": [
    {
      "target_model": "user_state",
      "claim": "当前冲刺下任务颗粒度可能偏大",
      "scope": "current_sprint",
      "confidence": 0.72,
      "needs_user_confirmation": false,
      "ttl": "72h"
    },
    {
      "target_model": "sparkle_self_model",
      "claim": "最近生成的长任务对该用户可能不适配",
      "scope": "strategy",
      "confidence": 0.66,
      "needs_user_confirmation": false
    }
  ]
}
```

### 6.7 UXDirective

控制状态带、回执、预测选项、Aurora 是否显性出现。

```json
{
  "directive_id": "uxd_001",
  "status_band_state": "risk_detected",
  "show_context_receipt": true,
  "show_strategy_receipt": true,
  "predicted_reply_options": [
    "确实排大了",
    "只是今天临时忙",
    "不是任务大，是我不会做",
    "都不对，我解释一下"
  ],
  "allow_full_aurora_wake": true
}
```

---

## Layer 7：Actuation & Audit Layer / 执行与审计层

这是从"建议"变成"控制"的关键。

每个下游模块执行后必须返回：

```text
我是否应用了 directive？
应用了哪些？
没应用哪些？
为什么没应用？
最终输出是否符合约束？
```

示例：

```json
{
  "audit_id": "audit_001",
  "directive_id": "ed_001",
  "target_module": "task_generator",
  "applied": true,
  "applied_constraints": [
    "max_task_duration_min",
    "avoid_new_chapter",
    "required_task_type"
  ],
  "overridden_constraints": [],
  "generated_output_id": "task_tcp_recovery_001",
  "generated_output_summary": {
    "duration_min": 23,
    "topic": "tcp_congestion_control",
    "task_type": "worked_example_then_drill",
    "new_chapter": false
  }
}
```

如果任务生成超过 25 分钟，就是 fail。

这不是风格偏好，而是验收标准。

---

## Layer 8：Outcome & Causal Attribution Layer / 结果与因果归因层

系统必须知道自己的干预有没有用。

第一版不用复杂因果推断，但必须做最小因果记录。

```json
{
  "causal_trace_id": "ct_001",
  "intervention": "max_task_duration_25min",
  "reason": "recent_task_overrun",
  "expected_outcome": "task_started_and_completed",
  "actual_outcome": {
    "started": true,
    "completed": false,
    "time_spent_min": 12,
    "user_feedback": "还是看不懂"
  },
  "attribution": {
    "intervention_effect": "insufficient",
    "new_hypothesis": "knowledge_explanation_failure",
    "confidence": 0.61
  },
  "next_policy_suggestion": "switch_to_worked_example_before_drill"
}
```

注意表达上不能过度自信。

系统内部可以说：

```text
缩短任务后完成率可能未改善，问题可能不是时间，而是理解方式。
```

不能说：

```text
已证明缩短任务无效。
```

---

# 4. Aurora 的最终定义

## 4.1 Aurora 不是聊天人格，而是 Sparkle 的认知内核

Aurora 的职责：

```text
感知状态
管理时间
裁决冲突
控制上下文
决定是否用资料
决定是否主动介入
决定如何表达
决定是否写入模型
决定是否重规划
决定是否生成任务
决定是否唤醒完整 Aurora Core
```

用户看到的是 Aurora 的一部分体验，但 Aurora 的本质是控制系统。

---

## 4.2 Aurora 自己也有状态

这是你强调得非常对的一点。

Sparkle 有很多模型：

```text
UserModel
GoalModel
KnowledgeModel
TaskModel
SourceModel
SituationModel
CommunityModel
RelationshipModel
SparkleSelfModel
```

但 Aurora 不能只是这些模型的汇总器。

Aurora 自己必须维护一套简短、独立、可操作的状态寄存器：

```text
当前我对用户最重要的判断是什么？
哪些判断置信度不够？
哪些判断和行为证据冲突？
我上次做了什么策略调整？
那个调整有没有用？
我现在是否应该继续当前策略？
我是否需要主动找用户确认？
我和用户当前的关系姿态是什么？
我是否刚刚误判过用户？
```

示例：

```json
{
  "aurora_state": {
    "current_primary_hypothesis": "用户当前卡点不是概念没见过，而是题型迁移失败",
    "confidence": 0.74,
    "open_questions": [
      "今晚真实可用时间是否只有 45 分钟",
      "用户是否仍以先过线为目标"
    ],
    "recent_self_correction": {
      "claim": "之前任务粒度可能排大",
      "confidence": 0.68
    },
    "relationship_stance": "direct_but_careful",
    "next_best_confirmation": "确认任务颗粒度是否排大"
  }
}
```

这就是 Aurora 看起来像"真的在思考"的基础。

不是因为 prompt 写"你像朋友"，而是它有：

```text
状态
记忆
假设
反证
开放问题
自我修正
未来预测
```

---

# 5. Aurora 能级调度：L0 / L1 / L2 / L3 / L4

最终定稿：**完整 Aurora 不能常驻。**

完整 Aurora Core 是高成本、稀缺、限时的主动交互式建模会话。

但 Sparkle 必须一直有低成本感知和异步后台更新。

## L0：Rule Sensor / 规则与统计感知

不调用大模型。

每次事件发生都可以运行。

负责：

```text
记录任务完成
记录耗时
记录小测
更新时间
检查 deadline
检查 quiet hours
检查任务是否过期
检查状态是否 stale
检查是否触发 wake
```

输出：

```text
RawEvent
TimeContext
basic signals
```

体验：

```text
用户无感。
```

---

## L1：Light Aurora / 轻量 Aurora

每轮标准交互前运行。

可以是小模型、规则 + 小模型、缓存状态结合。

负责：

```text
判断本轮意图
判断是否需要资料
选择上下文模式
生成基本 AuroraControlSignal
判断是否需要状态带回执
判断是否要升级到 L2 / L3
```

体验：

```text
Aurora · 已按当前任务校准
Aurora · 本轮未调用课件
Aurora · 已参考最近错因
```

---

## L2：Mid Aurora / 中等 Aurora

非每轮运行。

触发条件：

```text
任务失败
任务超时
同类错因重复
用户说"你没懂我"
资料策略可能失效
计划偏离
目标行为冲突
状态冲突
deadline 高压
召回失败
```

负责：

```text
局部策略仲裁
局部重规划
生成更强 directive
生成用户确认卡
判断是否需要 L3
```

体验：

```text
Aurora · 发现一个策略风险

我目前认为：今晚任务可能排大了。
依据：最近两张任务都明显超时。
[缩小今晚任务] [不是这个问题] [进入深度校准]
```

---

## L3：Full Aurora Core / 完全态 Aurora

高成本、限时、稀缺。

不常驻。

进入条件：

```text
系统发现关键模型冲突
用户连续否定系统判断
策略连续失效
目标发生变化
deadline 高风险
用户主动唤醒
标准层无法处理
SparkleSelfModel 置信度下降
```

它负责：

```text
主动交互式建模
解释当前假设
展示证据与冲突
提出关键问题
接收用户纠正
更新状态寄存器
输出新的策略与 directive
退回后台
```

体验不是普通聊天，而是一次"认知校准事件"。

示例：

```text
Aurora：
等一下，我需要重新校准一下。

我发现一个冲突：
你一开始说每天可以学 2 小时，
但最近两张任务卡都明显超时。

我现在怀疑：
不是你不努力，而是我之前高估了你当前能承受的任务颗粒度。

我先确认一个关键点：
今晚真实可用时间更接近哪一个？

[30 分钟] [45 分钟] [60 分钟] [都不对，我解释一下]
```

完成后：

```text
这次校准完成。
我更新了三件事：
1. 今晚任务不超过 45 分钟；
2. 后续两天优先小任务；
3. TCP 先用 worked example，不直接刷题。

Aurora 先退回后台。
```

---

## L4：Async Deep Learning / 异步深度学习层

这是后台系统，不阻塞用户对话。

负责：

```text
跨天行为分析
成就回流
召回效果评估
资料有效性评估
策略效果评估
错因聚类
知识星图更新
社群聚合洞察
Skill Extraction
长期模型候选写入
```

它可以跑 Celery / batch / stream consumer。

用户体验：

```text
第二天回来时，Sparkle 已经更新了对他的理解。
```

而不是每次回答前都长时间思考。

---

# 6. 时间感知机制：Time-Aware Sparkle

这是必须 P0 做的能力。

用户离开 1 小时、2 小时、1 天再回来，系统状态不能停留在上一轮。

## 6.1 时间是第一等上下文

新增 TimeContext：

```json
{
  "now": "2026-04-26T21:30:00+08:00",
  "timezone": "Asia/Singapore",
  "goal_deadline": "2026-05-03T09:00:00+08:00",
  "time_to_deadline_hours": 155.5,
  "last_user_interaction_at": "2026-04-26T19:20:00+08:00",
  "elapsed_since_last_interaction_min": 130,
  "active_task": {
    "task_id": "task_tcp_001",
    "expected_end_at": "2026-04-26T20:05:00+08:00",
    "status": "started_but_no_completion"
  },
  "quiet_hours": {
    "active": false
  },
  "deadline_phase": "normal_sprint"
}
```

## 6.2 Stale State Guard

每轮用户返回时，先检查：

```text
上次任务是否应该结束？
用户是否完成？
deadline 是否更近？
提醒是否发送过？
资料解析是否完成？
后台分析是否产生新状态？
```

输出 TimeDeltaPacket：

```json
{
  "elapsed_since_last_seen_min": 130,
  "pending_task_status": "expected_finished_but_no_feedback",
  "new_background_updates": [
    "source_parsing_completed",
    "knowledge_nodes_mapped"
  ],
  "deadline_phase_changed": false,
  "recommended_resume_strategy": "ask_task_status_then_recover"
}
```

## 6.3 返回体验

用户回来后，不应该直接继续上一句话。

应该这样：

```text
你离开了大约 2 小时。
上一张 TCP 任务卡原本预计 45 分钟结束，但我还没有收到完成反馈。

先不用重新开始。
你现在是哪种情况？

[做完了，补记录]
[做了一半，卡住了]
[没开始]
[换个小任务]
```

这就是时间感知。

## 6.4 deadline phase

Exam Sprint 中必须有时间阶段：

```text
D-7 to D-5：建立最小通过路径
D-4 to D-3：主瓶颈训练
D-2：高频题型和错因修复
D-1：考前生存策略
D-0：只做高收益复盘，不开新坑
```

Aurora 的策略必须随着时间自动变化。

例如 D-1：

```text
avoid_new_chapter = true
prefer_high_yield_review = true
task_duration_cap = 25
retrieval_mode = graph_summary_or_exam_pack
```

---

# 7. 主动式建模：Proactive Modeling

主动不是骚扰。

主动是：

> 当系统发现自己的模型不够可靠，且这个不可靠会影响用户目标时，主动找用户确认。

## 7.1 触发条件

Aurora 主动找用户的条件：

```text
关键状态置信度低，但影响高
用户行为和自述冲突
连续任务失败
连续错因重复
资料策略失效
deadline 进入高风险阶段
用户长期未回来
成就信号和质量信号冲突
外部伙伴信号需要确认
系统自我模型发现策略失效
```

## 7.2 主动介入层级

不要一上来全屏。

分三档：

```text
1. 状态带轻提醒
2. 交互卡片确认
3. Full Aurora Core Session
```

示例：

```text
Aurora · 需要确认一个判断

我现在怀疑今晚任务排大了。
依据：最近两张任务都明显超时。

这个判断对吗？

[确实排大了]
[只是今天临时忙]
[不是任务大，是我不会做]
[都不对，我解释一下]
```

每组预测选项必须包含：

```text
都不对，我解释一下
```

这是用户主权。

---

# 8. 预测回答选项：PredictedReplyOption Engine

预测选项不是模式选择器。

它是 Aurora 建模问题里的语义快捷回答。

对象：

```json
{
  "question_id": "task_granularity_confirmation",
  "options": [
    {
      "label": "确实排大了",
      "semantic_value": "task_too_large",
      "confidence": 0.42,
      "effect": {
        "state_patch": {
          "task_granularity_fit": "too_large"
        }
      },
      "whether_disconfirming": false,
      "whether_freeform": false,
      "telemetry_id": "opt_001"
    },
    {
      "label": "只是今天临时忙",
      "semantic_value": "temporary_time_conflict",
      "confidence": 0.26,
      "effect": {
        "state_patch": {
          "task_granularity_fit": "unknown",
          "situation_constraint": "temporary_busy"
        }
      },
      "whether_disconfirming": true,
      "whether_freeform": false,
      "telemetry_id": "opt_002"
    },
    {
      "label": "不是任务大，是我不会做",
      "semantic_value": "knowledge_blocker",
      "confidence": 0.22,
      "effect": {
        "state_patch": {
          "knowledge_bottleneck": "stronger"
        }
      },
      "whether_disconfirming": true,
      "whether_freeform": false,
      "telemetry_id": "opt_003"
    },
    {
      "label": "都不对，我解释一下",
      "semantic_value": "freeform_correction",
      "confidence": 0.10,
      "effect": {
        "open_free_input": true
      },
      "whether_disconfirming": true,
      "whether_freeform": true,
      "telemetry_id": "opt_004"
    }
  ]
}
```

四类预测选项：

```text
事实确认类：今晚能学多久？
假设确认类：是不是任务排大了？
策略选择类：接下来缩小任务还是换讲法？
关系边界类：刚才语气是否太直接？
```

这会让 Aurora 像朋友一样自然地确认，而不是像表单。

---

# 9. 多消息 Aurora 会话：不是"一问一答"

你提到的一个极关键点是：

> Aurora 多条消息不是因为被命令发多条，而是因为它真的有多个需要表达和确认的点。

最终设计：

Aurora Core Session 不是普通 chat completion。

它需要：

```text
AuroraAgenda
AuroraMessageQueue
PendingQuestion
InterruptionPolicy
ResumePolicy
SessionClosure
```

## 9.1 AuroraAgenda

```json
{
  "session_id": "aurora_core_001",
  "scope": "校准今晚任务颗粒度与后续两天策略",
  "agenda_items": [
    {
      "id": "a1",
      "type": "explain_conflict",
      "status": "done"
    },
    {
      "id": "a2",
      "type": "confirm_available_time",
      "status": "waiting_user"
    },
    {
      "id": "a3",
      "type": "update_strategy",
      "status": "pending"
    }
  ]
}
```

## 9.2 用户打断时怎么处理

用户突然问：

```text
等等，TCP 三次握手到底是什么？
```

Aurora 不应该生硬说：

```text
请先回答我的问题。
```

应该：

```text
可以，先回答这个。
三次握手的核心是确认双方收发能力。

不过这个问题也说明一件事：
你现在可能不只是卡在任务颗粒度，也有一些传输层基础概念不稳。

我先用 30 秒讲清楚，然后再回到刚才那个任务安排问题。
```

然后 Agenda 暂停，回答完再恢复。

这就是朋友感。

---

# 10. 自适应 Context / Harness Engineering

这是 Sparkle 的核心护城河之一。

## 10.1 术语定稿

最终使用：

```text
Aurora Adaptive Context / Harness Engineering
```

含义：

> Aurora 在系统边界内，动态决定本轮该加载什么上下文、调用什么资料、使用哪些工具、怎么设置 prompt 参数、是否检索、是否写入模型、是否召回、是否显性校准。

它不是让 Aurora 任意修改系统。

而是：

```text
硬边界内的自主调度。
```

## 10.2 Harness 边界

Aurora 不能突破：

```text
用户隐私设置
勿扰时间
安全规则
用户明确排除的资料
权限边界
成本上限
数据保留政策
长期模型写入规则
社群匿名规则
不可逆操作确认规则
```

例如：

```json
{
  "hard_bounds": {
    "quiet_hours_no_push": true,
    "do_not_use_excluded_sources": true,
    "no_long_term_write_without_threshold": true,
    "no_partner_signal_write_without_user_confirmation": true,
    "max_context_tokens": 8000,
    "max_full_aurora_sessions_per_day": 2
  }
}
```

在边界内，Aurora 可以自由调参：

```text
RAG 开不开
用哪个资料
任务多长
语气多直接
是否追问
是否召回
是否显性解释
是否生成小测
是否局部重规划
```

这就是"给 Aurora 空间，但不失控"。

---

# 11. 资料与知识星图闭环

Sparkle 不能做普通文件夹 + RAG。

最终目标：

```text
资料 → SourceSlice → KnowledgeNode → TaskCard → Mistake → ModelUpdate → NextContextPlan
```

## 11.1 为什么 Sparkle 要比 Projects / NotebookLM 更进一步

ChatGPT Projects 官方定位是把长期工作相关的聊天、文件和自定义指令组织在一个智能工作区里；Claude Projects 官方文档也强调自包含工作区、聊天历史和知识库；NotebookLM 官方定位是围绕用户上传来源进行总结、连接和 source-grounded 问答。

Sparkle 的差异不是"也能上传资料"。

Sparkle 的差异是：

```text
资料不是上下文。
资料是目标推进闭环的一部分。
```

NotebookLM 强在 source-grounded answer。

Sparkle 要强在：

```text
source-grounded action
source-grounded task
source-grounded mistake repair
source-grounded planning
source-grounded causal learning
```

---

## 11.2 SourceAsset

```json
{
  "source_id": "src_001",
  "title": "计算机网络第 3 章：传输层",
  "type": "slides",
  "course": "computer_networks",
  "goal_id": "goal_cn_exam_7d",
  "owner": "user",
  "visibility": "private",
  "parsed_status": "parsed",
  "quality_score": 0.78,
  "mapped_nodes": [
    "cn.tcp",
    "cn.udp",
    "cn.congestion_control"
  ],
  "recommended_uses": [
    "concept_explanation",
    "task_material",
    "quiz_generation",
    "mistake_explanation"
  ],
  "not_recommended_uses": [
    "full_exam_scope_confirmation"
  ]
}
```

## 11.3 SourceSlice

```json
{
  "slice_id": "slice_001",
  "source_id": "src_001",
  "location": "p32-p45",
  "summary": "TCP 拥塞控制：慢启动、拥塞避免、ssthresh、cwnd 变化",
  "concepts": [
    "slow_start",
    "congestion_avoidance",
    "cwnd",
    "ssthresh"
  ],
  "knowledge_nodes": [
    "cn.tcp.congestion_control"
  ],
  "evidence_type": "definition_and_example",
  "noise_risk": "low"
}
```

## 11.4 KnowledgeNode

```json
{
  "node_id": "cn.tcp.congestion_control",
  "label": "TCP 拥塞控制",
  "mastery": 0.38,
  "exam_weight": 0.82,
  "trainability": 0.72,
  "source_coverage": [
    "slice_001"
  ],
  "mistake_clusters": [
    "窗口变量混淆",
    "慢启动和拥塞避免切换错误"
  ],
  "recommended_action": "worked_example_then_drill"
}
```

---

# 12. ContextPlan：RAG 不是开关

不要做：

```text
RAG 开 / 关
```

要做多级模式：

| 模式 | 用途 |
|------|------|
| `no_retrieval` | 通用解释，不用资料 |
| `graph_only` | 只用知识星图摘要 |
| `task_bound_rag` | 只用当前任务卡绑定资料 |
| `targeted_source_rag` | 检索少量相关资料片段 |
| `user_pinned_sources` | 用户指定资料必须参与 |
| `deep_source_synthesis` | 多资料综合，用于规划/复盘 |
| `community_aggregate_context` | 使用匿名社群聚合信号 |
| `aurora_core_case_file` | Full Aurora 使用压缩 case file |

## 12.1 什么时候必须用资料

```text
用户明确要求"按课件讲"
用户问老师 PPT 怎么说
用户要求根据上传资料
当前任务卡绑定资料
需要考试范围 grounding
需要引用证据
用户质疑"你是不是没看我的文件"
```

## 12.2 什么时候不该用资料

```text
用户问通用概念
资料质量低
资料和当前问题弱相关
用户认知负荷高
考前 24h 不适合展开原文
上下文预算紧张
知识星图摘要已经足够
用户明确排除资料
```

关键体验：

```text
本轮未调用课件。
原因：你问的是通用概念，我先用更短方式建立框架。
[按第 3 章课件重讲]
```

这会让用户感到：

> Sparkle 不是忘了资料，而是在管理资料。

---

# 13. Source Tray 与 Context Receipt

## 13.1 Source Tray

对话页提供资料托盘：

```text
资料策略：Aurora 自动选择

可参与资料：
☑ 第 3 章传输层课件        高相关
☐ 往年题 2023              中相关
☐ Week 7 作业              中相关
☐ 全部课件                 不建议：范围太大
☑ 我的最近错题              建议开启
```

模式：

```text
[自动] [只用我选的资料] [不要用资料]
```

默认是自动。

用户选择资料时必须有作用域：

```text
只用于本次回答
用于当前任务卡
用于今天
固定到当前目标
```

避免永久污染。

## 13.2 Context Receipt

每次资料相关回答后显示：

```text
基于：
当前目标 · 7 天计网先过
当前任务 · TCP 拥塞控制专项
资料 · 第 3 章课件 p32-p45
错因 · 窗口变化混淆
策略 · worked example 优先

未使用：
完整传输层课件，因为范围太大，会污染解释。
```

按钮：

```text
[按课件重讲]
[改用往年题]
[不要用这份资料]
[查看证据]
```

这就是用户可感知的 Context Engineering。

---

# 14. 任务卡：策略执行协议

任务卡不是 todo。

任务卡必须包含：

```text
为什么做
做什么
做到什么程度
使用哪些资料
为什么用这些资料
步骤
卡住怎么办
验收方式
完成后更新什么状态
失败后怎么恢复
```

示例：

```text
任务：25 分钟修复 TCP 拥塞控制窗口题

为什么做：
这是你当前最高收益薄弱点，最近 3 次相关题都错在窗口变化。

材料：
- 第 3 章课件 p32-p45：规则回顾
- 往年题 2023 第 4 题：worked example
- 最近错因：cwnd / ssthresh 混淆

步骤：
1. 5 分钟看压缩规则；
2. 8 分钟跟做 worked example；
3. 8 分钟做 2 道变式；
4. 4 分钟小测和错因标记。

卡住时：
不要重看完整课件。
点"我卡住了"，Sparkle 只调取当前题和相关规则。

完成后更新：
- TCP 拥塞控制掌握度
- 窗口变化错因状态
- 后续任务颗粒度判断
- 当前资料有效性
```

---

# 15. Aurora 状态带：系统存在感入口

Aurora 状态带不是装饰。

它是用户理解系统后台工作的统一入口。

最终状态：

| 状态 | 展示 |
|------|------|
| 轻量感知中 | Aurora · 正在按当前任务校准 |
| 已校准 | Aurora · 已对齐今日任务 |
| 发现风险 | Aurora · 发现策略风险 |
| 需要确认 | Aurora · 需要确认一个判断 |
| 资料感知 | Aurora · 已参考当前任务资料 |
| 未用资料 | Aurora · 本轮未调用课件 |
| 深度可用 | Aurora · 深度校准可用 |
| 冷却中 | Aurora · 深度校准冷却中 |

示例展开：

```text
本轮上下文

我参考了：
- 当前任务卡：TCP 拥塞控制专项
- 第 3 章课件：拥塞控制部分
- 最近错因：窗口变化判断错误

我没有参考：
- 全部课件，因为范围太大
- 往年题，因为这轮先修概念迁移，不做完整真题

[改用往年题讲] [不要用课件] [查看证据]
```

这会让用户感觉 Sparkle 在"认真管理他的世界"，而不是普通 AI 在回复。

---

# 16. 成就系统：从奖励变成成长信号

成就不是 GrowthSignal 本身。

成就是 GrowthSignal 的来源之一。

流程：

```text
Achievement Event
→ Reinforcement Signal
→ Growth State Patch
→ Policy Change
→ User-visible Recognition
→ Outcome Audit
```

七连胜不能直接写成：

```text
用户执行力强
```

只能写成：

```text
用户在当前冲刺目标下表现出连续完成行为。
需要结合任务价值、小测结果、耗时和主观压力判断是否是真实执行稳定性。
```

用户体验：

```text
你连续 7 天完成了任务。
我不会只把它当成徽章。

我会先理解成：
你已经建立起一段可持续的执行节奏。

但我也会同时看小测和错因，确认这不是只完成了低难任务。

接下来我会先做两个调整：
1. 少用启动式催促；
2. 今天给你一个略有挑战、但仍可完成的任务。

如果你其实已经很累，可以直接告诉我。
```

这才是成熟教练感。

---

# 17. 主动召回：Goal-Respectful Recall

召回不是增长骚扰。

召回必须基于：

```text
用户目标中的下一步价值
```

三类召回：

| 类型 | 目的 | 示例 |
|------|------|------|
| Activation Recall | 启动第一步 | 上传资料后未诊断 |
| Recovery Recall | 从失败恢复 | 任务错过后重排 |
| Deadline Recall | 高风险节点 | 考前 48h 沉默 |

示例：

```text
我已经把你的计网课件挂到知识星图上了。
现在只需要 12 分钟诊断，就能判断 7 天内先救哪三块。
今天不用完整学习，先做这个就够。
```

召回必须记录 outcome：

```json
{
  "recall_id": "recall_001",
  "trigger": "uploaded_sources_but_no_diagnostic_after_24h",
  "message_strategy": "low_effort_next_step",
  "opened": true,
  "acted": false,
  "next_state_update": "opened_but_no_action"
}
```

---

# 18. 社群系统：共调节，不是聊天广场

社群是 Sparkle 的社会层。

它有三种作用：

## 18.1 Commitment Loop / 责任伙伴闭环

用户承诺：

```text
今晚 25 分钟完成 TCP 拥塞控制专项。
```

伙伴看到：

```text
小林今晚承诺：
完成 TCP 拥塞控制专项任务
预计 25 分钟
完成标准：2 道变式题至少做对 1 道
```

伙伴可以：

```text
提醒
见证
反馈外部观察
```

但伙伴信号不能直接写长期模型。

必须：

```text
external_observation_candidate
needs_user_confirmation = true
```

## 18.2 Cohort Mistake Loop / 共性错因闭环

匿名聚合：

```text
同目标用户在 TCP 窗口变化中常错：
- cwnd / ssthresh 混淆
- 超时后的阈值更新
- 三次重复 ACK 后变化
```

影响：

```text
任务卡模板
小测题型
知识节点难度
Aurora 策略
Sprint Pack 优化
```

## 18.3 Resource Quality Loop / 共享资料质量闭环

共享资料进入 Community Resource Pool。

必须经过：

```text
权限
质量评分
适用课程 / 老师 / 年份
知识节点挂载
使用效果反馈
```

用户接受后才进入个人 Source Library。

不能自动污染个人上下文。

---

# 19. 混合时间轴：从 history 升级为 Causal Audit Timeline

混合时间轴不是流水账。

它记录因果链：

```text
事件
信号
状态变化
Aurora 裁决
Directive
输出改变
用户是否感知
结果
下一次模型更新
```

示例：

```json
{
  "event_type": "causal_trace",
  "time": "Day2 20:14",
  "raw_event": "task_timeout:tcp_task_001",
  "actionable_signal": "task_granularity_may_be_too_large",
  "state_patch": "task_granularity_fit=too_large",
  "policy_decision": "recover_execution_rhythm",
  "execution_directive": {
    "max_task_duration_min": 25,
    "avoid_new_chapter": true
  },
  "generated_task": "tcp_recovery_25min",
  "user_visible_receipt": "我把今晚任务压到 25 分钟",
  "outcome_to_measure": [
    "task_started",
    "task_completed",
    "quiz_accuracy",
    "user_feedback"
  ]
}
```

这让系统能回答：

```text
为什么今天任务变短？
为什么没有加载完整课件？
为什么不推进新章节？
为什么 Aurora 说之前可能排大了？
```

这就是可信。

---

# 20. SparkleSelfModel：系统必须建模自己

这是高阶但必须进入 P1。

Sparkle 不只建模用户，也要建模自己：

```text
我给这个用户的任务是不是经常排大？
我调用课件是否真的帮助他理解？
我是不是太常用鼓励话术？
我是不是过早推进新章节？
我的召回是否有效？
我的预测选项是否让用户纠正了我？
```

对象：

```json
{
  "self_model_claim": {
    "claim": "最近长任务策略对该用户不适配",
    "confidence": 0.67,
    "scope": "current_sprint",
    "evidence": [
      "2 次长任务超时",
      "用户反馈任务做不完"
    ],
    "counter_evidence": [],
    "policy_effect": [
      "cap_task_duration",
      "prefer_recovery_task"
    ]
  }
}
```

这会让 Sparkle 越用越好。

---

# 21. Skill Extraction：持续学习与 Learning Base

你提出的 skill 思路非常关键。

Sparkle 不应该每次都从零规划。

当一个策略被证明有效时，系统应该提取成 skill。

## 21.1 什么情况下提取 skill

不是每次都提取。

触发条件：

```text
某套任务策略连续成功
用户反馈明显正向
小测提升明显
任务完成率提升
某资料使用方式特别有效
某类用户/目标/阶段重复适用
Aurora 自我模型确认策略有效
```

## 21.2 Skill 类型

### Personal Skill

只给这个用户用。

例如：

```text
这个用户在计网冲刺中，对"worked example → 2 道变式 → 4 分钟错因回顾"反应很好。
```

### Cohort Skill

给同课程 / 同目标用户使用。

例如：

```text
7 天计网先过用户，TCP 拥塞控制适合先做窗口变化 worked example，而不是先读完整课件。
```

### System Skill / Learning Base

平台级策略资产。

例如：

```text
Exam Rescue Sprint：重复错因 + deadline 高压时，优先恢复可完成节奏，再修最高收益瓶颈。
```

## 21.3 Skill 对象

```json
{
  "skill_id": "skill_exam_tcp_worked_example_repair",
  "scope": "cohort",
  "applicable_when": {
    "goal_mode": "exam_rescue",
    "knowledge_bottleneck": "tcp_congestion_control",
    "transfer_failure": true,
    "deadline_pressure": "medium_high"
  },
  "strategy": {
    "task_type": "worked_example_then_drill",
    "duration_min": 25,
    "source_mode": "task_bound_rag",
    "avoid": [
      "full_chapter_review"
    ]
  },
  "evidence": {
    "completion_rate_delta": 0.18,
    "quiz_accuracy_delta": 0.22,
    "sample_size": 38
  },
  "privacy": {
    "contains_personal_data": false,
    "shareable": true
  }
}
```

Skill 不是 prompt。

Skill 是策略资产。

---

# 22. 执行度：Decision Realization Score

最终指标必须从"AI 说得好不好"升级为：

> **AI 判断是否真正改变了系统行动，并改善了结果。**

核心指标：

| 指标 | 含义 |
|------|------|
| Signal-to-State Rate | 高价值信号有多少进入状态 |
| State-to-Policy Rate | 状态变化有多少触发策略裁决 |
| Policy-to-Directive Rate | 策略有多少变成 directive |
| Directive Application Rate | directive 有多少被下游执行 |
| Output Change Rate | 输出是否真的改变 |
| User-visible Receipt Rate | 用户是否感知到改变 |
| Outcome Feedback Rate | 改变后是否记录结果 |
| Intervention Effectiveness | 干预是否可能有效 |
| Retraction Rate | 系统是否能撤销错误判断 |
| Orphan Signal Count | 发出但无人消费的信号数量 |

最终验收不是：

```text
有没有生成 AuroraControlSignal
```

而是：

```text
Aurora 的判断有没有真的改变任务、计划、资料调用、回复或召回？
```

---

# 23. 置信度机制：Confidence is not decoration

置信度不能只是字段。

它决定：

```text
是否写入状态
是否需要用户确认
是否能变成硬约束
是否允许长期写入
是否触发 Aurora Core
```

## 23.1 置信度来源

```text
证据数量
证据质量
证据新鲜度
来源可靠性
跨来源一致性
是否有反证
历史预测准确率
用户确认
结果反馈
```

## 23.2 写入规则

| 情况 | 动作 |
|------|------|
| 低置信 + 低影响 | 暂存，不打扰 |
| 低置信 + 高影响 | 问用户确认 |
| 中置信 + 可逆 | 可临时调整 |
| 高置信 + 可逆 | 可直接进入 directive |
| 高置信 + 不可逆 | 仍需确认 |
| 外部伙伴信号 | 默认候选，需要用户确认 |
| 社群聚合信号 | 只能作为弱偏置 |

## 23.3 反证机制

每个状态必须有 counter_evidence。

```json
{
  "state_key": "prefers_short_tasks",
  "supporting_evidence": [
    "短任务完成率高"
  ],
  "counter_evidence": [
    "用户上周完成一次 90 分钟模拟卷"
  ],
  "retract_if": [
    "连续 2 次完成长任务",
    "用户明确表示不喜欢碎片任务"
  ]
}
```

没有反证机制，Aurora 会变固执。

---

# 24. 用户主权：可解释、可纠正、可拒绝

高影响判断必须可纠正。

尤其是：

```text
你焦虑
你执行力不稳定
你适合短任务
你在逃避难点
你目标变了
你不适合冲高分
你需要提醒
```

表达方式：

```text
我现在这样判断，但你可以纠正我。
```

示例：

```text
我目前判断：任务可能排大了。
依据是最近两张任务都明显超时。

但这也可能只是你这两天临时忙。
你觉得更接近哪种？

[确实排大了]
[只是临时忙]
[不是任务大，是我不会做]
[都不对，我解释一下]
```

这就是用户主权。

---

# 25. First Minute Aha：新用户 60 秒内必须感到被理解

第一分钟体验最终定稿：

用户输入：

```text
我 7 天后计网考试，零基础，想先别挂。
```

Sparkle 必须回答：

```text
明白。你现在不是"正常学习计网"，而是"7 天先过线抢救"。

这意味着普通复习计划会害你，
因为它会把时间平均分给所有章节。

我们要先找：
1. 高频；
2. 可训练；
3. 最可能转成分数；
4. 现在还来得及补的部分。

现在不用填完整问卷。
你有课件、往年题或作业吗？
有的话我会把它们接到你的计网知识星图里。
没有的话，我们先做 12 分钟诊断，找最小通过路径。

[上传资料]
[做 12 分钟诊断]
[我只想先过线]
[我想冲高分]
```

这就是啊哈。

不是：

```text
请填写你的学习目标、基础、时间……
```

而是先证明 Sparkle 懂当前场景。

---

# 26. 7 天 Exam Sprint 的最终闭环

以计网 7 天为 P0 证明场。

## Day 0：目标建模 + 资料接入

```text
用户输入目标
→ Sparkle 判断 exam_rescue
→ 询问资料 / 诊断
→ 上传课件 / 往年题
→ SourceAsset / SourceSlice
→ 知识星图点亮
→ 12 分钟诊断
→ 最小通过路径
```

## Day 1-2：最高收益节点训练

```text
任务卡绑定资料
小测记录错因
Aurora 管理 RAG
知识节点更新
```

## Day 3-4：瓶颈修复

```text
重复错因触发 Mid Aurora
任务颗粒度调整
worked example 优先
```

## Day 5-6：高频题型与模拟

```text
错因集中修复
资料只按题型调用
不再展开大章
```

## Day 7 / D-1

```text
不推进新章节
只做高收益复盘
只加载压缩知识星图和错因
召回更谨慎但更关键
```

---

# 27. 最小 Demo：必须证明 Sparkle 的独特性

P0 Demo 不要大而全。

做一条能震撼用户的闭环。

## Demo 场景

```text
用户 7 天后考计算机网络。
上传一份课件 + 一份往年题。
Sparkle 把资料挂到知识星图。
用户做诊断。
生成任务卡。
用户错 TCP 窗口题。
Aurora 下一轮改变资料调用和任务策略。
```

## Demo 必须出现 12 个体验点

1. 用户输入目标后 60 秒内出现 exam_rescue 判断；
2. 上传资料后，知识星图节点被点亮；
3. 资料卡显示覆盖节点、用途和不足；
4. 对话里能看到 Aurora 本轮用了哪些资料；
5. 用户能手动选择资料参与本轮；
6. Sparkle 能解释为什么不加载完整课件；
7. 任务卡明确绑定资料和错因；
8. 用户小测错因写回知识节点；
9. 下一轮因为错因改变策略；
10. Aurora 状态带显示"策略风险 / 资料感知"；
11. 混合时间轴记录完整 causal trace；
12. 至少展示一个匿名社群共性错因或共享资料推荐。

这 12 点跑通，Sparkle 就和普通 AI 工具拉开差距。

---

# 28. Code Agent P0 任务书

下面是可以直接交给 coding agent 的执行口径。

---

## 项目名称

```text
Sparkle Causal Control OS v1.0 - P0 Demo
```

## 目标

不要新增孤立功能。

要建立一条完整闭环：

```text
目标输入
→ FirstMinuteSnapshot
→ 资料上传
→ SourceAsset / SourceSlice
→ 知识星图节点挂载
→ ContextPlan
→ 任务卡
→ 小测错因
→ ActionableSignal
→ StatePatch
→ PolicyDecision
→ ExecutionDirective / RetrievalDirective
→ DirectiveApplicationAudit
→ ContextReceipt / UserVisibleReceipt
→ CausalTrace
```

---

## P0-1：FirstMinuteSnapshot

输入：

```text
我 7 天后计网考试，零基础，想先别挂。
```

必须输出：

```json
{
  "detected_mode": "exam_rescue",
  "path_mode": "minimum_pass",
  "deadline_days": 7,
  "baseline": "near_zero",
  "next_best_action": "diagnostic_or_upload_materials",
  "first_user_visible_hypothesis": "这不是普通学习计划，而是 7 天先过线抢救。"
}
```

验收：

```text
用户无需填完整表单，60 秒内看到个性化判断和低成本下一步。
```

---

## P0-2：TimeContext + StaleStateGuard

必须实现：

```text
last_interaction_at
elapsed_since_last_interaction
active_task_expected_end_at
task_stale_status
deadline_phase
quiet_hours
```

验收场景：

```text
用户开始 45 分钟任务后离开 2 小时再回来。
系统不能继续上一句。
必须出现返回恢复卡：
"上一张任务预计已结束，但我还没收到完成反馈。"
```

---

## P0-3：ActionableStatePacket v1

StateAggregator 输出必须结构化：

```json
{
  "goal_frame": {},
  "time_context": {},
  "current_bottleneck": {},
  "execution_pattern": {},
  "risk_flags": [],
  "context_recommendation": {},
  "next_best_action": {}
}
```

验收：

```text
任务生成器和回复层消费这些字段，而不是只消费自然语言 prompt。
```

---

## P0-4：ExecutionDirective 最小硬约束

支持三个硬约束：

```text
max_task_duration_min
avoid_new_chapter
required_task_type
```

验收：

```text
连续任务超时后，下一张任务卡必须 <= 25 分钟。
不能推进新章节。
任务类型必须是 worked_example_then_drill。
```

---

## P0-5：RetrievalDirective / ContextPlan

支持 retrieval modes：

```text
no_retrieval
graph_only
task_bound_rag
targeted_source_rag
user_pinned_sources
```

字段：

```json
{
  "retrieval_mode": "",
  "must_load": [],
  "may_load": [],
  "do_not_load": [],
  "token_budget": 0,
  "pollution_guard": "",
  "citation_required": false,
  "user_visible_receipt": true
}
```

验收：

```text
同一问题在"通用解释"和"按课件解释"下，ContextPlan 不同。
```

---

## P0-6：SourceAsset / SourceSlice / KnowledgeNodeEvidence

资料上传后必须生成：

```text
SourceAsset
SourceSlice
KnowledgeNodeEvidence
```

验收：

```text
上传传输层课件后，TCP / UDP / 拥塞控制节点被挂载。
知识星图节点能显示资料覆盖。
```

---

## P0-7：ContextReceipt

每次资料相关回答后显示：

```text
用了哪些资料
为什么用
没用哪些资料
为什么没用
用户如何覆盖
```

验收：

```text
用户能看到"本轮没有加载完整课件，因为范围太大"。
```

---

## P0-8：DirectiveApplicationAudit

每个任务生成后必须记录：

```json
{
  "directive_id": "",
  "target_module": "task_generator",
  "applied": true,
  "applied_constraints": [],
  "overridden_constraints": [],
  "generated_output_id": ""
}
```

验收：

```text
可从 trace 看到 Aurora 判断是否真的改变任务。
```

---

## P0-9：UserVisibleReceipt

至少在"任务超时 → 任务变小"链路中出现：

```text
我把今晚任务压到 25 分钟。
原因是最近两次长任务都超时。
目标不是少学，而是先恢复可完成节奏。
```

验收：

```text
用户能感知"因为我之前的行为，Sparkle 改变了下一步"。
```

---

## P0-10：CausalTrace

记录：

```text
event
signal
state_patch
policy_decision
directive
generated_output
receipt
outcome_to_measure
```

验收：

```text
可以追踪为什么某张任务卡变短、为什么调用某份课件、为什么没推进新章节。
```

---

# 29. P1 任务

P0 跑通后，P1 做这些。

## P1-1：AchievementReinforcementConsumer

成就回流：

```text
achievement_unlocked
→ possible_growth_signal
→ current_sprint execution momentum
→ tone / nudge / challenge 调整
```

禁止直接写长期人格。

## P1-2：AuroraWakeEligibility

判断是否可唤醒完整 Aurora：

```json
{
  "can_user_wake_full_aurora": true,
  "user_quota_remaining": 1,
  "cooldown_status": "available",
  "recommended_session_type": "strategy_recalibration",
  "wake_reasons": [],
  "suggested_scope": ""
}
```

## P1-3：PredictedReplyOption Engine

每个确认问题必须有自由纠正入口。

## P1-4：RecallOpportunity

支持：

```text
上传资料未诊断
首张任务卡未启动
任务错过
考前 48h 沉默
```

## P1-5：SparkleSelfModel

记录策略是否有效。

## P1-6：CommunitySignal v1

只做匿名共性错因 + 共享资料推荐。

---

# 30. P2 任务

P2 再做：

```text
完整关系模型
长期个性化 policy learning
复杂 skill extraction
多策略实验系统
社群责任伙伴闭环
完整 Full Aurora Core Session
多消息队列
复杂 quota/cooldown
学习基地 Learning Base
```

---

# 31. 十条最终铁律

## 铁律 1：没有 action 的 signal 是噪音

任何信号不能影响：

```text
任务
计划
回复
召回
资料调用
模型写入
```

就不要进核心状态包。

## 铁律 2：没有 audit 的 directive 是幻觉

Aurora 说降低难度不算。

任务真的降低难度，并记录应用了约束，才算。

## 铁律 3：没有 outcome 的 action 不是学习

系统改了任务，但不知道结果，就是瞎调。

## 铁律 4：没有 receipt 的个性化很难被感知

用户必须看到：

```text
因为 X，我调整了 Y。
```

但要克制。

## 铁律 5：资料不能默认污染上下文

上传资料 ≠ 每轮都塞资料。

## 铁律 6：RAG 不是开关，而是 ContextPlan

必须有 retrieval_mode、must_load、do_not_load、token_budget、pollution_guard。

## 铁律 7：sprint 状态不能写成长期人格

这是长期画像污染。

## 铁律 8：高影响判断必须可纠正

用户永远可以说：

```text
都不对，我解释一下。
```

## 铁律 9：Full Aurora 不常驻

Light Aurora 常驻，Full Aurora 稀缺。

## 铁律 10：Sparkle 必须因为看见用户而改变行动

否则它只是聪明观察者。

---

# 32. 最终一句话定稿

Sparkle 的最终形态不是"一个更聪明的 AI 学习助手"。

它是：

> **一个以 Aurora 为认知内核、以知识星图为目标资产、以任务卡为执行协议、以混合时间轴为因果审计、以社群为共调节层、以 Skill Extraction 为持续学习机制的 AI-native 目标实现操作系统。**

最核心的产品体验是：

> 用户不需要管理上下文、不需要写 prompt、不需要自己判断该看哪份资料、不需要自己把失败解释成计划调整。
> Sparkle 会持续理解他的目标、材料、状态、时间和反馈，并以可解释、可纠正、可验证的方式改变下一步怎么帮他。

最终落地口号：

> **Sparkle 不能只是看见用户。
> Sparkle 必须因为看见用户，而改变自己如何帮助用户。**

---

*文档版本: v1.0 定稿*
*日期: 2026-04-27*
*状态: FINAL — 用户最终拍板*
