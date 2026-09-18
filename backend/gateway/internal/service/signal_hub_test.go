package service

import (
	"errors"
	"sync"
	"testing"
	"time"
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

// blockingConn blocks inside WriteJSON until released, simulating a slow
// chat connection (writeWait floors at 60s).
type blockingConn struct {
	release chan struct{}
}

func (c *blockingConn) WriteJSON(payload interface{}) error {
	<-c.release
	return nil
}

func (c *blockingConn) Close() error {
	return nil
}

// R2-GW-5 regression: a stalled connection for one user must not delay
// widget pushes to other users. With the old hub-wide sendMu, Send below
// deadlocked behind the blocked write and the test failed by timeout.
func TestSignalHubSendDoesNotHeadOfLineBlockOtherUsers(t *testing.T) {
	hub := NewSignalHub()
	release := make(chan struct{})
	hub.Register("slow-user", &blockingConn{release: release})
	other := &testSignalConn{}
	hub.Register("other-user", other)

	slowSendDone := make(chan struct{})
	go func() {
		defer close(slowSendDone)
		hub.Send("slow-user", map[string]string{"type": "widget"})
	}()

	otherSendDone := make(chan struct{})
	go func() {
		defer close(otherSendDone)
		hub.Send("other-user", map[string]string{"type": "widget"})
	}()

	select {
	case <-otherSendDone:
	case <-time.After(2 * time.Second):
		t.Fatal("Send to an unrelated user blocked behind a stalled connection (hub-wide send lock regression)")
	}

	if other.writes != 1 {
		t.Fatalf("other connection writes = %d, want 1", other.writes)
	}

	// Unblock the stalled write and let the slow send drain cleanly.
	close(release)
	<-slowSendDone
}
