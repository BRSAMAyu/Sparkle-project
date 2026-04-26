from pathlib import Path


def test_f11_achievement_events_have_process_event_publishers() -> None:
    backend_root = Path(__file__).resolve().parents[2]
    call_points = {
        "CONTRACT_COMPLETED": backend_root / "app/services/achievement_engine.py",
        "CONTRACT_FAILED": backend_root / "app/api/v1/achievements.py",
        "MUTUAL_STUDY": backend_root / "app/api/v1/accountability.py",
        "HIDDEN_TRIGGER": backend_root / "app/services/achievement_event_consumer.py",
        "SPRINT_STARTED": backend_root / "app/consumers/achievement_plan_consumer.py",
        "SPRINT_ABANDONED": backend_root / "app/api/v1/plans.py",
        "DAILY_CHECKIN": backend_root / "app/api/v1/accountability.py",
        "WEEKEND_WARRIOR": backend_root / "app/services/achievement_event_consumer.py",
    }

    missing: list[str] = []
    for event_name, path in call_points.items():
        source = path.read_text(encoding="utf-8")
        if f"AchievementEvent.{event_name}" not in source or "process_event(" not in source:
            missing.append(f"{event_name} in {path.relative_to(backend_root)}")

    assert missing == []
