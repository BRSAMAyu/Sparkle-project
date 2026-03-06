#!/usr/bin/env python3
"""Community smoke: auth-backed lists/search plus gateway CQRS write/read."""
import os
import sys
import time
import uuid

import httpx

API_BASE = os.getenv("API_BASE_URL", "http://127.0.0.1:8000/api/v1")
GATEWAY_BASE = os.getenv("GATEWAY_BASE_URL", "http://127.0.0.1:8080/api/v1")
DEMO_USERNAME = os.getenv("LOCAL_SMOKE_USERNAME", "chat_test")
DEMO_PASSWORD = os.getenv("LOCAL_SMOKE_PASSWORD", "Chat123456")


def assert_status(resp: httpx.Response, expected: int, label: str) -> None:
    if resp.status_code != expected:
        raise RuntimeError(f"{label} failed: {resp.status_code} {resp.text}")


def main() -> int:
    with httpx.Client(timeout=20.0) as client:
        login = client.post(
            f"{API_BASE}/auth/login",
            json={"username": DEMO_USERNAME, "password": DEMO_PASSWORD},
        )
        assert_status(login, 200, "login")
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        friends = client.get(f"{API_BASE}/community/friends", headers=headers)
        assert_status(friends, 200, "community friends")
        friend_data = friends.json()
        print(f"friends ok: count={len(friend_data)}")

        groups = client.get(f"{API_BASE}/community/groups", headers=headers)
        assert_status(groups, 200, "community groups")
        group_data = groups.json()
        print(f"groups ok: count={len(group_data)}")

        search_users = client.get(
            f"{API_BASE}/community/users/search",
            headers=headers,
            params={"keyword": "spark"},
        )
        assert_status(search_users, 200, "community user search")
        print(f"user search ok: count={len(search_users.json())}")

        search_groups = client.get(
            f"{API_BASE}/community/groups/search",
            headers=headers,
            params={"keyword": "学习"},
        )
        assert_status(search_groups, 200, "community group search")
        print(f"group search ok: count={len(search_groups.json())}")

        post_marker = f"local-smoke-{uuid.uuid4().hex[:8]}"
        create_post = client.post(
            f"{GATEWAY_BASE}/community/posts",
            headers=headers,
            json={"content": post_marker, "topic": "local-acceptance", "image_urls": []},
        )
        assert_status(create_post, 201, "gateway create post")
        post_id = create_post.json()["id"]
        print(f"gateway post created: id={post_id}")

        found = False
        for _ in range(12):
            feed = client.get(f"{GATEWAY_BASE}/community/feed", params={"page": 1, "limit": 20})
            assert_status(feed, 200, "gateway feed")
            items = feed.json()
            if any((item.get("content") or "") == post_marker for item in items):
                found = True
                break
            time.sleep(1)
        if not found:
            raise RuntimeError("gateway feed did not reflect newly created post")

    print("Community smoke passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
