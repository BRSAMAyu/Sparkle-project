#!/usr/bin/env python3
"""Gateway-backed acceptance for seed libraries, sharing, task links, and AI prompt inputs."""

from __future__ import annotations

import asyncio
import json
import os
import uuid

import requests

from app.core.security import create_access_token, get_password_hash
from app.db.session import AsyncSessionLocal
from app.models.user import User


AUTH_BASE = os.getenv("AUTH_BASE_URL", "http://127.0.0.1:8000/api/v1")
BASE_URL = os.getenv("GATEWAY_BASE_URL", "http://127.0.0.1:8080/api/v1")
PASSWORD = os.getenv("SEED_LIBRARY_TEST_PASSWORD", "Temp123456")
TIMEOUT = 60


def request_json(
    session: requests.Session,
    method: str,
    path: str,
    *,
    token: str,
    expected: int | None = None,
    **kwargs,
):
    response = session.request(
        method,
        f"{BASE_URL}{path}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=TIMEOUT,
        **kwargs,
    )
    ok = response.status_code == expected if expected is not None else 200 <= response.status_code < 300
    if not ok:
        raise RuntimeError(f"{method} {path} -> {response.status_code}: {response.text[:800]}")
    if not response.content:
        return None
    return response.json()


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


async def main() -> int:
    owner = await create_test_user("seed_owner")
    outsider = await create_test_user("seed_outsider")

    session = requests.Session()

    official_resp = request_json(
        session,
        "GET",
        "/seed-libraries",
        token=owner["token"],
        params={"is_official": "true", "page_size": 20},
    )
    official_libraries = official_resp["data"]
    if len(official_libraries) < 3:
        raise RuntimeError(f"Expected official libraries to be initialized, got: {json.dumps(official_resp, ensure_ascii=False)}")
    official_library_id = official_libraries[0]["id"]

    subscribe_resp = request_json(
        session,
        "POST",
        f"/seed-libraries/subscribe/{official_library_id}",
        token=owner["token"],
        json={"priority": 10, "notes": "official acceptance"},
    )
    if subscribe_resp["data"]["library_id"] != official_library_id:
        raise RuntimeError(f"Official library subscribe failed: {json.dumps(subscribe_resp, ensure_ascii=False)}")

    subscriptions = request_json(
        session,
        "GET",
        "/seed-libraries/subscriptions/me",
        token=owner["token"],
    )
    if not any(item["library_id"] == official_library_id for item in subscriptions["data"]):
        raise RuntimeError(f"Subscribed official library missing from subscriptions: {json.dumps(subscriptions, ensure_ascii=False)}")

    library_resp = request_json(
        session,
        "POST",
        "/seed-libraries",
        token=owner["token"],
        expected=201,
        json={
            "name": f"我的私有种子库-{uuid.uuid4().hex[:6]}",
            "description": "验收用户上传与 AI few-shot 的私有种子库",
            "category": "few_shot",
            "visibility": "private",
            "language": "zh",
            "tags": ["acceptance", "private"],
            "extra_metadata": {"source": "acceptance"},
        },
    )
    library_id = library_resp["data"]["id"]

    item_resp = request_json(
        session,
        "POST",
        f"/seed-libraries/{library_id}/items",
        token=owner["token"],
        expected=201,
        json={
            "item_type": "example",
            "title": "自定义 few-shot 示例",
            "subject": "验收学科",
            "difficulty_level": "beginner",
            "tags": ["acceptance", "few-shot"],
            "content_data": {
                "input": "什么是验收测试？",
                "output": "验收测试用于验证系统是否满足真实业务场景。",
                "explanation": "这是用于验证用户自有种子库能进入 AI prompt 的示例。",
            },
        },
    )
    item_id = item_resp["data"]["id"]

    import_resp = request_json(
        session,
        "POST",
        f"/seed-libraries/{library_id}/items/import",
        token=owner["token"],
        expected=201,
        json={
            "items": [
                {
                    "item_type": "example",
                    "title": "批量导入示例 A",
                    "subject": "验收学科",
                    "difficulty_level": "beginner",
                    "tags": ["imported"],
                    "content_data": {
                        "input": "A",
                        "output": "B",
                    },
                },
                {
                    "item_type": "template",
                    "title": "批量导入模板",
                    "subject": "验收学科",
                    "tags": ["template_key_acceptance"],
                    "content": "这是一个批量导入的模板。",
                },
            ],
        },
    )
    if import_resp["imported_count"] != 2 or import_resp["failed_count"] != 0:
        raise RuntimeError(f"Batch import failed: {json.dumps(import_resp, ensure_ascii=False)}")

    library_detail = request_json(
        session,
        "GET",
        f"/seed-libraries/{library_id}",
        token=owner["token"],
    )
    if library_detail["data"]["item_count"] < 3:
        raise RuntimeError(f"Library item count not updated: {json.dumps(library_detail, ensure_ascii=False)}")

    items_resp = request_json(
        session,
        "GET",
        f"/seed-libraries/{library_id}/items",
        token=owner["token"],
        params={"page_size": 20},
    )
    if len(items_resp["data"]) < 3:
        raise RuntimeError(f"Seed library items missing after upload/import: {json.dumps(items_resp, ensure_ascii=False)}")

    outsider_detail = session.get(
        f"{BASE_URL}/seed-libraries/{library_id}",
        headers={"Authorization": f"Bearer {outsider['token']}"},
        timeout=TIMEOUT,
    )
    if outsider_detail.status_code != 404:
        raise RuntimeError(f"Private library should be hidden from outsiders, got {outsider_detail.status_code}: {outsider_detail.text[:400]}")

    outsider_items = session.get(
        f"{BASE_URL}/seed-libraries/{library_id}/items",
        headers={"Authorization": f"Bearer {outsider['token']}"},
        timeout=TIMEOUT,
    )
    if outsider_items.status_code != 404:
        raise RuntimeError(f"Private library items should be hidden from outsiders, got {outsider_items.status_code}: {outsider_items.text[:400]}")

    query_resp = request_json(
        session,
        "POST",
        "/seed-libraries/query",
        token=owner["token"],
        json={
            "query": "验收测试",
            "categories": ["few_shot"],
            "subjects": ["验收学科"],
            "use_subscribed_only": True,
            "include_official": False,
            "use_semantic_search": False,
            "limit": 10,
        },
    )
    if not any(item["id"] == item_id for item in query_resp["items"]):
        raise RuntimeError(f"Owned private library was not included in subscribed-only query: {json.dumps(query_resp, ensure_ascii=False)}")

    few_shot_resp = request_json(
        session,
        "GET",
        "/seed-libraries/examples/few-shot",
        token=owner["token"],
        params={"subject": "验收学科", "count": 5},
    )
    if not any(example["input"] == "什么是验收测试？" for example in few_shot_resp):
        raise RuntimeError(f"Owned seed example did not surface through few-shot endpoint: {json.dumps(few_shot_resp, ensure_ascii=False)}")

    group_resp = request_json(
        session,
        "POST",
        "/community/groups",
        token=owner["token"],
        json={
            "name": f"Seed QA {uuid.uuid4().hex[:6]}",
            "description": "种子库验收群",
            "type": "squad",
            "focus_tags": ["seed", "qa"],
            "max_members": 8,
            "is_public": False,
            "join_requires_approval": False,
        },
    )
    group_id = group_resp["id"]

    share_library_resp = request_json(
        session,
        "POST",
        "/community/share",
        token=owner["token"],
        json={
            "resource_type": "seed_library",
            "resource_id": library_id,
            "target_group_id": group_id,
            "permission": "view",
            "comment": "分享我的验收种子库",
        },
    )
    if share_library_resp["seed_library_id"] != library_id:
        raise RuntimeError(f"Seed library share response mismatch: {json.dumps(share_library_resp, ensure_ascii=False)}")

    share_item_resp = request_json(
        session,
        "POST",
        "/community/share",
        token=owner["token"],
        json={
            "resource_type": "seed_item",
            "resource_id": item_id,
            "target_group_id": group_id,
            "permission": "view",
            "comment": "分享我的验收种子条目",
        },
    )
    if share_item_resp["seed_item_id"] != item_id:
        raise RuntimeError(f"Seed item share response mismatch: {json.dumps(share_item_resp, ensure_ascii=False)}")

    group_resources = request_json(
        session,
        "GET",
        f"/community/groups/{group_id}/resources",
        token=owner["token"],
    )
    if not any(item.get("seed_library_id") == library_id for item in group_resources):
        raise RuntimeError(f"Shared seed library missing from group resources: {json.dumps(group_resources, ensure_ascii=False)}")
    if not any(item.get("seed_item_id") == item_id for item in group_resources):
        raise RuntimeError(f"Shared seed item missing from group resources: {json.dumps(group_resources, ensure_ascii=False)}")

    task_resp = request_json(
        session,
        "POST",
        "/tasks",
        token=owner["token"],
        json={
            "title": "验证种子库任务挂接",
            "type": "learning",
            "estimated_minutes": 20,
            "difficulty": 2,
            "energy_cost": 2,
            "tags": ["seed", "acceptance"],
        },
    )
    task_id = task_resp["data"]["id"]

    task_library_link = request_json(
        session,
        "POST",
        f"/tasks/{task_id}/resources",
        token=owner["token"],
        json={
            "resource_type": "seed_library",
            "resource_id": library_id,
            "is_primary": True,
        },
    )
    task_item_link = request_json(
        session,
        "POST",
        f"/tasks/{task_id}/resources",
        token=owner["token"],
        json={
            "resource_type": "seed_item",
            "resource_id": item_id,
        },
    )
    if task_library_link["data"]["resource_type"] != "seed_library":
        raise RuntimeError(f"Task seed library link failed: {json.dumps(task_library_link, ensure_ascii=False)}")
    if task_item_link["data"]["resource_type"] != "seed_item":
        raise RuntimeError(f"Task seed item link failed: {json.dumps(task_item_link, ensure_ascii=False)}")

    task_resources = request_json(
        session,
        "GET",
        f"/tasks/{task_id}/resources",
        token=owner["token"],
    )
    resource_types = [item["resource_type"] for item in task_resources["data"]]
    if resource_types.count("seed_library") != 1 or resource_types.count("seed_item") != 1:
        raise RuntimeError(f"Task resources missing seed attachments: {json.dumps(task_resources, ensure_ascii=False)}")

    result = {
        "official_library_count": len(official_libraries),
        "subscription_count": len(subscriptions["data"]),
        "user_library_id": library_id,
        "user_item_id": item_id,
        "imported_count": import_resp["imported_count"],
        "group_shared_types": sorted(
            {
                item["resource_type"]
                for item in group_resources
                if item["resource_type"] in {"seed_library", "seed_item"}
            }
        ),
        "task_resource_types": resource_types,
        "few_shot_inputs": [example["input"] for example in few_shot_resp],
        "query_match_count": query_resp["total_count"],
        "privacy_block_status": {
            "detail_status": outsider_detail.status_code,
            "items_status": outsider_items.status_code,
        },
    }
    print("ALL_OK")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
