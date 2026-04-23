package service

import (
	"errors"
	"sync"
	"testing"
)

type testSignalConn struct {
	mu     sync.Mutex
	writes int
	closed bool
	fail   bool
}

func (c *testSignalConn) WriteJSON(payload interface{}) error {
	c.mu.Lock()
	defer c.mu.Unlock()
	if c.fail {
		return errors.New("write failed")
	}
	c.writes++
	return nil
}

func (c *testSignalConn) Close() error {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.closed = true
	return nil
}

func TestSignalHubSendRemovesFailedConnections(t *testing.T) {
	hub := NewSignalHub()
	good := &testSignalConn{}
	bad := &testSignalConn{fail: true}
	hub.Register("user-1", good)
	hub.Register("user-1", bad)

	hub.Send("user-1", map[string]string{"type": "widget"})

	if good.writes != 1 {
		t.Fatalf("good connection writes = %d, want 1", good.writes)
	}
	if !bad.closed {
		t.Fatal("failed connection was not closed")
	}
	if _, ok := hub.connections["user-1"][bad]; ok {
		t.Fatal("failed connection was not unregistered")
	}
}

func TestSignalHubSendAllowsConcurrentUnregister(t *testing.T) {
	hub := NewSignalHub()
	conns := make([]*testSignalConn, 50)
	for i := range conns {
		conns[i] = &testSignalConn{}
		hub.Register("user-1", conns[i])
	}

	var wg sync.WaitGroup
	for i := 0; i < 20; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			hub.Send("user-1", map[string]string{"type": "widget"})
		}()
	}
	for _, conn := range conns {
		wg.Add(1)
		go func(conn *testSignalConn) {
			defer wg.Done()
			hub.Unregister("user-1", conn)
		}(conn)
	}
	wg.Wait()
}
