package service

import (
	"encoding/json"
	"sync"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// ============================================================
// FileEventHub Tests
// ============================================================

func TestNewFileEventHub(t *testing.T) {
	hub := NewFileEventHub()
	assert.NotNil(t, hub)
	assert.NotNil(t, hub.connections)
	assert.Equal(t, 0, len(hub.connections))
}

func TestFileEventHub_RegisterAndCount(t *testing.T) {
	hub := NewFileEventHub()

	assert.Equal(t, 0, hub.Count("user-1"))

	// Register a mock connection
	conn := &mockWSConn{}
	hub.Register("user-1", conn)
	assert.Equal(t, 1, hub.Count("user-1"))

	// Register another for same user
	conn2 := &mockWSConn{}
	hub.Register("user-1", conn2)
	assert.Equal(t, 2, hub.Count("user-1"))

	// Different user
	conn3 := &mockWSConn{}
	hub.Register("user-2", conn3)
	assert.Equal(t, 1, hub.Count("user-2"))
	assert.Equal(t, 2, hub.Count("user-1"))
}

func TestFileEventHub_RegisterMultipleSameConnection(t *testing.T) {
	hub := NewFileEventHub()
	conn := &mockWSConn{}

	hub.Register("user-1", conn)
	hub.Register("user-1", conn) // duplicate — map dedupes
	assert.Equal(t, 1, hub.Count("user-1"))
}

func TestFileEventHub_Unregister(t *testing.T) {
	hub := NewFileEventHub()
	conn := &mockWSConn{}
	conn2 := &mockWSConn{}

	hub.Register("user-1", conn)
	hub.Register("user-1", conn2)
	assert.Equal(t, 2, hub.Count("user-1"))

	hub.Unregister("user-1", conn)
	assert.Equal(t, 1, hub.Count("user-1"))

	// Unregister last connection — should remove user entry
	hub.Unregister("user-1", conn2)
	assert.Equal(t, 0, hub.Count("user-1"))
}

func TestFileEventHub_UnregisterNonexistent(t *testing.T) {
	hub := NewFileEventHub()
	conn := &mockWSConn{}

	// Should not panic
	assert.NotPanics(t, func() {
		hub.Unregister("nonexistent", conn)
	})
	assert.Equal(t, 0, hub.Count("nonexistent"))
}

func TestFileEventHub_UnregisterNonexistentConnection(t *testing.T) {
	hub := NewFileEventHub()
	conn1 := &mockWSConn{}
	conn2 := &mockWSConn{}

	hub.Register("user-1", conn1)
	hub.Unregister("user-1", conn2) // conn2 not registered
	assert.Equal(t, 1, hub.Count("user-1"))
}

func TestFileEventHub_Send(t *testing.T) {
	hub := NewFileEventHub()
	conn := &mockWSConn{}
	hub.Register("user-1", conn)

	hub.Send("user-1", map[string]string{"type": "test"})
	assert.Equal(t, 1, conn.writeCount())
}

func TestFileEventHub_SendToNoConnections(t *testing.T) {
	hub := NewFileEventHub()
	// Should not panic
	assert.NotPanics(t, func() {
		hub.Send("nonexistent", map[string]string{"type": "test"})
	})
}

func TestFileEventHub_SendRemovesFailingConnections(t *testing.T) {
	hub := NewFileEventHub()
	good := &mockWSConn{}
	bad := &mockWSConn{failWrite: true}

	hub.Register("user-1", good)
	hub.Register("user-1", bad)

	hub.Send("user-1", map[string]string{"type": "test"})

	assert.Equal(t, 1, good.writeCount())
	assert.Equal(t, 1, hub.Count("user-1"), "bad connection should be removed")
	assert.True(t, bad.isClosed())
}

func TestFileEventHub_ConcurrentRegisterUnregister(t *testing.T) {
	hub := NewFileEventHub()
	var wg sync.WaitGroup

	for i := 0; i < 50; i++ {
		conn := &mockWSConn{}
		wg.Add(2)
		go func(c *mockWSConn) {
			defer wg.Done()
			hub.Register("user-1", c)
		}(conn)
		go func(c *mockWSConn) {
			defer wg.Done()
			hub.Unregister("user-1", c)
		}(conn)
	}
	wg.Wait()
}

// ============================================================
// FileStatusEvent.normalize Tests
// ============================================================

func TestFileStatusEvent_Normalize_SyncProgress(t *testing.T) {
	tests := []struct {
		name              string
		event             FileStatusEvent
		expectedProgress  int
		expectedPercent   int
		expectedStatus    string
		expectedStage     string
	}{
		{
			name: "progress_syncs_to_percent",
			event: FileStatusEvent{Progress: 50, ProgressPercent: 0, Status: "processing"},
			expectedProgress: 50, expectedPercent: 50, expectedStatus: "extracting", expectedStage: "extracting",
		},
		{
			name: "percent_syncs_to_progress",
			event: FileStatusEvent{Progress: 0, ProgressPercent: 75, Status: "processing"},
			expectedProgress: 75, expectedPercent: 75, expectedStatus: "building_nodes", expectedStage: "building_nodes",
		},
		{
			name: "both_set_keeps_both",
			event: FileStatusEvent{Progress: 30, ProgressPercent: 30, Status: "processing"},
			expectedProgress: 30, expectedPercent: 30, expectedStatus: "embedding", expectedStage: "embedding",
		},
		{
			name: "processed_becomes_done",
			event: FileStatusEvent{Status: "processed"},
			expectedProgress: 0, expectedPercent: 0, expectedStatus: "done", expectedStage: "done",
		},
		{
			name: "failed_stays_failed",
			event: FileStatusEvent{Status: "failed", Error: "something went wrong"},
			expectedProgress: 0, expectedPercent: 0, expectedStatus: "failed", expectedStage: "failed",
		},
		{
			name: "uploading_stage_queued",
			event: FileStatusEvent{Status: "uploading"},
			expectedProgress: 0, expectedPercent: 0, expectedStatus: "queued", expectedStage: "queued",
		},
		{
			name: "uploaded_stage_queued",
			event: FileStatusEvent{Status: "uploaded"},
			expectedProgress: 0, expectedPercent: 0, expectedStatus: "queued", expectedStage: "queued",
		},
		{
			name: "queued_stage_queued",
			event: FileStatusEvent{Status: "queued"},
			expectedProgress: 0, expectedPercent: 0, expectedStatus: "queued", expectedStage: "queued",
		},
		{
			name: "done_stays_done",
			event: FileStatusEvent{Status: "done"},
			expectedProgress: 0, expectedPercent: 0, expectedStatus: "done", expectedStage: "done",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			tt.event.normalize()
			assert.Equal(t, tt.expectedProgress, tt.event.Progress)
			assert.Equal(t, tt.expectedPercent, tt.event.ProgressPercent)
			assert.Equal(t, tt.expectedStatus, tt.event.Status)
			assert.Equal(t, tt.expectedStage, tt.event.Stage)
		})
	}
}

func TestFileStatusEvent_Normalize_StageAlreadySet(t *testing.T) {
	event := FileStatusEvent{Stage: "custom_stage", Status: "processing", Progress: 50}
	event.normalize()
	// When stage is already set, it should keep it since normalize only sets if empty
	// But wait: the logic says if Stage == "" then set it. So if already set, it stays.
	assert.Equal(t, "custom_stage", event.Stage)
}

// ============================================================
// documentStage Tests
// ============================================================

func TestDocumentStage(t *testing.T) {
	tests := []struct {
		name     string
		status   string
		progress int
		expected string
	}{
		{"failed", "failed", 0, "failed"},
		{"processed", "processed", 0, "done"},
		{"done", "done", 0, "done"},
		{"uploading", "uploading", 0, "queued"},
		{"uploaded", "uploaded", 0, "queued"},
		{"queued", "queued", 0, "queued"},
		{"progress_10_extracting", "processing", 10, "extracting"},
		{"progress_24_extracting", "processing", 24, "extracting"},
		{"progress_25_embedding", "processing", 25, "embedding"},
		{"progress_50_embedding", "processing", 50, "embedding"},
		{"progress_69_embedding", "processing", 69, "embedding"},
		{"progress_70_building_nodes", "processing", 70, "building_nodes"},
		{"progress_100_building_nodes", "processing", 100, "building_nodes"},
		{"unknown_status_low_progress", "unknown", 5, "extracting"},
		{"unknown_status_mid_progress", "unknown", 40, "embedding"},
		{"unknown_status_high_progress", "unknown", 80, "building_nodes"},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			assert.Equal(t, tt.expected, documentStage(tt.status, tt.progress))
		})
	}
}

// ============================================================
// FileStatusEvent JSON Serialization Tests
// ============================================================

func TestFileStatusEvent_JSONRoundTrip(t *testing.T) {
	original := FileStatusEvent{
		Type:            "file_status",
		FileID:          "file-123",
		UserID:          "user-456",
		Status:          "done",
		Progress:        100,
		ProgressPercent: 100,
		NodesFound:      intPtr(42),
	}

	data, err := json.Marshal(original)
	require.NoError(t, err)

	var parsed FileStatusEvent
	err = json.Unmarshal(data, &parsed)
	require.NoError(t, err)

	assert.Equal(t, original.Type, parsed.Type)
	assert.Equal(t, original.FileID, parsed.FileID)
	assert.Equal(t, original.UserID, parsed.UserID)
	assert.Equal(t, original.Status, parsed.Status)
	assert.Equal(t, original.Progress, parsed.Progress)
	assert.Equal(t, original.ProgressPercent, parsed.ProgressPercent)
	assert.NotNil(t, parsed.NodesFound)
	assert.Equal(t, 42, *parsed.NodesFound)
}

func TestFileStatusEvent_OmitEmpty(t *testing.T) {
	event := FileStatusEvent{
		Type:   "file_status",
		FileID: "file-1",
		UserID: "user-1",
		Status: "queued",
	}

	data, err := json.Marshal(event)
	require.NoError(t, err)

	// Optional fields should be omitted
	assert.NotContains(t, string(data), `"stage"`)
	assert.NotContains(t, string(data), `"job_id"`)
	assert.NotContains(t, string(data), `"error"`)
	assert.NotContains(t, string(data), `"nodes_found"`)
}

// ============================================================
// FileProcessingRequest JSON Tests
// ============================================================

func TestFileProcessingRequest_JSONRoundTrip(t *testing.T) {
	req := FileProcessingRequest{
		FileID:             "file-abc",
		UserID:             "user-xyz",
		DownloadURL:        "https://storage.example.com/file",
		FileName:           "report.pdf",
		MimeType:           "application/pdf",
		ThumbnailUploadURL: "https://storage.example.com/thumb",
	}

	data, err := json.Marshal(req)
	require.NoError(t, err)

	var parsed FileProcessingRequest
	err = json.Unmarshal(data, &parsed)
	require.NoError(t, err)

	assert.Equal(t, req.FileID, parsed.FileID)
	assert.Equal(t, req.UserID, parsed.UserID)
	assert.Equal(t, req.DownloadURL, parsed.DownloadURL)
	assert.Equal(t, req.FileName, parsed.FileName)
	assert.Equal(t, req.MimeType, parsed.MimeType)
	assert.Equal(t, req.ThumbnailUploadURL, parsed.ThumbnailUploadURL)
}

// ============================================================
// FileProcessingClient Constructor Tests
// ============================================================

func TestNewFileProcessingClient(t *testing.T) {
	t.Run("trims_trailing_slash", func(t *testing.T) {
		c := NewFileProcessingClient("http://backend:8000/", "key")
		assert.Equal(t, "http://backend:8000", c.baseURL)
	})

	t.Run("no_trailing_slash", func(t *testing.T) {
		c := NewFileProcessingClient("http://backend:8000", "key")
		assert.Equal(t, "http://backend:8000", c.baseURL)
	})

	t.Run("empty_base_url", func(t *testing.T) {
		c := NewFileProcessingClient("", "key")
		assert.Equal(t, "", c.baseURL)
	})
}

func TestFileProcessingClient_TriggerProcessing_NilClient(t *testing.T) {
	var c *FileProcessingClient
	err := c.TriggerProcessing(nil, FileProcessingRequest{})
	assert.NoError(t, err, "nil client should return nil")
}

func TestFileProcessingClient_TriggerProcessing_EmptyBaseURL(t *testing.T) {
	c := NewFileProcessingClient("", "key")
	err := c.TriggerProcessing(nil, FileProcessingRequest{})
	assert.NoError(t, err, "empty base URL should return nil")
}

// ============================================================
// PostView / UserView JSON Tests
// ============================================================

func TestPostView_JSONRoundTrip(t *testing.T) {
	post := PostView{
		ID:        "post-1",
		UserID:    "user-1",
		Content:   "Hello world",
		ImageURLs: []string{"https://img.example.com/1.jpg"},
		Topic:     "general",
		LikeCount: 42,
		User: UserView{
			ID:        "user-1",
			Username:  "testuser",
			AvatarURL: "https://img.example.com/avatar.jpg",
		},
	}

	data, err := json.Marshal(post)
	require.NoError(t, err)

	var parsed PostView
	err = json.Unmarshal(data, &parsed)
	require.NoError(t, err)

	assert.Equal(t, post.ID, parsed.ID)
	assert.Equal(t, post.UserID, parsed.UserID)
	assert.Equal(t, post.Content, parsed.Content)
	assert.Equal(t, post.ImageURLs, parsed.ImageURLs)
	assert.Equal(t, post.Topic, parsed.Topic)
	assert.Equal(t, post.LikeCount, parsed.LikeCount)
	assert.Equal(t, post.User.ID, parsed.User.ID)
	assert.Equal(t, post.User.Username, parsed.User.Username)
}

// ============================================================
// FileStorageService parsePublicStorageURL Tests
// ============================================================

func TestParsePublicStorageURL(t *testing.T) {
	tests := []struct {
		name     string
		raw      string
		secure   bool
		wantNil  bool
		wantHost string
	}{
		{"empty_returns_nil", "", false, true, ""},
		{"whitespace_returns_nil", "   ", false, true, ""},
		{"http_url", "http://localhost:9000", false, false, "localhost:9000"},
		{"https_url", "https://storage.example.com", true, false, "storage.example.com"},
		{"no_scheme_insecure", "localhost:9000", false, false, "localhost:9000"},
		{"no_scheme_secure", "storage.example.com", true, false, "storage.example.com"},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			u, err := parsePublicStorageURL(tt.raw, tt.secure)
			if tt.wantNil {
				assert.Nil(t, u)
			} else {
				require.NoError(t, err)
				require.NotNil(t, u)
				assert.Equal(t, tt.wantHost, u.Host)
			}
		})
	}
}

// ============================================================
// FileStorageService rewritePresignedURL Tests (via struct)
// ============================================================

func TestRewritePresignedURL_Nil(t *testing.T) {
	s := &FileStorageService{}
	result := s.rewritePresignedURL(nil)
	assert.Equal(t, "", result)
}

// ============================================================
// StoredFile Struct Test
// ============================================================

func TestStoredFile_Fields(t *testing.T) {
	f := StoredFile{
		Status:     "uploading",
		Visibility: "private",
	}
	assert.Equal(t, "uploading", f.Status)
	assert.Equal(t, "private", f.Visibility)
}

// ============================================================
// UserContextData Struct Test
// ============================================================

func TestUserContextData_EmptyJSON(t *testing.T) {
	data := UserContextData{
		PendingTasks:   []TaskSummary{},
		ActivePlans:    []PlanSummary{},
		FocusStats:     FocusStatsSummary{},
		RecentProgress: []ProgressEvent{},
	}

	jsonData, err := json.Marshal(data)
	require.NoError(t, err)
	assert.Contains(t, string(jsonData), `"pending_tasks":[]`)
	assert.Contains(t, string(jsonData), `"active_plans":[]`)
}

// ============================================================
// UserContext Helper Function Tests
// ============================================================

func TestStringifyProfilePreference(t *testing.T) {
	tests := []struct {
		name    string
		value   interface{}
		want    string
		wantOK  bool
	}{
		{"nil", nil, "", false},
		{"empty_string", "", "", false},
		{"nonempty_string", "hello", "hello", true},
		{"bool_true", true, "true", true},
		{"bool_false", false, "false", true},
		{"float64", 3.14, "3.14", true},
		{"float32", float32(2.5), "2.50", true},
		{"int", 42, "42", true},
		{"int32", int32(7), "7", true},
		{"int64", int64(100), "100", true},
		{"string_slice", []string{"a", "b"}, `["a","b"]`, true},
		{"map_value", map[string]string{"k": "v"}, `{"k":"v"}`, true},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, ok := stringifyProfilePreference(tt.value)
			assert.Equal(t, tt.wantOK, ok)
			if tt.wantOK {
				assert.Equal(t, tt.want, got)
			}
		})
	}
}

func TestTimeToMillis(t *testing.T) {
	t.Run("nil_time", func(t *testing.T) {
		assert.Equal(t, int64(0), timeToMillis(nil))
	})

	t.Run("valid_time", func(t *testing.T) {
		now := time.Now()
		ms := timeToMillis(&now)
		assert.Greater(t, ms, int64(0))
		assert.Equal(t, now.UnixMilli(), ms)
	})
}

func TestFNV64Hex_Deterministic(t *testing.T) {
	lines := []string{"a", "b", "c"}
	h1 := fnv64Hex(lines)
	h2 := fnv64Hex(lines)
	assert.Equal(t, h1, h2, "FNV64 hex should be deterministic")
	assert.True(t, len(h1) > 0)
}

func TestFNV64Hex_OrderIndependent(t *testing.T) {
	// fnv64Hex sorts lines internally, so order shouldn't matter
	h1 := fnv64Hex([]string{"c", "a", "b"})
	h2 := fnv64Hex([]string{"a", "b", "c"})
	assert.Equal(t, h1, h2, "FNV64 hex should be order-independent due to sort")
}

func TestFNV64Hex_Empty(t *testing.T) {
	h := fnv64Hex([]string{})
	assert.True(t, len(h) > 0, "empty input should still produce a hash")
}

// ============================================================
// ChatUserProfileSnapshot Test
// ============================================================

func TestChatUserProfileSnapshot_Fields(t *testing.T) {
	snap := ChatUserProfileSnapshot{
		Nickname:    "Alice",
		Timezone:    "Asia/Shanghai",
		Language:    "zh-CN",
		IsPro:       true,
		Level:       5,
		AvatarURL:   "https://img.example.com/avatar.jpg",
		Preferences: map[string]string{"theme": "dark"},
	}
	assert.Equal(t, "Alice", snap.Nickname)
	assert.True(t, snap.IsPro)
	assert.Equal(t, "dark", snap.Preferences["theme"])
}

// ============================================================
// PreferencesUpdatedPayload JSON Test
// ============================================================

func TestPreferencesUpdatedPayload_JSONRoundTrip(t *testing.T) {
	payload := PreferencesUpdatedPayload{
		UserID:            "user-123",
		PreferenceVersion: 5,
		ChangedKeys:       []string{"timezone", "language"},
		UpdatedAt:         1700000000000,
		Source:            "explicit",
	}

	data, err := json.Marshal(payload)
	require.NoError(t, err)

	var parsed PreferencesUpdatedPayload
	err = json.Unmarshal(data, &parsed)
	require.NoError(t, err)

	assert.Equal(t, payload.UserID, parsed.UserID)
	assert.Equal(t, payload.PreferenceVersion, parsed.PreferenceVersion)
	assert.Equal(t, payload.ChangedKeys, parsed.ChangedKeys)
	assert.Equal(t, payload.Source, parsed.Source)
}

// ============================================================
// Helper types and functions
// ============================================================

type mockWSConn struct {
	mu        sync.Mutex
	writes    int
	closed    bool
	failWrite bool
}

func (c *mockWSConn) WriteJSON(v interface{}) error {
	c.mu.Lock()
	defer c.mu.Unlock()
	if c.failWrite {
		return errMockWrite
	}
	c.writes++
	return nil
}

func (c *mockWSConn) Close() error {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.closed = true
	return nil
}

func (c *mockWSConn) writeCount() int {
	c.mu.Lock()
	defer c.mu.Unlock()
	return c.writes
}

func (c *mockWSConn) isClosed() bool {
	c.mu.Lock()
	defer c.mu.Unlock()
	return c.closed
}

var errMockWrite = &writeError{}

type writeError struct{}

func (e *writeError) Error() string { return "mock write error" }

func intPtr(v int) *int {
	return &v
}
