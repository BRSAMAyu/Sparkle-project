import asyncio
import sys
import os
import uuid
from loguru import logger
from sqlalchemy import select

# Add backend directory to path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from app.db.session import AsyncSessionLocal
from app.models.galaxy import KnowledgeNode, NodeRelation
from app.models.subject import Subject

KNOWLEDGE_DATA = [
    {
        "name": "数据结构",
        "description": "数据结构是计算机中存储、组织数据的方式。常见的数据结构包括数组、链表、栈、队列、树和图。掌握数据结构是提高程序运行效率的关键。",
        "importance_level": 5,
        "subject_id": 1,
        "keywords": ["数组", "链表", "树", "图"],
        "relations": [("CS101", "prerequisite")]
    },
    {
        "name": "算法分析",
        "description": "算法分析研究算法的时间复杂度和空间复杂度。大O表示法是描述算法增长趋势的标准方式。理解算法性能对于开发高性能软件至关重要。",
        "importance_level": 5,
        "subject_id": 1,
        "keywords": ["时间复杂度", "空间复杂度", "大O表示法"],
        "relations": [("数据结构", "related")]
    },
    {
        "name": "机器学习",
        "description": "机器学习是人工智能的一个子集，致力于开发能从数据中自动学习并改进的算法。包括监督学习、无监督学习和强化学习。",
        "importance_level": 4,
        "subject_id": 1,
        "keywords": ["监督学习", "神经网络", "深度学习"],
        "relations": [("数据结构", "related")]
    },
    {
        "name": "线性代数",
        "description": "线性代数研究向量空间和线性变换。矩阵运算、特征值和特征向量是其核心内容。它是计算机图形学和机器学习的数学基础。",
        "importance_level": 4,
        "subject_id": 1,
        "keywords": ["矩阵", "向量", "特征值"],
        "relations": [("机器学习", "prerequisite")]
    },
    {
        "name": "微积分",
        "description": "微积分是研究变化的数学。微分和积分是其两大支柱。在机器学习中，梯度下降算法正是利用了导数的概念来最小化损失函数。",
        "importance_level": 3,
        "subject_id": 1,
        "keywords": ["导数", "积分", "梯度"],
        "relations": [("线性代数", "related")]
    }
]

async def seed_more_data():
    logger.info("🚀 Starting high-density knowledge seeding...")
    async with AsyncSessionLocal() as session:
        # 确保学科存在
        stmt = select(Subject).where(Subject.id == 1)
        result = await session.execute(stmt)
        subject = result.scalars().first()
        if not subject:
            subject = Subject(id=1, name="Computer Science", category="Science", is_active=True)
            session.add(subject)
            await session.commit()

        # 注入节点
        node_map = {}
        for data in KNOWLEDGE_DATA:
            stmt = select(KnowledgeNode).where(KnowledgeNode.name == data["name"])
            result = await session.execute(stmt)
            node = result.scalars().first()

            if not node:
                logger.info(f"Creating node: {data['name']}")
                node = KnowledgeNode(
                    id=uuid.uuid4(),
                    name=data["name"],
                    description=data["description"],
                    importance_level=data["importance_level"],
                    subject_id=data["subject_id"],
                    keywords=data["keywords"],
                    source_type="seed"
                )
                session.add(node)
                await session.flush() # 为了获取 id
                logger.success(f"✅ Created {data['name']}")
            else:
                logger.info(f"Node already exists: {data['name']}")
            
            node_map[data["name"]] = node

        # 注入关系
        logger.info("🔗 Seeding relations...")
        for data in KNOWLEDGE_DATA:
            target_node = node_map.get(data["name"])
            for source_name, rel_type in data.get("relations", []):
                # 寻找源节点 (可能是之前脚本注入的)
                stmt = select(KnowledgeNode).where(KnowledgeNode.name == source_name)
                res = await session.execute(stmt)
                source_node = res.scalars().first()

                if source_node:
                    # 检查关系是否已存在
                    stmt_rel = select(NodeRelation).where(
                        NodeRelation.source_node_id == source_node.id,
                        NodeRelation.target_node_id == target_node.id
                    )
                    res_rel = await session.execute(stmt_rel)
                    if not res_rel.scalars().first():
                        new_rel = NodeRelation(
                            source_node_id=source_node.id,
                            target_node_id=target_node.id,
                            relation_type=rel_type,
                            strength=0.8,
                            created_by="seed"
                        )
                        session.add(new_rel)
                        logger.success(f"✅ Linked {source_name} -> {data['name']}")

        await session.commit()
        logger.info("🏁 Seeding complete.")

if __name__ == "__main__":
    asyncio.run(seed_more_data())
