package main

import (
	"context"
	"database/sql"
	"log"
	"net"
	"net/http"
	"net/http/httputil"
	"net/url"
	"os"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
	_ "github.com/lib/pq"
	"github.com/prometheus/client_golang/prometheus/promhttp"
	redisv9 "github.com/redis/go-redis/v9"
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
	otelinfra "github.com/sparkle/gateway/internal/infra/otel"
	redisinfra "github.com/sparkle/gateway/internal/infra/redis"
	"github.com/sparkle/gateway/internal/middleware"
	"github.com/sparkle/gateway/internal/service"
	"github.com/sparkle/gateway/internal/worker"
	"go.opentelemetry.io/contrib/instrumentation/github.com/gin-gonic/gin/otelgin"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/propagation"
	"go.uber.org/zap"

	swaggerFiles "github.com/swaggo/files"
	ginSwagger "github.com/swaggo/gin-swagger"
)

type databaseHandles struct {
	pool         *pgxpool.Pool
	conn         *pgx.Conn
	sqlDB        *sql.DB
	queries      *db.Queries
	chaosManager *chaos.Manager
}

type serviceBundle struct {
	quota          *service.QuotaService
	chatHistory    *service.ChatHistoryService
	semantic       *service.SemanticCacheService
	billing        *service.CostCalculator
	userContext    *service.UserContextService
	taskCommand    *service.TaskCommandService
	fileMetadata   *service.FileMetadataService
	fileProcessing *service.FileProcessingClient
	fileStorage    *service.FileStorageService
	fileEventHub   *service.FileEventHub
	signalHub      *service.SignalHub
}

type handlerBundle struct {
	wsFactory                *handler.WebSocketFactory
	wsTicketHandler          *handler.WSTicketHandler
	chatHistoryHandler       *handler.ChatHistoryHandler
	fileEventHandler         *handler.FileEventHandler
	chatOrchestrator         *handler.ChatOrchestrator
	signalPushHandler        *handler.SignalPushHandler
	groupChatHandler         *handler.GroupChatHandler
	errorBookHandler         *handler.ErrorBookHandler
	chaosHandler             *handler.ChaosHandler
	fileHandler              *handler.FileHandler
	interventionPushHandler  *handler.InterventionPushHandler
	interventionProxyHandler *handler.InterventionProxyHandler
	dashboardProxyHandler    *handler.DashboardProxyHandler
	predictiveProxyHandler   *handler.PredictiveProxyHandler
	dataConsistencyHandler   *handler.DataConsistencyHandler
	sttHandler               *handler.STTHandler
	wsProxy                  *handler.WebSocketProxy
	authHandler              *handler.AuthHandler
	galaxyHandler            *handler.GalaxyHandler
}

type cqrsBundle struct {
	metrics            *metrics.CQRSMetrics
	outboxRepo         *outbox.PostgresRepository
	projectionManager  *projection.Manager
	snapshotManager    *projection.SnapshotManager
	projectionBuilder  *projection.Builder
	dlqHandler         *cqrsWorker.DLQHandler
	commSyncWorker     *worker.CommunitySyncWorker
	taskSyncWorker     *worker.TaskSyncWorker
	galaxySyncWorker   *worker.GalaxySyncWorker
	outboxPublisherRun func()
	outboxCleanerRun   func()
	dlqCleanerRun      func()
}

type proxyBundle struct {
	proxy            *httputil.ReverseProxy
	abTestMiddleware *middleware.ABTestMiddleware
}

func initTracer() func(context.Context) error {
	return otelinfra.InitTracer("sparkle-gateway")
}

func initDatabase(ctx context.Context, cfg *config.Config) (*databaseHandles, error) {
	pool, err := pgxpool.New(ctx, cfg.DatabaseURL)
	if err != nil {
		return nil, err
	}

	conn, err := pgx.Connect(ctx, cfg.DatabaseURL)
	if err != nil {
		pool.Close()
		return nil, err
	}

	sqlDB, err := sql.Open("postgres", cfg.DatabaseURL)
	if err != nil {
		conn.Close(ctx)
		pool.Close()
		return nil, err
	}

	chaosManager := chaos.NewManager(conn)
	queries := db.New(chaosManager)

	return &databaseHandles{
		pool:         pool,
		conn:         conn,
		sqlDB:        sqlDB,
		queries:      queries,
		chaosManager: chaosManager,
	}, nil
}

func initRedis(cfg *config.Config) (*redisv9.Client, error) {
	return redisinfra.NewClient(cfg)
}

func initServices(cfg *config.Config, dbh *databaseHandles, rdb *redisv9.Client, logger *zap.Logger) (*serviceBundle, error) {
	quotaService := service.NewQuotaService(rdb)
	chatHistoryTTL := cfg.CacheStrategy.GoRedisCache.ChatHistoryTTL
	if chatHistoryTTL == 0 {
		chatHistoryTTL = 30 * time.Minute
	}
	chatHistoryService := service.NewChatHistoryServiceWithTTL(rdb, chatHistoryTTL)
	semanticCacheService := service.NewSemanticCacheService(rdb)
	billingService := service.NewCostCalculator()
	userContextService := service.NewUserContextService(dbh.pool)
	taskCommandService := service.NewTaskCommandService(dbh.pool)
	fileMetadataService := service.NewFileMetadataService(dbh.pool)
	fileProcessingClient := service.NewFileProcessingClient(cfg.BackendURL, cfg.InternalAPIKey)
	fileStorageService, err := service.NewFileStorageService(cfg, logger)
	if err != nil {
		return nil, err
	}

	return &serviceBundle{
		quota:          quotaService,
		chatHistory:    chatHistoryService,
		semantic:       semanticCacheService,
		billing:        billingService,
		userContext:    userContextService,
		taskCommand:    taskCommandService,
		fileMetadata:   fileMetadataService,
		fileProcessing: fileProcessingClient,
		fileStorage:    fileStorageService,
		fileEventHub:   service.NewFileEventHub(),
		signalHub:      service.NewSignalHub(),
	}, nil
}

func initClients(cfg *config.Config) (*agent.Client, *galaxy.Client, *error_book.Client, error) {
	agentClient, err := agent.NewClient(cfg)
	if err != nil {
		return nil, nil, nil, err
	}

	galaxyClient, err := galaxy.NewClient(cfg)
	if err != nil {
		log.Printf("Warning: Unable to connect to galaxy service: %v", err)
	}

	errorBookClient, err := error_book.NewClient(cfg)
	if err != nil {
		if galaxyClient != nil {
			galaxyClient.Close()
		}
		agentClient.Close()
		return nil, nil, nil, err
	}

	return agentClient, galaxyClient, errorBookClient, nil
}

func initHandlers(cfg *config.Config, dbh *databaseHandles, rdb *redisv9.Client, services *serviceBundle, agentClient *agent.Client, galaxyClient *galaxy.Client, errorBookClient *error_book.Client, logger *zap.Logger) (*handlerBundle, error) {
	wsFactory := handler.NewWebSocketFactory(cfg)
	wsTicketHandler := handler.NewWSTicketHandler(cfg, rdb)
	chatHistoryHandler := handler.NewChatHistoryHandler(services.chatHistory)
	fileEventHandler := handler.NewFileEventHandler(wsFactory, services.fileEventHub, cfg)
	chatOrchestrator := handler.NewChatOrchestrator(
		agentClient,
		galaxyClient,
		dbh.queries,
		services.chatHistory,
		services.quota,
		services.semantic,
		services.billing,
		wsFactory,
		cfg,
		services.userContext,
		services.taskCommand,
		cfg.BackendURL,
		services.signalHub,
	)
	signalPushHandler := handler.NewSignalPushHandler(cfg, services.signalHub)
	groupChatHandler := handler.NewGroupChatHandler(dbh.queries)
	errorBookHandler := handler.NewErrorBookHandler(errorBookClient)
	chaosHandler := handler.NewChaosHandler(services.chatHistory, cfg.ToxiproxyURL)
	fileHandler := handler.NewFileHandler(services.fileStorage, services.fileMetadata, services.fileProcessing)
	interventionPushHandler := handler.NewInterventionPushHandler(chatOrchestrator)
	interventionProxyHandler := handler.NewInterventionProxyHandler(cfg.BackendURL)
	dashboardProxyHandler := handler.NewDashboardProxyHandler(cfg.BackendURL)
	predictiveProxyHandler := handler.NewPredictiveProxyHandler(cfg.BackendURL)
	dataConsistencyHandler := handler.NewDataConsistencyHandler(services.chatHistory, dbh.queries, rdb)

	sttURL := strings.Replace(cfg.BackendURL, "http://", "ws://", 1)
	sttURL = strings.Replace(sttURL, "https://", "wss://", 1)
	sttHandler := handler.NewSTTHandler(sttURL+"/api/v1/stt/stream", logger)

	wsProxy := handler.NewWebSocketProxy(cfg.BackendURL, logger)

	appleAuthService, err := service.NewAppleAuthService(cfg)
	if err != nil {
		log.Printf("Warning: Apple Auth Service init failed: %v", err)
	}
	authHandler := handler.NewAuthHandler(cfg, dbh.queries, appleAuthService)

	// Galaxy handler for knowledge graph endpoints
	galaxyHandler := handler.NewGalaxyHandler(galaxyClient, rdb, cfg.BackendURL)

	return &handlerBundle{
		wsFactory:                wsFactory,
		wsTicketHandler:          wsTicketHandler,
		chatHistoryHandler:       chatHistoryHandler,
		fileEventHandler:         fileEventHandler,
		chatOrchestrator:         chatOrchestrator,
		signalPushHandler:        signalPushHandler,
		groupChatHandler:         groupChatHandler,
		errorBookHandler:         errorBookHandler,
		chaosHandler:             chaosHandler,
		fileHandler:              fileHandler,
		interventionPushHandler:  interventionPushHandler,
		interventionProxyHandler: interventionProxyHandler,
		dashboardProxyHandler:    dashboardProxyHandler,
		predictiveProxyHandler:   predictiveProxyHandler,
		dataConsistencyHandler:   dataConsistencyHandler,
		sttHandler:               sttHandler,
		wsProxy:                  wsProxy,
		authHandler:              authHandler,
		galaxyHandler:            galaxyHandler,
	}, nil
}

func initCQRS(ctx context.Context, cfg *config.Config, dbh *databaseHandles, rdb *redisv9.Client, services *serviceBundle, logger *zap.Logger) *cqrsBundle {
	cqrsMetrics := metrics.NewCQRSMetrics("sparkle")
	eventBus := cqrsEvent.NewRedisEventBus(rdb)
	outboxRepo := outbox.NewPostgresRepository(dbh.pool)
	outboxPublisher := outbox.NewPublisher(outboxRepo, eventBus, cqrsMetrics, logger)
	outboxCleaner := outbox.NewCleaner(outboxRepo, cqrsMetrics, logger)
	dlqHandler := cqrsWorker.NewDLQHandler(rdb, logger)
	dlqCleaner := cqrsWorker.NewDLQCleaner(dlqHandler, 24*time.Hour, logger)

	projectionManager := projection.NewManager(dbh.pool, logger)
	snapshotManager := projection.NewSnapshotManager(dbh.pool, logger)
	projectionBuilder := projection.NewBuilder(dbh.pool, projectionManager, snapshotManager, cqrsMetrics, logger)

	communityProjectionHandler := projection.NewCommunityProjectionHandler(rdb, dbh.pool, logger)
	if err := projectionManager.RegisterHandler(communityProjectionHandler); err != nil {
		logger.Error("Failed to register community projection handler", zap.Error(err))
	}
	taskProjectionHandler := projection.NewTaskProjectionHandler(rdb, dbh.pool, logger)
	if err := projectionManager.RegisterHandler(taskProjectionHandler); err != nil {
		logger.Error("Failed to register task projection handler", zap.Error(err))
	}
	galaxyProjectionHandler := projection.NewGalaxyProjectionHandler(rdb, dbh.pool, logger)
	if err := projectionManager.RegisterHandler(galaxyProjectionHandler); err != nil {
		logger.Error("Failed to register galaxy projection handler", zap.Error(err))
	}

	commCmdService := service.NewCommunityCommandService(dbh.pool)
	commQueryService := service.NewCommunityQueryService(rdb)
	_ = commCmdService
	_ = commQueryService

	commSyncWorker := worker.NewCommunitySyncWorker(rdb, dbh.pool, cqrsMetrics, logger)
	taskSyncWorker := worker.NewTaskSyncWorker(rdb, dbh.pool, cqrsMetrics, logger)
	galaxySyncWorker := worker.NewGalaxySyncWorker(rdb, dbh.pool, cqrsMetrics, logger)

	fileEventSubscriber := service.NewFileEventSubscriber(rdb, services.fileEventHub, logger)
	go func() {
		if err := fileEventSubscriber.Run(context.Background()); err != nil {
			logger.Error("File event subscriber stopped", zap.Error(err))
		}
	}()

	fileGC := service.NewFileGCService(services.fileMetadata, services.fileStorage, cfg, logger)
	go func() {
		if err := fileGC.Run(context.Background()); err != nil {
			logger.Error("File GC stopped", zap.Error(err))
		}
	}()

	if cfg.RabbitMQURL != "" {
		galaxyOutboxRelay, err := worker.NewOutboxRelay(dbh.sqlDB, cfg.RabbitMQURL, logger, cqrsMetrics)
		if err != nil {
			logger.Error("Failed to initialize Galaxy Outbox Relay", zap.Error(err))
		} else {
			go galaxyOutboxRelay.Start(ctx)
		}
	} else {
		logger.Info("Skipping Galaxy Outbox Relay (RABBITMQ_URL not set)")
	}

	return &cqrsBundle{
		metrics:           cqrsMetrics,
		outboxRepo:        outboxRepo,
		projectionManager: projectionManager,
		snapshotManager:   snapshotManager,
		projectionBuilder: projectionBuilder,
		dlqHandler:        dlqHandler,
		commSyncWorker:    commSyncWorker,
		taskSyncWorker:    taskSyncWorker,
		galaxySyncWorker:  galaxySyncWorker,
		outboxPublisherRun: func() {
			if err := outboxPublisher.Run(context.Background()); err != nil {
				logger.Error("Outbox publisher stopped", zap.Error(err))
			}
		},
		outboxCleanerRun: func() {
			if err := outboxCleaner.Run(context.Background()); err != nil {
				logger.Error("Outbox cleaner stopped", zap.Error(err))
			}
		},
		dlqCleanerRun: func() {
			if err := dlqCleaner.Run(context.Background()); err != nil {
				logger.Error("DLQ cleaner stopped", zap.Error(err))
			}
		},
	}
}

func startCQRSWorkers(cqrs *cqrsBundle, log *zap.Logger) {
	go cqrs.outboxPublisherRun()
	go cqrs.outboxCleanerRun()
	go cqrs.dlqCleanerRun()

	go func() {
		if err := cqrs.commSyncWorker.Run(context.Background()); err != nil {
			log.Error("Community sync worker stopped", zap.Error(err))
		}
	}()
	go func() {
		if err := cqrs.taskSyncWorker.Run(context.Background()); err != nil {
			log.Error("Task sync worker stopped", zap.Error(err))
		}
	}()
	go func() {
		if err := cqrs.galaxySyncWorker.Run(context.Background()); err != nil {
			log.Error("Galaxy sync worker stopped", zap.Error(err))
		}
	}()
}

func setupRouter(cfg *config.Config, dbh *databaseHandles, rdb *redisv9.Client, services *serviceBundle, handlers *handlerBundle, cqrs *cqrsBundle, proxy *proxyBundle) *gin.Engine {
	r := gin.Default()
	r.GET("/metrics", gin.WrapH(promhttp.Handler()))
	r.Use(otelgin.Middleware("sparkle-gateway"))
	r.Use(middleware.RequestContextMiddleware())
	r.Use(middleware.SecurityHeadersMiddleware())
	if cfg.CORSEnabled {
		r.Use(middleware.CORSMiddleware(cfg))
	}
	healthVersion := os.Getenv("APP_VERSION")
	if strings.TrimSpace(healthVersion) == "" {
		healthVersion = "dev"
	}
	handler.NewHealthHandler(dbh.pool, rdb, healthVersion).RegisterRoutes(r)

	r.GET("/ws/chat", middleware.WsAuthMiddleware(cfg, rdb), handlers.chatOrchestrator.HandleWebSocket)
	r.GET("/ws/files", middleware.WsAuthMiddleware(cfg, rdb), handlers.fileEventHandler.HandleWebSocket)
	r.GET("/ws/stt", middleware.WsAuthMiddleware(cfg, rdb), handlers.sttHandler.HandleWebSocket)

	r.GET("/api/v1/community/groups/:group_id/ws",
		middleware.WsAuthMiddleware(cfg, rdb),
		handlers.wsProxy.HandleCommunityWS)
	r.GET("/api/v1/community/ws/connect",
		middleware.WsAuthMiddleware(cfg, rdb),
		handlers.wsProxy.HandlePersonalWS)

	authMiddleware := middleware.AuthMiddleware(cfg)
	authRateLimit := middleware.AuthRateLimitMiddleware()

	api := r.Group("/api/v1")
	{
		api.GET("/health", func(c *gin.Context) {
			c.JSON(http.StatusOK, gin.H{
				"status": "ok",
				"ready":  "/ready",
				"live":   "/live",
			})
		})
		api.GET("/health/cqrs", func(c *gin.Context) {
			outboxPendingCount, err := cqrs.outboxRepo.GetPendingCount(context.Background())
			if err != nil {
				c.JSON(http.StatusInternalServerError, gin.H{
					"status": "error",
					"error":  err.Error(),
				})
				return
			}

			commRunning := cqrs.commSyncWorker.IsRunning()
			taskRunning := cqrs.taskSyncWorker.IsRunning()
			galaxyRunning := cqrs.galaxySyncWorker.IsRunning()

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
		})

		api.POST("/auth/apple", authRateLimit, handlers.authHandler.AppleLogin)
		api.POST(
			"/ws/ticket",
			authMiddleware,
			middleware.UserBasedRateLimit(cfg.WSTicketRateRPS, cfg.WSTicketRateBurst),
			handlers.wsTicketHandler.Issue,
		)
		api.GET("/chat/sessions", authMiddleware, handlers.chatHistoryHandler.GetRecentSessions)
		api.GET("/chat/history/:conversation_id", authMiddleware, handlers.chatHistoryHandler.GetConversationHistory)

		api.GET("/groups/:group_id/messages", authMiddleware, handlers.groupChatHandler.GetMessages)
		handlers.errorBookHandler.RegisterRoutes(api, authMiddleware)

		commCmdService := service.NewCommunityCommandService(dbh.pool)
		commQueryService := service.NewCommunityQueryService(rdb)
		commHandler := v1.NewCommunityHandler(commCmdService, commQueryService)
		commHandler.RegisterRoutes(api, authMiddleware)

		handlers.fileHandler.RegisterRoutes(api, authMiddleware)
		handlers.dataConsistencyHandler.RegisterRoutes(api)

		// Galaxy routes - authentication passthrough with rate limiting
		galaxyRateLimit := middleware.UserBasedRateLimit(10, 20) // 10 RPS, 20 burst
		handlers.galaxyHandler.RegisterRoutes(api, authMiddleware, galaxyRateLimit)

		api.Any("/interventions/*path", authMiddleware, handlers.interventionProxyHandler.Proxy)
		api.Any("/dashboard/*path", authMiddleware, handlers.dashboardProxyHandler.Proxy)
		api.Any("/predictive/*path", authMiddleware, handlers.predictiveProxyHandler.Proxy)
	}

	internal := r.Group("/internal", middleware.InternalAPIKeyMiddleware(cfg))
	{
		internal.POST("/interventions/push", handlers.interventionPushHandler.HandlePush)
		internal.POST("/signals/push", handlers.signalPushHandler.HandlePush)
	}

	r.GET("/swagger/*any", ginSwagger.WrapHandler(swaggerFiles.Handler))

	admin := r.Group("/admin", middleware.AdminAuthMiddleware(cfg))
	{
		chaosRoutes := admin.Group("/chaos", middleware.ChaosGuardMiddleware(cfg))
		chaosRoutes.POST("/inject", dbh.chaosManager.HandleInject)
		chaosRoutes.POST("/config", handlers.chaosHandler.SetThreshold)
		chaosRoutes.GET("/status", handlers.chaosHandler.GetStatus)
		chaosRoutes.POST("/grpc/latency", handlers.chaosHandler.SetGrpcLatency)
		chaosRoutes.DELETE("/grpc/latency", handlers.chaosHandler.ResetGrpcLatency)

		admin.GET("/cqrs/projections", func(c *gin.Context) {
			projections, err := cqrs.projectionManager.GetAllProjections(c.Request.Context())
			if err != nil {
				c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
				return
			}
			c.JSON(http.StatusOK, projections)
		})

		admin.GET("/cqrs/projections/:name", func(c *gin.Context) {
			name := c.Param("name")
			info, err := cqrs.projectionManager.GetProjectionInfo(c.Request.Context(), name)
			if err != nil {
				c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
				return
			}
			c.JSON(http.StatusOK, info)
		})

		admin.POST("/cqrs/projections/:name/reset", func(c *gin.Context) {
			name := c.Param("name")
			if err := cqrs.projectionManager.ResetProjection(c.Request.Context(), name); err != nil {
				c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
				return
			}
			c.JSON(http.StatusOK, gin.H{"status": "resetting"})
		})

		admin.POST("/cqrs/projections/:name/pause", func(c *gin.Context) {
			name := c.Param("name")
			if err := cqrs.projectionManager.PauseProjection(c.Request.Context(), name); err != nil {
				c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
				return
			}
			c.JSON(http.StatusOK, gin.H{"status": "paused"})
		})

		admin.POST("/cqrs/projections/:name/resume", func(c *gin.Context) {
			name := c.Param("name")
			if err := cqrs.projectionManager.ResumeProjection(c.Request.Context(), name); err != nil {
				c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
				return
			}
			c.JSON(http.StatusOK, gin.H{"status": "resumed"})
		})

		admin.GET("/cqrs/snapshots/:name/count", func(c *gin.Context) {
			name := c.Param("name")
			count, err := cqrs.snapshotManager.GetSnapshotCount(c.Request.Context(), name)
			if err != nil {
				c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
				return
			}
			c.JSON(http.StatusOK, gin.H{"count": count})
		})

		admin.POST("/cqrs/projections/:name/rebuild", func(c *gin.Context) {
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
				progress, err := cqrs.projectionBuilder.RebuildFromEventStore(ctx, name, aggregateType, opts)
				if err != nil {
					log.Printf("Projection rebuild failed: projection=%s err=%v", name, err)
				} else {
					log.Printf(
						"Projection rebuild completed: projection=%s processed=%d duration=%s",
						name,
						progress.ProcessedEvents,
						progress.Duration,
					)
				}
			}()

			c.JSON(http.StatusOK, gin.H{
				"status":  "rebuild_started",
				"message": "Rebuild is running in background. Check /admin/cqrs/projections/" + name + " for status",
			})
		})

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
				progress, err := cqrs.projectionBuilder.RebuildFromSnapshot(ctx, name, aggregateType, opts)
				if err != nil {
					log.Printf("Projection rebuild from snapshot failed: projection=%s err=%v", name, err)
				} else {
					log.Printf(
						"Projection rebuild from snapshot completed: projection=%s processed=%d duration=%s",
						name,
						progress.ProcessedEvents,
						progress.Duration,
					)
				}
			}()

			c.JSON(http.StatusOK, gin.H{
				"status":  "rebuild_started",
				"message": "Rebuild from snapshot is running in background",
			})
		})

		admin.POST("/cqrs/projections/:name/snapshot", func(c *gin.Context) {
			name := c.Param("name")
			info, err := cqrs.projectionManager.GetProjectionInfo(c.Request.Context(), name)
			if err != nil {
				c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
				return
			}

			snapshotData := map[string]interface{}{
				"projection_name": name,
				"position":        info.LastProcessedPosition,
				"status":          info.Status,
				"version":         info.Version,
			}

			if err := cqrs.projectionBuilder.CreateSnapshot(c.Request.Context(), name, snapshotData); err != nil {
				c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
				return
			}

			c.JSON(http.StatusOK, gin.H{
				"status":   "snapshot_created",
				"position": info.LastProcessedPosition,
			})
		})

		admin.GET("/cqrs/dlq/stats", func(c *gin.Context) {
			stats, err := cqrs.dlqHandler.GetStats(c.Request.Context())
			if err != nil {
				c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
				return
			}
			c.JSON(http.StatusOK, stats)
		})

		admin.POST("/cqrs/dlq/cleanup", func(c *gin.Context) {
			deleted, err := cqrs.dlqHandler.Cleanup(c.Request.Context())
			if err != nil {
				c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
				return
			}
			c.JSON(http.StatusOK, gin.H{
				"status":        "cleanup_completed",
				"deleted_count": deleted,
			})
		})

		admin.POST("/cqrs/dlq/retry/:message_id", func(c *gin.Context) {
			messageID := c.Param("message_id")
			if err := cqrs.dlqHandler.RetryEntry(c.Request.Context(), messageID); err != nil {
				c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
				return
			}
			c.JSON(http.StatusOK, gin.H{
				"status":     "retry_submitted",
				"message_id": messageID,
			})
		})

		admin.DELETE("/cqrs/dlq/:message_id", func(c *gin.Context) {
			messageID := c.Param("message_id")
			if err := cqrs.dlqHandler.DeleteEntry(c.Request.Context(), messageID); err != nil {
				c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
				return
			}
			c.JSON(http.StatusOK, gin.H{
				"status":     "deleted",
				"message_id": messageID,
			})
		})

		admin.GET("/cqrs/outbox/stats", func(c *gin.Context) {
			pendingCount, err := cqrs.outboxRepo.GetPendingCount(c.Request.Context())
			if err != nil {
				c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
				return
			}
			c.JSON(http.StatusOK, gin.H{
				"pending_count": pendingCount,
			})
		})
	}

	r.NoRoute(func(c *gin.Context) {
		path := c.Request.URL.Path

		if strings.HasPrefix(path, "/api/v1/auth") ||
			path == "/api/v1/health" ||
			strings.HasPrefix(path, "/docs") ||
			strings.HasPrefix(path, "/redoc") ||
			strings.HasPrefix(path, "/openapi.json") {
			if strings.HasPrefix(path, "/api/v1/auth") {
				authRateLimit(c)
				if c.IsAborted() {
					return
				}
			}
			proxy.proxy.ServeHTTP(c.Writer, c.Request)
			return
		}

		authMiddleware(c)
		if c.IsAborted() {
			return
		}

		userID := c.GetString("user_id")
		if userID != "" {
			c.Request.Header.Set("X-User-ID", userID)
		}
		if token := c.GetString("auth_token"); token != "" {
			c.Request.Header.Set("Authorization", "Bearer "+token)
		}

		proxy.abTestMiddleware.AssignVariant()(c)
		proxy.proxy.ServeHTTP(c.Writer, c.Request)
		proxy.abTestMiddleware.RecordMetricAfter(c)
	})

	return r
}

func setupProxy(cfg *config.Config) (*proxyBundle, error) {
	backendURL := cfg.BackendURL
	if backendURL == "" {
		backendURL = "http://sparkle_api:8000"
	}
	abTestMiddleware := middleware.NewABTestMiddleware(&middleware.ABTestConfig{
		BackendURL: backendURL,
		Timeout:    3 * time.Second,
		Enabled:    true,
	})
	targetURL, err := url.Parse(backendURL)
	if err != nil {
		return nil, err
	}

	proxy := httputil.NewSingleHostReverseProxy(targetURL)
	proxy.Director = func(req *http.Request) {
		req.URL.Scheme = targetURL.Scheme
		req.URL.Host = targetURL.Host
		req.Host = targetURL.Host
		otel.GetTextMapPropagator().Inject(req.Context(), propagation.HeaderCarrier(req.Header))
	}

	transport := &http.Transport{
		Proxy: http.ProxyFromEnvironment,
		DialContext: (&net.Dialer{
			Timeout:   30 * time.Second,
			KeepAlive: 30 * time.Second,
		}).DialContext,
		MaxIdleConns:          100,
		IdleConnTimeout:       90 * time.Second,
		TLSHandshakeTimeout:   10 * time.Second,
		ExpectContinueTimeout: 1 * time.Second,
		DisableKeepAlives:     false,
		ForceAttemptHTTP2:     true,
	}
	proxy.Transport = transport
	proxy.FlushInterval = -1

	return &proxyBundle{
		proxy:            proxy,
		abTestMiddleware: abTestMiddleware,
	}, nil
}
