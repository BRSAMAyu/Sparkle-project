"""
数据迁移脚本：PostgreSQL → Apache AGE

将现有知识图谱数据迁移到 AGE，同时保持双写能力
"""

import asyncio
import sys
import os
import json
from datetime import datetime
from typing import List, Dict, Any

# 添加 backend 路径
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import select
from app.core.age_client import get_age_client, init_age
from app.models.knowledge import KnowledgeNode as PGKnowledgeNode, NodeRelation as PGNodeRelation
from app.models.user import User as PGUser
from app.models.graph_models import KnowledgeVertex, UserVertex, RelationEdge
from app.config import settings
from loguru import logger


class AgeMigrator:
    """AGE 数据迁移器"""

    def __init__(self):
        self.age_client = None
        self.pg_engine = None
        self.pg_session = None

    async def connect(self):
        """连接数据库"""
        # 连接 AGE
        self.age_client = await init_age()

        # 连接 PostgreSQL
        self.pg_engine = create_async_engine(
            settings.DATABASE_URL,
            echo=False,
            future=True
        )
        self.pg_session = AsyncSession(self.pg_engine)

        logger.info("数据库连接成功")

    async def close(self):
        """关闭连接"""
        if self.age_client:
            await self.age_client.close()
        if self.pg_session:
            await self.pg_session.close()
        if self.pg_engine:
            await self.pg_engine.dispose()

    async def migrate_users(self, batch_size: int = 100):
        """迁移用户数据"""
        print("\n📊 迁移用户数据...")

        offset = 0
        total = 0

        while True:
            # 分页查询
            result = await self.pg_session.execute(
                select(PGUser)
                .limit(batch_size)
                .offset(offset)
            )
            users = result.scalars().all()

            if not users:
                break

            for user in users:
                try:
                    # 创建用户顶点
                    user_vertex = UserVertex(
                        id=str(user.id),
                        username=user.username,
                        nickname=user.nickname or user.username,
                        flame_level=user.flame_level or 1,
                        created_at=user.created_at
                    )

                    await self.age_client.add_vertex(
                        "User",
                        user_vertex.to_dict()
                    )

                    total += 1
                    if total % 100 == 0:
                        print(f"  已迁移 {total} 个用户...")

                except Exception as e:
                    logger.warning(f"迁移用户 {user.id} 失败: {e}")

            offset += batch_size

        print(f"✅ 迁移完成: {total} 个用户")

    async def migrate_knowledge_nodes(self, batch_size: int = 100):
        """迁移知识节点"""
        print("\n📚 迁移知识节点...")

        offset = 0
        total = 0

        while True:
            # 分页查询
            result = await self.pg_session.execute(
                select(PGKnowledgeNode)
                .limit(batch_size)
                .offset(offset)
            )
            nodes = result.scalars().all()

            if not nodes:
                break

            for node in nodes:
                try:
                    # 创建知识节点顶点
                    vertex = KnowledgeVertex(
                        id=str(node.id),
                        name=node.name,
                        description=node.description or "",
                        importance=node.importance_level or 1,
                        sector=node.sector_code or "VOID",
                        keywords=node.keywords or [],
                        source_type=node.source_type or "seed",
                        created_at=node.created_at
                    )

                    await self.age_client.add_vertex(
                        "KnowledgeNode",
                        vertex.to_dict()
                    )

                    total += 1
                    if total % 100 == 0:
                        print(f"  已迁移 {total} 个知识节点...")

                except Exception as e:
                    logger.warning(f"迁移节点 {node.id} 失败: {e}")

            offset += batch_size

        print(f"✅ 迁移完成: {total} 个知识节点")

    async def migrate_relations(self, batch_size: int = 100):
        """迁移关系数据"""
        print("\n🔗 迁移关系数据...")

        offset = 0
        total = 0

        while True:
            # 分页查询
            result = await self.pg_session.execute(
                select(PGNodeRelation)
                .limit(batch_size)
                .offset(offset)
            )
            relations = result.scalars().all()

            if not relations:
                break

            for rel in relations:
                try:
                    # 查找源节点和目标节点
                    source_result = await self.pg_session.execute(
                        select(PGKnowledgeNode).where(PGKnowledgeNode.id == rel.source_node_id)
                    )
                    target_result = await self.pg_session.execute(
                        select(PGKnowledgeNode).where(PGKnowledgeNode.id == rel.target_node_id)
                    )

                    source = source_result.scalar_one_or_none()
                    target = target_result.scalar_one_or_none()

                    if not source or not target:
                        logger.warning(f"关系节点不存在: {rel.source_node_id} -> {rel.target_node_id}")
                        continue

                    # 创建边
                    await self.age_client.add_edge(
                        from_label="KnowledgeNode",
                        from_props={"id": str(rel.source_node_id)},
                        to_label="KnowledgeNode",
                        to_props={"id": str(rel.target_node_id)},
                        edge_label=rel.relation_type.upper(),
                        edge_props={
                            "strength": str(rel.strength),
                            "created_by": rel.created_by or "seed"
                        }
                    )

                    total += 1
                    if total % 100 == 0:
                        print(f"  已迁移 {total} 条关系...")

                except Exception as e:
                    logger.warning(f"迁移关系 {rel.id} 失败: {e}")

            offset += batch_size

        print(f"✅ 迁移完成: {total} 条关系")

    async def migrate_user_node_status(self, batch_size: int = 100):
        """迁移用户节点状态（生成用户兴趣和学习记录边）"""
        print("\n👤 迁移用户节点状态...")

        from app.models.user import UserNodeStatus

        offset = 0
        total = 0

        while True:
            result = await self.pg_session.execute(
                select(UserNodeStatus)
                .limit(batch_size)
                .offset(offset)
            )
            statuses = result.scalars().all()

            if not statuses:
                break

            for status in statuses:
                try:
                    # 如果用户对节点感兴趣（收藏或学习过）
                    if status.is_favorite or status.study_count > 0:
                        await self.age_client.add_edge(
                            from_label="User",
                            from_props={"id": str(status.user_id)},
                            to_label="KnowledgeNode",
                            to_props={"id": str(status.node_id)},
                            edge_label="INTERESTED_IN",
                            edge_props={
                                "strength": str(status.mastery_score / 100),
                                "last_accessed": status.last_study_at.isoformat() if status.last_study_at else ""
                            }
                        )

                    # 如果学习过
                    if status.study_count > 0:
                        await self.age_client.add_edge(
                            from_label="User",
                            from_props={"id": str(status.user_id)},
                            to_label="KnowledgeNode",
                            to_props={"id": str(status.node_id)},
                            edge_label="STUDIED",
                            edge_props={
                                "study_minutes": str(status.total_study_minutes),
                                "mastery_delta": str(status.mastery_score),
                                "last_study": status.last_study_at.isoformat() if status.last_study_at else ""
                            }
                        )

                    # 如果已掌握
                    if status.mastery_score >= 80:
                        await self.age_client.add_edge(
                            from_label="User",
                            from_props={"id": str(status.user_id)},
                            to_label="KnowledgeNode",
                            to_props={"id": str(status.node_id)},
                            edge_label="MASTERED"
                        )

                    total += 1
                    if total % 100 == 0:
                        print(f"  已迁移 {total} 条用户状态...")

                except Exception as e:
                    logger.warning(f"迁移用户状态失败: {e}")

            offset += batch_size

        print(f"✅ 迁移完成: {total} 条用户状态")

    async def verify_migration(self):
        """验证迁移结果"""
        print("\n🔍 验证迁移结果...")

        # 统计顶点
        vertex_count = await self.age_client.execute_cypher("""
        MATCH (n) RETURN labels(n) as label, COUNT(n) as count
        """)

        print("\n顶点统计:")
        for v in vertex_count:
            print(f"  {v['label']}: {v['count']}")

        # 统计边
        edge_count = await self.age_client.execute_cypher("""
        MATCH ()-[r]->() RETURN type(r) as type, COUNT(r) as count
        """)

        print("\n边统计:")
        for e in edge_count:
            print(f"  {e['type']}: {e['count']}")

        # 示例查询
        print("\n示例查询:")
        sample = await self.age_client.execute_cypher("""
        MATCH (u:User)-[:INTERESTED_IN]->(k:KnowledgeNode)
        RETURN u.nickname as user, k.name as knowledge
        LIMIT 3
        """)
        for s in sample:
            print(f"  {s['user']} → {s['knowledge']}")


async def main():
    """主函数"""
    print("=" * 70)
    print("🚀 Apache AGE 数据迁移工具")
    print("=" * 70)

    migrator = AgeMigrator()

    try:
        await migrator.connect()

        # 执行迁移
        await migrator.migrate_users()
        await migrator.migrate_knowledge_nodes()
        await migrator.migrate_relations()
        await migrator.migrate_user_node_status()

        # 验证
        await migrator.verify_migration()

        print("\n" + "=" * 70)
        print("🎉 数据迁移完成！")
        print("=" * 70)
        print("\n建议:")
        print("  1. 运行测试: python scripts/test_graph_queries.py")
        print("  2. 查看文档: docs/06_安全与质量报告/04_生产级修复总结.md")

    except Exception as e:
        logger.error(f"迁移失败: {e}")
        print(f"\n❌ 错误: {e}")
        sys.exit(1)

    finally:
        await migrator.close()


if __name__ == "__main__":
    asyncio.run(main())
