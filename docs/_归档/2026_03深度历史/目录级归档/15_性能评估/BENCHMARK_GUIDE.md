# Performance Benchmarking Guide

Complete guide to performance testing and benchmarking for the Sparkle system.

## Table of Contents

1. [Overview](#overview)
2. [Test Frameworks](#test-frameworks)
3. [Running Benchmarks](#running-benchmarks)
4. [Performance Targets](#performance-targets)
5. [Benchmark Writing](#benchmark-writing)
6. [CI/CD Integration](#cicd-integration)
7. [Result Analysis](#result-analysis)

## Overview

The Sparkle system has comprehensive performance testing across all three layers:

### Go Gateway
- gRPC client benchmarks
- Database connection pool tests
- Redis cache performance
- WebSocket routing benchmarks

### Python Engine
- Orchestrator FSM benchmarks
- LLM service performance
- Vector search benchmarks
- Tool registry performance

### Flutter Mobile
- Widget build/rebuild performance
- Scrolling performance
- Animation frame rate tests
- Golden (screenshot) tests

## Test Frameworks

### Go

**Framework**: Standard Go `testing` package with `testing.B`

```bash
# Run benchmarks
go test -bench=. -benchmem ./...

# CPU profiling
go test -bench=. -cpuprofile=cpu.prof

# Memory profiling
go test -bench=. -memprofile=mem.prof
```

### Python

**Framework**: pytest with pytest-benchmark

```bash
# Install
pip install pytest pytest-benchmark memory-profiler

# Run benchmarks
pytest tests/benchmark/ --benchmark-only

# Save baseline
pytest tests/benchmark/ --benchmark-only --benchmark-save=baseline

# Compare
pytest tests/benchmark/ --benchmark-only --benchmark-compare=baseline
```

### Flutter

**Framework**: flutter_test with golden_toolkit

```bash
# Install
cd mobile
flutter pub get

# Run performance tests
flutter test test/performance/

# Run golden tests
flutter test test/goldens/

# Update golden files
flutter test test/goldens/ --update-goldens
```

## Running Benchmarks

### Quick Start

```bash
# Go benchmarks
cd backend/gateway
go test -bench=. -benchmem ./...

# Python benchmarks
cd backend
pytest tests/benchmark/ --benchmark-only

# Flutter benchmarks
cd mobile
flutter test test/performance/
```

### Detailed Profiling

**Go CPU Profile:**
```bash
go test -bench=. -cpuprofile=cpu.prof ./...
go tool pprof -http=:8080 cpu.prof
```

**Go Memory Profile:**
```bash
go test -bench=. -memprofile=mem.prof ./...
go tool pprof -http=:8080 mem.prof
```

**Python Memory Profiling:**
```bash
pytest tests/benchmark/ -m memory \
  --memory-profiler-file=memory.prof
```

**Flutter Timeline:**
```bash
flutter test test/performance/ --timeline
flutter test test/performance/ --profile
```

## Performance Targets

### Go Gateway

| Operation | Target (ns/op) | Target (B/op) |
|-----------|----------------|---------------|
| gRPC metadata injection | < 1000 | < 500 |
| Cache get (hit) | < 100µs | < 1000 |
| DB connection acquire | < 10µs | < 500 |
| WebSocket message parse | < 5000 | < 2000 |

### Python Engine

| Operation | Target | Notes |
|-----------|--------|-------|
| State transition | < 50µs | Per transition |
| Context creation | < 100µs | Per context |
| Token estimation | < 1µs | Per character |
| Vector similarity (512d) | < 50µs | Per comparison |

### Flutter Mobile

| Widget | Build Target | Rebuild Target |
|--------|--------------|----------------|
| PlanReviewCard | < 16ms | < 5ms |
| ChatMessage | < 10ms | < 2ms |
| GalaxyNode | < 5ms | < 1ms |
| List (100 items) | < 100ms | - |

## Benchmark Writing

### Go Template

```go
func BenchmarkNewFeature(b *testing.B) {
    // Setup
    b.Run("scenario_1", func(b *testing.B) {
        b.ReportAllocs()

        // Pre-allocate if needed
        data := make([]byte, 1024)

        b.ResetTimer()  // Reset before measuring
        for i := 0; i < b.N; i++ {
            // Operation to benchmark
            result := process(data)
            _ = result  // Use result
        }
    })

    b.Run("scenario_2", func(b *testing.B) {
        // Different scenario
    })
}
```

### Python Template

```python
import pytest

@pytest.mark.benchmark
def test_component_performance():
    """
    Benchmark description
    基准描述
    """
    # Setup
    test_data = create_test_data()

    # Measure
    start = time.time()
    for i in range(1000):
        result = perform_operation(test_data)
    elapsed = time.time() - start

    # Assert
    assert elapsed < 0.1  # < 100ms
    assert len(result) > 0  # Verify correctness
```

### Flutter Template

```dart
testWidgets('MyWidget builds in under 16ms', (tester) async {
  final stopwatch = Stopwatch()..start();

  await tester.pumpWidget(
    MaterialApp(
      home: MyWidget(),
    ),
  );

  stopwatch.stop();

  print('MyWidget: ${stopwatch.elapsedMilliseconds}ms');
  expect(stopwatch.elapsedMilliseconds, lessThan(16));
});
```

## CI/CD Integration

### GitHub Actions Workflow

```yaml
name: Performance Benchmarks

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM

jobs:
  go-benchmarks:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run Go benchmarks
        run: |
          cd backend/gateway
          go test -bench=. -benchmem ./... | tee bench.txt
      - name: Upload results
        uses: actions/upload-artifact@v2
        with:
          name: go-bench-results
          path: backend/gateway/bench.txt

  python-benchmarks:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          cd backend
          pip install -e .
          pip install pytest pytest-benchmark
      - name: Run Python benchmarks
        run: |
          cd backend
          pytest tests/benchmark/ --benchmark-only \
            --benchmark-save=baseline \
            --benchmark-json=results.json
      - name: Upload results
        uses: actions/upload-artifact@v2
        with:
          name: python-bench-results
          path: backend/results.json

  flutter-benchmarks:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Flutter
        uses: subosito/flutter-action@v2
        with:
          flutter-version: '3.16.0'
      - name: Run Flutter benchmarks
        run: |
          cd mobile
          flutter test test/performance/ > results.txt 2>&1
      - name: Upload results
        uses: actions/upload-artifact@v2
        with:
          name: flutter-bench-results
          path: mobile/results.txt
```

## Result Analysis

### Interpreting Go Benchmarks

```
BenchmarkCache_Get/cache_hit-12     1000000    1053 ns/op    512 B/op    8 allocs/op
```

- **1000000**: Number of iterations (b.N)
- **1053 ns/op**: Average time per operation
- **512 B/op**: Memory allocated per operation
- **8 allocs/op**: Number of allocations per operation

**Targets:**
- Fast operations: < 1000 ns/op
- Medium operations: < 10000 ns/op
- Slow operations: < 100000 ns/op

### Interpreting Python Benchmarks

```
test_state_transition_speed PASSED                             0.002
```

- Time shown is total execution time
- For 1000 iterations in example
- Per operation: 0.002 / 1000 = 2µs

**pytest-benchmark output:**
```
------------------------------------------------------
benchmark (mean)            Min     Max    Median
------------------------------------------------------
state_transition          1.2µs   5.6µs     1.5µs
------------------------------------------------------
```

### Interpreting Flutter Benchmarks

```
PlanReviewCard build: 12ms
```

- Direct measurement in milliseconds
- Target: < 16ms (60fps = 16.67ms per frame)
- Rebuilds should be faster (< 5ms)

### Performance Regression Detection

**Setup baselines:**
```bash
# Go - save baseline
go test -bench=. -benchmem ./... > baseline.txt

# Python - save baseline
pytest tests/benchmark/ --benchmark-save=baseline

# Flutter - save baseline
flutter test test/performance/ > baseline.txt
```

**Compare against baseline:**
```bash
# Go - compare (use benchstat)
go install golang.org/x/perf/cmd/benchstat@latest
benchstat baseline.txt current.txt

# Python - compare
pytest tests/benchmark/ --benchmark-compare=baseline

# Flutter - compare (manual)
diff baseline.txt current.txt
```

**Thresholds for alerting:**
- Go: > 10% degradation
- Python: > 15% degradation
- Flutter: > 20% degradation

## Best Practices

### 1. Benchmark Design

- **Test realistic workloads**: Use production-like data
- **Test multiple scenarios**: Small, medium, large inputs
- **Include warmup**: JIT compilation affects results
- **Run multiple times**: Take median, not just first run

### 2. Measurement

- **Use built-in tools**: Don't reinvent measurement
- **Profile before optimizing**: Identify actual bottlenecks
- **Measure consistently**: Same environment, same hardware
- **Document expectations**: Include targets in test

### 3. Analysis

- **Look at trends**: Not just individual runs
- **Consider variance**: Run multiple times
- **Profile outliers**: Understand why
- **Share findings**: Document for team

### 4. Maintenance

- **Keep benchmarks updated**: Match code changes
- **Review regularly**: Monthly or quarterly
- **Remove obsolete tests**: Don't keep dead code
- **Add new tests**: For new features

## Troubleshooting

### Unstable Results

**Symptoms**: High variance between runs

**Solutions**:
- Run multiple times, use median
- Increase iteration count
- Disable CPU frequency scaling
- Close background applications
- Use consistent hardware

### Slow Tests

**Symptoms**: Benchmarks take too long

**Solutions**:
- Reduce iteration count
- Profile to find slow code
- Use sub-benchmarks selectively
- Run in parallel where possible

### Memory Issues

**Symptoms**: Out of memory during tests

**Solutions**:
- Profile memory usage
- Check for leaks
- Reduce data size
- Run tests in isolation

## Resources

### Go
- [Go Testing Package](https://golang.org/pkg/testing/)
- [Go Profiling](https://golang.org/doc/diagnostics.html)
- [pprof](https://github.com/google/pprof)

### Python
- [pytest Documentation](https://docs.pytest.org/)
- [pytest-benchmark](https://pytest-benchmark.readthedocs.io/)
- [memory_profiler](https://pypi.org/project/memory-profiler/)

### Flutter
- [Flutter Testing](https://docs.flutter.dev/cookbook/testing)
- [Flutter Performance](https://docs.flutter.dev/perf)
- [DevTools](https://docs.flutter.dev/tools/devtools/overview)

### General
- [The Art of Benchmarking](https://easyperf.net/blog/2019/08/02/Perf-Measurement-Basics/)
- [Statistical Analysis for Benchmarking](https://numpy.org/doc/stable/reference/routines.statistics.html)
- [Continuous Benchmarking](https://github.com/google/continuous-benchmarking-workflow)
