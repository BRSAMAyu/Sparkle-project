#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MEMORY_SERVICE = REPO_ROOT / "backend/app/services/memory_service.py"


def main() -> int:
    text = MEMORY_SERVICE.read_text(encoding="utf-8")
    list_recent_anchor = "async def list_recent_episodic("
    start = text.find(list_recent_anchor)
    if start < 0:
        print("[Rule Z / episodic_user_scope] FAIL missing list_recent_episodic")
        return 1

    end = text.find("\n    async def ", start + len(list_recent_anchor))
    if end < 0:
        end = len(text)
    body = text[start:end]

    required_tokens = (
        "select(EpisodicMemory).where(",
        "EpisodicMemory.user_id == user_id",
    )
    missing = [token for token in required_tokens if token not in body]
    if missing:
        print("[Rule Z / episodic_user_scope] FAIL")
        for token in missing:
            print(f"missing token: {token}")
        return 1

    print("[Rule Z / episodic_user_scope] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
