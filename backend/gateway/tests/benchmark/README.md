# Go Gateway Performance Benchmarks

This directory contains comprehensive performance benchmarks for the Go Gateway layer.

## Overview

The benchmark suite measures:
- **gRPC Client Performance**: Throughput, latency, memory allocation
- **Database Operations**: Connection pooling, query execution, batch processing
- **Redis Cache**: Hit rates, concurrency, entry sizes, semantic operations
- **WebSocket Routing**: Message throughput, connection scaling

## Running Benchmarks

### Basic Benchmark Execution

```bash
# Run all benchmarks
cd backend/gateway
go test -bench=. -benchmem ./...

# Run specific package benchmarks
go test -bench=. -benchmem ./internal/agent
go test -bench=. -benchmem ./internal/db
go test -bench=. -benchmem ./internal/service
```

### Detailed Profiling

```bash
# CPU profiling
go test -bench=. -cpuprofile=cpu.prof ./internal/agent
go tool pprof cpu.prof

# Memory profiling
go test -bench=. -memprofile=mem.prof ./internal/db
go tool pprof mem.prof

# Both profiles
go test -bench=. -cpuprofile=cpu.prof -memprofile=mem.prof ./internal/service
```

### Benchmark-Specific Options

```bash
# Run benchmarks for specific duration (default: 1s)
go test -bench=. -benchtime=5s ./internal/agent

# Run multiple times for stability
go test -bench=. -count=5 ./internal/db

# Disable CPU profiling for faster results
go test -bench=. -cpuprofile="" ./internal/service

# Run specific benchmark by name
go test -bench=BenchmarkMetadataInjection ./internal/agent

# Run benchmarks matching pattern
go test -bench="Cache/Get" ./internal/service
```

## Benchmark Categories

### 1. gRPC Client (`internal/agent/client_bench_test.go`)

Measures gRPC client operations overhead:

- `BenchmarkMetadataInjection` - Metadata creation cost
- `BenchmarkChatRequestAllocation` - Message allocation by size
- `BenchmarkContextCreation` - Context overhead
- `BenchmarkTraceIDOperations` - Trace ID handling
- `BenchmarkMessageSerialization` - Protobuf serialization

**Expected Results:**
- Metadata injection: < 1000 ns/op
- Small message allocation: < 5000 ns/op
- Context with timeout: < 2000 ns/op

### 2. Database Operations (`internal/db/db_bench_test.go`)

Measures database interaction patterns:

- `BenchmarkConnectionPool_*` - Pool acquire/release
- `BenchmarkDatabase_QuerySerialization` - Query preparation
- `BenchmarkRowScanning` - Result row processing
- `BenchmarkBatchOperations` - Batch insert performance

**Expected Results:**
- Connection acquire: < 10 µs/op (with warm pool)
- Small row scan: < 1 µs/op
- Batch 100 inserts: < 5 ms total

### 3. Redis Cache (`internal/service/cache_bench_test.go`)

Measures cache operations and patterns:

- `BenchmarkCache_Get` - Cache hit/miss performance
- `BenchmarkCache_Set` - Write performance by entry size
- `BenchmarkCache_Concurrent*` - Concurrency behavior
- `BenchmarkSemanticCache_*` - Vector similarity

**Expected Results:**
- Cache get (hit): < 100 µs/op
- Cache set (small): < 150 µs/op
- Concurrent reads: > 100k ops/sec
- Semantic similarity (512d): < 50 µs/op

## Interpreting Results

### Key Metrics

- **ns/op** - Nanoseconds per operation (lower is better)
- **B/op** - Bytes allocated per operation (lower is better)
- **allocs/op** - Number of allocations per operation (lower is better)

### Example Output

```
BenchmarkCache_Get/cache_hit-12          1000000    1053 ns/op    512 B/op    8 allocs/op
BenchmarkCache_Get/cache_miss-12         1000000    1234 ns/op    640 B/op   10 allocs/op
```

This means:
- Cache hits take ~1µs with 512 bytes allocated
- Cache misses take ~1.2µs with 640 bytes allocated

### Performance Targets

| Operation | Target (ns/op) | Target (B/op) |
|-----------|----------------|---------------|
| gRPC Metadata Injection | < 1000 | < 500 |
| Cache Get (hit) | < 100000 | < 1000 |
| Cache Set (small) | < 150000 | < 2000 |
| DB Connection Acquire | < 10000 | < 500 |
| Small Row Scan | < 1000 | < 500 |

## Benchmark Writing Guide

When adding new benchmarks:

1. **Use `b.ReportAllocs()`** to track memory allocations
2. **Reset timer** before measuring the actual operation
3. **Use sub-benchmarks** (`b.Run`) for related scenarios
4. **Include realistic data sizes** (small, medium, large)

### Template

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
            _ = result  // Use result to avoid optimization
        }
    })

    b.Run("scenario_2", func(b *testing.B) {
        // Different scenario
    })
}
```

## Continuous Integration

Benchmarks run in CI to detect performance regressions:

```yaml
# .github/workflows/benchmark.yml
- name: Run benchmarks
  run: |
    go test -bench=. -benchmem ./... | tee benchmark.txt

- name: Compare with baseline
  run: |
    go install golang.org/x/perf/cmd/benchstat@latest
    benchstat baseline.txt benchmark.txt
```

## Troubleshooting

### Unstable Results

- Run multiple times: `go test -bench=. -count=5`
- Increase duration: `go test -bench=. -benchtime=10s`
- Disable CPU frequency scaling
- Close other applications

### High Memory Allocations

- Check for unnecessary allocations in loops
- Use `sync.Pool` for reusable objects
- Pre-allocate slices with known capacity

### Slow Benchmarks

- Verify you're not measuring setup/teardown
- Use `b.ResetTimer()` before measured code
- Check for unintentional I/O operations

## See Also

- [Go Testing Package](https://golang.org/pkg/testing/)
- [Go Profiling](https://golang.org/doc/diagnostics.html)
- [pgx Documentation](https://pkg.go.dev/github.com/jackc/pgx/v5)
- [Redis Go Client](https://redis.uptrace.dev/)
