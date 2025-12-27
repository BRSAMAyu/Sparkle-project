import json
from typing import List, Dict, AsyncGenerator, Optional, Any, AsyncIterator
import asyncio
from loguru import logger
from dataclasses import dataclass

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
        else:
            # 默认使用通用 LLM 配置 (OpenAI, Qwen 等)
            api_key = settings.LLM_API_KEY
            base_url = settings.LLM_API_BASE_URL
            
        self.provider: LLMProvider = OpenAICompatibleProvider(
            api_key=api_key,
            base_url=base_url
        )
        self.default_model = settings.LLM_MODEL_NAME
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
        # 🎭 Demo Mode 拦截
        mock_response = self._check_demo_match(messages)
        if mock_response:
            # 模拟思考延迟
            await asyncio.sleep(1.0)
            return mock_response

        model = model or self.default_model
        logger.debug(f"Sending chat request to model: {model}")
        return await self.provider.chat(messages, model=model, temperature=temperature, **kwargs)

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
        # 🎭 Demo Mode 拦截 - 流式返回预设响应
        mock_response = self._check_demo_match(messages)
        if mock_response:
            # 模拟流式输出，每次输出几个字符
            chunk_size = 10
            for i in range(0, len(mock_response), chunk_size):
                chunk = mock_response[i:i + chunk_size]
                yield chunk
                # 模拟打字效果的延迟
                await asyncio.sleep(0.03)
            return

        model = model or self.default_model
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
        
        Args:
            system_prompt: 系统提示词
            user_message: 用户消息
            tools: OpenAI 格式的工具定义
            conversation_history: 对话历史
            
        Returns:
            LLMResponse: 包含文本和工具调用的响应
        """
        messages = [{"role": "system", "content": system_prompt}]
        
        if conversation_history:
            messages.extend(conversation_history)
        
        messages.append({"role": "user", "content": user_message})

        # Using self.provider.client (AsyncOpenAI) directly for tool calls
        if hasattr(self.provider, 'client'):
            response = await self.provider.client.chat.completions.create(
                model=self.default_model,
                messages=messages,
                tools=tools,
                tool_choice="auto",  # 让模型自动决定是否调用工具
                temperature=0.7, # Default temperature
            )
            
            choice = response.choices[0]
            message = choice.message
            
            tool_calls_dicts = []
            if message.tool_calls:
                for tc in message.tool_calls:
                    tool_calls_dicts.append({
                        "id": tc.id,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments, # Arguments are already string
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
        conversation_history: List[Dict], # full history up to LLM's initial response
        tool_results: List[Dict] # tool_results from executor
    ) -> LLMResponse:
        """
        将工具执行结果反馈给 LLM，获取最终回复
        """
        messages = conversation_history[:] # Copy history
        
        # Append tool messages
        for result in tool_results:
            # Need to find the original tool_call_id from the conversation_history if possible
            # Or just append as a 'tool' role message
            messages.append({
                "role": "tool",
                # "tool_call_id": result.get("tool_call_id", ""), # if we track original tool_call_id
                "content": json.dumps(result, ensure_ascii=False)
            })
        
        # Now call LLM again without tools, get final message
        if hasattr(self.provider, 'client'):
            response = await self.provider.client.chat.completions.create(
                model=self.default_model,
                messages=messages,
                temperature=0.7,
            )
            choice = response.choices[0]
            message = choice.message
            return LLMResponse(
                content=message.content or "",
                tool_calls=None, # No more tool calls expected
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

        Yields:
            StreamChunk: 文本块、工具调用或 Token 使用量
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

        if hasattr(self.provider, 'client'):
            stream = await self.provider.client.chat.completions.create(
                model=self.default_model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                stream=True,
                temperature=0.7,
                stream_options={"include_usage": True}  # 请求 usage 信息
            )

            collected_tool_call_chunks = {} # {id: {name: "", args_str: ""}}
            usage_data = None

            async for chunk in stream:
                # Handle usage data (may come in final chunk)
                if hasattr(chunk, 'usage') and chunk.usage:
                    usage_data = chunk.usage

                # Handle choices
                if chunk.choices:
                    delta = chunk.choices[0].delta

                    # Text content
                    if delta.content:
                        yield StreamChunk(type="text", content=delta.content)

                    # Tool call chunks
                    if delta.tool_calls:
                        for tc_chunk in delta.tool_calls:
                            tool_call_id = tc_chunk.id

                            if tool_call_id not in collected_tool_call_chunks:
                                collected_tool_call_chunks[tool_call_id] = {
                                    "name": "",
                                    "args_str": ""
                                }

                            if tc_chunk.function.name:
                                collected_tool_call_chunks[tool_call_id]["name"] = tc_chunk.function.name
                                yield StreamChunk(type="tool_call_chunk", tool_call_id=tool_call_id, tool_name=tc_chunk.function.name)

                            if tc_chunk.function.arguments:
                                collected_tool_call_chunks[tool_call_id]["args_str"] += tc_chunk.function.arguments
                                yield StreamChunk(type="tool_call_chunk", tool_call_id=tool_call_id, arguments=tc_chunk.function.arguments)

            # After stream ends, yield full tool call if any
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

            # Finally, yield usage data
            if usage_data:
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
        
        Args:
            user_nickname: Name of the user
            persona: "coach" (strict) or "anime" (gentle/cute) or others
            trigger_type: "memory", "sprint", "inactivity"
            context_data: Data from strategy (nodes, plan name, etc.)
            
        Returns:
            Dict with "title" and "body" keys.
        """
        
        # 1. Define Persona Prompts
        persona_prompts = {
            "coach": """
            Role: Strict, discipline-focused Study Coach.
            Tone: Stern, urgent, authoritative. 
            Style: Use rhetorical questions, emphasize consequences of laziness.
            Example: "还没学完？你的线性代数正在哭泣！"
            """,
            "anime": """
            Role: Gentle, cute, energetic Anime Assistant (like a younger sister or supportive friend).
            Tone: Sweet, encouraging, uses emojis (✨, 🥺, 🔥).
            Style: Address user as '欧尼酱' or '亲爱的', emphasize growing together.
            Example: "欧尼酱~ 记忆碎片要消失了哦，快来补救吧！✨"
            """
        }
        
        selected_persona_prompt = persona_prompts.get(persona, persona_prompts["coach"]) # Default to coach
        
        # 2. Define Context Description based on Trigger
        trigger_desc = ""
        if trigger_type == "memory":
            nodes = ", ".join(context_data.get("nodes", []))
            retention = int(context_data.get("retention_rate", 0) * 100)
            trigger_desc = f"User is forgetting these topics: {nodes}. Retention is down to {retention}%. Explain that reviewing now saves time later."
        elif trigger_type == "sprint":
            plan_name = context_data.get("plan_name", "Plan")
            hours = context_data.get("hours_remaining", 0)
            trigger_desc = f"Deadline approaching for plan '{plan_name}' in {hours} hours. Urge immediate action to avoid failure."
        elif trigger_type == "inactivity":
            trigger_desc = "User hasn't studied for over 24 hours. Gently guilt-trip (coach) or sweetly miss them (anime) to bring them back."
        
        # 3. Construct Full Prompt
        system_prompt = f"""
        You are Sparkle, an AI Learning Assistant.
        {selected_persona_prompt}
        
        Task: Write a push notification for user '{user_nickname}'.
        Context: {trigger_desc}
        
        Constraints:
        1. Language: Chinese (Simplified).
        2. Length: Body must be under 30 words. Title under 10 words.
        3. Format: Return ONLY a valid JSON object with keys "title" and "body". Do not wrap in markdown code blocks.
        4. Content: Must explain "WHY study NOW".
        """
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Generate push notification now."}
        ]
        
        # 4. Call LLM
        try:
            response_text = await self.chat(messages, temperature=0.8) # Slightly higher temp for creativity
            
            # 5. Parse JSON
            # Clean up potential markdown formatting like ```json ... ```
            cleaned_text = response_text.replace("```json", "").replace("```", "").strip()
            
            content = json.loads(cleaned_text)
            
            # Fallback validation
            if "title" not in content or "body" not in content:
                raise ValueError("Missing keys in JSON response")
                
            return content
            
        except Exception as e:
            logger.error(f"Failed to generate push content: {e}")
            # Fallback hardcoded messages
            if persona == "anime":
                return {
                    "title": "想你了~ ✨",
                    "body": f"{user_nickname}，好久没来学习了，记忆都要发霉啦！🥺"
                }
            else:
                return {
                    "title": "学习提醒",
                    "body": f"{user_nickname}，该复习了。拖延只会增加未来的负担。"
                }

# Singleton instance
llm_service = LLMService()