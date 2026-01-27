#!/usr/bin/env python3
"""
Print effective config and verify DB/Redis connectivity.
"""
import asyncio
import os
import sys
from urllib.parse import urlparse

import asyncpg
import redis

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.config import settings
from app.config.settings import to_sync_database_url


def _redact_url(raw_url: str) -> str:
    if not raw_url:
        return ""
    parsed = urlparse(raw_url)
    if not parsed.username and not parsed.password:
        return raw_url
    username = parsed.username or ""
    netloc = f"{username}:***@{parsed.hostname}"
    if parsed.port:
        netloc = f"{netloc}:{parsed.port}"
    return parsed._replace(netloc=netloc).geturl()


async def _check_postgres() -> None:
    conn = await asyncpg.connect(to_sync_database_url(settings.DATABASE_URL))
    try:
        value = await conn.fetchval("SELECT 1")
    finally:
        await conn.close()
    if value != 1:
        raise RuntimeError("unexpected PostgreSQL SELECT 1 result")


def _check_redis() -> None:
    client = redis.Redis.from_url(settings.REDIS_URL)
    if not client.ping():
        raise RuntimeError("Redis PING failed")


def main() -> int:
    print("Effective config (redacted):")
    print(f"  DATABASE_URL={_redact_url(settings.DATABASE_URL)}")
    print(f"  REDIS_URL={_redact_url(settings.REDIS_URL)}")
    print(f"  POSTGRES_HOST={settings.POSTGRES_HOST}")
    print(f"  POSTGRES_PORT={settings.POSTGRES_PORT}")
    print(f"  POSTGRES_DB={settings.POSTGRES_DB}")
    print(f"  REDIS_HOST={settings.REDIS_HOST}")
    print(f"  REDIS_PORT={settings.REDIS_PORT}")

    asyncio.run(_check_postgres())
    _check_redis()

    print("Connectivity: postgres=ok redis=ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
