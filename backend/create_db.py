import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from app.config import settings
from app.db.session import Base
import app.models # Import all models to register them

async def create_db_tables():
    engine = create_async_engine(settings.DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    print("Database tables created successfully!")

if __name__ == "__main__":
    asyncio.run(create_db_tables())
