package worker

// PROD-LOG #8 契约测试：关停窗口内的 "context canceled" 必须以 INFO（或更低）
// 级别落日志，不得伪装成 ERROR（每次重启 ~13 条假错误的根因）；仅进程上下文
// 仍存活时的失败保持 ERROR。

import (
	"context"
	"errors"
	"sync"
	"testing"
	"time"

	"github.com/alicebob/miniredis/v2"
	"github.com/redis/go-redis/v9"
	"go.uber.org/zap"
	"go.uber.org/zap/zapcore"
	"go.uber.org/zap/zaptest/observer"

	"github.com/sparkle/gateway/internal/cqrs/event"
	"github.com/sparkle/gateway/internal/cqrs/metrics"
)

var (
	sharedMetricsOnce sync.Once
	sharedMetrics     *metrics.CQRSMetrics
)

// testMetrics 返回测试二进制内共享的单例 CQRSMetrics：NewCQRSMetrics 会向
// prometheus 默认注册表注册，第二个实例会 panic（duplicate collector）。
func testMetrics(t *testing.T) *metrics.CQRSMetrics {
	t.Helper()
	sharedMetricsOnce.Do(func() {
		sharedMetrics = metrics.NewCQRSMetrics("test_cqrs_worker")
	})
	return sharedMetrics
}

var noopHandler event.EventHandler = func(_ context.Context, _ event.DomainEvent, _ string) error {
	return nil
}

func waitForLogEntry(t *testing.T, observed *observer.ObservedLogs, msg string, timeout time.Duration) {
	t.Helper()
	deadline := time.Now().Add(timeout)
	for time.Now().Before(deadline) {
		for _, entry := range observed.TakeAll() {
			if entry.Message == msg {
				return
			}
		}
		time.Sleep(10 * time.Millisecond)
	}
	t.Fatalf("log entry %q not observed within %s", msg, timeout)
}

func TestRunGracefulShutdownLogsNoError(t *testing.T) {
	mr := miniredis.RunT(t)
	rdb := redis.NewClient(&redis.Options{Addr: mr.Addr()})
	t.Cleanup(func() { _ = rdb.Close() })

	core, observed := observer.New(zapcore.InfoLevel)
	w := NewBaseWorker(rdb, nil, testMetrics(t), zap.New(core),
		"cqrs:stream:shutdown-test", "grp-shutdown", "consumer-1")

	ctx, cancel := context.WithCancel(context.Background())
	runResult := make(chan error, 1)
	go func() {
		runResult <- w.Run(ctx, noopHandler)
	}()

	waitForLogEntry(t, observed, "Worker started", 2*time.Second)
	cancel()

	select {
	case err := <-runResult:
		if !errors.Is(err, context.Canceled) {
			t.Fatalf("Run() = %v, want context.Canceled", err)
		}
	case <-time.After(5 * time.Second):
		t.Fatal("Run did not return after context cancel")
	}

	for _, entry := range observed.TakeAll() {
		if entry.Level >= zapcore.ErrorLevel {
			t.Fatalf("graceful shutdown must not log ERROR, got %q: %s", entry.Level, entry.Message)
		}
	}
}

func TestRunLiveProcessFailureStillLogsError(t *testing.T) {
	mr := miniredis.RunT(t)
	rdb := redis.NewClient(&redis.Options{Addr: mr.Addr()})

	core, observed := observer.New(zapcore.InfoLevel)
	w := NewBaseWorker(rdb, nil, testMetrics(t), zap.New(core),
		"cqrs:stream:failure-test", "grp-failure", "consumer-1",
		WorkerOptions{
			BatchSize:        10,
			BlockTimeout:     20 * time.Millisecond,
			IdempotencyCheck: false,
			EnableDLQ:        true,
			MaxRetries:       1,
		},
	)

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	runResult := make(chan error, 1)
	go func() {
		runResult <- w.Run(ctx, noopHandler)
	}()

	waitForLogEntry(t, observed, "Worker started", 2*time.Second)

	// Redis 变不可达而进程上下文仍存活：processMessages 的失败必须保持 ERROR。
	mr.Close()
	waitForLogEntry(t, observed, "Error processing messages", 5*time.Second)

	select {
	case <-runResult:
		t.Fatal("Run returned before context cancel")
	default:
	}
}

func TestLogRunnerStoppedGradesByShutdownState(t *testing.T) {
	core, observed := observer.New(zapcore.InfoLevel)
	log := zap.New(core)

	// err == nil → INFO（无错误收尾）
	LogRunnerStopped(log, context.Background(), "runner-a", nil)

	// 关停窗口（ctx 已取消）→ INFO，即使 err == context.Canceled
	shutdownCtx, cancel := context.WithCancel(context.Background())
	cancel()
	LogRunnerStopped(log, shutdownCtx, "runner-b", context.Canceled)

	// 进程仍存活时失败 → ERROR
	LogRunnerStopped(log, context.Background(), "runner-c", errors.New("boom"))

	// 非关停期出现的 canceled → 保持 ERROR（卡语义：仅关停期 canceled 降级）
	LogRunnerStopped(log, context.Background(), "runner-d", context.Canceled)

	entries := observed.TakeAll()
	if len(entries) != 4 {
		t.Fatalf("got %d log entries, want 4", len(entries))
	}
	wantLevels := []zapcore.Level{
		zapcore.InfoLevel,
		zapcore.InfoLevel,
		zapcore.ErrorLevel,
		zapcore.ErrorLevel,
	}
	for i, want := range wantLevels {
		if entries[i].Level != want {
			t.Fatalf("entry %d (%s) = %s, want %s", i, entries[i].Message, entries[i].Level, want)
		}
	}
	if entries[1].Message != "runner-b stopped (graceful shutdown)" {
		t.Fatalf("shutdown entry message = %q", entries[1].Message)
	}
}
