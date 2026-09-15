from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
RUNNER = REPO_ROOT / "scripts" / "run_all_rule_guards.sh"


def _write_script(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


def test_guard_runner_passes_when_all_rules_pass(tmp_path) -> None:
    pass_a = tmp_path / "pass_a.sh"
    pass_b = tmp_path / "pass_b.sh"
    _write_script(pass_a, "#!/usr/bin/env bash\necho A\n")
    _write_script(pass_b, "#!/usr/bin/env bash\necho B\n")

    manifest = tmp_path / "guards.tsv"
    manifest.write_text(f"A\t\"{pass_a}\"\nB\t\"{pass_b}\"\n", encoding="utf-8")

    result = subprocess.run(
        [str(RUNNER), "--manifest", str(manifest)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "all rule guards passed" in result.stdout


def test_guard_runner_fails_on_single_rule_failure(tmp_path) -> None:
    ok = tmp_path / "ok.sh"
    bad = tmp_path / "bad.sh"
    _write_script(ok, "#!/usr/bin/env bash\necho ok\n")
    _write_script(bad, "#!/usr/bin/env bash\necho bad\nexit 3\n")

    manifest = tmp_path / "guards.tsv"
    manifest.write_text(f"A\t\"{ok}\"\nB\t\"{bad}\"\n", encoding="utf-8")

    result = subprocess.run(
        [str(RUNNER), "--manifest", str(manifest)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "rule guards failed: B" in result.stderr


def test_guard_runner_supports_single_rule_mode(tmp_path) -> None:
    selected = tmp_path / "selected.sh"
    skipped = tmp_path / "skipped.sh"
    marker = tmp_path / "selected.txt"
    _write_script(selected, f"#!/usr/bin/env bash\necho chosen > \"{marker}\"\n")
    _write_script(skipped, "#!/usr/bin/env bash\necho skipped\nexit 9\n")

    manifest = tmp_path / "guards.tsv"
    manifest.write_text(f"A\t\"{skipped}\"\nB\t\"{selected}\"\n", encoding="utf-8")

    result = subprocess.run(
        [str(RUNNER), "--manifest", str(manifest), "--rule", "B"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert marker.read_text(encoding="utf-8").strip() == "chosen"
    assert "[Rule A]" not in result.stdout


def test_guard_runner_supports_parallel_jobs(tmp_path) -> None:
    first = tmp_path / "first.sh"
    second = tmp_path / "second.sh"
    _write_script(first, "#!/usr/bin/env bash\nsleep 0.1\necho first\n")
    _write_script(second, "#!/usr/bin/env bash\nsleep 0.1\necho second\n")

    manifest = tmp_path / "guards.tsv"
    manifest.write_text(f"A\t\"{first}\"\nB\t\"{second}\"\n", encoding="utf-8")

    result = subprocess.run(
        [str(RUNNER), "--manifest", str(manifest), "--jobs", "2"],
        cwd=REPO_ROOT,
        env={**os.environ},
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "[Rule A] START" in result.stdout
    assert "[Rule B] START" in result.stdout
