# Sparkle 智能学习助手：混合检索与重排序架构升级报告 (v3.0)

**版本**: v3.0  
**日期**: 2025-12-27  
**状态**: 规划中  
**目标**: 解决“查不准、幻觉多、专有名词失效”痛点，构建工业级 RAG 检索系统。

## 1. 现状与痛点分析 (Current State)

### 1.1 当前架构 (RAG v1.0)
*   **存储**: PostgreSQL 16 (pgvector extension)
*   **检索**: 
    *   语义检索: `ORDER BY embedding <=> query_embedding` (Cosine Distance)
    *   关键词检索: SQL `ILIKE` (简单的子串匹配，非全文检索)
*   **融合**: 简单的线性加权或分开展示
*   **重排序**: 无 (依赖向量相似度直接截断)

### 1.2 核心痛点
1.  **专有名词失效**: 搜索特定的代码函数名、错误码或公式 ID 时，Embedding 往往无法精确匹配（因为语义可能被稀释），而 `ILIKE` 无法处理词形变化和权重。
2.  **长尾知识检索差**: 对于非热门、低频的知识点，向量召回率低。
3.  **上下文缺失**: 固定长度切片可能切断上下文，导致 LLM 回答时缺乏必要信息。
4.  **延迟**: 随着数据量增加，PGVector 的纯暴力搜索（如果不加 IVFFlat 索引）延迟会上升。

## 2. 目标架构 (RAG v2.0)

我们将引入 **Redis Stack (RediSearch)** 作为核心搜索引擎，利用其原生支持的 Hybrid Search (Vector + BM25) 能力，并结合 **Cross-Encoder** 进行精细重排序。

### 2.1 架构图

```mermaid
graph TD
    UserQuery[用户查询] --> QueryAnalysis[查询分析/HyDE]
    QueryAnalysis --> |语义向量| PathA[Path A: 稠密检索 (Vector)]
    QueryAnalysis --> |关键词| PathB[Path B: 稀疏检索 (BM25)]
    
    subgraph "Redis Stack Engine"
        PathA --> RedisIndex
        PathB --> RedisIndex
        RedisIndex[Redis Search Index\n(Parent-Child Schema)]
    end
    
    RedisIndex --> |Top 100| Candidates[候选集融合 (RRF)]
    Candidates --> Reranker[重排序 (Cross-Encoder)]
    Reranker --> |Top 5| LLM[LLM 生成回答]
```

## 3. 详细设计 (Detailed Design)

### 3.1 预处理与索引层 (Ingestion)

放弃 PostgreSQL 直接作为检索源，改为 **Postgres (Source of Truth) -> Redis (Search Index)** 的同步模式。

#### 3.1.1 智能切片 (Parent-Child Indexing)
为了解决“检索精准度”与“上下文完整性”的矛盾，采用父子索引策略：

*   **Parent Chunk (完整上下文)**:
    *   对应 `KnowledgeNode`。
    *   长度: 完整内容 (或 800-1000 tokens)。
    *   存储: Postgres (主), Redis JSON (作为引用)。
*   **Child Chunk (检索单元)**:
    *   对 Parent 进行滑动窗口切分。
    *   长度: 100-200 tokens (Overlap: 50 tokens)。
    *   存储: Redis JSON (用于建立向量索引)。
    *   索引逻辑: 搜索时匹配 Child，返回时通过 `parent_id` 找回 Parent 内容喂给 LLM。

#### 3.1.2 Redis Schema 设计
利用 RedisJSON + RediSearch。

**Key Format**: `sparkle:chunk:{parent_id}:{chunk_index}`

```json
{
  "id": "uuid-chunk-01",
  "parent_id": "uuid-node-A",
  "content": "Python 的列表推导式是一种...",  // Child chunk content
  "vector": [0.12, 0.33, ...],            // Embedding of Child chunk
  "subject_id": 101,                      // Filter
  "importance": 5,                        // Filter
  "keywords": "python list comprehension" // Text search field
}
```

**Index Definition (`FT.CREATE`)**:
```bash
FT.CREATE idx:knowledge ON JSON 
  PREFIX 1 "sparkle:chunk:" 
  SCHEMA 
    $.content AS content TEXT WEIGHT 1.0
    $.keywords AS keywords TEXT WEIGHT 2.0
    $.subject_id AS subject_id NUMERIC
    $.vector AS vector VECTOR HNSW 6 DIM 1024 DISTANCE_METRIC COSINE TYPE FLOAT32
```

### 3.2 双路召回策略

#### Path A: 稠密检索 (Dense)
*   **Query**: 用户 Query 的向量 (或 HyDE 生成的向量)。
*   **Command**: `FT.SEARCH idx:knowledge "*=>[KNN 50 @vector $query_vec AS vector_score]"`
*   **优势**: 语义理解，跨语言匹配。

#### Path B: 稀疏检索 (Sparse)
*   **Query**: 提取的关键词。
*   **Command**: `FT.SEARCH idx:knowledge "@content:(keyword1 | keyword2) @keywords:(keyword1)"`
*   **算法**: BM25 (Redis 默认)。
*   **优势**: 精确匹配，专有名词命中。

### 3.3 融合与重排序 (Fusion & Rerank)

#### 3.3.1 RRF 融合 (已在 `RerankService` 中定义)
由于 Redis 和 BM25 分数机制不同，使用排名融合：
$$ Score = \frac{1}{k + rank_{vector}} + \frac{1}{k + rank_{bm25}} $$

#### 3.3.2 Cross-Encoder 重排序
*   **模型**: `BAAI/bge-reranker-v2-m3` (支持多语言，性能强)。
*   **部署**: 本地加载 (HuggingFace) 或独立推理服务。
*   **逻辑**: 对 RRF 选出的 Top 30-50 个 Child Chunks，获取其对应的 Parent Content，与 Query 拼接计算相关性得分。

## 4. 实施路线图 (Implementation Plan)

### Phase 1: 基础设施准备 (Day 1)
1.  **Redis 配置**: 确认 `docker-compose.yml` 中 Redis Stack 可用 (已完成)。
2.  **Schema 定义**: 编写 Python 脚本创建 Redis 索引 (`scripts/init_redis_index.py`)。
3.  **数据同步**: 编写 `scripts/sync_pg_to_redis.py`，将现有的 Postgres `KnowledgeNode` 切片并同步到 Redis。

### Phase 2: 检索服务重构 (Day 2)
1.  **Redis Client**: 在 `backend/app/core` 中封装 `RedisSearchClient`。
2.  **Hybrid Logic**: 重写 `GalaxyService.hybrid_search`，移除 Postgres 搜索逻辑，改为调用 Redis。
3.  **Chunking Logic**: 实现 `SemanticSplitter` 类，处理父子切片。

### Phase 3: 重排序与优化 (Day 3)
1.  **Reranker 集成**: 引入 `sentence-transformers`，实例化 CrossEncoder。
2.  **Fallback 机制**: 如果 Reranker 超时，降级为 RRF 结果。
3.  **HyDE 优化**: 调整 HyDE 的 Prompt，使其生成更适合 BM25 匹配的关键词。

### Phase 4: 评估与测试 (Day 4)
1.  **构建测试集**: 50 个“刁钻”问题 (专有名词、模糊描述)。
2.  **指标计算**: 计算 Hit Rate@5 和 MRR。
3.  **压力测试**: 测试高并发下的 Redis 响应时间。

## 5. 依赖变更
*   New Python Deps: `redis-om` (可选), `sentence-transformers`, `langchain-text-splitters`.
*   Resources: Reranker 模型需要约 2-4GB 显存或内存。

---
**批准人**: 技术委员会
**执行人**: AI Agent
