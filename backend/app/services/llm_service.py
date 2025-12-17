from typing import List, Dict, AsyncGenerator, Optional
import asyncio
from loguru import logger

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


class LLMService:
    def __init__(self):
        self.provider: LLMProvider = OpenAICompatibleProvider(
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_API_BASE_URL
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

# Singleton instance
llm_service = LLMService()
