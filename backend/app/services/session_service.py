"""
Session management utilities.
Stores short-lived sessions in Redis for authentication flows.
"""
from __future__ import annotations

import json
from datetime import datetime, UTC
from uuid import uuid4

import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.cache import cache_service
from app.core.redis_utils import resolve_redis_password


async def _get_redis_client() -> tuple[redis.Redis, bool]:
    """Return a Redis client and whether it should be closed by the caller."""
    if cache_service.redis is not None:
        return cache_service.redis, False

    password, _ = resolve_redis_password(settings.REDIS_URL, settings.REDIS_PASSWORD)
    client = redis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
        password=password,
    )
    return client, True


async def create_session(
    db: AsyncSession,
    user_id: str,
    metadata: dict | None = None,
    expires_in: int = 3600,
) -> str:
    """Create a new session and persist it in Redis."""
    _ = db  # Reserved for future DB-backed session storage.
    session_id = str(uuid4())
    payload = {
        "user_id": user_id,
        "metadata": metadata or {},
        "created_at": datetime.now(UTC).isoformat(),
    }

    client, should_close = await _get_redis_client()
    try:
        await client.set(f"session:{session_id}", json.dumps(payload), ex=expires_in)
    finally:
        if should_close:
            if hasattr(client, "aclose"):
                await client.aclose()
            else:
                await client.close()

    return session_id
