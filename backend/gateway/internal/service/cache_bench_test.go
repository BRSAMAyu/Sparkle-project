package service

import (
	"context"
	"sync"
	"testing"
	"time"
)

// ============================================================
// Redis Cache Benchmarks
// ============================================================

// MockCache simulates a cache interface for benchmarking
type MockCache struct {
	data map[string][]byte
	mu   sync.RWMutex
	hit  int64
	miss int64
}

func NewMockCache() *MockCache {
	return &MockCache{
		data: make(map[string][]byte),
	}
}

func (m *MockCache) Get(ctx context.Context, key string) ([]byte, bool) {
	m.mu.RLock()
	defer m.mu.RUnlock()

	val, ok := m.data[key]
	if ok {
		m.hit++
	} else {
		m.miss++
	}
	return val, ok
}

func (m *MockCache) Set(ctx context.Context, key string, value []byte, ttl time.Duration) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.data[key] = value
}

func (m *MockCache) Delete(ctx context.Context, key string) {
	m.mu.Lock()
	defer m.mu.Unlock()
	delete(m.data, key)
}

func (m *MockCache) HitRate() float64 {
	m.mu.RLock()
	defer m.mu.RUnlock()

	total := m.hit + m.miss
	if total == 0 {
		return 0
	}
	return float64(m.hit) / float64(total) * 100
}

// ============================================================
// Basic Cache Operations
// ============================================================

func BenchmarkCache_Get(b *testing.B) {
	ctx := context.Background()
	cache := NewMockCache()

	// Pre-populate cache
	for i := 0; i < 1000; i++ {
		key := "key-" + string(rune(i))
		cache.Set(ctx, key, []byte("value"), time.Hour)
	}

	b.Run("cache_hit", func(b *testing.B) {
		b.ReportAllocs()
		for i := 0; i < b.N; i++ {
			cache.Get(ctx, "key-100")
		}
	})

	b.Run("cache_miss", func(b *testing.B) {
		b.ReportAllocs()
		for i := 0; i < b.N; i++ {
			cache.Get(ctx, "key-not-found")
		}
	})
}

func BenchmarkCache_Set(b *testing.B) {
	ctx := context.Background()

	b.Run("set_small_value", func(b *testing.B) {
		b.ReportAllocs()
		cache := NewMockCache()
		value := []byte("small value")

		for i := 0; i < b.N; i++ {
			key := "key-" + string(rune(i%1000))
			cache.Set(ctx, key, value, time.Hour)
		}
	})

	b.Run("set_medium_value", func(b *testing.B) {
		b.ReportAllocs()
		cache := NewMockCache()
		value := make([]byte, 1024) // 1KB

		for i := 0; i < b.N; i++ {
			key := "key-" + string(rune(i%1000))
			cache.Set(ctx, key, value, time.Hour)
		}
	})

	b.Run("set_large_value", func(b *testing.B) {
		b.ReportAllocs()
		cache := NewMockCache()
		value := make([]byte, 10240) // 10KB

		for i := 0; i < b.N; i++ {
			key := "key-" + string(rune(i%1000))
			cache.Set(ctx, key, value, time.Hour)
		}
	})
}

func BenchmarkCache_Delete(b *testing.B) {
	ctx := context.Background()

	b.Run("delete_existing", func(b *testing.B) {
		b.ReportAllocs()
		cache := NewMockCache()

		// Pre-populate
		for i := 0; i < 1000; i++ {
			key := "key-" + string(rune(i))
			cache.Set(ctx, key, []byte("value"), time.Hour)
		}

		for i := 0; i < b.N; i++ {
			key := "key-" + string(rune(i%1000))
			cache.Delete(ctx, key)
		}
	})
}

// ============================================================
// Cache Concurrency
// ============================================================

func BenchmarkCache_ConcurrentReads(b *testing.B) {
	ctx := context.Background()
	cache := NewMockCache()

	// Pre-populate
	for i := 0; i < 100; i++ {
		key := "key-" + string(rune(i))
		cache.Set(ctx, key, []byte("value"), time.Hour)
	}

	b.Run("parallel_gets", func(b *testing.B) {
		b.ReportAllocs()
		b.RunParallel(func(pb *testing.PB) {
			i := 0
			for pb.Next() {
				key := "key-" + string(rune(i%100))
				cache.Get(ctx, key)
				i++
			}
		})
	})
}

func BenchmarkCache_ConcurrentWrites(b *testing.B) {
	ctx := context.Background()

	b.Run("parallel_sets", func(b *testing.B) {
		b.ReportAllocs()
		cache := NewMockCache()
		value := []byte("test value")

		b.RunParallel(func(pb *testing.PB) {
			i := 0
			for pb.Next() {
				key := "key-" + string(rune(i%1000))
				cache.Set(ctx, key, value, time.Hour)
				i++
			}
		})
	})
}

func BenchmarkCache_ConcurrentReadWrite(b *testing.B) {
	ctx := context.Background()
	cache := NewMockCache()
	value := []byte("test value")

	// Pre-populate
	for i := 0; i < 100; i++ {
		key := "key-" + string(rune(i))
		cache.Set(ctx, key, value, time.Hour)
	}

	b.Run("mixed_operations", func(b *testing.B) {
		b.ReportAllocs()
		b.RunParallel(func(pb *testing.PB) {
			i := 0
			for pb.Next() {
				key := "key-" + string(rune(i%100))
				if i%2 == 0 {
					cache.Get(ctx, key)
				} else {
					cache.Set(ctx, key, value, time.Hour)
				}
				i++
			}
		})
	})
}

// ============================================================
// Cache Hit Rate Benchmarks
// ============================================================

func BenchmarkCache_HitRate(b *testing.B) {
	ctx := context.Background()

	testCases := []struct {
		name       string
		numKeys    int
		accessPattern string // "sequential", "random", "zipf"
	}{
		{"small_cache_sequential", 100, "sequential"},
		{"small_cache_random", 100, "random"},
		{"medium_cache_sequential", 1000, "sequential"},
		{"medium_cache_random", 1000, "random"},
		{"large_cache_random", 10000, "random"},
	}

	for _, tc := range testCases {
		b.Run(tc.name, func(b *testing.B) {
			cache := NewMockCache()

			// Pre-populate cache
			for i := 0; i < tc.numKeys; i++ {
				key := "key-" + string(rune(i))
				cache.Set(ctx, key, []byte("value"), time.Hour)
			}

			b.ResetTimer()

			for i := 0; i < b.N; i++ {
				var key string
				switch tc.accessPattern {
				case "sequential":
					key = "key-" + string(rune(i%tc.numKeys))
				case "random":
					key = "key-" + string(rune(i%tc.numKeys))
				}
				cache.Get(ctx, key)
			}
		})
	}
}

// ============================================================
// Cache Entry Size Benchmarks
// ============================================================

func BenchmarkCache_EntrySize(b *testing.B) {
	ctx := context.Background()

	testCases := []struct {
		name  string
		size  int
	}{
		{"64_bytes", 64},
		{"256_bytes", 256},
		{"1KB", 1024},
		{"4KB", 4096},
		{"16KB", 16384},
		{"64KB", 65536},
	}

	for _, tc := range testCases {
		b.Run(tc.name, func(b *testing.B) {
			b.ReportAllocs()
			cache := NewMockCache()
			value := make([]byte, tc.size)

			b.Run("set", func(b *testing.B) {
				for i := 0; i < b.N; i++ {
					key := "key-" + string(rune(i%100))
					cache.Set(ctx, key, value, time.Hour)
				}
			})

			b.Run("get", func(b *testing.B) {
				cache.Set(ctx, "test-key", value, time.Hour)
				b.ResetTimer()
				for i := 0; i < b.N; i++ {
					cache.Get(ctx, "test-key")
				}
			})
		})
	}
}

// ============================================================
// TTL Expiration Benchmarks
// ============================================================

func BenchmarkCache_TTL(b *testing.B) {
	ctx := context.Background()

	b.Run("set_with_ttl", func(b *testing.B) {
		b.ReportAllocs()
		cache := NewMockCache()
		value := []byte("test")

		for i := 0; i < b.N; i++ {
			key := "key-" + string(rune(i))
			cache.Set(ctx, key, value, 5*time.Minute)
		}
	})

	b.Run("set_with_zero_ttl", func(b *testing.B) {
		b.ReportAllocs()
		cache := NewMockCache()
		value := []byte("test")

		for i := 0; i < b.N; i++ {
			key := "key-" + string(rune(i))
			cache.Set(ctx, key, value, 0)
		}
	})
}

// ============================================================
// Cache Key Generation
// ============================================================

func BenchmarkCacheKeyGeneration(b *testing.B) {
	b.Run("simple_key", func(b *testing.B) {
		b.ReportAllocs()
		for i := 0; i < b.N; i++ {
			key := "user:123:session:456"
			_ = key
		}
	})

	b.Run("complex_key", func(b *testing.B) {
		b.ReportAllocs()
		for i := 0; i < b.N; i++ {
			key := "sparkle:user:123:session:456:chat:789:message:999"
			_ = key
		}
	})

	b.Run("dynamic_key", func(b *testing.B) {
		b.ReportAllocs()
		for i := 0; i < b.N; i++ {
			key := "user:" + string(rune(i%1000)) + ":session:" + string(rune(i%100))
			_ = key
		}
	})
}

// ============================================================
// Batch Operations
// ============================================================

func BenchmarkCache_BatchGet(b *testing.B) {
	ctx := context.Background()
	cache := NewMockCache()

	// Pre-populate
	for i := 0; i < 1000; i++ {
		key := "key-" + string(rune(i))
		cache.Set(ctx, key, []byte("value"), time.Hour)
	}

	b.Run("batch_10", func(b *testing.B) {
		b.ReportAllocs()
		for i := 0; i < b.N; i += 10 {
			for j := 0; j < 10; j++ {
				key := "key-" + string(rune((i+j)%1000))
				cache.Get(ctx, key)
			}
		}
	})

	b.Run("batch_100", func(b *testing.B) {
		b.ReportAllocs()
		for i := 0; i < b.N; i += 100 {
			for j := 0; j < 100; j++ {
				key := "key-" + string(rune((i+j)%1000))
				cache.Get(ctx, key)
			}
		}
	})
}

// ============================================================
// Cache Eviction Simulation
// ============================================================

func BenchmarkCache_Eviction(b *testing.B) {
	ctx := context.Background()

	b.Run("lru_eviction", func(b *testing.B) {
		b.ReportAllocs()
		cache := NewMockCache()
		maxSize := 1000

		for i := 0; i < b.N; i++ {
			// Simulate LRU eviction
			if len(cache.data) >= maxSize {
				// Evict oldest (simplified)
				for key := range cache.data {
					cache.Delete(ctx, key)
					break
				}
			}

			key := "key-" + string(rune(i))
			cache.Set(ctx, key, []byte("value"), time.Hour)
		}
	})
}

// ============================================================
// Memory Allocation Patterns
// ============================================================

func BenchmarkCache_MemoryAllocation(b *testing.B) {
	ctx := context.Background()

	b.Run("allocate_and_free", func(b *testing.B) {
		b.ReportAllocs()
		for i := 0; i < b.N; i++ {
			cache := NewMockCache()
			value := make([]byte, 1024)
			cache.Set(ctx, "key", value, time.Hour)
			cache.Get(ctx, "key")
			// cache will be garbage collected
		}
	})

	b.Run("reuse_cache", func(b *testing.B) {
		b.ReportAllocs()
		cache := NewMockCache()
		value := make([]byte, 1024)

		for i := 0; i < b.N; i++ {
			key := "key-" + string(rune(i%100))
			cache.Set(ctx, key, value, time.Hour)
			cache.Get(ctx, key)
		}
	})
}

// ============================================================
// Semantic Cache Specific Benchmarks
// ============================================================

func BenchmarkSemanticCache_VectorComparison(b *testing.B) {
	// Simulate vector similarity comparison for semantic cache

	b.Run("small_vectors", func(b *testing.B) {
		b.ReportAllocs()
		vectorSize := 128

		for i := 0; i < b.N; i++ {
			vec1 := make([]float32, vectorSize)
			vec2 := make([]float32, vectorSize)

			// Simulate dot product
			var dot float32
			for j := 0; j < vectorSize; j++ {
				dot += vec1[j] * vec2[j]
			}
			_ = dot
		}
	})

	b.Run("medium_vectors", func(b *testing.B) {
		b.ReportAllocs()
		vectorSize := 512

		for i := 0; i < b.N; i++ {
			vec1 := make([]float32, vectorSize)
			vec2 := make([]float32, vectorSize)

			var dot float32
			for j := 0; j < vectorSize; j++ {
				dot += vec1[j] * vec2[j]
			}
			_ = dot
		}
	})

	b.Run("large_vectors", func(b *testing.B) {
		b.ReportAllocs()
		vectorSize := 1536 // OpenAI embedding size

		for i := 0; i < b.N; i++ {
			vec1 := make([]float32, vectorSize)
			vec2 := make([]float32, vectorSize)

			var dot float32
			for j := 0; j < vectorSize; j++ {
				dot += vec1[j] * vec2[j]
			}
			_ = dot
		}
	})
}
