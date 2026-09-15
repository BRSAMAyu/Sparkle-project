package config

import (
	"strings"
	"testing"

	"github.com/spf13/viper"
)

func TestLoadUsesGatewayDatabaseURLWhenRBACEnabled(t *testing.T) {
	viper.Reset()
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
	t.Setenv("SPARKLE_RBAC_ENABLED", "false")
	t.Setenv("DATABASE_URL", "postgresql://postgres:legacy@sparkle_db:5432/sparkle")
	t.Setenv("SPARKLE_GATEWAY_DATABASE_URL", "postgresql://sparkle_gateway:pw@sparkle_db:5432/sparkle")

	cfg := Load()

	if !strings.Contains(cfg.DatabaseURL, "postgres:legacy") {
		t.Fatalf("DatabaseURL = %q, want legacy URL", cfg.DatabaseURL)
	}
}
