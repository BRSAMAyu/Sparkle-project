#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SERVICE = REPO_ROOT / "backend/app/services/theater/prediction_theater_service.py"


def scan_rule_z_theater() -> list[str]:
    text = SERVICE.read_text(encoding="utf-8")
    violations: list[str] = []

    required_tokens = (
        "simulate_what_if(\n",
        "save_snapshot(\n",
        "promote_node_to_galaxy(\n",
        "adopt_prediction(\n",
        "record_actual_outcome(\n",
        "_get_prediction_for_user_or_raise(prediction_id, user_id=user_id)",
        "TheaterPrediction.user_id == user_id",
        "TheaterCandidateBundle.user_id == user_id",
    )
    for token in required_tokens:
        if token not in text:
            violations.append(f"ZT001 missing token `{token}` in {SERVICE}")

    if "message=\"resource access denied\"" not in text:
        violations.append("ZT002 theater denial message must stay fixed as `resource access denied`")
    if 'event_bus.publish("theater.access_denied"' not in text:
        violations.append("ZT003 theater access denial audit event is missing")

    return violations


def main() -> int:
    violations = scan_rule_z_theater()
    if violations:
        print("[Rule Z / theater_user_scope] FAIL")
        for violation in violations:
            print(violation)
        return 1
    print("[Rule Z / theater_user_scope] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
