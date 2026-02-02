
import asyncio
from app.db.session import engine
from app.models.base import Base
from sqlalchemy import text

# 导入所有模型以确保 Base.metadata 注册了它们
import app.models.user
import app.models.task
import app.models.plan
import app.models.galaxy
import app.models.memory
import app.models.tool_history
import app.models.user_memory_settings

async def sync_database():
    print("🚀 Starting manual database schema synchronization...")
    async with engine.begin() as conn:
        # 0. 确保 pgvector 扩展已加载
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        
        # 1. 物理建表
        await conn.run_sync(Base.metadata.create_all)
        
        # 2. 强制同步 Alembic 版本
        # 确保版本表存在并插入最新版本号
        await conn.execute(text("CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(64) PRIMARY KEY)"))
        await conn.execute(text("TRUNCATE TABLE alembic_version"))
        await conn.execute(text("INSERT INTO alembic_version (version_num) VALUES ('4f6c3b8e1d2a')"))
        
    print("✅ Physical Schema Sync Complete and Alembic version aligned to 4f6c3b8e1d2a")

if __name__ == "__main__":
    asyncio.run(sync_database())
