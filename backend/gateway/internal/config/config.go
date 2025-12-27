package config

import (
	"log"

	"github.com/spf13/viper"
)

type Config struct {
	Port          string `mapstructure:"PORT"`
	DatabaseURL   string `mapstructure:"DATABASE_URL"`
	AgentAddress  string `mapstructure:"AGENT_ADDRESS"`
	JWTSecret     string `mapstructure:"JWT_SECRET"`
	RedisURL      string `mapstructure:"REDIS_URL"`
	RedisPassword string `mapstructure:"REDIS_PASSWORD"`
	BackendURL    string `mapstructure:"BACKEND_URL"`
}

func Load() *Config {
	viper.SetDefault("PORT", "8080")
	viper.SetDefault("DATABASE_URL", "postgres://postgres:password@localhost:5432/sparkle")
	viper.SetDefault("AGENT_ADDRESS", "localhost:50051")
	viper.SetDefault("JWT_SECRET", "Jk8Lm2Np5Qr9St3Uv7Wx1Yz4Ab6Cd0Ef8Gh3Ij7Kl2Mn9Op4Qr6Sv0Tw1Xy5Za")
	viper.SetDefault("REDIS_URL", "127.0.0.1:6379")
	viper.SetDefault("REDIS_PASSWORD", "")
	viper.SetDefault("BACKEND_URL", "http://localhost:8000")

	// Read from .env file if it exists
	viper.SetConfigFile(".env")
	viper.ReadInConfig() // Ignore error if file not found

	viper.AutomaticEnv()

	var cfg Config
	if err := viper.Unmarshal(&cfg); err != nil {
		log.Fatalf("Failed to load config: %v", err)
	}
	return &cfg
}