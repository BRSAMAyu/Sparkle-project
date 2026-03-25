# API Keys 配置总结

## ✅ 配置状态

**配置时间**: 2026-01-29
**配置完整度**: 7/7 (100%)
**Demo Mode**: 已禁用

## 📋 已配置的服务

### 1. XiaoMi MIMO (小米米默) - 快速响应

```bash
XIAOMI_MIMO_API_KEY=sk-cmwqykkej4amo184uyqf700glf5xcqiuahremcrg2j2kb8o6o
XIAOMI_MIMO_BASE_URL=https://api.xiaomimimo.com/v1
XIAOMI_CHAT_MODEL=mimo-v2-flash
XIAOMI_TEMPERATURE=0.3
```

**用途**: FAST tier 快速响应模型
**特点**: 极速响应，适合闲聊和简单问答

---

### 2. Zhipu GLM (智谱AI) - 编程/工具

```bash
ZHIPU_API_KEY=e78e70c5f139453c9d0df15b848fa084.W31a9cNerGcSYDTt
ZHIPU_BASE_URL=https://open.bigmodel.cn/api/paas/v4
ZHIPU_CHAT_MODEL=glm-4.7
ZHIPU_TOOLS_MODEL=glm-4.7
ZHIPU_FLASH_MODEL=glm-4.7-flashx
GLM_4_7_FLASH_MODEL=glm-4.7-flash
ZHIPU_TEMPERATURE=0.3
```

**用途**: STANDARD/REASONING tier，支持思考模式
**特点**:
- `glm-4.7`: 标准响应（非思考模式）
- `glm-4.7-flash`: 30B级快速响应模型
- 支持工具调用和 Function Call

---

### 3. DashScope (阿里云百炼) - 通义千问

```bash
DASHSCOPE_API_KEY=sk-cd9af6e3b7da44c9b67de53c69f2fae8
DASHSCOPE_BASE_HTTP_API_URL=https://dashscope.aliyuncs.com/api/v1
DASHSCOPE_BASE_URL_COMPATIBLE=https://dashscope.aliyuncs.com/compatible-mode/v1
DASHSCOPE_CHAT_MODEL=qwen-plus
DASHSCOPE_REASON_MODEL=qwen-plus
DASHSCOPE_TEMPERATURE=0.7
DASHSCOPE_EMBEDDING_MODEL=text-embedding-v4
DASHSCOPE_RERANK_MODEL=qwen3-rerank
```

**用途**:
- **对话**: STANDARD tier 通用模型
- **Embedding**: 向量嵌入（默认）
- **Rerank**: 文档重排序（默认）

**API 方式**: 使用官方 SDK (`dashscope.TextEmbedding.call()`)

---

### 4. DeepSeek - 深度推理

```bash
DEEPSEEK_API_KEY=sk-29c29c1c5a9447949b09762140a210ef
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_CHAT_MODEL=deepseek-chat
DEEPSEEK_REASON_MODEL=deepseek-reasoner
```

**用途**:
- `deepseek-chat`: STANDARD tier 标准模型
- `deepseek-reasoner`: REASONING tier 深度推理模型

**特点**: 强大的推理能力，适合复杂任务

---

### 5. SiliconFlow (硅基流动) - 专家模型

```bash
SILICONFLOW_API_KEY=sk-wregwpyfxrafholmzwrrbucyyvtfgepffgqfysmljdutoqpx
SILICONFLOW_BASE_URL=https://api.siliconflow.cn/v1
SILICONFLOW_OCR_MODEL=deepseek-ai/DeepSeek-OCR
SILICONFLOW_EMBEDDING_MODEL=Qwen/Qwen3-Embedding-4B
SILICONFLOW_RERANK_MODEL=Qwen/Qwen3-Reranker-4B
```

**用途**:
- **OCR**: 文档识别与清洗（SPECIALIST tier）
- **翻译**: Hunyuan MT 机器翻译（SPECIALIST tier）
- **Embedding/Rerank**: 备用（通过 HTTP API）

**API 方式**: HTTP API (`httpx.AsyncClient`)

---

### 6. Hunyuan Translation (via SiliconFlow)

```bash
HUNYUAN_API_KEY=sk-wregwpyfxrafholmzwrrbucyyvtfgepffgqfysmljdutoqpx
HUNYUAN_BASE_URL=https://api.siliconflow.cn/v1
HUNYUAN_TRANSLATE_MODEL=tencent/Hunyuan-MT-7B
```

**用途**: 机器翻译专用模型
**API 方式**: OpenAI 兼容 API

---

### 7. XunFei STT (科大讯飞) - 语音转文字

```bash
XUNFEI_API_KEY=f53891ea367c5f58d38dcfc6e27a902c
XUNFEI_API_SECRET=MDZmNzlkZDk2NWRmYWM1M2M5OTExYjVi
XUNFEI_STT_DOMAIN=iat
XUNFEI_STT_LANGUAGE=zh-CN
XUNFEI_STT_SAMPLE_RATE=16000
XUNFEI_STT_MAX_AUDIO_DURATION=60
XUNFEI_STT_EOS_MS=6000
```

**用途**: 实时语音识别
**API 方式**: WebSocket API (HMAC-SHA256 签名)

---

### 8. Embedding & Rerank 配置

```bash
# 默认使用 DashScope
EMBEDDING_PROVIDER=dashscope
EMBEDDING_MODEL=text-embedding-v4
EMBEDDING_DIM=1024
RERANK_PROVIDER=dashscope
RERANK_MODEL=qwen3-rerank
```

---

## 🎯 模型层级映射

```
ModelTier 层级:
├── FREE_FAST        → (暂无)
├── FREE_REASONING   → (暂无)
├── FAST             → xiaomi_chat (mimo-v2-flash)
├── STANDARD         → zhipu_chat (glm-4.7), deepseek_chat, dashscope_chat (qwen-plus)
├── REASONING        → zhipu_reason (glm-4.7), deepseek_reasoner, dashscope_reason (qwen-plus)
└── SPECIALIST       → siliconflow_ocr, siliconflow_translate
```

---

## 📊 API 调用方式总结

| 服务 | Provider | API 方式 | 用途 |
|------|----------|---------|------|
| XiaoMi MIMO | HTTP API | - | 快速响应 |
| Zhipu GLM | OpenAI 兼容 API | `extra_body` 参数 | 对话/工具 |
| DashScope Embedding | **官方 SDK** | `dashscope.TextEmbedding.call()` | 向量嵌入 |
| DashScope Rerank | **官方 SDK** | `dashscope.TextReRank.call()` | 重排序 |
| SiliconFlow OCR | HTTP API | `httpx.AsyncClient` | 文档识别 |
| Hunyuan 翻译 | OpenAI 兼容 API | `AsyncOpenAI` | 机器翻译 |
| DeepSeek | OpenAI 兼容 API | - | 对话/推理 |
| XunFei STT | WebSocket API | HMAC-SHA256 签名 | 语音识别 |

---

## ✅ 配置文件

| 文件 | 状态 |
|------|------|
| `backend/.env` | ✅ 已更新真实 API keys |
| `backend/.env.example` | ✅ 已更新配置模板 |
| `backend/test_all_api_keys.py` | ✅ 测试脚本 |

---

## 🔐 安全提示

⚠️ **重要提醒**：
1. `.env` 文件包含真实的 API keys，**不要提交到 Git**
2. `.gitignore` 已配置忽略 `.env` 文件
3. 生产环境使用环境变量或密钥管理服务

---

## 🧪 测试

运行测试验证配置：

```bash
cd backend
python test_all_api_keys.py
```

预期输出：

```
🎉 所有 API Key 已正确配置，Demo Mode 已禁用
```

---

## 📝 相关文档

- [Embedding & Rerank 配置](./EMBEDDING_RERANK_CONFIG.md)
- [GLM-4.7-Flash 配置](./GLM_4_7_FLASH_SETUP.md)
- [SPECIALIST Tier 配置](./SPECIALIST_TIER_SETUP.md)
