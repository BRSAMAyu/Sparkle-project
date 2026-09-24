package config

import (
	"strings"
	"testing"

	"github.com/spf13/viper"
)

func TestLoadUsesGatewayDatabaseURLWhenRBACEnabled(t *testing.T) {
	viper.Reset()
	// Load() 对缺失 JWT_SECRET 直接 Fatal；worktree 内无 .env（不入库），
	// 测试自带一份以保持自包含（与 config_ws_upgrade_test.go 同一口径）。
	t.Setenv("JWT_SECRET", "rbac-test-jwt-secret")
	t.Setenv("SPARKLE_RBAC_ENABLED", "true")
	t.Setenv("DATABASE_URL", "postgresql://postgres:legacy@sparkle_db:5432/sparkle")
	t.Setenv("SPARKLE_GATEWAY_DATABASE_URL", "postgresql://sparkle_gateway:pw@sparkle_db:5432/sparkle?sslmode=require")

	cfg := Load()

	if !strings.Contains(cfg.DatabaseURL, "sparkle_gateway") {
		t.Fatalf("DatabaseURL = %q, want gateway role URL", cfg.DatabaseURL)
	}
	if !strings.Contains(cfg.DatabaseURL, "sslmode=require") {
		t.Fatalf("DatabaseURL = %q, want TLS sslmode", cfg.DatabaseURL)
	}
}

func TestLoadKeepsLegacyDatabaseURLWhenRBACDisabled(t *testing.T) {
	viper.Reset()
	t.Setenv("JWT_SECRET", "rbac-test-jwt-secret")
	t.Setenv("SPARKLE_RBAC_ENABLED", "false")
	t.Setenv("DATABASE_URL", "postgresql://postgres:legacy@sparkle_db:5432/sparkle")
	t.Setenv("SPARKLE_GATEWAY_DATABASE_URL", "postgresql://sparkle_gateway:pw@sparkle_db:5432/sparkle")

	cfg := Load()

	if !strings.Contains(cfg.DatabaseURL, "postgres:legacy") {
		t.Fatalf("DatabaseURL = %q, want legacy URL", cfg.DatabaseURL)
	}
}
