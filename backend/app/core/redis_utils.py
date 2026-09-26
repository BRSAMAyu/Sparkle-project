"""
Redis connection helpers.
"""
from __future__ import annotations

from typing import Awaitable, TypeVar
from urllib.parse import urlparse

T = TypeVar("T")


def ensure_awaitable(result: Awaitable[T] | T) -> Awaitable[T]:
    """把 redis-py 命令返回值统一成可 await 的形态。

    redis-py 的 sync/async 命令共享一套注解，async 客户端的命令返回值类型被
    标成 ``Union[Awaitable[T], T]``；实际使用 ``redis.asyncio`` 客户端时运行期
    恒为 awaitable，这里显式收窄以便 ``await`` 通过类型检查。
    """
    if isinstance(result, Awaitable):
        return result

    async def _wrap() -> T:
        return result

    return _wrap()


PLACEHOLDER_PASSWORDS = {
    "<password>",
    "devpassword",
    "changeme",
    "REPLACE_ME",
    "password",
    "",
}


def normalize_redis_password(value: str | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        value = str(value)
    stripped = value.strip()
    if stripped == "":
        return None
    if stripped in PLACEHOLDER_PASSWORDS:
        return None
    return stripped


def resolve_redis_password(redis_url: str, redis_password: str | None) -> tuple[str | None, str]:
    try:
        parsed = urlparse(redis_url or "")
        if parsed.password is not None:
            url_password = normalize_redis_password(parsed.password)
            if url_password:
                return url_password, "url"
    except Exception:
        pass

    env_password = normalize_redis_password(redis_password)
    if env_password:
        return env_password, "env"

    return None, "default"


def format_redis_url_for_log(redis_url: str) -> str:
    try:
        parsed = urlparse(redis_url or "")
        scheme = parsed.scheme or "redis"
        host = parsed.hostname or ""
        port = f":{parsed.port}" if parsed.port else ""
        path = parsed.path or ""
        return f"{scheme}://{host}{port}{path}"
    except Exception:
        return redis_url
