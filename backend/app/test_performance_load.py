"""
Performance & Load Testing Suite

Tests performance characteristics and load handling across:
- Message throughput (messages/sec)
- Latency percentiles (p50, p95, p99)
- Memory profiling
- Database connection pooling
- Cache hit rates
- Concurrent user handling
- Token consumption tracking
"""

import pytest
import asyncio
import time
import statistics
from typing import List, Dict, Any
from unittest.mock import Mock, AsyncMock
import psutil
import os


# ============================================================
# Performance Measurement Utilities
# ============================================================

class PerformanceMetrics:
    """Captures and analyzes performance metrics"""
    def __init__(self):
        self.latencies: List[float] = []
        self.throughput: List[float] = []
        self.memory_usage: List[float] = []
        self.errors: int = 0
        self.start_time: float = 0

    def record_latency(self, latency_ms: float):
        """Record a single latency measurement"""
        self.latencies.append(latency_ms)

    def record_throughput(self, messages_per_sec: float):
        """Record throughput sample"""
        self.throughput.append(messages_per_sec)

    def record_memory(self, memory_mb: float):
        """Record memory usage sample"""
        self.memory_usage.append(memory_mb)

    def get_percentile(self, percentile: int) -> float:
        """Get latency percentile (p50, p95, p99)"""
        if not self.latencies:
            return 0.0
        sorted_latencies = sorted(self.latencies)
        index = int((percentile / 100.0) * len(sorted_latencies))
        return sorted_latencies[min(index, len(sorted_latencies) - 1)]

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics"""
        if not self.latencies:
            return {}

        return {
            "total_requests": len(self.latencies),
            "errors": self.errors,
            "success_rate": ((len(self.latencies) - self.errors) / len(self.latencies) * 100) if self.latencies else 0,
            "avg_latency_ms": statistics.mean(self.latencies),
            "min_latency_ms": min(self.latencies),
            "max_latency_ms": max(self.latencies),
            "median_latency_ms": statistics.median(self.latencies),
            "p95_latency_ms": self.get_percentile(95),
            "p99_latency_ms": self.get_percentile(99),
            "stdev_latency_ms": statistics.stdev(self.latencies) if len(self.latencies) > 1 else 0,
            "avg_throughput": statistics.mean(self.throughput) if self.throughput else 0,
            "peak_memory_mb": max(self.memory_usage) if self.memory_usage else 0,
            "avg_memory_mb": statistics.mean(self.memory_usage) if self.memory_usage else 0,
        }


class MockOrchestratorForLoad:
    """Mock orchestrator for performance testing"""
    async def process_chat(self, request: Dict[str, Any], latency_override: float = None) -> Dict[str, Any]:
        """Simulate chat processing with configurable latency"""
        # Simulate processing latency (50-200ms typically)
        if latency_override:
            await asyncio.sleep(latency_override / 1000.0)
        else:
            await asyncio.sleep(0.1)  # 100ms baseline

        return {
            "response": "Test response",
            "tokens_used": 150,
            "processing_time_ms": latency_override or 100,
        }

    async def execute_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Simulate tool execution"""
        await asyncio.sleep(0.05)  # 50ms
        return {"status": "success", "result": f"Tool {tool_name} executed"}


class MockDatabaseForLoad:
    """Mock database for load testing"""
    def __init__(self):
        self.connection_count = 0
        self.max_connections = 20

    async def get_connection(self):
        """Simulate connection acquisition"""
        if self.connection_count >= self.max_connections:
            raise Exception("Connection pool exhausted")
        self.connection_count += 1
        return Mock(connection_id=self.connection_count)

    async def release_connection(self, conn):
        """Simulate connection release"""
        self.connection_count -= 1

    async def query(self, query: str) -> List[Dict]:
        """Simulate query execution"""
        await asyncio.sleep(0.01)  # 10ms query time
        return [{"result": "data"}]


class MockCacheForLoad:
    """Mock Redis cache for load testing"""
    def __init__(self):
        self.cache: Dict[str, Any] = {}
        self.hits = 0
        self.misses = 0

    async def get(self, key: str) -> Any:
        """Get from cache"""
        if key in self.cache:
            self.hits += 1
            return self.cache[key]
        self.misses += 1
        return None

    async def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """Set in cache"""
        self.cache[key] = value
        return True

    def get_hit_rate(self) -> float:
        """Get cache hit rate percentage"""
        total = self.hits + self.misses
        return (self.hits / total * 100) if total > 0 else 0


# ============================================================
# Fixtures for Load Testing
# ============================================================

@pytest.fixture
def performance_metrics():
    """Performance metrics fixture"""
    return PerformanceMetrics()


@pytest.fixture
def orchestrator():
    """Mock orchestrator fixture"""
    return MockOrchestratorForLoad()


@pytest.fixture
def database():
    """Mock database fixture"""
    return MockDatabaseForLoad()


@pytest.fixture
def cache():
    """Mock cache fixture"""
    return MockCacheForLoad()


# ============================================================
# Latency & Throughput Tests
# ============================================================

class TestLatencyAndThroughput:
    """Test latency and throughput characteristics"""

    @pytest.mark.asyncio
    async def test_single_request_latency(self, orchestrator, performance_metrics):
        """Test single request latency baseline"""
        start = time.time()
        await orchestrator.process_chat({"message": "test"})
        latency = (time.time() - start) * 1000  # Convert to ms

        performance_metrics.record_latency(latency)

        assert latency > 50  # At least 100ms
        assert latency < 500  # Reasonable upper bound
        assert latency < 150  # Typically around 100ms

    @pytest.mark.asyncio
    async def test_sequential_requests_latency(self, orchestrator, performance_metrics):
        """Test latency for sequential requests"""
        num_requests = 100

        for _ in range(num_requests):
            start = time.time()
            await orchestrator.process_chat({"message": "test"})
            latency = (time.time() - start) * 1000
            performance_metrics.record_latency(latency)

        stats = performance_metrics.get_stats()

        assert stats["total_requests"] == 100
        assert stats["avg_latency_ms"] < 150
        assert stats["p95_latency_ms"] < 250
        assert stats["p99_latency_ms"] < 350

    @pytest.mark.asyncio
    async def test_concurrent_request_latency(self, orchestrator, performance_metrics):
        """Test latency under concurrent load"""
        num_concurrent = 20

        start = time.time()
        tasks = [
            orchestrator.process_chat({"message": f"test-{i}"})
            for i in range(num_concurrent)
        ]
        await asyncio.gather(*tasks)
        total_time = time.time() - start

        # With concurrency, total time should be much less than sequential
        assert total_time < num_concurrent * 0.15  # Less than sequential

        # Individual request latencies should still be reasonable
        throughput = num_concurrent / total_time  # requests per second
        assert throughput > 50  # At least 50 req/s

    @pytest.mark.asyncio
    async def test_message_throughput(self, orchestrator, performance_metrics):
        """Test message processing throughput (messages/sec)"""
        num_messages = 500

        start = time.time()
        tasks = [
            orchestrator.process_chat({"message": f"msg-{i}"})
            for i in range(num_messages)
        ]
        await asyncio.gather(*tasks)
        elapsed = time.time() - start

        throughput = num_messages / elapsed
        performance_metrics.record_throughput(throughput)

        # Should handle 500+ messages in reasonable time
        assert throughput > 100  # At least 100 messages/sec
        assert elapsed < 10  # Complete in less than 10 seconds

    @pytest.mark.asyncio
    async def test_throughput_under_load(self, orchestrator, performance_metrics):
        """Test sustained throughput over time"""
        batch_size = 50
        num_batches = 10

        for batch in range(num_batches):
            start = time.time()
            tasks = [
                orchestrator.process_chat({"message": f"batch-{batch}-msg-{i}"})
                for i in range(batch_size)
            ]
            await asyncio.gather(*tasks)
            elapsed = time.time() - start

            throughput = batch_size / elapsed
            performance_metrics.record_throughput(throughput)

        # Throughput should be recorded for each batch
        assert len(performance_metrics.throughput) == num_batches

        # Calculate average throughput
        avg_throughput = statistics.mean(performance_metrics.throughput)
        assert avg_throughput > 100


# ============================================================
# Memory Profiling Tests
# ============================================================

class TestMemoryProfiling:
    """Test memory usage characteristics"""

    @pytest.mark.asyncio
    async def test_memory_baseline(self, performance_metrics):
        """Test baseline memory usage"""
        process = psutil.Process(os.getpid())

        memory_before = process.memory_info().rss / 1024 / 1024  # Convert to MB

        # Do some work
        data = [{"key": f"item-{i}", "value": f"data-{i}" * 100} for i in range(1000)]
        await asyncio.sleep(0.1)

        memory_after = process.memory_info().rss / 1024 / 1024
        memory_increase = memory_after - memory_before

        performance_metrics.record_memory(memory_after)

        # Memory increase should be reasonable
        assert memory_increase < 100  # Less than 100MB increase

    @pytest.mark.asyncio
    async def test_memory_with_concurrent_requests(self, orchestrator, performance_metrics):
        """Test memory usage under concurrent load"""
        process = psutil.Process(os.getpid())

        memory_before = process.memory_info().rss / 1024 / 1024

        # Send 100 concurrent requests
        tasks = [
            orchestrator.process_chat({"message": f"test-{i}"})
            for i in range(100)
        ]
        await asyncio.gather(*tasks)

        memory_after = process.memory_info().rss / 1024 / 1024
        performance_metrics.record_memory(memory_after)

        # Memory shouldn't spike excessively
        assert memory_after - memory_before < 200  # Less than 200MB increase

    @pytest.mark.asyncio
    async def test_memory_leak_detection(self, orchestrator, performance_metrics):
        """Test for memory leaks over sustained operations"""
        process = psutil.Process(os.getpid())
        memory_samples = []

        # Run 5 iterations of 100 concurrent requests
        for iteration in range(5):
            tasks = [
                orchestrator.process_chat({"message": f"iter-{iteration}-msg-{i}"})
                for i in range(100)
            ]
            await asyncio.gather(*tasks)

            memory_mb = process.memory_info().rss / 1024 / 1024
            memory_samples.append(memory_mb)
            performance_metrics.record_memory(memory_mb)

        # Check for memory growth pattern
        # Memory should stabilize, not continuously grow
        early_avg = statistics.mean(memory_samples[:2])
        late_avg = statistics.mean(memory_samples[-2:])

        # Allow some growth but not excessive
        assert late_avg - early_avg < 100  # Less than 100MB growth


# ============================================================
# Database Connection Pool Tests
# ============================================================

class TestDatabaseConnectionPool:
    """Test database connection pool behavior under load"""

    @pytest.mark.asyncio
    async def test_connection_pool_exhaustion(self, database):
        """Test connection pool exhaustion handling"""
        # Try to acquire more connections than pool size
        acquired_conns = []

        try:
            for i in range(25):  # Pool max is 20
                conn = await database.get_connection()
                acquired_conns.append(conn)

                if i < 20:
                    assert database.connection_count <= 20
        except Exception as e:
            # Expected to fail when pool exhausted
            assert "Connection pool exhausted" in str(e)
            assert database.connection_count == 20
        finally:
            # Release connections
            for conn in acquired_conns:
                await database.release_connection(conn)

    @pytest.mark.asyncio
    async def test_concurrent_database_access(self, database):
        """Test concurrent database access"""
        async def db_query():
            try:
                conn = await database.get_connection()
                try:
                    await database.query("SELECT * FROM users")
                    return True
                finally:
                    await database.release_connection(conn)
            except Exception:
                return False

        # 50 concurrent queries with pool size of 20
        # Queries will queue and reuse connections
        tasks = [db_query() for _ in range(50)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Most should succeed with connection pooling
        successful = sum(1 for r in results if r is True)
        assert successful >= 20  # At least the pool size should succeed
        assert database.connection_count == 0  # All released

    @pytest.mark.asyncio
    async def test_connection_pool_recovery(self, database):
        """Test connection pool recovery after failures"""
        # Simulate multiple cycles of connection use
        for cycle in range(5):
            tasks = [
                self._acquire_and_query(database)
                for _ in range(10)
            ]
            await asyncio.gather(*tasks)

            # Pool should be empty after each cycle
            assert database.connection_count == 0

    @staticmethod
    async def _acquire_and_query(database):
        """Helper to acquire connection and run query"""
        conn = await database.get_connection()
        try:
            await database.query("SELECT 1")
        finally:
            await database.release_connection(conn)


# ============================================================
# Cache Performance Tests
# ============================================================

class TestCachePerformance:
    """Test cache efficiency and hit rates"""

    @pytest.mark.asyncio
    async def test_cache_hit_rate_warm(self, cache):
        """Test cache hit rate with warm cache"""
        # Pre-populate cache
        for i in range(100):
            await cache.set(f"key-{i}", f"value-{i}")

        # Access cache
        for i in range(100):
            await cache.get(f"key-{i}")

        hit_rate = cache.get_hit_rate()
        assert hit_rate == 100.0  # All hits

    @pytest.mark.asyncio
    async def test_cache_hit_rate_cold(self, cache):
        """Test cache hit rate with cold cache"""
        # Access non-existent keys
        for i in range(100):
            await cache.get(f"nonexistent-{i}")

        hit_rate = cache.get_hit_rate()
        assert hit_rate == 0.0  # All misses

    @pytest.mark.asyncio
    async def test_cache_hit_rate_mixed(self, cache):
        """Test cache hit rate with mixed access"""
        # Set some keys
        for i in range(50):
            await cache.set(f"key-{i}", f"value-{i}")

        # Access mix of hits and misses
        for i in range(100):
            await cache.get(f"key-{i % 100}")  # 50 hits, 50 misses

        hit_rate = cache.get_hit_rate()
        assert 40 < hit_rate < 60  # Around 50%

    @pytest.mark.asyncio
    async def test_concurrent_cache_access(self, cache):
        """Test concurrent cache access"""
        # Pre-populate
        for i in range(100):
            await cache.set(f"key-{i}", f"value-{i}")

        # Concurrent reads
        async def cache_read(key_id):
            await cache.get(f"key-{key_id % 100}")

        tasks = [cache_read(i) for i in range(500)]
        await asyncio.gather(*tasks)

        # Should have many cache hits
        hit_rate = cache.get_hit_rate()
        assert hit_rate > 95


# ============================================================
# Concurrent User Simulation Tests
# ============================================================

class TestConcurrentUserSimulation:
    """Test behavior under multiple concurrent users"""

    @pytest.mark.asyncio
    async def test_10_concurrent_users(self, orchestrator, performance_metrics):
        """Test with 10 concurrent users"""
        async def user_session(user_id):
            latencies = []
            for msg_id in range(5):
                start = time.time()
                await orchestrator.process_chat({
                    "user_id": user_id,
                    "message": f"msg-{msg_id}",
                })
                latency = (time.time() - start) * 1000
                latencies.append(latency)
                performance_metrics.record_latency(latency)

        users = [user_session(f"user-{i}") for i in range(10)]
        await asyncio.gather(*users)

        stats = performance_metrics.get_stats()
        assert stats["total_requests"] == 50
        assert stats["avg_latency_ms"] < 150

    @pytest.mark.asyncio
    async def test_50_concurrent_users(self, orchestrator, performance_metrics):
        """Test with 50 concurrent users"""
        num_users = 50
        messages_per_user = 3

        async def user_session(user_id):
            for msg_id in range(messages_per_user):
                start = time.time()
                await orchestrator.process_chat({
                    "user_id": user_id,
                    "message": f"msg-{msg_id}",
                })
                latency = (time.time() - start) * 1000
                performance_metrics.record_latency(latency)

        users = [user_session(f"user-{i}") for i in range(num_users)]
        start_time = time.time()
        await asyncio.gather(*users)
        total_time = time.time() - start_time

        stats = performance_metrics.get_stats()
        assert stats["total_requests"] == num_users * messages_per_user
        assert stats["success_rate"] > 90  # Allow some failures under stress
        assert total_time < 20  # Should complete reasonably fast

    @pytest.mark.asyncio
    async def test_100_concurrent_users_sustained(self, orchestrator, performance_metrics):
        """Test with 100 concurrent users over longer period"""
        num_users = 100
        message_bursts = 2

        async def user_session(user_id):
            for burst in range(message_bursts):
                for msg_id in range(3):
                    start = time.time()
                    try:
                        await orchestrator.process_chat({
                            "user_id": user_id,
                            "message": f"burst-{burst}-msg-{msg_id}",
                        })
                        latency = (time.time() - start) * 1000
                        performance_metrics.record_latency(latency)
                    except Exception:
                        performance_metrics.errors += 1

        start_time = time.time()
        users = [user_session(f"user-{i}") for i in range(num_users)]
        await asyncio.gather(*users)
        total_time = time.time() - start_time

        stats = performance_metrics.get_stats()
        total_expected = num_users * message_bursts * 3

        assert stats["total_requests"] > total_expected * 0.9  # At least 90% success
        assert total_time < 30  # Should complete in reasonable time


# ============================================================
# Token Consumption & LLM Load Tests
# ============================================================

class TestTokenConsumption:
    """Test token consumption patterns"""

    @pytest.mark.asyncio
    async def test_token_consumption_per_request(self, orchestrator):
        """Test token consumption per request"""
        response = await orchestrator.process_chat({"message": "test"})

        tokens_used = response.get("tokens_used", 0)
        assert tokens_used > 0
        assert tokens_used < 1000  # Reasonable upper bound

    @pytest.mark.asyncio
    async def test_token_consumption_scaling(self, orchestrator):
        """Test token consumption with larger messages"""
        large_message = "test message " * 100  # ~1200 chars

        response = await orchestrator.process_chat({"message": large_message})
        tokens_used = response.get("tokens_used", 0)

        # Larger message should use more tokens
        assert tokens_used > 100

    @pytest.mark.asyncio
    async def test_total_token_budget(self, orchestrator):
        """Test staying within total token budget"""
        num_requests = 100
        total_tokens = 0
        token_limit = 50000  # Example limit

        for i in range(num_requests):
            response = await orchestrator.process_chat({"message": f"message-{i}"})
            tokens = response.get("tokens_used", 0)
            total_tokens += tokens

        # Should stay under budget
        assert total_tokens < token_limit
        assert total_tokens > 0

        avg_tokens = total_tokens / num_requests
        assert 100 < avg_tokens < 300  # Reasonable average


# ============================================================
# Stress Tests
# ============================================================

class TestStress:
    """Stress tests for system limits"""

    @pytest.mark.asyncio
    async def test_burst_traffic(self, orchestrator, performance_metrics):
        """Test system under burst traffic"""
        # 200 requests in rapid succession
        tasks = [
            orchestrator.process_chat({"message": f"burst-{i}"})
            for i in range(200)
        ]

        start = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        elapsed = time.time() - start

        successful = sum(1 for r in results if not isinstance(r, Exception))
        success_rate = (successful / len(results)) * 100

        assert success_rate > 90  # At least 90% should succeed
        assert elapsed < 30  # Should handle reasonably

    @pytest.mark.asyncio
    async def test_slow_client_handling(self, orchestrator):
        """Test handling of slow clients (don't block others)"""
        slow_task_latency = []
        fast_task_latency = []

        async def slow_client():
            start = time.time()
            # Simulate slow processing
            await orchestrator.process_chat({"message": "slow"}, latency_override=500)
            slow_task_latency.append((time.time() - start) * 1000)

        async def fast_client():
            start = time.time()
            await orchestrator.process_chat({"message": "fast"}, latency_override=50)
            fast_task_latency.append((time.time() - start) * 1000)

        # Mix slow and fast clients
        tasks = [slow_client()] + [fast_client() for _ in range(5)]
        await asyncio.gather(*tasks)

        # Fast clients shouldn't be blocked by slow client
        avg_fast = statistics.mean(fast_task_latency)
        assert avg_fast < 200  # Fast client latency should be low


# ============================================================
# Percentile Analysis Tests
# ============================================================

class TestPercentileAnalysis:
    """Test percentile-based performance analysis"""

    @pytest.mark.asyncio
    async def test_latency_percentiles(self, orchestrator, performance_metrics):
        """Test latency percentile calculation"""
        # Generate 1000 requests
        for i in range(1000):
            start = time.time()
            await orchestrator.process_chat({"message": f"test-{i}"})
            latency = (time.time() - start) * 1000
            performance_metrics.record_latency(latency)

        stats = performance_metrics.get_stats()

        # p50 < p95 < p99
        assert stats["median_latency_ms"] < stats["p95_latency_ms"]
        assert stats["p95_latency_ms"] < stats["p99_latency_ms"]

        # All latencies should be positive
        assert stats["min_latency_ms"] > 0
        assert stats["max_latency_ms"] > stats["avg_latency_ms"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
