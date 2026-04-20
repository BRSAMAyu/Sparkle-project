# SGW v2 核心抽象定义

> 版本: 1.1 | 日期: 2026-04-21 | 状态: FROZEN (审查修订版)
> 这些抽象是所有 Phase 的代码契约，实现可以迭代，接口不允许破坏性变更。

---

## 1. ScenarioSpec（测试场景规格）

**职责**：参数化描述一次测试要验证什么。当前硬编码在 `sgw_orchestrator.py` 中的 Stage 16 Rule Y 逻辑，将抽象到此接口。

```python
@dataclass
class ScenarioSpec:
    scenario_id: str              # "stage_16_rule_y" | "stage_17_social" | ...
    version: str                  # 语义版本
    description: str              # 人类可读描述

    # 被测系统接口
    target_endpoints: dict        # {ws_url, api_base_url, grpc_target}
    data_contracts: list[str]     # 相关 proto / API 契约引用

    # 硬违规规则
    compliance_rules: list[ComplianceRule]

    # 真实性评估维度
    authenticity_dims: list[AuthenticityDimension]

    # Persona 轴约束（本场景需要什么类型用户）
    persona_axis_constraints: PersonaAxisConstraints

    # 红队场景
    adversarial_playbook: str     # playbook 文件路径

    # 验收标准
    acceptance_criteria: AcceptanceCriteria

    # 运行时参数
    runtime_config: dict          # wall_clock_hours, min_sessions, etc.
```

**当前映射**：`OrchestratorConfig` (L98-142) + `hard_violation_rules.py` + 验收逻辑 (L1415-1448)

**扩展点**：Stage 17 新建一个 `scenario_stage_17.yaml` 即可复用全部基础设施。

---

## 2. PersonaAxes（三轴连续分布）

**职责**：替换当前 `persona_library.json` 的离散标签（44个固定 persona），改为从连续分布采样。

```python
@dataclass
class PersonaSample:
    """一次采样的具体 persona 实例（不是静态定义）"""
    sample_id: str                # 唯一标识（确定性种子生成）
    seed_persona_id: str | None   # 来源种子 persona（可为 None）

    # 三轴采样值
    behavior: BehaviorAxis
    narrative: NarrativeAxis
    expression: ExpressionAxis

    # 确定性种子（可复现）
    rng_seed: int


@dataclass
class BehaviorAxis:
    """行为轴：用户怎么和 AI 互动"""
    compliance: float             # 0-1, 对 AI 建议的遵从度
    digression_rate: float        # 0-1, 跑题概率
    challenge_tendency: float     # 0-1, 质疑/挑战倾向
    responsiveness: float         # 0-1, 对 AI 回复的反应紧密度
    emotion_intensity: float      # 0-1, 情绪表达强度


@dataclass
class NarrativeAxis:
    """叙事轴：session 内的剧情走向"""
    opening_motivation: str       # "考试失利" | "兴趣探索" | "职业困惑" | ...
    arc_shape: str                # "rising" | "oscillating" | "decline_then_recovery" | ...
    topic_jump_probability: float # 0-1, 话题跳转概率
    beats: list[ConversationBeat] # 剧情节点列表


@dataclass
class ExpressionAxis:
    """表达轴：用户怎么说话"""
    sentence_length: str          # "short" | "medium" | "long"
    colloquialisms: list[str]     # 口头禅/方言特征
    emoji_rate: float             # 0-1
    typo_rate: float              # 0-1, 错别字/笔误概率
    code_switch_rate: float       # 0-1, 中英混杂概率


@dataclass
class ConversationBeat:
    """剧情弧的一个节点"""
    beat_id: str
    turn_range: tuple[int, int]   # (start, end) turn index
    emotional_vector: str         # "低落" | "好奇" | "焦虑" | "振奋" | ...
    topic_hint: str               # 话题方向提示（不是逐句脚本）
    allow_skip: bool              # 是否允许跳过此 beat
    transition_triggers: list[str]  # 触发转移到下一 beat 的条件
```

**当前映射**：
- `persona_library.json` 的 44 条 → `seed_persona_id`
- `turn_requirements` (L1239-1257) 的 `turn_index % N` → `ConversationBeat`
- `mention_density` / `commitment_density` → `BehaviorAxis`

**关键设计决策**：
- 44 个 persona 退化为"种子约束"——确定三轴分布的均值和方差
- 实际每 session 从分布独立采样 → 样本空间从 44 扩到 ~5000+ 组合
- 三轴可正交实验（控其他只调一轴），这是归因的基础

---

## 3. TurnDecision（每轮对话方向决策）

**职责**：替换 `_build_turn_requirements()` 的机械规则，由 state machine 根据对话上下文输出。

```python
@dataclass
class TurnDecision:
    """State machine 输出的 '下一步做什么方向' """
    direction: str                # "回应建议" | "追问细节" | "表达感受" |
                                  # "切换话题" | "提出质疑" | "确认接受" | ...
    target_reference: str | None  # 应该引用 AI 回复中的哪部分（None = 自由发挥）
    emotional_tone: str           # "平静" | "焦虑" | "好奇" | "烦躁" | ...
    must_include: list[str]       # 必须包含的元素 ["mention_person", "time_anchor", ...]
    must_avoid: list[str]         # 必须避免的元素 ["empty_acknowledgment", "list_format", ...]

    # 元信息（不传给表达层 LLM，只记录到 DB）
    source: str                   # "state_machine" | "beat_transition" | "adversarial_strategy"
    confidence: float             # state machine 对此决策的置信度
```

**当前映射**：`_build_turn_requirements()` (L1239-1257) → 整个方法替换

**State Machine 输入**：
```
输入: (current_beat, last_ai_behavior_class, turn_index, persona_axes_sample)
输出: TurnDecision
```

**AI 行为分类**（对 AI 回复打标签）：

**关键设计决策：Phase 2 的 AIBehaviorClass 分类是 rule-based 的，不是 LLM 驱动的。**

理由：
1. 每轮额外调用 LLM 做分类会使 rate limit 压力翻倍（14000+ → 19000+ calls/run）
2. 分类结果用于 state machine 转向，不需要完美的语义理解
3. rule-based 可以做到 80%+ 准确率，足够驱动对话方向

```python
class AIBehaviorClass(str, Enum):
    GIVE_ADVICE = "give_advice"       # 给了具体步骤/建议
    ASK_QUESTION = "ask_question"     # 问了一个问题
    ENCOURAGE = "encourage"           # 夸奖/鼓励
    CONFIRM = "confirm"               # 确认/总结
    MISUNDERSTAND = "misunderstand"   # 误解用户意图
    REFUSE = "refuse"                 # 拒绝请求
    DIVERGE = "diverge"               # 话题发散
    NEUTRAL = "neutral"               # 中性回复
```

**Rule-based 分类器规则**（优先级从高到低，命中即返回）：

```python
def classify_ai_response(text: str) -> AIBehaviorClass:
    # 1. 问号结尾 → ask_question
    if text.rstrip().endswith("？") or text.rstrip().endswith("?"):
        return AIBehaviorClass.ASK_QUESTION

    # 2. 建议动词模式 → give_advice
    advice_patterns = ["你可以试试", "建议你", "我建议", "推荐", "试试看",
                       "第一步", "第二步", "以下是", "可以这样做", "方法"]
    if any(p in text for p in advice_patterns):
        return AIBehaviorClass.GIVE_ADVICE

    # 3. 鼓励模式 → encourage
    encourage_patterns = ["很棒", "做得好", "加油", "你很", "不错",
                          "继续努力", "相信自己", "很有潜力"]
    if any(p in text for p in encourage_patterns):
        return AIBehaviorClass.ENCOURAGE

    # 4. 拒绝模式 → refuse
    refuse_patterns = ["我不能", "无法", "不好意思", "抱歉，这个"]
    if any(p in text for p in refuse_patterns):
        return AIBehaviorClass.REFUSE

    # 5. 确认模式 → confirm
    confirm_patterns = ["好的，", "我理解", "总结一下", "所以你"]
    if any(p in text for p in confirm_patterns):
        return AIBehaviorClass.CONFIRM

    # 6. 长回复无以上特征 → neutral
    # 7. 默认 → neutral
    return AIBehaviorClass.NEUTRAL
```

**Fallback 机制**：如果 state machine 置信度 < 0.5（例如 neutral 分类），TurnDecision 退回 `beat` 定义的默认方向，不做激进转向。这避免了分类错误导致级联对话质量下降。

---

## 4. AuditReport（评估报告，拆成两条线）

**职责**：拆分当前混合的 5 维审计为两条独立评分线。

### 4.1 ComplianceAudit（合规审计，沿用当前 5 维）

```python
@dataclass
class ComplianceAuditResult:
    audit_id: str
    target_record_id: str
    dimensions: dict[str, float]  # {metadata_correctness, semantic_fidelity,
                                  #  entity_boundary, time_anchor_validity,
                                  #  confidence_calibration}
    overall: float
    is_soft_violation: bool       # overall < 0.85
    reason: str
    audit_model: str              # 使用的审计模型
    audit_provider: str           # 使用的提供商
```

**当前映射**：`_run_audit()` (L990-1061) + `audit_system_prompt.md` → 沿用

### 4.2 AuthenticityAudit（真实性审计，新增）

```python
@dataclass
class AuthenticityAuditResult:
    audit_id: str
    session_id: str
    dimensions: dict[str, float]  # {conversational_responsiveness,
                                  #  persona_consistency,
                                  #  arc_progression,
                                  #  emotional_authenticity,
                                  #  linguistic_naturalness}
    overall: float
    is_authentic: bool            # overall >= 0.7
    failure_patterns: list[str]   # 具体问题列表
    audit_model: str
    audit_provider: str
```

**新增**：对完整 session 做整体评估，不只评单条 memory 记录。

---

## 5. DiagnosticHypothesis（归因假设）

**职责**：Diagnostic Agent 的输出物，结构化描述一个失败模式的候选原因。

```python
@dataclass
class DiagnosticHypothesis:
    hypothesis_id: str
    created_at: str
    run_id: str

    # 假设内容
    statement: str                # "假设：adversarial persona 在 AI 给建议后，
                                  #  entity_boundary 维度高发违规"
    evidence_refs: list[str]      # 具体的 session_id / turn_id / audit_id
    affected_dimensions: list[str]  # 涉及的审计维度
    affected_persona_axes: dict   # 涉及的 persona 轴范围

    # 候选原因排序
    candidate_causes: list[CandidateCause]

    # 验证方案
    validation_plan: ExperimentPlan

    # 状态
    status: str                   # "proposed" | "testing" | "verified" | "rejected"


@dataclass
class CandidateCause:
    cause_id: str
    description: str
    likelihood: float             # 0-1, 初步判断的可能性
    fix_direction: str            # "adjust_prompt" | "tune_parameter" |
                                  # "fix_backend" | "retrain_model"


@dataclass
class ExperimentPlan:
    experiment_id: str
    hypothesis_id: str

    # 控制变量
    control_config: dict          # 基线配置（config_hash）
    treatment_config: dict        # 实验配置（改了什么）
    controlled_variables: list[str]  # 被控制的变量名
    manipulated_variable: str     # 被操纵的变量名

    # 样本
    sample_size: int              # 每组 session 数
    selection_criteria: dict      # 如何选择样本

    # 停止条件
    min_sessions: int
    max_duration_hours: float
    stopping_criteria: dict       # {metric: threshold}

    # 结果
    status: str                   # "planned" | "running" | "completed"
    result: dict | None           # 统计结果
    conclusion: str | None        # 接受/拒绝假设
```

---

## 6. ExperimentResult（实验结果）

```python
@dataclass
class ExperimentResult:
    experiment_id: str
    completed_at: str

    # 分组指标
    control_metrics: dict[str, float]
    treatment_metrics: dict[str, float]

    # 统计检验
    statistical_test: str         # "t_test" | "mann_whitney" | "permutation"
    p_value: float
    effect_size: float            # Cohen's d
    is_significant: bool          # p < 0.05

    # 切片分析
    slices: list[dict]            # 按维度切片的差分结果

    # 结论
    recommendation: str           # "adopt" | "reject" | "inconclusive"
    confidence: float             # 对此结论的置信度
```

---

## 7. IterationRecord（迭代记录）

```python
@dataclass
class IterationRecord:
    iteration_id: str
    run_id: str
    timestamp: str

    # 触发
    trigger: str                  # "scheduled" | "threshold_exceeded" | "manual"
    trigger_data: dict            # 具体触发条件的数据

    # 假设
    hypotheses_generated: list[str]  # hypothesis_id 列表
    hypothesis_selected: str      # 选择验证的 hypothesis_id

    # 实验
    experiment_id: str
    experiment_result: ExperimentResult | None

    # 决策
    action_taken: str             # "config_updated" | "no_change" | "escalate"
    config_changes: dict          # 具体改了什么参数
    reason: str                   # 为什么做这个决策

    # 多样性检查
    diversity_metrics: dict       # persona 轴覆盖率、AI 行为分布等
    diversity_alert: bool         # 是否有多样性坍缩
```

---

## 8. RunMeta（运行元数据）

```python
@dataclass
class RunMeta:
    run_id: str                   # 唯一运行标识
    scenario_id: str              # ScenarioSpec ID
    config_hash: str              # 配置的确定性哈希
    git_sha: str                  # 当前 git commit
    started_at: str
    ended_at: str | None
    status: str                   # "running" | "completed" | "failed" | "stopped"

    # 配置快照
    scenario_config: dict         # 完整配置（可复现）
    prompt_hashes: dict[str, str] # 各 prompt 文件的哈希
    model_versions: dict[str, str]# 各 LLM 模型版本

    # 摘要指标
    summary: dict                 # sessions, turns, violations, etc.
```

**关键设计**：`config_hash` 保证同一配置可复现。任何 prompt、阈值、persona 定义改动都改变 hash。

---

## 9. 抽象之间的关系图

```
ScenarioSpec
  │
  ├── defines ──→ PersonaAxisConstraints
  │                    │
  │                    └── constrains ──→ PersonaSample
  │                                          │
  │                                          ├── has ──→ BehaviorAxis
  │                                          ├── has ──→ NarrativeAxis
  │                                          │              └── has ──→ ConversationBeat
  │                                          └── has ──→ ExpressionAxis
  │
  ├── defines ──→ ComplianceRule[] ──→ ComplianceAuditResult
  │
  ├── defines ──→ AuthenticityDimension[] ──→ AuthenticityAuditResult
  │
  └── drives ──→ RunMeta
                    │
                    ├── produces ──→ TurnDecision[] ──→ (via StateMachine)
                    │                    │
                    │                    └── feeds ──→ PersonaSample expression
                    │
                    ├── produces ──→ ComplianceAuditResult[]
                    │
                    ├── produces ──→ AuthenticityAuditResult[]
                    │
                    └── triggers ──→ DiagnosticHypothesis
                                        │
                                        └── validated_by ──→ ExperimentPlan
                                                                │
                                                                └── produces ──→ ExperimentResult
                                                                                    │
                                                                                    └── logged_in ──→ IterationRecord
```

---

## 10. 实现优先级

| 抽象 | Phase | 优先级 | 理由 |
|------|-------|--------|------|
| PersonaSample + 三轴 | Phase 2 | P0 | 替换 turn_requirements 的基础 |
| ConversationBeat | Phase 2 | P0 | 剧情弧是反模板化的核心 |
| TurnDecision | Phase 2 | P0 | State machine 输出 |
| ComplianceAuditResult | Phase 3 | P1 | 沿用现有，小幅重构 |
| AuthenticityAuditResult | Phase 3 | P1 | 新增，需要新 prompt |
| RunMeta | Phase 1 | P0 | 可复现性的基础 |
| DiagnosticHypothesis | Phase 4 | P2 | 归因层核心 |
| ExperimentPlan | Phase 4 | P2 | 实验对比的基础 |
| IterationRecord | Phase 4 | P2 | 知识沉淀 |
| ScenarioSpec | Phase 5 | P3 | 通用化抽象 |

---

## 11. RateLimitBudget（速率限制预算）

**职责**：量化每次 SGW run 的 LLM 调用预算，按层分配，确保表达层和审计层互不饿死。

### 11.1 预算估算（单次 18h run，360 sessions × 12 turns）

| 层 | 调用点 | 估算调用数 | 模型 | 提供商 |
|---|--------|-----------|------|--------|
| **表达层** | 生成用户消息 | ~4,320 | glm-4-air / haiku | Zhipu / Anthropic |
| **表达层验证** | 检查 must_include 合规 | ~4,320 | rule-based | **不消耗 LLM** |
| **AI 行为分类** | classify_ai_response | ~4,320 | rule-based | **不消耗 LLM** |
| **Compliance Audit** | 5维评分 | ~500 (12%采样) | glm-4.7 | Zhipu |
| **Authenticity Audit** | 5维评分 (Phase 3) | ~360 (每session 1次) | claude-opus | Anthropic |
| **Diagnostic** | 假设生成 (Phase 4) | ~10 (每100 session 1次) | claude-opus | Anthropic |

**总 LLM 调用**：~5,180（Phase 2）→ ~5,540（Phase 3）→ ~5,550（Phase 4）

**vs 当前**：~5,400 调用。**不增加 LLM 调用总量**。

### 11.2 关键设计决策

1. **AI 行为分类 = rule-based**：不消耗 LLM 调用（见 Section 3）
2. **表达层验证 = rule-based**：检查 must_include 用正则/字符串匹配，不消耗 LLM
3. **表达层换便宜模型**：glm-4-air 或 haiku，吞吐量 5-10x 当前
4. **审计保留强模型**：compliance 用 glm-4.7，authenticity 用 opus
5. **模型/提供商隔离**：表达层和审计层用不同 provider，额度互不影响

### 11.3 预算隔离机制

```python
@dataclass
class RateLimitBudget:
    """每层的独立预算和退避策略"""
    expression: LayerBudget    # 表达层：高吞吐、低精度
    compliance: LayerBudget   # 合规审计：中吞吐、高精度
    authenticity: LayerBudget # 真实性审计：低吞吐、高精度
    diagnostic: LayerBudget   # 归因诊断：极低吞吐、极高精度

@dataclass
class LayerBudget:
    provider: str              # "zhipu" | "anthropic"
    model: str                 # 具体模型名
    calls_per_minute_limit: int
    calls_budget_total: int    # 整个 run 的总调用上限
    calls_used: int = 0
    backoff_seconds: float = 60.0
    exhausted: bool = False

    def can_call(self) -> bool:
        return not self.exhausted and self.calls_used < self.calls_budget_total

    def record_call(self) -> None:
        self.calls_used += 1
        if self.calls_used >= self.calls_budget_total * 0.9:
            # 90% 预警：该层即将耗尽
            pass
```

### 11.4 退避策略

- 某层 rate limit → **只影响该层**，不触发全局 cooldown
- 某层预算耗尽 → 该层停止，其他层继续（audit 可以在 expression 停止后继续处理积压）
- 全部层预算耗尽 → run 结束，写入报告

**与当前代码的区别**：当前 `global_cooldown_until` 影响所有 worker。改为按层独立 cooldown。

---

## 12. Persona 迁移计划

### 12.1 44 persona → 三轴参数映射

每个种子 persona 映射到三轴分布的参数：

| persona 字段 | 映射到 | 方式 |
|-------------|--------|------|
| `age_stage` | `BehaviorAxis.compliance` | 初中=0.2, 高中=0.3, 大学=0.5, 职场=0.6 |
| `goal` (exam) | `BehaviorAxis.challenge_tendency` | exam=0.2, interest=0.4, career=0.3 |
| `style` (fragmented) | `ExpressionAxis.sentence_length` | fragmented="short", narrative="long", emotional="medium" |
| `style` (emotional) | `BehaviorAxis.emotion_intensity` | emotional=0.8, narrative=0.4, fragmented=0.5 |
| `mention_density` | `BehaviorAxis.digression_rate` | 直接映射，适当缩放 |
| `commitment_density` | `BehaviorAxis.compliance` | 作为遵从度的辅助信号 |
| `speech_patterns` | `ExpressionAxis.colloquialisms` | 直接迁移 |
| `background` | `NarrativeAxis.opening_motivation` | LLM 提取（一次性） |

**缺少的字段处理**：
- `digression_rate`：从 `style` 推断（fragmented=0.4, narrative=0.2, emotional=0.3）
- `challenge_tendency`：从 `goal` 推断（exam=0.2, interest=0.4, career=0.3）
- `responsiveness`：全局默认 0.6，按 style 微调
- `emoji_rate` / `typo_rate` / `code_switch_rate`：从 `age_stage` 推断（初中生 emoji 多，职场错别字少）

### 12.2 NarrativeAxis 的种子生成

每个种子 persona 需要预定义 2-3 个 `NarrativeAxis` 模板（opening_motivation + arc_shape + beats）：

```json
{
  "seed_persona_id": "core_middle_exam_fragmented",
  "narrative_templates": [
    {
      "opening_motivation": "作业写不完，抱怨作业多",
      "arc_shape": "oscillating",
      "beats": [
        {"turn_range": [1,3], "emotional_vector": "烦躁", "topic_hint": "抱怨作业和考试"},
        {"turn_range": [4,7], "emotional_vector": "半信半疑", "topic_hint": "试探AI建议"},
        {"turn_range": [8,12], "emotional_vector": "还行吧", "topic_hint": "有点进展但不确定"}
      ]
    },
    {
      "opening_motivation": "数学考砸了，找AI安慰",
      "arc_shape": "decline_then_recovery",
      "beats": [
        {"turn_range": [1,3], "emotional_vector": "低落", "topic_hint": "说考试失利"},
        {"turn_range": [4,7], "emotional_vector": "好奇", "topic_hint": "听建议并尝试"},
        {"turn_range": [8,12], "emotional_vector": "振奋", "topic_hint": "有点进展寻求确认"}
      ]
    }
  ]
}
```

### 12.3 迁移验证

1. **并行运行期**：Phase 2 初期同时运行旧 `turn_requirements` 和新 `三轴 + state machine`
2. **对比指标**：同一 persona、同一 seed，比较两种方式的 soft violation rate 和 authenticity
3. **回退条件**：如果新方式 soft violation > 旧方式，暂停迁移，分析原因
4. **确认迁移**：新方式稳定优于旧方式后，移除旧代码

---

## 13. 表达层验证（反应性约束的强制执行）

**问题**：`TurnDecision.must_include` 是给 LLM 的指令，LLM 可能忽略。

**解决方案**：表达层 LLM 生成消息后，rule-based 验证器检查合规性。

```python
def validate_expression(message: str, decision: TurnDecision) -> bool:
    """验证生成的消息是否满足 TurnDecision 的约束"""
    # 1. must_include 检查
    for requirement in decision.must_include:
        if requirement == "mention_person":
            # 检查是否提到了人（代词或称呼）
            if not re.search(r"(妈妈|爸爸|同学|朋友|老师|同事|他|她|哥|姐)", message):
                return False
        elif requirement == "time_anchor":
            # 检查是否包含时间锚点
            if not re.search(r"(今天|明天|这周|周末|下周|今晚|以前|之后)", message):
                return False

    # 2. must_avoid 检查
    for avoidance in decision.must_avoid:
        if avoidance == "empty_acknowledgment":
            # 检查是否是空洞回复
            empty_patterns = ["好的", "嗯嗯", "谢谢", "了解", "明白"]
            if any(message.strip() == p for p in empty_patterns):
                return False

    # 3. target_reference 检查（如果 state machine 要求引用 AI 回复）
    if decision.target_reference:
        # 检查消息长度 > 15 字（引用通常需要一定长度）
        if len(message) < 15:
            return False

    return True
```

**重试策略**：验证失败时，最多重试 2 次（在 prompt 中加强约束），第 3 次仍然失败则接受结果并记录 `validation_failed=True` 到 turn 记录。

---

## 14. ComplianceRule 和 AuthenticityDimension 定义

补充 Section 1 ScenarioSpec 中引用但未定义的类型。

```python
@dataclass
class ComplianceRule:
    """一条硬违规或软违规的检测规则"""
    rule_id: str                  # "SGW-H001" | "SGW-S001" | ...
    severity: str                 # "hard" | "soft"
    description: str              # 人类可读描述
    check_function: str           # Python 函数引用（如 "hard_violation_rules.check_source_lane"）
    parameters: dict              # 函数参数（如 {"expected_lane": "inferred_extraction"}）

@dataclass
class AuthenticityDimension:
    """一个真实性评估维度"""
    dim_id: str                   # "conversational_responsiveness" | ...
    description: str              # 维度描述（写入 audit prompt）
    weight: float                 # 在 overall 计算中的权重
    threshold: float              # 该维度的通过阈值

@dataclass
class PersonaAxisConstraints:
    """本场景对 persona 轴的约束"""
    allowed_age_stages: list[str]       # ["middle_school", "high_school", ...]
    allowed_goals: list[str]            # ["exam", "interest", "career_transition"]
    allowed_styles: list[str]           # ["fragmented", "narrative", "emotional"]
    behavior_axis_ranges: dict[str, tuple[float, float]]  # {"compliance": (0.1, 0.8)}
    required_special_personas: list[str] # ["special_dialect_henan", ...]
```

---

## 15. ConversationBeat 语义澄清

**turn_range 语义**：闭区间 [start, end]，包含两端。

**Beat 跳过处理**：如果 `allow_skip=True` 的 beat 被跳过（state machine 判断不适合当前上下文），后续 turn 顺延到下一个 beat。如果所有 beat 都已结束但 turn_index 仍在推进，使用最后一个 beat 的 `topic_hint` 继续对话（`fallback = last beat`）。

**Beat 范围外 turn**：如果 turn_index 超出所有 beat 的 turn_range（例如 session 被延长），使用 `fallback beat`：
```python
FALLBACK_BEAT = ConversationBeat(
    beat_id="fallback",
    turn_range=(999, 9999),  # 匹配所有超出范围的 turn
    emotional_vector="自由",
    topic_hint="自然继续对话，可以引入新话题或深化当前话题",
    allow_skip=False,
    transition_triggers=[]
)
```

---

## 16. config_hash 与可复现性说明

`config_hash` 保证的是**配置层面的可复现**，不保证 LLM 输出的确定性。

可复现的范围：
- Session 数量、turn 数量、persona 采样分布 → **确定性**
- 违规检测、checkpoint 格式、数据库记录结构 → **确定性**
- LLM 生成的具体消息内容 → **非确定性**（受 temperature、provider 影响）
- Soft violation rate、authenticity score → **统计近似**（±10-15% 偏差正常）

因此：验收标准 1.7 修改为 "确定性指标偏差 < 1%，统计性指标偏差 < 15%"。
