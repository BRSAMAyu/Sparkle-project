package main

import (
	"context"
	"database/sql"
	"log"
	"net/http"
	"net/http/httputil"
	"net/url"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
	_ "github.com/lib/pq"
	"github.com/prometheus/client_golang/prometheus/promhttp"
	"github.com/sparkle/gateway/internal/agent"
	v1 "github.com/sparkle/gateway/internal/api/v1"
	"github.com/sparkle/gateway/internal/chaos"
	"github.com/sparkle/gateway/internal/config"
	cqrsEvent "github.com/sparkle/gateway/internal/cqrs/event"
	"github.com/sparkle/gateway/internal/cqrs/metrics"
	"github.com/sparkle/gateway/internal/cqrs/outbox"
	"github.com/sparkle/gateway/internal/cqrs/projection"
	cqrsWorker "github.com/sparkle/gateway/internal/cqrs/worker"
	"github.com/sparkle/gateway/internal/db"
	"github.com/sparkle/gateway/internal/error_book"
	"github.com/sparkle/gateway/internal/galaxy"
	"github.com/sparkle/gateway/internal/handler"
	"github.com/sparkle/gateway/internal/infra/logger"
	otelinfra "github.com/sparkle/gateway/internal/infra/otel"
	"github.com/sparkle/gateway/internal/infra/redis"
	"github.com/sparkle/gateway/internal/middleware"
	"github.com/sparkle/gateway/internal/service"
	"github.com/sparkle/gateway/internal/worker"
	"go.opentelemetry.io/contrib/instrumentation/github.com/gin-gonic/gin/otelgin"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/propagation"
	"go.uber.org/zap"

	swaggerFiles "github.com/swaggo/files"
	ginSwagger "github.com/swaggo/gin-swagger"
	// _ "github.com/sparkle/gateway/docs" // Uncomment after running `swag init`
)

func main() {
	// Initialize Zap Logger
	logger.Init("sparkle-gateway")
	defer logger.Log.Sync()

	cfg := config.Load()

	// Initialize OpenTelemetry
	shutdown := otelinfra.InitTracer("sparkle-gateway")
	defer func() {
		if err := shutdown(context.Background()); err != nil {
			logger.Log.Error("Error shutting down tracer provider", zap.Error(err))
		}
	}()

	// Connect to DB (pool for CQRS operations)
	ctx := context.Background()
	pool, err := pgxpool.New(ctx, cfg.DatabaseURL)
	if err != nil {
		log.Fatalf("Unable to create connection pool: %v", err)
	}
	defer pool.Close()

	// Also create single connection for legacy compatibility
	conn, err := pgx.Connect(ctx, cfg.DatabaseURL)
	if err != nil {
		log.Fatalf("Unable to connect to database: %v", err)
	}
	defer conn.Close(ctx)

	// Initialize Chaos Manager (Wraps DB Connection)
	chaosManager := chaos.NewManager(conn)
	queries := db.New(chaosManager)

	// Connect to Redis
	rdb, err := redis.NewClient(cfg)
	if err != nil {
		log.Fatalf("Unable to connect to Redis: %v", err)
	}
	defer rdb.Close()

	// Initialize Services
	quotaService := service.NewQuotaService(rdb)
	chatHistoryService := service.NewChatHistoryService(rdb)
	semanticCacheService := service.NewSemanticCacheService(rdb)
	billingService := service.NewCostCalculator()
	userContextService := service.NewUserContextService(pool) // P0: Add user context service
	taskCommandService := service.NewTaskCommandService(pool) // P0: Task command service for ActionCard confirmations
	fileMetadataService := service.NewFileMetadataService(pool)
	fileProcessingClient := service.NewFileProcessingClient(cfg.BackendURL, cfg.InternalAPIKey)

	fileStorageService, err := service.NewFileStorageService(cfg, logger.Log)
	if err != nil {
		log.Fatalf("Unable to initialize file storage: %v", err)
	}

	// Connect to Agent Service
	agentClient, err := agent.NewClient(cfg)
	if err != nil {
		log.Fatalf("Unable to connect to agent service: %v", err)
	}
	defer agentClient.Close()

	// Connect to Galaxy Service (gRPC)
	galaxyClient, err := galaxy.NewClient(cfg)
	if err != nil {
		log.Printf("Warning: Unable to connect to galaxy service: %v", err)
	}
	if galaxyClient != nil {
		defer galaxyClient.Close()
	}

	// Connect to Error Book Service
	errorBookClient, err := error_book.NewClient(cfg)
	if err != nil {
		log.Fatalf("Unable to connect to error book service: %v", err)
	}
	defer errorBookClient.Close()

	// Initialize Handlers
	wsFactory := handler.NewWebSocketFactory(cfg)
	fileEventHub := service.NewFileEventHub()
	fileEventHandler := handler.NewFileEventHandler(wsFactory, fileEventHub)
	chatOrchestrator := handler.NewChatOrchestrator(
		agentClient,
		galaxyClient,
		queries,
		chatHistoryService,
		quotaService,
		semanticCacheService,
		billingService,
		wsFactory,
		userContextService, // P0: Pass user context service
		taskCommandService, // P0: Pass task command service
		cfg.BackendURL,
	)
	groupChatHandler := handler.NewGroupChatHandler(queries)
	errorBookHandler := handler.NewErrorBookHandler(errorBookClient)
	chaosHandler := handler.NewChaosHandler(chatHistoryService)
	fileHandler := handler.NewFileHandler(fileStorageService, fileMetadataService, fileProcessingClient)

	// Auth Service
	appleAuthService, err := service.NewAppleAuthService(cfg)
	if err != nil {
		log.Printf("Warning: Apple Auth Service init failed: %v", err)
	}
	authHandler := handler.NewAuthHandler(cfg, queries, appleAuthService)

	// ==================== CQRS Infrastructure Initialization ====================

	// Initialize CQRS Metrics
	cqrsMetrics := metrics.NewCQRSMetrics("sparkle")

	// Initialize Event Bus (Redis Streams)
	eventBus := cqrsEvent.NewRedisEventBus(rdb)

	// Initialize Outbox Repository
	outboxRepo := outbox.NewPostgresRepository(pool)

	// Outbox Publisher Worker (publishes events from outbox to Redis streams)
	outboxPublisher := outbox.NewPublisher(outboxRepo, eventBus, cqrsMetrics, logger.Log)
	go func() {
		if err := outboxPublisher.Run(context.Background()); err != nil {
			logger.Log.Error("Outbox publisher stopped", zap.Error(err))
		}
	}()

	// Outbox Cleaner (removes old published entries)
	// Runs every hour, keeps entries for 7 days
	outboxCleaner := outbox.NewCleaner(outboxRepo, cqrsMetrics, logger.Log)
	go func() {
		if err := outboxCleaner.Run(context.Background()); err != nil {
			logger.Log.Error("Outbox cleaner stopped", zap.Error(err))
		}
	}()

	// DLQ Cleaner (removes old dead letter queue entries)
	// Runs every 24 hours, keeps entries for 7 days
	dlqHandler := cqrsWorker.NewDLQHandler(rdb, logger.Log)
	dlqCleaner := cqrsWorker.NewDLQCleaner(dlqHandler, 24*time.Hour, logger.Log)
	go func() {
		if err := dlqCleaner.Run(context.Background()); err != nil {
			logger.Log.Error("DLQ cleaner stopped", zap.Error(err))
		}
	}()

	// Initialize Projection Manager
	projectionManager := projection.NewManager(pool, logger.Log)

	// Initialize Snapshot Manager
	snapshotManager := projection.NewSnapshotManager(pool, logger.Log)

	// Initialize Projection Builder
	projectionBuilder := projection.NewBuilder(pool, projectionManager, snapshotManager, cqrsMetrics, logger.Log)

	// Register Projection Handlers
	// Community Projection Handler
	communityProjectionHandler := projection.NewCommunityProjectionHandler(rdb, pool, logger.Log)
	if err := projectionManager.RegisterHandler(communityProjectionHandler); err != nil {
		logger.Log.Error("Failed to register community projection handler", zap.Error(err))
	}

	// Task Projection Handler
	taskProjectionHandler := projection.NewTaskProjectionHandler(rdb, pool, logger.Log)
	if err := projectionManager.RegisterHandler(taskProjectionHandler); err != nil {
		logger.Log.Error("Failed to register task projection handler", zap.Error(err))
	}

	// Galaxy Projection Handler
	galaxyProjectionHandler := projection.NewGalaxyProjectionHandler(rdb, pool, logger.Log)
	if err := projectionManager.RegisterHandler(galaxyProjectionHandler); err != nil {
		logger.Log.Error("Failed to register galaxy projection handler", zap.Error(err))
	}

	// ==================== Community Module (CQRS) ====================

	// Community Command Service (uses Outbox Pattern)
	commCmdService := service.NewCommunityCommandService(pool)
	commQueryService := service.NewCommunityQueryService(rdb)
	commHandler := v1.NewCommunityHandler(commCmdService, commQueryService)

	// Community Sync Worker (consumes events from Redis, updates projections)
	commSyncWorker := worker.NewCommunitySyncWorker(rdb, pool, cqrsMetrics, logger.Log)

	// Start Community Sync Worker
	go func() {
		if err := commSyncWorker.Run(context.Background()); err != nil {
			logger.Log.Error("Community sync worker stopped", zap.Error(err))
		}
	}()

	// ==================== Task Module (CQRS) ====================

	// Task Command Service already initialized earlier (line 87) for ChatOrchestrator

	// Task Sync Worker (consumes events from Redis, updates projections)
	taskSyncWorker := worker.NewTaskSyncWorker(rdb, pool, cqrsMetrics, logger.Log)

	// Start Task Sync Worker
	go func() {
		if err := taskSyncWorker.Run(context.Background()); err != nil {
			logger.Log.Error("Task sync worker stopped", zap.Error(err))
		}
	}()

	// ==================== Galaxy Module (CQRS) ====================

	// Galaxy Command Service (uses Outbox Pattern)
	_ = service.NewGalaxyCommandService(pool)

	// Galaxy Sync Worker (consumes events from Redis, updates projections)
	galaxySyncWorker := worker.NewGalaxySyncWorker(rdb, pool, cqrsMetrics, logger.Log)

	// Start Galaxy Sync Worker
	go func() {
		if err := galaxySyncWorker.Run(context.Background()); err != nil {
			logger.Log.Error("Galaxy sync worker stopped", zap.Error(err))
		}
	}()

	fileEventSubscriber := service.NewFileEventSubscriber(rdb, fileEventHub, logger.Log)
	go func() {
		if err := fileEventSubscriber.Run(context.Background()); err != nil {
			logger.Log.Error("File event subscriber stopped", zap.Error(err))
		}
	}()

	// File GC Worker (cleanup stale uploads)
	fileGC := service.NewFileGCService(fileMetadataService, fileStorageService, cfg, logger.Log)
	go func() {
		if err := fileGC.Run(context.Background()); err != nil {
			logger.Log.Error("File GC stopped", zap.Error(err))
		}
	}()

	// ==================== Galaxy Outbox Relay (RabbitMQ) ====================
	// This relay processes the outbox_events table and publishes to RabbitMQ
	// for external service integration (Analytics, Task Stats, etc.)

	// Create raw DB connection for OutboxRelay as it uses sql.DB
	sqlDB, err := sql.Open("postgres", cfg.DatabaseURL)
	if err != nil {
		log.Fatalf("Unable to open sql.DB for outbox relay: %v", err)
	}
	defer sqlDB.Close()

	galaxyOutboxRelay, err := worker.NewOutboxRelay(sqlDB, cfg.RabbitMQURL, logger.Log, cqrsMetrics)
	if err != nil {
		logger.Log.Error("Failed to initialize Galaxy Outbox Relay", zap.Error(err))
	} else {
		go galaxyOutboxRelay.Start(context.Background())
	}

	// ==================== CQRS Health Check ====================

	// Register CQRS health check endpoint
	cqrsHealthHandler := func(c *gin.Context) {
		// Check outbox publisher status
		outboxPendingCount, err := outboxRepo.GetPendingCount(context.Background())
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{
				"status": "error",
				"error":  err.Error(),
			})
			return
		}

		// Check worker status
		commRunning := commSyncWorker.IsRunning()
		taskRunning := taskSyncWorker.IsRunning()
		galaxyRunning := galaxySyncWorker.IsRunning()

		c.JSON(http.StatusOK, gin.H{
			"status": "healthy",
			"components": gin.H{
				"outbox_publisher": gin.H{
					"pending_events": outboxPendingCount,
				},
				"workers": gin.H{
					"community": commRunning,
					"task":      taskRunning,
					"galaxy":    galaxyRunning,
				},
			},
		})
	}

	// Setup Router
	r := gin.Default()

	// Prometheus Metrics Endpoint
	r.GET("/metrics", gin.WrapH(promhttp.Handler()))

	// Apply OTel Middleware
	r.Use(otelgin.Middleware("sparkle-gateway"))

	// Apply Security Headers
	r.Use(middleware.SecurityHeadersMiddleware())

	// WebSocket Route (Go Native)
	r.GET("/ws/chat", middleware.AuthMiddleware(cfg), chatOrchestrator.HandleWebSocket)
	r.GET("/ws/files", middleware.AuthMiddleware(cfg), fileEventHandler.HandleWebSocket)

	// Middleware
	authMiddleware := middleware.AuthMiddleware(cfg)

	// API Routes
	api := r.Group("/api/v1")
	{
		// Health Checks
		api.GET("/health", func(c *gin.Context) {
			c.JSON(http.StatusOK, gin.H{"status": "ok"})
		})
		api.GET("/health/cqrs", cqrsHealthHandler)

		// Auth
		api.POST("/auth/apple", authHandler.AppleLogin)

		// Go Optimized Endpoints
		api.GET("/groups/:group_id/messages", authMiddleware, groupChatHandler.GetMessages)

		// Error Book Routes
		errorBookHandler.RegisterRoutes(api)

		// Community Routes
		commHandler.RegisterRoutes(api)

		// File Routes
		fileHandler.RegisterRoutes(api, authMiddleware)
	}

	// Swagger UI
	r.GET("/swagger/*any", ginSwagger.WrapHandler(swaggerFiles.Handler))

	// Admin Routes (Chaos Engineering + CQRS Management)
	// Protected by X-Admin-Secret header (required in production)
	admin := r.Group("/admin", middleware.AdminAuthMiddleware(cfg))
	{
		// Chaos Engineering
		admin.POST("/chaos/inject", chaosManager.HandleInject)
		admin.POST("/chaos/config", chaosHandler.SetThreshold)
		admin.GET("/chaos/status", chaosHandler.GetStatus)

		// CQRS Projection Management
		admin.GET("/cqrs/projections", func(c *gin.Context) {
			projections, err := projectionManager.GetAllProjections(c.Request.Context())
			if err != nil {
				c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
				return
			}
			c.JSON(http.StatusOK, projections)
		})

		admin.GET("/cqrs/projections/:name", func(c *gin.Context) {
			name := c.Param("name")
			info, err := projectionManager.GetProjectionInfo(c.Request.Context(), name)
			if err != nil {
				c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
				return
			}
			c.JSON(http.StatusOK, info)
		})

		admin.POST("/cqrs/projections/:name/reset", func(c *gin.Context) {
			name := c.Param("name")
			if err := projectionManager.ResetProjection(c.Request.Context(), name); err != nil {
				c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
				return
			}
			c.JSON(http.StatusOK, gin.H{"status": "resetting"})
		})

		admin.POST("/cqrs/projections/:name/pause", func(c *gin.Context) {
			name := c.Param("name")
			if err := projectionManager.PauseProjection(c.Request.Context(), name); err != nil {
				c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
				return
			}
			c.JSON(http.StatusOK, gin.H{"status": "paused"})
		})

		admin.POST("/cqrs/projections/:name/resume", func(c *gin.Context) {
			name := c.Param("name")
			if err := projectionManager.ResumeProjection(c.Request.Context(), name); err != nil {
				c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
				return
			}
			c.JSON(http.StatusOK, gin.H{"status": "resumed"})
		})

		// Snapshot Management
		admin.GET("/cqrs/snapshots/:name/count", func(c *gin.Context) {
			name := c.Param("name")
			count, err := snapshotManager.GetSnapshotCount(c.Request.Context(), name)
			if err != nil {
				c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
				return
			}
			c.JSON(http.StatusOK, gin.H{"count": count})
		})

		// Projection Rebuild
		// POST /admin/cqrs/projections/:name/rebuild - Rebuild projection from event store
		admin.POST("/cqrs/projections/:name/rebuild", func(c *gin.Context) {
			name := c.Param("name")

			// Determine aggregate type based on projection name
			var aggregateType cqrsEvent.AggregateType
			switch name {
			case "community_projection":
				aggregateType = cqrsEvent.AggregatePost
			case "task_projection":
				aggregateType = cqrsEvent.AggregateTask
			case "galaxy_projection":
				aggregateType = cqrsEvent.AggregateKnowledgeNode
			default:
				c.JSON(http.StatusBadRequest, gin.H{"error": "unknown projection name: " + name})
				return
			}

			// Start rebuild in background
			go func() {
				ctx := context.Background()
				opts := projection.DefaultRebuildOptions()
				progress, err := projectionBuilder.RebuildFromEventStore(ctx, name, aggregateType, opts)
				if err != nil {
					logger.Log.Error("Projection rebuild failed",
						zap.String("projection", name),
						zap.Error(err),
					)
				} else {
					logger.Log.Info("Projection rebuild completed",
						zap.String("projection", name),
						zap.Int64("processed", progress.ProcessedEvents),
						zap.Duration("duration", progress.Duration),
					)
				}
			}()

			c.JSON(http.StatusOK, gin.H{
				"status":  "rebuild_started",
				"message": "Rebuild is running in background. Check /admin/cqrs/projections/" + name + " for status",
			})
		})

		// POST /admin/cqrs/projections/:name/rebuild/snapshot - Rebuild from latest snapshot
		admin.POST("/cqrs/projections/:name/rebuild/snapshot", func(c *gin.Context) {
			name := c.Param("name")

			var aggregateType cqrsEvent.AggregateType
			switch name {
			case "community_projection":
				aggregateType = cqrsEvent.AggregatePost
			case "task_projection":
				aggregateType = cqrsEvent.AggregateTask
			case "galaxy_projection":
				aggregateType = cqrsEvent.AggregateKnowledgeNode
			default:
				c.JSON(http.StatusBadRequest, gin.H{"error": "unknown projection name: " + name})
				return
			}

			go func() {
				ctx := context.Background()
				opts := projection.DefaultRebuildOptions()
				progress, err := projectionBuilder.RebuildFromSnapshot(ctx, name, aggregateType, opts)
				if err != nil {
					logger.Log.Error("Projection rebuild from snapshot failed",
						zap.String("projection", name),
						zap.Error(err),
					)
				} else {
					logger.Log.Info("Projection rebuild from snapshot completed",
						zap.String("projection", name),
						zap.Int64("processed", progress.ProcessedEvents),
						zap.Duration("duration", progress.Duration),
					)
				}
			}()

			c.JSON(http.StatusOK, gin.H{
				"status":  "rebuild_started",
				"message": "Rebuild from snapshot is running in background",
			})
		})

		// POST /admin/cqrs/projections/:name/snapshot - Create snapshot
		admin.POST("/cqrs/projections/:name/snapshot", func(c *gin.Context) {
			name := c.Param("name")

			// Get projection info to get current position
			info, err := projectionManager.GetProjectionInfo(c.Request.Context(), name)
			if err != nil {
				c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
				return
			}

			// For simplicity, create empty snapshot data
			// In production, you'd serialize the actual projection state
			snapshotData := map[string]interface{}{
				"projection_name": name,
				"position":        info.LastProcessedPosition,
				"status":          info.Status,
				"version":         info.Version,
			}

			if err := projectionBuilder.CreateSnapshot(c.Request.Context(), name, snapshotData); err != nil {
				c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
				return
			}

			c.JSON(http.StatusOK, gin.H{
				"status":   "snapshot_created",
				"position": info.LastProcessedPosition,
			})
		})

		// GET /admin/cqrs/dlq/stats - Get DLQ statistics
		admin.GET("/cqrs/dlq/stats", func(c *gin.Context) {
			stats, err := dlqHandler.GetStats(c.Request.Context())
			if err != nil {
				c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
				return
			}
			c.JSON(http.StatusOK, stats)
		})

		// POST /admin/cqrs/dlq/cleanup - Manually trigger DLQ cleanup
		admin.POST("/cqrs/dlq/cleanup", func(c *gin.Context) {
			deleted, err := dlqHandler.Cleanup(c.Request.Context())
			if err != nil {
				c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
				return
			}
			c.JSON(http.StatusOK, gin.H{
				"status":        "cleanup_completed",
				"deleted_count": deleted,
			})
		})

		// POST /admin/cqrs/dlq/retry/:message_id - Retry a DLQ entry
		admin.POST("/cqrs/dlq/retry/:message_id", func(c *gin.Context) {
			messageID := c.Param("message_id")
			if err := dlqHandler.RetryEntry(c.Request.Context(), messageID); err != nil {
				c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
				return
			}
			c.JSON(http.StatusOK, gin.H{
				"status":     "retry_submitted",
				"message_id": messageID,
			})
		})

		// DELETE /admin/cqrs/dlq/:message_id - Delete a DLQ entry
		admin.DELETE("/cqrs/dlq/:message_id", func(c *gin.Context) {
			messageID := c.Param("message_id")
			if err := dlqHandler.DeleteEntry(c.Request.Context(), messageID); err != nil {
				c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
				return
			}
			c.JSON(http.StatusOK, gin.H{
				"status":     "deleted",
				"message_id": messageID,
			})
		})

		// GET /admin/cqrs/outbox/stats - Get outbox statistics
		admin.GET("/cqrs/outbox/stats", func(c *gin.Context) {
			pendingCount, err := outboxRepo.GetPendingCount(c.Request.Context())
			if err != nil {
				c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
				return
			}
			c.JSON(http.StatusOK, gin.H{
				"pending_count": pendingCount,
			})
		})
	}

	// Reverse Proxy for Python Backend (REST API)
	targetURL, err := url.Parse("http://localhost:8000")
	if err != nil {
		log.Fatalf("Failed to parse Python backend URL: %v", err)
	}

	proxy := httputil.NewSingleHostReverseProxy(targetURL)
	proxy.Director = func(req *http.Request) {
		req.URL.Scheme = targetURL.Scheme
		req.URL.Host = targetURL.Host
		req.Host = targetURL.Host

		// Inject OTel Trace Context into headers for full-link tracing
		otel.GetTextMapPropagator().Inject(req.Context(), propagation.HeaderCarrier(req.Header))
	}

	// Forward all other requests to Python Backend
	// This covers /api/v1/groups, /api/v1/users, etc.
	// We wrap the proxy with Auth checks for protected routes
	r.NoRoute(func(c *gin.Context) {
		path := c.Request.URL.Path

		// Public routes that don't need Go-side validation (let Python handle or open)
		// /api/v1/auth/* -> Login/Register
		// /api/v1/health -> Health check (though we handled one explicitly above)
		// /docs, /redoc, /openapi.json -> Swagger UI
		if strings.HasPrefix(path, "/api/v1/auth") ||
			path == "/api/v1/health" ||
			strings.HasPrefix(path, "/docs") ||
			strings.HasPrefix(path, "/redoc") ||
			strings.HasPrefix(path, "/openapi.json") {
			proxy.ServeHTTP(c.Writer, c.Request)
			return
		}

		// Verify Token
		authMiddleware(c)
		if c.IsAborted() {
			return
		}

		// Token is valid. Pass user_id to backend via header for trust (optional)
		userID := c.GetString("user_id")
		if userID != "" {
			c.Request.Header.Set("X-User-ID", userID)
		}

		proxy.ServeHTTP(c.Writer, c.Request)
	})

	logger.Log.Info("Gateway starting", zap.String("port", cfg.Port))
	if err := r.Run(":" + cfg.Port); err != nil {
		logger.Log.Fatal("Failed to run server", zap.Error(err))
	}
}
