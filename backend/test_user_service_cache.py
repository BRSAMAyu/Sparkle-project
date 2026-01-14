#!/usr/bin/env python3
"""
UserService 缓存系统测试

测试 Cache-Aside 模式的完整功能:
1. 缓存命中和未命中
2. 缓存写入
3. 缓存失效
4. 数据库降级
"""

import sys
import os
import asyncio
import time
from uuid import uuid4, UUID

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import redis.asyncio as redis
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from loguru import logger

from app.services.user_service import UserService
from app.models.user import User, PushPreference, UserStatus
from app.models.base import Base
from app.core.redis_utils import resolve_redis_password


# Test configuration
REDIS_URL = "redis://:devpassword@localhost:6379/2"  # 使用不同DB避免冲突
DATABASE_URL = "sqlite+aiosqlite:///./test_user_cache.db"


class UserServiceCacheTestSuite:
    """UserService 缓存测试套件"""

    def __init__(self):
        self.redis_client = None
        self.db_engine = None
        self.db_session_factory = None
        self.user_service = None

    async def setup(self):
        """设置测试环境"""
        logger.info("Setting up test environment...")

        # 连接 Redis
        resolved_password, _ = resolve_redis_password(REDIS_URL, None)
        self.redis_client = redis.from_url(REDIS_URL, decode_responses=False, password=resolved_password)
        try:
            await self.redis_client.ping()
            logger.info("✓ Redis connected")
        except Exception as e:
            logger.error(f"✗ Redis connection failed: {e}")
            raise

        # 清理测试数据
        keys = await self.redis_client.keys("user:*")
        if keys:
            await self.redis_client.delete(*keys)
            logger.info(f"✓ Cleaned {len(keys)} existing cache keys")

        # 设置数据库
        self.db_engine = create_async_engine(DATABASE_URL, echo=False)
        self.db_session_factory = sessionmaker(
            self.db_engine, class_=AsyncSession, expire_on_commit=False
        )

        # 重建表
        async with self.db_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✓ Database tables created")

        # 创建测试数据
        await self._create_test_data()

        # 初始化 UserService
        async with self.db_session_factory() as db:
            self.user_service = UserService(db, self.redis_client)

        logger.info("✓ All components initialized")

    async def _create_test_data(self):
        """创建测试用户数据"""
        async with self.db_session_factory() as db:
            # 创建测试用户
            user_id = UUID("00000000-0000-0000-0000-000000000001")
            user = User(
                id=user_id,
                username="test_user",
                email="test@example.com",
                hashed_password="test_hash",
                nickname="测试用户",
                flame_level=3,
                flame_brightness=0.7,
                depth_preference=0.6,
                curiosity_preference=0.8,
                is_active=True,
                status=UserStatus.ONLINE,
                registration_source="email"
            )
            db.add(user)

            # 创建推送偏好
            push_pref = PushPreference(
                user_id=user_id,
                timezone="Asia/Shanghai",
                enable_curiosity=True,
                persona_type="coach",
                daily_cap=5,
                active_slots=[{"start": "09:00", "end": "10:00"}]
            )
            db.add(push_pref)

            await db.commit()
            logger.info(f"✓ Created test user: {user_id}")

    async def test_cache_lookup(self):
        """测试缓存查找"""
        logger.info("\n=== Test 1: Cache Lookup ===")

        user_id = UUID("00000000-0000-0000-0000-000000000001")

        # 第一次调用 - 应该缓存未命中，查询数据库
        start = time.time()
        context1 = await self.user_service.get_context(user_id)
        db_time = time.time() - start
        assert context1 is not None
        assert context1.nickname == "测试用户"
        logger.info(f"✓ First call (DB): {db_time:.4f}s, nickname={context1.nickname}")

        # 第二次调用 - 应该缓存命中
        start = time.time()
        context2 = await self.user_service.get_context(user_id)
        cache_time = time.time() - start
        assert context2 is not None
        assert context2.nickname == "测试用户"
        logger.info(f"✓ Second call (Cache): {cache_time:.4f}s, nickname={context2.nickname}")

        # 验证缓存命中比数据库快
        assert cache_time < db_time, f"Cache should be faster: {cache_time} vs {db_time}"
        logger.info(f"✓ Cache is {db_time/cache_time:.1f}x faster than DB")

        return True

    async def test_cache_write(self):
        """测试缓存写入"""
        logger.info("\n=== Test 2: Cache Write ===")

        user_id = UUID("00000000-0000-0000-0000-000000000001")

        # 清除缓存
        await self.redis_client.delete(f"user:context:{user_id}")

        # 调用方法，应该写入缓存
        context = await self.user_service.get_context(user_id)
        assert context is not None

        # 验证缓存存在
        cached = await self.redis_client.get(f"user:context:{user_id}")
        assert cached is not None
        logger.info(f"✓ Cache written: {len(cached)} bytes")

        # 验证缓存内容
        import json
        data = json.loads(cached)
        assert data["nickname"] == "测试用户"
        logger.info(f"✓ Cache content verified: {data}")

        return True

    async def test_cache_invalidation(self):
        """测试缓存失效"""
        logger.info("\n=== Test 3: Cache Invalidation ===")

        user_id = UUID("00000000-0000-0000-0000-000000000001")

        # 先写入缓存
        await self.user_service.get_context(user_id)
        await self.user_service.get_analytics_summary(user_id)
        await self.user_service.get_preferences(user_id)
        await self.user_service.get_user_stats(user_id)

        # 验证缓存存在
        keys = [
            f"user:context:{user_id}",
            f"user:analytics:{user_id}",
            f"user:preferences:{user_id}",
            f"user:stats:{user_id}",
        ]
        for key in keys:
            assert await self.redis_client.get(key) is not None
        logger.info(f"✓ All {len(keys)} cache keys exist")

        # 调用失效方法
        result = await self.user_service.invalidate_user_cache(user_id)
        assert result is True
        logger.info("✓ Cache invalidation called")

        # 验证缓存已清除
        for key in keys:
            assert await self.redis_client.get(key) is None
        logger.info("✓ All cache keys invalidated")

        return True

    async def test_update_with_invalidation(self):
        """测试更新用户资料并自动失效缓存"""
        logger.info("\n=== Test 4: Update with Invalidation ===")

        user_id = UUID("00000000-0000-0000-0000-000000000001")

        # 先写入缓存
        await self.user_service.get_context(user_id)
        cached_before = await self.redis_client.get(f"user:context:{user_id}")
        assert cached_before is not None
        logger.info("✓ Cache exists before update")

        # 更新用户资料
        updates = {
            "nickname": "更新后的昵称",
            "depth_preference": 0.9
        }
        result = await self.user_service.update_user_profile(user_id, updates)
        assert result is True
        logger.info(f"✓ User profile updated: {updates}")

        # 验证缓存已失效
        cached_after = await self.redis_client.get(f"user:context:{user_id}")
        assert cached_after is None
        logger.info("✓ Cache automatically invalidated after update")

        # 再次获取，应该从DB获取新数据
        context = await self.user_service.get_context(user_id)
        assert context.nickname == "更新后的昵称"
        assert context.preferences["depth_preference"] == 0.9
        logger.info(f"✓ New data retrieved: nickname={context.nickname}")

        return True

    async def test_all_methods_with_cache(self):
        """测试所有带缓存的方法"""
        logger.info("\n=== Test 5: All Cached Methods ===")

        user_id = UUID("00000000-0000-0000-0000-000000000001")

        # 测试 get_context
        context = await self.user_service.get_context(user_id)
        assert context is not None
        logger.info(f"✓ get_context: {context.nickname}")

        # 测试 get_analytics_summary
        analytics = await self.user_service.get_analytics_summary(user_id)
        assert analytics is not None
        assert analytics["engagement_level"] == "high"
        logger.info(f"✓ get_analytics_summary: {analytics['engagement_level']}")

        # 测试 get_preferences
        prefs = await self.user_service.get_preferences(user_id)
        assert prefs is not None
        assert prefs.persona_type == "coach"
        logger.info(f"✓ get_preferences: {prefs.persona_type}")

        # 测试 get_user_stats
        stats = await self.user_service.get_user_stats(user_id)
        assert stats is not None
        assert stats["flame_level"] == 3
        logger.info(f"✓ get_user_stats: flame_level={stats['flame_level']}")

        # 验证所有缓存都存在
        keys = [
            f"user:context:{user_id}",
            f"user:analytics:{user_id}",
            f"user:preferences:{user_id}",
            f"user:stats:{user_id}",
        ]
        for key in keys:
            assert await self.redis_client.get(key) is not None
        logger.info(f"✓ All {len(keys)} methods cached successfully")

        return True

    async def test_cache_miss_fallback(self):
        """测试缓存未命中时的降级"""
        logger.info("\n=== Test 6: Cache Miss Fallback ===")

        # 使用不存在的用户ID
        fake_user_id = uuid4()

        # 应该返回None，不会崩溃
        context = await self.user_service.get_context(fake_user_id)
        assert context is None
        logger.info("✓ Gracefully handled non-existent user")

        # 验证没有缓存空结果
        cached = await self.redis_client.get(f"user:context:{fake_user_id}")
        assert cached is None
        logger.info("✓ No cache for non-existent user")

        return True

    async def test_concurrent_access(self):
        """测试并发访问缓存"""
        logger.info("\n=== Test 7: Concurrent Access ===")

        user_id = UUID("00000000-0000-0000-0000-000000000001")

        # 1. 测试带预热的并发 (应该全部命中缓存)
        logger.info("--- Subtest 7.1: With Pre-warm ---")
        await self.user_service.get_context(user_id)
        
        async def get_context():
            # 为每个并发请求创建新的 session，模拟真实 API 调用
            async with self.db_session_factory() as db:
                service = UserService(db, self.redis_client)
                return await service.get_context(user_id)

        tasks = [get_context() for _ in range(10)]
        results = await asyncio.gather(*tasks)
        assert all(r is not None for r in results)
        logger.info("✓ All 10 pre-warmed concurrent calls succeeded")

        # 2. 测试冷启动并发 (可能导致多次 DB 查询，但最终结果应一致)
        logger.info("--- Subtest 7.2: Cold Start (No Pre-warm) ---")
        await self.redis_client.delete(f"user:context:{user_id}")
        
        tasks = [get_context() for _ in range(10)]
        results = await asyncio.gather(*tasks)
        assert all(r is not None for r in results)
        # 注意: 如果之前运行过测试，nickname 可能是 "更新后的昵称"
        # 统一检查非空且类型正确即可，或者再次查询数据库确认当前值
        logger.info(f"✓ All 10 cold-start concurrent calls succeeded, first nickname: {results[0].nickname}")

        return True

    async def run_all_tests(self):
        """运行所有测试"""
        try:
            await self.setup()

            tests = [
                ("Cache Lookup", self.test_cache_lookup),
                ("Cache Write", self.test_cache_write),
                ("Cache Invalidation", self.test_cache_invalidation),
                ("Update with Invalidation", self.test_update_with_invalidation),
                ("All Cached Methods", self.test_all_methods_with_cache),
                ("Cache Miss Fallback", self.test_cache_miss_fallback),
                ("Concurrent Access", self.test_concurrent_access),
            ]

            passed = 0
            failed = 0

            for name, test_func in tests:
                try:
                    await test_func()
                    passed += 1
                    logger.info(f"✓ {name} PASSED")
                except AssertionError as e:
                    failed += 1
                    logger.error(f"✗ {name} FAILED: {e}")
                except Exception as e:
                    failed += 1
                    logger.error(f"✗ {name} ERROR: {e}")

            logger.info(f"\n{'='*50}")
            logger.info(f"Test Results: {passed} passed, {failed} failed")
            logger.info(f"{'='*50}")

            return failed == 0

        finally:
            # 清理
            if self.redis_client:
                keys = await self.redis_client.keys("user:*")
                if keys:
                    await self.redis_client.delete(*keys)
                await self.redis_client.close()
            if self.db_engine:
                async with self.db_engine.begin() as conn:
                    await conn.run_sync(Base.metadata.drop_all)
                await self.db_engine.dispose()
            logger.info("✓ Cleanup complete")


async def main():
    """主入口"""
    logger.info("Starting UserService Cache Test")
    logger.info("=" * 60)

    test_suite = UserServiceCacheTestSuite()
    success = await test_suite.run_all_tests()

    if success:
        logger.info("\n🎉 All cache tests passed!")
        return 0
    else:
        logger.error("\n❌ Some cache tests failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
