from uuid import uuid4

import pytest

from app.models.user import User
from app.services.focus_service import FocusService


@pytest.mark.asyncio
async def test_heatmap_data_returns_zero_baseline_for_sparse_user(db_session):
    user = User(
        id=uuid4(),
        username="focus_sparse_user",
        email="focus_sparse_user@example.com",
        hashed_password="hashed",
    )
    db_session.add(user)
    await db_session.commit()

    heatmap = await FocusService.get_heatmap_data(db_session, user.id, days=90)

    assert len(heatmap) == 1
    assert list(heatmap.values()) == [0.0]
