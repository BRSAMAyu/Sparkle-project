#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
TARGETS = [
    REPO_ROOT / "backend" / "app" / "services" / "traits_nlp_observer_service.py",
    REPO_ROOT / "backend" / "app" / "services" / "traits_coldstart_service.py",
    REPO_ROOT / "docs" / "aurora" / "stage28_coldstart_questions.md",
    REPO_ROOT / "docs" / "aurora" / "stage28_nlp_bias_calibration.md",
]
FORBIDDEN = ("你是", "你属于", "内向型", "外向型", "人格诊断")


def main() -> int:
    for path in TARGETS:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for token in FORBIDDEN:
            if token in text:
                raise AssertionError(f"diagnostic label token found in {path}: {token}")
    print("No diagnostic labels detected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
