from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID, uuid4

from app.models.memory import EpisodicMemory, Scene
from app.services.scene_consolidation_service import build_scene_id


def make_memory(
    *,
    user_id: UUID,
    summary: str,
    occurred_at: datetime,
    embedding: list[float] | None = None,
    source_type: str = "chat",
    source_lane: str = "inferred_extraction",
    subject_type: str = "self",
    tags: list[str] | None = None,
) -> EpisodicMemory:
    return EpisodicMemory(
        user_id=user_id,
        summary=summary,
        source_type=source_type,
        source_id="session-1",
        source_lane=source_lane,
        subject_type=subject_type,
        occurred_at=occurred_at,
        importance_score=0.9,
        confidence=0.92,
        evidence_score=0.8,
        correction_count=0,
        evidence_refs=[{"type": "chat_turn", "id": "turn-1", "schema_version": "stage26.test.v1"}],
        tags=tags or [],
        embedding=embedding,
    )


def make_scene(
    *,
    user_id: UUID,
    member_memory_ids: list[str],
    title: str = "周末早晨自我场景 · 数学",
    summary: str = "周末早晨聚合了 3 条自我相关记忆，主题集中在 数学。",
    quality_score: float = 0.8,
    time_start: datetime | None = None,
    time_end: datetime | None = None,
    centroid_embedding: list[float] | None = None,
    version: str = "scene.v1",
) -> Scene:
    start = time_start or datetime(2026, 4, 19, 9, 0, 0)
    end = time_end or start + timedelta(hours=2)
    now = datetime(2026, 4, 21, 9, 0, 0)
    return Scene(
        scene_id=build_scene_id(
            user_id=user_id,
            member_memory_ids=member_memory_ids,
            version=version,
        ),
        user_id=user_id,
        title=title,
        summary=summary,
        member_memory_ids=member_memory_ids,
        centroid_embedding=centroid_embedding or [0.9, 0.1, 0.0],
        time_start=start,
        time_end=end,
        quality_score=quality_score,
        version=version,
        created_at=now,
        updated_at=now,
    )


def random_user_id() -> UUID:
    return uuid4()
