package handler

import (
	"context"
	"encoding/json"
	"fmt"
	"sync"
	"time"

	"github.com/gorilla/websocket"
)

type wsSafeWriter struct {
	conn      *websocket.Conn
	writeMu   chan struct{}
	writeWait time.Duration
	closeOnce sync.Once
}

func newWSSafeWriter(conn *websocket.Conn, writeWait time.Duration) *wsSafeWriter {
	lock := make(chan struct{}, 1)
	lock <- struct{}{}
	return &wsSafeWriter{
		conn:      conn,
		writeMu:   lock,
		writeWait: writeWait,
	}
}

func (w *wsSafeWriter) withLock(fn func() error) error {
	ctx, cancel := context.WithTimeout(context.Background(), w.writeWait)
	defer cancel()
	return w.withLockContext(ctx, fn)
}

func (w *wsSafeWriter) withLockContext(ctx context.Context, fn func() error) error {
	if ctx == nil {
		ctx = context.Background()
	}
	select {
	case <-w.writeMu:
	case <-ctx.Done():
		return fmt.Errorf("ws writer lock timeout after %s: %w", w.writeWait, ctx.Err())
	}
	defer func() {
		w.writeMu <- struct{}{}
	}()
	return fn()
}

func (w *wsSafeWriter) WriteJSON(payload interface{}) error {
	data, err := json.Marshal(payload)
	if err != nil {
		return err
	}
	return w.WriteMessage(websocket.TextMessage, data)
}

func (w *wsSafeWriter) WriteMessage(messageType int, data []byte) error {
	return w.withLock(func() error {
		_ = w.conn.SetWriteDeadline(time.Now().Add(w.writeWait))
		defer func() {
			_ = w.conn.SetWriteDeadline(time.Time{})
		}()
		return w.conn.WriteMessage(messageType, data)
	})
}

func (w *wsSafeWriter) WriteControl(messageType int, data []byte) error {
	ctx, cancel := context.WithTimeout(context.Background(), w.writeWait)
	defer cancel()
	return w.WriteControlContext(ctx, messageType, data)
}

func (w *wsSafeWriter) WriteControlContext(ctx context.Context, messageType int, data []byte) error {
	if ctx == nil {
		ctx = context.Background()
	}
	if _, ok := ctx.Deadline(); !ok {
		var cancel context.CancelFunc
		ctx, cancel = context.WithTimeout(ctx, w.writeWait)
		defer cancel()
	}
	return w.withLockContext(ctx, func() error {
		deadline := time.Now().Add(w.writeWait)
		if ctxDeadline, ok := ctx.Deadline(); ok && ctxDeadline.Before(deadline) {
			deadline = ctxDeadline
		}
		return w.conn.WriteControl(messageType, data, deadline)
	})
}

func (w *wsSafeWriter) Close() error {
	var closeErr error
	closedNow := false
	w.closeOnce.Do(func() {
		closedNow = true
		closeErr = w.conn.Close()
	})
	if !closedNow {
		return nil
	}
	return closeErr
}
