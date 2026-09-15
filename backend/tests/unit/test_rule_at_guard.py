from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "guards" / "check_rule_at_no_orphan.py"
sys.path.insert(0, str(REPO_ROOT))

from scripts.guards.check_rule_at_no_orphan import scan_rule_at


def test_rule_at_guard_passes_on_repo() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        check=False,
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    assert result.returncode == 0, result.stderr or result.stdout


def test_rule_at_guard_flags_orphan_service(tmp_path) -> None:
    backend_app = tmp_path / "backend" / "app"
    services = backend_app / "services"
    docs = tmp_path / "docs" / "aurora"
    services.mkdir(parents=True)
    docs.mkdir(parents=True)
    orphan = services / "orphan_service.py"
    orphan.write_text("class OrphanService:\n    pass\n", encoding="utf-8")
    (docs / "rule_at_exceptions.md").write_text("# Rule AT exceptions\n", encoding="utf-8")

    violations = scan_rule_at(repo_root=tmp_path)

    assert any("orphan_service.py" in item for item in violations)
