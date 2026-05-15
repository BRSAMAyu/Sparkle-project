# 闭环反馈与成就系统深度审计报告

> 审计日期: 2026-05-15
> 审计范围: 闭环反馈、成就引擎、自适应重规划、计划审查、目标与任务系统、成长循环
> 审计员: 高级AI系统审计员
> 涉及文件: 35+ 核心文件

---

## 一、闭环反馈架构

### 1.1 反馈类型与来源

系统存在**6个主要反馈来源**，覆盖了从显式用户输入到隐式行为信号的完整光谱:

| 反馈来源 | 信号类型 | 采集入口 | 核心文件 |
|---------|---------|---------|---------|
| 任务完成反馈 | 显式 | `TaskFeedbackService.submit_feedback()` | `services/task_feedback_service.py` |
| 任务放弃信号 | 显式+隐式 | `TaskReflectionService.create_abandon_feedback_and_prompt()` | `services/task_reflection_service.py` |
| 任务快速操作 | 显式 | `AdaptiveReplanner.break_down_single_task_for_too_hard()` | `orchestration/adaptive_replanner.py` |
| 行为模式检测 | 隐式 | `BehaviorSignalCollector` | `services/behavior_signal_collector.py` |
| 被动信号追踪 | 隐式 | `PassiveSignalTracker` | `services/passive_signal_tracker.py` |
| 执行结果反馈 | 隐式 | `FeedbackDrivenAdjustmentService` | `services/feedback_adjustment_service.py` |

**TaskFeedbackCategory 枚举定义了8种反馈类别** (`models/task_feedback.py:17-27`):
- `TOO_DIFFICULT` / `TOO_EASY` / `JUST_RIGHT` -- 难度维
- `TOO_LONG` / `TOO_SHORT` -- 时长维
- `UNCLEAR` / `IRRELEVANT` -- 质量维
- `OTHER` -- 兜底

### 1.2 反馈收集机制

**主路径 -- 任务反馈提交** (`task_feedback_service.py:66-261`):

```
用户完成任务 → submit_feedback()
  ├─ _get_and_validate_task()        # 任务必须是 COMPLETED 状态
  ├─ _get_existing_feedback()        # 检查是否已有反馈(幂等)
  ├─ _create_feedback() / _update_feedback()
  ├─ calculate_preference_deltas()   # 计算偏好变化量
  ├─ _update_inferred_preferences()  # 平滑更新用户偏好(0.1阻尼)
  ├─ AdaptiveReplanner.on_task_feedback()   # 触发自适应
  ├─ _maybe_update_routing_profile_after_feedback()  # 更新路由画像
  ├─ TaskReflectionService            # 生成反思提示
  ├─ _classify_fail_safe_signal()     # 分类失效信号
  │   ├─ knowledge_gap → _record_knowledge_gap() → _insert_remedial_task()
  │   └─ time_pressure → _insert_remedial_task()
  └─ event_bus.publish("task.feedback_submitted")  # 发布事件
```

**副路径 -- 任务放弃** (`task_reflection_service.py:201-235`):
- 创建 `abandoned` 类别反馈
- 自动触发反思提示 (cooldown 24h/plan)
- 8种反思类别模板 (`PROMPT_TEMPLATES`)

**副路径 -- 事件总线消费** (`task_event_consumer.py`):
- `task.completed` → 行为信号收集 + 元认知刷新 + 社区桥接 + Spine记录 + 自适应重规划 + 目标进度更新
- `task.abandoned` → 行为信号 + 目标进度更新 + Spine结果记录 + 自适应计划健康评估
- `task.stuck` → 行为信号 + Spine桥接 + 自适应计划健康评估
- `task.feedback_submitted` → 行为信号 + 自适应重规划 + Quiz准确率检查

### 1.3 反馈回流路径

反馈数据通过**5条回流路径**影响AI决策:

**路径1: 偏好更新 → 计划生成**
```
TaskFeedback.calculate_preference_deltas()
  → PreferenceService.update_inferred(depth_delta * 0.1)
  → 下次规划时 ContextPackBuilder 读取偏好
  → 影响 plan_review_service 的 persona_strategy_mapping
```

**路径2: 自适应重规划 → 当前计划调整**
```
AdaptiveReplanner.on_task_feedback()
  → evaluate_plan_health_now()
  → PlanProgressService → PlanHealthReport
  → PlanAdjustmentApplier → 实际调整任务
```

**路径3: 认知碎片 → 长期记忆**
```
TaskReflectionService.submit_reflection_answer()
  → CognitiveService.create_fragment()
  → CognitiveService.analyze_behavior()
  → MemoryService.create_episodic_memory()
```

**路径4: 行为模式 → 计划约束**
```
BehaviorSignalCollector → BehaviorPattern (DB)
  → CognitivePatternTrigger.build_adjustments()
  → PlanParameterAdjustment → 计划参数修改
```

**路径5: 成就信号 → 画像更新**
```
AchievementEventConsumer._refresh_achievement_profile_signals()
  → ProfileWriteService.update_inferred_preference()
  → 信号: peak_hours, pace_style, motivation_response, reward_sensitivity
```

### 1.4 反馈对AI决策的影响

| 影响维度 | 反馈来源 | 影响机制 | 延迟 |
|---------|---------|---------|-----|
| 任务难度偏好 | `completion_quality` + `category` | `PreferenceService` 梯度更新 (阻尼0.1) | 即时 |
| 计划可行性 | `PlanQualityGate` + feasibility_comments | 拦截不切实际的计划 | 审查时 |
| 对齐分数 | `persona_strategy_mapping` + `alignment_score` | `<0.55` 时拒绝自动批准 | 审查时 |
| Sprint压缩 | `completion_rate` + `days_left` | `<0.5` 且 `<=5天` 触发压缩 | 任务完成后 |
| 连胜质量 | `StreakQualityService` | 质量<0.4 标记为WEAK | 每日 |
| 路由模式 | `RoutingProfileService.record_session_outcome()` | cognitive struggle → 标记 ignored | 反馈时 |

---

## 二、任务反馈系统

### 2.1 TaskFeedback 实现

**数据模型** (`models/task_feedback.py:29-115`):

```python
class TaskFeedback(BaseModel):
    user_id: UUID           # 用户ID
    task_id: UUID           # 任务ID
    completion_quality: int # 1-5星评分
    feedback_text: str      # 文字反馈
    category: str           # 反馈分类
    inferred_depth_delta: float     # 推断的深度偏好变化
    inferred_difficulty_delta: float # 推断的难度偏好变化
    task_difficulty_snapshot: int   # 快照: 任务难度
    task_type_snapshot: str         # 快照: 任务类型
    actual_minutes_snapshot: int    # 快照: 实际用时
    reflection_payload: JSON        # 结构化反思记录
```

**偏好计算** (`calculate_preference_deltas()`):
- 高评分(>=4): `depth_delta += 0.03`
- 低评分(<=2): `depth_delta -= 0.05`
- `too_difficult`: `depth -= 0.1, difficulty -= 0.15`
- `too_easy`: `depth += 0.1, difficulty += 0.15`
- `just_right`: `depth += 0.02` (强化)
- 时长偏差: `too_long`/`too_short` 各调 `depth +/- 0.05`

### 2.2 反馈触发时机

1. **用户主动提交** -- 完成任务后 (任务状态必须为COMPLETED)
2. **任务放弃时** -- `TaskReflectionService.create_abandon_feedback_and_prompt()`
3. **"太难"快速操作** -- `AdaptiveReplanner.break_down_single_task_for_too_hard()` 自动创建 `too_difficult` 反馈
4. **超时未完成** -- 被动信号追踪器检测

### 2.3 反馈数据结构

反馈数据的存储分为三层:
- **PostgreSQL** (`task_feedbacks` 表) -- 主存储，含偏好变化量和反思payload
- **Redis** (`spine:achievement_events:{user_id}`) -- 最近10条成就事件滚动列表
- **Event Bus** (Redis Streams `sparkle_events`) -- 事件驱动分发

---

## 三、反思系统

### 3.1 反思触发机制

**两种触发模式**:

**模式A: 轻量提示** (`maybe_enqueue_reflection_prompt()`)
- 触发条件: 任务反馈类别属于 `ELIGIBLE_CATEGORIES` (8种) + 时间>10min + 有plan_id + 不在cooldown
- Cooldown: 24小时/plan
- 输出: SystemUpdate reflection_card widget

**模式B: 深度反思** (`handle_triggered_reflection()`)
- 触发条件: 同上 + Kill Switch = `live`
- 通过 `ReflectionAgent` (LLM) 生成反思
- Rule Y 验证 → `MemoryInferredWriteLaneService` 写入L1记忆
- 完整监控指标: trigger_fired_total, context_tokens, rule_y_pass_rate, llm_latency, cost

### 3.2 反思内容分析

**结构化反思字段** (`submit_reflection_answer()`):
- `stuck_point` (必填): 卡在哪里
- `effective_method` (选填): 什么方法有效
- `adjustment_intention` (选填): 下次换什么做法

**知识节点关联** (`_resolve_reflection_knowledge_nodes()`):
- 通过任务关联的知识节点 (confidence 0.95)
- 通过 TaskKnowledgeLink (confidence 0.72-0.86)
- 通过文本匹配 KnowledgeNode (score >= 0.35)
- 最多关联3个节点

**AI回应生成** (`_build_connection_response()`):
- 个性化连接回应，结合历史反思和关联节点
- 例如: "你这次卡在「...」，我先把它挂到「...」上；它和之前「...」那条反思有相似的阻力"

### 3.3 反思结果的后续使用

1. **认知碎片写入**: `CognitiveService.create_fragment()` + `analyze_behavior()`
2. **情景记忆写入**: `MemoryService.create_episodic_memory()` (importance=0.78, confidence=0.88, decay=60d)
3. **任务-知识节点链接持久化**: `TaskKnowledgeLink` 创建/更新
4. **Phase4 Main Chain Artifact 刷新**: `MainChainArtifactService.refresh_for_legacy_plan()`
5. **事件发布**: `reflection.completed` → `TaskEventConsumer._handle_reflection_completed()` → `AdaptiveReplanner.evaluate_plan_health_now(trigger="reflection_completed")`
6. **SRL阶段事件**: `publish_srl_event(trigger_event_type="reflection.completed")`

---

## 四、成就引擎

### 4.1 成就定义与分类

**成就事件类型** (`services/achievement_engine.py:92-121`):

| 事件 | 说明 |
|------|------|
| `TASK_COMPLETED` | 任务完成 |
| `DAILY_CHECKIN` / `DAILY_STUDY` | 每日打卡/学习 |
| `NODE_UNLOCKED` / `NODE_MASTERED` | 知识节点解锁/掌握 |
| `STUDY_MINUTES_ACCUMULATED` | 学习时长累计 |
| `NIGHT_STUDY` / `EARLY_BIRD` | 深夜/早起学习 |
| `WEEKEND_WARRIOR` | 周末坚持学习 |
| `STREAK_MILESTONE` | 连胜里程碑 |
| `SPRINT_*` (6种) | 冲刺相关 |
| `COMMUNITY_SHARE` | 社区分享 |
| `AURORA_CALIBRATION` | Aurora校准 |
| `HIDDEN_TRIGGER` | 隐藏成就 |
| `CONTRACT_COMPLETED/FAILED` | 星火契约 |

**成就稀有度**: Common / Rare / Epic / Legendary
**声望轨道**: 5条 (streak/sprint/conquest/hidden/prestige)

**触发代码支持**: 28种 (`SUPPORTED_TRIGGER_CODES`)，匹配逻辑在 `_get_relevant_achievements()` 中 (line 452-555)

### 4.2 触发逻辑

**完整触发链** (`process_event()`, line 348-450):

```
process_event(user_id, event_type, **kwargs)
  ├─ _reserve_session_completion()     # 去重: session_id + event_type + task_id
  ├─ _update_streak_stats()            # 更新连胜统计 + quality streak
  ├─ _get_relevant_achievements()      # 获取相关成就定义
  ├─ for each achievement:
  │   ├─ _is_unlocked()                # 已解锁? (Redis缓存 + DB fallback)
  │   ├─ _check_prerequisites()        # 前置条件?
  │   ├─ _evaluate_progress()          # 评估进度 (28种trigger_code)
  │   ├─ _update_progress()            # 更新/创建进度记录
  │   ├─ _publish_achievement_progress() # 进度事件 (25/50/75%)
  │   ├─ _check_progress_milestone()   # 里程碑检测
  │   └─ if progress >= 1.0:
  │       ├─ _build_context_snapshot() # 快照: plan/task/node
  │       └─ _unlock_achievement()     # 解锁 + 发奖
  ├─ _handle_achievement_combo()       # 连击检测 (5min window)
  └─ _notify_unlocks() / _notify_milestones()  # WebSocket推送
```

**进度评估** (`_evaluate_progress()`, line 637-1121) 是最复杂的方法，支持28种trigger_code的进度计算。关键的评估逻辑:

- `STREAK_DAYS`: `current_streak / target_days`
- `TASKS_TOTAL`: `(solo + group * 0.7) / target`
- `NODES_UNLOCKED/MASTERED`: DB count / target
- `STUDY_MINUTES_TOTAL/SINGLE`: 累计/单次时长
- `WEEKEND_WARRIOR`: 周末连胜计算
- Sprint系列: Plan表查询 (type=SPRINT, is_active=False, progress条件)
- `PERFECTIONIST`: 单节点100%掌握度

### 4.3 光子奖励系统

**奖励类型** (`_grant_rewards()`, line 1751-1809):
- `photon`: 光子积分 (通过 `PhotonService.grant_photons()`)
- `title`: 称号解锁
- `galaxy_skin`: 星系皮肤
- `freeze_charge`: 连胜保护卡 (增加 `freeze_charges`)
- `visual_element`: 视觉元素

**连击奖励** (`_handle_achievement_combo()`, line 2603-2652):
- 5分钟内解锁>=2个: combo计数
- combo>=3: 额外 `combo * 10` 光子 (通过 `PhotonService.grant_photons(type=GRANT_BONUS)`)

**每日首胜** (`check_daily_first()`, line 2672-2719):
- 每天30光子
- 连胜>=3天: 额外1张保护卡

**光子奖励重试** (`_schedule_photon_reward_retry()`, line 1612-1734):
- Celery异步重试 (主路径)
- 本地3次重试 (降级路径, exponential backoff)
- 完整可观测性: `AchievementRewardObservability`

**契约系统** (`ContractService`, line 2806-2966):
- 用户下注光子承诺学习
- 完成: `stake * reward_multiplier` 光子奖励
- 失败: 扣除 staked 光子
- 分钟结转: 超出部分不丢弃 (`R5-P1-9`)

### 4.4 成就展示

- **成就地图**: `get_achievement_map()` -- 5条声望轨道, 节点+连接线, 推荐目标
- **进度追踪**: 实时进度百分比, 解锁提示, 推荐下一步
- **WebSocket推送**: 解锁瞬间推送 `achievement_unlock` 消息 (含glory_lines, context_story)
- **里程碑通知**: 稀有度>=Rare的成就创建 `milestone_notification`
- **进度通知**: 25/50/75%进度创建 `achievement_progress` 通知 (24h去重)
- **社区广播**: 用户开启 `share_achievements_to_community` 时广播到社区
- **成长编年史**: 持久化到PostgreSQL `GrowthChronicleSnapshot` + Redis chronicle

---

## 五、自适应重规划

### 5.1 触发条件

**3种触发入口**:

1. **任务完成时**: `on_task_completed()` → `evaluate_plan_health_now(trigger="task_completed")`
2. **反馈提交时**: `on_task_feedback()` → 检查是否为认知挣扎 (`is_strong_cognitive_struggle_feedback()`)
3. **反思完成时**: 通过 `task_event_consumer._handle_reflection_completed()` → `evaluate_plan_health_now(trigger="reflection_completed")`

**Cooldown机制**:
- `AUTO_ADJUSTMENT_COOLDOWN = 2小时`
- `AUTO_REPLAN_COOLDOWN = 12小时`
- `STRUGGLE_COOLDOWN_BYPASS_THRESHOLD = 2` -- 强认知挣扎可绕过cooldown

**认知挣扎检测** (`STRONG_COGNITIVE_STRUGGLE_MARKERS`):
- 中文: "不理解", "搞不懂", "看不懂", "不会", "没思路"
- 英文: "concept", "confus", "don't understand"

### 5.2 重规划策略

**CognitivePatternTrigger** (`adaptive_replanner.py:109-308`):
- 从 `BehaviorPattern` 表读取高置信度(>=0.7)模式
- 最多产生3个调整 (`MAX_ADJUSTMENTS_PER_RUN`)
- 支持的模式映射:

| 模式 | 调整 |
|------|------|
| 计划乐观偏差 | `task_duration_multiplier=1.3`, `phase_count_delta=+1` |
| 启动困难 | `max_session_minutes=20`, `require_start_ritual_micro_task=True` |
| 连续放弃 | `difficulty_shift_delta=-1`, `require_min_completion_unit=True` |
| 过度规划/焦虑 | `max_concurrent_tasks=3`, `hide_distant_phases=True` |
| 完美主义 | `quality_bar=eighty_percent`, `guidance_style=good_enough` |
| 委派抗拒 | `auto_delegate_suggestion=False`, `require_human_confirmation=True` |
| 前置知识不足 | `insert_prerequisite_review=True`, `weak_knowledge_node_ids=[...]` |

**Sprint压缩** (`should_compress()` + `build_compressed_sprint_day_spec()`):
- 触发: `completion_rate < 0.5 && days_left <= 5` 或 日历冲突+`days_left<=5`
- 压缩为: 35分钟保底恢复任务, 难度=1, 能耗=1
- 日历感知: 自动避开考试/课程冲突

**任务拆分** (`break_down_single_task_for_too_hard()`):
- LLM生成3-5个子任务 (5-20分钟/个)
- 回退: 3步固定拆分 (定位卡点→复述→最小检查)
- 自动降低难度, 标记 `too_hard`, `adaptive_breakdown` tags

**检查点补强** (`adjust_for_checkpoint()`):
- 检查点目标未达成时插入 `[复盘补强]` 任务
- 包含完整 micro_contract 和 fail_safe_rule

### 5.3 与FSM集成

- 通过 `PlanStateService` 写入 `adaptive_meta` 和 `feedback_log`
- `AdaptationRecord` 记录每次调整的 what/why/expected_effect
- `plan_state_service.upsert_plan_state()` 支持 facts patch + version bump
- 重规划结果通过 `ReplannerCardBridge` 生成卡片通知用户

---

## 六、计划审查系统

### 6.1 Plan Review 流程

**两级审查** (`plan_review_service.py`):

```
review_plan(plan, user_message, user_context)
  ├─ PlanQualityGate.evaluate()          # 预审查
  │   └─ 6维评分: fit/feasibility/grounding/next_action/adaptation/outcome_learning
  ├─ _collect_feasibility_comments()      # 可行性检查 (CRITICAL级直接拒绝)
  ├─ [Level 1] _quick_rule_check()        # 规则快速通道
  │   ├─ 高风险工具检查 (delete_*, reset_*, clear_*)
  │   ├─ 置信度阈值 (0.85 + strictness调整)
  │   ├─ 工具数量限制 (5 / strictness)
  │   ├─ 超额计划检测 (>=3个活跃计划)
  │   └─ 可行性验证 (高置信+简单计划)
  ├─ [Level 2] _llm_review()             # LLM深度审查 (2次重试)
  │   ├─ 温度=0.2, JSON输出
  │   ├─ 回退: _llm_review_fallback()   # 规则降级
  │   └─ [Level 2.5] _cross_model_review()  # 交叉审查 (低置信/高风险)
  ├─ StrategyCalibrationService          # 策略校准
  ├─ _score_plan_alignment()             # 对齐评分 (0-1)
  │   └─ <0.55 + require_alignment_check → NEEDS_MODIFICATION
  └─ _build_reasoning_payload()          # 解释性推理
```

### 6.2 2-tier Review 机制

**Tier 1: 规则快速通道**
- 自动批准条件: 只读工具 / 高置信简单计划(>=0.95) + 通过可行性验证
- 自动拒绝条件: 可行性CRITICAL / 质量门非approve / 对齐分<0.55且需要检查

**Tier 2: LLM审查**
- 4维评估: Safety / Alignment / Completeness / Quality
- 4种决定: approved / rejected / needs_modification / requires_confirmation
- 重试2次，每次delay递增
- 降级: 安全/只读→自动批准, 高风险→需确认, 混合→需确认

**Tier 2.5: 交叉模型审查** (新增)
- 触发: 低置信(<0.7) / 高风险工具 / 工具>8个 / 有CRITICAL评论但依然approved
- 使用不同模型 (chat vs reasoning)
- 可以推翻主审查的approved决定

### 6.3 ExecutablePlan v5.0

`ExecutablePlan` (`orchestration/schemas.py`) 包含:
- `plan_id`, `rationale`, `confidence`, `tool_calls`
- `execution_order` (分层并行), `risk_flags`
- `collaboration_mode` (sequential/parallel)
- `total_steps`, `timeout_ms`

**计划审批后流程** (`resume_plan_after_approval()`):
1. 存储审批记录到 `pending_actions_store`
2. 异步生成任务 (`_generate_tasks_after_approval()`)
3. 异步捕获计划目标到记忆 (`_capture_plan_goal_memory()`)
4. 可选自动委派 (`_auto_delegate_generated_tasks()`)

**连续拒绝检测** (`handle_review_feedback()`):
- 追踪拒绝次数 (Redis key, 1h TTL)
- 连续2次拒绝 → 触发信息收集 (`_trigger_information_collection()`)
- 用户批准 → 重置计数

---

## 七、目标与任务系统

### 7.1 Goal Clarification

目标澄清通过**对话式交互**完成:
- `orchestrator.py` FSM 中的 `clarify` 阶段
- `sufficiency_judge_schema.py` 定义了 `SufficiencyJudgment`:
  - `task_sufficiency`: 任务信息充分性
  - `context_sufficiency`: 上下文充分性
  - `CurrentTurnParseResult`: 意图/置信度/信息是否充分/目标是否解析/约束是否明确

### 7.2 Sufficiency Evaluation

**充分性评估在多个层面发生**:

1. **对话层面**: `SufficiencyJudgment` 判断当前对话是否可以进入规划阶段
2. **计划层面**: `PlanQualityGate` 6维评分 (fit/feasibility/grounding/next_action/adaptation/outcome_learning)
3. **可行性层面**: `_collect_feasibility_comments()` 检查时间/难度/技能匹配
4. **对齐层面**: `_score_plan_alignment()` 检查计划是否匹配用户画像

### 7.3 Staged Plan

**计划生成流程**:
1. `LangGraphPlanner.plan()` -- LangGraph FSM 规划 (10s超时)
2. `PlanReviewService.review_plan()` -- 两级审查
3. 批准后 → `_generate_tasks_after_approval()` -- 自动生成3-8个任务
4. 任务难度从 PlanType 推断: SPRINT→hard, 其他→medium
5. 任务数量: `max(3, min(8, total_hours/2))`

### 7.4 Task DAG Executor

**任务执行模型**:
- 任务通过 `order_index` 排序 (day_number * 1000)
- `execution_order` 支持分层并行
- DAG执行通过 `ToolExecutor.execute_tool_call()` 顺序执行
- 补偿操作: `compensation_call` 支持回滚

---

## 八、成长循环分析

### 8.1 各环节实现状态

| 环节 | 实现状态 | 核心组件 | 完成度 |
|------|---------|---------|--------|
| **Sense** | 已实现 | `ContextOrchestrator` (6维聚合) + `BehaviorSignalCollector` + `PassiveSignalTracker` | 90% |
| **Clarify** | 已实现 | `SufficiencyJudgment` + `CurrentTurnParseResult` + FSM clarify状态 | 85% |
| **Plan** | 已实现 | `LangGraphPlanner` + `PlanReviewService` + `PlanQualityGate` | 95% |
| **Execute** | 已实现 | `ToolExecutor` + `ExecutionService` + 任务DAG | 90% |
| **Reflect** | 已实现 | `TaskReflectionService` + `ReflectionAgent` + `CognitiveService` | 90% |
| **Reinforce** | 已实现 | `AchievementEngine` + 光子奖励 + 连胜系统 + 里程碑通知 | 95% |
| **Adapt** | 已实现 | `AdaptiveReplanner` + `CognitivePatternTrigger` + Sprint压缩 | 85% |

### 8.2 循环完整性评估

**完整闭环路径** (以"任务太难"为例):

```
1. SENSE:   用户在任务卡上标记"太难"
2. CLARIFY: TaskFeedbackService 接收 category="too_difficult"
3. PLAN:    → AdaptiveReplanner.on_task_feedback()
            → evaluate_plan_health_now(trigger="task_feedback_struggle")
4. EXECUTE: → break_down_single_task_for_too_hard()
            → LLM生成3-5个子任务 + 自动降低难度
            → 插入补强任务 (_insert_remedial_task)
5. REFLECT: → _maybe_record_breakdown_feedback()
            → TaskReflectionService 生成反思提示
6. REINFORCE: 任务完成后 → achievement_engine → 成就解锁 + 光子奖励
7. ADAPT:   → BehaviorPattern 更新 → CognitivePatternTrigger
            → 下次计划生成时应用 PlanParameterAdjustment
```

**闭环验证**: 反馈从产生到影响AI行为的完整路径存在且功能完备。

### 8.3 中断点和薄弱环节

1. **Sense→Clarify断层**: 行为信号收集(BehaviorSignalCollector)和充分性判断(SufficiencyJudgment)之间没有显式连接。被动信号如何转化为澄清对话的触发器，目前依赖事件总线的松散耦合。

2. **反思→行动的弱连接**: `reflection.completed` 事件通过 `task_event_consumer` 触发 `evaluate_plan_health_now`，但反思结论(stuck_point/effective_method)并没有直接转化为计划调整的具体指令。反思结果更多是写入记忆，等待下次规划时被读取。

3. **成就→激励回路**: 成就系统主要关注"识别+奖励"，但缺乏"成就解锁→动机增强→行为改变"的闭环验证。`achievement_reward_sensitivity` 写入了画像，但没有下游消费逻辑。

---

## 九、问题报告

### P0 (Critical)

**无P0问题** -- 核心反馈闭环完整，无数据丢失或系统崩溃风险。

### P1 (High)

#### P1-01: 反馈偏好的0.1阻尼系数可能过于保守

| 项 | 值 |
|----|-----|
| 严重程度 | P1 |
| 文件位置 | `task_feedback_service.py:628-629` |
| 原因分析 | `depth_delta * 0.1` 和 `difficulty_delta * 0.1` 的阻尼系数意味着用户需要连续10次"太难"反馈才能让偏好变化1个单位。对于初次使用或冷启动用户，这可能导致系统长时间无法适应用户实际水平。 |
| 修复建议 | 考虑引入动态阻尼: 冷启动期使用更大的系数(0.3-0.5)，稳定期回归0.1。或基于反馈一致性(连续同类反馈)加速收敛。 |

#### P1-02: 反馈事件处理中的异常吞没导致静默失败

| 项 | 值 |
|----|-----|
| 严重程度 | P1 |
| 文件位置 | `task_feedback_service.py:141-161`, `achievement_event_consumer.py:131-155` |
| 原因分析 | 自适应重规划、路由画像更新、反思提示生成等关键操作都被 `except Exception` 捕获后仅 log.warning，不会重试。如果Redis暂时不可用，这些操作会静默丢失。 |
| 修复建议 | 对于关键路径(自适应重规划、偏好更新)，应使用重试机制或将失败事件写入DLQ(Dead Letter Queue)。至少应通过Prometheus counter记录失败次数以便监控。 |

#### P1-03: `_get_stored_plan()` 未实现

| 项 | 值 |
|----|-----|
| 严重程度 | P1 |
| 文件位置 | `plan_review_service.py:1913-1928` |
| 原因分析 | `get_stored_plan()` 方法始终返回 `None`，注释为 "plan storage integration not yet implemented"。`resume_plan_after_approval()` 通过 `pending_actions_store` 绕过了这个问题，但 `get_stored_plan()` 作为公共API是失效的。 |
| 修复建议 | 实现该方法，从 `pending_actions_store` 或 Orchestrator 状态中检索已存储的计划，或者如果不再需要则移除此方法并更新调用方。 |

### P2 (Medium)

#### P2-01: 成就引擎 `_evaluate_progress` 方法过长 (484行)

| 项 | 值 |
|----|-----|
| 严重程度 | P2 |
| 文件位置 | `achievement_engine.py:637-1121` |
| 原因分析 | 28种trigger_code的评估逻辑全部在一个巨大的 `match/case` 中。这导致方法极度冗长，难以测试和维护。每种trigger_code的评估逻辑复杂度不同，有的需要多次DB查询。 |
| 修复建议 | 将每种trigger_code的评估提取为独立方法或策略类，使用注册表模式。例如 `ProgressEvaluatorRegistry.get(trigger_code).evaluate(user_id, config, kwargs)`。 |

#### P2-02: Sprint `SPRINT_AHEAD` 超前完成的检测逻辑简化处理

| 项 | 值 |
|----|-----|
| 严重程度 | P2 |
| 文件位置 | `achievement_engine.py:1076-1107` |
| 原因分析 | 代码注释明确指出 "这里简化处理，实际应用中需要更精确的记录"。当前的 `SPRINT_AHEAD` 检测只是统计历史完成率为100%的冲刺数量，而没有真正检测是否提前完成(target_date比较)。 |
| 修复建议 | 在Plan模型中添加 `actual_completed_at` 字段，或在UserAchievement的context_snapshot中记录提前天数，然后在评估时使用精确数据。 |

#### P2-03: `PlanQualityReport` 的 `decision` 映射存在冗余

| 项 | 值 |
|----|-----|
| 严重程度 | P2 |
| 文件位置 | `plan_review_service.py:627-633` (`_map_quality_gate_decision`) 和 `plan_quality_gate.py` |
| 原因分析 | `PlanQualityGate` 输出 `decision` 字符串 (approve/revise/downgrade_to_provisional/ask_more)，然后 `PlanReviewService` 再映射到 `ReviewDecision` 枚举。两层决策系统之间缺少统一的枚举定义。 |
| 修复建议 | 在 `PlanQualityGate` 层直接使用 `ReviewDecision` 枚举，或在两个服务之间共享一个 `PlanQualityDecision` 枚举。 |

#### P2-04: 反馈驱动的任务生成使用固定公式

| 项 | 值 |
|----|-----|
| 严重程度 | P2 |
| 文件位置 | `plan_review_service.py:2119-2123` |
| 原因分析 | `difficulty = "hard" if plan.type == PlanType.SPRINT else "medium"` 和 `task_count = max(3, min(8, int(total_hours / 2)))` 是硬编码的简化逻辑，没有考虑用户历史反馈和偏好。 |
| 修复建议 | 引入 `FeedbackDrivenTaskGenerationStrategy`，根据用户历史完成率、偏好难度和平均任务时长来动态调整生成的任务参数。 |

#### P2-05: `FeedbackDrivenAdjustmentService` 和 `TaskFeedbackService` 的职责重叠

| 项 | 值 |
|----|-----|
| 严重程度 | P2 |
| 文件位置 | `services/feedback_adjustment_service.py` vs `services/task_feedback_service.py` |
| 原因分析 | 两个服务都处理"反馈→调整"逻辑。`TaskFeedbackService` 在任务反馈提交时直接调用 `AdaptiveReplanner`，而 `FeedbackDrivenAdjustmentService` 在成就消费者中被调用处理 `TASK_COMPLETED` 事件。两个服务的调整逻辑可能产生冲突。 |
| 修复建议 | 明确划分职责: `TaskFeedbackService` 负责显式反馈的偏好更新，`FeedbackDrivenAdjustmentService` 负责任务完成后的隐式调整(时间校准、难度校准)。确保两者不会对同一任务同时产生矛盾调整。 |

#### P2-06: 反思系统缺少用户反馈闭环验证

| 项 | 值 |
|----|-----|
| 严重程度 | P2 |
| 文件位置 | `services/task_reflection_service.py` |
| 原因分析 | 反思系统会生成AI回应和写入记忆，但没有机制追踪这些建议是否被用户采纳、是否产生了积极效果。Rule Y验证了写入质量，但没有验证实际效果。 |
| 修复建议 | 在用户下次完成相关任务时，检查之前的反思建议是否被遵循。如果用户连续多次对相似卡点反思但行为未改变，应升级干预策略(从反思→主动调整计划)。 |

#### P2-07: `achievement_event_consumer.py` 中的 `try/except: pass` 模式

| 项 | 值 |
|----|-----|
| 严重程度 | P2 |
| 文件位置 | `achievement_event_consumer.py:131-155` |
| 原因分析 | 在 `_handle_task_completed` 中，StrategyMarketplace、FeedbackDrivenAdjustmentService、StateDrivenPushService 的调用都被 `except Exception: pass` 包裹。这意味着这些子系统的任何失败(包括配置错误)都会被完全静默。 |
| 修复建议 | 至少将 `pass` 替换为 `logger.warning()` 调用。对于关键操作，添加重试逻辑或DLQ。 |

#### P2-08: `calculate_preference_deltas` 中基于用时比率的推断被跳过

| 项 | 值 |
|----|-----|
| 严重程度 | P2 |
| 文件位置 | `models/task_feedback.py:103-114` |
| 原因分析 | 第104-113行的用时比率推断逻辑中，注释写着"这里简化处理，直接基于难度快照"，然后执行了 `pass` -- 这段代码完全没有实现。实际用时和预估用时的比率是判断任务是否匹配用户水平的重要信号。 |
| 修复建议 | 实现用时比率计算: `actual_minutes_snapshot / estimated_minutes`。如果比率>1.5，说明任务偏难或时间估计偏低；比率<0.5，说明偏简单。结合难度快照，动态调整 `difficulty_delta`。 |

---

## 十、架构亮点

1. **去重机制完善**: `SessionCompletion` 表 + Redis 缓存双重去重，确保同一任务/会话不会重复触发成就
2. **三态Kill Switch**: 反思系统支持 off/shadow/live 三态，shadow 模式下静默运行不产出，验证通过后才切live
3. **Rule Y 写入验证**: 反思结果通过 Rule Y 规则验证后才写入记忆，防止低质量推断污染用户画像
4. **交叉模型审查**: Plan Review 增加了 Tier 2.5 交叉审查，降低单一模型的误判风险
5. **连胜保护卡机制**: 连胜断裂时自动使用保护卡(如果是可用)，增加了用户粘性
6. **Sprint压缩感知日历**: 压缩策略会检查日历冲突，避免在考试/上课时安排保底任务
7. **完整可观测性**: 反思系统有完整的 Prometheus 指标(trigger_fired, context_tokens, rule_y_pass_rate, llm_latency, cost)
8. **光子奖励重试**: Celery异步重试 + 本地3次重试 + Observability记录，确保奖励不丢失

---

## 附录: 关键文件索引

| 文件 | 行数 | 角色 |
|------|------|------|
| `backend/app/orchestration/plan_review_service.py` | 2624 | 计划审查核心 (两级+交叉审查) |
| `backend/app/orchestration/adaptive_replanner.py` | ~1400 | 自适应重规划 (触发/策略/压缩/拆分) |
| `backend/app/services/achievement_engine.py` | 2981 | 成就引擎核心 (解锁/奖励/连胜/契约) |
| `backend/app/services/achievement_event_consumer.py` | 830 | 成就事件消费者 (事件分发/通知/画像) |
| `backend/app/services/task_feedback_service.py` | 755 | 任务反馈服务 (提交/偏好/补救) |
| `backend/app/services/task_reflection_service.py` | 1074 | 反思服务 (触发/LLM反思/记忆写入) |
| `backend/app/services/task_event_consumer.py` | 538 | 任务事件消费者 (事件路由) |
| `backend/app/services/feedback_adjustment_service.py` | ~300 | 反馈驱动调整 |
| `backend/app/services/feedback_learning_service.py` | ~200 | 反馈学习 (阈值/权重调整) |
| `backend/app/models/task_feedback.py` | 116 | TaskFeedback数据模型 |
| `backend/app/orchestration/plan_quality_gate.py` | ~200 | 计划质量门 (6维评分) |
| `backend/app/services/plan_state_service.py` | ~300 | 计划状态管理 (Redis缓存+DB) |
