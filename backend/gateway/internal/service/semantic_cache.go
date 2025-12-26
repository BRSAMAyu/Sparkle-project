package service

import (
	"context"
	"strings"

	"github.com/redis/go-redis/v9"
)

type SemanticCacheService struct {
	rdb *redis.Client
}

func NewSemanticCacheService(rdb *redis.Client) *SemanticCacheService {
	return &SemanticCacheService{rdb: rdb}
}

// Canonicalize normalizes user input to improve cache hit rate.
// "  Password Reset? " -> "password reset"
func (s *SemanticCacheService) Canonicalize(input string) string {
	sStr := strings.TrimSpace(strings.ToLower(input))
	sStr = strings.TrimRight(sStr, "?.!。？！")
	return sStr
}

// Search is a placeholder for future vector search implementation
func (s *SemanticCacheService) Search(ctx context.Context, vector []float32, lang, role, model string) (string, error) {
	// TODO: Implement FT.SEARCH logic
	// redis.call("FT.SEARCH", ...)
	return "", nil
}
