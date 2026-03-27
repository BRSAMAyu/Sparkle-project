#!/usr/bin/env python3
"""Acceptance for community admin, moderation, security, and utility flows."""

from __future__ import annotations

import asyncio
import json
import os
import uuid

import requests

from app.core.security import create_access_token, get_password_hash
from app.db.session import AsyncSessionLocal
from app.models.user import User

GATEWAY_BASE = os.getenv("GATEWAY_BASE_URL", "http://127.0.0.1:8080/api/v1")
PASSWORD = os.getenv("COMMUNITY_ADMIN_TEST_PASSWORD", "Temp123456")


def _fail(message: str, *, extra: object | None = None) -> int:
    print(f"FAIL {message}")
    if extra is not None:
        print(json.dumps(extra, ensure_ascii=False, indent=2, default=str))
    return 1


def _request_json(
    session: requests.Session,
    method: str,
    path: str,
    *,
    token: str,
    expected: int | None = None,
    **kwargs,
) -> object:
    response = session.request(
        method,
        f"{GATEWAY_BASE}{path}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=90,
        **kwargs,
    )
    ok = response.status_code == expected if expected is not None else 200 <= response.status_code < 300
    if not ok:
        raise RuntimeError(
            json.dumps(
                {
                    "method": method,
                    "path": path,
                    "status": response.status_code,
                    "body": response.text[:1500],
                },
                ensure_ascii=False,
            )
        )
    if not response.content:
        return None
    return response.json()


async def _create_test_user(prefix: str) -> dict[str, str]:
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


async def main() -> int:
    owner = await _create_test_user("community_admin_owner")
    member = await _create_test_user("community_admin_member")
    outsider = await _create_test_user("community_admin_outsider")

    session = requests.Session()
    passed: list[str] = []

    try:
        friend_req = _request_json(
            session,
            "POST",
            "/community/friends/request",
            token=owner["token"],
            json={"target_user_id": member["id"], "message": "admin acceptance"},
        )
        friendship_id = friend_req["friendship_id"]
        _request_json(
            session,
            "POST",
            "/community/friends/respond",
            token=member["token"],
            json={"friendship_id": friendship_id, "accept": True},
        )
        _request_json(
            session,
            "DELETE",
            f"/community/friends/{friendship_id}",
            token=owner["token"],
        )
        friends_after_delete = _request_json(
            session,
            "GET",
            "/community/friends",
            token=owner["token"],
        )
        if any(item["friend"]["id"] == member["id"] for item in friends_after_delete):
            return _fail("friend delete ineffective", extra=friends_after_delete)
        passed.append("friend_delete")

        _request_json(
            session,
            "POST",
            "/community/users/block",
            token=owner["token"],
            json={"target_user_id": outsider["id"], "reason": "admin acceptance"},
        )
        blocked = _request_json(
            session,
            "GET",
            "/community/users/blocked",
            token=owner["token"],
        )
        if not any(item["blocked_user"]["id"] == outsider["id"] for item in blocked):
            return _fail("blocked list missing target", extra=blocked)
        _request_json(
            session,
            "DELETE",
            f"/community/users/block/{outsider['id']}",
            token=owner["token"],
        )
        blocked_after_unblock = _request_json(
            session,
            "GET",
            "/community/users/blocked",
            token=owner["token"],
        )
        if any(item["blocked_user"]["id"] == outsider["id"] for item in blocked_after_unblock):
            return _fail("unblock ineffective", extra=blocked_after_unblock)
        passed.append("block_unblock")

        _request_json(
            session,
            "PUT",
            "/community/users/privacy",
            token=owner["token"],
            json={"searchable_by": "friends"},
        )
        privacy = _request_json(
            session,
            "GET",
            "/community/users/privacy",
            token=owner["token"],
        )
        if privacy["searchable_by"] != "friends":
            return _fail("privacy update ineffective", extra=privacy)
        passed.append("privacy")

        group_one = _request_json(
            session,
            "POST",
            "/community/groups",
            token=owner["token"],
            json={
                "name": f"Admin QA One {uuid.uuid4().hex[:6]}",
                "description": "community admin acceptance one",
                "type": "squad",
                "focus_tags": ["admin", "qa"],
                "max_members": 20,
                "is_public": True,
                "join_requires_approval": False,
            },
        )
        group_two = _request_json(
            session,
            "POST",
            "/community/groups",
            token=owner["token"],
            json={
                "name": f"Admin QA Two {uuid.uuid4().hex[:6]}",
                "description": "community admin acceptance two",
                "type": "squad",
                "focus_tags": ["broadcast", "qa"],
                "max_members": 20,
                "is_public": True,
                "join_requires_approval": False,
            },
        )
        group_one_id = group_one["id"]
        group_two_id = group_two["id"]
        _request_json(
            session,
            "POST",
            f"/community/groups/{group_one_id}/join",
            token=member["token"],
        )
        _request_json(
            session,
            "POST",
            f"/community/groups/{group_two_id}/join",
            token=member["token"],
        )

        announcement = _request_json(
            session,
            "PUT",
            f"/community/groups/{group_one_id}/announcement",
            token=owner["token"],
            json={"announcement": "请先看群公告后发言"},
        )
        if announcement["announcement"] != "请先看群公告后发言":
            return _fail("announcement update ineffective", extra=announcement)
        moderation = _request_json(
            session,
            "PUT",
            f"/community/groups/{group_one_id}/moderation",
            token=owner["token"],
            json={
                "keyword_filters": ["spoiler", "spam"],
                "mute_all": False,
                "slow_mode_seconds": 15,
            },
        )
        if moderation["slow_mode_seconds"] != 15:
            return _fail("moderation update ineffective", extra=moderation)
        passed.append("announcement_moderation")

        mute = _request_json(
            session,
            "POST",
            f"/community/groups/{group_one_id}/members/{member['id']}/mute",
            token=owner["token"],
            json={"user_id": member["id"], "duration_minutes": 5, "reason": "cooldown"},
        )
        if not mute.get("mute_until"):
            return _fail("mute missing mute_until", extra=mute)
        _request_json(
            session,
            "DELETE",
            f"/community/groups/{group_one_id}/members/{member['id']}/mute",
            token=owner["token"],
        )
        warn = _request_json(
            session,
            "POST",
            f"/community/groups/{group_one_id}/members/{member['id']}/warn",
            token=owner["token"],
            json={"user_id": member["id"], "reason": "注意消息质量"},
        )
        if warn["warn_count"] < 1:
            return _fail("warn ineffective", extra=warn)
        passed.append("mute_unmute_warn")

        group_message = _request_json(
            session,
            "POST",
            f"/community/groups/{group_one_id}/messages",
            token=member["token"],
            json={"message_type": "text", "content": "hello admin route #weekly"},
        )
        message_id = group_message["id"]

        favorite = _request_json(
            session,
            "POST",
            "/community/favorites",
            token=owner["token"],
            json={
                "group_message_id": message_id,
                "note": "keep this",
                "tags": ["qa", "important"],
            },
        )
        favorites = _request_json(
            session,
            "GET",
            "/community/favorites",
            token=owner["token"],
        )
        if not any(item["id"] == favorite["id"] for item in favorites):
            return _fail("favorite list missing item", extra=favorites)
        _request_json(
            session,
            "DELETE",
            f"/community/favorites/{favorite['id']}",
            token=owner["token"],
        )
        passed.append("favorite_list_delete")

        report = _request_json(
            session,
            "POST",
            "/community/reports",
            token=owner["token"],
            json={
                "group_message_id": message_id,
                "reason": "spam",
                "description": "acceptance moderation flow",
            },
        )
        pending_reports = _request_json(
            session,
            "GET",
            f"/community/groups/{group_one_id}/reports",
            token=owner["token"],
        )
        if not any(item["id"] == report["id"] for item in pending_reports):
            return _fail("pending reports missing item", extra=pending_reports)
        reviewed = _request_json(
            session,
            "PUT",
            f"/community/reports/{report['id']}",
            token=owner["token"],
            json={"status": "actioned", "action_taken": "warn"},
        )
        if reviewed["status"] != "actioned":
            return _fail("report review ineffective", extra=reviewed)
        passed.append("report_review")

        forwarded = _request_json(
            session,
            "POST",
            "/community/forward",
            token=owner["token"],
            json={
                "source_message_id": message_id,
                "source_type": "group",
                "target_group_id": group_two_id,
                "comment": "forward acceptance",
            },
        )
        if not forwarded.get("message_id"):
            return _fail("forward missing message id", extra=forwarded)
        broadcast = _request_json(
            session,
            "POST",
            "/community/broadcast",
            token=owner["token"],
            json={
                "content": "admin acceptance broadcast",
                "target_group_ids": [group_one_id, group_two_id],
            },
        )
        if broadcast["delivered_count"] < 2:
            return _fail("broadcast delivered_count too low", extra=broadcast)
        passed.append("forward_broadcast")

        advanced_search = _request_json(
            session,
            "POST",
            f"/community/groups/{group_one_id}/messages/search/advanced",
            token=owner["token"],
            json={"keyword": "admin route", "page": 1, "page_size": 20},
        )
        if advanced_search["total"] < 1:
            return _fail("advanced search empty", extra=advanced_search)
        topics = _request_json(
            session,
            "GET",
            f"/community/groups/{group_one_id}/topics",
            token=owner["token"],
        )
        if "topics" not in topics:
            return _fail("topics payload invalid", extra=topics)
        passed.append("advanced_search_topics")

        _request_json(
            session,
            "POST",
            "/community/checkin",
            token=owner["token"],
            json={"group_id": group_one_id, "message": "owner checkin", "today_duration_minutes": 30},
        )
        flame = _request_json(
            session,
            "GET",
            f"/community/groups/{group_one_id}/flame",
            token=owner["token"],
        )
        if flame["group_id"] != group_one_id:
            return _fail("flame payload invalid", extra=flame)
        passed.append("checkin_flame")

        encryption = _request_json(
            session,
            "POST",
            "/community/encryption/keys",
            token=owner["token"],
            json={"public_key": "dGVzdF9wdWJsaWNfa2V5", "key_type": "x25519", "device_id": "acceptance-device"},
        )
        key_id = encryption["id"]
        keys = _request_json(
            session,
            "GET",
            f"/community/encryption/keys/{owner['id']}",
            token=member["token"],
        )
        if not any(item["id"] == key_id for item in keys):
            return _fail("public key fetch missing item", extra=keys)
        _request_json(
            session,
            "DELETE",
            f"/community/encryption/keys/{key_id}",
            token=owner["token"],
        )
        passed.append("encryption_key_lifecycle")

    except RuntimeError as exc:
        return _fail("request failed", extra=json.loads(str(exc)))

    print(
        json.dumps(
            {
                "status": "ALL_OK",
                "passed": passed,
                "group_one_id": group_one_id,
                "group_two_id": group_two_id,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
