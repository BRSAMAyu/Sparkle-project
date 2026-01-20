package config

import (
	"log"
	neturl "net/url"
	"os"
	"path/filepath"
	"strconv"
	"strings"

	"github.com/spf13/viper"
)

type Config struct {
	Port               string  `mapstructure:"PORT"`
	DatabaseURL        string  `mapstructure:"DATABASE_URL"`
	PostgresHost       string  `mapstructure:"POSTGRES_HOST"`
	PostgresPort       int     `mapstructure:"POSTGRES_PORT"`
	PostgresUser       string  `mapstructure:"POSTGRES_USER"`
	PostgresPassword   string  `mapstructure:"POSTGRES_PASSWORD"`
	PostgresDB         string  `mapstructure:"POSTGRES_DB"`
	AgentAddress       string  `mapstructure:"AGENT_ADDRESS"`
	AgentTLSEnabled    bool    `mapstructure:"AGENT_TLS_ENABLED"`
	AgentTLSCACertPath string  `mapstructure:"AGENT_TLS_CA_CERT"`
	AgentTLSServerName string  `mapstructure:"AGENT_TLS_SERVER_NAME"`
	AgentTLSInsecure   bool    `mapstructure:"AGENT_TLS_INSECURE"`
	GRPCTimeoutSeconds int     `mapstructure:"GRPC_TIMEOUT_SECONDS"`
	JWTSecret          string  `mapstructure:"JWT_SECRET"`
	JWTIssuer          string  `mapstructure:"JWT_ISSUER"`
	JWTAudience        string  `mapstructure:"JWT_AUDIENCE"`
	AllowWsQueryToken  bool    `mapstructure:"ALLOW_WS_QUERY_TOKEN"`
	WSTicketTTLSeconds int     `mapstructure:"WS_TICKET_TTL_SECONDS"`
	WSTicketRateRPS    float64 `mapstructure:"WS_TICKET_RATE_RPS"`
	WSTicketRateBurst  int     `mapstructure:"WS_TICKET_RATE_BURST"`
	RedisURL           string  `mapstructure:"REDIS_URL"`
	RedisHost          string  `mapstructure:"REDIS_HOST"`
	RedisPort          int     `mapstructure:"REDIS_PORT"`
	RedisPassword      string  `mapstructure:"REDIS_PASSWORD"`
	BackendURL         string  `mapstructure:"BACKEND_URL"`
	AppleClientID      string  `mapstructure:"APPLE_CLIENT_ID"`
	AdminSecret        string  `mapstructure:"ADMIN_SECRET"`
	RabbitMQURL        string  `mapstructure:"RABBITMQ_URL"`
	InternalAPIKey     string  `mapstructure:"INTERNAL_API_KEY"`
	ChaosEnabled       bool    `mapstructure:"CHAOS_ENABLED"`
	ChaosAllowProd     bool    `mapstructure:"CHAOS_ALLOW_PROD"`
	ToxiproxyURL       string  `mapstructure:"TOXIPROXY_URL"`

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

	originURL, err := neturl.Parse(origin)
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

		allowedURL, err := neturl.Parse(allowed)
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

func isRunningInDocker() bool {
	if os.Getenv("IN_DOCKER") == "true" {
		return true
	}
	if _, err := os.Stat("/.dockerenv"); err == nil {
		return true
	}
	return false
}

func normalizeLocalDockerHost(host string) string {
	if isRunningInDocker() {
		return host
	}
	if host == "sparkle_db" || host == "sparkle_redis" {
		return "127.0.0.1"
	}
	return host
}

func normalizeDatabaseURL(raw string) string {
	if raw == "" {
		return ""
	}
	normalized := strings.TrimSpace(raw)
	if strings.HasPrefix(normalized, "postgresql+asyncpg://") {
		normalized = "postgresql://" + strings.TrimPrefix(normalized, "postgresql+asyncpg://")
	}
	if strings.HasPrefix(normalized, "postgresql+psycopg://") {
		normalized = "postgresql://" + strings.TrimPrefix(normalized, "postgresql+psycopg://")
	}
	if strings.HasPrefix(normalized, "postgresql+psycopg2://") {
		normalized = "postgresql://" + strings.TrimPrefix(normalized, "postgresql+psycopg2://")
	}
	if strings.HasPrefix(normalized, "postgres://") {
		normalized = "postgresql://" + strings.TrimPrefix(normalized, "postgres://")
	}
	parsed, err := neturl.Parse(normalized)
	if err != nil || parsed.Hostname() == "" {
		return normalized
	}
	host := normalizeLocalDockerHost(parsed.Hostname())
	if host == parsed.Hostname() {
		return normalized
	}
	parsed.Host = host
	if parsed.Port() != "" {
		parsed.Host = host + ":" + parsed.Port()
	}
	return parsed.String()
}

func normalizeRedisAddr(raw string) string {
	if raw == "" {
		return ""
	}
	trimmed := strings.TrimSpace(raw)
	if !strings.Contains(trimmed, "://") {
		return trimmed
	}
	parsed, err := neturl.Parse(trimmed)
	if err != nil || parsed.Host == "" {
		return trimmed
	}
	host := normalizeLocalDockerHost(parsed.Hostname())
	port := parsed.Port()
	if port != "" {
		return host + ":" + port
	}
	return host
}

func findEnvFileUpwards(startDir string, filename string) string {
	dir := startDir
	for i := 0; i < 8; i++ {
		candidate := filepath.Join(dir, filename)
		if _, err := os.Stat(candidate); err == nil {
			return candidate
		}
		parent := filepath.Dir(dir)
		if parent == dir {
			break
		}
		dir = parent
	}
	return ""
}

func Load() *Config {
	envKeys := []string{
		"PORT",
		"DATABASE_URL",
		"POSTGRES_HOST",
		"POSTGRES_PORT",
		"POSTGRES_USER",
		"POSTGRES_PASSWORD",
		"POSTGRES_DB",
		"AGENT_ADDRESS",
		"AGENT_TLS_ENABLED",
		"AGENT_TLS_CA_CERT",
		"AGENT_TLS_SERVER_NAME",
		"AGENT_TLS_INSECURE",
		"GRPC_TIMEOUT_SECONDS",
		"JWT_SECRET",
		"JWT_ISSUER",
		"JWT_AUDIENCE",
		"ALLOW_WS_QUERY_TOKEN",
		"WS_TICKET_TTL_SECONDS",
		"WS_TICKET_RATE_RPS",
		"WS_TICKET_RATE_BURST",
		"REDIS_URL",
		"REDIS_HOST",
		"REDIS_PORT",
		"REDIS_PASSWORD",
		"BACKEND_URL",
		"APPLE_CLIENT_ID",
		"ADMIN_SECRET",
		"RABBITMQ_URL",
		"INTERNAL_API_KEY",
		"CHAOS_ENABLED",
		"CHAOS_ALLOW_PROD",
		"TOXIPROXY_URL",
		"MINIO_ENDPOINT",
		"MINIO_ACCESS_KEY",
		"MINIO_SECRET_KEY",
		"MINIO_BUCKET",
		"MINIO_REGION",
		"MINIO_USE_SSL",
		"MINIO_AUTO_CREATE_BUCKET",
		"FILE_MAX_UPLOAD_SIZE",
		"FILE_PRESIGN_EXPIRES_SECONDS",
		"FILE_GC_INTERVAL_MINUTES",
		"FILE_GC_GRACE_HOURS",
		"FILE_GC_BATCH_SIZE",
		"ENVIRONMENT",
		"ALLOWED_ORIGINS",
		"CORS_ENABLED",
	}

	for _, key := range envKeys {
		if err := viper.BindEnv(key); err != nil {
			log.Printf("Failed to bind env key %s: %v", key, err)
		}
	}

	viper.SetDefault("PORT", "8080")
	viper.SetDefault("DATABASE_URL", "")
	viper.SetDefault("POSTGRES_HOST", "sparkle_db")
	viper.SetDefault("POSTGRES_PORT", 5432)
	viper.SetDefault("POSTGRES_USER", "postgres")
	viper.SetDefault("POSTGRES_PASSWORD", "change-me")
	viper.SetDefault("POSTGRES_DB", "sparkle")
	viper.SetDefault("AGENT_ADDRESS", "localhost:50051")
	viper.SetDefault("AGENT_TLS_ENABLED", false)
	viper.SetDefault("AGENT_TLS_CA_CERT", "")
	viper.SetDefault("AGENT_TLS_SERVER_NAME", "")
	viper.SetDefault("AGENT_TLS_INSECURE", false)
	viper.SetDefault("GRPC_TIMEOUT_SECONDS", 5)
	// JWT_SECRET has no default - must be set via environment variable or .env file
	viper.SetDefault("JWT_ISSUER", "")
	viper.SetDefault("JWT_AUDIENCE", "")
	viper.SetDefault("WS_TICKET_TTL_SECONDS", 120)
	viper.SetDefault("WS_TICKET_RATE_RPS", 2.0)
	viper.SetDefault("WS_TICKET_RATE_BURST", 5)
	viper.SetDefault("REDIS_URL", "")
	viper.SetDefault("REDIS_HOST", "sparkle_redis")
	viper.SetDefault("REDIS_PORT", 6379)
	viper.SetDefault("REDIS_PASSWORD", "change-me")
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

	// Read from .env files if they exist (root .env has priority)
	cwd, err := os.Getwd()
	if err == nil {
		rootEnv := findEnvFileUpwards(cwd, ".env")
		localEnv := filepath.Join(cwd, ".env")
		if rootEnv != "" && rootEnv != localEnv {
			if _, err := os.Stat(localEnv); err == nil {
				viper.SetConfigFile(localEnv)
				_ = viper.ReadInConfig()
			}
			viper.SetConfigFile(rootEnv)
			_ = viper.MergeInConfig()
		} else if _, err := os.Stat(localEnv); err == nil {
			viper.SetConfigFile(localEnv)
			_ = viper.ReadInConfig()
		}
	}

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

	if cfg.DatabaseURL == "" {
		host := normalizeLocalDockerHost(cfg.PostgresHost)
		cfg.DatabaseURL = "postgresql://" + cfg.PostgresUser + ":" + cfg.PostgresPassword + "@" + host + ":" + strconv.Itoa(cfg.PostgresPort) + "/" + cfg.PostgresDB
	}
	cfg.DatabaseURL = normalizeDatabaseURL(cfg.DatabaseURL)
	if cfg.RedisURL == "" {
		host := normalizeLocalDockerHost(cfg.RedisHost)
		cfg.RedisURL = host + ":" + strconv.Itoa(cfg.RedisPort)
	}
	cfg.RedisURL = normalizeRedisAddr(cfg.RedisURL)

	// Warn about default database password in non-development environments
	if !cfg.IsDevelopment() && strings.Contains(cfg.DatabaseURL, ":change-me@") {
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

	if !viper.IsSet("ALLOW_WS_QUERY_TOKEN") {
		cfg.AllowWsQueryToken = cfg.IsDevelopment()
	}

	return &cfg
}
