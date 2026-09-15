#!/usr/bin/env python3
"""Security acceptance checks for local gateway/API."""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.core.security import create_access_token, get_password_hash
from app.db.session import AsyncSessionLocal
from app.models.task import TaskType
from app.models.user import User
from scripts._acceptance_common import BASE_URL, REQUEST_TIMEOUT_SECONDS, assert_status


PASSWORD = os.getenv("LOCAL_SMOKE_PASSWORD", "Chat123456")
ROOT = Path(__file__).resolve().parents[2]


async def _create_user(prefix: str) -> dict[str, str]:
    async with AsyncSessionLocal() as db:
        suffix = uuid.uuid4().hex[:10]
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
    summary: dict[str, object] = {}

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as client:
        cors_resp = await client.options(
            f"{BASE_URL}/tasks",
            headers={
                "Origin": "http://evil.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        summary["SEC-03_status"] = cors_resp.status_code
        summary["SEC-03_allow_origin"] = cors_resp.headers.get("access-control-allow-origin")
        if cors_resp.headers.get("access-control-allow-origin") == "http://evil.com":
            raise RuntimeError("SEC-03 failed: evil origin allowed")
        summary["SEC-03"] = "PASS"

        internal_resp = await client.post(
            "http://127.0.0.1:8080/internal/interventions/push",
            json={"user_id": str(uuid.uuid4()), "message": "unauthorized"},
        )
        if internal_resp.status_code not in (401, 403):
            raise RuntimeError(f"SEC-04 failed: unexpected internal auth status {internal_resp.status_code}")
        summary["SEC-04"] = f"PASS_{internal_resp.status_code}"

        user_a = await _create_user("sec_a")
        user_b = await _create_user("sec_b")

        headers_a = {"Authorization": f"Bearer {user_a['token']}"}
        headers_b = {"Authorization": f"Bearer {user_b['token']}"}

        task_b = await client.post(
            f"{BASE_URL}/tasks",
            headers=headers_b,
            json={
                "title": "security task B",
                "type": TaskType.PLANNING.value,
                "estimated_minutes": 15,
                "priority": 1,
            },
        )
        assert_status(task_b, 200, "create task B")
        task_b_id = task_b.json()["data"]["id"]

        cross_access = await client.get(f"{BASE_URL}/tasks/{task_b_id}", headers=headers_a)
        if cross_access.status_code not in (403, 404):
            raise RuntimeError(f"SEC-05 failed: user A accessed user B task with {cross_access.status_code}")
        summary["SEC-05"] = "PASS"

        sql_payload = "test'; DROP TABLE tasks;--"
        sql_task = await client.post(
            f"{BASE_URL}/tasks",
            headers=headers_a,
            json={
                "title": sql_payload,
                "type": TaskType.PLANNING.value,
                "estimated_minutes": 15,
            },
        )
        assert_status(sql_task, 200, "sql payload task create")
        fetched_sql = await client.get(f"{BASE_URL}/tasks/{sql_task.json()['data']['id']}", headers=headers_a)
        assert_status(fetched_sql, 200, "sql payload task fetch")
        if fetched_sql.json()["data"]["title"] != sql_payload:
            raise RuntimeError("SEC-06 failed: SQL payload mutated unexpectedly")
        summary["SEC-06"] = "PASS"

        xss_payload = "<script>alert(1)</script>"
        xss_task = await client.post(
            f"{BASE_URL}/tasks",
            headers=headers_a,
            json={
                "title": xss_payload,
                "type": TaskType.PLANNING.value,
                "estimated_minutes": 15,
            },
        )
        assert_status(xss_task, 200, "xss payload task create")
        fetched_xss = await client.get(f"{BASE_URL}/tasks/{xss_task.json()['data']['id']}", headers=headers_a)
        assert_status(fetched_xss, 200, "xss payload task fetch")
        if fetched_xss.json()["data"]["title"] != xss_payload:
            raise RuntimeError("SEC-07 failed: XSS payload mutated unexpectedly")
        summary["SEC-07"] = "PASS_STORED_AS_TEXT"

        oversize_prepare = await client.post(
            f"{BASE_URL}/files/upload/prepare",
            headers=headers_a,
            json={
                "filename": "huge.bin",
                "file_size": 60 * 1024 * 1024,
                "mime_type": "application/octet-stream",
            },
        )
        if oversize_prepare.status_code != 400:
            raise RuntimeError(f"SEC-08 failed: oversize file not rejected {oversize_prepare.status_code}")
        summary["SEC-08"] = "PASS"

        rate_limited = False
        for _ in range(120):
            resp = await client.post(f"{BASE_URL}/auth/login", json={"username": user_a["username"], "password": "wrong-password"})
            if resp.status_code == 429:
                rate_limited = True
                break
        if not rate_limited:
            raise RuntimeError("SEC-09 failed: auth login never rate limited")
        summary["SEC-09"] = "PASS"

    ignore_check = subprocess.run(
        ["bash", "-lc", "grep -n \"^\\.env\" .gitignore .dockerignore"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if ignore_check.returncode != 0:
        raise RuntimeError("SEC-10 failed: .env ignore rules missing in .gitignore/.dockerignore")
    summary["SEC-10"] = "PASS"

    print("ALL_OK")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
