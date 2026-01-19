import pytest

from app.models.user import User
from app.scaffolding.scaffolding_fsm import ScaffoldingFSM


@pytest.mark.asyncio
async def test_scaffolding_fsm_updates_support_level(db_session):
    user = User(
        username="tester",
        email="tester@example.com",
        hashed_password="hashed",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    fsm = ScaffoldingFSM(db_session)
    state = await fsm.get_state(user.id)
    assert state.support_level == 3

    for _ in range(3):
        await fsm.apply_feedback(user.id, success=True)

    state = await fsm.get_state(user.id)
    assert state.support_level == 2

    for _ in range(2):
        await fsm.apply_feedback(user.id, success=False)

    state = await fsm.get_state(user.id)
    assert state.support_level == 3
