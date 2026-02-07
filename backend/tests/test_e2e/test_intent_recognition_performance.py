"""
Performance Benchmark Suite for Intent Recognition
===================================================

Measures performance metrics for Core Chain 1 components:
- Intent classification latency (Tier-1/2/3)
- Sufficiency check latency
- Memory usage
- Concurrent throughput

Run with:
    pytest tests/test_e2e/test_intent_recognition_performance.py -v -s
"""
import pytest
import asyncio
import time
import tracemalloc
from typing import List, Dict, Any
from collections import defaultdict

from app.orchestration.request_router import RequestRouter
from app.orchestration.sufficiency_checker import SufficiencyChecker


# =============================================================================
# Performance Fixtures
# =============================================================================

@pytest.fixture
def performance_metrics():
    """Track performance metrics across tests"""
    return {
        "latencies": defaultdict(list),
        "memory_usage": [],
        "throughput": {},
    }


@pytest.fixture
def request_router():
    """Create a lightweight router instance for local performance tests."""
    return RequestRouter(redis_client=None)


@pytest.fixture
def sufficiency_checker():
    """Create checker with non-strict mode for benchmark stability."""
    return SufficiencyChecker(strict_mode=False)


# =============================================================================
# Suite 1: Latency Benchmarks
# =============================================================================

class TestLatencyBenchmarks:
    """测试延迟性能指标"""

    @pytest.mark.asyncio
    async def test_tier1_classification_latency(self, request_router, performance_metrics):
        """
        Tier-1 (关键词匹配) 延迟基准
        目标: <10ms (P50), <25ms (P95)
        """
        test_messages = [
            "你好",
            "帮我制定学习计划",
            "翻译这个",
            "我的学习画像",
            "进入冲刺模式",
            "创建任务",
            "查询计划",
            "删除任务",
        ] * 10  # 80 iterations

        latencies = []
        for message in test_messages:
            start = time.perf_counter()
            await request_router._classify_intent_with_confidence(message)
            latency_ms = (time.perf_counter() - start) * 1000
            latencies.append(latency_ms)

        # Calculate percentiles
        latencies.sort()
        p50 = latencies[len(latencies) // 2]
        p95 = latencies[int(len(latencies) * 0.95)]
        p99 = latencies[int(len(latencies) * 0.99)]

        performance_metrics["latencies"]["tier1"] = latencies

        # Assertions
        assert p50 < 10, f"Tier-1 P50 latency too high: {p50:.2f}ms (target: <10ms)"
        assert p95 < 25, f"Tier-1 P95 latency too high: {p95:.2f}ms (target: <25ms)"

        print(f"\nTier-1 Latency Distribution:")
        print(f"  P50: {p50:.2f}ms")
        print(f"  P95: {p95:.2f}ms")
        print(f"  P99: {p99:.2f}ms")
        print(f"  Mean: {sum(latencies)/len(latencies):.2f}ms")

    @pytest.mark.asyncio
    async def test_sufficiency_check_latency(self, sufficiency_checker, performance_metrics):
        """
        信息充分性检查延迟基准
        目标: <50ms (P50)
        """
        test_cases = [
            {
                "intent": "create_task",
                "entities": {},
                "context": [],
            },
            {
                "intent": "create_task",
                "entities": {"task_title": "Study math"},
                "context": [],
            },
            {
                "intent": "delete_task",
                "entities": {"task_id": "123"},
                "context": [],
            },
        ] * 20  # 60 iterations

        latencies = []
        for case in test_cases:
            start = time.perf_counter()
            await sufficiency_checker.check(
                intent=case["intent"],
                extracted_entities=case["entities"],
                conversation_context=case["context"],
            )
            latency_ms = (time.perf_counter() - start) * 1000
            latencies.append(latency_ms)

        latencies.sort()
        p50 = latencies[len(latencies) // 2]
        p95 = latencies[int(len(latencies) * 0.95)]

        performance_metrics["latencies"]["sufficiency_check"] = latencies

        assert p50 < 50, f"Sufficiency check P50 latency too high: {p50:.2f}ms (target: <50ms)"

        print(f"\nSufficiency Check Latency Distribution:")
        print(f"  P50: {p50:.2f}ms")
        print(f"  P95: {p95:.2f}ms")
        print(f"  Mean: {sum(latencies)/len(latencies):.2f}ms")

    @pytest.mark.asyncio
    async def test_full_routing_latency(self, request_router, performance_metrics):
        """
        完整路由决策延迟（包括缓存检查，不包含外部LLM网络时延）
        目标: <100ms (P95)
        """
        test_messages = [
            "帮我制定学习计划",
            "翻译这个单词",
            "我的学习习惯分析",
            "进入冲刺模式",
            "创建一个学习任务",
        ] * 10  # 50 iterations

        latencies = []
        for message in test_messages:
            start = time.perf_counter()
            await request_router.decide(
                message=message,
                user_id="test-user",
                session_id="test-session",
            )
            latency_ms = (time.perf_counter() - start) * 1000
            latencies.append(latency_ms)

        latencies.sort()
        p50 = latencies[len(latencies) // 2]
        p95 = latencies[int(len(latencies) * 0.95)]

        performance_metrics["latencies"]["full_routing"] = latencies

        assert p95 < 100, f"Full routing P95 latency too high: {p95:.2f}ms (target: <100ms)"

        print(f"\nFull Routing Latency Distribution:")
        print(f"  P50: {p50:.2f}ms")
        print(f"  P95: {p95:.2f}ms")
        print(f"  Mean: {sum(latencies)/len(latencies):.2f}ms")


# =============================================================================
# Suite 2: Memory Usage
# =============================================================================

class TestMemoryUsage:
    """测试内存使用"""

    @pytest.mark.asyncio
    async def test_router_memory_footprint(self, request_router, performance_metrics):
        """
        路由器内存占用
        目标: <50MB (基础实例)
        """
        tracemalloc.start()

        # Create multiple router instances
        routers = []
        for _ in range(10):
            router = RequestRouter(redis_client=None)
            routers.append(router)

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Memory per router instance (in MB)
        memory_per_router_mb = (peak / 1024 / 1024) / 10

        performance_metrics["memory_usage"].append({
            "component": "router",
            "memory_mb": memory_per_router_mb,
        })

        assert memory_per_router_mb < 50, (
            f"Router memory footprint too high: {memory_per_router_mb:.2f}MB "
            f"(target: <50MB)"
        )

        print(f"\nRouter Memory Footprint:")
        print(f"  Per instance: {memory_per_router_mb:.2f}MB")
        print(f"  Peak (10 instances): {peak / 1024 / 1024:.2f}MB")

    @pytest.mark.asyncio
    async def test_checker_memory_footprint(self, performance_metrics):
        """
        SufficiencyChecker 内存占用
        目标: <10MB
        """
        tracemalloc.start()

        checkers = []
        for _ in range(100):
            checker = SufficiencyChecker(strict_mode=False)
            checkers.append(checker)

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        memory_per_checker_mb = (peak / 1024 / 1024) / 100

        performance_metrics["memory_usage"].append({
            "component": "sufficiency_checker",
            "memory_mb": memory_per_checker_mb,
        })

        assert memory_per_checker_mb < 10, (
            f"Checker memory footprint too high: {memory_per_checker_mb:.2f}MB "
            f"(target: <10MB)"
        )

        print(f"\nSufficiencyChecker Memory Footprint:")
        print(f"  Per instance: {memory_per_checker_mb:.2f}MB")


# =============================================================================
# Suite 3: Concurrent Throughput
# =============================================================================

class TestThroughput:
    """测试并发吞吐量"""

    @pytest.mark.asyncio
    async def test_concurrent_classification_throughput(self, request_router, performance_metrics):
        """
        并发分类吞吐量
        目标: >100 req/s (单机)
        """
        # Prepare test messages
        test_messages = ["你好", "制定计划", "翻译", "冲刺模式"] * 25  # 100 messages

        start = time.perf_counter()

        # Run all classifications concurrently
        tasks = [
            request_router._classify_intent_with_confidence(msg)
            for msg in test_messages
        ]
        results = await asyncio.gather(*tasks)

        elapsed_sec = time.perf_counter() - start
        throughput = len(test_messages) / elapsed_sec

        performance_metrics["throughput"]["classification"] = throughput

        # Verify all succeeded
        assert len(results) == len(test_messages), "All classifications should complete"

        # Throughput assertion
        assert throughput > 100, (
            f"Classification throughput too low: {throughput:.1f} req/s "
            f"(target: >100 req/s)"
        )

        print(f"\nConcurrent Classification Throughput:")
        print(f"  Requests: {len(test_messages)}")
        print(f"  Time: {elapsed_sec:.2f}s")
        print(f"  Throughput: {throughput:.1f} req/s")

    @pytest.mark.asyncio
    async def test_concurrent_routing_throughput(self, request_router, performance_metrics):
        """
        并发路由吞吐量（包括决策）
        目标: >50 req/s
        """
        test_messages = ["帮我制定学习计划"] * 50  # 50 messages

        start = time.perf_counter()

        tasks = [
            request_router.decide(
                message=msg,
                user_id=f"user-{i}",
                session_id=f"session-{i}",
            )
            for i, msg in enumerate(test_messages)
        ]
        results = await asyncio.gather(*tasks)

        elapsed_sec = time.perf_counter() - start
        throughput = len(test_messages) / elapsed_sec

        performance_metrics["throughput"]["routing"] = throughput

        assert len(results) == len(test_messages), "All routings should complete"
        assert throughput > 50, (
            f"Routing throughput too low: {throughput:.1f} req/s "
            f"(target: >50 req/s)"
        )

        print(f"\nConcurrent Routing Throughput:")
        print(f"  Requests: {len(test_messages)}")
        print(f"  Time: {elapsed_sec:.2f}s")
        print(f"  Throughput: {throughput:.1f} req/s")


# =============================================================================
# Suite 4: Stress Tests
# =============================================================================

class TestStress:
    """压力测试"""

    @pytest.mark.asyncio
    async def test_burst_classification(self, request_router):
        """
        突发流量测试：瞬间处理100个请求
        """
        messages = ["你好"] * 100

        start = time.perf_counter()
        results = await asyncio.gather(*[
            request_router._classify_intent_with_confidence(msg)
            for msg in messages
        ])
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert len(results) == 100, "All 100 requests should complete"
        assert elapsed_ms < 5000, f"Burst processing too slow: {elapsed_ms:.1f}ms"

        print(f"\nBurst Classification:")
        print(f"  Requests: 100")
        print(f"  Total time: {elapsed_ms:.1f}ms")
        print(f"  Avg latency: {elapsed_ms / 100:.2f}ms")

    @pytest.mark.asyncio
    async def test_sustained_load(self, request_router):
        """
        持续负载测试：持续1秒的请求
        """
        duration_sec = 1.0
        interval_ms = 10  # One request every 10ms = 100 req/s

        start = time.perf_counter()
        request_count = 0

        while (time.perf_counter() - start) < duration_sec:
            await request_router._classify_intent_with_confidence("测试消息")
            request_count += 1
            await asyncio.sleep(interval_ms / 1000)

        actual_duration = time.perf_counter() - start
        throughput = request_count / actual_duration

        print(f"\nSustained Load Test:")
        print(f"  Duration: {actual_duration:.2f}s")
        print(f"  Requests: {request_count}")
        print(f"  Throughput: {throughput:.1f} req/s")

        assert throughput >= 80, (
            f"Sustained throughput too low: {throughput:.1f} req/s "
            f"(target: >=80 req/s)"
        )


# =============================================================================
# Suite 5: Regression Tests
# =============================================================================

class TestRegression:
    """回归测试：防止性能退化"""

    @pytest.mark.asyncio
    async def test_classification_accuracy_not_degraded(self, request_router):
        """
        确保准确率没有退化
        """
        test_cases = [
            ("帮我制定学习计划", "create"),
            ("翻译这个", "translation"),
            ("我的学习画像", "prism"),
            ("进入冲刺", "sprint"),
            ("你好", "chat"),
        ]

        correct = 0
        for message, expected_intent in test_cases:
            intent, confidence = await request_router._classify_intent_with_confidence(message)
            if intent == expected_intent:
                correct += 1

        accuracy = correct / len(test_cases)

        assert accuracy >= 0.95, (
            f"Classification accuracy degraded: {accuracy:.1%} "
            f"(target: >=95%)"
        )

        print(f"\nClassification Accuracy:")
        print(f"  Correct: {correct}/{len(test_cases)}")
        print(f"  Accuracy: {accuracy:.1%}")


# =============================================================================
# Performance Summary Report
# =============================================================================

@pytest.fixture(autouse=True)
def performance_summary(request, performance_metrics):
    """Generate performance summary at the end of test run"""
    yield

    # Print summary after all tests complete
    if request.node.nodeid.endswith("TestLatencyBenchmarks"):
        print("\n" + "=" * 60)
        print("PERFORMANCE SUMMARY")
        print("=" * 60)

        for component, latencies in performance_metrics["latencies"].items():
            if latencies:
                latencies.sort()
                p50 = latencies[len(latencies) // 2]
                p95 = latencies[int(len(latencies) * 0.95)]
                avg = sum(latencies) / len(latencies)
                print(f"\n{component}:")
                print(f"  P50: {p50:.2f}ms")
                print(f"  P95: {p95:.2f}ms")
                print(f"  Avg: {avg:.2f}ms")

        if performance_metrics["throughput"]:
            print("\nThroughput:")
            for component, throughput in performance_metrics["throughput"].items():
                print(f"  {component}: {throughput:.1f} req/s")

        print("=" * 60)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
