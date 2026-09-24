package config

import (
	"testing"

	"github.com/spf13/viper"
)

// WSQ-1（WS-TICKET-DESIGN §3.3）：兜底钉阈值默认 30rps/burst60。
func TestLoadWSUpgradeRateDefaults(t *testing.T) {
	viper.Reset()
	// Load() 对缺失 JWT_SECRET 直接 Fatal；worktree 内无 .env（不入库），
	// 测试自带一份以保持自包含。
	t.Setenv("JWT_SECRET", "ws-upgrade-rate-test-secret")

	cfg := Load()

	if cfg.WSUpgradeRateRPS != 30.0 {
		t.Fatalf("WSUpgradeRateRPS default = %v, want 30", cfg.WSUpgradeRateRPS)
	}
	if cfg.WSUpgradeRateBurst != 60 {
		t.Fatalf("WSUpgradeRateBurst default = %v, want 60", cfg.WSUpgradeRateBurst)
	}
}

// WSQ-1：env 覆盖生效（WS_UPGRADE_RATE_RPS / WS_UPGRADE_RATE_BURST）。
func TestLoadWSUpgradeRateEnvOverride(t *testing.T) {
	viper.Reset()
	t.Setenv("JWT_SECRET", "ws-upgrade-rate-test-secret")
	t.Setenv("WS_UPGRADE_RATE_RPS", "7.5")
	t.Setenv("WS_UPGRADE_RATE_BURST", "13")

	cfg := Load()

	if cfg.WSUpgradeRateRPS != 7.5 {
		t.Fatalf("WSUpgradeRateRPS = %v, want 7.5 (env override)", cfg.WSUpgradeRateRPS)
	}
	if cfg.WSUpgradeRateBurst != 13 {
		t.Fatalf("WSUpgradeRateBurst = %v, want 13 (env override)", cfg.WSUpgradeRateBurst)
	}
}
