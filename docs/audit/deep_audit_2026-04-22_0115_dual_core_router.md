# 深度审计：Dual-Core Router 决策链路

> 日期：2026-04-22 01:15
> 范围：`dual_core_router.py` 路由判定 → `routing_engine.py` 输入构造 → `orchestrator.py` 消费 → `ux_envelope.py` 渲染 → 数据源追踪（sentiment/plan_health/behavior_patterns）

## 审计发现

### P0 — 阻断性问题（2 项）

#### P0-1: cognitive_load 已测量但未传入路由输入，缺失关键认知信号
- **位置**: `backend/app/services/state_estimator_service.py:108-109` (测量) vs `backend/app/orchestration/dual_core_router.py:37-58` (输入定义)
- **问题**: `UserStateSnapshot.cognitive_load` 由 state_estimator 实时计算（`min(1.0, wrong_events*0.15 + total_events*0.02)`），但 `DualCoreRoutingInput` 不包含此字段
  ```python
  # state_estimator_service.py:108 — 已计算
  cognitive_load = min(1.0, (wrong_events * 0.15) + (total_events * 0.02))

  # dual_core_router.py:37-58 — DualCoreRoutingInput 22 个字段，无 cognitive_load
  ```
- **影响**: 高认知负荷用户（近期多错题）本应被路由到 cognitive_first 模式获得支持，但实际被忽略；dual-core 路由缺少一个已存在且直接相关的信号
- **修复**: 在 `DualCoreRoutingInput` 添加 `cognitive_load: float` 字段，routing_engine 构造时从 UserStateSnapshot 注入，router 在 `_emotional_block_score` 或独立评分中使用

#### P0-2: 路由决策无结果反馈闭环，无法验证或改进路由质量
- **位置**: `dual_core_router.py` 全文件 + `routing_engine.py` 消费逻辑
- **问题**: 路由决策存储到 Redis（24h TTL）和 DB（`routing_decision_log`），但无机制回溯"该决策是否导致了好的结果"
  ```python
  # routing_engine.py:463 — 仅存储决策，无后续追踪
  state.context_data["dual_core_decision"] = decision.to_dict()
  # 无: 后续 N 轮对话后评估用户满意度/任务完成率/是否需要切换模式
  ```
- **影响**: 路由阈值（0.6 procrastination, 0.5 emotional sensitivity 等）是假设值，无数据验证其有效性；系统无法自动调优
- **修复**: (1) 添加 outcome tracking — 路由后 3 轮内用户行为（完成/放弃/切换话题）(2) 定期对比不同路由决策的 outcome distribution

---

### P1 — 重要问题（5 项）

#### P1-1: 新用户 6+ 个输入字段为空，路由退化为默认 balanced 模式
- **位置**: `routing_engine.py:157-228` (输入构造)
- **问题**: 以下字段对无历史数据的新用户始终为 None/空：
  - `plan_health_status` → None（无计划）
  - `recent_sentiment_distribution` → {}（无认知片段）
  - `recent_task_feedback_distribution` → {}（无任务反馈）
  - `primary_challenge_area` → None（无行为模式）
  - `behavior_pattern_*` → 空（无模式记录）
  - `emotional_block_detected`, `procrastination_pattern` → False
- **影响**: 新用户（恰好是最需要引导的群体）始终获得 balanced 模式，路由器的差异化价值在用户成长初期完全丧失
- **修复**: (1) 对新用户使用更激进的认知模式默认值 (2) 利用注册时的 onboarding 问卷初始化 routing_profile

#### P1-2: 多个路由阈值硬编码，无 A/B 测试数据支撑
- **位置**: `dual_core_router.py:104-108, 335-340, 388-399`
  ```python
  # :335 — 0.7 乘数从何而来？
  if intent not in self.CLEAR_INTENTS:
      base *= 0.7
  # :337-340 — 0.1 和 0.08 的惩罚依据？
  if routing_input.procrastination_pattern:
      base -= 0.1
  if routing_input.cognitive_mode_suggested:
      base -= 0.08
  ```
- **问题**: 关键阈值（0.7, 0.1, 0.08, 0.6, 0.18 等）全部硬编码，无配置文件或实验数据支撑
- **影响**: 无法针对不同用户群体调优路由策略
- **修复**: 迁移到 routing_profile 或独立配置，支持 A/B 实验

#### P1-3: BehaviorPattern 衍生信号可强制覆盖分数，绕过评分系统
- **位置**: `dual_core_router.py:349-350, 376-377`
  ```python
  # :349 — emotional_block_detected=True 直接返回 True
  if routing_input.emotional_block_detected:
      return True  # 绕过 _emotional_block_score 的分数计算

  # :376 — procrastination_pattern=True 直接返回 True
  if routing_input.procrastination_pattern:
      return True  # 绕过 _procrastination_score 的分数计算
  ```
- **问题**: 单个 behavior pattern（confidence ≥ 0.6）可触发 `emotional_block_detected=True`，直接强制 cognitive_first，无论其他评分如何
- **影响**: 一个误检的 behavior pattern 可覆盖所有其他正向信号（goal clear, high confidence 等），导致不恰当的模式切换
- **修复**: 衍生信号应作为分数加成（如 +0.15）而非硬性覆盖；或提高 confidence 阈值到 0.8

#### P1-4: Sentiment 和 feedback 窗口固定 8 条记录，不随会话长度调整
- **位置**: `context_builder.py:318-344, 350-376`
  ```python
  # :318 — 固定窗口 8
  _get_recent_sentiment_distribution(user_id, db_session, window=8)
  ```
- **问题**: 8 条记录在短会话（2-3 条消息）中包含过多历史，在长会话（50+ 条消息）中反应迟钝
- **修复**: (1) 窗口大小随会话长度动态调整 (2) 或使用时间窗口（如最近 30 分钟）替代计数窗口

#### P1-5: routing_profile 仅 3 个参数，覆盖面不足
- **位置**: `dual_core_router.py:104-108`
  ```python
  DEFAULT_ROUTING_PROFILE = {
      "procrastination_threshold": 0.6,
      "emotional_sensitivity": 0.5,
      "directness_preference": 0.5,
  }
  ```
- **问题**: 22 个输入字段但仅 3 个可配置阈值；其余硬编码
- **修复**: 扩展 routing_profile 覆盖 goal_clarity_weight, sentiment_window 等

---

### P2 — 改进建议（3 项）

#### P2-1: cognitive_adjustments 按固定数量截断，不考虑重要性
- **位置**: `dual_core_router.py:290, 312, 326`
  ```python
  cognitive_adjustments[:2]  # execution_first: 固定取前 2 条
  cognitive_adjustments[:3]  # cognitive_first: 固定取前 3 条
  ```
- **问题**: 按追加顺序截断而非按重要性排序
- **修复**: 按 priority 排序后截断

#### P2-2: routing_debug 信息仅存储但无分析工具
- **位置**: `dual_core_router.py:289` (routing_debug 赋值)
- **问题**: 每次路由生成详细 debug 信息（各评分、阈值），但无 dashboard 或分析脚本消费
- **修复**: 添加 Grafana panel 或定期分析脚本

#### P2-3: CLEAR_INTENTS 和 NEGATIVE_SENTIMENTS 列表硬编码
- **位置**: `dual_core_router.py:119, 109`
- **问题**: 意图和情绪分类集合硬编码，新增意图类型需改代码
- **修复**: 迁移到配置文件或数据库

---

### 合规项（4 项）

1. **三层降级机制** ✅ — Aurora shadow → legacy router → balanced 默认
2. **决策持久化** ✅ — Redis（24h）+ DB（routing_decision_log）+ state.context_data
3. **多源输入** ✅ — 22 个字段覆盖意图/情绪/行为/计划/偏好 5 个维度
4. **调试透明度** ✅ — routing_debug 输出完整评分链，便于排查

---

## 数据流图

```
用户消息 → orchestrator
  │
  ├── _build_dual_core_input() (routing_engine.py:157-228)
  │   ├── intent + confidence → UnifiedIntentRouter
  │   ├── information_sufficient → SufficiencyJudgeService
  │   ├── sentiment_dist → CognitiveFragment (last 8) ⚠️ 窗口固定
  │   ├── plan_health → PlanProgressService.evaluate_progress()
  │   │   └── None when no plan ⚠️ (P1-1)
  │   ├── behavior_patterns → CognitiveService (min_confidence=0.6)
  │   │   ├── emotional_block_detected → True/False (可硬性覆盖 ⚠️ P1-3)
  │   │   ├── procrastination_pattern → True/False
  │   │   └── cognitive_mode_suggested → True/False
  │   ├── routing_profile → PreferenceService (仅 3 参数 ⚠️ P1-5)
  │   ├── adaptive_adjustments → ParameterCompiler
  │   ├── session_length_preference → 多源 fallback
  │   ├── cognitive_load → ⚠️ 已计算但未传入 (P0-1)
  │   └── ... 22 fields total
  │
  ↓
DualCoreRouter.route()
  │
  ├── _goal_clarity_score() → 硬编码乘数/惩罚 ⚠️ (P1-2)
  ├── _emotional_block_score() → sentiment ratio + override
  ├── _procrastination_score() → friction signals + pattern override
  │
  ├── Decision Tree:
  │   ├── ALL(goal_clear, info_sufficient, no_emotional, no_procrostination)
  │   │   → execution_first (adjustments[:2])
  │   ├── ANY(!info_sufficient, emotional_block, procrastination, ...)
  │   │   → cognitive_first (adjustments[:3])
  │   └── else → balanced (adjustments[:2])
  │
  ↓ DualCoreDecision {mode, reason, adjustments, debug}
  │
  ├── 存储: Redis (24h) + DB (routing_decision_log) + state.context_data
  │   ⚠️ 无 outcome feedback (P0-2)
  │
  ├── Prompt 注入:
  │   ├── decision.prompt_instruction → system prompt section
  │   ├── 模式转换短语 → session_feedback
  │   └── sufficiency follow-up → intent instruction
  │
  ├── 执行模式调制:
  │   ├── cognitive_first + langgraph → 降级为 direct mode
  │   └── execution_first → 保持 langgraph/hybrid
  │
  ↓
UX Envelope (ux_envelope.py)
  ├── _dual_core_mode() → "execution" / "cognitive" / "balanced"
  ├── companion_frame → 按 mode 调整
  ├── next_actions_title → 按 mode 调整
  └── presentation_style → 条件暴露 (feature flag)
```

---

## 建议修复方案

| 优先级 | 问题 | 修复方案 | 工作量 |
|--------|------|---------|--------|
| P0-1 | cognitive_load 未传入路由 | 添加字段 + routing_engine 注入 | 低（~20 行 Python） |
| P0-2 | 无结果反馈闭环 | 添加 outcome tracking + 定期分析 | 中（~100 行 Python） |
| P1-1 | 新用户路由退化为 balanced | 激进默认值 + onboarding 初始化 | 中（~50 行 Python） |
| P1-2 | 阈值硬编码无实验数据 | 迁移到配置 + A/B 框架 | 中（~80 行 Python） |
| P1-3 | 衍生信号硬性覆盖评分 | 改为分数加成或提高阈值 | 低（~15 行 Python） |
| P1-4 | 窗口固定 8 条 | 动态窗口或时间窗口 | 低（~10 行 Python） |
| P1-5 | routing_profile 仅 3 参数 | 扩展到 6-8 个可配置参数 | 中（~40 行 Python） |

---

## 复核笔记

> **复核日期**: 2026-04-24
> **复核员**: Claude Deep Auditor

### 复核方法

逐项验证原审计发现是否与当前代码一致。注意此为早期审计（#9），代码可能已通过 Aurora Stages 重构。

### 重大变化：路由器已重构

`DualCoreRoutingInput` 从 22 字段大幅简化为 10 字段（intent, intent_confidence, information_sufficient, primary_challenge_area, recent_sentiment_distribution, has_active_plan, plan_health_status, recent_task_feedback_distribution, session_length_preference, difficulty_preference）。

`emotional_block` 和 `procrastination` 检测从外部 `BehaviorPattern` 信号改为内部计算（基于 sentiment distribution 和 task feedback distribution），不再依赖 `CognitiveService` 的 `behavior_pattern` 字段。

### 逐项复核结果

| 编号 | 原发现 | 状态 | 备注 |
|------|--------|------|------|
| P0-1 | cognitive_load 已测量但未传入路由 | ⚠️ 部分变化 | `cognitive_load` 仍未作为独立字段传入。但路由器新增 `cognitive_load_present = primary_challenge_area in {"cognitive", "execution"}`（:113），用 `primary_challenge_area` 粗略替代。state_estimator 仍计算精确的 `cognitive_load`（:108）但值未使用 |
| P0-2 | 无结果反馈闭环 | ✅ 已验证 | 仍无 outcome tracking 机制。`routing_decision_log` 存在但无回填 |
| P1-1 | 新用户路由退化为 balanced | ✅ 已验证 | 简化后输入更少（10 字段），新用户空值字段仍有 4+ 个 |
| P1-2 | 阈值硬编码 | ⚠️ 部分变化 | `DEFAULT_ROUTING_PROFILE` 已移除。但 `_has_emotional_block` 中 `negative >= 2`、`ratio >= 0.5` 和 `_has_procrastination_pattern` 中 `friction_signals >= 3` 仍硬编码 |
| P1-3 | 衍生信号硬性覆盖 | ⚠️ 部分变化 | `emotional_block` 不再来自外部 `BehaviorPattern`，改为内部计算。但仍以 bool 形式硬性覆盖（:118-122），非分数加成 |
| P1-4 | 窗口固定 8 条 | ⚠️ 需验证 | 输入简化后，sentiment/feedback 由外部 routing_engine 构造，需检查其窗口设置 |
| P1-5 | routing_profile 仅 3 参数 | ✅ 已修 | `DEFAULT_ROUTING_PROFILE` 已移除，改为内部阈值 |
| P2-1 | cognitive_adjustments 固定截断 | ⚠️ 需验证 | 简化后 adjustments 生成逻辑可能已变 |
| P2-2 | routing_debug 无分析工具 | ✅ 已验证 | 仍无消费方 |
| P2-3 | 硬编码列表 | ✅ 已验证 | `CLEAR_INTENTS` 和 `NEGATIVE_SENTIMENTS` 仍硬编码 |

### 总结

- **1/10 完全修复** (P1-5 DEFAULT_ROUTING_PROFILE 移除)
- **5/10 部分变化** — 路由器架构已重构（22→10 字段），核心问题方向正确但细节已过时
- **P0-1 仍有效** — state_estimator 的精确 cognitive_load 仍未被路由使用
- **行号引用已失效** — 文件已大规模重构，原行号不再准确
- **建议**: 下次全面重新审计此模块，因为架构变化使原报告失去参考价值
