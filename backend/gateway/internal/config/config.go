package config

import (
	"log"
	"net/url"
	"strings"

	"github.com/spf13/viper"
)

type Config struct {
	Port               string `mapstructure:"PORT"`
	DatabaseURL        string `mapstructure:"DATABASE_URL"`
	AgentAddress       string `mapstructure:"AGENT_ADDRESS"`
	AgentTLSEnabled    bool   `mapstructure:"AGENT_TLS_ENABLED"`
	AgentTLSCACertPath string `mapstructure:"AGENT_TLS_CA_CERT"`
	AgentTLSServerName string `mapstructure:"AGENT_TLS_SERVER_NAME"`
	AgentTLSInsecure   bool   `mapstructure:"AGENT_TLS_INSECURE"`
	GRPCTimeoutSeconds int    `mapstructure:"GRPC_TIMEOUT_SECONDS"`
	JWTSecret          string `mapstructure:"JWT_SECRET"`
	RedisURL           string `mapstructure:"REDIS_URL"`
	RedisPassword      string `mapstructure:"REDIS_PASSWORD"`
	BackendURL         string `mapstructure:"BACKEND_URL"`
	AppleClientID      string `mapstructure:"APPLE_CLIENT_ID"`
	AdminSecret        string `mapstructure:"ADMIN_SECRET"`
	RabbitMQURL        string `mapstructure:"RABBITMQ_URL"`
	InternalAPIKey     string `mapstructure:"INTERNAL_API_KEY"`
	ChaosEnabled       bool   `mapstructure:"CHAOS_ENABLED"`
	ChaosAllowProd     bool   `mapstructure:"CHAOS_ALLOW_PROD"`
	ToxiproxyURL       string `mapstructure:"TOXIPROXY_URL"`

	// File storage (MinIO/S3)
	MinioEndpoint         string `mapstructure:"MINIO_ENDPOINT"`
	MinioAccessKey        string `mapstructure:"MINIO_ACCESS_KEY"`
	MinioSecretKey        string `mapstructure:"MINIO_SECRET_KEY"`
	MinioBucket           string `mapstructure:"MINIO_BUCKET"`
	MinioRegion           string `mapstructure:"MINIO_REGION"`
	MinioUseSSL           bool   `mapstructure:"MINIO_USE_SSL"`
	MinioAutoCreateBucket bool   `mapstructure:"MINIO_AUTO_CREATE_BUCKET"`

	FileMaxUploadSize         int64 `mapstructure:"FILE_MAX_UPLOAD_SIZE"`
	FilePresignExpiresSeconds int   `mapstructure:"FILE_PRESIGN_EXPIRES_SECONDS"`
	FileGCIntervalMinutes     int   `mapstructure:"FILE_GC_INTERVAL_MINUTES"`
	FileGCGraceHours          int   `mapstructure:"FILE_GC_GRACE_HOURS"`
	FileGCBatchSize           int   `mapstructure:"FILE_GC_BATCH_SIZE"`

	// P3: WebSocket security configuration
	Environment    string   `mapstructure:"ENVIRONMENT"`     // dev, staging, production
	AllowedOrigins []string `mapstructure:"ALLOWED_ORIGINS"` // Comma-separated list of allowed origins
	CORSEnabled    bool     `mapstructure:"CORS_ENABLED"`    // Enable CORS for WebSocket
}

// IsDevelopment returns true if running in development mode
func (c *Config) IsDevelopment() bool {
	return c.Environment == "" || c.Environment == "dev" || c.Environment == "development"
}

// IsProduction returns true if running in production mode
func (c *Config) IsProduction() bool {
	return c.Environment == "prod" || c.Environment == "production"
}

// IsOriginAllowed checks if the given origin is allowed for WebSocket connections
func (c *Config) IsOriginAllowed(origin string) bool {
	// In development mode, allow all origins
	if c.IsDevelopment() {
		return true
	}

	originURL, err := url.Parse(origin)
	if err != nil || originURL.Scheme == "" || originURL.Host == "" {
		return false
	}

	originScheme := strings.ToLower(originURL.Scheme)
	originHost := strings.ToLower(originURL.Hostname())
	originPort := originURL.Port()

	// Check against whitelist
	for _, allowed := range c.AllowedOrigins {
		allowed = strings.TrimSpace(allowed)
		if allowed == "" {
			continue
		}
		if allowed == "*" {
			return true
		}

		if strings.HasPrefix(allowed, "*.") {
			domain := strings.TrimPrefix(allowed, "*.")
			if matchWildcardHost(originHost, domain) {
				return true
			}
			continue
		}

		allowedURL, err := url.Parse(allowed)
		if err != nil || allowedURL.Scheme == "" || allowedURL.Host == "" {
			allowedHost := strings.ToLower(allowed)
			if originHost == allowedHost {
				return true
			}
			continue
		}

		if strings.ToLower(allowedURL.Scheme) != originScheme {
			continue
		}

		allowedHost := strings.ToLower(allowedURL.Hostname())
		allowedPort := allowedURL.Port()

		if strings.HasPrefix(allowedHost, "*.") {
			domain := strings.TrimPrefix(allowedHost, "*.")
			if !matchWildcardHost(originHost, domain) {
				continue
			}
		} else if allowedHost != originHost {
			continue
		}

		if allowedPort != originPort {
			continue
		}

		return true
	}
	return false
}

func matchWildcardHost(host string, domain string) bool {
	host = strings.ToLower(host)
	domain = strings.ToLower(domain)

	if host == domain {
		return false
	}
	return strings.HasSuffix(host, "."+domain)
}

func Load() *Config {
	viper.SetDefault("PORT", "8080")
	viper.SetDefault("DATABASE_URL", "postgres://postgres:password@localhost:5432/sparkle")
	viper.SetDefault("AGENT_ADDRESS", "localhost:50051")
	viper.SetDefault("AGENT_TLS_ENABLED", false)
	viper.SetDefault("AGENT_TLS_CA_CERT", "")
	viper.SetDefault("AGENT_TLS_SERVER_NAME", "")
	viper.SetDefault("AGENT_TLS_INSECURE", false)
	viper.SetDefault("GRPC_TIMEOUT_SECONDS", 5)
	// JWT_SECRET has no default - must be set via environment variable or .env file
	viper.SetDefault("REDIS_URL", "127.0.0.1:6379")
	viper.SetDefault("REDIS_PASSWORD", "")
	viper.SetDefault("BACKEND_URL", "http://localhost:8000")
	viper.SetDefault("APPLE_CLIENT_ID", "")
	viper.SetDefault("RABBITMQ_URL", "") // Default to empty (disabled)
	viper.SetDefault("INTERNAL_API_KEY", "")
	viper.SetDefault("CHAOS_ENABLED", false)
	viper.SetDefault("CHAOS_ALLOW_PROD", false)
	viper.SetDefault("TOXIPROXY_URL", "http://toxiproxy:8474")

	// File storage defaults
	viper.SetDefault("MINIO_ENDPOINT", "localhost:9000")
	viper.SetDefault("MINIO_ACCESS_KEY", "minioadmin")
	viper.SetDefault("MINIO_SECRET_KEY", "minioadmin")
	viper.SetDefault("MINIO_BUCKET", "sparkle-files")
	viper.SetDefault("MINIO_REGION", "")
	viper.SetDefault("MINIO_USE_SSL", false)
	viper.SetDefault("MINIO_AUTO_CREATE_BUCKET", true)

	viper.SetDefault("FILE_MAX_UPLOAD_SIZE", int64(52428800))
	viper.SetDefault("FILE_PRESIGN_EXPIRES_SECONDS", 420)
	viper.SetDefault("FILE_GC_INTERVAL_MINUTES", 60)
	viper.SetDefault("FILE_GC_GRACE_HOURS", 24)
	viper.SetDefault("FILE_GC_BATCH_SIZE", 200)

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

	// Validate ADMIN_SECRET is set in non-development environments
	if !cfg.IsDevelopment() && cfg.AdminSecret == "" {
		log.Fatal("ADMIN_SECRET must be set in non-development environments. Set via ADMIN_SECRET environment variable or .env file.")
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
