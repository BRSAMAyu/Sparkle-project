# Embedding 和 Reranking 服务部署指南

## 🎯 概述

本项目已实现支持阿里云 DashScope 和硅基流动的 embedding 和 reranking 服务，采用双供应商架构确保高可用性。

## ✅ 验证结果

经过完整测试验证：

- ✅ **阿里云 DashScope API** - 正常工作
- ✅ **Embedding 服务** - 支持单文本和批量处理
- ✅ **Reranking 服务** - 支持基础 rerank 和带 instruct 的 rerank
- ✅ **错误处理** - 完善的重试机制和降级策略
- ✅ **维度配置** - 支持 1024 维向量

## 🚀 快速开始

### 1. 环境变量配置

#### 方案一：阿里云 DashScope（推荐）
```bash
export EMBEDDING_PROVIDER=dashscope
export RERANK_PROVIDER=dashscope
export DASHSCOPE_API_KEY=sk-your-dashscope-api-key

# 模型配置
export EMBEDDING_MODEL=text-embedding-v4
export RERANK_MODEL=qwen3-rerank
export EMBEDDING_DIM=1024
```

#### 方案二：硅基流动
```bash
export EMBEDDING_PROVIDER=siliconflow
export RERANK_PROVIDER=siliconflow
export SILICONFLOW_API_KEY=your-siliconflow-api-key
export SILICONFLOW_BASE_URL=https://api.siliconflow.cn

# 模型配置
export EMBEDDING_MODEL=Qwen/Qwen3-Embedding-4B
export RERANK_MODEL=Qwen/Qwen3-Reranker-4B
export EMBEDDING_DIM=1024
```

### 2. 使用示例

```python
from app.services.embedding_service import embedding_service
from app.services.rerank_service import rerank_service

# 获取文本向量
embedding = await embedding_service.get_embedding(
    "什么是人工智能？",
    text_type="query"
)

# 批量获取向量
embeddings = await embedding_service.batch_embeddings(
    ["文本1", "文本2", "文本3"],
    text_type="document"
)

# 文档 reranking
candidates = [
    {"id": 0, "content": "人工智能是计算机科学的一个分支"},
    {"id": 1, "content": "机器学习是实现人工智能的重要方法"}
]
reranked = await rerank_service.rerank(
    "什么是AI？",
    candidates,
    top_k=1,
    instruct="Given a web search query, retrieve relevant passages that answer the query."
)
```

## 📊 API 详细信息

### 🇨🇳 阿里云 DashScope API

#### Embedding API

**模型**: `text-embedding-v4`
- **输入**: 文本字符串列表
- **输出**: 1024 维浮点向量
- **支持特性**:
  - `text_type`: "query" 或 "document" 区分
  - `instruct`: 任务指令（通过 SDK）
  - `dimension`: 向量维度（1024）
- **Token 限制**: 8192
- **定价**: ¥0.0005/Token（Batch ¥0.00025/Token）

**示例**:
```python
import dashscope

resp = dashscope.TextEmbedding.call(
    model="text-embedding-v4",
    input=["什么是人工智能？"],
    dimension=1024,
    text_type="query"
)
```

#### Rerank API

**模型**: `qwen3-rerank`
- **输入**: 查询文本 + 候选文档列表
- **输出**: 按相关性排序的文档索引
- **支持特性**:
  - `top_n`: 返回前 N 个结果
  - `instruct`: 自定义排序指令
  - 最大 500 个文档，每个文档 4000 Token
- **定价**: ¥0.001/Token

**示例**:
```python
import dashscope

resp = dashscope.TextReRank.call(
    model="qwen3-rerank",
    query="什么是人工智能？",
    documents=[
        "人工智能是计算机科学的一个分支",
        "机器学习是实现人工智能的重要方法"
    ],
    top_n=2,
    instruct="Given a web search query, retrieve relevant passages that answer the query."
)
```

### 🌏 硅基流动 SiliconFlow API

#### Embedding API

**支持的模型**:
- **BGE 系列**: `BAAI/bge-large-zh-v1.5`, `BAAI/bge-large-en-v1.5`, `BAAI/bge-m3`
- **Qwen 系列**: `Qwen/Qwen3-Embedding-8B`, `Qwen/Qwen3-Embedding-4B`, `Qwen/Qwen3-Embedding-0.6B`

**特性**:
- **输入**: 文本字符串或字符串数组
- **输出**: 浮点向量数组
- **支持特性**:
  - `encoding_format`: "float" 或 "base64"
  - `dimensions`: Qwen 系列支持（64-4096）
  - **Token 限制**: BGE系列 512/8192，Qwen系列 32768

**示例**:
```python
import httpx

async def get_embedding(text):
    payload = {
        "model": "Qwen/Qwen3-Embedding-4B",
        "input": text,
        "encoding_format": "float",
        "dimensions": 1024
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.siliconflow.cn/v1/embeddings",
            headers={
                "Authorization": "Bearer your-api-key",
                "Content-Type": "application/json"
            },
            json=payload
        )
        return response.json()
```

#### Rerank API

**支持的模型**:
- **BGE 系列**: `BAAI/bge-reranker-v2-m3`, `Pro/BAAI/bge-reranker-v2-m3`
- **Qwen 系列**: `Qwen/Qwen3-Reranker-8B`, `Qwen/Qwen3-Reranker-4B`, `Qwen/Qwen3-Reranker-0.6B`

**特性**:
- **输入**: 查询文本 + 文档字符串数组
- **输出**: 按相关性排序的文档列表
- **支持特性**:
  - `top_n`: 返回前 N 个结果
  - `instruct`: 自定义排序指令（仅 Qwen 系列）
  - `return_documents`: 是否返回文档内容
  - `max_chunks_per_doc`: 文档分块数（BGE系列支持）
  - `overlap_tokens`: 分块重叠 Token 数（BGE系列支持）
- **文档限制**: 最少 1 个，无明确上限

**示例**:
```python
import httpx

async def rerank(query, documents):
    payload = {
        "model": "Qwen/Qwen3-Reranker-4B",
        "query": query,
        "documents": documents,
        "top_n": 5,
        "instruct": "Please rerank the documents based on the query."
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.siliconflow.cn/rerank",
            headers={
                "Authorization": "Bearer your-api-key",
                "Content-Type": "application/json"
            },
            json=payload
        )
        return response.json()
```

## 🔧 配置选项

### Provider 优先级

```python
# 嵌入服务优先级
if self.provider == "dashscope":
    return await self._dashscope_embeddings(texts)
elif self.provider == "siliconflow":
    return await self._siliconflow_embeddings(texts)

# Rerank 服务优先级
if self.provider == "dashscope":
    return await self._dashscope_rerank(query, documents)
elif self.provider == "siliconflow":
    return await self._siliconflow_rerank(query, documents)
```

### 错误处理机制

```python
# 自动重试机制
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def get_embedding(self, text: str) -> List[float]:
    # 自动降级到备用 provider
    # 自动重试失败的请求
```

## 📈 性能优化建议

### 1. 批量处理
- 使用 `batch_embeddings` 而不是多次调用 `get_embedding`
- 批量处理可以显著降低 API 调用成本

### 2. 缓存策略
- 在 Redis 中缓存常用文本的向量
- 避免重复计算相同内容的向量

### 3. 异步处理
- 所有 API 调用都使用异步方式
- 支持并发处理多个请求

### 4. 降级策略
- 当首选 provider 失败时自动切换到备用
- 保证服务的可用性

## 🔍 监控和日志

### API 调用监控

```python
# 记录 API 调用信息
logger.info(f"Embedding API - Model: {model}, Tokens: {tokens}, Cost: ${cost}")
logger.info(f"Rerank API - Model: {model}, Documents: {len(documents)}, TopN: {top_n}")
```

### 错误监控

```python
# 自动重试失败的请求
# 记录详细的错误信息
# 监控 provider 切换情况
```

## 🧪 测试验证

运行测试脚本验证配置：

```bash
# 直接测试 API
python test_embedding_rerank_direct.py

# 测试服务层
python test_services.py

# 验证配置
python validate_embedding_config.py
```

## 🎯 模型选择建议

### 1. 嵌入模型选择

| 使用场景 | 推荐模型 | 理由 |
|---------|---------|------|
| 中文语义搜索 | `text-embedding-v4` (阿里云) / `Qwen/Qwen3-Embedding-4B` (硅基流动) | 中文理解优秀，1024维 |
| 英文语义搜索 | `BAAI/bge-large-en-v1.5` (硅基流动) | 英文表现更好 |
| 成本敏感 | `Qwen/Qwen3-Embedding-0.6B` (硅基流动) | 更小的模型，更低成本 |
| 高精度需求 | `text-embedding-v4` (阿里云) | 最新模型，质量最好 |

### 2. 重排序模型选择

| 使用场景 | 推荐模型 | 理由 |
|---------|---------|------|
| 通用场景 | `qwen3-rerank` (阿里云) / `Qwen/Qwen3-Reranker-4B` (硅基流动) | 性能均衡 |
| 长文档处理 | `BAAI/bge-reranker-v2-m3` (硅基流动) | 支持文档分块 |
| 成本敏感 | `Qwen/Qwen3-Reranker-0.6B` (硅基流动) | 成本更低 |
| 中文优化 | `qwen3-rerank` (阿里云) | 中文理解更好 |

## 💰 成本优化

### 阿里云 DashScope 定价

- **text-embedding-v4**: ¥0.0005/Token
- **Batch 调用**: ¥0.00025/Token（优惠 50%）
- **qwen3-rerank**: ¥0.001/Token

### 硅基流动定价（参考）

- **Qwen系列**: 类似阿里云定价
- **BGE系列**: 通常更经济

### 优化建议

1. **批量处理**：
   - 使用 `batch_embeddings` 而不是多次调用
   - 阿里云使用 Batch 接口节省 50% 成本

2. **合理设置参数**：
   - 避免设置过大的 `top_n`
   - 对于长文档，考虑分块处理

3. **缓存策略**：
   - 缓存常用文本的向量
   - 使用 Redis 缓存热门查询的结果

4. **供应商轮换**：
   - 根据成本和使用量自动切换供应商
   - 设置预算告警

5. **监控告警**：
   - 监控 API 调用量和成本
   - 设置使用量上限

## 🚨 故障排除

### 常见问题

#### 通用问题

1. **API Key 无效**
   - 阿里云：检查 `DASHSCOPE_API_KEY` 是否正确
   - 硅基流动：检查 `SILICONFLOW_API_KEY` 是否正确
   - 确认 API Key 有足够配额

2. **网络连接问题**
   - 检查网络连接
   - 确认防火墙设置
   - 测试 API 端点连通性

3. **维度不匹配**
   - 确保 EMBEDDING_DIM 为 1024
   - 检查模型是否支持指定维度
   - 硅基流动 BGE 系列不支持 dimensions 参数

4. **服务降级**
   - 当首选 provider 不可用时自动切换到备用
   - 检查备用配置是否正确

#### 硅基流动特有问题

1. **URL 构建错误**
   - 硅基流动使用 `/rerank` 而不是 `/v1/rerank`
   - 硅基流动使用 `/v1/embeddings` 而不是 `/embeddings`

2. **参数名称错误**
   - 硅基流动使用 `instruct` 而不是 `instruction`
   - 某些参数只支持特定模型（如 Qwen 系列）

3. **模型不支持**
   - BGE 系列不支持 `dimensions` 参数
   - BGE 系列支持分块参数 `max_chunks_per_doc` 和 `overlap_tokens`

### 调试命令

#### 阿里云 DashScope

```bash
# 检查 embedding API
curl -X POST "https://dashscope.aliyuncs.com/compatible-mode/v1/embeddings" \
  -H "Authorization: Bearer $DASHSCOPE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "text-embedding-v4", "input": "test", "dimension": 1024}'

# 检查 rerank API
curl -X POST "https://dashscope.aliyuncs.com/compatible-mode/v1/rerank" \
  -H "Authorization: Bearer $DASHSCOPE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3-rerank",
    "query": "test",
    "documents": ["test document"],
    "top_n": 1
  }'
```

#### 硅基流动 SiliconFlow

```bash
# 检查 embedding API
curl -X POST "https://api.siliconflow.cn/v1/embeddings" \
  -H "Authorization: Bearer $SILICONFLOW_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen3-Embedding-4B",
    "input": "test",
    "encoding_format": "float",
    "dimensions": 1024
  }'

# 检查 rerank API
curl -X POST "https://api.siliconflow.cn/rerank" \
  -H "Authorization: Bearer $SILICONFLOW_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen3-Reranker-4B",
    "query": "test",
    "documents": ["test document"],
    "top_n": 1,
    "instruct": "Please rerank based on the query."
  }'
```

## 🔄 迁移指南

### 从 OpenAI 迁移

如果之前使用 OpenAI embeddings：

```python
# OpenAI
response = openai.embeddings.create(
    model="text-embedding-3-large",
    input=text
)

# DashScope (兼容接口)
response = dashscope.TextEmbedding.call(
    model="text-embedding-v4",
    input=text,
    dimension=1024
)
```

### 从其他服务商迁移

1. 更新环境变量配置
2. 调整模型名称
3. 更新 API 调用参数
4. 测试验证功能

---

**文档版本**: 1.0.0
**最后更新**: 2026-01-21
**适用版本**: Sparkle v0.3.0+