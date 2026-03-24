#!/usr/bin/env python3
"""End-to-end community acceptance against gateway-backed APIs."""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
import uuid

import requests

from app.core.security import create_access_token, get_password_hash
from app.db.session import AsyncSessionLocal
from app.models.user import User

GATEWAY_BASE = os.getenv("GATEWAY_BASE_URL", "http://127.0.0.1:8080/api/v1")
PASSWORD = os.getenv("COMMUNITY_TEST_PASSWORD", "Temp123456")


def fail(label: str, *, resp: requests.Response | None = None, extra: object | None = None) -> int:
    print(f"FAIL {label}")
    if resp is not None:
        print(f"STATUS {resp.status_code}")
        print(resp.text)
    if extra is not None:
        print(extra)
    return 1


async def create_test_user(prefix: str) -> dict[str, str]:
    async with AsyncSessionLocal() as db:
        suffix = uuid.uuid4().hex[:8]
        username = f"{prefix}_{suffix}"
        user = User(
            username=username,
            email=f"{username}@example.com",
            hashed_password=get_password_hash(PASSWORD),
            password_login_enabled=True,
            nickname=username,
            registration_source="email",
            is_active=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return {
            "id": str(user.id),
            "username": username,
            "token": create_access_token({"sub": str(user.id)}),
        }


def request_json(
    session: requests.Session,
    method: str,
    url: str,
    *,
    headers: dict[str, str],
    label: str,
    expected: int | None = None,
    **kwargs,
) -> object:
    resp = session.request(method, url, headers=headers, timeout=60, **kwargs)
    ok = resp.status_code == expected if expected is not None else 200 <= resp.status_code < 300
    if not ok:
        raise RuntimeError(json.dumps({"label": label, "status": resp.status_code, "body": resp.text}, ensure_ascii=False))
    if not resp.content:
        return None
    try:
        return resp.json()
    except ValueError:
        return resp.text


async def main() -> int:
    u1 = await create_test_user("community_a")
    u2 = await create_test_user("community_b")
    u3 = await create_test_user("community_c")

    session = requests.Session()
    h1 = {"Authorization": f"Bearer {u1['token']}"}
    h2 = {"Authorization": f"Bearer {u2['token']}"}
    h3 = {"Authorization": f"Bearer {u3['token']}"}

    try:
        friend_req = request_json(
            session,
            "POST",
            f"{GATEWAY_BASE}/community/friends/request",
            headers=h1,
            label="friend request",
            json={"target_user_id": u2["id"], "message": "hi"},
        )
        friendship_id = friend_req["friendship_id"]

        pending = request_json(
            session,
            "GET",
            f"{GATEWAY_BASE}/community/friends/pending",
            headers=h2,
            label="pending friends",
        )
        if not any(item["id"] == friendship_id for item in pending):
            return fail("pending friendship missing", extra=pending)
        if any("hashed_password" in json.dumps(item, ensure_ascii=False) for item in pending):
            return fail("pending friendship leaks password hash", extra=pending)

        request_json(
            session,
            "POST",
            f"{GATEWAY_BASE}/community/friends/respond",
            headers=h2,
            label="friend respond",
            json={"friendship_id": friendship_id, "accept": True},
        )
        friends = request_json(
            session,
            "GET",
            f"{GATEWAY_BASE}/community/friends",
            headers=h1,
            label="friends list",
        )
        if not any(item["friend"]["id"] == u2["id"] for item in friends):
            return fail("accepted friend not visible", extra=friends)

        private_msg = request_json(
            session,
            "POST",
            f"{GATEWAY_BASE}/community/messages",
            headers=h1,
            label="send private",
            json={
                "target_user_id": u2["id"],
                "message_type": "text",
                "content": "hello private",
            },
        )
        private_msg_id = private_msg["id"]
        history = request_json(
            session,
            "GET",
            f"{GATEWAY_BASE}/community/friends/{u2['id']}/messages",
            headers=h1,
            label="private history",
        )
        if not any(item["id"] == private_msg_id for item in history):
            return fail("private message missing from history", extra=history)
        request_json(
            session,
            "PATCH",
            f"{GATEWAY_BASE}/community/messages/{private_msg_id}",
            headers=h1,
            label="edit private",
            json={"content": "hello private edited"},
        )
        search = request_json(
            session,
            "GET",
            f"{GATEWAY_BASE}/community/friends/{u2['id']}/messages/search",
            headers=h1,
            label="search private",
            params={"keyword": "edited"},
        )
        if not any(item["id"] == private_msg_id for item in search):
            return fail("edited private message not searchable", extra=search)
        request_json(
            session,
            "POST",
            f"{GATEWAY_BASE}/community/messages/{private_msg_id}/reactions",
            headers=h2,
            label="private reaction",
            json={"emoji": "👍", "action": "add"},
        )
        request_json(
            session,
            "POST",
            f"{GATEWAY_BASE}/community/messages/{private_msg_id}/revoke",
            headers=h1,
            label="private revoke",
        )

        post = request_json(
            session,
            "POST",
            f"{GATEWAY_BASE}/community/posts",
            headers=h1,
            label="create post",
            expected=201,
            json={"content": f"community acceptance {uuid.uuid4().hex[:6]}", "topic": "qa"},
        )
        post_id = post["id"]
        feed_items = []
        for _ in range(12):
            feed_items = request_json(
                session,
                "GET",
                f"{GATEWAY_BASE}/community/feed",
                headers=h1,
                label="feed",
                params={"page": 1, "limit": 20},
            )
            if any(item["id"] == post_id for item in feed_items):
                break
            time.sleep(1)
        else:
            return fail("new post not visible in feed after polling", extra=feed_items)
        request_json(
            session,
            "POST",
            f"{GATEWAY_BASE}/community/posts/{post_id}/like",
            headers=h2,
            label="like post",
        )

        group = request_json(
            session,
            "POST",
            f"{GATEWAY_BASE}/community/groups",
            headers=h1,
            label="create group",
            json={
                "name": f"QA Squad {uuid.uuid4().hex[:6]}",
                "description": "community acceptance",
                "type": "squad",
                "focus_tags": ["qa", "community"],
                "max_members": 10,
                "is_public": True,
                "join_requires_approval": False,
            },
        )
        group_id = group["id"]

        request_json(
            session,
            "POST",
            f"{GATEWAY_BASE}/community/groups/{group_id}/join",
            headers=h2,
            label="join group u2",
        )
        request_json(
            session,
            "POST",
            f"{GATEWAY_BASE}/community/groups/{group_id}/join",
            headers=h3,
            label="join group u3",
        )
        members = request_json(
            session,
            "GET",
            f"{GATEWAY_BASE}/community/groups/{group_id}/members",
            headers=h1,
            label="group members",
        )
        member_ids = {item["user"]["id"] for item in members}
        if not {u1["id"], u2["id"], u3["id"]}.issubset(member_ids):
            return fail("group members incomplete", extra=members)

        request_json(
            session,
            "POST",
            f"{GATEWAY_BASE}/community/groups/{group_id}/members/{u2['id']}/promote",
            headers=h1,
            label="promote member",
        )
        members = request_json(
            session,
            "GET",
            f"{GATEWAY_BASE}/community/groups/{group_id}/members",
            headers=h1,
            label="group members after promote",
        )
        promoted_role = [item["role"] for item in members if item["user"]["id"] == u2["id"]][0]
        if promoted_role != "admin":
            return fail("promote member ineffective", extra=members)

        request_json(
            session,
            "POST",
            f"{GATEWAY_BASE}/community/groups/{group_id}/members/{u2['id']}/demote",
            headers=h1,
            label="demote member",
        )
        request_json(
            session,
            "POST",
            f"{GATEWAY_BASE}/community/groups/{group_id}/members/{u3['id']}/kick",
            headers=h1,
            label="kick member",
        )
        members = request_json(
            session,
            "GET",
            f"{GATEWAY_BASE}/community/groups/{group_id}/members",
            headers=h1,
            label="group members after kick",
        )
        if any(item["user"]["id"] == u3["id"] for item in members):
            return fail("kick member ineffective", extra=members)

        group_msg = request_json(
            session,
            "POST",
            f"{GATEWAY_BASE}/community/groups/{group_id}/messages",
            headers=h2,
            label="group message",
            json={"message_type": "text", "content": "hello group"},
        )
        group_msg_id = group_msg["id"]
        group_history = request_json(
            session,
            "GET",
            f"{GATEWAY_BASE}/community/groups/{group_id}/messages",
            headers=h1,
            label="group history",
        )
        if not any(item["id"] == group_msg_id for item in group_history):
            return fail("group message missing", extra=group_history)

        group_task = request_json(
            session,
            "POST",
            f"{GATEWAY_BASE}/community/groups/{group_id}/tasks",
            headers=h1,
            label="create group task",
            json={
                "title": "Task A",
                "description": "community acceptance",
                "tags": ["qa"],
                "estimated_minutes": 20,
                "difficulty": 2,
            },
        )
        group_task_id = group_task["id"]
        request_json(
            session,
            "POST",
            f"{GATEWAY_BASE}/community/tasks/{group_task_id}/claim",
            headers=h2,
            label="claim group task",
        )
        tasks = request_json(
            session,
            "GET",
            f"{GATEWAY_BASE}/community/groups/{group_id}/tasks",
            headers=h2,
            label="group tasks",
        )
        if not any(item["id"] == group_task_id for item in tasks):
            return fail("group task missing", extra=tasks)

        request_json(
            session,
            "POST",
            f"{GATEWAY_BASE}/community/groups/{group_id}/members/{u2['id']}/transfer-ownership",
            headers=h1,
            label="transfer ownership",
        )
        group_info = request_json(
            session,
            "GET",
            f"{GATEWAY_BASE}/community/groups/{group_id}",
            headers=h2,
            label="group info after transfer",
        )
        if group_info.get("my_role") != "owner":
            return fail("ownership transfer ineffective", extra=group_info)

        request_json(
            session,
            "POST",
            f"{GATEWAY_BASE}/community/groups/{group_id}/leave",
            headers=h1,
            label="leave group",
        )

        partnership = request_json(
            session,
            "POST",
            f"{GATEWAY_BASE}/accountability/request",
            headers=h1,
            label="accountability request",
            expected=201,
            json={
                "partner_id": u2["id"],
                "initiator_goal": "Study daily",
                "check_in_days": 1,
            },
        )
        partnership_id = partnership["id"]
        mine = request_json(
            session,
            "GET",
            f"{GATEWAY_BASE}/accountability/mine",
            headers=h2,
            label="accountability mine",
        )
        if not any(item["id"] == partnership_id for item in mine):
            return fail("accountability partnership missing", extra=mine)
        partnership = request_json(
            session,
            "POST",
            f"{GATEWAY_BASE}/accountability/{partnership_id}/respond",
            headers=h2,
            label="accountability respond",
            json={"accept": True, "partner_goal": "Review together"},
        )
        if partnership["status"] != "active":
            return fail("partnership not active", extra=partnership)

        checkin = request_json(
            session,
            "POST",
            f"{GATEWAY_BASE}/accountability/{partnership_id}/checkin",
            headers=h1,
            label="checkin 1",
            expected=201,
            json={"content": "done 45", "mood": 4, "minutes": 45},
        )
        request_json(
            session,
            "POST",
            f"{GATEWAY_BASE}/accountability/{partnership_id}/checkin",
            headers=h2,
            label="checkin 2",
            expected=201,
            json={"content": "done 30", "mood": 5, "minutes": 30},
        )
        request_json(
            session,
            "POST",
            f"{GATEWAY_BASE}/accountability/checkin/{checkin['id']}/like",
            headers=h2,
            label="checkin like",
        )
        request_json(
            session,
            "POST",
            f"{GATEWAY_BASE}/accountability/checkin/{checkin['id']}/encourage",
            headers=h2,
            label="checkin encourage",
            json={"message": "keep going"},
        )
        stats = request_json(
            session,
            "GET",
            f"{GATEWAY_BASE}/accountability/{partnership_id}/stats",
            headers=h1,
            label="accountability stats",
        )
        if stats["total_checkins"] < 2:
            return fail("accountability stats incorrect", extra=stats)
        request_json(
            session,
            "GET",
            f"{GATEWAY_BASE}/accountability/{partnership_id}/timeline",
            headers=h1,
            label="accountability timeline",
        )
        heatmap = request_json(
            session,
            "GET",
            f"{GATEWAY_BASE}/accountability/{partnership_id}/heatmap",
            headers=h1,
            label="accountability heatmap",
        )
        if heatmap["total_days"] < 1:
            return fail("accountability heatmap empty", extra=heatmap)
        request_json(
            session,
            "GET",
            f"{GATEWAY_BASE}/accountability/achievements",
            headers=h1,
            label="accountability achievements",
        )
        request_json(
            session,
            "GET",
            f"{GATEWAY_BASE}/accountability/{partnership_id}/achievements",
            headers=h1,
            label="partnership achievements",
        )
        end_resp = session.delete(
            f"{GATEWAY_BASE}/accountability/{partnership_id}",
            headers=h1,
            timeout=60,
        )
        if end_resp.status_code not in (200, 204):
            return fail("end partnership", resp=end_resp)
    except RuntimeError as exc:
        payload = json.loads(str(exc))
        return fail(payload["label"], extra=payload)

    print("ALL_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
