# 深度审计：ScaffoldingFSM 学习脚手架状态机链路

> 日期：2026-04-22 02:15
> 范围：`scaffolding_fsm.py` 状态机 → `srl_phase_tracker_service.py` SRL 阶段追踪 → `intervention_service.py` 干预生成 → `cognitive_service.py` 模式检测 → `dynamic_tool_registry.py` 工具选择 → `dual_core_router.py` 路由 → `context_pack.py` 上下文 → `prompts.py` 渲染 → Flutter 认知模块 → DB schema（5 张核心表）

## 审计发现

### P0 — 阻断性问题（2 项）

#### P0-1: ScaffoldingFSM 状态完全游离于 AI 对话核心之外，AI 无法感知用户学习能力
- **位置**: `backend/app/core/context_pack.py:352-389` (ContextPack) + `backend/app/orchestration/dual_core_router.py:37-58` (RoutingInput) + `backend/app/orchestration/dynamic_tool_registry.py:175-186` (ToolRegistry)
- **问题**: ScaffoldingFSM 追踪用户 capability_level (0.0-1.0)、current_zone (frustration/flow/boredom)、support_level (1-4)，但这些数据**未传入任何一个 AI 对话决策点**
  ```python
  # context_pack.py:352-389 — ContextPack 字段:
  # ✅ preferences, goals, episodic_memories, plan_context
  # ❌ 无 scaffolding_state, support_level, capability_level, current_zone

  # dual_core_router.py:37-58 — DualCoreRoutingInput 22 个字段:
  # ✅ intent, sentiment, plan_health, behavior_patterns...
  # ❌ 无 support_level, capability_level, current_zone, srl_phase

  # dynamic_tool_registry.py:175-186 — 工具选择逻辑:
  def get_tools_by_category(self, category: ToolCategory) -> list[BaseTool]:
      return [t for t in self._tools.values() if t.category == category]
  # ❌ 无 support_level 过滤，高支持需求用户与独立用户看到相同工具
  ```
- **验证**: `prompts.py:2008-2027` 仅有 `_format_process_scaffolding_section()` 一个渲染点，且仅在 `metacognition_process_scaffolding` payload 存在时渲染（大部分情况为空）
- **影响**: 挫败区用户（capability < 0.4）与无聊区用户（capability > 0.7）获得完全相同的 AI 响应。AI 无法根据用户学习能力调整指导强度、工具复杂度、回复详细度
- **修复**: (1) ContextPack 添加 scaffolding 段（support_level, current_zone, srl_phase） (2) DualCoreRoutingInput 添加 `support_level` 和 `current_zone` 字段 (3) ToolRegistry 根据 support_level 过滤/简化工具

#### P0-2: 认知模式检测结果不触发脚手架状态更新，自适应学习闭环断裂
- **位置**: `backend/app/services/cognitive_service.py:547-648` (_upsert_pattern) vs `backend/app/scaffolding/scaffolding_fsm.py:81-122` (apply_feedback)
- **问题**: cognitive_service 的 `_upsert_pattern()` 检测到行为模式（emotional_block, execution_struggle, cognitive_pattern）后仅发布事件，**不调用 ScaffoldingFSM 更新支持级别**
  ```python
  # cognitive_service.py:547-648 — 模式更新后:
  await self.db.commit()
  # 发布事件:
  await event_bus.publish("behavior.pattern.updated", ...)  # ✅
  # ❌ 无: await ScaffoldingFSM(db).apply_pattern_update(user_id, pattern_type, confidence)
  ```
- **对比**: 唯一更新 ScaffoldingFSM 的路径是 `intervention_service.py:628-647` 的 `_apply_scaffolding_feedback()` — 仅当用户**主动交互干预卡片**时触发
- **影响**: 系统检测到用户处于 emotional_block 模式（confidence 0.8），但 support_level 不变（仍为默认 3）。自适应学习闭环中"Sense → Adapt"的 Adapt 步骤完全缺失
- **修复**: (1) 在 `_upsert_pattern()` 中添加高置信度模式 → ScaffoldingFSM 更新调用 (2) 或在 `behavior_signal_collector.py` 中消费 `behavior.pattern.updated` 事件并更新 FSM

---

### P1 — 重要问题（4 项）

#### P1-1: ScaffoldingFSM 仅 DB 持久化无 Redis 缓存，每次干预创建 2 次 DB 查询
- **位置**: `backend/app/scaffolding/scaffolding_fsm.py:35-56` (get_state) + `backend/app/services/srl_phase_tracker_service.py:336-350` (对比)
- **问题**: `ScaffoldingFSM.get_state()` 每次直接查 DB，无缓存层。对比 SRL Phase Tracker 有 Redis 缓存（24h TTL，key: `aurora:stage29:srl:state:{user_id}`）
  ```python
  # scaffolding_fsm.py:35-56 — 每次查 DB
  async def get_state(self, user_id: UUID) -> ScaffoldingState:
      result = await self.db.execute(
          select(ScaffoldingState).where(ScaffoldingState.user_id == user_id)
      )
      return result.scalar_one_or_none() or self._create_default(user_id)
  ```
- **影响**: `intervention_service.create_adaptive_intervention()` 调用 `fsm.get_state()` + `fsm.snapshot()` = 至少 2 次 DB 查询
- **修复**: 添加 Redis 缓存层（60s TTL），写入时主动失效

#### P1-2: apply_feedback() 不区分模式类型，所有反馈等权处理
- **位置**: `backend/app/scaffolding/scaffolding_fsm.py:81-122`
- **问题**: 无论用户反馈来自 emotional_block 还是 execution_struggle 模式，`weight` 参数均为 1.0
  ```python
  # intervention_service.py:642 — 统一 weight
  await fsm.apply_feedback(
      user_id=user_id,
      success=success,
      feedback=feedback_type.value,
      weight=1.0,  # ← 不区分模式类型
      srl_phase=await self._load_srl_phase_hint(user_id),
  )
  ```
- **影响**: emotional 模式的反馈应比 execution 模式有更大影响（情绪问题需要更快响应），但当前等权处理
- **修复**: 根据 pattern_type 调整 weight（emotional: 1.5, cognitive: 1.0, execution: 0.8）

#### P1-3: Flutter 无学习阶段展示，用户无法看到自己的 SRL 阶段
- **位置**: `mobile/lib/features/home/presentation/providers/cognitive_state_provider.dart:7-37`
- **问题**: 该 provider 仅推导情绪状态（focus/tired/excited/joyful/calm），**无学习阶段**（Forethought/Performance/Self-Reflection）展示逻辑
- **影响**: 用户无法了解系统对自己学习阶段的判断，降低了透明度和信任
- **修复**: 在 cognitive_state_provider 中添加 SRL phase 展示

#### P1-4: Prompt 脚手架段落范围过窄，仅 metacognition_process_scaffolding
- **位置**: `backend/app/orchestration/prompts.py:2008-2027`
- **问题**: 唯一的脚手架渲染段 `_format_process_scaffolding_section()` 仅处理 `metacognition_process_scaffolding` payload，不包含 support_level、current_zone、capability_level 信息
  ```python
  # prompts.py:2008-2027 — 仅渲染 "过程复盘支架"
  lines = [
      "## 过程复盘支架 [L2 引导]",
      f"- {body}",
      "- 只帮助用户回看判断过程，不要把这类观察写成人格、身份或诊断结论。",
  ]
  ```
- **修复**: 扩展为完整脚手架段落，包含 current_zone 指导语 + support_level 对应的回复策略

---

### P2 — 改进建议（3 项）

#### P2-1: behavior_patterns 表与 scaffolding_states 表无 FK 关系
- **位置**: `backend/gateway/internal/db/schema.sql` — 两张表独立
- **问题**: 无法查询哪些行为模式影响了脚手架调整决策
- **修复**: 在 scaffolding_states 添加 `related_pattern_id` 或在 history JSON 中记录 pattern_id

#### P2-2: Nudge 服务不包含模式上下文
- **位置**: `backend/app/services/nudge_service.py:26-90`
- **问题**: 推送通知不包含 pattern_type 或 confidence 信息
- **修复**: 在 nudge payload 中添加模式摘要

#### P2-3: history JSON 截断为最近 10 条，审计追踪有限
- **位置**: `backend/app/scaffolding/scaffolding_fsm.py:75`
  ```python
  history = (state.history or []) + [entry]
  state.history = history[-10:]  # 仅保留最近 10 条
  ```
- **修复**: 扩展到 50 条或写入独立的 scaffolding_history 表

---

### 合规项（4 项）

1. **FSM 状态持久化** ✅ — `scaffolding_states` 表有 proper indexes（user_id unique + deleted_at）+ FK 到 users(id)
2. **SRL 阶段追踪** ✅ — `srl_phase_tracker_service.py` 有 DB + Redis 双层持久化 + 24h TTL 缓存
3. **干预反馈闭环** ✅ — `intervention_service._apply_scaffolding_feedback()` 在用户交互后正确更新 capability_level + support_level
4. **Kill Switch 机制** ✅ — Aurora Stage 29/30 kill switch 可关闭 SRL 集成和元认知集成，降级为基础 support_level

---

## 数据流图

```
用户行为 (任务完成/放弃/反馈/干预交互)
  │
  ├── [路径 A: 认知模式检测] ⚠️ 不触发 FSM 更新 (P0-2)
  │   ├── cognitive_service.analyze_behavior() → RAG + HyDE 分析
  │   ├── _upsert_pattern() → 写入 behavior_patterns 表 ✅
  │   ├── 发布 behavior.pattern.updated 事件 ✅
  │   └── ❌ 无调用 ScaffoldingFSM.apply_pattern_update()
  │
  ├── [路径 B: 干预反馈] ✅ 唯一更新路径
  │   ├── 用户交互干预卡片 → intervention_service
  │   ├── _apply_scaffolding_feedback()
  │   │   ├── fsm.apply_feedback(success=True/False, weight=1.0)
  │   │   │   ├── CapabilityTracker.update() → 调整 capability_level
  │   │   │   ├── 更新 current_zone (frustration/flow/boredom)
  │   │   │   ├── 3 次连续成功 → support_level -= 1 (降支持)
  │   │   │   └── 2 次连续失败 → support_level += 1 (升支持)
  │   │   └── ⚠️ weight 固定 1.0, 不区分模式类型 (P1-2)
  │   └── 写入 scaffolding_states 表 ⚠️ 无 Redis 缓存 (P1-1)
  │
  ├── [路径 C: SRL 阶段影响]
  │   ├── srl_phase_tracker → 10 种触发事件
  │   │   ├── task.started → FORETHOUGHT
  │   │   ├── plan.created → FORETHOUGHT
  │   │   ├── task.completed → SELF_REFLECTION
  │   │   └── ...
  │   ├── resolve_support_level()
  │   │   ├── FORETHOUGHT/SELF_REFLECTION → +1.0 支持增量
  │   │   └── PERFORMANCE → 0.0 增量
  │   └── combine_with_metacognition_delta() → 最终 support_level
  │
  ↓ ScaffoldingFSM 状态已更新 (仅在干预路径)
  │
  ├── [读取: 干预创建] ✅ 唯一消费路径
  │   ├── intervention_service.create_adaptive_intervention()
  │   │   ├── fsm.get_state() → DB 查询 ⚠️ (P1-1)
  │   │   ├── resolve_support_level() → SRL + 元认知调整
  │   │   ├── IntentGenerator.generate_intent() → 生成干预意图
  │   │   └── template_service.select_variant(support_level) → 选择模板
  │   └── 产出: 自适应干预通知 ✅
  │
  ├── [读取: AI 对话] ❌ 完全未接入 (P0-1)
  │   ├── ContextPackBuilder.build()
  │   │   └── ❌ 无 scaffolding 段
  │   ├── DualCoreRoutingInput
  │   │   └── ❌ 无 support_level, current_zone 字段
  │   ├── DynamicToolRegistry.get_tools()
  │   │   └── ❌ 无 support_level 过滤
  │   └── prompts.py
  │       └── ⚠️ 仅 metacognition_process_scaffolding (常为空)
  │
  ↓
  AI 行为: 无论用户处于 frustration/flow/boredom，响应完全相同
  └── 自适应学习闭环: Sense ✅ → Adapt ❌ → Respond ❌ → Evaluate ✅ (仅干预)
```

---

## 建议修复方案

| 优先级 | 问题 | 修复方案 | 工作量 |
|--------|------|---------|--------|
| P0-1 | 脚手架状态游离于 AI 核心 | ContextPack + Router + ToolRegistry 添加 scaffolding 字段 | 中（~80 行 Python） |
| P0-2 | 认知模式不触发 FSM 更新 | _upsert_pattern 中添加 FSM 调用或事件消费 | 低（~20 行 Python） |
| P1-1 | FSM 无 Redis 缓存 | 添加 60s TTL Redis 缓存 | 低（~30 行 Python） |
| P1-2 | 反馈不区分模式类型 | 根据 pattern_type 调整 weight | 低（~10 行 Python） |
| P1-3 | Flutter 无学习阶段展示 | 添加 SRL phase 展示 | 中（~40 行 Dart） |
| P1-4 | Prompt 脚手架段落过窄 | 扩展为完整脚手架渲染 | 中（~30 行 Python） |
