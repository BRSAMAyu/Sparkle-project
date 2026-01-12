package chaos

import (
	"context"
	"net/http"
	"sync"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgconn"
	"github.com/sparkle/gateway/internal/db"
)

// Manager handles chaos engineering injection
type Manager struct {
	db     db.DBTX
	mu     sync.RWMutex
	config Config
}

type Config struct {
	InjectLatency    bool
	LatencyDuration  time.Duration
	InjectError      bool
	ErrorRate        float64 // 0.0 to 1.0
}

func NewManager(database db.DBTX) *Manager {
	return &Manager{
		db: database,
	}
}

// Implement DBTX interface
func (m *Manager) Exec(ctx context.Context, sql string, args ...interface{}) (pgconn.CommandTag, error) {
	m.injectChaos()
	return m.db.Exec(ctx, sql, args...)
}

func (m *Manager) Query(ctx context.Context, sql string, args ...interface{}) (pgx.Rows, error) {
	m.injectChaos()
	return m.db.Query(ctx, sql, args...)
}

func (m *Manager) QueryRow(ctx context.Context, sql string, args ...interface{}) pgx.Row {
	m.injectChaos()
	return m.db.QueryRow(ctx, sql, args...)
}

func (m *Manager) injectChaos() {
	m.mu.RLock()
	defer m.mu.RUnlock()

	if m.config.InjectLatency {
		time.Sleep(m.config.LatencyDuration)
	}
}

// HTTP Handler
func (m *Manager) HandleInject(c *gin.Context) {
	type Request struct {
		Type     string `form:"type"`     // latency, error
		Duration string `form:"duration"` // e.g. 30s
	}

	var req Request
	if err := c.BindQuery(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid parameters"})
		return
	}

	m.mu.Lock()
	defer m.mu.Unlock()

	switch req.Type {
	case "latency":
		duration, err := time.ParseDuration(req.Duration)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid duration format"})
			return
		}
		m.config.InjectLatency = true
		m.config.LatencyDuration = duration
		
		// Auto disable after some time (safety mechanism)
		go func() {
			time.Sleep(2 * time.Minute)
			m.mu.Lock()
			m.config.InjectLatency = false
			m.mu.Unlock()
		}()

		c.JSON(http.StatusOK, gin.H{"status": "injected", "type": "latency", "duration": duration.String()})
	case "reset":
		m.config = Config{}
		c.JSON(http.StatusOK, gin.H{"status": "reset"})
	default:
		c.JSON(http.StatusBadRequest, gin.H{"error": "Unknown chaos type"})
	}
}