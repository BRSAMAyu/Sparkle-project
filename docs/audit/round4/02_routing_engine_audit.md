# 意图路由层深度审计报告

> 审计范围: `routing_engine.py` (2517 行) + `dual_core_router.py` (1089 行) + `context_pruner.py` (341 行)
> 审计日期: 2026-05-15
> 审计类型: 架构级深度审计

---

## 第一部分: 架构分析

### 1.1 路由图结构: 意图分类、评分与分发

路由引擎采用**三阶段串行管线**架构:

```
UnifiedIntentRouter.route() → RouteDecision
        ↓
_apply_adaptive_routing_policy() → 修正 RouteDecision
        ↓
_apply_stage4_routing_mode() + _apply_stage4_escalation() → 最终 RouteDecision
        ↓
_apply_dual_core_routing() → DualCoreDecision → 修正 execution_mode
```

**阶段一: 统一意图路由 (UnifiedIntentRouter)**
- 输入: 用户消息 + 对话历史 + gRPC 上下文
- 输出: `UnifiedIntentType` (plan/task/sprint_plan/error_diagnosis/translation/knowledge/chat/cognitive_prism) + confidence + execution_mode + risk_level
- 转换: `to_route_decision()` 将统一路由结果转为 `RouteDecision`

**阶段二: 自适应策略修正 (_apply_adaptive_routing_policy)**
- 基于 confidence、复杂度、上下文依赖性三维度修正
- 规则: 低置信度(0.6) + 复杂查询 → 升级到 hybrid; 高置信度(0.92) + 简单查询 → 降级到 direct
- 同时检查上下文连续性 (有摘要 + 上下文依赖标记 + 置信度 < 0.7 → 升级到 hybrid)

**阶段三: Aurora Stage4 路由模式与升级**
- Stage4 routing mode: 基于 AuroraEngine 的 backbone route 决策 (direct → langgraph 升级)
- Stage4 escalation: 通过 `detect_escalation()` 检测结构性讨论轮次，将 direct 模式升级为 langgraph

**阶段四: 双核心路由 (_apply_dual_core_routing)**
- 收集 30+ 信号维度 (见下节信号加权)
- 通过 `DualCoreRouter.route()` 输出三模式决策: execution_first / cognitive_first / balanced
- Aurora 各阶段 kill switch 控制 shadow/live 模式叠加
- Bayesian wire service 做最终路由目标调整

### 1.2 信号加权体系

路由引擎收集的信号分为**六层**:

| 层级 | 信号 | 来源 | 权重范围 |
|------|------|------|----------|
| L1 意图层 | intent, confidence, information_sufficient | UnifiedIntentRouter | 直接决定 |
| L2 情绪层 | emotional_block, sentiment_distribution, primary_challenge_area | CognitiveService, plan_context | 9.0 (最高) |
| L3 执行层 | procrastination_pattern, task_feedback_distribution, plan_health | CognitiveService, PlanProgressService | 8.0 |
| L4 认知层 | cognitive_mode, metacognition_accuracy, cognitive_load, SRL phase | StateAggregator, AuroraStage35/39 | 5.0-7.0 |
| L5 脊柱层 | spine_active_states (fatigue, execution_consistency, knowledge_bottleneck) | StateRegister | 4.0-4.5 |
| L6 社交层 | social_signals (mentions, commitments, relationships) | SocialSignalsV1 | 叠加约束 |

**DualCoreRouter 的优先级评分 (precedence)**:
```
emotional_block: 9.0 > procrastination: 8.0 > cognitive_mode: 7.0 >
route_outcome_failure: 7.5 > scaffolding_frustration: 6.5 >
low_metacognition: 6.0 > high_cognitive_load: 5.0 >
route_outcome_over_scaffolded: 4.5 > spine_fatigue: 4.0 >
reflection_phase: 3.0 > scaffolding_boredom: 2.5 > goal_clarity: 1.0
```

**信号合成方式**: 优先级互斥取最高 (dominant signal)，不是加权平均。各信号独立触发 cognitive_adjustments 和 execution_constraints，但模式选择由最高优先级信号主导。

### 1.3 回退层级

路由引擎的回退链路:

```
1. UnifiedIntentRouter 正常路由 → RouteDecision
2. UnifiedIntentRouter 失败 (异常) → fallback RouteDecision(execution_mode="direct", confidence=0.5)
3. DualCoreRouter kill switch OFF → DualCoreDecision(mode="balanced")
4. legacy_decision 为 None 且 aurora 无投影 → DualCoreDecision(mode="balanced")
5. cutover_state.mode == "active" + aurora_projection 存在 → 用 aurora 投影
6. cutover_state != "active" → 用 legacy_decision
7. Bayesian wire 失败 → 保持原 route_decision 不变
8. Stage33/35/39 各信号 kill switch OFF → 信号被置 None，不影响回退
9. ContextPruner tier3 总结失败 → 回退到 tier2 规则压缩
```

### 1.4 上下文修剪

`ContextPruner` 采用**三层策略**:

| 层级 | 触发条件 | 策略 | 延迟 |
|------|----------|------|------|
| Tier 1 | 消息数 ≤ 10 | 完整保留 | ~0ms |
| Tier 2 | 消息数 ≤ 30 | 规则压缩 (重要性过滤 + 低信号压缩) | ~1ms |
| Tier 3 | 消息数 > 30 | FAST 模型总结 + 锚点保留 | ~200-500ms |

**锚点保留**: tool_calls、tool_results、含关键决策词 (计划已创建/任务完成/阶段/里程碑) 的消息不会被总结。

**缓存策略**: SHA1 哈希摘要缓存 (TTL=3600s)。同 session 同消息集合只总结一次。

### 1.5 与 DualCoreRouter 的集成

`_apply_dual_core_routing` 的完整流程:

1. **输入构建** (`_build_dual_core_input`): 聚合 30+ 信号维度到 `DualCoreRoutingInput`
2. **Aurora kill switch 查询**: Stage33/35/39 各特征的 shadow/live 模式
3. **信号过滤**: 根据 kill switch 状态清除对应信号 (off → 置 None, shadow → 置 None 但保留候选输入)
4. **基线路由**: `DualCoreRouter.route(effective_routing_input)` → legacy_decision
5. **Aurora 投影**: `route_dual_core_via_aurora()` → aurora_projection (如果 cutover 非 off)
6. **主决策选择**: active → aurora 投影; 否则 → legacy_decision
7. **信号叠加**: social/SRL/metacog/cogload 各信号独立做 candidate vs baseline 对比
   - shadow 模式: 记录 delta 但不应用
   - live 模式: 应用到 decision (overlay 或替换)
8. **Stage20 充分性**: SufficiencyJudge 评估是否需要追问
9. **Stage21 技能**: SkillSelectionService 匹配并注入技能 prompt
10. **Bayesian wire**: 最终路由目标调整
11. **持久化**: route_history + routing_outcome + dual_core_snapshot

### 1.6 性能特征

**延迟预算 (估算)**:
- UnifiedIntentRouter: ~50-200ms (LLM 调用)
- Adaptive policy: ~0.1ms (纯规则)
- Stage4 routing + escalation: ~50-100ms (AuroraEngine.decide_backbone_route)
- _build_dual_core_input: ~100-300ms (多个 DB 查询 + Redis 读取)
  - PlanProgressService.evaluate_progress: ~50ms
  - StateAggregatorService.get_user_state: ~30-80ms (2 次)
  - CognitiveService.get_user_patterns: ~30ms
  - RoutingProfileService.get_profile: ~10ms
  - Spine StateRegister: ~5ms
  - RouteHistoryService.read_recent_decisions: ~10ms
- DualCoreRouter.route(): ~0.5ms (纯计算)
- Aurora projection: ~0.1ms (纯计算)
- Kill switch 查询: ~30-60ms (4 个 kill switch 服务)
- SufficiencyJudge: ~5ms (纯计算)
- SkillSelectionService: ~20-50ms
- BayesianRoutingWireService: ~10-30ms
- RouteHistoryService.record_decision: ~20ms (DB 写)
- **总计估算: 300-900ms**

**缓存策略**:
- Dual-core snapshot: Redis `user:routing:last_dual_core:{user_id}` (TTL=86400s)
- Context summary: Redis `summary:{session_id}:{hash}` (TTL=3600s)
- Calendar context: Redis `state_aggregator:calendar:{user_id}`
- 无 UnifiedIntentRouter 结果缓存 (每轮重新计算)

---

## 第二部分: 问题报告

### 问题 #1: Stage33 Live 模式 + Cutover Active 时 Social 信号叠加可能丢失主导信号

- **严重程度**: P1 (正确性)
- **位置**: `routing_engine.py:1288-1316` (`_apply_dual_core_routing` → social overlay)
- **描述**: 当 `social_mode == "live"` 且 `cutover_state.mode != "active"` 时，social_candidate_decision 直接使用 legacy_decision (L1288-1289)，导致 social 候选路由没有真正携带 social 信号。而在 cutover active 时，叠加使用 `_overlay_stage33_social_constraints` 只添加 cognitive_adjustments 和 execution_constraints，但**不改变 mode**。这意味着如果 aurora 投影的 mode 与 social 信号建议的 mode 不同，social 信号只能影响约束列表，无法真正改变路由模式。
- **影响**: Social 信号在 live + active cutover 组合下被降级为纯约束注入，无法真正触发 cognitive_first 切换，可能导致社交压力情境下仍走 execution_first 路径。
- **修复建议**: 在 `_overlay_stage33_social_constraints` 中增加 mode override 逻辑: 当 social_delta.mode_changed 且 candidate_mode == "cognitive_first" 时，允许覆盖 decision.mode。

### 问题 #2: Stage35/39 Live 模式直接替换 decision，后续信号叠加可能被覆盖

- **严重程度**: P1 (可靠性)
- **位置**: `routing_engine.py:1262-1263, 1279-1280`
- **描述**: metacog 和 cogload 信号在 live 模式下直接替换 `decision` 变量:
  ```python
  elif metacog_mode == "live" and cutover_state.mode != "active":
      decision = metacog_candidate_decision  # L1263
  ```
  后续的 social/SRL 信号叠加操作的是已经被替换的 decision。而 social/SRL 的 live 模式在 cutover != active 时直接使用 `legacy_decision` 作为 candidate。执行顺序为: metacog → cogload → social → srl，意味着 social/SRL 的 live 模式在 metacog/cogload live 之后会**重新使用 legacy_decision**，覆盖了 metacog/cogload 的效果。
- **影响**: 多信号同时 live 时，后执行的信号会覆盖先执行信号的路由决策。信号叠加顺序硬编码，缺乏优先级仲裁。
- **修复建议**: 引入信号叠加累加器，所有 live 信号的 delta 应叠加到同一个 decision 上，而非逐个替换。或在 live 模式下统一用 effective_routing_input 的路由结果为基线，各信号只做 overlay。

### 问题 #3: _apply_stage4_escalation 直接修改 RouteDecision 字段而非返回新对象

- **严重程度**: P2 (质量)
- **位置**: `routing_engine.py:2231-2234`
- **描述**: `_apply_stage4_escalation` 直接修改 `route_decision.execution_mode` 和 `route_decision.risk_level`，而非创建新对象。同样 `_apply_adaptive_routing_policy` 也是直接修改传入的 `route_decision`。这违反了不可变数据模式，调用方可能不期望传入对象被修改。
- **影响**: 在调试或日志记录时，原始路由决策信息可能已丢失。如果中间步骤失败回退，已被修改的对象无法恢复。
- **修复建议**: RouteDecision 应改为 frozen dataclass，或使用 `dataclasses.replace()` 创建新对象。

### 问题 #4: ContextPruner 低信号判断阈值过于激进

- **严重程度**: P2 (质量)
- **位置**: `context_pruner.py:209-217` (`_is_low_signal_message`)
- **描述**: 低信号判断条件为 `content in low_signal_values or len(content) <= 12`。12 个字符的阈值过于激进，用户发送 "我不太确定这个" (8 字符) 或 "先继续吧" (5 字符) 等包含路由信号的消息会被标记为低信号并压缩。
- **影响**: 短但包含路由关键信息的用户消息 (如 "卡住了" / "不理解" / "想放弃") 可能被压缩，导致 routing_engine 收到的上下文缺失关键路由信号。
- **修复建议**: 先检查高重要性关键词再判断低信号，或将长度阈值降低到 6 字符以下，或排除包含情绪/认知关键词的短消息。

### 问题 #5: _count_structural_topic_turns 只检查最近 10 条消息但无时间窗口限制

- **严重程度**: P2 (质量)
- **位置**: `routing_engine.py:2177`
- **描述**: `_count_structural_topic_turns` 只取 `messages[-10:]` 但没有时间过滤。如果用户在长会话中早期讨论过结构化话题，即使已经过去很长时间，这些计数仍会影响 escalation 判断。
- **影响**: 可能导致过期的结构化讨论信号触发不必要的 langgraph 升级。
- **修复建议**: 增加时间窗口限制 (如最近 30 分钟内的消息)，或在计数时加入时间衰减。

### 问题 #6: DualCoreRouter.route() 的 execution_first 条件过于严格，可能导致误判为 balanced

- **严重程度**: P2 (质量)
- **位置**: `dual_core_router.py:789-815`
- **描述**: execution_first 的条件要求**所有**阻塞信号都为 False:
  ```python
  (goal_clear or strong_metacognition_execution_bias)
  and routing_input.information_sufficient
  and not emotional_block
  and not procrastination_pattern
  and not cognitive_mode_suggested
  and not reflection_phase_detected
  and not low_metacognition_accuracy
  and not high_cognitive_load
  and not spine_fatigue_detected
  and not spine_knowledge_bottleneck
  and not route_outcome_support_needed
  ```
  任何一个信号为 True 都会阻止 execution_first。考虑到 `high_cognitive_load` 的默认阈值仅为 0.55，大部分用户都可能被阻止走 execution_first 路径。
- **影响**: execution_first 路径的实际触发率可能远低于预期，系统倾向于 cognitive_first 或 balanced，导致不必要的认知支持开销。
- **修复建议**: 引入信号强度分级，只有中等以上强度的阻塞信号才阻止 execution_first。或使用 precedence score 做加权判断，而非全有全无。

### 问题 #7: BayesianRoutingWireService 失败时静默跳过

- **严重程度**: P2 (可靠性)
- **位置**: `routing_engine.py:1432-1438`
- **描述**: Bayesian wire 应用失败时仅打印 warning 日志，不记录到 context_data，也不触发任何回退度量。route_decision 保持原样继续流转。
- **影响**: 如果 Bayesian wire 持续失败 (如 Redis 连接问题)，路由系统不会感知到服务降级，可能导致路由目标偏向历史基线。
- **修复建议**: 在 context_data 中记录 bayesian_wire 的成功/失败状态，并增加 Prometheus counter 度量。

### 问题 #8: _build_dual_core_input 中多次调用 StateAggregatorService.get_user_state

- **严重程度**: P2 (性能)
- **位置**: `routing_engine.py:798-803` (metacognition), `937-943` (sufficiency), `1001-1007` (skills)
- **描述**: 在 `_build_dual_core_input`、`_collect_stage20_sufficiency`、`_collect_stage21_skills` 中分别调用 `StateAggregatorService.get_user_state`，传入不同的 `required_fields`。三次调用可能在同一轮路由中产生 3 次 DB 查询，且后两次没有缓存复用。
- **影响**: 每轮路由增加约 90-240ms 的 DB 查询延迟 (3 次 get_user_state)。
- **修复建议**: 合并为一次 `get_user_state` 调用，传入所有需要的 `required_fields`，然后分发到各消费方。

### 问题 #9: Kill switch 查询串行执行增加延迟

- **严重程度**: P2 (性能)
- **位置**: `routing_engine.py:1076-1087`
- **描述**: Stage33/35/39 三个 kill switch 服务查询是串行执行的:
  ```python
  try:
      stage33_modes = await AuroraStage33KillSwitchService().summary()
  try:
      stage35_modes = await AuroraStage35KillSwitchService().summary()
  try:
      stage39_modes = await AuroraStage39KillSwitchService().summary()
  ```
  每个查询约 10-20ms (Redis/DB)，串行总计 30-60ms。
- **影响**: 路由管线的固定延迟开销。
- **修复建议**: 使用 `asyncio.gather()` 并行查询三个 kill switch。

### 问题 #10: 路由历史记录中 judgment_id 可能格式错误

- **严重程度**: P1 (正确性)
- **位置**: `routing_engine.py:1521`
- **描述**: `sufficiency_judgment_id` 在 `sufficiency_judgment_id` 为空字符串时会尝试 `uuid.UUID(sufficiency_judgment_id)`。虽然前面有 `if sufficiency_judgment_id` 的空值检查，但如果 kill switch 关闭时 `sufficiency_judgment_id` 为 `None`，后续 `uuid.UUID(sufficiency_judgment_id)` 会在 truthy 检查通过后对非 None 但非有效 UUID 的值报错。更关键的是: 在 L966 中 `judge.persist_judgment()` 的返回值被赋给 `judgment_id`，但如果 `sufficiency_enabled` 为 False (L951-952)，函数提前返回 `task_summary, context_summary, None`，此时 `judgment_id` 为 None。但如果 `task_summary is not None and context_summary is not None` 的条件不满足 (L949)，`judgment_id` 也是 None。此时 L1521 的 `uuid.UUID(sufficiency_judgment_id)` 会因 `sufficiency_judgment_id` 为 None 而跳过 (falsy)。但如果某种执行路径导致 `sufficiency_judgment_id` 为非空非 UUID 字符串，会导致异常。
- **影响**: 在边缘情况下可能导致 route history 记录失败，进而影响路由结果历史跟踪。
- **修复建议**: 在 L1521 增加更严格的类型检查: `isinstance(sufficiency_judgment_id, str) and sufficiency_judgment_id`。

### 问题 #11: _get_routing_profile 的异常处理过于宽泛

- **严重程度**: P2 (质量)
- **位置**: `routing_engine.py:1617-1618, 1639-1640`
- **描述**: `_get_routing_profile` 中使用 `with contextlib.suppress(Exception)` 吞掉了所有异常，包括 DB 连接错误、数据损坏等。如果 RoutingProfileService 持续失败，系统会静默使用默认配置文件，可能导致路由偏差。
- **影响**: 潜在的路由配置漂移无法被发现。
- **修复建议**: 至少在第一次失败时打印 warning 日志，或使用断路器模式在连续失败后触发告警。

### 问题 #12: DualCoreRouter 全局单例无参数快照

- **严重程度**: P2 (质量)
- **位置**: `dual_core_router.py:1089`
- **描述**: `dual_core_router = DualCoreRouter()` 作为模块级全局单例创建，没有传入 `parameter_snapshot`。这意味着它始终使用默认参数值，除非在 `routing_engine.py` 中通过 `_route_with_shortcuts` 函数使用了不同的 DualCoreRouter 实例。但代码中 `self.dual_core_router` 实际上引用的就是这个全局单例。
- **影响**: `RoutingParameterRegistry` 的动态参数调整不会生效，因为全局单例永远使用默认值。
- **修复建议**: 将 `dual_core_router` 改为工厂函数，或在 `_apply_dual_core_routing` 中创建带参数快照的 DualCoreRouter 实例。

### 问题 #13: ContextPruner 的 summary_cache_key 使用 SHA1 且哈希基于完整消息列表

- **严重程度**: P2 (性能)
- **位置**: `context_pruner.py:249-253`
- **描述**: 缓存键基于完整消息列表的 JSON 序列化哈希。如果历史中任何一条消息发生变化 (如追加新消息)，整个缓存键失效，需要重新总结。这意味着在 Tier 3 场景下，每次新消息追加都会触发一次完整的 LLM 总结调用。
- **影响**: 长对话中每轮路由都可能有 200-500ms 的总结延迟。
- **修复建议**: 采用增量总结策略: 只对新追加的消息做增量总结，与缓存的旧总结合并。

### 问题 #14: _blend_recent_adaptations 基于中文字符串匹配

- **严重程度**: P1 (可靠性)
- **位置**: `routing_engine.py:1659-1670`
- **描述**: 路由配置文件的适配混合基于中文字符串匹配:
  ```python
  if "深入" in what or "详尽" in what:
      adjusted["directness_preference"] = ...
  elif "简洁" in what or "概览" in what:
      adjusted["directness_preference"] = ...
  ```
  这种匹配方式极其脆弱。如果系统更新记录的 `what_changed` 字段使用了任何未预见的表述 (如 "详细"、"细致"、或 i18n 后的英文)，匹配会静默失败。
- **影响**: 用户的偏好学习信号可能无法正确反映到路由配置文件中。
- **修复建议**: 改用结构化的 adaptation_type 枚举或标签系统，而非自由文本匹配。

### 问题 #15: 路由引擎无超时保护

- **严重程度**: P1 (可靠性)
- **位置**: `routing_engine.py:1033-1605` (`_apply_dual_core_routing` 整体)
- **描述**: `_apply_dual_core_routing` 方法包含大量异步调用 (kill switch 查询、DB 查询、Redis 操作)，但没有任何整体超时保护。如果某个依赖服务 (如 PostgreSQL) 响应缓慢，整个路由过程会阻塞，进而阻塞 gRPC 流式响应。
- **影响**: 下游服务延迟可能导致整个聊天请求超时。对于流式响应场景，用户会看到长时间无输出。
- **修复建议**: 在 `_apply_dual_core_routing` 入口处使用 `asyncio.timeout()` 包裹，设置合理的总超时 (如 2 秒)。超时后回退到 balanced 模式。

### 问题 #16: _emit_dual_core_status 的过渡提示词硬编码中文

- **严重程度**: P2 (质量/i18n)
- **位置**: `routing_engine.py:874, 1369-1375`
- **描述**: `_emit_dual_core_status` 和模式切换过渡提示词都是硬编码中文字符串:
  ```python
  headline = "我会直接把目标收敛成可执行方案。"
  _TRANSITION_PHRASES = {
      "execution_first": "今天我会先陪你把这件事想清楚...",
  }
  ```
  这与项目的 i18n 双语策略冲突。非中文用户会看到中文状态提示。
- **影响**: 非中文用户体验降级。
- **修复建议**: 使用 `isChinese ? '中文' : 'English'` 模式，或从 ARB l10n 获取本地化字符串。

### 问题 #17: cognitive_first 模式下硬编码覆盖 execution_mode 为 direct

- **严重程度**: P1 (正确性)
- **位置**: `routing_engine.py:1585-1586`
- **描述**: 当 `decision.mode == "cognitive_first"` 且 `route_decision.execution_mode in ["langgraph", "hybrid"]` 时，强制将 execution_mode 改为 "direct":
  ```python
  if decision.mode == "cognitive_first" and route_decision.execution_mode in ["langgraph", "hybrid"]:
      route_decision.execution_mode = "direct"
  ```
  这意味着即使用户有复杂的认知需求 (如需要多步骤推理的知识梳理)，也会被限制在 direct 模式，无法使用 LangGraph 的状态机编排能力。
- **影响**: 认知优先场景下用户可能获得过于简化的回复，因为 direct 模式不支持复杂工具调用链。
- **修复建议**: cognitive_first 应该允许 hybrid 模式 (保留部分编排能力)，只将 execution_mode 限制在 "direct" 当任务明确不需要编排时。或引入 cognitive_langgraph 模式。

### 问题 #18: routing_engine.py L1092 直接修改传入的 user_context_payload

- **严重程度**: P2 (质量)
- **位置**: `routing_engine.py:1089-1102`
- **描述**: `_apply_dual_core_routing` 直接修改传入的 `user_context_payload` 字典:
  ```python
  if isinstance(user_context_payload, dict):
      user_context_payload["aurora_stage33_modes"] = dict(stage33_modes)
  ```
  这是一个副作用操作，调用方可能不期望传入的上下文被修改。如果同一 `user_context_payload` 被多个处理器共享，会产生数据竞争。
- **影响**: 潜在的数据竞争和难以追踪的副作用。
- **修复建议**: 使用 `context_data` 存储路由元信息，而非修改传入的 `user_context_payload`。

### 问题 #19: _extract_cognitive_load 不处理 user_profile 为 None 的情况

- **严重程度**: P2 (质量)
- **位置**: `routing_engine.py:155-156`
- **描述**: 当 `plan_context` 是 dict 但 `user_profile` 为 None 时:
  ```python
  user_profile = (plan_context or {}).get("user_profile") if isinstance(plan_context, dict) else None
  cognitive_state = user_profile.get("cognitive_state") if isinstance(user_profile, dict) else None
  ```
  这里 `user_profile` 可能是 None 或非 dict 值 (如空字符串)。如果上游 `plan_context["user_profile"]` 存储了非 dict 值 (如 `""` 或 `0`)，`isinstance(user_profile, dict)` 会正确处理。但如果 `user_profile` 是 None，代码会短路到 `profile_context` 分支。不过这不是 bug，因为 `isinstance(None, dict)` 是 False。问题是如果 `plan_context` 包含 `"user_profile": None`，`user_profile` 会是 None，`isinstance(None, dict)` 为 False，会跳过到 `profile_context` 分支。这是正确行为，但代码路径不够直观。

**更新**: 经重新审查，此处逻辑正确但有代码异味。不构成独立问题，合并到代码质量建议中。

### 问题 #20: _is_complex_user_query 的句号计数包含小数点

- **严重程度**: P2 (质量)
- **位置**: `routing_engine.py:2096-2103`
- **描述**: 复杂度判断中 `message.count(".")` 会匹配英文小数点，导致包含数字的消息 (如 "我的成绩从 3.5 提高到 3.8") 被误判为多句复杂查询。
- **影响**: 简单的数值比较消息可能被错误升级到 hybrid 模式。
- **修复建议**: 使用更精确的分句检测 (如正则 `\.\s` 或 NLTK 分句器)，或在计数前排除数字上下文中的句号。

---

## 附录: 问题汇总表

| # | 严重程度 | 位置 | 类别 | 简述 |
|---|----------|------|------|------|
| 1 | P1 | routing_engine.py:1288 | 信号叠加 | Social 信号在 live+active 模式下无法改变路由模式 |
| 2 | P1 | routing_engine.py:1262 | 信号冲突 | 多信号 live 模式下后执行信号覆盖先执行信号 |
| 3 | P2 | routing_engine.py:2231 | 不可变性 | RouteDecision 被原地修改 |
| 4 | P2 | context_pruner.py:209 | 上下文修剪 | 低信号阈值过于激进 (12 字符) |
| 5 | P2 | routing_engine.py:2177 | 信号时效 | 结构性话题计数无时间窗口 |
| 6 | P2 | dual_core_router.py:789 | 路由决策 | execution_first 条件过于严格 |
| 7 | P2 | routing_engine.py:1432 | 可靠性 | Bayesian wire 失败静默跳过 |
| 8 | P2 | routing_engine.py:798+937+1001 | 性能 | StateAggregatorService 被调用 3 次 |
| 9 | P2 | routing_engine.py:1076 | 性能 | Kill switch 查询串行执行 |
| 10 | P1 | routing_engine.py:1521 | 正确性 | judgment_id 类型检查不足 |
| 11 | P2 | routing_engine.py:1617 | 质量 | 异常处理过于宽泛 |
| 12 | P2 | dual_core_router.py:1089 | 质量 | 全局单例无参数快照 |
| 13 | P2 | context_pruner.py:249 | 性能 | 摘要缓存键每次新消息都失效 |
| 14 | P1 | routing_engine.py:1659 | 可靠性 | 路由配置适配基于中文字符串匹配 |
| 15 | P1 | routing_engine.py:1033 | 可靠性 | 路由引擎无整体超时保护 |
| 16 | P2 | routing_engine.py:874 | i18n | 状态提示词硬编码中文 |
| 17 | P1 | routing_engine.py:1585 | 正确性 | cognitive_first 硬编码覆盖为 direct 模式 |
| 18 | P2 | routing_engine.py:1089 | 质量 | 直接修改传入的 user_context_payload |
| 19 | -- | -- | -- | (合并到代码质量建议) |
| 20 | P2 | routing_engine.py:2096 | 质量 | 复杂度判断中句号计数包含小数点 |

**统计**: P1 = 6 个, P2 = 12 个, P0 = 0 个

**关键发现**:
1. 多信号叠加机制 (问题 #1, #2) 存在系统性设计缺陷，需要重构信号叠加逻辑
2. 路由引擎无超时保护 (问题 #15) 是生产环境重大风险
3. cognitive_first 模式的 direct 强制限制 (问题 #17) 可能导致认知场景下回复质量不足
4. 偏好学习的字符串匹配 (问题 #14) 是脆弱性热点
