# Sparkle 闭环落地工程方案 v1.1

## 从"Causal Control Spine 骨架已实现"到"活的因果控制系统"

> **现在不要再重建主架构。主干已经有了。接下来要做的是把还没闭环的能力接进现有 Spine，让每一个关键观察真的改变任务、计划、资料调用、社区策略、成就反馈和用户体验。**

---

# 1. 总策略

## 1.1 不做大重构，做闭环接线

正确做法：

```text
保留现有 Spine
→ 找到未消费的信号
→ 加最小 Directive / Policy Rule / UI Receipt
→ 接入下游模块
→ 记录 Audit 和 Outcome
→ 让用户看到变化
```

所有新能力必须落到一个用户可见变化上。

## 1.2 本阶段总链路

每一个未闭环能力都必须走这条标准流程：

```text
Trigger / Raw Event
→ ActionableSignal
→ StatePatch
→ PolicyDecision
→ Directive
→ Downstream Consumer
→ DirectiveApplicationAudit
→ UserVisibleReceipt / UI Change
→ Outcome
→ Policy / SelfModel / Skill Update
→ CausalTrace
```

---

# 2. 当前实际缺口分级

## A 类：主链已存在，但缺消费者 / policy rule

1. Achievement momentum → PolicyEngine
2. Community signals → CommunityDirective
3. OutcomeRecorder → PolicyEngine / SelfModel learning
4. Galaxy per-node mastery → planning difficulty
5. Deadline phase → ExamSprintPolicy

## B 类：后端 API 有，但前端体验没有闭合

1. Causal Timeline UI
2. Source Tray UI
3. 完整任务卡协议 UI
4. 神性时刻 UI / copy / 状态带入口
5. 成就回流后的 Aurora 反馈

## C 类：概念存在，但还没有系统化运行

1. Aurora L4 异步深度学习
2. SkillDirective 接入 Spine
3. Skill Extraction → Learning Base
4. 社群三闭环完整自动化
5. Policy Experiment / Outcome Learning
6. SourceAsset / SourceSlice 规范模型

---

# 3. P0 闭环一：成就 → AI 自适应

## 3.1 三级规则

### Rule A：高质量连胜（momentum >= 0.75 + quality_ok）

```text
recognize_consistency
reduce_activation_nudges
increase_challenge_small_if_safe
```

### Rule B：连胜但质量不足（momentum >= 0.75 + declining accuracy）

```text
recognize_effort_but_repair_quality
avoid_challenge_increase
task_type → mistake_repair
```

### Rule C：连胜但超时/压力高（momentum >= 0.75 + overrun OR high pressure）

```text
protect_sustainability
max_task_duration_min: 25
avoid: "你已经很稳了，再加一把"
```

## 3.2 验收

- seven_day_streak 影响下一轮任务和语气
- 连胜+质量差 → 不加难度
- 连胜+超时 → 缩短任务

---

# 4. P0 闭环二：CommunityDirective v1

## 4.1 CommunityDirective schema

```json
{
  "directive_id": "cd_001",
  "cohort_hint_shown": true,
  "resource_quality_filter": 0.5,
  "peer_context_mode": "anonymous",
  "max_frequency": "3_per_week"
}
```

## 4.2 三闭环

1. 责任伙伴闭环 → partner_observation → user confirmation
2. 同伴错因闭环 → cohort_common_mistake → KnowledgeNode / TaskTemplate
3. 资源质量闭环 → resource_quality → Source recommendation candidate

## 4.3 验收

- 社区共性错因能改变任务卡 why 和 task_type

---

# 5. P0 闭环三：TaskCardProtocol

## 5.1 完整字段

```text
why_this_task
materials
stuck_protocol
updates_after_completion
```

## 5.2 卡住协议

| 用户卡点    | ContextPlan                          |
| ------- | ------------------------------------ |
| 规则看不懂   | graph_only + source_slice definition |
| 会规则不会做题 | worked_example + mistake_cluster     |
| 步骤跟不上   | step_by_step_trace                   |
| 时间不够    | shrink_task                          |
| 状态不行    | recovery_task / affective support    |

## 5.3 验收

- 任务卡不再只是标题/时长/难度，而是完整执行协议

---

# 6. P0 闭环四：Outcome → PolicyEffectLedger

## 6.1 PolicyEffectEntry

```json
{
  "entry_id": "pe_001",
  "policy_key": "recover_execution_rhythm",
  "intervention_summary": "max_task_duration_min=25",
  "attribution": "insufficient",
  "user_feedback_signal": "看不懂",
  "new_hypothesis": "knowledge_explanation_failure"
}
```

## 6.2 学习规则

### Rule A：策略有效
task_started + task_completed + accuracy >= baseline + feedback != negative
→ strategy_confidence + small_delta, allow reuse

### Rule B：策略不足
task_started + NOT completed + feedback 指向"看不懂"
→ 不继续缩短任务，改 worked_example / step-by-step

### Rule C：没有启动
task NOT started
→ 先区分原因（时间/提醒/价值/状态），不直接判断设计无效

## 6.3 三层消费

```text
Outcome → PolicyEffectLedger → PolicyUpdateCandidate → shadow mode rule bias → 达到阈值后 live
```

第一版只做 shadow：policy_update_candidate 被记录，下一轮 PolicyDecision 可读取，但不改全局规则表。

## 6.4 验收

- 缩短任务仍失败后，下一轮不继续机械缩短，而改策略

---

# 7. P0 闭环五：SourceAsset wrapper + Source Tray

## 7.1 adapter-first

保留 DocumentChunk，新增 SourceAsset/SourceSlice wrapper。

## 7.2 验收

- 用户能选择资料参与本次回答
- Aurora 仍能解释使用/不使用原因

---

# 8. P0 闭环六：ExamSprintPolicy + Galaxy difficulty

## 8.1 ExamSprintPolicy 枚举

```text
exam_sprint_7d_rescue
exam_sprint_14d_intensive
standard_exam_mastery
```

## 8.2 D-7 → D-0 阶段策略

| 阶段  | Policy                                    |
| --- | ----------------------------------------- |
| D-7 | diagnostic_first, build_minimum_pass_path |
| D-5 | high_yield_node_training                  |
| D-3 | mistake_repair_priority                   |
| D-1 | no_new_chapter, review_only               |
| D-0 | low_load_recall                           |

## 8.3 Galaxy baseline → 任务难度

| Mastery   | Task Type                            |
| --------- | ------------------------------------ |
| 0.0 - 0.3 | concept compression + worked example |
| 0.3 - 0.5 | worked example + guided drill        |
| 0.5 - 0.7 | drill + mistake check                |
| 0.7+      | mixed practice / exam simulation     |

## 8.4 验收

- 7 天计网先过不会平均复习，按收益/掌握度/可训练性排任务

---

# 9. P0 闭环七：两个神性时刻

## 9.1 记得时间

StaleStateGuard 检测 → 结构化恢复卡片

## 9.2 承认误判

Outcome insufficient → self-correction receipt:
"我需要修正一下。之前把问题理解成 X，但反馈说明更可能是 Y。所以改成 Z。"

---

# 10. 总验收指标

| 指标                           | 验收含义                        |
| ---------------------------- | --------------------------- |
| Orphan Signal Count          | 关键事件是否仍无人消费                 |
| Directive Application Rate   | directive 是否真的被下游执行         |
| UserVisibleReceipt Rate      | 用户是否看到系统为什么调整               |
| Outcome Feedback Rate        | 行动后是否记录结果                   |
| Policy Self-Correction Count | 系统是否能承认并修正策略                |
| Source Pollution Avoidance   | 是否避免粗暴加载完整资料                |
| Task Protocol Completion     | 任务卡是否包含 why/materials/stuck |
| Community-to-Task Rate       | 社群信号是否真的改变任务                |
| Achievement-to-Policy Rate   | 成就是否改变策略                    |
| Galaxy-to-Plan Rate          | 星图掌握度是否改变计划                 |

---

# 11. 执行顺序

```text
P0-1: Achievement → PolicyEngine (3-tier rules)      ← DONE
P0-2: CommunityDirective v1                           ← DONE
P0-3: Task card protocol (why/materials/stuck)        ← NEXT
P0-4: Outcome → PolicyEffectLedger                    ← IN PROGRESS
P0-5: SourceAsset wrapper + Source Tray minimal       ← LATER
P0-6: ExamSprintPolicy + Galaxy difficulty            ← LATER
P0-7: Divine moments (admit misjudgment + remember time) ← LATER
```

---

# 12. 最终裁决

> **每一个关键观察都必须改变 Sparkle 的下一步。
> 每一次改变都必须能被审计。
> 每一次重要改变都必须能被用户感知、纠正和反馈。**

做到这个，Sparkle 才会从"已经有很强基础设施的 AI 学习系统"，真正变成一个用户能感受到的目标实现操作系统。
