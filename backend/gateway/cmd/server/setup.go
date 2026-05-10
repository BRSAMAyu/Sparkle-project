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
	"github.com/sparkle/gateway/internal/chaos"
	"github.com/sparkle/gateway/internal/config"
	"github.com/sparkle/gateway/internal/cqrs"
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
	appleAccount   *service.AppleAccountService
	groupChat      *service.GroupChatService
	consistency    *service.DataConsistencyService
}

type handlerBundle struct {
	wsFactory               *handler.WebSocketFactory
	wsTicketHandler         *handler.WSTicketHandler
	chatHistoryHandler      *handler.ChatHistoryHandler
	fileEventHandler        *handler.FileEventHandler
	chatOrchestrator        *handler.ChatOrchestrator
	signalPushHandler       *handler.SignalPushHandler
	groupChatHandler        *handler.GroupChatHandler
	errorBookHandler        *handler.ErrorBookHandler
	chaosHandler            *handler.ChaosHandler
	fileHandler             *handler.FileHandler
	interventionPushHandler *handler.InterventionPushHandler
	dataConsistencyHandler  *handler.DataConsistencyHandler
	sttHandler              *handler.STTHandler
	wsProxy                 *handler.WebSocketProxy
	authHandler             *handler.AuthHandler
	galaxyHandler           *handler.GalaxyHandler
	proxyRoutesHandler      *handler.ProxyRoutesHandler
}

type cqrsBundle struct {
	metrics            *metrics.CQRSMetrics
	outboxRepo         *outbox.PostgresRepository
	projectionManager  *projection.Manager
	snapshotManager    *projection.SnapshotManager
	projectionBuilder  *projection.Builder
	dlqHandler         *cqrsWorker.DLQHandler
	sagaCoordinator    *cqrs.SagaCoordinator
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

const (
	defaultDBMaxConns        int32 = 30
	defaultDBMinConns        int32 = 5
	defaultDBMaxConnIdleTime       = 15 * time.Minute
)

func initTracer() func(context.Context) error {
	return otelinfra.InitTracer("sparkle-gateway")
}

func initDatabase(ctx context.Context, cfg *config.Config) (*databaseHandles, error) {
	poolConfig, err := pgxpool.ParseConfig(cfg.DatabaseURL)
	if err != nil {
		return nil, err
	}
	applyDefaultPoolConfig(poolConfig)

	pool, err := pgxpool.NewWithConfig(ctx, poolConfig)
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

func applyDefaultPoolConfig(poolConfig *pgxpool.Config) {
	poolConfig.MaxConns = defaultDBMaxConns
	poolConfig.MinConns = defaultDBMinConns
	poolConfig.MaxConnIdleTime = defaultDBMaxConnIdleTime
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
	chatHistoryService := service.NewChatHistoryServiceWithPool(rdb, dbh.pool, chatHistoryTTL)
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
		appleAccount:   service.NewAppleAccountService(dbh.queries),
		groupChat:      service.NewGroupChatService(dbh.queries),
		consistency:    service.NewDataConsistencyService(chatHistoryService, dbh.queries, rdb),
	}, nil
}

func initClients(cfg *config.Config) (*agent.Client, *galaxy.Client, *error_book.Client, error) {
	healthCheckInterval := time.Duration(cfg.AgentHealthCheckInterval) * time.Second
	if healthCheckInterval <= 0 {
		healthCheckInterval = 10 * time.Second
	}
	healthCheckTimeout := time.Duration(cfg.AgentHealthCheckTimeout) * time.Second
	if healthCheckTimeout <= 0 {
		healthCheckTimeout = 5 * time.Second
	}
	agentClient, err := agent.NewClientWithHealthCheck(cfg, healthCheckInterval, healthCheckTimeout)
	if err != nil {
		return nil, nil, nil, err
	}

	galaxyClient, err := galaxy.NewClient(cfg)
	if err != nil {
		log.Printf("Warning: Unable to connect to galaxy service: %v", err)
		galaxyClient = nil // explicit nil; downstream handlers check for nil
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
		service.NewDBUserIdentityService(dbh.queries),
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
	groupChatHandler := handler.NewGroupChatHandler(services.groupChat)
	errorBookHandler := handler.NewErrorBookHandler(errorBookClient)
	chaosHandler := handler.NewChaosHandler(services.chatHistory, cfg.ToxiproxyURL)
	fileHandler := handler.NewFileHandler(services.fileStorage, services.fileMetadata, services.fileProcessing)
	interventionPushHandler := handler.NewInterventionPushHandler(chatOrchestrator)
	dataConsistencyHandler := handler.NewDataConsistencyHandler(services.consistency)

	sttURL := strings.Replace(cfg.BackendURL, "http://", "ws://", 1)
	sttURL = strings.Replace(sttURL, "https://", "wss://", 1)
	sttHandler := handler.NewSTTHandler(sttURL+"/api/v1/stt/stream", logger, cfg)

	wsProxy := handler.NewWebSocketProxy(cfg.BackendURL, logger, cfg, service.NewMessageDedupService(rdb))

	appleAuthService, err := service.NewAppleAuthService(cfg)
	if err != nil {
		log.Fatalf("Apple Auth Service init failed: %v", err)
	}
	authHandler := handler.NewAuthHandler(cfg, appleAuthService, services.appleAccount)

	// Galaxy handler for knowledge graph endpoints
	var galaxyCommandService *service.GalaxyCommandService
	if dbh.pool != nil {
		galaxyCommandService = service.NewGalaxyCommandService(dbh.pool)
	}
	galaxyHandler := handler.NewGalaxyHandler(galaxyClient, galaxyCommandService, rdb, cfg.BackendURL)

	return &handlerBundle{
		wsFactory:               wsFactory,
		wsTicketHandler:         wsTicketHandler,
		chatHistoryHandler:      chatHistoryHandler,
		fileEventHandler:        fileEventHandler,
		chatOrchestrator:        chatOrchestrator,
		signalPushHandler:       signalPushHandler,
		groupChatHandler:        groupChatHandler,
		errorBookHandler:        errorBookHandler,
		chaosHandler:            chaosHandler,
		fileHandler:             fileHandler,
		interventionPushHandler: interventionPushHandler,
		dataConsistencyHandler:  dataConsistencyHandler,
		sttHandler:              sttHandler,
		wsProxy:                 wsProxy,
		authHandler:             authHandler,
		galaxyHandler:           galaxyHandler,
	}, nil
}

func initCQRS(ctx context.Context, cfg *config.Config, dbh *databaseHandles, rdb *redisv9.Client, services *serviceBundle, logger *zap.Logger) *cqrsBundle {
	cqrsMetrics := metrics.NewCQRSMetrics("sparkle")
	eventBus := cqrsEvent.NewRedisEventBus(rdb)

	// FV-20: Initialize Saga coordinator for distributed transactions
	sagaCoordinator := cqrs.NewSagaCoordinator(dbh.pool, eventBus, logger)
	if err := sagaCoordinator.EnsureSchema(ctx); err != nil {
		logger.Error("Failed to ensure saga schema", zap.Error(err))
	}
	// Register the 4 cross-service saga definitions
	sagaCoordinator.Register(cqrs.NewTaskCreateSaga(
		cqrs.StepFunc{StepName: "create_task"},
		cqrs.StepFunc{StepName: "send_notification"},
		cqrs.StepFunc{StepName: "crdt_sync"},
	))
	sagaCoordinator.Register(cqrs.NewSourceUploadSaga(
		cqrs.StepFunc{StepName: "upload_source"},
		cqrs.StepFunc{StepName: "parse_content"},
		cqrs.StepFunc{StepName: "mount_nodes"},
	))
	sagaCoordinator.Register(cqrs.NewExperimentPromotionSaga(
		cqrs.StepFunc{StepName: "promote_experiment"},
		cqrs.StepFunc{StepName: "notify_stakeholders"},
		cqrs.StepFunc{StepName: "write_audit"},
	))
	sagaCoordinator.Register(cqrs.NewSkillPublishSaga(
		cqrs.StepFunc{StepName: "publish_skill"},
		cqrs.StepFunc{StepName: "register_marketplace"},
		cqrs.StepFunc{StepName: "send_notification"},
	))

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

	commSyncWorker := worker.NewCommunitySyncWorker(rdb, dbh.pool, cqrsMetrics, logger)
	taskSyncWorker := worker.NewTaskSyncWorker(rdb, dbh.pool, cqrsMetrics, logger)
	galaxySyncWorker := worker.NewGalaxySyncWorker(rdb, dbh.pool, cqrsMetrics, logger)

	fileEventSubscriber := service.NewFileEventSubscriber(rdb, services.fileEventHub, logger)
	go func() {
		if err := fileEventSubscriber.Run(ctx); err != nil {
			logger.Error("File event subscriber stopped", zap.Error(err))
		}
	}()

	fileGC := service.NewFileGCService(services.fileMetadata, services.fileStorage, cfg, logger)
	go func() {
		if err := fileGC.Run(ctx); err != nil {
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
		sagaCoordinator:   sagaCoordinator,
		commSyncWorker:    commSyncWorker,
		taskSyncWorker:    taskSyncWorker,
		galaxySyncWorker:  galaxySyncWorker,
		outboxPublisherRun: func() {
			if err := outboxPublisher.Run(ctx); err != nil {
				logger.Error("Outbox publisher stopped", zap.Error(err))
			}
		},
		outboxCleanerRun: func() {
			if err := outboxCleaner.Run(ctx); err != nil {
				logger.Error("Outbox cleaner stopped", zap.Error(err))
			}
		},
		dlqCleanerRun: func() {
			if err := dlqCleaner.Run(ctx); err != nil {
				logger.Error("DLQ cleaner stopped", zap.Error(err))
			}
		},
	}
}

func startCQRSWorkers(ctx context.Context, cqrs *cqrsBundle, log *zap.Logger) {
	go cqrs.outboxPublisherRun()
	go cqrs.outboxCleanerRun()
	go cqrs.dlqCleanerRun()

	go func() {
		if err := cqrs.commSyncWorker.Run(ctx); err != nil {
			log.Error("Community sync worker stopped", zap.Error(err))
		}
	}()
	go func() {
		if err := cqrs.taskSyncWorker.Run(ctx); err != nil {
			log.Error("Task sync worker stopped", zap.Error(err))
		}
	}()
	go func() {
		if err := cqrs.galaxySyncWorker.Run(ctx); err != nil {
			log.Error("Galaxy sync worker stopped", zap.Error(err))
		}
	}()
}

func setupRouter(cfg *config.Config, dbh *databaseHandles, rdb *redisv9.Client, services *serviceBundle, handlers *handlerBundle, cqrs *cqrsBundle, proxy *proxyBundle, agentClient *agent.Client, logger *zap.Logger) *gin.Engine {
	r := gin.Default()

	// Configure trusted proxies for accurate ClientIP() behind load balancers
	if len(cfg.TrustedProxies) > 0 {
		if err := r.SetTrustedProxies(cfg.TrustedProxies); err != nil {
			logger.Warn("Failed to set trusted proxies, using defaults", zap.Error(err))
		}
	} else if cfg.IsProduction() {
		logger.Fatal("TRUSTED_PROXIES not set in production. " +
			"Set TRUSTED_PROXIES to your load balancer IP(s).")
	}
	if cfg.IsDevelopment() {
		r.GET("/metrics", gin.WrapH(promhttp.Handler()))
	}
	r.Use(otelgin.Middleware("sparkle-gateway"))
	r.Use(middleware.I18n())
	r.Use(middleware.RequestContextMiddleware())
	r.Use(middleware.SecurityHeadersMiddleware(cfg))
	if cfg.CORSEnabled {
		r.Use(middleware.CORSMiddleware(cfg))
	}
	healthVersion := os.Getenv("APP_VERSION")
	if strings.TrimSpace(healthVersion) == "" {
		healthVersion = "dev"
	}
	handler.NewHealthHandler(dbh.pool, rdb, agentClient, healthVersion).RegisterRoutes(r)

	r.GET("/ws/chat", middleware.WsAuthMiddleware(cfg, rdb), handlers.chatOrchestrator.HandleWebSocket)
	r.GET("/ws/files", middleware.WsAuthMiddleware(cfg, rdb), handlers.fileEventHandler.HandleWebSocket)
	r.GET("/ws/stt", middleware.WsAuthMiddleware(cfg, rdb), handlers.sttHandler.HandleWebSocket)

	r.GET("/api/v1/community/groups/:group_id/ws",
		middleware.WsAuthMiddleware(cfg, rdb),
		handlers.wsProxy.HandleCommunityWS)
	r.GET("/api/v1/community/ws/connect",
		middleware.WsAuthMiddleware(cfg, rdb),
		handlers.wsProxy.HandlePersonalWS)

	authMiddleware := middleware.AuthMiddleware(cfg, rdb)
	authRateLimit := middleware.HybridRateLimitMiddlewareSimple(rdb, 5.0, 15)
	apiRateLimit := middleware.HybridRateLimitMiddlewareSimple(rdb, 15, 30)
	adminRateLimit := middleware.AdminRateLimitMiddleware(rdb)
	internalRateLimit := middleware.InternalRateLimitMiddleware(rdb)

	requestTimeout := 30
	if cfg.RequestTimeoutSeconds > 0 {
		requestTimeout = cfg.RequestTimeoutSeconds
	}

	// Create explicit proxy routes handler for better control and observability
	proxyRoutesHandler := handler.NewProxyRoutesHandler(
		proxy.proxy,
		proxy.abTestMiddleware,
		logger,
	)

	// Health endpoints outside rate-limited group for reliable monitoring access
		// route-tier: public
	r.GET("/api/v1/health", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{
			"status": "ok",
			"ready":  "/ready",
			"live":   "/live",
		})
	})
	r.GET("/api/v1/health/cqrs", authMiddleware, func(c *gin.Context) {
		// route-tier: authenticated — requires valid JWT; DB errors are sanitized
		outboxPendingCount, err := cqrs.outboxRepo.GetPendingCount(c.Request.Context())
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{
				"status": "error",
				"error":  "CQRS outbox component unhealthy",
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

	// route-tier: internal
	api := r.Group("/api/v1")
	api.Use(apiRateLimit)
	api.Use(middleware.MaxBodySizeMiddleware(middleware.DefaultMaxBodyBytes))
	api.Use(middleware.TimeoutMiddleware(time.Duration(requestTimeout) * time.Second))
	{
		api.POST("/auth/apple", authRateLimit, handlers.authHandler.AppleLogin)
		api.POST(
			"/ws/ticket",
			authMiddleware,
			middleware.HybridRateLimitMiddlewareSimple(rdb, cfg.WSTicketRateRPS, cfg.WSTicketRateBurst),
			handlers.wsTicketHandler.Issue,
		)
		api.GET("/chat/sessions", authMiddleware, handlers.chatHistoryHandler.GetRecentSessions)
		api.GET("/chat/history/:conversation_id", authMiddleware, handlers.chatHistoryHandler.GetConversationHistory)
		api.PATCH("/conversations/:conversation_id/settings", authMiddleware, handlers.chatHistoryHandler.PatchConversationSettings)

		api.GET("/groups/:group_id/messages", authMiddleware, handlers.groupChatHandler.GetMessages)
		handlers.errorBookHandler.RegisterRoutes(api, authMiddleware)

		handlers.fileHandler.RegisterRoutes(api, authMiddleware)
		handlers.dataConsistencyHandler.RegisterRoutes(api, authMiddleware)

		// Galaxy routes - authentication passthrough with rate limiting
		galaxyRateLimit := middleware.HybridRateLimitMiddlewareSimple(rdb, 10, 20)
		handlers.galaxyHandler.RegisterRoutes(api, authMiddleware, galaxyRateLimit)

		// Register explicit proxy routes for critical Python Backend APIs
		proxyRoutesHandler.RegisterProxyRoutes(api, authMiddleware)
	}

	internal := r.Group(
		"/internal",
		middleware.InternalAPIKeyMiddleware(cfg),
		middleware.InternalIPWhitelistMiddleware(cfg),
		internalRateLimit,
	)
	{
		// route-tier: internal
		internal.GET("/files/:file_id/download", handlers.fileHandler.GetInternalDownloadURL)
		internal.POST("/interventions/push", handlers.interventionPushHandler.HandlePush)
			// route-tier: internal
		internal.POST("/signals/push", handlers.signalPushHandler.HandlePush)
	}

	// FV-24: Network resilience middleware for upstream proxy routes
	resilienceCfg := middleware.DefaultNetworkResilienceConfig()
	r.Use(middleware.NetworkResilienceMiddleware(resilienceCfg))

	if cfg.IsDevelopment() {
		r.GET("/swagger/*any", ginSwagger.WrapHandler(swaggerFiles.Handler))
	}

	// route-tier: internal
	admin := r.Group("/admin", middleware.AdminAuthMiddleware(cfg), adminRateLimit)
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
				c.JSON(http.StatusInternalServerError, gin.H{"error": "internal error"})
				return
			}
			c.JSON(http.StatusOK, projections)
		})

		admin.GET("/cqrs/projections/:name", func(c *gin.Context) {
			name := c.Param("name")
			info, err := cqrs.projectionManager.GetProjectionInfo(c.Request.Context(), name)
			if err != nil {
				c.JSON(http.StatusInternalServerError, gin.H{"error": "internal error"})
				return
			}
			c.JSON(http.StatusOK, info)
		})

		admin.POST("/cqrs/projections/:name/reset", func(c *gin.Context) {
			name := c.Param("name")
			if err := cqrs.projectionManager.ResetProjection(c.Request.Context(), name); err != nil {
				c.JSON(http.StatusInternalServerError, gin.H{"error": "internal error"})
				return
			}
			c.JSON(http.StatusOK, gin.H{"status": "resetting"})
		})

		admin.POST("/cqrs/projections/:name/pause", func(c *gin.Context) {
			name := c.Param("name")
			if err := cqrs.projectionManager.PauseProjection(c.Request.Context(), name); err != nil {
				c.JSON(http.StatusInternalServerError, gin.H{"error": "internal error"})
				return
			}
			c.JSON(http.StatusOK, gin.H{"status": "paused"})
		})

		admin.POST("/cqrs/projections/:name/resume", func(c *gin.Context) {
			name := c.Param("name")
			if err := cqrs.projectionManager.ResumeProjection(c.Request.Context(), name); err != nil {
				c.JSON(http.StatusInternalServerError, gin.H{"error": "internal error"})
				return
			}
			c.JSON(http.StatusOK, gin.H{"status": "resumed"})
		})

		admin.GET("/cqrs/snapshots/:name/count", func(c *gin.Context) {
			name := c.Param("name")
			count, err := cqrs.snapshotManager.GetSnapshotCount(c.Request.Context(), name)
			if err != nil {
				c.JSON(http.StatusInternalServerError, gin.H{"error": "internal error"})
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
				c.JSON(http.StatusInternalServerError, gin.H{"error": "internal error"})
				return
			}

			snapshotData := map[string]interface{}{
				"projection_name": name,
				"position":        info.LastProcessedPosition,
				"status":          info.Status,
				"version":         info.Version,
			}

			if err := cqrs.projectionBuilder.CreateSnapshot(c.Request.Context(), name, snapshotData); err != nil {
				c.JSON(http.StatusInternalServerError, gin.H{"error": "internal error"})
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
				c.JSON(http.StatusInternalServerError, gin.H{"error": "internal error"})
				return
			}
			c.JSON(http.StatusOK, stats)
		})

		admin.POST("/cqrs/dlq/cleanup", func(c *gin.Context) {
			deleted, err := cqrs.dlqHandler.Cleanup(c.Request.Context())
			if err != nil {
				c.JSON(http.StatusInternalServerError, gin.H{"error": "internal error"})
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
				c.JSON(http.StatusInternalServerError, gin.H{"error": "internal error"})
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
				c.JSON(http.StatusInternalServerError, gin.H{"error": "internal error"})
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
				c.JSON(http.StatusInternalServerError, gin.H{"error": "internal error"})
				return
			}
			c.JSON(http.StatusOK, gin.H{
				"pending_count": pendingCount,
			})
		})
	}

	// route-tier: deprecated
	r.NoRoute(func(c *gin.Context) {
		path := c.Request.URL.Path
		method := c.Request.Method

		// DEBUG: 记录所有 NoRoute 请求
		zap.L().Debug("NoRoute: proxying request",
			zap.String("path", path),
			zap.String("method", method),
			zap.String("query", c.Request.URL.RawQuery))

		if shouldProxyNoRoutePath(path) {
			authRateLimit(c)
			if c.IsAborted() {
				return
			}
			// R5-G01: Privileged paths (logout, upgrade-guest) require auth
			if isPrivilegedNoRoutePath(path) {
				authMiddleware(c)
				if c.IsAborted() {
					return
				}
			}
			handler.SetProxyUserContextHeaders(c)
				proxy.proxy.ServeHTTP(c.Writer, c.Request)

			// 记录代理结果
			zap.L().Debug("NoRoute: auth path proxy completed",
				zap.String("path", path),
				zap.Int("status", c.Writer.Status()))
			return
		}

		c.JSON(http.StatusNotFound, gin.H{"error": "route not found"})
	})

	return r
}

func shouldProxyNoRoutePath(path string) bool {
	// Only proxy specific public auth paths — do NOT open-proxy /api/v1/auth/*
	// Apple login is handled by Go handler directly, so excluded here.
	publicAuthPrefixes := []string{
		"/api/v1/auth/register",
		"/api/v1/auth/login",
		"/api/v1/auth/social-login",
		"/api/v1/auth/refresh",
		"/api/v1/auth/forgot-password",
		"/api/v1/auth/reset-password",
		"/api/v1/auth/send-verification",
		"/api/v1/auth/verify-email",
		"/api/v1/auth/guest",
		"/api/v1/auth/logout",
		"/api/v1/auth/upgrade-guest",
	}
	for _, prefix := range publicAuthPrefixes {
		if strings.HasPrefix(path, prefix) {
			return true
		}
	}
	return false
}

// isPrivilegedNoRoutePath returns true for paths that require authentication
// even though they are proxied through NoRoute.
func isPrivilegedNoRoutePath(path string) bool {
	privileged := []string{
		"/api/v1/auth/logout",
		"/api/v1/auth/upgrade-guest",
	}
	for _, prefix := range privileged {
		if strings.HasPrefix(path, prefix) {
			return true
		}
	}
	return false
}

func setupProxy(cfg *config.Config, logger *zap.Logger) (*proxyBundle, error) {
	backendURL := cfg.BackendURL
	if backendURL == "" {
		backendURL = "http://sparkle_api:8000"
	}
	logger.Info("Gateway proxy configured",
		zap.String("backend_url", backendURL))

	abTestMiddleware := middleware.NewABTestMiddleware(&middleware.ABTestConfig{
		BackendURL: backendURL,
		Timeout:    3 * time.Second,
		Enabled:    true,
	})
	targetURL, err := url.Parse(backendURL)
	if err != nil {
		return nil, err
	}

	logger.Info("Gateway proxy target resolved",
		zap.String("target_host", targetURL.Host),
		zap.String("target_scheme", targetURL.Scheme))

	proxy := httputil.NewSingleHostReverseProxy(targetURL)
	proxy.Director = func(req *http.Request) {
		req.URL.Scheme = targetURL.Scheme
		req.URL.Host = targetURL.Host
		req.Host = targetURL.Host

		// Forward standard proxy headers so Python backend sees real client info
		if clientIP, _, err := net.SplitHostPort(req.RemoteAddr); err == nil {
			prior := req.Header.Get("X-Forwarded-For")
			if prior != "" {
				req.Header.Set("X-Forwarded-For", prior+", "+clientIP)
			} else {
				req.Header.Set("X-Forwarded-For", clientIP)
			}
		}
		if req.Header.Get("X-Forwarded-Proto") == "" {
			req.Header.Set("X-Forwarded-Proto", "http")
		}
		if req.Header.Get("X-Forwarded-Host") == "" {
			req.Header.Set("X-Forwarded-Host", req.Host)
		}

		otel.GetTextMapPropagator().Inject(req.Context(), propagation.HeaderCarrier(req.Header))
	}

	transport := &http.Transport{
		Proxy: http.ProxyFromEnvironment,
		DialContext: (&net.Dialer{
			Timeout:   30 * time.Second,
			KeepAlive: 30 * time.Second,
		}).DialContext,
		MaxIdleConns:          100,
		MaxIdleConnsPerHost:   20,
		MaxConnsPerHost:       100,
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
