package worker

// V3-FIX-481 契约测试：BaseWorker 进程内幂等缓存必须有界。
//
// 病灶（wt749 登记）：processedIDs（base.go:65）仅 Store 不淘汰——每条已处理
// 消息 ID 永久驻留，网关进程长活期间内存单调涨（stream ID ~15-20B/条 +
// sync.Map entry 开销，月级长跑百万条消息可达数十 MB 驻留）。
//
// 语义定位（V3-FIX-469 修后）：processed_events DB 闸才是权威重复吸收层
// （IsProcessed/MarkProcessed 经 normalizeEventKey 真实落库），进程内缓存只是
// 热路径加速层——淘汰任何条目最多让一条重投旧事件多付一次 DB IsProcessed
// 查询，绝不产生双重处理。因此缓存必须加界：容量淘汰后回落 DB 闸即正确。
//
// 本文件钉两条契约：
//  1. 连续标记超过容量的不同消息 ID 后，缓存驻留条数不得超容量（修前
//     sync.Map 无界增长即红）；
//  2. 容量内的缓存命中语义不变（markProcessed 后 isProcessed 命中，未标记
//     的 ID 不误报已处理）——加速层角色保留，删除缓存或破坏命中即红。

import (
	"context"
	"fmt"
	"testing"

	"github.com/alicebob/miniredis/v2"
	"github.com/redis/go-redis/v9"
	"go.uber.org/zap"
)

// processedCacheEntryCount measures the live entry count of the worker's
// in-process idempotency cache.
func processedCacheEntryCount(w *BaseWorker) int {
	return w.processedCache.Len()
}

func newCacheProbeWorker(t *testing.T) *BaseWorker {
	t.Helper()
	mr := miniredis.RunT(t)
	rdb := redis.NewClient(&redis.Options{Addr: mr.Addr()})
	t.Cleanup(func() { _ = rdb.Close() })

	return NewBaseWorker(rdb, nil, testMetrics(t), zap.NewNop(),
		"cqrs:stream:cache-bound-test", "grp-cache-bound", "consumer-1")
}

// TestProcessedIDsCacheStaysBounded：超过容量的连续标记后缓存必须有界。
func TestProcessedIDsCacheStaysBounded(t *testing.T) {
	w := newCacheProbeWorker(t)

	const overshoot = 64
	for i := 0; i < processedCacheSize+overshoot; i++ {
		w.markProcessed(context.Background(), fmt.Sprintf("1758-%d", i))
	}

	if got := processedCacheEntryCount(w); got > processedCacheSize {
		t.Fatalf("processed cache holds %d entries after %d markProcessed calls, want <= %d: cache grows without bound (V3-FIX-481)",
			got, processedCacheSize+overshoot, processedCacheSize)
	}
}

// TestProcessedCacheStillServesHits：容量内命中语义不变——已标记 ID 命中
// （跳过 DB 查），未标记 ID 不误报（nil repo 下回落即 false）。
func TestProcessedCacheStillServesHits(t *testing.T) {
	w := newCacheProbeWorker(t)

	const marked = "1758-1"
	w.markProcessed(context.Background(), marked)

	if !w.isProcessed(context.Background(), marked) {
		t.Fatalf("isProcessed(%q) = false after markProcessed: in-process hit must be served by the cache", marked)
	}
	const unknown = "1758-2"
	if w.isProcessed(context.Background(), unknown) {
		t.Fatalf("isProcessed(%q) = true without markProcessed and nil repository: must not report unprocessed IDs", unknown)
	}
}
