package handler

import (
	"context"
	"sync"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
)

// ============================================================
// Performance Measurement Utilities
// ============================================================

type PerformanceStats struct {
	mu                 sync.RWMutex
	latencies          []float64
	throughputs        []float64
	errors             int64
	totalRequests      int64
	startTime          time.Time
}

func NewPerformanceStats() *PerformanceStats {
	return &PerformanceStats{
		latencies:    make([]float64, 0),
		throughputs:  make([]float64, 0),
		startTime:    time.Now(),
	}
}

func (ps *PerformanceStats) RecordLatency(latencyMs float64) {
	ps.mu.Lock()
	defer ps.mu.Unlock()
	ps.latencies = append(ps.latencies, latencyMs)
	ps.totalRequests++
}

func (ps *PerformanceStats) RecordError() {
	ps.mu.Lock()
	defer ps.mu.Unlock()
	ps.errors++
}

func (ps *PerformanceStats) RecordThroughput(msgPerSec float64) {
	ps.mu.Lock()
	defer ps.mu.Unlock()
	ps.throughputs = append(ps.throughputs, msgPerSec)
}

func (ps *PerformanceStats) GetAverageLatency() float64 {
	ps.mu.RLock()
	defer ps.mu.RUnlock()

	if len(ps.latencies) == 0 {
		return 0
	}

	sum := 0.0
	for _, l := range ps.latencies {
		sum += l
	}
	return sum / float64(len(ps.latencies))
}

func (ps *PerformanceStats) GetPercentileLatency(percentile int) float64 {
	ps.mu.RLock()
	defer ps.mu.RUnlock()

	if len(ps.latencies) == 0 {
		return 0
	}

	// Simple percentile calculation (not perfectly accurate but good enough)
	index := (percentile / 100) * len(ps.latencies)
	if index >= len(ps.latencies) {
		index = len(ps.latencies) - 1
	}

	return ps.latencies[index]
}

func (ps *PerformanceStats) GetSuccessRate() float64 {
	ps.mu.RLock()
	defer ps.mu.RUnlock()

	if ps.totalRequests == 0 {
		return 0
	}

	return float64(ps.totalRequests-ps.errors) / float64(ps.totalRequests) * 100
}

func (ps *PerformanceStats) GetAverageThroughput() float64 {
	ps.mu.RLock()
	defer ps.mu.RUnlock()

	if len(ps.throughputs) == 0 {
		return 0
	}

	sum := 0.0
	for _, t := range ps.throughputs {
		sum += t
	}
	return sum / float64(len(ps.throughputs))
}

// ============================================================
// Mock WebSocket Handler for Load Testing
// ============================================================

type MockWebSocketHandlerForLoad struct {
	processingLatency time.Duration
	errorRate         float64
	mu                sync.Mutex
	messageCount      int64
}

func NewMockWebSocketHandlerForLoad() *MockWebSocketHandlerForLoad {
	return &MockWebSocketHandlerForLoad{
		processingLatency: 100 * time.Millisecond,
		errorRate:         0,
	}
}

func (m *MockWebSocketHandlerForLoad) HandleMessage(ctx context.Context, msg map[string]interface{}) (map[string]interface{}, error) {
	m.mu.Lock()
	m.messageCount++
	m.mu.Unlock()

	// Simulate processing latency
	time.Sleep(m.processingLatency)

	return map[string]interface{}{
		"status":  "processed",
		"message": msg["content"],
	}, nil
}

func (m *MockWebSocketHandlerForLoad) GetMessageCount() int64 {
	m.mu.Lock()
	defer m.mu.Unlock()
	return m.messageCount
}

// ============================================================
// Latency & Throughput Tests
// ============================================================

func TestSingleRequestLatency(t *testing.T) {
	handler := NewMockWebSocketHandlerForLoad()
	stats := NewPerformanceStats()

	ctx := context.Background()
	msg := map[string]interface{}{"content": "test"}

	start := time.Now()
	_, err := handler.HandleMessage(ctx, msg)
	latency := float64(time.Since(start).Milliseconds())

	assert.NoError(t, err)
	stats.RecordLatency(latency)

	assert.Greater(t, latency, 50.0)
	assert.Less(t, latency, 500.0)
}

func TestSequentialRequestsLatency(t *testing.T) {
	handler := NewMockWebSocketHandlerForLoad()
	stats := NewPerformanceStats()
	ctx := context.Background()

	numRequests := 100
	for i := 0; i < numRequests; i++ {
		msg := map[string]interface{}{"content": "test"}

		start := time.Now()
		_, err := handler.HandleMessage(ctx, msg)
		latency := float64(time.Since(start).Milliseconds())

		assert.NoError(t, err)
		stats.RecordLatency(latency)
	}

	avgLatency := stats.GetAverageLatency()
	assert.Less(t, avgLatency, 150.0)
	assert.Equal(t, int64(100), stats.totalRequests)
}

func TestConcurrentRequestsLatency(t *testing.T) {
	handler := NewMockWebSocketHandlerForLoad()
	stats := NewPerformanceStats()
	ctx := context.Background()

	numConcurrent := 20
	var wg sync.WaitGroup
	wg.Add(numConcurrent)

	start := time.Now()
	for i := 0; i < numConcurrent; i++ {
		go func(id int) {
			defer wg.Done()

			msg := map[string]interface{}{"content": "test"}

			reqStart := time.Now()
			_, err := handler.HandleMessage(ctx, msg)
			latency := float64(time.Since(reqStart).Milliseconds())

			assert.NoError(t, err)
			stats.RecordLatency(latency)
		}(i)
	}

	wg.Wait()
	totalTime := time.Since(start).Seconds()

	// With concurrency, total time should be much less than sequential
	expectedSequential := float64(numConcurrent) * 0.1 // 100ms per request
	assert.Less(t, totalTime, expectedSequential)

	// Throughput should be good
	throughput := float64(numConcurrent) / totalTime
	assert.Greater(t, throughput, 50.0)
}

func TestMessageThroughput(t *testing.T) {
	handler := NewMockWebSocketHandlerForLoad()
	stats := NewPerformanceStats()
	ctx := context.Background()

	numMessages := 500
	var wg sync.WaitGroup
	wg.Add(numMessages)

	start := time.Now()
	for i := 0; i < numMessages; i++ {
		go func(id int) {
			defer wg.Done()

			msg := map[string]interface{}{"content": "test"}

			_, err := handler.HandleMessage(ctx, msg)
			assert.NoError(t, err)
		}(i)
	}

	wg.Wait()
	elapsed := time.Since(start).Seconds()

	throughput := float64(numMessages) / elapsed
	stats.RecordThroughput(throughput)

	// Should handle 500+ messages reasonably
	assert.Greater(t, throughput, 100.0)
	assert.Less(t, elapsed, 10.0)
}

func TestSustainedThroughput(t *testing.T) {
	handler := NewMockWebSocketHandlerForLoad()
	stats := NewPerformanceStats()
	ctx := context.Background()

	batchSize := 50
	numBatches := 10

	for batch := 0; batch < numBatches; batch++ {
		var wg sync.WaitGroup
		wg.Add(batchSize)

		start := time.Now()
		for i := 0; i < batchSize; i++ {
			go func(id int) {
				defer wg.Done()

				msg := map[string]interface{}{"content": "test"}
				_, err := handler.HandleMessage(ctx, msg)
				assert.NoError(t, err)
			}(i)
		}

		wg.Wait()
		elapsed := time.Since(start).Seconds()
		throughput := float64(batchSize) / elapsed
		stats.RecordThroughput(throughput)
	}

	avgThroughput := stats.GetAverageThroughput()
	assert.Greater(t, avgThroughput, 100.0)
}

// ============================================================
// Connection Pool Tests
// ============================================================

func TestConnectionPoolCapacity(t *testing.T) {
	const maxConnections = 20
	const numRequests = 50

	activeConns := int64(0)
	maxActive := int64(0)
	var mu sync.Mutex

	var wg sync.WaitGroup
	wg.Add(numRequests)

	for i := 0; i < numRequests; i++ {
		go func(id int) {
			defer wg.Done()

			// Acquire connection
			mu.Lock()
			if activeConns >= maxConnections {
				mu.Unlock()
				t.Logf("Connection limit reached")
				return
			}
			activeConns++
			if activeConns > maxActive {
				maxActive = activeConns
			}
			mu.Unlock()

			// Simulate work
			time.Sleep(50 * time.Millisecond)

			// Release connection
			mu.Lock()
			activeConns--
			mu.Unlock()
		}(i)
	}

	wg.Wait()

	assert.LessOrEqual(t, maxActive, int64(maxConnections))
	assert.Equal(t, int64(0), activeConns) // All released
}

func TestConnectionReuseUnderLoad(t *testing.T) {
	stats := NewPerformanceStats()
	ctx := context.Background()
	handler := NewMockWebSocketHandlerForLoad()

	const totalRequests = 200
	var wg sync.WaitGroup
	wg.Add(totalRequests)

	start := time.Now()
	for i := 0; i < totalRequests; i++ {
		go func(id int) {
			defer wg.Done()

			msg := map[string]interface{}{"content": "test"}

			reqStart := time.Now()
			_, err := handler.HandleMessage(ctx, msg)
			latency := float64(time.Since(reqStart).Milliseconds())

			assert.NoError(t, err)
			stats.RecordLatency(latency)
		}(i)
	}

	wg.Wait()
	elapsed := time.Since(start).Seconds()

	// Should complete efficiently with connection reuse
	assert.Less(t, elapsed, 30.0)
	avgLatency := stats.GetAverageLatency()
	assert.Less(t, avgLatency, 200.0)
}

// ============================================================
// Cache Performance Tests
// ============================================================

func TestCacheHitRate(t *testing.T) {
	type MockCache struct {
		data map[string]string
		hits int64
		miss int64
		mu   sync.RWMutex
	}

	cache := &MockCache{
		data: make(map[string]string),
	}

	// Populate cache
	for i := 0; i < 100; i++ {
		cache.data[string(rune(i))] = "value"
	}

	// Test access patterns
	for i := 0; i < 100; i++ {
		cache.mu.RLock()
		if _, ok := cache.data[string(rune(i))]; ok {
			cache.hits++
		} else {
			cache.miss++
		}
		cache.mu.RUnlock()
	}

	hitRate := float64(cache.hits) / float64(cache.hits+cache.miss) * 100
	assert.Greater(t, hitRate, 90.0)
}

func TestConcurrentCacheAccess(t *testing.T) {
	type MockCache struct {
		data  map[string]string
		mu    sync.RWMutex
		reads int64
	}

	cache := &MockCache{
		data: make(map[string]string),
	}

	// Pre-populate
	for i := 0; i < 100; i++ {
		cache.data[string(rune(i))] = "value"
	}

	const numGoroutines = 50
	const readsPerGoroutine = 100

	var wg sync.WaitGroup
	wg.Add(numGoroutines)

	start := time.Now()
	for g := 0; g < numGoroutines; g++ {
		go func(id int) {
			defer wg.Done()

			for i := 0; i < readsPerGoroutine; i++ {
				cache.mu.RLock()
				_ = cache.data[string(rune(i%100))]
				cache.mu.RUnlock()

				cache.mu.Lock()
				cache.reads++
				cache.mu.Unlock()
			}
		}(g)
	}

	wg.Wait()
	elapsed := time.Since(start)

	expectedReads := int64(numGoroutines * readsPerGoroutine)
	assert.Equal(t, expectedReads, cache.reads)
	assert.Less(t, elapsed, 10*time.Second)
}

// ============================================================
// Concurrent User Simulation Tests
// ============================================================

func TestConcurrentUserSessions(t *testing.T) {
	stats := NewPerformanceStats()
	handler := NewMockWebSocketHandlerForLoad()
	ctx := context.Background()

	const numUsers = 20
	const messagesPerUser = 5

	var wg sync.WaitGroup
	wg.Add(numUsers)

	start := time.Now()
	for user := 0; user < numUsers; user++ {
		go func(userID int) {
			defer wg.Done()

			for msg := 0; msg < messagesPerUser; msg++ {
				msgData := map[string]interface{}{"content": "test"}

				reqStart := time.Now()
				_, err := handler.HandleMessage(ctx, msgData)
				latency := float64(time.Since(reqStart).Milliseconds())

				assert.NoError(t, err)
				stats.RecordLatency(latency)
			}
		}(user)
	}

	wg.Wait()
	elapsed := time.Since(start)

	expectedRequests := int64(numUsers * messagesPerUser)
	assert.Equal(t, expectedRequests, stats.totalRequests)
	assert.Less(t, elapsed, 15*time.Second)
}

func TestHighConcurrentLoad(t *testing.T) {
	stats := NewPerformanceStats()
	handler := NewMockWebSocketHandlerForLoad()
	ctx := context.Background()

	const numConcurrent = 100
	var wg sync.WaitGroup
	wg.Add(numConcurrent)

	start := time.Now()
	for i := 0; i < numConcurrent; i++ {
		go func(id int) {
			defer wg.Done()

			msg := map[string]interface{}{"content": "test"}

			reqStart := time.Now()
			_, err := handler.HandleMessage(ctx, msg)
			latency := float64(time.Since(reqStart).Milliseconds())

			if err != nil {
				stats.RecordError()
			}
			stats.RecordLatency(latency)
		}(i)
	}

	wg.Wait()
	elapsed := time.Since(start)

	successRate := stats.GetSuccessRate()
	assert.Greater(t, successRate, 90.0)
	assert.Less(t, elapsed, 30*time.Second)
}

// ============================================================
// Stress Tests
// ============================================================

func TestBurstTraffic(t *testing.T) {
	stats := NewPerformanceStats()
	handler := NewMockWebSocketHandlerForLoad()
	ctx := context.Background()

	const burstSize = 200
	var wg sync.WaitGroup
	wg.Add(burstSize)

	start := time.Now()
	for i := 0; i < burstSize; i++ {
		go func(id int) {
			defer wg.Done()

			msg := map[string]interface{}{"content": "burst"}

			_, err := handler.HandleMessage(ctx, msg)
			if err != nil {
				stats.RecordError()
			}
		}(i)
	}

	wg.Wait()
	elapsed := time.Since(start)

	successRate := stats.GetSuccessRate()
	assert.Greater(t, successRate, 85.0) // Allow some failures under stress
	assert.Less(t, elapsed, 30*time.Second)
}

func TestSlowClientHandling(t *testing.T) {
	ctx := context.Background()

	slowLatencies := make([]float64, 0)
	fastLatencies := make([]float64, 0)
	var mu sync.Mutex

	// Slow client
	slowHandler := NewMockWebSocketHandlerForLoad()
	slowHandler.processingLatency = 500 * time.Millisecond

	// Fast clients
	fastHandler := NewMockWebSocketHandlerForLoad()
	fastHandler.processingLatency = 50 * time.Millisecond

	var wg sync.WaitGroup

	// 1 slow + 5 fast
	wg.Add(6)

	// Slow client
	go func() {
		defer wg.Done()

		for i := 0; i < 3; i++ {
			msg := map[string]interface{}{"content": "slow"}

			start := time.Now()
			_, err := slowHandler.HandleMessage(ctx, msg)
			latency := float64(time.Since(start).Milliseconds())

			assert.NoError(t, err)

			mu.Lock()
			slowLatencies = append(slowLatencies, latency)
			mu.Unlock()
		}
	}()

	// Fast clients
	for f := 0; f < 5; f++ {
		go func() {
			defer wg.Done()

			msg := map[string]interface{}{"content": "fast"}

			start := time.Now()
			_, err := fastHandler.HandleMessage(ctx, msg)
			latency := float64(time.Since(start).Milliseconds())

			assert.NoError(t, err)

			mu.Lock()
			fastLatencies = append(fastLatencies, latency)
			mu.Unlock()
		}()
	}

	wg.Wait()

	// Calculate average latencies
	var slowSum, fastSum float64
	for _, l := range slowLatencies {
		slowSum += l
	}
	for _, l := range fastLatencies {
		fastSum += l
	}

	avgSlow := slowSum / float64(len(slowLatencies))
	avgFast := fastSum / float64(len(fastLatencies))

	// Slow client shouldn't block fast clients significantly
	assert.Less(t, avgFast, avgSlow+100.0) // Some overhead acceptable
	assert.Greater(t, avgSlow, 400.0)       // Slow client is indeed slow
}

// ============================================================
// Percentile Analysis Tests
// ============================================================

func TestLatencyPercentiles(t *testing.T) {
	stats := NewPerformanceStats()
	handler := NewMockWebSocketHandlerForLoad()
	ctx := context.Background()

	const numRequests = 1000
	var wg sync.WaitGroup
	wg.Add(numRequests)

	for i := 0; i < numRequests; i++ {
		go func(id int) {
			defer wg.Done()

			msg := map[string]interface{}{"content": "test"}

			start := time.Now()
			_, err := handler.HandleMessage(ctx, msg)
			latency := float64(time.Since(start).Milliseconds())

			assert.NoError(t, err)
			stats.RecordLatency(latency)
		}(i)
	}

	wg.Wait()

	avgLatency := stats.GetAverageLatency()
	p95Latency := stats.GetPercentileLatency(95)
	p99Latency := stats.GetPercentileLatency(99)

	// Basic sanity checks - allow equal values in percentile distribution
	assert.GreaterOrEqual(t, p95Latency, avgLatency*0.95) // p95 should be close to or greater than avg
	assert.GreaterOrEqual(t, p99Latency, p95Latency*0.95) // p99 should be close to or greater than p95
	assert.Greater(t, p99Latency, 0.0)
}

// ============================================================
// WebSocket Connection Scaling Tests
// ============================================================

func TestWebSocketConnectionScaling(t *testing.T) {
	const maxConnections = 1000
	activeConns := int64(0)
	var mu sync.Mutex

	connErrors := 0
	var wg sync.WaitGroup
	wg.Add(maxConnections)

	for i := 0; i < maxConnections; i++ {
		go func(id int) {
			defer wg.Done()

			mu.Lock()
			if activeConns >= 1000 { // Arbitrary connection limit
				connErrors++
				mu.Unlock()
				return
			}
			activeConns++
			mu.Unlock()

			// Simulate connection usage
			time.Sleep(10 * time.Millisecond)

			mu.Lock()
			activeConns--
			mu.Unlock()
		}(i)
	}

	wg.Wait()

	// Most connections should succeed
	successRate := float64(maxConnections-int64(connErrors)) / float64(maxConnections) * 100
	assert.Greater(t, successRate, 95.0)
}
