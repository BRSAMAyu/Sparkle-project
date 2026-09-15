#!/usr/bin/env python3
"""Preflight checks for local final sign-off runs.

This script intentionally validates the *effective* local runtime instead of
assuming Docker is the active source of truth. It catches the most common
"looks started but isn't actually usable" failures before manual acceptance:

- configured DB/Redis host or port is not listening
- backend / gateway health endpoints are down
- Alembic is not at head
- critical startup baseline objects are missing
"""

from __future__ import annotations

import asyncio
import os
import socket
import subprocess
import sys
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import asyncpg
import redis
import requests

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.config import settings
from app.config.settings import to_sync_database_url


@dataclass
class CheckResult:
    name: str
    status: str
    detail: str


def _redis_search_module_unavailable(exc: Exception) -> bool:
    lowered = str(exc).lower()
    return "unknown command" in lowered or ("module" in lowered and "not found" in lowered)


def _redact_url(raw_url: str) -> str:
    parsed = urlparse(raw_url)
    if not parsed.username and not parsed.password:
        return raw_url
    username = parsed.username or ""
    netloc = f"{username}:***@{parsed.hostname}"
    if parsed.port:
        netloc = f"{netloc}:{parsed.port}"
    return parsed._replace(netloc=netloc).geturl()


def _socket_open(host: str, port: int, timeout: float = 1.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


async def _check_postgres() -> CheckResult:
    parsed = urlparse(to_sync_database_url(settings.DATABASE_URL))
    host = parsed.hostname or settings.POSTGRES_HOST or "127.0.0.1"
    port = parsed.port or settings.POSTGRES_PORT or 5432
    if not _socket_open(host, int(port)):
        hint = ""
        if int(port) != 5432 and _socket_open(host, 5432):
            hint = f" (hint: {host}:5432 is listening; align DATABASE_URL or start the expected {port} service)"
        return CheckResult(
            "postgres_port",
            "FAIL",
            f"configured PostgreSQL endpoint is not listening: {host}:{port}{hint}",
        )

    try:
        conn = await asyncpg.connect(to_sync_database_url(settings.DATABASE_URL))
    except Exception as exc:  # noqa: BLE001
        return CheckResult("postgres_auth", "FAIL", f"{host}:{port} connect failed: {exc}")
    try:
        value = await conn.fetchval("SELECT 1")
    finally:
        await conn.close()
    if value != 1:
        return CheckResult("postgres_query", "FAIL", "unexpected SELECT 1 result")
    return CheckResult("postgres", "PASS", f"{host}:{port} reachable and queryable")


def _check_redis() -> CheckResult:
    parsed = urlparse(settings.REDIS_URL)
    host = parsed.hostname or settings.REDIS_HOST or "127.0.0.1"
    port = parsed.port or settings.REDIS_PORT or 6379
    if not _socket_open(host, int(port)):
        return CheckResult(
            "redis_port",
            "FAIL",
            f"configured Redis endpoint is not listening: {host}:{port}",
        )
    client = redis.Redis.from_url(settings.REDIS_URL)
    if not client.ping():
        return CheckResult("redis_ping", "FAIL", "Redis PING failed")
    return CheckResult("redis", "PASS", f"{host}:{port} reachable and pingable")


def _check_http(name: str, url: str) -> CheckResult:
    try:
        resp = requests.get(url, timeout=5)
    except Exception as exc:  # noqa: BLE001
        return CheckResult(name, "FAIL", f"{url} -> request failed: {exc}")
    if not (200 <= resp.status_code < 300):
        return CheckResult(name, "FAIL", f"{url} -> HTTP {resp.status_code}")
    return CheckResult(name, "PASS", f"{url} -> HTTP {resp.status_code}")


def _check_grpc_port(name: str, host: str, port: int) -> CheckResult:
    try:
        with socket.create_connection((host, port), timeout=3):
            return CheckResult(name, "PASS", f"{host}:{port} accepting connections")
    except OSError as exc:
        return CheckResult(name, "FAIL", f"{host}:{port} -> {exc}")


def _check_alembic_head() -> CheckResult:
    backend_dir = os.path.dirname(os.path.dirname(__file__))
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "current"],
        cwd=backend_dir,
        capture_output=True,
        text=True,
        check=False,
    )
    output = (result.stdout + result.stderr).strip()
    if result.returncode != 0:
        return CheckResult("alembic_current", "FAIL", output or "alembic current failed")
    if "(head)" not in output:
        return CheckResult("alembic_current", "FAIL", f"not at head: {output}")
    return CheckResult("alembic_current", "PASS", output)


async def _check_runtime_baseline() -> list[CheckResult]:
    try:
        conn = await asyncpg.connect(to_sync_database_url(settings.DATABASE_URL))
    except Exception as exc:  # noqa: BLE001
        return [
            CheckResult(
                "runtime_baseline",
                "FAIL",
                f"baseline checks skipped because PostgreSQL is unavailable: {exc}",
            )
        ]
    try:
        table_exists = await conn.fetchval(
            """
            SELECT EXISTS (
              SELECT 1
              FROM information_schema.tables
              WHERE table_name = 'user_learning_profiles'
            )
            """
        )
        prerequisite_count = await conn.fetchval(
            """
            SELECT COUNT(*)
            FROM node_relations
            WHERE lower(relation_type) = 'prerequisite'
            """
        )
    finally:
        await conn.close()

    redis_client = redis.Redis.from_url(settings.REDIS_URL)
    try:
        index_ok = bool(redis_client.execute_command("FT.INFO", "idx:knowledge"))
        index_detail = "idx:knowledge present"
        index_status = "PASS"
    except Exception as exc:  # noqa: BLE001
        if _redis_search_module_unavailable(exc):
            index_ok = False
            index_status = "WARN"
            index_detail = f"RediSearch module unavailable; knowledge retrieval will use degraded fallback paths: {exc}"
        else:
            index_ok = False
            index_status = "FAIL"
            index_detail = f"idx:knowledge missing or unavailable: {exc}"

    return [
        CheckResult(
            "user_learning_profiles",
            "PASS" if table_exists else "FAIL",
            "table exists" if table_exists else "table is missing",
        ),
        CheckResult(
            "knowledge_prerequisite_baseline",
            "PASS" if prerequisite_count and prerequisite_count > 0 else "FAIL",
            f"prerequisite relation count={prerequisite_count}",
        ),
        CheckResult(
            "redis_search_index",
            "PASS" if index_ok else index_status,
            index_detail,
        ),
    ]


def _print_header() -> None:
    print("Local sign-off preflight")
    print(f"  DATABASE_URL={_redact_url(settings.DATABASE_URL)}")
    print(f"  REDIS_URL={_redact_url(settings.REDIS_URL)}")
    print(f"  POSTGRES_HOST={settings.POSTGRES_HOST}")
    print(f"  POSTGRES_PORT={settings.POSTGRES_PORT}")
    print(f"  REDIS_HOST={settings.REDIS_HOST}")
    print(f"  REDIS_PORT={settings.REDIS_PORT}")


async def main() -> int:
    _print_header()

    results: list[CheckResult] = []
    results.append(await _check_postgres())
    results.append(_check_redis())
    results.append(_check_http("backend_health", "http://127.0.0.1:8000/health"))
    results.append(_check_grpc_port("grpc_engine", "127.0.0.1", 50051))
    results.append(_check_http("gateway_health", "http://127.0.0.1:8080/api/v1/health"))
    # CQRS health requires auth token, skip in preflight (gateway_health covers basic readiness)
    # results.append(_check_http("gateway_cqrs_health", "http://127.0.0.1:8080/api/v1/health/cqrs"))
    results.append(_check_alembic_head())
    results.extend(await _check_runtime_baseline())

    failed = [item for item in results if item.status == "FAIL"]
    for item in results:
        print(f"[{item.status}] {item.name}: {item.detail}")

    if failed:
        print(f"\nPreflight failed: {len(failed)} blocking issue(s).")
        return 1

    print("\nPreflight passed: local stack is ready for final sign-off.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
