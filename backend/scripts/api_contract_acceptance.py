#!/usr/bin/env python3
"""API contract acceptance for REST/WS/gRPC-adjacent local checks."""

from __future__ import annotations

import json
import os
import re
import socket
import asyncio
from pathlib import Path
from typing import Any

import httpx

from app.core.security import create_access_token, get_password_hash
from app.db.session import AsyncSessionLocal
from app.models.user import User
from scripts._acceptance_common import BASE_URL, REQUEST_TIMEOUT_SECONDS, assert_status, create_client


ROOT = Path(__file__).resolve().parents[2]
MOBILE_ENDPOINTS = ROOT / "mobile/lib/core/network/api_endpoints.dart"


def _extract_endpoints() -> list[str]:
    content = MOBILE_ENDPOINTS.read_text(encoding="utf-8")
    return sorted(set(re.findall(r"= '(/[^']+)'", content)))


def _expect_error_shape(payload: Any, label: str) -> None:
    if not isinstance(payload, dict):
        raise RuntimeError(f"{label} failed: non-dict error payload {payload!r}")
    if not any(key in payload for key in ("detail", "error", "message")):
        raise RuntimeError(f"{label} failed: missing standard error keys {payload!r}")


async def _create_user() -> dict[str, str]:
    async with AsyncSessionLocal() as db:
        username = f"api_contract_{os.urandom(4).hex()}"
        password = os.getenv("LOCAL_SMOKE_PASSWORD", "Chat123456")
        user = User(
            username=username,
            email=f"{username}@example.com",
            hashed_password=get_password_hash(password),
            password_login_enabled=True,
            nickname=username,
            registration_source="email",
            is_active=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return {"id": str(user.id), "token": create_access_token({"sub": str(user.id)})}


def main() -> int:
    summary: dict[str, Any] = {}

    with socket.socket() as sock:
        sock.settimeout(1.0)
        grpc_ok = sock.connect_ex(("127.0.0.1", 50051)) == 0
    summary["API-02_grpc_port_open"] = grpc_ok
    if not grpc_ok:
        raise RuntimeError("API-02 failed: gRPC 50051 not reachable")

    user = asyncio.run(_create_user())
    with create_client() as client:
        token = user["token"]
        headers = {"Authorization": f"Bearer {token}"}

        malformed_task = client.post(f"{BASE_URL}/tasks", headers=headers, json={"title": ""})
        if malformed_task.status_code not in (400, 422):
            raise RuntimeError(f"API-05 failed: malformed task returned {malformed_task.status_code}")
        _expect_error_shape(malformed_task.json(), "API-05")
        summary["API-05"] = "PASS"

        malformed_plan = client.post(f"{BASE_URL}/plans", headers=headers, json={"name": ""})
        if malformed_plan.status_code not in (400, 422):
            raise RuntimeError(f"API-06 failed: malformed plan returned {malformed_plan.status_code}")
        _expect_error_shape(malformed_plan.json(), "API-06")
        summary["API-06"] = "PASS"

        bad_login = client.post(f"{BASE_URL}/auth/login", json={"username": "nope"})
        if bad_login.status_code not in (400, 422):
            raise RuntimeError(f"API-07 failed: bad login returned {bad_login.status_code}")
        _expect_error_shape(bad_login.json(), "API-07")
        summary["API-07"] = "PASS"

        invalid_uuid = client.get(f"{BASE_URL}/tasks/not-a-uuid", headers=headers)
        if invalid_uuid.status_code not in (400, 422):
            raise RuntimeError(f"API-08 failed: invalid uuid returned {invalid_uuid.status_code}")
        _expect_error_shape(invalid_uuid.json(), "API-08")
        summary["API-08"] = "PASS"

        no_route = client.get(f"{BASE_URL}/definitely-not-exist", headers=headers)
        if no_route.status_code != 404:
            raise RuntimeError(f"API-14 failed: unexpected no-route status {no_route.status_code}")
        _expect_error_shape(no_route.json(), "API-14")
        summary["API-14"] = "PASS"

        ws_health = client.get(f"{BASE_URL}/ws/health", headers=headers)
        assert_status(ws_health, 200, "ws health")
        summary["API-10"] = "PASS"

        ws_metrics = client.get(f"{BASE_URL}/ws/metrics", headers=headers)
        assert_status(ws_metrics, 200, "ws metrics")
        summary["API-11"] = "PASS"

        experiments = client.get(f"{BASE_URL}/experiments/", headers=headers)
        assert_status(experiments, 200, "experiments list")
        summary["API-12"] = "PASS"

        endpoint_paths = _extract_endpoints()
        probe_subset = [
            "/auth/login",
            "/auth/register",
            "/tasks",
            "/plans",
            "/chat",
            "/dashboard/status",
            "/galaxy/graph",
            "/community/groups/directory",
            "/notification-center/notifications",
            "/vocabulary/dictionary/packages",
        ]
        missing = [path for path in probe_subset if path not in endpoint_paths]
        if missing:
            raise RuntimeError(f"API-13 failed: missing mobile endpoints {missing}")
        summary["API-13"] = "PASS"

        gateway_root = client.get("http://127.0.0.1:8080/swagger/index.html")
        assert_status(gateway_root, 200, "swagger")
        summary["API-swagger"] = "PASS"

    print("ALL_OK")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
