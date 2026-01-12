"""
LLM Client Wrapper
Provides a unified interface for different LLM providers (Qwen, DeepSeek, OpenAI)
"""
from typing import List, Dict, Any, Optional
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings


class LLMClient:
    """
    统一的 LLM 客户端接口
    支持多个提供商：Qwen, DeepSeek, OpenAI
    """

    def __init__(self):
        self.provider = settings.LLM_PROVIDER
        if self.provider == "deepseek":
            self.api_key = settings.DEEPSEEK_API_KEY
            self.base_url = settings.DEEPSEEK_BASE_URL
            self.model_name = settings.DEEPSEEK_CHAT_MODEL
        else:
            self.api_key = settings.LLM_API_KEY
            self.base_url = settings.LLM_API_BASE_URL
            self.model_name = settings.LLM_MODEL_NAME

        self.chat_model_name = settings.DEEPSEEK_CHAT_MODEL or settings.LLM_MODEL_NAME
        self.reason_model_name = settings.DEEPSEEK_REASON_MODEL or settings.LLM_REASON_MODEL_NAME

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, str]] = None,
        stream: bool = False,
        model: Optional[str] = None
    ) -> str:
        """
        调用 LLM Chat Completion API

        Args:
            messages: 对话消息列表 [{"role": "user", "content": "..."}]
            temperature: 温度参数 (0-2)
            max_tokens: 最大token数
            response_format: 响应格式，如 {"type": "json_object"}
            stream: 是否使用流式响应

        Returns:
            str: LLM 响应内容
        """
        async with httpx.AsyncClient(timeout=60.0) as client:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": model or self.chat_model_name or self.model_name,
                "messages": messages,
                "temperature": temperature,
            }

            if max_tokens:
                payload["max_tokens"] = max_tokens

            if response_format:
                payload["response_format"] = response_format

            if stream:
                payload["stream"] = True

            # 统一的 OpenAI 兼容 API 格式
            response = await client.post(
                f"{self.base_url}/v1/chat/completions" if not self.base_url.endswith("/chat/completions") else self.base_url,
                headers=headers,
                json=payload
            )

            response.raise_for_status()
            data = response.json()

            # 提取响应内容
            if "choices" in data and len(data["choices"]) > 0:
                return data["choices"][0]["message"]["content"]
            else:
                raise ValueError(f"Unexpected response format from LLM: {data}")

    async def reason_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, str]] = None
    ) -> str:
        """
        调用 LLM Reasoning 模型
        """
        return await self.chat_completion(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format,
            model=self.reason_model_name
        )

    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        生成文本向量 (批量)

        Args:
            texts: 文本列表

        Returns:
            List[List[float]]: 向量列表
        """
        async with httpx.AsyncClient(timeout=60.0) as client:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": settings.EMBEDDING_MODEL,
                "input": texts
            }

            response = await client.post(
                f"{self.base_url}/v1/embeddings" if not self.base_url.endswith("/embeddings") else self.base_url,
                headers=headers,
                json=payload
            )

            response.raise_for_status()
            data = response.json()

            # 按索引排序返回
            embeddings = [None] * len(texts)
            for item in data["data"]:
                embeddings[item["index"]] = item["embedding"]

            return embeddings


# 全局实例
llm_client = LLMClient()
