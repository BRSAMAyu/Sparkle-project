#!/usr/bin/env python3
"""Shared helpers for local acceptance scripts."""

from __future__ import annotations

import os
import time
from collections.abc import Callable
from typing import Any

import httpx


AUTH_BASE_URL = os.getenv("LOCAL_SMOKE_AUTH_BASE_URL", "http://127.0.0.1:8080/api/v1")
BASE_URL = os.getenv("LOCAL_SMOKE_BASE_URL", "http://127.0.0.1:8080/api/v1")
USERNAME = os.getenv("LOCAL_SMOKE_USERNAME", "chat_test")
PASSWORD = os.getenv("LOCAL_SMOKE_PASSWORD", "Chat123456")
REQUEST_TIMEOUT_SECONDS = float(os.getenv("LOCAL_SMOKE_TIMEOUT_SECONDS", "60"))


def ensure(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def create_client(*, timeout_seconds: float = REQUEST_TIMEOUT_SECONDS) -> httpx.Client:
    return httpx.Client(timeout=timeout_seconds)


def assert_status(resp: httpx.Response, expected: int, label: str) -> None:
    if resp.status_code != expected:
        raise RuntimeError(f"{label} failed: {resp.status_code} {resp.text[:800]}")


def login(client: httpx.Client) -> str:
    last_error = ""
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
        time.sleep(1.5 * (attempt + 1))
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
