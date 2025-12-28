package config

import (
	"log"
	"strings"

	"github.com/spf13/viper"
)

type Config struct {
	Port          string `mapstructure:"PORT"`
	DatabaseURL   string `mapstructure:"DATABASE_URL"`
	AgentAddress  string `mapstructure:"AGENT_ADDRESS"`
	AgentTLSEnabled bool   `mapstructure:"AGENT_TLS_ENABLED"`
	AgentTLSCACertPath string `mapstructure:"AGENT_TLS_CA_CERT"`
	AgentTLSServerName string `mapstructure:"AGENT_TLS_SERVER_NAME"`
	AgentTLSInsecure bool `mapstructure:"AGENT_TLS_INSECURE"`
	JWTSecret     string `mapstructure:"JWT_SECRET"`
	RedisURL      string `mapstructure:"REDIS_URL"`
	RedisPassword string `mapstructure:"REDIS_PASSWORD"`
	BackendURL    string `mapstructure:"BACKEND_URL"`
	AppleClientID string `mapstructure:"APPLE_CLIENT_ID"`

	// P3: WebSocket security configuration
	Environment     string   `mapstructure:"ENVIRONMENT"`          // dev, staging, production
	AllowedOrigins  []string `mapstructure:"ALLOWED_ORIGINS"`      // Comma-separated list of allowed origins
	CORSEnabled     bool     `mapstructure:"CORS_ENABLED"`         // Enable CORS for WebSocket
}

// IsDevelopment returns true if running in development mode
func (c *Config) IsDevelopment() bool {
	return c.Environment == "" || c.Environment == "dev" || c.Environment == "development"
}

// IsOriginAllowed checks if the given origin is allowed for WebSocket connections
func (c *Config) IsOriginAllowed(origin string) bool {
	// In development mode, allow all origins
	if c.IsDevelopment() {
		return true
	}

	// Check against whitelist
	for _, allowed := range c.AllowedOrigins {
		if allowed == "*" {
			return true
		}
		if strings.EqualFold(allowed, origin) {
			return true
		}
		// Support wildcard subdomains (e.g., *.example.com)
		if strings.HasPrefix(allowed, "*.") {
			domain := strings.TrimPrefix(allowed, "*.")
			if strings.HasSuffix(origin, domain) {
				return true
			}
		}
	}
	return false
}

func Load() *Config {
	viper.SetDefault("PORT", "8080")
	viper.SetDefault("DATABASE_URL", "postgres://postgres:password@localhost:5432/sparkle")
	viper.SetDefault("AGENT_ADDRESS", "localhost:50051")
	viper.SetDefault("AGENT_TLS_ENABLED", false)
	viper.SetDefault("AGENT_TLS_CA_CERT", "")
	viper.SetDefault("AGENT_TLS_SERVER_NAME", "")
	viper.SetDefault("AGENT_TLS_INSECURE", false)
	// JWT_SECRET has no default - must be set via environment variable or .env file
	viper.SetDefault("REDIS_URL", "127.0.0.1:6379")
	viper.SetDefault("REDIS_PASSWORD", "")
	viper.SetDefault("BACKEND_URL", "http://localhost:8000")
	viper.SetDefault("APPLE_CLIENT_ID", "")

	// P3: Security defaults
	viper.SetDefault("ENVIRONMENT", "dev")
	viper.SetDefault("ALLOWED_ORIGINS", "https://sparkle.app,https://api.sparkle.app")
	viper.SetDefault("CORS_ENABLED", true)

	// Read from .env file if it exists
	viper.SetConfigFile(".env")
	viper.ReadInConfig() // Ignore error if file not found

	viper.AutomaticEnv()

	var cfg Config
	if err := viper.Unmarshal(&cfg); err != nil {
		log.Fatalf("Failed to load config: %v", err)
	}

	// Validate JWT_SECRET is set in non-development environments
	if !cfg.IsDevelopment() && cfg.JWTSecret == "" {
		log.Fatal("JWT_SECRET must be set in non-development environments. Set via JWT_SECRET environment variable or .env file.")
	}

	// Warn about default database password in non-development environments
	if !cfg.IsDevelopment() && strings.Contains(cfg.DatabaseURL, ":password@") {
		log.Printf("[SECURITY WARNING] Using default database password in non-development environment. Set DATABASE_URL environment variable with secure credentials.")
	}

	// Parse comma-separated allowed origins
	originsStr := viper.GetString("ALLOWED_ORIGINS")
	if originsStr != "" {
		cfg.AllowedOrigins = strings.Split(originsStr, ",")
		for i := range cfg.AllowedOrigins {
			cfg.AllowedOrigins[i] = strings.TrimSpace(cfg.AllowedOrigins[i])
		}
	}

	return &cfg
}
