#!/usr/bin/env python3
"""Bootstrap and smoke-test the local Sparkle <-> OpenClaw execution path."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BACKEND_API = "http://127.0.0.1:8000/api/v1"
DEFAULT_GATEWAY_API = "http://127.0.0.1:8080/api/v1"
DEFAULT_NODE_NAME = "Sparkle Node"
DEFAULT_GATEWAY_PORT = "18789"


class StepError(RuntimeError):
    """Raised when a readiness step fails."""


def run_command(
    args: list[str],
    *,
    check: bool = True,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        args,
        cwd=str(cwd or REPO_ROOT),
        check=False,
        text=True,
        capture_output=True,
    )
    if check and result.returncode != 0:
        stderr = result.stderr.strip()
        stdout = result.stdout.strip()
        details = stderr or stdout or f"exit={result.returncode}"
        raise StepError(f"{' '.join(args)} failed: {details}")
    return result


def run_json(args: list[str]) -> dict[str, Any]:
    result = run_command(args)
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise StepError(f"{' '.join(args)} did not return valid JSON") from exc


def print_step(message: str) -> None:
    print(f"[openclaw-ready] {message}")


def ensure_binary(name: str) -> None:
    if shutil.which(name) is None:
        raise StepError(f"Missing required binary: {name}")


def http_json(
    method: str,
    url: str,
    *,
    payload: dict[str, Any] | None = None,
    token: str | None = None,
    timeout: int = 60,
) -> tuple[int, dict[str, Any]]:
    body = None
    headers: dict[str, str] = {}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            return response.getcode(), json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            payload = {"detail": raw}
        return exc.code, payload


def tailscale_online() -> bool:
    if shutil.which("tailscale") is None:
        return False
    result = run_command(["tailscale", "status", "--json"], check=False)
    if result.returncode != 0 or not result.stdout.strip():
        return False
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return False
    return bool(payload.get("Self", {}).get("Online"))


def set_config(path: str, value: str) -> None:
    run_command(["openclaw", "config", "set", path, value])


def maybe_unset_config(path: str) -> None:
    run_command(["openclaw", "config", "unset", path], check=False)


def configure_gateway(exposure: str, public_url: str | None) -> dict[str, Any]:
    effective_exposure = exposure
    if exposure == "auto":
        effective_exposure = "tailnet" if tailscale_online() else "lan"

    print_step(f"Configuring OpenClaw exposure: {effective_exposure}")
    set_config("gateway.mode", "local")

    if effective_exposure == "lan":
        set_config("gateway.tailscale.mode", "off")
        maybe_unset_config("plugins.entries.device-pair.config.publicUrl")
        set_config("gateway.bind", "lan")
    elif effective_exposure == "tailnet":
        if not tailscale_online():
            raise StepError("Requested tailnet exposure, but Tailscale is not online on this machine")
        maybe_unset_config("plugins.entries.device-pair.config.publicUrl")
        set_config("gateway.bind", "loopback")
        set_config("gateway.tailscale.mode", "serve")
    elif effective_exposure == "public-url":
        if not public_url:
            raise StepError("--public-url is required when exposure=public-url")
        set_config("gateway.bind", "loopback")
        set_config("gateway.tailscale.mode", "off")
        set_config("plugins.entries.device-pair.config.publicUrl", public_url)
    else:
        raise StepError(f"Unsupported exposure: {effective_exposure}")

    run_command(["openclaw", "gateway", "restart"])
    status = run_json(["openclaw", "gateway", "status", "--json"])
    qr = run_json(["openclaw", "qr", "--json"])
    return {
        "requested_exposure": exposure,
        "effective_exposure": effective_exposure,
        "bind_mode": ((status.get("gateway") or {}).get("bindMode")),
        "bind_host": ((status.get("gateway") or {}).get("bindHost")),
        "gateway_port": ((status.get("gateway") or {}).get("port")),
        "gateway_url": qr.get("gatewayUrl"),
        "url_source": qr.get("urlSource"),
        "setup_code": qr.get("setupCode"),
    }


def ensure_node_service() -> dict[str, Any]:
    print_step("Ensuring OpenClaw node host is running")
    status = run_json(["openclaw", "node", "status", "--json"])
    service = status.get("service", {})
    runtime = service.get("runtime", {})
    command_args = service.get("command", {}).get("programArguments", [])
    expected = ["node", "run", "--host", "127.0.0.1", "--port", DEFAULT_GATEWAY_PORT]

    needs_install = not service.get("loaded") or runtime.get("status") != "running"
    if command_args:
        joined = " ".join(command_args)
        for token in expected:
            if token not in joined:
                needs_install = True
                break

    if needs_install:
        run_command(
            [
                "openclaw",
                "node",
                "install",
                "--force",
                "--host",
                "127.0.0.1",
                "--port",
                DEFAULT_GATEWAY_PORT,
                "--display-name",
                DEFAULT_NODE_NAME,
            ]
        )
        run_command(["openclaw", "node", "restart"])
        status = run_json(["openclaw", "node", "status", "--json"])

    service = status.get("service", {})
    runtime = service.get("runtime", {})
    command_args = service.get("command", {}).get("programArguments", [])
    display_name = None
    if "--display-name" in command_args:
        index = command_args.index("--display-name")
        if index + 1 < len(command_args):
            display_name = command_args[index + 1]
    return {
        "loaded": bool(service.get("loaded")),
        "runtime_status": runtime.get("status"),
        "runtime_state": runtime.get("state"),
        "display_name": display_name,
    }


def approve_pending_devices() -> dict[str, Any]:
    print_step("Checking for pending OpenClaw pairing requests")
    devices = run_json(["openclaw", "devices", "list", "--json"])
    approvals = 0
    while devices.get("pending"):
        run_command(["openclaw", "devices", "approve", "--latest", "--json"])
        approvals += 1
        time.sleep(1)
        devices = run_json(["openclaw", "devices", "list", "--json"])
    nodes = run_json(["openclaw", "nodes", "status", "--json"])
    node_entries = list(nodes.get("nodes") or [])
    return {
        "approved_count": approvals,
        "pending_count": len(devices.get("pending") or []),
        "paired_count": len(devices.get("paired") or []),
        "connected_nodes": sum(1 for node in node_entries if node.get("connected")),
        "node_labels": [node.get("displayName") or node.get("nodeId") for node in node_entries],
    }


def check_backend_connection(base_api: str) -> dict[str, Any]:
    print_step(f"Checking backend execution status via {base_api}")
    status_code, payload = http_json("GET", f"{base_api}/executions/connection/status", timeout=30)
    if status_code != 200:
        raise StepError(f"Backend connection status failed with HTTP {status_code}: {payload}")
    if not payload.get("reachable"):
        raise StepError(f"Backend reports OpenClaw unreachable: {payload}")
    if int(payload.get("connected_nodes", 0)) < 1:
        raise StepError(f"Backend reports no connected OpenClaw nodes: {payload}")
    return payload


def check_gateway_health(base_api: str) -> dict[str, Any]:
    print_step(f"Checking proxy gateway health via {base_api}")
    health_code, health = http_json("GET", f"{base_api}/health", timeout=20)
    cqrs_code, cqrs = http_json("GET", f"{base_api}/health/cqrs", timeout=20)
    if health_code != 200:
        raise StepError(f"Gateway /health failed with HTTP {health_code}: {health}")
    if cqrs_code != 200:
        raise StepError(f"Gateway /health/cqrs failed with HTTP {cqrs_code}: {cqrs}")
    return {"health": health, "cqrs": cqrs}


def register_user(base_api: str) -> tuple[str, str]:
    username = f"openclaw_demo_{uuid.uuid4().hex[:10]}"
    payload = {
        "username": username,
        "email": f"{username}@example.com",
        "password": "Sparkle123!",
        "accepted_tos": True,
        "accepted_privacy": True,
        "tos_version": "openclaw-ready",
        "privacy_version": "openclaw-ready",
        "agreed_locale": "zh-CN",
    }
    status_code, response = http_json("POST", f"{base_api}/auth/register", payload=payload, timeout=60)
    if status_code not in {200, 201}:
        raise StepError(f"Register failed with HTTP {status_code}: {response}")
    token = response.get("access_token")
    if not token:
        raise StepError("Register response did not include access_token")
    return username, token


def create_demo_task(base_api: str, token: str) -> str:
    payload = {
        "title": "OpenClaw repo-root handoff demo",
        "type": "planning",
        "estimated_minutes": 5,
        "energy_cost": 1,
        "priority": 0,
        "tags": ["openclaw", "demo", "shell"],
    }
    status_code, response = http_json("POST", f"{base_api}/tasks", payload=payload, token=token, timeout=60)
    if status_code not in {200, 201}:
        raise StepError(f"Create task failed with HTTP {status_code}: {response}")
    task_id = ((response.get("data") or {}).get("id"))
    if not task_id:
        raise StepError("Create task response did not include task id")
    return str(task_id)


def handoff_demo_task(base_api: str, token: str, task_id: str) -> dict[str, Any]:
    payload = {
        "goal": "Run pwd and return the current working directory. Do not execute any other command.",
        "instructions": [
            "Only run pwd once.",
            "Do not modify files, network state, or environment variables.",
        ],
        "template_id": "shell_diagnostics",
    }
    status_code, response = http_json(
        "POST",
        f"{base_api}/executions/tasks/{task_id}/handoff",
        payload=payload,
        token=token,
        timeout=120,
    )
    if status_code != 200:
        raise StepError(f"Handoff failed with HTTP {status_code}: {response}")
    return response


def wait_for_terminal_intent(base_api: str, token: str, intent_id: str) -> dict[str, Any]:
    deadline = time.time() + 120
    last_payload: dict[str, Any] | None = None
    while time.time() < deadline:
        status_code, payload = http_json("GET", f"{base_api}/executions/{intent_id}", token=token, timeout=30)
        if status_code != 200:
            raise StepError(f"Fetching execution status failed with HTTP {status_code}: {payload}")
        last_payload = payload
        if payload.get("status") in {"succeeded", "failed", "waiting_approval", "handed_back"}:
            return payload
        time.sleep(1)
    raise StepError(f"Execution did not reach terminal status in time: {last_payload}")


def fetch_record(base_api: str, token: str, intent_id: str) -> dict[str, Any]:
    status_code, payload = http_json("GET", f"{base_api}/executions/{intent_id}/record", token=token, timeout=30)
    if status_code != 200:
        raise StepError(f"Fetching execution record failed with HTTP {status_code}: {payload}")
    return payload


def run_execution_smoke(base_api: str, repo_root: Path) -> dict[str, Any]:
    print_step(f"Running real OpenClaw handoff smoke via {base_api}")
    username, token = register_user(base_api)
    task_id = create_demo_task(base_api, token)
    intent = handoff_demo_task(base_api, token, task_id)
    terminal_intent = wait_for_terminal_intent(base_api, token, intent["id"])
    if terminal_intent.get("status") != "succeeded":
        raise StepError(f"Execution did not succeed: {terminal_intent}")
    record = fetch_record(base_api, token, intent["id"])
    preview_text = str(((record.get("result_preview") or {}).get("text")) or "")
    repo_root_text = str(repo_root)
    if repo_root_text not in preview_text:
        raise StepError(
            f"Execution succeeded but repo root was not observed in result preview: {preview_text}"
        )
    return {
        "username": username,
        "task_id": task_id,
        "intent_id": intent["id"],
        "intent_status": terminal_intent.get("status"),
        "record_id": record.get("id"),
        "record_duration_ms": record.get("duration_ms"),
        "record_preview": preview_text,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--exposure",
        choices=["auto", "lan", "tailnet", "public-url"],
        default="auto",
        help="How OpenClaw should expose its pairing route. auto prefers tailnet when Tailscale is online, else lan.",
    )
    parser.add_argument(
        "--public-url",
        default=None,
        help="Public reverse-proxy URL to advertise when exposure=public-url.",
    )
    parser.add_argument(
        "--backend-api",
        default=DEFAULT_BACKEND_API,
        help="Sparkle backend API base URL.",
    )
    parser.add_argument(
        "--gateway-api",
        default=DEFAULT_GATEWAY_API,
        help="Sparkle gateway API base URL.",
    )
    parser.add_argument(
        "--smoke-only",
        action="store_true",
        help="Skip OpenClaw bootstrap changes and run only validation/smoke steps.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    ensure_binary("openclaw")
    summary: dict[str, Any] = {
        "repo_root": str(REPO_ROOT),
        "backend_api": args.backend_api,
        "gateway_api": args.gateway_api,
        "bootstrap": None,
        "node_service": None,
        "pairing": None,
        "backend_status": None,
        "gateway_health": None,
        "smoke_backend": None,
        "smoke_gateway": None,
    }

    try:
        if not args.smoke_only:
            summary["bootstrap"] = configure_gateway(args.exposure, args.public_url)
            summary["node_service"] = ensure_node_service()
            summary["pairing"] = approve_pending_devices()
        else:
            print_step("Smoke-only mode: preserving current OpenClaw runtime config")

        summary["backend_status"] = check_backend_connection(args.backend_api)
        summary["gateway_health"] = check_gateway_health(args.gateway_api)
        summary["smoke_backend"] = run_execution_smoke(args.backend_api, REPO_ROOT)
        summary["smoke_gateway"] = run_execution_smoke(args.gateway_api, REPO_ROOT)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0
    except StepError as exc:
        print_step(str(exc))
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    sys.exit(main())
