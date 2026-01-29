import asyncio
from http import HTTPStatus
from typing import Any

import dashscope
import httpx
from loguru import logger

from app.config import settings


class RerankService:
    """
    Rerank Service for RAG v2.0
    Supports:
    - RRF (Reciprocal Rank Fusion)
    - DashScope (阿里云百炼 SDK)
    - SiliconFlow (HTTP API)
    """

    def __init__(self):
        self.provider = settings.RERANK_PROVIDER
        self.dashscope_api_key = settings.DASHSCOPE_API_KEY
        self.dashscope_base_url = settings.DASHSCOPE_BASE_HTTP_API_URL
        self.dashscope_model = settings.DASHSCOPE_RERANK_MODEL or settings.RERANK_MODEL

        self.siliconflow_api_key = settings.SILICONFLOW_API_KEY
        self.siliconflow_base_url = settings.SILICONFLOW_BASE_URL
        self.siliconflow_model = settings.SILICONFLOW_RERANK_MODEL or settings.RERANK_MODEL

    def reciprocal_rank_fusion(self, search_results_list: list[list[Any]], k: int = 60) -> list[tuple]:
        """
        RRF (Reciprocal Rank Fusion) algorithm.
        search_results_list: List of result lists (e.g. [vector_results, keyword_results])
        k: Constant for RRF (default 60)
        Returns: List of (item, score) sorted by score desc
        """
        scores = {} # item_id -> score
        items = {} # item_id -> item object

        for results in search_results_list:
            for rank, item in enumerate(results):
                # We assume item has an 'id' attribute or key
                # Handle dict or object
                item_id = str(item.get("id")) if isinstance(item, dict) else str(item.id)

                if item_id not in scores:
                    scores[item_id] = 0.0
                    items[item_id] = item

                scores[item_id] += 1.0 / (k + rank + 1)

        # Sort by score desc
        sorted_results = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [(items[item_id], score) for item_id, score in sorted_results]

    async def rerank(
        self,
        query: str,
        candidates: list[Any],
        top_k: int = 5,
        instruct: str | None = None,
    ) -> list[Any]:
        """
        Rerank candidates based on query using remote API.

        Args:
            query: Search query text
            candidates: List of candidate documents (dict or object)
            top_k: Number of top results to return
            instruct: Optional instruction for reranker (e.g., task-specific prompt)

        Returns:
            List[Any]: Reranked candidates (top_k items)
        """
        if not candidates:
            return []

        documents, valid_candidates = self._extract_documents(candidates)
        if not documents:
            return candidates[:top_k]

        try:
            if self.provider == "dashscope":
                indices = await self._dashscope_rerank(query, documents, top_k, instruct=instruct)
            elif self.provider == "siliconflow":
                indices = await self._siliconflow_rerank(query, documents, top_k, instruct=instruct)
            else:
                raise ValueError(f"Unsupported rerank provider: {self.provider}")

            return [valid_candidates[i] for i in indices if i < len(valid_candidates)]
        except Exception as e:
            logger.error(f"Error during reranking: {e}")
            return candidates[:top_k]

    def _extract_documents(self, candidates: list[Any]) -> tuple[list[str], list[Any]]:
        documents: list[str] = []
        valid_candidates: list[Any] = []

        for c in candidates:
            if isinstance(c, dict):
                text = c.get("content", "") or c.get("description", "") or c.get("name", "")
            else:
                text = getattr(c, "content", "") or getattr(c, "description", "") or getattr(c, "name", "")

            if text:
                documents.append(text)
                valid_candidates.append(c)

        return documents, valid_candidates

    async def _dashscope_rerank(
        self,
        query: str,
        documents: list[str],
        top_k: int,
        instruct: str | None = None,
    ) -> list[int]:
        def _call():
            dashscope.api_key = self.dashscope_api_key
            if self.dashscope_base_url:
                dashscope.base_http_api_url = self.dashscope_base_url

            payload = {
                "model": self.dashscope_model,
                "query": query,
                "documents": documents,
                "top_n": top_k,
            }
            if instruct:
                payload["instruct"] = instruct
            return dashscope.TextReRank.call(**payload)

        resp = await asyncio.to_thread(_call)
        if resp.status_code != HTTPStatus.OK:
            raise RuntimeError(f"DashScope rerank failed: {resp.code} {resp.message}")

        results = resp.output.get("results", [])
        if not results:
            return list(range(min(top_k, len(documents))))

        return [item["index"] for item in results]

    async def _siliconflow_rerank(
        self,
        query: str,
        documents: list[str],
        top_k: int,
        instruct: str | None = None,
    ) -> list[int]:
        # SiliconFlow rerank endpoint: {base_url}/rerank
        # With default base_url=https://api.siliconflow.cn/v1, this produces:
        # https://api.siliconflow.cn/v1/rerank
        base_url = self.siliconflow_base_url.rstrip("/")
        url = base_url if base_url.endswith("/rerank") else f"{base_url}/rerank"

        payload = {
            "model": self.siliconflow_model,
            "query": query,
            "documents": documents,
            "top_n": top_k,
            "return_documents": False,
        }
        if instruct:
            payload["instruct"] = instruct  # SiliconFlow uses "instruct", not "instruction"

        async with httpx.AsyncClient(timeout=30.0) as client:
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

        results = data.get("results", [])
        if not results:
            return list(range(min(top_k, len(documents))))

        return [item["index"] for item in results]

rerank_service = RerankService()
