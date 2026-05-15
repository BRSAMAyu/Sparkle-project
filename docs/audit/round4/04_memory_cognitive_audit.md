# Sparkle 记忆系统与认知棱镜深度审计报告

> 审计日期: 2026-05-15
> 审计范围: `memory_service.py` (1,320行) / `cognitive_service.py` (702行) / `behavior_signal_collector.py` (973行) / `self_model.py` (884行)
> 审计员: Opus Agent (独立审计)

---

## 第一部分: 架构分析

### 1.1 记忆服务 (MemoryService)

**文件**: `backend/app/services/memory_service.py`

**三层记忆模型**:

| 类型 | 模型 | 存储位置 | 特点 |
|------|------|----------|------|
| 偏好记忆 (Semantic) | `MemoryPreference` | PostgreSQL (JSONB) | 版本链式管理, evidence-based 置信度评分, `replaced_by_id` 链式引用 |
| 目标记忆 (Goal) | `MemoryGoal` | PostgreSQL (JSONB) | 状态机 (active/completed/archived/cancelled), 过期时间控制 |
| 情景记忆 (Episodic) | `EpisodicMemory` | PostgreSQL + pgvector | 语义向量检索, 场景聚合 (Scene), 多来源通道 (source_lane) |

**写入策略**:
- 通过 `_allow_write()` 策略评估器 (MemoryPolicyEvaluator) 控制写入权限
- 所有写入需要 evidence_refs (偏好/情景记忆) 支持, 类型限制在 `ALLOWED_EVIDENCE_TYPES` 白名单
- evidence_score 基于 `compute_score()` 计算, 支持 evidence_snapshot 快照用于高级审计
- `upsert_preference` 使用 `SELECT FOR UPDATE` 行锁防止版本竞态

**检索策略**:
- 偏好: 按 user_id + pref_key 查询最新版本 (version DESC)
- 情景: 时间范围 + subject_type 过滤, 支持 embedding 向量相似度 (但检索逻辑不在本文件)
- 会话情绪: Redis TTL (7天) 双 key 存储 (last + session)

**记忆修正与撤回**:
- 支持 retract (软删除, 设置 retracted_at) 和 revoke (针对推断类记忆)
- `apply_correction()`: 三种动作 -- reject/no_longer_applicable (撤回) / lower_confidence (降低置信度 -0.1)
- `record_memory_reference_outcome()`: 记录记忆引用结果 (accepted/corrected/ignored/denied), 动态调整置信度
- 所有修正操作记录到 `MemoryCorrection` 表用于溯源

**缺失机制**:
- 无显式记忆衰减 (decay) 实现, 虽然模型有 `decay_policy` 字段但 service 层未使用
- 无记忆总结/摘要化 (summarization) 机制
- 无用户删除后的级联清理

### 1.2 认知棱镜服务 (CognitiveService)

**文件**: `backend/app/services/cognitive_service.py`

**认知碎片 (CognitiveFragment)**:
- 多来源: capsule (闪念), interceptor (拦截器), behavior_auto (行为自动采集), tool_history, capsule_favorite
- 幂等性: 通过 `source_event_id` 防止重复创建碎片
- 内容安全: 敏感标签加密存储 (sensitive_tags_encrypted/key_id/version)
- 语义向量: pgvector 1024维, 带 graceful degradation (pgvector 不可用时回退)

**分析管线 (analyze_behavior)**:
1. 状态标记: PENDING -> PROCESSING
2. RAG 检索: Raw embedding + HyDE (Hypothetical Document Embedding) 双路检索
3. 上下文组装: 用户画像摘要 + 相似历史碎片 + 当前碎片内容
4. LLM 分析: 结构化 JSON 输出 (root_cause, pattern_name, pattern_type, description, solution_text, confidence_score)
5. 模式持久化: `_upsert_pattern()` 使用 EMA (alpha=0.3) 更新置信度
6. 事件发布: 触发 PROFILE_COGNITIVE_UPDATED 和 behavior.pattern.updated 事件

**模式匹配**:
- 当前使用精确字符串匹配 (pattern_name == pattern_name), 代码注释标明理想方案是向量搜索
- 置信度更新: EMA `0.3 * new + 0.7 * old`, 可增可减

**向量运行时降级**:
- 全局开关 `_VECTOR_RUNTIME_ENABLED` + 用户级开关 `_VECTOR_RUNTIME_DISABLED_USERS`
- 用户级开关 1 小时自动恢复, 上限 10,000 用户
- pgvector 错误自动降级为无 embedding 写入

### 1.3 行为信号采集器 (BehaviorSignalCollector)

**文件**: `backend/app/services/behavior_signal_collector.py`

**信号类型**:

| 信号 | 触发条件 | 冷却时间 |
|------|----------|----------|
| too_difficult_streak | 连续3次反馈"太难" | 24h |
| abandoned | 任务被放弃 | 24h |
| overrun_streak | 最近3次任务实际/预估>1.5x | 24h |
| plan_modifications | 24h内修改计划>=4次 | 24h |
| inactive_with_active_plan | 有活跃计划但3天无完成任务 | 24h |
| task_stuck_intervention | 卡住模式检测 | 24h |
| task_stuck_recovery | 卡住恢复检测 | 24h |
| breathing_recovery | 完成呼吸练习 | 24h |
| calculator_load | 计算器使用 (medium/complex) | 24h |
| capsule_favorite | 认知胶囊收藏操作 | 24h |
| tool_context_effect | 上下文感知工具使用 | 按记录 |

**聚合与节流**:
- Redis + 本地双重冷却机制 (Redis 不可用时 fallback 到内存 dict)
- `_maybe_update_task_inferred_preferences`: 每 5 次任务信号聚合一次推断偏好
- 加权中位数计算任务难度准确率, 滞回分类器 (hysteresis) 判断反思深度

**隐私处理**:
- 翻译工具: "原文和译文未写入工具历史" (privacy: raw_translation_text_not_stored)
- 笔记工具: "笔记原文未写入工具历史" (privacy: raw_note_text_not_stored)
- 闪念胶囊: "具体描述不写入工具历史" (privacy: raw_capsule_text_not_stored)
- 计算器: "表达式内容未被保存"

### 1.4 自我模型 (SparkleSelfModelService)

**文件**: `backend/app/aurora/runtime_v1/self_model.py`

**存储策略**: Redis 主存储 (TTL 90天) + PostgreSQL 备份 (AuroraStateSnapshot)

**五大假设追踪**:
1. daily_available_time -- 日可用学习时长
2. task_duration_fit -- 任务时长匹配度
3. task_difficulty_fit -- 任务难度匹配度
4. pressure_level_fit -- 压力强度匹配度
5. emotional_state_fit -- 情绪状态匹配度

**校准机制**:
- 任务完成: 各假设 +0.01~0.02
- 任务超时/失败: 各假设 -0.04~-0.12
- 用户纠正: 关键词匹配后 -0.06~-0.08
- 连续3次失败: 额外 -0.05
- 贝叶斯策略校准: 60% 权重给贝叶斯校准值, 40% 给当前值

**重新校准触发条件** (任一):
- 连续3次失败
- 任务完成率 < 55% (至少3个信号)
- 用户纠正 >= 2次
- 2个以上假设置信度 < 0.45

### 1.5 集成流程

```
用户行为事件
    |
    v
BehaviorSignalCollector.handle_*_event()
    |-- 冷却检查 (Redis/本地)
    |-- 条件判断 (阈值/模式检测)
    |
    v
CognitiveService.create_fragment()          -> CognitiveFragment (DB)
    |-- 幂等检查 (source_event_id)
    |-- Embedding 生成 (pgvector)
    |-- 事件发布 (cognitive.fragment.created)
    |
    v
CognitiveService.analyze_behavior()         -> BehaviorPattern (DB)
    |-- RAG 检索 (Raw + HyDE)
    |-- LLM 分析 (结构化 JSON)
    |-- EMA 置信度更新
    |-- 事件发布 (behavior.pattern.updated)
    |
    v
MemoryService.upsert_preference()           -> MemoryPreference (DB)
    |-- SELECT FOR UPDATE 行锁
    |-- 版本链更新
    |-- 进化追踪 (MemoryEvolutionService)
    |
    v
SparkleSelfModelService.record_*()          -> Redis + PG 备份
    |-- 假设调整
    |-- 贝叶斯校准
    |
    v
Prompt 组装 (通过 DualCoreRouter + ContextOrchestrator)
```

---

## 第二部分: 问题报告

### P0 级问题 (数据丢失/安全/崩溃)

#### P0-01: 缺失用户删除后的记忆数据清理
- **位置**: 全局 (memory_service.py / cognitive_service.py / behavior_signal_collector.py / self_model.py)
- **描述**: 当用户请求删除账户 (GDPR/隐私法规) 时, 系统缺少级联清理机制。代码库中不存在 `purge_user_data()` 或 `forget_user()` 类函数。记忆偏好、情景记忆、认知碎片、行为模式、自我模型 (Redis + PG)、会话情绪 (Redis)、校准回执 (Redis)、行为信号冷却记录 (Redis) 均无法批量清除。
- **影响**: 违反 GDPR "被遗忘权"; 删除用户后, 其全部 AI 画像和行为数据仍在系统中残留; 潜在的法律合规风险。
- **建议修复**:
  1. 实现 `MemoryService.purge_user_data(user_id)` 方法, 批量软删除/硬删除所有关联记录
  2. 实现 `CognitiveService.purge_user_data(user_id)` 方法
  3. 添加 Redis key pattern 清理: `memory:session_mood:{user_id}:*`, `aurora:self_model:{user_id}`, `aurora:recent_corrections:{user_id}:*`, `behavior:auto:cooldown:{user_id}:*`, `behavior:plan_mods:{user_id}:*`, `behavior:task_inferred_counter:{user_id}`
  4. 在用户删除 API 中调用清理链

#### P0-02: 全局向量开关导致跨用户影响
- **位置**: `cognitive_service.py:37-39, 69-73`
- **描述**: `_VECTOR_RUNTIME_ENABLED` 是一个全局布尔变量, 不与任何用户绑定。当任何一个用户的 pgvector 操作触发 `_disable_vector_runtime()` 时, 所有用户的向量功能都被禁用。虽然有用户级降级 `_VECTOR_RUNTIME_DISABLED_USERS`, 但全局开关的影响范围是无差别的。
- **影响**: 一个用户的 pgvector 错误 (如数据损坏) 可以导致全体用户的认知分析降级为无 embedding 模式; 认知碎片 RAG 检索失效, 行为模式识别质量下降; 系统恢复需要手动重启服务。
- **建议修复**:
  1. 移除全局 `_VECTOR_RUNTIME_ENABLED` 开关, 完全依赖用户级降级
  2. 或将全局开关改为 per-database/per-connection 级别, 而非 per-process
  3. 添加自动恢复机制 (当前仅用户级有 1h TTL, 全局无自动恢复)

### P1 级问题 (正确性/可靠性)

#### P1-01: 行为模式查询未过滤已软删除记录
- **位置**: `cognitive_service.py:589-594` (`_upsert_pattern`) 和 `cognitive_service.py:690-702` (`get_user_patterns`)
- **描述**: `_upsert_pattern()` 查询 `BehaviorPattern` 时仅用 `user_id == user_id AND pattern_name == pattern_name`, 未加 `deleted_at IS NULL` 过滤。`get_user_patterns()` 同样缺少 `deleted_at` 过滤。由于 `BehaviorPattern` 继承 `BaseModel` (有 deleted_at), 软删除的模式仍会被查询到并参与更新。
- **影响**: 用户已删除的行为模式可能被重新激活; 置信度 EMA 计算基于本应被忽略的历史数据; 可能向用户展示已标记删除的模式。
- **建议修复**: 在所有 BehaviorPattern 查询中添加 `.where(BehaviorPattern.deleted_at.is_(None))`。

#### P1-02: 认知碎片 RAG 查询未过滤已软删除/已撤回记录
- **位置**: `cognitive_service.py:381-389` 和 `cognitive_service.py:416-424` (RAG 查询)
- **描述**: `analyze_behavior()` 中的 RAG 相似度检索查询只过滤了 `user_id`、`embedding IS NOT NULL`、`id != fragment_id`, 未排除已删除 (`deleted_at IS NOT NULL`) 的碎片。已删除的认知碎片仍会作为上下文输入 LLM 分析。
- **影响**: 用户明确删除的内容仍可能影响行为分析结果; 分析质量下降 (引用了本应不存在的数据)。
- **建议修复**: 在 RAG 查询中添加 `.where(CognitiveFragment.deleted_at.is_(None))`。

#### P1-03: `_upsert_pattern` 无行锁, 存在竞态条件
- **位置**: `cognitive_service.py:589-594`
- **描述**: `_upsert_pattern()` 查询现有模式后决定创建或更新, 但未使用 `SELECT FOR UPDATE`。与 `upsert_preference()` (已使用 `with_for_update()`) 不同, 模式更新完全无锁保护。并发行为事件可能同时读取同一 pattern, 导致 frequency 计数和 evidence_ids 丢失。
- **影响**: 并发行为分析可能导致 `frequency += 1` 被覆盖 (只加了一次而非两次); evidence_ids 可能丢失新增的 fragment_id 引用; 置信度 EMA 计算不准确。
- **建议修复**: 使用 `with_for_update()` 锁定查到的 pattern 行, 或使用数据库级别的 UPSERT (ON CONFLICT) 操作。

#### P1-04: 认知分析 LLM prompt 包含用户完整画像, 存在过度暴露风险
- **位置**: `cognitive_service.py:453-484` (分析 prompt 构建)
- **描述**: `analyze_behavior()` 将 `user_summary` (通过 `get_user_profile_summary()` 获取的完整用户画像文本) 直接嵌入 prompt, 与原始碎片内容和相似历史碎片一起发送给 LLM。prompt 未对敏感信息 (如焦虑分数、情绪指标) 做脱敏处理。
- **影响**: 用户画像中的敏感心理健康指标 (anxiety_score, 情绪标签) 进入 LLM 上下文; 如果 LLM 服务存在日志或缓存, 敏感数据可能泄露; prompt 中包含大量个人数据, 增加了 LLM 产生有偏分析的概率。
- **建议修复**:
  1. 对 `user_summary` 中的敏感指标做脱敏/聚合处理 (如 "近期焦虑指数: 中等" 而非原始数值)
  2. 限制 prompt 中相似碎片的数量和详细程度
  3. 审计 LLM 服务的日志和缓存策略

#### P1-05: 记忆引用结果 "ignored" 不产生任何效果
- **位置**: `memory_service.py:1153` (record_memory_reference_outcome)
- **描述**: `MEMORY_REFERENCE_OUTCOMES = {"accepted", "corrected", "ignored", "denied"}` 定义了四种结果, 但在 `record_memory_reference_outcome()` 中, `ignored` 结果不触发任何置信度调整 (仅 accepted 和 corrected/denied 有逻辑)。一条反复被 "忽略" 的记忆, 其置信度不会降低, 持续被选入 prompt。
- **影响**: 不相关或低质量记忆持续占据 prompt 空间; 记忆选择质量无法通过隐式反馈 (忽略) 自我优化。
- **建议修复**: 为 "ignored" 结果添加小幅置信度衰减 (如 -0.02), 或在连续 N 次忽略后自动降低置信度。

#### P1-06: 情景记忆向量写入失败时静默丢弃
- **位置**: `memory_service.py:790-836`
- **描述**: `create_episodic_memory()` 在第一次 commit 因 pgvector 错误失败时, 会尝试无 embedding 重试。但如果第二次也失败 (非 pgvector 错误), 则静默返回 `None` 且仅记录 warning 日志。调用方可能不知道记忆未被存储。
- **影响**: 用户明确创建的记忆可能在静默中丢失; 无异常抛出, 上层无法感知失败。
- **建议修复**: 在第二次重试仍失败时抛出异常或返回更明确的状态, 而非静默返回 None。

#### P1-07: 行为信号冷却依赖实例级内存 dict, 多实例部署时失效
- **位置**: `behavior_signal_collector.py:86` (`self._local_cooldowns`)
- **描述**: `_local_cooldowns` 是实例级别的 `dict`, 当 Redis 不可用时作为 fallback。在多实例部署中, 不同实例有各自的 `_local_cooldowns`, 同一用户的信号可能在不同实例上绕过冷却。
- **影响**: 行为信号可能在冷却期内被重复发出; 认知碎片重复创建; 信号放大导致行为分析偏差。
- **建议修复**: 将冷却状态完全依赖 Redis, 实例级 dict 仅作为 Redis 暂时不可用时的短期缓冲 (带更短 TTL); 或使用分布式锁。

### P2 级问题 (性能/质量)

#### P2-01: 行为模式名称精确匹配导致模式碎片化
- **位置**: `cognitive_service.py:589-594`
- **描述**: `_upsert_pattern()` 使用 `pattern_name == pattern_name` 精确字符串匹配来查找现有模式。由于 pattern_name 由 LLM 生成, 同一行为模式可能因措辞差异被创建为多个独立模式 (如 "Planning Fallacy" vs "计划谬误" vs "过度乐观估计")。代码注释已承认: "Simple string matching for now. Ideal: Vector search on pattern descriptions."
- **影响**: 行为模式碎片化, 同一用户出现多个语义相同但名称不同的模式; 置信度分散, 无法累积到同一模式上; 向用户展示重复的模式发现通知。
- **建议修复**:
  1. 使用 embedding cosine similarity 对 pattern_name/description 做模糊匹配 (阈值 0.85+)
  2. 或维护一个标准化模式名映射表, LLM 输出后先归一化再匹配
  3. 短期方案: 对 pattern_name 做文本归一化 (lowercase + strip + 去除标点) 后匹配

#### P2-02: HyDE 生成增加延迟但可能无收益
- **位置**: `cognitive_service.py:398-436`
- **描述**: HyDE (Hypothetical Document Embedding) 仅在碎片内容 < HYDE_QUERY_LENGTH_THRESHOLD 时启用。短文本生成假设文档并做第二次 embedding + 向量检索, 增加了约 1-2 秒延迟 (有 HYDE_LATENCY_BUDGET_SEC 超时保护)。但对于行为自动采集的碎片 (如 "用户放弃了任务《xxx》"), HyDE 生成的假设文档质量可能不高。
- **影响**: 不必要的延迟增加; LLM 调用成本增加; 对行为碎片可能无检索质量提升。
- **建议修复**: 根据碎片 source_type 决定是否启用 HyDE (behavior_auto 类碎片可跳过); 或对 HyDE 检索结果做质量评估, 记录命中率后自适应。

#### P2-03: 置信度 EMA alpha=0.3 可能导致旧模式难以更新
- **位置**: `cognitive_service.py:605-606`
- **描述**: 行为模式置信度更新使用 EMA `alpha * new + (1-alpha) * old`, alpha=0.3。这意味着新观察只占 30% 权重。对于一个已观察 10 次的模式 (confidence=0.9), 即使后续连续获得低置信度观察 (0.4), 也需要约 5-6 次才能降至 0.7 以下。
- **影响**: 用户行为已改变时, 旧模式置信度下降缓慢; AI 行为调整滞后; 可能向用户展示过时的行为模式。
- **建议修复**: 考虑自适应 alpha (频率越高, alpha 越大, 即越信任新观察); 或引入基于时间衰减的权重调整。

#### P2-04: 自我模型 processed_signal_ids 无界增长风险
- **位置**: `self_model.py:402` 和 `self_model.py:598-601`
- **描述**: `processed_signal_ids` 列表使用 `[-_MAX_SIGNAL_IDS:]` 截断 (_MAX_SIGNAL_IDS=100)。虽然上限为 100, 但整个 self-model state 以 JSON 存储在 Redis, 每次读写都序列化/反序列化完整 state。当 state 中包含大量数据 (5 个假设 x 5 条 evidence + 100 个 signal IDs), 单次 Redis SET 约 2-5KB。
- **影响**: 高频任务场景下 Redis 写入频率高 (每次任务完成都写); 序列化/反序列化开销; 对 Redis 内存占用有一定压力。
- **建议修复**: 考虑将 processed_signal_ids 改为 Redis SET 数据结构单独存储 (SISMEMBER 检查), 减少 state 整体序列化开销。

#### P2-05: 认知碎片创建每次都发送 SystemUpdate, 可能造成通知洪水
- **位置**: `cognitive_service.py:245-258`
- **描述**: `create_fragment()` 每次都调用 `SystemUpdateService().enqueue()` 发送 "捕捉到新线索" 系统更新。在高活跃期 (如用户完成多个任务触发多个行为信号), 可能在短时间内产生大量系统通知。
- **影响**: 通知泛滥, 用户可能忽略重要通知; SystemUpdateService 队列压力增加。
- **建议修复**: 对 behavior_auto 类碎片降低通知频率 (如聚合后每日摘要), 或使用 system_update 的优先级机制做展示侧节流。

#### P2-06: 记忆进化追踪失败被静默吞没
- **位置**: `memory_service.py:159-187` (偏好进化) 和 `memory_service.py:503-524` (目标进化)
- **描述**: `MemoryEvolutionService.track_memory_change()` 调用被 `NON_CRITICAL_SERVICE_ERRORS` 异常捕获后仅记录 warning 日志。进化追踪的失败意味着记忆变更历史丢失, 但主写入路径不受影响。
- **影响**: 记忆进化图谱可能不完整; 审计时无法回溯完整的记忆变更链。
- **建议修复**: 将进化追踪失败记录到专用错误队列或指标, 以便监控追踪失败率。

#### P2-07: 认知碎片 embedding 生成失败时无后续重试机制
- **位置**: `cognitive_service.py:213-219`
- **描述**: `create_fragment()` 中 embedding 生成失败后, 碎片以无 embedding 状态存入数据库。注释说 "RAG won't work for this item until updated", 但代码中不存在后续重试或补偿机制。
- **影响**: 部分认知碎片永远无法被 RAG 检索到; 随着时间推移, RAG 覆盖率逐渐下降。
- **建议修复**: 实现后台任务定期扫描无 embedding 的碎片并重试生成; 或在 `_insert_fragment_without_embedding()` 后发布事件触发异步重试。

---

## 附录: 审计摘要

| 严重级别 | 数量 | 问题编号 |
|----------|------|----------|
| P0 (数据丢失/安全/崩溃) | 2 | P0-01, P0-02 |
| P1 (正确性/可靠性) | 7 | P1-01 ~ P1-07 |
| P2 (性能/质量) | 7 | P2-01 ~ P2-07 |
| **合计** | **16** | |

**最紧急修复建议**:
1. (P0-01) 实现用户数据级联清理 -- 合规必需
2. (P0-02) 消除全局向量开关的跨用户影响 -- 可靠性必需
3. (P1-01/P1-02) 在所有查询中添加 deleted_at 过滤 -- 数据正确性必需
4. (P1-03) 为 _upsert_pattern 添加行锁 -- 并发安全必需
