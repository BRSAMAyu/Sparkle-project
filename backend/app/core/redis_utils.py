"""
Redis connection helpers.
"""
from typing import Optional, Tuple
from urllib.parse import urlparse

PLACEHOLDER_PASSWORDS = {
    "<password>",
    "devpassword",
    "changeme",
    "REPLACE_ME",
    "password",
    "",
}


def normalize_redis_password(value: Optional[str]) -> Optional[str]:
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


def resolve_redis_password(redis_url: str, redis_password: Optional[str]) -> Tuple[Optional[str], str]:
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
