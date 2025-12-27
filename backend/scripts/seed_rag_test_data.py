import asyncio
import sys
import os
import uuid
from loguru import logger
from sqlalchemy import select

# Add backend directory to path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from app.db.session import AsyncSessionLocal
from app.models.galaxy import KnowledgeNode
from app.models.subject import Subject

async def seed_test_data():
    logger.info("Checking for test data 'CS101'...")
    async with AsyncSessionLocal() as session:
        # Check/Create Subject
        stmt = select(Subject).where(Subject.id == 1)
        result = await session.execute(stmt)
        subject = result.scalars().first()
        
        if not subject:
            logger.info("Creating default Subject id=1...")
            subject = Subject(
                id=1,
                name="Computer Science",
                category="Science",
                is_active=True
            )
            session.add(subject)
            await session.commit()
            logger.success("✅ Subject 'Computer Science' created.")
        
        # Check if node exists
        stmt = select(KnowledgeNode).where(KnowledgeNode.name == "CS101")
        result = await session.execute(stmt)
        node = result.scalars().first()
        
        if node:
            logger.info("✅ 'CS101' node already exists.")
        else:
            logger.info("Creating 'CS101' node...")
            new_node = KnowledgeNode(
                id=uuid.uuid4(),
                name="CS101",
                description="CS101 计算机科学导论。本课程介绍计算机科学的基本概念。期末考试占比 60%，期中考试 20%，平时作业 20%。",
                importance_level=1,
                subject_id=1, 
                keywords={"code": "CS101", "type": "course"},
                source_type="seed"
            )
            session.add(new_node)
            await session.commit()
            logger.success("✅ 'CS101' created.")
            
        # Check error node
        stmt = select(KnowledgeNode).where(KnowledgeNode.name == "Error 0x8004")
        result = await session.execute(stmt)
        error_node = result.scalars().first()
        
        if error_node:
            logger.info("✅ 'Error 0x8004' node already exists.")
        else:
            logger.info("Creating 'Error 0x8004' node...")
            err_node = KnowledgeNode(
                id=uuid.uuid4(),
                name="Error 0x8004",
                description="错误码 0x8004 通常表示'内存访问越界'。这通常发生在尝试访问未分配或已释放的内存区域时。建议检查指针是否为空以及数组索引是否超出范围。",
                importance_level=2,
                subject_id=1,
                keywords={"code": "0x8004", "type": "error"},
                source_type="seed"
            )
            session.add(err_node)
            await session.commit()
            logger.success("✅ 'Error 0x8004' created.")

if __name__ == "__main__":
    asyncio.run(seed_test_data())
