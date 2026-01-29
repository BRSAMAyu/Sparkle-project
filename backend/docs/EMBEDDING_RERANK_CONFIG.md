# Embedding 和 Rerank 配置说明

## 概述

系统支持双提供商配置 Embedding 和 Rerank 服务：
- **DashScope (阿里云百炼)**：默认提供商
- **SiliconFlow (硅基流动)**：备用提供商

## 当前默认配置

```python
# Embedding Service
EMBEDDING_PROVIDER = "dashscope"
EMBEDDING_MODEL = "text-embedding-v4"
EMBEDDING_DIM = 1024

# Rerank Service
RERANK_PROVIDER = "dashscope"
RERANK_MODEL = "qwen3-rerank"
```

## 模型对比

### Embedding 模型

| 提供商 | 模型名称 | 向量维度 | API 方式 |
|--------|---------|---------|---------|
| **DashScope** | `text-embedding-v4` | 1024 | SDK |
| SiliconFlow | `Qwen/Qwen3-Embedding-4B` | 1024 | HTTP API |

### Rerank 模型

| 提供商 | 模型名称 | API 方式 |
|--------|---------|---------|
| **DashScope** | `qwen3-rerank` | SDK |
| SiliconFlow | `Qwen/Qwen3-Reranker-4B` | HTTP API |

## 配置方法

### 方式 1: 修改 `.env` 文件

```bash
# 使用 DashScope (默认)
EMBEDDING_PROVIDER=dashscope
EMBEDDING_MODEL=text-embedding-v4
RERANK_PROVIDER=dashscope
RERANK_MODEL=qwen3-rerank

# 或使用 SiliconFlow
EMBEDDING_PROVIDER=siliconflow
EMBEDDING_MODEL=Qwen/Qwen3-Embedding-4B
RERANK_PROVIDER=siliconflow
RERANK_MODEL=Qwen/Qwen3-Reranker-4B
```

### 方式 2: 环境变量

```bash
export EMBEDDING_PROVIDER=dashscope
export RERANK_PROVIDER=dashscope
```

## API 调用方式

### DashScope (阿里云)

**Embedding**:
```python
# 使用官方 SDK
import dashscope

dashscope.api_key = settings.DASHSCOPE_API_KEY
response = dashscope.TextEmbedding.call(
    model="text-embedding-v4",
    input=texts,
    dimension=1024,
    text_type="document"
)
```

**Rerank**:
```python
# 使用官方 SDK
import dashscope

dashscope.api_key = settings.DASHSCOPE_API_KEY
response = dashscope.TextReRank.call(
    model="qwen3-rerank",
    query=query,
    documents=documents,
    top_n=top_k
)
```

### SiliconFlow (硅基流动)

**Embedding**:
```python
# 使用 HTTP API
import httpx

async with httpx.AsyncClient() as client:
    response = await client.post(
        "https://api.siliconflow.cn/v1/embeddings",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        json={
            "model": "Qwen/Qwen3-Embedding-4B",
            "input": texts,
            "encoding_format": "float",
            "dimensions": 1024
        }
    )
```

**Rerank**:
```python
# 使用 HTTP API
import httpx

async with httpx.AsyncClient() as client:
    response = await client.post(
        "https://api.siliconflow.cn/v1/rerank",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        json={
            "model": "Qwen/Qwen3-Reranker-4B",
            "query": query,
            "documents": documents,
            "top_n": top_k
        }
    )
```

## 服务实现

### Embedding Service

文件：`backend/app/services/embedding_service.py`

```python
class EmbeddingService:
    def __init__(self):
        self.provider = settings.EMBEDDING_PROVIDER

        # 根据 provider 选择调用方式
        if self.provider == "dashscope":
            return await self._dashscope_embeddings(texts)
        elif self.provider == "siliconflow":
            return await self._siliconflow_embeddings(texts)
```

### Rerank Service

文件：`backend/app/services/rerank_service.py`

```python
class RerankService:
    def __init__(self):
        self.provider = settings.RERANK_PROVIDER

        # 根据 provider 选择调用方式
        if self.provider == "dashscope":
            indices = await self._dashscope_rerank(query, documents, top_k)
        elif self.provider == "siliconflow":
            indices = await self._siliconflow_rerank(query, documents, top_k)
```

## 切换提供商的影响

### 切换到 DashScope
- ✅ 使用官方 SDK，调用更稳定
- ✅ 阿里云生态集成
- ✅ 支持 `text_type` 参数（query/document）
- ❌ 需要配置 `DASHSCOPE_API_KEY`

### 切换到 SiliconFlow
- ✅ HTTP API，更灵活
- ✅ 统一 API 端点
- ✅ 与其他 SiliconFlow 服务共享 API Key
- ❌ 需要自己处理 HTTP 请求
- ❌ 不支持 `text_type` 参数

## 测试

运行配置测试：

```bash
cd backend
python test_embedding_rerank_config.py
```

预期输出：

```
✅ Embedding Provider 正确设置为 dashscope
✅ Rerank Provider 正确设置为 dashscope
✅ Embedding Model 正确设置为 text-embedding-v4
✅ Rerank Model 正确设置为 qwen3-rerank
```

## 相关文件

- `backend/app/config/settings.py` - 配置定义
- `backend/app/services/embedding_service.py` - Embedding 服务实现
- `backend/app/services/rerank_service.py` - Rerank 服务实现
- `backend/.env.example` - 配置示例

## 更新日志

- 2026-01-29: 切换默认提供商到 DashScope
  - EMBEDDING_PROVIDER: siliconflow → dashscope
  - RERANK_PROVIDER: siliconflow → dashscope
  - EMBEDDING_MODEL: Qwen/Qwen3-Embedding-4B → text-embedding-v4
  - RERANK_MODEL: Qwen/Qwen3-Reranker-4B → qwen3-rerank
