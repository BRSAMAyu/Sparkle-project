# Sparkle V3 Master Design

## 0. 一句话
Sparkle V3 是一个围绕长期目标运行的 **Adaptive Human–AI Action System**：它维护真实世界状态，选择最相关上下文，判断用户为什么卡住，决定人/AI如何分工，执行或推动下一步，并从真实 outcome 与用户纠正中改进下一次决策。

## 1. 四个 Plane

### State Plane
PostgreSQL/CQRS/业务服务保存 authoritative state：Goal、Action、Artifact、Memory、Knowledge metadata、Events、Run、Permission、Entitlement。Redis 是缓存/队列/短期工作状态，不替代长期真值。

### Intelligence Plane
Context Compiler + Conflict Resolver + Aurora + Model Router + RAG/Reranker。只在语义不确定性处使用模型；确定性约束先过滤。

### Execution Plane
Action/Command protocol + Unified Agent Runtime + Tool Registry + Celery workers。模型提出 plan；工具执行受权限/幂等/预算/回执控制。

### Experience Plane
Flutter/Web/macOS UI + Today/Goal/Chat/Galaxy/My + Insights + Community + Proactive + Observability。所有 intelligence 必须通过用户可理解的状态呈现。

## 2. 核心循环
```
Goal + Current Reality
      ↓
User World Snapshot
      ↓
Context Compiler ── Memory / Knowledge / Events
      ↓
Conflict Resolution
      ↓
Aurora Decision
  ┌───┼────────────┐
Human Agent      Hybrid
  └───┼────────────┘
      ↓
Action / Run / Handoff
      ↓
Outcome / Evidence
      ↓
Experience Memory + Goal State + Analytics + Galaxy
      └────────────────────────→ next decision
```

## 3. “越用越好”的可执行定义
不是模型权重自动训练，也不是 vector DB 越来越大。

第 N 天比第 1 天更好，需要同时成立：
- 更少重复询问已确认信息；
- 在正确 scope 复用过去有用 intervention；
- 用户改口后能更新；
- 过期/删除信息不出现；
- 对无关问题不过度个性化；
- 过去 outcome 影响未来 action selection；
- 个性化带来可测 decision utility uplift。

## 4. 关键架构边界
- LLM 不是 truth database；
- Aurora 不直接绕过 Task/Command authoritative path；
- Memory retrieval 不绕过 identity/scope/TTL；
- RAG knowledge 不变成 User Memory；
- community context 不继承 private profile；
- Analytics 先事实 JSON 后解释；
- Agent Runtime 只有一套；OpenClaw 等能力适配进去；
- UI 的“成功”必须由真实 receipt 驱动。

## 5. 质量策略
V3 将 simulator 当第一等测试层。任何用户可见卡都至少要求：
- code-level test；
- integration proof；
- simulator/real-render proof；
- independent review；
- merge-head recheck。

AI 行为额外要求多次真实模型运行；视觉行为额外要求截图与 rubric；隐私/删除/执行额外 2 reviewers。

## 6. 交付优先级
Truth → First Value → Core Intelligence → Closed Loop → Trust → Experience Excellence → Commercial Runtime → Red Team。

任何阶段都优先修 false success / privacy / wrong user / bad state truth，然后才修美观。
