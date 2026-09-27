package worker

// V3-FIX-461 契约测试：CQRS stream 消费必须重投滞留 PEL 的 in-flight 事件。
//
// 病灶（wt739 登记）：BaseWorker 消费循环只读 `>`（组内从未派发过的新消息），
// 无 XAUTOCLAIM/"0" 起 PEL 回放——崩溃或优雅关停打断 in-flight 事件时
// （XAck/DLQ 均持已取消 ctx 失败），事件滞留 consumer PEL 永不重投。
//
// 本文件用 miniredis 模拟「worker 认领进 PEL 后崩溃（未 XAck）」：
// 直接以相同 consumer 名 XReadGroup 认领后不确认，即等价于崩溃现场
// （PEL 归属由 consumer 名决定，与进程是否存活无关），随后以同名 consumer
// 重启消费循环，事件必须被重投处理；修前恒滞留（handler 永不被调）即红。

import (
	"context"
	"encoding/json"
	"strings"
	"testing"
	"time"

	"github.com/alicebob/miniredis/v2"
	"github.com/google/uuid"
	"github.com/redis/go-redis/v9"
	"go.uber.org/zap"

	"github.com/sparkle/gateway/internal/cqrs/event"
)

// addTestEvent 向 stream 写入一条可被 parseRedisMessage 解析的事件，
// 字段形制与 event/redis_bus.go 的序列化一致。
func addTestEvent(t *testing.T, rdb *redis.Client, streamKey, eventID string) string {
	t.Helper()
	payload, err := json.Marshal(map[string]interface{}{"event_id": eventID})
	if err != nil {
		t.Fatalf("marshal payload: %v", err)
	}
	msgID, err := rdb.XAdd(context.Background(), &redis.XAddArgs{
		Stream: streamKey,
		Values: map[string]interface{}{
			"id":             eventID,
			"type":           "test.pel_event",
			"version":        1,
			"aggregate_type": "test",
			"aggregate_id":   uuid.NewString(),
			"timestamp":      time.Now().UTC().Format(time.RFC3339Nano),
			"payload":        string(payload),
			"metadata":       "",
		},
	}).Result()
	if err != nil {
		t.Fatalf("XAdd: %v", err)
	}
	return msgID
}

// claimAndAbandon 模拟崩溃现场：以给定 consumer 名认领组内全部未派发消息进
// PEL，且绝不 XAck——与「进程在 in-flight 处理中被杀」后的 Redis 状态一致。
func claimAndAbandon(t *testing.T, rdb *redis.Client, streamKey, group, consumer string) {
	t.Helper()
	// 崩溃前 worker 已通过 ensureConsumerGroup 建组
	if err := rdb.XGroupCreateMkStream(context.Background(), streamKey, group, "0").Err(); err != nil && !strings.Contains(err.Error(), "BUSYGROUP") {
		t.Fatalf("XGroupCreateMkStream: %v", err)
	}
	entries, err := rdb.XReadGroup(context.Background(), &redis.XReadGroupArgs{
		Group:    group,
		Consumer: consumer,
		Streams:  []string{streamKey, ">"},
		Count:    10,
	}).Result()
	if err != nil {
		t.Fatalf("XReadGroup claim: %v", err)
	}
	claimed := 0
	for _, s := range entries {
		claimed += len(s.Messages)
	}
	if claimed == 0 {
		t.Fatal("expected to claim at least one message into PEL")
	}
	pending, err := rdb.XPending(context.Background(), streamKey, group).Result()
	if err != nil {
		t.Fatalf("XPending: %v", err)
	}
	if pending.Count != int64(claimed) {
		t.Fatalf("PEL count = %d, want %d", pending.Count, claimed)
	}
}

func waitForEvent(t *testing.T, ch chan event.DomainEvent) event.DomainEvent {
	t.Helper()
	select {
	case evt := <-ch:
		return evt
	case <-time.After(5 * time.Second):
		t.Fatal("handler was not called within 5s: abandoned PEL entry never redelivered")
		return event.DomainEvent{}
	}
}

func waitForEventID(t *testing.T, ch chan string) string {
	t.Helper()
	select {
	case id := <-ch:
		return id
	case <-time.After(5 * time.Second):
		t.Fatal("expected delivery not observed within 5s")
		return ""
	}
}

func drainWorker(t *testing.T, cancel context.CancelFunc, runResult chan error) {
	t.Helper()
	cancel()
	select {
	case <-runResult:
	case <-time.After(5 * time.Second):
		t.Fatal("Run did not return after context cancel")
	}
}

// TestRunRedeliversAbandonedPendingEventAfterCrash：认领后未 XAck 的事件，
// 同名 consumer 重启后必须被重投处理，且处理成功后移出 PEL。
func TestRunRedeliversAbandonedPendingEventAfterCrash(t *testing.T) {
	mr := miniredis.RunT(t)
	rdb := redis.NewClient(&redis.Options{Addr: mr.Addr()})
	t.Cleanup(func() { _ = rdb.Close() })

	const (
		streamKey = "cqrs:stream:pel-redeliver-test"
		group     = "grp-pel-redeliver"
		consumer  = "pel_worker_1" // 固定 consumer 名（生产形制）
	)

	addTestEvent(t, rdb, streamKey, "evt-abandoned-1")
	claimAndAbandon(t, rdb, streamKey, group, consumer)

	events := make(chan event.DomainEvent, 16)
	handler := func(_ context.Context, evt event.DomainEvent, _ string) error {
		events <- evt
		return nil
	}

	w := NewBaseWorker(rdb, nil, testMetrics(t), zap.NewNop(),
		streamKey, group, consumer,
		Options{
			BatchSize:        10,
			BlockTimeout:     20 * time.Millisecond,
			IdempotencyCheck: true,
			EnableDLQ:        true,
			MaxRetries:       1,
		},
	)

	ctx, cancel := context.WithCancel(context.Background())
	runResult := make(chan error, 1)
	go func() {
		runResult <- w.Run(ctx, handler)
	}()
	t.Cleanup(func() { cancel() })

	got := waitForEvent(t, events)
	if got.ID != "evt-abandoned-1" {
		t.Fatalf("redelivered event ID = %q, want %q", got.ID, "evt-abandoned-1")
	}

	drainWorker(t, cancel, runResult)

	pending, err := rdb.XPending(context.Background(), streamKey, group).Result()
	if err != nil {
		t.Fatalf("XPending: %v", err)
	}
	if pending.Count != 0 {
		t.Fatalf("PEL count = %d after successful replay, want 0 (must be acked)", pending.Count)
	}
}

// TestRunDrainsPendingBeforeNewMessages：重启后滞留 PEL 的旧事件必须先于
// 之后新到达的事件被处理（恢复优先于新消费）。
func TestRunDrainsPendingBeforeNewMessages(t *testing.T) {
	mr := miniredis.RunT(t)
	rdb := redis.NewClient(&redis.Options{Addr: mr.Addr()})
	t.Cleanup(func() { _ = rdb.Close() })

	const (
		streamKey = "cqrs:stream:pel-order-test"
		group     = "grp-pel-order"
		consumer  = "pel_worker_1"
	)

	addTestEvent(t, rdb, streamKey, "evt-pending-old")
	claimAndAbandon(t, rdb, streamKey, group, consumer)
	// 崩溃之后才到达的新消息
	addTestEvent(t, rdb, streamKey, "evt-new-late")

	ordered := make(chan string, 16)
	done := make(chan struct{})
	handler := func(_ context.Context, evt event.DomainEvent, _ string) error {
		ordered <- evt.ID
		if evt.ID == "evt-new-late" {
			close(done)
		}
		return nil
	}

	w := NewBaseWorker(rdb, nil, testMetrics(t), zap.NewNop(),
		streamKey, group, consumer,
		Options{
			BatchSize:        10,
			BlockTimeout:     20 * time.Millisecond,
			IdempotencyCheck: true,
			EnableDLQ:        true,
			MaxRetries:       1,
		},
	)

	ctx, cancel := context.WithCancel(context.Background())
	runResult := make(chan error, 1)
	go func() {
		runResult <- w.Run(ctx, handler)
	}()
	t.Cleanup(func() { cancel() })

	select {
	case <-done:
	case <-time.After(5 * time.Second):
		t.Fatal("handler did not observe evt-new-late within 5s")
	}

	drainWorker(t, cancel, runResult)

	// 修前只有 evt-new-late 被投递（PEL 恒滞留），第二个接收会超时红出
	first := waitForEventID(t, ordered)
	second := waitForEventID(t, ordered)
	if first != "evt-pending-old" || second != "evt-new-late" {
		t.Fatalf("delivery order = [%q, %q], want [evt-pending-old, evt-new-late]: PEL must drain before new reads", first, second)
	}
}
