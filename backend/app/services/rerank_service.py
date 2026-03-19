from __future__ import annotations
import asyncio
from http import HTTPStatus
from typing import Any

import httpx
from loguru import logger

from app.config import settings
from app.services.circuit_breaker import CircuitBreakerOpenException, circuit_breaker_service

try:
    import dashscope
except ImportError:  # pragma: no cover - optional dependency in some test/dev envs
    dashscope = None


class RerankService:
    """
    Rerank Service for RAG v2.0

    支持双供应商自动故障切换：
    - DashScope (阿里云百炼 SDK) - 使用 qwen3-rerank
    - SiliconFlow (HTTP API) - 使用 Qwen/Qwen3-Reranker-4B (同款模型)

    当主供应商失败时，自动切换到备用供应商

    Also supports:
    - RRF (Reciprocal Rank Fusion)
    """

    # 供应商优先级顺序
    PROVIDER_ORDER = ["dashscope", "siliconflow"]

    def __init__(self):
        self.primary_provider = settings.RERANK_PROVIDER
        self.backup_provider = settings.RERANK_BACKUP_PROVIDER
        self.dashscope_api_key = settings.DASHSCOPE_API_KEY
        self.dashscope_base_url = settings.DASHSCOPE_BASE_HTTP_API_URL
        self.dashscope_model = settings.DASHSCOPE_RERANK_MODEL  # qwen3-rerank

        self.siliconflow_api_key = settings.SILICONFLOW_API_KEY
        self.siliconflow_base_url = settings.SILICONFLOW_BASE_URL
        self.siliconflow_model = settings.SILICONFLOW_RERANK_MODEL  # Qwen/Qwen3-Reranker-4B

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

        支持双供应商自动故障切换：主供应商失败时自动切换到备用供应商。

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

        # 构建供应商尝试顺序：主供应商优先，备用供应商其次
        providers_to_try = self._get_provider_order()

        last_error = None
        for provider in providers_to_try:
            try:
                await circuit_breaker_service.check(f"rerank:{provider}")
                if provider == "dashscope":
                    if not self.dashscope_api_key:
                        continue
                    indices = await self._dashscope_rerank(query, documents, top_k, instruct=instruct)
                elif provider == "siliconflow":
                    if not self.siliconflow_api_key:
                        continue
                    indices = await self._siliconflow_rerank(query, documents, top_k, instruct=instruct)
                else:
                    continue

                await circuit_breaker_service.record_success(f"rerank:{provider}")
                return [valid_candidates[i] for i in indices if i < len(valid_candidates)]
            except CircuitBreakerOpenException as e:
                logger.warning(f"Rerank provider {provider} skipped because circuit breaker is open: {e}")
                last_error = e
                continue
            except Exception as e:
                logger.warning(f"Rerank provider {provider} failed: {e}")
                await circuit_breaker_service.record_failure(f"rerank:{provider}")
                last_error = e
                continue

        # 所有供应商都失败，返回原始顺序的前 top_k 个
        logger.error(f"All rerank providers failed. Last error: {last_error}")
        return candidates[:top_k]

    def _get_provider_order(self) -> list[str]:
        """获取供应商尝试顺序 (主供应商优先)"""
        order = [self.primary_provider, self.backup_provider]
        for provider in self.PROVIDER_ORDER:
            if provider not in order:
                order.append(provider)
        return order

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
        if dashscope is None:
            raise RuntimeError("dashscope package is required for dashscope rerank provider")

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
