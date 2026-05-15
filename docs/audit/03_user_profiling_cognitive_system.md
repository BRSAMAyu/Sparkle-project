# 用户画像与认知系统深度审计报告

**审计日期**: 2026-05-15
**审计范围**: backend/app 下所有 profile、cognitive、memory、emotion、motivation、personalization、idiographic 相关模块
**审计方法**: 完整文件逐行读取 + 数据流追踪 + 架构一致性分析

---

## 一、用户画像系统

### 1.1 数据模型

用户画像系统采用**分层存储**架构：

| 存储层 | 模型 | 表名 | 职责 |
|--------|------|------|------|
| 显式偏好 | `UserPreferencesCenter` | user_preferences_center | 用户直接设置的偏好 (explicit/inferred 分区) |
| 偏好历史 | `MemoryPreference` | memory_preferences | 偏好变更的 append-only 审计日志 |
| 目标记忆 | `MemoryGoal` | memory_goals | 学习目标记录 |
| 情景记忆 | `EpisodicMemory` | episodic_memories | 长期情景记忆 |
| 认知碎片 | `CognitiveFragment` | cognitive_fragments | 用户行为/闪念原始记录 |
| 行为模式 | `BehaviorPattern` | behavior_patterns | AI 归纳的行为定式 |
| 纠正记录 | `MemoryCorrection` | memory_corrections | 用户纠正历史 |

**核心读模型**: `ProfileContext` (pydantic, 非持久化) -- 统一读接口返回值，缓存于 Redis TTL=120s。

**核心写入口**: `ProfileWriteService` -- 所有偏好变更必须通过此服务，同时写入 UserPreferencesCenter (主写模型) 和 MemoryPreference (审计日志)。

### 1.2 画像维度与字段

画像通过 `PREFERENCE_KEYS` 集合定义了 58 个合法偏好键 (参见 `backend/app/core/memory_constants.py`)，覆盖以下维度：

- **交互偏好** (12 个): depth_preference, curiosity_preference, persona_type, ai_verbosity, feedback_style, feedback_tone, response_style, coaching_style, learning_style, knowledge_level, focus_mode, sprint_mode
- **时间偏好** (8 个): timezone, active_slots, schedule_preferences, study_time_preference, focus_duration_preference, notification_frequency, daily_cap, weather_preferences
- **推送偏好** (5 个): enable_push, enable_curiosity_push, push_receptivity, consecutive_ignores, curiosity_push_receptivity
- **成就与动机** (4 个): achievement_motivation_response, achievement_pace_style, achievement_reward_sensitivity, achievement_peak_hours
- **行为推断** (8 个): chat_active_hours, avg_question_complexity, peak_focus_hours, focus_completion_rate, checkin_regularity, streak_consistency, motivation_type, difficulty_feedback_ratio
- **知识学习** (7 个): error_density_score, recurring_error_tags, error_correction_rate, task_difficulty_accuracy, task_reflection_depth, preferred_expansion_depth, vocabulary_retention_style
- **社区社交** (3 个): community_engagement_level, social_learning_preference, content_contribution_rate
- **其他** (11 个): preferred_focus_duration, inactive_push_hours, review_engagement, review_accuracy, response_satisfaction_rate, knowledge_expansion_satisfaction 等

**BigFive 人格特质**: 通过 `BigFiveTraits` 模型追踪 5 个维度 (openness, conscientiousness, extraversion, agreeableness, neuroticism)，每个维度包含 value/confidence/evidence_count/source，置信度被限制在 [0, 0.3] 区间。

### 1.3 更新机制

画像更新有两条路径：

**显式更新路径**:
1. 用户直接设置偏好 -> `ProfileWriteService.set_explicit_preferences()`
2. 写入 `UserPreferencesCenter.explicit` + `MemoryPreference` 审计日志
3. 发布 `ProfilePreferenceUpdated` 事件
4. 触发缓存失效 (Redis: user:profile_context, user:context, user:prefs:center)
5. 同步遗留字段 (User.depth_preference, PushPreference 等)

**推断更新路径**:
1. AI 从用户行为推断偏好 -> `ProfileWriteService.update_inferred_preference()`
2. 通过 `MemoryPolicyEvaluator` 检查写入策略
3. 检查是否有显式覆盖保护 (显式 > 推断)
4. 写入 `UserPreferencesCenter.inferred` + 审计日志
5. 添加推断元数据 (_confidence, _status, _last_updated)

**推断偏好学习**: `PreferenceInferenceService` 从用户反馈中学习，定义了 reason->action 映射和 behavior pattern->action 映射。包含震荡抑制机制 (5 分钟冷却期) 和反向惩罚 (0.5 系数)。

**事件驱动更新**: `ProfileEventConsumer` 监听 11 种事件类型，触发画像刷新和推断更新：
- preference.updated/deleted -> 缓存失效
- knowledge_node_updated/node_mastery_updated -> 知识摘要刷新
- behavior.pattern.updated -> 认知摘要刷新
- focus.session.completed -> 专注信号处理
- error_created -> 错误信号处理 + 自动碎片采集
- capsule_favorite_updated -> 胶囊偏好推断
- seed.created/consumed -> 种子库偏好推断
- tool_history_recorded -> 行为信号采集

### 1.4 画像使用场景

画像通过 `ProfileContextService.get_profile_context()` 生成 `ProfileContext` 对象，被以下场景消费：

1. **AI 编排器**: 通过 `ProfileTruthCompiler.compile()` 编译为 `CompiledInsightState`，注入 prompt
2. **个性化引擎**: `PersonalizationEngine` 从 ProfileContext 生成 LLMProfile/PushPolicyProfile/TaskPlanProfile
3. **前门展示**: `ProfileFrontDoorService` 构建用户可见的画像摘要，包含 claims/predictions/unknowns/evidence_refs
4. **状态聚合**: `StateAggregatorService` 读取 traits_prior 等字段，组装 `UserStateV1`
5. **矛盾检测**: `ProfileTruthCompiler` 检测 4 种矛盾类型 (difficulty vs friction, push vs recovery, self-report vs profile, pace vs capacity)
6. **内联快照**: `UserInsightState.to_inline_snapshot()` 生成 <=1200 字符的紧凑画像摘要，直接注入 LLM prompt

---

## 二、认知棱镜系统

### 2.1 认知模型定义

认知棱镜的核心数据模型：

- **CognitiveFragment**: 行为/闪念碎片，记录用户主动输入和被动捕捉的行为
  - source_type: capsule (闪念), interceptor (拦截器), behavior (隐式行为)
  - resource_type: text, audio, image
  - sentiment: anxious, bored, neutral 等
  - error_tags: 结构化错误标签 (如 ["planning.underestimate", "execution.procrastination"])
  - context_tags: 环境标签 (如 {"location": "library", "mood": "anxious"})
  - severity: 1-5 级严重程度
  - embedding: 1024 维语义向量 (pgvector)
  - 敏感标签加密存储 (V3.1)

- **BehaviorPattern**: 归因定式，基于碎片分析出的行为模式
  - pattern_type: cognitive, emotional, execution
  - confidence_score: AI 置信度 (0.0-1.0)
  - frequency: 出现次数
  - evidence_ids: 关联的碎片 ID 列表

### 2.2 行为->认知映射

认知分析流程：

1. **碎片采集**: `CognitiveService.create_fragment()` 创建 CognitiveFragment
   - 自动生成 1024 维 embedding (通过 embedding_service)
   - 支持 pgvector 不可用时的优雅降级 (per-user 级别禁用，1h 自动恢复)
   - 幂等性: 通过 source_event_id 避免重复创建

2. **异步分析**: `CognitiveEventConsumer` 监听 cognitive.fragment.created 事件
   - 限流: 同一用户 5 分钟内最多 3 次分析
   - 触发 `CognitiveService.analyze_behavior()`

3. **RAG 检索 + LLM 分析**:
   - **Raw RAG**: 用碎片的 embedding 做余弦相似度检索，取 top-K 相似碎片
   - **HyDE 策略**: 对短内容 (< 阈值) 生成假设文档，用 HyDE embedding 补充检索
   - 合并去重，限制最终上下文长度
   - 构建包含 RAG 上下文的 prompt，调用 LLM 识别模式
   - 支持 UnifiedAnalysisService 统一分析路径 (当 ANALYSIS_SYNC_ON_EVENT=true)

4. **模式更新**: `CognitiveService._upsert_pattern()`
   - 新建模式或更新已有模式 (名称匹配)
   - 置信度使用 EMA 平滑 (alpha=0.3)
   - 置信度 > 0.6 才保存模式
   - 发布 behavior.pattern.updated 和 PROFILE_COGNITIVE_UPDATED 事件

### 2.3 认知特征影响链

```
CognitiveFragment (采集) 
    -> BehaviorPattern (分析)
        -> PATTERN_POLICY_MAP (策略映射)
            -> PersonalizationEngine (个性化)
                -> LLMProfile.system_prompt_additions (prompt 注入)
```

**PATTERN_POLICY_MAP** (在 `ProfileContextService` 中定义) 映射了 13 种行为模式到具体策略信号：

| 行为模式 | 策略信号 |
|---------|---------|
| planning_optimism | task.time_estimate.add_buffer_30pct, plan.milestone.add_checkpoint |
| perfectionism_avoidance | task.difficulty.start_easy, llm.feedback.emphasize_progress |
| cognitive_blindspot | task.content.scaffold_prerequisites, llm.explanation.add_foundation |
| focus_decay | push.timing.earlier_reminder, llm.feedback.emphasize_progress |
| delegation_aversion | execution.delegate.require_confirmation |

**RISK_SIGNAL_MAP** 定义了 8 种模式到风险信号的映射 (如 planning_optimism -> risk.planning_overrun)。

**策略信号在 PersonalizationEngine 中的消费**:
- llm.* 信号 -> 注入 system_prompt_additions
- push.* 信号 -> 调整推送间隔和频率
- task.* 信号 -> 调整任务时长和难度梯度

---

## 三、记忆系统

### 3.1 记忆架构 (短期/长期/工作记忆)

系统实现三层记忆架构：

**工作记忆 (Working Memory)** -- 会话级别，存储于 Redis
- 服务: `WorkingMemoryService`
- 存储: Redis key `working_memory:{user_id}:{session_id}:{entry_id}`
- 每个 session 最多 40 条目
- TTL: 4 小时空闲过期，10 分钟会话结束宽限期
- 条目通过 semantic_key 去重，mention_count 追踪提及频次
- 支持 confirmed/rejected/consolidated 状态
- 可标记 consolidated_to_l1_id 关联长期记忆

**长期记忆 (Long-Term Memory)** -- 持久化，存储于 PostgreSQL
- 偏好: `MemoryPreference` -- append-only 版本链，最新版通过 replaced_by_id 追踪
- 目标: `MemoryGoal` -- 带 status 生命周期管理
- 情景: `EpisodicMemory` -- 带 embedding 的情景记忆
- 场景: `Scene` -- 多条记忆聚类形成的场景

**语义记忆 (Semantic Memory)** -- 知识层面
- `SemanticMemoryService` 管理策略节点 (StrategyNode) 和语义链接 (SemanticLink)
- 从错题分析中提取策略，通过 content_hash 去重

### 3.2 RAG 实现

RAG 通过 `CognitiveService.analyze_behavior()` 实现：

1. **向量检索**: pgvector 余弦相似度搜索
   - 维度: 1024
   - 检索范围: 同用户的其他碎片
   - 限制: RAG_RAW_RETRIEVAL_LIMIT (由 phase5_config 控制)

2. **HyDE 补充检索**:
   - 条件: HyDE 启用 + 碎片内容 < HYDE_QUERY_LENGTH_THRESHOLD
   - 流程: 生成假设文档 -> 生成 HyDE embedding -> 检索
   - 超时保护: HYDE_LATENCY_BUDGET_SEC

3. **合并去重**: raw + hyde 结果合并，RAG_MERGE_RESULT_LIMIT 截断

4. **Episodic Memory Embedding**: EpisodicMemory 也存储 embedding 字段，支持向量检索

### 3.3 向量嵌入策略

- **模型**: 通过 `embedding_service` 统一管理 (默认接口)
- **维度**: 1024
- **存储**: pgvector `Vector(1024)`，SQLite 兼容降级为 JSON
- **运行时保护**:
  - 全局开关 + per-user 级别禁用
  - 自动检测 vector runtime 错误 (pgvector 未安装等)
  - per-user 禁用后 1 小时自动恢复
  - 最大 10000 个 per-user 禁用记录，超限淘汰最旧
- **降级策略**: embedding 写入失败时，碎片仍保存 (embedding=null)，RAG 对该条目不生效

### 3.4 记忆检索与排序

**偏好检索**: `MemoryService.list_preferences()` -- 按 pref_key 分组取最新版本

**情景记忆检索**: `MemoryService.list_recent_episodic()` -- 按时间倒序，支持 subject_type 过滤

**记忆生命周期管理**:
- **纠正**: `apply_correction()` -- 支持 reject/lower_confidence 操作
- **撤回**: `retract_memory()` -- 保留记录但标记 retracted_at
- **吊销**: `revoke_inferred_memories()` -- 批量吊销推断记忆
- **参考结果追踪**: `record_memory_reference_outcome()` -- 记录记忆被接受/纠正/忽略/拒绝，反馈到 confidence

**证据健康**: `EvidenceHealthService` 负责证据引用的解析和快照

**记忆进化追踪**: `MemoryEvolutionService` 追踪每次变更的 old/new snapshot

---

## 四、情感/动机/状态系统

### 4.1 情感检测

**实现位置**: `StateAggregatorService._build_emotion_hint_summary()`

**数据源**:
1. CognitiveFragment.sentiment 字段 (AI 预分析结果)
2. 聊天消息关键词匹配 (`_classify_recent_chat_sentiment()`)

**关键词情感分类器**:
- frustrated: 烦/太难了/做不到/stuck/giving up 等 17 个关键词
- anxious: 焦虑/担心/anxiety/stressed 等 17 个关键词
- overwhelmed: 太多了/overwhelming/too much 等 14 个关键词
- happy: 开心/做到了/happy/awesome 等 17 个关键词
- motivated: 加油/继续/motivated/determined 等 16 个关键词

**输出**: `EmotionHintValue` -- dominant_sentiment, sentiment_distribution, emotional_block_detected

**情绪阻断检测**: dominant 为 anxious/frustrated/overwhelmed 时标记 emotional_block

**会话情绪**: `MemoryService.upsert_session_mood()` 在 Redis 中存储会话级情绪 (mood_score + mood_label)，7 天 TTL

### 4.2 动机模型

动机系统嵌入在个性化引擎中，通过以下推断偏好实现：

- **motivation_type**: 推断的动机类型 (如 "streak_driven")
- **achievement_motivation_response**: 对成就反馈的反应模式 (progress_praise/mastery_affirmation/milestone_celebration)
- **achievement_reward_sensitivity**: 奖励敏感度 (high/low)
- **achievement_pace_style**: 节奏偏好 (steady/sprint)
- **streak_consistency**: 连续性指标 (0-1)

**推断来源**:
- 成就解锁模式分析 -> achievement_motivation_response, achievement_pace_style
- 连续性统计 -> streak_consistency, motivation_type
- 行为模式分析 -> achievement_reward_sensitivity

### 4.3 状态追踪

**状态估计器**: `StateEstimatorService`
- 数据源: 最近 24 小时 TrackingEvent (最多 200 条)
- 计算 cognitive_load, strain_index, interruptibility, focus_mode, sprint_mode
- 公式:
  - cognitive_load = min(1.0, wrong_events * 0.15 + total_events * 0.02)
  - strain_index = min(1.0, wrong_ratio + 0.2 if wrong >= 3)
  - interruptibility = max(0.0, 1.0 - cognitive_load - (0.2 if focus_mode))

**状态聚合器**: `StateAggregatorService`
- 20 个维度字段，每个字段有独立 TTL (30s - 24h)
- 包含: commitment_summary, engagement_state, emotion_hint, learning_state, working_memory_snapshot, calendar_context, traits_prior, srl_phase, metacognition_profile, idiographic_summary 等
- 受 Aurora Stage 18 Kill Switch 控制 (off/shadow/live)
- 缓存: 进程内 _cache dict，上限 500 条目，自动淘汰过期

**SRL 阶段追踪**: 通过 SRLPhaseStateRecord 持久化当前/上一阶段
- 阶段: UNKNOWN -> FORETHOUGHT -> PERFORMANCE -> SELF_REFLECTION
- 数值映射: 0.0, 0.25, 0.55, 0.85

### 4.4 对AI行为的影响

情感/状态系统通过以下路径影响 AI 行为：

1. **DualCoreRoutingInput**: emotional_block_detected, procrastination_pattern, cognitive_mode_suggested 等字段影响双核路由决策
2. **PersonalizationEngine.get_llm_profile()**: 根据 emotion_hint 调整 tone 和策略
3. **PersonalizationEngine.get_push_policy_profile()**: emotional_block 时减少推送压力
4. **ProfileTruthCompiler._detect_contradictions()**: 4 条矛盾规则检测潜在冲突

---

## 五、个性化引擎

### 5.1 Prompt 组装个性化

`PersonalizationEngine.get_llm_profile()` 是核心个性化入口：

**输入**: user_id + session_context + override_preferences + profile_context

**解析链**:
1. 获取偏好 (显式 > 推断 > 默认值)
2. 解析 ProfileContext (如提供)
3. 构建个性化指令段落

**个性化维度**:

| 维度 | 偏好键 | 影响 |
|------|--------|------|
| 回答详细度 | depth_preference | verbose=concise(<0.3)/balanced/detailed(>0.7) |
| 探索倾向 | curiosity_preference | exploratory(>0.7)/focused(<0.3)/moderate |
| 语气风格 | feedback_style | playful(gentle)/professional |
| 角色设定 | persona_type | coach/anime/mentor/friend |
| 温度 | depth_preference | temperature=0.3+depth*0.4 |
| 是否追问 | depth_preference | should_ask_clarifying when depth>0.6 |
| 是否举例 | depth_preference | should_provide_examples when depth>0.5 |

**附加策略** (基于推断偏好和行为模式):
- error_density >= 0.7 -> 放慢节奏
- preferred_expansion_depth == "shallow" -> 减少扩展
- streak_consistency >= 0.8 -> 肯定坚持
- motivation_type == "streak_driven" -> 保护连续性
- achievement_motivation_response -> 调整反馈风格
- achievement_reward_sensitivity == "high" -> 自然指出收益
- achievement_pace_style -> steady/sprint 节奏建议
- task_reflection_depth == "deep" -> 鼓励深度反思
- cognitive behavior pattern policy_signals -> 行为策略适配

### 5.2 语气/风格适配

4 种预设角色 (persona_type):
- **coach**: 严格学习教练，直接/专业/督促
- **anime**: 温柔二次元助手，甜美/鼓励/活泼/颜文字
- **mentor**: 资深导师，睿智/耐心/启发式
- **friend**: 亲切学习伙伴，轻松/友好/支持

### 5.3 个性化覆盖度评估

**覆盖的场景**:
- LLM 交互: 详细度/探索性/语气/角色/策略 -- 完整覆盖
- 推送系统: 频率/时段/静默/间隔 -- 完整覆盖
- 任务规划: 时长/难度/探索比/复习优先级 -- 完整覆盖

**推断元数据注册表** (`INFERRED_META`): 为推断字段提供 source/explanation_template/adjustable 标记，覆盖约 20+ 字段。

---

## 六、Idiographic Association (个体特征关联)

### 6.1 个体特征建模

`IdiographicAssociationService` 实现个体层面的行为维度关联分析：

**10 个行为维度**:
| 维度 | 标签 |
|------|------|
| study_pace | 学习节奏 |
| completion_rate | 完成率 |
| engagement_level | 投入程度 |
| mood_valence | 情绪效价 |
| plan_adherence | 计划贴合度 |
| focus_duration_daily | 专注时长 |
| task_accuracy_daily | 任务预估准确度 |
| session_frequency_daily | 学习记录频次 |
| srl_phase_signal | 自我调节阶段 |
| metacognition_accuracy | 元认知准确性 |

**每日行为向量**: `DailyBehaviorVector` -- 每个用户每天一个 10 维向量

**数据来源**: 
- PersDynAttractorService (5 维: study_pace, completion_rate, engagement_level, mood_valence, plan_adherence)
- FocusSession 聚合 (focus_duration_daily)
- Task 完成数据 (task_accuracy_daily)
- StudyRecord 计数 (session_frequency_daily)
- SRLPhaseStateRecord (srl_phase_signal)
- MetacognitionService (metacognition_accuracy)

### 6.2 关联规则引擎

**窗口**: 45 天滑动窗口

**相关性分析**: `correlate_dimensions()` -- 维度间 Spearman 排序相关
- 密度门槛: >= 150 排序对，>= 70% 覆盖率
- BH 多重检验校正: q <= 0.05
- 最小绝对相关: |r| >= 0.30
- 置信度上限: 0.80
- Path B 模式 (数据不充分): 置信度 * 0.7

**变化点检测**: PELT 算法 (`detect_change_points`) 检测 30 天内各维度变化点

**展示策略**:
- 最多展示 3 个 top 关联
- 优先展示非情绪关联
- 用户已否决的关联 30 天内不展示
- 免责声明: "这只是你数据中的模式，不代表因果关系"

**用户否决机制**: `register_user_disconfirmation()` -- 用户可否决关联，30 天内抑制，高否决率自动降级 kill switch

**Kill Switch**: Aurora Stage 31 tri-state (off/shadow/live)

---

## 七、系统交互全景图

```
用户行为/输入
    |
    v
[CognitiveFragment 采集] -----> [CognitiveEventConsumer 异步分析]
    |                                      |
    |                                      v
    |                              [RAG + LLM 分析]
    |                                      |
    |                                      v
    |                              [BehaviorPattern 更新]
    |                                      |
    v                                      v
[ProfileWriteService] <--- [PreferenceInferenceService]
    |                              |
    v                              v
[UserPreferencesCenter]     [MemoryPreference 审计]
    |
    v
[ProfileContextService 编译] -----> [ProfileContext (Redis 缓存)]
    |                                          |
    |                                          v
    |                              [ProfileTruthCompiler]
    |                                          |
    |                              +-----------+-----------+
    |                              |           |           |
    |                              v           v           v
    |                        [矛盾检测]  [LLMProfile]  [TaskPlanProfile]
    |                                      |           |
    |                                      v           v
    |                              [Prompt 组装]  [推送策略]
    |
    +---> [StateAggregatorService (20 维)]
    |         |
    |         v
    |    [UserStateV1] ---> [DualCoreRouter] ---> [Orchestrator FSM]
    |
    +---> [IdiographicAssociationService]
    |         |
    |         v
    |    [维度关联分析] ---> [idiographic_summary]
    |
    +---> [WorkingMemoryService (Redis)]
              |
              v
         [会话内短期记忆] ---> [prompt 注入]
```

**事件流**:
```
ProfilePreferenceUpdated -> ProfileEventConsumer -> 缓存失效 + 系统更新
cognitive.fragment.created -> CognitiveEventConsumer -> 限流 + RAG 分析
behavior.pattern.updated -> ProfileEventConsumer -> 画像缓存失效
task.completed/focus.session.completed -> IdiographicAssociationService -> 重新计算
```

---

## 八、问题报告

### P0 -- 无

### P1 -- 需要修复

| # | 问题描述 | 严重程度 | 文件位置 | 原因分析 | 修复建议 |
|---|---------|---------|---------|---------|---------|
| P1-01 | BigFive 置信度验证范围过窄 [0, 0.3]，无法表达高置信度特质 | P1 | `backend/app/core/user_insight_state.py:47` | BigFiveDimension.confidence 被硬编码限制为最大 0.3，这意味着即使 AI 有充分证据，也无法表达超过 30% 的置信度。对于冷启动后多次 NLP 观察到的稳定特质，这个上限不合理。 | 评估是否将上限提高到 0.7 或 0.85，或者让 confidence 的含义从"单次观察置信度"变为"综合置信度"后调整范围。需要检查所有消费方是否依赖 0.3 上限。 |
| P1-02 | CognitiveService.analyze_behavior 中 fallback 分析路径调用 llm_service.mock 但对非 mock 场景缺少保护 | P1 | `backend/app/services/cognitive_service.py:515-527` | 当 `batch_model_key` 为 None 且 llm_service 不是 mock 时，代码先尝试检查 `__module__` 是否以 "unittest.mock" 开头，但此检查对真实 LLM 服务会走 false 分支，然后 `analysis` 为 None 进入后续的 `cognitive_llm.json_call`。逻辑正确但可读性差，且错误日志不够明确。 | 重构此分支逻辑，使 mock 检测和真实 LLM 调用路径更清晰，添加更多日志区分两条路径。 |
| P1-03 | ProfileEventConsumer 中错误处理后直接 raise 可能导致消费者退出循环 | P1 | `backend/app/services/profile_event_consumer.py:139,152` | `_handle_preference_updated` 和 `_handle_preference_deleted` 中 catch 异常后 log.error 然后 raise，这会导致上层事件循环中断。其他 handler (如 _handle_knowledge_updated) 也 raise。 | 应该在非关键错误时吞掉异常继续处理后续事件，仅在不可恢复错误时 raise。与 CognitiveEventConsumer 的模式保持一致。 |
| P1-04 | StateEstimatorService 使用同步 session.commit() 而不是异步 | P1 | `backend/app/services/state_estimator_service.py:35` | `self.db.add(snapshot)` + `await self.db.commit()` -- 虽然 db 是 AsyncSession，但 snapshot 的新增和提交在并发场景下可能与其他写入冲突。且此服务每次调用都创建新 snapshot，没有清理旧 snapshot 的机制。 | 添加旧 snapshot 清理机制 (如保留最近 N 个)；考虑使用 upsert 而不是每次新增。 |
| P1-05 | Idiographic 关联分析对 `PersDynAttractorService` 的强依赖可能导致冷启动用户完全无法分析 | P1 | `backend/app/services/idiographic_association_service.py:390` | `_build_daily_vectors` 中 5/10 维度来自 PersDynAttractorService，如果该服务对冷启动用户返回空数据，则分析质量严重下降，且 stage30_dim_count 永远为 0 导致 path_mode 永远是 "B"。 | 为冷启动场景设计降级策略：当 PersDyn 维度缺失时，用剩余行为维度独立分析，不要求 5 维全覆盖。 |

### P2 -- 建议改进

| # | 问题描述 | 严重程度 | 文件位置 | 原因分析 | 修复建议 |
|---|---------|---------|---------|---------|---------|
| P2-01 | 情感检测仅基于关键词匹配，无法识别复杂情绪表达 | P2 | `backend/app/state_aggregator/service.py:550-596` | `_classify_recent_chat_sentiment` 使用简单的关键词包含检查 (`any(kw in text for kw in keywords)`)，对多语言混合、反讽、委婉表达无法正确分类。且关键词列表硬编码在代码中。 | 考虑引入轻量级情绪分类模型 (如基于 embedding 的 few-shot 分类)，或至少将关键词列表外部化为配置。 |
| P2-02 | WorkingMemoryService 的 `_local_store` 是类变量 (class-level dict)，多实例共享状态 | P2 | `backend/app/working_memory/service.py:23` | `_local_store: dict[str, tuple[str, datetime | None]] = {}` 是类级变量，当 Redis 不可用时所有 WorkingMemoryService 实例共享同一个 dict。这在并发场景下可能导致数据竞争。 | 改为实例变量，或添加线程安全保护。 |
| P2-03 | ProfileWriteService._sync_legacy_fields 中 User/PushPreference 的同步是单向的 | P2 | `backend/app/services/profile_write_service.py:398-438` | `legacy fields (user.depth_preference, PushPreference.persona_type 等) 只在偏好变更时同步，但直接修改 User 表时不会反向同步到 UserPreferencesCenter。如果存在直接修改 User 表的代码路径，可能导致数据不一致。 | 审计所有修改 User.depth_preference/curiosity_preference/schedule_preferences 的代码路径，确保都通过 ProfileWriteService。 |
| P2-04 | PreferenceService 的 _PERSONALIZATION_CACHE 是进程内 dict，进程重启后丢失 | P2 | `backend/app/services/personalization/engine.py:605` | `_PERSONALIZATION_CACHE` 定义但实际未使用 (只有 put/pop 操作，没有 get 操作)。`invalidate_personalization_cache` 只做 pop，但没有任何地方填充此缓存。这是死代码。 | 要么移除此缓存机制，要么实现完整的缓存逻辑 (在 get_llm_profile 等方法中填充)。 |
| P2-05 | CognitiveFragment embedding 使用 deferred() 加载但 analysis 路径中直接访问 __dict__ | P2 | `backend/app/services/cognitive_service.py:363` | CognitiveFragment.embedding 标记为 `deferred()`，但 analyze_behavior 中通过 `fragment.__dict__.get("embedding")` 访问。SQLAlchemy deferred column 在 __dict__ 访问时可能不会触发加载。 | 使用显式查询加载 embedding (代码中已经有备用的 SELECT 查询)，移除 __dict__ 访问路径。 |
| P2-06 | ProfileFrontDoorService 中标题硬编码为中文 | P2 | `backend/app/services/profile_front_door_service.py:132-133` | `"title": "这是我现在对你的理解"` 和 `"headline": "当前画像前门"` 硬编码中文。违反项目 i18n 双语策略。 | 使用 ARB l10n 或 `isChinese ? '中文' : 'English'` 模式。 |
| P2-07 | StateAggregatorService 内部缓存 (_cache) 是进程内 dict，多实例部署时缓存不共享 | P2 | `backend/app/state_aggregator/service.py:110-113` | `_cache` 是实例变量，在多进程/多实例部署时各自独立缓存，可能导致不一致的 TTL 和状态。当前 TTL 30s-24h，短 TTL 的字段影响不大，但长 TTL 的字段 (learning_state=24h) 可能在不同实例间差异较大。 | 对长 TTL 字段考虑使用 Redis 共享缓存，或接受当前设计并文档化限制。 |
| P2-08 | Idiographic summary cache key 使用 SHA256 前 16 字符，理论上有碰撞风险 | P2 | `backend/app/services/idiographic_association_service.py:1031` | `_summary_cache_key` 对 user_id 做 SHA256 取前 16 字符 (64 bit)，当用户数量达到 ~4B 时碰撞概率变得不可忽略。虽然当前规模远未达到，但设计上不够健壮。 | 改为直接使用 user_id 字符串作为 cache key 的一部分 (如 `idiographic:{user_id}:summary`)，避免不必要的哈希和碰撞风险。 |
| P2-09 | ProfileContextService._get_cognitive_summary 的 PATTERN_POLICY_MAP 和 RISK_SIGNAL_MAP 中缺少部分 BehaviorPattern | P2 | `backend/app/services/profile_context_service.py:53-114` | PATTERN_POLICY_MAP 覆盖了 13 种模式名，但 CognitiveService 的 LLM 可以识别任意模式名。如果 LLM 产生了不在映射表中的模式名，该模式会被存储但不会产生策略信号，也不会出现在认知摘要的 policy_signals 中。 | 考虑为未知模式名提供默认策略信号映射，或在 LLM prompt 中约束只使用预定义的模式名。 |
| P2-10 | MemoryService.upsert_preference 的 SELECT FOR UPDATE 可能在高并发下产生锁等待 | P2 | `backend/app/services/memory_service.py:112-123` | `with_for_update()` 在同一用户同一 pref_key 的并发写入时会产生行锁等待。虽然这保证了正确性，但在批量推断更新多个 pref_key 时可能产生不必要的延迟。 | 考虑在批量操作时使用应用层锁 (如 Redis 分布式锁) 替代数据库行锁，或按 pref_key 排序写入避免死锁。 |

---

## 九、架构优点总结

1. **显式/推断分离**: UserPreferencesCenter 将 explicit 和 inferred 分开存储，显式覆盖推断，用户纠正优先
2. **append-only 审计**: MemoryPreference 形成完整的偏好变更链，支持版本追溯
3. **多层次缓存失效**: 偏好变更 -> Redis 缓存清除 -> 下次请求重新编译
4. **优雅降级**: pgvector 不可用时自动降级为无 embedding 模式，per-user 粒度控制
5. **Kill Switch 保护**: 所有 Aurora 特性都有 tri-state 控制 (off/shadow/live)
6. **矛盾检测**: ProfileTruthCompiler 的 4 条规则能检测用户自述与系统画像的冲突
7. **Idiographic 统计严谨**: BH 校正 + 密度门槛 + 用户否决 + 免责声明
8. **工作记忆隔离**: 会话级短期记忆与长期记忆分离，4h TTL 自动过期
9. **证据溯源**: 每条记忆都有 evidence_refs 引用和 evidence_score 评分
10. **推断振荡抑制**: PreferenceInferenceService 的冷却期和反向惩罚防止推断值剧烈波动
