package service

import (
	"context"
	"encoding/binary"
	"fmt"
	"math"
	"strings"
	"time"

	"github.com/redis/go-redis/v9"
)

const defaultCacheTTL = 1 * time.Hour

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

func (s *SemanticCacheService) canonicalizeScope(scope string) string {
	clean := strings.TrimSpace(strings.ToLower(scope))
	if clean == "" {
		return "global"
	}
	clean = strings.ReplaceAll(clean, " ", "_")
	clean = strings.ReplaceAll(clean, ":", "_")
	clean = strings.ReplaceAll(clean, "|", "_")
	return clean
}

// SearchExact performs a precise text match using the canonicalized query
func (s *SemanticCacheService) SearchExact(ctx context.Context, scope, query string) (string, error) {
	key := fmt.Sprintf("cache:text:%s:%s", s.canonicalizeScope(scope), s.Canonicalize(query))
	val, err := s.rdb.Get(ctx, key).Result()
	if err == redis.Nil {
		legacyKey := "cache:text:" + s.Canonicalize(query)
		legacyVal, legacyErr := s.rdb.Get(ctx, legacyKey).Result()
		if legacyErr == redis.Nil {
			return "", nil
		}
		if legacyErr != nil {
			return "", legacyErr
		}
		return legacyVal, nil
	}
	if err != nil {
		return "", err
	}
	return val, nil
}

// SetExact stores the response for a precise text match
func (s *SemanticCacheService) SetExact(ctx context.Context, scope, query, response string) error {
	key := fmt.Sprintf("cache:text:%s:%s", s.canonicalizeScope(scope), s.Canonicalize(query))
	return s.rdb.Set(ctx, key, response, defaultCacheTTL).Err()
}

// Search performs a vector similarity search using Redis RediSearch
func (s *SemanticCacheService) Search(ctx context.Context, vector []float32, lang, role, model string) (string, error) {
	// Convert vector to bytes for Redis
	// Assuming 4 bytes per float32 (Little Endian is standard for most systems, but we should match Python's struct.pack)
	// For simplicity in this P2 implementation, we assume standard IEEE 754 layout.
	blob := make([]byte, len(vector)*4)
	for i, v := range vector {
		u := math.Float32bits(v)
		binary.LittleEndian.PutUint32(blob[i*4:], u)
	}

	// Construct K-NN query
	// FT.SEARCH idx:embeddings "*=>[KNN 1 @vector $blob AS score]" PARAMS 2 blob <bytes> RETURN 1 payload DIALECT 2
	cmd := s.rdb.Do(ctx,
		"FT.SEARCH",
		"idx:embeddings",
		"*=>[KNN 1 @vector $blob AS score]",
		"PARAMS", "2", "blob", blob,
		"RETURN", "1", "payload",
		"SORTBY", "score",
		"DIALECT", "2",
	)

	res, err := cmd.Result()
	if err != nil {
		return "", err
	}

	// Parse response: [total_results, key, [field, value, ...], ...]
	// With DIALECT 2: [total, key, [payload, value, score, value]]
	// The structure depends on the driver's parsing of the array.
	// go-redis usually returns []interface{}
	results, ok := res.([]interface{})
	if !ok || len(results) < 2 {
		return "", nil // No results
	}

	count := results[0].(int64)
	if count == 0 {
		return "", nil
	}

	// Get the first result's fields
	// results[1] is the key name
	// results[2] is the fields array (map or list depending on parsing)
	// Let's assume standard array of attribute-value pairs if not a map.
	// Note: checking type is safer.

	// In some go-redis versions/configurations, FT.SEARCH returns a complex structure.
	// We'll traverse carefully.
	if len(results) > 2 {
		fields, ok := results[2].([]interface{})
		if ok {
			for i := 0; i < len(fields); i += 2 {
				key, _ := fields[i].(string)
				if key == "payload" {
					val, _ := fields[i+1].(string)
					return val, nil
				}
			}
		}
	}

	return "", nil
}
