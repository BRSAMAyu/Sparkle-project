"""Mock E2E test for adaptive intervention flow (no running services)."""

import asyncio

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.models.base import Base
from app.models.user import User
from app.services.intervention_service import InterventionService

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


async def run() -> None:
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        user = User(
            username="mock_user",
            email="mock_user@example.com",
            hashed_password="hashed",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        service = InterventionService(session)
        request, delivery = await service.create_adaptive_intervention(
            user_id=user.id,
            trigger_event="idle_trigger",
            urgency=0.6,
            context={"task_name": "数学作业", "suggested_step": "读题"},
            edge_state={"focus_score": 0.2},
        )

        assert request.id is not None
        assert request.template_variant_id is not None
        assert delivery.method == "websocket"

    await engine.dispose()
    print("✅ mock E2E flow completed")


if __name__ == "__main__":
    asyncio.run(run())
