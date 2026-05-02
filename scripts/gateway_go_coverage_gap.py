#!/usr/bin/env python3
"""Report Go gateway coverage shortfall in basis points.

The metric intentionally excludes generated protobuf packages under
backend/gateway/gen so the budget tracks hand-maintained gateway code.
"""

from __future__ import annotations

import argparse
import math
import subprocess
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
GATEWAY_DIR = REPO_ROOT / "backend" / "gateway"


def _normalize_path(value: str) -> str:
    return str(value).replace("\\", "/").strip().lstrip("./")


def _is_generated_go_package(file_path: str) -> bool:
    normalized = f"/{_normalize_path(file_path)}"
    return "/gen/" in normalized


def _run_go_coverage(profile: Path) -> None:
    proc = subprocess.run(
        ["go", "test", "-covermode=count", f"-coverprofile={profile}", "./..."],
        cwd=GATEWAY_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "go test failed")


def _coverage_percent(profile: Path) -> float:
    covered = 0
    total = 0
    for raw_line in profile.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("mode:"):
            continue
        parts = line.split()
        if len(parts) != 3:
            continue
        file_part, statement_count, hit_count = parts
        file_path = _normalize_path(file_part.split(":", 1)[0])
        if _is_generated_go_package(file_path):
            continue
        statements = int(statement_count)
        total += statements
        if int(hit_count) > 0:
            covered += statements
    if total == 0:
        raise RuntimeError(f"no non-generated Go coverage records in {profile}")
    return (covered / total) * 100.0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", help="Use an existing Go coverprofile instead of running go test")
    parser.add_argument("--target", type=float, default=65.0, help="Target coverage percentage")
    args = parser.parse_args()

    if args.profile:
        profile = Path(args.profile)
        if not profile.exists():
            raise FileNotFoundError(profile)
        coverage = _coverage_percent(profile)
    else:
        with tempfile.NamedTemporaryFile(prefix="sparkle-gateway-coverage-", suffix=".out") as handle:
            profile = Path(handle.name)
            _run_go_coverage(profile)
            coverage = _coverage_percent(profile)

    shortfall_bp = max(0, math.ceil((args.target - coverage) * 100))
    print(shortfall_bp)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"gateway_go_coverage_gap failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
