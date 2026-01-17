from typing import List, Dict, Any, Optional
import asyncio
from concurrent.futures import ThreadPoolExecutor
from loguru import logger
from app.config import settings

class RerankService:
    """
    Rerank Service for RAG v2.0
    Supports:
    - RRF (Reciprocal Rank Fusion)
    - Cross-Encoder Reranking (Local Model)
    """

    def __init__(self):
        self.model = None
        self.executor = ThreadPoolExecutor(max_workers=1)
        self._load_model_task = None
        self.enabled = settings.RERANKER_ENABLED
        self._load_failed = False

    async def ensure_model_loaded(self):
        """Ensure model is loaded (call this if auto-load failed)"""
        if not self.enabled or self._load_failed:
            return
        if not self.model and not self._load_model_task:
            self._load_model_task = asyncio.create_task(self._load_model())
        if self._load_model_task:
            await self._load_model_task

    async def _load_model(self):
        """Load Cross-Encoder model in background"""
        if not self.enabled or self._load_failed:
            return
        try:
            logger.info(f"⏳ Loading Reranker model ({settings.RERANK_MODEL})...")
            # Run in executor to avoid blocking loop
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(self.executor, self._init_transformer)
            logger.success("✅ Reranker model loaded.")
        except Exception as e:
            self._load_failed = True
            logger.warning(f"⚠️ Failed to load Reranker model, disabling reranker: {e}")

    def _init_transformer(self):
        from sentence_transformers import CrossEncoder
        # Use configured model (default: BAAI/bge-reranker-base)
        self.model = CrossEncoder(settings.RERANK_MODEL, max_length=512)

    def reciprocal_rank_fusion(self, search_results_list: List[List[Any]], k: int = 60) -> List[tuple]:
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
                if isinstance(item, dict):
                    item_id = str(item.get("id"))
                else:
                    item_id = str(item.id)
                    
                if item_id not in scores:
                    scores[item_id] = 0.0
                    items[item_id] = item
                
                scores[item_id] += 1.0 / (k + rank + 1)
        
        # Sort by score desc
        sorted_results = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [(items[item_id], score) for item_id, score in sorted_results]

    async def rerank(self, query: str, candidates: List[Any], top_k: int = 5) -> List[Any]:
        """
        Rerank candidates based on query using local Cross-Encoder.
        """
        if not candidates:
            return []

        if not self.enabled:
            return candidates[:top_k]

        if not self.model and not self._load_failed:
            await self.ensure_model_loaded()

        if not self.model:
            # If model not ready or failed, return original top_k
            logger.warning("Reranker model not ready, returning original order.")
            return candidates[:top_k]

        try:
            # Prepare pairs [query, doc_text]
            # Handle dict or object
            pairs = []
            valid_candidates = []
            
            for c in candidates:
                text = ""
                if isinstance(c, dict):
                    text = c.get('content', '') or c.get('description', '') or c.get('name', '')
                else:
                    text = getattr(c, 'content', '') or getattr(c, 'description', '') or getattr(c, 'name', '')
                
                if text:
                    pairs.append([query, text])
                    valid_candidates.append(c)
            
            if not pairs:
                return candidates[:top_k]

            # Run inference in executor
            loop = asyncio.get_running_loop()
            scores = await loop.run_in_executor(self.executor, lambda: self.model.predict(pairs))
            
            # Combine candidates with scores
            scored_candidates = list(zip(valid_candidates, scores))
            
            # Sort by score desc
            scored_candidates.sort(key=lambda x: x[1], reverse=True)
            
            # Return top_k items
            return [item for item, score in scored_candidates[:top_k]]
            
        except Exception as e:
            logger.error(f"Error during reranking: {e}")
            return candidates[:top_k]

rerank_service = RerankService()
