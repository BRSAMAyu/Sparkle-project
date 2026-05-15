# RAG Pipeline & LLM Service 层深度架构审计

> 审计日期: 2026-05-15
> 审计范围: `graph_rag.py` (2,396行) / `llm_service.py` (1,725行) / `embedding_service.py` (188行) / `llm_router.py` (1,232行) / `cost_controller.py` (272行) / `providers.py` / `fallback.py` / `concurrency.py`
> 审计人: Opus Agent

---

## 第一部分: 架构分析

### 1.1 GraphRAG 检索器 (`graph_rag.py`)

**检索管线主流程** (`retrieve` 方法, L2066-2330):

```
用户查询 → 预算检查 → 路由策略选择 → 缓存查找
  → [三种检索模式之一]:
    ├─ Multi-Hop (对比/关系类查询)
    ├─ FastPath (并行加速)
    └─ Sequential (串行兜底)
  → RetrievalDirective过滤 → Token预算执行 → 缓存写入 → 成本记录
```

**多跳遍历** (`_retrieve_multi_hop`, L924-1036):
- 通过LLM提取2-3个核心概念 (`extract_concepts_for_synthesis`)
- 并行执行: 概念提取 + 实体提取 + 基础向量检索 + 用户兴趣
- 对每个概念独立执行 `_vector_search_scoped`
- 图检索通过AGE (Apache AGE) Cypher查询执行
- 通过 `_merge_multi_hop_vector_results` 合并基础结果与概念结果
- `_build_multi_hop_metadata` 构建 `concept_blocks` 和 `graph_connections`
- 图桥接通过 `galaxy_service.find_relation_bridge` 在节点间查找关系路径

**HyDE增强** (`_prepare_vector_query`, L1412-1455):
- 精度探针: 先用原始查询做一次dense search (`_probe_query_chunk_similarity`), 若最高相似度 >= 0.85, 跳过HyDE
- HyDE扩展: 调用LLM生成假设性教科书段落, 超时2秒, 作为embedding查询文本
- 结果以 `HyDEPreparation` 数据类封装, 包含 `source`, `used_hyde`, `raw_similarity`, `skip_reason`

**RRF融合** (`_rrf_fuse`, L1129-1168):
- Reciprocal Rank Fusion, 参数 k=60
- 输入多个排序列表 (dense_results + bm25_results)
- 合并去重, 保留最高分来源
- 可选rerank (`_rerank_hybrid_results`), 通过 `settings.ENABLE_GRAPHRAG_RERANKER` 控制

**缓存机制**:
- 缓存键: SHA256(query + user_id + intent + knowledge_version + feedback_version + group_scope)
- TTL: `settings.GRAPHRAG_CACHE_TTL_SECONDS`
- 仅在 FastPath 模式下启用缓存
- 缓存命中时跳过全部检索, 直接返回 `GraphRAGResult`

**Token预算执行** (`_enforce_token_budget`, L463-486):
- 接受 `token_budget` 整数参数
- 按 `len(content) // 4` 估算每个chunk的token数
- 累积计算, 超预算则截断
- 保底至少保留1个结果

### 1.2 LLM Service (`llm_service.py`)

**Provider抽象层**:
- `OpenAICompatibleProvider` (`providers.py`): 封装 `AsyncOpenAI`, 统一兼容 DeepSeek/Zhipu/Xiaomi/DashScope/SiliconFlow
- 初始化时传入 `api_key` + `base_url`, 创建单一 `AsyncOpenAI` 实例
- 超时: connect=10s, total=60s (通过 `OpenAITimeout` 或 `httpx.Timeout`)

**动态路由**:
- `LLMRouter` 管理 24+ 个模型配置, 分为 FREE/FAST/STANDARD/PLUS/PRO/MAX/TOP/SPECIALIST/GLM_BATCH 层级
- 选择逻辑: AgentProfile → TaskType → 复杂度分析 → 健康检查 → tier映射 → 候选模型列表
- 支持环境变量覆盖 tier 映射 (`LLM_TIER_*`)
- 模型健康状态: 内存中追踪, 5次连续失败 → 不健康, 300秒无失败 → 自动恢复

**流式生命周期**:
- `stream_chat` (L937-1060): 非工具调用的流式输出
  - Demo模式 → 预算检查 → circuit breaker检查 → 回退管理器包装流 → yield chunks
  - 有 `first_chunk_time` (TTFC) 和 `chunk_count` 性能日志
- `chat_stream_with_tools` (L1263-1398): 带工具调用的流式输出
  - 收集 `tool_call_chunks` → 解析参数 → `tool_call_end` yield → usage data
  - 支持 MIMO 思考链 (`reasoning_content`) 和联网搜索引用 (`annotations`)
- `_create_raw_stream_with_fallback` (L774-789): 流式回退, 仅在首个chunk前触发

**工具调用**:
- `chat_with_tools`: OpenAI function calling 格式, 返回 `LLMResponse` 含 `tool_calls` 列表
- `continue_with_tool_results`: 将工具结果追加到消息, 继续对话
- 安全层: `sanitize_tool_payload` + `wrap_tool_result`

**回退链** (`fallback.py`):
- `execute_with_fallback`: 最多3次回退尝试
  - 检测原因: 429/timeout/503/connection/quota
  - 同tier优先 → 降级tier → 指数退避 (100ms * 2^n, 上限2s)
  - `ModelHealthTracker` (Redis): 失败计数 + 熔断器 (5次失败, 60秒恢复)
- `execute_stream_with_fallback`: 仅在首次chunk前回退, 开始传输后直接抛出

**安全层** (`llm_security_wrapper.py`):
- 输入净化 (`LLMSafetyService`): 提示注入检测, XSS过滤, 敏感信息脱敏
- 配额检查 (`LLMCostGuard`): per-user token估算 + Redis配额
- 输出验证 (`LLMOutputValidator`): 敏感信息检测, XSS过滤
- 流式输出无法回滚, 仅记录警告

### 1.3 Embedding Service (`embedding_service.py`)

**双供应商切换**:
- 主: DashScope (阿里百炼) - `text-embedding-v4`, 批量限制10条
- 备: SiliconFlow - `Qwen/Qwen3-Embedding-4B` (同款模型)
- 自动故障切换: 主供应商失败 → circuit breaker检查 → 备用供应商
- 重试: tenacity `stop_after_attempt(3)`, `wait_exponential(min=2, max=10)`

**批量处理**:
- DashScope: 按 `DASHSCOPE_MAX_BATCH=10` 分批, `asyncio.to_thread` 同步调用
- SiliconFlow: 单次HTTP POST, 无批量限制

**降级行为**:
- DEMO_MODE下返回全零向量 `[[0.0] * dim for _ in texts]`
- 正常模式下所有供应商失败则抛出 `RuntimeError`

### 1.4 成本流控集成

**成本流向**:
```
LLM调用 → llm_service.chat/chat_with_tools/chat_stream_with_tools
  → record_llm_cost(model_key, prompt_tokens, completion_tokens, source)
    → BudgetCircuitBreaker.record_spend(LLM, cost)
      → Redis INCRBYFLOAT + Prometheus Counter

RAG检索 → graph_rag.retrieve()
  → record_rag_cost("graphrag_retrieve")
    → BudgetCircuitBreaker.record_spend(RAG, cost)
```

**关键发现**:
- `llm_router.py` **不导入也不调用** `cost_controller` 的任何函数
- 预算执行仅在调用点 (`llm_service`, `graph_rag`), 不在模型选择层
- `cost_controller` 提供了 `is_llm_within_budget()` / `is_rag_within_budget()` / `check_and_trip()` 但:
  - `is_llm_within_budget()` 仅在 `chat()` 和 `stream_chat()` 入口检查
  - `reason()` 方法不检查预算
  - 没有基于预算的自动降级 (只有硬性拒绝)

---

## 第二部分: 问题报告

### 问题 #1: `cost_controller` 与 `llm_router` 断连 — 预算不执行于模型选择层

**严重性**: P0
**位置**: `backend/app/core/llm_router.py` (全文) + `backend/app/core/cost_controller.py`
**描述**: `cost_controller.py` 定义了每日预算 (LLM $10/天, RAG $2/天, Aurora $5/天) 和 `BudgetCircuitBreaker`, 但 `llm_router.py` 的 `select_model()` 和 `_select_by_policy()` 方法完全不导入、不查询、不执行任何 `cost_controller` 函数。模型选择仅基于 health/tier/complexity, 完全无视当前日消耗量。这意味着:
1. 一个bug或恶意客户端可以在预算耗尽前持续触发昂贵的MAX/TOP层级模型调用
2. `llm_service.chat()` 和 `stream_chat()` 虽然在入口做了 `is_llm_within_budget()` 检查, 但 `reason()` 方法没有此检查
3. 即使入口检查拒绝, 回退管理器的多次重试仍可能在检查与拒绝之间产生额外调用

**影响**: 每日LLM/RAG/Aurora成本可能无限增长, 预算形同虚设
**修复建议**:
1. 在 `LLMRouter.select_model()` 开头添加 `await is_llm_within_budget()` 检查, 超预算时自动降级到免费/低成本模型
2. 在 `reason()` 方法开头添加 `is_llm_within_budget()` 检查
3. 考虑在 `BudgetCircuitBreaker.check_budget()` 中添加 "soft limit" (80%预算时自动降级tier) + "hard limit" (100%时拒绝)

---

### 问题 #2: 图检索 (`graph_search`) 无用户隔离 — 潜在跨租户数据泄露

**严重性**: P0
**位置**: `backend/app/orchestration/graph_rag.py:1860-1941` (`graph_search` 方法)
**描述**: `graph_search` 方法的 Cypher 查询仅通过实体名称匹配 `KnowledgeNode`, 不包含任何 `user_id` 过滤:

```cypher
MATCH (start:KnowledgeNode {name: $entity})
-[rel]-(related:KnowledgeNode)
WHERE toFloat(rel.strength) > $min_strength
RETURN { ... }
```

这意味着:
1. 用户A的 "量子计算" 知识节点可以关联到用户B的私有节点
2. 返回的 `description` 字段可能包含用户B的私有笔记内容
3. `find_related_concepts` (L2364-2396) 和 `find_learning_path` (L2332-2362) 同样无用户隔离

虽然 `_redis_doc_matches_user` (L1682-1697) 对Redis文档结果做了用户/群组过滤, 但AGE图查询的结果完全没有此过滤。

**影响**: 用户A可能通过图检索看到用户B的知识图谱内容和关系
**修复建议**:
1. 在 `graph_search` 的Cypher查询中添加用户范围过滤:
```cypher
MATCH (start:KnowledgeNode {name: $entity})
-[rel]-(related:KnowledgeNode)
WHERE toFloat(rel.strength) > $min_strength
  AND (related.user_id = $user_id OR related.scope = 'public' OR related.id IN $accessible_node_ids)
```
2. 为 `find_related_concepts` 和 `find_learning_path` 添加 `user_id` 参数
3. 考虑在AGE图中为节点添加 `user_id` 属性和 `scope` (public/private/group)

---

### 问题 #3: 流式响应无总体超时 — 可能无限挂起

**严重性**: P1
**位置**: `backend/app/services/llm_service.py:937-1060` (`stream_chat` 方法) + `backend/app/services/llm/providers.py:121-156` (`stream_chat` 方法)
**描述**: `stream_chat` 的流式路径没有总体超时保护:
- `providers.py` 的 `stream_chat` 仅在创建连接时有60s总超时, 但一旦开始流式传输, `async for chunk in stream` 没有超时限制
- 如果LLM API在传输中途停止发送数据但不断开连接, 客户端将无限等待
- `llm_service.py` 的 `stream_chat` 方法没有 `asyncio.timeout` 包装
- 对比: `chat()` 有 `asyncio.timeout(120)`, `reason()` 有 `asyncio.timeout(180)`, 但流式没有

**影响**: WebSocket连接可能永久挂起, 资源泄漏, 用户体验极差
**修复建议**:
1. 在 `providers.py` 的 `stream_chat` 中添加 per-chunk 超时:
```python
async for chunk in stream:
    content = chunk.choices[0].delta.content
    if content:
        yield content
# 改为:
async for chunk in asyncio.timeout(30).wrap(stream):
    ...
```
2. 或在 `llm_service.py` 的 `stream_chat` 外层添加全局超时 (如 120s), 超时后主动关闭stream

---

### 问题 #4: `reason()` 方法缺少预算前置检查

**严重性**: P1
**位置**: `backend/app/services/llm_service.py:791-873` (`reason` 方法)
**描述**: `chat()` (L576) 和 `stream_chat()` (L979) 方法都在入口处检查 `is_llm_within_budget()`, 但 `reason()` 方法完全没有此检查。`reason()` 通常使用更昂贵的模型 (DEEP_REASONING tier → PRO/MAX), 且超时更长 (180s), 消耗更多token。这意味着:
1. 即使LLM日预算已耗尽, `reason()` 调用仍会继续
2. 攻击者可以绕过预算限制, 通过触发推理任务而非普通对话

**影响**: 预算被绕过, 高成本推理调用不受控制
**修复建议**: 在 `reason()` 方法开头 (L828 附近) 添加:
```python
if not await is_llm_within_budget():
    raise HTTPException(status_code=429, detail="Daily AI usage limit reached.")
```

---

### 问题 #5: Embedding服务失败静默返回全零向量 — 搜索质量无感降级

**严重性**: P1
**位置**: `backend/app/services/embedding_service.py:114-116`
**描述**: DEMO_MODE下, 所有供应商失败时返回 `[[0.0] * self.embedding_dim for _ in texts]`, 不抛出异常。如果在生产环境意外开启 DEMO_MODE:
1. 所有文档向量为全零, 语义搜索退化为随机结果
2. HyDE增强的 `_probe_query_chunk_similarity` 将返回无意义的相似度
3. Redis Search的hybrid_search中, 全零向量会匹配到随机的文档 (取决于向量索引实现)
4. 没有任何告警或指标记录此降级事件

此外, `get_embedding` 被 `retry(3次)` 包装, 但 `batch_embeddings` 也有 `retry(3次)`, 导致 `get_embedding` 实际上会有 3 * 3 = 9次重试。

**影响**: 搜索质量大幅下降但无任何可观测性
**修复建议**:
1. 在 DEMO_MODE 全零向量返回前, 记录 WARNING 日志 + Prometheus 计数器
2. 添加 `embedding_fallback_total` Prometheus 指标
3. 修复双重重试: `get_embedding` 不应有独立的 `@retry`, 因为它已调用有 `@retry` 的 `batch_embeddings`
4. 生产环境应禁用 DEMO_MODE 并添加启动检查

---

### 问题 #6: GraphRAG缓存键不含用户角色/权限信息 — 潜在缓存投毒

**严重性**: P1
**位置**: `backend/app/orchestration/graph_rag.py:683-705` (`_build_cache_key` 方法)
**描述**: 缓存键基于 `query + user_id + intent + knowledge_version + feedback_version + group_scope` 构建, 但:
1. 缓存是全局共享的 (无namespace隔离)
2. 虽然包含 `user_id`, 但如果同一用户在群组上下文中查询, `group_scope` 的变化会改变缓存键, 这本身是正确的
3. 然而, 缓存存储的 `GraphRAGResult` 包含完整的 `vector_results` 和 `graph_results`, 这些数据可能包含其他用户共享到群组的内容
4. 如果用户被移出群组, 旧的缓存键 (包含该群组scope) 仍可能在TTL内返回包含该群组数据的缓存结果

此外, 缓存键使用 SHA256 哈希, 无法通过键名审计缓存内容, 增加了调试难度。

**影响**: 被移出群组的用户可能在TTL内仍能看到群组内容
**修复建议**:
1. 在 `_get_cached_result` 返回前, 验证当前用户仍有权限访问 `group_scope` 中的群组
2. 或者, 在群组成员变更时, 使相关缓存失效 (通过修改 `feedback_version` 或 `knowledge_version`)
3. 考虑在缓存键中包含群组成员版本号

---

### 问题 #7: 多跳遍历无深度限制执行 — 图遍历可能过大

**严重性**: P2
**位置**: `backend/app/orchestration/graph_rag.py:1860-1941` (`graph_search`)
**描述**: `graph_search` 方法接受 `depth` 参数但实际未使用它。Cypher查询硬编码为一跳关联:
```cypher
MATCH (start:KnowledgeNode {name: $entity})
-[rel]-(related:KnowledgeNode)
```
而 `self.max_depth = 2` (L677) 从未被引用。这意味着:
1. 无论 `depth` 参数传什么值, 图搜索始终只做一跳
2. 如果将来有人实现多跳Cypher (`*1..depth`), 没有 `depth` 上限保护, 可能导致指数级结果膨胀
3. `LIMIT 10` 是硬编码的, 不能通过参数调整

同时, `_retrieve_multi_hop` 的概念级联搜索中, 每个概念搜索 `top_k=3`, 概念数最多3个, 总计最多9次向量搜索 + 1次基础搜索 = 10次搜索, 这可能在Redis高负载时造成压力。

**影响**: 当前一跳限制是安全的但与API承诺不一致; 未来扩展时可能引入性能问题
**修复建议**:
1. 要么移除 `depth` 参数 (如果确定只需要一跳), 要么实际使用它
2. 添加 `max_depth` 硬上限 (如 `min(depth, 3)`), 防止未来实现多跳时失控
3. 考虑为多概念并行搜索添加总并发限制

---

### 问题 #8: `reason()` / `stream_chat()` 缺少成本记录 — 账单不完整

**严重性**: P2
**位置**: `backend/app/services/llm_service.py:791-873` (`reason`) + L937-1060 (`stream_chat`)
**描述**: `chat_with_tools` (L1132-1140), `continue_with_tool_results` (L1243-1247), `chat_stream_with_tools` (L1382-1390) 都有 `record_llm_cost` 调用, 但:
1. `reason()` 方法 (L791-873) 没有任何成本记录 (没有 `_record_token_usage`, 没有 `record_llm_cost`, 没有 `_track_daily_user_tokens`)
2. `stream_chat()` (L937-1060) 也没有成本记录 (流式传输中无法获取usage数据, 除非provider返回 `stream_options.include_usage`)
3. `chat()` 方法 (L522-653) 虽然有预算前置检查, 但实际成本记录缺失 — 没有usage数据返回时无法记录

这意味着推理调用 (最昂贵的调用类型) 和流式调用 (最常见的调用类型) 的成本都没有被记录到 `cost_controller` 中。

**影响**: 实际LLM成本被大幅低估, 预算检查基于不完整数据
**修复建议**:
1. `reason()` 方法在回退管理器成功后, 通过估算 (输入消息长度 * 0.25) 记录最低成本
2. `stream_chat()` 在流结束后, 检查是否收到usage chunk并记录
3. `chat()` 方法在provider返回response后, 如果有usage则记录 (类似 `chat_with_tools` 的做法)
4. 添加 "估算兜底" 逻辑: 当没有精确usage数据时, 用 `len(messages) * 0.25 + len(response) * 0.25` 估算

---

### 问题 #9: Demo模式模糊匹配过于宽松 — 误触发预设响应

**严重性**: P2
**位置**: `backend/app/services/llm_service.py:496-508` (`_check_demo_match`)
**描述**: 模糊匹配逻辑: `if len(key) >= 3 and (key in user_content or user_content in key)`:
1. `user_content in key` 意味着如果用户输入 "帮我" 三个字, 就能匹配到 "帮我制定高数复习计划" (因为 "帮我" in key)
2. 这不是真正的模糊匹配, 而是 "包含关系" 匹配, 极易误触发
3. 所有未匹配的查询返回通用响应 (L503-508), 伪装成正常LLM输出

**影响**: 演示时可能返回无关预设内容, 误导演示观众
**修复建议**:
1. 移除 `user_content in key` 方向的匹配 (只保留 `key in user_content`)
2. 或改用编辑距离/语义相似度匹配
3. 对未匹配查询返回明确的演示模式标识, 而非伪装成正常响应

---

### 问题 #10: `_llm_service_cache` 无大小限制 — 内存泄漏风险

**严重性**: P2
**位置**: `backend/app/services/llm_service.py:1515` (`_llm_service_cache`)
**描述**: `_llm_service_cache` 是模块级字典, 按 `str(agent_role)` 缓存 `LLMService` 实例。每个实例持有 `AsyncOpenAI` 客户端 (包含HTTP连接池)。虽然当前 `AgentRole` 枚举有限 (~10个), 但:
1. `get_llm_service` 接受 `str` 类型, 不验证是否为有效 `AgentRole`
2. 任意字符串都会创建新实例并永久缓存
3. 没有LRU淘汰或上限检查

**影响**: 如果有代码传入动态生成的agent_role字符串, 会无限创建实例
**修复建议**:
1. 将 `_llm_service_cache` 改为 `functools.lru_cache(maxsize=16)` 或使用 `cachetools.LRUCache`
2. 在 `get_llm_service` 中验证 `agent_role` 是否为有效枚举值或已知别名

---

### 问题 #11: 回退管理器访问 `llm_router` 私有属性 — 耦合脆弱

**严重性**: P2
**位置**: `backend/app/services/llm/fallback.py:259,264` + `backend/app/core/llm_router.py:133-136`
**描述**: `LLMModelFallbackManager._get_fallback_candidates` 直接访问 `llm_router._tier_mapping` 和 `llm_router._available_models` (带下划线的私有属性):
```python
tier_mapping = llm_router._tier_mapping
config = llm_router._available_models[model_key]
```
如果 `LLMRouter` 重构内部数据结构 (如改用数据库存储模型配置), 回退管理器将静默失败。

**影响**: 维护风险, 重构可能导致回退完全失效
**修复建议**: 在 `LLMRouter` 中添加公共接口:
```python
def get_models_for_tier(self, tier: ModelTier) -> list[str]: ...
def get_model_config(self, model_key: str) -> ModelConfig | None: ...
```

---

### 问题 #12: 流式回退中流已经开始后的异常处理不完善

**严重性**: P2
**位置**: `backend/app/services/llm/fallback.py:459-549` (`execute_stream_with_fallback`)
**描述**: `StreamingFallbackHandler.execute` 中, 如果流式传输中途失败:
```python
if self.first_chunk_received:
    raise e  # 直接抛出, 不回退
```
这意味着:
1. 用户看到部分响应后突然中断, 无错误信息
2. WebSocket连接可能处于不确定状态
3. 没有尝试向客户端发送错误标记或重连提示

**影响**: 用户体验差, 部分响应突然中断
**修复建议**:
1. 在抛出异常前, yield一个特殊的错误标记chunk (如 `[STREAM_ERROR]`)
2. 或者由上层 (orchestrator) 捕获并生成优雅的降级消息
3. 考虑在WebSocket层面添加心跳检测, 识别断开的流

---

### 问题 #13: `graph_search` 的 `find_learning_path` 可变长度路径无上限保护

**严重性**: P2
**位置**: `backend/app/orchestration/graph_rag.py:2332-2362` (`find_learning_path`)
**描述**: Cypher查询使用 `[:PREREQUISITE*1..5]`, 允许最多5跳路径。如果图谱中存在环路或超长链路:
1. `UNWIND nodes(path)` 会展开路径上所有节点, 可能产生大量重复
2. 没有 `LIMIT` 子句限制返回的路径数量
3. 没有去重, 同一节点可能在不同路径中多次返回

**影响**: 图谱数据量大时可能导致查询超时或内存溢出
**修复建议**:
1. 添加 `LIMIT 20` 到Cypher查询
2. 在Python层对结果按节点名去重
3. 添加查询超时 (如 `asyncio.wait_for(..., timeout=5.0)`)

---

### 问题 #14: `EmbeddingService` 全局实例在import时创建 — 初始化顺序问题

**严重性**: P2
**位置**: `backend/app/services/embedding_service.py:188`
**描述**: `embedding_service = EmbeddingService()` 在模块级别创建, 构造函数读取 `settings.EMBEDDING_PROVIDER` 等配置。如果 `settings` 在import时未完全初始化 (如.env未加载), 将使用默认值且永不更新。

**影响**: 配置变更不生效, 需要重启服务
**修复建议**: 改为延迟初始化 (lazy init) 或使用依赖注入

---

## 问题汇总

| # | 严重性 | 文件 | 摘要 |
|---|--------|------|------|
| 1 | **P0** | `llm_router.py` + `cost_controller.py` | 预算不执行于模型选择层, `reason()` 无预算检查 |
| 2 | **P0** | `graph_rag.py:1860` | 图检索无用户隔离, 潜在跨租户数据泄露 |
| 3 | **P1** | `llm_service.py` + `providers.py` | 流式响应无总体超时, 可能无限挂起 |
| 4 | **P1** | `llm_service.py:791` | `reason()` 缺少预算前置检查 |
| 5 | **P1** | `embedding_service.py:114` | DEMO_MODE全零向量无告警, 双重重试导致9次尝试 |
| 6 | **P1** | `graph_rag.py:683` | 缓存键不含权限版本, 群组权限变更后缓存不过期 |
| 7 | **P2** | `graph_rag.py:1860` | `depth` 参数未使用, 与API承诺不一致 |
| 8 | **P2** | `llm_service.py:791,937` | `reason()`/`stream_chat()` 缺少成本记录 |
| 9 | **P2** | `llm_service.py:496` | Demo模式模糊匹配过于宽松 |
| 10 | **P2** | `llm_service.py:1515` | `_llm_service_cache` 无大小限制 |
| 11 | **P2** | `fallback.py:259` | 直接访问 `llm_router` 私有属性 |
| 12 | **P2** | `fallback.py:459` | 流式传输中断后异常处理不完善 |
| 13 | **P2** | `graph_rag.py:2332` | `find_learning_path` 无LIMIT, 可能超时 |
| 14 | **P2** | `embedding_service.py:188` | 全局实例import时创建, 配置不灵活 |

**P0: 2个** | **P1: 4个** | **P2: 8个**

---

## 优先修复建议 (按影响排序)

1. **立即修复** — 问题 #1: 在 `llm_router.select_model()` 和 `reason()` 中集成成本控制器
2. **立即修复** — 问题 #2: 图检索添加用户隔离, 评估数据泄露范围
3. **本周修复** — 问题 #3: 流式添加 per-chunk 超时 + 全局超时
4. **本周修复** — 问题 #4: `reason()` 添加预算检查 (1行代码修复)
5. **本周修复** — 问题 #8: `reason()`/`stream_chat()` 添加成本记录
6. **下周修复** — 问题 #5, #6, #7, #9-14
