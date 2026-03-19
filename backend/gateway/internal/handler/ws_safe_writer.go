package handler

import (
	"encoding/json"
	"time"

	"github.com/gorilla/websocket"
)

type wsSafeWriter struct {
	conn      *websocket.Conn
	writeMu   chan struct{}
	writeWait time.Duration
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
	<-w.writeMu
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
	return w.withLock(func() error {
		return w.conn.WriteControl(messageType, data, time.Now().Add(w.writeWait))
	})
}
