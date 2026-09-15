"""
Integration Test Configuration

Uses real PostgreSQL database for WebSocket tests that communicate with gRPC server.
"""

import ssl

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.config import settings
from sqlalchemy import select
from sqlalchemy.engine import make_url

from app.models.base import Base
from app.models.user import User
from app.models.plan import Plan
from app.core.security import create_access_token
from typing import AsyncGenerator, Dict


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Use real PostgreSQL database for integration tests.
    This ensures test data is visible to the gRPC server.
    """
    db_url = settings.DATABASE_URL
    connect_args = {}

    # asyncpg does not accept sslmode in the URL; strip it and map to ssl args.
    parsed = make_url(db_url)
    if parsed.drivername.startswith("postgresql+asyncpg"):
        query = dict(parsed.query)
        sslmode = query.pop("sslmode", None)
        sslrootcert = query.pop("sslrootcert", None)
        if sslrootcert:
            connect_args["ssl"] = ssl.create_default_context(cafile=sslrootcert)
        elif sslmode == "disable":
            connect_args["ssl"] = False
        elif sslmode in ("require", "verify-ca", "verify-full"):
            connect_args["ssl"] = True
        db_url = parsed.set(query=query).render_as_string(hide_password=False)

    engine = create_async_engine(db_url, echo=False, connect_args=connect_args)

    # Don't create tables - assume they already exist from migrations
    # async with engine.begin() as conn:
    #     await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        yield session

    # Note: Test users are cleaned up by the test_user fixture
    # We don't do global cleanup here to avoid foreign key issues

    await engine.dispose()


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user in PostgreSQL for integration tests"""
    from app.services.user_service import user_service

    user_data = {
        "username": "websocket_test_user",
        "email": "websocket_test@example.com",
        "nickname": "WebSocket Test User",
        "hashed_password": "test_password"
    }

    # Try to get existing user
    result = await db_session.execute(
        select(User).where(User.email == user_data["email"])
    )
    user = result.scalar_one_or_none()

    if not user:
        # Create new user
        user = User(**user_data)
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

    yield user

    # Cleanup is handled by db_session fixture


@pytest.fixture
def auth_headers(test_user: User) -> Dict[str, str]:
    """Generate authentication headers for WebSocket connection"""
    token = create_access_token(data={"sub": str(test_user.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def websocket_url() -> str:
    """Get WebSocket URL from environment"""
    import os
    gateway_host = os.getenv("GATEWAY_HOST", "localhost")
    gateway_port = os.getenv("GATEWAY_PORT", "8080")
    return f"ws://{gateway_host}:{gateway_port}/ws/chat"
