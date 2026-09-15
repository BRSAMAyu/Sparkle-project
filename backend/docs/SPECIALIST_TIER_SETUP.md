# SPECIALIST Tier 配置说明

## 概述

SPECIALIST Tier 专门用于配置专家模型，这些模型针对特定任务进行了优化，如 OCR（光学字符识别）、翻译等。

## 配置的专家模型

### 1. siliconflow_ocr - DeepSeek OCR

**用途**: 文档识别与清洗
- **模型**: `deepseek-ai/DeepSeek-OCR`
- **Provider**: SiliconFlow
- **Base URL**: `https://api.siliconflow.cn/v1`
- **Tier**: SPECIALIST
- **温度**: 0.3
- **特点**:
  - 专注于文档图像的文字识别
  - 支持复杂排版和多语言识别
  - 输出结构化文本

**业务集成**:
- 接入文档清洗链路 (`ingestion_service.py`)
- 通过 HTTP API 直接调用硅基流动

**使用场景**:
- 上传文档的文本提取
- 图片中的文字识别
- 扫描件数字化

### 2. siliconflow_translate - Hunyuan MT

**用途**: 机器翻译
- **模型**: `tencent/Hunyuan-MT-7B`
- **Provider**: SiliconFlow
- **Base URL**: `https://api.siliconflow.cn/v1`
- **Tier**: SPECIALIST
- **温度**: 0.2
- **特点**:
  - 专为机器翻译优化的模型
  - 支持多语言互译
  - 低温度设置确保翻译准确性

**业务集成**:
- 接入翻译链路 (`translation_service.py`)
- 通过 OpenAI 兼容 API 调用

**使用场景**:
- 多语言内容翻译
- 学习资料翻译
- 跨语言学习支持

## 环境变量配置

在 `.env` 文件中添加：

```bash
# SiliconFlow Configuration (专家模型：OCR、翻译等)
SILICONFLOW_API_KEY=your_siliconflow_api_key
SILICONFLOW_BASE_URL=https://api.siliconflow.cn/v1
SILICONFLOW_OCR_MODEL=deepseek-ai/DeepSeek-OCR

# Hunyuan Translation (via SiliconFlow)
HUNYUAN_API_KEY=your_siliconflow_api_key
HUNYUAN_BASE_URL=https://api.siliconflow.cn/v1
HUNYUAN_TRANSLATE_MODEL=tencent/Hunyuan-MT-7B
```

## 使用方法

### 方法 1: 直接选择专家模型

```python
from app.core.llm_router import llm_router

# 选择 OCR 模型
ocr_selection = llm_router.select_specific_model("siliconflow_ocr")

# 选择翻译模型
translate_selection = llm_router.select_specific_model("siliconflow_translate")

# 获取 API 参数
kwargs = llm_router.get_openai_client_kwargs(ocr_selection)
```

### 方法 2: 通过 Tier 选择

```python
from app.core.llm_router import llm_router
from app.core.agent_profiles import ModelTier, AgentRole

# 选择 SPECIALIST tier 中的模型
selection = llm_router.select_model(
    agent_role=AgentRole.GENERATION,
    force_tier=ModelTier.SPECIALIST
)
```

### 方法 3: 在服务中使用

```python
from app.services.llm_service import LLMService
from app.core.llm_router import llm_router

# 获取 OCR 模型配置
ocr_selection = llm_router.select_specific_model("siliconflow_ocr")
kwargs = llm_router.get_openai_client_kwargs(ocr_selection)

# 使用 OCR 模型
from app.services.llm.providers import OpenAICompatibleProvider
provider = OpenAICompatibleProvider(
    api_key=kwargs["api_key"],
    base_url=kwargs["base_url"]
)

response = await provider.chat(
    messages=[{"role": "user", "content": "识别这张图片中的文字"}],
    model=kwargs["model"]
)
```

## 模型层级总览

```
ModelTier 层级:
├── FREE_FAST        → glm_4_7_flash_no_thinking (免费快速)
├── FREE_REASONING   → glm_4_7_flash_thinking  (免费推理)
├── FAST             → xiaomi_chat, zhipu_flash (付费快速)
├── STANDARD         → zhipu_chat, deepseek_chat, dashscope_chat (付费标准)
├── REASONING        → zhipu_reason, deepseek_reason, dashscope_reason (付费推理)
└── SPECIALIST       → siliconflow_ocr, siliconflow_translate (专家模型)
```

## 配置文件

- `backend/app/core/agent_profiles.py` - ModelTier 枚举定义
- `backend/app/core/llm_router.py` - 模型配置和路由
- `backend/app/config/settings.py` - 环境变量定义
- `backend/.env.example` - 配置示例

## 测试

运行 SPECIALIST tier 配置测试：

```bash
cd backend
python test_specialist_tier.py
```

## 技术细节

### API Key 优先级

对于翻译模型，API Key 优先级：
1. `HUNYUAN_API_KEY` (如果设置)
2. `SILICONFLOW_API_KEY` (回退)

### 成本与性能

| 模型 | 成本 (per 1K tokens) | 平均延迟 | 用途 |
|------|---------------------|----------|------|
| siliconflow_ocr | 0.001 | 2000ms | 文档识别 |
| siliconflow_translate | 0.0005 | 1000ms | 机器翻译 |

## 相关文档

- [GLM-4.7-Flash 配置说明](./GLM_4_7_FLASH_SETUP.md)
- [LLM Router 源码](../../app/core/llm_router.py)
- [Agent Profiles 配置](../../app/core/agent_profiles.py)

## 更新日志

- 2026-01-29: 新增 SPECIALIST Tier
  - 添加 `ModelTier.SPECIALIST` 枚举
  - 添加 `ModelProvider.SILICONFLOW` 提供商
  - 配置 siliconflow_ocr (DeepSeek OCR) - 接入文档清洗链路
  - 配置 siliconflow_translate (Hunyuan MT) - 接入翻译链路
  - **注意**: 这两个模型在 LLMRouter 中仅作配置管理，不参与实际业务路由
  - **实际业务**: 翻译和 OCR 服务直接使用 settings 中的配置，通过各自服务独立调用
