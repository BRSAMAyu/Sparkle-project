package handler

import (
	"sort"
	"strings"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// GAP-1: Tests for chat_orchestrator_chatflow.go core functions
// This file covers the deterministic helpers that underpin every chat message.

func TestSemanticCacheScopeIsDeterministic(t *testing.T) {
	scope1 := semanticCacheScope(
		"user-123", "standard", `{"lang":"zh"}`,
		[]string{"file-a", "file-b"}, true,
		[]string{"search", "plan"}, map[string]interface{}{"aurora_l1": "on"},
	)
	scope2 := semanticCacheScope(
		"user-123", "standard", `{"lang":"zh"}`,
		[]string{"file-b", "file-a"}, true, // file order reversed — must produce same scope
		[]string{"plan", "search"}, // tool order reversed — must produce same scope
		map[string]interface{}{"aurora_l1": "on"},
	)
	assert.Equal(t, scope1, scope2, "semanticCacheScope must be order-independent for files and tools")
}

func TestSemanticCacheScopeVariesByUser(t *testing.T) {
	scopeA := semanticCacheScope("user-A", "standard", "", nil, false, nil, nil)
	scopeB := semanticCacheScope("user-B", "standard", "", nil, false, nil, nil)
	assert.NotEqual(t, scopeA, scopeB)
}

func TestSemanticCacheScopeVariesByReferences(t *testing.T) {
	on := semanticCacheScope("u", "standard", "", nil, true, nil, nil)
	off := semanticCacheScope("u", "standard", "", nil, false, nil, nil)
	assert.NotEqual(t, on, off)
	assert.True(t, strings.HasSuffix(on, "refs_on"))
	assert.True(t, strings.HasSuffix(off, "refs_off"))
}

func TestSemanticCacheScopeContainsMode(t *testing.T) {
	scope := semanticCacheScope("u", "study_plan", "", nil, false, nil, nil)
	assert.Contains(t, scope, "mode:study_plan")
}

func TestDefaultUseDocumentContextForMode(t *testing.T) {
	assert.True(t, defaultUseDocumentContextForMode("study_plan"))
	assert.False(t, defaultUseDocumentContextForMode("standard"))
	assert.False(t, defaultUseDocumentContextForMode(""))
	assert.False(t, defaultUseDocumentContextForMode("deep_analysis"))
}

func TestShortHashIsStable(t *testing.T) {
	h1 := shortHash("a", "b", "c")
	h2 := shortHash("a", "b", "c")
	require.Equal(t, h1, h2, "shortHash must be deterministic")
	require.Len(t, h1, 12, "shortHash must return a 12-character hex prefix")
}

func TestShortHashDiffersForDifferentInputs(t *testing.T) {
	assert.NotEqual(t, shortHash("a"), shortHash("b"))
	assert.NotEqual(t, shortHash("a", "b"), shortHash("b", "a"))
}

func TestEnsureChatExtraContextInitializesNilMap(t *testing.T) {
	input := &chatInput{}
	ctx := ensureChatExtraContext(input)
	require.NotNil(t, ctx, "ensureChatExtraContext must initialize nil ExtraContext")
	assert.Same(t, input.ExtraContext, ctx, "must return the same map stored on input")
}

func TestEnsureChatExtraContextPreservesExisting(t *testing.T) {
	existing := map[string]interface{}{"key": "val"}
	input := &chatInput{ExtraContext: existing}
	ctx := ensureChatExtraContext(input)
	assert.Equal(t, "val", ctx["key"])
}

// Verify file-ordering does not affect the cache scope (property test over permutations).
func TestSemanticCacheScopeFileOrderInvariant(t *testing.T) {
	files := []string{"f3", "f1", "f2"}
	scope := semanticCacheScope("u", "standard", "", files, false, nil, nil)

	sorted := append([]string(nil), files...)
	sort.Strings(sorted)
	scopeSorted := semanticCacheScope("u", "standard", "", sorted, false, nil, nil)

	assert.Equal(t, scope, scopeSorted, "cache scope must not depend on file ordering")
}
