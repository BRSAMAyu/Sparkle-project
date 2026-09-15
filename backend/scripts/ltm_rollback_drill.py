from __future__ import annotations

from app.config import settings


FLAGS = [
    "USE_CONTEXT_PACK",
    "ANALYSIS_SYNC_ON_EVENT",
    "ENABLE_EVIDENCE_HEALTH_JOB",
    "ENABLE_BEHAVIOR_DECAY",
    "ENABLE_MEMORY_RETRACTION",
    "USE_CONTEXT_INTENT_ROUTER",
    "ENABLE_MEMORY_PANEL",
    "ENABLE_MEMORY_GOVERNANCE",
    "ENABLE_MEMORY_EXPORT",
    "ENABLE_MEMORY_CORRECTION",
    "ENABLE_CONTEXT_PACK_TELEMETRY",
    "ENABLE_BUDGET_TUNING",
    "ENABLE_CONTEXT_RANKING",
    "ENABLE_MEMORY_CONFLICT_RESOLUTION",
    "ENABLE_PERSONALIZED_RANKING",
    "ENABLE_MEMORY_JOBS",
    "ENABLE_EVIDENCE_SNAPSHOT_ON_WRITE",
    "ENABLE_MEMORY_DECAY",
    "ENABLE_LTM_ROLLOUT",
]


def _flag_value(name: str) -> str:
    return "on" if getattr(settings, name, False) else "off"


def main() -> None:
    print("LTM Rollback Drill")
    print("===================")
    print("Current flags:")
    for name in FLAGS:
        print(f"- {name}: {_flag_value(name)}")

    print("\nRecommended rollback order:")
    print("1) Disable rollout gates and advanced pack features")
    print("2) Disable memory jobs + evidence snapshot on write")
    print("3) Disable memory corrections/retractions + governance endpoints")
    print("4) Disable context pack and analysis sync")

    print("\nFlags to switch off (in order):")
    ordered = [
        "ENABLE_LTM_ROLLOUT",
        "ENABLE_BUDGET_TUNING",
        "ENABLE_CONTEXT_RANKING",
        "ENABLE_MEMORY_CONFLICT_RESOLUTION",
        "ENABLE_PERSONALIZED_RANKING",
        "ENABLE_CONTEXT_PACK_TELEMETRY",
        "ENABLE_MEMORY_JOBS",
        "ENABLE_EVIDENCE_SNAPSHOT_ON_WRITE",
        "ENABLE_MEMORY_DECAY",
        "ENABLE_MEMORY_CORRECTION",
        "ENABLE_MEMORY_RETRACTION",
        "ENABLE_MEMORY_GOVERNANCE",
        "ENABLE_MEMORY_EXPORT",
        "USE_CONTEXT_PACK",
        "ANALYSIS_SYNC_ON_EVENT",
    ]
    for name in ordered:
        value = _flag_value(name)
        status = "ready" if value == "on" else "already_off"
        print(f"- {name}: {status}")

    print("\nValidation:")
    missing = [name for name in ordered if not hasattr(settings, name)]
    if missing:
        print(f"- Missing config keys: {', '.join(missing)}")
    else:
        print("- All rollback flags present in config")


if __name__ == "__main__":
    main()
