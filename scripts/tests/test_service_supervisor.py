"""V4-P03 supervisor end-to-end drill — real process supervision, falsifiable.

Exercises the ACTUAL supervisor module (``scripts/ops/service_supervisor.py``)
against REAL decoy processes on ephemeral ports:

1. healthy decoy → ``--once`` CLI exits 0 (green);
2. SIGKILL decoy → ``--once`` exits 1 with the service RED (loss detected);
3. full recovery: ``run_one_cycle(observe=False)`` executes the configured
   restart command, decoy comes back, next cycle is green;
4. FIX-542 at the supervisor layer: restart commands run with
   ``cwd=REPO_ROOT`` regardless of the caller's CWD (asserted via ``pwd``);
5. FIX-557 owner precheck under FIX-563 semantics: real ``docker inspect``
   is green when our repo-unique container is absent or owns a
   ``sparkle-project_*`` volume; a foreign ``sparkle-cosmos_*`` volume on our
   container is RED and would alert (read-only check — no container is ever
   mutated);
6. observe mode withholds restarts (alerts instead of acting).

No real stack ports (8000/8080/50051) are touched; everything runs on
127.0.0.1:0 decoys. Alerts are redirected to a tmp dir, never the repo's.
"""

from __future__ import annotations

import json
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SUPERVISOR = REPO_ROOT / "scripts" / "ops" / "service_supervisor.py"
PROBE_MOD = REPO_ROOT / "scripts" / "ops"
DECOY_SRC = (Path(__file__).parent / "test_supervisor_probe.py").read_text(
    encoding="utf-8"
)

sys.path.insert(0, str(PROBE_MOD))

import service_supervisor as sup  # noqa: E402
from supervisor_probe import probe_tcp  # noqa: E402


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture()
def decoy_factory(tmp_path):
    """Spawn decoys from a stable script file so restart_cmd can re-spawn them."""
    script = tmp_path / "decoy_server.py"
    script.write_text(
        "import http.server, sys\n"
        "class H(http.server.BaseHTTPRequestHandler):\n"
        "    def do_GET(self):\n"
        "        self.send_response(int(sys.argv[2])); self.end_headers(); self.wfile.write(b'ok')\n"
        "    def log_message(self, *a): pass\n"
        "http.server.HTTPServer(('127.0.0.1', int(sys.argv[1])), H).serve_forever()\n",
        encoding="utf-8",
    )
    spawned: list[subprocess.Popen] = []

    def spawn(port: int, status: int = 200) -> subprocess.Popen:
        proc = subprocess.Popen([sys.executable, str(script), str(port), str(status)])
        spawned.append(proc)
        return proc

    yield spawn
    for proc in spawned:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=5)


@pytest.fixture()
def alert_redirect(tmp_path, monkeypatch):
    """Redirect supervisor alerts into tmp (never write repo artifacts from tests)."""
    target = tmp_path / "alerts.jsonl"
    monkeypatch.setattr(sup, "ALERT_LOG", target)
    return target


def _wait_tcp(port: int, deadline_s: float = 5.0) -> None:
    end = time.time() + deadline_s
    while time.time() < end:
        if probe_tcp("127.0.0.1", port, timeout=0.5).ok:
            return
        time.sleep(0.05)
    raise AssertionError(f"decoy :{port} never reachable")


def test_once_cli_green_on_healthy_decoy(decoy_factory):
    port = _free_port()
    decoy_factory(port)
    _wait_tcp(port)
    cfg = tmp_cfg(port)
    proc = subprocess.run(
        [sys.executable, str(SUPERVISOR), "--once", "--config", str(cfg)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    report = json.loads(proc.stdout)
    assert report["all_green"] is True
    assert report["services"][0]["ok"] is True


def test_once_cli_red_after_real_kill(decoy_factory):
    port = _free_port()
    proc_decoy = decoy_factory(port)
    _wait_tcp(port)
    proc_decoy.kill()
    proc_decoy.wait(timeout=5)
    time.sleep(0.1)
    cfg = tmp_cfg(port)
    proc = subprocess.run(
        [sys.executable, str(SUPERVISOR), "--once", "--config", str(cfg)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert (
        proc.returncode == 1
    ), "supervisor --once must exit 1 when the service is really gone"
    report = json.loads(proc.stdout)
    assert report["all_green"] is False
    assert report["services"][0]["ok"] is False


def test_full_recovery_restart_cycle(decoy_factory, alert_redirect):
    """Loss → RED → supervisor executes restart_cmd → GREEN again."""
    port = _free_port()
    script_ref = alert_redirect.parent / "decoy_server.py"
    # Reuse the factory's script path via a fresh copy for restart_cmd.
    script_ref.write_text(
        "import http.server, sys\n"
        "class H(http.server.BaseHTTPRequestHandler):\n"
        "    def do_GET(self):\n"
        "        self.send_response(200); self.end_headers(); self.wfile.write(b'ok')\n"
        "    def log_message(self, *a): pass\n"
        "http.server.HTTPServer(('127.0.0.1', int(sys.argv[1])), H).serve_forever()\n",
        encoding="utf-8",
    )
    proc_decoy = decoy_factory(port)
    _wait_tcp(port)

    svc = {
        "name": "decoy-recover",
        "port": port,
        "health_url": f"http://127.0.0.1:{port}/",
        # Real restart command: re-spawn the decoy (cwd=REPO_ROOT, absolute script path).
        "restart_cmd": f"nohup {sys.executable} {script_ref} {port} 200 >> /dev/null 2>&1 &",
        "policy": {"fail_threshold": 1, "cooldown_s": 0, "max_restarts_per_hour": 5},
    }
    states: dict = {}
    green, outcomes = sup.run_one_cycle([svc], states, observe=False)
    assert green, outcomes
    assert outcomes[0]["action"] == "none"  # still healthy on first cycle

    # Real process loss:
    proc_decoy.kill()
    proc_decoy.wait(timeout=5)
    time.sleep(0.1)
    green1, outcomes1 = sup.run_one_cycle([svc], states, observe=False)
    assert not green1, "cycle after kill must be red"
    assert outcomes1[0]["action"] == "restart", outcomes1
    assert outcomes1[0]["executed"] is True

    # Give the restarted decoy a moment to bind, then verify recovery:
    _wait_tcp(port)
    green2, outcomes2 = sup.run_one_cycle([svc], states, observe=False)
    assert (
        green2
    ), "service must be green again after supervisor restart (recovery proof)"
    assert outcomes2[0]["ok"] is True
    assert alert_redirect.exists(), "restart must leave an alert trail"
    assert "restart_executed" in alert_redirect.read_text(encoding="utf-8")


def test_restart_runs_with_repo_cwd_not_caller_cwd(
    decoy_factory, alert_redirect, tmp_path, monkeypatch
):
    """FIX-542: restart actions must not inherit the caller's CWD."""
    svc = {
        "name": "cwd-proof",
        "port": _free_port(),  # nothing listening → immediate red
        "restart_cmd": "pwd",
        "policy": {"fail_threshold": 1, "cooldown_s": 0, "max_restarts_per_hour": 10},
    }
    monkeypatch.chdir(tmp_path)  # caller CWD is somewhere unrelated
    states: dict = {}
    _, outcomes = sup.run_one_cycle([svc], states, observe=False)
    entry = outcomes[0]
    assert entry["action"] == "restart" and entry["executed"] is True, entry
    assert entry["restart_exit"] == 0
    assert entry["restart_stdout_head"] == [
        str(REPO_ROOT)
    ], f"restart must run with cwd=REPO_ROOT ({REPO_ROOT}), got {entry['restart_stdout_head']}"


def test_observe_mode_withholds_restart(decoy_factory, alert_redirect):
    svc = {
        "name": "observed",
        "port": _free_port(),  # red
        "restart_cmd": "exit 7",  # would fail loudly if ever executed
        "policy": {"fail_threshold": 1, "cooldown_s": 0, "max_restarts_per_hour": 5},
    }
    states: dict = {}
    _, outcomes = sup.run_one_cycle([svc], states, observe=True)
    entry = outcomes[0]
    assert entry["action"] == "restart"
    assert entry["executed"] is False, "observe mode must never execute restarts"
    assert (
        alert_redirect.exists()
        and "restart_withheld_observe" in alert_redirect.read_text(encoding="utf-8")
    )


def test_restart_cap_alerts_instead_of_looping(alert_redirect):
    svc = {
        "name": "capped",
        "port": _free_port(),
        "restart_cmd": "true",
        "policy": {"fail_threshold": 1, "cooldown_s": 0, "max_restarts_per_hour": 2},
    }
    states: dict = {}
    actions = []
    for _ in range(4):
        _, outcomes = sup.run_one_cycle([svc], states, observe=False)
        actions.append(outcomes[0]["action"])
    assert actions[:2] == ["restart", "restart"]
    assert actions[2] == "alert", f"third failure within the hour must ALERT: {actions}"
    assert actions[3] == "alert"
    assert "restart_cap_alert" in alert_redirect.read_text(encoding="utf-8")


def test_fix557_owner_precheck_real_and_negative(monkeypatch):
    """Real (read-only) precheck on this machine + FIX-563 semantics matrix.

    FIX-563 inverted the ownership truth table: this repo's container is
    repo-unique (sparkle_proj_db), so ``sparkle-project_*`` mounts are OURS
    (green), a foreign ``sparkle-cosmos_*`` mount on our container is the
    violation (RED), and an absent container is nothing-to-guard (green).
    """
    real = sup.check_data_plane_owner()
    assert real["check"] == "data_plane_owner"
    if real["ok"] and "absent" not in real.get("detail", ""):
        assert "sparkle-project_" in real["detail"], real
    elif not real["ok"]:
        # Docker daemon down (or other inspect failure) — must say why.
        assert real["detail"], real

    class FakeOut:
        def __init__(self, returncode=0, stdout="", stderr=""):
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = stderr

    # Foreign volume attached to OUR container → RED + actionable note.
    monkeypatch.setattr(
        sup.subprocess,
        "run",
        lambda *a, **k: FakeOut(stdout="sparkle-cosmos_sparkle_postgres_data "),
    )
    foreign = sup.check_data_plane_owner()
    assert foreign["ok"] is False
    assert "FIX-563" in foreign["note"] and "RESTACK_RUNBOOK" in foreign["note"]

    # Our own volume → GREEN (post-FIX-563 this is the owner, not a violation).
    monkeypatch.setattr(
        sup.subprocess,
        "run",
        lambda *a, **k: FakeOut(stdout="sparkle-project_sparkle_postgres_data "),
    )
    ours = sup.check_data_plane_owner()
    assert ours["ok"] is True

    # Absent container → GREEN with an explanatory note (unique names cannot
    # shadow foreign volumes — the FIX-557 accident form is structurally dead).
    monkeypatch.setattr(
        sup.subprocess,
        "run",
        lambda *a, **k: FakeOut(returncode=1, stderr="Error: No such object: sparkle_proj_db"),
    )
    absent = sup.check_data_plane_owner()
    assert absent["ok"] is True
    assert "absent" in absent["detail"]


def tmp_cfg(port: int, tmp: Path | None = None) -> Path:
    cfg_path = Path(tempfile_dir()) / f"sup_cfg_{port}.json"
    cfg_path.write_text(
        json.dumps(
            {
                "services": [
                    {
                        "name": "decoy",
                        "port": port,
                        "health_url": f"http://127.0.0.1:{port}/",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    return cfg_path


def tempfile_dir() -> str:
    import tempfile

    return tempfile.gettempdir()
