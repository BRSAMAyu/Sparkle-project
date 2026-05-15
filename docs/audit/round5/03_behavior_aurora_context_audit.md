# Round 5 审计报告：行为信号采集 / Aurora L3 核心 / 上下文修剪器

**审计日期**: 2026-05-15
**审计范围**: BehaviorSignalCollector, L3FullCoreEngine, ContextPruner
**审计人**: Claude Opus Agent

---

## 第一部分：架构分析

### 1. BehaviorSignalCollector（行为信号采集器）

**文件**: `backend/app/services/behavior_signal_collector.py`（973 行）

#### 信号类型

BehaviorSignalCollector 负责将低级别用户行为事件聚合并转化为认知片段（CognitiveFragment）。共处理以下 7 种事件入口：

| 事件处理器 | 触发源 | 产生信号 |
|------------|--------|----------|
| `handle_task_feedback_event` | 任务反馈 | too_difficult_streak, inactivity, pattern_adjustment, task_inferred_preferences |
| `handle_task_abandoned_event` | 任务放弃 | 放弃片段 + task_stuck_intervention + inactivity |
| `handle_task_stuck_event` | 任务卡点 | task_stuck_intervention |
| `handle_task_completed_event` | 任务完成 | overrun_pattern + task_stuck_recovery + inactivity + task_inferred_preferences |
| `handle_plan_replanned_event` | 计划修改 | plan_modification_tracking + inactivity |
| `handle_tool_history_event` | 工具使用 | breathing_recovery / calculator_load / tool_context_effect |
| `handle_behavior_pattern_event` | 行为模式 | AdaptiveReplanner 触发 + BehaviorInterventionBridge 卡片协议 |
| `handle_capsule_favorite_event` | 胶囊收藏 | 偏好信号片段 |

#### 冷却管理（Cooldown）

采用双层冷却策略：

- **Redis 层**（主）：通过 `setex` 设置 TTL 键 `behavior:auto:cooldown:{user_id}:{signal_key}`，默认 24 小时
- **本地内存层**（备）：`_local_cooldowns` 字典存 datetime 过期时间，当 Redis 不可用时降级使用
- 回退路径：`_signal_on_cooldown` 在 Redis 异常时（ConnectionError, OSError, TimeoutError, RedisError）自动降级到本地字典

#### 认知片段创建模式

所有信号最终汇聚到 `cognitive_service.create_fragment()`，统一模式为：
1. 冷却检查 -> 2. 数据查询/聚合 -> 3. 创建 fragment -> 4. `analyze_behavior` -> 5. 标记冷却
每个 fragment 携带 `source_type`、`context_tags`（含 signal_key）、`error_tags`、`severity`（1-3）。

#### 推断偏好更新

`_maybe_update_task_inferred_preferences` 使用 Redis 计数器每 5 次信号聚合一次，基于近 14 天任务和反馈数据计算：
- `task_reflection_depth`（none/light/deep，带滞后带分类）
- `difficulty_feedback_ratio`（加权比例）
- `task_difficulty_accuracy`（加权中位数）

---

### 2. L3FullCoreEngine（Aurora L3 全核心）

**文件**: `backend/app/aurora/runtime_v1/l3_full_core.py`（497 行）

#### 会话生命周期

```
active → paused → completed → reflected
                ↘ abandoned
```

状态转移严格受 `SESSION_LIFECYCLE` 字典约束，终态为 `reflected` 和 `abandoned`。

#### 唤醒条件（Wake Conditions）

系统定义了 8 种标准唤醒条件，按优先级排序：

| 优先级 | 唤醒键 | 会话类型 | 时长 |
|--------|--------|----------|------|
| 1 | deadline_high_risk | exam_emergency | 300s |
| 2 | model_conflict | conflict_resolution | 180s |
| 3 | consecutive_user_rejections | belief_revision | 240s |
| 4 | consecutive_strategy_failures | strategy_recalibration | 240s |
| 5 | goal_changed | goal_realignment | 300s |
| 6 | self_model_confidence_dropped | self_model_recalibration | 240s |
| 7 | user_explicit_wake | deep_review | 300s |
| 8 | momentum_stalled | motivation_check | 240s |

#### 议程执行（Agenda Execution）

`execute_agenda_step` 实现：
1. 从 Redis 加载会话 -> 2. 验证会话状态为 active/paused -> 3. 记录用户回复 -> 4. 检查最大轮次（12）或议程完成 -> 5. 返回下一议程项 + 预测回复选项

每个议程项默认提供 3 个预测回复选项："是，确认" / "不完全对" / "都不对，我解释一下"。

#### 健康检查机制

`check_session_health` 执行三项检查：
- 最大会话年龄：24 小时 -> abandon
- 最大回复轮次：12 -> force_close
- 空闲超时：10 分钟 -> pause

#### 闭包产出（Closure）

`produce_closure` 从议程项中提取用户回复，映射为：
- `StatePatch`：状态键值变更（task_granularity_fit, knowledge_bottleneck）
- `PolicyChange`：策略变更（触发 PlanDirective 重新生成）
- `directives_to_regenerate`：默认包含 ExecutionDirective + ResponseDirective

---

### 3. ContextPruner（上下文修剪器）

**文件**: `backend/app/orchestration/context_pruner.py`（341 行）

#### 三层压缩策略

| 层级 | 条件 | 策略 | 产出 |
|------|------|------|------|
| 第 1 层 | 消息数 <= max_history（默认10） | 完整保留 | 原始消息 |
| 第 2 层 | 消息数 <= importance_threshold（默认30） | 规则压缩 | 低信号简述 + 近期完整 |
| 第 3 层 | 消息数 > importance_threshold | 同步摘要 + 锚点保留 | 摘要 + 锚点 + 近期 |

#### 摘要机制

第 3 层摘要使用 FAST 模型（`ModelTier.FAST`）同步生成：
- 提取近 4 条消息保持完整
- 早期消息中的锚点消息（tool_calls、计划关键词）保持完整
- 其余消息用 LLM 生成 100 字以内中文摘要
- 摘要缓存：基于 SHA1(messages) 的 Redis 键，TTL 默认 1 小时

#### 重要性判断

**高重要性**：包含工具调用，或含 "计划/任务/目标/焦虑/卡住/想放弃" 等关键词。
**低信号**：空内容，或匹配预定义短语集（"好的"/"嗯"/"ok" 等），或长度 <= 12 字符。
**锚点**：工具调用 + 高重要性 + 含 "计划已创建/任务完成/阶段/里程碑" 等锚点关键词。

#### 全局单例模式

`get_context_pruner()` 使用模块级 `context_pruner_instance` 全局单例，首次调用需传入 Redis 客户端，后续调用自动复用，支持 Redis 重连时替换客户端。

---

## 第二部分：问题报告

### 问题 1：任务标题未经脱敏直接嵌入认知片段内容

- **严重性**: P1
- **位置**: `behavior_signal_collector.py:115`
- **描述**: `handle_task_abandoned_event` 中，任务标题 `title` 直接拼接进认知片段的 `content` 字段（`f"用户放弃了任务《{title}》"`）。任务标题可能包含用户的敏感信息（如"准备面试——XX公司"、"看病——XX医院"等），这些内容会通过 `CognitiveService` 写入数据库，并可能在后续分析/日志/向量检索中暴露。
- **影响**: PII 泄露风险。认知片段会被 `analyze_behavior` 处理、可能被向量化存储（`CognitiveService` 使用 pgvector），一旦嵌入向量索引则难以彻底删除。同样的模式也出现在第 363 行（`too_difficult_streak`）、第 402 行（`overrun_pattern`）、第 502 行（`task_stuck_intervention`）、第 306 行（`capsule_favorite`）。
- **修复建议**: 引入统一的标题脱敏函数，在写入认知片段 `content` 之前截断或哈希化标题（如仅保留前 10 字符 + `...`）。对于 `context_tags` 中的 `task_title` 字段同理处理。建议与 `aurora/privacy.py` 的 PII redaction 管道对齐。

### 问题 2：`_local_cooldowns` 实例级字典在多实例部署下失效

- **严重性**: P1
- **位置**: `behavior_signal_collector.py:86`
- **描述**: `_local_cooldowns` 是实例级别的普通字典。在多实例部署（多个 Python gRPC worker）场景下，每个实例维护独立的冷却状态。当 Redis 不可用时降级到本地字典，不同实例之间无法共享冷却信息，导致同一个信号可能被多个实例同时触发，产生重复的认知片段。
- **影响**: 生产环境中 Redis 短暂不可用时（网络抖动、Redis 重启），信号风暴风险——同一用户同一信号被多个 worker 重复触发，产生冗余片段和不必要的 LLM 调用。
- **修复建议**: (1) 在 `_mark_signal_emitted` 中，即使本地冷却标记成功也应检查 Redis 是否恢复并尝试补偿写入。(2) 考虑使用 Redis 持久化作为唯一的冷却存储，本地缓存仅作为 Redis 超时（而非错误）场景的短期缓冲。(3) 或引入 Redis Lua 脚本实现原子性的 check-and-set。

### 问题 3：`validate_entry` 允许任意字符串触发 L3 会话

- **严重性**: P1
- **位置**: `l3_full_core.py:189-196`
- **描述**: 当 `wake_reasons` 中的所有字符串都不匹配预定义的 8 个唤醒条件时，`validate_entry` 仍返回 `allowed=True`，使用 `strategy_recalibration` 作为默认 session_type，并将 `wake_reasons[0]` 作为 `matched_condition`。这意味着任何非空字符串数组都能通过验证。
- **影响**: L3 是"高成本、限配额"的认知校准事件。未定义的唤醒原因不应自动进入 L3 会话——可能被上游 bug 或恶意构造的事件意外触发，消耗用户配额并产生不必要的 LLM 开销。`matched_condition` 被设为任意字符串也会污染下游的遥测和审计数据。
- **修复建议**: 将默认分支改为拒绝（`allowed=False, reason="unknown_wake_reason"`）。如果确实需要灵活扩展，应建立一个注册表机制（如 Redis 中的动态配置或数据库表），明确记录允许的自定义唤醒原因，而非接受任意值。

### 问题 4：全局 `vector_runtime` 开关影响所有用户

- **严重性**: P1
- **位置**: `cognitive_service.py:37-73`（L3 通过 `AuroraCoreSessionService` -> `CognitiveService` 间接依赖）
- **描述**: `_VECTOR_RUNTIME_ENABLED` 是模块级全局布尔值。当一个用户的 pgvector 操作触发错误时，`_disable_vector_runtime()` 将其设为 `False`，导致所有用户的向量化操作被禁用。虽然已有按用户禁用机制（`_VECTOR_RUNTIME_DISABLED_USERS`），但全局开关仍然是第一道门——一旦全局关闭，按用户检查根本不会执行（第 82 行：`if not _VECTOR_RUNTIME_ENABLED: return False`）。
- **影响**: 一个用户的 pgvector 故障（如临时索引损坏）会导致全平台用户的认知片段向量化功能不可用，影响认知检索质量。`seed_library_service.py` 中存在完全相同的模式（`_SEED_VECTOR_RUNTIME_ENABLED`）。
- **修复建议**: 移除全局 `_VECTOR_RUNTIME_ENABLED` 开关，仅保留按用户禁用机制。初始状态下所有用户默认启用，仅出错用户被临时禁用（已有 1 小时 TTL 自动恢复机制）。如果确实需要全局开关，应使用数据库/Redis 配置而非进程内变量，确保多实例间一致。

### 问题 5：`len(content) <= 12` 分类为"低信号"对非中文文本过于激进

- **严重性**: P2
- **位置**: `context_pruner.py:217`
- **描述**: `_is_low_signal_message` 使用 `len(content) <= 12` 作为低信号判断条件。对中文而言，12 个字符可能构成完整句子（如"我今天状态不太好" = 8 字符），但对英文/拼音输入而言，12 个字符可能只是 "Yes, I agree"（12 字符，有意义）或 "I need help"（11 字符，高信号）。更重要的是，一个简短但关键的回答如 "放弃"（2 字符）实际上被列入了 `low_signal_values` 白名单，而 "不要放弃"（4 字符）由于长度 <= 12 也会被误判为低信号。
- **影响**: 用户的简短但关键回复（特别是非中文用户）可能在第 2 层压缩中被降级为简述，丢失上下文信息，影响 LLM 后续推理质量。
- **修复建议**: (1) 将长度阈值从 12 调整为更保守的值（如 6），或按语言/字符类型动态调整（CJK 字符权重更高）。(2) 在长度判断之前先检查是否包含高重要性关键词（`_is_high_importance_message` 已有定义，应在此处复用）。(3) 对于长度 <= 12 但不在 `low_signal_values` 集合中的消息，应保留原始内容。

### 问题 6：`user_id` 参数被显式忽略，无个性化摘要

- **严重性**: P2
- **位置**: `context_pruner.py:115`
- **描述**: `_get_summarized_history` 接收 `user_id` 参数但立即通过 `del user_id` 丢弃，并注释"保留参数位，后续可用于个性化总结"。摘要 prompt 是硬编码的中文指令："用中文简洁总结以下对话的关键信息"。不同用户可能有不同的语言偏好（英文用户、多语言用户），也可能有不同的关注重点。
- **影响**: (1) 非中文用户收到的摘要是中文生成的，可能与对话语言不一致。(2) 缓失了利用用户画像（如当前目标、已知偏好）优化摘要质量的机会。
- **修复建议**: (1) 根据 `user_id` 查询用户语言偏好，动态选择摘要 prompt 语言。(2) 可在摘要 prompt 中注入用户当前目标和阶段信息（来自 PlanState），使摘要更有针对性。(3) 删除 `del user_id`，改为实际使用。

### 问题 7：`_get_last_activity` 未正确提取最新活动时间

- **严重性**: P1
- **位置**: `l3_full_core.py:438-452`
- **描述**: `_get_last_activity` 方法的实现有逻辑缺陷。第 441 行执行了 `session.get("agenda", {}).get("agenda_items", [])` 但结果未被赋值给任何变量。方法仅从 `created_at` 获取时间戳并返回，完全忽略了议程项中的活动记录。这意味着空闲超时检查（`check_session_health` 中的 10 分钟 idle timeout）永远不会基于实际用户交互时间触发——只要会话创建时间在 10 分钟内，即使议程项已全部完成也不会触发暂停。
- **影响**: 空闲会话自动暂停机制失效。用户可能打开 L3 会话后离开，会话在 10 分钟内不会自动暂停（除非创建时间超过 10 分钟），占用配额和 Redis 资源。
- **修复建议**: 遍历议程项，找到最新 `status == "done"` 的项的时间戳作为 last_activity。如果议程项没有独立时间戳，可使用 `updated_at` 字段或从 `record_reply` 时注入时间戳。

### 问题 8：认知片段中任务标题多处重复泄露

- **严重性**: P1
- **位置**: `behavior_signal_collector.py:119`（context_tags 中 `task_title`）
- **描述**: 不仅是 `content` 字段，`context_tags` 字典中也直接存储了 `task_title: title`（第 119 行）、`capsule_title`（第 327 行）。这些 context_tags 会被持久化到数据库，并可能通过 API 返回给前端。
- **影响**: 与问题 1 相同的 PII 泄露路径，但更隐蔽——`context_tags` 是结构化数据，可能被日志系统、分析管道单独索引。
- **修复建议**: 与问题 1 统一处理，在 `context_tags` 中也应脱敏或使用 ID 引用替代。

### 问题 9：BehaviorSignalCollector 中 handle_behavior_pattern_event 存在双重 commit 风险

- **严重性**: P2
- **位置**: `behavior_signal_collector.py:210-263`
- **描述**: `handle_behavior_pattern_event` 在第 263 行执行 `await self.db.commit()`，但此方法内部先调用了 `AdaptiveReplanner.on_behavior_pattern_detected`（第 198 行），再调用 `BehaviorInterventionBridge.on_behavior_pattern`（第 212 行）。如果 AdaptiveReplanner 内部也执行了 commit，则第 263 行的 commit 是多余的；如果 AdaptiveReplanner 依赖同一事务，则中间的 `begin_nested()` savepoint 可能导致部分提交部分回滚的不一致状态。
- **影响**: 在高并发信号处理场景下可能出现数据不一致——intervention 记录已提交但 replanner 的调整未提交，或反之。
- **修复建议**: 统一事务管理策略。建议使用 `begin_nested()` savepoint 包裹所有操作，在方法末尾统一 commit。或将 AdaptiveReplanner 和 Bridge 的调用改为同一事务链。

### 问题 10：ContextPruner 摘要 prompt 硬编码中文，与 i18n 策略冲突

- **严重性**: P2
- **位置**: `context_pruner.py:161-164`
- **描述**: `_summarize_sync` 中的 prompt 和 system message 完全硬编码为中文（"用中文简洁总结以下对话的关键信息"、"你是对话总结助手"）。根据项目 CLAUDE.md 中的 i18n 策略（`isChinese ? '中文' : 'English'`），用户可能使用英文交互，但摘要始终以中文生成。
- **影响**: 英文对话的摘要质量下降——FAST 模型可能将英文对话翻译为中文摘要，丢失语义精度。双语混合对话的摘要可能偏向中文。
- **修复建议**: 检测历史消息的主要语言（可统计中文字符比例），动态切换摘要 prompt 语言。或利用 `user_id` 参数（当前被忽略）查询用户语言偏好。

### 问题 11：ContextPruner 全局单例在测试和热重载场景下可能持有过时 Redis 连接

- **严重性**: P2
- **位置**: `context_pruner.py:324-341`
- **描述**: `get_context_pruner()` 使用模块级全局变量 `context_pruner_instance`。虽然第 337-339 行处理了 Redis 客户端替换，但比较逻辑 `context_pruner_instance.redis is not redis_client` 使用身份比较（`is`）而非相等比较。如果 Redis 客户端被重新包装（如连接池重建），身份比较可能失败。
- **影响**: 在开发环境热重载或 Redis 故障恢复后，ContextPruner 可能持有已断开的 Redis 连接，导致摘要缓存读写失败。
- **修复建议**: (1) 使用更健壮的连接健康检查（如 `redis.ping()`）而非身份比较。(2) 考虑使用依赖注入框架管理生命周期，而非手动单例。

---

## 问题汇总

| # | 严重性 | 文件 | 行号 | 简述 |
|---|--------|------|------|------|
| 1 | P1 | behavior_signal_collector.py | 115 | 任务标题未脱敏直接嵌入片段 content（PII 风险） |
| 2 | P1 | behavior_signal_collector.py | 86 | _local_cooldowns 多实例部署下冷却失效 |
| 3 | P1 | l3_full_core.py | 189-196 | 任意字符串可触发 L3 会话 |
| 4 | P1 | cognitive_service.py | 37-73 | 全局 vector_runtime 开关影响全平台用户 |
| 5 | P2 | context_pruner.py | 217 | len<=12 低信号判断对非中文文本过于激进 |
| 6 | P2 | context_pruner.py | 115 | user_id 被显式忽略，摘要无个性化 |
| 7 | P1 | l3_full_core.py | 438-452 | _get_last_activity 未正确提取活动时间，空闲超时失效 |
| 8 | P1 | behavior_signal_collector.py | 119 | context_tags 中 task_title 同样存在 PII 泄露 |
| 9 | P2 | behavior_signal_collector.py | 210-263 | 双重 commit 风险，事务管理不统一 |
| 10 | P2 | context_pruner.py | 161-164 | 摘要 prompt 硬编码中文，与 i18n 策略冲突 |
| 11 | P2 | context_pruner.py | 324-341 | 全局单例 Redis 连接身份比较不可靠 |

**P1 问题**: 6 个（问题 1, 2, 3, 4, 7, 8）
**P2 问题**: 5 个（问题 5, 6, 9, 10, 11）

**建议优先修复顺序**: 问题 4（全局影响面最大）> 问题 3（安全漏洞）> 问题 1+8（PII 合规）> 问题 7（功能缺陷）> 问题 2（生产韧性）> 其余 P2
