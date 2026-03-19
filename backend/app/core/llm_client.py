"""
LLM Client Wrapper
Provides a unified interface for different LLM providers (Qwen, DeepSeek, OpenAI)
"""
from __future__ import annotations
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings


class LLMClient:
    """
    统一的 LLM 客户端接口
    支持多个提供商：Qwen, DeepSeek, OpenAI, Xiaomi, Zhipu
    """

    def __init__(self):
        self.provider = settings.LLM_PROVIDER
        
        # Initialize defaults
        self.api_key = settings.LLM_API_KEY
        self.base_url = settings.LLM_API_BASE_URL
        self.model_name = settings.LLM_MODEL_NAME
        self.chat_model_name = settings.LLM_MODEL_NAME
        self.reason_model_name = settings.LLM_REASON_MODEL_NAME

        # Provider specific overrides
        if self.provider == "deepseek":
            self.api_key = settings.DEEPSEEK_API_KEY
            self.base_url = settings.DEEPSEEK_BASE_URL
            self.model_name = settings.DEEPSEEK_CHAT_MODEL
            self.chat_model_name = settings.DEEPSEEK_CHAT_MODEL
            self.reason_model_name = settings.DEEPSEEK_REASON_MODEL
        elif self.provider == "dashscope":
            self.api_key = settings.DASHSCOPE_API_KEY
            self.base_url = settings.DASHSCOPE_BASE_URL_COMPATIBLE
            self.model_name = settings.DASHSCOPE_CHAT_MODEL
            self.chat_model_name = settings.DASHSCOPE_CHAT_MODEL
            self.reason_model_name = settings.DASHSCOPE_REASON_MODEL
        elif self.provider == "xiaomi":
            self.api_key = settings.XIAOMI_MIMO_API_KEY
            self.base_url = settings.XIAOMI_MIMO_BASE_URL
            self.model_name = settings.XIAOMI_CHAT_MODEL
            self.chat_model_name = settings.XIAOMI_CHAT_MODEL
            self.reason_model_name = settings.XIAOMI_CHAT_MODEL  # Xiaomi使用相同模型，通过tag控制
        elif self.provider == "zhipu":
            self.api_key = settings.ZHIPU_API_KEY
            self.base_url = settings.ZHIPU_CODING_BASE_URL
            self.model_name = settings.ZHIPU_CHAT_MODEL
            self.chat_model_name = settings.ZHIPU_CHAT_MODEL
            self.reason_model_name = settings.ZHIPU_CHAT_MODEL  # Zhipu使用相同模型，通过tag控制

        # Fallback if specific model names are not set
        if not self.chat_model_name:
            self.chat_model_name = self.model_name
        if not self.reason_model_name:
            self.reason_model_name = self.chat_model_name

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int | None = None,
        response_format: dict[str, str] | None = None,
        stream: bool = False,
        model: str | None = None
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

            # 构建 API URL
            # 1. 如果 base_url 已经包含完整路径 (ending in /chat/completions)，直接使用
            # 2. 如果 base_url 包含版本号 (v1, v4)，直接追加 /chat/completions
            # 3. 否则默认追加 /v1/chat/completions
            url = self.base_url.rstrip("/")
            if url.endswith("/chat/completions"):
                pass
            elif url.endswith("/v1") or url.endswith("/v4"):
                url = f"{url}/chat/completions"
            else:
                url = f"{url}/v1/chat/completions"

            response = await client.post(
                url,
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
        messages: list[dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int | None = None,
        response_format: dict[str, str] | None = None
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

    async def generate_embeddings(self, texts: list[str]) -> list[list[float]]:
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

            # 构建 API URL (与 chat_completion 保持一致的逻辑)
            # 1. 如果 base_url 已经包含完整路径 (ending in /embeddings)，直接使用
            # 2. 如果 base_url 包含版本号 (v1, v4)，直接追加 /embeddings
            # 3. 否则默认追加 /v1/embeddings
            url = self.base_url.rstrip("/")
            if url.endswith("/embeddings"):
                pass
            elif url.endswith("/v1") or url.endswith("/v4"):
                url = f"{url}/embeddings"
            else:
                url = f"{url}/v1/embeddings"

            response = await client.post(
                url,
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
