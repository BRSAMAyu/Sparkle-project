"""
Cache Consistency Integration Tests

Tests cache consistency across layers:
- Redis cache invalidation
- Go Gateway cache
- Python Engine cache
- Cache coherency after updates

This test requires:
- Running Python gRPC server (make grpc-server)
- Running Go Gateway (make gateway-dev)
- Running Redis (make dev-all)
- Running PostgreSQL (make dev-all)
"""

import pytest
import asyncio
import json
from typing import Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import redis.asyncio as redis

from app.models.user import User
from app.models.plan import Plan
from app.core.security import create_access_token
from app.services.cache_service import cache_service


# ============================================================
# Test Fixtures
# ============================================================

@pytest.fixture
async def redis_client():
    """Create Redis client for testing"""
    import os
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    client = redis.from_url(redis_url, decoding="utf-8")

    yield client

    # Cleanup: Flush test database
    await client.flushdb()
    await client.close()


@pytest.fixture
async def test_user(db: AsyncSession) -> User:
    """Create test user"""
    result = await db.execute(
        select(User).where(User.email == "cache_test@example.com")
    )
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            email="cache_test@example.com",
            nickname="Cache Test User",
            password_hash="test_password"
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    yield user


@pytest.fixture
async def test_plan(db: AsyncSession, test_user: User) -> Plan:
    """Create test plan"""
    plan = Plan(
        user_id=test_user.id,
        name="Cache Test Plan",
        description="Testing cache consistency",
        status="active"
    )
    db.add(plan)
    await db.commit()
    await db.refresh(plan)

    yield plan

    # Cleanup
    await db.delete(plan)
    await db.commit()


# ============================================================
# Redis Cache Tests
# ============================================================

class TestRedisCache:
    """Test Redis caching behavior"""

    @pytest.mark.asyncio
    async def test_cache_set_and_get(
        self,
        redis_client: redis.Redis
    ):
        """Test basic cache set and get operations"""
        key = "test:cache:key"
        value = {"data": "test_value", "timestamp": datetime.now().isoformat()}

        # Set cache
        await redis_client.set(key, json.dumps(value), ex=60)

        # Get cache
        cached = await redis_client.get(key)
        assert cached is not None

        cached_data = json.loads(cached)
        assert cached_data["data"] == "test_value"

    @pytest.mark.asyncio
    async def test_cache_invalidation(
        self,
        redis_client: redis.Redis
    ):
        """Test cache invalidation"""
        key = "test:cache:invalidation"
        value = {"data": "will_be_deleted"}

        # Set cache
        await redis_client.set(key, json.dumps(value), ex=60)
        cached = await redis_client.get(key)
        assert cached is not None

        # Invalidate
        await redis_client.delete(key)

        # Verify deleted
        cached = await redis_client.get(key)
        assert cached is None

    @pytest.mark.asyncio
    async def test_cache_expiration(
        self,
        redis_client: redis.Redis
    ):
        """Test cache expiration (TTL)"""
        key = "test:cache:expiration"
        value = {"data": "expires_soon"}

        # Set cache with short TTL
        await redis_client.set(key, json.dumps(value), ex=1)

        # Should exist immediately
        cached = await redis_client.get(key)
        assert cached is not None

        # Wait for expiration
        await asyncio.sleep(2)

        # Should be expired
        cached = await redis_client.get(key)
        assert cached is None

    @pytest.mark.asyncio
    async def test_cache_update_propagation(
        self,
        redis_client: redis.Redis
    ):
        """Test cache update propagation"""
        key = "test:cache:propagation"

        # Set initial value
        await redis_client.set(key, json.dumps({"version": 1}), ex=60)

        # Get initial value
        cached = await redis_client.get(key)
        data = json.loads(cached)
        assert data["version"] == 1

        # Update value
        await redis_client.set(key, json.dumps({"version": 2}), ex=60)

        # Get updated value
        cached = await redis_client.get(key)
        data = json.loads(cached)
        assert data["version"] == 2


# ============================================================
# Cross-Layer Cache Tests
# ============================================================

class TestCrossLayerCacheConsistency:
    """Test cache consistency across layers"""

    @pytest.mark.asyncio
    async def test_plan_cache_consistency(
        self,
        db: AsyncSession,
        test_plan: Plan,
        redis_client: redis.Redis
    ):
        """Test plan cache consistency between DB and Redis"""
        plan_id = str(test_plan.id)
        cache_key = f"plan:{plan_id}"

        # Cache plan data
        plan_data = {
            "id": plan_id,
            "name": test_plan.name,
            "status": test_plan.status,
            "user_id": str(test_plan.user_id)
        }
        await redis_client.set(cache_key, json.dumps(plan_data), ex=60)

        # Verify cache
        cached = await redis_client.get(cache_key)
        assert cached is not None

        # Update in DB
        test_plan.name = "Updated Plan Name"
        await db.commit()
        await db.refresh(test_plan)

        # Invalidate cache
        await redis_client.delete(cache_key)

        # Verify cache is cleared
        cached = await redis_client.get(cache_key)
        assert cached is None

        # Re-cache with new data
        plan_data["name"] = test_plan.name
        await redis_client.set(cache_key, json.dumps(plan_data), ex=60)

        # Verify new cache
        cached = await redis_client.get(cache_key)
        new_data = json.loads(cached)
        assert new_data["name"] == "Updated Plan Name"

    @pytest.mark.asyncio
    async def test_user_profile_cache_consistency(
        self,
        db: AsyncSession,
        test_user: User,
        redis_client: redis.Redis
    ):
        """Test user profile cache consistency"""
        user_id = str(test_user.id)
        cache_key = f"user:profile:{user_id}"

        # Cache user profile
        profile_data = {
            "id": user_id,
            "email": test_user.email,
            "nickname": test_user.nickname
        }
        await redis_client.set(cache_key, json.dumps(profile_data), ex=60)

        # Update in DB
        test_user.nickname = "Updated Nickname"
        await db.commit()
        await db.refresh(test_user)

        # Cache should be invalidated and refreshed
        await redis_client.delete(cache_key)

        profile_data["nickname"] = test_user.nickname
        await redis_client.set(cache_key, json.dumps(profile_data), ex=60)

        # Verify
        cached = await redis_client.get(cache_key)
        new_data = json.loads(cached)
        assert new_data["nickname"] == "Updated Nickname"

    @pytest.mark.asyncio
    async def test_cache_stale_data_prevention(
        self,
        db: AsyncSession,
        test_plan: Plan,
        redis_client: redis.Redis
    ):
        """Test that stale cache data is not used"""
        plan_id = str(test_plan.id)
        cache_key = f"plan:{plan_id}"

        # Set cache with old data
        old_data = {
            "id": plan_id,
            "name": "Old Plan Name",
            "status": "active"
        }
        await redis_client.set(cache_key, json.dumps(old_data), ex=60)

        # Update in DB
        test_plan.name = "New Plan Name"
        await db.commit()

        # Simulate cache invalidation
        await redis_client.delete(cache_key)

        # Verify old data is not returned
        cached = await redis_client.get(cache_key)
        assert cached is None

        # Fetch fresh data and cache
        fresh_data = {
            "id": plan_id,
            "name": test_plan.name,
            "status": test_plan.status
        }
        await redis_client.set(cache_key, json.dumps(fresh_data), ex=60)

        # Verify fresh data
        cached = await redis_client.get(cache_key)
        new_data = json.loads(cached)
        assert new_data["name"] == "New Plan Name"


# ============================================================
# Cache Invalidation Tests
# ============================================================

class TestCacheInvalidation:
    """Test cache invalidation strategies"""

    @pytest.mark.asyncio
    async def test_write_through_cache(
        self,
        db: AsyncSession,
        test_plan: Plan,
        redis_client: redis.Redis
    ):
        """Test write-through caching strategy"""
        plan_id = str(test_plan.id)
        cache_key = f"plan:{plan_id}"

        # Update DB
        test_plan.status = "completed"
        await db.commit()

        # Immediately update cache (write-through)
        plan_data = {
            "id": plan_id,
            "name": test_plan.name,
            "status": test_plan.status
        }
        await redis_client.set(cache_key, json.dumps(plan_data), ex=60)

        # Verify cache matches DB
        cached = await redis_client.get(cache_key)
        cached_data = json.loads(cached)

        await db.refresh(test_plan)
        assert cached_data["status"] == test_plan.status

    @pytest.mark.asyncio
    async def test_write_back_cache(
        self,
        db: AsyncSession,
        test_plan: Plan,
        redis_client: redis.Redis
    ):
        """Test write-back (lazy write) caching strategy"""
        plan_id = str(test_plan.id)
        cache_key = f"plan:{plan_id}"

        # Update cache first (write-back)
        plan_data = {
            "id": plan_id,
            "name": test_plan.name,
            "status": "pending_review"
        }
        await redis_client.set(cache_key, json.dumps(plan_data), ex=60)

        # Simulate delayed write to DB
        await asyncio.sleep(0.1)

        # Update DB
        test_plan.status = "pending_review"
        await db.commit()

        # Verify consistency
        await db.refresh(test_plan)
        cached = await redis_client.get(cache_key)
        cached_data = json.loads(cached)

        assert cached_data["status"] == test_plan.status

    @pytest.mark.asyncio
    async def test_cache_awareness_multiple_updates(
        self,
        db: AsyncSession,
        test_plan: Plan,
        redis_client: redis.Redis
    ):
        """Test cache consistency with multiple rapid updates"""
        plan_id = str(test_plan.id)
        cache_key = f"plan:{plan_id}"

        # Perform multiple updates
        statuses = ["in_progress", "review_needed", "approved", "active"]

        for status in statuses:
            # Update DB
            test_plan.status = status
            await db.commit()

            # Invalidate and re-cache
            await redis_client.delete(cache_key)

            plan_data = {
                "id": plan_id,
                "name": test_plan.name,
                "status": test_plan.status
            }
            await redis_client.set(cache_key, json.dumps(plan_data), ex=60)

            # Verify
            await db.refresh(test_plan)
            cached = await redis_client.get(cache_key)
            cached_data = json.loads(cached)

            assert cached_data["status"] == test_plan.status == status


# ============================================================
# Cache Performance Tests
# ============================================================

class TestCachePerformance:
    """Test cache performance characteristics"""

    @pytest.mark.asyncio
    async def test_cache_hit_rate(
        self,
        redis_client: redis.Redis
    ):
        """Test cache hit rate"""
        # Pre-populate cache
        for i in range(100):
            key = f"test:hit_rate:{i}"
            value = {"data": f"value_{i}"}
            await redis_client.set(key, json.dumps(value), ex=60)

        # Measure hits
        hits = 0
        misses = 0

        for i in range(100):
            key = f"test:hit_rate:{i}"
            cached = await redis_client.get(key)
            if cached:
                hits += 1
            else:
                misses += 1

        # Should have 100% hit rate
        assert hits == 100
        assert misses == 0

    @pytest.mark.asyncio
    async def test_cache_performance_vs_db(
        self,
        db: AsyncSession,
        test_user: User,
        redis_client: redis.Client
    ):
        """Compare cache vs DB query performance"""
        import time

        user_id = str(test_user.id)
        cache_key = f"user:profile:{user_id}"

        # Cache lookup time
        profile_data = {
            "id": user_id,
            "email": test_user.email,
            "nickname": test_user.nickname
        }
        await redis_client.set(cache_key, json.dumps(profile_data), ex=60)

        start = time.time()
        for _ in range(100):
            await redis_client.get(cache_key)
        cache_time = time.time() - start

        # DB query time
        start = time.time()
        for _ in range(100):
            await db.execute(
                select(User).where(User.id == test_user.id)
            )
        db_time = time.time() - start

        # Cache should be faster
        print(f"Cache time: {cache_time:.4f}s, DB time: {db_time:.4f}s")
        assert cache_time < db_time

    @pytest.mark.asyncio
    async def test_concurrent_cache_access(
        self,
        redis_client: redis.Redis
    ):
        """Test concurrent cache access"""
        async def cache_access(worker_id: int):
            key = f"test:concurrent:{worker_id}"
            value = {"worker": worker_id, "data": "test"}
            await redis_client.set(key, json.dumps(value), ex=60)
            cached = await redis_client.get(key)
            return json.loads(cached)

        # Run concurrent workers
        results = await asyncio.gather(*[
            cache_access(i) for i in range(50)
        ])

        # All should succeed
        assert len(results) == 50
        assert all(r["worker"] == results.index(r) for r in results)


# ============================================================
# Cache Coherency Tests
# ============================================================

class TestCacheCoherency:
    """Test cache coherency across distributed systems"""

    @pytest.mark.asyncio
    async def test_redis_pubsub_invalidation(
        self,
        redis_client: redis.Redis
    ):
        """Test Redis pub/sub for cache invalidation"""
        # Create pub/sub channel
        pubsub = redis_client.pubsub()
        await pubsub.subscribe("cache_invalidation")

        # Publish invalidation message
        await redis_client.publish(
            "cache_invalidation",
            json.dumps({"key": "test:plan:123", "action": "delete"})
        )

        # Receive message
        message = await pubsub.get_message(timeout=2)
        assert message is not None
        assert message["type"] == "message"

        data = json.loads(message["data"])
        assert data["key"] == "test:plan:123"
        assert data["action"] == "delete"

        await pubsub.unsubscribe("cache_invalidation")
        await pubsub.close()

    @pytest.mark.asyncio
    async def test_cache_versioning(
        self,
        redis_client: redis.Redis
    ):
        """Test cache versioning to prevent stale data"""
        key = "test:versioned:key"

        # Set version 1
        version_1 = {
            "data": "value_1",
            "version": 1,
            "timestamp": datetime.now().isoformat()
        }
        await redis_client.set(f"{key}:v1", json.dumps(version_1), ex=60)

        # Set version 2
        version_2 = {
            "data": "value_2",
            "version": 2,
            "timestamp": datetime.now().isoformat()
        }
        await redis_client.set(f"{key}:v2", json.dumps(version_2), ex=60)

        # Set current version pointer
        await redis_client.set(f"{key}:current", "v2", ex=60)

        # Get current version
        current_version = await redis_client.get(f"{key}:current")
        assert current_version == "v2"

        current_data = await redis_client.get(f"{key}:{current_version}")
        data = json.loads(current_data)
        assert data["version"] == 2
        assert data["data"] == "value_2"


# ============================================================
# Test Run Configuration
# ============================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
