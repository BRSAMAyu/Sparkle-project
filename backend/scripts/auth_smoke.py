#!/usr/bin/env python3
"""End-to-end auth and user-settings smoke test against the live local API."""
import os
import sys
import uuid

import httpx

API_BASE = os.getenv("API_BASE_URL", "http://127.0.0.1:8000/api/v1")
DEMO_USERNAME = os.getenv("LOCAL_SMOKE_USERNAME", "chat_test")
DEMO_PASSWORD = os.getenv("LOCAL_SMOKE_PASSWORD", "Chat123456")


def assert_status(resp: httpx.Response, expected: int, label: str) -> None:
    if resp.status_code != expected:
        raise RuntimeError(f"{label} failed: {resp.status_code} {resp.text}")


def _register_ephemeral_user(client: httpx.Client) -> tuple[str, str]:
    username = f"auth_smoke_{uuid.uuid4().hex[:10]}"
    resp = client.post(
        f"{API_BASE}/auth/register",
        json={
            "username": username,
            "password": DEMO_PASSWORD,
            "email": f"{username}@example.com",
            "accepted_tos": True,
            "accepted_privacy": True,
            "tos_version": "local-acceptance",
            "privacy_version": "local-acceptance",
            "agreed_locale": "zh-CN",
        },
    )
    assert_status(resp, 200, "register fallback")
    payload = resp.json()
    return payload["access_token"], username


def main() -> int:
    with httpx.Client(timeout=20.0) as client:
        login = client.post(
            f"{API_BASE}/auth/login",
            json={"username": DEMO_USERNAME, "password": DEMO_PASSWORD},
        )
        if login.status_code == 429:
            token, active_username = _register_ephemeral_user(client)
        else:
            assert_status(login, 200, "login")
            token = login.json()["access_token"]
            active_username = DEMO_USERNAME
        headers = {"Authorization": f"Bearer {token}"}

        me = client.get(f"{API_BASE}/users/me", headers=headers)
        assert_status(me, 200, "users/me")
        profile = me.json()
        print(f"login ok: user={profile['username']} id={profile['id']} source={active_username}")

        preference_payload = {
            "learning_depth": profile.get("depth_preference", 0.7),
            "curiosity_level": profile.get("curiosity_preference", 0.8),
        }
        update_pref = client.put(
            f"{API_BASE}/users/me/preferences",
            headers=headers,
            json=preference_payload,
        )
        assert_status(update_pref, 200, "users/me/preferences")

        push_pref = client.get(f"{API_BASE}/users/me/push-preference", headers=headers)
        assert_status(push_pref, 200, "users/me/push-preference")
        push_data = push_pref.json()
        push_update = client.put(
            f"{API_BASE}/users/me/push-preference",
            headers=headers,
            json={
                "enable_curiosity": push_data.get("enable_curiosity", True),
                "persona_type": push_data.get("persona_type", "coach"),
                "daily_cap": push_data.get("daily_cap", 5),
                "active_slots": push_data.get("active_slots", []),
                "timezone": push_data.get("timezone", "Asia/Shanghai"),
            },
        )
        assert_status(push_update, 200, "users/me/push-preference update")

    print("Auth and user settings smoke passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
