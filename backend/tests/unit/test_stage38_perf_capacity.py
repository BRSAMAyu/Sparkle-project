from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from unittest.mock import AsyncMock, MagicMock, Mock

from app.tasks.update_similarities import _update_learning_profiles


@pytest.mark.asyncio
async def test_update_learning_profiles_flushes_in_batches(monkeypatch):
    db = AsyncMock()
    db.add = Mock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()

    users_result = MagicMock()
    users_result.all.return_value = [(uuid4(),), (uuid4(),), (uuid4(),)]

    profile_result = MagicMock()
    profile_result.scalar_one_or_none.return_value = None

    db.execute = AsyncMock(side_effect=[users_result, profile_result, profile_result, profile_result])

    monkeypatch.setattr("app.tasks.update_similarities.SIMILARITY_BATCH_FLUSH_SIZE", 2)
    monkeypatch.setattr(
        "app.tasks.update_similarities._get_user_learning_stats",
        AsyncMock(
            side_effect=[
                {"subject_distribution": {"math": 1}, "total_study_minutes": 10, "total_items_completed": 1},
                {"subject_distribution": {"english": 2}, "total_study_minutes": 20, "total_items_completed": 2},
                {"subject_distribution": {"physics": 3}, "total_study_minutes": 30, "total_items_completed": 3},
            ]
        ),
    )

    updated = await _update_learning_profiles(db)

    assert updated == 3
    assert db.add.call_count == 3
    db.flush.assert_awaited_once()
    db.commit.assert_awaited_once()


def test_stage38_hnsw_migration_uses_concurrent_autocommit():
    migration_path = (
        Path(__file__).resolve().parents[2]
        / "alembic"
        / "versions"
        / "stage38_06_add_vector_hnsw_indexes.py"
    )
    content = migration_path.read_text(encoding="utf-8")

    assert "autocommit_block" in content
    assert "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_document_chunks_embedding_hnsw" in content
    assert "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_knowledge_nodes_embedding_hnsw" in content
    assert "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_episodic_memories_embedding_hnsw" in content
    assert "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_scenes_centroid_embedding_hnsw" in content
