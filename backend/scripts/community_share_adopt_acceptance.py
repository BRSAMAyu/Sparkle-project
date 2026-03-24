#!/usr/bin/env python3
"""Acceptance for community share/adopt closures across private chat and group resources."""

from __future__ import annotations

import asyncio
import json
import os
import uuid

import requests

from app.core.security import create_access_token, get_password_hash
from app.db.session import AsyncSessionLocal
from app.models.task import Task
from app.models.plan import Plan
from app.models.user import User

GATEWAY_BASE = os.getenv("GATEWAY_BASE_URL", "http://127.0.0.1:8080/api/v1")
PASSWORD = os.getenv("COMMUNITY_SHARE_TEST_PASSWORD", "Temp123456")


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
        raise RuntimeError(f"{method} {path} -> {response.status_code}: {response.text[:1200]}")
    if not response.content:
        return None
    return response.json()


def _extract_id(payload: object, *keys: str) -> str | None:
    if isinstance(payload, dict):
        for key in keys:
            value = payload.get(key)
            if isinstance(value, str) and value:
                return value
        data = payload.get("data")
        if isinstance(data, dict):
            for key in keys:
                value = data.get(key)
                if isinstance(value, str) and value:
                    return value
    return None


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


async def _ensure_task_owner(task_id: str, user_id: str) -> bool:
    async with AsyncSessionLocal() as db:
        task = await db.get(Task, uuid.UUID(task_id))
        return bool(task and str(task.user_id) == user_id)


async def _ensure_plan_owner(plan_id: str, user_id: str) -> bool:
    async with AsyncSessionLocal() as db:
        plan = await db.get(Plan, uuid.UUID(plan_id))
        return bool(plan and str(plan.user_id) == user_id)


async def main() -> int:
    owner = await _create_test_user("share_owner")
    recipient = await _create_test_user("share_recipient")

    session = requests.Session()

    try:
        friend_req = _request_json(
            session,
            "POST",
            "/community/friends/request",
            token=owner["token"],
            json={"target_user_id": recipient["id"], "message": "share-adopt acceptance"},
        )
        friendship_id = _extract_id(friend_req, "friendship_id")
        if not friendship_id:
            return _fail("friend request missing friendship_id", extra=friend_req)

        _request_json(
            session,
            "POST",
            "/community/friends/respond",
            token=recipient["token"],
            json={"friendship_id": friendship_id, "accept": True},
        )

        plan_payload = _request_json(
            session,
            "POST",
            "/plans",
            token=owner["token"],
            expected=201,
            json={
                "name": f"分享验收计划-{uuid.uuid4().hex[:6]}",
                "type": "growth",
                "description": "验证计划卡分享与采纳闭环",
                "subject": "系统联动",
                "daily_available_minutes": 35,
                "total_estimated_hours": 12,
                "priority": "normal",
                "plan_stage": "daily",
            },
        )
        plan_id = _extract_id(plan_payload, "id")
        if not plan_id:
            return _fail("plan create missing id", extra=plan_payload)

        task_payload = _request_json(
            session,
            "POST",
            "/tasks",
            token=owner["token"],
            json={
                "title": f"分享验收任务-{uuid.uuid4().hex[:6]}",
                "type": "learning",
                "plan_id": plan_id,
                "estimated_minutes": 25,
                "difficulty": 2,
                "energy_cost": 2,
                "tags": ["share", "acceptance"],
            },
        )
        task_id = _extract_id(task_payload, "id")
        if not task_id:
            return _fail("task create missing id", extra=task_payload)

        group_payload = _request_json(
            session,
            "POST",
            "/community/groups",
            token=owner["token"],
            json={
                "name": f"分享采纳验收-{uuid.uuid4().hex[:6]}",
                "description": "group share/adopt acceptance",
                "type": "squad",
                "focus_tags": ["share", "plan", "task"],
                "max_members": 8,
                "is_public": True,
                "join_requires_approval": False,
            },
        )
        group_id = _extract_id(group_payload, "id")
        if not group_id:
            return _fail("group create missing id", extra=group_payload)

        _request_json(
            session,
            "POST",
            f"/community/groups/{group_id}/join",
            token=recipient["token"],
        )

        plan_group_share = _request_json(
            session,
            "POST",
            "/community/share",
            token=owner["token"],
            json={
                "resource_type": "plan",
                "resource_id": plan_id,
                "target_group_id": group_id,
                "permission": "view",
                "comment": "group share plan",
            },
        )
        task_group_share = _request_json(
            session,
            "POST",
            "/community/share",
            token=owner["token"],
            json={
                "resource_type": "task",
                "resource_id": task_id,
                "target_group_id": group_id,
                "permission": "view",
                "comment": "group share task",
            },
        )
        group_resources = _request_json(
            session,
            "GET",
            f"/community/groups/{group_id}/resources",
            token=recipient["token"],
        )
        resource_types = {item.get("resource_type") for item in group_resources if isinstance(item, dict)}
        if not {"plan", "task"}.issubset(resource_types):
            return _fail("group resources missing plan/task", extra=group_resources)

        plan_private_share = _request_json(
            session,
            "POST",
            "/community/share",
            token=owner["token"],
            json={
                "resource_type": "plan",
                "resource_id": plan_id,
                "target_user_id": recipient["id"],
                "permission": "view",
                "comment": "private share plan",
            },
        )
        task_private_share = _request_json(
            session,
            "POST",
            "/community/share",
            token=owner["token"],
            json={
                "resource_type": "task",
                "resource_id": task_id,
                "target_user_id": recipient["id"],
                "permission": "view",
                "comment": "private share task",
            },
        )

        private_history = _request_json(
            session,
            "GET",
            f"/community/friends/{owner['id']}/messages",
            token=recipient["token"],
        )
        plan_shared_resource_id = _extract_id(plan_private_share, "id")
        task_shared_resource_id = _extract_id(task_private_share, "id")
        if not plan_shared_resource_id or not task_shared_resource_id:
            return _fail(
                "private share response missing shared_resource ids",
                extra={"plan": plan_private_share, "task": task_private_share},
            )
        history_share_ids = {
            str((item.get("content_data") or {}).get("shared_resource_id"))
            for item in private_history
            if isinstance(item, dict)
        }
        if plan_shared_resource_id not in history_share_ids or task_shared_resource_id not in history_share_ids:
            return _fail("private history missing shared messages", extra=private_history)

        adopted_plan = _request_json(
            session,
            "POST",
            f"/community/shared-resources/{plan_shared_resource_id}/adopt",
            token=recipient["token"],
        )
        adopted_task = _request_json(
            session,
            "POST",
            f"/community/shared-resources/{task_shared_resource_id}/adopt",
            token=recipient["token"],
        )
        new_plan_id = _extract_id(adopted_plan, "new_resource_id")
        new_task_id = _extract_id(adopted_task, "new_resource_id")
        if not new_plan_id or not new_task_id:
            return _fail("adopt response missing new_resource_id", extra={"plan": adopted_plan, "task": adopted_task})

        if not await _ensure_plan_owner(new_plan_id, recipient["id"]):
            return _fail("adopted plan not owned by recipient", extra=adopted_plan)
        if not await _ensure_task_owner(new_task_id, recipient["id"]):
            return _fail("adopted task not owned by recipient", extra=adopted_task)

        recipient_plan_detail = _request_json(session, "GET", f"/plans/{new_plan_id}", token=recipient["token"])
        recipient_task_detail = _request_json(session, "GET", f"/tasks/{new_task_id}", token=recipient["token"])
        if _extract_id(recipient_plan_detail, "id") != new_plan_id:
            return _fail("recipient cannot open adopted plan", extra=recipient_plan_detail)
        if _extract_id(recipient_task_detail, "id") != new_task_id:
            return _fail("recipient cannot open adopted task", extra=recipient_task_detail)

        print(
            json.dumps(
                {
                    "status": "ALL_OK",
                    "group_id": group_id,
                    "group_shared_types": sorted(resource_types),
                    "plan_shared_resource_id": plan_shared_resource_id,
                    "task_shared_resource_id": task_shared_resource_id,
                    "adopted_plan_id": new_plan_id,
                    "adopted_task_id": new_task_id,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    except RuntimeError as exc:
        return _fail("community share/adopt acceptance", extra={"error": str(exc)})


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
