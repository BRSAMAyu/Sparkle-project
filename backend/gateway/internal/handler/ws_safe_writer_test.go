package handler

import (
	"testing"
	"time"

	"github.com/stretchr/testify/require"
)

func TestWSSafeWriterWithLockTimesOut(t *testing.T) {
	writer := &wsSafeWriter{
		writeMu:   make(chan struct{}, 1),
		writeWait: 10 * time.Millisecond,
	}

	errCh := make(chan error, 1)
	go func() {
		errCh <- writer.withLock(func() error {
			return nil
		})
	}()

	select {
	case err := <-errCh:
		require.Error(t, err)
		require.Contains(t, err.Error(), "lock timeout")
	case <-time.After(200 * time.Millisecond):
		t.Fatal("withLock did not time out")
	}
}
