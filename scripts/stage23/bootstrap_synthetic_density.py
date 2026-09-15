from __future__ import annotations

import json
from pathlib import Path

OUTPUT_PATH = Path("docs/product/stage23_synthetic_density.json")
PAIR_COUNT = 150
SOURCE_STATE_DIMENSION_ORDER = (
    "tool_category",
    "sufficiency_level",
    "conflict_outcome",
    "skill_domain",
    "achievement_tier",
    "calendar_pressure",
    "cohort_segment",
)


def _encode_source_state_key(source_state: dict[str, str]) -> str:
    return "|".join(f"{name}={source_state[name]}" for name in SOURCE_STATE_DIMENSION_ORDER)


def _build_pair(index: int, user_index: int) -> dict[str, object]:
    source_state = {
        "tool_category": ("chat", "plan", "task", "general")[index % 4],
        "sufficiency_level": ("low", "medium", "high")[index % 3],
        "conflict_outcome": ("clear", "pending", "resolved")[index % 3],
        "skill_domain": ("none", "plan", "focus", "reflection", "mixed")[index % 5],
        "achievement_tier": ("none", "emerging", "active", "advanced")[index % 4],
        "calendar_pressure": ("none", "low", "medium", "high")[(index + user_index) % 4],
        "cohort_segment": ("general", "exam_beginner", "habit_intermediate", "project_advanced")[index % 4],
    }
    outcome = ("plan_success", "task_completion", "user_correction", "timeout")[index % 4]
    return {
        "decision_id": f"synthetic-{user_index}-{index}",
        "source_state": source_state,
        "source_state_key": _encode_source_state_key(source_state),
        "target": ("direct", "langgraph", "hybrid")[index % 3],
        "outcome": outcome,
        "success": outcome in {"plan_success", "task_completion"},
    }


def main() -> int:
    users = []
    for user_index in range(3):
        user_id = f"synthetic__stage23__{user_index}"
        pairs = [_build_pair(index, user_index) for index in range(PAIR_COUNT)]
        users.append({"user_id": user_id, "pairs": pairs})

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(
            {
                "generated_at": "2026-04-21T23:30:00",
                "source_dimensions": list(SOURCE_STATE_DIMENSION_ORDER),
                "users": users,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"PASS synthetic density bootstrap: users={len(users)} pairs_per_user={PAIR_COUNT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
