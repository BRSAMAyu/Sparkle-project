#!/usr/bin/env python3
import asyncio
import json
import os
import sys
import uuid
from typing import Optional

import aiohttp
import websockets

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8080")
WS_BASE_URL = os.getenv("WS_BASE_URL", "ws://localhost:8080")

RESET = "\033[0m"
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"


def log_success(msg: str) -> None:
    print(f"{GREEN}[SUCCESS] {msg}{RESET}")


def log_error(msg: str) -> None:
    print(f"{RED}[ERROR] {msg}{RESET}")


def log_info(msg: str) -> None:
    print(f"{YELLOW}[INFO] {msg}{RESET}")


async def get_test_token() -> str:
    token = os.getenv("TEST_JWT_TOKEN")
    if token:
        return token

    log_info("No TEST_JWT_TOKEN provided. Set TEST_JWT_TOKEN to a valid JWT.")
    sys.exit(1)


async def get_ws_ticket(session: aiohttp.ClientSession, token: str) -> Optional[str]:
    url = f"{API_BASE_URL}/api/v1/ws/ticket"
    headers = {"Authorization": f"Bearer {token}"}

    try:
        async with session.post(url, headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                ticket = data.get("ticket")
                log_success(f"Got Ticket: {ticket} (TTL: {data.get('expires_in')}s)")
                return ticket
            if resp.status == 429:
                log_error("Rate limit exceeded for Ticket API")
                return None
            text = await resp.text()
            log_error(f"Failed to get ticket: HTTP {resp.status} - {text}")
            return None
    except Exception as exc:
        log_error(f"Exception getting ticket: {exc}")
        return None


async def test_ws_connection_with_ticket(ticket: str) -> bool:
    uri = f"{WS_BASE_URL}/ws/chat"
    subprotocol = f"ticket={ticket}"
    log_info(f"Connecting to {uri} with subprotocol: {subprotocol}")

    try:
        async with websockets.connect(uri, subprotocols=[subprotocol]) as websocket:
            log_success("WebSocket connection established successfully!")
            if websocket.subprotocol == subprotocol:
                log_success(f"Server echoed subprotocol correctly: {websocket.subprotocol}")
            else:
                log_error(f"Server echoed wrong subprotocol: {websocket.subprotocol}")

            await websocket.send(
                json.dumps(
                    {
                        "type": "message",
                        "message": "Hello from Ticket Test",
                        "session_id": str(uuid.uuid4()),
                    }
                )
            )

            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                log_info(f"Received from server: {response}")
            except asyncio.TimeoutError:
                log_info("No immediate response (expected if just connecting)")

            await websocket.close()
            log_success("Connection closed normally.")
            return True
    except websockets.exceptions.InvalidStatusCode as exc:
        log_error(f"WebSocket Handshake Failed: HTTP {exc.status_code}")
        return False
    except Exception as exc:
        log_error(f"WebSocket Connection Failed: {exc}")
        return False


async def test_replay_attack(ticket: str) -> bool:
    log_info(f"Attempting Replay Attack with used ticket: {ticket}")
    subprotocol = f"ticket={ticket}"
    uri = f"{WS_BASE_URL}/ws/chat"

    try:
        async with websockets.connect(uri, subprotocols=[subprotocol]) as websocket:
            log_error("SECURITY FAIL: Replay attack succeeded! (Should be rejected)")
            await websocket.close()
            return False
    except websockets.exceptions.InvalidStatusCode as exc:
        if exc.status_code == 401:
            log_success("SECURITY PASS: Replay attack rejected with 401 Unauthorized.")
            return True
        log_info(f"Replay attack failed with unexpected code: {exc.status_code}")
        return True
    except Exception as exc:
        log_info(f"Replay attack failed as expected: {exc}")
        return True


async def main() -> None:
    token = await get_test_token()

    async with aiohttp.ClientSession() as session:
        ticket = await get_ws_ticket(session, token)
        if not ticket:
            sys.exit(1)

        success = await test_ws_connection_with_ticket(ticket)
        if not success:
            sys.exit(1)

        secure = await test_replay_attack(ticket)
        if not secure:
            sys.exit(1)

        log_info("Testing Rate Limiting (Burst 5)...")
        for idx in range(8):
            t = await get_ws_ticket(session, token)
            if t is None:
                log_info(f"Request {idx + 1} blocked (expected if > burst)")

        log_info("Test Suite Completed.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
