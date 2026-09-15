#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PUBLISH_TARGETS = (
    "backend/app/services/task_service.py",
    "backend/app/services/simulation/simulation_engine.py",
    "backend/app/services/seed_library_service.py",
    "backend/app/services/theater/prediction_theater_service.py",
    "backend/app/services/shop_service.py",
    "backend/app/services/stage33_journey_event_service.py",
)
CONSUMER_TARGETS = (
    "backend/app/consumers/journey_consumer_base.py",
    "backend/app/consumers/plan_task_generation_consumer.py",
    "backend/app/consumers/user_memory_seed_consumer.py",
    "backend/app/services/galaxy_event_consumer.py",
)
BARE_PUBLISH_TOKENS = (
    "event_bus.publish(",
    "self.event_bus.publish(",
)
RELIABLE_PUBLISH_TOKENS = (
    "event_bus_reliable.publish(",
    "self.event_bus_reliable.publish(",
)
RELIABLE_CONSUMER_TOKENS = (
    "@reliable_consumer",
    "JourneyEventConsumerBase",
)


def scan_rule_az(*, repo_root: Path | None = None) -> list[str]:
    repo_root = repo_root or REPO_ROOT
    violations: list[str] = []

    for rel_path in PUBLISH_TARGETS:
        path = repo_root / rel_path
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for token in BARE_PUBLISH_TOKENS:
            if token in text:
                violations.append(f"AZ001 {rel_path} contains bare publish token `{token}`")
        if ".publish(" in text and not any(token in text for token in RELIABLE_PUBLISH_TOKENS):
            violations.append(f"AZ002 {rel_path} does not publish through event_bus_reliable")

    for rel_path in CONSUMER_TARGETS:
        path = repo_root / rel_path
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        if any(token in text for token in RELIABLE_CONSUMER_TOKENS):
            continue
        violations.append(f"AZ003 {rel_path} is missing reliable_consumer coverage")

    return violations


def main() -> int:
    violations = scan_rule_az()
    if violations:
        print("[Rule AZ] FAIL")
        for violation in violations:
            print(violation)
        return 1
    print("[Rule AZ] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
