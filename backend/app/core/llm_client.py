"""
LLM Client Wrapper
Provides a unified interface for different LLM providers (Qwen, DeepSeek, OpenAI)
"""
from __future__ import annotations
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings
from app.core.llm_secure_io import (
    refresh_llm_safety_mode,
    sanitize_llm_output,
    sanitize_text_for_llm,
    secure_messages,
)
from app.services.llm.providers import OpenAICompatibleProvider


class LLMClient:
    """
    统一的 LLM 客户端接口
    支持多个提供商：Qwen, DeepSeek, OpenAI, Xiaomi, Zhipu
    """

    def __init__(self):
        pass

    def _resolve_provider_config(self) -> dict[str, str]:
        provider = settings.LLM_PROVIDER

        api_key = settings.LLM_API_KEY
        base_url = settings.LLM_API_BASE_URL
        model_name = settings.LLM_MODEL_NAME
        chat_model_name = settings.LLM_MODEL_NAME
        reason_model_name = settings.LLM_REASON_MODEL_NAME

        if provider == "deepseek":
            api_key = settings.DEEPSEEK_API_KEY
            base_url = settings.DEEPSEEK_BASE_URL
            model_name = settings.DEEPSEEK_CHAT_MODEL
            chat_model_name = settings.DEEPSEEK_CHAT_MODEL
            reason_model_name = settings.DEEPSEEK_REASON_MODEL
        elif provider == "dashscope":
            api_key = settings.DASHSCOPE_API_KEY
            base_url = settings.DASHSCOPE_BASE_URL_COMPATIBLE
            model_name = settings.DASHSCOPE_CHAT_MODEL
            chat_model_name = settings.DASHSCOPE_CHAT_MODEL
            reason_model_name = settings.DASHSCOPE_REASON_MODEL
        elif provider == "xiaomi":
            api_key = settings.XIAOMI_MIMO_API_KEY
            base_url = settings.XIAOMI_MIMO_BASE_URL
            model_name = settings.XIAOMI_CHAT_MODEL
            chat_model_name = settings.XIAOMI_CHAT_MODEL
            reason_model_name = settings.XIAOMI_CHAT_MODEL
        elif provider == "zhipu":
            api_key = settings.ZHIPU_API_KEY
            base_url = settings.ZHIPU_CODING_BASE_URL
            model_name = settings.ZHIPU_CHAT_MODEL
            chat_model_name = settings.ZHIPU_CHAT_MODEL
            reason_model_name = settings.ZHIPU_CHAT_MODEL

        if not chat_model_name:
            chat_model_name = model_name
        if not reason_model_name:
            reason_model_name = chat_model_name

        return {
            "provider": provider,
            "api_key": api_key,
            "base_url": base_url,
            "model_name": model_name,
            "chat_model_name": chat_model_name,
            "reason_model_name": reason_model_name,
        }

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
        await refresh_llm_safety_mode()
        provider_config = self._resolve_provider_config()
        safe_messages = secure_messages(messages, wrap_user_messages=True)
        async with httpx.AsyncClient(timeout=60.0) as client:
            headers = {
                "Authorization": f"Bearer {provider_config['api_key']}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": model or provider_config["chat_model_name"] or provider_config["model_name"],
                "messages": safe_messages,
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
            url = provider_config["base_url"].rstrip("/")
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
                return sanitize_llm_output(
                    data["choices"][0]["message"]["content"],
                    context={"type": "llm_client.chat_completion"},
                )
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
        provider_config = self._resolve_provider_config()
        return await self.chat_completion(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format,
            model=provider_config["reason_model_name"],
        )

    async def generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        """
        生成文本向量 (批量)

        Args:
            texts: 文本列表

        Returns:
            List[List[float]]: 向量列表
        """
        await refresh_llm_safety_mode()
        provider_config = self._resolve_provider_config()
        safe_texts = [sanitize_text_for_llm(text) for text in texts]
        async with httpx.AsyncClient(timeout=60.0) as client:
            headers = {
                "Authorization": f"Bearer {provider_config['api_key']}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": settings.EMBEDDING_MODEL,
                "input": safe_texts
            }

            # 构建 API URL (与 chat_completion 保持一致的逻辑)
            # 1. 如果 base_url 已经包含完整路径 (ending in /embeddings)，直接使用
            # 2. 如果 base_url 包含版本号 (v1, v4)，直接追加 /embeddings
            # 3. 否则默认追加 /v1/embeddings
            url = provider_config["base_url"].rstrip("/")
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
            embeddings = [None] * len(safe_texts)
            for item in data["data"]:
                embeddings[item["index"]] = item["embedding"]

            return embeddings


# 全局实例
llm_client = LLMClient()


class SecureLLMClient:
    """Small secure wrapper for ad-hoc provider calls outside LLMService."""

    def __init__(self, provider: OpenAICompatibleProvider):
        self._provider = provider

    @classmethod
    def get(
        cls,
        *,
        api_key: str,
        base_url: str,
        timeout_seconds: float = 60.0,
    ) -> SecureLLMClient:
        return cls(
            OpenAICompatibleProvider(
                api_key=api_key,
                base_url=base_url,
                timeout_seconds=timeout_seconds,
            )
        )

    async def chat(
        self,
        messages: list[dict[str, Any]],
        *,
        model: str,
        temperature: float = 0.7,
        user_id: str | None = None,
        **kwargs,
    ) -> str:
        await refresh_llm_safety_mode()
        safe_messages = secure_messages(
            messages,
            user_id=user_id,
            wrap_user_messages=True,
        )
        response = await self._provider.chat(
            safe_messages,
            model=model,
            temperature=temperature,
            **kwargs,
        )
        return sanitize_llm_output(
            response,
            context={"type": "secure_llm_client.chat", "user_id": user_id},
        )
