package service

import (
	"context"
	"testing"

	"github.com/alicebob/miniredis/v2"
	"github.com/redis/go-redis/v9"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// TestNewSemanticCacheService tests SemanticCacheService initialization
func TestNewSemanticCacheService(t *testing.T) {
	s := miniredis.NewMiniRedis()
	require.NoError(t, s.Start())
	defer s.Close()

	rdb := redis.NewClient(&redis.Options{Addr: s.Addr()})
	scs := NewSemanticCacheService(rdb)

	assert.NotNil(t, scs)
	assert.Equal(t, rdb, scs.rdb)
}

// TestCanonicalize tests the input canonicalization logic
func TestCanonicalize(t *testing.T) {
	s := miniredis.NewMiniRedis()
	require.NoError(t, s.Start())
	defer s.Close()

	rdb := redis.NewClient(&redis.Options{Addr: s.Addr()})
	scs := NewSemanticCacheService(rdb)

	tests := []struct {
		name     string
		input    string
		expected string
	}{
		{
			name:     "leading and trailing whitespace",
			input:    "  password reset  ",
			expected: "password reset",
		},
		{
			name:     "uppercase to lowercase",
			input:    "PASSWORD RESET",
			expected: "password reset",
		},
		{
			name:     "question mark suffix",
			input:    "Password Reset?",
			expected: "password reset",
		},
		{
			name:     "exclamation mark suffix",
			input:    "Password Reset!",
			expected: "password reset",
		},
		{
			name:     "period suffix",
			input:    "Password Reset.",
			expected: "password reset",
		},
		{
			name:     "chinese question mark",
			input:    "密码重置？",
			expected: "密码重置",
		},
		{
			name:     "chinese exclamation mark",
			input:    "密码重置！",
			expected: "密码重置",
		},
		{
			name:     "chinese period",
			input:    "密码重置。",
			expected: "密码重置",
		},
		{
			name:     "mixed punctuation",
			input:    "  Password Reset?  ",
			expected: "password reset",
		},
		{
			name:     "multiple trailing punctuation",
			input:    "Password Reset??",
			expected: "password reset",
		},
		{
			name:     "complex example",
			input:    "  How Do I Reset My Password?  ",
			expected: "how do i reset my password",
		},
		{
			name:     "empty string",
			input:    "",
			expected: "",
		},
		{
			name:     "only whitespace",
			input:    "   ",
			expected: "",
		},
		{
			name:     "only punctuation",
			input:    "???",
			expected: "",
		},
		{
			name:     "tabs and newlines",
			input:    "\t\n  password\n\t",
			expected: "password",
		},
		{
			name:     "no changes needed",
			input:    "password reset",
			expected: "password reset",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := scs.Canonicalize(tt.input)
			assert.Equal(t, tt.expected, result)
		})
	}
}

// TestCanonicalizeIdempotent tests that canonicalization is idempotent
func TestCanonicalizeIdempotent(t *testing.T) {
	s := miniredis.NewMiniRedis()
	require.NoError(t, s.Start())
	defer s.Close()

	rdb := redis.NewClient(&redis.Options{Addr: s.Addr()})
	scs := NewSemanticCacheService(rdb)

	inputs := []string{
		"  Password Reset?  ",
		"UPPERCASE QUERY",
		"Mixed Case Text",
		"special!punctuation.",
	}

	for _, input := range inputs {
		t.Run(input, func(t *testing.T) {
			first := scs.Canonicalize(input)
			second := scs.Canonicalize(first)
			assert.Equal(t, first, second, "canonicalization should be idempotent")
		})
	}
}

// TestCanonicalizeUnicodeHandling tests unicode character handling
func TestCanonicalizeUnicodeHandling(t *testing.T) {
	s := miniredis.NewMiniRedis()
	require.NoError(t, s.Start())
	defer s.Close()

	rdb := redis.NewClient(&redis.Options{Addr: s.Addr()})
	scs := NewSemanticCacheService(rdb)

	tests := []struct {
		name     string
		input    string
		expected string
	}{
		{
			name:     "japanese hiragana",
			input:    "パスワード リセット？",
			expected: "パスワード リセット",
		},
		{
			name:     "korean hangul",
			input:    "암호 재설정?",
			expected: "암호 재설정",
		},
		{
			name:     "emoji with punctuation",
			input:    "Help! 🆘?",
			expected: "help! 🆘",
		},
		{
			name:     "accented characters",
			input:    "Réinitialiser?",
			expected: "réinitialiser",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := scs.Canonicalize(tt.input)
			assert.Equal(t, tt.expected, result)
		})
	}
}

// TestCanonicalizeForCacheHits tests that similar inputs canonicalize to same output
func TestCanonicalizeForCacheHits(t *testing.T) {
	s := miniredis.NewMiniRedis()
	require.NoError(t, s.Start())
	defer s.Close()

	rdb := redis.NewClient(&redis.Options{Addr: s.Addr()})
	scs := NewSemanticCacheService(rdb)

	// These should all canonicalize to the same string (cache hit)
	queries := []string{
		"password reset",
		"Password Reset",
		"PASSWORD RESET",
		"  password reset  ",
		"password reset?",
		"PASSWORD RESET?",
		"  PASSWORD RESET?  ",
	}

	expected := scs.Canonicalize(queries[0])
	for _, query := range queries {
		result := scs.Canonicalize(query)
		assert.Equal(t, expected, result, "query should canonicalize to same value for cache hits")
	}
}

// TestSearchPlaceholder tests that Search method exists and handles placeholder behavior
func TestSearchPlaceholder(t *testing.T) {
	s := miniredis.NewMiniRedis()
	require.NoError(t, s.Start())
	defer s.Close()

	rdb := redis.NewClient(&redis.Options{Addr: s.Addr()})
	scs := NewSemanticCacheService(rdb)

	ctx := context.Background()
	vector := []float32{0.1, 0.2, 0.3}

	result, err := scs.Search(ctx, vector, "en", "user", "gpt-4")
	assert.NoError(t, err)
	assert.Equal(t, "", result)
}

// BenchmarkCanonicalize benchmarks canonicalization performance
func BenchmarkCanonicalize(b *testing.B) {
	s := miniredis.NewMiniRedis()
	s.Start()
	defer s.Close()

	rdb := redis.NewClient(&redis.Options{Addr: s.Addr()})
	scs := NewSemanticCacheService(rdb)

	input := "  How Do I Reset My Password?  "

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		scs.Canonicalize(input)
	}
}

// BenchmarkCanonicalizeWithUnicode benchmarks canonicalization with unicode
func BenchmarkCanonicalizeWithUnicode(b *testing.B) {
	s := miniredis.NewMiniRedis()
	s.Start()
	defer s.Close()

	rdb := redis.NewClient(&redis.Options{Addr: s.Addr()})
	scs := NewSemanticCacheService(rdb)

	input := "  密码重置？  "

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		scs.Canonicalize(input)
	}
}
