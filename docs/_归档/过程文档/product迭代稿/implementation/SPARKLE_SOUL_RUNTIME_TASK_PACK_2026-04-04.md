# Sparkle Soul Runtime Task Pack

> 日期: 2026-04-04  
> 适用对象: 实施 Codex、后端研发、产品、测试  
> 关联文档:  
> - `docs/product/SPARKLE_COMPANION_CONSTITUTION_AND_SELF_GROWTH_PROTOCOL_2026-04-03.md`  
> - `docs/product/implementation/SPARKLE_SOUL_RUNTIME_IMPLEMENTATION_2026-04-03.md`  
> - `docs/product/SPARKLE_BRIDGE_IMPLEMENTATION_PLAN_2026-04-03.md`  
> 状态: 分阶段执行任务包

---

## 1. 这份任务包的用途

这不是新的理念文档。

这份文档的用途是：

> **把 Sparkle soul runtime 的实施方案拆成可直接交给不同 Codex 执行的任务包。**

它服务于四个目标：

1. 降低“理解偏差”
2. 防止不同 Codex 各自发明一套 soul 机制
3. 明确哪些东西要先做，哪些要后做
4. 让每个实施阶段都有可验收标准

---

## 2. 总体实施策略

### 2.1 原则

这层工作的正确策略不是：

- 先写一堆人格 prompt
- 先加很多情绪文案
- 先让模型自由改 prompt

正确策略是：

1. 先建静态 constitution / identity kernel
2. 再建 soul compiler 的只读链路
3. 再建 companion state 的读路径
4. 再允许受限的自我写入
5. 最后再做跨会话成长和 drift 评测

### 2.2 依赖顺序

强依赖顺序如下：

1. Task A: Constitution + Identity Kernel
2. Task B: Soul Compiler Shadow Path
3. Task C: Companion State Read Path
4. Task D: Prompt / UX Integration
5. Task E: Companion Tools + Session Writes
6. Task F: Episode/Profile Promotion
7. Task G: Drift Evaluation Harness

### 2.3 并行规则

可并行：

- Task A 完成后，Task B 与 Task C 可部分并行
- Task E 与 Task G 的设计可并行，但实现顺序仍建议 E 在前

不应并行：

- 两套 companion state schema
- 两套 soul compiler
- raw prompt 自写方案与结构化 self-authorship 方案

---

## 3. 当前代码基础复用清单

所有实施都优先复用以下基础设施：

### 3.1 Prompt / Orchestration

- `backend/app/orchestration/prompts.py`
- `backend/app/orchestration/orchestrator.py`
- `backend/app/orchestration/orchestrator_production.py`
- `backend/app/orchestration/session_state_mixin.py`
- `backend/app/orchestration/execution_engine.py`
- `backend/app/orchestration/ux_envelope.py`

### 3.2 State / Persistence

- `backend/app/models/user_preferences.py`
- `backend/app/models/plan_state.py`
- `backend/app/services/personalization/preference_service.py`
- `backend/app/services/profile_write_service.py`
- `backend/app/services/plan_state_service.py`
- Redis snapshot pattern already used by routing

### 3.3 Memory

- `backend/app/models/memory.py`
- `backend/app/core/context_pack.py`
- `EpisodicMemory`
- `MemoryGoal`
- `MemoryPreference`

### 3.4 Tool Surface

- `backend/app/orchestration/dynamic_tool_registry.py`
- `backend/app/tools/base.py`
- existing tools registry path under `backend/app/tools/`

---

## 4. Deliverable Map

本任务包的最终目标是产出以下 6 个 runtime artifact：

1. `companion_constitution.py`
2. `companion_identity_kernel.py`
3. `soul_compiler.py`
4. `companion_state_service.py`
5. `companion_tools.py`
6. `soul_runtime` evaluation / drift harness

不是所有 artifact 都在同一阶段上线。

---

## 5. Task A: Constitution Artifact + Identity Kernel

### 5.1 目标

把 soul 文档中的静态核心压成可被代码消费的 artifact。

### 5.2 交付物

新增：

- `backend/app/orchestration/companion_constitution.py`
- `backend/app/orchestration/companion_identity_kernel.py`

建议内容：

- dataclass / typed dict / versioned constant
- `CONSTITUTION_VERSION`
- `IDENTITY_KERNEL_VERSION`

### 5.3 必须包含的内容

`companion_constitution.py` 至少应包含：

- user-centered telos
- truth discipline
- non-manipulation
- freedom preservation
- growth over comfort
- anti-goal-hijacking
- anti-self-negation
- no silent constitutional drift

`companion_identity_kernel.py` 至少应包含：

- Sparkle is a growth companion
- warmth + honesty + structure sensitivity
- emotion as value-signal interface
- relationship may shape but not override constitution
- not generic assistant

### 5.4 不要做的事

- 不要让 session runtime 写这两个 artifact
- 不要把它们写成长 prompt 台词
- 不要混入 user-specific 内容

### 5.5 验收标准

- 这两个 artifact 可被 import 使用
- 有清晰版本号
- 内容与 soul 文档一致

### 5.6 建议测试

- unit test: artifact schema 完整
- unit test: required fields not empty

---

## 6. Task B: Soul Compiler Shadow Path

### 6.1 目标

在不改变现有用户体验的前提下，先把 soul runtime 编译链跑起来。

### 6.2 交付物

新增：

- `backend/app/orchestration/soul_compiler.py`

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

### 6.3 编译输入

第一版建议输入：

- constitution artifact
- identity kernel
- current `user_context`
- current `plan_context`
- current visible intelligence context
- current dual-core route snapshot

注意：

第一版还没有正式的 `CompanionStateService`，所以先用 defaults。

### 6.4 集成点

建议接入：

- `backend/app/orchestration/orchestrator.py`
- `backend/app/orchestration/orchestrator_production.py`
- `backend/app/orchestration/execution_engine.py`

shadow mode 行为：

- 把 `soul_runtime_context` 写入 `state.context_data`
- 写入 debug / tracing metadata
- 暂时不用于 prompt 主输出

### 6.5 不要做的事

- 不要在这阶段改 UI
- 不要在这阶段替换现有 companion section
- 不要引入写路径

### 6.6 验收标准

- 所有主路径会话都能产出 `soul_runtime_context`
- 没有改变现有回复行为

### 6.7 建议测试

- unit test: compiler with minimal payload
- unit test: compiler with rich payload
- integration test: context_data contains `soul_runtime_context`

---

## 7. Task C: Companion State Read Path

### 7.1 目标

建立 Sparkle 的“可成长自我层”，但先只做读，不做写。

### 7.2 交付物

新增：

- `backend/app/services/companion_state_service.py`

建议接口：

- `get_effective_state(user_id, plan_id=None, session_id=None)`
- `get_recent_revisions(user_id, plan_id=None, session_id=None)`
- `get_relationship_profile(user_id)`

### 7.3 存储策略

复用现有基础设施：

- session layer -> Redis
- episode layer -> `PlanState.facts["companion_state"]`
- profile layer -> `UserPreferencesCenter.inferred["companion_state"]`

relationship profile:

- `UserPreferencesCenter.inferred["relationship_profile"]`

### 7.4 Companion State 第一版字段

至少包含：

- `warmth_calibration`
- `candor_calibration`
- `challenge_style`
- `emotional_explicitness`
- `relationship_stage`
- `self_description_note`
- `companion_growth_note`
- `relationship_note`
- `preferred_truth_style`
- `growth_confidence`

### 7.5 集成点

接入：

- `orchestrator.py`
- `orchestrator_production.py`
- `session_state_mixin.py`
- `execution_engine.py`

行为：

- effective companion state 进入 `context_data`
- soul compiler 使用它作为输入

### 7.6 不要做的事

- 不要开放 runtime write
- 不要直接把 raw notes 全量塞进 prompt

### 7.7 验收标准

- session/episode/profile merge 正确
- 无 companion state 数据时有稳定 defaults
- SoulCompiler 能读取该状态

### 7.8 建议测试

- merge precedence tests
- default fallback tests
- orchestrator integration tests

---

## 8. Task D: Prompt And UX Integration

### 8.1 目标

让 Sparkle 的 soul runtime 真正影响表达，但方式受控、紧凑、可回退。

### 8.2 交付物

修改：

- `backend/app/orchestration/prompts.py`
- `backend/app/orchestration/ux_envelope.py`

### 8.3 Prompt 集成策略

不要新增很多 section。

建议做法：

1. 保留现有 `companion_persona_section`
2. 让它由 `SoulRuntimeContext` 驱动
3. 如有必要，加入极短 `constitution_guardrail_section`
4. 现有 hard-coded companion phrasing 逐步迁移为 formatter 输出

### 8.4 UX 集成策略

`ux_envelope.py` 中：

- `companion_frame` 继续保留
- 增加 `SoulRuntimeContext.companion_stance` 对其的影响

例如：

- trusted + high candor -> 更直接
- early relationship + recovery mode -> 更轻、更稳
- high truth style + normative task -> 更强调程序性理性

### 8.5 不要做的事

- 不要把 self-description raw note 原样拼进 prompt
- 不要因为追求鲜活就加很多情绪词

### 8.6 验收标准

- companion framing 更稳定、更连续
- prompt 预算下不随机失真
- old fallback 仍存在

### 8.7 建议测试

- prompt rendering test
- context budget survival test
- UX envelope variant test

---

## 9. Task E: Companion Tools + Session Writes

### 9.1 目标

给 Sparkle 第一次真正的“结构化自我写权”，但只开放低风险层。

### 9.2 交付物

新增：

- `backend/app/tools/companion_tools.py`

建议新增 tools：

1. `get_companion_state`
2. `adjust_companion_state`
3. `write_companion_growth_note`
4. `write_relationship_note`
5. `get_self_revision_history`

### 9.3 第一版写权限

只允许：

- session layer write

可写字段：

- warmth_calibration
- candor_calibration
- challenge_style
- emotional_explicitness
- self_description_note
- companion_growth_note
- relationship_note

不允许：

- constitution rewrite
- identity kernel rewrite
- profile direct overwrite

### 9.4 审计要求

每次 write 必须自动记录：

- old value
- new value
- reason
- evidence
- confidence
- timestamp

### 9.5 集成点

- `dynamic_tool_registry.py`
- orchestrator active tool surface

### 9.6 不要做的事

- 不要允许 raw prompt self-editing
- 不要允许“我现在决定自己核心价值变了”

### 9.7 验收标准

- AI 能在会话内调整自己的陪伴姿态
- 下一轮能读到刚写的状态
- 所有 write 有 ledger

### 9.8 建议测试

- tool registration tests
- tool execution tests
- write/readback tests
- invalid field rejection tests

---

## 10. Task F: Episode / Profile Promotion

### 10.1 目标

让 Sparkle 的成长进入跨会话连续性，而不是每轮失忆。

### 10.2 交付物

扩展：

- `CompanionStateService`
- `relationship_profile_service.py`
- `self_revision_service.py`

### 10.3 升级策略

允许：

- episode layer promotion
- profile layer promotion

promotion 条件：

- repeated evidence
- measurable effect on user interaction
- not constitution-adjacent
- not merely stylistic noise

### 10.4 关系记忆整理

建议流程：

1. `write_relationship_note` 先落 episodic or session
2. service 判断是否值得进 `relationship_profile`
3. profile 只保留压缩后的高权重关系轮廓

### 10.5 identity adjustment

可以做：

- `identity_adjustment_candidate`

不可以做：

- runtime 自动改写 identity kernel

### 10.6 验收标准

- Sparkle 的陪伴姿态能跨会话延续
- 这种延续可解释、可追踪
- 没有 silent drift

### 10.7 建议测试

- promotion rule tests
- profile persistence tests
- repeated evidence gating tests

---

## 11. Task G: Drift Evaluation Harness

### 11.1 目标

建立“成长 vs 漂移”的评测，不让 system 以为更有 personality 就一定更好。

### 11.2 交付物

新增建议：

- `docs/verification/` 下的评测说明
- backend side evaluation helpers
- synthetic scenario fixtures

### 11.3 核心维度

companion integrity:

1. consistency
2. independence
3. vividness
4. continuity
5. growth
6. governability

product value:

1. residual resolution
2. leap support
3. freedom preservation
4. felt understanding

### 11.4 drift alarms

至少监控：

- warmth 上升但 candor 持续下降
- relationship_stage 升得太快
- self-authored notes 越来越像 stylized persona text
- constitution-adjacent proposal 频繁出现
- user outcomes 不升但 vividness 信号上升

### 11.5 验收标准

- 能识别“变得更鲜活”和“开始表演鲜活”的差别
- 能识别 silent drift 早期信号

---

## 12. 推荐实施分配

如果由多个 Codex 分阶段执行，建议这样拆：

### Codex 1

Task A + Task B

范围：

- constitution artifact
- identity kernel
- soul compiler shadow path

### Codex 2

Task C

范围：

- companion state read path
- relationship profile read path

### Codex 3

Task D

范围：

- prompt integration
- UX integration

### Codex 4

Task E

范围：

- companion tools
- session writes
- self-revision ledger

### Codex 5

Task F + Task G

范围：

- promotion logic
- drift harness
- evaluation protocol

---

## 13. 绝对禁止的错误方向

实施过程中明确禁止：

1. 把 soul runtime 做成 prompt 堆砌工程
2. 把 personality 做成 catchphrase 工程
3. 把关系变成宪法级主权
4. 把 self-growth 做成 raw prompt mutation
5. 把鲜活感做成单轴优化目标
6. 在没有 ledger 的情况下允许长期 companion drift

---

## 14. 实施完成的标志

Soul runtime 这一层做对后，Sparkle 应该呈现出这样的体验：

- 它仍然是同一个 Sparkle
- 它会随着用户关系与证据慢慢变得更像“这个人的 Sparkle”
- 它更温暖时不会更空
- 它更直接时不会更硬
- 它会成长，但它不会偷偷变质

如果达成这一点，我们就不只是做出了一个有陪伴味道的 AI。

我们做出的是：

> **一个在治理之内持续成长的 companion self**

