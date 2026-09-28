#!/usr/bin/env python3
"""Service supervisor probe & decision core (V4-P03, FIX-530/542).

Pure, side-effect-free detection layer for the formal service supervisor:

- ``probe_tcp`` / ``probe_http``: health vs ready probes against real
  processes. A live PID alone proves nothing — a "pseudo-dead" process
  (alive but not accepting / returning 5xx) must probe RED.
- ``ServicePolicy`` + ``ProbeState.evaluate``: limited-retry decision state
  machine. ``n`` consecutive failures trigger one restart attempt; a cooldown
  suppresses restart loops; an hourly cap converts further failures into
  alerts (restart must not hide the root cause); a blackout window forces
  observe-only.

No backend imports, no network side effects unless a probe function is
called, stdlib only. The bash/daemon layer (``service_supervisor.py``)
consumes this module, so the tests here exercise the exact logic the
supervisor runs.
"""

from __future__ import annotations

import json
import socket
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any

DEFAULT_TIMEOUT_S = 2.0
DEFAULT_FAIL_THRESHOLD = 3
DEFAULT_COOLDOWN_S = 90.0
DEFAULT_MAX_RESTARTS_PER_HOUR = 3


@dataclass(frozen=True)
class ProbeResult:
    """Outcome of a single probe."""

    ok: bool
    kind: str  # "tcp" | "http"
    target: str
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "kind": self.kind,
            "target": self.target,
            "detail": self.detail,
        }


def probe_tcp(host: str, port: int, timeout: float = DEFAULT_TIMEOUT_S) -> ProbeResult:
    """TCP connect probe — proves a listener accepts, nothing more."""
    target = f"tcp://{host}:{port}"
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return ProbeResult(ok=True, kind="tcp", target=target)
    except OSError as exc:
        return ProbeResult(
            ok=False, kind="tcp", target=target, detail=f"{type(exc).__name__}: {exc}"
        )


def probe_http(
    url: str,
    timeout: float = DEFAULT_TIMEOUT_S,
    ok_statuses: tuple[int, ...] = (200, 204),
) -> ProbeResult:
    """HTTP GET probe. 2xx (by default) = ok; anything else (4xx/5xx/conn error) = red."""
    try:
        req = urllib.request.Request(
            url, method="GET", headers={"User-Agent": "sparkle-supervisor-probe/1"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = resp.status
            ok = status in ok_statuses
            return ProbeResult(
                ok=ok, kind="http", target=url, detail=f"status={status}"
            )
    except urllib.error.HTTPError as exc:
        return ProbeResult(
            ok=False, kind="http", target=url, detail=f"status={exc.code}"
        )
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        return ProbeResult(
            ok=False, kind="http", target=url, detail=f"{type(exc).__name__}: {exc}"
        )


@dataclass(frozen=True)
class ServicePolicy:
    """Per-service restart policy (limited retry, no restart-loop cover-up)."""

    name: str
    fail_threshold: int = DEFAULT_FAIL_THRESHOLD
    cooldown_s: float = DEFAULT_COOLDOWN_S
    max_restarts_per_hour: int = DEFAULT_MAX_RESTARTS_PER_HOUR
    blackout_windows: tuple[
        tuple[str, str], ...
    ] = ()  # ("HH:MM","HH:MM") local time, inclusive


@dataclass
class ProbeState:
    """Consecutive-failure state for one service, with the restart decision.

    The decision is pure with respect to ``(state, probe_ok, now)`` — the
    caller performs any actual restart. This keeps the failure/limit logic
    unit-testable against real probe outcomes.
    """

    policy: ServicePolicy
    consecutive_fails: int = 0
    last_restart_ts: float = 0.0
    restart_timestamps: tuple[float, ...] = field(default=())
    alerted_cap: bool = False

    def evaluate(self, probe_ok: bool, now: float | None = None) -> dict[str, Any]:
        """Fold one probe outcome; return the decision (never performs it)."""
        now = time.time() if now is None else now
        decision: dict[str, Any] = {
            "service": self.policy.name,
            "action": "none",
            "reason": "",
        }
        if probe_ok:
            self.consecutive_fails = 0
            self.alerted_cap = False
            decision["reason"] = "probe_ok"
            return decision

        self.consecutive_fails += 1
        decision["consecutive_fails"] = self.consecutive_fails

        # 3) Blackout window: observe only, never act.
        if self._in_blackout(now):
            decision["action"] = "observe_only"
            decision["reason"] = "blackout_window"
            return decision

        if self.consecutive_fails < self.policy.fail_threshold:
            decision["reason"] = "below_fail_threshold"
            return decision

        # 4) Hourly restart cap: alert, stop restarting (root cause must surface).
        recent = [ts for ts in self.restart_timestamps if now - ts < 3600.0]
        self.restart_timestamps = tuple(recent)
        if len(recent) >= self.policy.max_restarts_per_hour:
            decision["action"] = "alert"
            decision["reason"] = (
                f"restart_cap_reached ({len(recent)}/{self.policy.max_restarts_per_hour} in last hour) — "
                "manual intervention required"
            )
            return decision

        # 5) Cooldown: one in-flight recovery window at a time.
        if (
            self.last_restart_ts
            and (now - self.last_restart_ts) < self.policy.cooldown_s
        ):
            decision["action"] = "wait_cooldown"
            decision["reason"] = (
                f"cooldown {now - self.last_restart_ts:.0f}s < {self.policy.cooldown_s:.0f}s"
            )
            return decision

        decision["action"] = "restart"
        decision["reason"] = f"{self.consecutive_fails} consecutive probe failures"
        self.last_restart_ts = now
        self.restart_timestamps = tuple(recent) + (now,)
        self.consecutive_fails = 0
        return decision

    def _in_blackout(self, now: float) -> bool:
        if not self.policy.blackout_windows:
            return False
        local = time.localtime(now)
        hm = f"{local.tm_hour:02d}:{local.tm_min:02d}"
        for start, end in self.policy.blackout_windows:
            if start <= hm <= end:
                return True
        return False


def probe_service(service: dict[str, Any]) -> dict[str, Any]:
    """Probe one service spec: {"name", "port"?, "health_url"?, "ready_url"?}.

    Health (process up) and readiness (serving correctly) are reported
    separately per the ops spec; service is DOWN if any configured probe is red.
    """
    results: dict[str, Any] = {}
    if "port" in service and service["port"]:
        r = probe_tcp("127.0.0.1", int(service["port"]))
        results["port"] = r.to_dict()
    if service.get("health_url"):
        results["health"] = probe_http(service["health_url"]).to_dict()
    if service.get("ready_url"):
        results["ready"] = probe_http(service["ready_url"]).to_dict()
    ok = all(v["ok"] for v in results.values()) if results else False
    return {"name": service.get("name", "?"), "ok": ok, "probes": results}


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--spec", required=True, help="JSON service spec or '@file.json'"
    )
    parser.add_argument(
        "--json", action="store_true", dest="as_json", help="machine-readable output"
    )
    args = parser.parse_args(argv)

    raw = args.spec
    if raw.startswith("@"):
        with open(raw[1:], encoding="utf-8") as fh:
            raw = fh.read()
    service = json.loads(raw)
    outcome = probe_service(service)
    if args.as_json:
        print(json.dumps(outcome, ensure_ascii=False))
    else:
        mark = "GREEN" if outcome["ok"] else "RED"
        print(
            f"[{mark}] {outcome['name']}: "
            + "; ".join(
                f"{k}={v['detail'] or 'ok'}" for k, v in outcome["probes"].items()
            )
        )
    return 0 if outcome["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
