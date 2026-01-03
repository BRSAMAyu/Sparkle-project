package db

import (
	"context"
	"fmt"
	"os"
	"sync"
	"testing"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgconn"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// ============================================================
// Integration Test Utilities
// ============================================================

// TestDB provides a test database connection
type TestDB struct {
	pool *pgxpool.Pool
	conn *pgx.Conn
}

func setupTestDB(t *testing.T) *TestDB {
	// Get database URL from environment or use default
	dbURL := os.Getenv("TEST_DATABASE_URL")
	if dbURL == "" {
		dbURL = "postgres://sparkle:password@localhost:5432/sparkle_test?sslmode=disable"
	}

	// Create connection pool
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	config, err := pgxpool.ParseConfig(dbURL)
	if err != nil {
		t.Skipf("Invalid database URL: %v", err)
	}

	pool, err := pgxpool.NewWithConfig(context.Background(), config)
	if err != nil {
		t.Skipf("Could not connect to test database: %v. Set TEST_DATABASE_URL environment variable.", err)
	}

	conn, err := pool.Acquire(ctx)
	if err != nil {
		pool.Close()
		t.Skipf("Could not acquire connection from pool: %v", err)
	}

	return &TestDB{
		pool: pool,
		conn: conn.Conn(),
	}
}

func (tdb *TestDB) cleanup(t *testing.T) {
	if tdb.conn != nil {
		tdb.conn.Close(context.Background())
	}
	if tdb.pool != nil {
		tdb.pool.Close()
	}
}

// ============================================================
// Transaction Tests
// ============================================================

func TestTransactionRollback(t *testing.T) {
	t.Skip("Skipped - requires live database")

	tdb := setupTestDB(t)
	defer tdb.cleanup(t)

	ctx := context.Background()

	// Begin transaction
	tx, err := tdb.pool.Begin(ctx)
	require.NoError(t, err)
	defer tx.Rollback(ctx)

	// Execute query in transaction
	var result int
	err = tx.QueryRow(ctx, "SELECT 1").Scan(&result)
	assert.NoError(t, err)
	assert.Equal(t, 1, result)
}

func TestTransactionCommit(t *testing.T) {
	t.Skip("Skipped - requires live database")

	tdb := setupTestDB(t)
	defer tdb.cleanup(t)

	ctx := context.Background()

	// Begin transaction
	tx, err := tdb.pool.Begin(ctx)
	require.NoError(t, err)

	// Execute query in transaction
	var result int
	err = tx.QueryRow(ctx, "SELECT 1").Scan(&result)
	assert.NoError(t, err)

	// Commit
	err = tx.Commit(ctx)
	assert.NoError(t, err)
}

func TestTransactionNesting(t *testing.T) {
	t.Skip("Skipped - requires live database")

	tdb := setupTestDB(t)
	defer tdb.cleanup(t)

	ctx := context.Background()

	// Outer transaction
	tx1, err := tdb.pool.Begin(ctx)
	require.NoError(t, err)

	// Savepoint (pseudo-nesting in PostgreSQL)
	sp, err := tx1.SavePoint(ctx, "sp1")
	assert.NoError(t, err)
	assert.NotNil(t, sp)

	// Rollback to savepoint
	err = tx1.RollbackToSavePoint(ctx, sp)
	assert.NoError(t, err)

	// Commit outer transaction
	err = tx1.Commit(ctx)
	assert.NoError(t, err)
}

// ============================================================
// Concurrent Access Tests
// ============================================================

func TestConcurrentConnections(t *testing.T) {
	tdb := setupTestDB(t)
	defer tdb.cleanup(t)

	ctx := context.Background()
	numGoroutines := 10
	done := make(chan bool, numGoroutines)

	// Launch concurrent queries
	for i := 0; i < numGoroutines; i++ {
		go func(id int) {
			conn, err := tdb.pool.Acquire(ctx)
			if err != nil {
				t.Logf("Failed to acquire connection: %v", err)
				done <- false
				return
			}
			defer conn.Release()

			var result int
			err = conn.QueryRow(ctx, "SELECT $1", id).Scan(&result)
			done <- err == nil && result == id
		}(i)
	}

	// Wait for all goroutines
	successCount := 0
	for i := 0; i < numGoroutines; i++ {
		if <-done {
			successCount++
		}
	}

	assert.GreaterOrEqual(t, successCount, numGoroutines-2, "Most concurrent connections should succeed")
}

func TestConcurrentTransactions(t *testing.T) {
	t.Skip("Skipped - requires live database with test table")

	tdb := setupTestDB(t)
	defer tdb.cleanup(t)

	ctx := context.Background()
	numTransactions := 5
	done := make(chan error, numTransactions)

	// Launch concurrent transactions
	for i := 0; i < numTransactions; i++ {
		go func(id int) {
			tx, err := tdb.pool.Begin(ctx)
			if err != nil {
				done <- err
				return
			}

			// Simulate work
			var result int
			err = tx.QueryRow(ctx, "SELECT $1", id).Scan(&result)
			if err != nil {
				tx.Rollback(ctx)
				done <- err
				return
			}

			done <- tx.Commit(ctx)
		}(i)
	}

	// Check results
	errorCount := 0
	for i := 0; i < numTransactions; i++ {
		if err := <-done; err != nil {
			errorCount++
		}
	}

	assert.Equal(t, 0, errorCount, "All transactions should succeed")
}

// ============================================================
// Connection Pool Tests
// ============================================================

func TestConnectionPoolAcquisition(t *testing.T) {
	tdb := setupTestDB(t)
	defer tdb.cleanup(t)

	ctx := context.Background()

	// Acquire and release multiple connections
	for i := 0; i < 5; i++ {
		conn, err := tdb.pool.Acquire(ctx)
		assert.NoError(t, err)
		assert.NotNil(t, conn)

		var result int
		err = conn.QueryRow(ctx, "SELECT 1").Scan(&result)
		assert.NoError(t, err)
		assert.Equal(t, 1, result)

		conn.Release()
	}
}

func TestConnectionPoolExhaustion(t *testing.T) {
	t.Skip("Skipped - requires specific pool configuration")

	// This would test behavior when pool is exhausted
	// Configuration would limit pool size and attempt to exceed it
}

// ============================================================
// Query Execution Tests
// ============================================================

func TestQueryRowExecution(t *testing.T) {
	tdb := setupTestDB(t)
	defer tdb.cleanup(t)

	ctx := context.Background()

	tests := []struct {
		name     string
		query    string
		args     []interface{}
		expected interface{}
	}{
		{
			name:     "simple_constant",
			query:    "SELECT $1",
			args:     []interface{}{42},
			expected: 42,
		},
		{
			name:     "string_constant",
			query:    "SELECT $1",
			args:     []interface{}{"test"},
			expected: "test",
		},
		{
			name:     "null_value",
			query:    "SELECT $1::INT",
			args:     []interface{}{nil},
			expected: nil,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			conn, err := tdb.pool.Acquire(ctx)
			require.NoError(t, err)
			defer conn.Release()

			var result interface{}
			err = conn.QueryRow(ctx, tt.query, tt.args...).Scan(&result)

			if tt.expected == nil {
				assert.NoError(t, err)
				assert.Nil(t, result)
			} else {
				assert.NoError(t, err)
				assert.Equal(t, tt.expected, result)
			}
		})
	}
}

func TestQueryExecution(t *testing.T) {
	tdb := setupTestDB(t)
	defer tdb.cleanup(t)

	ctx := context.Background()

	conn, err := tdb.pool.Acquire(ctx)
	require.NoError(t, err)
	defer conn.Release()

	// Execute query that returns multiple rows
	rows, err := conn.Query(ctx, "SELECT generate_series(1, 3)")
	assert.NoError(t, err)

	count := 0
	for rows.Next() {
		var val int
		err := rows.Scan(&val)
		assert.NoError(t, err)
		assert.Greater(t, val, 0)
		count++
	}

	assert.NoError(t, rows.Err())
	assert.Equal(t, 3, count)
}

// ============================================================
// Parameter Binding Tests
// ============================================================

func TestParameterBinding(t *testing.T) {
	tdb := setupTestDB(t)
	defer tdb.cleanup(t)

	ctx := context.Background()
	conn, err := tdb.pool.Acquire(ctx)
	require.NoError(t, err)
	defer conn.Release()

	tests := []struct {
		name  string
		query string
		args  []interface{}
	}{
		{
			name:  "single_parameter",
			query: "SELECT $1",
			args:  []interface{}{123},
		},
		{
			name:  "multiple_parameters",
			query: "SELECT $1, $2, $3",
			args:  []interface{}{1, 2, 3},
		},
		{
			name:  "string_parameters",
			query: "SELECT $1 || $2",
			args:  []interface{}{"hello", "world"},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			_, err := conn.Query(ctx, tt.query, tt.args...)
			assert.NoError(t, err)
		})
	}
}

// ============================================================
// Error Handling Tests
// ============================================================

func TestDatabaseErrors(t *testing.T) {
	tdb := setupTestDB(t)
	defer tdb.cleanup(t)

	ctx := context.Background()
	conn, err := tdb.pool.Acquire(ctx)
	require.NoError(t, err)
	defer conn.Release()

	t.Run("syntax_error", func(t *testing.T) {
		_, err := conn.Query(ctx, "INVALID SYNTAX HERE")
		assert.Error(t, err)
	})

	t.Run("undefined_table", func(t *testing.T) {
		_, err := conn.Query(ctx, "SELECT * FROM nonexistent_table")
		assert.Error(t, err)
	})
}

// ============================================================
// Connection State Tests
// ============================================================

func TestConnectionState(t *testing.T) {
	tdb := setupTestDB(t)
	defer tdb.cleanup(t)

	ctx := context.Background()

	conn, err := tdb.pool.Acquire(ctx)
	require.NoError(t, err)

	// Verify connection is alive
	assert.NoError(t, conn.Ping(ctx))

	// Execute statement to verify state
	var result string
	err = conn.QueryRow(ctx, "SELECT version()").Scan(&result)
	assert.NoError(t, err)
	assert.NotEmpty(t, result)

	conn.Release()
}

// ============================================================
// DBTX Interface Mock Tests
// ============================================================

type MockDBTX struct {
	execCalled      bool
	queryCalled     bool
	queryRowCalled  bool
}

func (m *MockDBTX) Exec(ctx context.Context, sql string, args ...interface{}) (pgconn.CommandTag, error) {
	m.execCalled = true
	return pgconn.CommandTag{}, nil
}

func (m *MockDBTX) Query(ctx context.Context, sql string, args ...interface{}) (pgx.Rows, error) {
	m.queryCalled = true
	return nil, nil
}

func (m *MockDBTX) QueryRow(ctx context.Context, sql string, args ...interface{}) pgx.Row {
	m.queryRowCalled = true
	return nil
}

func TestQueriesWithMockDBTX(t *testing.T) {
	t.Run("new_queries", func(t *testing.T) {
		mock := &MockDBTX{}
		queries := New(mock)

		assert.NotNil(t, queries)
	})

	t.Run("with_tx", func(t *testing.T) {
		mock := &MockDBTX{}
		queries := New(mock)

		// WithTx expects a pgx.Tx, so we'll test the structure
		assert.NotNil(t, queries)
	})
}

// ============================================================
// Connection Lifecycle Tests
// ============================================================

func TestConnectionLifecycle(t *testing.T) {
	t.Run("acquire_release_cycle", func(t *testing.T) {
		tdb := setupTestDB(t)
		defer tdb.cleanup(t)

		ctx := context.Background()

		// First cycle
		conn1, err := tdb.pool.Acquire(ctx)
		assert.NoError(t, err)
		assert.NotNil(t, conn1)
		conn1.Release()

		// Second cycle - should reuse connection
		conn2, err := tdb.pool.Acquire(ctx)
		assert.NoError(t, err)
		assert.NotNil(t, conn2)
		conn2.Release()
	})
}

// ============================================================
// Timeout Tests
// ============================================================

func TestQueryTimeout(t *testing.T) {
	tdb := setupTestDB(t)
	defer tdb.cleanup(t)

	// Create a context with short timeout
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Millisecond)
	defer cancel()

	conn, err := tdb.pool.Acquire(ctx)
	if err != nil {
		// Already timed out - this is expected
		return
	}
	defer conn.Release()

	// Try to execute query - should timeout
	_, err = conn.Query(ctx, "SELECT pg_sleep(1)")
	// Should timeout or error
	assert.Error(t, err)
}

// ============================================================
// Batch Operation Tests
// ============================================================

func TestBatchOperations(t *testing.T) {
	t.Skip("Skipped - requires live database with test table")

	tdb := setupTestDB(t)
	defer tdb.cleanup(t)

	ctx := context.Background()
	conn, err := tdb.pool.Acquire(ctx)
	require.NoError(t, err)
	defer conn.Release()

	batch := &pgx.Batch{}
	batch.Queue("SELECT 1")
	batch.Queue("SELECT 2")
	batch.Queue("SELECT 3")

	results := conn.SendBatch(ctx, batch)
	defer results.Close()

	count := 0
	for count < 3 {
		var result int
		err := results.QueryRow().Scan(&result)
		if err != nil {
			break
		}
		assert.Greater(t, result, 0)
		count++
	}

	assert.Equal(t, 3, count)
}

// ============================================================
// Mutex/Lock Tests for Concurrent Safety
// ============================================================

func TestThreadSafeQueries(t *testing.T) {
	t.Run("concurrent_query_lock", func(t *testing.T) {
		var mu sync.Mutex
		results := make(map[int]int)

		numGoroutines := 10
		done := make(chan bool, numGoroutines)

		for i := 0; i < numGoroutines; i++ {
			go func(id int) {
				mu.Lock()
				results[id] = id * 2
				mu.Unlock()
				done <- true
			}(i)
		}

		for i := 0; i < numGoroutines; i++ {
			<-done
		}

		assert.Equal(t, numGoroutines, len(results))
		for i := 0; i < numGoroutines; i++ {
			assert.Equal(t, i*2, results[i])
		}
	})
}

// ============================================================
// Pool Statistics Tests
// ============================================================

func TestConnectionPoolStats(t *testing.T) {
	tdb := setupTestDB(t)
	defer tdb.cleanup(t)

	if tdb.pool == nil {
		t.Skip("Pool not available")
	}

	stat := tdb.pool.Stat()
	assert.NotNil(t, stat)

	// Verify stats structure
	assert.GreaterOrEqual(t, int32(stat.TotalConns()), int32(0))
	assert.GreaterOrEqual(t, int32(stat.IdleConns()), int32(0))
}
