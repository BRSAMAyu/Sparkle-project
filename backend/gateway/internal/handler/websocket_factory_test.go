package handler

import (
	"net/http/httptest"
	"testing"

	"github.com/sparkle/gateway/internal/config"
	"github.com/stretchr/testify/assert"
)

// TestNewWebSocketFactory tests WebSocketFactory creation
func TestNewWebSocketFactory(t *testing.T) {
	cfg := &config.Config{
		AllowedOrigins: []string{"https://example.com"},
	}

	factory := NewWebSocketFactory(cfg)

	assert.NotNil(t, factory)
	assert.Equal(t, cfg, factory.config)
}

// TestCreateUpgrader tests upgrader creation with proper buffer sizes
func TestCreateUpgrader(t *testing.T) {
	cfg := &config.Config{
		AllowedOrigins: []string{"https://example.com"},
	}

	factory := NewWebSocketFactory(cfg)
	upgrader := factory.CreateUpgrader()

	assert.Equal(t, 4096, upgrader.ReadBufferSize)
	assert.Equal(t, 4096, upgrader.WriteBufferSize)
	assert.NotNil(t, upgrader.CheckOrigin)
}

// TestCheckOrigin_NoOriginHeader tests allowing connections without origin header
func TestCheckOrigin_NoOriginHeader(t *testing.T) {
	cfg := &config.Config{
		AllowedOrigins: []string{"https://example.com"},
	}

	factory := NewWebSocketFactory(cfg)
	req := httptest.NewRequest("GET", "http://localhost:8080/ws", nil)
	// No Origin header set

	result := factory.checkOrigin(req)

	assert.True(t, result, "should allow request with no origin header (same-origin)")
}

// TestCheckOrigin_AllowedOrigin tests allowing whitelisted origin
func TestCheckOrigin_AllowedOrigin(t *testing.T) {
	cfg := &config.Config{
		AllowedOrigins: []string{"https://example.com", "https://app.example.com"},
	}

	factory := NewWebSocketFactory(cfg)
	req := httptest.NewRequest("GET", "http://localhost:8080/ws", nil)
	req.Header.Set("Origin", "https://example.com")

	result := factory.checkOrigin(req)

	assert.True(t, result, "should allow whitelisted origin")
}

// TestCheckOrigin_DeniedOrigin tests rejecting non-whitelisted origin in production
func TestCheckOrigin_DeniedOrigin(t *testing.T) {
	cfg := &config.Config{
		Environment:    "production",
		AllowedOrigins: []string{"https://example.com"},
	}

	factory := NewWebSocketFactory(cfg)
	req := httptest.NewRequest("GET", "http://localhost:8080/ws", nil)
	req.Header.Set("Origin", "https://malicious.com")

	result := factory.checkOrigin(req)

	assert.False(t, result, "should reject non-whitelisted origin in production")
}

// TestCheckOrigin_MultipleAllowedOrigins tests with multiple whitelisted origins
func TestCheckOrigin_MultipleAllowedOrigins(t *testing.T) {
	cfg := &config.Config{
		Environment: "production",
		AllowedOrigins: []string{
			"https://example.com",
			"https://app.example.com",
			"https://mobile.example.com",
		},
	}

	factory := NewWebSocketFactory(cfg)

	tests := []struct {
		origin  string
		allowed bool
	}{
		{"https://example.com", true},
		{"https://app.example.com", true},
		{"https://mobile.example.com", true},
		{"https://other.com", false},
		{"http://example.com", false}, // Different scheme
	}

	for _, tt := range tests {
		t.Run(tt.origin, func(t *testing.T) {
			req := httptest.NewRequest("GET", "http://localhost:8080/ws", nil)
			req.Header.Set("Origin", tt.origin)

			result := factory.checkOrigin(req)

			assert.Equal(t, tt.allowed, result)
		})
	}
}

// TestCheckOrigin_EmptyAllowedOrigins tests behavior with empty allowed origins list in production
func TestCheckOrigin_EmptyAllowedOrigins(t *testing.T) {
	cfg := &config.Config{
		Environment:    "production",
		AllowedOrigins: []string{},
	}

	factory := NewWebSocketFactory(cfg)
	req := httptest.NewRequest("GET", "http://localhost:8080/ws", nil)
	req.Header.Set("Origin", "https://example.com")

	result := factory.checkOrigin(req)

	assert.False(t, result, "should reject origin when no origins are whitelisted in production")
}

// TestCheckOrigin_CaseInsensitivity tests origin comparison is case-insensitive
func TestCheckOrigin_CaseInsensitivity(t *testing.T) {
	cfg := &config.Config{
		Environment:    "production",
		AllowedOrigins: []string{"https://example.com"},
	}

	factory := NewWebSocketFactory(cfg)

	tests := []struct {
		origin  string
		allowed bool
	}{
		{"https://example.com", true},
		{"https://Example.com", true}, // Case-insensitive match (EqualFold)
		{"https://EXAMPLE.COM", true}, // Case-insensitive match (EqualFold)
	}

	for _, tt := range tests {
		t.Run(tt.origin, func(t *testing.T) {
			req := httptest.NewRequest("GET", "http://localhost:8080/ws", nil)
			req.Header.Set("Origin", tt.origin)

			result := factory.checkOrigin(req)

			assert.Equal(t, tt.allowed, result)
		})
	}
}

// TestCheckOrigin_PortMattering tests that port is considered in origin
func TestCheckOrigin_PortMattering(t *testing.T) {
	cfg := &config.Config{
		Environment:    "production",
		AllowedOrigins: []string{"https://example.com:8080"},
	}

	factory := NewWebSocketFactory(cfg)

	tests := []struct {
		origin  string
		allowed bool
	}{
		{"https://example.com:8080", true},
		{"https://example.com", false},      // Different port (missing explicit port)
		{"https://example.com:9090", false}, // Different port number
	}

	for _, tt := range tests {
		t.Run(tt.origin, func(t *testing.T) {
			req := httptest.NewRequest("GET", "http://localhost:8080/ws", nil)
			req.Header.Set("Origin", tt.origin)

			result := factory.checkOrigin(req)

			assert.Equal(t, tt.allowed, result)
		})
	}
}

// TestDefaultUpgrader tests development-mode upgrader
func TestDefaultUpgrader(t *testing.T) {
	upgrader := DefaultUpgrader()

	assert.Equal(t, 1024, upgrader.ReadBufferSize)
	assert.Equal(t, 1024, upgrader.WriteBufferSize)
	assert.NotNil(t, upgrader.CheckOrigin)

	// Dev mode should allow any origin
	req := httptest.NewRequest("GET", "http://localhost:8080/ws", nil)
	req.Header.Set("Origin", "https://anyorigin.com")

	result := upgrader.CheckOrigin(req)
	assert.True(t, result, "dev mode should allow any origin")
}

// TestCheckOrigin_SpecialCharactersInOrigin tests origins with special characters
func TestCheckOrigin_SpecialCharactersInOrigin(t *testing.T) {
	cfg := &config.Config{
		Environment: "production",
		AllowedOrigins: []string{
			"https://sub-domain.example.com",
			"https://example-v2.com",
		},
	}

	factory := NewWebSocketFactory(cfg)

	tests := []struct {
		origin  string
		allowed bool
	}{
		{"https://sub-domain.example.com", true},
		{"https://example-v2.com", true},
		{"https://sub_domain.example.com", false},
	}

	for _, tt := range tests {
		t.Run(tt.origin, func(t *testing.T) {
			req := httptest.NewRequest("GET", "http://localhost:8080/ws", nil)
			req.Header.Set("Origin", tt.origin)

			result := factory.checkOrigin(req)

			assert.Equal(t, tt.allowed, result)
		})
	}
}

// TestCheckOrigin_SchemeMattering tests that scheme is part of origin validation
func TestCheckOrigin_SchemeMattering(t *testing.T) {
	cfg := &config.Config{
		Environment:    "production",
		AllowedOrigins: []string{"https://example.com"},
	}

	factory := NewWebSocketFactory(cfg)

	tests := []struct {
		origin  string
		allowed bool
	}{
		{"https://example.com", true},
		{"http://example.com", false}, // Different scheme
		{"ws://example.com", false},   // WebSocket scheme
		{"wss://example.com", false},  // Secure WebSocket scheme
	}

	for _, tt := range tests {
		t.Run(tt.origin, func(t *testing.T) {
			req := httptest.NewRequest("GET", "http://localhost:8080/ws", nil)
			req.Header.Set("Origin", tt.origin)

			result := factory.checkOrigin(req)

			assert.Equal(t, tt.allowed, result)
		})
	}
}

// TestCheckOrigin_WildcardDomain tests wildcard subdomain support
func TestCheckOrigin_WildcardDomain(t *testing.T) {
	cfg := &config.Config{
		Environment:    "production",
		AllowedOrigins: []string{"*.example.com", "https://example.com"}, // Added direct match for HasSuffix test
	}

	factory := NewWebSocketFactory(cfg)

	tests := []struct {
		origin  string
		allowed bool
	}{
		{"https://app.example.com", true},       // Matches *.example.com wildcard
		{"https://mobile.example.com", true},    // Matches *.example.com wildcard
		{"https://example.com", true},           // Direct match
		{"https://evil-example.com", false},     // Not a subdomain
		{"https://example.com.evil.com", false}, // Suffix injection attempt
		{"https://example.org", false},          // Different domain
	}

	for _, tt := range tests {
		t.Run(tt.origin, func(t *testing.T) {
			req := httptest.NewRequest("GET", "http://localhost:8080/ws", nil)
			req.Header.Set("Origin", tt.origin)

			result := factory.checkOrigin(req)

			assert.Equal(t, tt.allowed, result)
		})
	}
}

// TestCheckOrigin_WildcardOriginInProduction tests that allow-all wildcard is
// ignored in production. Production deployments must use explicit origins.
func TestCheckOrigin_WildcardOriginInProduction(t *testing.T) {
	cfg := &config.Config{
		Environment:    "production",
		AllowedOrigins: []string{"*"},
	}

	factory := NewWebSocketFactory(cfg)

	tests := []string{
		"https://example.com",
		"https://any-domain.com",
		"http://localhost:3000",
		"https://malicious.com",
	}

	for _, origin := range tests {
		t.Run(origin, func(t *testing.T) {
			req := httptest.NewRequest("GET", "http://localhost:8080/ws", nil)
			req.Header.Set("Origin", origin)

			result := factory.checkOrigin(req)

			assert.False(t, result, "production should reject wildcard origins")
		})
	}
}

// TestCheckOrigin_WildcardOriginInDevelopment tests allow-all wildcard support
// for local development only.
func TestCheckOrigin_WildcardOriginInDevelopment(t *testing.T) {
	cfg := &config.Config{
		Environment:    "development",
		AllowedOrigins: []string{"*"},
	}

	factory := NewWebSocketFactory(cfg)

	tests := []string{
		"https://example.com",
		"https://any-domain.com",
		"http://localhost:3000",
		"https://malicious.com",
	}

	for _, origin := range tests {
		t.Run(origin, func(t *testing.T) {
			req := httptest.NewRequest("GET", "http://localhost:8080/ws", nil)
			req.Header.Set("Origin", origin)

			result := factory.checkOrigin(req)

			assert.True(t, result, "development wildcard should allow any origin")
		})
	}
}

// TestCheckOrigin_DevelopmentMode tests development mode allows local origins by default.
func TestCheckOrigin_DevelopmentMode(t *testing.T) {
	cfg := &config.Config{
		Environment:    "dev",
		AllowedOrigins: []string{},
	}

	factory := NewWebSocketFactory(cfg)

	allowed := []string{
		"http://localhost:3000",
		"http://127.0.0.1:8080",
	}
	denied := []string{
		"https://example.com",
		"https://malicious.com",
	}

	for _, origin := range allowed {
		t.Run("allow_"+origin, func(t *testing.T) {
			req := httptest.NewRequest("GET", "http://localhost:8080/ws", nil)
			req.Header.Set("Origin", origin)

			result := factory.checkOrigin(req)

			assert.True(t, result, "development mode should allow local origins")
		})
	}

	for _, origin := range denied {
		t.Run("deny_"+origin, func(t *testing.T) {
			req := httptest.NewRequest("GET", "http://localhost:8080/ws", nil)
			req.Header.Set("Origin", origin)

			result := factory.checkOrigin(req)

			assert.False(t, result, "development mode should reject arbitrary cross-site origins")
		})
	}
}
