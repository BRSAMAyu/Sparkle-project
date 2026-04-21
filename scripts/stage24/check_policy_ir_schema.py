#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.policy_ir import policy_ir_json_schema

SNAPSHOT_PATH = REPO_ROOT / "docs/aurora/stage24_policy_ir_schema_v1.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    current = policy_ir_json_schema()
    if args.write:
        SNAPSHOT_PATH.write_text(json.dumps(current, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("updated")
        return 0

    expected = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    if expected != current:
        print("IR schema drift detected")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
