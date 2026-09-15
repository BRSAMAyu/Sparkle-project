"""
Performance Benchmark Tests for Tool Registry
工具注册表性能基准测试

Tests performance characteristics:
1. Tool lookup speed
2. Schema validation overhead
3. Tool execution dispatch
4. Registry scalability with many tools
"""
import pytest
import time
import tracemalloc
from unittest.mock import Mock


@pytest.fixture
def mock_tool_registry():
    """Create mock tool registry for benchmarking"""
    tools = {}

    # Register 100 mock tools
    for i in range(100):
        tools[f"tool_{i}"] = {
            "name": f"tool_{i}",
            "description": f"Test tool {i}",
            "parameters": {
                "type": "object",
                "properties": {
                    f"param_{j}": {"type": "string"}
                    for j in range(5)
                },
            },
        }

    return tools


@pytest.mark.benchmark
def test_tool_lookup(mock_tool_registry):
    """
    Benchmark tool lookup speed
    工具查找速度基准
    """
    tool_names = list(mock_tool_registry.keys())

    start = time.time()

    # Perform 10000 tool lookups
    for i in range(10000):
        tool_name = tool_names[i % len(tool_names)]
        tool = mock_tool_registry.get(tool_name)

    elapsed = time.time() - start

    # Should be very fast (< 10ms for 10k lookups)
    assert elapsed < 0.01


@pytest.mark.benchmark
def test_schema_validation(mock_tool_registry):
    """
    Benchmark schema validation overhead
    模式验证开销基准
    """
    # Simulate schema validation
    tool_schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "limit": {"type": "integer"},
            "filters": {
                "type": "object",
                "properties": {
                    "category": {"type": "string"},
                    "date": {"type": "string"},
                },
            },
        },
    }

    valid_args = {
        "query": "test",
        "limit": 10,
        "filters": {"category": "test"},
    }

    start = time.time()

    # Validate 1000 times
    for i in range(1000):
        # Simple type checking
        for key, value in valid_args.items():
            if key in tool_schema["properties"]:
                prop_schema = tool_schema["properties"][key]
                if prop_schema.get("type") == "string":
                    assert isinstance(value, str)
                elif prop_schema.get("type") == "integer":
                    assert isinstance(value, int)

    elapsed = time.time() - start

    # Should be fast (< 20ms for 1000 validations)
    assert elapsed < 0.02


@pytest.mark.benchmark
def test_tool_execution_dispatch():
    """
    Benchmark tool execution dispatch
    工具执行分发性能基准
    """
    # Mock tool implementations
    tools = {
        "search": Mock(return_value={"results": []}),
        "calculate": Mock(return_value={"result": 42}),
        "fetch": Mock(return_value={"data": "test"}),
    }

    requests = [
        {"tool": "search", "args": {"query": "test"}},
        {"tool": "calculate", "args": {"x": 1, "y": 2}},
        {"tool": "fetch", "args": {"url": "http://example.com"}},
    ] * 100  # 300 total requests

    start = time.time()

    # Dispatch tool executions
    for req in requests:
        tool_name = req["tool"]
        args = req["args"]
        tool_impl = tools.get(tool_name)
        if tool_impl:
            result = tool_impl(**args)

    elapsed = time.time() - start

    # Should be fast (< 50ms for 300 dispatches)
    assert elapsed < 0.05


@pytest.mark.benchmark
def test_registry_scaling():
    """
    Test registry performance with varying tool counts
    不同工具数量注册表性能测试
    """
    registry_sizes = [10, 50, 100, 500, 1000]

    for size in registry_sizes:
        # Create registry
        registry = {
            f"tool_{i}": {
                "name": f"tool_{i}",
                "description": f"Tool {i}",
            }
            for i in range(size)
        }

        # Benchmark lookup
        start = time.time()
        for i in range(1000):
            tool_name = f"tool_{i % size}"
            tool = registry.get(tool_name)
        elapsed = time.time() - start

        print(f"Registry size {size}: {elapsed:.4f}s for 1000 lookups")
        # Lookup should scale well
        assert elapsed < 0.05


@pytest.mark.benchmark
def test_tool_schema_serialization():
    """
    Benchmark tool schema serialization
    工具模式序列化性能基准
    """
    import json

    tool_schema = {
        "name": "search",
        "description": "Search the knowledge base",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results",
                    "default": 10,
                },
            },
            "required": ["query"],
        },
    }

    start = time.time()

    # Serialize 1000 times
    for i in range(1000):
        json_str = json.dumps(tool_schema)

    elapsed = time.time() - start

    # Should be fast (< 20ms for 1000 serializations)
    assert elapsed < 0.02


@pytest.mark.benchmark
def test_tool_filtering():
    """
    Benchmark filtering tools by category
    按类别过滤工具性能基准
    """
    tools = {
        f"tool_{i}": {
            "name": f"tool_{i}",
            "category": ["search", "calculation", "fetch"][i % 3],
        }
        for i in range(100)
    }

    start = time.time()

    # Filter by category 100 times
    for i in range(100):
        category = ["search", "calculation", "fetch"][i % 3]
        filtered_tools = {
            name: tool
            for name, tool in tools.items()
            if tool["category"] == category
        }

    elapsed = time.time() - start

    # Should be fast (< 10ms for 100 filterings)
    assert elapsed < 0.01


@pytest.mark.benchmark
def test_concurrent_tool_execution():
    """
    Simulate concurrent tool execution
    并发工具执行模拟
    """
    import threading

    tools = {
        f"tool_{i}": Mock(return_value={"result": i})
        for i in range(20)
    }

    results = []
    threads = []

    def execute_tool(tool_name, args):
        tool = tools.get(tool_name)
        if tool:
            result = tool(**args)
            results.append(result)

    start = time.time()

    # Execute 20 tools concurrently
    for i in range(20):
        thread = threading.Thread(
            target=execute_tool,
            args=(f"tool_{i}", {"param": "value"})
        )
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    elapsed = time.time() - start

    # Should complete quickly
    assert elapsed < 0.1
    assert len(results) == 20


@pytest.mark.benchmark
def test_tool_parameter_binding():
    """
    Benchmark tool parameter binding
    工具参数绑定性能基准
    """
    tool_schema = {
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer"},
                "offset": {"type": "integer"},
            },
        }
    }

    # Sample arguments
    args_list = [
        {"query": "test", "limit": 10},
        {"query": "search", "limit": 20, "offset": 5},
        {"query": "find", "offset": 0},
    ] * 100  # 300 total

    start = time.time()

    # Bind parameters 300 times
    for args in args_list:
        bound_params = {}
        for key, value in args.items():
            if key in tool_schema["parameters"]["properties"]:
                bound_params[key] = value

    elapsed = time.time() - start

    # Should be fast (< 10ms for 300 bindings)
    assert elapsed < 0.01


@pytest.mark.benchmark
def test_tool_registry_memory_usage():
    """
    Test memory usage with large tool registry
    大工具注册表内存使用测试
    """
    tracemalloc.start()

    # Create registry with 1000 tools
    registry = {
        f"tool_{i}": {
            "name": f"tool_{i}",
            "description": f"Tool description {i}" * 10,  # Longer description
            "parameters": {
                "type": "object",
                "properties": {
                    f"param_{j}": {"type": "string"}
                    for j in range(10)
                },
            },
        }
        for i in range(1000)
    }

    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    # Memory should be reasonable (< 50MB for 1000 tools)
    peak_mb = peak / 1024 / 1024
    print(f"Registry memory: {peak_mb:.2f}MB for 1000 tools")
    assert peak_mb < 50


@pytest.mark.benchmark
def test_dynamic_tool_loading():
    """
    Simulate dynamic tool loading/unloading
    动态工具加载/卸载模拟
    """
    registry = {}

    start = time.time()

    # Load and unload tools
    for i in range(100):
        # Load tool
        tool_name = f"tool_{i % 50}"  # Cycle through 50 tools
        registry[tool_name] = {
            "name": tool_name,
            "description": f"Tool {tool_name}",
        }

        # Unload some tools
        if i > 50 and i % 10 == 0:
            remove_name = f"tool_{i % 50}"
            if remove_name in registry:
                del registry[remove_name]

    elapsed = time.time() - start

    # Should be fast (< 10ms for 100 load/unload operations)
    assert elapsed < 0.01


@pytest.mark.benchmark
def test_tool_chain_execution():
    """
    Benchmark tool chain execution
    工具链执行性能基准
    """
    tools = {
        "extract": Mock(return_value={"data": "extracted"}),
        "transform": Mock(return_value={"result": "transformed"}),
        "load": Mock(return_value={"status": "loaded"}),
    }

    chain = ["extract", "transform", "load"] * 10  # 30 tool calls

    start = time.time()

    # Execute chain
    context = {}
    for tool_name in chain:
        tool = tools.get(tool_name)
        if tool:
            result = tool(**context)
            context.update(result)

    elapsed = time.time() - start

    # Should be fast (< 20ms for 30 chained calls)
    assert elapsed < 0.02


@pytest.mark.benchmark
def test_tool_permission_checking():
    """
    Benchmark tool permission checking
    工具权限检查性能基准
    """
    tools = {
        f"tool_{i}": {
            "required_permission": f"perm_{i % 10}",
        }
        for i in range(100)
    }

    user_permissions = [f"perm_{i}" for i in range(10)]

    start = time.time()

    # Check permissions 1000 times
    for i in range(1000):
        tool_name = f"tool_{i % 100}"
        tool = tools.get(tool_name)
        if tool:
            required = tool["required_permission"]
            has_permission = required in user_permissions

    elapsed = time.time() - start

    # Should be fast (< 10ms for 1000 checks)
    assert elapsed < 0.01


@pytest.mark.benchmark
def test_tool_result_caching():
    """
    Simulate tool result caching
    工具结果缓存模拟
    """
    cache = {}

    def cached_tool_call(tool_name, args):
        cache_key = f"{tool_name}:{str(args)}"
        if cache_key in cache:
            return cache[cache_key]

        # Simulate tool execution
        result = {"tool": tool_name, "args": args, "result": "executed"}
        cache[cache_key] = result
        return result

    start = time.time()

    # Execute 1000 calls (50% cache hits)
    for i in range(1000):
        tool_name = f"tool_{i % 100}"
        args = {"param": i % 50}
        result = cached_tool_call(tool_name, args)

    elapsed = time.time() - start

    # Cached calls should be fast
    assert elapsed < 0.05
    assert len(cache) > 0  # Cache was populated
