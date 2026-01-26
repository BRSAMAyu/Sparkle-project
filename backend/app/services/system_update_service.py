import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from loguru import logger

from app.core.cache import cache_service


class SystemUpdateService:
    KEY_PREFIX = "system_updates:"
    TTL_SECONDS = 7 * 24 * 60 * 60
    MAX_ITEMS = 200

    def __init__(self, redis_client=None):
        self.redis = redis_client or cache_service.redis

    async def enqueue(self, user_id: UUID | str, payload: Dict[str, Any]) -> None:
        if not self.redis:
            return
        key = f"{self.KEY_PREFIX}{user_id}"
        raw = json.dumps(payload, ensure_ascii=True, default=str)
        try:
            pipe = self.redis.pipeline()
            pipe.lpush(key, raw)
            pipe.ltrim(key, 0, self.MAX_ITEMS - 1)
            pipe.expire(key, self.TTL_SECONDS)
            await pipe.execute()
        except Exception as exc:
            logger.warning(f"SystemUpdate enqueue failed: {exc}")

    async def drain(self, user_id: UUID | str, limit: int = 20) -> List[Dict[str, Any]]:
        if not self.redis:
            return []
        key = f"{self.KEY_PREFIX}{user_id}"
        try:
            pipe = self.redis.pipeline()
            pipe.lrange(key, 0, max(limit - 1, 0))
            pipe.ltrim(key, limit, -1)
            result = await pipe.execute()
            raw_items = result[0] if result else []
        except Exception as exc:
            logger.warning(f"SystemUpdate drain failed: {exc}")
            return []

        updates: List[Dict[str, Any]] = []
        for raw in raw_items:
            try:
                updates.append(json.loads(raw))
            except json.JSONDecodeError:
                continue
        return updates

    async def list_updates(
        self,
        user_id: UUID | str,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        if not self.redis:
            return []
        key = f"{self.KEY_PREFIX}{user_id}"
        start = max(offset, 0)
        end = max(start + limit - 1, start)
        try:
            raw_items = await self.redis.lrange(key, start, end)
        except Exception as exc:
            logger.warning(f"SystemUpdate list failed: {exc}")
            return []

        updates: List[Dict[str, Any]] = []
        for raw in raw_items:
            try:
                updates.append(json.loads(raw))
            except json.JSONDecodeError:
                continue
        return updates


def build_system_update(
    *,
    update_type: str,
    category: str,
    title: str,
    description: str,
    priority: str = "low",
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "type": update_type,
        "category": category,
        "title": title,
        "description": description,
        "priority": priority,
        "metadata": metadata or {},
        "created_at": int(datetime.utcnow().timestamp()),
    }
