package main

import (
	"context"
	"log"

	"github.com/sparkle/gateway/internal/config"
	"github.com/sparkle/gateway/internal/infra/logger"
	"go.uber.org/zap"
)

func main() {
	// Initialize Zap Logger
	logger.Init("sparkle-gateway")
	defer logger.Log.Sync()

	cfg := config.Load()

	// Initialize OpenTelemetry
	shutdown := initTracer()
	defer func() {
		if err := shutdown(context.Background()); err != nil {
			logger.Log.Error("Error shutting down tracer provider", zap.Error(err))
		}
	}()

	ctx := context.Background()
	dbh, err := initDatabase(ctx, cfg)
	if err != nil {
		log.Fatalf("Unable to initialize database: %v", err)
	}
	defer dbh.pool.Close()
	defer dbh.conn.Close(ctx)
	defer dbh.sqlDB.Close()

	rdb, err := initRedis(cfg)
	if err != nil {
		log.Fatalf("Unable to connect to Redis: %v", err)
	}
	defer rdb.Close()

	services, err := initServices(cfg, dbh, rdb, logger.Log)
	if err != nil {
		log.Fatalf("Unable to initialize services: %v", err)
	}

	agentClient, galaxyClient, errorBookClient, err := initClients(cfg)
	if err != nil {
		log.Fatalf("Unable to initialize gRPC clients: %v", err)
	}
	defer agentClient.Close()
	if galaxyClient != nil {
		defer galaxyClient.Close()
	}
	defer errorBookClient.Close()

	handlers, err := initHandlers(cfg, dbh, rdb, services, agentClient, galaxyClient, errorBookClient, logger.Log)
	if err != nil {
		log.Fatalf("Unable to initialize handlers: %v", err)
	}

	cqrs := initCQRS(ctx, cfg, dbh, rdb, services, logger.Log)
	startCQRSWorkers(cqrs, logger.Log)

	proxy, err := setupProxy(cfg)
	if err != nil {
		log.Fatalf("Failed to setup backend proxy: %v", err)
	}

	r := setupRouter(cfg, dbh, rdb, services, handlers, cqrs, proxy)

	logger.Log.Info("Gateway starting", zap.String("port", cfg.Port))
	if err := r.Run(":" + cfg.Port); err != nil {
		logger.Log.Fatal("Failed to run server", zap.Error(err))
	}
}
