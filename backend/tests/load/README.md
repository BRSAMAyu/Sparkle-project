# System-Wide Load Testing Suite

Comprehensive load testing for the entire Sparkle system using Locust and K6.

## Setup

### Install Dependencies

```bash
# Python (Locust)
cd backend
pip install locust

# Node.js (K6)
npm install -g k6
```

### Test Environment

```bash
# Start all services
make dev-all

# Wait for services to be healthy
make smoke
```

## Running Load Tests

### Locust (Python)

```bash
# Start Locust web UI
cd backend
locust -f tests/load/locustfile.py --host=http://localhost:8080

# Run headless (command line)
locust -f tests/load/locustfile.py --host=http://localhost:8080 --headless \
  --users 100 --spawn-rate 10 --run-time 5m

# Run specific user class
locust -f tests/load/locustfile.py --host=http://localhost:8080 \
  --user-class SparkleUser --users 50
```

### K6 (JavaScript)

```bash
# Run K6 test
k6 run backend/tests/load/k6/scenarios.js

# Run with options
k6 run --vus 100 --duration 5m backend/tests/load/k6/scenarios.js

# Run with stages (ramp-up)
k6 run --env STAGES='["1m:10","5m:50","1m:100","5m:100","1m:0"]' \
  backend/tests/load/k6/scenarios.js
```

### Orchestration Script

```bash
# Run all load tests
./scripts/run-load-tests.sh all

# Run specific test
./scripts/run-load-tests.sh locust
./scripts/run-load-tests.sh k6

# Run with custom parameters
./scripts/run-load-tests.sh locust --users 200 --duration 10m
```

## Test Scenarios

### 1. Chat Workload (`SparkleUser`)

**Operations:**
- Send chat messages (70%)
- Get chat history (20%)
- Submit feedback (10%)
- Health checks (background)

**Load Levels:**
- Light: 10 concurrent users
- Medium: 50 concurrent users
- Heavy: 100 concurrent users
- Stress: 500+ concurrent users

### 2. WebSocket Workload (`WebSocketChatUser`)

**Operations:**
- WebSocket connection establishment
- Message streaming
- Connection lifecycle

**Load Levels:**
- Light: 25 concurrent connections
- Medium: 100 concurrent connections
- Heavy: 500 concurrent connections

### 3. Galaxy/Knowledge Graph (`GalaxyUser`)

**Operations:**
- Get nodes (60%)
- Get edges (30%)
- Search knowledge (10%)

**Load Levels:**
- Light: 20 concurrent users
- Medium: 50 concurrent users
- Heavy: 100 concurrent users

### 4. Plan Review Workflow (`PlanSubmissionUser`)

**Operations:**
- Submit plan (50%)
- Get review status (25%)
- Submit feedback (25%)

**Load Levels:**
- Light: 10 concurrent users
- Medium: 25 concurrent users
- Heavy: 50 concurrent users

## Performance Targets

### Response Times (p95)

| Endpoint | Target (Light) | Target (Medium) | Target (Heavy) |
|----------|----------------|-----------------|----------------|
| POST /chat/stream | < 500ms | < 1000ms | < 2000ms |
| GET /chat/history | < 200ms | < 500ms | < 1000ms |
| POST /feedback | < 300ms | < 500ms | < 1000ms |
| GET /galaxy/nodes | < 200ms | < 500ms | < 1000ms |
| POST /plans | < 1000ms | < 2000ms | < 5000ms |

### Throughput

| Scenario | Target RPS | Notes |
|----------|-----------|-------|
| Chat only | > 100 | Sustained |
| Mixed workload | > 200 | All scenarios |
| Maximum capacity | > 500 | Burst |

### Error Rates

| Load Level | Target Error Rate |
|------------|-------------------|
| Light | < 0.1% |
| Medium | < 1% |
| Heavy | < 5% |
| Stress | < 10% |

## Service Level Agreements

### Availability

```
Uptime Target: 99.5% (monthly)
Maintenance Windows: 4 hours/month scheduled
```

### Latency

```
p50 (median):  < 200ms
p95:           < 1000ms
p99:           < 2000ms
```

### Throughput

```
Sustained:     200 RPS
Peak:          500 RPS (for 5 minutes)
Burst:         1000 RPS (for 30 seconds)
```

## Test Results

### Baseline Performance

Run baseline tests to establish performance benchmarks:

```bash
# Establish baseline
./scripts/run-load-tests.sh all --save-baseline

# View baseline
cat tests/load/results/baseline.json
```

### Regression Detection

Compare current performance against baseline:

```bash
# Run comparison
./scripts/run-load-tests.sh all --compare-baseline

# View comparison report
cat tests/load/results/comparison.json
```

## Monitoring During Tests

### Metrics to Track

1. **Request Metrics**
   - Response time (p50, p95, p99)
   - Request rate
   - Error rate

2. **Resource Metrics**
   - CPU utilization
   - Memory usage
   - Disk I/O
   - Network I/O

3. **Service Metrics**
   - Database connection pool
   - Redis cache hit rate
   - gRPC latency
   - WebSocket connections

### Monitoring Tools

```bash
# Prometheus metrics
curl http://localhost:9090/metrics

# Grafana dashboard
open http://localhost:3000

# Service logs
docker compose logs -f gateway
docker compose logs -f grpc-server
```

## Load Test Profiles

### Sustained Load Test

```bash
# Run for 30 minutes at medium load
locust -f tests/load/locustfile.py --headless \
  --users 50 --spawn-rate 5 --run-time 30m
```

### Ramp-Up Test

```bash
# Gradually increase load
k6 run --env STAGES='["2m:10","5m:50","10m:100","5m:200","2m:0"]' \
  tests/load/k6/scenarios.js
```

### Stress Test

```bash
# Push to failure
locust -f tests/load/locustfile.py --headless \
  --users 1000 --spawn-rate 100 --run-time 10m
```

### Spike Test

```bash
# Sudden load spike
k6 run --env STAGES='["1m:10","1s:500","5m:10"]' \
  tests/load/k6/scenarios.js
```

## Test Data Management

### Generating Test Data

```bash
# Create test users
python scripts/generate_test_data.py --users 1000

# Create test sessions
python scripts/generate_test_data.py --sessions 500

# Create test knowledge graph
python scripts/generate_test_data.py --galaxy --nodes 10000
```

### Cleanup

```bash
# Clean up test data
python scripts/cleanup_test_data.py --all

# Clean up specific data
python scripts/cleanup_test_data.py --users --older-than 7d
```

## CI/CD Integration

### GitHub Actions

```yaml
name: Load Tests

on:
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM
  workflow_dispatch:

jobs:
  load-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Start services
        run: make dev-all

      - name: Run load tests
        run: ./scripts/run-load-tests.sh all --headless

      - name: Upload results
        uses: actions/upload-artifact@v2
        with:
          name: load-test-results
          path: backend/tests/load/results/
```

## Troubleshooting

### Connection Refused

**Issue**: Cannot connect to services

**Solution**:
```bash
# Check services are running
docker compose ps

# Restart services
make dev-all
```

### High Error Rates

**Issue**: Many requests failing

**Solutions**:
- Check service logs
- Verify database connections
- Check rate limits
- Review error messages

### Slow Performance

**Issue**: Response times degraded

**Solutions**:
- Check CPU/memory usage
- Review database query performance
- Check cache hit rates
- Profile application code

### Memory Leaks

**Issue**: Memory usage increasing

**Solutions**:
- Monitor memory over time
- Check for connection leaks
- Review garbage collection
- Profile memory usage

## Best Practices

1. **Run tests in isolation** - Dedicated test environment
2. **Start small** - Begin with light load, increase gradually
3. **Monitor continuously** - Watch metrics during tests
4. **Document baselines** - Track performance over time
5. **Test realistically** - Simulate actual user behavior
6. **Clean up** - Remove test data after tests
7. **Automate** - Integrate into CI/CD pipeline
8. **Review results** - Analyze and act on findings

## See Also

- [Locust Documentation](https://docs.locust.io/)
- [K6 Documentation](https://k6.io/docs/)
- [Load Testing Best Practices](https://docs.locust.io/en/stable/testing-best-practices.html)
- [Performance Monitoring](docs/performance/MONITORING.md)
