# API 配置管理文档

> 本项目所有外部 API 统一通过环境变量配置，无硬编码

## 📋 配置概览

| 服务 | 提供商 | 用途 | 环境变量前缀 |
|------|--------|------|--------------|
| LLM 聊天 | 阿里云 DashScope | AI 对话 | `DASHSCOPE_*` |
| 文档清洗 | 硅基流动 SiliconFlow | OCR 文档处理 | `SILICONFLOW_*` |
| 翻译 | 硅基流动 SiliconFlow | Hunyuan 翻译 | `HUNYUAN_*` |
| Embedding | 阿里云 DashScope | 文本向量化 | `DASHSCOPE_*` |
| Rerank | 阿里云 DashScope | 重排序 | `DASHSCOPE_*` |
| 语音转文字 | 科大讯飞 XunFei | STT | `XUNFEI_*` |

---

## 🔧 环境变量配置

### 阿里云 DashScope (通义千问)

```bash
# API 密钥
DASHSCOPE_API_KEY=sk-your-api-key-here

# 端点配置
DASHSCOPE_BASE_HTTP_API_URL=https://dashscope.aliyuncs.com/api/v1
DASHSCOPE_BASE_URL_COMPATIBLE=https://dashscope.aliyuncs.com/compatible-mode/v1

# 模型配置
DASHSCOPE_CHAT_MODEL=qwen-plus          # 聊天模型
DASHSCOPE_REASON_MODEL=qwen-plus        # 推理模型
DASHSCOPE_TEMPERATURE=0.7               # 温度参数

# Embedding / Rerank
DASHSCOPE_EMBEDDING_MODEL=text-embedding-v4
DASHSCOPE_RERANK_MODEL=qwen3-rerank
```

**用途**：
- LLM 对话 (`llm_router.py` → `dashscope_chat`)
- Embedding 向量化 (`embedding_service.py` → `EMBEDDING_PROVIDER=dashscope`)
- Rerank 重排序 (`rerank_service.py` → `RERANK_PROVIDER=dashscope`)

---

### 硅基流动 SiliconFlow

```bash
# API 密钥
SILICONFLOW_API_KEY=sk-your-api-key-here

# 端点配置
SILICONFLOW_BASE_URL=https://api.siliconflow.cn/v1

# 模型配置
SILICONFLOW_OCR_MODEL=deepseek-ai/DeepSeek-OCR          # 文档清洗
SILICONFLOW_EMBEDDING_MODEL=Qwen/Qwen3-Embedding-4B     # 备用 Embedding
SILICONFLOW_RERANK_MODEL=Qwen/Qwen3-Reranker-4B         # 备用 Rerank
```

**用途**：
- 文档清洗 OCR (`ingestion_service.py`)
- Hunyuan 翻译模型 (`HUNYUAN_*` 配置，复用此 API Key)

---

### 混元 Hunyuan Translation (通过 SiliconFlow)

```bash
# API 密钥（复用 SILICONFLOW_API_KEY）
HUNYUAN_API_KEY=sk-your-api-key-here

# 端点配置
HUNYUAN_BASE_URL=https://api.siliconflow.cn/v1

# 模型配置
HUNYUAN_CHAT_MODEL=tencent/Hunyuan-A13B-Instruct
HUNYUAN_REASON_MODEL=tencent/Hunyuan-A13B-Instruct
```

**用途**：
- 文本翻译 (`focus_tools.py`)

---

### 科大讯飞 XunFei (语音转文字)

```bash
# API 密钥
XUNFEI_API_KEY=your-xunfei-api-key-here
XUNFEI_API_SECRET=your-xunfei-api-secret-here

# STT 配置
XUNFEI_STT_DOMAIN=iat                           # 听写/实时转写
XUNFEI_STT_LANGUAGE=zh-CN                       # 中文
XUNFEI_STT_SAMPLE_RATE=16000                    # 采样率
XUNFEI_STT_MAX_AUDIO_DURATION=60                # 最大音频时长(秒)
XUNFEI_STT_EOS_MS=6000                          # 静音检测阈值(毫秒)
```

**用途**：
- 语音转文字 STT (`stt_service.py` → `xunfei_provider.py`)

**获取方式**：[科大讯飞控制台](https://console.xfyun.cn/)

---

## 🔒 安全最佳实践

### 1. 本地开发
```bash
# 复制示例配置
cp backend/.env.example backend/.env

# 填入真实 API 密钥
# 编辑 backend/.env
```

### 2. 生产环境
```bash
# 使用环境变量或密钥管理服务
export DASHSCOPE_API_KEY="sk-production-key"
export SILICONFLOW_API_KEY="sk-production-key"
# ...
```

### 3. Docker 部署
```yaml
# docker-compose.yml
services:
  grpc-server:
    environment:
      - DASHSCOPE_API_KEY=${DASHSCOPE_API_KEY}
      - SILICONFLOW_API_KEY=${SILICONFLOW_API_KEY}
```

### 4. Git 提交
✅ `.env` 已在 `.gitignore` 中
❌ 永远不要提交真实 API 密钥到代码仓库

---

## 📝 配置验证

检查配置是否正确加载：

```python
from app.config import settings

# 验证 API 密钥
print(f"DashScope: {'✓' if settings.DASHSCOPE_API_KEY else '✗'}")
print(f"SiliconFlow: {'✓' if settings.SILICONFLOW_API_KEY else '✗'}")
print(f"XunFei: {'✓' if settings.XUNFEI_API_KEY else '✗'}")
```

---

## 🔄 切换提供商

### 切换 Embedding 提供商

```bash
# 使用阿里云
EMBEDDING_PROVIDER=dashscope
EMBEDDING_MODEL=text-embedding-v4

# 使用硅基流动
EMBEDDING_PROVIDER=siliconflow
EMBEDDING_MODEL=Qwen/Qwen3-Embedding-4B
```

### 切换 Rerank 提供商

```bash
# 使用阿里云
RERANK_PROVIDER=dashscope
RERANK_MODEL=qwen3-rerank

# 使用硅基流动
RERANK_PROVIDER=siliconflow
RERANK_MODEL=Qwen/Qwen3-Reranker-4B
```

### 切换 LLM 提供商

```python
from app.core.llm_router import llm_router, ModelProvider

# 方式1: 通过 LLM_PROVIDER 环境变量
# LLM_PROVIDER=dashscope

# 方式2: 代码中指定
selection = llm_router.select_specific_model("dashscope_chat")
```

---

## 📚 相关文档

- [阿里云 DashScope 文档](https://help.aliyun.com/zh/model-studio/)
- [硅基流动 SiliconFlow 文档](https://docs.siliconflow.cn/)
- [科大讯飞 XunFei 文档](https://www.xfyun.cn/doc/)
