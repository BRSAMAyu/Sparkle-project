"""
向量嵌入服务 (Embedding Service)
用于将文本转换为向量表示，支持语义搜索

支持双供应商自动故障切换：
- DashScope (阿里云百炼 SDK) - 主供应商
- SiliconFlow (HTTP API) - 备用供应商
"""
import asyncio
from http import HTTPStatus

import httpx
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings
from app.services.circuit_breaker import CircuitBreakerOpenException, circuit_breaker_service

try:
    import dashscope
except ImportError:  # pragma: no cover - optional dependency in some test/dev envs
    dashscope = None


class EmbeddingService:
    """
    文本向量嵌入服务

    支持双供应商自动故障切换：
    - DashScope (阿里云百炼 SDK) - 使用 text-embedding-v4
    - SiliconFlow (HTTP API) - 使用 Qwen/Qwen3-Embedding-4B (同款模型)

    当主供应商失败时，自动切换到备用供应商
    """

    # 供应商优先级顺序
    PROVIDER_ORDER = ["dashscope", "siliconflow"]

    def __init__(self):
        self.primary_provider = settings.EMBEDDING_PROVIDER
        self.backup_provider = settings.EMBEDDING_BACKUP_PROVIDER
        self.embedding_dim = settings.EMBEDDING_DIM

        # DashScope 配置 (阿里云百炼)
        self.dashscope_api_key = settings.DASHSCOPE_API_KEY
        self.dashscope_base_url = settings.DASHSCOPE_BASE_HTTP_API_URL
        self.dashscope_model = settings.DASHSCOPE_EMBEDDING_MODEL  # text-embedding-v4

        # SiliconFlow 配置 (备用)
        self.siliconflow_api_key = settings.SILICONFLOW_API_KEY
        self.siliconflow_base_url = settings.SILICONFLOW_BASE_URL
        self.siliconflow_model = settings.SILICONFLOW_EMBEDDING_MODEL  # Qwen/Qwen3-Embedding-4B

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def get_embedding(self, text: str, text_type: str = "document") -> list[float]:
        """
        获取文本的向量表示

        Args:
            text: 输入文本
            text_type: query | document

        Returns:
            List[float]: 向量
        """
        embeddings = await self.batch_embeddings([text], text_type=text_type)
        return embeddings[0]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def batch_embeddings(self, texts: list[str], text_type: str = "document") -> list[list[float]]:
        """
        批量获取文本向量 (支持双供应商自动故障切换)

        Args:
            texts: 文本列表
            text_type: query | document

        Returns:
            List[List[float]]: 向量列表
        """
        if not texts:
            return []

        # 构建供应商尝试顺序：主供应商优先，备用供应商其次
        providers_to_try = self._get_provider_order()

        last_error = None
        for provider in providers_to_try:
            try:
                await circuit_breaker_service.check(f"embedding:{provider}")
                if provider == "dashscope":
                    if not self.dashscope_api_key:
                        continue
                    result = await self._dashscope_embeddings(texts, text_type=text_type)
                elif provider == "siliconflow":
                    if not self.siliconflow_api_key:
                        continue
                    result = await self._siliconflow_embeddings(texts)
                else:
                    continue
                await circuit_breaker_service.record_success(f"embedding:{provider}")
                return result
            except CircuitBreakerOpenException as e:
                logger.warning(f"Embedding provider {provider} skipped because circuit breaker is open: {e}")
                last_error = e
                continue
            except Exception as e:
                logger.warning(f"Embedding provider {provider} failed: {e}")
                await circuit_breaker_service.record_failure(f"embedding:{provider}")
                last_error = e
                continue

        # 所有供应商都失败
        if settings.DEMO_MODE:
            return [[0.0] * self.embedding_dim for _ in texts]
        raise RuntimeError(f"All embedding providers failed. Last error: {last_error}")

    def _get_provider_order(self) -> list[str]:
        """获取供应商尝试顺序 (主供应商优先)"""
        order = [self.primary_provider, self.backup_provider]
        for provider in self.PROVIDER_ORDER:
            if provider not in order:
                order.append(provider)
        return order

    async def _dashscope_embeddings(self, texts: list[str], text_type: str = "document") -> list[list[float]]:
        if dashscope is None:
            raise RuntimeError("dashscope package is required for dashscope embedding provider")

        def _call():
            dashscope.api_key = self.dashscope_api_key
            if self.dashscope_base_url:
                dashscope.base_http_api_url = self.dashscope_base_url

            payload = {
                "model": self.dashscope_model,
                "input": texts,
                "dimension": self.embedding_dim,
                "text_type": text_type,
            }
            return dashscope.TextEmbedding.call(**payload)

        resp = await asyncio.to_thread(_call)
        if resp.status_code != HTTPStatus.OK:
            raise RuntimeError(f"DashScope embedding failed: {resp.code} {resp.message}")

        embeddings = resp.output.get("embeddings", [])
        return [item["embedding"] for item in embeddings]

    async def _siliconflow_embeddings(self, texts: list[str]) -> list[list[float]]:
        base_url = self.siliconflow_base_url.rstrip("/")
        url = base_url if base_url.endswith("/embeddings") else f"{base_url}/embeddings"
        payload = {
            "model": self.siliconflow_model,
            "input": texts,
            "encoding_format": "float",
            "dimensions": self.embedding_dim,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {self.siliconflow_api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        embeddings = [None] * len(texts)
        for item in data["data"]:
            embeddings[item["index"]] = item["embedding"]
        return embeddings


# 全局实例
embedding_service = EmbeddingService()
