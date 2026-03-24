#!/usr/bin/env python3
"""End-to-end acceptance for galaxy, learning path, plans, tasks, and sharing."""

from __future__ import annotations

import asyncio
import json
import os
import uuid
from typing import Any

import requests
from sqlalchemy import func, select
from sqlalchemy.orm import aliased

from app.core.security import create_access_token, get_password_hash
from app.db.session import AsyncSessionLocal
from app.models.community import SharedResource
from app.models.galaxy import KnowledgeNode, NodeRelation
from app.models.plan import Plan
from app.models.task import Task
from app.models.user import User

GATEWAY_BASE = os.getenv("GATEWAY_BASE_URL", "http://127.0.0.1:8080/api/v1")
PASSWORD = os.getenv("GALAXY_TEST_PASSWORD", "Temp123456")


def fail(label: str, *, resp: requests.Response | None = None, extra: object | None = None) -> int:
    print(f"FAIL {label}")
    if resp is not None:
        print(f"STATUS {resp.status_code}")
        print(resp.text)
    if extra is not None:
        print(json.dumps(extra, ensure_ascii=False, default=str, indent=2))
    return 1


def request_json(
    session: requests.Session,
    method: str,
    url: str,
    *,
    headers: dict[str, str],
    label: str,
    expected: int | None = None,
    timeout: int = 120,
    **kwargs,
) -> Any:
    resp = session.request(method, url, headers=headers, timeout=timeout, **kwargs)
    ok = resp.status_code == expected if expected is not None else 200 <= resp.status_code < 300
    if not ok:
        raise RuntimeError(json.dumps({"label": label, "status": resp.status_code, "body": resp.text}, ensure_ascii=False))
    if not resp.content:
        return None
    return resp.json()


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


async def pick_learning_path_pair() -> dict[str, str]:
    async with AsyncSessionLocal() as db:
        source = aliased(KnowledgeNode)
        target = aliased(KnowledgeNode)
        row = (
            await db.execute(
                select(
                    source.id,
                    source.name,
                    target.id,
                    target.name,
                )
                .select_from(NodeRelation)
                .join(source, source.id == NodeRelation.source_node_id)
                .join(target, target.id == NodeRelation.target_node_id)
                .where(func.lower(NodeRelation.relation_type) == "prerequisite")
                .limit(1)
            )
        ).first()
        if not row:
            raise RuntimeError("No prerequisite relation found")
        return {
            "source_id": str(row[0]),
            "source_name": row[1],
            "target_id": str(row[2]),
            "target_name": row[3],
        }


async def ensure_shared_resource(shared_resource_id: str) -> bool:
    async with AsyncSessionLocal() as db:
        shared = await db.get(SharedResource, uuid.UUID(shared_resource_id))
        return shared is not None


async def ensure_plan_source(plan_id: str) -> dict[str, Any] | None:
    async with AsyncSessionLocal() as db:
        plan = await db.get(Plan, uuid.UUID(plan_id))
        if not plan:
            return None
        return {
            "source": plan.source,
            "source_metadata": plan.source_metadata,
        }


async def ensure_task_exists(task_id: str) -> bool:
    async with AsyncSessionLocal() as db:
        task = await db.get(Task, uuid.UUID(task_id))
        return task is not None


async def main() -> int:
    user = await create_test_user("galaxy_accept")
    pair = await pick_learning_path_pair()

    session = requests.Session()
    headers = {"Authorization": f"Bearer {user['token']}"}

    try:
        print(f"USING {pair['source_name']} -> {pair['target_name']}")

        graph = request_json(
            session,
            "GET",
            f"{GATEWAY_BASE}/galaxy/graph",
            headers=headers,
            label="galaxy graph",
        )
        if not graph.get("nodes"):
            return fail("galaxy graph empty", extra=graph)

        spark = request_json(
            session,
            "POST",
            f"{GATEWAY_BASE}/galaxy/node/{pair['source_id']}/spark",
            headers=headers,
            label="spark node",
        )
        spark_node_id = ((spark or {}).get("spark_event") or {}).get("node_id")
        if str(spark_node_id) != pair["source_id"]:
            return fail("spark node mismatch", extra=spark)

        detail = request_json(
            session,
            "GET",
            f"{GATEWAY_BASE}/galaxy/node/{pair['target_id']}",
            headers=headers,
            label="node detail",
        )
        if detail.get("node", {}).get("id") != pair["target_id"]:
            return fail("node detail mismatch", extra=detail)

        favorite = request_json(
            session,
            "POST",
            f"{GATEWAY_BASE}/galaxy/node/{pair['target_id']}/favorite",
            headers=headers,
            label="favorite node",
        )
        if not favorite.get("is_favorite"):
            return fail("favorite node did not enable", extra=favorite)

        decay = request_json(
            session,
            "POST",
            f"{GATEWAY_BASE}/galaxy/node/{pair['target_id']}/decay/pause",
            headers=headers,
            label="pause decay",
        )
        if not decay.get("decay_paused"):
            return fail("decay pause did not persist", extra=decay)

        position_update = request_json(
            session,
            "POST",
            f"{GATEWAY_BASE}/galaxy/nodes/positions",
            headers=headers,
            label="update positions",
            json={
                "updates": [
                    {"id": pair["source_id"], "x": 100.0, "y": 100.0},
                    {"id": pair["target_id"], "x": 200.0, "y": 200.0},
                ]
            },
        )
        if int(position_update.get("updated_count", 0)) < 2:
            return fail("node positions not updated", extra=position_update)

        viewport = request_json(
            session,
            "POST",
            f"{GATEWAY_BASE}/galaxy/nodes/viewport",
            headers=headers,
            label="viewport graph",
            json={"min_x": 50, "max_x": 250, "min_y": 50, "max_y": 250},
        )
        viewport_nodes = {str(node.get("id")) for node in viewport.get("nodes", [])}
        if pair["target_id"] not in viewport_nodes:
            return fail("viewport missing target node", extra=viewport)

        request_json(
            session,
            "POST",
            f"{GATEWAY_BASE}/galaxy/predict-next",
            headers=headers,
            label="predict next",
        )

        learning_path = request_json(
            session,
            "GET",
            f"{GATEWAY_BASE}/learning-paths/{pair['target_id']}",
            headers=headers,
            label="learning path",
        )
        path_ids = {str(item.get("id")) for item in learning_path}
        if pair["target_id"] not in path_ids or pair["source_id"] not in path_ids:
            return fail("learning path missing prerequisite chain", extra=learning_path)

        path_plan = request_json(
            session,
            "POST",
            f"{GATEWAY_BASE}/learning-paths/{pair['target_id']}/plan",
            headers=headers,
            label="generate learning path plan",
            timeout=180,
        )
        plan_id = path_plan.get("plan_id")
        if not plan_id:
            return fail("learning path plan missing plan_id", extra=path_plan)
        if not path_plan.get("tasks"):
            return fail("learning path plan returned no tasks", extra=path_plan)

        stored_plan = await ensure_plan_source(plan_id)
        if not stored_plan or stored_plan.get("source") != "learning_path":
            return fail("learning path plan source metadata missing", extra=stored_plan)

        progress = request_json(
            session,
            "GET",
            f"{GATEWAY_BASE}/plans/{plan_id}/learning-path-progress",
            headers=headers,
            label="learning path progress",
        )
        target_node = progress.get("target_node") or {}
        if target_node.get("id") != pair["target_id"] or not target_node.get("is_target"):
            return fail("learning path progress target node invalid", extra=progress)
        if "status" not in target_node:
            return fail("learning path progress target node missing status", extra=progress)

        generated_tasks = request_json(
            session,
            "POST",
            f"{GATEWAY_BASE}/plans/{plan_id}/generate-tasks",
            headers=headers,
            label="generate tasks for plan",
            json={"count": 2},
            timeout=180,
        )
        if not isinstance(generated_tasks, list) or not generated_tasks:
            return fail("plan generate-tasks returned empty", extra=generated_tasks)

        direct_task_resp = request_json(
            session,
            "POST",
            f"{GATEWAY_BASE}/tasks",
            headers=headers,
            label="create task with knowledge link",
            json={
                "title": f"掌握 {pair['target_name']}",
                "type": "learning",
                "plan_id": plan_id,
                "estimated_minutes": 30,
                "difficulty": 2,
                "energy_cost": 1,
                "knowledge_node_id": pair["target_id"],
                "tags": ["acceptance", "knowledge"],
            },
        )
        direct_task = (direct_task_resp or {}).get("data") or {}
        task_id = direct_task.get("id")
        if not task_id or direct_task.get("knowledge_node_id") != pair["target_id"]:
            return fail("created task missing knowledge link", extra=direct_task_resp)
        if not await ensure_task_exists(task_id):
            return fail("created task not persisted", extra=direct_task_resp)

        full_plan = request_json(
            session,
            "POST",
            f"{GATEWAY_BASE}/learning-paths/{pair['target_id']}/full-plan",
            headers=headers,
            label="generate full path plan",
            timeout=180,
        )
        full_plan_id = full_plan.get("plan_id")
        parent_task_id = full_plan.get("parent_task_id")
        if not full_plan_id or not parent_task_id or int(full_plan.get("subtask_count", 0)) <= 0:
            return fail("full path plan incomplete", extra=full_plan)

        group = request_json(
            session,
            "POST",
            f"{GATEWAY_BASE}/community/groups",
            headers=headers,
            label="create share group",
            json={
                "name": f"知识联动验收-{uuid.uuid4().hex[:6]}",
                "description": "galaxy-plan acceptance",
                "type": "squad",
                "focus_tags": ["knowledge", "plan"],
                "max_members": 10,
                "is_public": True,
                "join_requires_approval": False,
            },
        )
        group_id = group.get("id")
        if not group_id:
            return fail("group create missing id", extra=group)

        for resource_type, resource_id in (
            ("knowledge_node", pair["target_id"]),
            ("plan", plan_id),
            ("task", task_id),
        ):
            shared = request_json(
                session,
                "POST",
                f"{GATEWAY_BASE}/community/share",
                headers=headers,
                label=f"share {resource_type}",
                json={
                    "resource_type": resource_type,
                    "resource_id": resource_id,
                    "target_group_id": group_id,
                    "permission": "view",
                    "comment": f"share {resource_type}",
                },
            )
            shared_id = shared.get("id")
            if not shared_id or not await ensure_shared_resource(shared_id):
                return fail(f"shared resource not persisted: {resource_type}", extra=shared)

        group_resources = request_json(
            session,
            "GET",
            f"{GATEWAY_BASE}/community/groups/{group_id}/resources",
            headers=headers,
            label="group resources",
        )
        resource_types = {item.get("resource_type") for item in group_resources}
        if not {"knowledge_node", "plan", "task"}.issubset(resource_types):
            return fail("group resources missing shared items", extra=group_resources)

        print("ALL_OK")
        print(json.dumps(
            {
                "target_node": pair["target_name"],
                "plan_id": plan_id,
                "full_plan_id": full_plan_id,
                "task_id": task_id,
                "group_id": group_id,
                "shared_types": sorted(resource_types),
            },
            ensure_ascii=False,
            indent=2,
        ))
        return 0
    except RuntimeError as exc:
        payload = json.loads(str(exc))
        return fail(payload["label"], extra=payload)


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
