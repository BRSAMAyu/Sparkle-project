# Sparkle 完全体落地路线 v2.0

> **文档类型**: 产品 + 工程路线图
> **日期**: 2026-04-27
> **状态**: ACTIVE BLUEPRINT
> **前置**: Signal-to-Action Spine 完全体 (330/330 tests, 9/9 directive types)

---

## 修正：v1 专家愿景的 3 个偏差

1. **不要过度考试化** — GoalWorldGraph 应泛化到考研/项目/求职/健身/创业，不只是 exam sprint
2. **不要过度暴露内部机制** — 用户不需要知道 "PolicyEngine" 或 "StateRegister"，他们看到的是 "我的学习计划根据你的进度做了调整"
3. **长期成长编年史必须用户共治** — 不是 surveillance，是 user-co-owned growth narrative

---

## 最终产品定义：9 个核心系统

| # | 系统 | 面向用户价值 | 现有基础设施 |
|---|------|------------|------------|
| 1 | Goal Modeling | 目标澄清 → 好目标 | Aurora Runtime v1 三层架构 |
| 2 | Goal World Graph | 目标空间可视化 + 节点掌握度 | Galaxy 知识星图 |
| 3 | Source & Evidence | 资料不是噪声而是可控上下文 | SourceAsset/SourceSlice/SourceTray |
| 4 | Aurora Control | 自适应干预 + 用户可纠正 | Signal Spine 9 directive types |
| 5 | Task Protocol | 任务卡 8 字段标准 | planning_workflow._build_task_guide_json |
| 6 | Causal Timeline | "为什么给我这个任务" 可追溯 | CausalTrace + Timeline API |
| 7 | Community | 同伴经验转策略 | CommunityDirective v1 |
| 8 | Skill Extraction | 有效策略自动提取 | SkillExtractionService |
| 9 | Growth Chronicle | 成长叙事，用户共治 | Achievement + Reflection |

---

## P1: Living Experience Layer（活体验层）

**目标**: 把已有基础设施变成用户能感知、能理解、能纠正的活体验

### P1-1: Causal Timeline UI

**用户价值**: 用户问 "为什么给我这个任务"，系统能展示完整因果链

**工程规格**:
- 后端: Timeline API 已有 (`/spine/timeline`), 需要增强为 timeline card 渲染
- 新增 `TimelineCardRenderer` — 将 CausalTrace 转为用户可理解的卡片
- 卡片类型:
  - compact: "根据你的学习进度，建议调整任务难度" (1 行)
  - expanded: 展示 signal → policy → directive → outcome 完整链路
- 用户纠正动作:
  - "这个判断不对" → UserVisibleReceipt with correction options
  - "我想调整策略" → PredictedReplyOption escape hatch

**验收**:
- [ ] TimelineCardRenderer 支持 compact + expanded 两种模式
- [ ] 每张卡片有 "为什么?" 展开按钮
- [ ] 用户可纠正错误判断
- [ ] 纠正记录进入 CausalTrace

### P1-2: Source Tray + SourceAsset Wrapper

**用户价值**: 用户控制什么资料进入 AI 上下文

**工程规格**:
- SourceAsset/SourceSlice types 已存在
- 需要 SourceTray 组件: 用户可勾选/排除资料
- RetrievalDirective 集成: source_scope 从 user_selected 读取 SourceTray 选择
- ContextReceipt 增强: 显示 "用了什么资料 / 没用什么 / 为什么"

**验收**:
- [ ] SourceTray UI 组件
- [ ] RetrievalDirective 从 SourceTrayState 读取选择
- [ ] ContextReceipt 显示资料使用详情

### P1-3: Aurora Wake + Core Session v1

**用户价值**: 系统不只是被动回复，而是主动理解

**工程规格**:
- AuroraWakeEligibility 已实现 (7 tests)
- 需要 Core Session: 一次完整 goal→plan→execute→reflect 周期
- Session lifecycle: active → paused → completed → reflected
- Session 状态持久化到 Redis

**验收**:
- [ ] Core Session lifecycle 管理
- [ ] Session 状态跨设备同步

### P1-4: CommunityDirective v1

**用户价值**: 同伴的错我不用犯

**工程规格**:
- CommunityDirective 类型已存在
- 需要 3 种具体循环:
  1. cohort_mistake: 同伴常见错误 → 匿名提示
  2. partner_observation: 责任伙伴反馈 → 策略微调
  3. resource_quality: 资源质量评分 → 推荐优化
- Community signal → PolicyEngine → CommunityDirective pipeline

**验收**:
- [ ] cohort_mistake 循环完整
- [ ] partner_observation 循环完整
- [ ] resource_quality 循环完整

### P1-5: SkillDirective v1

**用户价值**: 有效策略被记住，下次自动复用

**工程规格**:
- SkillExtractionService 已实现
- 需要 SkillDirective 消费端:
  - inject: 将已提取 Skill 注入任务生成
  - recommend: 推荐相关 Skill 给用户确认
  - extract: 触发新 Skill 提取
- skill_tcp_worked_example_repair: 首个通用 TCP (Transfer Control Protocol for learning)

**验收**:
- [ ] Skill inject 在 task generation 中生效
- [ ] Skill recommend 提供用户确认选项
- [ ] Worked-example-repair TCP 完整实现

### P1-6: Goal-Respectful Recall v1

**用户价值**: 系统主动召回不是骚扰，是有意义的提醒

**工程规格**:
- RecallOpportunityDetector 已实现 (10 tests)
- 需要 NotificationDirective 消费端集成
- 冷却期 + 频率限制 + 用户偏好
- 召回消息模板: 4 种 trigger × 3 种策略

**验收**:
- [ ] Notification service 消费 RecallOpportunity
- [ ] 冷却期 + 频率限制正确
- [ ] 用户可配置召回偏好

---

## P2: Self-Improving Learning Layer（自进化学习层）

**目标**: 系统从结果中学习，策略越来越好

### P2-1: L4 Async Deep Learning
- 异步策略优化 — 后台分析 PolicyEffectLedger
- A/B 策略实验 — shadow mode 对比

### P2-2: Policy Experiments
- 影子实验框架 — 同一信号两个策略并行评估
- 实验结果 → 策略升级

### P2-3: Skill Lifecycle
- Skill 创建 → 验证 → 推广 → 废弃完整生命周期
- 个人 Skill → 群组 Skill → 系统 Skill 升级路径

### P2-4: Learning Base
- 策略学习基础设施 — 可复用的学习算法
- Bayesian 更新 + 规则混合

### P2-5: Relationship Model
- 用户-AI 关系建模 — trust level / interaction style / correction frequency
- 关系状态影响策略选择

---

## P3: General Goal OS Layer（通用目标 OS 层）

**目标**: 从考试冲刺泛化到任何目标

### P3-1: GoalWorldGraph Generalization
- Galaxy 泛化: exam → any goal type
- Domain Pack: 每个领域一套策略模板
- Multi-Goal Arbitration: 多目标时优先级裁决

### P3-2: Growth Chronicle
- 用户共治成长叙事
- 里程碑 → 故事线 → 洞察

### P3-3: External Integrations
- Calendar → AI context
- 3rd party tools → task execution

---

## P4: Research-Grade

- Counterfactual evaluation: "如果没干预会怎样"
- User Simulator: 合成用户测试策略效果
- Domain Pack Marketplace: 用户贡献领域策略

---

## 工程契约

### Spine Contract（每个新功能必须满足 12 点）

1. Signal 必须有且仅有一个 Policy 规则消费
2. Directive 必须有下游消费者
3. Audit 必须验证输出满足约束
4. Receipt 必须短、具体、可纠正
5. CausalTrace 必须记录完整链路
6. Outcome 必须记录干预结果
7. Kill switch 必须支持 off/shadow/live
8. 不写长期人格 (scope ≤ current_sprint)
9. 社群信号不直接写个人状态
10. 成就不直接改长期人格
11. 用户纠正 = 高置信度 claim
12. 所有参数有合理默认值

### Definition of Done（10 条）

1. [ ] CausalTrace 完整记录 signal → directive → outcome
2. [ ] UserVisibleReceipt 用户可见
3. [ ] DirectiveApplicationAudit 验证通过
4. [ ] 单元测试覆盖（每个方法至少 1 个 test）
5. [ ] E2E 测试覆盖关键路径
6. [ ] Kill switch 支持 off/shadow/live
7. [ ] 零 TODO/FIXME
8. [ ] 无安全漏洞（OWASP top 10）
9. [ ] 文档更新（progress doc）
10. [ ] Opus review 通过

---

## 执行顺序 (P1)

```
P1-1: Causal Timeline UI
  ├── TimelineCardRenderer (compact/expanded)
  ├── 用户纠正动作集成
  └── 验收: "为什么给我这个任务" 完整可追溯
      ↓
P1-2: Source Tray + SourceAsset Wrapper
  ├── SourceTray UI 组件
  ├── RetrievalDirective 集成
  └── 验收: 用户可控资料上下文
      ↓
P1-3: Aurora Wake + Core Session v1
  ├── Session lifecycle
  └── 验收: 完整 goal→plan→execute→reflect 周期
      ↓
P1-4: CommunityDirective v1
  ├── cohort_mistake 循环
  ├── partner_observation 循环
  └── resource_quality 循环
      ↓
P1-5: SkillDirective v1
  ├── Skill inject/recommend/extract
  └── worked-example-repair TCP
      ↓
P1-6: Goal-Respectful Recall v1
  ├── Notification 消费端
  └── 冷却期 + 偏好
```

---

## 12 North Star Metrics

| # | 指标 | 目标 | 测量方式 |
|---|------|------|---------|
| 1 | 7-day exam pass rate | ≥80% | 考后用户自报 |
| 2 | Task completion rate | ≥70% | completed / assigned |
| 3 | Signal→Directive conversion | ≥60% | DRS metrics |
| 4 | User correction rate | 5-15% | receipts with correction |
| 5 | Skill extraction rate | ≥1 per user per week | SkillEntry count |
| 6 | Recall engagement | ≥40% | recall → action rate |
| 7 | Community signal quality | ≥70% positive | cohort feedback |
| 8 | Causal trace coverage | ≥90% | traces with full chain |
| 9 | Goal achievement rate | ≥50% at 30 days | goal.status = completed |
| 10 | Session completion | ≥60% | full cycle / started |
| 11 | Self-correction rate | ≥10% | outcome attribution cycles |
| 12 | User satisfaction (NPS) | ≥40 | in-app survey |

---

*每次 stage 完成后更新此文档和 progress doc*
