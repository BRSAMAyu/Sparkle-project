#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.db.session import AsyncSessionLocal  # noqa: E402
from app.services.card_protocol.consistency_validator import (  # noqa: E402
    CardProtocolConsistencyValidator,
)


async def _run(limit: int | None, output_json: bool) -> int:
    async with AsyncSessionLocal() as db:
        issues = await CardProtocolConsistencyValidator(db).validate(limit=limit)

    critical_count = sum(1 for issue in issues if issue.severity == "critical")
    warning_count = sum(1 for issue in issues if issue.severity == "warning")
    if output_json:
        print(
            json.dumps(
                {
                    "ok": critical_count == 0,
                    "critical_count": critical_count,
                    "warning_count": warning_count,
                    "issues": [issue.to_dict() for issue in issues],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print(
            "Card Protocol dual-write consistency: "
            f"{critical_count} critical, {warning_count} warning"
        )
        for issue in issues:
            print(
                f"[{issue.severity.upper()}] {issue.code} "
                f"{issue.entity_type}:{issue.entity_id} — {issue.message}"
            )
    return 1 if critical_count else 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate legacy Plan/Task rows against Card Protocol projections.",
    )
    parser.add_argument("--limit", type=int, default=None, help="Limit recent legacy plans/tasks checked.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    args = parser.parse_args()
    return asyncio.run(_run(args.limit, args.json))


if __name__ == "__main__":
    raise SystemExit(main())
