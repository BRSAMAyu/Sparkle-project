# Python Performance Benchmarks

Comprehensive performance benchmarks for the Python Engine layer.

## Running Benchmarks

### Basic Execution

```bash
# Run all benchmarks
cd backend
pytest tests/benchmark/ -v

# Run with benchmark marks
pytest tests/benchmark/ -m benchmark -v

# Run specific benchmark file
pytest tests/benchmark/test_orchestrator_bench.py -v

# Run with verbose output
pytest tests/benchmark/ -v -s
```

### With Profiling

```bash
# Install profiling dependencies
pip install pytest-benchmark memory-profiler py-spy

# Run with pytest-benchmark
pytest tests/benchmark/ --benchmark-only

# Generate benchmark comparison
pytest tests/benchmark/ --benchmark-only --benchmark-save=baseline

# Compare with baseline
pytest tests/benchmark/ --benchmark-only --benchmark-compare=baseline
```

### Memory Profiling

```bash
# Run specific test with memory profiling
python -m memory_profiler backend/tests/benchmark/test_orchestrator_bench.py

# Or use tracemalloc (built-in)
pytest tests/benchmark/test_orchestrator_bench.py::test_memory_usage_large_context -v
```

## Benchmark Categories

### 1. Orchestrator FSM (`test_orchestrator_bench.py`)

**State Transition Speed**
- `test_state_transition_speed` - 1000 state transitions in < 50ms
- `test_concurrent_state_transitions` - 1000 transitions across 10 threads

**Context Management**
- `test_context_creation_overhead` - Create 100 contexts in < 10ms
- `test_context_memory_usage` - < 50MB for 1000 contexts

**Event Processing**
- `test_event_processing_overhead` - Process 1000 events in < 50ms

### 2. LLM Service (`test_llm_service_bench.py`)

**Token Processing**
- `test_token_estimation` - Estimate tokens for various text sizes
- `test_prompt_construction` - Build prompts efficiently

**Streaming**
- `test_streaming_chunk_processing` - Process streaming chunks

**Context Scaling**
- `test_context_window_scaling` - Performance across different context sizes

### 3. Vector Search (`test_vector_search_bench.py`)

**Similarity Computation**
- `test_vector_similarity_cosine` - Cosine similarity benchmarks
- `test_vector_similarity_euclidean` - Euclidean distance benchmarks

**Search Operations**
- `test_knn_search` - K-nearest neighbors search
- `test_approximate_search` - Simulated ANN search

**Scaling**
- `test_vector_memory_usage` - Memory usage with large collections
- `test_multilingual_vector_sizes` - Different embedding model sizes

### 4. Tool Registry (`test_tool_registry_bench.py`)

**Lookup Operations**
- `test_tool_lookup` - 10k lookups in < 10ms
- `test_tool_filtering` - Filter tools by category

**Execution**
- `test_tool_execution_dispatch` - Dispatch 300 calls in < 50ms
- `test_concurrent_tool_execution` - Concurrent execution

**Registry Management**
- `test_registry_scaling` - Performance with 10-1000 tools
- `test_dynamic_tool_loading` - Load/unload operations

### 5. Existing Benchmarks

**Transparency Data Generator** (`test_transparency_performance.py`)
- Step creation and lifecycle
- Event serialization
- Memory overhead

**Statistics** (`test_statistics_performance.py`)
- Statistical computation performance

**Budget Optimization** (`test_budget_optimization_performance.py`)
- Token budget optimization

## Performance Targets

### Orchestrator FSM

| Operation | Target | Notes |
|-----------|--------|-------|
| State transition | < 50µs | Per transition |
| Context creation | < 100µs | Per context |
| Event processing | < 50µs | Per event |
| Memory per context | < 50KB | With 10 messages |

### LLM Service

| Operation | Target | Notes |
|-----------|--------|-------|
| Token estimation | < 1µs | Per character |
| Prompt construction | < 10µs | Per template |
| Streaming chunk | < 5µs | Per chunk |
| 8k context processing | < 100ms | Total |

### Vector Search

| Operation | Target | Notes |
|-----------|--------|-------|
| Cosine similarity (512d) | < 50µs | Per comparison |
| KNN search (1k vectors) | < 10ms | Top-10 |
| ANN search (10k vectors) | < 50ms | Approximate |
| Memory per vector (512d) | < 10KB | Including overhead |

### Tool Registry

| Operation | Target | Notes |
|-----------|--------|-------|
| Tool lookup | < 1µs | Dictionary lookup |
| Schema validation | < 10µs | Per validation |
| Execution dispatch | < 100µs | Per dispatch |
| Memory per tool | < 5KB | Including schema |

## Writing New Benchmarks

### Template

```python
"""
Performance benchmark for [Component]
[Component description in Chinese]
"""
import pytest
import time
import tracemalloc

@pytest.mark.benchmark
def test_component_operation():
    """
    Benchmark description
    基准描述
    """
    # Setup
    test_data = create_test_data()

    start = time.time()

    # Operation to benchmark
    for i in range(1000):
        result = perform_operation(test_data)

    elapsed = time.time() - start

    # Assertions
    assert elapsed < 0.1  # Should complete in < 100ms
    assert len(result) > 0  # Verify correctness
```

### Best Practices

1. **Use `@pytest.mark.benchmark`** for all benchmark tests
2. **Include realistic data sizes** - small, medium, large
3. **Measure memory usage** with `tracemalloc` for large operations
4. **Test concurrent operations** where applicable
5. **Provide both English and Chinese descriptions**
6. **Document performance targets** in test docstrings

### Memory Profiling Template

```python
def test_memory_usage():
    """
    Test memory usage for [operation]
    [操作]内存使用测试
    """
    tracemalloc.start()

    # Perform operation
    result = large_operation()

    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    peak_mb = peak / 1024 / 1024
    assert peak_mb < 100  # < 100MB
```

## Continuous Integration

### GitHub Actions Workflow

```yaml
name: Performance Benchmarks

on: [push, pull_request]

jobs:
  benchmark:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -e .
          pip install pytest pytest-benchmark

      - name: Run benchmarks
        run: |
          pytest tests/benchmark/ --benchmark-only \
            --benchmark-save=baseline \
            --benchmark-json=output.json

      - name: Upload results
        uses: actions/upload-artifact@v2
        with:
          name: benchmark-results
          path: output.json
```

## Interpreting Results

### Example Output

```
tests/benchmark/test_orchestrator_bench.py::test_state_transition_speed PASSED
tests/benchmark/test_context_memory_usage PASSED
====================== 2 passed in 0.15s =======================
```

### Performance Regression Detection

```bash
# Save baseline
pytest tests/benchmark/ --benchmark-only --benchmark-save=baseline

# After changes
pytest tests/benchmark/ --benchmark-only --benchmark-compare=baseline

# Output will show % change
# [REGRESSION] test_operation: +15% (was 100ms, now 115ms)
```

## Troubleshooting

### Unstable Benchmarks

- Increase iterations for more stable results
- Run multiple times and take median
- Check for background processes
- Disable frequency scaling

### Memory Leaks

- Use `tracemalloc` to identify allocation points
- Check for circular references
- Verify cleanup in teardown
- Run with `pytest-leaks` plugin

### Slow Tests

- Profile with `py-spy` to identify bottlenecks
- Check for I/O operations in benchmarks
- Verify not measuring setup/teardown
- Use `time.perf_counter()` for high-resolution timing

## See Also

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-benchmark Documentation](https://pytest-benchmark.readthed.io/)
- [Python Profiling](https://docs.python.org/3/library/profile.html)
- [NumPy Performance](https://numpy.org/doc/stable/reference/routines.performance.html)
