# Sparkle 前沿理念融合可行性综合分析报告

> **版本**: 4.0 (三轮审查版) | **日期**: 2026-04-19 | **输入**: 5份 Deep Research 报告
> **范围**: 长期陪伴型Agent | Social Brain | Agent系统架构 | Skill自进化 | Model Router
> **验证方式**: 5个并行Agent对全部关键子系统的代码级深度审查
> **评审历史**: v2.0代码验证 → v3.0同行评审(6补充+3挑战) → v4.0关键事实修正(6项)
> **锚定状态**: 已纳入 Stage 16 final-accept / Stage 17 dispatch 文档链路，作为 Roadmap v2.0 的前沿理念输入基线

---

## 一、执行摘要

本报告对5份前沿研究报告中的先进理念与Sparkle代码库进行了**逐文件验证式**的融合分析。核心发现：

**Sparkle不是"功能缺失"，而是"连接断裂"**。系统拥有143张表、37个模块、19+事件类型、23个agent profile、10+ model tier、5+ LLM provider——基础设施远比表面看到的强大。真正的问题在于**已实现的子系统之间的信号流断裂**：

1. **MemoryService是"半Ghost Ship"（v4.0修正）**：4种记忆类型完整实现，57个preference key已定义，embedding已支持。**读路径已连通**——通过`orchestrator.py:1718`无条件调用`_apply_context_focus_overlay()` → `ContextPackBuilder` → `list_preference_records()` + `list_active_goals()` + `list_recent_episodic()`。**但写路径完全断开**——chat flow中没有从对话结果写入MemoryService的逻辑，用户在对话中表达的新偏好、新目标不会被记录。
2. **Proactive引擎已存在但太弱**：SchedulerService每15分钟运行Smart Push Cycle，5种策略（Sprint/Memory/EmptyCapsule/Curiosity/Inactivity），InterventionService有自适应介入——但**没有真正的"状态驱动唤醒"**，只有定时+事件触发。
3. **LLM Router远超预期**：llm_router.py实现了10+ model tier、5+ provider、health-based fallback、agent-role routing、task-type routing、circuit breaker、concurrency control——**已经是一个生产级的分层路由系统**，不是"单一LLM调用"。
4. **认知学习系统有4层深度**：BehaviorSignalCollector（5种主动检测+3种推断偏好=8种行为指标）→ CognitiveService（碎片分析+模式检测）→ Bayesian Learner（概率学习）→ SelfEvolutionService（校准+理解深度L0-L5）——但**没有Skill/Procedural Memory概念**。
5. **Community系统完全实现**：好友生命周期、责任伙伴+打卡、群组+消息、社交信号收集（3种偏好推断）、ML好友推荐——但**没有"关系→行为约束"的编译层**。

### 融合优先级排序（基于代码验证修正）

| 优先级 | 领域 | 真实差距 | 预期ROI | 融合难度 |
|--------|------|----------|---------|----------|
| **P0** | 接通MemoryService**写路径**到orchestrator | 读路径已连通，写路径断开 | ★★★★★ | 中 |
| **P0** | 增强PushService→Wake Engine | 已有基础架构 | ★★★★☆ | 中 |
| **P1** | Skill/Procedural Store | 完全缺失 | ★★★★☆ | 中高 |
| **P1** | Social Brain Policy Compiler | 数据存在但无编译 | ★★★☆☆ | 高 |
| **P2** | LLM Router升级为控制平面 | 已有80%基础 | ★★★☆☆ | 低 |

---

## 二、五大领域核心理念 + Sparkle代码级映射

### 2.1 长期陪伴型Agent（Proactive Companion）

**前沿核心理念**:
长期陪伴型Agent的核心不是更强任务执行能力，而是更强**状态感知、唤醒决策和主动介入**能力。PASK的DD-MM-PAS范式（Demand Detection → Memory Modeling → Proactive Agent System）、Springdrift的Sensorium（每周期注入结构化自我状态块）、美团长程任务代理的"意图维护→条件唤醒"两阶段模型是三个最值得借鉴的范式。

**Sparkle代码验证结果**:

| 前沿概念 | Sparkle实际状态 | 代码位置 |
|----------|----------------|----------|
| 感知层 | ✅ **已实现** — ContextOrchestrator聚合6维上下文 | `context_manager.py:29-62` |
| 状态估计 | ✅ **已实现** — DualCoreRouter根据17维输入做模式判断 | `dual_core_router.py:37-58,148-330` |
| 定时唤醒 | ✅ **已实现** — SchedulerService每15分钟Smart Push Cycle | `scheduler_service.py:33,75-84` |
| 介入策略 | ⚠️ **部分实现** — InterventionService有介入创建，PushService有5种策略 | `intervention_service.py:264-343`, `push_service.py:52-122` |
| Sensorium | ❌ **缺失** — 没有Springdrift式的结构化自我状态注入 | — |
| 状态驱动唤醒 | ❌ **缺失** — 没有基于用户状态偏离的自主唤醒 | — |
| 介入收益/成本权衡 | ❌ **缺失** — 介入决策无收益vs成本估计 | — |

**关键发现**: Sparkle的主动性不是"从零开始"，而是**已有基础设施但缺乏"状态驱动"维度**。PushService.evaluate()基于5种策略做推送决策，但这些策略是固定的（sprint冲刺、memory复习、empty capsule补充、curiosity好奇心、inactivity不活跃），不是基于用户实时状态的动态评估。与前沿研究中"当用户目标偏离度>阈值时自主唤醒"的范式存在差距。

**最高ROI的融合路径**: 不需要新建唤醒引擎——增强现有SchedulerService + PushService，在`process_user_push()`中引入**用户状态聚合**（目标偏离度、学习连续性、情绪趋势），将"固定策略列表"升级为"状态驱动的策略选择器"。

### 2.2 Social Brain 控制层

**前沿核心理念**:
Social Brain应被定义为`SB = (G, X, U, F, Π)`——以图状态为底座、以关系推理为核心、以策略编译为输出的控制中间层。关键跃迁是：从"关系用于分析/推荐"到"关系用于**控制行为**"（relationship → permission / obligation / risk / policy）。数据来源分三层：硬约束（组织结构/IAM）、高权重软约束（通信协作日志）、低置信软约束（模型推断关系）。

**Sparkle代码验证结果**:

| 前沿概念 | Sparkle实际状态 | 代码位置 |
|----------|----------------|----------|
| 关系图 | ✅ **隐式存在** — friendship、accountability_partnership、group_members表 | DB schema: friendships, accountability_partnership |
| 信号桥接 | ✅ **已实现** — community_signal_bridge桥接群组→个人 | `community_signal_bridge.py:38-158` |
| 社交偏好推断 | ✅ **已实现** — community_signal_collector推断3种偏好(engagement_level, social_learning_preference, content_contribution_rate) | `community_signal_collector.py:34-172` |
| 好友匹配 | ✅ **已实现** — friend_match_service用Jaccard+互补+风险桶 | `friend_match_service.py` |
| 推荐反馈学习 | ✅ **已实现** — 多阶段反馈收集+相似度/互补度/舒适度评分 | `friend_match_service.py` (recommendation feedback) |
| 责任伙伴+打卡 | ✅ **已实现** — 完整partnership生命周期+daily checkin+streak | `community_service.py:accountability` |
| **关系→行为约束** | ❌ **完全缺失** — 没有Policy Compiler | — |
| **关系→AI提示** | ❌ **断裂** — accountability数据不进入AI推理 | — |

**关键发现**: Sparkle的社交系统**远比想象中完整**——好友生命周期、责任伙伴(含goal tracking)、群组管理(3种类型)、消息系统(线程+回复+@提及+反应)、打卡(streak+flame)、社交信号收集(3种偏好推断)、ML好友推荐。**但所有这些数据不约束AI行为**。当用户A设定了"每天背30个单词"并与B成为责任伙伴时，系统不会在A连续2天未完成时主动介入，也不会在B看到A的进度时调整B的AI行为。

**最高ROI的融合路径**: 在accountability场景做最小Policy Compiler——从`accountability_partnership`表读取commitment状态，编译为intervention触发条件和AI prompt约束。不需要新建图数据库，直接在现有PostgreSQL表上加查询层。

### 2.3 Agent系统架构（Memory + Loop + Execution + Context）

**前沿核心理念**:
下一代Agent的决定性差异来自memory lifecycle、minimal sufficient context、runtime execution、feedback adaptation这四层闭环。Memory Taxonomy应至少区分：Working Memory（常驻）、Episodic Store（不可变证据）、Semantic Store（可更新事实）、Profile Store（稳定特质）、Procedural Store（技能沉淀）、Conflict Index（矛盾检测）。Loop应为：ingest→extract→update→retrieve→compose→act→verify→reflect→consolidate。

**Sparkle代码验证结果**:

| 前沿概念 | Sparkle实际状态 | 代码位置 |
|----------|----------------|----------|
| Episodic Memory | ✅ **模型已实现** — EpisodicMemory with embedding, importance_score, tags | `models/memory.py:77-106` |
| Preference Memory | ✅ **模型已实现** — MemoryPreference with versioning, confidence, correction_count | `models/memory.py:15-42` |
| Goal Memory | ✅ **模型已实现** — MemoryGoal with status, target_date, linked_task_id | `models/memory.py:44-75` |
| Correction Tracking | ✅ **模型已实现** — MemoryCorrection for retraction/correction | `models/memory.py:108-126` |
| 57个Preference Key | ✅ **已定义** — PREFERENCE_KEYS in memory_constants.py | `memory_constants.py` |
| Memory CRUD | ✅ **已实现** — upsert_preference, create_goal, create_episodic_memory, apply_correction | `memory_service.py:69-651` |
| Feature Flags | ✅ **全部启用** — ENABLE_MEMORY_RETRACTION/ENABLE_CONTEXT_FOCUSING/ENABLE_LTM_ROLLOUT等全部=True | `config/settings.py:439-468` |
| **Memory→Orchestrator读路径** | ✅ **已连通** — orchestrator.py:1718无条件调用 → ContextPackBuilder → list_preferences/goals/episodic | `orchestrator.py:1718` → `session_state_mixin.py:667` → `context_pack.py:461-463` |
| **Memory→Orchestrator写路径** | ❌ **完全断开** — chat flow中无MemoryService写入逻辑 | — |
| Working Memory | ❌ **缺失** — 无pinned profile block | — |
| Conflict Index | ❌ **缺失** — 无contradiction detection | — |
| Sufficiency-based retrieval | ⚠️ **部分** — sufficiency_checker有7种intent的多字段验证+上下文推断+LLM fallback+loop detection，但检查的是"用户是否提供了足够操作信息"而非"AI是否有足够用户上下文做个性化判断" | `sufficiency_checker.py` |

**这是全系统最重要的修正（v4.0）**。MemoryService是"半Ghost Ship"——

**读路径已连通**（v3.0之前文档错误地认为完全断开）：
- `orchestrator.py:1718` **无条件**调用`_apply_context_focus_overlay()`
- 调用链：`session_state_mixin.py:667` → `context_focus.py:383` → `context_pack.py:461-463`
- 最终调用：`MemoryService.list_preference_records()` + `list_active_goals()` + `list_recent_episodic()`
- 条件：`ENABLE_CONTEXT_FOCUSING=True`（已确认默认启用）
- **注意**：`orchestrator.py:1301`有另一处调用但**在标准模式下被跳过**（`chat_mode != CHAT_MODE_STANDARD`条件）。真正的连接是line 1718的无条件调用。

**写路径完全断开**：
- chat flow中没有任何从对话结果写入MemoryService的逻辑
- 用户在对话中表达的新偏好（"我其实不喜欢早起"）、新目标（"我想准备期末考试"）不会被记录
- MemoryService的57个preference key和goal tracking在对话结束后**无法更新**
- 这意味着**读路径读到的数据永远是初始化时或后台job写入的，不会从对话中丰富**

**对比prompt管线**：`context_manager.py`聚合的error_summary、recent_errors来自其他服务（galaxy_service、error_book），不是MemoryService。MemoryService的数据（用户长期偏好、目标、episodic事件）**通过context_pack.py进入prompt**，但只读不写。

**最高ROI的融合路径**: 聚焦**写路径接通**——在`orchestrator.py`的response完成后，从对话中提取事实/偏好/目标变化并写入MemoryService。读路径已通，不需要再做。

### 2.4 Skill自进化系统

**前沿核心理念**:
Skill = {context, trigger, procedure, expected_outcome, constraints}。系统闭环：User Behavior → Skill Extraction → Skill Validation → Skill Library → Skill Deployment → User Feedback → Iteration。Voyager证明procedural memory最佳载体是可执行程序，AutoSkill证明对话轨迹可自动抽象为技能，质量门禁必须包含自动验证+跨任务测试。

**Sparkle代码验证结果**:

| 前沿概念 | Sparkle实际状态 | 代码位置 |
|----------|----------------|----------|
| 工具注册 | ✅ **已实现** — DynamicToolRegistry with 22+ tools, 6 categories | `dynamic_tool_registry.py:48-156` |
| 行为模式检测 | ✅ **已实现** — 3+ patterns（planning optimism, focus decay, cognitive blindspot） | `behavior_pattern_service.py:22-222` |
| 信号采集 | ✅ **已实现** — 5种主动检测(task_resistance, underestimate, overplanning, inactive_stall, abandonment) + 3种推断偏好(reflection_depth, difficulty_feedback_ratio, difficulty_accuracy) = 8种行为指标 | `behavior_signal_collector.py:34-491` |
| 推断偏好学习 | ✅ **已实现** — task_reflection_depth, difficulty_feedback_ratio, task_difficulty_accuracy | `behavior_signal_collector.py:443-453` |
| 贝叶斯学习 | ✅ **已实现** — MultiDimensionalLearner (4维: success, latency, cost, satisfaction) | `learning/multi_dimensional_learner.py` |
| 策略存储 | ✅ **已实现** — StrategyStore with 5-stage lifecycle (DISTILLED→USER_REVIEWED→USER_PRIVATE→COMMUNITY_SHARED→RETIRED) | `learning/strategy_store.py:23-41` |
| 理解深度 | ✅ **已实现** — L0-L5 progression based on preferences, patterns, alignment scores | `self_evolution_service.py:232-402` |
| Agent Profiles | ✅ **已实现** — 23 roles with per-agent model tier, temperature, tools, persona | `agent_profiles.py:1-835` |
| 自适应重规划 | ✅ **已实现** — 认知模式→约束映射（planning optimism→duration×1.3, procrastination→max 20min session） | `adaptive_replanner.py:124-198` |
| **Skill/Procedural Memory** | ❌ **完全缺失** | — |
| **轨迹→技能自动提炼** | ❌ **完全缺失** | — |
| **技能库+质量门禁** | ❌ **完全缺失** | — |
| **跨用户技能共享** | ❌ **完全缺失** | — |

**关键发现**: Sparkle的认知学习系统有4层深度，比想象中复杂得多。但**所有学习都停留在"参数调整"层面**——贝叶斯概率更新、偏好权重调整、策略校准——没有"沉淀为可复用技能"的能力。BehaviorSignalCollector能检测"用户反复高估任务时间"（planning optimism pattern），adaptive_replanner能据此把后续任务时间×1.3——但这不能变成"下次遇到类似用户时自动应用的经验"。

**最高ROI的融合路径**: 利用已有的StrategyStore（已实现lifecycle管理）作为Skill Library的存储底座。关键改造是：从"策略只在本用户内使用"扩展为"策略可跨用户共享（经匿名化）"。BehaviorSignalCollector的pattern detection结果天然可以作为skill trigger。

### 2.5 Model Router 控制平面

**前沿核心理念**:
Model Routing应从一次性分类问题升级为**状态感知、资源感知、会话感知的序列决策/控制问题**。分层架构：Policy Gate → Cache Layer → Semantic Belief Layer → Controller Layer → Execution & Observability Layer。五类路由信号：query语义、会话状态、模型能力、系统状态、策略约束。

**Sparkle代码验证结果**:

| 前沿概念 | Sparkle实际状态 | 代码位置 |
|----------|----------------|----------|
| 多Provider支持 | ✅ **已实现** — Xiaomi/DeepSeek/Zhipu/Aliyun/SiliconFlow/Hunyuan | `llm_service.py` |
| 多Tier路由 | ✅ **已实现** — FREE/FAST/STANDARD/PLUS/PRO/MAX/TOP + GLM_BATCH + SPECIALIST | `llm_router.py` |
| Agent-Role路由 | ✅ **已实现** — 23个agent role各自有model tier偏好 | `llm_router.py:593-716` |
| Task-Type路由 | ✅ **已实现** — DEEP_REASONING/ERROR_DIAGNOSIS/TOOL_PLANNING等影响tier | `llm_router.py` |
| Health Fallback | ✅ **已实现** — 5次连续失败→标记unhealthy, 300s无失败→自动恢复 | `llm_router.py:63-90,1109-1152` |
| Fallback Chain | ✅ **已实现** — MAX→PRO→PLUS→STANDARD→FAST→FREE_FAST | `llm_router.py:1109-1152` |
| Circuit Breaker | ✅ **已实现** — circuit_breaker.py | `services/circuit_breaker.py` |
| Concurrency Control | ✅ **已实现** — per-provider并发限制 | `services/llm/concurrency.py` |
| Reasoning Mode | ✅ **已实现** — fast/balanced/deep影响tier选择 | `llm_router.py` |
| Complexity-Aware | ✅ **已实现** — message complexity评估（可选） | `llm_router.py` |
| Policy Gate (auth/DLP) | ⚠️ **部分** — Go Gateway有auth/rate limit, 但无DLP/guardrails in router | Go middleware |
| Cache Layer | ⚠️ **部分** — Go侧有semantic cache, 但router无cache感知 | Go gateway |
| Semantic Belief Layer | ⚠️ **隐式** — complexity评估+intent routing存在，但无显式difficulty/utility估计 | — |
| 会话感知路由 | ❌ **缺失** — router不考虑session history或对话阶段 | — |
| 预算/成本控制 | ❌ **缺失** — 无per-user预算限制 | — |
| 可审计reason code | ❌ **缺失** — 路由决策无结构化reason输出 | — |

**关键发现**: Sparkle的LLM Router**已经是一个生产级的分层路由系统**，远非"单一LLM调用"。它具备5+ provider、10+ tier、health-based fallback、agent-role routing、task-type routing、circuit breaker、concurrency control——这已经覆盖了前沿报告中"分层控制平面"约70%的概念。缺失的是**会话感知路由**（DialRouter式多轮优化）和**成本治理**（预算限制+reason code）。

**最高ROI的融合路径**: 不是"新建router"——而是在现有llm_router.py的select_model()中引入**会话阶段信号**（orchestrator已知的intent stage和plan health）和**reason code输出**（记录为什么选了这个tier）。

---

## 三、Sparkle 真实差距矩阵（代码验证版）

### 3.1 记忆系统差距

| 维度 | Sparkle实际状态 | 理想态 | 差距 | 修复成本 |
|------|----------------|--------|------|----------|
| 记忆模型 | 4种（Episodic/Preference/Goal/Correction），57个key，已实现 | 5种（+Procedural），全部接通 | 缺Procedural | 新模块 |
| **读路径** | ✅ **已连通** — orchestrator:1718→ContextPackBuilder→MemoryService | — | **已满足** | 0 |
| **写路径** | ❌ **完全断开** — chat flow中无MemoryService写入 | 每turn结束后写 | **未接通** | ~80行 |
| Prompt渲染 | error_summary等已渲染（来自error book/galaxy），MemoryService数据通过context_pack.py也已进入prompt | — | **已满足** | 0 |
| Feature Flags | 全部已启用 | — | 不是问题 | 0 |
| Working Memory | ❌ 缺失 | pinned profile block | 缺失 | 新模块 |
| Conflict Index | MemoryCorrection存在但无自动conflict detection | contradiction detection | 弱 | 中 |
| Consolidation | memory_evolution_service.py有change tracking，但无episode→scene→profile升级链 | lifecycle consolidation | 弱 | 中 |

**核心结论（v4.0修正）**: 记忆系统的差距**不是"完全没有连接"而是"只读不写"**。读路径通过context_focus_overlay已连通。修复应聚焦于**写路径接通**——在对话结束后将新事实/偏好/目标写入MemoryService。

### 3.2 主动性差距

| 维度 | Sparkle实际状态 | 理想态 | 差距 |
|------|----------------|--------|------|
| 定时唤醒 | ✅ SchedulerService每15分钟Smart Push Cycle | 事件+状态驱动唤醒 | 有基础，缺状态维度 |
| Push策略 | ✅ 5种（Sprint/Memory/EmptyCapsule/Curiosity/Inactivity） | 动态策略选择器 | 策略太固定 |
| 介入创建 | ✅ InterventionService有adaptive creation + scaffolding FSM | 收益/成本权衡 | 缺权衡逻辑 |
| 介入交付 | ✅ InterventionEventConsumer + 参数编译→plan调整 | 完整闭环 | 已有 |
| 概念缺口标记 | ✅ GalaxyEventConsumer在error created时主动查找active plan的prerequisite gap | 全面状态监测 | 只覆盖error场景 |
| 成就临界提示 | ✅ AchievementEngine检测80%+进度 | 全面目标跟踪 | 只覆盖achievement |
| **用户不活跃唤醒** | ❌ 缺失 | "3天未登录→主动关怀" | **缺失** |
| **计划停滞检测** | ❌ 缺失 | "计划连续N天无进展→主动建议" | **缺失** |
| **情绪趋势预警** | ❌ 缺失 | "情绪持续低落→情感支持" | **缺失** |

**核心结论**: 主动性系统已有**可观的基础设施**（Scheduler+Push+Intervention+EventConsumer），但缺少"状态聚合→动态决策"的核心逻辑。不需要新建架构，只需要在PushService.process_user_push()中引入用户状态聚合器。

### 3.3 社会关系差距

| 维度 | Sparkle实际状态 | 理想态 | 差距 |
|------|----------------|--------|------|
| 好友系统 | ✅ 完整生命周期（request/accept/block/delete + cascade） | — | 已满足 |
| 责任伙伴 | ✅ partnership+checkin+streak+encouragement+achievement集成 | obligation→intervention | 缺Policy Compiler |
| 群组系统 | ✅ 3种类型(SQUAD/SPRINT/OFFICIAL)+消息+任务+打卡 | group→constraint | 缺Policy Compiler |
| 社交信号 | ✅ 3种偏好推断(engagement_level, social_learning_preference, content_contribution_rate) | 社交信号→AI行为 | 信号存在但未驱动AI |
| ML好友推荐 | ✅ Jaccard+互补+风险桶+反馈学习 | — | 已满足 |
| **关系→AI提示** | ❌ 断裂 | accountability goal进入prompt | **断裂** |
| **关系→介入触发** | ❌ 缺失 | commitment→主动提醒 | **缺失** |
| **关系→可见性控制** | ❌ 缺失 | partner看摘要, non-partner看什么 | **缺失** |

**核心结论**: 社交系统的数据层和功能层**完全就绪**，缺的是"关系编译为行为约束"的控制层。Accountability是最自然的MVP场景——partnership表已有initiator_goal和partner_goal字段，只需要读取并编译为intervention触发条件。

### 3.4 技能系统差距

| 维度 | Sparkle实际状态 | 理想态 | 差距 |
|------|----------------|--------|------|
| 工具注册 | ✅ 22+ tools, 6 categories, 自动发现 | — | 已满足 |
| 模式检测 | ✅ planning optimism, focus decay, cognitive blindspot | — | 已满足 |
| 行为学习 | ✅ 4层（信号→碎片→贝叶斯→校准） | — | 已满足 |
| 策略生命周期 | ✅ DISTILLED→USER_REVIEWED→USER_PRIVATE→COMMUNITY_SHARED→RETIRED (5阶段) | — | 基础已满足 |
| **Skill自动提炼** | ❌ | 轨迹→技能 | **完全缺失** |
| **Procedural Memory** | ❌ | 技能库 | **完全缺失** |
| **跨用户共享** | ❌ | 匿名化技能 | **完全缺失** |

**核心结论**: Sparkle有**强大的行为学习和模式检测基础设施**，但所有学习都停留在"参数/权重调整"层面，没有"沉淀为可复用技能"的能力。StrategyStore的lifecycle管理已经提供了Skill Library的骨架——扩展它比从零开始更合理。

### 3.5 路由系统差距

| 维度 | Sparkle实际状态 | 理想态 | 差距 |
|------|----------------|--------|------|
| 多Provider/Tier | ✅ 5+ provider, 10+ tier, 完整fallback | — | **已满足** |
| Agent-Role路由 | ✅ 23个agent role各有tier偏好 | — | **已满足** |
| Health+Fallback | ✅ 5次失败→unhealthy, 自动恢复, 6级fallback | — | **已满足** |
| Circuit Breaker | ✅ per-provider | — | **已满足** |
| **会话感知路由** | ❌ | DialRouter式多轮优化 | **缺失** |
| **预算控制** | ❌ | per-user budget limit | **缺失** |
| **Reason Code** | ❌ | 路由决策可审计 | **缺失** |

**核心结论**: LLM Router是Sparkle最接近前沿水平的子系统。主要差距不在架构而在**可观测性**（reason code）和**会话感知**（多轮对话中动态调整模型选择）。

---

## 四、融合方案：基于代码实际的分层路线图

### Phase 0: 接通写路径 + 快速胜利（1-2周）— ROI最高

**目标**: 接通MemoryService写路径，释放对话中产生的用户洞察。

**v4.0重要修正**: 读路径已通过`orchestrator.py:1718`→`ContextPackBuilder`→`MemoryService`连通。Phase 0聚焦**写路径接通**和低成本快速胜利。

```
Phase 0A: MemoryService 写路径接通 (~80行)
├── 文件: backend/app/orchestration/orchestrator.py
├── 位置: response完成后
├── 改动:
│   ├── 从AI response中抽取候选事实/偏好变化（需要extraction逻辑）
│   ├── 与已有preferences做冲突检测（新偏好是否与已有矛盾）
│   ├── 决定写入粒度（"我喜欢早起"是一个preference还是两个？）
│   ├── 执行ADD/UPDATE/DELETE/NOOP分类（对标Mem0，可能需要额外LLM调用）
│   └── 写入MemoryService
├── Token预算管理: memory context不超过总context window的15%
├── 风险与缓解:
│   └── AI提取的事实可能是幻觉→ 写入前验证：新preference必须有对话中的明确证据
│   └── Token预算冲突→ 动态分配：memory不超过总context的15%
└── 建议: 初期仅写入高置信度偏好（用户明确表达的），观察一个迭代周期

Phase 0B: Prompt管线验证+扩展 (~15行)
├── 文件: backend/app/orchestration/prompts.py
├── 验证: error_summary/recent_errors/recent_mastery_changes的渲染
│   已有 _mark_rendered() 调用，确认数据确实进入最终prompt
├── 增加来源: 将 MemoryService 的 preferences 和 goals 也加入渲染
├── 预期效果: AI上下文从error book/galaxy扩展到memory service
└── 风险: 低 — 增量添加，不修改现有渲染逻辑

Phase 0C: Accountability → Intervention 触发 (~20行)
├── 文件: 新建 backend/app/services/accountability_intervention.py
├── 逻辑:
│   ├── 查询 accountability_partnership 表
│   ├── WHERE status='ACTIVE' AND check_in_streak中断 >= 2天
│   └── 创建 InterventionRequest(trigger="commitment_stalled")
├── 集成: 在 SchedulerService.daily_jobs 中调用
├── 预期效果: 责任伙伴的commitment首次能触发系统主动介入
├── 风险与缓解:
│   └── 隐私——accountability数据进入AI prompt → 只包含用户自己的承诺，不包含伙伴的具体数据
└── 新文件，不影响现有逻辑
```

**Phase 0实际工作量**: Phase 0A(写路径~80行) + Phase 0B(prompt扩展~15行) + Phase 0C(accountability~20行) + Phase 0+Social(社交→Router~10行) + 测试(~30行) = **~155行**。注意：写路径是核心工作，需要设计提取逻辑和冲突检测。

### Phase 1: 状态聚合器 + 增强PushService（2-3周）

**目标**: 将PushService从"固定策略"升级为"状态驱动"。

```
Phase 1A: User State Aggregator (新模块, ~200行)
├── 文件: backend/app/services/user_state_aggregator.py
├── 聚合源:
│   ├── memory_service.list_active_goals() → 目标状态
│   ├── plan_context_builder.build() → 计划健康度
│   ├── behavior_pattern_service.detect() → 行为模式
│   ├── cognitive_service.get_patterns() → 认知状态
│   └── community_signal_collector.get_preferences() → 社交偏好
├── 输出: UserStateSnapshot {
│     goal_drift_score: float,      # 目标偏离度
│     learning_continuity: float,   # 学习连续性 (0-1)
│     emotion_trend: str,           # "improving" | "stable" | "declining"
│     plan_staleness_days: int,     # 计划停滞天数
│     engagement_level: str,        # community_signal_collector已有
│     intervention_sensitivity: float  # 基于历史反馈
│   }
└── 集成: PushService.process_user_push() 中调用

Phase 1B: State-Driven Strategy + Timing Selection (~150行)
├── 文件: backend/app/services/push_service.py (改造)
├── 变更:
│   ├── 现有5种策略保留为"候选"
│   ├── 新增 state→strategy 映射:
│   │   ├── plan_staleness_days >= 3 → PlanRestartStrategy
│   │   ├── learning_continuity < 0.3 → MicroStartStrategy
│   │   ├── emotion_trend == "declining" → EmotionalSupportStrategy
│   │   ├── goal_drift_score > 0.6 → GoalRecalibrationStrategy
│   │   └── 无特殊状态 → 从现有策略中选择
│   ├── 新增介入时机评估（何时推送比推什么更重要）:
│   │   ├── 用户正在活跃对话中 → 不打断，但准备好介入内容
│   │   ├── 用户刚离开应用 → 等待10-30分钟，给缓冲期
│   │   ├── 用户连续N天未活跃 → 主动推送，但频率递减
│   │   └── 用户在活跃学习时段 → 可以推送学习相关的介入
│   └── 新增打扰预算:
│       └── 每日最大主动介入次数≤2（基于intervention_sensitivity调整）
├── 风险与缓解:
│   └── Push疲劳——更多状态驱动推送可能导致用户反感 → 严格打扰预算+带"减少打扰"反馈选项
└── 预期效果: 系统基于用户真实状态和最佳时机做推送决策
```

### Phase 2: Memory Lifecycle 增强（3-4周）

**目标**: 在已接通的MemoryService基础上增加高级能力。

```
Phase 2A: Working Memory / Pinned Profile Block (~150行)
├── 每次 chat 请求开始时:
│   ├── 固定加载: top-5 preferences + active goals + user traits
│   ├── 组装为 ~300 token 的 pinned block
│   └── 注入到 system prompt 或 context payload 的固定位置
├── 效果: AI始终知道用户是谁、想要什么、正在做什么

Phase 2B: Write Path Enhancement (~200行)
├── 对标Mem0的ADD/UPDATE/DELETE/NOOP分类:
│   ├── 每个turn结束后，从AI response中抽取候选事实
│   ├── 与现有preferences做冲突检测
│   ├── 分类: 新事实→ADD, 变化→UPDATE, 过时→DELETE, 无变化→NOOP
│   └── 写入MemoryService
├── 触发点: orchestrator.py response完成后

Phase 2C: Consolidation Trigger (~100行)
├── 会话结束时: 提炼本次会话的关键信息→update preferences
├── compaction时: 压缩长对话→semantic note
├── sleep-time (SchedulerService已有): 批量consolidation
└── 对标HiMem的reconsolidation逻辑

Phase 2D: Context Sufficiency Judge (~120行)
├── 文件: backend/app/core/context_pack.py 或 context_manager.py
├── 核心问题: 接通MemoryService后，往prompt里塞多少数据？
│   top-5 preferences还是top-20？如果AI说"信息不够"系统能否自动补充？
├── 对标:
│   ├── HiMem: 先查Note Memory → 不够再下钻Episodic层
│   └── EverMemOS: scene match → episode rerank → sufficiency check → query rewrite
├── 实现逻辑:
│   ├── Step 1: 从Profile Store加载固定block（~300 token）
│   ├── Step 2: 从Semantic Store做coarse retrieval（基于query语义）
│   ├── Step 3: Sufficiency Judge判断"当前拼装的上下文是否足够AI做出高质量判断"
│   ├── Step 4: 不够 → 自动扩展检索范围（从Episodic Store补充证据）
│   └── Step 5: 记录sufficiency score用于后续优化
├── 这不是sufficiency_checker.py的字段验证——那检查的是"用户是否提供了足够操作信息"（远比v1.0描述的复杂，含7种intent验证+上下文推断+LLM fallback）
│   这是检查"AI是否有足够用户上下文做出个性化判断"
└── 风险: 增加一次判断的LLM调用成本 → 可用轻量模型做judge
```

### Phase 3: Skill System MVP（4-6周）

**目标**: 基于已有的StrategyStore和BehaviorSignalCollector建立技能提炼闭环。

```
Phase 3A: 双层技能系统设计
├── 区分两类技能（Voyager/SAGE的核心洞察）:
│
├── Declarative Skills（声明式技能）
│   ├── 载体: 自然语言描述的策略
│   ├── 存储: 扩展现有StrategyStore
│   ├── 增加字段: trigger_condition, context_pattern, quality_score
│   ├── 用途: 认知层面——"用户有planning optimism倾向时，建议拆小任务"
│   └── 检索: pgvector语义匹配 + trigger条件匹配
│
└── Procedural Skills（过程式技能）— 需要新模型
    ├── 载体: 工具调用序列模板 [create_task(params), set_reminder(task_id, timing)]
    ├── 存储: 新建ProceduralSkill模型，关联到DynamicToolRegistry
    ├── 不同于Voyager的Python代码——Sparkle的工具调用是JSON格式的tool calls
    ├── 用途: 执行层面——"用户要准备考试时，自动调用 create_plan→create_tasks→set_reminders"
    └── 质量门禁: Skill必须经过distilled→reviewed生命周期，不能直接投入使用

Phase 3B: Pattern → Skill 自动提炼
├── BehaviorSignalCollector检测到重复模式时
├── Declarative: 自动创建Strategy条目 (lifecycle=distilled)
├── Procedural: 从成功执行的tool call序列中提取模板
├── 经N次验证后升级为 reviewed
├── 经M次跨用户验证后升级为 shared
├── 风险与缓解:
│   └── 自动提炼的Skill质量不可控 → 必须经过lifecycle，不能直接投入使用
│   └── Skill过拟合单个用户 → 去个性化验证，跨用户测试

Phase 3C: Skill Deployment
├── Declarative Skills → 注入到prompt中作为"经验建议"
├── Procedural Skills → 作为候选tool call序列供orchestrator选择
└── 跟踪使用效果→更新quality_score
```

### Phase 4: Social Brain Policy Compiler（6-8周）

**目标**: 在Accountability场景实现"关系→行为约束"。

```
Phase 4A: Accountability Policy Compiler
├── 读取 accountability_partnership 表
├── 编译规则:
│   ├── commitment → obligation: "A承诺X" → A连续N天未完成→intervention
│   ├── partnership → visibility: "A和B是伙伴" → B可看A的周摘要
│   ├── partnership → notification: "A完成目标" → B收到庆祝
│   └── partnership → AI constraint: "A有伙伴" → AI提醒A对伙伴的承诺

Phase 4B: 关系数据进入AI Prompt
├── 有责任伙伴的用户，AI prompt中包含:
│   ├── "你有责任伙伴B，你们共同承诺..."
│   ├── "你已经连续N天完成/未完成..."
│   └── "你的伙伴B的进度是..."
└── 无责任伙伴的用户，无此内容
```

---

## 五、跨领域协同分析

### 5.1 记忆×主动性

```
User State Aggregator (Phase 1)
    │
    ├── MemoryService.preferences ──→ 用户偏好影响推送策略
    ├── MemoryService.goals ──────→ 目标偏离度影响唤醒决策
    ├── BehaviorSignalCollector ──→ 行为模式影响介入时机
    └── CognitiveService.patterns ─→ 认知状态影响介入方式
```

**依赖**: Phase 0A（MemoryService接通）是Phase 1的前提。没有记忆数据，User State Aggregator无法聚合。

### 5.2 社交×主动性

```
Accountability Policy Compiler (Phase 4)
    │
    ├── partnership.commitment ──→ 触发InterventionService
    ├── partnership.streak ──────→ 影响PushService策略选择
    └── partner.progress ────────→ 生成push内容("你的伙伴正在进步")
```

**优势**: 两者都基于已有的InterventionService和PushService，协同成本低。

### 5.3 社交→DualCoreRouter 快速通道

**补充（评审）**: Social Brain的MVP不应局限于Accountability场景。一个更低成本、更高价值的切入点是：将已有的社交信号作为dual-core-router的第18维输入。

```
community_signal_collector 已推断的3种社交偏好
    │
    ├── engagement_level ──────→ 影响AI交互模式（活跃→激励型，沉默→温和型）
    ├── social_learning_preference → 影响AI建议方式（个人偏好→自主建议，社交偏好→引入伙伴/群组）
    └── 群组sprint进度 ────────→ 当用户在活跃sprint组里时，AI切换到更激励的模式

代码量: ~10行（在dual_core_router.py的DualCoreRoutingInput中增加social_context字段）
依赖: community_signal_collector已有数据，无需新增采集
```

**建议**: Phase 4拆为两步——Phase 4A（社交信号→Router，~10行，与Phase 0同步做）先于Phase 4B（Accountability Policy Compiler，~400行，需要更多设计）。

### 5.4 五报告元架构：依赖链而非平行菜单

**补充（评审）**: v2.0把5份报告作为5个平行领域分析，但它们之间有明确的依赖关系。理解这个依赖链是Phase排序的根本原因：

```
Memory Lifecycle (R3)           ← 系统的"状态基座"
    ↓ 提供用户状态基线
Proactive Awakening (R1)        ← 依赖Memory才知道"状态偏离了"
    ↓ 主动介入产生新交互
Skill Extraction (R4)           ← 从新交互中提炼可复用行为
    ↓ 技能影响模型选择
Model Router (R5)               ← 复杂技能用强模型，简单任务用弱模型
    ↑                            ↑
Social Brain (R2)               ← 关系数据影响所有层的决策约束
    │
    └── 关系数据影响Memory写入权限、介入策略的用户偏好、技能的跨用户共享边界
```

**这解释了为什么Phase 0A（Memory接通）是所有其他Phase的前提**——不只是Memory×主动性的依赖，而是Memory是整个系统的"状态基座"。没有Memory：
- Proactive不知道"偏离了什么"（无基线）
- Skill不知道"从什么经验中提炼"（无轨迹）
- Router不知道"上次用了什么模型"（无routing history）
- Social Brain不知道"用户对伙伴的承诺是什么"（无commitment记录）

**Phase排序的逻辑因此是**: Memory → Proactive → Skill → Router，Social Brain横切所有层。

```
BehaviorSignalCollector (已有)
    │
    ├── 检测重复模式 ────→ Pattern → Skill自动提炼 (Phase 3)
    │                          │
    ├── Skill存入StrategyStore ←─── 验证后升级lifecycle
    │                          │
    └── Skill注入AI prompt ←─────── 提升后续交互质量
                                   │
                                   └── 新交互产生新信号 → 循环
```

**关键**: StrategyStore（已有）是连接记忆和技能的枢纽。Phase 3不是"新建"技能系统，而是"扩展"现有的策略学习系统。

---

## 六、关键设计决策（基于代码实际）

### 决策1: MemoryService接入方式

**决策**: 在orchestrator.py中直接import并调用，不新增中间层。

**理由**: MemoryService已有完整的async CRUD接口（upsert_preference, list_preferences等），orchestrator也已有完整的context building流程。直接在现有流程中插入MemoryService调用是最小成本方案。不需要像前沿报告中Letta那样的"memory OS"，因为Sparkle的orchestrator已经承担了context管理的角色。

### 决策2: 主动性升级策略

**决策**: 增强PushService而非新建Wake Engine。

**理由**: PushService已有15分钟定时循环、5种策略、用户活跃时段检测、频率上限。这些是Springdrift Sensorium和美团长程代理的"简化版"。在PushService中增加UserStateAggregator作为输入源，比从零构建Wake Engine的ROI高得多。

### 决策3: 技能系统载体

**决策**: 区分Declarative Skills（扩展StrategyStore）和Procedural Skills（新建ProceduralSkill模型关联DynamicToolRegistry）。

**理由**: Voyager/SAGE/XSkill的核心洞察是procedural memory的最佳载体是**可执行程序**而非自然语言。StrategyStore存的是文字描述的策略，这适合Declarative Skills（认知层面）。但Sparkle有DynamicToolRegistry（22+ tools）和工具调用能力——Procedural Skills应记录工具调用序列模板（如`[create_task(params), set_reminder(task_id, timing)]`），这不是"加几个字段"能弥合的，需要一个新模型。

### 决策4: Social Brain范围

**决策**: 两步走——先做社交信号→DualCoreRouter（~10行，Phase 0同步），再做Accountability Policy Compiler（~400行，Phase 4）。

**理由（评审修正）**: community_signal_collector已推断3种社交偏好（engagement_level, social_learning_preference, content_contribution_rate），群组sprint有实时进度数据。这些数据已经在采集但没有一个进入dual-core-router的决策。把已有社交信号作为dual-core-router的第18维输入（"当用户在活跃sprint组里时AI切换到更激励模式"）的成本远低于Accountability Policy Compiler，但价值可能更高。Accountability Policy Compiler仍然做，但不再是最初的MVP。

### 决策5: LLM Router方向

**决策**: 增加reason code、routing history tracking和会话感知，不做架构重构。

**理由**: llm_router.py已是生产级路由系统。但DialRouter的核心发现是**单轮最优≠多轮最优**——在plan→execute→reflect循环中，第1轮用便宜模型做意图识别，第2轮升级到强模型做规划，第3轮降级做总结。这需要session state中维护routing history（前面用了什么模型、后面可能需要什么模型）。建议在Phase 2中加入routing history tracking，作为未来session-aware routing的基础。

---

## 七、对Coding Agent的知识摘要

以下是为后续开发Agent提供的精炼知识要点：

### 7.1 记忆系统知识

- **半Ghost Ship（v4.0修正）**: `memory_service.py`完全实现（4种模型, 57个key, full CRUD）。**读路径已连通**：`orchestrator.py:1718`无条件调用 → `session_state_mixin.py:667` → `context_pack.py:461-463` → `list_preference_records()` + `list_active_goals()` + `list_recent_episodic()`。**写路径完全断开**：chat flow中无MemoryService写入逻辑。
- **数据来源区分**: prompt中的error_summary/recent_errors来自ContextOrchestrator（通过context_manager.py聚合galaxy_service和error_book），不是来自MemoryService。MemoryService数据通过context_pack.py进入prompt。
- **注意line 1300 vs 1718**: orchestrator.py:1300的另一处调用在标准模式下被跳过（`chat_mode != CHAT_MODE_STANDARD`），真正的连接是line 1718的无条件调用
- **Feature Flags全部True**: ENABLE_CONTEXT_FOCUSING, ENABLE_CONTEXT_BRIEFING, ENABLE_LTM_ROLLOUT等已全部启用
- **MemoryCorrection模型存在**: 支持retraction/correction，但无自动conflict detection触发

### 7.2 主动性系统知识

- **SchedulerService** (`scheduler_service.py`): 核心定时引擎，每15分钟触发Smart Push Cycle
- **PushService** (`push_service.py`): 5种策略(Sprint/Memory/EmptyCapsule/Curiosity/Inactivity)，有活跃时段检测和频率上限
- **InterventionService** (`intervention_service.py`): 有adaptive creation + scaffolding FSM + template bandit selection
- **InterventionEventConsumer** (`intervention_event_consumer.py`): 交付介入+编译参数到plan
- **缺失**: 无用户不活跃唤醒、无计划停滞检测、无情绪趋势预警

### 7.3 LLM路由知识

- **llm_router.py**: `select_model()`接受agent_role, task_type, reasoning_mode, force_tier等参数
- **Agent Profiles** (`agent_profiles.py`): 23个role各有model_policy（preferred_models, fallback_tier, blocked_providers）
- **Fallback Chain**: MAX→PRO→PLUS→STANDARD→FAST→FREE_FAST
- **Health Tracking**: 5次连续失败→unhealthy，300s无失败→auto recovery
- **缺失**: 无reason code输出，无routing history（session中维护前面用了什么模型），无per-user budget
- **DialRouter核心发现**: 单轮最优≠多轮最优——多轮对话中需要session state维护routing history

### 7.4 社交系统知识

- **CommunityService**: 完整的好友/群组/消息/打卡系统（2477行）
- **accountability_partnership表**: 有initiator_goal, partner_goal, check_in_days, status, streak
- **community_signal_bridge.py**: 桥接群组任务完成→个人任务同步，知识分享→mastery bonus
- **community_signal_collector.py**: 推断3种社交偏好(engagement_level, social_learning_preference, content_contribution_rate)
- **friend_match_service.py**: Jaccard相似度+互补+风险桶+反馈学习
- **缺失**: 无"关系→行为约束"编译，accountability goal不进入AI prompt，社交信号不进入dual-core-router
- **快速通道（评审新增）**: community_signal_collector的3种偏好可直接作为dual_core_router.py的第18维输入（~10行代码）

### 7.5 认知/学习系统知识

- **CognitiveService**: 碎片创建(embedding+event bus) + RAG分析(HyDE策略) + 模式检测(EMA置信度)
- **BehaviorSignalCollector**: 5种主动检测(task_resistance, underestimate, overplanning, inactive_stall, abandonment) + 3种推断偏好(reflection_depth, difficulty_feedback_ratio, difficulty_accuracy) = 8种行为指标
- **behavior_pattern_service.py**: planning optimism(时间×1.3), focus decay(<70%), cognitive blindspot
- **MultiDimensionalLearner**: 4维(success, latency, cost, satisfaction)贝叶斯更新，Redis持久化
- **SelfEvolutionService**: L0-L5理解深度(preferences≥3→L1, patterns≥2→L2, alignment≥0.7→L3...)
- **StrategyStore**: lifecycle管理(DISTILLED→USER_REVIEWED→USER_PRIVATE→COMMUNITY_SHARED→RETIRED, 5阶段) + 应用追踪
- **缺失**: 无Skill/Procedural Memory概念，无轨迹→技能自动提炼
- **关键区分（评审补充）**: StrategyStore适合Declarative Skills（文字描述策略），Procedural Skills（工具调用序列模板）需新建ProceduralSkill模型关联DynamicToolRegistry
- **Context Sufficiency（评审补充）**: 现有sufficiency_checker.py远比"检查intent字段"复杂（7种intent多字段验证、上下文推断、LLM fallback、loop detection），但它检查的是"用户是否提供了足够信息来执行操作"，不检查"AI是否有足够用户上下文做个性化判断"——后者是Phase 2D要解决的问题。用贬低现有系统来论证新功能的必要性会损害报告可信度。

## 六B、风险矩阵（评审补充）

| Phase | 核心风险 | 缓解措施 | 未缓解的后果 |
|-------|---------|----------|-------------|
| 0A-Read | ~~旧偏好数据质量差~~ (v4.0: 读路径已连通，数据质量由现有confidence过滤保障) | — | — |
| 0A-Write | AI从对话中提取的事实可能是幻觉（hallucinated preferences） | 写入前验证：新preference必须有对话中的明确证据 | 错误偏好进入长期存储，难以清除 |
| 0A-Write | Token预算冲突——memory context挤压对话历史空间 | 动态预算分配：memory不超过总context的15% | AI丢失近期对话上下文 |
| 1 | Push疲劳——更多状态驱动推送可能导致用户反感 | 严格打扰预算（每天≤2次主动介入）+ "减少打扰"反馈选项 | 用户关闭通知或卸载 |
| 2D | Sufficiency Judge增加LLM调用成本 | 用轻量模型做judge，或用规则近似 | 检索过少→AI判断质量下降，检索过多→成本/延迟上升 |
| 3 | 自动提炼的Skill质量不可控 | 必须经过distilled→reviewed的lifecycle，不能直接投入使用 | 劣质Skill污染prompt，降低AI输出质量 |
| 3 | Procedural Skill的tool call序列可能过时（tool接口变更） | Skill绑定tool version，tool变更时标记Skill需review | 执行失败的Skill浪费用户时间 |
| 4 | 隐私——accountability数据进入AI prompt | 只包含用户自己的承诺，不包含伙伴的具体数据 | 用户隐私泄露，信任崩塌 |
| 全局 | 多子系统并发写Memory导致状态不一致 | Memory写入走event sourcing，单线程序列化 | 用户画像矛盾，AI行为不可预测 |

---

## 八、总结

### 8.1 核心洞察

Sparkle不是"功能不足"的系统，而是"连接不足"的系统。5份前沿报告中的先进理念，Sparkle在**基础设施层面**已经实现了70-80%：

- Memory: 4种模型+57 key+CRUD ✅ 读路径已连通 ✅ 但写路径断开 ❌
- Proactive: Scheduler+Push+Intervention ✅ 但缺状态驱动 ❌
- Routing: 5+ provider+10+ tier+fallback ✅ 但缺可观测性 ❌
- Social: 好友+伙伴+群组+推荐 ✅ 但缺Policy Compiler ❌
- Learning: 4层认知+贝叶斯+策略 ✅ 但缺Skill沉淀 ❌

### 8.2 工作量估算（修正版）

| Phase | 核心改动 | 代码量 | 依赖 |
|-------|---------|--------|------|
| Phase 0A-Read | ~~Memory读路径接通~~ (v4.0: 已连通, 无需改动) | 0行 | 无 |
| Phase 0A-Write | Memory写路径接通 | ~80行 | 无 |
| Phase 0B | Prompt扩展 | ~15行 | 无（读路径已连通） |
| Phase 0C | Accountability→Intervention | ~20行 | 无 |
| Phase 0+Social | 社交信号→DualCoreRouter | ~10行 | 无 |
| Phase 0 测试 | 验证+回归 | ~30行 | — |
| **Phase 0 总计** | | **~155行** | |
| Phase 1 | State Aggregator + Push增强 + 时机评估 | ~350行 | Phase 0A-Read |
| Phase 2 | Memory Lifecycle + Sufficiency Judge + Routing History | ~620行 | Phase 0A |
| Phase 3 | 双层Skill System (Declarative + Procedural) | ~500行 | Phase 2 |
| Phase 4 | Accountability Policy Compiler | ~400行 | Phase 1 |

### 8.3 建议立即行动

**Phase 0A-Write（MemoryService写路径接通）** 是ROI最高的单个改动——接通写路径后，AI对话中产生的用户偏好、目标、关键事件将自动沉淀为长期记忆。建议立即启动，与Phase 0+Social（社交信号→Router，~10行）同步做。读路径已连通（v4.0确认），无需额外改动。

---

## 附录: 参考文献索引

| 编号 | 报告来源 | 核心参考 |
|------|----------|----------|
| R1 | 长期陪伴型Agent | PASK (DD-MM-PAS), Springdrift (Sensorium), 美团长程任务代理 (意图维护→条件唤醒), VisionClaw (始终在线), Deng等人 (人本主动对话) |
| R2 | Social Brain | Normative MAS/AMELI (关系→制度→控制), Microsoft Graph (permission-aware grounding), Teamwork Graph (ACL+agent visibility), Mem0 (entity linking) |
| R3 | Agent系统架构 | EverMemOS (MemCell→MemScene→Profile生命周期), HiMem (note-first retrieval + reconsolidation), Mem0 (ADD/UPDATE/DELETE/NOOP), Zep (temporal KG), Letta (pinned memory blocks), Voyager (skill library as code) |
| R4 | Skill自进化 | AutoSkill (对话→SKILL.md), SAGE (RL skill generation), Voyager (procedural memory=可执行代码), XSkill (双流经验+技能), Claude Agent Skills (SKILL.md标准) |
| R5 | Model Router | RouteLLM (偏好数据训练), DialRouter (多轮序列决策), RouterWise (resource-aware routing), Portkey (composable AI gateway), IRT-Router (可解释latent factors) |

*报告v4.0结束。v2.0所有事实性陈述经过5个并行Agent逐文件验证。v3.0合并独立第二审阅者的6项补充（元架构依赖图、Phase 0 Read/Write拆分、Context Sufficiency Judge、介入时机评估、Declarative/Procedural Skill区分、风险矩阵）和3项挑战修正（Social Brain范围扩展、代码量精确化、Routing History）。v4.0基于第三轮审查修正6项关键事实：MemoryService"半Ghost Ship"（读路径已连通）、StrategyStore 5阶段（非4阶段）、社交信号3种（非5种）、BehaviorSignalCollector 8种指标（非4种）、Phase 0A-Read已满足（聚焦写路径）、sufficiency_checker被低估（有3层检查但无用户上下文充分性判断）。*
