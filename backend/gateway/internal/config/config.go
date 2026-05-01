/*
Core: <cognitive|execution|bridge|infra>
Phase: <sense|clarify|plan|execute|reflect|reinforce|adapt|none>
Stage: <首次引入 Stage 号>
*/

package config

import (
	"bufio"
	"bytes"
	"log"
	"net"
	neturl "net/url"
	"os"
	"path/filepath"
	"strconv"
	"strings"

	"github.com/spf13/viper"
)

const (
	DefaultWSMessageRateRPS   = 10.0
	DefaultWSMessageRateBurst = 20
)

type Config struct {
	Port                        string   `mapstructure:"PORT"`
	DatabaseURL                 string   `mapstructure:"DATABASE_URL"`
	PostgresHost                string   `mapstructure:"POSTGRES_HOST"`
	PostgresPort                int      `mapstructure:"POSTGRES_PORT"`
	PostgresUser                string   `mapstructure:"POSTGRES_USER"`
	PostgresPassword            string   `mapstructure:"POSTGRES_PASSWORD"`
	PostgresDB                  string   `mapstructure:"POSTGRES_DB"`
	AgentAddress                string   `mapstructure:"AGENT_ADDRESS"`
	AgentTLSEnabled             bool     `mapstructure:"AGENT_TLS_ENABLED"`
	AgentTLSCACertPath          string   `mapstructure:"AGENT_TLS_CA_CERT"`
	AgentTLSServerName          string   `mapstructure:"AGENT_TLS_SERVER_NAME"`
	AgentTLSInsecure            bool     `mapstructure:"AGENT_TLS_INSECURE"`
	GRPCTimeoutSeconds          int      `mapstructure:"GRPC_TIMEOUT_SECONDS"`
	JWTSecret                   string   `mapstructure:"JWT_SECRET"`
	JWTIssuer                   string   `mapstructure:"JWT_ISSUER"`
	JWTAudience                 string   `mapstructure:"JWT_AUDIENCE"`
	JWTAccessTokenExpireMinutes int      `mapstructure:"JWT_ACCESS_TOKEN_EXPIRE_MINUTES"`
	JWTRefreshTokenExpireDays   int      `mapstructure:"JWT_REFRESH_TOKEN_EXPIRE_DAYS"`
	AllowWsQueryToken           bool     `mapstructure:"ALLOW_WS_QUERY_TOKEN"`
	WSTicketTTLSeconds          int      `mapstructure:"WS_TICKET_TTL_SECONDS"`
	WSTicketRateRPS             float64  `mapstructure:"WS_TICKET_RATE_RPS"`
	WSTicketRateBurst           int      `mapstructure:"WS_TICKET_RATE_BURST"`
	WSMaxMessageBytes           int64    `mapstructure:"WS_MAX_MESSAGE_BYTES"`
	WSMessageRateRPS            float64  `mapstructure:"WS_MESSAGE_RATE_RPS"`
	WSMessageRateBurst          int      `mapstructure:"WS_MESSAGE_RATE_BURST"`
	WSMaxConnections            int      `mapstructure:"WS_MAX_CONNECTIONS_PER_USER"`
	WSGlobalMaxConnections      int      `mapstructure:"WS_GLOBAL_MAX_CONNECTIONS"`
	StreamMaxConcurrent         int      `mapstructure:"STREAM_MAX_CONCURRENT"`
	RedisURL                    string   `mapstructure:"REDIS_URL"`
	RedisHost                   string   `mapstructure:"REDIS_HOST"`
	RedisPort                   int      `mapstructure:"REDIS_PORT"`
	RedisPassword               string   `mapstructure:"REDIS_PASSWORD"`
	RedisFailClosed             bool     `mapstructure:"REDIS_FAIL_CLOSED"` // Security: reject tokens on Redis failure
	BackendURL                  string   `mapstructure:"BACKEND_URL"`
	AppleClientID               string   `mapstructure:"APPLE_CLIENT_ID"`
	AdminSecret                 string   `mapstructure:"ADMIN_SECRET"`
	RabbitMQURL                 string   `mapstructure:"RABBITMQ_URL"`
	InternalAPIKey              string   `mapstructure:"INTERNAL_API_KEY"`
	InternalIPWhitelist         []string `mapstructure:"INTERNAL_IP_WHITELIST"`
	ChaosEnabled                bool     `mapstructure:"CHAOS_ENABLED"`
	ChaosAllowProd              bool     `mapstructure:"CHAOS_ALLOW_PROD"`
	ToxiproxyURL                string   `mapstructure:"TOXIPROXY_URL"`

	// File storage (MinIO/S3)
	MinioEndpoint         string `mapstructure:"MINIO_ENDPOINT"`
	MinioPublicEndpoint   string `mapstructure:"MINIO_PUBLIC_ENDPOINT"`
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
	TrustedProxies []string `mapstructure:"TRUSTED_PROXIES"` // Trusted reverse proxy IPs/CIDRs (production: set to LB IP)

	// Cache Strategy Configuration
	CacheStrategy CacheStrategy `mapstructure:"CACHE_STRATEGY"`

	// Health check and circuit breaker configuration
	AgentHealthCheckInterval int `mapstructure:"AGENT_HEALTH_CHECK_INTERVAL"` // seconds, default 10
	AgentHealthCheckTimeout  int `mapstructure:"AGENT_HEALTH_CHECK_TIMEOUT"`  // seconds, default 5
	CircuitBreakerThreshold  int `mapstructure:"CIRCUIT_BREAKER_THRESHOLD"`   // default 5

	// Graceful shutdown
	ShutdownTimeoutSeconds int `mapstructure:"SHUTDOWN_TIMEOUT_SECONDS"` // default 15

	// WebSocket lifecycle
	WSPongWaitSeconds     int `mapstructure:"WS_PONG_WAIT_SECONDS"`     // default 90
	WSPingIntervalSeconds int `mapstructure:"WS_PING_INTERVAL_SECONDS"` // default 30
	WSWriteWaitSeconds    int `mapstructure:"WS_WRITE_WAIT_SECONDS"`    // default 10
	WSIdleTimeoutSeconds  int `mapstructure:"WS_IDLE_TIMEOUT_SECONDS"`  // default 300

	// Request timeout
	RequestTimeoutSeconds int `mapstructure:"REQUEST_TIMEOUT_SECONDS"` // default 30
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
	originURL, err := neturl.Parse(origin)
	if err != nil || originURL.Scheme == "" || originURL.Host == "" {
		return false
	}

	originScheme := strings.ToLower(originURL.Scheme)
	originHost := strings.ToLower(originURL.Hostname())
	originPort := originURL.Port()

	// In development we still reject arbitrary cross-site origins, but allow
	// local hosts plus any explicit whitelist entries from config.
	if c.IsDevelopment() {
		switch originHost {
		case "localhost", "127.0.0.1", "::1":
			return true
		}
	}

	// Check against whitelist
	for _, allowed := range c.AllowedOrigins {
		allowed = strings.TrimSpace(allowed)
		if allowed == "" {
			continue
		}
		if allowed == "*" {
			if c.IsProduction() {
				// Wildcard origin is never allowed in production
				continue
			}
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

func isInsecureSecret(value string) bool {
	trimmed := strings.TrimSpace(value)
	if trimmed == "" {
		return true
	}
	insecure := map[string]struct{}{
		"dev-secret-key":                      {},
		"dev_secret_key_change_in_production": {},
		"change-me":                           {},
		"CHANGE_ME_IN_PRODUCTION":             {},
	}
	_, found := insecure[trimmed]
	return found
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
		host := trimmed
		port := ""
		if strings.Contains(trimmed, ":") {
			if parsedHost, parsedPort, err := net.SplitHostPort(trimmed); err == nil {
				host = parsedHost
				port = parsedPort
			} else {
				parts := strings.Split(trimmed, ":")
				if len(parts) == 2 {
					host = parts[0]
					port = parts[1]
				}
			}
		}
		host = normalizeLocalDockerHost(host)
		if port != "" {
			return host + ":" + port
		}
		return host
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
	found := ""
	for i := 0; i < 8; i++ {
		candidate := filepath.Join(dir, filename)
		if _, err := os.Stat(candidate); err == nil {
			found = candidate
		}
		parent := filepath.Dir(dir)
		if parent == dir {
			break
		}
		dir = parent
	}
	return found
}

func loadEnvFileIntoViper(path string) {
	content, err := os.ReadFile(path)
	if err != nil {
		return
	}

	scanner := bufio.NewScanner(bytes.NewReader(content))
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		if strings.HasPrefix(line, "export ") {
			line = strings.TrimSpace(strings.TrimPrefix(line, "export "))
		}
		parts := strings.SplitN(line, "=", 2)
		if len(parts) != 2 {
			continue
		}
		key := strings.TrimSpace(parts[0])
		val := strings.TrimSpace(parts[1])
		if key == "" {
			continue
		}
		if len(val) >= 2 {
			if (val[0] == '"' && val[len(val)-1] == '"') || (val[0] == '\'' && val[len(val)-1] == '\'') {
				val = val[1 : len(val)-1]
			}
		}
		viper.Set(key, val)
	}
}

func applyEnvironmentOverrides(keys []string) {
	for _, key := range keys {
		if val, ok := os.LookupEnv(key); ok {
			viper.Set(key, val)
		}
	}
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
		"JWT_ACCESS_TOKEN_EXPIRE_MINUTES",
		"JWT_REFRESH_TOKEN_EXPIRE_DAYS",
		"ALLOW_WS_QUERY_TOKEN",
		"WS_TICKET_TTL_SECONDS",
		"WS_TICKET_RATE_RPS",
		"WS_TICKET_RATE_BURST",
		"WS_MAX_MESSAGE_BYTES",
		"WS_MESSAGE_RATE_RPS",
		"WS_MESSAGE_RATE_BURST",
		"WS_MAX_CONNECTIONS_PER_USER",
		"WS_GLOBAL_MAX_CONNECTIONS",
		"REDIS_URL",
		"REDIS_HOST",
		"REDIS_PORT",
		"REDIS_PASSWORD",
		"REDIS_FAIL_CLOSED",
		"BACKEND_URL",
		"APPLE_CLIENT_ID",
		"ADMIN_SECRET",
		"RABBITMQ_URL",
		"INTERNAL_API_KEY",
		"INTERNAL_IP_WHITELIST",
		"CHAOS_ENABLED",
		"CHAOS_ALLOW_PROD",
		"TOXIPROXY_URL",
		"SHUTDOWN_TIMEOUT_SECONDS",
		"WS_PONG_WAIT_SECONDS",
		"WS_PING_INTERVAL_SECONDS",
		"WS_WRITE_WAIT_SECONDS",
		"WS_IDLE_TIMEOUT_SECONDS",
		"REQUEST_TIMEOUT_SECONDS",
		"MINIO_ENDPOINT",
		"MINIO_PUBLIC_ENDPOINT",
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
	viper.SetDefault("POSTGRES_PASSWORD", "")
	viper.SetDefault("POSTGRES_DB", "sparkle")
	viper.SetDefault("AGENT_ADDRESS", "localhost:50051")
	viper.SetDefault("AGENT_TLS_ENABLED", false)
	viper.SetDefault("AGENT_TLS_CA_CERT", "")
	viper.SetDefault("AGENT_TLS_SERVER_NAME", "")
	viper.SetDefault("AGENT_TLS_INSECURE", false)
	viper.SetDefault("GRPC_TIMEOUT_SECONDS", 180)
	// JWT_SECRET has no default - must be set via environment variable or .env file
	viper.SetDefault("JWT_ISSUER", "sparkle-gateway")
	viper.SetDefault("JWT_AUDIENCE", "sparkle-app")
	viper.SetDefault("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", 30) // 30 minutes for access token
	viper.SetDefault("JWT_REFRESH_TOKEN_EXPIRE_DAYS", 7)    // 7 days for refresh token
	viper.SetDefault("WS_TICKET_TTL_SECONDS", 120)
	viper.SetDefault("WS_TICKET_RATE_RPS", 2.0)
	viper.SetDefault("WS_TICKET_RATE_BURST", 5)
	viper.SetDefault("WS_MAX_MESSAGE_BYTES", int64(262144))
	viper.SetDefault("WS_MESSAGE_RATE_RPS", DefaultWSMessageRateRPS)
	viper.SetDefault("WS_MESSAGE_RATE_BURST", DefaultWSMessageRateBurst)
	viper.SetDefault("WS_MAX_CONNECTIONS_PER_USER", 2)
	viper.SetDefault("WS_GLOBAL_MAX_CONNECTIONS", 2000)
	viper.SetDefault("REDIS_URL", "")
	viper.SetDefault("REDIS_HOST", "sparkle_redis")
	viper.SetDefault("REDIS_PORT", 6379)
	viper.SetDefault("REDIS_PASSWORD", "")
	// Security: Fail-Closed mode for Redis - production should set to true
	// In development, defaults to false (Fail-Open) for easier debugging
	viper.SetDefault("REDIS_FAIL_CLOSED", false)
	viper.SetDefault("BACKEND_URL", "http://localhost:8000")
	viper.SetDefault("APPLE_CLIENT_ID", "")
	viper.SetDefault("RABBITMQ_URL", "") // Default to empty (disabled)
	viper.SetDefault("INTERNAL_API_KEY", "")
	viper.SetDefault("INTERNAL_IP_WHITELIST", "127.0.0.1/8,::1/128,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16,fc00::/7")
	viper.SetDefault("CHAOS_ENABLED", false)
	viper.SetDefault("CHAOS_ALLOW_PROD", false)
	viper.SetDefault("TOXIPROXY_URL", "http://toxiproxy:8474")

	// File storage defaults
	viper.SetDefault("MINIO_ENDPOINT", "localhost:9000")
	viper.SetDefault("MINIO_PUBLIC_ENDPOINT", "")
	viper.SetDefault("MINIO_ACCESS_KEY", "")
	viper.SetDefault("MINIO_SECRET_KEY", "")
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

	// Health check and circuit breaker defaults
	viper.SetDefault("AGENT_HEALTH_CHECK_INTERVAL", 10) // 10 seconds
	viper.SetDefault("AGENT_HEALTH_CHECK_TIMEOUT", 5)   // 5 seconds
	viper.SetDefault("CIRCUIT_BREAKER_THRESHOLD", 5)    // 5 failures to trip

	// Graceful shutdown
	viper.SetDefault("SHUTDOWN_TIMEOUT_SECONDS", 15)

	// WebSocket lifecycle
	viper.SetDefault("WS_PONG_WAIT_SECONDS", 90)
	viper.SetDefault("WS_PING_INTERVAL_SECONDS", 30)
	viper.SetDefault("WS_WRITE_WAIT_SECONDS", 10)
	viper.SetDefault("WS_IDLE_TIMEOUT_SECONDS", 300)

	// Request timeout
	viper.SetDefault("REQUEST_TIMEOUT_SECONDS", 30)

	// Circuit breaker advanced defaults (used by health_checker)
	viper.SetDefault("CIRCUIT_BREAKER_SUCCESS_THRESHOLD", 2)
	viper.SetDefault("CIRCUIT_BREAKER_TIMEOUT", 30)
	viper.SetDefault("CIRCUIT_BREAKER_HALF_OPEN_REQUESTS", 3)

	// Read from .env files if they exist (root .env has priority)
	cwd, err := os.Getwd()
	if err == nil {
		rootEnv := findEnvFileUpwards(cwd, ".env")
		localEnv := filepath.Join(cwd, ".env")
		if rootEnv != "" && rootEnv != localEnv {
			if _, err := os.Stat(localEnv); err == nil {
				loadEnvFileIntoViper(localEnv)
				viper.SetConfigFile(localEnv)
				_ = viper.ReadInConfig()
			}
			loadEnvFileIntoViper(rootEnv)
			viper.SetConfigFile(rootEnv)
			_ = viper.MergeInConfig()
		} else if _, err := os.Stat(localEnv); err == nil {
			loadEnvFileIntoViper(localEnv)
			viper.SetConfigFile(localEnv)
			_ = viper.ReadInConfig()
		}
	}

	viper.AutomaticEnv()
	applyEnvironmentOverrides(envKeys)

	var cfg Config
	if err := viper.Unmarshal(&cfg); err != nil {
		log.Fatalf("Failed to load config: %v", err)
	}

	// Validate JWT_SECRET is set in non-development environments
	if !cfg.IsDevelopment() && cfg.JWTSecret == "" {
		log.Fatal("JWT_SECRET must be set in non-development environments. Set via JWT_SECRET environment variable or .env file.")
	}
	if !cfg.IsDevelopment() && isInsecureSecret(cfg.JWTSecret) {
		log.Fatal("JWT_SECRET is using an insecure default. Set a high-entropy value via JWT_SECRET.")
	}

	// Validate ADMIN_SECRET is set in non-development environments
	if !cfg.IsDevelopment() && cfg.AdminSecret == "" {
		log.Fatal("ADMIN_SECRET must be set in non-development environments. Set via ADMIN_SECRET environment variable or .env file.")
	}
	if !cfg.IsDevelopment() && isInsecureSecret(cfg.AdminSecret) {
		log.Fatal("ADMIN_SECRET is using an insecure default. Set a high-entropy value via ADMIN_SECRET.")
	}
	if !cfg.IsDevelopment() && cfg.AgentTLSInsecure {
		log.Fatal("AGENT_TLS_INSECURE must be false in non-development environments.")
	}
	if !cfg.IsDevelopment() {
		cfg.RedisFailClosed = true
		if cfg.AllowWsQueryToken {
			log.Fatal("ALLOW_WS_QUERY_TOKEN must be false in non-development environments.")
		}
		if strings.TrimSpace(cfg.InternalAPIKey) == "" {
			log.Fatal("INTERNAL_API_KEY must be set in non-development environments.")
		}
		if strings.TrimSpace(cfg.MinioAccessKey) == "" || strings.TrimSpace(cfg.MinioSecretKey) == "" {
			log.Fatal("MINIO_ACCESS_KEY and MINIO_SECRET_KEY must be non-empty in non-development environments.")
		}
		if strings.TrimSpace(cfg.MinioAccessKey) == "minioadmin" || strings.TrimSpace(cfg.MinioSecretKey) == "minioadmin" {
			log.Fatal("Refusing to start with default MinIO credentials in non-development environments.")
		}
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
	whitelistStr := viper.GetString("INTERNAL_IP_WHITELIST")
	if whitelistStr != "" {
		cfg.InternalIPWhitelist = strings.Split(whitelistStr, ",")
		for i := range cfg.InternalIPWhitelist {
			cfg.InternalIPWhitelist[i] = strings.TrimSpace(cfg.InternalIPWhitelist[i])
		}
	}

	if !viper.IsSet("ALLOW_WS_QUERY_TOKEN") {
		cfg.AllowWsQueryToken = cfg.IsDevelopment()
	}

	return &cfg
}
