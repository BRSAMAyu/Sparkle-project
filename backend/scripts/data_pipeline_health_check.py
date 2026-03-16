#!/usr/bin/env python3
"""
数据链路健康检查脚本

全面检查 PostgreSQL、Redis、扩展、索引、LLM 服务状态
"""
import asyncio
import sys
import os
import time
from typing import Dict, List, Any

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from loguru import logger
from sqlalchemy import text
from app.db.session import AsyncSessionLocal
from app.config import settings
from app.core.redis_utils import resolve_redis_password
from app.services.embedding_service import embedding_service
from app.services.rerank_service import rerank_service
from app.services.llm_service import llm_service
from app.core.age_client import get_age_client
from app.models.galaxy import KnowledgeNode
from sqlalchemy import select, func
from redis.asyncio import Redis


class HealthCheckResult:
    """健康检查结果"""

    def __init__(self, name: str):
        self.name = name
        self.passed = False
        self.details = []
        self.errors = []
        self.warnings = []
        self.duration = 0.0

    def add_detail(self, detail: str):
        self.details.append(detail)

    def add_error(self, error: str):
        self.errors.append(error)

    def add_warning(self, warning: str):
        self.warnings.append(warning)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "passed": self.passed,
            "details": self.details,
            "errors": self.errors,
            "warnings": self.warnings,
            "duration": self.duration,
        }


class DataPipelineHealthCheck:
    """数据链路健康检查"""

    def __init__(self):
        self.results: List[HealthCheckResult] = []

    async def check_postgresql_connection(self) -> HealthCheckResult:
        """检查 PostgreSQL 连接"""
        result = HealthCheckResult("PostgreSQL 连接")
        start_time = time.time()

        try:
            async with AsyncSessionLocal() as session:
                db_result = await session.execute(text("SELECT version()"))
                version = db_result.scalar()
                result.add_detail(f"版本: {version[:50]}...")
                result.passed = True

        except Exception as e:
            result.add_error(f"连接失败: {e}")

        result.duration = time.time() - start_time
        return result

    async def check_pgvector_extension(self) -> HealthCheckResult:
        """检查 pgvector 扩展"""
        result = HealthCheckResult("pgvector 扩展")
        start_time = time.time()

        try:
            async with AsyncSessionLocal() as session:
                db_result = await session.execute(text(
                    "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')"
                ))
                exists = db_result.scalar()

                if exists:
                    db_result = await session.execute(text(
                        "SELECT extversion FROM pg_extension WHERE extname = 'vector'"
                    ))
                    version = db_result.scalar()
                    result.add_detail(f"已安装 (版本: {version})")
                    result.passed = True
                else:
                    result.add_error("pgvector 扩展未安装")

        except Exception as e:
            result.add_error(f"检查失败: {e}")

        result.duration = time.time() - start_time
        return result

    async def check_age_extension(self) -> HealthCheckResult:
        """检查 Apache AGE 扩展"""
        result = HealthCheckResult("Apache AGE 扩展")
        start_time = time.time()

        try:
            async with AsyncSessionLocal() as session:
                db_result = await session.execute(text(
                    "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'age')"
                ))
                exists = db_result.scalar()

                if exists:
                    db_result = await session.execute(text(
                        "SELECT extversion FROM pg_extension WHERE extname = 'age'"
                    ))
                    version = db_result.scalar()
                    result.add_detail(f"已安装 (版本: {version})")

                    # 检查默认图谱
                    db_result = await session.execute(text(
                        "SELECT EXISTS(SELECT 1 FROM ag_graph WHERE name = 'sparkle_galaxy')"
                    ))
                    graph_exists = db_result.scalar()
                    if graph_exists:
                        result.add_detail("默认图谱 'sparkle_galaxy' 存在")
                    else:
                        result.add_warning("默认图谱 'sparkle_galaxy' 不存在，请运行 init_age_extension.py")

                    result.passed = True
                else:
                    result.add_error("AGE 扩展未安装，请先安装")

        except Exception as e:
            result.add_error(f"检查失败: {e}")

        result.duration = time.time() - start_time
        return result

    async def check_knowledge_nodes(self) -> HealthCheckResult:
        """检查知识节点数据"""
        result = HealthCheckResult("知识节点数据")
        start_time = time.time()

        try:
            async with AsyncSessionLocal() as session:
                # 总数
                db_result = await session.execute(select(func.count(KnowledgeNode.id)))
                total = db_result.scalar()
                result.add_detail(f"总节点数: {total}")

                # 有 embedding 的数量
                db_result = await session.execute(
                    select(func.count(KnowledgeNode.id)).where(KnowledgeNode.embedding.isnot(None))
                )
                with_embedding = db_result.scalar()
                result.add_detail(f"有 embedding: {with_embedding} ({with_embedding/total*100 if total > 0 else 0:.1f}%)")

                # 有 description 的数量
                db_result = await session.execute(
                    select(func.count(KnowledgeNode.id)).where(KnowledgeNode.description.isnot(None))
                )
                with_description = db_result.scalar()
                result.add_detail(f"有描述: {with_description} ({with_description/total*100 if total > 0 else 0:.1f}%)")

                if total == 0:
                    result.add_warning("数据库中没有知识节点")
                elif with_embedding == 0:
                    result.add_warning("所有节点都没有 embedding，请运行 backfill_embeddings.py")
                elif with_embedding < total * 0.5:
                    result.add_warning("超过 50% 的节点没有 embedding")

                result.passed = True

        except Exception as e:
            result.add_error(f"检查失败: {e}")

        result.duration = time.time() - start_time
        return result

    async def check_redis_connection(self) -> HealthCheckResult:
        """检查 Redis 连接"""
        result = HealthCheckResult("Redis 连接")
        start_time = time.time()

        try:
            resolved_password, _ = resolve_redis_password(settings.REDIS_URL, settings.REDIS_PASSWORD)
            redis = Redis.from_url(settings.REDIS_URL, password=resolved_password, decode_responses=True)

            await redis.ping()
            result.add_detail("连接成功")

            # 检查内存
            info = await redis.info("memory")
            used_memory = info.get("used_memory_human", "unknown")
            result.add_detail(f"内存使用: {used_memory}")

            # 检查模块
            modules = await redis.module_list()
            module_names = [m.get("name", "") for m in modules]
            result.add_detail(f"已加载模块: {len(module_names)} 个")

            if "search" in module_names or "searchlight" in module_names or "ReJSON" in module_names:
                result.add_detail("Redis Search 模块已加载")
            else:
                result.add_warning("Redis Search 模块未加载")

            await redis.close()
            result.passed = True

        except Exception as e:
            result.add_error(f"连接失败: {e}")

        result.duration = time.time() - start_time
        return result

    async def check_redis_search_index(self) -> HealthCheckResult:
        """检查 Redis Search 索引"""
        result = HealthCheckResult("Redis Search 索引")
        start_time = time.time()

        try:
            resolved_password, _ = resolve_redis_password(settings.REDIS_URL, settings.REDIS_PASSWORD)
            redis = Redis.from_url(settings.REDIS_URL, password=resolved_password, decode_responses=True)

            # 检查知识节点索引
            try:
                info = await redis.ft("idx:knowledge").info()
                num_docs = info.get("num_docs", 0)
                result.add_detail(f"idx:knowledge 存在 (文档数: {num_docs})")

                if num_docs == 0:
                    result.add_warning("索引为空，请运行 sync_pg_to_redis.py")

                result.passed = True
            except Exception as e:
                if "Unknown Index" in str(e):
                    result.add_error("idx:knowledge 索引不存在，请运行 init_redis_index.py")
                else:
                    raise

            await redis.close()

        except Exception as e:
            if not result.errors:
                result.add_error(f"检查失败: {e}")

        result.duration = time.time() - start_time
        return result

    async def check_embedding_service(self) -> HealthCheckResult:
        """检查 Embedding 服务"""
        result = HealthCheckResult("Embedding 服务")
        start_time = time.time()

        try:
            test_text = "测试文本"
            embedding = await embedding_service.get_embedding(test_text, text_type="document")

            if embedding and len(embedding) == settings.EMBEDDING_DIM:
                result.add_detail(f"正常 (维度: {len(embedding)})")
                result.passed = True
            else:
                result.add_error(f"返回维度不匹配，期望 {settings.EMBEDDING_DIM}，得到 {len(embedding) if embedding else 0}")

        except Exception as e:
            result.add_error(f"服务失败: {e}")

        result.duration = time.time() - start_time
        return result

    async def check_rerank_service(self) -> HealthCheckResult:
        """检查 Rerank 服务"""
        result = HealthCheckResult("Rerank 服务")
        start_time = time.time()

        try:
            query = "测试查询"
            candidates = [
                {"content": "相关内容"},
                {"content": "不相关内容"},
            ]

            results = await rerank_service.rerank(query, candidates, top_k=2)

            if results:
                result.add_detail(f"正常 (返回: {len(results)} 条)")
                result.passed = True
            else:
                result.add_warning("返回空结果")

        except Exception as e:
            result.add_error(f"服务失败: {e}")

        result.duration = time.time() - start_time
        return result

    async def check_llm_service(self) -> HealthCheckResult:
        """检查 LLM 服务"""
        result = HealthCheckResult("LLM 服务")
        start_time = time.time()

        try:
            messages = [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello"}
            ]
            response = await llm_service.chat(messages)

            if response:
                result.add_detail(f"正常 (响应: {len(response)} 字符)")
                result.passed = True
            else:
                result.add_error("返回空响应")

        except Exception as e:
            result.add_error(f"服务失败: {e}")

        result.duration = time.time() - start_time
        return result

    async def check_age_client(self) -> HealthCheckResult:
        """检查 AGE 客户端"""
        result = HealthCheckResult("AGE 客户端")
        start_time = time.time()

        try:
            client = get_age_client()

            # 测试简单查询
            test_result = await client.execute_cypher(
                "MATCH (n) RETURN count(n) as count LIMIT 1"
            )

            result.add_detail("连接正常")
            result.add_detail(f"图谱中的节点: {test_result[0]['count'] if test_result else 0}")
            result.passed = True

        except Exception as e:
            result.add_error(f"连接失败: {e}")

        result.duration = time.time() - start_time
        return result

    async def run_all_checks(self):
        """运行所有检查"""
        print("=" * 60)
        print("🔍 数据链路健康检查")
        print("=" * 60)
        print()

        checks = [
            self.check_postgresql_connection(),
            self.check_pgvector_extension(),
            self.check_age_extension(),
            self.check_knowledge_nodes(),
            self.check_redis_connection(),
            self.check_redis_search_index(),
            self.check_embedding_service(),
            self.check_rerank_service(),
            self.check_llm_service(),
            self.check_age_client(),
        ]

        self.results = await asyncio.gather(*checks)

        self.print_summary()

    def print_summary(self):
        """打印检查摘要"""
        print("\n" + "=" * 60)
        print("📊 检查结果摘要")
        print("=" * 60)

        passed = sum(1 for r in self.results if r.passed)
        total = len(self.results)
        pass_rate = (passed / total * 100) if total > 0 else 0

        print(f"\n通过率: {passed}/{total} ({pass_rate:.0f}%)")
        print()

        for result in self.results:
            status = "✅" if result.passed else "❌"
            duration = f" ({result.duration:.3f}s)" if result.duration > 0 else ""
            print(f"{status} {result.name}{duration}")

            for detail in result.details:
                print(f"   ℹ️  {detail}")

            for warning in result.warnings:
                print(f"   ⚠️  {warning}")

            for error in result.errors:
                print(f"   ❌ {error}")

            print()

        print("=" * 60)

        # 打印修复建议
        if passed < total:
            print("\n🔧 修复建议:")

            for result in self.results:
                if not result.passed or result.warnings:
                    if result.name == "pgvector 扩展":
                        print("   - 创建 pgvector 扩展: CREATE EXTENSION vector;")
                    elif result.name == "Apache AGE 扩展":
                        print("   - 运行: python scripts/init_age_extension.py")
                    elif result.name == "知识节点数据" and any("embedding" in w for w in result.warnings):
                        print("   - 运行: python scripts/backfill_embeddings.py")
                    elif result.name == "Redis Search 索引":
                        print("   - 运行: python scripts/init_redis_index.py")
                        print("   - 同步数据: python scripts/sync_pg_to_redis.py")
                    elif result.name == "Embedding 服务":
                        print("   - 检查 DASHSCOPE_API_KEY 配置")

            print()

        if pass_rate >= 80:
            print("🎉 数据链路健康检查通过！")
        elif pass_rate >= 60:
            print("⚠️  数据链路部分功能可用，存在一些问题需要修复")
        else:
            print("❌ 数据链路存在严重问题，需要全面检查")

        print("=" * 60)


async def main():
    """主函数"""
    checker = DataPipelineHealthCheck()
    await checker.run_all_checks()


if __name__ == "__main__":
    asyncio.run(main())
