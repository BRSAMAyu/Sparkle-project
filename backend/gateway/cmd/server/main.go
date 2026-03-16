package main

import (
	"context"
	"log"
	"net/http"
	"os/signal"
	"syscall"
	"time"

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

	r := setupRouter(cfg, dbh, rdb, services, handlers, cqrs, proxy, agentClient)

	// --- Graceful shutdown ---
	srv := &http.Server{
		Addr:    ":" + cfg.Port,
		Handler: r,
	}

	// Start server in a goroutine
	go func() {
		logger.Log.Info("Gateway starting", zap.String("port", cfg.Port))
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			logger.Log.Fatal("Failed to run server", zap.Error(err))
		}
	}()

	// Wait for interrupt signal
	quit, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()
	<-quit.Done()

	shutdownTimeout := 15
	if cfg.ShutdownTimeoutSeconds > 0 {
		shutdownTimeout = cfg.ShutdownTimeoutSeconds
	}
	logger.Log.Info("Shutdown signal received, draining connections...",
		zap.Int("timeout_seconds", shutdownTimeout))

	// Phase 1: Drain WebSocket connections (1/3 of total timeout)
	drainTimeout := time.Duration(shutdownTimeout/3) * time.Second
	if drainTimeout < 2*time.Second {
		drainTimeout = 2 * time.Second
	}
	if registry := handlers.chatOrchestrator.Registry(); registry != nil {
		connCount := registry.Count()
		logger.Log.Info("Draining WebSocket connections",
			zap.Int("count", connCount),
			zap.Duration("drain_timeout", drainTimeout))
		registry.DrainAll(drainTimeout)
		logger.Log.Info("WebSocket connections drained")
	}

	// Phase 2: Shutdown HTTP server (remaining time)
	shutdownCtx, shutdownCancel := context.WithTimeout(context.Background(), time.Duration(shutdownTimeout)*time.Second)
	defer shutdownCancel()

	if err := srv.Shutdown(shutdownCtx); err != nil {
		logger.Log.Error("Server forced to shutdown", zap.Error(err))
	}

	logger.Log.Info("Server exited gracefully")
}
