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

var noopHandler event.Handler = func(_ context.Context, _ event.DomainEvent, _ string) error {
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

	// 同上（V3-FIX-544/552）：负载 runner 下 goroutine 启动与首次日志落表也被
	// 拖慢，2s 预算同族收紧；等待成立即返回，放宽只消假阴性。
	waitForLogEntry(t, observed, "Worker started", 10*time.Second)
	cancel()

	// V3-FIX-552（CI 负载敏感测试族）：Run 退出要等在途 XReadGroup/命令级超时
	// 收尾（go-redis 池 dial 重试吃预算，FIX-544 实录机制），负载下可能晚于 5s。
	// 等待成立即返回，预算放宽不影响健康路径时长，只消假阴性：5s → 30s。
	select {
	case err := <-runResult:
		if !errors.Is(err, context.Canceled) {
			t.Fatalf("Run() = %v, want context.Canceled", err)
		}
	case <-time.After(30 * time.Second):
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
		Options{
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

	// 同上（V3-FIX-544）：负载 runner 下 goroutine 启动与首次日志落表也被
	// 拖慢，2s 预算同族收紧；等待成立即返回，放宽只消假阴性。
	waitForLogEntry(t, observed, "Worker started", 10*time.Second)

	// Redis 变不可达而进程上下文仍存活：processMessages 的失败必须保持 ERROR。
	//
	// V3-FIX-544（CI 负载敏感测试族）：断言本身就是相对等待（waitForLogEntry
	// 轮询至成立），这里给的是等待预算而非固定 deadline。健康路径实测 ~1.6s
	// （go-redis 池 5 次 dial 重试 + 命令级退避吃掉大半），CI 28 在负载 runner
	// 上超 5s 预算（5.00s 超时形态实录）。等待成立即返回，放宽预算不影响
	// 健康路径时长，只消除负载下的假阴性：5s → 30s。
	mr.Close()
	waitForLogEntry(t, observed, "Error processing messages", 30*time.Second)

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
	LogRunnerStopped(context.Background(), log, "runner-a", nil)

	// 关停窗口（ctx 已取消）→ INFO，即使 err == context.Canceled
	shutdownCtx, cancel := context.WithCancel(context.Background())
	cancel()
	LogRunnerStopped(shutdownCtx, log, "runner-b", context.Canceled)

	// 进程仍存活时失败 → ERROR
	LogRunnerStopped(context.Background(), log, "runner-c", errors.New("boom"))

	// 非关停期出现的 canceled → 保持 ERROR（卡语义：仅关停期 canceled 降级）
	LogRunnerStopped(context.Background(), log, "runner-d", context.Canceled)

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
