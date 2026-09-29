#!/usr/bin/env python3
"""Sparkle formal service supervisor (V4-P03; formalizes FIX-530/542 ops face).

Successor of the temporary ``/tmp/engine_watchdog.sh`` (FIX-530) — checked
into the repo, self-anchoring, testable, limited-retry:

- **CWD never decides anything** (FIX-542): REPO_ROOT is derived from this
  file's location; restart actions run with ``cwd=REPO_ROOT`` explicitly, and
  gateway restarts export ``GATEWAY_LOCALES_DIR`` pointing at the repo's
  locales dir (the Go side additionally self-resolves at startup).
- **Detection**: per-service TCP port probe + HTTP health/ready probes via
  ``supervisor_probe`` (a live PID is not health — pseudo-dead processes
  probe RED). Data-plane checks (PG/Redis/MinIO) are observe-only.
- **Limited retry, no loop cover-up** (ops spec): ``fail_threshold``
  consecutive failures → one restart attempt; ``cooldown_s`` between
  attempts; ``max_restarts_per_hour`` → further failures raise ALERT and
  stop restarting so the root cause surfaces.
- **FIX-557 data-plane iron rule (FIX-563 semantics)**: the supervisor NEVER
  starts/stops containers and NEVER touches volumes. Before data-plane checks
  it reads ``docker inspect sparkle_proj_db`` mounts (read-only) and ALERTs if
  the volume prefix is not ``sparkle-project_`` — i.e. our uniquely-named
  container (FIX-563) is mounted on a foreign (sparkle-cosmos_*) volume. A
  missing container is NOT a violation: post-FIX-563 names are repo-unique, so
  absence cannot shadow anyone's data. FIX-577: the expected prefix follows
  ``COMPOSE_PROJECT_NAME`` (default ``sparkle-project``, the value the Makefile
  pins), so the precheck stays correct in worktree checkouts too.
- **Alerts** append JSONL to ``artifacts/ops/supervisor_alerts.jsonl``.

Modes:
    python3 scripts/ops/service_supervisor.py --once            # one cycle, exit 0 green / 1 red
    python3 scripts/ops/service_supervisor.py --observe --interval 30
    python3 scripts/ops/service_supervisor.py --config my.json  # custom service set
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ops"))

from supervisor_probe import ProbeState, ServicePolicy, probe_service  # noqa: E402

ALERT_LOG = REPO_ROOT / "artifacts" / "ops" / "supervisor_alerts.jsonl"
# FIX-577: the expected volume owner prefix follows the pinned compose project
# name. The Makefile and scripts/dev/up.sh export COMPOSE_PROJECT_NAME
# (default sparkle-project), so restart actions they drive always manage the
# project this prefix names; reading the env here keeps the precheck and the
# actual compose project in agreement in any checkout/worktree.
DATA_VOLUME_OWNER_PREFIX = os.environ.get("COMPOSE_PROJECT_NAME", "sparkle-project") + "_"
DATA_CONTAINER = "sparkle_proj_db"  # FIX-563: repo-unique name (was sparkle_db)


def default_services() -> list[dict[str, Any]]:
    """Default supervised set = V3 local topology process services.

    Restart commands go through the repo's own make targets (existing startup
    scripts) with cwd=REPO_ROOT; log paths under /tmp match current practice.
    Data-plane containers are intentionally absent — observe-only below.
    """
    gateway_locales = REPO_ROOT / "backend" / "gateway" / "locales"
    return [
        {
            "name": "engine-api",
            "port": 8000,
            "health_url": "http://127.0.0.1:8000/health",
            "restart_cmd": "make api-server >> /tmp/uvicorn_supervised.log 2>&1 &",
            "policy": {
                "fail_threshold": 3,
                "cooldown_s": 90,
                "max_restarts_per_hour": 3,
            },
        },
        {
            "name": "engine-grpc",
            "port": 50051,
            "restart_cmd": "make grpc-server >> /tmp/grpc_supervised.log 2>&1 &",
            "policy": {
                "fail_threshold": 3,
                "cooldown_s": 90,
                "max_restarts_per_hour": 3,
            },
        },
        {
            "name": "gateway",
            "port": 8080,
            "health_url": "http://127.0.0.1:8080/healthz",
            "ready_url": "http://127.0.0.1:8080/readyz",
            "restart_cmd": (
                f"GATEWAY_LOCALES_DIR={gateway_locales} make gateway-dev >> /tmp/gateway_supervised.log 2>&1 &"
            ),
            "policy": {
                "fail_threshold": 3,
                "cooldown_s": 90,
                "max_restarts_per_hour": 3,
            },
        },
    ]


def check_data_plane_owner() -> dict[str, Any]:
    """Read-only FIX-557/563 precheck: is our data-plane container misowned?

    Post-FIX-563 the container name is repo-unique (sparkle_proj_db), so the
    only violation left to guard is a foreign volume attached to OUR container.
    Absent container = nothing to guard (green, with a note).
    """
    try:
        out = subprocess.run(
            [
                "docker",
                "inspect",
                DATA_CONTAINER,
                "--format",
                "{{range .Mounts}}{{.Name}} {{end}}",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "check": "data_plane_owner",
            "ok": False,
            "detail": f"docker inspect failed: {exc}",
        }
    if out.returncode != 0:
        # docker CLI phrasing varies ("No such object" / "error: no such object")
        if "no such object" in (out.stderr or "").lower():
            return {
                "check": "data_plane_owner",
                "ok": True,
                "detail": f"{DATA_CONTAINER} absent — nothing to guard (FIX-563: repo-unique names cannot shadow foreign volumes)",
            }
        return {
            "check": "data_plane_owner",
            "ok": False,
            "detail": f"{DATA_CONTAINER} not inspectable: {out.stderr.strip()}",
        }
    mounts = out.stdout.strip()
    ok = DATA_VOLUME_OWNER_PREFIX in mounts
    return {
        "check": "data_plane_owner",
        "ok": ok,
        "detail": mounts or "(no mounts)",
        "note": (
            ""
            if ok
            else f"volume prefix is not {DATA_VOLUME_OWNER_PREFIX}* — cross-repo volume misownership on a repo-unique container (FIX-557/FIX-563); do NOT rebuild from this repo, see scripts/RESTACK_RUNBOOK.md"
        ),
    }


def check_data_plane_services() -> list[dict[str, Any]]:
    """Observe-only data-plane health (never restarts containers)."""
    checks: list[dict[str, Any]] = []
    probes = [
        ("postgres", ["docker", "exec", "sparkle_proj_db", "pg_isready", "-U", "postgres"]),
        ("redis", ["docker", "exec", "sparkle_proj_redis", "redis-cli", "ping"]),
        ("minio", None),  # HTTP below
    ]
    for name, cmd in probes:
        if cmd is None:
            try:
                import urllib.request

                with urllib.request.urlopen(
                    "http://127.0.0.1:9000/minio/health/live", timeout=3
                ) as resp:
                    ok = resp.status == 200
                    detail = f"status={resp.status}"
            except Exception as exc:  # noqa: BLE001 — probe surface reports everything
                ok, detail = False, f"{type(exc).__name__}: {exc}"
        else:
            try:
                out = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                lines = (out.stdout or out.stderr).strip().splitlines()[:1]
                detail = lines[0] if lines else f"exit={out.returncode}"
                # redis-cli exits 0 even on server errors (e.g. NOAUTH) — the
                # reply body, not the exit code, decides. NOAUTH means the
                # server is alive but auth-gated (liveness, not full readiness).
                if name == "redis":
                    if detail.startswith("PONG"):
                        ok = True
                    elif "NOAUTH" in detail or "AUTH" in detail:
                        ok = True
                        detail = f"{detail} (alive but auth-gated; liveness only)"
                    else:
                        ok = False
                else:
                    ok = out.returncode == 0
            except (OSError, subprocess.TimeoutExpired) as exc:
                ok, detail = False, f"{type(exc).__name__}: {exc}"
        checks.append({"check": f"data_plane:{name}", "ok": ok, "detail": detail})
    return checks


def alert(event: dict[str, Any]) -> None:
    event = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"), **event}
    line = json.dumps(event, ensure_ascii=False)
    print(f"[ALERT] {line}", file=sys.stderr)
    try:
        ALERT_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(ALERT_LOG, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except OSError as exc:
        print(f"[ALERT] could not write alert log: {exc}", file=sys.stderr)


def run_one_cycle(
    services: list[dict[str, Any]], states: dict[str, ProbeState], observe: bool
) -> tuple[bool, list[dict[str, Any]]]:
    """Probe all services; perform (or withhold) decisions. Returns (all_green, outcomes)."""
    all_green = True
    outcomes: list[dict[str, Any]] = []
    for svc in services:
        name = svc["name"]
        policy = ServicePolicy(name=name, **svc.get("policy", {}))
        state = states.setdefault(name, ProbeState(policy=policy))
        probe = probe_service(svc)
        decision = state.evaluate(probe["ok"])
        entry: dict[str, Any] = {
            "service": name,
            "ok": probe["ok"],
            "probes": probe["probes"],
            **decision,
        }
        if not probe["ok"]:
            all_green = False
        if decision["action"] == "restart":
            if observe:
                entry["executed"] = False
                entry["note"] = "observe mode — restart withheld"
                alert(
                    {
                        "level": "warn",
                        "service": name,
                        "event": "restart_withheld_observe",
                        "probe": probe["probes"],
                    }
                )
            else:
                cmd = svc.get("restart_cmd")
                if not cmd:
                    entry["executed"] = False
                    entry["note"] = "no restart_cmd configured — alerting instead"
                    alert(
                        {
                            "level": "warn",
                            "service": name,
                            "event": "no_restart_cmd",
                            "probe": probe["probes"],
                        }
                    )
                else:
                    proc = subprocess.run(
                        cmd,
                        shell=True,
                        cwd=str(REPO_ROOT),
                        capture_output=True,
                        text=True,
                        timeout=60,
                    )
                    entry["executed"] = True
                    entry["restart_exit"] = proc.returncode
                    entry["restart_cwd"] = str(REPO_ROOT)
                    entry["restart_stdout_head"] = (
                        (proc.stdout or "").strip().splitlines()[:1]
                    )
                    alert(
                        {
                            "level": "warn",
                            "service": name,
                            "event": "restart_executed",
                            "reason": decision["reason"],
                            "exit": proc.returncode,
                        }
                    )
        elif decision["action"] == "alert":
            alert(
                {
                    "level": "error",
                    "service": name,
                    "event": "restart_cap_alert",
                    "reason": decision["reason"],
                }
            )
        outcomes.append(entry)
    return all_green, outcomes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", help="JSON file with {'services': [...]} (default: standard trio)"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="single probe cycle then exit (exit 1 if any service red)",
    )
    parser.add_argument(
        "--observe", action="store_true", help="never restart; report/alert only"
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=30.0,
        help="seconds between cycles (default 30)",
    )
    parser.add_argument(
        "--data-plane",
        action="store_true",
        help="include observe-only PG/Redis/MinIO checks + FIX-557 owner precheck",
    )
    args = parser.parse_args(argv)

    if args.config:
        with open(args.config, encoding="utf-8") as fh:
            cfg = json.load(fh)
        services = cfg["services"]
    else:
        services = default_services()

    states: dict[str, ProbeState] = {}

    if args.once:
        owner = check_data_plane_owner()
        if not owner["ok"]:
            alert({"level": "error", **owner})
        all_green, outcomes = run_one_cycle(services, states, observe=True)
        report: dict[str, Any] = {
            "mode": "once",
            "all_green": all_green and owner["ok"],
            "services": outcomes,
            "data_plane_owner": owner,
        }
        if args.data_plane:
            report["data_plane"] = check_data_plane_services()
        print(json.dumps(report, ensure_ascii=False, indent=1))
        return 0 if report["all_green"] else 1

    alert(
        {
            "level": "info",
            "event": "supervisor_started",
            "pid": os.getpid(),
            "services": [s["name"] for s in services],
            "observe": args.observe,
        }
    )
    try:
        while True:
            started = time.time()
            run_one_cycle(services, states, observe=args.observe)
            elapsed = time.time() - started
            time.sleep(max(1.0, args.interval - elapsed))
    except KeyboardInterrupt:
        alert({"level": "info", "event": "supervisor_stopped", "pid": os.getpid()})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
