#!/usr/bin/env python3
"""Validate required local configuration before starting acceptance runs."""
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.config import settings


REQUIRED_CORE = {
    "DATABASE_URL": settings.DATABASE_URL,
    "REDIS_URL": settings.REDIS_URL,
    "INTERNAL_API_KEY": settings.INTERNAL_API_KEY,
}

REQUIRED_AI = {
    "DASHSCOPE_API_KEY": settings.DASHSCOPE_API_KEY,
    "DEEPSEEK_API_KEY": settings.DEEPSEEK_API_KEY,
    "ZHIPU_API_KEY": settings.ZHIPU_API_KEY,
    "SILICONFLOW_API_KEY": settings.SILICONFLOW_API_KEY,
    "XIAOMI_MIMO_API_KEY": settings.XIAOMI_MIMO_API_KEY,
    "XUNFEI_APP_ID": settings.XUNFEI_APP_ID,
    "XUNFEI_API_KEY": settings.XUNFEI_API_KEY,
    "XUNFEI_API_SECRET": settings.XUNFEI_API_SECRET,
}


def _check_group(name: str, values: dict[str, str]) -> list[str]:
    print(f"[{name}]")
    missing: list[str] = []
    for key, value in values.items():
        ok = bool((value or "").strip())
        print(f"  {'OK   ' if ok else 'MISS '} {key}")
        if not ok:
            missing.append(key)
    return missing


def main() -> int:
    core_missing = _check_group("core", REQUIRED_CORE)
    ai_missing = _check_group("ai", REQUIRED_AI)

    if core_missing or ai_missing:
        print("\nBlocking configuration gaps detected.")
        if core_missing:
            print(f"  core missing: {', '.join(core_missing)}")
        if ai_missing:
            print(f"  ai missing: {', '.join(ai_missing)}")
        return 1

    print("\nLocal configuration audit passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
