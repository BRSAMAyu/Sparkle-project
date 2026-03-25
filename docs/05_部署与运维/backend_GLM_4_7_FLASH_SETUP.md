# GLM-4.7-Flash 模型配置说明

## 概述

GLM-4.7-Flash 是 30B 级 SOTA 模型，提供了兼顾性能与效率的新选择。面向 Agentic Coding 场景强化了编码能力、长程任务规划与工具协同。

## 模型配置

### 1. 非思考模式 (`glm_4_7_flash_no_thinking`)

- **用途**: 快速响应场景
- **Tier**: FREE_FAST (免费快速)
- **配置**: `clear_thinking=True`
- **特点**:
  - 极速响应，适合需要快速回复的任务
  - 关闭思考模式，直接生成结果
  - 免费使用，成本最低

### 2. 思考模式 (`glm_4_7_flash_thinking`)

- **用途**: 深度推理场景
- **Tier**: FREE_REASONING (免费推理)
- **配置**: `clear_thinking=False`
- **特点**:
  - 启用保留式思考，保持推理连续性
  - 适合复杂任务、编程、问题分析等
  - 免费使用，兼顾成本和能力

## 环境变量配置

在 `.env` 文件中添加：

```bash
# Zhipu GLM Configuration
ZHIPU_API_KEY=your_zhipu_api_key
ZHIPU_BASE_URL=https://open.bigmodel.cn/api/paas/v4
ZHIPU_CHAT_MODEL=glm-4.7
ZHIPU_TOOLS_MODEL=glm-4.7
ZHIPU_FLASH_MODEL=glm-4.7-flashx
GLM_4_7_FLASH_MODEL=glm-4.7-flash
ZHIPU_TEMPERATURE=0.3
```

## 使用方法

### 方法 1: 通过 LLMRouter 直接选择

```python
from app.core.llm_router import llm_router

# 选择非思考模式
selection = llm_router.select_specific_model(
    "glm_4_7_flash_no_thinking",
    agent_role=AgentRole.GENERATION
)

# 选择思考模式
selection = llm_router.select_specific_model(
    "glm_4_7_flash_thinking",
    agent_role=AgentRole.GENERATION
)
```

### 方法 2: 通过 AgentRole 和 TaskType 自动选择

```python
from app.services.llm_service import LLMService
from app.core.agent_profiles import AgentRole, TaskType

# Code Agent 会自动使用合适的模型
llm_service = LLMService(agent_role=AgentRole.CODE_AGENT)

# 深度推理任务会自动使用思考模式
llm_service.switch_model_for_task(TaskType.DEEP_REASONING)
```

### 方法 3: 在现有代码中使用

```python
# 在 orchestrator.py 或其他服务中
from app.services.llm_service import get_llm_service_for_task

# 获取适合深度推理的 LLM 服务（会自动选择 glm_4_7_flash_thinking）
reasoning_llm = get_llm_service_for_task(TaskType.DEEP_REASONING)

response = await reasoning_llm.chat(messages)
```

## 模型层级映射

### FREE_FAST Tier（免费快速）
1. **glm_4_7_flash_no_thinking**: glm-4.7-flash ⭐ 新增

### FREE_REASONING Tier（免费推理）
1. **glm_4_7_flash_thinking**: glm-4.7-flash ⭐ 新增

### FAST Tier（付费极速响应）
1. xiaomi_chat: mimo-v2-flash
2. zhipu_flash: glm-4.7-flashx

### STANDARD Tier（付费标准响应）
1. zhipu_chat: glm-4.7
2. deepseek_chat: deepseek-chat
3. dashscope_chat: qwen-plus

### REASONING Tier（付费深度推理）
1. zhipu_reason: glm-4.7
2. deepseek_reason: deepseek-reasoner
3. dashscope_reason: qwen-plus

### SPECIALIST Tier（专家模型）
1. **siliconflow_ocr**: deepseek-ai/DeepSeek-OCR (文档识别)
2. **siliconflow_translate**: tencent/Hunyuan-MT-7B (机器翻译)

## API 特性

GLM-4.7-Flash 支持以下特性：

- ✅ 思考模式 (Thinking Mode)
- ✅ 流式输出 (Streaming)
- ✅ Function Call (工具调用)
- ✅ 上下文缓存 (Context Caching)
- ✅ 结构化输出 (JSON Mode)
- ✅ 200K 上下文窗口
- ✅ 128K 最大输出 Tokens

## 推荐使用场景

### 非思考模式适用场景
- 简单问答
- 快速信息查询
- 实时对话
- 简单文本生成

### 思考模式适用场景
- 复杂问题分析
- 编程任务
- 数学和逻辑推理
- 长文本生成
- 知识星图构建
- 错题诊断

## 测试

运行配置测试：

```bash
cd backend
python test_glm_4_7_flash.py
```

运行 API 调用测试（需要设置 API Key）：

```bash
cd backend
python test_glm_api_call.py
```

## 技术细节

### clear_thinking 参数

- `clear_thinking=True`: 关闭思考模式，相当于 `thinking={"type": "disabled"}`
- `clear_thinking=False`: 开启保留式思考，相当于 `thinking={"type": "enabled"}`

### Extra Body 传递

思考模式参数通过 `extra_body` 传递给 OpenAI 兼容客户端：

```python
{
    "model": "glm-4.7-flash",
    "messages": [...],
    "extra_body": {
        "clear_thinking": False  # 思考模式
    }
}
```

## 相关文件

- `backend/app/core/llm_router.py` - 模型路由配置
- `backend/app/config/settings.py` - 环境变量定义
- `backend/.env.example` - 配置示例
- `backend/test_glm_4_7_flash.py` - 配置测试
- `backend/test_glm_api_call.py` - API 调用测试

## 更新日志

- 2026-01-29: 新增 GLM-4.7-Flash 模型支持
  - 添加非思考模式配置 `glm_4_7_flash_no_thinking` (FREE_FAST tier)
  - 添加思考模式配置 `glm_4_7_flash_thinking` (FREE_REASONING tier)
  - 新增 `FREE_FAST` 和 `FREE_REASONING` 两个免费模型层级
  - 更新 tier 映射，将免费模型独立管理
