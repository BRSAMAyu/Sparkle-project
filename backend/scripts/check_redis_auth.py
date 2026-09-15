#!/usr/bin/env python3
"""
Redis auth sanity check.
"""
import os
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

import redis.asyncio as redis
from loguru import logger

from app.config import settings
from app.core.redis_utils import resolve_redis_password, format_redis_url_for_log


async def main() -> int:
    redis_url = os.getenv("REDIS_URL", settings.REDIS_URL)
    env_password = os.getenv("REDIS_PASSWORD", settings.REDIS_PASSWORD)
    resolved_password, source = resolve_redis_password(redis_url, env_password)

    logger.info(
        "Redis Auth Check: {}, Password={}, PasswordSource={}".format(
            format_redis_url_for_log(redis_url),
            "Yes" if resolved_password else "No",
            source,
        )
    )

    client = redis.from_url(redis_url, password=resolved_password, decode_responses=False)
    try:
        await client.ping()
        logger.info("Redis ping OK")
        return 0
    except Exception as exc:
        logger.error(f"Redis ping failed: {exc}")
        return 1
    finally:
        await client.close()


if __name__ == "__main__":
    import asyncio

    raise SystemExit(asyncio.run(main()))
