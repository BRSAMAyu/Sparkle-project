#!/usr/bin/env python3
from __future__ import annotations

import argparse
import collections
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
HEADER_TOKENS = ("Core:", "Phase:", "Stage:")
DEFAULT_LIMIT = 50
DEFAULT_THRESHOLD = 0.40


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check Core/Phase header coverage on the hot file set.")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    return parser.parse_args()


def _candidate_files() -> list[Path]:
    files: list[Path] = []
    for root, suffix in ((REPO_ROOT / "backend/app", ".py"), (REPO_ROOT / "backend/gateway", ".go")):
        for path in root.rglob(f"*{suffix}"):
            if any(part in {"__pycache__", "gen", "vendor"} for part in path.parts):
                continue
            head = "\n".join(path.read_text(encoding="utf-8").splitlines()[:5])
            if "Code generated" in head and "DO NOT EDIT" in head:
                continue
            files.append(path)
    return files


def _hot_files(limit: int) -> list[Path]:
    candidates = {path.relative_to(REPO_ROOT).as_posix(): path for path in _candidate_files()}
    result = subprocess.run(
        ["git", "log", "--format=", "--name-only", "--", "backend/app", "backend/gateway"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    counter: collections.Counter[str] = collections.Counter()
    for raw in result.stdout.splitlines():
        path = raw.strip()
        if path in candidates:
            counter[path] += 1
    ranked = sorted(candidates, key=lambda item: (-counter[item], item))
    return [candidates[item] for item in ranked[: max(1, limit)]]


def _has_header(path: Path) -> bool:
    head = "\n".join(path.read_text(encoding="utf-8").splitlines()[:20])
    return all(token in head for token in HEADER_TOKENS)


def main() -> int:
    args = parse_args()
    files = _hot_files(args.limit)
    covered = [path for path in files if _has_header(path)]
    coverage = (len(covered) / len(files)) if files else 1.0

    if coverage < args.threshold:
        print("[Core/Phase Header] FAIL")
        print(f"coverage={coverage:.2%} threshold={args.threshold:.0%} covered={len(covered)} total={len(files)}")
        for path in files:
            if path not in covered:
                print(path.relative_to(REPO_ROOT).as_posix())
        return 1

    print(
        f"[Core/Phase Header] PASS - coverage={coverage:.2%} "
        f"covered={len(covered)} total={len(files)} threshold={args.threshold:.0%}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
