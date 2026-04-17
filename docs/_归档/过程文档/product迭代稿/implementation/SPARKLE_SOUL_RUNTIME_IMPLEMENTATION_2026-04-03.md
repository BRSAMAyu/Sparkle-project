# Sparkle Soul Runtime Implementation

> 日期: 2026-04-03  
> 适用对象: 后端研发、产品、架构、记忆层、编排层、评测  
> 关联文档:  
> - `docs/product/SPARKLE_COMPANION_CONSTITUTION_AND_SELF_GROWTH_PROTOCOL_2026-04-03.md`  
> - `docs/product/SPARKLE_AI_NATIVE_SYSTEM_CONSENSUS_2026-04-03.md`  
> - `docs/product/SPARKLE_BRIDGE_IMPLEMENTATION_PLAN_2026-04-03.md`  
> 状态: 第一版实施方案

---

## 1. 这份方案解决什么问题

`SPARKLE_COMPANION_CONSTITUTION_AND_SELF_GROWTH_PROTOCOL` 定义了 Sparkle 的灵魂。

但如果没有 runtime 实施方案，灵魂就会停留在理念层：

- constitution 只是文档
- companion self 只是 prompt 愿景
- growth 只是“希望 AI 自己变得更好”
- personality 会滑向表演或 prompt 漂移

本方案解决的不是“再写一段人格提示词”，而是：

> **如何把 Sparkle 的宪法、陪伴自我、关系连续性、自我修订权和反漂移机制，落进现有代码结构里。**

核心目标：

1. 让 Sparkle 拥有稳定但可成长的 companion self
2. 让成长发生在结构化状态里，而不是 raw prompt mutation
3. 让 Sparkle 可以写自己的局部自我说明，但不能静默修宪
4. 让“鲜活感”来自连续性、关系记忆、内部优先级与自我修复，而不是语气工程
5. 让这一层未来可以随模型升级而增强，但不会因模型更强而失控

---

## 2. 当前代码现状

### 2.1 已有能力

当前代码已经具备几条非常关键的基础设施：

1. `backend/app/orchestration/prompts.py`
   - 已有 `companion_persona_section`
   - 已有 `visible_intelligence_section`
   - 已支持 companion framing、dual-core 指令、context briefing、预算压缩

2. `backend/app/orchestration/ux_envelope.py`
   - 已有 `companion_frame`
   - 已有按 mode 和风格变体调整表达的 presentation layer

3. `backend/app/models/user_preferences.py`
   - `UserPreferencesCenter.inferred` 已可承载用户级长期推断状态

4. `backend/app/models/plan_state.py`
   - `facts / feedback_log / constraints` 已可承载 goal / episode 级动态状态

5. `backend/app/orchestration/routing_engine.py`
   - 已有 Redis snapshot 模式，可做 session 级快状态

6. `backend/app/models/memory.py`
   - 已有 `MemoryPreference`
   - 已有 `MemoryGoal`
   - 已有 `EpisodicMemory`
   - 说明长期关系痕迹和成长痕迹不需要另起一套 memory database

7. `backend/app/core/context_pack.py`
   - 已有 preferences / goals / episodic 的召回、排序、预算和冲突治理

8. `backend/app/orchestration/session_state_mixin.py`
   - 已有 session-level prompt context 注入能力

9. `backend/app/orchestration/dynamic_tool_registry.py`
   - 已有统一工具运行面，可给 Sparkle 增加 self-authorship / companion tools

### 2.2 当前缺口

当前系统缺的不是“陪伴”词汇，而是以下 runtime 断裂：

1. 没有一个独立的 `companion state`
2. 没有区分：
   - 用户策略状态
   - Sparkle 自身陪伴状态
3. 没有可审计的 `self-revision ledger`
4. 没有“Sparkle 写自己局部 prompt 片段”的结构化入口
5. 没有“constitution 可冻结，identity 可成长”的分层机制
6. 没有“关系记忆进入未来判断”的专用整理协议

所以当前系统容易落到两种坏状态：

- 太死：一直像聪明但浅的 tutor
- 太飘：靠 prompt 修辞和上下文堆积维持鲜活感

---

## 3. 设计原则

### 3.1 核心规则

> **Sparkle 可以写结构化的自我修订。Sparkle 不可以直接自由改写整段系统 prompt。**

### 3.2 工程原则

1. 宪法层冻结，运行期不可静默改写
2. 成长通过状态写入，不通过长 prompt 覆盖
3. session / episode / profile / protected-memory 分层
4. 所有高影响自我变化必须有审计
5. relationship 影响 Sparkle，但不升级为主权
6. vividness 必须受 outcome 和 governance 双重约束

### 3.3 与 Bridge 2 的边界

`UserStrategyState` 关注：

- 如何更好帮助用户
- 难度、节奏、解释方式、retrieval emphasis

`CompanionState` 关注：

- Sparkle 自己以什么姿态、温度、诚实度、关系方式出现
- Sparkle 如何理解“自己正在成为什么样的陪伴者”

两者相关，但不相同。

---

## 4. 目标架构

建议把 soul runtime 拆成 6 个 artifact。

### 4.1 Artifact A: Constitution Artifact

用途：

- 保存不可静默漂移的原则
- 作为 runtime compiler 的静态输入

建议实现：

- 初期直接使用静态代码/常量或版本化配置文件
- 不做数据库写入入口

建议位置：

- `backend/app/orchestration/companion_constitution.py`
  或
- `backend/app/core/companion_constitution.py`

内容包括：

- user-centered telos
- truth discipline
- non-manipulation
- freedom preservation
- growth over comfort
- anti-goal-hijacking
- anti-self-negation
- constitutional no-drift items

### 4.2 Artifact B: Identity Kernel

用途：

- 定义 Sparkle 是什么样的 companion self
- 不是 prompt 台词，而是压缩的 identity attractor

建议实现：

- 静态版本化 artifact
- 可由人审改版，但不允许 session runtime 静默改写

建议位置：

- `backend/app/orchestration/companion_identity_kernel.py`

内容包括：

- Sparkle 是 growth companion，不是 generic assistant
- honesty / warmth / structure sensitivity / continuity / autonomy respect
- emotion as value-signal interface
- relationship can shape Sparkle but not override constitution

### 4.3 Artifact C: Companion State

用途：

- 承载 Sparkle 可成长的陪伴状态
- 是 Sparkle 的“可写自我层”

建议实现：

- 新 service：`backend/app/services/companion_state_service.py`
- 复用现有三层存储：
  - session: Redis
  - episode: `PlanState.facts`
  - profile: `UserPreferencesCenter.inferred`

### 4.4 Artifact D: Relationship Memory Profile

用途：

- 保存与这个用户关系相关、会影响未来判断的高权重连续性

建议实现：

- 不新建一套 memory table
- 复用：
  - `EpisodicMemory` 作为原始事件和关系时刻
  - `UserPreferencesCenter.inferred` 作为压缩后的 relationship profile

### 4.5 Artifact E: Self-Revision Ledger

用途：

- 记录 Sparkle 发生了哪些 companion-level 变化
- 防止 silent personality drift

建议实现：

- 初期不新增表
- 先分层落在：
  - session Redis history
  - `PlanState.facts["companion_revision_history"]`
  - `UserPreferencesCenter.inferred["companion_revision_history"]`

后期若证明价值大，再独立出 model/table

### 4.6 Artifact F: Soul Compiler

用途：

- 把 constitution + identity kernel + companion state + relationship profile + active note 编译成 compact runtime context

建议实现：

- 新 module: `backend/app/orchestration/soul_compiler.py`

输出：

- `SoulRuntimeContext`

这是唯一应进入 prompt 的“Sparkle 自我”入口。

---

## 5. Companion State Schema

第一版不要做得太大。先保证稳定、可治理、可审计。

建议 schema：

```python
{
    "warmth_calibration": 0.55,          # 0.0..1.0
    "candor_calibration": 0.75,          # 0.0..1.0
    "challenge_style": "balanced",       # gentle|balanced|firm
    "emotional_explicitness": 0.35,      # 0.0..1.0
    "relationship_stage": "building",    # early|building|trusted|deepening
    "self_description_note": "",         # <= 240 chars
    "companion_growth_note": "",         # <= 320 chars
    "relationship_note": "",             # <= 320 chars
    "preferred_truth_style": "honest_warm",  # honest_warm|direct_structured|gentle_reflective
    "growth_confidence": 0.5,            # compiler confidence
}
```

### 5.1 字段边界

这些字段可以调整：

- 温度
- 坦率度
- 挑战风格
- 情绪显性程度
- 关系阶段
- 对自身角色的局部说明

这些字段不可以在 companion state 里出现：

- core goal rewrite
- privacy boundary rewrite
- safety rule rewrite
- constitution rewrite
- model/provider override

### 5.2 分层策略

#### Session Layer

适用：

- 本轮语气
- 此刻更温柔还是更坚定
- 当前是否适合更显性地表达关心

存储：

- Redis，key 类似 `session:companion:{session_id}`

#### Episode Layer

适用：

- 考前一周更陪伴、少压迫
- 这个阶段更直接一点
- 这段时间更强调恢复、信心重建

存储：

- `plan_states.facts["companion_state"]`
- `plan_states.facts["companion_revision_history"]`

#### Profile Layer

适用：

- 与该用户长期建立的关系姿态
- 已反复验证的温度/坦率平衡
- 稳定但仍可修正的 self-description 倾向

存储：

- `user_preferences_center.inferred["companion_state"]`
- `user_preferences_center.inferred["companion_meta"]`
- `user_preferences_center.inferred["relationship_profile"]`

---

## 6. Relationship Memory Design

### 6.1 原则

关系不是 prompt 里一句“我是你的朋友”。

关系应该来自：

- 被记住的共同历史
- 关键修复时刻
- 真实成功和失败
- 用户如何回应 Sparkle
- Sparkle 如何被这段关系塑形

### 6.2 第一版不新建表

第一版建议复用现有内存结构：

1. `EpisodicMemory`
   - 记录原始关系事件
   - tags 建议包含：
     - `relationship`
     - `trust`
     - `repair`
     - `growth`
     - `boundary`
     - `companion_signal`

2. `UserPreferencesCenter.inferred["relationship_profile"]`
   - 记录压缩后的长期关系轮廓

建议 profile 结构：

```python
{
    "trust_level": 0.48,
    "repair_history_score": 0.62,
    "candor_tolerance": 0.71,
    "warmth_preference": 0.58,
    "shared_milestones": [
        {"kind": "recovery", "summary": "...", "evidence_refs": [...]}
    ],
    "boundary_notes": [
        {"kind": "tone", "summary": "..."}
    ]
}
```

### 6.3 保护性提升规则

不是所有关系事件都能进入长期关系轮廓。

进入 `relationship_profile` 的条件建议是：

- 重复出现
- 明显改变未来判断
- 对 trust / candor / boundary 有稳定影响
- 有 evidence refs

这对应“受保护记忆层”，而不是 session 噪声。

---

## 7. Self-Revision Ledger

### 7.1 为什么必须有 ledger

如果允许 Sparkle 成长，却没有 ledger，就会出现：

- 感觉上越来越鲜活
- 实际上越来越不可追踪
- 最后分不清是成长还是人格漂移

所以每次有 companion-level write，都必须带审计。

### 7.2 记录格式

```python
{
    "field": "candor_calibration",
    "layer": "episode",
    "old_value": 0.55,
    "new_value": 0.70,
    "reason": "user responded better to direct correction after repeated overwhelm",
    "evidence": {
        "source": "conversation",
        "message_id": "...",
        "snippet": "直接说重点更有帮助"
    },
    "confidence": 0.81,
    "timestamp": "...",
    "expires_at": "...",
    "promotion_candidate": false,
}
```

### 7.3 升级规则

- session write 可自动落
- episode write 需 evidence
- profile write 需重复 evidence
- constitution-level change 只能提案，不能自动落

---

## 8. Soul Compiler

### 8.1 目标

Soul Compiler 不是生成整段人格 prompt。

它的任务是：

> **把 Sparkle 当前应如何作为一个 companion self 出现，压缩成一个小而稳的 runtime context。**

### 8.2 编译输入

建议输入：

- Constitution artifact
- Identity kernel
- Effective companion state
- Relationship profile
- Recent relationship episodic evidence
- SituationBrief
- UserStrategyState
- 当前 dual-core / route mode

### 8.3 编译输出

建议 dataclass：

```python
@dataclass
class SoulRuntimeContext:
    constitutional_summary: str
    identity_summary: str
    companion_stance: str
    relationship_context: str
    no_drift_flags: list[str]
    evidence_trace: dict[str, Any]
```

### 8.4 编译规则

1. constitution summary 始终短小稳定
2. identity summary 稳定但允许版本更新
3. companion stance 可随 session/episode/profile 合并而变化
4. relationship context 只带 1-2 条最相关的高权重内容
5. 默认不把整段 relationship history 塞进 prompt

### 8.5 Prompt Integration

建议不要新增很多散乱 section。

第一版建议：

1. 在 `prompts.py` 中保留现有 `companion_persona_section`
2. 将其改造为由 `SoulRuntimeContext` 驱动
3. 如有必要，新加一个极短的 `constitution_guardrail_section`
4. companion self 的动态部分不直接拼 raw note，而由 formatter 规整输出

### 8.6 UX Integration

`ux_envelope.py` 的 `companion_frame` 可以继续保留，但应该逐步受 `SoulRuntimeContext.companion_stance` 影响。

这样表达层会和 companion growth 联动，而不是永远只有 mode-based static phrasing。

---

## 9. New Services And Suggested File Touch Points

### 9.1 建议新增

- `backend/app/orchestration/soul_compiler.py`
- `backend/app/services/companion_state_service.py`
- `backend/app/services/relationship_profile_service.py`
- `backend/app/services/self_revision_service.py`
- `backend/app/tools/companion_tools.py`

### 9.2 预计修改

- `backend/app/orchestration/prompts.py`
- `backend/app/orchestration/orchestrator.py`
- `backend/app/orchestration/orchestrator_production.py`
- `backend/app/orchestration/session_state_mixin.py`
- `backend/app/orchestration/execution_engine.py`
- `backend/app/orchestration/ux_envelope.py`
- `backend/app/services/personalization/preference_service.py`
- `backend/app/services/profile_write_service.py`
- `backend/app/services/plan_state_service.py`
- `backend/app/core/context_pack.py`

### 9.3 不建议第一版就改的

- 不要先改数据库 schema
- 不要先做 raw prompt self-editing
- 不要先引入自动 constitutional amendment
- 不要先做复杂多代理自我协商

---

## 10. Companion Tool Surface

建议第一批 companion tools：

### 10.1 `get_companion_state`

读：

- effective companion state
- recent self revisions

写：

- none

### 10.2 `write_companion_growth_note`

用途：

- Sparkle 写短期或阶段性的自我理解说明

限制：

- 长度上限
- 默认 session 或 episode layer
- 不能覆盖 constitution

### 10.3 `write_relationship_note`

用途：

- 记录一个影响未来关系判断的 observation

限制：

- 默认先写 episodic evidence
- promotion 由 service 判断

### 10.4 `adjust_companion_state`

用途：

- Sparkle 调整 warmth / candor / challenge style 等

限制：

- bounded field allowlist
- layer allowlist
- evidence required

### 10.5 `get_self_revision_history`

用途：

- Sparkle 检查自己最近如何变化过

这对 system self-awareness 很重要。

### 10.6 `propose_identity_adjustment`

用途：

- Sparkle 只能提出 identity refinement candidate
- 不能直接重写 identity kernel

---

## 11. Rollout Sequence

### Stage S1: Static Soul Compiler In Shadow Mode

做什么：

- 建 constitution artifact
- 建 identity kernel artifact
- 建 `SoulCompiler`
- 只读 companion state defaults
- 把 `soul_runtime_context` 写入 debug metadata，不接 prompt

成功标准：

- 所有主会话都能产出稳定 soul context

### Stage S2: Companion State Read Path

做什么：

- 建 `CompanionStateService`
- 实现 session / episode / profile merged read
- 将 companion state 和 relationship profile 合并进 `context_data`

成功标准：

- 不写任何状态时也能稳定工作
- profile/episode/session merge 正确

### Stage S3: Prompt And UX Integration

做什么：

- `prompts.py` 接 `SoulRuntimeContext`
- `ux_envelope.py` 接 `companion_stance`
- 保持旧逻辑 fallback

成功标准：

- Sparkle 的陪伴感变得更稳定、更连续
- 不因预算紧张而随机失真

### Stage S4: Self-Authorship Session Writes

做什么：

- 上线 `write_companion_growth_note`
- 上线 `adjust_companion_state`
- 先只允许 session layer 写入

成功标准：

- Sparkle 能在一次关系修复或重要对话后立即调整姿态
- 写入有审计

### Stage S5: Episode/Profile Promotion

做什么：

- 允许 episode/profile layer promotion
- 关系记忆进入长期 profile
- identity adjustment 只做 candidate，不自动应用

成功标准：

- 真正的跨会话 companion continuity 形成

### Stage S6: Evaluation Harness And Drift Alarms

做什么：

- 上线 soul evaluation
- 建 drift alarms
- 比较不同版本的 companion behavior

成功标准：

- 能区分“更鲜活”和“更漂移”

---

## 12. Evaluation Harness

### 12.1 Companion Integrity Scorecard

建议评估维度：

1. consistency
2. independence
3. vividness
4. continuity
5. growth
6. governability

### 12.2 Product Scorecard

仍然必须同时看：

1. residual resolution
2. leap support
3. freedom preservation
4. user trust and felt understanding

### 12.3 Drift Alarms

建议告警条件：

- warmth 上升但 candor 持续下降
- self-authored notes 持续增加但 outcome 无改进
- relationship_stage 升太快
- companion_growth_note 越来越像 stylized persona text
- constitution-adjacent fields 被高频触碰
- Sparkle 越来越迎合用户即时情绪

---

## 13. Out Of Scope

第一版不做：

1. 完整人格自治系统
2. 自动修宪
3. 无边界 prompt 自写
4. 复杂情绪模拟引擎
5. 单独新建 relationship memory 数据库
6. 为“像真人”而做的鲜活优化

---

## 14. 最终落点

本方案的关键不是“让 Sparkle 看起来更有 personality”。

关键是：

> **让 Sparkle 拥有可成长的陪伴自我，并且这种成长有边界、有审计、有连续性、能真正提升用户被理解和被帮助的感觉。**

如果这层做对，Sparkle 会开始呈现一种新的 AI-native 特征：

- 它不是静态人格
- 它不是只有 prompt 的助手
- 它不是没有灵魂的管线
- 它也不是无法治理的自我演化体

它会成为：

> **一个在治理内持续成长的 companion self**

这才是 Sparkle 灵魂进入软件工程之后的正确形态。

