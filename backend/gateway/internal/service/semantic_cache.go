package service

import (
	"context"
	"encoding/binary"
	"fmt"
	"math"
	"strconv"
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
	if !ok {
		return "", fmt.Errorf("unexpected FT.SEARCH response type %T", res)
	}
	if len(results) == 0 {
		return "", fmt.Errorf("empty FT.SEARCH response")
	}

	count, err := redisSearchResultCount(results[0])
	if err != nil {
		return "", err
	}
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
	if len(results) < 3 {
		return "", fmt.Errorf("FT.SEARCH response missing fields for %d result(s)", count)
	}

	return redisSearchPayload(results[2])
}

func redisSearchResultCount(raw interface{}) (int64, error) {
	switch v := raw.(type) {
	case int64:
		return v, nil
	case int:
		return int64(v), nil
	case int32:
		return int64(v), nil
	case uint64:
		if v > math.MaxInt64 {
			return 0, fmt.Errorf("FT.SEARCH result count overflows int64: %d", v)
		}
		return int64(v), nil
	case string:
		count, err := strconv.ParseInt(v, 10, 64)
		if err != nil {
			return 0, fmt.Errorf("invalid FT.SEARCH result count %q: %w", v, err)
		}
		return count, nil
	default:
		return 0, fmt.Errorf("unexpected FT.SEARCH result count type %T", raw)
	}
}

func redisSearchPayload(raw interface{}) (string, error) {
	switch fields := raw.(type) {
	case []interface{}:
		if len(fields)%2 != 0 {
			return "", fmt.Errorf("malformed FT.SEARCH fields: odd field count %d", len(fields))
		}
		for i := 0; i < len(fields); i += 2 {
			key, ok := fields[i].(string)
			if !ok {
				return "", fmt.Errorf("unexpected FT.SEARCH field name type at index %d: %T", i, fields[i])
			}
			if key != "payload" {
				continue
			}
			val, ok := fields[i+1].(string)
			if !ok {
				return "", fmt.Errorf("unexpected FT.SEARCH payload type %T", fields[i+1])
			}
			return val, nil
		}
		return "", fmt.Errorf("FT.SEARCH result missing payload field")
	case map[string]interface{}:
		rawPayload, ok := fields["payload"]
		if !ok {
			return "", fmt.Errorf("FT.SEARCH result missing payload field")
		}
		payload, ok := rawPayload.(string)
		if !ok {
			return "", fmt.Errorf("unexpected FT.SEARCH payload type %T", rawPayload)
		}
		return payload, nil
	case nil:
		return "", fmt.Errorf("nil FT.SEARCH fields")
	default:
		return "", fmt.Errorf("unexpected FT.SEARCH fields type %T", raw)
	}
}
