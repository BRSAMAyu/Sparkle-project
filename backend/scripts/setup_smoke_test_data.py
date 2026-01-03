import asyncio
import sys
import os
import uuid
from loguru import logger

# Add parent directory to path to import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import AsyncSessionLocal
from app.models.galaxy import KnowledgeNode
from app.models.subject import Subject

async def setup_data():
    """Setup data for Smoke Test"""
    logger.info("🧪 Setting up Smoke Test data...")
    
    test_nodes = [
        {
            "name": "CS101 课程说明",
            "desc": "CS101 课程是计算机科学入门。期末考试占比 40%，期中考试 20%，平时作业 40%。任课老师是张教授。",
            "keywords": ["CS101", "考试", "占比"]
        },
        {
            "name": "系统错误码 0x8004",
            "desc": "错误码 0x8004 代表 'DB_CONNECTION_TIMEOUT'。这通常发生在数据库负载过高或 Redis 响应慢时。",
            "keywords": ["0x8004", "错误码", "超时"]
        },
        {
            "name": "Sparkle RAG v2.0",
            "desc": "Sparkle 学习助手采用 RAG v2.0 架构，支持混合检索和本地重排序。混合检索结合了向量搜索和 BM25 关键词匹配。",
            "keywords": ["RAG", "混合检索", "BM25"]
        }
    ]

    async with AsyncSessionLocal() as session:
        for item in test_nodes:
            # Check if node already exists
            from sqlalchemy import select
            stmt = select(KnowledgeNode).where(KnowledgeNode.name == item["name"])
            res = await session.execute(stmt)
            if res.scalar_one_or_none():
                logger.info(f"⏭️ Node '{item['name']}' already exists. Skipping.")
                continue

            node = KnowledgeNode(
                id=uuid.uuid4(),
                name=item["name"],
                description=item["desc"],
                importance_level=5,
                source_type='test',
                is_seed=True,
                keywords=item["keywords"]
            )
            session.add(node)
            logger.info(f"✅ Created node: {item['name']}")
        
        await session.commit()
    
    logger.success("🚀 Smoke Test data setup complete!")

if __name__ == "__main__":
    asyncio.run(setup_data())
