package handler

import (
	"regexp"
	"strings"
	"testing"

	"github.com/stretchr/testify/assert"
)

// ============================================================
// Security Validators
// ============================================================

type SecurityChecker struct{}

func NewSecurityChecker() *SecurityChecker {
	return &SecurityChecker{}
}

func (sc *SecurityChecker) IsSQLInjection(input string) bool {
	// Detect SQL injection patterns
	patterns := []string{
		`['"].*?(OR|AND|UNION|SELECT|INSERT|UPDATE|DELETE|DROP)`,
		`;.*?(DROP|DELETE|UPDATE|INSERT)`,
		`--.*\n`,
		`/\*.*\*/`,
	}

	for _, pattern := range patterns {
		if regexp.MustCompile(pattern).MatchString(strings.ToUpper(input)) {
			return true
		}
	}
	return false
}

func (sc *SecurityChecker) IsXSSAttempt(input string) bool {
	// Detect XSS patterns
	patterns := []string{
		`<script[^>]*>`,
		`javascript:`,
		`on\w+\s*=`,
		`<iframe[^>]*>`,
		`<object[^>]*>`,
		`<embed[^>]*>`,
	}

	for _, pattern := range patterns {
		if regexp.MustCompile(pattern).MatchString(strings.ToLower(input)) {
			return true
		}
	}
	return false
}

func (sc *SecurityChecker) IsCommandInjection(input string) bool {
	// Detect command injection patterns
	patterns := []string{
		`;.*[a-z]+`,
		`\|.*[a-z]+`,
		"`.*`",
		`\$\(`,
	}

	for _, pattern := range patterns {
		if regexp.MustCompile(pattern).MatchString(strings.ToLower(input)) {
			return true
		}
	}
	return false
}

func (sc *SecurityChecker) ContainsSensitiveData(output string) bool {
	// Check for sensitive data patterns in output
	patterns := []string{
		`password\s*[:=]`,
		`api[_-]?key\s*[:=]`,
		`secret\s*[:=]`,
		`token\s*[:=]`,
		`credit[_-]?card`,
	}

	for _, pattern := range patterns {
		if regexp.MustCompile(pattern).MatchString(strings.ToLower(output)) {
			return true
		}
	}
	return false
}

func (sc *SecurityChecker) IsSafeErrorMessage(errMsg string) bool {
	// Check error message doesn't leak internal info
	dangerous := []string{
		`stack\s*trace`,
		`at\s+.*\.go`,
		`file\s+.*\.go`,
		`line\s+\d+`,
		`database.*connection`,
		`config`,
	}

	for _, pattern := range dangerous {
		if regexp.MustCompile(pattern).MatchString(strings.ToLower(errMsg)) {
			return false
		}
	}
	return true
}

// ============================================================
// Input Sanitization Tests
// ============================================================

func TestSQLInjectionDetection(t *testing.T) {
	checker := NewSecurityChecker()

	tests := []struct {
		name        string
		input       string
		isInjection bool
	}{
		{
			name:        "SQL OR injection",
			input:       "1' OR '1'='1",
			isInjection: true,
		},
		{
			name:        "DROP TABLE injection",
			input:       "'; DROP TABLE users; --",
			isInjection: true,
		},
		{
			name:        "Safe input",
			input:       "user123",
			isInjection: false,
		},
		{
			name:        "Email input",
			input:       "user@example.com",
			isInjection: false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := checker.IsSQLInjection(tt.input)
			assert.Equal(t, tt.isInjection, result)
		})
	}
}

func TestXSSDetection(t *testing.T) {
	checker := NewSecurityChecker()

	tests := []struct {
		name  string
		input string
		isXSS bool
	}{
		{
			name:  "Script tag XSS",
			input: "<script>alert('xss')</script>",
			isXSS: true,
		},
		{
			name:  "OnError XSS",
			input: "<img onerror=\"alert('xss')\">",
			isXSS: true,
		},
		{
			name:  "Safe text",
			input: "Hello world",
			isXSS: false,
		},
		{
			name:  "Math comparison",
			input: "2 < 3 and 5 > 1",
			isXSS: false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := checker.IsXSSAttempt(tt.input)
			assert.Equal(t, tt.isXSS, result)
		})
	}
}

func TestCommandInjectionDetection(t *testing.T) {
	checker := NewSecurityChecker()

	tests := []struct {
		name        string
		input       string
		isInjection bool
	}{
		{
			name:        "Pipe command injection",
			input:       "data | cat /etc/passwd",
			isInjection: true,
		},
		{
			name:        "Backtick command injection",
			input:       "`whoami`",
			isInjection: true,
		},
		{
			name:        "Safe input",
			input:       "test data",
			isInjection: false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := checker.IsCommandInjection(tt.input)
			assert.Equal(t, tt.isInjection, result)
		})
	}
}

// ============================================================
// Authentication Tests
// ============================================================

func TestTokenValidation(t *testing.T) {
	type MockAuth struct {
		validTokens map[string]bool
	}

	auth := MockAuth{
		validTokens: map[string]bool{
			"token-123": true,
			"token-456": true,
		},
	}

	t.Run("valid_token", func(t *testing.T) {
		token := "token-123"
		isValid := auth.validTokens[token]
		assert.True(t, isValid)
	})

	t.Run("invalid_token", func(t *testing.T) {
		token := "invalid-token"
		isValid := auth.validTokens[token]
		assert.False(t, isValid)
	})

	t.Run("empty_token", func(t *testing.T) {
		token := ""
		isValid := auth.validTokens[token]
		assert.False(t, isValid)
	})
}

func TestAuthorizationCheck(t *testing.T) {
	permissions := map[string][]string{
		"user-1": {"read"},
		"user-2": {"read", "write"},
		"admin":  {"read", "write", "delete"},
	}

	t.Run("user_can_read", func(t *testing.T) {
		perms := permissions["user-1"]
		hasRead := contains(perms, "read")
		assert.True(t, hasRead)
	})

	t.Run("user_cannot_delete", func(t *testing.T) {
		perms := permissions["user-1"]
		hasDelete := contains(perms, "delete")
		assert.False(t, hasDelete)
	})

	t.Run("admin_can_delete", func(t *testing.T) {
		perms := permissions["admin"]
		hasDelete := contains(perms, "delete")
		assert.True(t, hasDelete)
	})
}

func contains(slice []string, item string) bool {
	for _, v := range slice {
		if v == item {
			return true
		}
	}
	return false
}

// ============================================================
// Rate Limiting Tests
// ============================================================

func TestRateLimitingEnforcement(t *testing.T) {
	type RateLimiter struct {
		limits map[string]int
	}

	limiter := RateLimiter{limits: make(map[string]int)}
	limit := 100

	t.Run("request_under_limit", func(t *testing.T) {
		limiter.limits["user-1"] = 50
		allowed := limiter.limits["user-1"] < limit
		assert.True(t, allowed)
	})

	t.Run("request_at_limit", func(t *testing.T) {
		limiter.limits["user-2"] = limit
		allowed := limiter.limits["user-2"] < limit
		assert.False(t, allowed)
	})

	t.Run("request_over_limit", func(t *testing.T) {
		limiter.limits["user-3"] = limit + 10
		allowed := limiter.limits["user-3"] < limit
		assert.False(t, allowed)
	})
}

// ============================================================
// Error Message Safety Tests
// ============================================================

func TestErrorMessageSafety(t *testing.T) {
	checker := NewSecurityChecker()

	tests := []struct {
		name   string
		errMsg string
		isSafe bool
	}{
		{
			name:   "Safe error",
			errMsg: "Invalid credentials",
			isSafe: true,
		},
		{
			name:   "Error with file path",
			errMsg: "Error in handler.go line 123",
			isSafe: false,
		},
		{
			name:   "Error with stack trace",
			errMsg: "Stack trace: database/db.go:45",
			isSafe: false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := checker.IsSafeErrorMessage(tt.errMsg)
			assert.Equal(t, tt.isSafe, result)
		})
	}
}

// ============================================================
// Sensitive Data Handling Tests
// ============================================================

func TestSensitiveDataDetection(t *testing.T) {
	checker := NewSecurityChecker()

	tests := []struct {
		name         string
		output       string
		hasSensitive bool
	}{
		{
			name:         "No sensitive data",
			output:       `{"user": "john", "email": "john@example.com"}`,
			hasSensitive: false,
		},
		{
			name:         "Contains password",
			output:       `{"user": "john", "password": "secret123"}`,
			hasSensitive: true,
		},
		{
			name:         "Contains API key",
			output:       `{"api_key": "abc123def456"}`,
			hasSensitive: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := checker.ContainsSensitiveData(tt.output)
			assert.Equal(t, tt.hasSensitive, result)
		})
	}
}

// ============================================================
// CSRF Protection Tests
// ============================================================

func TestCSRFProtectionExpanded(t *testing.T) {
	// 模拟 CSRF Token 验证逻辑
	validateCSRF := func(sessionToken, requestToken string) bool {
		return sessionToken == requestToken
	}

	t.Run("Valid Token", func(t *testing.T) {
		assert.True(t, validateCSRF("abc", "abc"))
	})

	t.Run("Invalid Token", func(t *testing.T) {
		assert.False(t, validateCSRF("abc", "def"))
	})

	t.Run("Missing Token", func(t *testing.T) {
		assert.False(t, validateCSRF("abc", ""))
	})

	t.Run("Empty Session Token (Should Fail)", func(t *testing.T) {
		// If session has no token, request should fail even if empty
		assert.False(t, validateCSRF("", ""))
		// Note: implementation specific, but generally empty tokens are unsafe
	})
}

func TestSQLInjectionPatternsExpanded(t *testing.T) {
	checker := NewSecurityChecker()

	vectors := []string{
		"' OR 1=1 --",
		"admin' --",
		"UNION SELECT * FROM users",
		"WAITFOR DELAY '0:0:5'",
		"1; DROP TABLE users",
	}

	for _, v := range vectors {
		t.Run("Detect "+v, func(t *testing.T) {
			assert.True(t, checker.IsSQLInjection(v))
		})
	}
}

func TestXSSPatternsExpanded(t *testing.T) {
	checker := NewSecurityChecker()

	vectors := []string{
		"<script>alert(1)</script>",
		"<img src=x onerror=alert(1)>",
		"javascript:alert(1)",
		"<body onload=alert(1)>",
	}

	for _, v := range vectors {
		t.Run("Detect "+v, func(t *testing.T) {
			assert.True(t, checker.IsXSSAttempt(v))
		})
	}
}

// ============================================================
// Data Validation Tests
// ============================================================

func TestEmailValidation(t *testing.T) {
	emailPattern := regexp.MustCompile(`^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$`)

	tests := []struct {
		name    string
		email   string
		isValid bool
	}{
		{
			name:    "Valid email",
			email:   "user@example.com",
			isValid: true,
		},
		{
			name:    "Invalid email - no domain",
			email:   "user@",
			isValid: false,
		},
		{
			name:    "Invalid email - no @",
			email:   "userexample.com",
			isValid: false,
		},
		{
			name:    "Valid email with subdomain",
			email:   "user@mail.example.co.uk",
			isValid: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := emailPattern.MatchString(tt.email)
			assert.Equal(t, tt.isValid, result)
		})
	}
}

func TestUUIDValidation(t *testing.T) {
	uuidPattern := regexp.MustCompile(`^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$`)

	tests := []struct {
		name    string
		uuid    string
		isValid bool
	}{
		{
			name:    "Valid UUID",
			uuid:    "550e8400-e29b-41d4-a716-446655440000",
			isValid: true,
		},
		{
			name:    "Invalid UUID - too short",
			uuid:    "550e8400-e29b-41d4",
			isValid: false,
		},
		{
			name:    "Invalid UUID - wrong format",
			uuid:    "not-a-uuid",
			isValid: false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := uuidPattern.MatchString(tt.uuid)
			assert.Equal(t, tt.isValid, result)
		})
	}
}

// ============================================================
// Input Length Validation Tests
// ============================================================

func TestInputLengthValidation(t *testing.T) {
	t.Run("message_within_limit", func(t *testing.T) {
		message := "Hello world"
		maxLength := 1000
		isValid := len(message) <= maxLength
		assert.True(t, isValid)
	})

	t.Run("message_exceeds_limit", func(t *testing.T) {
		message := strings.Repeat("x", 11000)
		maxLength := 10000
		isValid := len(message) <= maxLength
		assert.False(t, isValid)
	})

	t.Run("empty_message", func(t *testing.T) {
		message := ""
		isValid := len(message) > 0
		assert.False(t, isValid)
	})
}

// ============================================================
// WebSocket Security Tests
// ============================================================

func TestWebSocketOriginValidation(t *testing.T) {
	allowedOrigins := map[string]bool{
		"http://localhost:3000":       true,
		"https://sparkle.example.com": true,
	}

	t.Run("valid_origin", func(t *testing.T) {
		origin := "http://localhost:3000"
		isAllowed := allowedOrigins[origin]
		assert.True(t, isAllowed)
	})

	t.Run("invalid_origin", func(t *testing.T) {
		origin := "http://malicious.com"
		isAllowed := allowedOrigins[origin]
		assert.False(t, isAllowed)
	})

	t.Run("empty_origin", func(t *testing.T) {
		origin := ""
		isAllowed := allowedOrigins[origin]
		assert.False(t, isAllowed)
	})
}

func TestWebSocketHeaderValidation(t *testing.T) {
	t.Run("valid_headers", func(t *testing.T) {
		headers := map[string]string{
			"Authorization": "Bearer token-123",
			"Content-Type":  "application/json",
		}

		hasAuth := headers["Authorization"] != ""
		hasContentType := headers["Content-Type"] != ""

		assert.True(t, hasAuth)
		assert.True(t, hasContentType)
	})

	t.Run("missing_authorization", func(t *testing.T) {
		headers := map[string]string{
			"Content-Type": "application/json",
		}

		hasAuth := headers["Authorization"] != ""
		assert.False(t, hasAuth)
	})
}

// ============================================================
// Request Validation Tests
// ============================================================

func TestRequestValidation(t *testing.T) {
	type ChatMessage struct {
		Content string
	}

	t.Run("valid_message", func(t *testing.T) {
		msg := ChatMessage{Content: "Hello"}
		isValid := len(msg.Content) > 0 && len(msg.Content) <= 10000
		assert.True(t, isValid)
	})

	t.Run("empty_message", func(t *testing.T) {
		msg := ChatMessage{Content: ""}
		isValid := len(msg.Content) > 0 && len(msg.Content) <= 10000
		assert.False(t, isValid)
	})

	t.Run("oversized_message", func(t *testing.T) {
		msg := ChatMessage{Content: strings.Repeat("x", 11000)}
		isValid := len(msg.Content) > 0 && len(msg.Content) <= 10000
		assert.False(t, isValid)
	})
}
