from __future__ import annotations

import json
from pathlib import Path

INPUT_PATH = Path("docs/product/stage23_synthetic_density.json")
SOURCE_STATE_DIMENSION_ORDER = (
    "tool_category",
    "sufficiency_level",
    "conflict_outcome",
    "skill_domain",
    "achievement_tier",
    "calendar_pressure",
    "cohort_segment",
)


def main() -> int:
    if not INPUT_PATH.exists():
        raise SystemExit("FAIL data density: synthetic density artifact missing")

    payload = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
    failures: list[str] = []
    for user in payload.get("users", []):
        pairs = user.get("pairs", [])
        if len(pairs) < 150:
            failures.append(f"{user.get('user_id')}:pair_count={len(pairs)}")
            continue
        covered = {
            name
            for name in SOURCE_STATE_DIMENSION_ORDER
            if len({pair.get("source_state", {}).get(name) for pair in pairs}) > 1
        }
        if len(covered) < 5:
            failures.append(f"{user.get('user_id')}:dimension_coverage={len(covered)}")
        success_count = sum(1 for pair in pairs if pair.get("success"))
        ratio = success_count / len(pairs)
        if not 0.25 <= ratio <= 0.75:
            failures.append(f"{user.get('user_id')}:success_ratio={ratio:.3f}")

    if failures:
        raise SystemExit("FAIL data density:\n" + "\n".join(failures))

    print(f"PASS data density: users={len(payload.get('users', []))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
