#!/usr/bin/env python3
"""Verify OpenAPI contract snapshot has no unintended drift."""

from __future__ import annotations

import argparse
import difflib
import json
import subprocess
import sys
from pathlib import Path


def _preferred_python(repo_root: Path) -> str:
    backend_venv = repo_root / "backend" / ".venv" / "bin" / "python"
    if backend_venv.exists():
        return str(backend_venv)
    return sys.executable


def _load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeError(f"Missing snapshot file: {path}") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description="Check OpenAPI contract drift")
    parser.add_argument("--snapshot", default="docs/contracts/openapi_snapshot.json")
    parser.add_argument("--update", action="store_true", help="Regenerate snapshot in-place")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    snapshot_path = repo_root / args.snapshot
    generated_path = repo_root / "quality" / "openapi_snapshot.generated.json"
    python_bin = _preferred_python(repo_root)

    if args.update:
        subprocess.check_call(
            [python_bin, str(repo_root / "scripts" / "export_openapi_snapshot.py"), "--output", args.snapshot],
            cwd=repo_root,
        )
        print("✅ OpenAPI snapshot updated")
        return 0

    subprocess.check_call(
        [python_bin, str(repo_root / "scripts" / "export_openapi_snapshot.py"), "--output", str(generated_path.relative_to(repo_root))],
        cwd=repo_root,
    )

    expected = _load_json(snapshot_path)
    actual = _load_json(generated_path)

    if expected != actual:
        expected_str = json.dumps(expected, ensure_ascii=False, indent=2).splitlines()
        actual_str = json.dumps(actual, ensure_ascii=False, indent=2).splitlines()
        diff = "\n".join(
            difflib.unified_diff(
                expected_str,
                actual_str,
                fromfile=str(snapshot_path),
                tofile=str(generated_path),
                lineterm="",
            )
        )
        print("❌ OpenAPI contract drift detected.")
        print("Run: python3 scripts/check_openapi_contract.py --update")
        print(diff[:12000])
        return 1

    print("✅ OpenAPI contract check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
