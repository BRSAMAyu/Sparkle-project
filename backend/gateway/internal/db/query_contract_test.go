package db

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func readGatewayFile(t *testing.T, relative string) string {
	t.Helper()
	content, err := os.ReadFile(filepath.Join(relative))
	if err != nil {
		t.Fatalf("read %s: %v", relative, err)
	}
	return string(content)
}

func TestSchemaContainsCriticalTablesAndEnums(t *testing.T) {
	schema := readGatewayFile(t, "schema.sql")

	requiredFragments := []string{
		"CREATE TABLE users",
		"CREATE TABLE chat_messages",
		"CREATE TABLE chat_sessions",
		"CREATE TABLE event_outbox",
		"CREATE TABLE event_store",
		"CREATE TABLE projection_metadata",
		"CREATE TYPE accountabilitystatus AS ENUM",
	}

	for _, fragment := range requiredFragments {
		if !strings.Contains(schema, fragment) {
			t.Fatalf("schema.sql missing required fragment: %s", fragment)
		}
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
		sqlMarker := "-- name: " + queryName + " :"
		if !strings.Contains(querySQL, sqlMarker) {
			t.Fatalf("query.sql missing marker %s", sqlMarker)
		}
		goMarker := "func (q *Queries) " + queryName + "("
		if !strings.Contains(generated, goMarker) {
			t.Fatalf("query.sql.go missing generated method %s", goMarker)
		}
	}
}

func TestLuaScriptsExistForQuotaContract(t *testing.T) {
	scripts := []string{
		"scripts/decr_quota.lua",
		"scripts/record_usage.lua",
		"scripts/record_usage_segment.lua",
		"scripts/reserve_quota.lua",
	}

	for _, scriptPath := range scripts {
		content := readGatewayFile(t, scriptPath)
		if strings.TrimSpace(content) == "" {
			t.Fatalf("%s should not be empty", scriptPath)
		}
	}
}
