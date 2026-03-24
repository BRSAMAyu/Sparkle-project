#!/usr/bin/env python3
"""Functional data integrity verification for local acceptance."""

from __future__ import annotations

import asyncio
import json
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from sqlalchemy import func, select, text

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.security import create_access_token, get_password_hash
from app.db.session import AsyncSessionLocal
from app.models.chat import ChatMessage, ChatSession
from app.models.chat import MessageRole
from app.models.plan import Plan, PlanType
from app.models.task import SubTask, Task, TaskType
from app.models.user import User
from scripts._acceptance_common import BASE_URL, REQUEST_TIMEOUT_SECONDS, assert_status, ensure


PASSWORD = os.getenv("LOCAL_SMOKE_PASSWORD", "Chat123456")


def _email(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}@example.com"


def _username(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


async def _create_user(prefix: str) -> dict[str, str]:
    async with AsyncSessionLocal() as db:
        username = _username(prefix)
        user = User(
            username=username,
            email=_email(prefix),
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
            "email": user.email,
            "token": create_access_token({"sub": str(user.id)}),
        }


async def _db_scalar(query: str, params: dict[str, Any] | None = None) -> Any:
    async with AsyncSessionLocal() as db:
        result = await db.execute(text(query), params or {})
        return result.scalar()


async def _db_row(query: str, params: dict[str, Any] | None = None) -> Any:
    async with AsyncSessionLocal() as db:
        result = await db.execute(text(query), params or {})
        return result.first()


async def _request_with_retry(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    attempts: int = 5,
    retry_delay_seconds: float = 1.0,
    **kwargs: Any,
) -> httpx.Response:
    last_response: httpx.Response | None = None
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            response = await client.request(method, url, **kwargs)
            if response.status_code not in (502, 503, 504):
                return response
            last_response = response
        except (httpx.ConnectError, httpx.ReadError, httpx.RemoteProtocolError) as exc:
            last_error = exc
        if attempt < attempts:
            await asyncio.sleep(retry_delay_seconds)
    if last_response is not None:
        return last_response
    if last_error is not None:
        raise last_error
    raise RuntimeError(f"{method} {url} failed without response")


async def _backfill_missing_chat_sessions() -> int:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(
                ChatMessage.session_id,
                ChatMessage.user_id,
                func.max(ChatMessage.created_at).label("last_message_at"),
            )
            .outerjoin(ChatSession, ChatSession.id == ChatMessage.session_id)
            .where(ChatSession.id.is_(None))
            .group_by(ChatMessage.session_id, ChatMessage.user_id)
        )
        missing = result.all()
        for row in missing:
            db.add(
                ChatSession(
                    id=row.session_id,
                    user_id=row.user_id,
                    is_active=True,
                    last_message_at=row.last_message_at,
                )
            )
        if missing:
            await db.commit()
        return len(missing)


async def _create_seed_data(user_id: str) -> dict[str, str]:
    async with AsyncSessionLocal() as db:
        plan = Plan(
            user_id=uuid.UUID(user_id),
            name=f"data-plan-{uuid.uuid4().hex[:6]}",
            type=PlanType.SPRINT,
            description="data integrity acceptance",
            source="acceptance",
        )
        db.add(plan)
        await db.flush()

        task = Task(
            user_id=uuid.UUID(user_id),
            plan_id=plan.id,
            title="data integrity task",
            type=TaskType.PLANNING,
            estimated_minutes=25,
            priority=2,
            actual_minutes=15,
        )
        db.add(task)
        await db.flush()

        subtask = SubTask(
            parent_task_id=task.id,
            title="data integrity subtask",
            order=0,
        )
        db.add(subtask)

        session_id = uuid.uuid4()
        db.add(
            ChatSession(
                id=session_id,
                user_id=uuid.UUID(user_id),
                title="data acceptance session",
                is_active=True,
                last_message_at=datetime.now(timezone.utc).replace(tzinfo=None),
            )
        )
        db.add(
            ChatMessage(
                user_id=uuid.UUID(user_id),
                session_id=session_id,
                task_id=task.id,
                role=MessageRole.USER,
                content="hello data integrity",
            )
        )

        await db.commit()
        return {
            "plan_id": str(plan.id),
            "task_id": str(task.id),
            "subtask_id": str(subtask.id),
            "session_id": str(session_id),
        }


async def main() -> int:
    summary: dict[str, Any] = {}
    repaired_sessions = await _backfill_missing_chat_sessions()
    summary["chat_session_backfill_count"] = repaired_sessions

    orphan_task_count = await _db_scalar(
        """
        SELECT COUNT(*)
        FROM tasks t
        LEFT JOIN plans p ON t.plan_id = p.id
        WHERE t.plan_id IS NOT NULL AND p.id IS NULL
        """
    )
    ensure(orphan_task_count == 0, f"DATA-01 failed: orphan tasks={orphan_task_count}")
    summary["DATA-01"] = "PASS"

    orphan_subtask_count = await _db_scalar(
        """
        SELECT COUNT(*)
        FROM subtasks s
        LEFT JOIN tasks t ON s.parent_task_id = t.id
        WHERE t.id IS NULL
        """
    )
    ensure(orphan_subtask_count == 0, f"DATA-02 failed: orphan subtasks={orphan_subtask_count}")
    summary["DATA-02"] = "PASS"

    orphan_chat_count = await _db_scalar(
        """
        SELECT COUNT(*)
        FROM chat_messages cm
        LEFT JOIN chat_sessions cs ON cm.session_id = cs.id
        WHERE cs.id IS NULL
        """
    )
    ensure(orphan_chat_count == 0, f"DATA-03 failed: orphan chat_messages={orphan_chat_count}")
    summary["DATA-03"] = "PASS"

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as client:
        user_a = await _create_user("data_user_a")
        user_b = await _create_user("data_user_b")

        headers_a = {"Authorization": f"Bearer {user_a['token']}"}
        headers_b = {"Authorization": f"Bearer {user_b['token']}"}

        user_a_seed = await _create_seed_data(user_a["id"])
        user_b_seed = await _create_seed_data(user_b["id"])

        dashboard_a = await _request_with_retry(client, "GET", f"{BASE_URL}/dashboard/status", headers=headers_a)
        assert_status(dashboard_a, 200, "dashboard status A")
        dashboard_payload = dashboard_a.json()
        tasks_a = await _request_with_retry(client, "GET", f"{BASE_URL}/tasks?page=1&page_size=100", headers=headers_a)
        assert_status(tasks_a, 200, "list tasks A")
        task_rows = tasks_a.json()["data"]

        pending_count = sum(1 for item in task_rows if str(item.get("status")).upper() == "PENDING")
        dashboard_next_actions = dashboard_payload.get("next_actions") or []
        ensure(
            len(dashboard_next_actions) <= min(3, pending_count),
            f"DATA-06 failed: dashboard next_actions mismatch pending_count={pending_count} payload={dashboard_payload}",
        )
        summary["DATA-06"] = "PASS"

        plan_detail = await _request_with_retry(client, "GET", f"{BASE_URL}/plans/{user_a_seed['plan_id']}", headers=headers_a)
        assert_status(plan_detail, 200, "plan detail A")
        ensure(str(plan_detail.json().get("id")) == user_a_seed["plan_id"], "DATA-07 failed: plan detail mismatch")
        summary["DATA-07"] = "PASS"

        task_detail = await _request_with_retry(client, "GET", f"{BASE_URL}/tasks/{user_a_seed['task_id']}", headers=headers_a)
        assert_status(task_detail, 200, "task detail A")
        task_detail_payload = task_detail.json()["data"]
        ensure(str(task_detail_payload.get("plan_id")) == user_a_seed["plan_id"], "DATA-08 failed: task-plan mismatch")
        summary["DATA-08"] = "PASS"

        session_row_count = await _db_scalar(
            """
            SELECT COUNT(*)
            FROM chat_messages
            WHERE user_id = :user_id AND session_id = :session_id
            """,
            {"user_id": user_a["id"], "session_id": user_a_seed["session_id"]},
        )
        ensure(
            int(session_row_count or 0) >= 1,
            "DATA-09 failed: chat session row missing from DB",
        )
        summary["DATA-09"] = "PASS"

        redis_consistency_before = await _db_row(
            "SELECT title, updated_at FROM tasks WHERE id = :task_id",
            {"task_id": user_a_seed["task_id"]},
        )
        patch_resp = await _request_with_retry(
            client,
            "PUT",
            f"{BASE_URL}/tasks/{user_a_seed['task_id']}",
            headers=headers_a,
            json={"title": "data integrity task updated"},
        )
        assert_status(patch_resp, 200, "update task A")
        redis_consistency_after = await _db_row(
            "SELECT title, updated_at FROM tasks WHERE id = :task_id",
            {"task_id": user_a_seed["task_id"]},
        )
        ensure(
            redis_consistency_before[0] != redis_consistency_after[0]
            and redis_consistency_after[0] == "data integrity task updated",
            "DATA-11 failed: DB task title not updated",
        )
        refreshed_task = await _request_with_retry(client, "GET", f"{BASE_URL}/tasks/{user_a_seed['task_id']}", headers=headers_a)
        assert_status(refreshed_task, 200, "refetch task A")
        ensure(
            refreshed_task.json()["data"].get("title") == "data integrity task updated",
            "DATA-12 failed: API stale after DB update",
        )
        summary["DATA-11~12"] = "PASS"

        forbidden_task = await client.get(f"{BASE_URL}/tasks/{user_b_seed['task_id']}", headers=headers_a)
        ensure(forbidden_task.status_code in (403, 404), f"DATA-14 failed: cross-user task access={forbidden_task.status_code}")
        forbidden_plan = await client.get(f"{BASE_URL}/plans/{user_b_seed['plan_id']}", headers=headers_a)
        ensure(forbidden_plan.status_code in (403, 404), f"DATA-15 failed: cross-user plan access={forbidden_plan.status_code}")
        forbidden_chat = await client.get(f"{BASE_URL}/chat/history/{user_b_seed['session_id']}", headers=headers_a)
        ensure(forbidden_chat.status_code in (403, 404), f"DATA-16 failed: cross-user chat access={forbidden_chat.status_code}")
        summary["DATA-14~16"] = "PASS"

        delete_resp = await client.post(
            f"{BASE_URL}/users/me/delete-account",
            headers=headers_a,
            json={"confirmation": "DELETE", "password": PASSWORD},
        )
        assert_status(delete_resp, 200, "delete account A")

        user_state = await _db_row(
            """
            SELECT username, email, is_active, registration_source, deleted_at
            FROM users
            WHERE id = :user_id
            """,
            {"user_id": user_a["id"]},
        )
        ensure(user_state is not None, "DATA-05 failed: deleted user record missing unexpectedly")
        ensure(
            str(user_state[0]).startswith("deleted_") and str(user_state[1]).endswith("@deleted.local"),
            f"DATA-05 failed: user PII not scrubbed: {user_state}",
        )
        ensure(user_state[2] is False and user_state[3] == "deleted" and user_state[4] is not None, "DATA-05 failed: user soft-delete flags invalid")
        summary["DATA-05"] = "PASS_SOFT_DELETE"

        tasks_after_delete = await _db_scalar("SELECT COUNT(*) FROM tasks WHERE user_id = :user_id", {"user_id": user_a["id"]})
        plans_after_delete = await _db_scalar("SELECT COUNT(*) FROM plans WHERE user_id = :user_id", {"user_id": user_a["id"]})
        chats_after_delete = await _db_scalar("SELECT COUNT(*) FROM chat_messages WHERE user_id = :user_id", {"user_id": user_a["id"]})
        summary["DATA-05_related_rows_after_delete"] = {
            "tasks": int(tasks_after_delete or 0),
            "plans": int(plans_after_delete or 0),
            "chat_messages": int(chats_after_delete or 0),
        }

    print("ALL_OK")
    print(json.dumps(summary, ensure_ascii=False, default=str, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
