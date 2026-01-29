"""
向量嵌入服务 (Embedding Service)
用于将文本转换为向量表示，支持语义搜索
"""
from typing import List
import asyncio
from http import HTTPStatus

import dashscope
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings


class EmbeddingService:
    """
    文本向量嵌入服务

    支持多个 Provider：
    - DashScope (阿里云百炼 SDK)
    - SiliconFlow (HTTP API)
    """

    def __init__(self):
        self.provider = settings.EMBEDDING_PROVIDER
        self.embedding_dim = settings.EMBEDDING_DIM

        self.dashscope_api_key = settings.DASHSCOPE_API_KEY
        self.dashscope_base_url = settings.DASHSCOPE_BASE_HTTP_API_URL
        self.dashscope_model = settings.DASHSCOPE_EMBEDDING_MODEL or settings.EMBEDDING_MODEL

        self.siliconflow_api_key = settings.SILICONFLOW_API_KEY
        self.siliconflow_base_url = settings.SILICONFLOW_BASE_URL
        self.siliconflow_model = settings.SILICONFLOW_EMBEDDING_MODEL or settings.EMBEDDING_MODEL

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def get_embedding(self, text: str, text_type: str = "document") -> List[float]:
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
    async def batch_embeddings(self, texts: List[str], text_type: str = "document") -> List[List[float]]:
        """
        批量获取文本向量

        Args:
            texts: 文本列表
            text_type: query | document

        Returns:
            List[List[float]]: 向量列表
        """
        if not texts:
            return []

        if self.provider == "dashscope":
            if not self.dashscope_api_key:
                if settings.DEMO_MODE:
                    return [[0.0] * self.embedding_dim for _ in texts]
                raise ValueError("DASHSCOPE_API_KEY not set for dashscope embedding provider")
            return await self._dashscope_embeddings(texts, text_type=text_type)
        if self.provider == "siliconflow":
            if not self.siliconflow_api_key:
                if settings.DEMO_MODE:
                    return [[0.0] * self.embedding_dim for _ in texts]
                raise ValueError("SILICONFLOW_API_KEY not set for siliconflow embedding provider")
            return await self._siliconflow_embeddings(texts)

        raise ValueError(f"Unsupported embedding provider: {self.provider}")

    async def _dashscope_embeddings(self, texts: List[str], text_type: str = "document") -> List[List[float]]:
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

    async def _siliconflow_embeddings(self, texts: List[str]) -> List[List[float]]:
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
