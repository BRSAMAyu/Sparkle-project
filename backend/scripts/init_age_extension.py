#!/usr/bin/env python3
"""
初始化 Apache AGE 扩展

检查并创建 AGE 扩展、默认图谱、基础节点类型和关系类型
"""
import asyncio
import sys
import os

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.age_client import get_age_client, init_age
from app.db.extensions import ensure_database_extensions
from app.db.session import AsyncSessionLocal
from sqlalchemy import text
from loguru import logger


async def check_database_extensions():
    """检查并创建 AGE / vector 扩展"""
    print("=" * 60)
    print("🔍 检查数据库扩展状态")
    print("=" * 60)

    async with AsyncSessionLocal() as session:
        status = await ensure_database_extensions(session, ("vector", "age"))

        vector_ready = status.get("vector", False)
        if vector_ready:
            result = await session.execute(text("SELECT extversion FROM pg_extension WHERE extname = 'vector'"))
            version = result.scalar()
            print(f"✅ pgvector 扩展已安装 (版本: {version})")
        else:
            print("❌ pgvector 扩展不可用")
            print("\n当前数据库镜像未内置 vector，请先切换到包含 pgvector 的数据库镜像。")

        age_ready = status.get("age", False)
        if age_ready:
            result = await session.execute(text("SELECT extversion FROM pg_extension WHERE extname = 'age'"))
            version = result.scalar()
            print(f"✅ Apache AGE 扩展已安装 (版本: {version})")
        else:
            print("❌ Apache AGE 扩展不可用")
            print("\n当前数据库镜像未内置 AGE，请先切换到包含 AGE 的数据库镜像。")

    return vector_ready and age_ready


async def init_age_schema():
    """初始化 AGE 图谱 Schema"""
    print("\n" + "=" * 60)
    print("🚀 初始化 AGE 图谱 Schema")
    print("=" * 60)

    try:
        # 初始化 AGE 客户端
        client = await init_age()
        print("✅ AGE 客户端已连接")

        # 1. 创建默认图谱
        print("\n[1/3] 创建默认图谱...")
        try:
            await client.create_graph("sparkle_galaxy")
            print("   ✅ 图谱 'sparkle_galaxy' 已创建")
        except Exception as e:
            if "already exists" in str(e).lower():
                print("   ✅ 图谱 'sparkle_galaxy' 已存在")
            else:
                raise

        # 2. 创建基础节点类型
        print("\n[2/3] 创建基础节点类型...")
        vertex_labels = [
            ("User", ["id", "name", "email"]),
            ("KnowledgeNode", ["id", "name", "description", "sector", "importance"]),
        ]

        for label, properties in vertex_labels:
            try:
                await client.create_vertex_label(label, properties)
                print(f"   ✅ 节点类型: {label}")
            except Exception as e:
                if "already exists" in str(e).lower():
                    print(f"   ✅ 节点类型已存在: {label}")
                else:
                    print(f"   ⚠️  创建节点类型失败: {label} - {e}")

        # 3. 创建基础关系类型
        print("\n[3/3] 创建基础关系类型...")
        edge_labels = [
            ("STUDIES", ["strength", "created_by"]),
            ("INTERESTED_IN", ["strength", "created_by"]),
            ("RELATED", ["strength", "created_by"]),
            ("PREREQUISITE", ["strength", "created_by"]),
            ("APPLIES_TO", ["strength", "created_by"]),
        ]

        for label, properties in edge_labels:
            try:
                await client.create_edge_label(label, properties)
                print(f"   ✅ 关系类型: {label}")
            except Exception as e:
                if "already exists" in str(e).lower():
                    print(f"   ✅ 关系类型已存在: {label}")
                else:
                    print(f"   ⚠️  创建关系类型失败: {label} - {e}")

        # 4. 验证 Schema
        print("\n" + "-" * 60)
        print("🔍 验证 Schema...")
        result = await client.execute_cypher(
            "MATCH (n) RETURN {vertex_labels: labels(n)} as result LIMIT 10"
        )

        if result:
            print(f"   ✅ 找到 {len(result)} 个节点")
            for row in result[:5]:
                labels = row.get("vertex_labels", [])
                if labels:
                    print(f"      - {labels}")
        else:
            print("   ℹ️  图谱中暂无节点数据")

        await client.close()

        print("\n" + "=" * 60)
        print("🎉 AGE 扩展初始化完成！")
        print("=" * 60)
        print("\n下一步:")
        print("  - 运行数据同步: python scripts/migrate_to_age.py")
        print("  - 测试图查询: python scripts/test_graph_queries.py")

        return True

    except Exception as e:
        logger.error(f"初始化 AGE 失败: {e}")
        print(f"\n❌ 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """主函数"""
    # 1. 检查 AGE 扩展
    extensions_ready = await check_database_extensions()

    if not extensions_ready:
        print("\n❌ 数据库扩展未准备完成，无法继续")
        sys.exit(1)

    # 2. 初始化 Schema
    success = await init_age_schema()

    if success:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
