# Stage 30 Metacognition Extension — 前置理论与代码探索研究报告

> **Version**: 2.0 (终稿, 经自审修正)
> **Date**: 2026-04-21
> **Author**: Chief Architect Research Pre-scan
> **Status**: Final — 供 dispatch plan 设计参考
> **Scope**: 理论前沿、代码约束、架构建议、风险清单

---

## 0. 自审修正声明

初稿 (v1.0) 存在 7 个需要修正的问题，终稿中已全部处理：

| # | 初稿问题 | 修正 |
|---|---------|------|
| 1 | DeviationDetector 扩展方案过于简化 | 改为独立计算逻辑，不与 PersDyn attractors 共享管道 (§3.5) |
| 2 | JOL/EOL/FOK 作为 Stage 30 实现目标 | 降级为理论参考，标注为"需 UI 扩展的未来阶段" (§1, §2) |
| 3 | prompts.py 元认知空白描述不精确 | 区分"内容层指令"(已有) vs "过程层支架"(缺失) (§3.6) |
| 4 | ScaffoldingFSM 双重叠加冲突未识别 | 增加 delta 范围约束：metacognition 调节 ±0.5 而非 ±1 (§3.4) |
| 5 | 缺少 kill switch / DLQ / metrics 工程要求 | 参照 Stage 29 完整模式补充 (§3.7) |
| 6 | 与 SufficiencyJudge 边界未定义 | 明确划分 (§3.8) |
| 7 | 冷启动过度依赖 traits_prior | 改为 sample_size < 5 时 bias = "unknown"，不做路由 (§3.2) |

---

## 1. 理论框架推荐

### 推荐框架: Winne & Hadwin COPES + Nelson-Narens 元认知监控 (混合)

**选择理由**: Sparkle 已有 Zimmerman 三阶段 SRL 追踪器 (Stage 29)，其 Forethought → Performance → Self-Reflection 直接对齐 Winne & Hadwin 的四阶段模型 (差别仅为 Winne & Hadwin 将 Forethought 拆为 task perception + goal setting)。Zimmerman 模型的短板在于**没有形式化元认知监控本身**——它描述学习者在哪个阶段，但不描述学习者对自己认知过程的监控质量。

Nelson & Narens (1990) 的 Object-Level / Meta-Level 架构补位：

```
Meta-Level (元认知监控 + 控制)
    ↕ monitoring: Object → Meta (观察自己的认知状态)
    ↕ control: Meta → Object (调整自己的认知策略)
Object-Level (认知操作: 学习、计划、执行任务)
```

**关键映射到 Sparkle**:

| Nelson-Narens 概念 | Sparkle 工程对应 | 数据来源 |
|---|---|---|
| 监控信息流 (Object → Meta) | 用户对自己能力的判断 vs 实际表现 | `Task.due_date` vs `Task.completed_at` |
| 控制信息流 (Meta → Object) | AI 根据元认知信号调整支持策略 | `DualCoreRouter.cognitive_adjustments` |
| 元认知准确性 | calibration_bias (overconfident / underconfident / calibrated) | 新计算 |
| 元认知策略知识 | 用户是否主动调整学习策略 | `plan.created` 频率 + `task.abandoned` 后续行为 |

**Nelson-Narens 的 JOL/EOL/FOK 三层判断模型** (Judgment of Learning, Ease of Learning, Feeling of Knowing) 在理论上完美，但 Stage 30 **不能直接实现**，原因：
- JOL/EOL/FOK 都需要用户主动提供自我评估 ("我觉得这个内容掌握了 80%")
- Sparkle 目前没有任何收集用户自我评估的 UI 机制或对话意图
- 这需要在 Flutter 层新增"置信度收集"组件，属于跨边界 L3 变更

**Stage 30 的实现策略**: 用**行为代理指标** (behavioral proxies) 替代直接自我报告，通过可观测行为推断元认知状态。这是 learning analytics 领域 2024-2025 的主流方法 (Frontiers in Education, 2025 系统综述确认)。

### 辅助理论: Butler & Winne 反馈模型

Sparkle 的 `DualCoreRouter` 已工程实现了 Butler & Winne 模型的"外部反馈 → 元认知监控 → 认知操作"路径。2024-2025 研究一致证实 GAI 聊天机器人可在对话中支架 SRL (Journal of Learning Analytics, 2024; ScienceDirect, 2025)。Stage 30 的元认知扩展是在已有反馈架构上的精度提升，而非从零建设。

---

## 2. 可观测信号清单

### 2.1 可立即使用的信号 (Stage 30 核心实现范围)

| 信号 | 含义 | Sparkle 数据源 | 计算方法 | 注意事项 |
|------|------|---------------|---------|---------|
| **计划-执行差距** | 时间估算 vs 实际完成时间 | `Task.due_date` vs `Task.completed_at` | `Σ|actual - planned| / N` 滚动14天 | 高估时间 (underconfident) vs 低估时间 (overconfident) 方向性重要 |
| **任务放弃率** | abandoned / total 比率 | `TaskStatus.ABANDONED` vs 全部任务 | 14天滚动比率 | 高放弃率可能是元认知规划失败的信号 |
| **专注完成率** | FocusSession COMPLETED / 总数 | `FocusSession.status` | 14天滚动比率 | 频繁中断专注 = 可能高估了自己的专注能力 |
| **计划修正频率** | plan.created + plan.updated 节奏 | EventBus `plan.created` 事件 | 14天内次数 | 适度修正 = 好的元认知; 零修正或过度修正 = 值得关注 |
| **复盘频率** | 反思类记忆的数量 | `EpisodicMemory.source_type == "reflection"` | 14天计数 | 已有 `recent_reflections` aggregator 字段 |
| **求助时机** | 用户向 AI 求助 vs 独立完成的节奏 | `ChatSession` 时间戳 + `Task` 状态变化 | 需跨表关联：同一 task 前后是否有 chat session | 不是简单的"问得多=差"——好学者在卡住时求助，差的要么不求助要么过度依赖 |

### 2.2 需要未来扩展的信号 (Stage 30 以后)

| 信号 | 为什么需要扩展 |
|------|-------------|
| **JOL 自评准确度** | 需要新增"用户自我评估"UI 或对话意图 |
| **元认知语言特征** | 需要在 ChatMessage 内容上加 NLP 检测层 ("我不确定"/"让我想想") |
| **复习间隔规律性** | `StudyRecord` + `UserNodeStatus` 存在但跨节点间隔分析需新逻辑 |
| **策略调整意识** | 需要新增"用户主动改变学习方法"的意图识别 |

---

## 3. 实现架构建议

### 3.1 核心定位: SRL 的同层 peer 服务

**不做 SRL 子模块**。`SRLPhaseTrackerService` 是独立文件、独立 EventBus 消费者。`MetacognitionMonitorService` 应采用完全相同的架构模式——peer 服务而非嵌套子模块。

```
backend/app/services/
├── srl_phase_tracker_service.py         # Stage 29 (已有)
├── metacognition_monitor_service.py      # Stage 30 (新增)
├── aurora_stage29_srl_kill_switch_service.py   # Stage 29 (已有)
├── aurora_stage30_metacognition_kill_switch_service.py  # Stage 30 (新增)
```

**理由**:
- 解耦: 两个服务独立消费 EventBus，互不依赖
- 可独立 kill switch: Rule AO 要求元认知反馈可独立关闭
- 遵循 Stage 29 建立的模式，减少架构认知负担

### 3.2 核心数据模型

```python
class MetacognitionSnapshot(BaseModel):
    user_id: UUID
    overall_score: float            # [0, 1], 综合元认知能力代理
    calibration_bias: str           # "overconfident" | "underconfident" | "calibrated" | "unknown"
    calibration_magnitude: float    # [0, 1], 偏差幅度
    dominant_gap: str | None        # 过程性描述 (Rule AO 合规)
    strategy_adjustment_count_14d: int
    task_completion_predictability: float  # [0, 1], 计划-实际一致性
    sample_size: int
    confidence: float               # 估计置信度
    evidence_ids: list[str]
    computed_at: datetime
```

**冷启动规则** (修正初稿的过度依赖问题):
- `sample_size < 5`: `calibration_bias = "unknown"`, `confidence = 0.0`, **不做路由调整**
- `sample_size >= 5`: 开始计算 calibration，但 `confidence = max(0.3, min(0.85, sample_size / 20))`
- **不用 `traits_prior` (Big Five) 作为校准先验**: conscientiousness 与元认知校准仅弱相关 (r ≈ 0.2-0.3)，作为先验会引入系统性偏差

### 3.3 EventBus 集成

```python
# MetacognitionMonitorService 消费以下已有事件 (不发新事件):
CONSUMED_EVENTS = {
    "task.completed",           # → 计算计划-实际差距
    "task.feedback_submitted",  # → 记录取助模式
    "task.abandoned",           # → 更新放弃率
    "focus.completed",          # → 更新专注完成率
    "plan.created",             # → 更新计划修正频率
}

# 可选新增 (Stage 30 后期):
# "metacognition.snapshot.generated"  → 下游消费者 (Aggregator, Router) 订阅
```

遵循 Stage 29 模式:
- `STREAM_NAME = "sparkle_events"`
- `GROUP_NAME = "metacognition_monitor"`
- DLQ + retry (3 次重试后进入 dead letter)
- 本地锁 + 分布式锁双重保护
- Prometheus metrics: `META_EVENT_CONSUMED_TOTAL`, `META_DLQ_SIZE`, `META_EVENT_LAG_P95`

### 3.4 ScaffoldingFSM 交互 (注意叠加冲突)

**问题**: `resolve_support_level` 已在 SRLPhase 为 FORETHOUGHT/SELF_REFLECTION 时 +1 support_level。如果 metacognition 再叠加 ±1，可能导致 support_level 在高元认知差距时被推到 4 (最大值)，形成过度支持。

**解决方案**: Metacognition 调节作为**二次微调**而非并行调节:

```python
# resolve_support_level 的扩展:
# SRL phase delta: ±1 (已有)
# Metacognition delta: ±0.5 (新增, 仅在 SRL delta = 0 时生效)

# 即:
# - SRL phase 已调整时 → metacognition 不额外调整 (避免双重推高)
# - SRL phase 未调整时 (PERFORMANCE 阶段) → metacognition 可微调 ±0.5
```

### 3.5 DeviationDetector 扩展 (修正初稿)

**初稿错误**: 建议将 calibration_bias 作为新维度插入 `DeviationDetector`。

**实际情况**: `DeviationDetector.detect()` 接受 `attractors: dict[str, AttractorState]`，这些 attractor 来自 `PersDynAttractorService` 的 EMA 计算管道 (baseline, variability_14d_stddev, recovery_rate_slope)。校准信号的数据源 (Task 时间戳) 和计算模式 (均值偏差) 与人格动力学 attractor 完全不同。

**正确方案**: 不修改 `DeviationDetector`。在 `MetacognitionMonitorService` 内部实现独立的偏差检测:

```python
# 内部方法, 不与 PersDyn/DeviationDetector 共享管道:
def _detect_calibration_deviation(self, snapshot: MetacognitionSnapshot) -> Deviation | None:
    if snapshot.calibration_bias == "unknown":
        return None
    # 使用简单的阈值检测, 而非 z-score (样本量通常不够 z-score 的正态假设)
    if snapshot.calibration_magnitude > 0.3:
        return Deviation(
            dim="metacognition_calibration",
            current_value=snapshot.calibration_magnitude,
            baseline=0.0,  # 理想校准
            z_score=0.0,   # 不使用 z-score
            direction="above" if snapshot.calibration_bias == "overconfident" else "below",
            projected_3d=0.0,  # 不做轨迹投影 (数据不够)
            confidence=snapshot.confidence,
        )
    return None
```

如果偏差检测结果需要进入 `ForesightSnapshot`，应作为 `existing_predictions` 的一部分注入，而非混入 `deviations` tuple (后者语义绑定到 PersDyn attractor)。

### 3.6 Prompts 集成: 内容层 vs 过程层

**现状分析** (`prompts.py`):
- **已有** (内容层): "加入复盘与纠错机制" (L638), "评估标准" (L635), "复盘连续 N 天" (L2330)
- **已有** (半元认知): `recent_reflections` aggregator 字段 → 会渲染到 context
- **缺失** (过程层支架): 没有任何 prompt 片段引导 AI 帮助用户反思自己的认知过程本身

**新增内容** (过程层支架, Rule AO 合规):

```python
# 在 prompts.py 的 companion 指令段新增 (仅当 metacognition 条件触发时注入):
METACOGNITION_STANZA = """
## 元认知过程引导
- 不要告诉用户"你的元认知能力较低"——这是诊断性标签 (Rule AO 禁止)
- 而是用提问引导用户反思: "你觉得这个时间预估合理吗？" "上次类似任务实际花了多久？"
- 当检测到用户高估自己时，提供具体的对比数据而非评判: "上次这个阶段你预估了 2 小时，实际用了 3.5 小时"
- 当检测到用户低估自己时，提供具体的成功证据: "过去两周你在 X 类任务上的完成率是 85%，比你预期的要高"
"""
```

### 3.7 Kill Switch 模式

严格遵循 Stage 29 的 `AuroraStage29SRLKillSwitchService` 模式:

```python
class AuroraStage30MetacognitionKillSwitchService:
    # 两级开关:
    # - mode: "on" | "off" | "shadow" (shadow = 计算但不输出)
    # - monitor_mode: "on" | "off"

    # 与 Stage 29 的 tracker_mode 对称
    # Redis key: "aurora:stage30:kill_switch:{user_id}"
    # 默认: mode="shadow", monitor_mode="on" (安全启动)
```

### 3.8 与 SufficiencyJudge (Stage 22) 的边界

| 维度 | SufficiencyJudge (Stage 22) | MetacognitionMonitor (Stage 30) |
|------|---------------------------|--------------------------------|
| **问题** | "当前对话有足够信息执行任务吗？" | "用户对自己能力的判断准确吗？" |
| **时间尺度** | 当前对话轮次 | 14天滚动窗口 |
| **输入** | `CurrentTurnParseResult` + `UserStateV1` | 历史任务完成数据 |
| **输出** | `task_sufficiency_score` + `missing_dimensions` | `calibration_bias` + `dominant_gap` |
| **路由影响** | 影响信息收集 vs 执行的决策 | 影响支持强度和反馈风格的决策 |

**关键区分**: SufficiencyJudge 是**情境性的** (situational)，MetacognitionMonitor 是**发展性的** (developmental)。两者不应合并。

### 3.9 Aggregator 字段

```python
# UserStateFieldName 新增:
"metacognition_summary"

# 值类型:
@dataclass(frozen=True)
class MetacognitionSummaryValue:
    overall_score: float                    # [0, 1]
    calibration_bias: str                   # "overconfident" | "underconfident" | "calibrated" | "unknown"
    calibration_magnitude: float            # [0, 1]
    dominant_gap: str | None                # 过程性描述
    strategy_adjustment_count_14d: int
    task_completion_predictability: float    # [0, 1]
    sample_size: int
    confidence: float

# TTL: 300s (与 achievement_summary 同级, 因为元认知变化缓慢)
```

### 3.10 DualCoreRouter 扩展

```python
# DualCoreRoutingInput 新增:
metacognition_calibration_bias: str | None = None   # 4 种值, unknown 时不影响路由
metacognition_overall_score: float | None = None    # [0, 1], confidence > 0.3 时才使用
```

路由逻辑 (仅当 calibration_bias != "unknown"):
- `overconfident` + `execution_first` → cognitive_adjustments: "在推进前，先验证用户对当前理解的准确度"
- `underconfident` + `cognitive_first` → cognitive_adjustments: "用户倾向低估自己，提供具体的已完成证据来校准信心"
- `overconfident` + 当前无 active plan → execution_constraints: "建议用户先做一个更小范围的试运行来校准时间预估"

---

## 4. 关键风险与缓解

### 4.1 Rule AO 合规 (最高优先级)

Rule AO: "Metacognition 组件不得输出诊断性标签，只允许生成过程性反馈。"

**红线清单**:
- **禁止**: "你的元认知能力较低", "你缺乏自我监控意识", "你的学习策略有问题"
- **允许**: "你的计划-执行差距在过去两周扩大了", "上次这个阶段你预估了 2 小时，实际用了 3.5 小时", "过去两周你没有主动调整过学习计划"

**工程保障**:
- `calibration_bias` 和 `calibration_magnitude` 永远不直接渲染到用户可见的 prompt
- 所有用户可见反馈必须通过 prompts.py 的 `METACOGNITION_STANZA` 模板生成
- Kill switch 可独立关闭元认知反馈层，不影响其他系统

### 4.2 元认知过载

过多元认知提示会干扰学习过程本身。

**缓解**:
- 每个对话轮次最多 1 条元认知相关提示 (硬限制)
- 元认知提示频率受 ScaffoldingFSM support_level 调控: support_level ≥ 3 时才输出
- 用户可通过 `UserPreferencesCenter` 关闭元认知反馈 (默认关闭, 遵循 Aurora 默认-OFF 原则)

### 4.3 AI 过度辅助 / 认知卸载

2024-2025 研究明确警告 (SAGE 2025; EDUCAUSE Review 2025; ScienceDirect 2026):
- GenAI 工具允许学生外包计划、监控、评估等元认知过程，长期可能削弱自主学习能力
- "更好的结果, 更差的思维"悖论: AI 产出的答案更好，但学生的思维能力在退化
- **Scaffolding withdrawal 问题**: 一项研究显示，使用 AI 辅助的学生在练习测试中多答对了 48%，但 AI 移除后表现下降

**缓解**:
- 元认知反馈采用**提问式**而非指令式: "你觉得这个时间预估合理吗？" 而非 "你的时间预估偏短"
- 保留 productive struggle 空间: 检测到用户正在独立思考 (ChatSession 中长时间间隔后发送较长内容) 时，延迟或抑制元认知干预
- 元认知能力本身就是抵御 AI 过度依赖的主要防线 (Structural Learning, 2025)。Stage 30 的设计目标不是替代用户的元认知过程，而是让用户**意识到**自己的认知模式

### 4.4 数据稀疏与低活跃用户

**缓解** (修正初稿):
- `sample_size < 5`: 不做任何路由调整，不输出任何元认知提示
- `sample_size >= 5 但 < 10`: 输出提示但 confidence 封顶 0.5
- 不使用 Big Five traits_prior 作为校准先验 (弱相关，r ≈ 0.2-0.3)

### 4.5 SRLPhaseTracker 与 MetacognitionMonitor 的时序依赖

两者都消费 EventBus 的 `task.completed` 等事件。如果 SRLPhaseTracker 先处理事件导致 phase 转换，而 MetacognitionMonitor 依赖当前 phase 来计算元认知信号，可能出现时序不一致。

**缓解**: MetacognitionMonitor 不依赖实时 SRL phase。它使用 `StateAggregator` 缓存的 `srl_phase` 字段 (TTL 30s-24h)，而非直接监听 SRL phase 转换事件。

---

## 5. 推荐阅读

1. **Wang et al. (2024)** — "Metacognitive Prompting Improves Understanding in Large Language Models" [NAACL 2024](https://arxiv.org/abs/2308.05342)
   - 关键发现: MP 持续优于 Chain-of-Thought，提供可操作的提示策略设计参考
   - 对 Stage 30 的价值: 验证"提问式元认知支架"的有效性

2. **Frontiers in Education (2025)** — "AI-powered Learning Analytics for Metacognitive and Socioemotional Development" [全文](https://www.frontiersin.org/journals/education/articles/10.3389/feduc.2025.1672901/full)
   - 关键发现: 2025 系统综述，确认 AI 驱动的学习分析可促进元认知发展
   - 对 Stage 30 的价值: 证实行为代理指标方法的主流地位

3. **ScienceDirect (2026)** — "Self-Regulation and Overreliance on Artificial Intelligence" [链接](https://www.sciencedirect.com/science/article/pii/S0747563226000828)
   - 关键发现: 过度依赖 AI 损害自主问题解决和自我调节能力
   - 对 Stage 30 的价值: 定义安全边界，指导 kill switch 设计

4. **Bellwether Education (2025)** — "Productive Struggle: How AI Is Changing Education" [链接](https://bellwether.org/publications/productive-struggle/)
   - 关键发现: AI 能力与学习所需的认知摩擦之间的张力
   - 对 Stage 30 的价值: 指导"何时干预/何时退后"的设计决策

5. **PMC/NIH (2025)** — "Metacognitive Sensitivity: The Key to Calibrating Trust and Optimal AI Use" [链接](https://pmc.ncbi.nlm.nih.gov/articles/PMC12103939/)
   - 关键发现: AI 表达置信度的方式会改变人类对 AI 输出的信任校准
   - 对 Stage 30 的价值: Sparkle 反馈的呈现方式本身会影响用户的元认知校准

6. **Computers & Education: AI (2025)** — "Analytics of Self-Regulated Learning Strategies and Scaffolding" [链接](https://www.sciencedirect.com/science/article/pii/S2666920X25000505)
   - 关键发现: 目标设定等元认知策略的计算分析方法
   - 对 Stage 30 的价值: 提供具体的行为信号到元认知推断的映射方法

7. **Heliyon / Cell Press (2024)** — "Contribution of Metacognitive Questions to Accuracy of Judgment of Learning" [链接](https://www.cell.com/heliyon/fulltext/S2405-8440(24)16086-0)
   - 关键发现: 元认知支持显著提升 JOL 准确性
   - 对 Stage 30 的价值: 直接验证"提问式支架"优于"告知式反馈"

8. **EDUCAUSE Review (2025)** — "The Paradox of AI Assistance: Better Results, Worse Thinking" [链接](https://er.educause.edu/articles/2025/12/the-paradox-of-ai-assistance-better-results-worse-thinking)
   - 关键发现: AI 产出更好结果但可能削弱思维能力
   - 对 Stage 30 的价值: 强化"默认-OFF + 用户主动启用"的设计原则

---

## 6. 与 Stage 29 的衔接

Stage 29 的 `SRLPhaseTracker` 追踪 Zimmerman 三阶段。元认知监控是 SRL 每个阶段**内部**的监控子过程，不是并行的第四阶段：

```
SRLPhase.FORETHOUGHT (Stage 29 追踪的外部阶段)
  └── 元认知子过程: "这个任务对我有多难？" (EOL 判断的代理)
      └── 可观测信号: 计划时间估算的准确性

SRLPhase.PERFORMANCE (Stage 29 追踪的外部阶段)
  └── 元认知子过程: "我现在做得怎么样？" (JOL 判断的代理)
      └── 可观测信号: 专注完成率 + 任务放弃率

SRLPhase.SELF_REFLECTION (Stage 29 追踪的外部阶段)
  └── 元认知子过程: "我之前的预测准确吗？" (校准评估)
      └── 可观测信号: 计划-实际差距 + 策略调整频率
```

**数据流**:

```
EventBus 事件 (task.completed, focus.completed, ...)
    │
    ├──→ SRLPhaseTrackerService (Stage 29, 已有)
    │         ↓ SRLPhaseState
    │         → StateAggregator._build_srl_phase_summary
    │
    └──→ MetacognitionMonitorService (Stage 30, 新增, 独立消费者)
              ↓ MetacognitionSnapshot
              → StateAggregator._build_metacognition_summary (新增字段)
                    ↓
              DualCoreRouter (新增 calibration_bias 输入)
                    ↓
              ScaffoldingFSM (新增 ±0.5 微调, 仅在 SRL delta = 0 时)
                    ↓
              Prompts (新增 METACOGNITION_STANZA, 过程层支架)
```

**关键约束**:
- MetacognitionMonitorService 遵循 EventBus 解耦模式 (Rule AN)
- 实现 `AuroraStage30MetacognitionKillSwitchService` (两级开关: mode + monitor_mode)
- 默认 mode = "shadow" (计算但不输出)，遵循 Aurora 默认-OFF 原则
- Dispatch plan §0 必须包含: Phase 映射、7-phase growth loop 定位 (主要服务于 Reflect + Adapt)、Rule 审查 (特别是 Rule AO + Rule AN)、Path B/C fallback

---

## 7. Stage 30 Dispatch Plan 准备清单

基于本研究的发现，dispatch plan 应包含以下模块:

| 模块 | 估计范围 | 依赖 |
|------|---------|------|
| `metacognition_monitor_service.py` | 核心服务 | EventBus, PG, Redis |
| `aurora_stage30_metacognition_kill_switch_service.py` | Kill switch | Redis |
| `metacognition_schema.py` | 数据模型 | Pydantic |
| `state_aggregator/schema.py` 扩展 | 新增字段 | Aggregator |
| `state_aggregator/service.py` 扩展 | `_build_metacognition_summary` | MetacognitionMonitorService |
| `dual_core_router.py` 扩展 | 2 个新输入字段 | - |
| `scaffolding_fsm.py` 扩展 | ±0.5 微调逻辑 | - |
| `prompts.py` 扩展 | METACOGNITION_STANZA | - |
| Prometheus metrics | 3-4 个新指标 | - |
| 单元测试 | 至少 5 个核心测试用例 | - |

---

*End of Report*
