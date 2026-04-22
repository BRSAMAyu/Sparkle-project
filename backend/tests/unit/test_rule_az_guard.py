from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "guards" / "check_rule_az_eventbus_reliability.py"
sys.path.insert(0, str(REPO_ROOT))

from scripts.guards.check_rule_az_eventbus_reliability import scan_rule_az


def test_rule_az_guard_passes_on_repo() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        check=False,
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    assert result.returncode == 0, result.stderr or result.stdout


def test_rule_az_guard_flags_bare_publish(tmp_path) -> None:
    target = tmp_path / "backend" / "app" / "services"
    target.mkdir(parents=True)
    task_service = target / "task_service.py"
    task_service.write_text(
        "from app.core.event_bus import event_bus\n\nasync def publish_event():\n    await event_bus.publish('task.started', {})\n",
        encoding="utf-8",
    )

    violations = scan_rule_az(repo_root=tmp_path)

    assert any("AZ001" in item and "task_service.py" in item for item in violations)
