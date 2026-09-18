#!/usr/bin/env python3
"""Rule BM: R2-08 dead gateway routes stay removed.

The P3 gateway sweep (2026-09-18) deleted 16 dead proxy registrations and
corrected POST /exam-sprint/completion to GET per the R2-08 §2.2 route audit
(see docs/competition/2026-tmall-hackathon/系统审查/round2/08-r2-fixes.md §5).
This guard fails if any of those dead surfaces reappear in the gateway, or if
the corrected method regresses.

Evasion hatch: annotate the offending line with `rule-bm: ignore <reason>`.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PROXY_ROUTES_PATH = REPO_ROOT / "backend/gateway/internal/handler/proxy_routes.go"
GALAXY_HANDLER_PATH = REPO_ROOT / "backend/gateway/internal/handler/galaxy_handler.go"

# Go registration fragments that must never reappear (whitespace-normalized
# substrings of `x.<METHOD>("path", ...)` registrations).
FORBIDDEN_REGISTRATIONS = [
    'cards.GET("",',
    'cards.POST("",',
    'cards.PUT("/*path",',
    'cards.PATCH("/*path",',
    'tasks.GET("/suggestions",',
    'tasks.POST("/:id/reopen",',
    'goals.PATCH("/:id",',
    'cqrs.GET("/dlq/stats",',
    'community.POST("/messages/private",',
    'community.GET("/messages/private/:user_id",',
    'community.DELETE("/messages/private/:msg_id",',
    'community.PATCH("/posts/:post_id",',
    'community.DELETE("/groups/:group_id/leave",',
    'community.DELETE("/groups/:group_id/messages/:msg_id",',
    'community.POST("/share/:share_id/adopt",',
    'galaxy.GET("/nodes",',
]

# The one method correction from the sweep: GET must stay, POST must not.
EXAM_COMPLETION_GET = 'examSprint.GET("/completion",'
EXAM_COMPLETION_POST = 'examSprint.POST("/completion",'

IGNORE_RE = re.compile(r"rule-bm:\s*ignore\s+.+", re.IGNORECASE)


def _scan(path: Path) -> list[str]:
    failures: list[str] = []
    if not path.exists():
        failures.append(f"required file missing: {path.relative_to(REPO_ROOT)}")
        return failures

    for lineno, raw in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        line = raw.strip()
        if IGNORE_RE.search(line):
            continue
        for fragment in FORBIDDEN_REGISTRATIONS:
            if fragment in line:
                failures.append(
                    f"{path.relative_to(REPO_ROOT)}:{lineno}: dead route "
                    f"re-registered: {fragment}... (R2-08 §2.2; annotate with "
                    f"`rule-bm: ignore <reason>` if the engine gained this surface)"
                )
        if path == PROXY_ROUTES_PATH:
            if EXAM_COMPLETION_POST in line:
                failures.append(
                    f"{path.relative_to(REPO_ROOT)}:{lineno}: POST "
                    f"/exam-sprint/completion re-registered — the engine only "
                    f"serves GET (R2-08 §2.2 #10)"
                )
            if EXAM_COMPLETION_GET in line:
                continue  # required; checked below

    if path == PROXY_ROUTES_PATH:
        text = path.read_text(encoding="utf-8")
        if EXAM_COMPLETION_GET not in text and not IGNORE_RE.search(text):
            failures.append(
                f"{path.relative_to(REPO_ROOT)}: GET /exam-sprint/completion "
                f"registration missing (R2-08 §2.2 #10 correction removed?)"
            )
    return failures


def main() -> int:
    failures = _scan(PROXY_ROUTES_PATH) + _scan(GALAXY_HANDLER_PATH)
    if failures:
        print("RULE BM FAILED: R2-08 dead gateway routes must stay removed")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("RULE BM OK: R2-08 dead gateway routes remain removed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
