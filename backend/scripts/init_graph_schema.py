"""
初始化图谱 Schema

创建所有必要的顶点和边标签
"""

import asyncio
import sys
import os

# 添加 backend 路径
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.core.age_client import get_age_client, init_age
from app.models.graph_models import GraphSchema
from loguru import logger


async def init_graph_schema():
    """初始化图谱 Schema"""
    print("=" * 60)
    print("🚀 初始化 Apache AGE 图谱 Schema")
    print("=" * 60)

    try:
        # 初始化 AGE 客户端
        client = await init_age()

        # 1. 创建图谱
        print("\n[1/4] 创建图谱...")
        await client.create_graph("sparkle_galaxy")
        print("✅ 图谱 sparkle_galaxy 已创建")

        # 2. 创建顶点标签
        print("\n[2/4] 创建顶点标签...")
        vertex_labels = GraphSchema.get_vertex_labels()
        for label in vertex_labels:
            await client.create_vertex_label(label)
            print(f"  ✅ {label}")

        # 3. 创建边标签
        print("\n[3/4] 创建边标签...")
        edge_labels = GraphSchema.get_edge_labels()
        for label in edge_labels:
            await client.create_edge_label(label, properties=["strength", "created_by"])
            print(f"  ✅ {label}")

        # 4. 验证创建结果
        print("\n[4/4] 验证 Schema...")
        verify_query = """
        MATCH (n)
        RETURN {vertex_labels: labels(n)} as result
        LIMIT 10
        """

        result = await client.execute_cypher(verify_query)
        print(f"✅ Schema 验证完成: {len(result)} 个标签")

        print("\n" + "=" * 60)
        print("🎉 图谱 Schema 初始化完成！")
        print("=" * 60)
        print("\n下一步:")
        print("  1. 运行数据迁移: python scripts/migrate_to_age.py")
        print("  2. 测试查询: python scripts/test_graph_queries.py")

        await client.close()

    except Exception as e:
        logger.error(f"初始化失败: {e}")
        print(f"\n❌ 错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(init_graph_schema())
