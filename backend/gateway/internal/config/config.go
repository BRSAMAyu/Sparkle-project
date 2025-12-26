package config

import (
	"log"

	"github.com/spf13/viper"
)

type Config struct {
	Port         string `mapstructure:"PORT"`
	DatabaseURL  string `mapstructure:"DATABASE_URL"`
	AgentAddress string `mapstructure:"AGENT_ADDRESS"`
	JWTSecret    string `mapstructure:"JWT_SECRET"`
}

func Load() *Config {
	viper.SetDefault("PORT", "8080")
	viper.SetDefault("DATABASE_URL", "postgres://postgres:password@localhost:5432/sparkle")
	viper.SetDefault("AGENT_ADDRESS", "localhost:50051")
	viper.SetDefault("JWT_SECRET", "change-me")

	viper.AutomaticEnv()

	var cfg Config
	if err := viper.Unmarshal(&cfg); err != nil {
		log.Fatalf("Failed to load config: %v", err)
	}
	return &cfg
}
