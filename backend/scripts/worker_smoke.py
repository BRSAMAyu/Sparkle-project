#!/usr/bin/env python3
"""Worker smoke for local stack: enqueue tasks, verify Redis/DB side effects."""
import asyncio
import json
import os
import sys
import time
import uuid

import redis.asyncio as redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.config import settings
from app.config.settings import to_sync_database_url
from app.core.redis_utils import resolve_redis_password
from app.db.url import to_async_database_url


async def _wait_for_summary(redis_client: redis.Redis, session_id: str, timeout: float = 45.0) -> None:
    deadline = time.time() + timeout
    key = f"summary:{session_id}"
    while time.time() < deadline:
        value = await redis_client.get(key)
        if value:
            print(f"summary worker ok: key={key}")
            return
        await asyncio.sleep(1)
    raise RuntimeError(f"summary worker timeout waiting for {key}")


async def _wait_for_billing(engine, request_id: str, timeout: float = 20.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        async with engine.connect() as conn:
            result = await conn.execute(
                text("SELECT COUNT(*) FROM token_usage WHERE request_id = :request_id"),
                {"request_id": request_id},
            )
            if result.scalar_one() == 1:
                print(f"billing worker ok: request_id={request_id}")
                return
        await asyncio.sleep(1)
    raise RuntimeError(f"billing worker timeout waiting for request_id={request_id}")


async def main() -> int:
    password, _ = resolve_redis_password(settings.REDIS_URL, settings.REDIS_PASSWORD)
    redis_client = redis.from_url(settings.REDIS_URL, password=password, decode_responses=True)
    engine = create_async_engine(to_async_database_url(settings.DATABASE_URL), pool_pre_ping=True)

    try:
        async with engine.connect() as conn:
            result = await conn.execute(
                text("SELECT id::text FROM users WHERE username = :username LIMIT 1"),
                {"username": os.getenv("LOCAL_SMOKE_USERNAME", "chat_test")},
            )
            user_id = result.scalar_one_or_none()
        if not user_id:
            raise RuntimeError("demo user not found; run `make fixture-init` first")

        session_id = f"smoke-session-{uuid.uuid4().hex[:8]}"
        request_id = f"smoke-req-{uuid.uuid4()}"

        await redis_client.rpush(
            "queue:summarization",
            json.dumps(
                {
                    "session_id": session_id,
                    "user_id": user_id,
                    "history": [
                        {"role": "user", "content": "请帮我总结线性代数复习重点"},
                        {"role": "assistant", "content": "重点包括向量空间、特征值、矩阵分解。"},
                    ],
                    "priority": "normal",
                    "timestamp": time.time(),
                }
            ),
        )

        await redis_client.rpush(
            "queue:billing",
            json.dumps(
                {
                    "user_id": user_id,
                    "session_id": session_id,
                    "request_id": request_id,
                    "model": "local-smoke-model",
                    "prompt_tokens": 11,
                    "completion_tokens": 7,
                    "total_tokens": 18,
                    "cost": 0.001,
                    "timestamp": time.time(),
                }
            ),
        )

        await asyncio.gather(
            _wait_for_summary(redis_client, session_id),
            _wait_for_billing(engine, request_id),
        )
    finally:
        await redis_client.aclose()
        await engine.dispose()

    print("Worker smoke passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
