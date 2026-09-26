"""V3-FIX-260 wire 对齐钉：AchievementType 11 值（含 planning）过 wire 不失真。

后端 AchievementType.PLANNING 是后端单面新增（DB 迁移 r20807 已重建 11 小写值），
本卡修 mobile 侧镜像缺口；此处钉住后端三面一致性，防止未来再次单面漂移：
1. ORM StrEnum 值序 == DB 迁移重建的 11 小写值；
2. Pydantic wire 序列化/反序列化 planning 值无损；
3. OpenAPI 快照（docs/contracts/openapi_snapshot.json）值集与枚举一致。
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from app.models.achievement import AchievementRarity, AchievementType
from app.schemas.achievement import AchievementBase

REPO_ROOT = Path(__file__).resolve().parents[3]

# 与 alembic/versions/r20807_achievementtype_lowercase_20260918.py 重建值逐一对齐
EXPECTED_WIRE_VALUES = [
    "milestone",
    "streak",
    "mastery",
    "task_complete",
    "hidden",
    "social",
    "contract",
    "study_time",
    "node_explore",
    "sprint",
    "planning",
]


def test_achievement_type_enum_matches_db_rebuilt_wire_values():
    assert [member.value for member in AchievementType] == EXPECTED_WIRE_VALUES


def test_planning_survives_pydantic_wire_roundtrip():
    payload = {
        "id": "ach-planning",
        "created_at": "2026-09-25T00:00:00Z",
        "updated_at": "2026-09-25T00:00:00Z",
        "name": "规划成就",
        "type": "planning",
        "rarity": "rare",
    }

    decoded = AchievementBase.model_validate(payload)
    assert decoded.type is AchievementType.PLANNING

    encoded = AchievementBase(
        id="ach-planning",
        created_at=datetime(2026, 9, 25, tzinfo=timezone.utc),
        updated_at=datetime(2026, 9, 25, tzinfo=timezone.utc),
        name="规划成就",
        type=AchievementType.PLANNING,
        rarity=AchievementRarity.RARE,
    ).model_dump(mode="json")
    assert encoded["type"] == "planning"


def test_openapi_snapshot_pins_achievement_type_value_set():
    snapshot_path = REPO_ROOT / "docs" / "contracts" / "openapi_snapshot.json"
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    schema = snapshot["components"]["schemas"]["AchievementType"]

    assert schema["enum"] == EXPECTED_WIRE_VALUES
