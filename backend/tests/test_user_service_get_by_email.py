import pytest

from app.models.user import User
from app.services.user_service import UserService


@pytest.mark.asyncio
async def test_get_by_email_returns_user(db_session):
    user = User(
        username="testuser",
        email="testuser@example.com",
        hashed_password="not-a-real-hash",
        nickname="Tester",
        registration_source="email",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    fetched = await UserService.get_by_email(db_session, email=user.email)

    assert fetched is not None
    assert fetched.id == user.id
    assert fetched.email == user.email
