"""
Performance Benchmark Tests for Core Python Operations
Python核心操作性能基准测试

Tests performance characteristics:
1. Dict/list operations
2. String operations
3. Context management
4. Concurrent operations
"""
import pytest
import time
import tracemalloc
from threading import Thread


@pytest.mark.benchmark
def test_dict_operations_performance():
    """
    Benchmark dictionary operations
    字典操作性能基准
    """
    # Test dict get/set
    start = time.time()

    test_dict = {}
    for i in range(10000):
        test_dict[f"key_{i}"] = f"value_{i}"

    for i in range(10000):
        _ = test_dict.get(f"key_{i}")

    elapsed = time.time() - start

    # Should be fast (< 50ms for 20k operations)
    assert elapsed < 0.05


@pytest.mark.benchmark
def test_list_operations_performance():
    """
    Benchmark list operations
    列表操作性能基准
    """
    start = time.time()

    # List append
    test_list = []
    for i in range(10000):
        test_list.append(i)

    # List iteration
    for item in test_list:
        _ = item

    elapsed = time.time() - start

    # Should be fast (< 20ms)
    assert elapsed < 0.02


@pytest.mark.benchmark
def test_string_operations_performance():
    """
    Benchmark string operations
    字符串操作性能基准
    """
    test_strings = [
        "Hello, world!",
        "This is a longer test string with more words.",
        "x" * 100,
        " ".join(["word"] * 100),
    ]

    start = time.time()

    for i in range(1000):
        for test_str in test_strings:
            # Common string operations
            _ = len(test_str)
            _ = test_str.split()
            _ = test_str.lower()

    elapsed = time.time() - start

    # Should be fast (< 50ms)
    assert elapsed < 0.05


@pytest.mark.benchmark
def test_context_manager_performance():
    """
    Benchmark context manager overhead
    上下文管理器开销基准
    """
    class SimpleContext:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    ctx = SimpleContext()

    start = time.time()

    for i in range(10000):
        with ctx:
            pass

    elapsed = time.time() - start

    # Should be fast (< 100ms for 10k context switches)
    assert elapsed < 0.1


@pytest.mark.benchmark
def test_json_serialization_performance():
    """
    Benchmark JSON serialization/deserialization
    JSON序列化/反序列化性能基准
    """
    import json

    test_data = {
        "user_id": "test-user",
        "messages": [
            {"role": "user", "content": f"Message {i}"}
            for i in range(100)
        ],
    }

    start = time.time()

    for i in range(1000):
        json_str = json.dumps(test_data)
        _ = json.loads(json_str)

    elapsed = time.time() - start

    # Should be fast (< 100ms for 1000 serializations)
    assert elapsed < 0.1


@pytest.mark.benchmark
def test_memory_allocation():
    """
    Test memory allocation patterns
    内存分配模式测试
    """
    tracemalloc.start()

    # Allocate many small objects
    objects = []
    for i in range(10000):
        objects.append({"key": f"value_{i}"})

    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    # Memory should be reasonable (< 50MB for 10k dict)
    peak_mb = peak / 1024 / 1024
    assert peak_mb < 50


@pytest.mark.benchmark
def test_concurrent_operations():
    """
    Test concurrent operation performance
    并发操作性能测试
    """
    results = []

    def worker(worker_id):
        for i in range(100):
            results.append((worker_id, i))

    start = time.time()

    threads = []
    for i in range(10):
        t = Thread(target=worker, args=(i,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    elapsed = time.time() - start

    # Should complete quickly (< 50ms for 1000 operations across 10 threads)
    assert elapsed < 0.05
    assert len(results) == 1000


@pytest.mark.benchmark
def test_list_comprehension_performance():
    """
    Benchmark list comprehension vs loops
    列表推导式vs循环性能基准
    """
    # List comprehension
    start = time.time()
    for _ in range(1000):
        result = [x * 2 for x in range(1000)]
    list_comp_time = time.time() - start

    # Traditional loop
    start = time.time()
    for _ in range(1000):
        result = []
        for x in range(1000):
            result.append(x * 2)
    loop_time = time.time() - start

    # Both should be fast, list comprehension usually faster
    assert list_comp_time < 0.5
    assert loop_time < 0.5

    print(f"List comprehension: {list_comp_time:.4f}s, Loop: {loop_time:.4f}s")


@pytest.mark.benchmark
def test_set_operations_performance():
    """
    Benchmark set operations
    集合操作性能基准
    """
    set_a = set(range(10000))
    set_b = set(range(5000, 15000))

    start = time.time()

    for i in range(100):
        _ = set_a & set_b  # Intersection
        _ = set_a | set_b  # Union
        _ = set_a - set_b  # Difference

    elapsed = time.time() - start

    # Should be fast (< 50ms for 300 set operations on 10k elements)
    assert elapsed < 0.05


@pytest.mark.benchmark
def test_function_call_overhead():
    """
    Benchmark function call overhead
    函数调用开销基准
    """
    def simple_function(x, y):
        return x + y

    def complex_function(x, y):
        result = x + y
        result *= 2
        return result

    start = time.time()

    for i in range(100000):
        _ = simple_function(i, i + 1)
        _ = complex_function(i, i + 1)

    elapsed = time.time() - start

    # Should be fast (< 100ms for 200k function calls)
    assert elapsed < 0.1


@pytest.mark.benchmark
def test_class_instantiation_performance():
    """
    Benchmark class instantiation
    类实例化性能基准
    """
    class SimpleClass:
        def __init__(self, x, y):
            self.x = x
            self.y = y

    class ComplexClass:
        def __init__(self, x, y):
            self.x = x
            self.y = y
            self.data = list(range(100))

    start = time.time()

    for i in range(10000):
        simple = SimpleClass(i, i + 1)
        complex = ComplexClass(i, i + 1)

    elapsed = time.time() - start

    # Should be fast (< 100ms for 20k instantiations)
    assert elapsed < 0.1


@pytest.mark.benchmark
def test_sorting_performance():
    """
    Benchmark sorting operations
    排序操作性能基准
    """
    import random

    data = [random.randint(1, 10000) for _ in range(1000)]

    start = time.time()

    for i in range(100):
        sorted_data = sorted(data)

    elapsed = time.time() - start

    # Should be fast (< 50ms for 100 sorts of 1000 elements)
    assert elapsed < 0.05


@pytest.mark.benchmark
def test_regex_performance():
    """
    Benchmark regex operations
    正则表达式操作性能基准
    """
    import re

    pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
    test_text = "Contact us at test@example.com or support@test.org for more info."

    start = time.time()

    for i in range(10000):
        _ = pattern.findall(test_text)

    elapsed = time.time() - start

    # Should be fast (< 100ms for 10k regex matches)
    assert elapsed < 0.1


@pytest.mark.benchmark
def test_dict_comprehension_performance():
    """
    Benchmark dict comprehension
    字典推导式性能基准
    """
    start = time.time()

    for i in range(1000):
        result = {x: x * 2 for x in range(1000)}

    elapsed = time.time() - start

    # Should be fast (< 100ms for 1000 dict comprehensions of 1000 items)
    assert elapsed < 0.1


@pytest.mark.benchmark
def test_generator_performance():
    """
    Benchmark generator vs list
    生成器vs列表性能基准
    """
    # Generator
    start = time.time()
    for _ in range(100):
        gen_sum = sum(x * 2 for x in range(1000))
    gen_time = time.time() - start

    # List
    start = time.time()
    for _ in range(100):
        list_sum = sum([x * 2 for x in range(1000)])
    list_time = time.time() - start

    # Generator should use less memory, similar speed
    assert gen_time < 0.5
    assert list_time < 0.5

    print(f"Generator: {gen_time:.4f}s, List: {list_time:.4f}s")
