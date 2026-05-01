#!/usr/bin/env python3
"""
回填知识节点 Embedding

批量读取知识节点并生成 embedding 向量
"""
import argparse
import asyncio
import sys
import os
import time
from typing import List

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from loguru import logger
from sqlalchemy import select, func
from app.db.session import AsyncSessionLocal
from app.models.galaxy import KnowledgeNode
from app.services.embedding_service import embedding_service
from app.config import settings


class EmbeddingBackfill:
    """Embedding 回填器"""

    def __init__(self, batch_size: int = 10, delay: float = 0.2):  # DashScope limit: ≤10 per batch
        self.batch_size = batch_size
        self.delay = delay
        self.stats = {
            "total_nodes": 0,
            "nodes_without_embedding": 0,
            "processed": 0,
            "skipped": 0,
            "errors": 0,
            "start_time": None,
            "end_time": None,
        }

    async def get_nodes_without_embedding(self, session, limit: int = None) -> List[KnowledgeNode]:
        """获取没有 embedding 的节点"""
        stmt = select(KnowledgeNode).where(KnowledgeNode.embedding.is_(None))
        if limit:
            stmt = stmt.limit(limit)
        stmt = stmt.order_by(KnowledgeNode.id)

        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def update_embeddings(self, nodes: List[KnowledgeNode]) -> int:
        """批量更新 embedding"""
        if not nodes:
            return 0

        # 准备文本
        texts = []
        for node in nodes:
            text = f"{node.name}. {node.description or ''}"
            texts.append(text)

        try:
            # 批量生成 embedding
            embeddings = await embedding_service.batch_embeddings(texts, text_type="document")

            # 更新数据库
            async with AsyncSessionLocal() as session:
                for node, embedding in zip(nodes, embeddings):
                    node.embedding = embedding
                    session.add(node)

                await session.commit()

            return len(nodes)

        except Exception as e:
            logger.error(f"批量更新失败: {e}")
            return 0

    async def run(self):
        """执行回填"""
        self.stats["start_time"] = time.time()

        print("=" * 60)
        print("🚀 开始回填知识节点 Embedding")
        print("=" * 60)

        async with AsyncSessionLocal() as session:
            # 统计节点数量
            result = await session.execute(select(func.count(KnowledgeNode.id)))
            self.stats["total_nodes"] = result.scalar()

            result = await session.execute(
                select(func.count(KnowledgeNode.id)).where(KnowledgeNode.embedding.is_(None))
            )
            self.stats["nodes_without_embedding"] = result.scalar()

        print(f"\n📊 节点统计:")
        print(f"   总节点数: {self.stats['total_nodes']}")
        print(f"   需要 embedding: {self.stats['nodes_without_embedding']}")

        if self.stats["nodes_without_embedding"] == 0:
            print("\n✅ 所有节点都已有 embedding，无需回填")
            return

        print(f"\n⚙️  配置:")
        print(f"   批量大小: {self.batch_size}")
        print(f"   延迟: {self.delay}s")

        # 分批处理
        offset = 0
        while True:
            async with AsyncSessionLocal() as session:
                nodes = await self.get_nodes_without_embedding(session, limit=self.batch_size)

            if not nodes:
                break

            print(f"\n🔄 处理批次 {offset // self.batch_size + 1} ({len(nodes)} 个节点)...")

            try:
                updated = await self.update_embeddings(nodes)
                self.stats["processed"] += updated

                print(f"   ✅ 已更新: {updated} 个节点")

            except Exception as e:
                logger.error(f"批处理失败: {e}")
                self.stats["errors"] += len(nodes)

            offset += len(nodes)

            # 避免触发 API 限流
            if self.delay > 0:
                await asyncio.sleep(self.delay)

            # 安全检查
            if offset >= self.stats["nodes_without_embedding"]:
                break

        self.stats["end_time"] = time.time()
        self.print_summary()

    def print_summary(self):
        """打印统计摘要"""
        duration = self.stats["end_time"] - self.stats["start_time"]

        print("\n" + "=" * 60)
        print("📊 回填完成统计")
        print("=" * 60)
        print(f"总节点数: {self.stats['total_nodes']}")
        print(f"需要处理: {self.stats['nodes_without_embedding']}")
        print(f"已更新: {self.stats['processed']}")
        print(f"错误: {self.stats['errors']}")
        print(f"耗时: {duration:.2f}s")
        if self.stats['processed'] > 0:
            print(f"平均: {duration / self.stats['processed']:.3f}s/节点")


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="回填知识节点 Embedding")
    parser.add_argument("--batch-size", type=int, default=10, help="批量大小 (DashScope API 限制 ≤10)")
    parser.add_argument("--delay", type=float, default=0.2, help="API 调用延迟（秒）")
    parser.add_argument("--dry-run", action="store_true", help="仅统计，不实际更新")

    args = parser.parse_args()

    if args.dry_run:
        print("=" * 60)
        print("🔍 Dry Run 模式")
        print("=" * 60)

        async with AsyncSessionLocal() as session:
            result = await session.execute(select(func.count(KnowledgeNode.id)))
            total = result.scalar()

            result = await session.execute(
                select(func.count(KnowledgeNode.id)).where(KnowledgeNode.embedding.is_(None))
            )
            without_embedding = result.scalar()

        print(f"总节点数: {total}")
        print(f"需要 embedding: {without_embedding}")
        print("\n使用 --batch-size 和 --delay 参数控制处理速度")
        return

    backfill = EmbeddingBackfill(batch_size=args.batch_size, delay=args.delay)
    await backfill.run()


if __name__ == "__main__":
    asyncio.run(main())
