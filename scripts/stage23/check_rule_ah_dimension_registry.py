from __future__ import annotations

from pathlib import Path

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
    doc_path = Path("docs/aurora/rule_ah_dimension_registry.md")
    if not doc_path.exists():
        raise SystemExit("FAIL rule ah registry: markdown missing")

    text = doc_path.read_text(encoding="utf-8")
    missing = [name for name in SOURCE_STATE_DIMENSION_ORDER if f"`{name}`" not in text]
    if missing:
        raise SystemExit(f"FAIL rule ah registry: missing markdown entries for {missing}")

    encoder_path = Path("backend/app/services/source_state_encoder.py")
    encoder_text = encoder_path.read_text(encoding="utf-8")
    for name in SOURCE_STATE_DIMENSION_ORDER:
        if f'"{name}"' not in encoder_text:
            raise SystemExit(f"FAIL rule ah registry: encoder missing dimension {name}")

    print(f"PASS rule ah registry: dimensions={len(SOURCE_STATE_DIMENSION_ORDER)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
