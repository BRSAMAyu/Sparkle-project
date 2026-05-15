# Plan Review & Knowledge Services 深度架构审计

> 审计范围: `plan_review_service.py` (2,624行) / `knowledge_service.py` (395行) / `retrieval_service.py` (676行)
> 审计日期: 2026-05-15
> 审计重点: 计划审查绕过、审查死锁、知识检索跨租户泄漏、质量评估准确性、超时保护、并发修改、申诉公平性

---

## 一、架构分析

### 1.1 Plan Review Service 架构

计划审查服务采用 **三层递进审查模型**:

```
Feasibility Gate (确定性规则)
    ↓ Critical → NEEDS_MODIFICATION
    ↓ Pass →
Quick Rule Check (轻量规则)
    ↓ 通过 → Quality Gate + Alignment Check → Auto-Approved
    ↓ 不通过 →
LLM Deep Review (大模型深度审查)
    ↓ 可选: Cross-Model Review (交叉审查)
    ↓
Quality Gate + Alignment Scoring → Final Decision
```

**核心决策路径**:
- 可行性门控 (`_collect_feasibility_comments`) — 纯确定性规则，检测时间/目标不匹配
- 快速规则检查 (`_quick_rule_check`) — 高风险工具、置信度、工具数量、风险标记、过度承诺
- LLM 深度审查 (`_llm_review`) — 带重试的大模型调用，含降级回退策略
- 交叉审查 (`_cross_model_review`) — 对低置信度/高风险计划使用第二模型验证
- 质量门控 (`PlanQualityGate`) — 多维度评分 (fit/feasibility/grounding/next_action/adaptation/outcome_learning)
- 画像对齐 (`_score_plan_alignment`) — 将计划与用户近期执行画像对齐

**反馈闭环**:
- 用户确认通过 `handle_review_feedback` → Redis `claim` 原子操作防并发
- 连续两次拒绝触发信息收集 → 重置计数
- 修改请求触发 `trigger_replanning` → 后台异步执行重新规划

### 1.2 Knowledge Service 架构

```
KnowledgeService (应用层)
    ├─ retrieve_context() — RAG v2.0, 含 HyDE 优化
    ├─ semantic_search() — GraphRAG 路径的轻量向量搜索
    ├─ create_or_update_link() — 知识图谱边管理
    └─ find_node_by_name() — 精确名称查找

KnowledgeRetrievalService (检索层)
    ├─ hybrid_search() — Redis BM25 + Vector 并行检索 + RRF 融合 + Reranking
    ├─ semantic_search_ranked_nodes() — pgvector 余弦距离搜索
    ├─ keyword_search() — ILIKE + JSONB 关键词搜索
    ├─ document_vector_search() — 文档块向量搜索 (含群组文件权限检查)
    └─ 多级降级链: Redis → pgvector → keyword → 空结果
```

**关键设计决策**: `KnowledgeNode` 是**全局共享实体**，不绑定 `user_id`。用户与节点的关联通过 `UserNodeStatus` 表 (mastery_score/is_unlocked 等) 实现。这意味着语义搜索和关键词搜索天然是跨用户的——节点是"公共知识"，用户状态是"私有进度"。

---

## 二、问题清单

### P0-01: 语义搜索无租户隔离但 `keyword_search` 伪装接受 `user_id`

- **位置**: `retrieval_service.py:565-613` (`keyword_search`) / `retrieval_service.py:509-563` (`semantic_search_ranked_nodes`) / `knowledge_service.py:326-385` (`semantic_search`)
- **描述**: `keyword_search` 方法签名接受 `user_id: UUID` 参数，但**函数体内完全未使用此参数**进行任何过滤。查询直接在全局 `KnowledgeNode` 表上执行 ILIKE 和 JSONB 搜索，无任何租户隔离。同样，`semantic_search_ranked_nodes` 和 `KnowledgeService.semantic_search` 均不接受 `user_id` 参数，直接在全表搜索。
- **影响**: 这是**有意的设计** (KnowledgeNode 是全局共享知识图谱)，但 `keyword_search` 的 `user_id` 参数会产生误导，让调用者以为搜索是租户隔离的。当前全局搜索在大多数场景是正确行为（知识节点本身不包含私密用户数据），但若未来 `KnowledgeNode` 增加私有节点类型（如 `source_type='user_private'`），则会变成真正的数据泄漏。
- **修复建议**: (1) 为 `keyword_search` 移除未使用的 `user_id` 参数，或在函数签名/文档中明确标注搜索是全局的; (2) 在 `KnowledgeNode` 模型增加 `visibility` 字段 (global/private/group)，并在检索时过滤; (3) 在 `semantic_search_ranked_nodes` 中增加 `visibility` 过滤条件以预留安全边界。

### P0-02: Pending Actions Store 过期时间仅 5 分钟，审查流程可能超时丢失

- **位置**: `pending_actions.py:31` (`expire_minutes: int = 5`)
- **描述**: 待确认操作存储默认 TTL 为 5 分钟。用户提交计划审查后，需要在 5 分钟内完成确认/拒绝/修改操作，否则操作过期丢失。对于复杂计划（含交叉审查、多轮 LLM 调用），用户可能需要更长时间阅读和理解计划内容，尤其是教育场景中的学生用户。
- **影响**: 用户在审阅计划过程中操作过期，导致: (1) 用户无法确认或拒绝已审查的计划; (2) 计划停留在未决状态; (3) 用户需要重新触发整个审查流程，增加延迟和 LLM 调用成本。
- **修复建议**: (1) 将 `expire_minutes` 从 5 分钟提升至 15-30 分钟; (2) 支持按 `tool_name` 配置不同过期时间，高风险操作保持短过期，计划审查使用长过期; (3) 在过期前通过 SSE 推送提醒用户。

### P1-01: `_cross_model_review` 失败时静默返回 `None`，审查降级无告警

- **位置**: `plan_review_service.py:1095-1126`
- **描述**: 交叉审查（第二模型验证）在异常时返回 `None`，调用方 (`review_plan` L384-411) 仅检查 `if cross_result:`，当为 `None` 时完全跳过交叉审查，不产生任何告警或指标。这意味着本应触发交叉审查的高风险计划在交叉审查服务故障时会退回到单模型审查结果。
- **影响**: 高风险计划（低置信度/高风险工具/多工具调用）在交叉审查服务故障时，仅依赖单模型审查，降低了安全防护层级。无指标追踪降级发生频率。
- **修复建议**: (1) 在交叉审查失败时增加 `RETRIEVAL_ERROR_TOTAL` 或专用指标; (2) 将交叉审查降级事件记录到 `review_feedback_entry`; (3) 考虑在连续 N 次交叉审查失败时触发全局告警。

### P1-02: `_should_cross_review` 使用 `tool_name` 属性但 `ToolCallSpec` 的字段名为 `name`

- **位置**: `plan_review_service.py:1078`
- **描述**: `_should_cross_review` 方法中使用 `tc.tool_name` 访问工具调用名称 (`tool_names = [tc.tool_name for tc in (plan.tool_calls or []) if hasattr(tc, "tool_name")]`)，但 `ToolCallSpec` dataclass 的字段名为 `name` 而非 `tool_name`。虽然代码使用了 `hasattr` 保护不会抛异常，但会导致 `tool_names` 始终为空列表，高风险工具的交叉审查触发条件永远不会被满足。
- **影响**: 基于高风险工具名称的交叉审查触发条件**失效**。包含 `delete_task`、`batch_delete` 等高风险工具的计划不会因工具名称触发交叉审查，仅能通过置信度或工具数量触发。
- **修复建议**: 将 `tc.tool_name` 改为 `tc.name`，并移除 `hasattr` 保护 (或保留但增加 `getattr(tc, 'name', getattr(tc, 'tool_name', ''))`)。

### P1-03: LLM 审查降级时空计划自动批准，缺乏安全兜底

- **位置**: `plan_review_service.py:1156-1172`
- **描述**: `_llm_review_fallback` 方法在 LLM 审查不可用时，对**空计划**（无工具调用）直接返回 `APPROVED` 且 `confidence=1.0`。虽然空计划确实不会产生破坏性操作，但 `confidence=1.0` 的设定具有误导性——这是一个降级决策，不应标记为高置信度。此外，空计划被批准后仍会进入后续执行流程，可能产生无意义的计划记录和事件。
- **影响**: (1) 降级批准被标记为高置信度，可能误导上游决策; (2) 空计划批准后会触发任务生成 (`_generate_tasks_after_approval`)，虽然该逻辑会因无工具而快速返回，但产生了不必要的系统负载和日志噪音。
- **修复建议**: (1) 将空计划降级批准的 confidence 设为 `0.5` 而非 `1.0`; (2) 在 `review_feedback_entry` 中标记 `fallback_used=True`; (3) 考虑直接返回 `REQUIRES_CONFIRMATION` 而非 `APPROVED`。

### P1-04: `review_plan` 方法过长（~270行），决策逻辑分散且存在重复

- **位置**: `plan_review_service.py:230-497`
- **描述**: `review_plan` 方法包含约 270 行代码，其中: (1) 对齐分数检查逻辑在自动批准路径 (L314-351) 和 LLM 审查路径 (L441-453) 中重复出现; (2) `review_feedback_entry` 构建和 `reasoning_payload` 构建逻辑重复; (3) 决策路径的分支嵌套深达 5 层。
- **影响**: 代码可维护性差，修改某个决策逻辑时容易遗漏另一处重复，增加引入 bug 的风险。例如，如果修改对齐分数的阈值，需要同步修改两处代码。
- **修复建议**: (1) 将 `review_plan` 拆分为 `_apply_alignment_check(decision, alignment_score, mode_strategy)` 和 `_finalize_review_result(...)` 等子方法; (2) 提取共用的反馈条目构建和指标上报逻辑; (3) 将自动批准路径和 LLM 审查路径的公共后处理合并。

### P1-05: `_generate_tasks_after_approval` 使用 `plan.type == PlanType.SPRINT` 硬编码难度推断

- **位置**: `plan_review_service.py:2119`
- **描述**: 任务生成时通过 `difficulty = "hard" if plan.type == PlanType.SPRINT else "medium"` 硬编码推断难度，完全忽略了审查阶段已经计算的 `quality_report` 和 `feasibility` 评分。一个通过审查的 SPRINT 计划可能实际上应该是 `medium` 或 `easy` 难度（如用户的背景和完成率已经很高）。
- **影响**: SPRINT 计划生成的任务始终被标记为 `hard` 难度，可能导致: (1) 新手用户收到过难的任务; (2) 任务完成率下降; (3) 与审查阶段的质量评估结论不一致。
- **修复建议**: (1) 从 `quality_report` 或 `user_context` 中推断难度，而非硬编码; (2) 考虑在 `review_result` 中携带推荐难度，传递给任务生成逻辑; (3) 至少应该根据用户 `skill_level` 调整难度。

### P1-06: `_execute_replan_action` 规划超时后降级为 fallback plan，但 fallback 仍需审查

- **位置**: `plan_review_service.py:2356-2376`
- **描述**: 重新规划时，如果 LangGraph Planner 超时（10秒），会使用 `build_fallback_plan` 生成降级计划。该降级计划随后会进入 `review_plan` 审查流程。但 `build_fallback_plan` 的质量通常很低（超时场景下的应急方案），审查大概率会拒绝或要求修改，导致用户陷入"超时 → fallback → 拒绝 → 重新规划 → 再超时"的死循环。
- **影响**: Planner 服务持续超时时，用户无法获得有效计划，形成无限重试循环。
- **修复建议**: (1) 记录 replan 尝试次数，连续 2 次 fallback 后直接通知用户并停止自动 replan; (2) 增加 replan 的全局超时（如 30 秒总时限）; (3) 在 fallback 场景下降低审查严格度。

### P2-01: `KnowledgeService.semantic_search` 缺少 `user_id` 参数但返回全局结果

- **位置**: `knowledge_service.py:326-385`
- **描述**: `semantic_search` 方法不接受 `user_id` 参数，直接在全局 `KnowledgeNode` 表上做向量搜索。与 `KnowledgeRetrievalService.semantic_search_ranked_nodes` 行为一致（全局搜索），但与 `GalaxyService.semantic_search` (接受 `user_id` 并附加用户状态) 的接口约定不一致。
- **影响**: 调用者无法获取用户特定的掌握度信息，返回的 `KnowledgeSearchHit` 仅包含节点基本信息和相似度，不含用户进度。这在 GraphRAG 场景下不影响检索质量，但限制了个性化排序的可能。
- **修复建议**: (1) 增加 `user_id` 可选参数，有值时关联 `UserNodeStatus` 做个性化排序; (2) 或在文档中明确标注此方法仅返回全局知识节点，不含用户维度。

### P2-02: `KnowledgeService.create_or_update_link` 存在重复的 `_invalidate_after_graph_mutation` 调用和延迟导入

- **位置**: `knowledge_service.py:148-166`
- **描述**: `create_or_update_link` 中，`from app.services.expansion_service import ExpansionService` 的延迟导入在两个分支（关系已存在/新建关系）中各出现一次，代码重复。且在已有关系不需要修改时 (`changed=False`)，仍然执行了不必要的 `_invalidate_after_graph_mutation` 调用。
- **影响**: (1) `changed=False` 时的无效缓存清除会产生不必要的性能开销; (2) 延迟导入在两个分支中重复，增加维护成本。
- **修复建议**: (1) 将延迟导入移到函数顶部; (2) 仅在 `changed=True` 时执行 `_invalidate_after_graph_mutation`。

### P2-03: `_build_review_prompt` 泄露内部字段名给 LLM

- **位置**: `plan_review_service.py:1293-1300`
- **描述**: 审查提示词中直接输出 `active_focus_id` 和 `pending_tasks_count` 等内部字段名，这些字段名对 LLM 的审查推理无实际帮助，反而占用 token 预算。当 `active_focus_id` 为 UUID 格式时，LLM 可能会尝试"理解"这个无意义的 ID 字符串。
- **影响**: 浪费 LLM token，轻微降低审查质量（信息噪音）。
- **修复建议**: (1) 用语义化描述替代原始字段名，如 "Current Focus: Active" / "None"; (2) 将 `pending_tasks_count` 转化为自然语言如 "3 pending tasks"。

### P2-04: 拒绝计数使用 `INCR` 但每次都重置 `EXPIRE`，可能延长计数窗口

- **位置**: `plan_review_service.py:2493-2496`
- **描述**: `track_rejection_count` 每次调用 `INCR` 后都执行 `EXPIRE key 3600`，这意味着每次新的拒绝都会把 TTL 重置为 1 小时。如果用户在第 55 分钟拒绝一次，然后在第 60 分钟又拒绝一次，第一次的计数不会被清除，实际窗口从第一次拒绝开始算可达近 2 小时。
- **影响**: 拒绝计数窗口比设计的 1 小时更长，可能导致 "连续两次拒绝" 的阈值在不合理的时间跨度内被触发。
- **修复建议**: 仅在第一次 `INCR` 返回 1 时设置 `EXPIRE` (`if count == 1: await redis.expire(key, 3600)`)。

### P2-05: `_hybrid_search` 的语义缓存使用 `user_id` 作为缓存键的一部分，但知识库是全局的

- **位置**: `retrieval_service.py:149-163`
- **描述**: `hybrid_search` 调用 `semantic_cache_service.get_with_lock` 时传入 `user_id=str(user_id)` 作为缓存键的一部分。但知识节点是全局共享的，相同查询对不同用户应返回相同的节点集合（用户状态是在后续 `_build_results_from_nodes` 中附加的）。按用户 ID 分片缓存会大幅降低缓存命中率。
- **影响**: 语义缓存效果差，每个用户的首次查询都会触发完整的检索流程，增加 Redis 和向量搜索负载。
- **修复建议**: (1) 缓存键不包含 `user_id`，改为使用全局缓存; (2) 用户状态在缓存命中后通过 `_build_results_from_nodes` 单独附加; (3) 或在文档中明确标注缓存策略的设计意图。

### P2-06: `retrieve_context` 中 `get_node_neighbors` 未传 `user_id`

- **位置**: `knowledge_service.py:309`
- **描述**: 在 `retrieve_context` 中，当策略启用图谱扩展 (`strategy.enable_graph`) 时，调用 `self.galaxy_service.get_node_neighbors(node.id, limit=5)` 获取邻居节点，但未传入 `user_id`。如果 `get_node_neighbors` 有访问控制逻辑，这可能导致返回其他用户的私有邻居节点。
- **影响**: 在图谱扩展路径中可能返回无权限的邻居节点信息。实际影响取决于 `get_node_neighbors` 的实现——如果它也是全局查询则无实际泄漏，但接口设计不一致。
- **修复建议**: 检查 `get_node_neighbors` 的实现，确认是否需要 `user_id` 参数进行访问控制。

### P2-07: `_score_plan_alignment` 的对齐评分算法过于粗糙

- **位置**: `plan_review_service.py:1484-1551`
- **描述**: 对齐评分使用简单的布尔匹配策略: 每个画像信号是否满足预定义条件（如 `low_scope = tool_count <= 5 and risk_count <= 1`）。这些阈值是硬编码的，不根据用户历史动态调整。例如，`task_difficulty: lower` 的满足条件是 `tool_count <= 5 and risk_count <= 1`，但一个有 6 个工具但都是简单查询的计划也会被判为"不满足低难度约束"。
- **影响**: 对齐评分精度有限，可能产生误判: (1) 将合理的计划判为对齐度低; (2) 将不合理的计划判为对齐度高。
- **修复建议**: (1) 引入连续评分而非布尔判断; (2) 将阈值参数化到 `mode_strategy` 或 `user_context`; (3) 考虑使用 LLM 对对齐度做辅助判断。

### P2-08: `_validate_feasibility` 中文科生检测逻辑存在刻板印象风险

- **位置**: `plan_review_service.py:960-977`
- **描述**: 可行性验证中包含对文科生背景的特殊处理: `_is_liberal_arts(user_background)` 检查后，如果用户尝试"爬虫"或"web开发"等目标，会检查计划是否包含"环境安装/基础"步骤，否则不通过可行性验证。这种基于背景标签的技能假设可能不准确，且硬编码的目标关键词列表（"爬虫/web开发/全栈/crawler"）无法覆盖所有情况。
- **影响**: (1) 文科生标签的用户即使已有编程基础，也可能被不必要地阻止; (2) 非文科生标签但同样缺乏基础的用户不会被此检查保护; (3) 关键词列表维护成本高。
- **修复建议**: (1) 基于用户实际技能评估（如已完成任务的类型/数量）而非背景标签做判断; (2) 将硬编码关键词列表移至配置; (3) 在阻止时提供更细致的解释和绕过路径。

---

## 三、审查流程防绕过评估

| 攻击路径 | 防护状态 | 说明 |
|---------|---------|------|
| 直接调用 `resume_plan_after_approval` 跳过审查 | **无防护** | 该方法不验证计划是否经过审查流程，仅检查 `pending_actions_store` 中是否存在 action。但 action 是在 `resume_plan_after_approval` 内部创建的，攻击者可构造任意 `plan_id` 直接调用。 |
| 构造高置信度 + 只读工具计划绕过 LLM 审查 | **已防护** | 快速规则检查 + 可行性门控 + 质量门控三层防护 |
| LLM 审查返回 `approved` 但置信度低 | **部分防护** | 置信度低于 0.7 会触发交叉审查，但交叉审查使用不同模型且无超时保护 |
| 降级场景（LLM 不可用）自动批准 | **部分防护** | 高风险工具仍需确认，但空计划会被自动批准 (P1-03) |
| 连续拒绝后触发信息收集绕过审查 | **已防护** | 使用 Redis 原子操作 `SET NX` 防并发触发 |

---

## 四、总结

### 按严重级别统计

| 级别 | 数量 | 关键问题 |
|------|------|---------|
| P0 | 2 | 知识搜索租户隔离接口误导、审查操作过期时间过短 |
| P1 | 6 | 交叉审查字段名错误、空计划降级批准、LLM 审查降级无告警、方法过长维护风险、硬编码难度推断、replan 死循环风险 |
| P2 | 8 | 接口一致性、重复代码、token 浪费、计数窗口延长、缓存命中率、接口参数缺失、评分粗糙、刻板印象风险 |

### 核心发现

1. **Plan Review 的安全防护体系整体健全** — 三层递进审查 + 交叉审查 + 质量门控 + 可行性验证提供了良好的纵深防御。
2. **最严重的功能缺陷是 P1-02** — `_should_cross_review` 使用 `tool_name` 而非 `name`，导致高风险工具的交叉审查触发条件**静默失效**。
3. **知识服务的租户隔离设计是合理的** — `KnowledgeNode` 作为全局共享实体的设计在知识图谱场景中是正确选择，但接口签名应明确反映这一点。
4. **审查流程的健壮性瓶颈在降级路径** — LLM 不可用时的降级策略存在多处可改进点（空计划批准、降级无指标、replan 循环）。
