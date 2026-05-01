# Sparkle Signal-to-Action Spine

> **日期**: 2026-04-27
> **版本**: v1.0 定稿
> **本质**: 从"聪明的观察者"到"真正的教练"
> **P0 口号**: 先打通一条可验收的因果链，不要一次做完整 OS

---

## 一、核心命题

Sparkle 现在已经有很多观察能力、事件能力、记忆能力、路由能力、成就能力、追踪能力，但它们还没有稳定汇聚成一个用户能感受到的"教练式行动系统"。

这次不是做成就系统，不是做召回系统，也不是做更复杂的 Aurora。

> **让 Sparkle 的每一个重要观察，都能沿着一条可追踪、可执行、可感知的路径，变成对用户更有帮助的下一步行动。**

> Sparkle 不能只是"看见用户"。Sparkle 必须因为看见用户，而改变自己如何帮助用户。

---

## 二、P0 最高优先级澄清

### A1. 本轮不是"重构全系统"

不是让 agent 大规模重写事件系统、画像系统、任务系统、RAG系统、Aurora系统、知识星图、社群、成就、推送。

正确做法：**在现有系统上建立一条可验证的 P0 因果链路。**

P0 只需要证明：
```
一个重要观察
→ 被解释成 ActionableSignal
→ 改变 ActionableState
→ 经过 PolicyDecision
→ 生成 Directive
→ 下游模块执行
→ 用户看到 Receipt
→ Trace 里能审计
```

第一版不是 OS 全量完成，而是 OS 的第一条主干神经打通。

### A2. P0 的唯一证明场：计网 7 天抢救

所有 P0 任务必须围绕这个场景：
- 用户 7 天后计算机网络考试
- 基础薄弱
- 目标先不挂科
- 上传课件
- 做诊断
- 生成任务卡
- 任务超时 / 做题出错
- Sparkle 因此改变下一步

**如果一个改动不能服务这个路径，默认不是 P0。**

### A3. P0 不要求"智能最优"，要求"控制链路真实"

第一版不要追求 Aurora 判断多完美。要追求：
- 判断可追踪
- 约束可执行
- 执行可审计
- 用户可感知
- 结果可回流

P0 的价值不是"AI 真的像顶级教练"，而是：**Sparkle 第一次拥有了从观察到行动的硬通道。**

---

## 三、三大 Milestone

### Milestone 1：控制链路最小可运行

**目标**：证明 Aurora 判断能改变任务卡。

**数据对象**：RawEvent → ActionableSignal → ActionableStatePacket → PolicyDecision → ExecutionDirective → DirectiveApplicationAudit → UserVisibleReceipt → CausalTrace

**场景**：
```
连续任务超时
→ 判断任务颗粒度偏大
→ max_task_duration_min = 25
→ 下一张任务卡真的 <= 25 分钟
→ 用户看到为什么变短
→ trace 可审计
```

### Milestone 2：资料闭环最小可运行

**目标**：证明资料不是 RAG 噪声，而是可控上下文资产。

**数据对象**：SourceAsset → SourceSlice → KnowledgeNodeEvidence → RetrievalDirective / ContextPlan → ContextReceipt

**场景**：
```
用户上传计网传输层课件
→ 系统挂载 TCP / UDP / 拥塞控制节点
→ 用户问 TCP 拥塞控制
→ Aurora 选择 task_bound_rag
→ 只加载相关 slice，不加载完整课件
→ 回复底部展示 ContextReceipt
```

### Milestone 3：错因驱动策略改变

**目标**：证明学习结果能改变后续策略。

**数据对象**：MiniQuizResult → MistakeSignal → KnowledgeStatePatch → PolicyDecision → ExecutionDirective → TaskCard regeneration → CausalTrace

**场景**：
```
用户 TCP 窗口题连续错
→ 识别 transfer_failure / mistake_cluster
→ avoid_new_chapter = true
→ required_task_type = worked_example_then_drill
→ 下一张任务卡改为错因修复
```

---

## 四、P0 数据对象精简版

### D1. ActionableSignal v0

```json
{
  "signal_id": "sig_001",
  "source_event_ids": ["evt_001"],
  "source_system": "task_service",
  "state_key": "task_granularity_fit",
  "claim": "recent_task_too_large",
  "confidence": 0.72,
  "scope": "current_sprint",
  "ttl_hours": 72,
  "evidence_summary": "连续 2 次任务实际耗时超过预估 40%",
  "possible_effects": [
    "cap_task_duration",
    "avoid_new_chapter",
    "prefer_worked_example"
  ],
  "priority": "high"
}
```

### D2. ActionableStatePacket v0

```json
{
  "goal_frame": {
    "mode": "exam_rescue",
    "subject": "computer_networks",
    "deadline_days": 7,
    "target": "pass_first"
  },
  "top_states": [
    {
      "state_key": "task_granularity_fit",
      "value": "too_large",
      "confidence": 0.72,
      "scope": "current_sprint"
    }
  ],
  "current_bottleneck": {
    "node_id": "cn.tcp.congestion_control",
    "type": "transfer_failure"
  },
  "risk_flags": [
    "deadline_pressure_high",
    "recent_task_overrun"
  ],
  "next_best_action": {
    "type": "generate_recovery_task",
    "strategy": "worked_example_then_drill"
  }
}
```

### D3. PolicyDecision v0

```json
{
  "policy_decision_id": "pd_001",
  "primary_strategy": "recover_execution_rhythm",
  "secondary_strategy": "repair_current_bottleneck",
  "hard_constraints": {
    "max_task_duration_min": 25,
    "avoid_new_chapter": true,
    "required_task_type": "worked_example_then_drill"
  },
  "soft_biases": {
    "tone": "direct_but_reassuring",
    "difficulty": "medium_low"
  },
  "visibility": "receipt",
  "requires_user_confirmation": false,
  "reasoning_summary": "最近任务超时，先恢复可完成节奏。"
}
```

### D4. ExecutionDirective v0

```json
{
  "directive_id": "ed_001",
  "policy_decision_id": "pd_001",
  "target_module": "task_generator",
  "scope": "today",
  "hard_constraints": {
    "max_task_duration_min": 25,
    "avoid_new_chapter": true,
    "required_task_type": "worked_example_then_drill"
  },
  "user_visible_reason": "最近两次长任务都超时，我会先把今晚任务压小。"
}
```

### D5. DirectiveApplicationAudit v0

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
  "violations": [],
  "generated_output_id": "task_002",
  "generated_output_summary": {
    "duration_min": 23,
    "new_chapter": false,
    "task_type": "worked_example_then_drill"
  }
}
```

### D6. UserVisibleReceipt v0

```json
{
  "receipt_id": "rcpt_001",
  "type": "strategy_adjustment",
  "message": "我把今晚任务压到 25 分钟，因为最近两次长任务都超时。目标不是少学，而是先恢复可完成节奏。",
  "actions": [
    "confirm",
    "correct",
    "dismiss"
  ],
  "related_state_keys": [
    "task_granularity_fit"
  ]
}
```

### D7. CausalTrace v0

```json
{
  "trace_id": "ct_001",
  "raw_event_ids": ["evt_001", "evt_002"],
  "signal_ids": ["sig_001"],
  "state_keys_changed": ["task_granularity_fit"],
  "policy_decision_id": "pd_001",
  "directive_ids": ["ed_001"],
  "audit_ids": ["audit_001"],
  "receipt_ids": ["rcpt_001"],
  "outcome_to_measure": [
    "task_started",
    "task_completed",
    "actual_duration_min",
    "mini_quiz_accuracy",
    "user_feedback"
  ]
}
```

---

## 五、P0 验收用例

### E1. 任务超时导致任务变短

**Given**: 用户在 7 天计网冲刺中；连续 2 张任务卡预估 45 分钟，实际均超过 65 分钟

**When**: 系统生成下一张任务卡

**Then**:
- 产生 ActionableSignal: task_granularity_fit=too_large
- 产生 PolicyDecision: recover_execution_rhythm
- 产生 ExecutionDirective: max_task_duration_min <= 25
- 下一张任务卡 duration <= 25
- DirectiveApplicationAudit.applied = true
- 用户看到 Receipt

### E2. 错因重复导致不推进新章节

**Given**: 用户连续 3 次在 TCP 拥塞控制窗口变化题上出错

**When**: 系统生成下一步计划

**Then**:
- knowledge_bottleneck = cn.tcp.congestion_control
- transfer_failure = true
- avoid_new_chapter = true
- required_task_type = worked_example_then_drill
- 下一张任务卡主题仍是 TCP 拥塞控制
- 不能生成应用层新章节任务

### E3. 上传课件后按需调用资料

**Given**: 用户上传计网第 4 章传输层课件；资料已解析并挂载到 TCP 节点

**When 1**: 用户问：TCP 拥塞控制是什么？
**Then 1**: ContextPlan 可以使用 graph_only 或 targeted_source_rag；不应加载完整课件；ContextReceipt 显示本轮是否使用课件

**When 2**: 用户问：按我上传的课件讲 TCP 拥塞控制。
**Then 2**: ContextPlan 必须使用 user_pinned_sources 或 targeted_source_rag；must_load 包含相关 SourceSlice；回复必须有资料依据

### E4. 新用户 60 秒啊哈

**Given**: 新用户第一次输入：我 7 天后计网考试，零基础，想先别挂。

**Then**:
- 不要求先完成完整表单
- 必须输出 exam_rescue 判断
- 必须解释为什么不能普通复习
- 必须给出低成本下一步：上传资料或 12 分钟诊断
- 必须给出可纠正选项

### E5. StaleStateGuard

**Given**: 用户开始 45 分钟任务后离开 2 小时；没有完成反馈

**When**: 用户再次打开对话

**Then**:
- 系统不能直接继续上一轮回答
- 必须生成 TimeDeltaPacket
- 必须询问任务状态
- 提供选项：做完了 / 做一半 / 没开始 / 换小任务

---

## 六、实现顺序

```
Step 1: 先做 trace 骨架，不做智能
    RawEvent → CausalTrace skeleton
    即使中间字段先为空，也要能看到 trace 框架

Step 2: 做一个固定规则信号
    连续 2 次任务超时 → task_granularity_fit=too_large
    不要一上来 LLM 推断

Step 3: 让一个 directive 真正控制任务生成
    max_task_duration_min=25
    这一步最关键

Step 4: 加 audit
    确认任务真的 <=25 分钟

Step 5: 加 receipt
    让用户看到调整原因

Step 6: 再接资料闭环
    SourceSlice / ContextPlan / ContextReceipt

Step 7: 再接错因闭环
    MistakeSignal / KnowledgeStatePatch / repair task

Step 8: 再接 Aurora 状态带
    先展示：本轮用了哪些上下文 / 为什么任务变短 / 是否有策略风险
    不要先做炫酷 UI
```

---

## 七、coding agent 最容易误解的 12 件事

| # | 误解 | 正确理解 |
|---|------|---------|
| C1 | 每个事件都转 ActionableSignal | 只有**可能改变行动**的事件才转 ActionableSignal |
| C2 | 把用户信息都塞进 State Register | State Register **只放**会影响本轮/近期控制决策的状态位 |
| C3 | 让 LLM 读状态后写策略建议 | PolicyDecision **必须输出结构化** hard_constraints / soft_biases / visibility / confirmation |
| C4 | 把 directive 拼进 system prompt | 下游模块**必须以结构化参数消费** directive |
| C5 | 任务生成后随便记一条 applied=true | Audit 要**验证输出是否满足 directive** |
| C6 | 每次调整都给用户长篇解释 | Receipt 要**短、具体、可纠正** |
| C7 | 把所有引用资料列出来 | ContextReceipt 说明**"用了什么、没用什么、为什么"** |
| C8 | rag_enabled=true/false | RetrievalDirective = retrieval_mode + source_scope + budget + pollution_guard |
| C9 | 做一个"和 Aurora 聊天"的入口 | Full Aurora 是**限时校准 session**，有 agenda、有退出、有冷却、有状态写回 |
| C10 | 七连胜 → 用户执行力强 | 七连胜 → **当前 sprint 下存在连续完成行为**，需结合质量判断 |
| C11 | 同学说他拖延 → 写入用户拖延 | 外部信号默认是 **candidate**，必须用户确认或弱偏置 |
| C12 | 现在就做 Learning Base | P0 只记录 trace 和 outcome，为未来 skill extraction 留数据 |

---

## 八、工程边界与降级策略

| 场景 | 策略 |
|------|------|
| LLM 不稳定 | PolicyDecision 第一版规则化：`if task_overrun_count >= 2: max_task_duration_min = 25` |
| 知识星图挂载不完整 | 先允许手动映射：课件第4章 → cn.transport_layer |
| RAG 检索质量不稳 | 先使用用户手选资料 + 章节切片，不做全库向量搜索 |
| 成就回流复杂 | 先不做成就回流，优先任务超时和错因重复 |
| 社群信号复杂 | P0 只展示一条匿名共性错因，不进入个人模型 |

---

## 九、产品微交互（决定"它像系统"还是"它像真的懂我"）

### H1. 用户纠正后必须立即承认

用户点"不是任务大，是我不会做"：
> 明白，那我收回"任务颗粒度偏大"这个判断。我现在改判为：当前主要问题是知识瓶颈，不是时间安排。下一张任务我会保留短时长，但重点换成 worked example，而不是单纯缩小任务。

### H2. 系统不确定时要说"不确定"

> 我现在不确定是任务太大，还是你这两天临时忙。但这会影响今晚安排，所以我先问你一个很短的问题。

### H3. Receipt 要有撤销入口

[这样安排] [不是这个原因] [别再这样判断]

### H4. ContextReceipt 要允许覆盖

[按课件重讲] [改用往年题] [不要用这份资料]

### H5. 状态带不要一直闪

只在状态变化、资料调用、策略风险、校准需要时有明显变化。

---

## 十、防膨胀约束（残忍执行）

Causal Control OS 很容易变成"架构对象爆炸"。**每新增一个对象，都要绑定一个 P0 用户可见变化：**

| 对象 | 必须带来的用户可见变化 |
|------|---------------------|
| ActionableSignal | 用户下一步变了 |
| PolicyDecision | 任务/计划/资料调用变了 |
| ExecutionDirective | 任务参数真的变了 |
| RetrievalDirective | 资料调用方式真的变了 |
| UserVisibleReceipt | 用户知道为什么变了 |
| CausalTrace | 团队能审计为什么变了 |

**如果没有这个约束，就会架构膨胀。不然又会变成一堆漂亮 JSON 在数据库里睡觉，毫无用处。**

---

## 十一、最终定稿结论

1. **P0 要极度收窄**：先打通一条因果链，不要一次做完整 OS
2. **Directive 必须硬执行并审计**，否则 Aurora 仍然只是 prompt 建议
3. **用户必须感知"因为我做了 X，Sparkle 改变了 Y"**，否则闭环再完整也没有产品价值

最短执行原则：
- 先让 Sparkle 在一个地方真的改变
- 再让它在更多地方改变
- 不要先让它到处"看见"

---

*文档版本: v1.0 定稿*
*日期: 2026-04-27*
*基于: Sparkle Signal-to-Action Spine 设计讨论*
