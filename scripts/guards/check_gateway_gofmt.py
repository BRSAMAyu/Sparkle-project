#!/usr/bin/env python3
r"""GOFMT-GW — repo-wide `gofmt -l` over backend/gateway.

Incident (2026-09, CI run 36080561418): CI died at the lint-first gate on
`backend/gateway/internal/middleware/s2_ticket_budget_repro_test.go` being
not gofmt-formatted. The 83 local rule guards had no Go formatting check at
all — the format drift shipped all the way to CI before anyone saw it.
The file itself was fixed in d680a891 (pure whitespace); this guard closes
the blind spot so the next drift dies locally, not in CI.

Why repo-wide and not new-from-rev: CI's golangci-lint runs with
`new-from-rev: e6256a3` (see backend/gateway/.golangci.yml), so findings on
or before the baseline revision do not block — a formatting regression in
touched-but-old files can slip. This guard runs plain `gofmt -l` over the
whole backend/gateway tree with no baseline: output non-empty => fail,
listing every unformatted file. Stricter than CI on purpose; local guards
exist to intercept earlier than CI, not to mirror it.

Scope alignment with backend/gateway/.golangci.yml excludes: generated
protobuf code (*.pb.go) and vendor/mocks trees are out of scope, matching
the lint config's "never lint generated protobuf code" policy.

golangci-lint itself is intentionally NOT part of this guard: CI pins the
golangci-lint-action at `version: latest` (floating) and gates on a
git-history-dependent new-from-rev, so a local run cannot guarantee CI
equivalence and would flake on version drift. gofmt formatting is the
stable, deterministic subset — the CI golangci run remains the backstop
for the rest.

Known accepted limitation: `gofmt -l` walks the full tree (no testdata
skip, unlike `go test`). A future intentionally-misformatted Go fixture
under backend/gateway would need an explicit exemption added here —
reviewable, fail-closed default.

Exit: 0 on pass, 1 on any unformatted file / environment problem
(missing gofmt fails closed, never silently green).
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
GATEWAY_DIR = REPO_ROOT / "backend" / "gateway"

# Mirrors backend/gateway/.golangci.yml issue exclusions (exclude-dirs
# vendor/mocks; "never lint generated protobuf code").
EXCLUDED_DIR_NAMES = {"vendor", "mocks"}
EXCLUDED_SUFFIXES = (".pb.go",)


def _is_excluded(path: Path) -> bool:
    if path.name.endswith(EXCLUDED_SUFFIXES):
        return True
    return any(part in EXCLUDED_DIR_NAMES for part in path.parts)


def _rel(path: Path) -> Path:
    try:
        return path.relative_to(REPO_ROOT)
    except ValueError:
        return path


def main() -> int:
    if not GATEWAY_DIR.is_dir():
        print(f"[GOFMT-GW] FAIL: gateway dir not found: {GATEWAY_DIR}", file=sys.stderr)
        return 1

    gofmt = shutil.which("gofmt")
    if gofmt is None:
        print(
            "[GOFMT-GW] FAIL: gofmt not found on PATH — install Go; "
            "guard fails closed rather than silently passing.",
            file=sys.stderr,
        )
        return 1

    result = subprocess.run(
        [gofmt, "-l", str(GATEWAY_DIR)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"[GOFMT-GW] FAIL: gofmt exited {result.returncode}", file=sys.stderr)
        if result.stderr.strip():
            print(result.stderr.strip(), file=sys.stderr)
        return 1

    unformatted = sorted(
        Path(line.strip())
        for line in result.stdout.splitlines()
        if line.strip() and not _is_excluded(Path(line.strip()))
    )

    if not unformatted:
        print(f"[GOFMT-GW] PASS: {GATEWAY_DIR.relative_to(REPO_ROOT)} is gofmt-clean")
        return 0

    print(
        f"[GOFMT-GW] FAIL: {len(unformatted)} file(s) in backend/gateway "
        "not gofmt-formatted (CI golangci-lint gofmt linter will block):",
        file=sys.stderr,
    )
    for path in unformatted:
        print(f"  {_rel(path)}", file=sys.stderr)
    print("remediation: gofmt -w backend/gateway", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
