package handler

import (
	"context"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync"
	"testing"
	"time"

	"github.com/gorilla/websocket"
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

func TestWSSafeWriterWriteControlContextTimesOutWaitingForLock(t *testing.T) {
	writer := &wsSafeWriter{
		writeMu:   make(chan struct{}, 1),
		writeWait: time.Hour,
	}

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Millisecond)
	defer cancel()

	err := writer.WriteControlContext(ctx, websocket.PingMessage, nil)
	require.Error(t, err)
	require.ErrorIs(t, err, context.DeadlineExceeded)
}

func TestWSSafeWriterCloseIsIdempotent(t *testing.T) {
	serverConn, clientConn, cleanup := newWSSafeWriterTestPair(t)
	defer cleanup()

	writer := newWSSafeWriter(serverConn, time.Second)
	require.NoError(t, writer.Close())
	require.NoError(t, writer.Close())
	require.NoError(t, writer.Close())
	_ = clientConn.Close()
}

func TestWSSafeWriterConcurrentCloseDoesNotPanic(t *testing.T) {
	serverConn, clientConn, cleanup := newWSSafeWriterTestPair(t)
	defer cleanup()

	writer := newWSSafeWriter(serverConn, time.Second)
	var wg sync.WaitGroup
	errs := make(chan error, 32)
	for i := 0; i < 32; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			errs <- writer.Close()
		}()
	}
	wg.Wait()
	close(errs)

	for err := range errs {
		require.NoError(t, err)
	}
	_ = clientConn.Close()
}

func newWSSafeWriterTestPair(t *testing.T) (*websocket.Conn, *websocket.Conn, func()) {
	t.Helper()

	connCh := make(chan *websocket.Conn, 1)
	errCh := make(chan error, 1)
	upgrader := websocket.Upgrader{CheckOrigin: func(*http.Request) bool { return true }}
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		conn, err := upgrader.Upgrade(w, r, nil)
		if err != nil {
			errCh <- err
			return
		}
		connCh <- conn
	}))

	clientConn, _, err := websocket.DefaultDialer.Dial("ws"+strings.TrimPrefix(server.URL, "http"), nil)
	require.NoError(t, err)

	select {
	case err := <-errCh:
		server.Close()
		_ = clientConn.Close()
		require.NoError(t, err)
	case serverConn := <-connCh:
		cleanup := func() {
			_ = serverConn.Close()
			_ = clientConn.Close()
			server.Close()
		}
		return serverConn, clientConn, cleanup
	case <-time.After(time.Second):
		server.Close()
		_ = clientConn.Close()
		t.Fatal("server WebSocket connection was not established")
	}

	return nil, nil, func() {}
}
