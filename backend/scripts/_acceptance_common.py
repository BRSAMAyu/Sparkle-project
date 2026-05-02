#!/usr/bin/env python3
"""Shared helpers for local acceptance scripts."""

from __future__ import annotations

import asyncio
import os
import time
import uuid
from collections.abc import Callable
from typing import Any

import httpx
import requests


AUTH_BASE_URL = os.getenv("LOCAL_SMOKE_AUTH_BASE_URL", "http://127.0.0.1:8080/api/v1")
BASE_URL = os.getenv("LOCAL_SMOKE_BASE_URL", "http://127.0.0.1:8080/api/v1")
USERNAME = os.getenv("LOCAL_SMOKE_USERNAME", "chat_test")
PASSWORD = os.getenv("LOCAL_SMOKE_PASSWORD", "Chat123456")
SECONDARY_PASSWORD = os.getenv("LOCAL_SMOKE_SECONDARY_PASSWORD", "Temp123456")
DEMO_PASSWORD = os.getenv("LOCAL_SMOKE_DEMO_PASSWORD", "Chat123456")
DEMO_FRIEND_PASSWORD = os.getenv("LOCAL_SMOKE_DEMO_FRIEND_PASSWORD", "DemoFriend123")
REQUEST_TIMEOUT_SECONDS = float(os.getenv("LOCAL_SMOKE_TIMEOUT_SECONDS", "60"))


def ensure(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def create_client(*, timeout_seconds: float = REQUEST_TIMEOUT_SECONDS) -> httpx.Client:
    return httpx.Client(timeout=timeout_seconds)


def assert_status(resp: httpx.Response, expected: int, label: str) -> None:
    if resp.status_code != expected:
        raise RuntimeError(f"{label} failed: {resp.status_code} {resp.text[:800]}")


async def _issue_local_smoke_token_async(username: str, password: str) -> str:
    from sqlalchemy import or_, select

    from app.core.security import create_access_token, get_password_hash
    from app.db.session import AsyncSessionLocal
    from app.models.user import User

    async with AsyncSessionLocal() as db:
        user = await db.scalar(
            select(User).where(or_(User.username == username, User.email == username))
        )
        if user is None:
            fallback_username = username if "@" not in username else username.split("@", 1)[0]
            user = User(
                username=fallback_username,
                email=username if "@" in username else f"{fallback_username}@example.com",
                hashed_password=get_password_hash(password),
                password_login_enabled=True,
                nickname=fallback_username,
                registration_source="acceptance_local_fallback",
                is_active=True,
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
        return create_access_token({"sub": str(user.id), "sid": uuid.uuid4().hex})


def issue_local_smoke_token(username: str = USERNAME, password: str = PASSWORD) -> str:
    return asyncio.run(_issue_local_smoke_token_async(username, password))


def login(client: httpx.Client) -> str:
    last_error = ""
    saw_rate_limit = False
    for attempt in range(5):
        response = client.post(
            f"{AUTH_BASE_URL}/auth/login",
            json={"username": USERNAME, "password": PASSWORD},
        )
        if response.status_code == 200:
            return response.json()["access_token"]
        last_error = f"{response.status_code} {response.text[:400]}"
        if response.status_code != 429:
            break
        saw_rate_limit = True
        time.sleep(1.5 * (attempt + 1))
    if saw_rate_limit:
        return issue_local_smoke_token()
    raise RuntimeError(f"login failed: {last_error}")


def login_with_requests(
    *,
    session: requests.Session | None = None,
    auth_base_url: str = AUTH_BASE_URL,
    username: str = USERNAME,
    password: str = PASSWORD,
    timeout_seconds: float = REQUEST_TIMEOUT_SECONDS,
) -> str:
    requester = session or requests
    last_error = ""
    saw_rate_limit = False
    for attempt in range(5):
        response = requester.post(
            f"{auth_base_url}/auth/login",
            json={"username": username, "password": password},
            timeout=timeout_seconds,
        )
        if response.status_code == 200:
            return response.json()["access_token"]
        last_error = f"{response.status_code} {response.text[:400]}"
        if response.status_code != 429:
            break
        saw_rate_limit = True
        time.sleep(1.5 * (attempt + 1))
    if saw_rate_limit:
        return issue_local_smoke_token(username=username, password=password)
    raise RuntimeError(f"login failed: {last_error}")


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def poll_until(
    callback: Callable[[], Any],
    *,
    timeout_seconds: int = 25,
    interval_seconds: float = 1.5,
) -> Any:
    deadline = time.monotonic() + timeout_seconds
    last_value = None
    while time.monotonic() < deadline:
        last_value = callback()
        if last_value:
            return last_value
        time.sleep(interval_seconds)
    return last_value
