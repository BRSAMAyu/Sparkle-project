#!/usr/bin/env python3
"""
Token Metering System - End-to-End Integration Test

Tests the complete token metering flow:
1. TokenTracker records usage
2. Validator checks quota
3. BillingWorker persists to database
4. Statistics and reporting
"""

import sys
import os
import asyncio
import json
from datetime import datetime

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import redis.asyncio as redis
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from loguru import logger

# Import our components
from app.orchestration.token_tracker import TokenTracker
from app.orchestration.validator import RequestValidator
from app.services.billing_worker import BillingWorker
from app.models.chat import TokenUsage
from app.models.base import Base


# Test configuration
REDIS_URL = "redis://:devpassword@localhost:6379/1"
DATABASE_URL = "sqlite+aiosqlite:///./test_token_metering.db"


class TokenMeteringTestSuite:
    """Complete test suite for token metering system"""

    def __init__(self):
        self.redis_client = None
        self.db_engine = None
        self.db_session_factory = None
        self.token_tracker = None
        self.validator = None
        self.billing_worker = None

    async def setup(self):
        """Setup test environment"""
        logger.info("Setting up test environment...")

        # Connect to Redis
        self.redis_client = redis.from_url(REDIS_URL, decode_responses=False)
        try:
            await self.redis_client.ping()
            logger.info("✓ Redis connected")
        except Exception as e:
            logger.error(f"✗ Redis connection failed: {e}")
            raise

        # Clean up any existing test data first
        patterns = [
            "user:daily_tokens:*",
            "session:tokens:*",
            "queue:billing",
            "user:details:*",
            "model:tokens:*",
        ]
        for pattern in patterns:
            keys = await self.redis_client.keys(pattern)
            if keys:
                await self.redis_client.delete(*keys)

        # Setup database
        self.db_engine = create_async_engine(DATABASE_URL, echo=False)
        self.db_session_factory = sessionmaker(
            self.db_engine, class_=AsyncSession, expire_on_commit=False
        )

        # Drop and recreate tables
        async with self.db_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✓ Database tables created")

        # Initialize components
        self.token_tracker = TokenTracker(self.redis_client)
        self.validator = RequestValidator(self.redis_client, daily_quota=100000)
        self.billing_worker = BillingWorker(
            redis_client=self.redis_client,
            db_session_factory=self.db_session_factory,
            batch_size=5,
            flush_interval=2,
            worker_id="test-worker"
        )

        logger.info("✓ All components initialized")

    async def cleanup(self):
        """Cleanup test data"""
        logger.info("Cleaning up test data...")

        # Clear Redis test data
        if self.redis_client:
            # Clear all test-related keys
            patterns = [
                "user:daily_tokens:*",
                "session:tokens:*",
                "queue:billing",
                "user:details:*",
                "model:tokens:*",
                "test:*"
            ]
            for pattern in patterns:
                keys = await self.redis_client.keys(pattern)
                if keys:
                    await self.redis_client.delete(*keys)

        # Drop tables
        if self.db_engine:
            async with self.db_engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)

        logger.info("✓ Cleanup complete")

    async def test_token_tracker(self):
        """Test TokenTracker functionality"""
        logger.info("\n=== Test 1: TokenTracker ===")

        user_id = "00000000-0000-0000-0000-000000000001"
        session_id = "test_session_001"
        request_id = "test_request_001"

        # Test 1: Record usage
        total = await self.token_tracker.record_usage(
            user_id=user_id,
            session_id=session_id,
            request_id=request_id,
            prompt_tokens=150,
            completion_tokens=250,
            model="gpt-4",
            cost=0.012
        )

        assert total == 400, f"Expected 400, got {total}"
        logger.info(f"✓ Record usage: {total} tokens")

        # Test 2: Get daily usage
        daily_usage = await self.token_tracker.get_daily_usage(user_id)
        assert daily_usage == 400, f"Expected 400, got {daily_usage}"
        logger.info(f"✓ Daily usage: {daily_usage} tokens")

        # Test 3: Check quota
        quota = await self.token_tracker.check_quota(user_id, daily_limit=100000)
        assert quota["within_quota"] == True
        assert quota["used"] == 400
        assert quota["remaining"] == 99600
        logger.info(f"✓ Quota check: {quota['percentage']} used")

        # Test 4: Get session usage
        session_usage = await self.token_tracker.get_session_usage(session_id)
        assert session_usage == 400, f"Expected 400, got {session_usage}"
        logger.info(f"✓ Session usage: {session_usage} tokens")

        # Test 5: Cost estimation
        cost = await self.token_tracker.estimate_cost(1000, 500, "gpt-4")
        # gpt-4: $0.03/1k input, $0.06/1k output
        # (1000*0.03 + 500*0.06) / 1000 = $0.06
        assert cost == 0.06, f"Expected 0.06, got {cost}"
        logger.info(f"✓ Cost estimation: ${cost}")

        # Test 6: Multiple records
        await self.token_tracker.record_usage(
            user_id=user_id,
            session_id=session_id,
            request_id="test_request_002",
            prompt_tokens=100,
            completion_tokens=200,
            model="gpt-4"
        )

        daily_usage = await self.token_tracker.get_daily_usage(user_id)
        assert daily_usage == 700, f"Expected 700, got {daily_usage}"
        logger.info(f"✓ Multiple records: {daily_usage} tokens total")

        return True

    async def test_validator_quota(self):
        """Test validator quota enforcement"""
        logger.info("\n=== Test 2: Validator Quota ===")

        # Setup: Create a mock request
        from app.gen.agent.v1 import agent_service_pb2

        user_id = "00000000-0000-0000-0000-000000000002"

        # Test 1: Within quota
        request = agent_service_pb2.ChatRequest(
            user_id=user_id,
            session_id="test_session_002",
            request_id="test_request_003",
            message="Hello, world!"
        )

        # Record some usage first
        await self.token_tracker.record_usage(
            user_id=user_id,
            session_id="test_session_002",
            request_id="test_request_003",
            prompt_tokens=50,
            completion_tokens=50,
            model="gpt-4"
        )

        result = await self.validator.validate_chat_request(request)
        assert result.is_valid == True, f"Expected valid, got {result.error_message}"
        logger.info("✓ Request within quota validated")

        # Test 2: Exceed quota
        # Record 99,900 more tokens to reach 100,000
        for i in range(100):
            await self.token_tracker.record_usage(
                user_id=user_id,
                session_id="test_session_002",
                request_id=f"test_request_{i+4}",
                prompt_tokens=500,
                completion_tokens=500,
                model="gpt-4"
            )

        # Now validate again
        request2 = agent_service_pb2.ChatRequest(
            user_id=user_id,
            session_id="test_session_002",
            request_id="test_request_104",
            message="Another message"
        )

        result2 = await self.validator.validate_chat_request(request2)
        assert result2.is_valid == False, "Expected invalid due to quota"
        assert "quota exceeded" in result2.error_message.lower()
        logger.info(f"✓ Quota exceeded rejected: {result2.error_message}")

        return True

    async def test_billing_worker(self):
        """Test BillingWorker persistence"""
        logger.info("\n=== Test 3: Billing Worker ===")

        # Clear queue first
        await self.redis_client.delete("queue:billing")

        # Add multiple records to queue
        user_id = "00000000-0000-0000-0000-000000000003"
        for i in range(10):
            await self.token_tracker.record_usage(
                user_id=user_id,
                session_id=f"test_session_{i}",
                request_id=f"test_request_{i}",
                prompt_tokens=100 + i * 10,
                completion_tokens=50 + i * 5,
                model="gpt-4",
                cost=0.003 + i * 0.0001
            )

        # Verify records are in queue
        queue_len = await self.redis_client.llen("queue:billing")
        assert queue_len == 10, f"Expected 10 records in queue, got {queue_len}"
        logger.info(f"✓ Records queued: {queue_len}")

        # Start billing worker in background
        worker_task = asyncio.create_task(self.billing_worker.start())
        await asyncio.sleep(3)  # Wait for worker to process

        # Stop worker
        await self.billing_worker.stop()
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass

        # Verify records were persisted to database
        async with self.db_session_factory() as db:
            result = await db.execute(
                TokenUsage.__table__.select().where(
                    TokenUsage.user_id == user_id
                )
            )
            records = result.fetchall()

        assert len(records) == 10, f"Expected 10 records in DB, got {len(records)}"
        logger.info(f"✓ Records persisted: {len(records)}")

        # Verify data integrity
        total_tokens = sum(r.total_tokens for r in records)
        expected_tokens = sum(150 + i * 15 for i in range(10))
        assert total_tokens == expected_tokens, f"Expected {expected_tokens}, got {total_tokens}"
        logger.info(f"✓ Data integrity: {total_tokens} total tokens")

        return True

    async def test_billing_statistics(self):
        """Test BillingWorker statistics methods"""
        logger.info("\n=== Test 4: Billing Statistics ===")

        # Use the same user_id as the billing worker test
        user_id = "00000000-0000-0000-0000-000000000003"

        # Ensure we have data in DB from previous test
        # Get daily revenue stats
        stats = await self.billing_worker.get_daily_revenue()
        logger.info(f"✓ Daily revenue: ${stats['total_cost']:.6f}, {stats['total_tokens']} tokens, {stats['request_count']} requests")

        # Get user stats
        user_stats = await self.billing_worker.get_user_stats(user_id, days=1)
        logger.info(f"✓ User stats: {user_stats['total_tokens']} tokens, ${user_stats['total_cost']:.6f} cost")

        assert stats['request_count'] > 0
        assert user_stats['total_tokens'] > 0

        return True

    async def test_concurrent_operations(self):
        """Test concurrent token tracking"""
        logger.info("\n=== Test 5: Concurrent Operations ===")

        user_id = "00000000-0000-0000-0000-000000000004"

        async def record_usage_async(i):
            await self.token_tracker.record_usage(
                user_id=user_id,
                session_id=f"concurrent_session_{i}",
                request_id=f"concurrent_request_{i}",
                prompt_tokens=100,
                completion_tokens=100,
                model="gpt-4"
            )

        # Run 20 concurrent operations
        tasks = [record_usage_async(i) for i in range(20)]
        await asyncio.gather(*tasks)

        # Verify total
        total = await self.token_tracker.get_daily_usage(user_id)
        assert total == 4000, f"Expected 4000, got {total}"
        logger.info(f"✓ Concurrent operations: {total} tokens from 20 requests")

        return True

    async def run_all_tests(self):
        """Run all tests"""
        try:
            await self.setup()

            tests = [
                ("TokenTracker", self.test_token_tracker),
                ("Validator Quota", self.test_validator_quota),
                ("Billing Worker", self.test_billing_worker),
                ("Statistics", self.test_billing_statistics),
                ("Concurrent", self.test_concurrent_operations),
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
            await self.cleanup()
            if self.redis_client:
                await self.redis_client.close()
            if self.db_engine:
                await self.db_engine.dispose()


async def main():
    """Main entry point"""
    logger.info("Starting Token Metering System Integration Test")
    logger.info("=" * 60)

    test_suite = TokenMeteringTestSuite()
    success = await test_suite.run_all_tests()

    if success:
        logger.info("\n🎉 All tests passed!")
        return 0
    else:
        logger.error("\n❌ Some tests failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
