from __future__ import annotations

from datetime import datetime
from pathlib import Path
from uuid import uuid4

from app.services.scene_consolidation_service import SceneConsolidationService
from tests.unit.scene_test_helpers import make_memory


def test_scene_title_uses_time_slot_and_topic_tags(db_session) -> None:
    service = SceneConsolidationService(db_session)
    memories = [
        make_memory(
            user_id=uuid4(),
            summary="周末晨间刷数学题",
            occurred_at=datetime(2026, 4, 19, 9, 0, 0),
            embedding=[0.9, 0.1],
            tags=["topic:数学"],
            subject_type="study",
        )
    ]

    title, summary = service._compose_title_summary(
        memories=memories,
        time_start=memories[0].occurred_at,
        time_end=memories[0].occurred_at,
    )

    assert "周末早晨" in title
    assert "数学" in title
    assert "学习" in summary


def test_scene_summary_is_capped_at_200_characters(db_session) -> None:
    service = SceneConsolidationService(db_session)
    memories = [
        make_memory(
            user_id=uuid4(),
            summary="超长主题" * 50,
            occurred_at=datetime(2026, 4, 19, 9, 0, 0),
            embedding=[0.9, 0.1],
            tags=["topic:" + ("超长主题" * 50)],
        )
    ]

    _, summary = service._compose_title_summary(
        memories=memories,
        time_start=memories[0].occurred_at,
        time_end=memories[0].occurred_at,
    )

    assert len(summary) <= 200


def test_scene_title_builder_has_no_llm_imports() -> None:
    backend_root = Path(__file__).resolve().parents[2]
    source = (backend_root / "app" / "services" / "scene_consolidation_service.py").read_text(encoding="utf-8")

    assert "openai" not in source.lower()
    assert "anthropic" not in source.lower()
    assert "llm_" not in source.lower()
