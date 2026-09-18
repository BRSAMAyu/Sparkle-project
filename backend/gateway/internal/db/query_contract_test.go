package db

import (
	"os"
	"path/filepath"
	"regexp"
	"runtime"
	"strings"
	"testing"
)

func gatewayDBDir(t *testing.T) string {
	t.Helper()
	_, filename, _, ok := runtime.Caller(0)
	if !ok {
		t.Fatal("failed to resolve query_contract_test.go path")
	}
	return filepath.Dir(filename)
}

func readGatewayFile(t *testing.T, relative string) string {
	t.Helper()
	content, err := os.ReadFile(filepath.Join(gatewayDBDir(t), relative))
	if err != nil {
		t.Fatalf("read %s: %v", relative, err)
	}
	return string(content)
}

func requirePattern(t *testing.T, content string, pattern string, description string) {
	t.Helper()
	re := regexp.MustCompile(pattern)
	if !re.MatchString(content) {
		t.Fatalf("missing %s matching %q", description, pattern)
	}
}

func TestSchemaContainsCriticalTablesAndEnums(t *testing.T) {
	schema := readGatewayFile(t, "schema.sql")

	requiredPatterns := map[string]string{
		"users table":               `(?m)^CREATE TABLE (?:public\.)?users\s+\($`,
		"chat_messages table":       `(?m)^CREATE TABLE (?:public\.)?chat_messages\s+\($`,
		"chat_sessions table":       `(?m)^CREATE TABLE (?:public\.)?chat_sessions\s+\($`,
		"event_outbox table":        `(?m)^CREATE TABLE (?:public\.)?event_outbox\s+\($`,
		"event_store table":         `(?m)^CREATE TABLE (?:public\.)?event_store\s+\($`,
		"projection_metadata table": `(?m)^CREATE TABLE (?:public\.)?projection_metadata\s+\($`,
		"accountabilitystatus enum": `(?m)^CREATE TYPE (?:public\.)?accountabilitystatus AS ENUM\s+\($`,
	}

	for description, pattern := range requiredPatterns {
		requirePattern(t, schema, pattern, description)
	}
}

func TestQueryDefinitionsMatchGeneratedCriticalMethods(t *testing.T) {
	querySQL := readGatewayFile(t, "query.sql")
	generated := readGatewayFile(t, "query.sql.go")

	criticalQueries := []string{
		"GetUserByEmail",
		"CreateChatMessage",
		"GetChatHistory",
		"UpsertChatSession",
		"GetUnpublishedOutboxEntries",
		"GetEventsByAggregate",
		"GetProjectionMetadata",
	}

	for _, queryName := range criticalQueries {
		sqlPattern := `(?m)^-- name: ` + regexp.QuoteMeta(queryName) + ` :[a-z]+$`
		requirePattern(t, querySQL, sqlPattern, "query.sql marker for "+queryName)

		goPattern := `(?m)^func \(q \*Queries\) ` + regexp.QuoteMeta(queryName) + `\(`
		requirePattern(t, generated, goPattern, "generated method for "+queryName)
	}
}

func TestLuaScriptsMatchQuotaContract(t *testing.T) {
	// Live quota chain: usage metering scripts must exist and stay non-empty.
	liveScripts := []string{
		"scripts/record_usage.lua",
		"scripts/record_usage_segment.lua",
	}
	for _, scriptPath := range liveScripts {
		content := readGatewayFile(t, scriptPath)
		if strings.TrimSpace(content) == "" {
			t.Fatalf("%s should not be empty", scriptPath)
		}
	}

	// Deletion ratchet (R2-05 §4.1 option 1): the reserve/refund/decr family
	// was dead code — zero production callers and no initializer for its
	// user:quota:* keys. These scripts must stay deleted; reintroducing them
	// requires reviving this test consciously.
	deadScripts := []string{
		"scripts/decr_quota.lua",
		"scripts/reserve_quota.lua",
		"scripts/refund_quota.lua",
	}
	for _, scriptPath := range deadScripts {
		if _, err := os.Stat(filepath.Join(gatewayDBDir(t), scriptPath)); err == nil {
			t.Fatalf("%s must stay deleted (dead reserve/refund/decr family, R2-05 §4.1)", scriptPath)
		}
	}
}
