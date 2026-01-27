"""
Performance Benchmark Tests for Transparency Data Generator
透明度数据生成器性能基准测试

Tests performance characteristics:
1. Step creation speed
2. Event serialization speed
3. Memory overhead
4. Scalability with many steps
"""
import pytest
import time
import tracemalloc
import json
from datetime import datetime
from app.orchestration.transparency_data_generator import (
    TransparencyDataGenerator,
    TransparencyStep,
    StepType,
    StepStatus,
)


@pytest.fixture
def generator():
    return TransparencyDataGenerator()


@pytest.mark.benchmark
def test_step_creation_performance(generator):
    """
    Benchmark step creation
    步骤创建性能基准
    """
    start = time.time()

    # Create 1000 steps
    steps = []
    for i in range(1000):
        step = generator.create_step(
            name=f"Step {i}",
            step_type=StepType.TOOL_EXECUTION,
            agent_type="test_agent",
            metadata={"index": i}
        )
        steps.append(step)

    elapsed = time.time() - start

    # Should be very fast (< 50ms for 1000 steps)
    assert elapsed < 0.05
    assert len(steps) == 1000


@pytest.mark.benchmark
def test_step_lifecycle_performance(generator):
    """
    Benchmark complete step lifecycle (create → start → complete)
    完整步骤生命周期性能基准
    """
    start = time.time()

    for i in range(100):
        step = generator.create_step(
            name=f"Step {i}",
            step_type=StepType.LLM_INFERENCE,
            agent_type="llm"
        )

        generator.start_step(step)

        # Simulate some work
        result = {"output": f"result-{i}"}

        generator.complete_step(step, result)

    elapsed = time.time() - start

    # 100 complete lifecycles should be fast (< 100ms)
    assert elapsed < 0.1


@pytest.mark.benchmark
def test_event_serialization_performance(generator):
    """
    Benchmark event serialization to JSON
    事件JSON序列化性能基准
    """
    # Create a realistic event
    step = generator.create_step(
        name="Complex Tool Execution",
        step_type=StepType.TOOL_EXECUTION,
        agent_type="tool_agent",
        metadata={
            "tool": "search",
            "query": "test query",
            "results": 10,
            "latency": 150
        }
    )

    generator.start_step(step)
    generator.complete_step(step, {"status": "success"})

    # Serialize 1000 times
    start = time.time()
    for _ in range(1000):
        event = generator.get_step_event(step)
        json_str = json.dumps(event)
    elapsed = time.time() - start

    # Should be very fast (< 50ms for 1000 serializations)
    assert elapsed < 0.05

    # Verify serialization is valid
    event_dict = json.loads(json_str)
    assert event_dict["name"] == "Complex Tool Execution"


@pytest.mark.benchmark
def test_complete_event_generation(generator):
    """
    Benchmark generating complete transparency summary
    完整透明度摘要生成性能基准
    """
    # Create 100 steps
    for i in range(100):
        step = generator.create_step(
            name=f"Step {i}",
            step_type=StepType.PLANNING if i % 2 == 0 else StepType.TOOL_EXECUTION,
            agent_type="orchestrator"
        )
        generator.start_step(step)
        generator.complete_step(step, {"index": i})

    # Generate complete event
    start = time.time()
    complete_event = generator.get_complete_event()
    elapsed = time.time() - start

    # Should be fast (< 10ms)
    assert elapsed < 0.01

    # Verify structure
    assert "summary" in complete_event
    assert "total_steps" == 100
    assert len(complete_event["steps"]) == 100


@pytest.mark.benchmark
def test_convenience_methods(generator):
    """
    Benchmark convenience tracking methods
    便捷追踪方法性能基准
    """
    methods = [
        lambda: generator.track_planning_step("Test Plan", {}),
        lambda: generator.track_tool_execution("search", {"query": "test"}),
        lambda: generator.track_llm_inference("gpt-4", {"tokens": 100}),
    ]

    for method in methods:
        start = time.time()

        # Call 100 times
        for _ in range(100):
            method()

        elapsed = time.time() - start

        # Each method should be fast (< 10ms for 100 calls)
        assert elapsed < 0.01


def test_memory_usage_with_many_steps(generator):
    """
    Test memory usage with many active steps
    多活动步骤内存使用测试
    """
    tracemalloc.start()

    # Create 10,000 steps
    for i in range(10000):
        step = generator.create_step(
            name=f"Memory Test Step {i}",
            step_type=StepType.PLANNING,
            agent_type="test"
        )
        generator.start_step(step)

    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    # Memory usage should be reasonable
    # (10,000 steps with metadata)
    peak_mb = peak / 1024 / 1024
    assert peak_mb < 50  # < 50MB


@pytest.mark.benchmark
def test_json_event_size(generator):
    """
    Test that JSON events are compact
    测试JSON事件紧凑性
    """
    step = generator.create_step(
        name="Test Step",
        step_type=StepType.TOOL_EXECUTION,
        agent_type="agent",
        metadata={"key1": "value1", "key2": "value2"}
    )

    generator.start_step(step)
    generator.complete_step(step, {"result": "success"})

    event = generator.get_step_event(step)
    json_str = json.dumps(event)

    # Event should be compact (< 1KB)
    size_kb = len(json_str.encode('utf-8')) / 1024
    assert size_kb < 1.0


@pytest.mark.benchmark
def test_concurrent_step_tracking(generator):
    """
    Test thread-safe concurrent step tracking
    并发步骤追踪线程安全测试
    """
    import threading

    steps = []
    threads = []

    def create_steps(thread_id):
        for i in range(100):
            step = generator.create_step(
                name=f"Thread {thread_id} Step {i}",
                step_type=StepType.PLANNING,
                agent_type="test"
            )
            steps.append(step)

    # Create 10 threads, each creating 100 steps
    start = time.time()
    for i in range(10):
        thread = threading.Thread(target=create_steps, args=(i,))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    elapsed = time.time() - start

    # All 1000 steps should be created quickly
    assert elapsed < 0.1
    assert len(steps) == 1000

    # All step IDs should be unique
    step_ids = [s.step_id for s in steps]
    assert len(set(step_ids)) == 1000  # All unique


@pytest.mark.benchmark
def test_step_metadata_overhead(generator):
    """
    Test performance with varying metadata sizes
    不同元数据大小性能影响
    """
    # Small metadata
    small_meta = {"key": "value"}
    step_small = generator.create_step("Small", StepType.TOOL_EXECUTION, "agent", small_meta)
    start = time.time()
    for _ in range(100):
        generator.get_step_event(step_small)
    time_small = time.time() - start

    # Large metadata
    large_meta = {f"key{i}": "value" * 10 for i in range(100)}
    step_large = generator.create_step("Large", StepType.TOOL_EXECUTION, "agent", large_meta)
    start = time.time()
    for _ in range(100):
        generator.get_step_event(step_large)
    time_large = time.time() - start

    # Large metadata should not be dramatically slower
    assert time_large < time_small * 5  # At most 5x slower


@pytest.mark.benchmark
def test_batch_event_generation(generator):
    """
    Test generating all events at once (simulating workflow end)
    批量事件生成性能基准（模拟工作流结束）
    """
    # Simulate complete workflow with 50 steps
    steps = []
    for i in range(50):
        step = generator.create_step(
            name=f"Workflow Step {i}",
            step_type=StepType.PLANNING if i < 10 else StepType.TOOL_EXECUTION,
            agent_type="orchestrator",
            metadata={"step_index": i}
        )
        generator.start_step(step)
        generator.complete_step(step, {"step": i})
        steps.append(step)

    # Generate complete event with all steps
    start = time.time()
    complete_event = generator.get_complete_event()
    elapsed = time.time() - start

    # Should be very fast (< 20ms for 50 steps)
    assert elapsed < 0.02

    # Verify all steps are included
    assert complete_event["total_steps"] == 50
    assert len(complete_event["steps"]) == 50


def test_error_event_generation(generator):
    """
    Test that error events don't add significant overhead
    错误事件生成不增加显著开销
    """
    # Normal event
    normal_step = generator.create_step("Normal", StepType.TOOL_EXECUTION, "agent")
    generator.start_step(normal_step)
    generator.complete_step(normal_step, {"result": "ok"})

    # Error event
    error_step = generator.create_step("Error", StepType.TOOL_EXECUTION, "agent")
    generator.start_step(error_step)
    generator.complete_step(error_step, None, error="Test error")

    # Both should serialize similarly fast
    import time

    start = time.time()
    normal_event = generator.get_step_event(normal_step)
    time_normal = time.time() - start

    start = time.time()
    error_event = generator.get_step_event(error_step)
    time_error = time.time() - start

    # Error event should not be significantly slower
    assert time_error < time_normal * 2
