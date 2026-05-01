"""
Manual XiaoMi MIMO smoke test.

This script intentionally reads credentials only from the environment and never
prints key material. It is skipped unless XIAOMI_MIMO_API_KEY is configured.
"""

from __future__ import annotations

import asyncio
import os


async def test_with_key(api_key: str) -> bool:
    """Use the configured API key for a minimal live provider check."""
    print("\n" + "=" * 60)
    print("Testing XiaoMi MIMO API key from environment")
    print("=" * 60)

    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=api_key, base_url="https://api.xiaomimimo.com/v1")
        response = await client.chat.completions.create(
            model=os.getenv("XIAOMI_CHAT_MODEL", "mimo-v2-flash"),
            messages=[{"role": "user", "content": "你好"}],
            max_tokens=20,
        )

        content = response.choices[0].message.content
        print("\nXiaoMi MIMO API test succeeded")
        print(f"   Response: {content}")
        print(f"   Token usage: {response.usage.total_tokens} tokens")
        return True

    except Exception as exc:
        error_str = str(exc)
        print("\nXiaoMi MIMO API test failed")
        print(f"   Error: {error_str}")

        if "401" in error_str or "Invalid API Key" in error_str:
            print("\n   The configured API key may be expired, revoked, malformed, or out of quota.")
        return False


async def main() -> int:
    api_key = os.getenv("XIAOMI_MIMO_API_KEY", "").strip()
    if not api_key:
        print("XIAOMI_MIMO_API_KEY is not set; skipping live provider test.")
        return 0
    return 0 if await test_with_key(api_key) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
