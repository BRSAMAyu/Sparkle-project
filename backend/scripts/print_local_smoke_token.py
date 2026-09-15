#!/usr/bin/env python3
"""Print a usable local smoke token, falling back to an ephemeral account on 429."""

from __future__ import annotations

import os
import uuid

import httpx


API_BASE = os.getenv("API_BASE_URL", "http://127.0.0.1:8000/api/v1")
USERNAME = os.getenv("LOCAL_SMOKE_USERNAME", "chat_test")
PASSWORD = os.getenv("LOCAL_SMOKE_PASSWORD", "Chat123456")


def main() -> int:
    with httpx.Client(timeout=20.0) as client:
        login = client.post(
            f"{API_BASE}/auth/login",
            json={"username": USERNAME, "password": PASSWORD},
        )
        if login.status_code == 200:
            print(login.json()["access_token"])
            return 0

        if login.status_code != 429:
            login.raise_for_status()

        username = f"local_smoke_{uuid.uuid4().hex[:10]}"
        register = client.post(
            f"{API_BASE}/auth/register",
            json={
                "username": username,
                "password": PASSWORD,
                "email": f"{username}@example.com",
                "accepted_tos": True,
                "accepted_privacy": True,
                "tos_version": "local-acceptance",
                "privacy_version": "local-acceptance",
                "agreed_locale": "zh-CN",
            },
        )
        register.raise_for_status()
        print(register.json()["access_token"])
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
