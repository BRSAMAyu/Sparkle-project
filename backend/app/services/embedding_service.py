"""
向量嵌入服务 (Embedding Service)
用于将文本转换为向量表示，支持语义搜索
"""
from typing import List
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings


class EmbeddingService:
    """
    文本向量嵌入服务

    支持多个 LLM 提供商：
    - Qwen (通义千问)
    - DeepSeek
    - OpenAI (备用)
    """

    def __init__(self):
        self.provider = settings.LLM_PROVIDER
        self.api_key = settings.LLM_API_KEY
        self.base_url = settings.LLM_API_BASE_URL
        self.embedding_model = settings.EMBEDDING_MODEL
        self.embedding_dim = settings.EMBEDDING_DIM

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def get_embedding(self, text: str) -> List[float]:
        """
        获取文本的向量表示

        Args:
            text: 输入文本

        Returns:
            List[float]: 向量 (默认 1536 维)
        """
        embeddings = await self.batch_embeddings([text])
        return embeddings[0]

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        批量获取文本向量

        Args:
            texts: 文本列表

        Returns:
            List[List[float]]: 向量列表
        """
        if not texts:
            return []

        async with httpx.AsyncClient(timeout=60.0) as client:
            # 使用 OpenAI 兼容的 API 格式
            response = await client.post(
                f"{self.base_url}/v1/embeddings" if "/v1/embeddings" not in self.base_url else self.base_url,
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.embedding_model,
                    "input": texts
                }
            )
            response.raise_for_status()
            data = response.json()

            # 按索引顺序返回
            embeddings = [None] * len(texts)
            for item in data["data"]:
                embeddings[item["index"]] = item["embedding"]

            return embeddings

    async def _qwen_embedding(self, client: httpx.AsyncClient, text: str) -> List[float]:
        """通义千问 Embedding API"""
        response = await client.post(
            f"{self.base_url}/embeddings",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.embedding_model,
                "input": text
            }
        )
        response.raise_for_status()
        data = response.json()
        return data["data"][0]["embedding"]

    async def _deepseek_embedding(self, client: httpx.AsyncClient, text: str) -> List[float]:
        """DeepSeek Embedding API"""
        response = await client.post(
            f"{self.base_url}/embeddings",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": "deepseek-embedding",
                "input": text
            }
        )
        response.raise_for_status()
        data = response.json()
        return data["data"][0]["embedding"]

    async def _openai_embedding(self, client: httpx.AsyncClient, text: str) -> List[float]:
        """OpenAI Embedding API"""
        response = await client.post(
            f"{self.base_url}/embeddings",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": "text-embedding-ada-002",
                "input": text
            }
        )
        response.raise_for_status()
        data = response.json()
        return data["data"][0]["embedding"]


# 全局实例
embedding_service = EmbeddingService()
