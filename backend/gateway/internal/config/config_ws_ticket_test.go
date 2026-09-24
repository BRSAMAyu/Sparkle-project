package config

import (
	"strings"
	"testing"

	"github.com/spf13/viper"
)

// WSQ-2（WS-TICKET-DESIGN §2.3/§3.3/§5-R2）默认口径：
// ?ticket= 独立闸门默认 true（生产也放行）；TTL 120s、上限 300s；
// 签发口 5rps/burst10（三端 x 6 连击 = 18/min，旧 burst5 会掐合法重连）。
func TestLoadWSTicketConfigDefaults(t *testing.T) {
	viper.Reset()
	// Load() 对缺失 JWT_SECRET 直接 Fatal；测试自带一份保持自包含。
	t.Setenv("JWT_SECRET", "ws-ticket-config-test-secret")

	cfg := Load()

	if !cfg.AllowWsQueryTicket {
		t.Fatalf("AllowWsQueryTicket default = false, want true (production-allowed)")
	}
	if cfg.WSTicketTTLSeconds != 120 {
		t.Fatalf("WSTicketTTLSeconds default = %d, want 120", cfg.WSTicketTTLSeconds)
	}
	if cfg.WSTicketTTLSecondsMax != 300 {
		t.Fatalf("WSTicketTTLSecondsMax default = %d, want 300", cfg.WSTicketTTLSecondsMax)
	}
	if cfg.WSTicketRateRPS != 5.0 {
		t.Fatalf("WSTicketRateRPS default = %v, want 5 (R2: 3-device reconnect storm)", cfg.WSTicketRateRPS)
	}
	if cfg.WSTicketRateBurst != 10 {
		t.Fatalf("WSTicketRateBurst default = %d, want 10", cfg.WSTicketRateBurst)
	}
	if err := wsTicketTTLExceedsMax(cfg.WSTicketTTLSeconds, cfg.WSTicketTTLSecondsMax); err != nil {
		t.Fatalf("default TTL must pass its own ceiling, got %v", err)
	}
}

// WSQ-2：env 覆盖全链生效（新键在 envKeys 绑定表内）。
func TestLoadWSTicketConfigEnvOverride(t *testing.T) {
	viper.Reset()
	t.Setenv("JWT_SECRET", "ws-ticket-config-test-secret")
	t.Setenv("ALLOW_WS_QUERY_TICKET", "false")
	t.Setenv("WS_TICKET_TTL_SECONDS", "480")
	t.Setenv("WS_TICKET_TTL_SECONDS_MAX", "600")
	t.Setenv("WS_TICKET_RATE_RPS", "8.5")
	t.Setenv("WS_TICKET_RATE_BURST", "21")

	cfg := Load()

	if cfg.AllowWsQueryTicket {
		t.Fatalf("AllowWsQueryTicket = true, want false (env override)")
	}
	if cfg.WSTicketTTLSeconds != 480 {
		t.Fatalf("WSTicketTTLSeconds = %d, want 480 (env override)", cfg.WSTicketTTLSeconds)
	}
	if cfg.WSTicketTTLSecondsMax != 600 {
		t.Fatalf("WSTicketTTLSecondsMax = %d, want 600 (env override)", cfg.WSTicketTTLSecondsMax)
	}
	if cfg.WSTicketRateRPS != 8.5 {
		t.Fatalf("WSTicketRateRPS = %v, want 8.5 (env override)", cfg.WSTicketRateRPS)
	}
	if cfg.WSTicketRateBurst != 21 {
		t.Fatalf("WSTicketRateBurst = %d, want 21 (env override)", cfg.WSTicketRateBurst)
	}
	if err := wsTicketTTLExceedsMax(cfg.WSTicketTTLSeconds, cfg.WSTicketTTLSecondsMax); err != nil {
		t.Fatalf("TTL 480 under raised ceiling 600 must pass, got %v", err)
	}
}

// TTL clamp 边界（§6.1-4）：==max 放行、>max 拒绝；3600 坏示范必须被钳；
// 报错信息同时带两个 env 名（运维可定位）。
func TestWSTicketTTLClampBoundary(t *testing.T) {
	if err := wsTicketTTLExceedsMax(120, 300); err != nil {
		t.Fatalf("TTL 120 under ceiling 300 must pass, got %v", err)
	}
	if err := wsTicketTTLExceedsMax(300, 300); err != nil {
		t.Fatalf("TTL == ceiling (300) must pass, got %v", err)
	}
	if err := wsTicketTTLExceedsMax(301, 300); err == nil {
		t.Fatalf("TTL ceiling+1 (301) must be rejected")
	}
	err := wsTicketTTLExceedsMax(3600, 300)
	if err == nil {
		t.Fatalf("the shipped 3600s bad example must be rejected by the clamp")
	}
	if !strings.Contains(err.Error(), "WS_TICKET_TTL_SECONDS=") ||
		!strings.Contains(err.Error(), "WS_TICKET_TTL_SECONDS_MAX=") {
		t.Fatalf("violation message must name both env vars, got %q", err.Error())
	}
}
