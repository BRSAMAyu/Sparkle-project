import json
from typing import List, Dict, AsyncGenerator, Optional, Any, AsyncIterator
import asyncio
from loguru import logger
from dataclasses import dataclass
from opentelemetry import trace
from fastapi import HTTPException

from app.config import settings
from app.services.llm.base import LLMProvider
from app.services.llm.providers import OpenAICompatibleProvider

# ==========================================
# 🎭 演示模式预设响应 (Demo Mock Responses)
# ==========================================
# 用于竞赛演示，确保关键流程 100% 成功且秒回
# 要启用: 在 .env 中设置 DEMO_MODE=true
#
# 💡 使用说明:
# 1. 在演示脚本中输入的文字必须与下面的 key 完全一致
# 2. 可以按需添加更多关键词和响应
# ==========================================

DEMO_MOCK_RESPONSES: Dict[str, str] = {
    "帮我制定高数复习计划": """好的！基于你的学习情况，我为你制定了一个高效的高数复习计划。

📚 **高数冲刺复习计划**

根据艾宾浩斯遗忘曲线和你的知识星图分析，我发现你在以下几个知识点需要重点复习：

1. **极限与连续** - 掌握度较低，建议优先复习
2. **导数的应用** - 需要强化，特别是最值问题
3. **积分计算** - 基础还不错，做题巩固即可

我已为你生成以下任务卡片：

```json
{
  "actions": [
    {
      "type": "create_task",
      "data": {
        "title": "极限与连续重难点复习",
        "type": "learning",
        "estimated_minutes": 45,
        "priority": "high"
      }
    },
    {
      "type": "create_task",
      "data": {
        "title": "导数应用专题练习",
        "type": "training",
        "estimated_minutes": 30,
        "priority": "medium"
      }
    },
    {
      "type": "create_task",
      "data": {
        "title": "积分计算刷题",
        "type": "training",
        "estimated_minutes": 25,
        "priority": "normal"
      }
    }
  ]
}
```

建议按照上述顺序学习，先攻克弱项，再巩固强项。加油！🔥""",

    "我今天要学什么": """早上好！让我看看你的学习状态...

📊 **今日学习建议**

根据你的知识星图和遗忘曲线分析：

🔴 **需要复习** (掌握度下降):
- 线性代数：矩阵运算 (距上次学习已过 5 天)
- 高数：积分技巧 (掌握度降至 65%)

🟡 **今日推荐学习**:
- 概率论：条件概率 (按计划应今日学习)

💡 我建议你今天先花 20 分钟复习线代矩阵运算，然后再学习新内容。

需要我帮你创建今日学习任务吗？""",

    "这道题怎么做": """好的，让我来帮你分析这道题！

📝 **解题思路**

首先，我们需要识别题目的关键信息和考查的知识点。

一般来说，解题可以分为以下步骤：
1. **审题** - 明确已知条件和所求
2. **建模** - 建立数学模型或找到适用的公式
3. **计算** - 按步骤规范计算
4. **验证** - 检查结果是否合理

如果你能把具体的题目发给我，我可以给你更详细的解答和分析哦！

💡 小提示：遇到不会的题目，先尝试自己思考 5 分钟，这样学习效果更好！""",
}

@dataclass
class LLMResponse:
    content: str
    tool_calls: Optional[List[Dict]] = None
    finish_reason: str = "stop"

@dataclass
class StreamChunk:
    type: str  # "text" | "tool_call_chunk" | "tool_call_end" | "usage"
    content: Optional[str] = None
    tool_call_id: Optional[str] = None
    tool_name: Optional[str] = None
    arguments: Optional[str] = None # For tool_call_chunk
    full_arguments: Optional[Dict] = None # For tool_call_end
    # Token usage fields
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None

tracer = trace.get_tracer(__name__)

class LLMService:
    """
    LLM 服务
    支持工具调用（Function Calling）
    """
    
    def __init__(self):
        # 根据提供商选择配置
        provider_type = settings.LLM_PROVIDER.lower()
        
        if provider_type == "deepseek":
            api_key = settings.DEEPSEEK_API_KEY
            base_url = settings.DEEPSEEK_BASE_URL
            self.chat_model = settings.DEEPSEEK_CHAT_MODEL or settings.LLM_MODEL_NAME
            self.reason_model = settings.DEEPSEEK_REASON_MODEL or settings.LLM_REASON_MODEL_NAME
        else:
            # 默认使用通用 LLM 配置 (OpenAI, Qwen 等)
            api_key = settings.LLM_API_KEY
            base_url = settings.LLM_API_BASE_URL
            self.chat_model = settings.LLM_MODEL_NAME
            self.reason_model = settings.LLM_REASON_MODEL_NAME or settings.LLM_MODEL_NAME
            
        self._provider_error: Optional[str] = None
        try:
            self.provider = OpenAICompatibleProvider(
                api_key=api_key,
                base_url=base_url
            )
        except Exception as e:
            self.provider = None
            self._provider_error = str(e)
            logger.warning(f"LLM provider unavailable; LLM features disabled: {e}")
        self.default_model = self.chat_model
        self.demo_mode = getattr(settings, 'DEMO_MODE', False)

    def _check_demo_match(self, messages: List[Dict[str, str]]) -> Optional[str]:
        """
        检查是否匹配演示关键词

        Returns:
            匹配的预设响应，如果不匹配则返回 None
        """
        if not self.demo_mode:
            return None

        # 获取最后一条用户消息
        user_content = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_content = msg.get("content", "").strip()
                break

        if not user_content:
            return None

        # 精确匹配
        if user_content in DEMO_MOCK_RESPONSES:
            logger.info(f"⚡ [DEMO MODE] Exact match for: {user_content}")
            return DEMO_MOCK_RESPONSES[user_content]

        # 模糊匹配 (包含关键词)
        for key, response in DEMO_MOCK_RESPONSES.items():
            if key in user_content or user_content in key:
                logger.info(f"⚡ [DEMO MODE] Fuzzy match for: {user_content} -> {key}")
                return response

        return None

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """
        Send a chat request to the LLM.
        """
        if not self.provider:
            raise HTTPException(
                status_code=501,
                detail=f"LLM provider unavailable: {self._provider_error or 'missing dependency'}"
            )
        model = model or self.chat_model
        with tracer.start_as_current_span("llm_chat") as span:
            span.set_attribute("llm.model", model)
            span.set_attribute("llm.temperature", temperature)
            
            # 🎭 Demo Mode 拦截
            mock_response = self._check_demo_match(messages)
            if mock_response:
                span.set_attribute("llm.demo_mode", True)
                # 模拟思考延迟
                await asyncio.sleep(1.0)
                return mock_response

            logger.debug(f"Sending chat request to model: {model}")
            response = await self.provider.chat(messages, model=model, temperature=temperature, **kwargs)
            return response

    async def reason(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.2,
        **kwargs
    ) -> str:
        """
        Send a deep reasoning request to the LLM.
        """
        if not self.provider:
            raise HTTPException(
                status_code=501,
                detail=f"LLM provider unavailable: {self._provider_error or 'missing dependency'}"
            )
        model = model or self.reason_model
        with tracer.start_as_current_span("llm_reason") as span:
            span.set_attribute("llm.model", model)
            span.set_attribute("llm.temperature", temperature)
            response = await self.provider.chat(messages, model=model, temperature=temperature, **kwargs)
            return response

    async def reason_json(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.2,
        **kwargs
    ) -> Any:
        """
        Request JSON output from the LLM using reasoning model.
        """
        raw = await self.reason(messages, model=model, temperature=temperature, **kwargs)
        cleaned = raw.replace("```json", "").replace("```", "").strip()

        def _extract_json_block(text: str) -> Optional[str]:
            for start, end in (("{", "}"), ("[", "]")):
                if start in text and end in text:
                    return text[text.find(start):text.rfind(end) + 1]
            return None

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            extracted = _extract_json_block(cleaned)
            if extracted:
                return json.loads(extracted)
            logger.warning("Failed to parse JSON from LLM reasoning response, returning empty result")
            return {}

    async def chat_json(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.3,
        **kwargs
    ) -> Any:
        """
        Request JSON output from the LLM and parse it safely.
        """
        raw = await self.chat(messages, model=model, temperature=temperature, **kwargs)
        cleaned = raw.replace("```json", "").replace("```", "").strip()

        def _extract_json_block(text: str) -> Optional[str]:
            for start, end in (("{", "}"), ("[", "]")):
                if start in text and end in text:
                    return text[text.find(start):text.rfind(end) + 1]
            return None

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            extracted = _extract_json_block(cleaned)
            if extracted:
                return json.loads(extracted)
            logger.warning("Failed to parse JSON from LLM response, returning empty result")
            return {}

    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        Stream chat response from the LLM.
        """
        if not self.provider:
            raise HTTPException(
                status_code=501,
                detail=f"LLM provider unavailable: {self._provider_error or 'missing dependency'}"
            )
        model = model or self.chat_model
        with tracer.start_as_current_span("llm_stream_chat") as span:
            span.set_attribute("llm.model", model)
            
            # 🎭 Demo Mode 拦截 - 流式返回预设响应
            mock_response = self._check_demo_match(messages)
            if mock_response:
                span.set_attribute("llm.demo_mode", True)
                # 模拟流式输出，每次输出几个字符
                chunk_size = 10
                for i in range(0, len(mock_response), chunk_size):
                    chunk = mock_response[i:i + chunk_size]
                    yield chunk
                    # 模拟打字效果的延迟
                    await asyncio.sleep(0.03)
                return

            logger.debug(f"Starting stream chat with model: {model}")
            async for chunk in self.provider.stream_chat(messages, model=model, temperature=temperature, **kwargs):
                yield chunk

    async def chat_with_tools(
        self,
        system_prompt: str,
        user_message: str,
        tools: List[Dict[str, Any]],
        conversation_history: Optional[List[Dict]] = None
    ) -> LLMResponse:
        """
        带工具调用的聊天
        """
        messages = [{"role": "system", "content": system_prompt}]
        
        if conversation_history:
            messages.extend(conversation_history)
        
        messages.append({"role": "user", "content": user_message})

        if not self.provider:
            raise HTTPException(
                status_code=501,
                detail=f"LLM provider unavailable: {self._provider_error or 'missing dependency'}"
            )

        if hasattr(self.provider, 'client'):
            with tracer.start_as_current_span("llm_chat_with_tools") as span:
                span.set_attribute("llm.model", self.default_model)
                
                response = await self.provider.client.chat.completions.create(
                    model=self.default_model,
                    messages=messages,
                    tools=tools,
                    tool_choice="auto",
                    temperature=0.7,
                )
                
                choice = response.choices[0]
                message = choice.message
                
                if response.usage:
                    span.set_attribute("llm.usage.prompt_tokens", response.usage.prompt_tokens)
                    span.set_attribute("llm.usage.completion_tokens", response.usage.completion_tokens)
                    span.set_attribute("llm.usage.total_tokens", response.usage.total_tokens)

                tool_calls_dicts = []
                if message.tool_calls:
                    for tc in message.tool_calls:
                        tool_calls_dicts.append({
                            "id": tc.id,
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            }
                        })

                return LLMResponse(
                    content=message.content or "",
                    tool_calls=tool_calls_dicts,
                    finish_reason=choice.finish_reason
                )
        else:
            raise NotImplementedError("Current LLM provider does not support tool calling directly.")
    
    async def continue_with_tool_results(
        self,
        conversation_history: List[Dict],
        tool_results: List[Dict]
    ) -> LLMResponse:
        """
        将工具执行结果反馈给 LLM，获取最终回复
        """
        messages = conversation_history[:]
        for result in tool_results:
            messages.append({
                "role": "tool",
                "content": json.dumps(result, ensure_ascii=False)
            })
        
        if not self.provider:
            raise HTTPException(
                status_code=501,
                detail=f"LLM provider unavailable: {self._provider_error or 'missing dependency'}"
            )

        if hasattr(self.provider, 'client'):
            with tracer.start_as_current_span("llm_continue_after_tools") as span:
                span.set_attribute("llm.model", self.default_model)
                
                response = await self.provider.client.chat.completions.create(
                    model=self.default_model,
                    messages=messages,
                    temperature=0.7,
                )
                choice = response.choices[0]
                message = choice.message
                
                if response.usage:
                    span.set_attribute("llm.usage.prompt_tokens", response.usage.prompt_tokens)
                    span.set_attribute("llm.usage.completion_tokens", response.usage.completion_tokens)
                    span.set_attribute("llm.usage.total_tokens", response.usage.total_tokens)

                return LLMResponse(
                    content=message.content or "",
                    tool_calls=None,
                    finish_reason=choice.finish_reason
                )
        else:
            raise NotImplementedError("Current LLM provider does not support tool calling directly.")
    
    async def chat_stream_with_tools(
        self,
        system_prompt: str,
        user_message: str,
        tools: List[Dict[str, Any]]
    ) -> AsyncIterator[StreamChunk]:
        """
        流式聊天（支持工具调用）
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

        if not self.provider:
            raise HTTPException(
                status_code=501,
                detail=f"LLM provider unavailable: {self._provider_error or 'missing dependency'}"
            )

        if hasattr(self.provider, 'client'):
            with tracer.start_as_current_span("llm_chat_stream_with_tools") as span:
                span.set_attribute("llm.model", self.default_model)
                
                stream = await self.provider.client.chat.completions.create(
                    model=self.default_model,
                    messages=messages,
                    tools=tools,
                    tool_choice="auto",
                    stream=True,
                    temperature=0.7,
                    stream_options={"include_usage": True}
                )

                collected_tool_call_chunks = {}
                usage_data = None

                async for chunk in stream:
                    if hasattr(chunk, 'usage') and chunk.usage:
                        usage_data = chunk.usage

                    if chunk.choices:
                        delta = chunk.choices[0].delta
                        if delta.content:
                            yield StreamChunk(type="text", content=delta.content)

                        if delta.tool_calls:
                            for tc_chunk in delta.tool_calls:
                                tool_call_id = tc_chunk.id
                                if tool_call_id not in collected_tool_call_chunks:
                                    collected_tool_call_chunks[tool_call_id] = {"name": "", "args_str": ""}
                                if tc_chunk.function.name:
                                    collected_tool_call_chunks[tool_call_id]["name"] = tc_chunk.function.name
                                    yield StreamChunk(type="tool_call_chunk", tool_call_id=tool_call_id, tool_name=tc_chunk.function.name)
                                if tc_chunk.function.arguments:
                                    collected_tool_call_chunks[tool_call_id]["args_str"] += tc_chunk.function.arguments
                                    yield StreamChunk(type="tool_call_chunk", tool_call_id=tool_call_id, arguments=tc_chunk.function.arguments)

                for tool_call_id, data in collected_tool_call_chunks.items():
                    if data["name"] and data["args_str"]:
                        try:
                            full_arguments = json.loads(data["args_str"])
                            yield StreamChunk(
                                type="tool_call_end",
                                tool_call_id=tool_call_id,
                                tool_name=data["name"],
                                full_arguments=full_arguments
                            )
                        except json.JSONDecodeError:
                            logger.error(f"Failed to decode tool arguments for {tool_call_id}: {data['args_str']}")

                if usage_data:
                    span.set_attribute("llm.usage.prompt_tokens", usage_data.prompt_tokens)
                    span.set_attribute("llm.usage.completion_tokens", usage_data.completion_tokens)
                    span.set_attribute("llm.usage.total_tokens", usage_data.total_tokens)
                    yield StreamChunk(
                        type="usage",
                        prompt_tokens=usage_data.prompt_tokens,
                        completion_tokens=usage_data.completion_tokens,
                        total_tokens=usage_data.total_tokens
                    )
        else:
            raise NotImplementedError("Current LLM provider does not support streamed tool calling directly.")

    async def generate_push_content(
        self,
        user_nickname: str,
        persona: str,
        trigger_type: str,
        context_data: Dict
    ) -> Dict[str, str]:
        """
        Generate "irresistible" push notification content based on persona.
        """
        persona_prompts = {
            "coach": "Role: Strict, discipline-focused Study Coach. Tone: Stern, urgent, authoritative.",
            "anime": "Role: Gentle, cute, energetic Anime Assistant. Tone: Sweet, encouraging."
        }
        selected_persona_prompt = persona_prompts.get(persona, persona_prompts["coach"])
        
        trigger_desc = ""
        if trigger_type == "memory":
            nodes = ", ".join(context_data.get("nodes", []))
            trigger_desc = f"User is forgetting: {nodes}."
        elif trigger_type == "sprint":
            trigger_desc = f"Deadline approaching for plan '{context_data.get('plan_name')}'."
        elif trigger_type == "inactivity":
            trigger_desc = "User hasn't studied for over 24 hours."
        
        system_prompt = f"You are Sparkle, an AI Learning Assistant. {selected_persona_prompt} Context: {trigger_desc}"
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Generate push notification now."}
        ]
        
        try:
            with tracer.start_as_current_span("llm_generate_push") as span:
                span.set_attribute("llm.persona", persona)
                span.set_attribute("llm.trigger", trigger_type)
                
                response_text = await self.chat(messages, temperature=0.8)
                cleaned_text = response_text.replace("```json", "").replace("```", "").strip()
                content = json.loads(cleaned_text)
                return content
        except Exception as e:
            logger.error(f"Failed to generate push content: {e}")
            return {"title": "学习提醒", "body": f"{user_nickname}，该复习了。"}

# Singleton instance
llm_service = LLMService()
