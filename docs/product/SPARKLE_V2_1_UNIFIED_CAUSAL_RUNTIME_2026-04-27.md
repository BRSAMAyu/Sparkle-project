# Sparkle v2 后续完整修复方案

> **Date**: 2026-04-27
> **Version**: v2.1 Unified Causal Runtime
> **Core Principle**: 所有用户可见行为都必须从同一条 Causal Runtime 经过

## 核心诊断

v2 的问题不是能力缺失，而是运行形态缺失：

1. **Aurora 和 Spine 是双系统** — 互相不知道存在
2. **模块实现了但没有成为生产路径** — 12 个孤立模块、3000+ 行沉睡代码
3. **神性时刻有逻辑没有体验** — 4/6 只有后端对象，用户感知不到
4. **长期稳定性不足** — 老用户回归失忆、高频退化、多目标污染

## 五条总线

```
1. Event Bus — 事实事件总线
2. State Bus — ActionableStatePacket / AuroraCaseFile / ActiveState
3. Control Bus — PolicyDecision / AuroraControlSignal / Directives
4. Experience Bus — Receipt / StatusBand / TimelineCard / RecoveryCard
5. Learning Bus — Outcome / PolicyEffect / SkillEffectiveness / SourceEffectiveness
```

## v2.1-v2.5 Roadmap

### v2.1: 统一运行内核
- Aurora ↔ Spine 合流
- ExperienceEnvelope 上线
- 神性时刻进入主链
- 孤立模块注册激活

### v2.2: 长期稳定性
- SpineSnapshot + Rehydration
- TraceCompaction
- RollingMetrics
- MultiGoalNamespace

### v2.3: 极端场景
- FatigueGuard
- exam_crisis_zero_base
- Degraded Mode
- Redis Recovery

### v2.4: Learning Layer
- PolicyExperiment shadow
- StrategyBelief consumption by PolicyEngine
- Skill lifecycle
- SourceEffectiveness

### v2.5: General Goal OS 准备
- GoalWorldGraph
- DomainPack
- MultiGoalArbitration

## 核心对象

### CausalTurnContext (每轮唯一事实来源)
```json
{
  "turn_id": "turn_123",
  "user_id": "u_001",
  "goal_id": "goal_cn_exam_7d",
  "message": "我还是看不懂 TCP 窗口题",
  "actionable_state_packet": {},
  "recent_policy_effects": [],
  "source_context_summary": {},
  "community_context_summary": {},
  "relationship_context": {},
  "aurora_case_file": {},
  "runtime_mode": "live"
}
```

### ExperienceEnvelope (统一体验输出)
```json
{
  "experience_envelope": {
    "turn_id": "turn_123",
    "primary_message": {},
    "status_band": {},
    "receipts": [],
    "context_receipt": {},
    "cards": [],
    "predicted_reply_options": [],
    "timeline_updates": [],
    "task_card_updates": [],
    "debug_trace_id": ""
  }
}
```

### Capability Hook Points
```
pre_turn_enricher     — 本轮开始前补充上下文
signal_producer       — 事件转 ActionableSignal
policy_bias_provider  — 给 PolicyEngine 提供偏置
directive_provider    — 生成专门 directive
experience_renderer   — 系统变化变用户可见卡片
post_outcome_learner  — 根据结果学习
```

## 12 孤立模块的正确接入位置

| 模块 | 接入方式 |
|------|---------|
| policy_analytics | async / dashboard / Learning Bus |
| policy_experiments | shadow first，产出 PolicyUpdateCandidate |
| research_grade | research/admin only |
| growth_chronicle | pre_turn_enricher + experience card |
| relationship_model | response_policy_bias_provider |
| skill_extraction | post_outcome_learner / async L4 |
| source_tray_integration | retrieval_policy_provider + context_receipt_renderer |
| external_integration | external_signal_bridge，goal-bound |
| goal_type_adapter | planning_policy_provider |
| learning_base | policy_bias_provider / skill matcher |
| material_signal | source_signal_producer |
| timeline_card_renderer | experience_renderer |

## 六个神性时刻闭环

每个必须有: Trigger → Signal → StatePatch → PolicyDecision → Directive → ExperienceEnvelope → UserAction → Outcome → CausalTrace

1. **看见坚持** — streak → GrowthMomentumSignal → reinforce_without_overpressure
2. **承认误判** — user_correction → self_correction → strategy change
3. **知道不用资料** — retrieval_decision → SourceDecision → ContextReceipt
4. **记得时间** — user_return → RecoveryCard → 阻塞型确认
5. **阻止低收益** — deadline_pressure → quality_cross_check → 建议不强制
6. **社群经验转策略** — cohort_mistake → CommunityDirective → task bias

## 极端条件防护

### FatigueGuard
输入: 连续在线时长、任务数量、交互频率、正确率下降、深夜使用
输出: fatigue_level (low/medium/high/critical) + recommended_policy

### Crisis Mode (零基础+3天)
策略: 不追求体系，只追求最低可得分路径，每步可验收，强制不平均复习

### Degraded Mode (Redis down)
分层: Normal → Degraded Read (Postgres) → Stateless Safe → Recovery

## E2E 测试矩阵 (最少12条)

1. First Minute Aha → plan → task
2. 用户离开2h → Recovery Card
3. 用户纠正"不是任务太长，是不会" → 自我纠错
4. 普通概念问题 → 不调用课件 + ContextReceipt
5. 用户明确"按课件讲" → 调用 SourceSlice
6. 七连胜 → Growth Card + 策略改变
7. 社区共性错因 → 任务模板改变
8. 多目标冲突 → MultiGoalArbitration
9. Redis down → Degraded Mode
10. 老用户3月回归 → Snapshot Rehydration
11. 考前24h高频 → FatigueGuard
12. 零基础3天考试 → Crisis Mode

## Definition of Done (所有 PR 必须满足)

1. 是否进入 Unified Causal Runtime？
2. 是否有 CausalTurnContext 输入？
3. 是否产生或消费 ActionableSignal / State / Policy / Directive？
4. 是否进入 ExperienceEnvelope？
5. 用户是否能看见关键变化？
6. 用户是否能纠正？
7. 是否有 Outcome？
8. 是否有 CausalTrace？
9. 是否有 kill switch / shadow mode？
10. 是否有 E2E 测试？
11. 是否考虑 Redis/TTL/老用户回归？
12. 是否考虑多目标作用域？
