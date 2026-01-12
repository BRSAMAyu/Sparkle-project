import asyncio
from app.db.session import engine
from sqlalchemy import text

async def fix_db():
    async with engine.begin() as conn:
        await conn.execute(text("DROP TABLE IF EXISTS notifications"))
    print("Dropped notifications table")

if __name__ == "__main__":
    asyncio.run(fix_db())
