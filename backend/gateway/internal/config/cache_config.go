package config

import "time"

// CacheStrategy defines the cache strategy configuration for different layers
type CacheStrategy struct {
	// FlutterMemoryCache - UI state cache in Flutter
	FlutterMemoryCache FlutterMemoryCacheConfig `yaml:"flutter_memory_cache"`

	// GoRedisCache - Redis cache in Go Gateway
	GoRedisCache GoRedisCacheConfig `yaml:"go_redis_cache"`

	// PythonRedisCache - Redis cache in Python Engine
	PythonRedisCache PythonRedisCacheConfig `yaml:"python_redis_cache"`
}

// FlutterMemoryCacheConfig - Flutter memory cache configuration
type FlutterMemoryCacheConfig struct {
	// TTL for UI state cache
	TTL time.Duration `yaml:"ttl"`
}

// GoRedisCacheConfig - Go Redis cache configuration
type GoRedisCacheConfig struct {
	// ChatHistoryTTL - TTL for chat history cache
	ChatHistoryTTL time.Duration `yaml:"chat_history_ttl"`

	// SemanticCacheTTL - TTL for semantic cache
	SemanticCacheTTL time.Duration `yaml:"semantic_cache_ttl"`

	// UserContextTTL - TTL for user context cache
	UserContextTTL time.Duration `yaml:"user_context_ttl"`

	// ConnectionStateTTL - TTL for connection state cache
	ConnectionStateTTL time.Duration `yaml:"connection_state_ttl"`
}

// PythonRedisCacheConfig - Python Redis cache configuration
type PythonRedisCacheConfig struct {
	// LLMTTL - TTL for LLM cache
	LLMTTL time.Duration `yaml:"llm_ttl"`

	// ToolCacheTTL - TTL for tool cache
	ToolCacheTTL time.Duration `yaml:"tool_cache_ttl"`

	// FSMStateTTL - TTL for FSM state cache
	FSMStateTTL time.Duration `yaml:"fsm_state_ttl"`
}

// DefaultCacheStrategy returns the default cache strategy configuration
func DefaultCacheStrategy() CacheStrategy {
	return CacheStrategy{
		FlutterMemoryCache: FlutterMemoryCacheConfig{
			TTL: 5 * time.Minute, // UI state
		},
		GoRedisCache: GoRedisCacheConfig{
			ChatHistoryTTL:   30 * time.Minute, // Chat history
			SemanticCacheTTL: 1 * time.Hour,    // Semantic cache
			UserContextTTL:   1 * time.Hour,    // User context
			ConnectionStateTTL: 5 * time.Minute, // Connection state
		},
		PythonRedisCache: PythonRedisCacheConfig{
			LLMTTL:        1 * time.Hour,    // LLM cache
			ToolCacheTTL:  5 * time.Minute,  // Tool cache
			FSMStateTTL:   10 * time.Minute, // FSM state
		},
	}
}

// Validate validates the cache strategy configuration
func (cs *CacheStrategy) Validate() error {
	// Validate Flutter memory cache
	if cs.FlutterMemoryCache.TTL <= 0 {
		return nil // Use default
	}

	// Validate Go Redis cache
	if cs.GoRedisCache.ChatHistoryTTL <= 0 {
		return nil // Use default
	}
	if cs.GoRedisCache.SemanticCacheTTL <= 0 {
		return nil // Use default
	}
	if cs.GoRedisCache.UserContextTTL <= 0 {
		return nil // Use default
	}
	if cs.GoRedisCache.ConnectionStateTTL <= 0 {
		return nil // Use default
	}

	// Validate Python Redis cache
	if cs.PythonRedisCache.LLMTTL <= 0 {
		return nil // Use default
	}
	if cs.PythonRedisCache.ToolCacheTTL <= 0 {
		return nil // Use default
	}
	if cs.PythonRedisCache.FSMStateTTL <= 0 {
		return nil // Use default
	}

	return nil
}
