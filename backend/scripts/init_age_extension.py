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
from app.db.session import AsyncSessionLocal
from sqlalchemy import text
from loguru import logger


async def check_age_extension():
    """检查并创建 AGE 扩展"""
    print("=" * 60)
    print("🔍 检查 Apache AGE 扩展状态")
    print("=" * 60)

    async with AsyncSessionLocal() as session:
        # 检查 AGE 扩展是否存在
        result = await session.execute(text(
            "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'age')"
        ))
        age_exists = result.scalar()

        if age_exists:
            print("✅ Apache AGE 扩展已安装")

            # 获取 AGE 版本
            result = await session.execute(text(
                "SELECT extversion FROM pg_extension WHERE extname = 'age'"
            ))
            version = result.scalar()
            print(f"   版本: {version}")
        else:
            print("❌ Apache AGE 扩展未安装")
            print("\n请运行以下命令安装 AGE:")
            print("  Docker: 在 docker-compose.yml 中添加 AGE 扩展配置")
            print("  本地: 参考 AGE 官方文档安装")
            return False

    return True


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
        verify_query = """
        SELECT * FROM cypher('sparkle_galaxy', $$
            MATCH (n) RETURN DISTINCT labels(n) as vertex_labels
            LIMIT 10
        $$) as (result agtype);
        """

        result = await client.execute_cypher(
            "MATCH (n) RETURN DISTINCT labels(n) as vertex_labels LIMIT 10"
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
    age_installed = await check_age_extension()

    if not age_installed:
        print("\n❌ Apache AGE 扩展未安装，无法继续")
        sys.exit(1)

    # 2. 初始化 Schema
    success = await init_age_schema()

    if success:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
